-- RecoveryOS Phase 2 provider-neutral payment orchestration schema.
-- Banking rails/custody remain external. These tables preserve intent,
-- human authorization, provider-observed lifecycle evidence, and reversals.

CREATE TABLE recovery_payment_instructions (
  id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES recovery_tenants(id) ON DELETE RESTRICT,
  payer_id text NOT NULL,
  payee_id text NOT NULL,
  currency text NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
  amount_cents bigint NOT NULL CHECK (amount_cents > 0),
  purpose text NOT NULL,
  finding_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  idempotency_key text NOT NULL,
  instruction_hash text NOT NULL CHECK (instruction_hash ~ '^[0-9a-f]{64}$'),
  created_by bigint NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id,idempotency_key),
  UNIQUE (tenant_id,instruction_hash),
  UNIQUE (tenant_id,id)
);

CREATE TABLE recovery_payment_authorizations (
  id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES recovery_tenants(id) ON DELETE RESTRICT,
  instruction_id text NOT NULL,
  authorized_cents bigint NOT NULL CHECK (authorized_cents > 0),
  authorized_by bigint NOT NULL,
  reason text NOT NULL,
  authorization_hash text NOT NULL CHECK (authorization_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id,instruction_id),
  UNIQUE (tenant_id,authorization_hash),
  FOREIGN KEY (tenant_id,instruction_id)
    REFERENCES recovery_payment_instructions(tenant_id,id) ON DELETE RESTRICT
);

CREATE TABLE recovery_payment_events (
  id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES recovery_tenants(id) ON DELETE RESTRICT,
  instruction_id text NOT NULL,
  state text NOT NULL CHECK (state IN ('SUBMITTED','ACCEPTED','SETTLED','FAILED','REVERSED')),
  provider text NOT NULL,
  provider_reference text,
  amount_cents bigint NOT NULL CHECK (amount_cents > 0),
  source_hash text NOT NULL CHECK (source_hash ~ '^[0-9a-f]{64}$'),
  occurred_at timestamptz NOT NULL,
  event_hash text NOT NULL CHECK (event_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id,event_hash),
  UNIQUE (tenant_id,provider,provider_reference,state),
  FOREIGN KEY (tenant_id,instruction_id)
    REFERENCES recovery_payment_instructions(tenant_id,id) ON DELETE RESTRICT
);

CREATE INDEX recovery_payment_instruction_tenant_idx
  ON recovery_payment_instructions(tenant_id,created_at DESC);
CREATE INDEX recovery_payment_event_instruction_idx
  ON recovery_payment_events(tenant_id,instruction_id,occurred_at ASC,created_at ASC);

CREATE TRIGGER recovery_payment_instruction_immutable
  BEFORE UPDATE OR DELETE ON recovery_payment_instructions
  FOR EACH ROW EXECUTE FUNCTION recovery_block_mutation();
CREATE TRIGGER recovery_payment_authorization_immutable
  BEFORE UPDATE OR DELETE ON recovery_payment_authorizations
  FOR EACH ROW EXECUTE FUNCTION recovery_block_mutation();
CREATE TRIGGER recovery_payment_event_immutable
  BEFORE UPDATE OR DELETE ON recovery_payment_events
  FOR EACH ROW EXECUTE FUNCTION recovery_block_mutation();

CREATE OR REPLACE FUNCTION recovery_payment_authorization_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected_amount bigint;
BEGIN
  SELECT amount_cents INTO expected_amount
  FROM recovery_payment_instructions
  WHERE tenant_id=NEW.tenant_id AND id=NEW.instruction_id;
  IF expected_amount IS NULL THEN RAISE EXCEPTION 'payment instruction missing'; END IF;
  IF NEW.authorized_cents <> expected_amount THEN RAISE EXCEPTION 'authorization amount mismatch'; END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER recovery_payment_authorization_guard_t
  BEFORE INSERT ON recovery_payment_authorizations
  FOR EACH ROW EXECUTE FUNCTION recovery_payment_authorization_guard();

CREATE OR REPLACE FUNCTION recovery_payment_event_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected_amount bigint;
DECLARE prior_state text;
DECLARE prior_at timestamptz;
DECLARE has_auth boolean;
BEGIN
  SELECT amount_cents INTO expected_amount
  FROM recovery_payment_instructions
  WHERE tenant_id=NEW.tenant_id AND id=NEW.instruction_id;
  IF expected_amount IS NULL THEN RAISE EXCEPTION 'payment instruction missing'; END IF;
  IF NEW.amount_cents <> expected_amount THEN RAISE EXCEPTION 'provider event amount mismatch'; END IF;

  SELECT EXISTS(
    SELECT 1 FROM recovery_payment_authorizations
    WHERE tenant_id=NEW.tenant_id AND instruction_id=NEW.instruction_id
  ) INTO has_auth;
  IF NOT has_auth THEN RAISE EXCEPTION 'payment event requires authorization'; END IF;

  SELECT state, occurred_at INTO prior_state, prior_at
  FROM recovery_payment_events
  WHERE tenant_id=NEW.tenant_id AND instruction_id=NEW.instruction_id
  ORDER BY occurred_at DESC, created_at DESC
  LIMIT 1;

  IF prior_state IS NULL THEN
    prior_state := 'AUTHORIZED';
  ELSIF NEW.occurred_at < prior_at THEN
    RAISE EXCEPTION 'payment event predates prior event';
  END IF;

  IF NOT (
    (prior_state='AUTHORIZED' AND NEW.state='SUBMITTED') OR
    (prior_state='SUBMITTED' AND NEW.state IN ('ACCEPTED','FAILED')) OR
    (prior_state='ACCEPTED' AND NEW.state IN ('SETTLED','FAILED')) OR
    (prior_state='SETTLED' AND NEW.state='REVERSED')
  ) THEN
    RAISE EXCEPTION 'invalid payment lifecycle transition';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER recovery_payment_event_guard_t
  BEFORE INSERT ON recovery_payment_events
  FOR EACH ROW EXECUTE FUNCTION recovery_payment_event_guard();
