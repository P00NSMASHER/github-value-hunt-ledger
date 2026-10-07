-- RecoveryOS Phase 1 production data-plane reference schema.
-- Authentication/session tables are provided by the hosting environment.
-- This file preserves tenant/evidence invariants used by the deployed Phase 1 app.

CREATE TABLE recovery_tenants (
  id text PRIMARY KEY,
  name text NOT NULL,
  slug text NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE recovery_tenant_memberships (
  tenant_id text NOT NULL REFERENCES recovery_tenants(id) ON DELETE RESTRICT,
  user_id bigint NOT NULL,
  role text NOT NULL CHECK (role IN ('owner','reviewer','viewer')),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id,user_id)
);

CREATE TABLE recovery_populations (
  id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES recovery_tenants(id) ON DELETE RESTRICT,
  buyer_id text NOT NULL,
  business_unit text NOT NULL,
  population_hash text NOT NULL CHECK (population_hash ~ '^[0-9a-f]{64}$'),
  status text NOT NULL CHECK (status IN ('DRAFT','FROZEN','CLOSED')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id,population_hash),
  UNIQUE (tenant_id,id)
);

CREATE TABLE recovery_ingress_receipts (
  id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES recovery_tenants(id) ON DELETE RESTRICT,
  transport text NOT NULL CHECK (transport IN ('API','EMAIL','SFTP','PORTAL','UPLOAD','BATCH')),
  filename text NOT NULL,
  file_sha256 text NOT NULL CHECK (file_sha256 ~ '^[0-9a-f]{64}$'),
  size_bytes bigint NOT NULL CHECK (size_bytes >= 0),
  detected_format text NOT NULL,
  status text NOT NULL CHECK (status IN ('ACCEPT','REJECT')),
  route text NOT NULL,
  reasons jsonb NOT NULL DEFAULT '[]'::jsonb,
  receipt_hash text NOT NULL CHECK (receipt_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id,receipt_hash)
);

CREATE TABLE recovery_freight_records (
  id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES recovery_tenants(id) ON DELETE RESTRICT,
  population_id text NOT NULL,
  buyer_id text NOT NULL,
  business_unit text NOT NULL,
  invoice_id text NOT NULL,
  shipment_id text NOT NULL,
  mode text NOT NULL CHECK (mode IN ('PARCEL','LTL','TL','INTERMODAL','AIR','OCEAN')),
  currency text NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
  billed_total_cents bigint NOT NULL CHECK (billed_total_cents >= 0),
  record_hash text NOT NULL CHECK (record_hash ~ '^[0-9a-f]{64}$'),
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id,record_hash),
  FOREIGN KEY (tenant_id,population_id)
    REFERENCES recovery_populations(tenant_id,id) ON DELETE RESTRICT
);

CREATE TABLE recovery_incumbent_snapshots (
  id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES recovery_tenants(id) ON DELETE RESTRICT,
  population_id text NOT NULL,
  source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
  snapshot_hash text NOT NULL CHECK (snapshot_hash ~ '^[0-9a-f]{64}$'),
  payload jsonb NOT NULL,
  frozen_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id,snapshot_hash),
  FOREIGN KEY (tenant_id,population_id)
    REFERENCES recovery_populations(tenant_id,id) ON DELETE RESTRICT
);

CREATE TABLE recovery_challenge_findings (
  id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES recovery_tenants(id) ON DELETE RESTRICT,
  population_id text NOT NULL,
  economic_key text NOT NULL,
  record_hash text NOT NULL CHECK (record_hash ~ '^[0-9a-f]{64}$'),
  incumbent_snapshot_hash text NOT NULL CHECK (incumbent_snapshot_hash ~ '^[0-9a-f]{64}$'),
  category text NOT NULL,
  billed_cents bigint NOT NULL CHECK (billed_cents >= 0),
  expected_cents bigint NOT NULL CHECK (expected_cents >= 0),
  variance_cents bigint NOT NULL CHECK (variance_cents >= 0),
  net_new_candidate_cents bigint NOT NULL CHECK (net_new_candidate_cents >= 0),
  attribution_state text NOT NULL CHECK (attribution_state IN ('CHALLENGER_ONLY','INCUMBENT_KNOWN','SUPPRESSED','REVIEW')),
  confidence_ppm integer NOT NULL CHECK (confidence_ppm BETWEEN 0 AND 1000000),
  blocker_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
  evidence jsonb NOT NULL DEFAULT '[]'::jsonb,
  matched_incumbent_matter_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  finding_hash text NOT NULL CHECK (finding_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id,finding_hash),
  UNIQUE (tenant_id,id),
  FOREIGN KEY (tenant_id,population_id)
    REFERENCES recovery_populations(tenant_id,id) ON DELETE RESTRICT
);

CREATE TABLE recovery_review_dispositions (
  id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES recovery_tenants(id) ON DELETE RESTRICT,
  finding_id text NOT NULL,
  reviewer_user_id bigint NOT NULL,
  decision text NOT NULL CHECK (decision IN ('CONFIRM','REJECT','NEED_EVIDENCE','MODIFY_RULE','ESCALATE')),
  reason text NOT NULL,
  corrected_expected_cents bigint CHECK (corrected_expected_cents IS NULL OR corrected_expected_cents >= 0),
  rule_candidate text,
  disposition_hash text NOT NULL CHECK (disposition_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id,disposition_hash),
  FOREIGN KEY (tenant_id,finding_id)
    REFERENCES recovery_challenge_findings(tenant_id,id) ON DELETE RESTRICT
);

CREATE TABLE recovery_audit_events (
  id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES recovery_tenants(id) ON DELETE RESTRICT,
  event_type text NOT NULL,
  object_id text NOT NULL,
  object_hash text NOT NULL CHECK (object_hash ~ '^[0-9a-f]{64}$'),
  actor_user_id bigint,
  event_hash text NOT NULL CHECK (event_hash ~ '^[0-9a-f]{64}$'),
  occurred_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id,event_hash)
);

CREATE TABLE recovery_api_keys (
  id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES recovery_tenants(id) ON DELETE RESTRICT,
  label text NOT NULL,
  key_hash text NOT NULL UNIQUE CHECK (key_hash ~ '^[0-9a-f]{64}$'),
  scope text NOT NULL CHECK (scope IN ('ingest')),
  created_by bigint NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  revoked_at timestamptz
);

CREATE OR REPLACE FUNCTION recovery_block_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'immutable recovery evidence cannot be updated or deleted';
END;
$$;

CREATE TRIGGER recovery_populations_immutable
  BEFORE UPDATE OR DELETE ON recovery_populations
  FOR EACH ROW EXECUTE FUNCTION recovery_block_mutation();
CREATE TRIGGER recovery_ingress_immutable
  BEFORE UPDATE OR DELETE ON recovery_ingress_receipts
  FOR EACH ROW EXECUTE FUNCTION recovery_block_mutation();
CREATE TRIGGER recovery_records_immutable
  BEFORE UPDATE OR DELETE ON recovery_freight_records
  FOR EACH ROW EXECUTE FUNCTION recovery_block_mutation();
CREATE TRIGGER recovery_incumbent_immutable
  BEFORE UPDATE OR DELETE ON recovery_incumbent_snapshots
  FOR EACH ROW EXECUTE FUNCTION recovery_block_mutation();
CREATE TRIGGER recovery_findings_immutable
  BEFORE UPDATE OR DELETE ON recovery_challenge_findings
  FOR EACH ROW EXECUTE FUNCTION recovery_block_mutation();
CREATE TRIGGER recovery_review_immutable
  BEFORE UPDATE OR DELETE ON recovery_review_dispositions
  FOR EACH ROW EXECUTE FUNCTION recovery_block_mutation();
CREATE TRIGGER recovery_audit_immutable
  BEFORE UPDATE OR DELETE ON recovery_audit_events
  FOR EACH ROW EXECUTE FUNCTION recovery_block_mutation();
