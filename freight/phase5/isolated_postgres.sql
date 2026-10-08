-- RETALLY Phase 5 isolated QA PostgreSQL. NEVER apply to published RecoveryOS.
-- Target: independently verified QA system_identifier 7694294930552894346.
-- Isolated schema, fictional identifiers, no real provider or customer activity.
DO $guard$
BEGIN
 IF (SELECT system_identifier::text FROM pg_control_system()) <> '7694294930552894346'
 OR to_regclass('public.recovery_payment_events') IS NOT NULL
 THEN RAISE EXCEPTION 'PHASE5_REQUIRES_DEDICATED_QA_CLUSTER';
 END IF;
END $guard$;

CREATE SCHEMA IF NOT EXISTS phase5_qa;
CREATE TABLE IF NOT EXISTS phase5_qa.instructions (
 tenant_id text NOT NULL CHECK (tenant_id LIKE 'SIM-%'),
 instruction_id text NOT NULL CHECK (instruction_id LIKE 'SIM-%'),
 currency text NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
 amount_cents bigint NOT NULL CHECK (amount_cents > 0),
 authorized boolean NOT NULL DEFAULT false,
 PRIMARY KEY (tenant_id,instruction_id)
);
CREATE TABLE IF NOT EXISTS phase5_qa.events (
 event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 tenant_id text NOT NULL,
 instruction_id text NOT NULL,
 event_seq int NOT NULL CHECK (event_seq > 0),
 provider text NOT NULL CHECK (provider LIKE 'SIM-%'),
 provider_reference text NOT NULL,
 actor_id text NOT NULL CHECK (actor_id LIKE 'SIM-%'),
 state text NOT NULL CHECK(state IN ('SUBMITTED','ACCEPTED','SETTLED','FAILED','REVERSED','OUTCOME_UNKNOWN')),
 amount_cents bigint NOT NULL CHECK(amount_cents > 0),
 source_sha256 text NOT NULL CHECK(source_sha256 ~ '^[0-9a-f]{64}$'),
 occurred_at timestamptz NOT NULL,
 prior_hash text,
 event_hash text NOT NULL CHECK (event_hash ~ '^[0-9a-f]{64}$'),
 created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
 FOREIGN KEY (tenant_id,instruction_id) REFERENCES phase5_qa.instructions(tenant_id,instruction_id),
 UNIQUE (tenant_id,instruction_id,event_seq),
 UNIQUE (tenant_id,instruction_id,provider,provider_reference),
 UNIQUE (tenant_id,instruction_id,event_hash)
);
CREATE OR REPLACE FUNCTION phase5_qa.record_provider_event(
 p_tenant text,p_instruction text,p_state text,p_provider text,
 p_reference text,p_actor text,p_amount bigint,p_source_hash text,p_occurred_at timestamptz
)
RETURNS TABLE(accepted_event_id bigint,accepted_event_hash text,is_replay boolean,result_state text)
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,phase5_qa AS $body$
DECLARE inst record; old record; last_event record; prior_state text; next_seq int;
        h text; prior_hash text; payload text;
BEGIN
 IF p_tenant NOT LIKE 'SIM-%' OR p_instruction NOT LIKE 'SIM-%'
 OR p_provider NOT LIKE 'SIM-%' OR p_actor NOT LIKE 'SIM-%'
 OR p_reference IS NULL OR length(p_reference)=0 OR p_amount IS NULL OR p_amount<=0
 OR p_source_hash IS NULL OR p_source_hash !~ '^[0-9a-f]{64}$'
 OR p_occurred_at IS NULL OR p_state NOT IN ('SUBMITTED','ACCEPTED','SETTLED','FAILED','REVERSED','OUTCOME_UNKNOWN')
 THEN RAISE EXCEPTION 'INVALID_SYNTHETIC_PROVIDER_EVENT'; END IF;
 -- Entire transition, replay lookup and INSERT are serialized per scoped instruction.
 PERFORM pg_advisory_xact_lock(hashtextextended(p_tenant||':'||p_instruction,3491));
 SELECT * INTO inst FROM phase5_qa.instructions
 WHERE tenant_id=p_tenant AND instruction_id=p_instruction FOR UPDATE;
 IF NOT FOUND OR inst.authorized IS DISTINCT FROM true THEN
   RAISE EXCEPTION 'INSTRUCTION_NOT_AUTHORIZED'; END IF;
 IF inst.amount_cents<>p_amount THEN
   RAISE EXCEPTION 'EVENT_AMOUNT_MISMATCH'; END IF;
 SELECT * INTO old FROM phase5_qa.events
 WHERE tenant_id=p_tenant AND instruction_id=p_instruction AND provider=p_provider AND provider_reference=p_reference;
 IF FOUND THEN
    IF (old.state,old.actor_id,old.amount_cents,old.source_sha256,old.occurred_at)
       IS DISTINCT FROM (p_state,p_actor,p_amount,p_source_hash,p_occurred_at)
    THEN RAISE EXCEPTION 'CONFLICTING_PROVIDER_REFERENCE_REPLAY'; END IF;
    accepted_event_id:=old.event_id; accepted_event_hash:=old.event_hash; is_replay:=true;result_state:=old.state;
    RETURN NEXT;RETURN;
 END IF;
 SELECT * INTO last_event FROM phase5_qa.events
 WHERE tenant_id=p_tenant AND instruction_id=p_instruction ORDER BY event_seq DESC LIMIT 1;
 IF FOUND THEN
   prior_state:=last_event.state;
   next_seq:=last_event.event_seq+1;
   prior_hash:=last_event.event_hash;
   IF p_occurred_at < last_event.occurred_at THEN RAISE EXCEPTION 'EVENT_TIME_REGRESSION'; END IF;
 ELSE
   prior_state:='AUTHORIZED';next_seq:=1;prior_hash:=NULL;
 END IF;
 IF NOT ((prior_state='AUTHORIZED' AND p_state='SUBMITTED')
    OR (prior_state='SUBMITTED' AND p_state IN ('ACCEPTED','FAILED','OUTCOME_UNKNOWN'))
    OR (prior_state='ACCEPTED' AND p_state IN ('SETTLED','FAILED','OUTCOME_UNKNOWN'))
    OR (prior_state='SETTLED' AND p_state='REVERSED'))
 THEN RAISE EXCEPTION 'INVALID_PAYMENT_STATE_TRANSITION'; END IF;
 payload:=jsonb_build_object('tenant',p_tenant,'instruction',p_instruction,
      'seq',next_seq,'provider',p_provider,'reference',p_reference,'actor',p_actor,
      'state',p_state,'amount_cents',p_amount,'source_sha256',p_source_hash,
      'occurred_at',to_char(p_occurred_at AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
      'prior_hash',prior_hash)::text;
 h:=encode(digest(payload,'sha256'),'hex');
 INSERT INTO phase5_qa.events
 (tenant_id,instruction_id,event_seq,provider,provider_reference,actor_id,
  state,amount_cents,source_sha256,occurred_at,prior_hash,event_hash)
 VALUES (p_tenant,p_instruction,next_seq,p_provider,p_reference,p_actor,
         p_state,p_amount,p_source_hash,p_occurred_at,prior_hash,h)
 RETURNING event_id,event_hash INTO accepted_event_id,accepted_event_hash;
 is_replay:=false;result_state:=p_state;
 RETURN NEXT;
END $body$;

-- Prevent direct mutability of synthetic provider evidence.
CREATE OR REPLACE FUNCTION phase5_qa.reject_event_mutation() RETURNS trigger
LANGUAGE plpgsql AS $f$ BEGIN RAISE EXCEPTION 'IMMUTABLE_QA_EVENT'; END $f$;
DROP TRIGGER IF EXISTS immutable_p5_events ON phase5_qa.events;
CREATE TRIGGER immutable_p5_events BEFORE UPDATE OR DELETE ON phase5_qa.events
 FOR EACH ROW EXECUTE FUNCTION phase5_qa.reject_event_mutation();
