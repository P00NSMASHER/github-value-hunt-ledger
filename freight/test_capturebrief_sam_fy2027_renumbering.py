"""Source-bound FY2027 SAM.gov renumbering regression; no live scoring claim."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

FIXTURE = (Path(__file__).with_name("fixtures") /
           "capturebrief_sam_fy2027_renumbering_candidate_v0.json")


def validate_candidate(data: dict) -> None:
    """Reject a publisher notice being promoted to two awards or a live RFP."""
    source = data["source"]
    facts = data["published_update_facts"]
    quality = data["quality_and_ground_truth"]
    if (data["schema_version"] != "0.1.0"
            or data["engine"] != "capturebrief"
            or data["evaluation_family"]
                != "GOVERNMENT_PROCUREMENT_NOTICE_IDENTITY_ASOF_NOT_AWARD_SCORING"
            or source["official_notice_url"]
                != "https://sam.gov/opp/f62daacc86a04009b67fd9c9aeabb6b2/view"
            or source["notice_record_uuid"] != "f62daacc86a04009b67fd9c9aeabb6b2"
            or source["published_notice_number"] != "N00024-26-R-4444"
            or source["reported_planned_fy2027_rfp_number"] != "N00024-27-R-4444"
            or source["notice_type"] != "PRESOLICITATION"
            or source["original_publication_date"] != "2026-06-30"
            or source["publisher_administrative_update_date"] != "2026-09-28"
            or source["publisher_response_due_date"] != "2026-10-13"
            or source["publisher_nominal_inactive_date"] != "2026-10-28"
            or source["original_publisher_http_bytes_acquired"] is not False
            or source["original_publisher_http_sha256"] is not None
            or source["dataset_specific_commercial_reuse_rights_verified"] is not False
            or source["source_admission"] != "HOLD_PENDING_ORIGINAL_RESPONSE_AND_PROVIDER_TERMS"
            or facts["fy2027_renumbering_described_by_publisher"] is not True
            or facts["formal_rfp_was_still_planned_as_of_publisher_update"] is not True
            or facts["new_fy2027_rfp_posting_verified_as_of_research_date"] is not False
            or facts["current_formal_rfp_status"] != "UNKNOWN"
            or facts["two_independent_contract_awards_proven"] is not False
            or facts["award_date"] is not None
            or facts["independently_confirmed_current_response_acceptance"] != "UNKNOWN"
            or facts["fy2027_rfp_is_not_a_second_published_award_from_this_notice"] is not True
            or quality["independently_held_out_labeled_notice_lifecycle_cases"] != 0
            or quality["independent_award_labels"] != 0
            or quality["independent_bid_eligibility_labels"] != 0
            or quality["later_new_number_status_checked_with_original_live_response"] is not False
            or quality["current_bid_eligibility"] != "UNKNOWN"
            or quality["commercial_capturebrief_scoring_validated"] is not False
            or data["handoff"]["engine_code_changed"] is not False
            or data["handoff"]["release_approved"] is not False):
        raise ValueError("UNVERIFIED_SAM_FY2027_RFP_OR_AWARD_PROMOTION")
    controls = data["synthetic_negative_controls"]
    if (len(controls) != 5
            or len({x["id"] for x in controls}) != 5
            or not all(x["kind"] == "SYNTHETIC"
                           and x["id"].startswith("SYNTH_")
                           and x["expected"].startswith("REJECT_")
                           for x in controls)):
        raise ValueError("SYNTHETIC_NEGATIVE_CONTROL_DRIFT")


class SAMFY2027RenumberingEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_one_indexed_presolicitation_not_two_awards_or_posted_rfps(self):
        validate_candidate(self.data)
        self.assertEqual(self.data["quality_and_ground_truth"][
            "original_publisher_notice_records_indexed"], 1)
        self.assertEqual(self.data["published_update_facts"][
            "public_amendment_proposed_contract_types"], ["FFP", "CPFF"])
        self.assertEqual(self.data["published_update_facts"][
            "planned_formal_rfp_release_window"],
            "LATE_FALL_2026_OCTOBER_OR_NOVEMBER_ANTICIPATED")

    def test_five_explicit_synthetic_controls_and_unknown_status(self):
        validate_candidate(self.data)
        self.assertTrue(all(x["kind"] == "SYNTHETIC" for x in
                            self.data["synthetic_negative_controls"]))
        self.assertEqual(self.data["quality_and_ground_truth"][
            "source_page_content_fingerprint"], "UNKNOWN_NOT_ACQUIRED")
        self.assertEqual(self.data["handoff"]["capturebrief_owner"], ":52")
        self.assertEqual(self.data["handoff"]["independent_qa"], ":44")

    def test_mutated_rights_rfp_award_and_provenance_are_rejected(self):
        poisonings = [
            ("source", "original_publisher_http_bytes_acquired", True),
            ("source", "original_publisher_http_sha256", "forged-original-sha256"),
            ("source", "dataset_specific_commercial_reuse_rights_verified", True),
            ("source", "notice_type", "SOLICITATION"),
            ("source", "reported_planned_fy2027_rfp_number", "N00024-26-R-4444"),
            ("published_update_facts", "new_fy2027_rfp_posting_verified_as_of_research_date", True),
            ("published_update_facts", "two_independent_contract_awards_proven", True),
            ("published_update_facts", "current_formal_rfp_status", "OPEN_FOR_BIDS"),
            ("quality_and_ground_truth", "independent_award_labels", 1),
        ]
        for section, name, bogus_value in poisonings:
            with self.subTest(field=name):
                poisoned = copy.deepcopy(self.data)
                poisoned[section][name] = bogus_value
                with self.assertRaises(ValueError):
                    validate_candidate(poisoned)


if __name__ == "__main__":
    unittest.main()
