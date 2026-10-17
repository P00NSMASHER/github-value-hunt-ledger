-- RETALLY lead-response evidence gate: additive; run only after 0001, 0002, 0003.
-- No existing inquiry or case is silently marked responded.
-- Evidence digest is a pointer to approved, independently inspected Zoho material;
-- it is NOT a standalone proof that a response was sent or received.
CREATE TABLE IF NOT EXISTS inquiry_response_states (
 reference TEXT PRIMARY KEY REFERENCES inquiries(reference) ON DELETE CASCADE,
 response_state TEXT NOT NULL CHECK(response_state IN ('REPORTED','VERIFIED','WAIVED')),
 responded_at INTEGER,
 reported_by TEXT,
 response_evidence_digest TEXT,
 verified_at INTEGER,
 verified_by TEXT,
 verification_evidence_digest TEXT,
 waived_at INTEGER,
 waived_by TEXT,
 waiver_reason TEXT,
 waiver_evidence_digest TEXT,
 last_action_id TEXT NOT NULL,
 last_action TEXT NOT NULL CHECK(last_action IN ('RECORD_RESPONSE','VERIFY_RESPONSE','WAIVE_RESPONSE')),
 last_actor_sub TEXT NOT NULL,
 last_evidence_digest TEXT NOT NULL,
 last_action_at INTEGER NOT NULL,
 CHECK (
   (response_state='REPORTED' AND responded_at>0 AND length(reported_by)>=3
     AND length(response_evidence_digest)=64 AND verified_at IS NULL
     AND verified_by IS NULL AND waived_at IS NULL AND waived_by IS NULL
     AND last_action='RECORD_RESPONSE')
   OR
   (response_state='VERIFIED' AND responded_at>0 AND verified_at>=responded_at
     AND verified_by<>reported_by AND length(verified_by)>=3
     AND length(response_evidence_digest)=64 AND
     length(verification_evidence_digest)=64 AND waived_at IS NULL
     AND waived_by IS NULL AND last_action='VERIFY_RESPONSE')
   OR
   (response_state='WAIVED' AND responded_at IS NULL AND reported_by IS NULL
     AND response_evidence_digest IS NULL AND verified_at IS NULL
     AND verified_by IS NULL AND waived_at>0 AND length(waived_by)>=3
     AND waiver_reason IN ('SPAM','INVALID_CONTACT','WITHDRAWN','DO_NOT_CONTACT','OUT_OF_SCOPE')
     AND length(waiver_evidence_digest)=64 AND last_action='WAIVE_RESPONSE')
 )
);
CREATE INDEX IF NOT EXISTS inquiry_response_state_idx
 ON inquiry_response_states(response_state,last_action_at);

-- Only an immutable event receipt, not customer content, is retained in this ledger.
CREATE TABLE IF NOT EXISTS inquiry_response_action_audit (
 action_id TEXT PRIMARY KEY,
 reference TEXT NOT NULL,
 action TEXT NOT NULL CHECK(action IN ('RECORD_RESPONSE','VERIFY_RESPONSE','WAIVE_RESPONSE')),
 actor_sub TEXT NOT NULL,
 evidence_digest TEXT NOT NULL,
 occurred_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS inquiry_response_action_idx
 ON inquiry_response_action_audit(reference,occurred_at);

CREATE TRIGGER IF NOT EXISTS inquiry_response_insert_audit
AFTER INSERT ON inquiry_response_states
BEGIN
 INSERT INTO inquiry_response_action_audit(action_id,reference,action,actor_sub,evidence_digest,occurred_at)
 VALUES(NEW.last_action_id,NEW.reference,NEW.last_action,NEW.last_actor_sub,NEW.last_evidence_digest,NEW.last_action_at);
END;
CREATE TRIGGER IF NOT EXISTS inquiry_response_update_audit
AFTER UPDATE ON inquiry_response_states
WHEN NEW.last_action_id IS NOT OLD.last_action_id
BEGIN
 INSERT INTO inquiry_response_action_audit(action_id,reference,action,actor_sub,evidence_digest,occurred_at)
 VALUES(NEW.last_action_id,NEW.reference,NEW.last_action,NEW.last_actor_sub,NEW.last_evidence_digest,NEW.last_action_at);
END;
CREATE TRIGGER IF NOT EXISTS inquiry_response_audit_immutable_update
BEFORE UPDATE ON inquiry_response_action_audit
BEGIN
 SELECT RAISE(ABORT,'inquiry_response_audit_immutable');
END;
CREATE TRIGGER IF NOT EXISTS inquiry_response_audit_immutable_delete
BEFORE DELETE ON inquiry_response_action_audit
BEGIN
 SELECT RAISE(ABORT,'inquiry_response_audit_immutable');
END;

-- A recorded response cannot be rewritten, downgraded, or silently waived.
CREATE TRIGGER IF NOT EXISTS inquiry_response_transition_guard
BEFORE UPDATE ON inquiry_response_states
WHEN NOT (
 OLD.response_state='REPORTED' AND NEW.response_state='VERIFIED'
 AND NEW.responded_at=OLD.responded_at
 AND NEW.reported_by=OLD.reported_by
 AND NEW.response_evidence_digest=OLD.response_evidence_digest
 AND NEW.verified_at>=OLD.responded_at
 AND NEW.verified_by<>OLD.reported_by
 AND NEW.last_action='VERIFY_RESPONSE'
 AND NEW.last_action_id<>OLD.last_action_id
)
BEGIN
 SELECT RAISE(ABORT,'inquiry_response_transition_denied');
END;

-- A response receipt may be removed only with its entire, separately approved inquiry purge.
CREATE TRIGGER IF NOT EXISTS inquiry_response_delete_guard
BEFORE DELETE ON inquiry_response_states
WHEN EXISTS(SELECT 1 FROM inquiries WHERE reference=OLD.reference)
BEGIN
 SELECT RAISE(ABORT,'inquiry_response_delete_denied');
END;
