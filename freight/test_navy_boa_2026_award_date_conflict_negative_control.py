"""Independent first-party SAM.gov negative control: conflicting award years.

Two different PUBLIC official Navy NSWC Crane notices carry the same award ID,
but disagree by 294 years on the contract award date. The original award
notice states 2320; the official justification states 2026. That is an
original-record contradiction, NOT proof of an independently settled award.

Official award notice (published 2026-10-05):
 https://sam.gov/opp/0c221247a10f41848b1b34c830844847/view
Official justification (published 2026-10-06):
 https://sam.gov/opp/b77d73d400f34d769bc4f40501458d12/view
Original presolicitation (published 2024-04-02):
 https://sam.gov/opp/e066c72da9074a7eb0975cd80088cec6/view

Human-transcribed public source metadata only. Original document bytes are
not held, source-specific reuse rights are unverified, independent USAspending
transaction/modification history is not validated, and $25M is a ceiling,
NOT proof of obligation or recoverable customer cash.
No D1/network calls or production changes.
"""
from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone

from freight.capturebrief_sam_fy2027_asof import assess_cross_source_chronology

AWARD_NOTICE = {
    "publisher": "Department of the Navy / NSWC CRANE via SAM.gov",
    "notice_type": "Award Notice (Original)",
    "notice_id": "0c221247a10f41848b1b34c830844847",
    "published": "2026-10-05",
    "solicitation": "N0016424RJW78",
    "award_id": "N0016426GMP07",
    "award_date": "2320-09-23",  # EXACT official award notice date, not an inferred repair.
    "contractor": "L3 TECHNOLOGIES, INC.",
    "contractor_uei": "F3QZR1JK1TA8",
    "base_and_all_options_ceiling_usd": 25000000,
}
JUSTIFICATION = {
    "publisher": "Department of the Navy / NSWC CRANE via SAM.gov",
    "notice_type": "Justification (Original)",
    "notice_id": "b77d73d400f34d769bc4f40501458d12",
    "published": "2026-10-06",
    "related_notice": "N0016424RJW78",
    "award_id": "N0016426GMP07",
    "award_date": "2026-09-23",  # Exact separate official justification claim.
    "modification_number": None,  # Officially blank, NOT proven absent.
}
PRESOLICITATION = {
    "notice_type": "Presolicitation",
    "notice_id": "e066c72da9074a7eb0975cd80088cec6",
    "published": "2024-04-02",
    "solicitation": "N0016424RJW78",
}
OBSERVED = datetime(2026, 11, 5, 21, 0, tzinfo=timezone.utc)


def original_notice_date_crosscheck(award_notice: dict, justification: dict) -> str:
    """Test-only source contradiction detector, NOT award join verification."""
    if (award_notice.get("award_id") != justification.get("award_id")
            or not award_notice.get("award_id")
            or award_notice.get("solicitation") != justification.get("related_notice")
            or not award_notice.get("solicitation")
            or award_notice.get("publisher") != justification.get("publisher")
            or not award_notice.get("publisher")):
        return "UNKNOWN_UNMATCHED_ORIGINAL_SOURCE_IDENTITY"
    if not award_notice.get("award_date") or not justification.get("award_date"):
        return "UNKNOWN_MISSING_OFFICIAL_DATE"
    if award_notice["award_date"] != justification["award_date"]:
        return "FALSIFIED_CONFLICTING_OFFICIAL_AWARD_DATE"
    return "SOURCE_DATE_CONSISTENT_NOT_TRANSACTION_VERIFIED"


class NavyBoa2026OriginalSourceNegativeControl(unittest.TestCase):
    def test_same_official_issuer_and_award_id_but_dates_conflict(self):
        self.assertEqual(AWARD_NOTICE["award_id"], JUSTIFICATION["award_id"])
        self.assertEqual(AWARD_NOTICE["publisher"], JUSTIFICATION["publisher"])
        self.assertEqual(AWARD_NOTICE["solicitation"], JUSTIFICATION["related_notice"])
        self.assertEqual(AWARD_NOTICE["award_date"], "2320-09-23")
        self.assertEqual(JUSTIFICATION["award_date"], "2026-09-23")
        self.assertEqual(
            original_notice_date_crosscheck(AWARD_NOTICE, JUSTIFICATION),
            "FALSIFIED_CONFLICTING_OFFICIAL_AWARD_DATE",
        )

    def test_unrelated_award_or_missing_provenance_does_not_falsify_a_join(self):
        different = copy.deepcopy(JUSTIFICATION)
        different["award_id"] = "N0016426GMP99"
        self.assertEqual(
            original_notice_date_crosscheck(AWARD_NOTICE, different),
            "UNKNOWN_UNMATCHED_ORIGINAL_SOURCE_IDENTITY",
        )
        different = copy.deepcopy(JUSTIFICATION)
        different["publisher"] = "ANOTHER FEDERAL ISSUER"
        self.assertEqual(
            original_notice_date_crosscheck(AWARD_NOTICE, different),
            "UNKNOWN_UNMATCHED_ORIGINAL_SOURCE_IDENTITY",
        )
        different = copy.deepcopy(JUSTIFICATION)
        different["award_date"] = None
        self.assertEqual(
            original_notice_date_crosscheck(AWARD_NOTICE, different),
            "UNKNOWN_MISSING_OFFICIAL_DATE",
        )

    def test_2320_award_year_causes_unsafe_preaward_candidate_in_current_gate(self):
        # Genuine 2024 presolicitation exists; no 2024 source-byte custody exists.
        notice = {
            "solicitation_number": PRESOLICITATION["solicitation"],
            "agency_code": "DOD",
            "office": "NSWC CRANE",
            "posted_date": PRESOLICITATION["published"],
        }
        award = {
            "solicitation_identifier": AWARD_NOTICE["solicitation"],
            "matched_issuer_agency_code": "DOD",
            "matched_issuer_office": "NSWC CRANE",
            "award_date_signed": AWARD_NOTICE["award_date"],
        }
        # Demonstrates EXISTING pure-function false candidate, not a validated hit.
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award, source_observed_at=OBSERVED
            ),
            "PREAWARD_CHRONOLOGY_CANDIDATE_ONLY",
        )
        # The other OFFICIAL record leads to the correct retrospective hold.
        award["award_date_signed"] = JUSTIFICATION["award_date"]
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award, source_observed_at=OBSERVED
            ),
            "ARCHIVE_OBSERVED_AFTER_AWARD_NOT_ASOF",
        )
        self.assertEqual(
            original_notice_date_crosscheck(AWARD_NOTICE, JUSTIFICATION),
            "FALSIFIED_CONFLICTING_OFFICIAL_AWARD_DATE",
        )

    def test_unknown_modifications_and_ceiling_are_not_outcomes(self):
        self.assertIsNone(JUSTIFICATION["modification_number"])
        self.assertEqual(AWARD_NOTICE["base_and_all_options_ceiling_usd"], 25000000)
        # No original transaction proof, modification count, or customer recovery.
        self.assertNotIn("verified_obligation_usd", AWARD_NOTICE)
        self.assertNotIn("verified_recovery_usd", AWARD_NOTICE)
        self.assertNotIn("independent_transaction_sha256", JUSTIFICATION)


if __name__ == "__main__":
    unittest.main()
