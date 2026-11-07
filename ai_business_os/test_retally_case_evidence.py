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

    def test_dispositions_record_actor_and_preserve_stage_hold_and_evidence(self):
        with self.db:
            self.db.execute("INSERT INTO identity VALUES(1,'synthetic','fixture','local',2)")
        desk.update_task(self.db, self.ref, "Case owner", "2026-11-07", "Await agreement")
        for action, outcome in (("decline", "declined"), ("cancel", "canceled"), ("dispute", "disputed")):
            with self.subTest(action=action):
                self.assertEqual(desk.case_disposition(self.db, self.ref), "active")
                self.assertEqual(desk.set_disposition(self.db, self.ref, action, "Synthetic review",
                                 actor="Operator", expected="active"), outcome)
                with self.assertRaises(ValueError):
                    desk.set_disposition(self.db, self.ref, action, "Repeated request", actor="Operator", expected="active")
                self.assertIn("reopening", desk.next_action("inquiry", "Await agreement", outcome))
                self.assertEqual(desk.set_disposition(self.db, self.ref, "reopen", "Reviewed",
                                 actor="Second operator", expected=outcome), "active")
        case = self.db.execute("SELECT stage,hold,owner FROM pilot_cases").fetchone()
        self.assertEqual(tuple(case), ("inquiry", "Await agreement", "Case owner"))
        self.assertIn("Await agreement", desk.next_action(case["stage"], case["hold"]))
        trail = self.db.execute("SELECT action,detail FROM case_events WHERE action IN "
                                "('decline','cancel','dispute','reopen') ORDER BY seq").fetchall()
        self.assertEqual([row[0] for row in trail], ["decline","reopen","cancel","reopen","dispute","reopen"])
        self.assertEqual(json.loads(trail[0][1]), {"actor":"Operator","reason":"Synthetic review",
                                                   "from":"active","to":"declined","stage":"inquiry"})
        self.assertEqual(json.loads(trail[-1][1])["actor"], "Second operator")
        # Reopening neither clears an independent hold nor supplies missing evidence.
        with self.assertRaises(ValueError):
            desk.advance(self.db, self.ref, "qualified")
        desk.update_task(self.db, self.ref, "Case owner", "2026-11-07", "")
        with self.assertRaises(ValueError):
            desk.advance(self.db, self.ref, "qualified")
        desk.add_artifact(self.db, self.ref, "fit", self.label)
        desk.set_disposition(self.db, self.ref, "dispute", "Open dispute", actor="Operator", expected="active")
        with self.assertRaises(ValueError):
            desk.advance(self.db, self.ref, "qualified")

    def test_dispositions_require_synthetic_binding_and_operator_reason(self):
        with self.assertRaises(ValueError):
            desk.set_disposition(self.db, self.ref, "dispute", "Test", actor="Operator", expected="active")
        with self.db:
            self.db.execute("INSERT INTO identity VALUES(1,'synthetic','fixture','local',2)")
        for action, reason, actor in (("dispute", "", "Operator"), ("dispute", "Test", ""), ("reopen", "Test", "Op")):
            with self.subTest(action=action), self.assertRaises(ValueError):
                desk.set_disposition(self.db, self.ref, action, reason, actor=actor, expected="active")
        self.assertEqual(desk.case_disposition(self.db, self.ref), "active")

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
