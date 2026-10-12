"""Adversarial tests for same-population head-to-head benchmarking.

Run by the existing unittest-based Freight CI. No real customer/vendor data.
"""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from freight.test_audit_acceptance import _pilot, _refresh_hashes
from freight.vendor_head_to_head import (
    ComparisonInvalid, VENDORS, compare_vendor_study,
)

POLICY = json.loads(
    (Path(__file__).resolve().parent / "AUDIT_ACCEPTANCE_POLICY_V2.json").read_text("utf-8")
)


def _entry(vendor="RecoveryOS", *, source_kind="SYNTHETIC_TEST", pilot=None):
    packet = deepcopy(pilot if pilot is not None else _pilot())
    packet["roles"]["recoveryos_operator_id"] = "operator:" + vendor
    return {
        "vendor": vendor,
        "source_kind": source_kind,
        "output_receipt_sha256": ("a" if vendor == "RecoveryOS" else "b") * 64,
        "pilot": packet,
    }


def _study(*entries, study_kind="SYNTHETIC"):
    return {"schema_version": 1, "study_kind": study_kind, "submissions": list(entries)}


class HeadToHeadTests(unittest.TestCase):
    def test_missing_competitors_never_become_failed_scores(self):
        report = compare_vendor_study(_study(_entry()), POLICY)
        self.assertEqual(report["observed_vendor_count"], 1)
        self.assertEqual(len(report["missing_vendors"]), 5)
        self.assertEqual(report["comparison_status"], "INCOMPLETE_VENDOR_COVERAGE")
        self.assertFalse(report["market_best_product_proven"])
        self.assertFalse(report["source_code_access_inferred"])
        self.assertFalse(report["verified_realized_recovery"])
        self.assertEqual(report["sample_leaders_if_independently_proven"], [])
        self.assertEqual(len(report["vendor_results"]), 1)
        self.assertEqual(report["vendor_results"][0]["vendor"], "RecoveryOS")

    def test_no_vendor_output_is_explicitly_not_evidence_of_failure(self):
        report = compare_vendor_study(_study(), POLICY)
        self.assertEqual(report["comparison_status"], "NO_VENDOR_MEASUREMENTS")
        self.assertEqual(report["observed_vendor_count"], 0)
        self.assertEqual(report["missing_vendors"], list(VENDORS))
        self.assertEqual(report["vendor_results"], [])

    def test_identical_frozen_truth_allows_neutral_sample_comparison(self):
        report = compare_vendor_study(
            _study(_entry(), _entry("Loop")), POLICY
        )
        self.assertEqual(report["observed_vendor_count"], 2)
        self.assertEqual(report["comparison_status"], "INCOMPLETE_VENDOR_COVERAGE")
        expected_exact = 220
        for item in report["vendor_results"]:
            self.assertEqual(item["exactness"]["fully_correct_invoice_amount_cases"],
                             expected_exact)
            self.assertEqual(item["exactness"]["adjudicated_cases"], 240)
            self.assertEqual(item["exactness"]["review_on_adjudicated_cases"], 20)

    def test_false_positive_is_not_laundered_into_good_score(self):
        competitor = _entry("Loop")
        case = competitor["pilot"]["cases"][60]
        self.assertEqual(case["truth_label"], "NEGATIVE")
        case.update(
            predicted_label="POSITIVE", predicted_variance_cents=10_000,
            predicted_net_new_cents=10_000,
        )
        _refresh_hashes(competitor["pilot"])
        result = compare_vendor_study(
            _study(_entry(), competitor), POLICY
        )
        comparison = {r["vendor"]: r for r in result["vendor_results"]}
        self.assertEqual(comparison["Loop"]["classification"]["false_positive"], 1)
        self.assertEqual(
            comparison["Loop"]["exactness"]["fully_correct_invoice_amount_cases"], 219
        )
        self.assertEqual(comparison["RecoveryOS"]["classification"]["false_positive"], 0)
        self.assertNotEqual(
            comparison["RecoveryOS"]["exactness"]["end_to_end_exact_rate"],
            comparison["Loop"]["exactness"]["end_to_end_exact_rate"],
        )
        self.assertFalse(result["market_best_product_proven"])

    def test_different_frozen_truth_is_rejected_even_with_resigned_hash(self):
        competitor = _entry("Loop")
        competitor["pilot"]["cases"][0]["truth_variance_cents"] += 1
        _refresh_hashes(competitor["pilot"])
        with self.assertRaisesRegex(ComparisonInvalid, "identical frozen"):
            compare_vendor_study(_study(_entry(), competitor), POLICY)

    def test_different_sample_selection_is_rejected(self):
        competitor = _entry("Loop")
        competitor["pilot"]["cases"][0]["case_id"] = "different-case"
        _refresh_hashes(competitor["pilot"])
        with self.assertRaisesRegex(ComparisonInvalid, "identical frozen"):
            compare_vendor_study(_study(_entry(), competitor), POLICY)

    def test_output_tampering_without_hash_update_is_rejected(self):
        competitor = _entry("Loop")
        competitor["pilot"]["cases"][0]["predicted_variance_cents"] = 1234
        with self.assertRaisesRegex(ComparisonInvalid, "invalid or unverified"):
            compare_vendor_study(_study(_entry(), competitor), POLICY)

    def test_blindness_violation_rejects_submission(self):
        competitor = _entry("Loop")
        competitor["pilot"]["blindness"]["truth_owner_saw_recoveryos_before_truth_freeze"] = True
        with self.assertRaisesRegex(ComparisonInvalid, "invalid or unverified"):
            compare_vendor_study(_study(_entry(), competitor), POLICY)

    def test_different_population_hash_is_rejected(self):
        competitor = _entry("Loop")
        competitor["pilot"]["population"]["population_hash"] = "a" * 64
        base = _entry()
        base["pilot"]["population"]["population_hash"] = "c" * 64
        with self.assertRaisesRegex(ComparisonInvalid, "identical frozen"):
            compare_vendor_study(_study(base, competitor), POLICY)

    def test_different_study_cutoff_is_rejected(self):
        competitor = _entry("Loop")
        competitor["pilot"]["timeline"]["joint_unseal_at"] = "2026-10-05T00:00:00Z"
        with self.assertRaisesRegex(ComparisonInvalid, "identical frozen"):
            compare_vendor_study(_study(_entry(), competitor), POLICY)

    def test_duplicate_and_imposter_vendors_are_rejected(self):
        for vendor_entries in (
            (_entry(), _entry()),
            (_entry(), _entry("Some Other Logistics Vendor")),
        ):
            with self.subTest(vendors=[x["vendor"] for x in vendor_entries]):
                with self.assertRaisesRegex(ComparisonInvalid, "duplicate vendor|unsupported"):
                    compare_vendor_study(_study(*vendor_entries), POLICY)

    def test_pretend_private_or_marketing_sources_cannot_enter_benchmark(self):
        invalid = _entry()
        invalid["source_kind"] = "SCRAPED_PROPRIETARY_REPOSITORY"
        with self.assertRaisesRegex(ComparisonInvalid, "source kind"):
            compare_vendor_study(_study(invalid), POLICY)

    def test_unverified_synthetic_cannot_be_turned_into_buyer_blind_evidence(self):
        with self.assertRaisesRegex(ComparisonInvalid, "synthetic output"):
            compare_vendor_study(
                _study(_entry(), study_kind="BUYER_AUTHORIZED_BLIND"), POLICY
            )

    def test_all_vendor_synthetic_rehearsal_never_claims_market_leader(self):
        results = compare_vendor_study(
            _study(*(_entry(v) for v in VENDORS)), POLICY
        )
        self.assertEqual(results["comparison_status"], "SYNTHETIC_REHEARSAL_ONLY")
        self.assertEqual(results["missing_vendors"], [])
        self.assertEqual(results["observed_vendor_count"], 6)
        self.assertFalse(results["market_best_product_proven"])
        self.assertEqual(results["sample_leaders_if_independently_proven"], [])

    def test_real_output_packet_is_still_not_universal_product_claim(self):
        results = compare_vendor_study(_study(
            *(_entry(v, source_kind="AUTHORIZED_VENDOR_DEMO") for v in VENDORS),
            study_kind="BUYER_AUTHORIZED_BLIND",
        ), POLICY)
        self.assertEqual(results["comparison_status"], "SAMPLE_COMPARISON_READY")
        self.assertEqual(set(results["sample_leaders_if_independently_proven"]), set(VENDORS))
        self.assertFalse(results["market_best_product_proven"])
        self.assertFalse(results["verified_realized_recovery"])

    def test_invalid_receipt_sha_is_rejected(self):
        r = _entry()
        r["output_receipt_sha256"] = "signature-unknown"
        with self.assertRaisesRegex(ComparisonInvalid, "SHA-256"):
            compare_vendor_study(_study(r), POLICY)

    def test_sensitive_case_ids_are_not_exposed_in_aggregate(self):
        entry = _entry()
        secret = "private-customer-invoice-28402"
        entry["pilot"]["cases"][0]["case_id"] = secret
        _refresh_hashes(entry["pilot"])
        report = compare_vendor_study(_study(entry), POLICY)
        serialized = json.dumps(report, sort_keys=True)
        self.assertNotIn(secret, serialized)
        self.assertNotIn("economic_issue_id", serialized)
        self.assertNotIn("case-", serialized)

    def test_bad_schema_unknown_kind_and_invalid_list_rejected(self):
        for study in (
            {"schema_version": 3, "study_kind": "SYNTHETIC", "submissions": []},
            {"schema_version": 1, "study_kind": "UNKNOWN", "submissions": []},
            {"schema_version": 1, "study_kind": "SYNTHETIC", "submissions": {}},
            {"schema_version": 1, "study_kind": "SYNTHETIC",
             "submissions": [_entry()] * 7},
        ):
            with self.subTest(study=str(study.get("study_kind"))):
                with self.assertRaises(ComparisonInvalid):
                    compare_vendor_study(study, POLICY)


if __name__ == "__main__":
    unittest.main()
