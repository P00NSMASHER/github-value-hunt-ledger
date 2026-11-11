"""DoW/Air Force public award-notice duplicate and modification negative control.

Official publisher pages examined in public index on 2026-11-06:
 Dec 12 2025: https://www.war.gov/News/Contracts/Contract/Article/4358989/contracts-for-dec-12-2025/
 Jun  5 2026: https://www.war.gov/News/Contracts/Contract/Article/4510415/contracts-for-june-5-2026/
 Jun  9 2026: https://www.war.gov/News/Contracts/Contract/Article/4512718/contracts-for-june-9-2026/

June 9 publisher CORRECTION explicitly calls the June 5 base entry a
duplicate and replaces it with $280,715,050 modification P00001.

Research-only human-transcribed first-party publisher claims. Issuer HTML
direct GET returned 403, so original bytes/hashes and independent award
transaction, full modification history, source rights, money recovered,
and any cash transfer are UNVERIFIED. No commercial benchmark.
No live API, D1, production, deploy or customer access.
"""
from __future__ import annotations

import copy
import unittest
from datetime import date

BASE = {
    "page_date": "2025-12-12",
    "issuer": "Air Force Life Cycle Management Center",
    "office": "Eglin Air Force Base, Florida",
    "contractor": "Kongsberg Defence & Aerospace",
    "contract_id": "FA8681-26-C-B002",
    "action": "BASE_CONTRACT",
    "modification": None,
    "lot": "TWO",
    "amount_usd": 240_904_098,
    "obligated_fy2024_usd": 137_970_866,
    "obligated_fy2025_usd": 102_933_232,
}
DUPLICATE = {**BASE, "page_date": "2026-06-05"}
CORRECTION = {
    "page_date": "2026-06-09",
    "corrected_announcement_date": "2026-06-05",
    "issuer": "Air Force Life Cycle Management Center",
    "office": "Eglin Air Force Base, Florida",
    "contractor": "Kongsberg Defence & Aerospace",
    "contract_id": "FA8681-26-C-B002",
    "action": "MODIFICATION",
    "modification": "P00001",
    "lot": "THREE",
    "amount_usd": 280_715_050,
    "obligated_fy2024_usd": 195_464,
    "obligated_fy2025_usd": 280_519_586,
    "correction_labels_june5_as_duplicate": True,
}
# Fixed publisher-page transcription anchors; NOT original-byte fingerprints.
ANCHORS = tuple(copy.deepcopy(item) for item in (BASE, DUPLICATE, CORRECTION))
UNKNOWN = "UNKNOWN_OR_UNAUTHENTICATED_PUBLISHER_IDENTITY"


def adjudicate_publisher_duplicate(original, repost, correction, *, asof):
    """Offline evidence-QA gate only; never a payment or contract truth label."""
    if type(asof) is not date or any(
        type(item) is not dict or item != anchor
        for item, anchor in zip((original, repost, correction), ANCHORS)
    ):
        return UNKNOWN
    if asof < date.fromisoformat(correction["page_date"]):
        return "CORRECTION_NOT_PUBLISHED_AS_OF_DATE"
    if (not correction["correction_labels_june5_as_duplicate"]
            or repost["page_date"] != correction["corrected_announcement_date"]
            or not (original["page_date"] < repost["page_date"] < correction["page_date"])
            or any(original[key] != repost[key] for key in original if key != "page_date")
            or any(original[key] != correction[key]
                   for key in ("issuer", "office", "contractor", "contract_id"))
            or original["action"] != "BASE_CONTRACT"
            or correction["action"] != "MODIFICATION"
            or original["modification"] is not None
            or correction["modification"] != "P00001"):
        return UNKNOWN
    return "FALSIFIED_JUNE5_SECOND_BASE_AWARD_CORRECTED_TO_P00001"


class KongsbergDuplicateAwardNegativeControls(unittest.TestCase):
    def test_first_party_correction_falsifies_second_base_award(self):
        self.assertEqual(
            adjudicate_publisher_duplicate(BASE, DUPLICATE, CORRECTION,
                                           asof=date(2026, 11, 6)),
            "FALSIFIED_JUNE5_SECOND_BASE_AWARD_CORRECTED_TO_P00001",
        )
        self.assertEqual(BASE["contract_id"], CORRECTION["contract_id"])
        self.assertEqual(BASE["action"], "BASE_CONTRACT")
        self.assertEqual(CORRECTION["modification"], "P00001")
        self.assertNotEqual(BASE["lot"], CORRECTION["lot"])

    def test_duplicate_new_base_award_overstatement_is_240904098(self):
        # Difference in apparent base award count, NOT contract ceiling/cash.
        self.assertEqual(BASE["amount_usd"] + DUPLICATE["amount_usd"]
                         - BASE["amount_usd"], 240_904_098)
        self.assertEqual(BASE["amount_usd"], DUPLICATE["amount_usd"])
        for action in (BASE, CORRECTION):
            self.assertEqual(action["obligated_fy2024_usd"]
                             + action["obligated_fy2025_usd"],
                             action["amount_usd"])

    def test_correction_cannot_be_backdated_to_june5(self):
        for day in (date(2026, 6, 5), date(2026, 6, 8)):
            self.assertEqual(
                adjudicate_publisher_duplicate(BASE, DUPLICATE, CORRECTION,
                                               asof=day),
                "CORRECTION_NOT_PUBLISHED_AS_OF_DATE",
            )

    def test_mismatched_original_party_id_amount_or_modification_fails_closed(self):
        for idx, field, value in (
            (0, "contract_id", "FA8681-26-C-B999"),
            (1, "contractor", "OTHER RECIPIENT"),
            (2, "issuer", "UNRELATED ISSUER"),
            (1, "amount_usd", 240_904_099),
            (2, "modification", "P00002"),
            (2, "lot", "TWO"),
            (2, "correction_labels_june5_as_duplicate", False),
            (2, "corrected_announcement_date", "2026-06-06"),
        ):
            with self.subTest(field=field):
                records = list(copy.deepcopy(ANCHORS))
                records[idx][field] = value
                self.assertEqual(
                    adjudicate_publisher_duplicate(*records,
                                                   asof=date(2026, 11, 6)),
                    UNKNOWN,
                )

    def test_same_contract_id_on_two_pages_is_not_two_independent_awards(self):
        self.assertEqual(BASE["contract_id"], DUPLICATE["contract_id"])
        self.assertEqual(BASE["action"], DUPLICATE["action"])
        self.assertEqual(BASE["modification"], DUPLICATE["modification"])
        self.assertNotEqual(DUPLICATE["page_date"], CORRECTION["page_date"])

    def test_solicitation_history_legal_rights_transaction_and_cash_unknown(self):
        for item in ANCHORS:
            for key in ("solicitation_id", "independent_award_transaction_verified",
                        "all_modifications_reconciled", "customer_recovery_usd",
                        "cleared_cash_usd", "commercial_source_reuse_approved"):
                self.assertNotIn(key, item)
        self.assertIsNone(BASE["modification"])
        self.assertEqual(CORRECTION["modification"], "P00001")


if __name__ == "__main__":
    unittest.main()
