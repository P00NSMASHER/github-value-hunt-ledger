"""NASA SpaceX CCtCap: first-party modification-versus-base-award negative control.

This is a research-only, human-transcribed, PUBLIC agency-source fixture.
Do not infer a new 2026 base award from SAM's "Justification (Original)"
notice: NASA's separately published original CCtCap contract and 2015
award announcement show that the SpaceX CCtCap contract already existed.

NASA original contract index (contract NNK14MA74C):
https://www.nasa.gov/foia/nasa-e-libraries/kennedy-foia-library/electronic-library-spacex-cctcap/
NASA original contract PDF (cover names contract NNK14MA74C):
https://www.nasa.gov/wp-content/uploads/2019/08/CCtCap_SpaceX_508.pdf
NASA January 5, 2015 statement: CCtCap awards made September 16, 2014:
https://www.nasa.gov/news-release/nasa-statement-on-gao-decision-to-deny-commercial-crew-contract-protest/
2026 original SAM justification dated September 29 (modification #136):
https://sam.gov/opp/b3a197c860214b308533407935d58f89/view

No claim of original SAM HTML/attachment byte custody, transaction-level
modification verification, a dollar value, eligibility, reuse approval,
real customer recovery, or a 2026 original BASE-contract award.
No live network, D1, confidential data, or product feature code.
"""
from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone

from freight.capturebrief_sam_fy2027_asof import assess_cross_source_chronology


NASA_EARLIER = {
    "agency": "NATIONAL AERONAUTICS AND SPACE ADMINISTRATION",
    "program": "Commercial Crew Transportation Capability (CCtCap)",
    "original_cc_tcap_contract_id": "NNK14MA74C",
    "contractor": "Space Exploration Technologies Corp. (SpaceX)",
    "2015_statement_reports_award_date": "2014-09-16",
    "original_nasa_contract_published": True,
}
SAM_2026 = {
    "agency": "NATIONAL AERONAUTICS AND SPACE ADMINISTRATION",
    "office": "NASA KENNEDY SPACE CENTER",
    "notice_id": "NNK14MA74C-Modification-136",
    "related_notice": "NNK14MA74C",
    "award_number": "NNK14MA74C",
    "title": "Modification to the SpaceX Commercial Crew Transportation Capabilities (CCtCap) Contract",
    "notice_kind": "Justification (Original)",
    "reported_action_date": "2026-09-18",
    "original_notice_published": "2026-09-29",
    "modification_number": 136,
    "task_order_number": "NNK17MA01T",
    "contractor_in_description": "SpaceX",
    "original_contract_modification_transaction_verified": False,
    "public_notice_raw_bytes_retained": False,
    "source_specific_reuse_approved": False,
    "2026_obligated_amount_usd": None,
    "verified_customer_recovery_usd": None,
}
SOURCE_OBSERVED = datetime(2026, 11, 6, 5, 0, tzinfo=timezone.utc)


def adjudicate_new_2026_base_award_claim(earlier: dict, later: dict) -> str:
    """Test-only falsification gate. Not a transaction or source-rights validator."""
    if (
        earlier.get("agency") != later.get("agency")
        or not earlier.get("agency")
        or earlier.get("original_cc_tcap_contract_id") != later.get("award_number")
        or later.get("award_number") != later.get("related_notice")
        or not earlier.get("original_cc_tcap_contract_id")
        or earlier.get("contractor") != NASA_EARLIER["contractor"]
        or earlier.get("program") != NASA_EARLIER["program"]
    ):
        return "UNKNOWN_OR_UNMATCHED_ORIGINAL_SOURCE"
    if (
        not earlier.get("original_nasa_contract_published")
        or not earlier.get("2015_statement_reports_award_date")
        or not later.get("reported_action_date")
        or not later.get("original_notice_published")
    ):
        return "UNKNOWN_MISSING_SOURCE_CHRONOLOGY"
    if (
        later.get("modification_number") == 136
        and later.get("notice_id") == earlier["original_cc_tcap_contract_id"] + "-Modification-136"
        and later.get("title", "").startswith("Modification to the SpaceX")
        and later.get("notice_kind") == "Justification (Original)"
        and earlier["2015_statement_reports_award_date"] < later["reported_action_date"]
        and later["reported_action_date"] < later["original_notice_published"]
    ):
        return "FALSIFIED_NEW_2026_BASE_AWARD_LABEL"
    return "UNKNOWN_NOT_ADJUDICATED"


class NasaSpaceX2026ModificationNegativeControl(unittest.TestCase):
    def test_2014_agency_contract_and_2026_modification_disprove_new_base_award(self):
        self.assertEqual(
            adjudicate_new_2026_base_award_claim(NASA_EARLIER, SAM_2026),
            "FALSIFIED_NEW_2026_BASE_AWARD_LABEL",
        )
        self.assertNotEqual(SAM_2026["notice_id"], SAM_2026["award_number"])
        self.assertEqual(SAM_2026["modification_number"], 136)
        self.assertEqual(SAM_2026["notice_kind"], "Justification (Original)")

    def test_unrelated_contract_or_missing_modification_cannot_be_falsified(self):
        wrong_contract = copy.deepcopy(SAM_2026)
        wrong_contract["award_number"] = "UNRELATED-ID"
        self.assertEqual(
            adjudicate_new_2026_base_award_claim(NASA_EARLIER, wrong_contract),
            "UNKNOWN_OR_UNMATCHED_ORIGINAL_SOURCE",
        )
        missing_mod = copy.deepcopy(SAM_2026)
        missing_mod["modification_number"] = None
        self.assertEqual(
            adjudicate_new_2026_base_award_claim(NASA_EARLIER, missing_mod),
            "UNKNOWN_NOT_ADJUDICATED",
        )
        missing_prior = copy.deepcopy(NASA_EARLIER)
        missing_prior["original_nasa_contract_published"] = False
        self.assertEqual(
            adjudicate_new_2026_base_award_claim(missing_prior, SAM_2026),
            "UNKNOWN_MISSING_SOURCE_CHRONOLOGY",
        )

    def test_original_notice_is_not_preaward_and_notice_id_is_not_award_id(self):
        notice = {
            "solicitation_number": SAM_2026["notice_id"],
            "agency_code": "NASA",
            "office": SAM_2026["office"],
            "posted_date": SAM_2026["original_notice_published"],
        }
        candidate = {
            "solicitation_identifier": SAM_2026["award_number"],
            "matched_issuer_agency_code": "NASA",
            "matched_issuer_office": SAM_2026["office"],
            "award_date_signed": SAM_2026["reported_action_date"],
        }
        self.assertEqual(
            assess_cross_source_chronology(
                notice, candidate, source_observed_at=SOURCE_OBSERVED
            ),
            "UNMATCHED_OR_UNKNOWN",
        )
        notice["solicitation_number"] = SAM_2026["related_notice"]
        self.assertEqual(
            assess_cross_source_chronology(
                notice, candidate, source_observed_at=SOURCE_OBSERVED
            ),
            "FUTURE_POSTED_NOTICE_NOT_PREAWARD",
        )
        # Replacing the post date with an older program date does NOT prove
        # that THIS September 2026 modification was available in 2014.
        notice["posted_date"] = NASA_EARLIER["2015_statement_reports_award_date"]
        self.assertEqual(
            assess_cross_source_chronology(
                notice, candidate, source_observed_at=SOURCE_OBSERVED
            ),
            "ARCHIVE_OBSERVED_AFTER_AWARD_NOT_ASOF",
        )

    def test_no_financial_or_permission_promotion_from_original_notice(self):
        self.assertIsNone(SAM_2026["2026_obligated_amount_usd"])
        self.assertIsNone(SAM_2026["verified_customer_recovery_usd"])
        self.assertFalse(SAM_2026["original_contract_modification_transaction_verified"])
        self.assertFalse(SAM_2026["public_notice_raw_bytes_retained"])
        self.assertFalse(SAM_2026["source_specific_reuse_approved"])


if __name__ == "__main__":
    unittest.main()
