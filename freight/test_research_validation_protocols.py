"""Mission 7: evidence-bound, negative-control study design acceptance tests."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

from freight.research_evidence_gate import canon_hash, run_mission
from freight.research_validation_protocols import (
    BOOK, build_protocol_report, render_html, validate_protocols,
)

AS_OF = date(2026, 10, 10)


def fixtures():
    _, opposition = run_mission(as_of=AS_OF)
    return json.loads(BOOK.read_text(encoding="utf-8")), opposition


class ValidationProtocolTests(unittest.TestCase):
    def test_six_source_bound_methods_are_not_claimed_as_trials(self):
        book, opposition = fixtures()
        self.assertEqual(validate_protocols(book, opposition, as_of=AS_OF), [])
        report = build_protocol_report(as_of=AS_OF, book=book, decisions=opposition)
        self.assertEqual(report["protocol_count"], 6)
        self.assertEqual(report["existing_lab_number"], 14)
        self.assertFalse(report["new_lab_created"])
        self.assertEqual(report["external_studies_executed"], 0)
        self.assertEqual(report["observed_customer_outcomes"], 0)
        self.assertEqual(report["approved_preregistrations"], 0)
        self.assertFalse(report["external_actions_allowed"])
        self.assertFalse(report["public_performance_claims_allowed"])
        self.assertEqual(report["receipt_sha256"], canon_hash({
            k: v for k, v in report.items() if k != "receipt_sha256"
        }))
        self.assertEqual(len({p["study_type"] for p in report["protocols"]}), 6)
        self.assertTrue(all(p["status"] == "DESIGN_REVIEW_REQUIRED_NOT_EXECUTED"
                            and p["actual_sample_count"] == 0
                            and p["can_publish_customer_results"] is False
                            for p in report["protocols"]))

    def test_priorities_follow_existing_evidence_register_not_new_fake_roi(self):
        book, opposition = fixtures()
        r = build_protocol_report(as_of=AS_OF, book=book, decisions=opposition)
        self.assertEqual(r["opposition_receipt_sha256"], opposition["receipt_sha256"])
        self.assertEqual(r["protocol_book_sha256"], canon_hash(book))
        scores = [p["priority_score_ordinal_not_forecast"] for p in r["protocols"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        for p in r["protocols"]:
            decision = next(d for d in opposition["decisions"]
                            if d["id"] == p["decision_id"])
            self.assertEqual(p["source_claim_ids"], decision["claim_ids"])
            self.assertIn("STUDY_PERMISSIONS_AND_DATA_RIGHTS_NOT_GRANTED",
                          p["blocking_gates"])

    def test_forged_permission_never_promotes_study(self):
        book, opposition = fixtures()
        for key in ("preregistration_approved", "threshold_approved",
                    "sample_size_approved", "published_performance_claim",
                    "contact_or_carrier_action_authorized",
                    "financial_action_authorized"):
            bad = deepcopy(book)
            bad["experiments"][0][key] = True
            self.assertTrue(any(key in s for s in
                                validate_protocols(bad, opposition, as_of=AS_OF)),
                            key)

    def test_forged_sample_or_success_must_fail(self):
        book, opposition = fixtures()
        mutations = (
            ("observed_sample_count", 23),
            ("independently_verified_outcomes", 5),
            ("protocol_execution_status", "SUCCEEDED"),
            ("source_data_mode", "CUSTOMER_PRIVATE"),
            ("decision_threshold", 0.9),
            ("sample_size_target", 100),
        )
        for key, value in mutations:
            bad = deepcopy(book)
            bad["experiments"][2][key] = value
            self.assertTrue(validate_protocols(bad, opposition, as_of=AS_OF), key)
            with self.assertRaisesRegex(ValueError, "INVALID_VALIDATION_PROTOCOLS"):
                build_protocol_report(as_of=AS_OF, book=bad, decisions=opposition)

    def test_outcomes_must_be_exact_integer_zero_not_false(self):
        book, opposition = fixtures()
        bad = deepcopy(book)
        bad["experiments"][0]["observed_sample_count"] = False
        self.assertTrue(validate_protocols(bad, opposition, as_of=AS_OF))
        bad = deepcopy(book)
        bad["actual_external_experiments_run"] = False
        self.assertTrue(validate_protocols(bad, opposition, as_of=AS_OF))

    def test_conflicts_with_opposition_claim_dependencies_rejected(self):
        book, opposition = fixtures()
        bad = deepcopy(book)
        bad["experiments"][0]["dependent_claim_ids"] = ["campaign.market.cfs"]
        self.assertIn("research dependencies", "; ".join(
            validate_protocols(bad, opposition, as_of=AS_OF)))

    def test_duplicate_experiment_or_decision_id_rejected(self):
        book, opposition = fixtures()
        bad = deepcopy(book)
        bad["experiments"][1]["experiment_id"] = bad["experiments"][0]["experiment_id"]
        self.assertTrue(validate_protocols(bad, opposition, as_of=AS_OF))
        bad = deepcopy(book)
        bad["experiments"][1]["decision_id"] = bad["experiments"][0]["decision_id"]
        self.assertTrue(validate_protocols(bad, opposition, as_of=AS_OF))

    def test_denominator_and_nonresponse_prevent_cherry_picking(self):
        book, opposition = fixtures()
        for key in ("numerator", "denominator", "formula"):
            bad = deepcopy(book)
            bad["experiments"][3]["primary_metric"][key] = ""
            self.assertTrue(validate_protocols(bad, opposition, as_of=AS_OF), key)
        bad = deepcopy(book)
        bad["experiments"][2]["primary_metric"]["formula"] = "correct / total"
        self.assertIn("zero-denominator", "; ".join(
            validate_protocols(bad, opposition, as_of=AS_OF)))
        bad = deepcopy(book)
        bad["experiments"][3]["missingness_policy"] = ""
        self.assertTrue(validate_protocols(bad, opposition, as_of=AS_OF))

    def test_missing_licenses_adjudication_or_confounders_block_protocol(self):
        book, opposition = fixtures()
        for field in ("required_evidence", "confounders"):
            bad = deepcopy(book)
            bad["experiments"][4][field] = ["one example"]
            self.assertTrue(validate_protocols(bad, opposition, as_of=AS_OF))
        bad = deepcopy(book)
        bad["experiments"][5]["independent_reviewer"] = ""
        self.assertTrue(validate_protocols(bad, opposition, as_of=AS_OF))
        bad = deepcopy(book)
        bad["experiments"][1]["stop_rule"] = ""
        self.assertTrue(validate_protocols(bad, opposition, as_of=AS_OF))

    def test_future_or_fake_top_level_claims_rejected(self):
        book, opposition = fixtures()
        for key, value in (
            ("created_on", "2026-12-25"),
            ("actual_external_experiments_run", 2),
            ("public_performance_claims_authorized", True),
            ("scope", "PRODUCTION_APPROVED"),
        ):
            bad = deepcopy(book)
            bad[key] = value
            self.assertTrue(validate_protocols(bad, opposition, as_of=AS_OF))

    def test_no_missing_sixth_decision_can_pass(self):
        book, opposition = fixtures()
        bad = deepcopy(book)
        bad["experiments"].pop()
        self.assertTrue(validate_protocols(bad, opposition, as_of=AS_OF))
        bad = deepcopy(opposition)
        bad["decisions"].pop()
        self.assertTrue(validate_protocols(book, bad, as_of=AS_OF))

    def test_escaping_and_digest_determinism(self):
        book, opposition = fixtures()
        result_a = build_protocol_report(as_of=AS_OF, book=book, decisions=opposition)
        result_b = build_protocol_report(as_of=AS_OF, book=book, decisions=opposition)
        self.assertEqual(result_a, result_b)
        dirty = deepcopy(result_a)
        dirty["protocols"][0]["title"] = '<script>alert("x")</script>'
        dirty["protocols"][0]["confounders"] = ['<img src=x onerror=alert(1)>']
        html = render_html(dirty)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img ", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("Zero independent customer", html)

    def test_later_date_does_not_revalidate_expired_sources(self):
        report = build_protocol_report(as_of=date(2027, 2, 1))
        self.assertEqual(report["external_studies_executed"], 0)
        self.assertTrue(any("DEPENDENT_SOURCE_OBSERVATIONS_STILL_REQUIRE_REVIEW"
                            in p["blocking_gates"] for p in report["protocols"]))
        self.assertTrue(all(p["can_publish_customer_results"] is False
                            for p in report["protocols"]))


if __name__ == "__main__":
    unittest.main()
