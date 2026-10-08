-- RETALLY Mission 16: verified-origin inquiry case action audit.
-- Stacked on 0002. Nonproduction candidate, apply to isolated D1 only.
-- Adds immutable audit of actions derived from a separately verified Access JWT.
-- SQL itself cannot validate identity: use ONLY the restricted server handler.
ALTER TABLE inquiry_case_dispositions ADD COLUMN last_action_id TEXT;
ALTER TABLE inquiry_case_dispositions ADD COLUMN last_action TEXT;
ALTER TABLE inquiry_case_dispositions ADD COLUMN last_actor_sub TEXT;
ALTER TABLE inquiry_case_dispositions ADD COLUMN last_evidence_digest TEXT;
ALTER TABLE inquiry_case_dispositions ADD COLUMN last_action_at INTEGER;
ALTER TABLE inquiry_case_dispositions ADD COLUMN closed_by TEXT;
ALTER TABLE inquiry_case_dispositions ADD COLUMN hold_by TEXT;

CREATE TABLE IF NOT EXISTS inquiry_case_action_audit (
  action_id TEXT PRIMARY KEY,
  reference TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN
    ('ACKNOWLEDGE','CLOSE','SET_HOLD','RELEASE_HOLD','APPROVE_PURGE')),
  actor_sub TEXT NOT NULL,
  evidence_digest TEXT NOT NULL,
  occurred_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS inquiry_case_action_ref_idx
  ON inquiry_case_action_audit(reference,occurred_at);

CREATE TRIGGER IF NOT EXISTS inquiry_case_audit_insert
AFTER INSERT ON inquiry_case_dispositions
WHEN NEW.last_action_id IS NOT NULL
BEGIN
  INSERT INTO inquiry_case_action_audit
    (action_id,reference,action,actor_sub,evidence_digest,occurred_at)
  VALUES(NEW.last_action_id,NEW.reference,NEW.last_action,
         NEW.last_actor_sub,NEW.last_evidence_digest,NEW.last_action_at);
END;
CREATE TRIGGER IF NOT EXISTS inquiry_case_audit_update
AFTER UPDATE ON inquiry_case_dispositions
WHEN NEW.last_action_id IS NOT NULL AND
     NEW.last_action_id IS NOT OLD.last_action_id
BEGIN
  INSERT INTO inquiry_case_action_audit
    (action_id,reference,action,actor_sub,evidence_digest,occurred_at)
  VALUES(NEW.last_action_id,NEW.reference,NEW.last_action,
         NEW.last_actor_sub,NEW.last_evidence_digest,NEW.last_action_at);
END;
CREATE TRIGGER IF NOT EXISTS inquiry_case_audit_immutable_update
BEFORE UPDATE ON inquiry_case_action_audit
BEGIN
  SELECT RAISE(ABORT,'case_action_audit_immutable');
END;
CREATE TRIGGER IF NOT EXISTS inquiry_case_audit_immutable_delete
BEFORE DELETE ON inquiry_case_action_audit
BEGIN
  SELECT RAISE(ABORT,'case_action_audit_immutable');
END;
