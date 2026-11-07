"""Research-only source-bound NAVSUP award identity / placeholder negative control.

Issuer-original public SAM.gov notice (published 2026-09-28):
https://sam.gov/workspace/contract/opp/f6f7933b2c16426ca7c3e8022d4e0f6a/view

Official structured fields name Notice ID N68836 but Related Notice
N6883626Q0063, Award N6883626P0074, CSIC SOLUTIONS LLC, UEI
RJSDHZERNDS3, award date 2026-09-25 and *base plus all options*
$99,000. Its narrative separately has literal unfilled [Insert ...]
contract, solicitation, date and value placeholders.

This fixture is a human transcription of publicly indexed agency text;
not proof of retained primary bytes, a transaction-level FPDS/USAspending
record, any award modification, a paid obligation, recoverable funds, or
source-specific commercial-reuse approval. It makes no additional claims
from a third-party opportunity cluster sharing generic ID N68836.
No network/D1, production code, workflow, deployment or customer data.
"""
from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone

from freight.capturebrief_sam_fy2027_asof import assess_cross_source_chronology

ORIGINAL = {
    "official_notice_url": (
        "https://sam.gov/workspace/contract/opp/"
        "f6f7933b2c16426ca7c3e8022d4e0f6a/view"
    ),
    "publisher": "DEPARTMENT OF THE NAVY",
    "office": "NAVSUP FLC JACKSONVILLE ERP",
    "agency_code": "DOD",
    "sam_opportunity_uuid": "f6f7933b2c16426ca7c3e8022d4e0f6a",
    "generic_notice_id": "N68836",
    "related_notice": "N6883626Q0063",
    "contract_award_number": "N6883626P0074",
    "contractor": "CSIC SOLUTIONS LLC",
    "awardee_uei": "RJSDHZERNDS3",
    "published_date": "2026-09-28",
    "award_date": "2026-09-25",
    "base_all_options_usd": 99_000,
    "narrative_contract_number": "[Insert Contract / PO Number, e.g., N68836-26-P-XXXX]",
    "narrative_solicitation_number": "[Insert Solicitation Number]",
    "narrative_award_date": "[Insert Award Date]",
    "source_raw_bytes_retained": False,
    "award_transaction_reconciled": False,
    "confirmed_contract_modifications": None,
    "transaction_obligated_usd": None,
    "verified_customer_recovery_usd": None,
    "source_reuse_permission_verified": False,
}

# Static transcription anchor is only an internal anti-corruption check.
# It is NOT independent cryptographic authentication of issuer bytes.
ANCHOR = (
    ("sam_opportunity_uuid", "f6f7933b2c16426ca7c3e8022d4e0f6a"),
    ("publisher", "DEPARTMENT OF THE NAVY"),
    ("office", "NAVSUP FLC JACKSONVILLE ERP"),
    ("generic_notice_id", "N68836"),
    ("related_notice", "N6883626Q0063"),
    ("contract_award_number", "N6883626P0074"),
    ("contractor", "CSIC SOLUTIONS LLC"),
    ("awardee_uei", "RJSDHZERNDS3"),
    ("published_date", "2026-09-28"),
    ("award_date", "2026-09-25"),
    ("base_all_options_usd", 99_000),
)


def adjudicate_notice_join(original: dict, proposed: dict) -> str:
    """Fail closed on misleading generic notice IDs and narrative placeholders.

    This is a fixture-specific research gate, not a production matcher or
    independently authenticated transaction-level award benchmark.
    """
    if type(original) is not dict or type(proposed) is not dict:
        return "UNKNOWN_MALFORMED_SOURCE"
    if (
        original.get("official_notice_url") != ORIGINAL["official_notice_url"]
        or any(original.get(field) != value for field, value in ANCHOR)
    ):
        return "UNKNOWN_UNAUTHENTICATED_TRANSCRIPTION"
    if (
        proposed.get("sam_opportunity_uuid") != original["sam_opportunity_uuid"]
        or proposed.get("publisher") != original["publisher"]
        or proposed.get("office") != original["office"]
    ):
        return "REJECT_UNMATCHED_ORIGINAL_NOTICE"
    if proposed.get("solicitation_identifier") != original["related_notice"]:
        return "REJECT_GENERIC_NOTICE_ID_AS_SOLICITATION"
    if (
        proposed.get("contract_award_number") != original["contract_award_number"]
        or proposed.get("contractor") != original["contractor"]
        or proposed.get("awardee_uei") != original["awardee_uei"]
    ):
        return "REJECT_UNMATCHED_AWARD_IDENTITY"
    if (
        proposed.get("award_date") != original["award_date"]
        or proposed.get("base_all_options_usd") != original["base_all_options_usd"]
    ):
        return "REJECT_UNMATCHED_AWARD_DATE_OR_VALUE"
    if (
        proposed.get("claimed_obligated_usd") is not None
        or proposed.get("claimed_customer_recovery_usd") is not None
        or proposed.get("claimed_modification") is not None
    ):
        return "REJECT_UNVERIFIED_TRANSACTION_OR_CASH_CLAIM"
    return "OFFICIAL_NOTICE_FIELDS_CONSISTENT_AWARD_TRANSACTION_UNKNOWN"


def candidate() -> dict:
    return {
        "sam_opportunity_uuid": ORIGINAL["sam_opportunity_uuid"],
        "publisher": ORIGINAL["publisher"],
        "office": ORIGINAL["office"],
        "solicitation_identifier": ORIGINAL["related_notice"],
        "contract_award_number": ORIGINAL["contract_award_number"],
        "contractor": ORIGINAL["contractor"],
        "awardee_uei": ORIGINAL["awardee_uei"],
        "award_date": ORIGINAL["award_date"],
        "base_all_options_usd": ORIGINAL["base_all_options_usd"],
        "claimed_obligated_usd": None,
        "claimed_customer_recovery_usd": None,
        "claimed_modification": None,
    }


class NavyJacksonville2026OfficialAwardPlaceholderNegativeControl(unittest.TestCase):
    def test_original_structured_fields_and_narrative_are_distinct(self):
        self.assertEqual(ORIGINAL["generic_notice_id"], "N68836")
        self.assertNotEqual(ORIGINAL["generic_notice_id"], ORIGINAL["related_notice"])
        self.assertNotEqual(ORIGINAL["related_notice"], ORIGINAL["contract_award_number"])
        self.assertEqual(ORIGINAL["base_all_options_usd"], 99_000)
        self.assertTrue(ORIGINAL["narrative_contract_number"].startswith("[Insert "))
        self.assertTrue(ORIGINAL["narrative_solicitation_number"].startswith("[Insert "))
        self.assertEqual(
            adjudicate_notice_join(ORIGINAL, candidate()),
            "OFFICIAL_NOTICE_FIELDS_CONSISTENT_AWARD_TRANSACTION_UNKNOWN",
        )

    def test_generic_notice_id_is_not_a_solicitation_join_key(self):
        bad = candidate()
        bad["solicitation_identifier"] = ORIGINAL["generic_notice_id"]
        self.assertEqual(
            adjudicate_notice_join(ORIGINAL, bad),
            "REJECT_GENERIC_NOTICE_ID_AS_SOLICITATION",
        )
        bad["solicitation_identifier"] = ORIGINAL["narrative_solicitation_number"]
        self.assertEqual(
            adjudicate_notice_join(ORIGINAL, bad),
            "REJECT_GENERIC_NOTICE_ID_AS_SOLICITATION",
        )

    def test_other_award_or_vendor_is_not_this_award(self):
        for field, wrong in (
            ("contract_award_number", "N6883625PS026"),
            ("contract_award_number", ORIGINAL["narrative_contract_number"]),
            ("contractor", "BUSINESS PREP, LLC"),
            ("awardee_uei", "TMGZB1SH1FL1"),
        ):
            with self.subTest(field=field, wrong=wrong):
                bad = candidate()
                bad[field] = wrong
                self.assertEqual(
                    adjudicate_notice_join(ORIGINAL, bad),
                    "REJECT_UNMATCHED_AWARD_IDENTITY",
                )
        bad_original = copy.deepcopy(ORIGINAL)
        bad_original["related_notice"] = "N68836"
        self.assertEqual(
            adjudicate_notice_join(bad_original, candidate()),
            "UNKNOWN_UNAUTHENTICATED_TRANSCRIPTION",
        )

    def test_options_ceiling_is_not_obligated_or_recovered_cash(self):
        for field in ("claimed_obligated_usd", "claimed_customer_recovery_usd"):
            bad = candidate()
            bad[field] = 99_000
            self.assertEqual(
                adjudicate_notice_join(ORIGINAL, bad),
                "REJECT_UNVERIFIED_TRANSACTION_OR_CASH_CLAIM",
            )
        bad = candidate()
        bad["claimed_modification"] = "P00001"
        self.assertEqual(
            adjudicate_notice_join(ORIGINAL, bad),
            "REJECT_UNVERIFIED_TRANSACTION_OR_CASH_CLAIM",
        )
        self.assertIsNone(ORIGINAL["confirmed_contract_modifications"])

    def test_award_notice_is_not_preaward_opportunity_at_source_readback(self):
        notice = {
            "solicitation_number": ORIGINAL["related_notice"],
            "agency_code": ORIGINAL["agency_code"],
            "office": ORIGINAL["office"],
            "posted_date": ORIGINAL["published_date"],
        }
        award = {
            "solicitation_identifier": ORIGINAL["related_notice"],
            "matched_issuer_agency_code": ORIGINAL["agency_code"],
            "matched_issuer_office": ORIGINAL["office"],
            "award_date_signed": ORIGINAL["award_date"],
        }
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award,
                source_observed_at=datetime(2026, 11, 6, tzinfo=timezone.utc),
            ),
            "FUTURE_POSTED_NOTICE_NOT_PREAWARD",
        )
        award["solicitation_identifier"] = ORIGINAL["generic_notice_id"]
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award,
                source_observed_at=datetime(2026, 11, 6, tzinfo=timezone.utc),
            ),
            "UNMATCHED_OR_UNKNOWN",
        )


if __name__ == "__main__":
    unittest.main()
