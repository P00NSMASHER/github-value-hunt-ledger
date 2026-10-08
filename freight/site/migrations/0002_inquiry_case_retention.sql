-- RETALLY Mission 14: controlled inquiry case disposition / guarded retention.
-- ADDITIVE MIGRATION ONLY. DO NOT apply to production without explicit release approval.
-- An inquiry is never safe to purge merely because a provider accepted an email.
-- Migration neither deletes nor alters existing inquiries.
CREATE TABLE IF NOT EXISTS inquiry_case_dispositions (
  reference TEXT PRIMARY KEY REFERENCES inquiries(reference) ON DELETE CASCADE,
  case_state TEXT NOT NULL CHECK (case_state IN ('ACKNOWLEDGED','CLOSED')),
  operator_id TEXT NOT NULL CHECK (length(trim(operator_id)) >= 3),
  acknowledged_at INTEGER NOT NULL CHECK (acknowledged_at > 0),
  closed_at INTEGER,
  legal_hold INTEGER NOT NULL DEFAULT 0 CHECK (legal_hold IN (0,1)),
  hold_reason TEXT CHECK (hold_reason IS NULL OR hold_reason IN
    ('LEGAL','DISPUTE','COMPLIANCE','CUSTOMER_REQUEST','SECURITY_INCIDENT')),
  retention_until INTEGER,
  purge_approved_at INTEGER,
  purge_approved_by TEXT,
  CHECK ((case_state='ACKNOWLEDGED' AND closed_at IS NULL) OR
         (case_state='CLOSED' AND closed_at IS NOT NULL AND closed_at>=acknowledged_at)),
  CHECK (legal_hold=0 OR (hold_reason IS NOT NULL AND purge_approved_at IS NULL)),
  CHECK ((purge_approved_at IS NULL AND purge_approved_by IS NULL) OR
         (purge_approved_at IS NOT NULL AND purge_approved_by IS NOT NULL AND
          length(trim(purge_approved_by)) >= 3 AND purge_approved_by<>operator_id AND
          case_state='CLOSED' AND
          legal_hold=0 AND purge_approved_at>=closed_at AND
          retention_until IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS inquiry_purge_audit (
  reference TEXT PRIMARY KEY,
  purged_at INTEGER NOT NULL,
  approved_at INTEGER NOT NULL,
  approved_by TEXT NOT NULL,
  original_accepted_at INTEGER NOT NULL
);

-- Once a purge has committed, its pseudonymous receipt cannot be silently
-- edited or deleted by a routine data-management query.
CREATE TRIGGER IF NOT EXISTS inquiry_purge_audit_immutable_update
BEFORE UPDATE ON inquiry_purge_audit
BEGIN
  SELECT RAISE(ABORT,'inquiry_purge_audit_immutable');
END;
CREATE TRIGGER IF NOT EXISTS inquiry_purge_audit_immutable_delete
BEFORE DELETE ON inquiry_purge_audit
BEGIN
  SELECT RAISE(ABORT,'inquiry_purge_audit_immutable');
END;

CREATE INDEX IF NOT EXISTS inquiry_case_legal_hold_idx
  ON inquiry_case_dispositions(legal_hold,case_state);

-- A privileged SQL mistake must not erase pending, provider-only, unhandled,
-- legally held, too-young, or unapproved inquiries.
-- The audit insert and deletion occur in the same SQLite transaction.
CREATE TRIGGER IF NOT EXISTS inquiry_require_review_before_delete
BEFORE DELETE ON inquiries
BEGIN
  SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM inquiry_case_dispositions d
     WHERE d.reference=OLD.reference
       AND d.case_state='CLOSED'
       AND d.closed_at IS NOT NULL
       AND d.legal_hold=0
       AND d.purge_approved_at IS NOT NULL
       AND d.purge_approved_at<=CAST(strftime('%s','now') AS INTEGER)
       AND d.closed_at<=CAST(strftime('%s','now') AS INTEGER)
       AND d.purge_approved_by IS NOT NULL
       AND d.retention_until IS NOT NULL
       AND d.retention_until<=CAST(strftime('%s','now') AS INTEGER)
       AND OLD.accepted_at <= CAST(strftime('%s','now') AS INTEGER) - 90*86400
  ) THEN RAISE(ABORT,'inquiry_delete_requires_closed_case_approved_retention_and_no_hold') END;

  INSERT INTO inquiry_purge_audit(
    reference,purged_at,approved_at,approved_by,original_accepted_at
  )
  SELECT OLD.reference,CAST(strftime('%s','now') AS INTEGER),
         d.purge_approved_at,d.purge_approved_by,OLD.accepted_at
    FROM inquiry_case_dispositions d WHERE d.reference=OLD.reference;
END;
