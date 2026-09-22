PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS crawl_runs (
  id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  mode TEXT NOT NULL,
  status TEXT NOT NULL,
  stats_json TEXT
);

CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY,
  payer_key TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  landing_url TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshots (
  id INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES sources(id),
  requested_url TEXT NOT NULL,
  final_url TEXT,
  fetched_at TEXT NOT NULL,
  http_status INTEGER,
  content_type TEXT,
  byte_count INTEGER NOT NULL DEFAULT 0,
  sha256 TEXT,
  etag TEXT,
  last_modified TEXT,
  blob_relpath TEXT,
  parser_status TEXT NOT NULL,
  UNIQUE(source_id, requested_url, sha256)
);

CREATE INDEX IF NOT EXISTS idx_tic_snapshots_sha ON snapshots(sha256);

CREATE TABLE IF NOT EXISTS snapshot_observations (
  id INTEGER PRIMARY KEY,
  snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
  observed_at TEXT NOT NULL,
  http_status INTEGER,
  final_url TEXT,
  etag TEXT,
  last_modified TEXT,
  UNIQUE(snapshot_id, observed_at)
);

CREATE TABLE IF NOT EXISTS mrf_files (
  id INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES sources(id),
  discovered_from_snapshot_id INTEGER REFERENCES snapshots(id),
  url TEXT NOT NULL,
  file_type TEXT NOT NULL,
  reporting_entity_name TEXT,
  reporting_entity_type TEXT,
  last_updated_on TEXT,
  schema_version TEXT,
  etag TEXT,
  last_modified TEXT,
  content_length INTEGER,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  access_status TEXT NOT NULL DEFAULT 'DISCOVERED',
  UNIQUE(source_id, url)
);

CREATE INDEX IF NOT EXISTS idx_tic_mrf_type ON mrf_files(file_type);
CREATE INDEX IF NOT EXISTS idx_tic_mrf_entity ON mrf_files(reporting_entity_name);

CREATE TABLE IF NOT EXISTS plans (
  id INTEGER PRIMARY KEY,
  mrf_file_id INTEGER NOT NULL REFERENCES mrf_files(id),
  plan_name TEXT,
  plan_id_type TEXT,
  plan_id TEXT,
  plan_market_type TEXT,
  UNIQUE(
    mrf_file_id,
    COALESCE(plan_name,''),
    COALESCE(plan_id_type,''),
    COALESCE(plan_id,''),
    COALESCE(plan_market_type,'')
  )
);

CREATE TABLE IF NOT EXISTS rate_extract_runs (
  id INTEGER PRIMARY KEY,
  mrf_file_id INTEGER NOT NULL REFERENCES mrf_files(id),
  started_at TEXT NOT NULL,
  finished_at TEXT,
  parser_version TEXT NOT NULL,
  code_filter_sha256 TEXT,
  npi_filter_sha256 TEXT,
  source_sha256 TEXT,
  source_etag TEXT,
  source_last_modified TEXT,
  status TEXT NOT NULL,
  stats_json TEXT
);

CREATE TABLE IF NOT EXISTS provider_groups (
  id INTEGER PRIMARY KEY,
  rate_extract_run_id INTEGER NOT NULL REFERENCES rate_extract_runs(id),
  provider_group_id TEXT NOT NULL,
  tin_type TEXT,
  tin_value TEXT,
  UNIQUE(rate_extract_run_id, provider_group_id, COALESCE(tin_type,''), COALESCE(tin_value,''))
);

CREATE TABLE IF NOT EXISTS provider_group_npis (
  provider_group_row_id INTEGER NOT NULL REFERENCES provider_groups(id),
  npi TEXT NOT NULL,
  PRIMARY KEY(provider_group_row_id, npi)
);

CREATE TABLE IF NOT EXISTS rates (
  id INTEGER PRIMARY KEY,
  rate_extract_run_id INTEGER NOT NULL REFERENCES rate_extract_runs(id),
  billing_code_type TEXT NOT NULL,
  billing_code_type_version TEXT,
  billing_code TEXT NOT NULL,
  description TEXT,
  name TEXT,
  billing_class TEXT,
  negotiation_arrangement TEXT,
  negotiated_type TEXT,
  negotiated_rate TEXT,
  expiration_date TEXT,
  provider_group_id TEXT,
  service_codes_json TEXT,
  billing_code_modifiers_json TEXT,
  additional_information TEXT,
  evidence_fingerprint TEXT NOT NULL,
  UNIQUE(rate_extract_run_id, evidence_fingerprint)
);

CREATE INDEX IF NOT EXISTS idx_tic_rates_code ON rates(billing_code_type, billing_code);
CREATE INDEX IF NOT EXISTS idx_tic_rates_provider_ref ON rates(provider_group_id);
CREATE INDEX IF NOT EXISTS idx_tic_rates_expiration ON rates(expiration_date);

CREATE TABLE IF NOT EXISTS crawl_errors (
  id INTEGER PRIMARY KEY,
  source_id INTEGER,
  url TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  stage TEXT NOT NULL,
  error_type TEXT NOT NULL,
  detail TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS payer_rate_public_evidence AS
SELECT
  s.payer_key,
  s.display_name AS payer_display_name,
  f.id AS mrf_file_id,
  f.url AS mrf_url,
  f.reporting_entity_name,
  f.reporting_entity_type,
  f.last_updated_on,
  f.schema_version,
  r.billing_code_type,
  r.billing_code_type_version,
  r.billing_code,
  r.description,
  r.name,
  r.billing_class,
  r.negotiation_arrangement,
  r.negotiated_type,
  r.negotiated_rate,
  r.expiration_date,
  r.provider_group_id,
  r.service_codes_json,
  r.billing_code_modifiers_json,
  x.source_sha256,
  x.source_etag,
  x.source_last_modified,
  x.parser_version,
  'CORROBORATING_PUBLIC_RATE' AS authority_role
FROM rates r
JOIN rate_extract_runs x ON x.id=r.rate_extract_run_id
JOIN mrf_files f ON f.id=x.mrf_file_id
JOIN sources s ON s.id=f.source_id;
