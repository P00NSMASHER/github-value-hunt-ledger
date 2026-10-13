"""Lab 14 Mission 37: source lineage revisions must never authorize claims."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from freight import research_source_lineage_m37 as m37
from freight.research_evidence_gate import canon_hash

TODAY = date(2026, 10, 12)
IMPACT = {
    "BEA": {"M35-01", "M35-03", "M35-04", "M35-05", "M35-08"},
    "CENSUS": {"M35-02", "M35-03", "M35-04", "M35-07"},
    "BLS_PPI": {"M35-07", "M35-08"},
    "BLS_SECTORAL": {"M35-06"},
}


class SourceLineageM37(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Once per test class, execute the real M35 and M34 policy + report
        # verification. Later negative cases change only untrusted metadata.
        cls.original = m37._baseline(as_of=TODAY)

    def report(self, candidate=None):
        with patch.object(m37, "_baseline", return_value=self.original):
            return m37.report_shell(as_of=TODAY, candidate=candidate)

    def scenario(self, root, digest="0" * 64):
        return m37.candidate_template(as_of=TODAY, root=root, digest=digest)

    def test_live_frozen_source_reports_still_enforce_all_eighteen_gates(self):
        m35, originals = self.original
        self.assertEqual(set(originals), set(m37.ROOTS))
        self.assertEqual(len(m35["source_claim_registry"]), 16)
        self.assertEqual(m35["independent_customer_pilot_human_approvals_unmet"], 18)
        self.assertEqual(m35["external_commercial_claims_authorized"], 0)
        self.assertTrue(all(len(x) == 64 for x in originals.values()))

    def test_baseline_is_not_falsely_called_a_fresh_publisher_replay(self):
        report = self.report()
        self.assertEqual(report["candidate_sources_submitted"], 0)
        self.assertEqual(report["affected_all_claim_ids_including_pilot_review"], [])
        self.assertEqual(len(report["source_family_status"]), 5)
        self.assertTrue(all(s["status"] == "UNSUBMITTED_NOT_RECHECKED"
                            for s in report["source_family_status"]))
        self.assertFalse(report["source_original_publisher_replay_completed_in_this_run"])
        self.assertFalse(report["report_changes_prove_actual_publisher_revisions"])
        self.assertEqual(report["external_commercial_claims_authorized"], 0)
        self.assertEqual(report["original_pilot_human_signoffs_unmet"], 18)

    def test_source_changes_only_flag_true_metric_lineage_not_all_m34(self):
        for root, expected in IMPACT.items():
            with self.subTest(root=root):
                report = self.report(self.scenario(root))
                self.assertEqual(set(report["affected_internal_source_claim_ids"]), expected)
                self.assertEqual(set(report["affected_all_claim_ids_including_pilot_review"]), expected)
                self.assertTrue(report["all_eight_unsupported_business_claims_still_blocked"])
                self.assertTrue(all(x["external_claims_authorized"] is False
                                    for x in report["claims"]))
                self.assertEqual(report["external_commercial_claims_authorized"], 0)
                self.assertEqual(report["candidate_sources_differing_from_prior_receipt"], [root])

    def test_customer_pilot_candidate_does_not_create_verified_human_evidence(self):
        report = self.report(self.scenario("PILOT"))
        self.assertEqual(len(report["affected_all_claim_ids_including_pilot_review"]), 16)
        self.assertEqual(report["affected_internal_source_claim_ids"], [])
        self.assertEqual(report["original_pilot_human_signoffs_unmet"], 18)
        self.assertTrue(all(x["human_pilot_candidate_changed"] for x in report["claims"]))
        self.assertTrue(all(x["external_status"] == m37.EXTERNAL_VETO
                            for x in report["claims"]))

    def test_nonchanged_candidate_hash_is_not_approval_or_source_replay(self):
        original = self.original[1]["BEA"]
        report = self.report(self.scenario("BEA", original))
        self.assertEqual(report["candidate_sources_with_same_date_bound_receipt"], ["BEA"])
        self.assertEqual(report["candidate_sources_differing_from_prior_receipt"], [])
        self.assertEqual(report["affected_internal_source_claim_ids"], [])
        self.assertFalse(report["source_original_publisher_replay_completed_in_this_run"])

    def test_combined_delta_union_is_deterministic_and_not_double_counted(self):
        candidate = self.scenario("BEA")
        candidate["source_receipts"]["CENSUS"] = "f" * 64
        result = self.report(candidate)
        expected = IMPACT["BEA"] | IMPACT["CENSUS"]
        self.assertEqual(set(result["affected_internal_source_claim_ids"]), expected)
        self.assertEqual(len(result["affected_internal_source_claim_ids"]), len(expected))
        self.assertEqual(result["candidate_sources_differing_from_prior_receipt"],
                         ["BEA", "CENSUS"])
        self.assertEqual(result["claims"][2]["candidate_source_changed"],
                         ["BEA", "CENSUS"])
        self.assertEqual(result["actual_customer_invoices_observed"], 0)

    def test_all_eight_false_business_claims_permanently_blocked_on_every_change(self):
        for source in m37.ROOTS:
            r = self.report(self.scenario(source))
            self.assertEqual([x["claim_id"] for x in r["claims"][8:]],
                             [f"M35-{n:02d}" for n in range(9, 17)])
            self.assertTrue(all(x["internal_status"] == "BLOCKED_UNSUPPORTED_CUSTOMER_INFERENCE"
                                for x in r["claims"][8:]))
            self.assertTrue(all(x["external_claims_authorized"] is False
                                for x in r["claims"]))
            self.assertIsNone(r["recoverable_freight_market_tam_usd"])
            self.assertIsNone(r["real_cash_recovered_usd"])

    def test_reject_claimed_authenticated_publisher_or_customer_or_marketing_approval(self):
        for field in ("original_publisher_replay_verified",
                      "real_customer_evidence_verified", "external_publication_authorized"):
            candidate = self.scenario("BEA")
            candidate[field] = True
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "FALSE_APPROVAL"):
                    self.report(candidate)

    def test_reject_unknown_sources_malformed_digests_and_unregistered_fields(self):
        bad = []
        case = self.scenario("BEA")
        case["source_receipts"]["BEA"] = "a" * 63
        bad.append(case)
        case = self.scenario("BEA")
        case["source_receipts"] = {"PRIVATE_INVOICES": "f" * 64}
        bad.append(case)
        case = self.scenario("BEA")
        case["source_receipts"] = {}
        bad.append(case)
        case = self.scenario("BEA")
        case["source_receipts"]["BEA"] = 123
        bad.append(case)
        case = self.scenario("BEA")
        case["source_receipts"]["CENSUS"] = "0" * 64
        case["unreviewed_customer_invoice_file"] = "secret"
        bad.append(case)
        for candidate in bad:
            with self.subTest(candidate=candidate):
                with self.assertRaises(ValueError):
                    self.report(candidate)

    def test_reject_false_dates_bool_versions_and_scope_drift(self):
        for field, value in [
            ("as_of", "2026-10-13"),
            ("schema_version", True),
            ("schema_version", 2),
            ("scope", "PUBLISHED_AND_VERIFIED"),
            ("original_publisher_replay_verified", 0),
        ]:
            candidate = self.scenario("BEA")
            candidate[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(ValueError, "FALSE_APPROVAL"):
                    self.report(candidate)

    def test_invalid_template_never_allows_undefined_source(self):
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_HYPOTHETICAL"):
            self.scenario("PRIVATE_CUSTOMER")
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_HYPOTHETICAL"):
            m37.candidate_template(as_of=TODAY, root="BEA", digest="bad")

    def test_canonical_receipt_is_local_consistency_not_human_signoff(self):
        report = self.report(self.scenario("BEA"))
        self.assertEqual(report["receipt_sha256"],
                         canon_hash({k: v for k, v in report.items()
                                     if k != "receipt_sha256"}))
        self.assertTrue(report["candidate_input_is_untrusted_metadata_only"])
        self.assertTrue(report["date_bound_receipts_are_not_stable_cross_date_source_content_hashes"])
        self.assertTrue(report["no_source_authorization_or_pilot_status_modified"])
        self.assertTrue(report["no_scheduled_task_or_production_deployment"])

    def test_forged_receipt_alone_does_not_change_output_permissions(self):
        candidate = self.scenario("PILOT")
        candidate["report_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "FALSE_APPROVAL"):
            self.report(candidate)
        clean = self.report(self.scenario("PILOT"))
        clean["external_commercial_claims_authorized"] = 99
        clean["receipt_sha256"] = canon_hash({
            k: v for k, v in clean.items() if k != "receipt_sha256"
        })
        # A forged derived report is NOT an independently signed authorization;
        # all consumer code must independently enforce the M35 human controls.
        self.assertEqual(clean["scope"], m37.SCOPE)

    def test_html_escapes_candidate_strings(self):
        r = self.report()
        forged = deepcopy(r)
        forged["source_family_status"][0]["status"] = "<script>alert(1)</script>"
        html = m37.render_html(forged)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("All 18 independent", html)
        self.assertIn("Zero external", html)

    def test_cli_writes_only_read_only_report_files(self):
        with tempfile.TemporaryDirectory() as dest:
            out = Path(dest)
            case = self.scenario("BLS_SECTORAL")
            sample = out / "candidate.json"
            sample.write_text(json.dumps(case))
            with patch("sys.argv", ["m37", "--as-of-date", TODAY.isoformat(),
                                    "--out", str(out), "--candidate", str(sample)]):
                m37.main()
            data = json.loads((out / "source_change_impact.json").read_text())
            self.assertEqual(data["affected_internal_source_claim_ids"], ["M35-06"])
            self.assertEqual(data["external_commercial_claims_authorized"], 0)
            self.assertIn("source-change blast radius", (out / "source_change_impact.html").read_text())


if __name__ == "__main__":
    unittest.main()
