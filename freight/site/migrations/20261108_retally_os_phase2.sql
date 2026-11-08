-- RETALLY OS private operator state. The authoritative inquiry receipt is never altered.
-- Every table is separate from production intake rate limits and notification state.
CREATE TABLE IF NOT EXISTS retally_os_cases (
  reference TEXT PRIMARY KEY CHECK(reference GLOB 'RA-*'),
  owner TEXT NOT NULL CHECK(length(owner) BETWEEN 1 AND 80),
  due_on TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL CHECK(status IN ('reviewing','qualified','on_hold','closed')),
  note TEXT NOT NULL CHECK(length(note)<=1000),
  version INTEGER NOT NULL DEFAULT 1 CHECK(version>=1),
  updated_by TEXT NOT NULL CHECK(length(updated_by) BETWEEN 3 AND 128),
  updated_at INTEGER NOT NULL CHECK(updated_at>0)
);
CREATE TABLE IF NOT EXISTS retally_os_case_events (
  event_id INTEGER PRIMARY KEY,
  reference TEXT NOT NULL,
  version INTEGER NOT NULL,
  actor TEXT NOT NULL,
  status TEXT NOT NULL,
  occurred_at INTEGER NOT NULL,
  record_digest TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS retally_os_case_events_ref_idx ON retally_os_case_events(reference,event_id);
CREATE TRIGGER IF NOT EXISTS retally_os_case_insert AFTER INSERT ON retally_os_cases BEGIN
  INSERT INTO retally_os_case_events(reference,version,actor,status,occurred_at,record_digest)
  VALUES(NEW.reference,NEW.version,NEW.updated_by,NEW.status,NEW.updated_at,
    hex(NEW.reference||':'||NEW.version||':'||NEW.status||':'||NEW.updated_by));
END;
CREATE TRIGGER IF NOT EXISTS retally_os_case_update AFTER UPDATE ON retally_os_cases BEGIN
  INSERT INTO retally_os_case_events(reference,version,actor,status,occurred_at,record_digest)
  VALUES(NEW.reference,NEW.version,NEW.updated_by,NEW.status,NEW.updated_at,
    hex(NEW.reference||':'||NEW.version||':'||NEW.status||':'||NEW.updated_by));
END;
CREATE TABLE IF NOT EXISTS retally_os_social_drafts (
  draft_id TEXT PRIMARY KEY,
  title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 100),
  body TEXT NOT NULL CHECK(length(body) BETWEEN 1 AND 1800),
  channel TEXT NOT NULL CHECK(channel IN ('facebook','instagram','linkedin','x')),
  status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','reviewed')),
  version INTEGER NOT NULL DEFAULT 1 CHECK(version>=1),
  updated_by TEXT NOT NULL CHECK(length(updated_by) BETWEEN 3 AND 128),
  updated_at INTEGER NOT NULL CHECK(updated_at>0)
);
CREATE TABLE IF NOT EXISTS retally_os_social_events (
  event_id INTEGER PRIMARY KEY,
  draft_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  actor TEXT NOT NULL,
  status TEXT NOT NULL,
  occurred_at INTEGER NOT NULL
);
CREATE TRIGGER IF NOT EXISTS retally_os_social_insert AFTER INSERT ON retally_os_social_drafts BEGIN
  INSERT INTO retally_os_social_events(draft_id,version,actor,status,occurred_at)
  VALUES(NEW.draft_id,NEW.version,NEW.updated_by,NEW.status,NEW.updated_at);
END;
CREATE TRIGGER IF NOT EXISTS retally_os_social_update AFTER UPDATE ON retally_os_social_drafts BEGIN
  INSERT INTO retally_os_social_events(draft_id,version,actor,status,occurred_at)
  VALUES(NEW.draft_id,NEW.version,NEW.updated_by,NEW.status,NEW.updated_at);
END;
