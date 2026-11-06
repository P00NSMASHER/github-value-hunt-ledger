"""First-party Army PrSM negative control: a NEW SAM award notice describes an OLD contract modification.

Source-bound HUMAN-TRANSCRIBED public record, not original-byte custody or
an independently verified FPDS/USAspending transaction. Three original issuers'
government pages (DOD/Army published contract announcements and SAM notice):

2025 ORIGINAL base contract (Mar 28, 2025, Army/ACC Redstone):
https://www.defense.gov/News/Contracts/Contract/Article/4138718/
2026 MODIFICATION P00007 (Jun 23, 2026, Army/ACC Redstone):
https://www.war.gov/News/Contracts/Contract/Article/4524437/contracts-for-june-23-2026/
2026 SAM notice PFA-JA24-1648-A01, labelled "Award Notice (Original)":
https://sam.gov/opp/b8d607cfbf3c4c7c8d4132fed7e8fcd5/view

Scope of falsification: June 2026 is NOT the first award of the
W31P4Q-25-D-0010 base contract, and $13,339,535,048 is a modified CEILING,
not verified disbursement/obligation or customer recovery. "Original" is a
SAM notice revision label, not proof of original contract formation.

Not independently verified: transaction-level modification history, original
HTML/PDF bytes and SHA, source-specific commercial reuse, or real recovery.
No D1, network, product code, customer data, or deployment.
"""
from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone

from freight.capturebrief_sam_fy2027_asof import assess_cross_source_chronology

BASE_2025 = {
    "issuer": "DEPARTMENT OF THE ARMY",
    "contracting_office": "ARMY CONTRACTING COMMAND, REDSTONE ARSENAL",
    "contractor": "LOCKHEED MARTIN CORP.",
    "contract_id": "W31P4Q-25-D-0010",
    "base_award_announced": "2025-03-28",
    "base_award_value_usd": 4_937_045_400,
    "original_2025_issuer_publication": True,
}
ARMY_2026 = {
    "issuer": "DEPARTMENT OF THE ARMY",
    "contracting_office": "ARMY CONTRACTING COMMAND, REDSTONE ARSENAL",
    "contractor": "LOCKHEED MARTIN CORP.",
    "contract_id": "W31P4Q-25-D-0010",
    "modification": "P00007",
    "award_action_date": "2026-06-23",
    "ceiling_increase_usd": 8_402_489_648,
    "new_cumulative_ceiling_usd": 13_339_535_048,
    "obligated_at_modification_usd": None,
}
SAM_2026 = {
    "issuer": "DEPARTMENT OF THE ARMY",
    "contracting_office": "W6QK ACC-RSA",
    "notice_id": "PFA-JA24-1648-A01",
    "type": "Award Notice (Original)",
    "published": "2026-06-24",
    "action_date": "2026-06-23",
    "award_number": "W31P4Q25D0010",
    "contractor": "Lockheed Martin Corporation",
    "contractor_uei": "XFJMYSYFJEK4",  # SAM-only identity, not independently corroborated
    "base_and_all_options_usd": 13_339_535_048,
    "description_modification": "P00007",
    "source_bytes_sha256": None,
    "verified_transaction_modification": False,
    "source_specific_reuse_approved": False,
    "verified_customer_recoveries_usd": None,
}
OBSERVED = datetime(2026, 11, 6, 5, 0, tzinfo=timezone.utc)


def norm_contract(v: object) -> str:
    return v.replace("-", "").upper() if isinstance(v, str) else ""


def adjudicate_original_award_claim(base: dict, action: dict, sam: dict) -> str:
    """Fail-closed research negative control; NOT an award-transaction validator."""
    if not all(isinstance(x, dict) for x in (base, action, sam)):
        return "UNKNOWN_MALFORMED_ORIGINAL_SOURCE"
    if (
        not base.get("contract_id")
        or norm_contract(base["contract_id"]) != norm_contract(action.get("contract_id"))
        or norm_contract(action.get("contract_id")) != norm_contract(sam.get("award_number"))
        or base.get("issuer") != action.get("issuer")
        or action.get("issuer") != sam.get("issuer")
        or not base.get("issuer")
        or base.get("contracting_office") != action.get("contracting_office")
        or base.get("contractor") != action.get("contractor")
        or not base.get("contractor")
    ):
        return "UNKNOWN_OR_UNMATCHED_SOURCE_IDENTITY"
    if (
        not base.get("original_2025_issuer_publication")
        or not base.get("base_award_announced")
        or not action.get("award_action_date")
        or not sam.get("published")
        or not sam.get("action_date")
    ):
        return "UNKNOWN_MISSING_ORIGINAL_SOURCE_CHRONOLOGY"
    if not (
        base["base_award_announced"] < action["award_action_date"]
        == sam["action_date"] < sam["published"]
    ):
        return "UNKNOWN_CONFLICTING_ACTION_CHRONOLOGY"
    if (
        action.get("modification") != "P00007"
        or sam.get("description_modification") != action["modification"]
        or sam.get("type") != "Award Notice (Original)"
    ):
        return "UNKNOWN_MODIFICATION_IDENTITY"
    if (
        type(base.get("base_award_value_usd")) is not int
        or type(action.get("ceiling_increase_usd")) is not int
        or type(action.get("new_cumulative_ceiling_usd")) is not int
        or type(sam.get("base_and_all_options_usd")) is not int
        or base["base_award_value_usd"] + action["ceiling_increase_usd"]
        != action["new_cumulative_ceiling_usd"]
        or action["new_cumulative_ceiling_usd"] != sam["base_and_all_options_usd"]
    ):
        return "UNKNOWN_CONFLICTING_CEILING_AMOUNTS"
    return "FALSIFIED_NEW_2026_BASE_AWARD_LABEL"


class ArmyPrsmOriginalContractVsModificationNegativeControl(unittest.TestCase):
    def test_first_party_2025_base_and_2026_amendment_are_same_contract(self):
        self.assertEqual(
            adjudicate_original_award_claim(BASE_2025, ARMY_2026, SAM_2026),
            "FALSIFIED_NEW_2026_BASE_AWARD_LABEL",
        )
        self.assertNotEqual(SAM_2026["notice_id"], SAM_2026["award_number"])
        self.assertEqual(ARMY_2026["modification"], "P00007")
        self.assertEqual(SAM_2026["type"], "Award Notice (Original)")

    def test_mismatched_contract_original_or_issuer_must_remain_unknown(self):
        for field, value in (("contract_id", "W31P4Q-25-D-9999"),
                             ("issuer", "OTHER FEDERAL AGENCY"),
                             ("contractor", "UNRELATED CONTRACTOR")):
            with self.subTest(field=field):
                changed = copy.deepcopy(BASE_2025)
                changed[field] = value
                self.assertEqual(
                    adjudicate_original_award_claim(changed, ARMY_2026, SAM_2026),
                    "UNKNOWN_OR_UNMATCHED_SOURCE_IDENTITY",
                )
        missing = copy.deepcopy(BASE_2025)
        missing["original_2025_issuer_publication"] = False
        self.assertEqual(
            adjudicate_original_award_claim(missing, ARMY_2026, SAM_2026),
            "UNKNOWN_MISSING_ORIGINAL_SOURCE_CHRONOLOGY",
        )

    def test_ceiling_mutation_or_missing_modification_cannot_verify(self):
        changed = copy.deepcopy(SAM_2026)
        changed["base_and_all_options_usd"] += 1
        self.assertEqual(
            adjudicate_original_award_claim(BASE_2025, ARMY_2026, changed),
            "UNKNOWN_CONFLICTING_CEILING_AMOUNTS",
        )
        changed = copy.deepcopy(ARMY_2026)
        changed["modification"] = None
        self.assertEqual(
            adjudicate_original_award_claim(BASE_2025, changed, SAM_2026),
            "UNKNOWN_MODIFICATION_IDENTITY",
        )

    def test_original_revision_notice_cannot_create_preaward_2026_lead(self):
        notice = {
            "solicitation_number": SAM_2026["notice_id"],
            "agency_code": "DOD",
            "office": SAM_2026["contracting_office"],
            "posted_date": SAM_2026["published"],
        }
        award = {
            "solicitation_identifier": SAM_2026["award_number"],
            "matched_issuer_agency_code": "DOD",
            "matched_issuer_office": SAM_2026["contracting_office"],
            "award_date_signed": SAM_2026["action_date"],
        }
        self.assertEqual(
            assess_cross_source_chronology(notice, award, source_observed_at=OBSERVED),
            "UNMATCHED_OR_UNKNOWN",
        )
        notice["solicitation_number"] = SAM_2026["award_number"]
        self.assertEqual(
            assess_cross_source_chronology(notice, award, source_observed_at=OBSERVED),
            "FUTURE_POSTED_NOTICE_NOT_PREAWARD",
        )

    def test_ceiling_is_not_cash_or_proven_permissions(self):
        self.assertEqual(
            BASE_2025["base_award_value_usd"] + ARMY_2026["ceiling_increase_usd"],
            SAM_2026["base_and_all_options_usd"],
        )
        self.assertIsNone(ARMY_2026["obligated_at_modification_usd"])
        self.assertIsNone(SAM_2026["verified_customer_recoveries_usd"])
        self.assertIsNone(SAM_2026["source_bytes_sha256"])
        self.assertFalse(SAM_2026["verified_transaction_modification"])
        self.assertFalse(SAM_2026["source_specific_reuse_approved"])


if __name__ == "__main__":
    unittest.main()
