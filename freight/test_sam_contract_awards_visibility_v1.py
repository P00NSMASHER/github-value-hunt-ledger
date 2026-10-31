"""GSA contract-award visibility negative controls (research-only, no API calls).

Official API policy documentation is original; every case below is SYNTHETIC.
These tests verify guard semantics, not CaptureBrief product scoring accuracy.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit
import unittest

PACK = Path(__file__).with_name("fixtures") / "sam_contract_awards_public_visibility_v1.json"


def guard(p):
    """Conservative synthetic research oracle, never a production classifier."""
    kind = p["type"]
    if kind == "award_absence":
        if not p["authenticated"]:
            return "UNKNOWN_NO_AUTHORIZED_SOURCE_QUERY"
        if not p["pagination_complete"]:
            return "UNKNOWN_PARTIAL_PAGINATION"
        if p["funded_and_awarded_dod"] and p["days_since_signed"] < 90:
            return "UNKNOWN_DOD_PUBLIC_REVEAL_WINDOW"
        return "UNKNOWN_ABSENCE_NOT_INDEPENDENT_NEGATIVE"
    if kind == "deleted_absence":
        return ("UNKNOWN_DELETED_LOOKBACK_EXCEEDED"
                if p["months_since_deleted"] > 6
                else "UNKNOWN_DELETION_NOT_INDEPENDENT_NEGATIVE")
    if kind == "piid_family":
        if not p["referenced_idv_present"]:
            return "UNKNOWN_NONUNIQUE_PIID"
        return ("UNKNOWN_MODIFICATIONS_NOT_DISTINCT_BASE_AWARDS"
                if p["modification_rows"] > 1
                else "UNKNOWN_NOT_BANK_CASH")
    if kind == "cross_source":
        return "UNKNOWN_INDEPENDENCE_NOT_PROVED"
    if kind == "date_equivalence":
        return "UNKNOWN_DATE_SIGNED_UNVERIFIED"
    if kind == "third_party_rights":
        return "HOLD_THIRD_PARTY_DATA_REUSE"
    raise ValueError("UNSUPPORTED_SYNTHETIC_PROBE")


class PublicAwardsVisibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK.read_text(encoding="utf-8"))

    def test_first_party_provenance_and_no_original_custody(self):
        p = self.pack
        self.assertEqual(p["schema_version"], 1)
        self.assertEqual(p["source"]["first_party_documentation_url"],
                         "https://open.gsa.gov/api/contract-awards/")
        self.assertEqual(urlsplit(p["source"]["data_api_endpoint"]).hostname,
                         "api.sam.gov")
        self.assertEqual(p["source"]["original_api_calls"], 0)
        self.assertEqual(p["source"]["original_award_records_collected"], 0)
        self.assertIsNone(p["source"]["original_document_response_sha256"])
        self.assertIsNone(p["source"]["original_document_response_byte_length"])
        self.assertEqual(p["source"]["documentation_last_modified_at"],
                         "UNKNOWN_NOT_PUBLISHER_ATTESTED")
        self.assertFalse(p["rights"]["commercial_customer_scoring_authorized"])
        self.assertFalse(p["rights"]["award_data_and_embedded_third_party_commercial_rights_verified"])
        self.assertTrue(p["rights"]["no_api_credentials_or_personal_fields_stored"])

    def test_documented_api_visibility_and_pagination_boundaries(self):
        x = self.pack["documented_limits"]
        self.assertEqual(x["dod_funded_and_awarded_reveal_lag_days"], 90)
        self.assertEqual(x["deleted_contracts_retrievable_lookback_months"], 6)
        self.assertEqual(x["default_search_page_size"], 10)
        self.assertEqual(x["maximum_search_page_size"], 100)
        self.assertEqual(x["maximum_sync_search_rows"], 400000)
        self.assertEqual(x["maximum_async_extract_rows"], 1000000)
        self.assertEqual(x["default_nonfederal_no_role_personal_api_requests_per_day"], 10)
        self.assertFalse(x["missing_public_award_is_independent_negative_label"])
        self.assertFalse(x["obligation_does_not_establish_bank_settlement"] is False)

    def test_all_synthetic_case_expectations_and_independent_holdouts(self):
        cases = self.pack["synthetic_controls"]
        ids = [case["id"] for case in cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(cases), self.pack["quality_and_benchmark"]["synthetic_cases"])
        self.assertTrue(any(c["split"] == "synthetic_holdout" for c in cases))
        self.assertTrue(any(c["split"] == "synthetic_calibration" for c in cases))
        for c in cases:
            with self.subTest(id=c["id"]):
                self.assertTrue(c["id"].startswith("SYN_"))
                self.assertEqual(c["source"], "RESEARCH_AUTHORED_SYNTHETIC_NOT_ORIGINAL_AWARD")
                self.assertIn(c["split"], {"synthetic_holdout", "synthetic_calibration"})
                self.assertIsNone(c["independent_real_label"])
                self.assertEqual(guard(c["probe"]), c["expected_guard"])
                self.assertFalse(c["expected_guard"].startswith("NO_AWARD"))
        summary = self.pack["quality_and_benchmark"]
        self.assertEqual(summary["synthetic_calibration"],
                         sum(c["split"] == "synthetic_calibration" for c in cases))
        self.assertEqual(summary["synthetic_holdout"],
                         sum(c["split"] == "synthetic_holdout" for c in cases))
        self.assertEqual(summary["true_independent_heldout_real_award_labels"], 0)
        self.assertIsNone(summary["real_precision"])
        self.assertIsNone(summary["real_recall"])

    def test_naive_public_absence_false_negative_synthetic_contrast(self):
        misses = [c for c in self.pack["synthetic_controls"]
                  if c["probe"]["type"] == "award_absence"]
        self.assertEqual(len(misses), 6)
        naive_no_award = sum(1 for _ in misses)  # synthetic deliberately unsafe heuristic
        guarded_no_award = sum(guard(c["probe"]) == "NO_AWARD" for c in misses)
        self.assertEqual((naive_no_award, guarded_no_award), (6, 0))
        self.assertEqual(sum(guard(c["probe"]) == "UNKNOWN_DOD_PUBLIC_REVEAL_WINDOW"
                             for c in misses), 2)
        # This is six constructed counterexamples, NOT six real adverse outcomes.

    def test_piid_modification_grouping_and_deletion_limit(self):
        by_id = {c["id"]: c for c in self.pack["synthetic_controls"]}
        self.assertEqual(guard(by_id["SYN_PIID_THREE_MODIFICATIONS"]["probe"]),
                         "UNKNOWN_MODIFICATIONS_NOT_DISTINCT_BASE_AWARDS")
        self.assertEqual(guard(by_id["SYN_PIID_MISSING_REFERENCED_IDV"]["probe"]),
                         "UNKNOWN_NONUNIQUE_PIID")
        self.assertEqual(guard(by_id["SYN_DELETED_7_MONTHS_MISSING"]["probe"]),
                         "UNKNOWN_DELETED_LOOKBACK_EXCEEDED")
        self.assertEqual(guard({"type": "deleted_absence", "months_since_deleted": 3}),
                         "UNKNOWN_DELETION_NOT_INDEPENDENT_NEGATIVE")

    def test_restricted_rights_and_source_lineage_fail_closed(self):
        by_id = {c["id"]: c for c in self.pack["synthetic_controls"]}
        self.assertEqual(guard(by_id["SYN_FPDS_DERIVED_USASPENDING"]["probe"]),
                         "UNKNOWN_INDEPENDENCE_NOT_PROVED")
        self.assertEqual(guard(by_id["SYN_RESTRICTED_PRE_2022_DNB_FIELD"]["probe"]),
                         "HOLD_THIRD_PARTY_DATA_REUSE")
        self.assertFalse(self.pack["rights"]["commercial_customer_scoring_authorized"])
        self.assertEqual(self.pack["quality_and_benchmark"]
                         ["independently_matched_sam_fy2027_notice_to_award_pairs"], 0)
        self.assertEqual(self.pack["quality_and_benchmark"]
                         ["independent_negative_award_outcomes"], 0)


if __name__ == "__main__":
    unittest.main()
