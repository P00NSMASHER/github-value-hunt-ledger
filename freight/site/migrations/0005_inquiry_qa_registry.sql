-- RETALLY controlled QA register: additive; no customer data deletion or case mutation.
-- The only eligible record is the independently verified owner-run 2026-10-17
-- Turnstile -> D1 -> Resend -> Zoho synthetic test (PR #466).
-- New QA exclusions require a reviewed source change; user-submitted
-- company names, campaign tags or vague "test" text NEVER exclude leads.
CREATE TABLE IF NOT EXISTS inquiry_qa_registry (
 reference TEXT PRIMARY KEY REFERENCES inquiries(reference) ON DELETE CASCADE,
 provenance TEXT NOT NULL CHECK(provenance='OWNER_LIVE_SYNTHETIC_ACCEPTANCE_20261017'),
 evidence_ref TEXT NOT NULL CHECK(evidence_ref='github-value-hunt-ledger#466'),
 tagged_at INTEGER NOT NULL CHECK(tagged_at>0)
);

CREATE TRIGGER IF NOT EXISTS inquiry_qa_registry_known_reference
BEFORE INSERT ON inquiry_qa_registry
WHEN NEW.reference<>'RA-20261017-26F3BC58'
BEGIN
 SELECT RAISE(ABORT,'unreviewed_qa_exclusion_denied');
END;

CREATE TRIGGER IF NOT EXISTS inquiry_qa_registry_immutable_update
BEFORE UPDATE ON inquiry_qa_registry
BEGIN
 SELECT RAISE(ABORT,'qa_provenance_immutable');
END;

-- A normal operator cannot remove the QA marker while its parent inquiry
-- exists; legitimate approved case purges may cascade after the parent deletion.
CREATE TRIGGER IF NOT EXISTS inquiry_qa_registry_immutable_delete
BEFORE DELETE ON inquiry_qa_registry
WHEN EXISTS(SELECT 1 FROM inquiries WHERE reference=OLD.reference)
BEGIN
 SELECT RAISE(ABORT,'qa_provenance_delete_denied');
END;

-- Exact synthetic identity checks stop a coincidental matching reference
-- from being hidden. The migration is safely repeatable, not a bulk UPDATE.
INSERT OR IGNORE INTO inquiry_qa_registry(reference,provenance,evidence_ref,tagged_at)
SELECT reference,'OWNER_LIVE_SYNTHETIC_ACCEPTANCE_20261017',
       'github-value-hunt-ledger#466',CAST(strftime('%s','now') AS INTEGER)
FROM inquiries
WHERE reference='RA-20261017-26F3BC58'
 AND full_name='RETALLY QA TEST'
 AND company_name='RETALLY INTERNAL TEST'
 AND notification_status='delivery_verified';
