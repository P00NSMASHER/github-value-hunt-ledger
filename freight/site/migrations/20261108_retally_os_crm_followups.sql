-- RETALLY OS owner-only CRM follow-ups. The existing inquiries table remains canonical.
-- No external communication, payment claims, or customer identity copies are created.
-- Deleting an authoritative inquiry via the reviewed privacy-retention process
-- cascades to its follow-up tasks and task events (foreign_keys must remain enabled).
CREATE TABLE IF NOT EXISTS retally_os_tasks (
  task_id TEXT PRIMARY KEY CHECK(length(task_id)=36),
  reference TEXT NOT NULL REFERENCES inquiries(reference) ON DELETE CASCADE,
  title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 140),
  owner TEXT NOT NULL CHECK(length(trim(owner)) BETWEEN 1 AND 80),
  due_on TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','done','cancelled')),
  note TEXT NOT NULL DEFAULT '' CHECK(length(note)<=1000),
  version INTEGER NOT NULL DEFAULT 1 CHECK(version>=1),
  created_by TEXT NOT NULL CHECK(length(created_by) BETWEEN 3 AND 128),
  created_at INTEGER NOT NULL CHECK(created_at>0),
  updated_by TEXT NOT NULL CHECK(length(updated_by) BETWEEN 3 AND 128),
  updated_at INTEGER NOT NULL CHECK(updated_at>0)
);
CREATE INDEX IF NOT EXISTS retally_os_tasks_reference_status_idx
  ON retally_os_tasks(reference,status,due_on);
CREATE INDEX IF NOT EXISTS retally_os_tasks_status_due_idx
  ON retally_os_tasks(status,due_on,updated_at);
CREATE TABLE IF NOT EXISTS retally_os_task_events (
  event_id INTEGER PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES retally_os_tasks(task_id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  actor TEXT NOT NULL,
  status TEXT NOT NULL,
  due_on TEXT NOT NULL,
  occurred_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS retally_os_task_events_task_idx
  ON retally_os_task_events(task_id,event_id);
CREATE TRIGGER IF NOT EXISTS retally_os_task_created
AFTER INSERT ON retally_os_tasks BEGIN
  INSERT INTO retally_os_task_events(task_id,version,actor,status,due_on,occurred_at)
  VALUES(NEW.task_id,NEW.version,NEW.updated_by,NEW.status,NEW.due_on,NEW.updated_at);
END;
CREATE TRIGGER IF NOT EXISTS retally_os_task_updated
AFTER UPDATE ON retally_os_tasks BEGIN
  INSERT INTO retally_os_task_events(task_id,version,actor,status,due_on,occurred_at)
  VALUES(NEW.task_id,NEW.version,NEW.updated_by,NEW.status,NEW.due_on,NEW.updated_at);
END;
