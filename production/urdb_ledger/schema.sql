PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ingestion_runs (
  id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  stats_json TEXT
);

CREATE TABLE IF NOT EXISTS source_snapshots (
  id INTEGER PRIMARY KEY,
  source_kind TEXT NOT NULL,
  source_version TEXT,
  requested_url TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  byte_count INTEGER NOT NULL,
  blob_relpath TEXT NOT NULL,
  etag TEXT,
  last_modified TEXT,
  UNIQUE(source_kind, requested_url, sha256)
);

CREATE TABLE IF NOT EXISTS releases (
  id INTEGER PRIMARY KEY,
  release_key TEXT NOT NULL UNIQUE,
  commit_sha TEXT,
  commit_date TEXT,
  message TEXT,
  built_utc TEXT,
  source_url TEXT,
  tariff_count INTEGER,
  utility_count INTEGER,
  active_count INTEGER,
  metadata_sha256 TEXT
);

CREATE TABLE IF NOT EXISTS release_files (
  id INTEGER PRIMARY KEY,
  release_id INTEGER NOT NULL REFERENCES releases(id),
  logical_name TEXT NOT NULL,
  source_url TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  byte_count INTEGER NOT NULL,
  blob_relpath TEXT NOT NULL,
  UNIQUE(release_id, logical_name, sha256)
);

CREATE TABLE IF NOT EXISTS tariff_release_observations (
  release_id INTEGER NOT NULL REFERENCES releases(id),
  label TEXT NOT NULL,
  utility TEXT,
  eiaid TEXT,
  name TEXT,
  sector TEXT,
  servicetype TEXT,
  startdate TEXT,
  enddate TEXT,
  supersedes TEXT,
  superseded_by TEXT,
  status TEXT,
  source TEXT,
  uri TEXT,
  fixedchargefirstmeter TEXT,
  mincharge TEXT,
  approved INTEGER,
  is_default INTEGER,
  row_fingerprint TEXT NOT NULL,
  PRIMARY KEY(release_id, label)
);

CREATE INDEX IF NOT EXISTS idx_tariff_obs_label
  ON tariff_release_observations(label);
CREATE INDEX IF NOT EXISTS idx_tariff_obs_utility
  ON tariff_release_observations(utility, name, startdate);

CREATE TABLE IF NOT EXISTS current_tariffs (
  label TEXT PRIMARY KEY,
  utility TEXT,
  eiaid TEXT,
  name TEXT,
  description TEXT,
  sector TEXT,
  servicetype TEXT,
  startdate TEXT,
  enddate TEXT,
  supersedes TEXT,
  superseded_by TEXT,
  status TEXT,
  source TEXT,
  uri TEXT,
  fixedchargefirstmeter TEXT,
  fixedchargeeaaddl TEXT,
  mincharge TEXT,
  annualmincharge TEXT,
  approved INTEGER,
  is_default INTEGER,
  has_energy_rates INTEGER,
  has_demand_rates INTEGER,
  has_flat_demand INTEGER,
  has_coincident_demand INTEGER,
  release_id INTEGER REFERENCES releases(id),
  source_file_sha256 TEXT,
  row_fingerprint TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_current_tariffs_utility
  ON current_tariffs(utility, name, startdate, enddate);
CREATE INDEX IF NOT EXISTS idx_current_tariffs_eia
  ON current_tariffs(eiaid);

CREATE TABLE IF NOT EXISTS tariff_history_edges (
  label TEXT PRIMARY KEY,
  supersedes TEXT,
  superseded_by TEXT,
  chain_root TEXT NOT NULL,
  chain_depth INTEGER NOT NULL,
  cycle_detected INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_history_chain
  ON tariff_history_edges(chain_root, chain_depth);

CREATE TABLE IF NOT EXISTS ingestion_errors (
  id INTEGER PRIMARY KEY,
  occurred_at TEXT NOT NULL,
  stage TEXT NOT NULL,
  source TEXT,
  error_type TEXT NOT NULL,
  detail TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS tariff_effective_ledger AS
SELECT
  t.label,
  t.utility,
  t.eiaid,
  t.name,
  t.description,
  t.sector,
  t.servicetype,
  t.startdate AS effective_from,
  t.enddate AS effective_to,
  t.status,
  t.supersedes,
  t.superseded_by,
  h.chain_root,
  h.chain_depth,
  t.source,
  t.uri,
  t.release_id,
  t.source_file_sha256,
  t.row_fingerprint
FROM current_tariffs t
LEFT JOIN tariff_history_edges h ON h.label=t.label;
