"""Mission 42: exact duplicate-row denials in independent settlement assurance.

All data is synthetic and constructed in temporary SQLite tables lacking PK
constraints to mirror hostile or legacy financial-import conditions.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from freight.lab_assurance import AssuranceRejected, digest
from freight import lab_settlement_identity_m42 as m42

TODAY = date(2026, 10, 13)
EXPECTED = {
    "ALLOCATION": "DUPLICATE_ALLOCATION_ID",
    "COUNTER": "DUPLICATE_COUNTER_ID",
    "REVERSAL": "DUPLICATE_OR_INVALID_REVERSAL_ID",
}


class SettlementIdentityM42Tests(unittest.TestCase):
    def test_three_scopes_are_registered_without_external_data(self):
        self.assertEqual(tuple(x[0] for x in m42.ATTACKS),
                         ("ALLOCATION", "COUNTER", "REVERSAL"))
        self.assertEqual({x[0]: x[4] for x in m42.ATTACKS}, EXPECTED)
        self.assertEqual(m42.EXPECTED_USD["recovered_cents"], 500)
        self.assertEqual(m42.EXPECTED_USD["collected_fee_cents"], 100)

    def test_each_duplicate_can_reach_test_verifier_and_fails_exactly(self):
        for name, rejection in EXPECTED.items():
            with self.subTest(name=name):
                one = m42.replay_one(name)
                self.assertEqual(one["scenario"], name)
                self.assertEqual(one["current_verifier_actual_denial"], rejection)
                self.assertEqual(one["current_verifier_expected_denial"], rejection)
                self.assertTrue(one["positive_control_verified_with_test_only_signers"])
                self.assertTrue(one["negative_case_rejected_exactly"])
                self.assertEqual(one["source_row_observation"]["before_row_count"], 1)
                self.assertEqual(one["source_row_observation"]["after_row_count"], 2)
                self.assertEqual(
                    one["source_row_observation"]["after_distinct_identity_count"], 1
                )
                self.assertTrue(one["source_row_observation"]["actual_duplicate_present_in_disposable_sqlite"])
                self.assertNotEqual(one["isolated_before_sha256"],one["isolated_after_sha256"])
                self.assertFalse(one["historical_vulnerable_revision_replayed"])
                self.assertFalse(one["historical_defect_closed"])
                self.assertFalse(one["real_customer_cash_or_bank_receipt_proven"])

    def test_full_three_attack_campaign_reuses_existing_lab_14(self):
        report = m42.run_campaign(as_of=TODAY)
        self.assertEqual(report["scope"], m42.SCOPE)
        self.assertEqual(report["existing_lab_number"], 14)
        self.assertFalse(report["new_lab_created"])
        self.assertEqual(report["unconstrained_duplicate_row_attacks"], 3)
        self.assertEqual(report["independent_verifier_expected_denials"], 3)
        self.assertEqual(report["historical_original_findings_open"], 26)
        self.assertEqual(report["historical_original_findings_closed"], 0)
        self.assertEqual(report["original_vulnerable_baseline_replays"], 0)
        self.assertEqual(report["separate_human_pilot_controls_unmet"], 18)
        self.assertEqual(report["actual_real_customer_transactions_imported"], 0)
        self.assertIsNone(report["actual_verified_cash_recovered_usd"])
        self.assertEqual(report["external_publication_claims_authorized"], 0)
        self.assertTrue(report["source_tests_are_not_real_bank_or_carrier_attestation"])
        self.assertTrue(report["no_customer_contact_production_deployment_or_schedules"])
        self.assertEqual(report["receipt_sha256"],
                         digest({k: v for k, v in report.items() if k != "receipt_sha256"}))

    def test_wrong_failure_reason_does_not_count_as_negative_proof(self):
        positive = SimpleNamespace(
            status="PASS_SYNTHETIC_ONLY",
            scope="SIGNED_SYNTHETIC_EVIDENCE_ONLY",
            verified_claims=1,verified_receipts=2,
            currency_totals={"USD": m42.EXPECTED_USD},
        )
        with patch.object(m42, "_observe",
                          side_effect=[positive, AssuranceRejected("MISSING_PROVIDER")]):
            with self.assertRaisesRegex(ValueError,"M42_WRONG_DUPLICATE_ROW_REJECTION"):
                m42.replay_one("COUNTER")

    def test_malicious_acceptance_instead_of_rejection_fails_campaign(self):
        positive = SimpleNamespace(
            status="PASS_SYNTHETIC_ONLY",
            scope="SIGNED_SYNTHETIC_EVIDENCE_ONLY",
            verified_claims=1,verified_receipts=2,
            currency_totals={"USD":m42.EXPECTED_USD},
        )
        with patch.object(m42,"_observe",return_value=positive):
            with self.assertRaisesRegex(
                ValueError,"M42_VERIFIER_SILENTLY_ACCEPTED_DUPLICATE_SQLITE_ROWS"
            ):
                m42.replay_one("REVERSAL")

    def test_malformed_positive_control_is_never_waved_through(self):
        bad = SimpleNamespace(
            status="PASS_SYNTHETIC_ONLY",
            scope="SIGNED_SYNTHETIC_EVIDENCE_ONLY",
            verified_claims=1, verified_receipts=2,
            currency_totals={"USD":{**m42.EXPECTED_USD,"recovered_cents":99999}},
        )
        with patch.object(m42,"_observe",return_value=bad):
            with self.assertRaisesRegex(ValueError,"M42_KNOWN_GOOD_SYNTHETIC_SETTLEMENT_REJECTED"):
                m42.replay_one("ALLOCATION")

    def test_invalid_case_ids_cannot_execute_dynamic_sql(self):
        for value in ("allocations","counter_events","foo","",None,0,True,"x'; DROP TABLE"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError,"M42_UNKNOWN_DUPLICATE_SOURCE_SCENARIO"):
                    m42.replay_one(value)

    def test_unknown_sql_attack_cannot_mutate_even_temporary_file(self):
        with tempfile.TemporaryDirectory() as home:
            from freight.test_lab_assurance import populate
            db = Path(home) / "fictional.sqlite3"
            populate(db)
            before=db.read_bytes()
            with self.assertRaisesRegex(ValueError,"M42_UNREGISTERED_IDENTITY_ATTACK"):
                m42._attack(db,"UNREGISTERED")
            self.assertEqual(before,db.read_bytes())

    def test_reversal_split_keeps_same_aggregate_but_duplicate_id(self):
        with tempfile.TemporaryDirectory() as home:
            from freight.test_lab_assurance import populate
            db=Path(home)/"fictional.sqlite3"
            populate(db)
            observed=m42._attack(db,"REVERSAL")
            self.assertEqual(observed["after_row_count"],2)
            with sqlite3.connect(db) as con:
                rows=con.execute(
                    "SELECT amount_cents FROM reversal_edges "
                    "WHERE reversal_id='reversal-500' ORDER BY amount_cents"
                ).fetchall()
            self.assertEqual([x[0] for x in rows],[1,499])
            self.assertEqual(sum(x[0] for x in rows),500)

    def test_null_reversal_id_fails_in_current_verifier(self):
        with tempfile.TemporaryDirectory() as home:
            from freight.test_lab_assurance import populate,assertions_and_fees,BUYER,BU,verifier
            from freight.lab_assurance import verify_settlement
            db=Path(home)/"fictional.sqlite3"
            populate(db)
            with sqlite3.connect(db) as con:
                con.execute("UPDATE reversal_edges SET reversal_id=NULL")
            p,events=assertions_and_fees()
            with self.assertRaises(AssuranceRejected) as raised:
                verify_settlement(db,buyer_id=BUYER,business_unit=BU,
                                  assertions=p,fee_events=events,verifier=verifier())
            self.assertEqual(raised.exception.code,"DUPLICATE_OR_INVALID_REVERSAL_ID")

    def test_unknown_as_of_date_rejected(self):
        for d in (date(2026,10,12),"2026-10-13",None,False):
            with self.subTest(as_of=d), self.assertRaisesRegex(ValueError,"M42_INVALID_AS_OF_DATE"):
                m42.run_campaign(as_of=d)

    def test_html_escaping_and_no_real_cash_claims(self):
        data = m42.run_campaign(as_of=TODAY)
        forged=deepcopy(data)
        forged["cases"][0]["scenario"]="<script>alert(1)</script>"
        text=m42.render_html(forged)
        self.assertNotIn("<script>",text)
        self.assertIn("&lt;script&gt;",text)
        self.assertIn("26 historical findings",text)
        self.assertIn("No real customer",text) if "No real customer" in text else self.assertIn("no ",text.lower())

    def test_cli_report_contains_derived_status_no_customer_data(self):
        with tempfile.TemporaryDirectory() as home:
            root=Path(home)
            target=root/"report"
            with patch("sys.argv",["m42","--as-of-date","2026-10-13","--out",str(target)]):
                m42.main()
            j=json.loads((target/"settlement_identity_m42.json").read_text())
            self.assertEqual(j["unconstrained_duplicate_row_attacks"],3)
            self.assertEqual(j["external_publication_claims_authorized"],0)
            self.assertEqual(j["historical_original_findings_closed"],0)
            self.assertIn("Duplicate financial row identifiers",
                          (target/"settlement_identity_m42.html").read_text())

    def test_cli_invalid_scope_rejects_before_output_directory(self):
        with tempfile.TemporaryDirectory() as home:
            target=Path(home)/"not-created"
            with patch("sys.argv",["m42","--as-of-date","2026-10-12","--out",str(target)]):
                with self.assertRaisesRegex(ValueError,"M42_INVALID_AS_OF_DATE"):
                    m42.main()
            self.assertFalse(target.exists())


if __name__=="__main__":
    unittest.main()
