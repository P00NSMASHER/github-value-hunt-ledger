PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ingestion_runs (
  id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  stats_json TEXT
);

CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY,
  source_key TEXT NOT NULL UNIQUE,
  payer_name TEXT NOT NULL,
  adapter TEXT NOT NULL,
  source_url TEXT NOT NULL,
  historical INTEGER NOT NULL DEFAULT 0,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS source_snapshots (
  id INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES sources(id),
  observed_at TEXT NOT NULL,
  requested_url TEXT NOT NULL,
  final_url TEXT,
  http_status INTEGER,
  content_type TEXT,
  byte_count INTEGER NOT NULL DEFAULT 0,
  sha256 TEXT,
  blob_relpath TEXT,
  etag TEXT,
  last_modified TEXT,
  parser_status TEXT NOT NULL,
  UNIQUE(source_id, requested_url, sha256)
);

CREATE INDEX IF NOT EXISTS idx_source_snapshots_sha
  ON source_snapshots(sha256);

CREATE TABLE IF NOT EXISTS mrf_files (
  id INTEGER PRIMARY KEY,
  payer_name TEXT NOT NULL,
  source_key TEXT NOT NULL,
  file_url TEXT NOT NULL,
  file_type TEXT NOT NULL,
  discovered_at TEXT NOT NULL,
  discovered_from_snapshot_id INTEGER REFERENCES source_snapshots(id),
  source_manifest_sha256 TEXT,
  historical INTEGER NOT NULL DEFAULT 0,
  content_length INTEGER,
  etag TEXT,
  last_modified TEXT,
  filename TEXT,
  reporting_entity_name TEXT,
  reporting_entity_type TEXT,
  schema_version TEXT,
  last_updated_on TEXT,
  parse_status TEXT NOT NULL DEFAULT 'catalogued',
  UNIQUE(source_key, file_url, source_manifest_sha256)
);

CREATE INDEX IF NOT EXISTS idx_mrf_files_type ON mrf_files(file_type);
CREATE INDEX IF NOT EXISTS idx_mrf_files_payer ON mrf_files(payer_name);
CREATE INDEX IF NOT EXISTS idx_mrf_files_manifest ON mrf_files(source_manifest_sha256);

CREATE TABLE IF NOT EXISTS plans (
  id INTEGER PRIMARY KEY,
  source_key TEXT NOT NULL,
  plan_name TEXT,
  plan_id_type TEXT,
  plan_id TEXT,
  plan_market_type TEXT,
  issuer_name TEXT,
  plan_sponsor_name TEXT,
  UNIQUE(source_key, plan_name, plan_id_type, plan_id, plan_market_type, issuer_name, plan_sponsor_name)
);

CREATE TABLE IF NOT EXISTS file_plan_links (
  mrf_file_id INTEGER NOT NULL REFERENCES mrf_files(id),
  plan_id INTEGER NOT NULL REFERENCES plans(id),
  index_snapshot_id INTEGER REFERENCES source_snapshots(id),
  PRIMARY KEY(mrf_file_id, plan_id)
);

CREATE TABLE IF NOT EXISTS provider_groups (
  id INTEGER PRIMARY KEY,
  rate_file_url TEXT NOT NULL,
  rate_file_sha256 TEXT,
  provider_group_id INTEGER NOT NULL,
  tin_type TEXT,
  tin_value TEXT,
  npi TEXT,
  source_locator TEXT NOT NULL,
  UNIQUE(rate_file_url, provider_group_id, tin_type, tin_value, npi)
);

CREATE INDEX IF NOT EXISTS idx_provider_groups_npi ON provider_groups(npi);
CREATE INDEX IF NOT EXISTS idx_provider_groups_tin ON provider_groups(tin_type, tin_value);

CREATE TABLE IF NOT EXISTS rate_rows (
  id INTEGER PRIMARY KEY,
  rate_file_url TEXT NOT NULL,
  rate_file_sha256 TEXT,
  reporting_entity_name TEXT,
  billing_code_type TEXT,
  billing_code_type_version TEXT,
  billing_code TEXT NOT NULL,
  name TEXT,
  description TEXT,
  negotiation_arrangement TEXT,
  provider_group_id INTEGER,
  negotiated_rate TEXT NOT NULL,
  negotiated_type TEXT,
  expiration_date TEXT,
  billing_class TEXT,
  service_code_json TEXT,
  billing_code_modifier_json TEXT,
  additional_information TEXT,
  source_locator TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  extraction_run_id TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rate_rows_code ON rate_rows(billing_code_type, billing_code);
CREATE INDEX IF NOT EXISTS idx_rate_rows_provider_group ON rate_rows(provider_group_id);
CREATE INDEX IF NOT EXISTS idx_rate_rows_expiration ON rate_rows(expiration_date);

CREATE TABLE IF NOT EXISTS ingestion_errors (
  id INTEGER PRIMARY KEY,
  source_key TEXT,
  url TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  stage TEXT NOT NULL,
  error_type TEXT NOT NULL,
  detail TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS payer_rate_benchmark_ledger AS
SELECT
  rr.reporting_entity_name,
  rr.billing_code_type,
  rr.billing_code_type_version,
  rr.billing_code,
  rr.name,
  rr.description,
  rr.negotiation_arrangement,
  rr.provider_group_id,
  rr.negotiated_rate,
  rr.negotiated_type,
  rr.expiration_date,
  rr.billing_class,
  rr.service_code_json,
  rr.billing_code_modifier_json,
  rr.additional_information,
  rr.rate_file_url,
  rr.rate_file_sha256,
  rr.source_locator,
  rr.observed_at,
  rr.extraction_run_id,
  pg.tin_type,
  pg.tin_value,
  pg.npi
FROM rate_rows rr
LEFT JOIN provider_groups pg
  ON pg.rate_file_url = rr.rate_file_url
 AND pg.provider_group_id = rr.provider_group_id;
