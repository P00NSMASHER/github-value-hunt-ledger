"""USAF original SAM notice: a contract modification is not a new base award.

Original issuer notice, indexed public SAM.gov text (checked 2026-11-06):
https://sam.gov/opp/77acd7b42a5541e899acbea386182fb8/view

USAF/Robins AFB notice FA8538-25-D-0003-P00002 explicitly calls P00002
a $2,357,979 modification; overall value changes from $10,452,726.65
to $12,810,705.65. The structured Award Details header instead prints
$12,810,705.65 as Base and All Options Value. It ALSO prints award date
2026-09-22 while description item (14) says 2016-09-22. Keep that date
conflict UNKNOWN; neither field authenticates the underlying transaction.
The structured PSC is J016 (aircraft parts repair), but the narrative's
item (5) says J066. Neither code independently verifies an exact PSC join.

This is a human-transcribed, PUBLIC issuer-source negative control, not
raw original-byte custody or an independently reconciled award/obligation.
Do not attribute $12.81M of new 2026 obligations, add $12.81M and $2.36M,
invent source-usage rights, or count customer recoveries. No network/D1.
"""
from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone

from freight.capturebrief_sam_fy2027_asof import assess_cross_source_chronology

OFFICIAL = {
    "source": "https://sam.gov/opp/77acd7b42a5541e899acbea386182fb8/view",
    "issuing_agency": "DEPT OF THE AIR FORCE",
    "office": "FA8538 AFSC PZAAB",
    "notice_id": "FA8538-25-D-0003-P00002",
    "source_notice_uuid": "77acd7b42a5541e899acbea386182fb8",
    "related_solicitation": "FA8538-24-R-0014",
    "original_solicitation_in_description": "FA8538-24-R-0014-0001",
    "contract_award_line_solicitation_in_description": "FA8538-24-R-0014-001",
    "contractor": "L3HARRIS TECHNOLOGIES, INC.",
    "contractor_uei": "PMH3MAVQGE44",
    "award_date_header": "2026-09-22",
    "award_date_in_description": "2016-09-22",
    "notice_original_published": "2026-09-25",
    "modification": "P00002",
    "psc_header": "J016",
    "psc_description_item_5": "J066",
    "prior_total_usd_cents": 1045272665,
    "modification_action_usd_cents": 235797900,
    "new_total_usd_cents": 1281070565,
    "original_bytes_sha256": None,
    "independent_contract_transaction_confirmed": False,
    "contract_modification_obligation_usd_cents": None,
    "cash_received_usd_cents": None,
    "source_reuse_rights_verified": False,
}

# Immutable case-specific transcription anchors; no publisher signature.
SOURCE_ANCHORS = {k: v for k, v in OFFICIAL.items() if k not in (
    "original_bytes_sha256", "independent_contract_transaction_confirmed",
    "contract_modification_obligation_usd_cents", "cash_received_usd_cents",
    "source_reuse_rights_verified"
)}

def assess_claim(source: dict, claim: dict) -> str:
    """Reject false issuer/action joins; do not certify an award transaction."""
    if type(source) is not dict or type(claim) is not dict:
        return "UNKNOWN_MALFORMED"
    if any(source.get(k) != v for k, v in SOURCE_ANCHORS.items()):
        return "UNKNOWN_SOURCE_NOT_AUTHENTICATED"
    for k in ("issuing_agency", "office", "notice_id", "contractor",
              "contractor_uei", "modification"):
        if claim.get(k) != source[k]:
            return "UNKNOWN_UNMATCHED_IDENTITY_OR_MODIFICATION"
    if (source["prior_total_usd_cents"] + source["modification_action_usd_cents"]
            != source["new_total_usd_cents"]):
        return "UNKNOWN_INCONSISTENT_ISSUER_AMOUNTS"
    # Official structured PSC and narrative PSC disagree. A claim of exact
    # product/service classification must not resolve the conflict by fiat.
    if "claimed_exact_psc" in claim:
        if source["psc_header"] != source["psc_description_item_5"]:
            return "UNKNOWN_CONFLICTING_ISSUER_PSC"
        if claim["claimed_exact_psc"] != source["psc_header"]:
            return "UNKNOWN_UNMATCHED_ISSUER_PSC"
    # Official header and two description fields name three DIFFERENT
    # solicitation strings. A claim of a verified exact original-solicitation
    # join cannot inherit the notice-level modification consistency result.
    if "claimed_original_solicitation" in claim:
        refs = {
            source["related_solicitation"],
            source["original_solicitation_in_description"],
            source["contract_award_line_solicitation_in_description"],
        }
        if len(refs) != 1:
            return "UNKNOWN_CONFLICTING_ISSUER_SOLICITATION_REFERENCES"
        if claim["claimed_original_solicitation"] not in refs:
            return "UNKNOWN_UNMATCHED_ISSUER_SOLICITATION"
    if claim.get("award_date") == source["award_date_in_description"]:
        return "UNKNOWN_CONFLICTING_ISSUER_AWARD_YEAR"
    if claim.get("claimed_new_base_award_usd_cents") == source["new_total_usd_cents"]:
        return "FALSIFIED_TOTAL_MISLABELED_AS_NEW_BASE_AWARD"
    if claim.get("claimed_modification_usd_cents") == source["new_total_usd_cents"]:
        return "FALSIFIED_TOTAL_MISLABELED_AS_MODIFICATION_AMOUNT"
    if claim.get("claimed_modification_usd_cents") != source["modification_action_usd_cents"]:
        return "UNKNOWN_UNRECONCILED_ACTION_AMOUNT"
    if (claim.get("claimed_verified_obligation_usd_cents") is not None
            or claim.get("claimed_paid_recovery_usd_cents") is not None):
        return "UNKNOWN_UNVERIFIED_OBLIGATION_OR_CASH"
    return "ISSUER_NOTICE_MODIFICATION_CONSISTENT_TRANSACTION_UNKNOWN"

def candidate() -> dict:
    return {**{k: OFFICIAL[k] for k in (
        "issuing_agency", "office", "notice_id", "contractor",
        "contractor_uei", "modification")},
        "award_date": OFFICIAL["award_date_header"],
        "claimed_modification_usd_cents": OFFICIAL["modification_action_usd_cents"],
        "claimed_verified_obligation_usd_cents": None,
        "claimed_paid_recovery_usd_cents": None}

class AirForceL3HarrisSourceBoundNegativeControl(unittest.TestCase):
    def test_same_original_issuer_distinguishes_action_from_overall_total(self):
        self.assertEqual(OFFICIAL["prior_total_usd_cents"] +
                         OFFICIAL["modification_action_usd_cents"],
                         OFFICIAL["new_total_usd_cents"])
        self.assertEqual(assess_claim(OFFICIAL, candidate()),
                         "ISSUER_NOTICE_MODIFICATION_CONSISTENT_TRANSACTION_UNKNOWN")
        wrong = candidate()
        wrong["claimed_modification_usd_cents"] = OFFICIAL["new_total_usd_cents"]
        self.assertEqual(assess_claim(OFFICIAL, wrong),
                         "FALSIFIED_TOTAL_MISLABELED_AS_MODIFICATION_AMOUNT")
        wrong = candidate()
        wrong["claimed_new_base_award_usd_cents"] = OFFICIAL["new_total_usd_cents"]
        self.assertEqual(assess_claim(OFFICIAL, wrong),
                         "FALSIFIED_TOTAL_MISLABELED_AS_NEW_BASE_AWARD")

    def test_wrong_contractor_uei_contract_issuer_or_modification_cannot_join(self):
        for key, bad in (("contractor", "OTHER CONTRACTOR"),
                         ("contractor_uei", "WRONG-UEI"),
                         ("notice_id", "FA8538-25-D-0004-P00002"),
                         ("office", "OTHER OFFICE"),
                         ("issuing_agency", "DEPT OF THE NAVY"),
                         ("modification", "P00001")):
            with self.subTest(key=key):
                mutated = candidate()
                mutated[key] = bad
                self.assertEqual(assess_claim(OFFICIAL, mutated),
                                 "UNKNOWN_UNMATCHED_IDENTITY_OR_MODIFICATION")
        mutated_source = copy.deepcopy(OFFICIAL)
        mutated_source["modification_action_usd_cents"] += 100
        self.assertEqual(assess_claim(mutated_source, candidate()),
                         "UNKNOWN_SOURCE_NOT_AUTHENTICATED")

    def test_official_description_year_conflicts_with_header_not_a_2016_award(self):
        self.assertNotEqual(OFFICIAL["award_date_in_description"],
                            OFFICIAL["award_date_header"])
        wrong = candidate()
        wrong["award_date"] = OFFICIAL["award_date_in_description"]
        self.assertEqual(assess_claim(OFFICIAL, wrong),
                         "UNKNOWN_CONFLICTING_ISSUER_AWARD_YEAR")
        notice = {
            "solicitation_number": OFFICIAL["related_solicitation"],
            "agency_code": "DOD", "office": OFFICIAL["office"],
            "posted_date": OFFICIAL["notice_original_published"]
        }
        award = {
            "solicitation_identifier": OFFICIAL["related_solicitation"],
            "matched_issuer_agency_code": "DOD",
            "matched_issuer_office": OFFICIAL["office"],
            "award_date_signed": OFFICIAL["award_date_header"]
        }
        self.assertEqual(assess_cross_source_chronology(
            notice, award, source_observed_at=datetime(
                2026, 11, 6, tzinfo=timezone.utc)),
            "FUTURE_POSTED_NOTICE_NOT_PREAWARD")

    def test_three_official_solicitation_strings_cannot_be_joined_as_exact(self):
        # SAM.gov related-notice header and description items (8) and (11)
        # disagree; the agency's notice is NOT a validated exact-source join.
        refs = {
            OFFICIAL["related_solicitation"],
            OFFICIAL["original_solicitation_in_description"],
            OFFICIAL["contract_award_line_solicitation_in_description"],
        }
        self.assertEqual(len(refs), 3)
        for claimed in (*sorted(refs), "FA8538-24-R-0014-9999"):
            with self.subTest(claimed=claimed):
                wrong = candidate()
                wrong["claimed_original_solicitation"] = claimed
                self.assertEqual(
                    assess_claim(OFFICIAL, wrong),
                    "UNKNOWN_CONFLICTING_ISSUER_SOLICITATION_REFERENCES",
                )
        # The source itself must not be rewritten to a unified identity.
        forged = copy.deepcopy(OFFICIAL)
        forged["original_solicitation_in_description"] = (
            forged["related_solicitation"])
        self.assertEqual(
            assess_claim(forged, candidate()),
            "UNKNOWN_SOURCE_NOT_AUTHENTICATED",
        )

    def test_official_psc_conflict_must_not_be_promoted_to_exact_join(self):
        # First-party SAM structured PSC J016 versus description (5) J066.
        self.assertEqual(OFFICIAL["psc_header"], "J016")
        self.assertEqual(OFFICIAL["psc_description_item_5"], "J066")
        for code in ("J016", "J066", "J999"):
            with self.subTest(claimed_exact_psc=code):
                wrong = candidate()
                wrong["claimed_exact_psc"] = code
                self.assertEqual(assess_claim(OFFICIAL, wrong),
                                 "UNKNOWN_CONFLICTING_ISSUER_PSC")
        # Altering the transcribed original to erase the discrepancy is not proof.
        forged = copy.deepcopy(OFFICIAL)
        forged["psc_description_item_5"] = "J016"
        self.assertEqual(assess_claim(forged, candidate()),
                         "UNKNOWN_SOURCE_NOT_AUTHENTICATED")

    def test_original_notice_is_not_obligation_payment_or_rights_evidence(self):
        self.assertIsNone(OFFICIAL["original_bytes_sha256"])
        self.assertFalse(OFFICIAL["independent_contract_transaction_confirmed"])
        self.assertIsNone(OFFICIAL["contract_modification_obligation_usd_cents"])
        self.assertIsNone(OFFICIAL["cash_received_usd_cents"])
        self.assertFalse(OFFICIAL["source_reuse_rights_verified"])
        wrong = candidate()
        wrong["claimed_verified_obligation_usd_cents"] = 235797900
        self.assertEqual(assess_claim(OFFICIAL, wrong),
                         "UNKNOWN_UNVERIFIED_OBLIGATION_OR_CASH")

if __name__ == "__main__":
    unittest.main()
