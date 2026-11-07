"""DOL Job Corps FY2026 MATOC: first-party shared-capacity falsification.

Original US Department of Labor SAM.gov solicitation (updated 2026-02-13):
https://sam.gov/opp/baee4c785cb143b28c0d15a3fb8b56f6/view
Original DOL SAM.gov award notice (published 2026-09-01):
https://sam.gov/opp/f30e46c9f1074d5b813826df085c4903/view

Human-transcribed public-source facts, researched 2026-11-07 UTC. The
award notice explicitly says 360 million dollars is ONE maximum capacity
shared across SIXTEEN IDIQ contracts. A $360M per-contract display is
not $5.76B of independent capacity, dollars obligated, financial loss,
or a customer recovery. Solicitation Amendment 0001 (2026-02-13) is
not a verified post-award contract modification. Source HTML/PDF bytes,
award transactions, signed modifications, independent identities,
commercial reuse permission, and customer cash remain unverified.
This source-negative control is NOT a validated benchmark or FY2027 label.
No network or D1 reads, source downloads, or product writes in tests.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, date, timezone
import unittest

from freight.capturebrief_sam_fy2027_asof import assess_cross_source_chronology

SOLICITATION = {
    "publisher": "US DEPARTMENT OF LABOR VIA SAM.GOV",
    "office": "DOL - JCAS - AEC",
    "notice_guid": "baee4c785cb143b28c0d15a3fb8b56f6",
    "notice_id": "1605AE-25-R-00001",
    "kind": "SOLICITATION_UPDATED",
    "original_published": "2026-01-28",
    "amendment_published": "2026-02-13",
    "amendment_number": "0001",
    "amendment_scope": "SOLICITATION_PREAWARD",
    "offers_due": "2026-02-27",
}
AWARD = {
    "publisher": "US DEPARTMENT OF LABOR VIA SAM.GOV",
    "office": "DOL - JCAS - AEC",
    "notice_guid": "f30e46c9f1074d5b813826df085c4903",
    "related_notice_id": "1605AE-25-R-00001",
    "award_number": "1605AE-26-D-0009",
    "award_date": "2026-09-01",
    "original_published": "2026-09-01",
    "kind": "AWARD_NOTICE_ORIGINAL",
    "contractor": "MFS CONSTRUCTION LLC",
    "contractor_uei": "ZNDWJV6WGFU9",
    "awarded_idiq_count": 16,
    "ceiling_usd": 360_000_000,
    "ceiling_scope": "SHARED_ACROSS_16_IDIQ_CONTRACTS",
    "postaward_contract_modification_number": None,
    "independent_obligation_usd": None,
    "original_signed_transaction_retrieved": False,
    "original_source_bytes_sha256": None,
    "commercial_reuse_approved": False,
    "verified_customer_recovery_usd": None,
}
UNKNOWN = "UNKNOWN_UNMATCHED_OR_UNVERIFIED_SOURCE"
FALSE_16X = "FALSIFIED_5760M_INDEPENDENT_CAPACITY"
FALSE_MOD = "FALSIFIED_PREAWARD_AMENDMENT_IS_CONTRACT_MODIFICATION"
SHARED_ONLY = "SHARED_360M_CAPACITY_NOT_OBLIGATION_OR_RECOVERY"


def classify_claim(sol: dict, award: dict, *, claim: str) -> str:
    """A *specific source-identity* QA gate, not an award accounting engine."""
    if type(sol) is not dict or type(award) is not dict:
        return UNKNOWN
    # This is source-bound transcription validation, not byte authentication.
    required_s = (
        "publisher", "office", "notice_guid", "notice_id", "kind",
        "original_published", "amendment_published", "amendment_number",
        "amendment_scope", "offers_due",
    )
    required_a = (
        "publisher", "office", "notice_guid", "related_notice_id",
        "award_number", "award_date", "original_published", "kind",
        "contractor", "contractor_uei", "awarded_idiq_count", "ceiling_usd",
        "ceiling_scope", "postaward_contract_modification_number",
        "independent_obligation_usd", "original_signed_transaction_retrieved",
        "original_source_bytes_sha256", "commercial_reuse_approved",
        "verified_customer_recovery_usd",
    )
    if any(sol.get(key) != SOLICITATION[key] for key in required_s):
        return UNKNOWN
    if any(award.get(key) != AWARD[key] for key in required_a):
        return UNKNOWN
    if (sol["notice_id"] != award["related_notice_id"]
            or sol["notice_guid"] == award["notice_guid"]
            or sol["office"] != award["office"]
            or sol["publisher"] != award["publisher"]):
        return UNKNOWN
    try:
        original = date.fromisoformat(sol["original_published"])
        amended = date.fromisoformat(sol["amendment_published"])
        due = date.fromisoformat(sol["offers_due"])
        awarded = date.fromisoformat(award["award_date"])
        announced = date.fromisoformat(award["original_published"])
    except (TypeError, ValueError):
        return UNKNOWN
    if not original < amended < due < awarded <= announced:
        return UNKNOWN
    if claim == "SIXTEEN_INDEPENDENT_360M_AWARDS":
        return FALSE_16X
    if claim == "AMENDMENT_0001_IS_POSTAWARD_CONTRACT_MODIFICATION":
        return FALSE_MOD
    if claim == "ONE_SHARED_360M_CEILING":
        return SHARED_ONLY
    return UNKNOWN


class DOLJobCorps2026SharedCeilingNegativeControl(unittest.TestCase):
    def test_original_issuer_notice_award_and_shared_ceiling_falsify_16x(self):
        self.assertEqual(SOLICITATION["notice_id"], AWARD["related_notice_id"])
        self.assertNotEqual(SOLICITATION["notice_guid"], AWARD["notice_guid"])
        self.assertEqual(AWARD["award_number"], "1605AE-26-D-0009")
        self.assertEqual(AWARD["contractor_uei"], "ZNDWJV6WGFU9")
        self.assertEqual(classify_claim(
            SOLICITATION, AWARD, claim="SIXTEEN_INDEPENDENT_360M_AWARDS"
        ), FALSE_16X)
        self.assertEqual(AWARD["awarded_idiq_count"] * AWARD["ceiling_usd"],
                         5_760_000_000)
        self.assertEqual(classify_claim(
            SOLICITATION, AWARD, claim="ONE_SHARED_360M_CEILING"
        ), SHARED_ONLY)

    def test_february_amendment_does_not_become_september_contract_modification(self):
        self.assertEqual(classify_claim(
            SOLICITATION, AWARD,
            claim="AMENDMENT_0001_IS_POSTAWARD_CONTRACT_MODIFICATION"
        ), FALSE_MOD)
        self.assertLess(SOLICITATION["amendment_published"], AWARD["award_date"])
        self.assertIsNone(AWARD["postaward_contract_modification_number"])
        self.assertIsNone(AWARD["independent_obligation_usd"])
        self.assertIsNone(AWARD["verified_customer_recovery_usd"])
        self.assertFalse(AWARD["original_signed_transaction_retrieved"])
        self.assertIsNone(AWARD["original_source_bytes_sha256"])
        self.assertFalse(AWARD["commercial_reuse_approved"])

    def test_poisoned_join_and_source_claims_remain_unknown_not_falsified(self):
        for which, changes in (
            ("sol", {"notice_id": "1605AE-25-R-99999"}),
            ("sol", {"notice_guid": AWARD["notice_guid"]}),
            ("sol", {"amendment_scope": "POSTAWARD_CONTRACT_MODIFICATION"}),
            ("sol", {"amendment_published": "2026-10-13"}),
            ("award", {"related_notice_id": "1605AE-25-R-99999"}),
            ("award", {"award_number": "1605AE-26-D-0001"}),
            ("award", {"contractor_uei": "DIFFERENT"}),
            ("award", {"contractor": "DIFFERENT"}),
            ("award", {"office": "DIFFERENT"}),
            ("award", {"awarded_idiq_count": 1}),
            ("award", {"ceiling_scope": "PER_VENDOR"}),
            ("award", {"ceiling_usd": 5_760_000_000}),
            ("award", {"postaward_contract_modification_number": 1}),
            ("award", {"independent_obligation_usd": 360_000_000}),
            ("award", {"original_source_bytes_sha256": "FAKE"}),
        ):
            with self.subTest(which=which, changes=changes):
                s, a = deepcopy(SOLICITATION), deepcopy(AWARD)
                (s if which == "sol" else a).update(changes)
                self.assertEqual(classify_claim(
                    s, a, claim="SIXTEEN_INDEPENDENT_360M_AWARDS"
                ), UNKNOWN)

    def test_retrospective_sam_solicitation_not_prospective_observation(self):
        notice = {
            "solicitation_number": SOLICITATION["notice_id"],
            "agency_code": "DOL",
            "office": SOLICITATION["office"],
            "posted_date": SOLICITATION["amendment_published"],
        }
        award = {
            "solicitation_identifier": AWARD["related_notice_id"],
            "matched_issuer_agency_code": "DOL",
            "matched_issuer_office": AWARD["office"],
            "award_date_signed": AWARD["award_date"],
        }
        retrospective = datetime(2026, 11, 7, tzinfo=timezone.utc)
        self.assertEqual(assess_cross_source_chronology(
            notice, award, source_observed_at=retrospective
        ), "ARCHIVE_OBSERVED_AFTER_AWARD_NOT_ASOF")
        # Hypothetical February capture: test the nonvacuous positive path;
        # it is NOT an actual contemporaneous publisher observation.
        hypothetical = datetime(2026, 2, 20, tzinfo=timezone.utc)
        self.assertEqual(assess_cross_source_chronology(
            notice, award, source_observed_at=hypothetical
        ), "PREAWARD_CHRONOLOGY_CANDIDATE_ONLY")
        award["matched_issuer_office"] = ""
        self.assertEqual(assess_cross_source_chronology(
            notice, award, source_observed_at=hypothetical
        ), "ISSUER_NOT_INDEPENDENTLY_MATCHED")


if __name__ == "__main__":
    unittest.main()
