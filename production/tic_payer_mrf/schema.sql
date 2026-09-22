PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  mode TEXT NOT NULL,
  status TEXT NOT NULL,
  stats_json TEXT
);

CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY,
  source_id TEXT NOT NULL UNIQUE,
  payer_family TEXT NOT NULL,
  resolver TEXT NOT NULL,
  seed_url TEXT NOT NULL,
  config_json TEXT NOT NULL,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_observations (
  id INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES sources(id),
  requested_url TEXT NOT NULL,
  final_url TEXT,
  fetched_at TEXT NOT NULL,
  http_status INTEGER,
  content_type TEXT,
  byte_count INTEGER NOT NULL DEFAULT 0,
  sha256 TEXT,
  blob_relpath TEXT,
  etag TEXT,
  last_modified TEXT,
  parser_status TEXT NOT NULL,
  reporting_entity_name TEXT,
  reporting_entity_type TEXT,
  last_updated_on TEXT,
  schema_version TEXT,
  UNIQUE(source_id, requested_url, sha256)
);

CREATE INDEX IF NOT EXISTS idx_source_observations_sha ON source_observations(sha256);

CREATE TABLE IF NOT EXISTS catalog_files (
  id INTEGER PRIMARY KEY,
  file_url TEXT NOT NULL UNIQUE,
  file_kind TEXT NOT NULL,
  description TEXT,
  discovered_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  source_observation_id INTEGER REFERENCES source_observations(id),
  payer_family TEXT,
  reporting_entity_name TEXT,
  content_length INTEGER,
  content_type TEXT,
  etag TEXT,
  last_modified TEXT,
  http_status INTEGER,
  metadata_status TEXT NOT NULL DEFAULT 'unprobed'
);

CREATE INDEX IF NOT EXISTS idx_catalog_kind ON catalog_files(file_kind);
CREATE INDEX IF NOT EXISTS idx_catalog_payer ON catalog_files(payer_family);

CREATE TABLE IF NOT EXISTS plans (
  id INTEGER PRIMARY KEY,
  plan_key TEXT NOT NULL UNIQUE,
  plan_name TEXT,
  plan_sponsor_name TEXT,
  issuer_name TEXT,
  plan_id_type TEXT,
  plan_id TEXT,
  plan_market_type TEXT
);

CREATE TABLE IF NOT EXISTS file_plan_links (
  catalog_file_id INTEGER NOT NULL REFERENCES catalog_files(id),
  plan_id INTEGER NOT NULL REFERENCES plans(id),
  source_observation_id INTEGER REFERENCES source_observations(id),
  PRIMARY KEY(catalog_file_id, plan_id)
);

CREATE TABLE IF NOT EXISTS mrf_snapshots (
  id INTEGER PRIMARY KEY,
  catalog_file_id INTEGER REFERENCES catalog_files(id),
  requested_url TEXT,
  source_file_name TEXT,
  fetched_at TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  blob_relpath TEXT NOT NULL,
  byte_count INTEGER NOT NULL,
  content_type TEXT,
  reporting_entity_name TEXT,
  reporting_entity_type TEXT,
  last_updated_on TEXT,
  schema_version TEXT,
  plan_name TEXT,
  issuer_name TEXT,
  plan_sponsor_name TEXT,
  plan_id_type TEXT,
  plan_id TEXT,
  plan_market_type TEXT,
  mrf_kind TEXT NOT NULL,
  parser_version TEXT NOT NULL,
  UNIQUE(sha256, mrf_kind, parser_version)
);

CREATE INDEX IF NOT EXISTS idx_mrf_sha ON mrf_snapshots(sha256);

CREATE TABLE IF NOT EXISTS provider_groups (
  id INTEGER PRIMARY KEY,
  snapshot_id INTEGER NOT NULL REFERENCES mrf_snapshots(id),
  provider_group_id INTEGER NOT NULL,
  network_names_json TEXT,
  evidence_locator TEXT NOT NULL,
  UNIQUE(snapshot_id, provider_group_id)
);

CREATE TABLE IF NOT EXISTS provider_entities (
  id INTEGER PRIMARY KEY,
  provider_group_row_id INTEGER NOT NULL REFERENCES provider_groups(id),
  tin_type TEXT,
  tin_value TEXT,
  business_name TEXT,
  npi TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_provider_entity_unique
ON provider_entities(
  provider_group_row_id,
  COALESCE(tin_type,''),
  COALESCE(tin_value,''),
  COALESCE(npi,'')
);

CREATE INDEX IF NOT EXISTS idx_provider_npi ON provider_entities(npi);
CREATE INDEX IF NOT EXISTS idx_provider_tin ON provider_entities(tin_type, tin_value);

CREATE TABLE IF NOT EXISTS negotiated_rates (
  id INTEGER PRIMARY KEY,
  snapshot_id INTEGER NOT NULL REFERENCES mrf_snapshots(id),
  billing_code_type TEXT,
  billing_code_type_version TEXT,
  billing_code TEXT NOT NULL,
  description TEXT,
  negotiation_arrangement TEXT,
  provider_group_id INTEGER,
  negotiated_type TEXT,
  negotiated_rate TEXT NOT NULL,
  expiration_date TEXT,
  billing_class TEXT,
  setting TEXT,
  service_codes_json TEXT,
  modifiers_json TEXT,
  additional_information TEXT,
  evidence_locator TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rates_code ON negotiated_rates(billing_code_type, billing_code);
CREATE INDEX IF NOT EXISTS idx_rates_group ON negotiated_rates(snapshot_id, provider_group_id);
CREATE INDEX IF NOT EXISTS idx_rates_expiration ON negotiated_rates(expiration_date);

CREATE TABLE IF NOT EXISTS allowed_amounts (
  id INTEGER PRIMARY KEY,
  snapshot_id INTEGER NOT NULL REFERENCES mrf_snapshots(id),
  billing_code_type TEXT,
  billing_code_type_version TEXT,
  billing_code TEXT NOT NULL,
  description TEXT,
  tin_type TEXT,
  tin_value TEXT,
  billing_class TEXT,
  service_codes_json TEXT,
  modifiers_json TEXT,
  allowed_amount TEXT NOT NULL,
  billed_charge TEXT,
  npi TEXT,
  evidence_locator TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_allowed_code ON allowed_amounts(billing_code_type, billing_code);
CREATE INDEX IF NOT EXISTS idx_allowed_npi ON allowed_amounts(npi);

CREATE TABLE IF NOT EXISTS errors (
  id INTEGER PRIMARY KEY,
  occurred_at TEXT NOT NULL,
  stage TEXT NOT NULL,
  source_id TEXT,
  url TEXT,
  error_type TEXT NOT NULL,
  detail TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS payer_rate_evidence AS
SELECT
  s.id AS snapshot_id,
  s.sha256 AS source_sha256,
  s.requested_url AS source_url,
  s.reporting_entity_name,
  s.last_updated_on,
  s.schema_version,
  s.plan_name,
  s.issuer_name,
  s.plan_sponsor_name,
  s.plan_id_type,
  s.plan_id,
  r.billing_code_type,
  r.billing_code_type_version,
  r.billing_code,
  r.negotiation_arrangement,
  r.provider_group_id,
  r.negotiated_type,
  r.negotiated_rate,
  r.expiration_date,
  r.billing_class,
  r.setting,
  r.service_codes_json,
  r.modifiers_json,
  r.evidence_locator
FROM negotiated_rates r
JOIN mrf_snapshots s ON s.id=r.snapshot_id;

CREATE VIEW IF NOT EXISTS payer_allowed_amount_evidence AS
SELECT
  s.id AS snapshot_id,
  s.sha256 AS source_sha256,
  s.requested_url AS source_url,
  s.reporting_entity_name,
  s.last_updated_on,
  s.schema_version,
  s.plan_name,
  s.issuer_name,
  s.plan_id_type,
  s.plan_id,
  a.billing_code_type,
  a.billing_code_type_version,
  a.billing_code,
  a.tin_type,
  a.tin_value,
  a.billing_class,
  a.allowed_amount,
  a.billed_charge,
  a.npi,
  a.evidence_locator
FROM allowed_amounts a
JOIN mrf_snapshots s ON s.id=a.snapshot_id;
