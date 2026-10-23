-- RETALLY Unified Research: independent scheduled public-source metadata store.
-- NO raw third-party documents, invoices, customer identities, payments, or
-- unverified commercial/ground-truth assertions. Every source is a rights hold.
CREATE TABLE IF NOT EXISTS sources(
  id TEXT PRIMARY KEY CHECK(length(id)=64),
  url TEXT NOT NULL UNIQUE,
  first_seen TEXT NOT NULL,
  rights_state TEXT NOT NULL DEFAULT 'UNVERIFIED_RIGHTS_HOLD'
    CHECK(rights_state='UNVERIFIED_RIGHTS_HOLD'),
  truth_state TEXT NOT NULL DEFAULT 'UNVERIFIED_TRUTH_HOLD'
    CHECK(truth_state='UNVERIFIED_TRUTH_HOLD')
);
CREATE TABLE IF NOT EXISTS source_engines(
  source_id TEXT NOT NULL REFERENCES sources(id),
  lane TEXT NOT NULL CHECK(lane IN
    ('freightrecovery','permitplate','capturebrief','recoveryos')),
  PRIMARY KEY(source_id,lane)
);
CREATE TABLE IF NOT EXISTS lane_health(
  name TEXT PRIMARY KEY CHECK(name IN
    ('freightrecovery','permitplate','capturebrief','recoveryos')),
  last_attempt_ms INTEGER NOT NULL DEFAULT 0,
  last_success_ms INTEGER,
  last_status TEXT NOT NULL DEFAULT 'NEVER'
    CHECK(last_status IN ('NEVER','OK','DEGRADED','FAILED'))
);
CREATE TABLE IF NOT EXISTS runs(
  run_key TEXT PRIMARY KEY,
  lane TEXT NOT NULL CHECK(lane IN
    ('freightrecovery','permitplate','capturebrief','recoveryos')),
  started_ms INTEGER NOT NULL,
  finished_ms INTEGER,
  status TEXT NOT NULL CHECK(status IN ('RUNNING','OK','DEGRADED','FAILED')),
  new_sources INTEGER NOT NULL DEFAULT 0 CHECK(new_sources >= 0),
  feed_errors TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_sources_first_seen ON sources(first_seen);
CREATE INDEX IF NOT EXISTS idx_run_start ON runs(started_ms DESC);
INSERT OR IGNORE INTO lane_health(name) VALUES
 ('freightrecovery'),('permitplate'),('capturebrief'),('recoveryos');
