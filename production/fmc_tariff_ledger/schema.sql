PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS crawl_runs (
  id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  directory_fetched_at TEXT,
  shard_index INTEGER NOT NULL DEFAULT 0,
  shard_count INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL,
  stats_json TEXT
);

CREATE TABLE IF NOT EXISTS entities (
  id INTEGER PRIMARY KEY,
  entity_class TEXT NOT NULL,
  organization_no TEXT NOT NULL,
  legal_name TEXT NOT NULL,
  trade_name TEXT NOT NULL DEFAULT '',
  active INTEGER NOT NULL,
  UNIQUE(entity_class, organization_no, legal_name, trade_name, active)
);

CREATE TABLE IF NOT EXISTS tariff_locations (
  id INTEGER PRIMARY KEY,
  entity_id INTEGER NOT NULL REFERENCES entities(id),
  canonical_url TEXT NOT NULL,
  directory_url TEXT NOT NULL,
  directory_snapshot_sha256 TEXT,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  UNIQUE(entity_id, canonical_url)
);

CREATE TABLE IF NOT EXISTS snapshots (
  id INTEGER PRIMARY KEY,
  tariff_location_id INTEGER NOT NULL REFERENCES tariff_locations(id),
  requested_url TEXT NOT NULL,
  final_url TEXT,
  fetched_at TEXT NOT NULL,
  http_status INTEGER,
  content_type TEXT,
  byte_count INTEGER NOT NULL DEFAULT 0,
  sha256 TEXT,
  blob_relpath TEXT,
  parser_status TEXT NOT NULL,
  title TEXT,
  source_version TEXT,
  effective_from TEXT,
  effective_to TEXT,
  UNIQUE(tariff_location_id, requested_url, sha256)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_sha ON snapshots(sha256);
CREATE INDEX IF NOT EXISTS idx_snapshots_effective ON snapshots(effective_from, effective_to);

CREATE TABLE IF NOT EXISTS terms (
  id INTEGER PRIMARY KEY,
  snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
  entity_class TEXT NOT NULL,
  organization_no TEXT NOT NULL,
  legal_name TEXT NOT NULL,
  rule_type TEXT NOT NULL,
  term_kind TEXT NOT NULL,
  amount_value TEXT,
  currency TEXT,
  unit TEXT,
  quantity_value TEXT,
  effective_from TEXT,
  effective_to TEXT,
  source_version TEXT,
  evidence_locator TEXT,
  evidence_excerpt TEXT NOT NULL,
  confidence REAL NOT NULL,
  parser_version TEXT NOT NULL DEFAULT 'fmc-ledger-v2',
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_terms_rule_effective
  ON terms(organization_no, rule_type, effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_terms_snapshot ON terms(snapshot_id);

-- A persistent crawl may rediscover an unchanged snapshot. Preserve one normalized
-- term per snapshot/parser/evidence tuple rather than multiplying identical rows.
CREATE UNIQUE INDEX IF NOT EXISTS idx_terms_stable_dedupe
ON terms(
  snapshot_id,
  parser_version,
  rule_type,
  term_kind,
  COALESCE(amount_value, ''),
  COALESCE(currency, ''),
  COALESCE(unit, ''),
  COALESCE(quantity_value, ''),
  COALESCE(effective_from, ''),
  COALESCE(effective_to, ''),
  COALESCE(source_version, ''),
  COALESCE(evidence_locator, ''),
  evidence_excerpt
);

CREATE TRIGGER IF NOT EXISTS terms_ignore_stable_duplicate
BEFORE INSERT ON terms
WHEN EXISTS (
  SELECT 1 FROM terms x
  WHERE x.snapshot_id = NEW.snapshot_id
    AND x.parser_version = COALESCE(NEW.parser_version, 'fmc-ledger-v2')
    AND x.rule_type = NEW.rule_type
    AND x.term_kind = NEW.term_kind
    AND COALESCE(x.amount_value, '') = COALESCE(NEW.amount_value, '')
    AND COALESCE(x.currency, '') = COALESCE(NEW.currency, '')
    AND COALESCE(x.unit, '') = COALESCE(NEW.unit, '')
    AND COALESCE(x.quantity_value, '') = COALESCE(NEW.quantity_value, '')
    AND COALESCE(x.effective_from, '') = COALESCE(NEW.effective_from, '')
    AND COALESCE(x.effective_to, '') = COALESCE(NEW.effective_to, '')
    AND COALESCE(x.source_version, '') = COALESCE(NEW.source_version, '')
    AND COALESCE(x.evidence_locator, '') = COALESCE(NEW.evidence_locator, '')
    AND x.evidence_excerpt = NEW.evidence_excerpt
)
BEGIN
  SELECT RAISE(IGNORE);
END;

CREATE TABLE IF NOT EXISTS crawl_errors (
  id INTEGER PRIMARY KEY,
  tariff_location_id INTEGER,
  url TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  stage TEXT NOT NULL,
  error_type TEXT NOT NULL,
  detail TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS carrier_rule_effective_ledger AS
SELECT
  e.entity_class,
  e.organization_no,
  e.legal_name,
  e.trade_name,
  tl.canonical_url AS tariff_location,
  s.requested_url AS evidence_url,
  s.final_url,
  s.sha256 AS source_sha256,
  s.fetched_at,
  COALESCE(t.effective_from, s.effective_from) AS effective_from,
  COALESCE(t.effective_to, s.effective_to) AS effective_to,
  COALESCE(t.source_version, s.source_version) AS source_version,
  t.rule_type,
  t.term_kind,
  t.amount_value,
  t.currency,
  t.unit,
  t.quantity_value,
  t.confidence,
  t.parser_version,
  t.evidence_locator,
  t.evidence_excerpt
FROM terms t
JOIN snapshots s ON s.id = t.snapshot_id
JOIN tariff_locations tl ON tl.id = s.tariff_location_id
JOIN entities e ON e.id = tl.entity_id;
