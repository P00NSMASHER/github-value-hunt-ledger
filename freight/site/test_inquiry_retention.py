"""Mission 14: real SQLite/D1-compatible retention safety regressions (synthetic only)."""
import sqlite3
import time
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent
MIGRATION_1 = (BASE / "migrations/0001_inquiry.sql").read_text()
MIGRATION_2 = (BASE / "migrations/0002_inquiry_case_retention.sql").read_text()
NOW = int(time.time())
DAY = 86400


def connect(with_guard=True):
    db = sqlite3.connect(":memory:")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(MIGRATION_1)
    if with_guard:
        db.executescript(MIGRATION_2)
    return db


def seed(db, ref="RA-20261008-ABCD1234", days_old=91, status="pending"):
    db.execute("""INSERT INTO inquiries
        (reference,idempotency_key,fingerprint,full_name,work_email,company_name,
        annual_spend,modes_json,details_json,accepted_at,notification_status)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (ref, "test-id-" + ref, "fakehash", "Sample", "example@example.org",
         "Sample Company", "$1M-$5M", '["LTL"]', '{}',
         NOW-days_old*DAY, status))
    return ref


def disposition(db, ref, state="CLOSED", hold=False,
                approved=False, until_days_ago=1):
    ack=NOW-30*DAY
    close=NOW-20*DAY if state=="CLOSED" else None
    d=(ref,state,"role:operator-1",ack,close,int(hold),
       "LEGAL" if hold else None,
       NOW-until_days_ago*DAY if until_days_ago is not None else None,
       NOW-2*DAY if approved else None,
       "role:approver-2" if approved else None)
    db.execute("""INSERT INTO inquiry_case_dispositions
        (reference,case_state,operator_id,acknowledged_at,closed_at,legal_hold,
         hold_reason,retention_until,purge_approved_at,purge_approved_by)
        VALUES(?,?,?,?,?,?,?,?,?,?)""",d)


class InquiryRetentionTests(unittest.TestCase):
    def setUp(self):
        self.db=connect()

    def tearDown(self):
        self.db.close()

    def delete(self, ref):
        self.db.execute("DELETE FROM inquiries WHERE reference=?", (ref,))

    def count(self, tab="inquiries"):
        return self.db.execute("SELECT COUNT(*) FROM "+tab).fetchone()[0]

    def assert_blocked(self, ref):
        with self.assertRaisesRegex(sqlite3.IntegrityError,
                                    "inquiry_delete_requires_closed"):
            self.delete(ref)
        self.assertEqual(self.count(),1)
        self.assertEqual(self.count("inquiry_purge_audit"),0)

    def test_original_unconditional_cleanup_would_erase_unresolved(self):
        old=connect(False)
        try:
            seed(old)
            old.execute("DELETE FROM inquiries WHERE accepted_at < ?", (NOW-90*DAY,))
            self.assertEqual(old.execute("SELECT COUNT(*) FROM inquiries").fetchone()[0],0)
        finally:
            old.close()

    def test_additive_migration_preserves_preexisting_unacknowledged_records(self):
        old=connect(False)
        try:
            ref=seed(old)
            old.executescript(MIGRATION_2)
            with self.assertRaises(sqlite3.IntegrityError):
                old.execute("DELETE FROM inquiries WHERE reference=?",(ref,))
            self.assertEqual(old.execute("SELECT COUNT(*) FROM inquiries").fetchone()[0],1)
        finally:
            old.close()

    def test_pending_over_90_days_blocked(self):
        self.assert_blocked(seed(self.db))

    def test_provider_accepted_over_90_days_blocked(self):
        self.assert_blocked(seed(self.db,status="provider_accepted"))

    def test_delivery_verified_but_unhandled_blocked(self):
        self.assert_blocked(seed(self.db,status="delivery_verified"))

    def test_acknowledged_not_closed_blocked(self):
        ref=seed(self.db)
        disposition(self.db,ref,state="ACKNOWLEDGED")
        self.assert_blocked(ref)

    def test_closed_but_no_purge_approval_blocked(self):
        ref=seed(self.db)
        disposition(self.db,ref,approved=False)
        self.assert_blocked(ref)

    def test_legal_hold_blocks_purge_and_forbids_forged_approval(self):
        ref=seed(self.db)
        disposition(self.db,ref,hold=True)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("""UPDATE inquiry_case_dispositions
                SET purge_approved_at=?,purge_approved_by=?
                WHERE reference=?""",(NOW-2*DAY,"role:approver-2",ref))
        self.assert_blocked(ref)

    def test_purge_during_unexpired_retention_blocked(self):
        ref=seed(self.db)
        disposition(self.db,ref,approved=True,until_days_ago=-5)
        self.assert_blocked(ref)

    def test_younger_than_90_days_blocked_even_with_approval(self):
        ref=seed(self.db,days_old=89)
        disposition(self.db,ref,approved=True)
        self.assert_blocked(ref)

    def test_approved_closed_older_case_deleted_with_atomic_pseudonymous_receipt(self):
        ref=seed(self.db)
        disposition(self.db,ref,approved=True)
        self.delete(ref)
        self.assertEqual(self.count(),0)
        rows=self.db.execute("""SELECT reference,approved_by,original_accepted_at
                                FROM inquiry_purge_audit""").fetchall()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][0],ref)
        self.assertEqual(rows[0][1],"role:approver-2")
        self.assertNotIn("example@example.org",str(rows))

    def test_duplicate_purge_approval_and_audit_replay_fail_closed(self):
        ref=seed(self.db)
        disposition(self.db,ref,approved=True)
        self.db.execute("""INSERT INTO inquiry_purge_audit(
            reference,purged_at,approved_at,approved_by,original_accepted_at)
            VALUES(?,?,?,?,?)""",(ref,NOW,NOW-2*DAY,"role:test",NOW-91*DAY))
        with self.assertRaises(sqlite3.IntegrityError):
            self.delete(ref)
        self.assertEqual(self.count(),1)

    def test_bad_closed_state_without_timestamp_cannot_be_admitted(self):
        ref=seed(self.db)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("""INSERT INTO inquiry_case_dispositions
                (reference,case_state,operator_id,acknowledged_at)
                VALUES(?,'CLOSED','role:operator-1',?)""",(ref,NOW))

    def test_operator_hold_requires_structured_reason(self):
        ref=seed(self.db)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("""INSERT INTO inquiry_case_dispositions
                (reference,case_state,operator_id,acknowledged_at,legal_hold)
                VALUES(?,'ACKNOWLEDGED','role:operator-1',?,1)""",(ref,NOW))

    def test_migration_is_idempotent(self):
        self.db.executescript(MIGRATION_2)
        self.assert_blocked(seed(self.db))


if __name__ == "__main__":
    unittest.main(verbosity=2)
