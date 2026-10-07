-- RecoveryOS Phase 3 Step 1 security hardening reference.
-- This file records the application-data-plane controls applied to the deployed
-- Floot/Neon PostgreSQL environment. It is not a provider certification.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_unique ON users (lower(email));

ALTER TABLE recovery_api_keys DROP CONSTRAINT IF EXISTS recovery_api_keys_scope_check;
ALTER TABLE recovery_api_keys
  ADD CONSTRAINT recovery_api_keys_scope_check
  CHECK (scope IN ('ingest','payment_event'));

ALTER TABLE recovery_audit_events
  ADD COLUMN IF NOT EXISTS previous_event_hash text,
  ADD COLUMN IF NOT EXISTS actor_type text NOT NULL DEFAULT 'SYSTEM'
    CHECK (actor_type IN ('SYSTEM','HUMAN','API_KEY')),
  ADD COLUMN IF NOT EXISTS source_table text NOT NULL DEFAULT 'legacy';

CREATE OR REPLACE FUNCTION recovery_append_audit_event() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  rowj jsonb;
  tenant text;
  object_id_value text;
  object_hash_value text;
  actor_value bigint;
  actor_type_value text;
  previous_hash text;
  event_id_value text;
  occurred timestamptz;
  hash_material text;
  digest_value text;
BEGIN
  rowj := to_jsonb(NEW);
  tenant := rowj->>'tenant_id';
  IF tenant IS NULL OR tenant = '' THEN
    RETURN NEW;
  END IF;

  PERFORM pg_advisory_xact_lock(hashtextextended(tenant, 0));

  object_id_value := COALESCE(rowj->>'id', TG_TABLE_NAME);
  object_hash_value := COALESCE(
    rowj->>'record_hash',
    rowj->>'finding_hash',
    rowj->>'disposition_hash',
    rowj->>'instruction_hash',
    rowj->>'authorization_hash',
    rowj->>'event_hash',
    rowj->>'receipt_hash',
    rowj->>'snapshot_hash',
    rowj->>'population_hash',
    rowj->>'key_hash'
  );
  IF object_hash_value IS NULL OR object_hash_value !~ '^[0-9a-f]{64}$' THEN
    object_hash_value := encode(digest(rowj::text, 'sha256'), 'hex');
  END IF;

  actor_value := NULL;
  IF rowj ? 'reviewer_user_id' THEN actor_value := NULLIF(rowj->>'reviewer_user_id','')::bigint;
  ELSIF rowj ? 'authorized_by' THEN actor_value := NULLIF(rowj->>'authorized_by','')::bigint;
  ELSIF rowj ? 'created_by' THEN actor_value := NULLIF(rowj->>'created_by','')::bigint;
  END IF;
  actor_type_value := CASE WHEN actor_value IS NULL THEN 'SYSTEM' ELSE 'HUMAN' END;

  SELECT event_hash INTO previous_hash
  FROM recovery_audit_events
  WHERE tenant_id = tenant
  ORDER BY occurred_at DESC, id DESC
  LIMIT 1;

  event_id_value := gen_random_uuid()::text;
  occurred := clock_timestamp();
  hash_material := concat_ws('|',
    tenant,TG_TABLE_NAME,object_id_value,object_hash_value,
    COALESCE(previous_hash,''),actor_type_value,COALESCE(actor_value::text,''),
    occurred::text,event_id_value
  );
  digest_value := encode(digest(hash_material, 'sha256'), 'hex');

  INSERT INTO recovery_audit_events(
    id,tenant_id,event_type,object_id,object_hash,actor_user_id,event_hash,
    occurred_at,previous_event_hash,actor_type,source_table
  ) VALUES (
    event_id_value,tenant,'INSERT_'||upper(TG_TABLE_NAME),object_id_value,
    object_hash_value,actor_value,digest_value,occurred,previous_hash,
    actor_type_value,TG_TABLE_NAME
  );
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS recovery_audit_population_insert ON recovery_populations;
CREATE TRIGGER recovery_audit_population_insert AFTER INSERT ON recovery_populations
FOR EACH ROW EXECUTE FUNCTION recovery_append_audit_event();
DROP TRIGGER IF EXISTS recovery_audit_ingress_insert ON recovery_ingress_receipts;
CREATE TRIGGER recovery_audit_ingress_insert AFTER INSERT ON recovery_ingress_receipts
FOR EACH ROW EXECUTE FUNCTION recovery_append_audit_event();
DROP TRIGGER IF EXISTS recovery_audit_record_insert ON recovery_freight_records;
CREATE TRIGGER recovery_audit_record_insert AFTER INSERT ON recovery_freight_records
FOR EACH ROW EXECUTE FUNCTION recovery_append_audit_event();
DROP TRIGGER IF EXISTS recovery_audit_snapshot_insert ON recovery_incumbent_snapshots;
CREATE TRIGGER recovery_audit_snapshot_insert AFTER INSERT ON recovery_incumbent_snapshots
FOR EACH ROW EXECUTE FUNCTION recovery_append_audit_event();
DROP TRIGGER IF EXISTS recovery_audit_finding_insert ON recovery_challenge_findings;
CREATE TRIGGER recovery_audit_finding_insert AFTER INSERT ON recovery_challenge_findings
FOR EACH ROW EXECUTE FUNCTION recovery_append_audit_event();
DROP TRIGGER IF EXISTS recovery_audit_review_insert ON recovery_review_dispositions;
CREATE TRIGGER recovery_audit_review_insert AFTER INSERT ON recovery_review_dispositions
FOR EACH ROW EXECUTE FUNCTION recovery_append_audit_event();
DROP TRIGGER IF EXISTS recovery_audit_api_key_insert ON recovery_api_keys;
CREATE TRIGGER recovery_audit_api_key_insert AFTER INSERT ON recovery_api_keys
FOR EACH ROW EXECUTE FUNCTION recovery_append_audit_event();
DROP TRIGGER IF EXISTS recovery_audit_payment_instruction_insert ON recovery_payment_instructions;
CREATE TRIGGER recovery_audit_payment_instruction_insert AFTER INSERT ON recovery_payment_instructions
FOR EACH ROW EXECUTE FUNCTION recovery_append_audit_event();
DROP TRIGGER IF EXISTS recovery_audit_payment_authorization_insert ON recovery_payment_authorizations;
CREATE TRIGGER recovery_audit_payment_authorization_insert AFTER INSERT ON recovery_payment_authorizations
FOR EACH ROW EXECUTE FUNCTION recovery_append_audit_event();
DROP TRIGGER IF EXISTS recovery_audit_payment_event_insert ON recovery_payment_events;
CREATE TRIGGER recovery_audit_payment_event_insert AFTER INSERT ON recovery_payment_events
FOR EACH ROW EXECUTE FUNCTION recovery_append_audit_event();

CREATE OR REPLACE FUNCTION recovery_verify_audit_chain(p_tenant text)
RETURNS TABLE(total_events bigint, invalid_hashes bigint, broken_links bigint)
LANGUAGE sql STABLE AS $$
  WITH ordered AS (
    SELECT id,tenant_id,source_table,object_id,object_hash,actor_type,
           actor_user_id,occurred_at,previous_event_hash,event_hash,
           lag(event_hash) OVER (ORDER BY occurred_at ASC,id ASC) AS expected_previous
    FROM recovery_audit_events
    WHERE tenant_id=p_tenant
  ),
  checked AS (
    SELECT *,
      encode(digest(concat_ws('|',
        tenant_id,source_table,object_id,object_hash,
        COALESCE(previous_event_hash,''),actor_type,
        COALESCE(actor_user_id::text,''),occurred_at::text,id
      ),'sha256'),'hex') AS recomputed
    FROM ordered
  )
  SELECT count(*)::bigint,
         count(*) FILTER (WHERE recomputed<>event_hash)::bigint,
         count(*) FILTER (
           WHERE COALESCE(previous_event_hash,'')<>COALESCE(expected_previous,'')
         )::bigint
  FROM checked;
$$;

CREATE OR REPLACE FUNCTION recovery_api_key_update_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.id<>OLD.id OR NEW.tenant_id<>OLD.tenant_id OR NEW.label<>OLD.label
     OR NEW.key_hash<>OLD.key_hash OR NEW.scope<>OLD.scope
     OR NEW.created_by<>OLD.created_by OR NEW.created_at<>OLD.created_at THEN
    RAISE EXCEPTION 'API key immutable fields cannot change';
  END IF;
  IF OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at THEN
    RAISE EXCEPTION 'revoked API key cannot be changed';
  END IF;
  IF OLD.revoked_at IS NULL AND NEW.revoked_at IS NULL THEN
    RAISE EXCEPTION 'API key update must revoke the key';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS recovery_api_key_update_guard_t ON recovery_api_keys;
CREATE TRIGGER recovery_api_key_update_guard_t
BEFORE UPDATE ON recovery_api_keys
FOR EACH ROW EXECUTE FUNCTION recovery_api_key_update_guard();

CREATE OR REPLACE FUNCTION recovery_audit_api_key_revoke() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE previous_hash text;
DECLARE event_id_value text;
DECLARE occurred timestamptz;
DECLARE digest_value text;
BEGIN
  IF OLD.revoked_at IS NULL AND NEW.revoked_at IS NOT NULL THEN
    PERFORM pg_advisory_xact_lock(hashtextextended(NEW.tenant_id,0));
    SELECT event_hash INTO previous_hash
    FROM recovery_audit_events
    WHERE tenant_id=NEW.tenant_id
    ORDER BY occurred_at DESC,id DESC LIMIT 1;
    event_id_value:=gen_random_uuid()::text;
    occurred:=clock_timestamp();
    digest_value:=encode(digest(concat_ws('|',
      NEW.tenant_id,'recovery_api_keys:REVOKE',NEW.id,NEW.key_hash,
      COALESCE(previous_hash,''),'SYSTEM','',occurred::text,event_id_value
    ),'sha256'),'hex');
    INSERT INTO recovery_audit_events(
      id,tenant_id,event_type,object_id,object_hash,actor_user_id,event_hash,
      occurred_at,previous_event_hash,actor_type,source_table
    ) VALUES (
      event_id_value,NEW.tenant_id,'REVOKE_RECOVERY_API_KEY',NEW.id,NEW.key_hash,
      NULL,digest_value,occurred,previous_hash,'SYSTEM','recovery_api_keys'
    );
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS recovery_audit_api_key_revoke_t ON recovery_api_keys;
CREATE TRIGGER recovery_audit_api_key_revoke_t
AFTER UPDATE ON recovery_api_keys
FOR EACH ROW EXECUTE FUNCTION recovery_audit_api_key_revoke();
