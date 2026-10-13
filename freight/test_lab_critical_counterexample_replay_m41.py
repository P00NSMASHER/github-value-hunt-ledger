"""M41 critical historical-finding analogs: real local signer and SQLite probes.

Synthetic only. These do not re-run original vulnerable revisions or
establish independently reviewed fixes for any prior defects.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from freight.lab_assurance import AssuranceRejected, digest
from freight import lab_critical_counterexample_replay_m41 as m41
from freight.lab_historical_disposition_m40 import _book

TODAY = date(2026, 10, 13)


class CriticalCounterexampleM41Tests(unittest.TestCase):
    def test_four_closed_historical_ids_and_exact_expected_current_denials(self):
        self.assertEqual(m41.FINDING_IDS,
                         ("LAB-P0-01", "LAB-P0-02", "LAB-P0-03", "D-01"))
        self.assertEqual(set(m41.EXPECTED_REJECTIONS), set(m41.FINDING_IDS))
        book = _book()
        observed = {row["id"]: row for row in book["entries"][:26]}
        self.assertTrue(all(observed[k]["severity"] == "CRITICAL"
                            and observed[k]["remediation"] == "OPEN_UNVERIFIED"
                            for k in m41.FINDING_IDS))

    def test_all_four_positive_controls_and_direct_sql_adversarial_attacks(self):
        for fid in m41.FINDING_IDS:
            with self.subTest(finding=fid):
                row = m41.replay_one(fid)
                self.assertEqual(row["historical_finding_id"], fid)
                self.assertEqual(row["positive_control_result"], "PASS_SYNTHETIC_ONLY")
                self.assertEqual(row["positive_control_recovered_cents"], 500)
                self.assertEqual(row["positive_control_earned_fee_cents"], 100)
                self.assertTrue(row["attack_sqlite_differed_from_positive_control"])
                self.assertEqual(row["observed_denial"], m41.EXPECTED_REJECTIONS[fid])
                self.assertEqual(row["expected_independent_verifier_denial"],
                                 row["observed_denial"])
                self.assertEqual(row["historical_disposition"], "OPEN_UNVERIFIED")
                self.assertFalse(row["original_defect_verified_repaired"])
                self.assertFalse(row["original_historical_bug_reproduced_from_pinned_old_revision"])
                self.assertNotEqual(row["test_only_before_database_sha256"],
                                    row["test_only_after_database_sha256"])
                self.assertEqual(len(row["test_only_after_database_sha256"]), 64)

    def test_full_campaign_keeps_original_twenty_six_unverified(self):
        r=m41.run_campaign(as_of=TODAY)
        self.assertEqual(r["scope"], m41.SCOPE)
        self.assertEqual(r["original_lab_number"], 14)
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["current_source_paths_attacked"], 4)
        self.assertEqual(r["current_source_guards_rejected_attack"], 4)
        self.assertEqual([x["historical_finding_id"] for x in r["cases"]],
                         list(m41.FINDING_IDS))
        self.assertEqual(r["historical_original_defects_open"], 26)
        self.assertEqual(r["historical_original_defects_closed"], 0)
        self.assertEqual(r["original_pinned_vulnerable_revisions_replayed"], 0)
        self.assertEqual(r["independent_historical_fix_signoffs"], 0)
        self.assertEqual(r["independent_customer_pilot_controls_unmet"], 18)
        self.assertEqual(r["external_empirical_commercial_claims_approved"], 0)
        self.assertFalse(r["external_customer_or_carrier_authority_established"])
        self.assertFalse(r["production_customer_settlement_data_read"])
        self.assertIsNone(r["actual_recovered_customer_cash_usd"])
        self.assertTrue(r["no_live_external_effects_or_schedule_changes"])
        self.assertEqual(r["receipt_sha256"],
                         digest({k:v for k,v in r.items() if k!="receipt_sha256"}))

    def test_fake_positive_when_attack_not_rejected_is_fatal(self):
        good=SimpleNamespace(
            status="PASS_SYNTHETIC_ONLY",
            scope="SIGNED_SYNTHETIC_EVIDENCE_ONLY",
            verified_claims=1, verified_receipts=2,
            currency_totals={"USD":dict(m41.BASELINE)},
        )
        with patch.object(m41, "_observe", return_value=good):
            with self.assertRaisesRegex(
                ValueError, "M41_CRITICAL_CURRENT_IMPLEMENTATION_ACCEPTED_FORGED_EVIDENCE"
            ):
                m41.replay_one("LAB-P0-01")

    def test_wrong_negative_reason_is_not_treated_as_success(self):
        good=SimpleNamespace(
            status="PASS_SYNTHETIC_ONLY",
            scope="SIGNED_SYNTHETIC_EVIDENCE_ONLY",
            verified_claims=1, verified_receipts=2,
            currency_totals={"USD":dict(m41.BASELINE)},
        )
        with patch.object(m41, "_observe",
                          side_effect=[good,AssuranceRejected("UNRELATED_FAILURE")]):
            with self.assertRaisesRegex(
                ValueError, "M41_WRONG_DENIAL_MECHANISM"
            ):
                m41.replay_one("LAB-P0-03")

    def test_bad_positive_control_cannot_be_used_to_prove_negative(self):
        bad=SimpleNamespace(
            status="PASS_SYNTHETIC_ONLY",
            scope="SIGNED_SYNTHETIC_EVIDENCE_ONLY",
            verified_claims=1, verified_receipts=2,
            currency_totals={"USD":{"recovered_cents":500,
                                    "earned_fee_cents":999,
                                    "collected_fee_cents":100,
                                    "fee_refund_due_cents":0}},
        )
        with patch.object(m41,"_observe",return_value=bad):
            with self.assertRaisesRegex(ValueError,
                                         "M41_POSITIVE_SYNTHETIC_SETTLEMENT_CHAIN_NOT_VERIFIED"):
                m41.replay_one("LAB-P0-02")

    def test_unregistered_cases_and_wrong_identifiers_are_rejected(self):
        for fid in ("LAB-P0-04","Y-02","GATE-001","case-1","",None,123,True):
            with self.subTest(fid=fid):
                with self.assertRaisesRegex(ValueError,
                                              "M41_UNKNOWN_OR_UNCONTROLLED_HISTORICAL_FINDING"):
                    m41.replay_one(fid)

    def test_wrong_historical_registry_status_cannot_promote_original_fixes(self):
        fake=deepcopy(_book())
        fake["entries"][0]["remediation"]="FIXED_AND_PUBLISHED"
        with patch.object(m41,"_book",return_value=fake):
            with self.assertRaisesRegex(ValueError,
                                         "M41_CRITICAL_HISTORICAL_REGISTER_RELABELED"):
                m41.run_campaign(as_of=TODAY)

    def test_a_changed_campaign_date_does_not_approve_fresh_source_data(self):
        for bad in (date(2026,10,12),"2026-10-13",None,True):
            with self.subTest(date=bad):
                with self.assertRaisesRegex(ValueError,"M41_INVALID_RESEARCH_AS_OF_DATE"):
                    m41.run_campaign(as_of=bad)

    def test_report_renders_escaped_and_labels_original_scope(self):
        report=m41.run_campaign(as_of=TODAY)
        modified=deepcopy(report)
        modified["cases"][0]["observed_denial"]="<img src=x onerror=alert(1)>"
        html=m41.render_html(modified)
        self.assertIn("&lt;img",html)
        self.assertNotIn("<img",html)
        self.assertIn("26 remain open",html)
        self.assertIn("not",html.lower())

    def test_cli_writes_read_only_synthetic_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            from unittest.mock import patch as mock_patch
            out=Path(tmp)/"out"
            with mock_patch("sys.argv",[
                "m41","--as-of-date","2026-10-13","--out",str(out),
            ]):
                m41.main()
            j=json.loads((out/"critical_counterexample_replay.json").read_text())
            h=(out/"critical_counterexample_replay.html").read_text()
            self.assertEqual(j["current_source_guards_rejected_attack"],4)
            self.assertEqual(j["historical_original_defects_closed"],0)
            self.assertIn("Four executable critical-case controls",h)
            self.assertFalse(any("TEST-ONLY HMAC key" in k for k in j))

    def test_invalid_date_does_not_create_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"not-made"
            with patch("sys.argv",["m41","--as-of-date","2026-10-12","--out",str(out)]):
                with self.assertRaises(ValueError):
                    m41.main()
            self.assertFalse(out.exists())


if __name__=="__main__":
    unittest.main()
