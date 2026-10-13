-- RecoveryOS M8: STAGING-ONLY candidate, review before any production migration.
-- Applied only to isolated unpublished Floot M8 database.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
ALTER TABLE recovery_payment_instructions ADD COLUMN IF NOT EXISTS request_sha256 text;
CREATE TABLE IF NOT EXISTS recovery_eligibility_certifications (
  tenant_id text NOT NULL,
  economic_key text NOT NULL,
  currency text NOT NULL CHECK(currency IN ('USD','EUR','GBP','CAD','AUD','CHF','NZD')),
  canonical_finding_id text NOT NULL,
  finding_hash text NOT NULL CHECK(finding_hash ~ '^[0-9a-f]{64}$'),
  source_hash text NOT NULL CHECK(source_hash ~ '^[0-9a-f]{64}$'),
  authority_hash text NOT NULL CHECK(authority_hash ~ '^[0-9a-f]{64}$'),
  buyer_attestation_hash text NOT NULL CHECK(buyer_attestation_hash ~ '^[0-9a-f]{64}$'),
  eligible_cents bigint NOT NULL CHECK(eligible_cents > 0),
  certified_by bigint NOT NULL REFERENCES users(id),
  certified_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY(tenant_id,economic_key,currency),
  UNIQUE(tenant_id,canonical_finding_id),
  FOREIGN KEY(tenant_id,canonical_finding_id) REFERENCES recovery_challenge_findings(tenant_id,id)
);
CREATE TABLE IF NOT EXISTS recovery_value_allocations (
  id text PRIMARY KEY,
  tenant_id text NOT NULL,
  instruction_id text NOT NULL,
  finding_id text NOT NULL,
  economic_key text NOT NULL,
  currency text NOT NULL,
  amount_cents bigint NOT NULL CHECK (amount_cents>0),
  allocated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(tenant_id,instruction_id,finding_id),
  FOREIGN KEY(tenant_id,instruction_id) REFERENCES recovery_payment_instructions(tenant_id,id),
  FOREIGN KEY(tenant_id,finding_id) REFERENCES recovery_challenge_findings(tenant_id,id),
  FOREIGN KEY(tenant_id,economic_key,currency) REFERENCES recovery_eligibility_certifications(tenant_id,economic_key,currency)
);
CREATE INDEX IF NOT EXISTS recovery_value_allocations_economic_idx
  ON recovery_value_allocations(tenant_id,economic_key,currency);
CREATE OR REPLACE FUNCTION recovery_eligibility_certificate_guard()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE f recovery_challenge_findings%ROWTYPE; curr text; decision text;
BEGIN
 SELECT * INTO f FROM recovery_challenge_findings
 WHERE tenant_id=NEW.tenant_id AND id=NEW.canonical_finding_id;
 IF NOT FOUND OR f.economic_key<>NEW.economic_key OR f.finding_hash<>NEW.finding_hash
 OR f.attribution_state<>'CHALLENGER_ONLY' OR f.blocker_codes<>'[]'::jsonb
 OR f.net_new_candidate_cents<NEW.eligible_cents OR jsonb_array_length(f.evidence)<1
 THEN RAISE EXCEPTION 'uncertifiable finding or insufficient economic capacity'; END IF;
 SELECT r.currency INTO curr FROM recovery_freight_records r
 WHERE r.tenant_id=NEW.tenant_id AND r.record_hash=f.record_hash;
 IF curr IS NULL OR curr<>NEW.currency THEN RAISE EXCEPTION 'certificate currency does not match source'; END IF;
 SELECT d.decision INTO decision FROM recovery_review_dispositions d
 WHERE d.tenant_id=NEW.tenant_id AND d.finding_id=f.id
 ORDER BY d.created_at DESC,d.id DESC LIMIT 1;
 IF decision IS DISTINCT FROM 'CONFIRM' THEN RAISE EXCEPTION 'finding not most recently confirmed'; END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS recovery_eligibility_guard_t ON recovery_eligibility_certifications;
CREATE TRIGGER recovery_eligibility_guard_t BEFORE INSERT ON recovery_eligibility_certifications
FOR EACH ROW EXECUTE FUNCTION recovery_eligibility_certificate_guard();
CREATE OR REPLACE FUNCTION recovery_allocation_conservation_guard()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE cert recovery_eligibility_certifications%ROWTYPE; payment recovery_payment_instructions%ROWTYPE;
DECLARE already numeric; amount_in_instruction numeric;
BEGIN
 SELECT * INTO cert FROM recovery_eligibility_certifications
 WHERE tenant_id=NEW.tenant_id AND economic_key=NEW.economic_key AND currency=NEW.currency FOR UPDATE;
 IF NOT FOUND OR cert.canonical_finding_id<>NEW.finding_id THEN
   RAISE EXCEPTION 'allocation not supported by canonical certified entitlement';
 END IF;
 SELECT * INTO payment FROM recovery_payment_instructions
 WHERE tenant_id=NEW.tenant_id AND id=NEW.instruction_id;
 IF NOT FOUND OR payment.currency<>cert.currency OR payment.request_sha256 IS NULL THEN
   RAISE EXCEPTION 'payment is not a financially certified instruction';
 END IF;
 SELECT coalesce(sum(a.amount_cents),0) INTO already FROM recovery_value_allocations a
 WHERE a.tenant_id=NEW.tenant_id AND a.economic_key=NEW.economic_key AND a.currency=NEW.currency;
 IF already+NEW.amount_cents>cert.eligible_cents
   THEN RAISE EXCEPTION 'economic capacity exceeded'; END IF;
 SELECT coalesce(sum(a.amount_cents),0) INTO amount_in_instruction FROM recovery_value_allocations a
 WHERE a.tenant_id=NEW.tenant_id AND a.instruction_id=NEW.instruction_id;
 IF amount_in_instruction+NEW.amount_cents>payment.amount_cents
   THEN RAISE EXCEPTION 'instruction allocation sum exceeds amount'; END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS recovery_allocation_conservation_t ON recovery_value_allocations;
CREATE TRIGGER recovery_allocation_conservation_t BEFORE INSERT ON recovery_value_allocations
FOR EACH ROW EXECUTE FUNCTION recovery_allocation_conservation_guard();
DROP TRIGGER IF EXISTS recovery_allocation_immutability_t ON recovery_value_allocations;
CREATE TRIGGER recovery_allocation_immutability_t BEFORE UPDATE OR DELETE ON recovery_value_allocations
FOR EACH ROW EXECUTE FUNCTION recovery_block_mutation();
DROP TRIGGER IF EXISTS recovery_certificate_immutability_t ON recovery_eligibility_certifications;
CREATE TRIGGER recovery_certificate_immutability_t BEFORE UPDATE OR DELETE ON recovery_eligibility_certifications
FOR EACH ROW EXECUTE FUNCTION recovery_block_mutation();

CREATE OR REPLACE FUNCTION recovery_prepare_financial_instruction(
 p_tenant text,p_actor bigint,p_body jsonb,p_instruction_hash text
) RETURNS TABLE(instruction_id text,instruction_hash text,replayed boolean)
LANGUAGE plpgsql AS $$
DECLARE existing recovery_payment_instructions%ROWTYPE;
DECLARE pkey text; cc text; amt bigint; ids jsonb; hashval text; id_new text; remaining numeric;
DECLARE item text; cert recovery_eligibility_certifications%ROWTYPE; f recovery_challenge_findings%ROWTYPE;
DECLARE r_currency text; last_decision text; consumed numeric; cap numeric; portion numeric;
DECLARE sorted_ids text[];
BEGIN
 IF p_body IS NULL OR jsonb_typeof(p_body)<>'object' OR p_body->>'tenant_id' IS DISTINCT FROM p_tenant
   THEN RAISE EXCEPTION 'invalid tenant scope'; END IF;
 IF NOT EXISTS(SELECT 1 FROM recovery_tenant_memberships
  WHERE tenant_id=p_tenant AND user_id=p_actor AND role IN ('owner','reviewer'))
   THEN RAISE EXCEPTION 'user cannot prepare tenant payments'; END IF;
 pkey:=p_body->>'idempotency_key'; cc:=p_body->>'currency';
 IF length(coalesce(pkey,''))<8 OR cc NOT IN ('USD','EUR','GBP','CAD','AUD','CHF','NZD')
   THEN RAISE EXCEPTION 'invalid idempotency or unsupported currency minor unit'; END IF;
 IF jsonb_typeof(p_body->'amount_cents')<>'number'
   OR jsonb_typeof(p_body->'finding_ids')<>'array'
   OR jsonb_array_length(p_body->'finding_ids')<1
   THEN RAISE EXCEPTION 'invalid amount or empty findings'; END IF;
 amt:=(p_body->>'amount_cents')::bigint;
 IF amt<=0 OR length(coalesce(p_body->>'purpose',''))<3
  OR nullif(p_body->>'payer_id','') IS NULL OR nullif(p_body->>'payee_id','') IS NULL
  OR p_instruction_hash !~ '^[0-9a-f]{64}$'
   THEN RAISE EXCEPTION 'invalid payment fields'; END IF;
 SELECT array_agg(x ORDER BY x) INTO sorted_ids FROM jsonb_array_elements_text(p_body->'finding_ids') q(x);
 IF array_length(sorted_ids,1)<>array_length(ARRAY(SELECT DISTINCT unnest(sorted_ids)),1)
 THEN RAISE EXCEPTION 'duplicate finding reference'; END IF;
 IF sorted_ids IS NULL OR array_length(sorted_ids,1)>500 THEN RAISE EXCEPTION 'unsupported finding count'; END IF;
 IF p_body->'finding_ids' <> to_jsonb(sorted_ids)
 THEN RAISE EXCEPTION 'findings must be sorted for stable hashing'; END IF;
 hashval:=encode(digest(p_body::text,'sha256'),'hex');
 -- Coarse tenant lock provides a conservative first-customer contention boundary.
 PERFORM pg_advisory_xact_lock(hashtextextended('recovery-m8:'||p_tenant,0));
 SELECT * INTO existing FROM recovery_payment_instructions WHERE tenant_id=p_tenant AND idempotency_key=pkey;
 IF FOUND THEN
   IF existing.request_sha256 IS NULL OR existing.request_sha256<>hashval OR existing.instruction_hash<>p_instruction_hash
     THEN RAISE EXCEPTION 'conflicting or legacy idempotency request'; END IF;
   RETURN QUERY SELECT existing.id,existing.instruction_hash,true;
   RETURN;
 END IF;
 remaining:=amt;
 FOREACH item IN ARRAY sorted_ids LOOP
   SELECT * INTO f FROM recovery_challenge_findings WHERE tenant_id=p_tenant AND id=item FOR UPDATE;
   IF NOT FOUND OR f.attribution_state<>'CHALLENGER_ONLY' OR f.blocker_codes<>'[]'::jsonb
    OR jsonb_array_length(f.evidence)<1 THEN RAISE EXCEPTION 'finding not eligible'; END IF;
   SELECT * INTO cert FROM recovery_eligibility_certifications
   WHERE tenant_id=p_tenant AND economic_key=f.economic_key AND currency=cc FOR UPDATE;
   IF NOT FOUND OR cert.canonical_finding_id<>item OR cert.finding_hash<>f.finding_hash
    OR cert.eligible_cents>f.net_new_candidate_cents THEN RAISE EXCEPTION 'certified entitlement missing or mismatched'; END IF;
   SELECT r.currency INTO r_currency FROM recovery_freight_records r
     WHERE r.tenant_id=p_tenant AND r.record_hash=f.record_hash;
   IF r_currency IS DISTINCT FROM cc THEN RAISE EXCEPTION 'mixed currency source'; END IF;
   SELECT d.decision INTO last_decision FROM recovery_review_dispositions d
   WHERE d.tenant_id=p_tenant AND d.finding_id=f.id
   ORDER BY d.created_at DESC,d.id DESC LIMIT 1;
   IF last_decision IS DISTINCT FROM 'CONFIRM' THEN RAISE EXCEPTION 'latest review not confirmed'; END IF;
   -- Existing immutable legacy instructions are not accounted for by new ledger.
   IF EXISTS (SELECT 1 FROM recovery_payment_instructions old
     WHERE old.tenant_id=p_tenant AND old.request_sha256 IS NULL AND old.finding_ids @> to_jsonb(ARRAY[item]))
   THEN RAISE EXCEPTION 'legacy commitment requires review/backfill'; END IF;
   SELECT coalesce(sum(a.amount_cents),0) INTO consumed FROM recovery_value_allocations a
   WHERE a.tenant_id=p_tenant AND a.economic_key=cert.economic_key AND a.currency=cc;
   cap:=greatest(cert.eligible_cents-consumed,0);
   remaining:=remaining-least(remaining,cap);
 END LOOP;
 IF remaining<>0 THEN RAISE EXCEPTION 'certified eligible economic capacity exceeded'; END IF;
 id_new:='pay_'||substr(encode(gen_random_bytes(14),'hex'),1,25);
 INSERT INTO recovery_payment_instructions
   (id,tenant_id,payer_id,payee_id,currency,amount_cents,purpose,finding_ids,idempotency_key,instruction_hash,created_by,request_sha256)
 VALUES (id_new,p_tenant,p_body->>'payer_id',p_body->>'payee_id',cc,amt,p_body->>'purpose',
         p_body->'finding_ids',pkey,p_instruction_hash,p_actor,hashval);
 remaining:=amt;
 FOREACH item IN ARRAY sorted_ids LOOP
   IF remaining=0 THEN EXIT; END IF;
   SELECT * INTO cert FROM recovery_eligibility_certifications
     WHERE tenant_id=p_tenant AND canonical_finding_id=item;
   SELECT coalesce(sum(a.amount_cents),0) INTO consumed FROM recovery_value_allocations a
     WHERE a.tenant_id=p_tenant AND a.economic_key=cert.economic_key AND a.currency=cc;
   portion:=least(remaining,cert.eligible_cents-consumed);
   IF portion>0 THEN
     INSERT INTO recovery_value_allocations
       (id,tenant_id,instruction_id,finding_id,economic_key,currency,amount_cents)
     VALUES ('ra_'||substr(encode(gen_random_bytes(14),'hex'),1,25),
      p_tenant,id_new,item,cert.economic_key,cc,portion::bigint);
     remaining:=remaining-portion;
   END IF;
 END LOOP;
 IF remaining<>0 THEN RAISE EXCEPTION 'allocation failed to conserve total'; END IF;
 RETURN QUERY SELECT id_new,p_instruction_hash,false;
END $$;
-- Payment SETTLED is provider assertion, not proof of money movement.
CREATE OR REPLACE VIEW recovery_m8_verified_cash_by_currency AS
 SELECT i.tenant_id,i.currency,0::numeric AS verified_minor_units
 FROM recovery_payment_instructions i WHERE FALSE;
