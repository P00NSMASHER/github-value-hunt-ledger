-- RETALLY PHASE 5C: dedicated fictional QA cash reconciliation. DO NOT APPLY TO PRODUCTION.
DO $isolation$ BEGIN
 IF (SELECT system_identifier::text FROM pg_control_system()) <> '7694294930552894346'
    OR to_regclass('public.recovery_tenants') IS NOT NULL
 THEN RAISE EXCEPTION 'PHASE5C_QA_CLUSTER_GUARD'; END IF;
END $isolation$;
CREATE SCHEMA IF NOT EXISTS phase5c_qa;
CREATE TABLE IF NOT EXISTS phase5c_qa.cases (
 tenant_id text NOT NULL CHECK (tenant_id LIKE 'SIM-%'),
 case_id text NOT NULL CHECK (case_id LIKE 'SIM-%'),
 customer_id text NOT NULL CHECK (customer_id LIKE 'SIM-%'),
 invoice_id text NOT NULL CHECK (invoice_id LIKE 'SIM-%'),
 carrier_id text NOT NULL CHECK (carrier_id LIKE 'SIM-%'),
 currency text NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
 max_claim_cents bigint NOT NULL CHECK (max_claim_cents >= 0),
 PRIMARY KEY (tenant_id,case_id)
);
CREATE TABLE IF NOT EXISTS phase5c_qa.issuer_keys (
 tenant_id text NOT NULL CHECK (tenant_id LIKE 'SIM-%'),
 key_id text NOT NULL CHECK (key_id LIKE 'SIM-%'),
 role text NOT NULL CHECK (role IN ('BUYER','CARRIER','BUYER_ACCOUNTING','RETALLY_BILLING','PAYMENT_PROCESSOR','INDEPENDENT_VERIFIER')),
 public_key_pem text NOT NULL CHECK (public_key_pem LIKE '-----BEGIN PUBLIC KEY%'),
 enabled_from timestamptz NOT NULL,
 expires_at timestamptz NOT NULL,
 revoked_at timestamptz,
 PRIMARY KEY(tenant_id,key_id),
 CHECK (expires_at > enabled_from)
);
CREATE TABLE IF NOT EXISTS phase5c_qa.documents (
 tenant_id text NOT NULL,
 case_id text NOT NULL,
 record_id text NOT NULL CHECK(record_id LIKE 'SIM-%'),
 kind text NOT NULL CHECK(kind IN (
 'CONTRACT','CARRIER_CREDIT','CUSTOMER_POST','CUSTOMER_REVERSAL',
 'FEE_INVOICE','FEE_COLLECTION','FEE_CREDIT','FEE_REFUND')),
 economic_key text NOT NULL CHECK(economic_key LIKE 'SIM-%'),
 reference_id text,
 amount_cents bigint NOT NULL CHECK(amount_cents >= 0),
 fee_bps integer,
 currency text NOT NULL CHECK(currency ~ '^[A-Z]{3}$'),
 occurred_at timestamptz NOT NULL,
 source_sha256 text NOT NULL CHECK(source_sha256 ~ '^[a-f0-9]{64}$'),
 issuer_key_id text NOT NULL,
 body jsonb NOT NULL,
 signature_b64 text NOT NULL CHECK (length(signature_b64)>=80),
 inserted_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
 PRIMARY KEY (tenant_id,record_id),
 UNIQUE(tenant_id,case_id,kind,economic_key),
 FOREIGN KEY(tenant_id,case_id) REFERENCES phase5c_qa.cases(tenant_id,case_id),
 FOREIGN KEY(tenant_id,issuer_key_id) REFERENCES phase5c_qa.issuer_keys(tenant_id,key_id),
 CHECK ((kind='CONTRACT' AND amount_cents=0 AND fee_bps BETWEEN 1 AND 9999)
      OR (kind<>'CONTRACT' AND fee_bps IS NULL AND amount_cents>0))
);
-- An external document may not be relabeled with a fresh record ID to count twice.
CREATE UNIQUE INDEX IF NOT EXISTS phase5c_one_artifact_per_economic_kind
 ON phase5c_qa.documents(tenant_id,case_id,kind,source_sha256);
CREATE OR REPLACE FUNCTION phase5c_qa.guard_signed_financial_record()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,phase5c_qa AS $body$
DECLARE c record; signer record; predecessor record; cap bigint; used bigint; earned bigint;
        invoice_total bigint; credited bigint; collected bigint; refunded bigint; invoice_credits bigint;
        net_post bigint; contract_bps integer; expected_role text;
BEGIN
 SELECT * INTO c FROM phase5c_qa.cases
 WHERE tenant_id=NEW.tenant_id AND case_id=NEW.case_id FOR UPDATE;
 IF NOT FOUND OR NEW.currency<>c.currency THEN RAISE EXCEPTION 'CROSS_CASE_OR_CURRENCY'; END IF;
 SELECT * INTO signer FROM phase5c_qa.issuer_keys
 WHERE tenant_id=NEW.tenant_id AND key_id=NEW.issuer_key_id;
 expected_role:=CASE NEW.kind
   WHEN 'CONTRACT' THEN 'BUYER'
   WHEN 'CARRIER_CREDIT' THEN 'CARRIER'
   WHEN 'CUSTOMER_POST' THEN 'BUYER_ACCOUNTING'
   WHEN 'CUSTOMER_REVERSAL' THEN 'BUYER_ACCOUNTING'
   WHEN 'FEE_INVOICE' THEN 'RETALLY_BILLING'
   WHEN 'FEE_COLLECTION' THEN 'PAYMENT_PROCESSOR'
   WHEN 'FEE_CREDIT' THEN 'RETALLY_BILLING'
   WHEN 'FEE_REFUND' THEN 'PAYMENT_PROCESSOR' END;
 IF NOT FOUND OR signer.role<>expected_role
 OR NEW.occurred_at<signer.enabled_from OR NEW.occurred_at>=signer.expires_at
 OR (signer.revoked_at IS NOT NULL AND NEW.occurred_at>=signer.revoked_at)
 THEN RAISE EXCEPTION 'INVALID_ISSUER_ROLE_OR_PERIOD'; END IF;
 IF NEW.body->>'tenantId' IS DISTINCT FROM NEW.tenant_id
 OR NEW.body->>'caseId' IS DISTINCT FROM NEW.case_id
 OR NEW.body->>'recordId' IS DISTINCT FROM NEW.record_id
 OR NEW.body->>'economicKey' IS DISTINCT FROM NEW.economic_key
 OR NEW.body->>'kind' IS DISTINCT FROM NEW.kind
 OR NEW.body->>'currency' IS DISTINCT FROM NEW.currency
 OR NEW.body->>'sourceHash' IS DISTINCT FROM NEW.source_sha256
 OR NEW.body->>'referenceId' IS DISTINCT FROM NEW.reference_id
 OR (NEW.body->>'amountCents')::bigint IS DISTINCT FROM NEW.amount_cents
 OR (NEW.body->>'feeBps')::int IS DISTINCT FROM NEW.fee_bps
 OR NEW.body->>'customerId' IS DISTINCT FROM c.customer_id
 OR NEW.body->>'invoiceId' IS DISTINCT FROM c.invoice_id
 OR NEW.body->>'issuerKeyId' IS DISTINCT FROM NEW.issuer_key_id
 THEN RAISE EXCEPTION 'SIGNED_ENVELOPE_SCOPE_MISMATCH'; END IF;
 IF NEW.kind='CONTRACT' THEN
   IF EXISTS(SELECT 1 FROM phase5c_qa.documents WHERE tenant_id=NEW.tenant_id AND case_id=NEW.case_id AND kind='CONTRACT')
   THEN RAISE EXCEPTION 'DUPLICATE_CONTRACT_VERSION_REQUIRES_AMENDMENT'; END IF;
   RETURN NEW;
 END IF;
 SELECT fee_bps INTO contract_bps FROM phase5c_qa.documents
 WHERE tenant_id=NEW.tenant_id AND case_id=NEW.case_id AND kind='CONTRACT'
   AND occurred_at<=NEW.occurred_at;
 IF contract_bps IS NULL THEN RAISE EXCEPTION 'MISSING_HISTORICAL_SIGNED_CONTRACT'; END IF;
 IF NEW.kind='CARRIER_CREDIT' THEN
   SELECT COALESCE(sum(amount_cents),0) INTO used FROM phase5c_qa.documents
   WHERE tenant_id=NEW.tenant_id AND case_id=NEW.case_id AND kind='CARRIER_CREDIT';
   IF used+NEW.amount_cents>c.max_claim_cents THEN RAISE EXCEPTION 'CLAIM_CAP_EXCEEDED'; END IF;
 ELSIF NEW.kind='CUSTOMER_POST' THEN
   SELECT * INTO predecessor FROM phase5c_qa.documents
   WHERE tenant_id=NEW.tenant_id AND case_id=NEW.case_id AND record_id=NEW.reference_id AND kind='CARRIER_CREDIT';
   IF NOT FOUND OR predecessor.amount_cents<>NEW.amount_cents OR predecessor.occurred_at>NEW.occurred_at
   THEN RAISE EXCEPTION 'UNBACKED_CUSTOMER_POST'; END IF;
   IF EXISTS (SELECT 1 FROM phase5c_qa.documents WHERE tenant_id=NEW.tenant_id AND case_id=NEW.case_id
       AND kind='CUSTOMER_POST' AND reference_id=NEW.reference_id)
   THEN RAISE EXCEPTION 'DUPLICATE_CUSTOMER_POST'; END IF;
 ELSIF NEW.kind='CUSTOMER_REVERSAL' THEN
   SELECT * INTO predecessor FROM phase5c_qa.documents
   WHERE tenant_id=NEW.tenant_id AND case_id=NEW.case_id AND record_id=NEW.reference_id AND kind='CUSTOMER_POST';
   IF NOT FOUND THEN RAISE EXCEPTION 'UNBACKED_EXCESSIVE_REVERSAL'; END IF;
   SELECT COALESCE(sum(amount_cents),0) INTO used FROM phase5c_qa.documents
   WHERE tenant_id=NEW.tenant_id AND case_id=NEW.case_id AND kind='CUSTOMER_REVERSAL'
     AND reference_id=NEW.reference_id;
   IF predecessor.occurred_at>NEW.occurred_at
    OR NEW.amount_cents+used>predecessor.amount_cents
   THEN RAISE EXCEPTION 'UNBACKED_EXCESSIVE_REVERSAL'; END IF;
 ELSE
   SELECT COALESCE(sum(amount_cents) FILTER (WHERE kind='CUSTOMER_POST'),0)
       -COALESCE(sum(amount_cents) FILTER (WHERE kind='CUSTOMER_REVERSAL'),0),
       COALESCE(sum(amount_cents) FILTER (WHERE kind='FEE_INVOICE'),0),
       COALESCE(sum(amount_cents) FILTER (WHERE kind='FEE_CREDIT'),0),
       COALESCE(sum(amount_cents) FILTER (WHERE kind='FEE_COLLECTION'),0),
       COALESCE(sum(amount_cents) FILTER (WHERE kind='FEE_REFUND'),0)
   INTO net_post,invoice_total,invoice_credits,collected,refunded
   FROM phase5c_qa.documents WHERE tenant_id=NEW.tenant_id AND case_id=NEW.case_id;
   earned:=((net_post*contract_bps+5000)/10000);
   IF NEW.kind='FEE_INVOICE' AND (NEW.amount_cents>earned OR invoice_total+NEW.amount_cents>earned)
   THEN RAISE EXCEPTION 'UNAUTHORIZED_FEE_INVOICE'; END IF;
   IF NEW.kind='FEE_COLLECTION' AND collected+NEW.amount_cents>invoice_total-invoice_credits
   THEN RAISE EXCEPTION 'COLLECTION_EXCEEDS_INVOICE'; END IF;
   IF NEW.kind='FEE_CREDIT' AND (invoice_credits+NEW.amount_cents>invoice_total
      OR invoice_total-invoice_credits-NEW.amount_cents>earned)
   THEN RAISE EXCEPTION 'INCORRECT_FEE_CREDIT'; END IF;
   IF NEW.kind='FEE_REFUND' AND (refunded+NEW.amount_cents>collected
      OR NEW.amount_cents>collected-refunded-earned
      OR invoice_total-invoice_credits<>earned)
   THEN RAISE EXCEPTION 'REFUND_NOT_DUE_OR_DUPLICATE'; END IF;
 END IF;
 RETURN NEW;
END $body$;
DROP TRIGGER IF EXISTS validate_phase5c_record ON phase5c_qa.documents;
CREATE TRIGGER validate_phase5c_record BEFORE INSERT ON phase5c_qa.documents
 FOR EACH ROW EXECUTE FUNCTION phase5c_qa.guard_signed_financial_record();
CREATE OR REPLACE FUNCTION phase5c_qa.reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $b$
BEGIN RAISE EXCEPTION 'IMMUTABLE_FINANCIAL_EVIDENCE'; END $b$;
DROP TRIGGER IF EXISTS immutable_phase5c_records ON phase5c_qa.documents;
CREATE TRIGGER immutable_phase5c_records BEFORE UPDATE OR DELETE ON phase5c_qa.documents
 FOR EACH ROW EXECUTE FUNCTION phase5c_qa.reject_mutation();
CREATE OR REPLACE VIEW phase5c_qa.financial_summary AS
SELECT c.tenant_id,c.case_id,c.customer_id,c.invoice_id,c.currency,c.max_claim_cents,
  COALESCE((SELECT sum(amount_cents) FROM phase5c_qa.documents d WHERE d.tenant_id=c.tenant_id AND d.case_id=c.case_id AND d.kind='CARRIER_CREDIT'),0)::bigint AS carrier_credits_cents,
  COALESCE((SELECT sum(amount_cents) FROM phase5c_qa.documents d WHERE d.tenant_id=c.tenant_id AND d.case_id=c.case_id AND d.kind='CUSTOMER_POST'),0)::bigint AS customer_posted_cents,
  COALESCE((SELECT sum(amount_cents) FROM phase5c_qa.documents d WHERE d.tenant_id=c.tenant_id AND d.case_id=c.case_id AND d.kind='CUSTOMER_REVERSAL'),0)::bigint AS reversed_cents,
  COALESCE((SELECT sum(amount_cents) FROM phase5c_qa.documents d WHERE d.tenant_id=c.tenant_id AND d.case_id=c.case_id AND d.kind='FEE_INVOICE'),0)::bigint AS invoiced_cents,
  COALESCE((SELECT sum(amount_cents) FROM phase5c_qa.documents d WHERE d.tenant_id=c.tenant_id AND d.case_id=c.case_id AND d.kind='FEE_CREDIT'),0)::bigint AS credited_fee_cents,
  COALESCE((SELECT sum(amount_cents) FROM phase5c_qa.documents d WHERE d.tenant_id=c.tenant_id AND d.case_id=c.case_id AND d.kind='FEE_COLLECTION'),0)::bigint AS gross_fee_collected_cents,
  COALESCE((SELECT sum(amount_cents) FROM phase5c_qa.documents d WHERE d.tenant_id=c.tenant_id AND d.case_id=c.case_id AND d.kind='FEE_REFUND'),0)::bigint AS fee_refunded_cents,
  (SELECT fee_bps FROM phase5c_qa.documents d WHERE d.tenant_id=c.tenant_id AND d.case_id=c.case_id AND d.kind='CONTRACT' ORDER BY occurred_at LIMIT 1) AS fee_bps
FROM phase5c_qa.cases c;
-- Keep public.m7_reconciled_cash_by_currency's WHERE 1=0 fail-closed safeguard UNCHANGED.
