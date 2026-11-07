"""Prevent unverified cash, delivery and conflicting evidence from becoming pilot facts."""

import hashlib
import json
import sqlite3
import unittest

from ai_business_os import retally_case_desk as desk
from ai_business_os.retally_inquiry_sync import SCHEMA


class CaseEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA + desk.SCHEMA)
        self.ref = "RA-20261107-ABCD1234"
        self.account = "account:fixture"
        self.label = {"fixture": True, "reference": self.ref}
        self.db.execute(
            "INSERT INTO delivery(seq,reference,fingerprint,service,accepted_at,phase) "
            "VALUES(1,?,'fingerprint','freight',1,'done')",
            (self.ref,),
        )
        desk.open_case(self.db, self.ref, self.account, "Pilot owner", "2026-11-07")

    def legacy_row(self, kind, content):
        raw = json.dumps(content)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        with self.db:
            self.db.execute("INSERT INTO case_artifacts VALUES(?,?,?,?)", (self.ref, kind, digest, raw))
        return digest

    def test_terminal_transitions_reject_even_previously_saved_receipts(self):
        receipt = dict(self.label, customer_delivery_verified=False)
        with self.assertRaises(ValueError):
            desk.add_artifact(self.db, self.ref, "delivery_receipt", receipt)
        self.legacy_row("delivery_receipt", receipt)
        with self.db:
            self.db.execute("UPDATE pilot_cases SET stage='quality-reviewed' WHERE reference=?", (self.ref,))
        with self.assertRaises(ValueError):
            desk.advance(self.db, self.ref, "delivered")
        self.assertEqual(self.db.execute("SELECT stage FROM pilot_cases").fetchone()[0], "quality-reviewed")
        with self.assertRaises(ValueError):
            desk.customer_register(self.db)

    def test_only_unfunded_usd_receipt_collection_is_supported(self):
        good = dict(self.label, currency="USD", receipts=[], collected_cents=0)
        for change in (
            {"collected_cents": 99999},
            {"currency": "EUR"},
            {"receipts": ["unverified"]},
            {"collected_cents": False},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                desk.add_artifact(self.db, self.ref, "fee_receipts", dict(good, **change))
        stamp = desk.add_artifact(self.db, self.ref, "fee_receipts", good)
        digest, evidence = desk.case_evidence(self.db, self.account, self.ref, "fee_receipts")
        self.assertEqual((digest, desk.collected_fee_cents(evidence)), (stamp, 0))
        invalid = self.legacy_row("fee_receipts", dict(good, currency="EUR", collected_cents=99999))
        with self.assertRaises(ValueError):
            desk.case_artifact(self.db, self.account, self.ref, "fee_receipts", invalid)
        with self.assertRaisesRegex(ValueError, "conflicting"):
            desk.case_evidence(self.db, self.account, self.ref, "fee_receipts")
        with self.assertRaises(ValueError):
            desk.case_evidence(self.db, "account:other", self.ref, "fee_receipts")


if __name__ == "__main__":
    unittest.main()
