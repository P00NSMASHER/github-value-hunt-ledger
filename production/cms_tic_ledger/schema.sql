PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS registry_snapshots (
  id INTEGER PRIMARY KEY,
  source_url TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  http_status INTEGER,
  content_type TEXT,
  byte_count INTEGER NOT NULL DEFAULT 0,
  sha256 TEXT,
  blob_relpath TEXT,
  UNIQUE(source_url, sha256)
);

CREATE TABLE IF NOT EXISTS source_roots (
  id INTEGER PRIMARY KEY,
  payer_name TEXT NOT NULL,
  payer_type TEXT NOT NULL DEFAULT '',
  root_url TEXT NOT NULL,
  notes TEXT NOT NULL DEFAULT '',
  source_tier TEXT NOT NULL,
  registry_sha256 TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  UNIQUE(payer_name, root_url)
);

CREATE TABLE IF NOT EXISTS discovery_runs (
  id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  shard_index INTEGER NOT NULL DEFAULT 0,
  shard_count INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL,
  stats_json TEXT
);

CREATE TABLE IF NOT EXISTS observations (
  id INTEGER PRIMARY KEY,
  source_root_id INTEGER REFERENCES source_roots(id),
  url TEXT NOT NULL,
  parent_url TEXT,
  observed_at TEXT NOT NULL,
  kind TEXT NOT NULL,
  discovery_method TEXT NOT NULL,
  http_status INTEGER,
  content_type TEXT,
  content_length INTEGER,
  etag TEXT,
  last_modified TEXT,
  sha256 TEXT,
  blob_relpath TEXT,
  status TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_obs_url ON observations(url);
CREATE INDEX IF NOT EXISTS idx_obs_sha ON observations(sha256);

CREATE TABLE IF NOT EXISTS reporting_entities (
  id INTEGER PRIMARY KEY,
  source_root_id INTEGER REFERENCES source_roots(id),
  index_url TEXT NOT NULL,
  index_sha256 TEXT,
  reporting_entity_name TEXT NOT NULL DEFAULT '',
  reporting_entity_type TEXT NOT NULL DEFAULT '',
  last_updated_on TEXT,
  schema_version TEXT,
  UNIQUE(index_url, index_sha256)
);

CREATE TABLE IF NOT EXISTS plans (
  plan_key TEXT PRIMARY KEY,
  reporting_entity_id INTEGER REFERENCES reporting_entities(id),
  plan_name TEXT NOT NULL DEFAULT '',
  issuer_name TEXT NOT NULL DEFAULT '',
  plan_id_type TEXT NOT NULL DEFAULT '',
  plan_id TEXT NOT NULL DEFAULT '',
  plan_sponsor_name TEXT NOT NULL DEFAULT '',
  plan_market_type TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS files (
  file_key TEXT PRIMARY KEY,
  source_root_id INTEGER REFERENCES source_roots(id),
  url TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  last_updated_on TEXT,
  schema_version TEXT,
  content_length INTEGER,
  etag TEXT,
  last_modified TEXT,
  source_index_url TEXT,
  source_index_sha256 TEXT,
  status TEXT NOT NULL DEFAULT 'discovered'
);

CREATE INDEX IF NOT EXISTS idx_files_kind ON files(kind);
CREATE INDEX IF NOT EXISTS idx_files_size ON files(content_length);

CREATE TABLE IF NOT EXISTS file_plans (
  file_key TEXT NOT NULL REFERENCES files(file_key),
  plan_key TEXT NOT NULL REFERENCES plans(plan_key),
  PRIMARY KEY(file_key, plan_key)
);

CREATE TABLE IF NOT EXISTS ingest_runs (
  id INTEGER PRIMARY KEY,
  file_key TEXT REFERENCES files(file_key),
  source_url TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  source_sha256 TEXT,
  raw_blob_relpath TEXT,
  compressed_bytes INTEGER,
  parser_version TEXT NOT NULL,
  filters_json TEXT NOT NULL,
  output_manifest TEXT,
  status TEXT NOT NULL,
  stats_json TEXT
);

CREATE TABLE IF NOT EXISTS errors (
  id INTEGER PRIMARY KEY,
  source_root_id INTEGER,
  url TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  stage TEXT NOT NULL,
  error_type TEXT NOT NULL,
  detail TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS file_plan_catalog AS
SELECT
  f.file_key,
  f.url,
  f.kind,
  f.description,
  f.content_length,
  f.etag,
  f.last_modified,
  f.first_seen_at,
  f.last_seen_at,
  f.last_updated_on,
  f.schema_version,
  p.plan_key,
  p.plan_name,
  p.issuer_name,
  p.plan_id_type,
  p.plan_id,
  p.plan_sponsor_name,
  p.plan_market_type,
  re.reporting_entity_name,
  re.reporting_entity_type,
  re.index_url,
  re.index_sha256
FROM files f
LEFT JOIN file_plans fp ON fp.file_key=f.file_key
LEFT JOIN plans p ON p.plan_key=fp.plan_key
LEFT JOIN reporting_entities re ON re.id=p.reporting_entity_id;
