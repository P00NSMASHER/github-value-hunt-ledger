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


CREATE TABLE IF NOT EXISTS registry_sources (
  id INTEGER PRIMARY KEY,
  source_key TEXT NOT NULL,
  repository TEXT NOT NULL,
  revision TEXT NOT NULL,
  source_path TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  byte_count INTEGER NOT NULL,
  blob_relpath TEXT NOT NULL,
  upstream_license TEXT,
  evidence_class TEXT NOT NULL,
  UNIQUE(repository, revision, source_path, sha256)
);

CREATE TABLE IF NOT EXISTS national_hospital_registry (
  id INTEGER PRIMARY KEY,
  registry_source_id INTEGER NOT NULL REFERENCES registry_sources(id),
  ccn TEXT NOT NULL,
  hospital_name TEXT NOT NULL,
  address TEXT,
  city TEXT,
  state TEXT,
  zip TEXT,
  hospital_type TEXT,
  domain TEXT,
  pointer_url TEXT,
  mrf_url TEXT,
  mrf_last_updated TEXT,
  cms_template_version TEXT,
  finding TEXT,
  assessable INTEGER,
  checked_at TEXT,
  evidence TEXT,
  UNIQUE(registry_source_id, ccn)
);

CREATE INDEX IF NOT EXISTS idx_national_hospital_registry_ccn
  ON national_hospital_registry(ccn);
CREATE INDEX IF NOT EXISTS idx_national_hospital_registry_mrf
  ON national_hospital_registry(mrf_url);
CREATE INDEX IF NOT EXISTS idx_national_hospital_registry_domain
  ON national_hospital_registry(domain);

CREATE TABLE IF NOT EXISTS historical_hospital_mrf_registry (
  id INTEGER PRIMARY KEY,
  registry_source_id INTEGER NOT NULL REFERENCES registry_sources(id),
  ccn TEXT,
  reporting_entity_name_legal TEXT,
  reporting_entity_name_common TEXT,
  reporting_entity_type TEXT,
  machine_readable_url TEXT,
  machine_readable_url_status TEXT,
  machine_readable_page TEXT,
  supplemental_url TEXT,
  file_name TEXT,
  file_format TEXT,
  file_size TEXT,
  meets_standard TEXT,
  standard_issue TEXT,
  state_or_region TEXT,
  last_updated_date TEXT,
  entry_date TEXT,
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_historical_hospital_mrf_ccn
  ON historical_hospital_mrf_registry(ccn);
CREATE INDEX IF NOT EXISTS idx_historical_hospital_mrf_url
  ON historical_hospital_mrf_registry(machine_readable_url);

CREATE VIEW IF NOT EXISTS hospital_discovery_evidence AS
SELECT
  'direct_cms_hpt' AS evidence_class,
  NULL AS ccn,
  he.location_name AS hospital_name,
  NULL AS address,
  NULL AS city,
  NULL AS state,
  sd.root_url AS domain_or_root,
  ts.requested_url AS pointer_url,
  he.mrf_url AS mrf_url,
  NULL AS mrf_last_updated,
  NULL AS cms_template_version,
  'DIRECT_POINTER_OBSERVED' AS finding,
  he.discovered_at AS observed_or_checked_at,
  ts.sha256 AS source_sha256
FROM hpt_entries he
JOIN source_domains sd ON sd.id=he.source_id
LEFT JOIN txt_snapshots ts ON ts.id=he.txt_snapshot_id

UNION ALL

SELECT
  'national_2026_tracker',
  n.ccn,
  n.hospital_name,
  n.address,
  n.city,
  n.state,
  n.domain,
  n.pointer_url,
  n.mrf_url,
  n.mrf_last_updated,
  n.cms_template_version,
  n.finding,
  n.checked_at,
  rs.sha256
FROM national_hospital_registry n
JOIN registry_sources rs ON rs.id=n.registry_source_id

UNION ALL

SELECT
  'historical_2022_registry',
  h.ccn,
  COALESCE(NULLIF(h.reporting_entity_name_common,''), h.reporting_entity_name_legal),
  NULL,
  NULL,
  h.state_or_region,
  NULL,
  h.machine_readable_page,
  h.machine_readable_url,
  h.last_updated_date,
  NULL,
  h.machine_readable_url_status,
  h.entry_date,
  rs.sha256
FROM historical_hospital_mrf_registry h
JOIN registry_sources rs ON rs.id=h.registry_source_id;
