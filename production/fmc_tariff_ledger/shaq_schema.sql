PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS shaq_runs (
  id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  endpoint TEXT NOT NULL,
  server_name TEXT,
  server_version TEXT,
  parser_version TEXT NOT NULL,
  status TEXT NOT NULL,
  stats_json TEXT
);

CREATE TABLE IF NOT EXISTS shaq_queries (
  id INTEGER PRIMARY KEY,
  run_id INTEGER NOT NULL REFERENCES shaq_runs(id),
  tool_name TEXT NOT NULL,
  arguments_json TEXT NOT NULL,
  requested_at TEXT NOT NULL,
  completed_at TEXT,
  response_text TEXT,
  response_sha256 TEXT,
  raw_relpath TEXT,
  is_error INTEGER NOT NULL DEFAULT 0,
  error_text TEXT,
  UNIQUE(run_id, tool_name, arguments_json)
);

CREATE INDEX IF NOT EXISTS idx_shaq_query_sha
  ON shaq_queries(response_sha256);

CREATE TABLE IF NOT EXISTS shaq_ports (
  id INTEGER PRIMARY KEY,
  query_id INTEGER REFERENCES shaq_queries(id),
  route_page_id INTEGER REFERENCES shaq_route_pages(id),
  raw_name TEXT NOT NULL,
  normalized_name TEXT NOT NULL,
  port_code TEXT,
  country TEXT,
  aliases_json TEXT,
  raw_record_json TEXT NOT NULL,
  UNIQUE(query_id, raw_name, COALESCE(port_code, ''))
);

CREATE TABLE IF NOT EXISTS shaq_route_pages (
  id INTEGER PRIMARY KEY,
  run_id INTEGER REFERENCES shaq_runs(id),
  url TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  http_status INTEGER,
  content_type TEXT,
  byte_count INTEGER NOT NULL DEFAULT 0,
  sha256 TEXT,
  blob_relpath TEXT,
  page_title TEXT,
  page_heading TEXT,
  parser_status TEXT NOT NULL,
  lastmod TEXT,
  UNIQUE(url, sha256)
);

CREATE INDEX IF NOT EXISTS idx_shaq_route_page_sha
  ON shaq_route_pages(sha256);

CREATE TABLE IF NOT EXISTS shaq_rates (
  id INTEGER PRIMARY KEY,
  query_id INTEGER NOT NULL REFERENCES shaq_queries(id),
  origin_query TEXT,
  destination_query TEXT,
  origin_raw TEXT,
  destination_raw TEXT,
  carrier_raw TEXT,
  carrier_normalized TEXT,
  fmc_organization_no TEXT,
  fmc_identity_status TEXT NOT NULL DEFAULT 'UNRESOLVED',
  service_type TEXT,
  container_type TEXT,
  amount_value TEXT,
  currency TEXT,
  valid_from TEXT,
  valid_to TEXT,
  rate_basis TEXT,
  transit_time TEXT,
  source_url TEXT,
  rate_kind TEXT NOT NULL DEFAULT 'UNKNOWN',
  source_label TEXT,
  source_contract_reference TEXT,
  evidence_excerpt TEXT NOT NULL,
  raw_record_json TEXT,
  parser_confidence REAL NOT NULL,
  parser_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_shaq_rates_lane
  ON shaq_rates(origin_raw, destination_raw, container_type);
CREATE INDEX IF NOT EXISTS idx_shaq_rates_carrier
  ON shaq_rates(carrier_normalized, fmc_organization_no);
CREATE INDEX IF NOT EXISTS idx_shaq_rates_validity
  ON shaq_rates(valid_from, valid_to);

CREATE UNIQUE INDEX IF NOT EXISTS idx_shaq_route_rate_dedupe
ON shaq_rates(
  COALESCE(route_page_id, -1),
  COALESCE(origin_raw, ''),
  COALESCE(destination_raw, ''),
  COALESCE(carrier_raw, ''),
  COALESCE(container_type, ''),
  COALESCE(amount_value, ''),
  COALESCE(currency, ''),
  COALESCE(valid_from, ''),
  COALESCE(valid_to, ''),
  COALESCE(source_url, '')
);

CREATE TABLE IF NOT EXISTS carrier_identity_map (
  id INTEGER PRIMARY KEY,
  carrier_raw_pattern TEXT NOT NULL,
  carrier_normalized TEXT NOT NULL,
  fmc_organization_no TEXT,
  mapping_method TEXT NOT NULL,
  confidence REAL NOT NULL,
  reviewed INTEGER NOT NULL DEFAULT 0,
  evidence TEXT,
  created_at TEXT NOT NULL,
  UNIQUE(carrier_raw_pattern, carrier_normalized)
);


CREATE TABLE IF NOT EXISTS shaq_source_classification (
  id INTEGER PRIMARY KEY,
  source_pattern TEXT NOT NULL UNIQUE,
  rate_kind TEXT NOT NULL,
  classification_method TEXT NOT NULL,
  reviewed INTEGER NOT NULL DEFAULT 0,
  evidence TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dataset_authorizations (
  id INTEGER PRIMARY KEY,
  dataset_key TEXT NOT NULL UNIQUE,
  authorization_scope TEXT NOT NULL,
  asserted_by TEXT NOT NULL,
  asserted_at TEXT NOT NULL,
  evidence_note TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS shaq_rate_authority_view AS
SELECT
  r.*,
  CASE
    WHEN r.rate_kind <> 'CARRIER_CONTRACT' THEN 'BENCHMARK_ONLY'
    WHEN r.fmc_organization_no IS NULL THEN 'UNRESOLVED'
    WHEN r.fmc_identity_status NOT IN ('REVIEWED_EXACT','REVIEWED_NORMALIZED_ALIAS') THEN 'IDENTITY_REVIEW_REQUIRED'
    WHEN r.valid_from IS NULL AND r.valid_to IS NULL THEN 'VALIDITY_REVIEW_REQUIRED'
    ELSE 'AUTHORITY_READY'
  END AS authority_readiness
FROM shaq_rates r;
