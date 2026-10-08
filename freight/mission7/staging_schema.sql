-- RETALLY RecoveryOS M7. ISOLATED STAGING SCHEMA ONLY. Not a production migration.
-- Reconstructed from a real, successfully provisioned Floot QA PostgreSQL database.
-- All 'm7_' objects are standalone and use synthetic data exclusively.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS m7_tenants (
  "id" text NOT NULL,
  PRIMARY KEY (id),
  NOT NULL id
);

CREATE TABLE IF NOT EXISTS m7_findings (
  "tenant_id" text NOT NULL,
  "id" text NOT NULL,
  "economic_key" text NOT NULL,
  "currency" text NOT NULL,
  "candidate_cents" bigint NOT NULL,
  "net_new_candidate_cents" bigint NOT NULL,
  "attribution_state" text NOT NULL,
  "confirmed" boolean DEFAULT false NOT NULL,
  "authority_verified" boolean DEFAULT false NOT NULL,
  "source_verified" boolean DEFAULT false NOT NULL,
  "buyer_eligibility_verified" boolean DEFAULT false NOT NULL,
  "blockers" jsonb DEFAULT '[]'::jsonb NOT NULL,
  UNIQUE (tenant_id, economic_key, currency),
  PRIMARY KEY (tenant_id, id),
  NOT NULL attribution_state,
  NOT NULL authority_verified,
  NOT NULL blockers,
  NOT NULL buyer_eligibility_verified,
  NOT NULL candidate_cents,
  NOT NULL confirmed,
  NOT NULL currency,
  NOT NULL economic_key,
  NOT NULL id,
  NOT NULL net_new_candidate_cents,
  NOT NULL source_verified,
  NOT NULL tenant_id,
  FOREIGN KEY (tenant_id) REFERENCES m7_tenants(id),
  CHECK ((attribution_state = ANY (ARRAY['CHALLENGER_ONLY'::text, 'INCUMBENT_KNOWN'::text, 'REVIEW'::text, 'SUPPRESSED'::text]))),
  CHECK ((jsonb_typeof(blockers) = 'array'::text)),
  CHECK ((candidate_cents >= 0)),
  CHECK (((net_new_candidate_cents >= 0) AND (net_new_candidate_cents <= candidate_cents))),
  CHECK ((currency ~ '^[A-Z]{3}$'::text))
);

CREATE TABLE IF NOT EXISTS m7_instructions (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "tenant_id" text NOT NULL,
  "idempotency_key" text NOT NULL,
  "request_hash" text NOT NULL,
  "request_payload" jsonb NOT NULL,
  "payer_id" text NOT NULL,
  "payee_id" text NOT NULL,
  "currency" text NOT NULL,
  "amount_cents" bigint NOT NULL,
  "purpose" text NOT NULL,
  "created_at" timestamptz DEFAULT clock_timestamp() NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, idempotency_key),
  PRIMARY KEY (id),
  NOT NULL amount_cents,
  NOT NULL created_at,
  NOT NULL currency,
  NOT NULL id,
  NOT NULL idempotency_key,
  NOT NULL payee_id,
  NOT NULL payer_id,
  NOT NULL purpose,
  NOT NULL request_hash,
  NOT NULL request_payload,
  NOT NULL tenant_id,
  FOREIGN KEY (tenant_id) REFERENCES m7_tenants(id),
  CHECK ((amount_cents > 0)),
  CHECK ((currency ~ '^[A-Z]{3}$'::text)),
  CHECK ((length(idempotency_key) >= 8)),
  CHECK ((request_hash ~ '^[0-9a-f]{64}$'::text))
);

CREATE TABLE IF NOT EXISTS m7_allocations (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "tenant_id" text NOT NULL,
  "instruction_id" uuid NOT NULL,
  "finding_id" text NOT NULL,
  "economic_key" text NOT NULL,
  "currency" text NOT NULL,
  "amount_cents" bigint NOT NULL,
  "created_at" timestamptz DEFAULT clock_timestamp() NOT NULL,
  UNIQUE (tenant_id, instruction_id, finding_id),
  PRIMARY KEY (id),
  NOT NULL amount_cents,
  NOT NULL created_at,
  NOT NULL currency,
  NOT NULL economic_key,
  NOT NULL finding_id,
  NOT NULL id,
  NOT NULL instruction_id,
  NOT NULL tenant_id,
  FOREIGN KEY (tenant_id, finding_id) REFERENCES m7_findings(tenant_id, id),
  FOREIGN KEY (tenant_id, instruction_id) REFERENCES m7_instructions(tenant_id, id),
  CHECK ((amount_cents > 0)),
  CHECK ((currency ~ '^[A-Z]{3}$'::text))
);

CREATE TABLE IF NOT EXISTS m7_settlement_attestations (
  "id" uuid DEFAULT gen_random_uuid() NOT NULL,
  "tenant_id" text NOT NULL,
  "instruction_id" uuid NOT NULL,
  "status" text NOT NULL,
  "currency" text NOT NULL,
  "amount_cents" bigint NOT NULL,
  "source_sha256" text NOT NULL,
  "verified_by" text,
  "occurred_at" timestamptz NOT NULL,
  "created_at" timestamptz DEFAULT clock_timestamp() NOT NULL,
  PRIMARY KEY (id),
  NOT NULL amount_cents,
  NOT NULL created_at,
  NOT NULL currency,
  NOT NULL id,
  NOT NULL instruction_id,
  NOT NULL occurred_at,
  NOT NULL source_sha256,
  NOT NULL status,
  NOT NULL tenant_id,
  FOREIGN KEY (tenant_id, instruction_id) REFERENCES m7_instructions(tenant_id, id),
  CHECK ((amount_cents > 0)),
  CHECK ((((status = ANY (ARRAY['BUYER_VERIFIED'::text, 'CASH_RECONCILED'::text])) AND (verified_by IS NOT NULL) AND (length(verified_by) > 2)) OR (status <> ALL (ARRAY['BUYER_VERIFIED'::text, 'CASH_RECONCILED'::text])))),
  CHECK ((currency ~ '^[A-Z]{3}$'::text)),
  CHECK ((source_sha256 ~ '^[0-9a-f]{64}$'::text)),
  CHECK ((status = ANY (ARRAY['PROVIDER_REPORTED'::text, 'BUYER_VERIFIED'::text, 'CASH_RECONCILED'::text, 'REVERSED'::text])))
);

CREATE INDEX m7_allocations_economic_key_idx ON public.m7_allocations USING btree (tenant_id, economic_key, currency);

CREATE OR REPLACE FUNCTION public.m7_block_mutation()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN RAISE EXCEPTION 'mission7 financial rows are immutable'; END $function$;

CREATE OR REPLACE FUNCTION public.m7_prepare_instruction(p_tenant text, p_idempotency_key text, p_request jsonb)
 RETURNS TABLE(instruction_id uuid, request_hash text, replayed boolean)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_existing m7_instructions%ROWTYPE;
  v_hash text;
  v_currency text;
  v_amount bigint;
  v_alloc_total numeric:=0;
  v_instruction uuid;
  v_item jsonb;
  v_finding m7_findings%ROWTYPE;
  v_item_cents bigint;
  v_allocated numeric;
  v_seen text[]:=ARRAY[]::text[];
BEGIN
  IF p_tenant IS NULL OR NOT EXISTS(SELECT 1 FROM m7_tenants WHERE id=p_tenant)
    THEN RAISE EXCEPTION 'tenant not found'; END IF;
  IF p_idempotency_key IS NULL OR length(p_idempotency_key)<8
    THEN RAISE EXCEPTION 'invalid idempotency key'; END IF;
  IF p_request IS NULL OR jsonb_typeof(p_request)<>'object'
    THEN RAISE EXCEPTION 'request object required'; END IF;
  IF jsonb_typeof(p_request->'amountCents')<>'number'
    OR jsonb_typeof(p_request->'allocations')<>'array'
    THEN RAISE EXCEPTION 'invalid financial request'; END IF;
  IF jsonb_array_length(p_request->'allocations') NOT BETWEEN 1 AND 500
    THEN RAISE EXCEPTION 'invalid allocation count'; END IF;
  v_amount := (p_request->>'amountCents')::bigint;
  v_currency := p_request->>'currency';
  IF v_amount<=0 OR v_currency IS NULL OR v_currency !~ '^[A-Z]{3}$'
     OR nullif(p_request->>'payerId','') IS NULL OR nullif(p_request->>'payeeId','') IS NULL
     OR length(coalesce(p_request->>'purpose',''))<3
    THEN RAISE EXCEPTION 'invalid payment parameters'; END IF;
  v_hash := encode(digest(p_request::text,'sha256'),'hex');
  -- Lock by tenant + key before checking for an existing exact replay.
  PERFORM pg_advisory_xact_lock(hashtextextended('m7:idem:'||p_tenant||':'||p_idempotency_key,0));
  SELECT * INTO v_existing FROM m7_instructions
    WHERE tenant_id=p_tenant AND idempotency_key=p_idempotency_key;
  IF FOUND THEN
    IF v_existing.request_hash<>v_hash OR v_existing.request_payload<>p_request
      THEN RAISE EXCEPTION 'conflicting idempotency replay'; END IF;
    RETURN QUERY SELECT v_existing.id,v_hash,true;
    RETURN;
  END IF;
  -- Sorted row locking enforces conservation even under competing concurrent requests.
  FOR v_item IN SELECT value FROM jsonb_array_elements(p_request->'allocations') AS t(value)
                ORDER BY value->>'findingId'
  LOOP
    IF jsonb_typeof(v_item)<>'object'
      OR jsonb_typeof(v_item->'amountCents')<>'number'
      OR nullif(v_item->>'findingId','') IS NULL
       THEN RAISE EXCEPTION 'invalid allocation item'; END IF;
    IF (v_item->>'findingId')=ANY(v_seen)
      THEN RAISE EXCEPTION 'duplicate finding in one payment'; END IF;
    v_seen:=array_append(v_seen,v_item->>'findingId');
    v_item_cents:=(v_item->>'amountCents')::bigint;
    IF v_item_cents<=0 THEN RAISE EXCEPTION 'allocation amount must be positive'; END IF;
    SELECT * INTO v_finding FROM m7_findings
      WHERE tenant_id=p_tenant AND id=v_item->>'findingId' FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'finding outside tenant or missing'; END IF;
    IF v_finding.currency<>v_currency THEN RAISE EXCEPTION 'mixed currency allocation'; END IF;
    IF NOT(v_finding.confirmed AND v_finding.authority_verified AND v_finding.source_verified
      AND v_finding.buyer_eligibility_verified
      AND v_finding.attribution_state='CHALLENGER_ONLY'
      AND v_finding.blockers='[]'::jsonb)
      THEN RAISE EXCEPTION 'finding not independently eligible'; END IF;
    SELECT coalesce(sum(a.amount_cents),0) INTO v_allocated
      FROM m7_allocations a
      WHERE a.tenant_id=p_tenant AND a.economic_key=v_finding.economic_key AND a.currency=v_currency;
    IF v_allocated+v_item_cents>v_finding.net_new_candidate_cents
      THEN RAISE EXCEPTION 'economic recovery allocation capacity exceeded'; END IF;
    v_alloc_total:=v_alloc_total+v_item_cents;
    IF v_alloc_total>9223372036854775807
      THEN RAISE EXCEPTION 'allocation sum overflow'; END IF;
  END LOOP;
  IF v_alloc_total<>v_amount THEN RAISE EXCEPTION 'allocated cents do not match payment'; END IF;
  INSERT INTO m7_instructions
    (tenant_id,idempotency_key,request_hash,request_payload,payer_id,payee_id,currency,amount_cents,purpose)
  VALUES(p_tenant,p_idempotency_key,v_hash,p_request,p_request->>'payerId',
         p_request->>'payeeId',v_currency,v_amount,p_request->>'purpose')
  RETURNING id INTO v_instruction;
  INSERT INTO m7_allocations(tenant_id,instruction_id,finding_id,economic_key,currency,amount_cents)
    SELECT p_tenant,v_instruction,f.id,f.economic_key,f.currency,(item.value->>'amountCents')::bigint
    FROM jsonb_array_elements(p_request->'allocations') item
    JOIN m7_findings f ON f.tenant_id=p_tenant AND f.id=item.value->>'findingId';
  RETURN QUERY SELECT v_instruction,v_hash,false;
END $function$;

CREATE TRIGGER m7_allocations_immutable BEFORE DELETE OR UPDATE ON m7_allocations FOR EACH ROW EXECUTE FUNCTION m7_block_mutation();
CREATE TRIGGER m7_instructions_immutable BEFORE DELETE OR UPDATE ON m7_instructions FOR EACH ROW EXECUTE FUNCTION m7_block_mutation();
CREATE TRIGGER m7_settlement_immutable BEFORE DELETE OR UPDATE ON m7_settlement_attestations FOR EACH ROW EXECUTE FUNCTION m7_block_mutation();

CREATE OR REPLACE VIEW m7_reconciled_cash_by_currency AS
SELECT tenant_id,
    currency,
    sum(amount_cents) AS claimed_reconciled_minor_units
   FROM m7_settlement_attestations
  WHERE status = 'CASH_RECONCILED'::text
  GROUP BY tenant_id, currency;
