PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ingestion_runs (
  id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  stats_json TEXT
);

CREATE TABLE IF NOT EXISTS authority_versions (
  id INTEGER PRIMARY KEY,
  authority_key TEXT NOT NULL,
  repository TEXT NOT NULL,
  revision TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  schema_path TEXT NOT NULL,
  schema_blob_sha TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  UNIQUE(authority_key, revision, schema_blob_sha)
);

CREATE TABLE IF NOT EXISTS source_domains (
  id INTEGER PRIMARY KEY,
  source_key TEXT NOT NULL UNIQUE,
  hospital_name TEXT,
  homepage_url TEXT NOT NULL,
  root_url TEXT NOT NULL,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS txt_snapshots (
  id INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES source_domains(id),
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

CREATE TABLE IF NOT EXISTS hpt_entries (
  id INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES source_domains(id),
  txt_snapshot_id INTEGER REFERENCES txt_snapshots(id),
  location_name TEXT NOT NULL,
  source_page_url TEXT NOT NULL,
  mrf_url TEXT NOT NULL,
  contact_fields_present INTEGER NOT NULL DEFAULT 0,
  discovered_at TEXT NOT NULL,
  UNIQUE(source_id, location_name, mrf_url, txt_snapshot_id)
);

CREATE INDEX IF NOT EXISTS idx_hpt_entries_url ON hpt_entries(mrf_url);

CREATE TABLE IF NOT EXISTS mrf_snapshots (
  id INTEGER PRIMARY KEY,
  mrf_url TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  requested_url TEXT NOT NULL,
  final_url TEXT,
  http_status INTEGER,
  content_type TEXT,
  format TEXT,
  compression TEXT,
  byte_count INTEGER NOT NULL DEFAULT 0,
  sha256 TEXT NOT NULL,
  blob_relpath TEXT,
  etag TEXT,
  last_modified TEXT,
  schema_version TEXT,
  hospital_name TEXT,
  last_updated_on TEXT,
  attestation_confirmed INTEGER,
  parser_status TEXT NOT NULL,
  authority_version_id INTEGER REFERENCES authority_versions(id),
  UNIQUE(mrf_url, sha256)
);

CREATE INDEX IF NOT EXISTS idx_mrf_snapshots_sha ON mrf_snapshots(sha256);
CREATE INDEX IF NOT EXISTS idx_mrf_snapshots_hospital ON mrf_snapshots(hospital_name);

CREATE TABLE IF NOT EXISTS hospital_identities (
  mrf_snapshot_id INTEGER NOT NULL REFERENCES mrf_snapshots(id),
  location_name TEXT,
  hospital_address TEXT,
  license_number TEXT,
  license_state TEXT,
  type_2_npi TEXT,
  PRIMARY KEY(mrf_snapshot_id, location_name, hospital_address, type_2_npi)
);

CREATE INDEX IF NOT EXISTS idx_hospital_identity_npi ON hospital_identities(type_2_npi);

CREATE TABLE IF NOT EXISTS charge_rows (
  id INTEGER PRIMARY KEY,
  mrf_snapshot_id INTEGER NOT NULL REFERENCES mrf_snapshots(id),
  extraction_run_id TEXT NOT NULL,
  description TEXT,
  code_type TEXT NOT NULL,
  code TEXT NOT NULL,
  setting TEXT,
  modifier_json TEXT,
  gross_charge TEXT,
  discounted_cash TEXT,
  minimum_negotiated TEXT,
  maximum_negotiated TEXT,
  payer_name TEXT,
  plan_name TEXT,
  methodology TEXT,
  standard_charge_dollar TEXT,
  standard_charge_percentage TEXT,
  standard_charge_algorithm TEXT,
  median_amount TEXT,
  percentile_10 TEXT,
  percentile_90 TEXT,
  allowed_amount_count TEXT,
  additional_payer_notes TEXT,
  additional_generic_notes TEXT,
  source_locator TEXT NOT NULL,
  observed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_charge_rows_code ON charge_rows(code_type, code);
CREATE INDEX IF NOT EXISTS idx_charge_rows_payer ON charge_rows(payer_name, plan_name);
CREATE INDEX IF NOT EXISTS idx_charge_rows_snapshot ON charge_rows(mrf_snapshot_id);

CREATE TABLE IF NOT EXISTS ingestion_errors (
  id INTEGER PRIMARY KEY,
  source_key TEXT,
  url TEXT,
  occurred_at TEXT NOT NULL,
  stage TEXT NOT NULL,
  error_type TEXT NOT NULL,
  detail TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS hospital_rate_benchmark_ledger AS
SELECT
  ms.hospital_name,
  ms.last_updated_on,
  ms.schema_version,
  hi.location_name,
  hi.hospital_address,
  hi.license_state,
  hi.type_2_npi,
  cr.description,
  cr.code_type,
  cr.code,
  cr.setting,
  cr.modifier_json,
  cr.gross_charge,
  cr.discounted_cash,
  cr.minimum_negotiated,
  cr.maximum_negotiated,
  cr.payer_name,
  cr.plan_name,
  cr.methodology,
  cr.standard_charge_dollar,
  cr.standard_charge_percentage,
  cr.standard_charge_algorithm,
  cr.median_amount,
  cr.percentile_10,
  cr.percentile_90,
  cr.allowed_amount_count,
  cr.additional_payer_notes,
  cr.additional_generic_notes,
  ms.mrf_url,
  ms.sha256 AS mrf_sha256,
  cr.source_locator,
  cr.observed_at,
  cr.extraction_run_id
FROM charge_rows cr
JOIN mrf_snapshots ms ON ms.id = cr.mrf_snapshot_id
LEFT JOIN hospital_identities hi ON hi.mrf_snapshot_id = ms.id;
