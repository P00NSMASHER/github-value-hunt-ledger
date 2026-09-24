from dataclasses import replace
import unittest

from recoveryworks.branches.freight_audit import CarrierInvoice, LineItem
from recoveryworks.branches.freight_validation import (
    adversarial_scenarios,
    render_adversarial_validation_markdown,
    run_adversarial_scenario,
    run_adversarial_validation,
)


REQUIRED_SCENARIOS = {
    "clean_invoice",
    "duplicate_fuel",
    "wrong_linehaul_rate",
    "unauthorized_liftgate",
    "unsupported_detention",
    "missed_detention_revenue",
    "mismatched_load_ids",
    "bad_ocr_pod_timestamps",
    "ambiguous_authority",
}


class FreightAdversarialValidationTests(unittest.TestCase):
    def test_matrix_covers_required_adversarial_cases(self):
        scenarios = adversarial_scenarios()
        self.assertEqual(len(scenarios), 9)
        self.assertEqual(
            {item.scenario_id for item in scenarios},
            REQUIRED_SCENARIOS,
        )

    def test_default_matrix_has_zero_false_positives_and_false_negatives(self):
        summary = run_adversarial_validation()

        self.assertEqual(summary.scenario_count, 9)
        self.assertEqual(summary.passed_count, 9)
        self.assertEqual(summary.failed_count, 0)

        self.assertEqual(
            (
                summary.candidate_true_positive,
                summary.candidate_true_negative,
                summary.candidate_false_positive,
                summary.candidate_false_negative,
            ),
            (5, 4, 0, 0),
        )
        self.assertEqual(
            (
                summary.validation_true_positive,
                summary.validation_true_negative,
                summary.validation_false_positive,
                summary.validation_false_negative,
            ),
            (3, 6, 0, 0),
        )

        self.assertEqual(summary.expected_candidate_cents, 102_500)
        self.assertEqual(summary.actual_candidate_cents, 102_500)
        self.assertEqual(summary.candidate_overclaim_cents, 0)
        self.assertEqual(summary.candidate_underdetect_cents, 0)

        self.assertEqual(summary.expected_validated_cents, 62_500)
        self.assertEqual(summary.actual_validated_cents, 62_500)
        self.assertEqual(summary.validated_overclaim_cents, 0)
        self.assertEqual(summary.validated_underdetect_cents, 0)

        self.assertEqual(summary.exact_candidate_dollar_cases, 9)
        self.assertEqual(summary.exact_validated_dollar_cases, 9)
        self.assertEqual(len(summary.suite_hash), 64)

    def test_identity_and_authority_failures_keep_candidate_separate_from_validated(self):
        results = {
            item.scenario_id: item
            for item in run_adversarial_validation().results
        }

        mismatch = results["mismatched_load_ids"]
        self.assertEqual(mismatch.actual_candidate_cents, 20_000)
        self.assertEqual(mismatch.actual_validated_cents, 0)
        self.assertEqual(mismatch.actual_review_cents, 20_000)
        self.assertEqual(mismatch.actual_case_states, ("REVIEW",))
        self.assertEqual(mismatch.actual_integrity_blockers, ("load_id_mismatch",))

        ambiguous = results["ambiguous_authority"]
        self.assertEqual(ambiguous.actual_candidate_cents, 20_000)
        self.assertEqual(ambiguous.actual_validated_cents, 0)
        self.assertEqual(ambiguous.actual_review_cents, 20_000)
        self.assertEqual(
            ambiguous.actual_authority_blockers,
            ("AMBIGUOUS_APPLICABLE_CHARGE_RULE",),
        )

    def test_duplicate_finding_overlap_does_not_inflate_dollars(self):
        result = next(
            item
            for item in run_adversarial_validation().results
            if item.scenario_id == "duplicate_fuel"
        )
        self.assertEqual(result.actual_candidate_cents, 30_000)
        self.assertEqual(result.actual_validated_cents, 30_000)
        self.assertEqual(
            result.actual_supplemental_types,
            ("line_overcharge", "total_mismatch"),
        )

    def test_detention_evidence_failures_do_not_create_broker_recovery(self):
        results = {
            item.scenario_id: item
            for item in run_adversarial_validation().results
        }
        unsupported = results["unsupported_detention"]
        self.assertEqual(unsupported.actual_candidate_cents, 0)
        self.assertEqual(unsupported.actual_validated_cents, 0)
        self.assertEqual(
            unsupported.actual_supplemental_types,
            ("detention_unsupported", "missing_pod"),
        )

        bad_ocr = results["bad_ocr_pod_timestamps"]
        self.assertEqual(bad_ocr.actual_candidate_cents, 0)
        self.assertEqual(
            bad_ocr.actual_integrity_blockers,
            ("bad_pod_data",),
        )

        underbilled = results["missed_detention_revenue"]
        self.assertEqual(underbilled.actual_candidate_cents, 0)
        self.assertEqual(
            underbilled.actual_supplemental_types,
            ("detention_underbilled",),
        )

    def test_harness_measures_false_positive_dollars_separately(self):
        base = next(
            item for item in adversarial_scenarios()
            if item.scenario_id == "clean_invoice"
        )
        mutated = replace(
            base,
            scenario_id="forced_false_positive",
            invoice=CarrierInvoice(
                "INV-FP",
                "LOAD-CLEAN",
                "carrier",
                120_000,
                line_items=[LineItem("Linehaul", 120_000)],
            ),
            expected_candidate_cents=0,
            expected_validated_cents=0,
            expected_case_states=(),
            expected_supplemental_types=("total_mismatch",),
        )
        result = run_adversarial_scenario(mutated)

        self.assertTrue(result.candidate_false_positive)
        self.assertTrue(result.validation_false_positive)
        self.assertEqual(result.candidate_overclaim_cents, 20_000)
        self.assertEqual(result.validated_overclaim_cents, 20_000)
        self.assertFalse(result.passed)

    def test_harness_measures_false_negative_dollars_separately(self):
        base = next(
            item for item in adversarial_scenarios()
            if item.scenario_id == "clean_invoice"
        )
        mutated = replace(
            base,
            scenario_id="forced_false_negative",
            expected_candidate_cents=20_000,
            expected_validated_cents=20_000,
            expected_case_states=("VALIDATED",),
        )
        result = run_adversarial_scenario(mutated)

        self.assertTrue(result.candidate_false_negative)
        self.assertTrue(result.validation_false_negative)
        self.assertEqual(result.candidate_underdetect_cents, 20_000)
        self.assertEqual(result.validated_underdetect_cents, 20_000)
        self.assertFalse(result.passed)

    def test_no_adversarial_case_grants_external_action_or_claims_realized_recovery(self):
        summary = run_adversarial_validation()
        self.assertTrue(
            all(not item.external_action_allowed for item in summary.results)
        )
        self.assertTrue(
            all(not item.realized_recovery_asserted for item in summary.results)
        )

    def test_markdown_keeps_candidate_validation_and_realized_states_separate(self):
        report = render_adversarial_validation_markdown(
            run_adversarial_validation()
        )
        self.assertIn("Candidate detection TP/TN/FP/FN", report)
        self.assertIn("Validation TP/TN/FP/FN", report)
        self.assertIn("Candidate overclaim / under-detection", report)
        self.assertIn("Validated overclaim / under-detection", report)
        self.assertIn("candidate discrepancies", report.lower())
        self.assertIn("realized recovery remain separate states", report)
        self.assertIn("duplicate_fuel — PASS", report)
        self.assertIn("ambiguous_authority — PASS", report)


if __name__ == "__main__":
    unittest.main()
