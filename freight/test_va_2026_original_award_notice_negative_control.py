"""VA procurement original-source negative control: award notices are NOT pre-award leads.

This is a human-transcribed, public-source metadata fixture, NOT original-byte
custody, independent USAspending/FPDS transaction reconciliation, evidence of a
contract modification, a fraud finding, or an approved accuracy benchmark.

Official issuer pages, independently inspected in the public SAM.gov index:
  Apr 13, 2026 updated SOLICITATION (amendment 0001):
    https://sam.gov/opp/2d297ac70f22448fb733e8f07c7a1249/view
  Sep 11, 2026 original AWARD NOTICE:
    https://sam.gov/opp/d67f5c5dfd7a4e2388aa481d54e3753d/view

The source pages are JS-dependent: current original HTML/attachment bytes and
their digests were NOT captured. Numbers/identities here reflect the official
public page text; record-level modifications remain UNKNOWN.

No network calls, production D1 reads, customer data, feature code, or deployment.
"""
from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone

from freight.capturebrief_sam_fy2027_asof import assess_cross_source_chronology

SOURCE = {
    "issuer": "Department of Veterans Affairs",
    "office": "250-NETWORK CONTRACT OFFICE 10 (36C250)",
    "agency_code": "VA",
    "solicitation_id": "36C25026B0034",
    "original_solicitation_amendment": "0001",
    "solicitation_updated_publication_date": "2026-04-13",
    "solicitation_page": "https://sam.gov/opp/2d297ac70f22448fb733e8f07c7a1249/view",
    "award_notice_type": "Award Notice (Original)",
    "award_notice_original_published": "2026-09-11",
    "award_notice_page": "https://sam.gov/opp/d67f5c5dfd7a4e2388aa481d54e3753d/view",
    "award_contract_id": "36C25026C0119",
    "award_signed_date": "2026-09-11",
    "contractor": "PANACEA CONSTRUCTION GROUP LLC",
    "contractor_uei": "DARPZL19UP45",
    "agency_noticed_base_and_all_options_usd": 405949,
    "award_contract_modification_number": None,
    "award_contract_modification_count": None,
    "raw_original_award_document_sha256": None,
    "independent_award_transaction_verified": False,
    "verified_recovery_usd": None,
    "source_reuse_rights_approved": False,
}

OBSERVED_AFTER_AWARD = datetime(2026, 11, 5, tzinfo=timezone.utc)
HYPOTHETICAL_APRIL_CAPTURE = datetime(2026, 4, 14, tzinfo=timezone.utc)


def chronology_inputs():
    notice = {
        "solicitation_number": SOURCE["solicitation_id"],
        "agency_code": SOURCE["agency_code"],
        "office": SOURCE["office"],
        "posted_date": SOURCE["award_notice_original_published"],
    }
    candidate_award = {
        "solicitation_identifier": SOURCE["solicitation_id"],
        "matched_issuer_agency_code": SOURCE["agency_code"],
        "matched_issuer_office": SOURCE["office"],
        "award_date_signed": SOURCE["award_signed_date"],
    }
    return notice, candidate_award


def official_notice_identity_gate(candidate):
    """Test-only record-consistency guard, NOT an award-transaction validator."""
    fields = (
        "solicitation_id", "award_contract_id", "office", "contractor",
        "contractor_uei", "agency_noticed_base_and_all_options_usd",
    )
    if not isinstance(candidate, dict) or any(
        k not in candidate or candidate[k] is None or candidate[k] == ""
        for k in fields
    ):
        return "UNKNOWN_INCOMPLETE_IDENTITY"
    if any(candidate[k] != SOURCE[k] for k in fields):
        return "REJECT_MISMATCHED_ORIGINAL_AWARD_NOTICE"
    return "OFFICIAL_NOTICE_CONSISTENT_TRANSACTION_UNVERIFIED"


class VA2026AwardNoticeNegativeControls(unittest.TestCase):
    def test_original_award_notice_not_retroactive_preaward_opportunity(self):
        notice, award = chronology_inputs()
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award, source_observed_at=OBSERVED_AFTER_AWARD
            ),
            "FUTURE_POSTED_NOTICE_NOT_PREAWARD",
        )
        # Updating the notice date to the April solicitation date does NOT
        # make a source first observed in November an April as-of capture.
        notice["posted_date"] = SOURCE["solicitation_updated_publication_date"]
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award, source_observed_at=OBSERVED_AFTER_AWARD
            ),
            "ARCHIVE_OBSERVED_AFTER_AWARD_NOT_ASOF",
        )
        # A counterfactual April snapshot checks the positive boundary only.
        # No actual original April capture is represented by this test.
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award, source_observed_at=HYPOTHETICAL_APRIL_CAPTURE
            ),
            "PREAWARD_CHRONOLOGY_CANDIDATE_ONLY",
        )

    def test_updated_solicitation_cannot_be_observed_before_publication(self):
        """Independent VA notice timing control; neither capture is evidence.

        The agency's Apr 13 amendment cannot appear in an Apr 12 snapshot.
        An Apr 14 snapshot is only a counterfactual candidate, not proof
        that this lab captured the updated source then.
        """
        notice, award = chronology_inputs()
        notice["posted_date"] = SOURCE["solicitation_updated_publication_date"]
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award,
                source_observed_at=datetime(2026, 4, 12, tzinfo=timezone.utc),
            ),
            "SOURCE_OBSERVED_BEFORE_NOTICE_POSTED_NOT_ASOF",
        )
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award,
                source_observed_at=HYPOTHETICAL_APRIL_CAPTURE,
            ),
            "PREAWARD_CHRONOLOGY_CANDIDATE_ONLY",
        )

    def test_solicitation_id_not_award_id_and_issuer_must_match(self):
        notice, award = chronology_inputs()
        notice["solicitation_number"] = SOURCE["award_contract_id"]
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award, source_observed_at=OBSERVED_AFTER_AWARD
            ),
            "UNMATCHED_OR_UNKNOWN",
        )
        notice["solicitation_number"] = SOURCE["solicitation_id"]
        notice["office"] = "OTHER CONTRACTING OFFICE"
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award, source_observed_at=OBSERVED_AFTER_AWARD
            ),
            "ISSUER_CONFLICT",
        )
        notice["office"] = ""
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award, source_observed_at=OBSERVED_AFTER_AWARD
            ),
            "ISSUER_NOT_INDEPENDENTLY_MATCHED",
        )

    def test_wrong_awardee_or_uei_does_not_become_verified_join(self):
        self.assertEqual(
            official_notice_identity_gate(SOURCE),
            "OFFICIAL_NOTICE_CONSISTENT_TRANSACTION_UNVERIFIED",
        )
        for field, wrong_value in (
            ("contractor", "UNRELATED COMPANY"),
            ("contractor_uei", "INVALID-UEI"),
            ("award_contract_id", "36C25026C9999"),
            ("solicitation_id", "36C25026B9999"),
            ("agency_noticed_base_and_all_options_usd", 405950),
            ("office", "UNRELATED CONTRACTING OFFICE"),
        ):
            with self.subTest(field=field):
                candidate = copy.deepcopy(SOURCE)
                candidate[field] = wrong_value
                self.assertEqual(
                    official_notice_identity_gate(candidate),
                    "REJECT_MISMATCHED_ORIGINAL_AWARD_NOTICE",
                )
        missing = copy.deepcopy(SOURCE)
        missing.pop("contractor_uei")
        self.assertEqual(
            official_notice_identity_gate(missing),
            "UNKNOWN_INCOMPLETE_IDENTITY",
        )

    def test_solicitation_amendment_is_not_contract_modification_or_recovery(self):
        self.assertEqual(SOURCE["original_solicitation_amendment"], "0001")
        self.assertNotEqual(SOURCE["solicitation_id"], SOURCE["award_contract_id"])
        self.assertEqual(SOURCE["award_notice_type"], "Award Notice (Original)")
        self.assertEqual(SOURCE["agency_noticed_base_and_all_options_usd"], 405949)
        self.assertIsNone(SOURCE["award_contract_modification_number"])
        self.assertIsNone(SOURCE["award_contract_modification_count"])
        self.assertIsNone(SOURCE["raw_original_award_document_sha256"])
        self.assertIsNone(SOURCE["verified_recovery_usd"])
        self.assertFalse(SOURCE["independent_award_transaction_verified"])
        self.assertFalse(SOURCE["source_reuse_rights_approved"])


if __name__ == "__main__":
    unittest.main()
