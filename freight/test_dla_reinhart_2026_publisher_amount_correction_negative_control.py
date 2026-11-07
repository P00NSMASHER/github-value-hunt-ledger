"""RETALLY evidence QA: DLA foodservice public announcement correction, research only.

Two Department of War original-publisher announcement pages indexed Nov 6, 2026:
 May 22: https://www.war.gov/News/Contracts/Contract/Article/4499778/contracts-for-may-22-2026/
 May 27: https://www.war.gov/News/Contracts/Contract/Article/4502028/contracts-for-may-27-2026/

May 22 announced maximum IDIQ amount $75,108,333 for DLA contract
SPE300-26-D-3015 awarded to Reinhart Foodservice LLC. May 27 explicitly
corrected the amount to $150,216,668 for the same original announcement.
Official source pages were indexed, but direct original-byte requests returned
HTTP 403. No authenticated independent award transaction, complete modification
history, independently verified solicitation, source rights, real recovery or
cash transfer was observed. Publisher-claim falsification ONLY. NOT a
validated award/financial benchmark; no network/D1/production code access.
"""
from __future__ import annotations

import copy
import unittest
from datetime import date

ORIGINAL = {
    "publisher": "U.S. Department of War",
    "publisher_date": "2026-05-22",
    "source_url": "https://www.war.gov/News/Contracts/Contract/Article/4499778/contracts-for-may-22-2026/",
    "agency": "Defense Logistics Agency Troop Support",
    "contracting_office": "Philadelphia, Pennsylvania",
    "contractor": "Reinhart Foodservice LLC",
    "contract_number": "SPE300-26-D-3015",
    "contract_type": "IDIQ_MAXIMUM",
    "published_maximum_usd": 75_108_333,
}
CORRECTION = {
    "publisher": "U.S. Department of War",
    "publisher_date": "2026-05-27",
    "source_url": "https://www.war.gov/News/Contracts/Contract/Article/4502028/contracts-for-may-27-2026/",
    "correction_of_date": "2026-05-22",
    "agency": "Defense Logistics Agency Troop Support",
    "contracting_office": "Philadelphia, Pennsylvania",
    "contractor": "Reinhart Foodservice LLC",
    "contract_number": "SPE300-26-D-3015",
    "superseded_published_maximum_usd": 75_108_333,
    "corrected_published_maximum_usd": 150_216_668,
}
PINNED_ORIGINAL = copy.deepcopy(ORIGINAL)
PINNED_CORRECTION = copy.deepcopy(CORRECTION)
UNKNOWN = "UNKNOWN_UNAUTHENTICATED_OR_MISMATCHED_PUBLISHER_CLAIM"
CORRECTED = "FALSIFIED_OLD_PUBLISHER_MAXIMUM_NOT_AWARD_TRANSACTION"


def adjudicate_publisher_amount_correction(original, correction, *, asof):
    """Evaluate two pinned publisher claims; no independent-award admission."""
    if (type(asof) is not date or type(original) is not dict
            or type(correction) is not dict
            or original != PINNED_ORIGINAL or correction != PINNED_CORRECTION):
        return UNKNOWN
    if any(original[key] != correction[key] for key in (
            "publisher", "agency", "contracting_office", "contractor",
            "contract_number")):
        return UNKNOWN
    if (correction["correction_of_date"] != original["publisher_date"]
            or correction["superseded_published_maximum_usd"]
            != original["published_maximum_usd"]
            or correction["corrected_published_maximum_usd"] <= 0
            or correction["corrected_published_maximum_usd"]
            == correction["superseded_published_maximum_usd"]):
        return UNKNOWN
    original_day = date.fromisoformat(original["publisher_date"])
    corrected_day = date.fromisoformat(correction["publisher_date"])
    if asof < original_day:
        return "NOT_YET_DATED_AT_PUBLISHER_SOURCE"
    if asof < corrected_day:
        return "CORRECTION_NOT_YET_DATED_AT_PUBLISHER_SOURCE"
    return CORRECTED


class DLAReinhartAmountCorrectionNegativeControls(unittest.TestCase):
    def test_publisher_correction_disproves_original_announced_maximum(self):
        self.assertEqual(adjudicate_publisher_amount_correction(
            ORIGINAL, CORRECTION, asof=date(2026, 11, 6)), CORRECTED)
        self.assertEqual(CORRECTION["corrected_published_maximum_usd"], 150_216_668)
        self.assertEqual(CORRECTION["superseded_published_maximum_usd"], 75_108_333)
        self.assertEqual(CORRECTION["corrected_published_maximum_usd"]
                         - ORIGINAL["published_maximum_usd"], 75_108_335)
        # The two maxima are NOT exactly 2x, nor two separate awards.
        self.assertEqual(CORRECTION["corrected_published_maximum_usd"]
                         - 2 * ORIGINAL["published_maximum_usd"], 2)

    def test_correction_cannot_backfill_earlier_publisher_dates(self):
        self.assertEqual(adjudicate_publisher_amount_correction(
            ORIGINAL, CORRECTION, asof=date(2026, 5, 21)),
            "NOT_YET_DATED_AT_PUBLISHER_SOURCE")
        for day in (date(2026, 5, 22), date(2026, 5, 26)):
            self.assertEqual(adjudicate_publisher_amount_correction(
                ORIGINAL, CORRECTION, asof=day),
                "CORRECTION_NOT_YET_DATED_AT_PUBLISHER_SOURCE")
        self.assertEqual(adjudicate_publisher_amount_correction(
            ORIGINAL, CORRECTION, asof=date(2026, 5, 27)), CORRECTED)

    def test_adversarial_issuer_party_identity_and_dollar_mismatches_rejected(self):
        mutations = (
            (0, "contract_number", "SPE300-26-D-XXXX"),
            (1, "contract_number", "SPE300-26-D-XXXX"),
            (0, "contractor", "unverified contractor"),
            (1, "agency", "Other government agency"),
            (1, "contracting_office", "unknown"),
            (0, "published_maximum_usd", 75_108_334),
            (1, "superseded_published_maximum_usd", 75_108_334),
            (1, "corrected_published_maximum_usd", 150_216_666),
            (1, "correction_of_date", "2026-05-23"),
            (1, "source_url", "https://example.org/not-original"),
            (1, "publisher_date", "2026-05-22"),
        )
        for position, field, bad in mutations:
            with self.subTest(field=field, position=position):
                source_pair = [copy.deepcopy(ORIGINAL), copy.deepcopy(CORRECTION)]
                source_pair[position][field] = bad
                self.assertEqual(adjudicate_publisher_amount_correction(
                    *source_pair, asof=date(2026, 11, 6)), UNKNOWN)

    def test_published_maximum_not_transaction_modification_or_cash(self):
        self.assertEqual(ORIGINAL["contract_type"], "IDIQ_MAXIMUM")
        self.assertNotEqual(ORIGINAL["source_url"], CORRECTION["source_url"])
        self.assertEqual(ORIGINAL["contract_number"], CORRECTION["contract_number"])
        for record in (ORIGINAL, CORRECTION):
            for absent_key in ("solicitation_number", "modification_number",
                               "complete_award_transaction", "obligated_usd",
                               "paid_usd", "customer_recovery_usd",
                               "cash_received_usd", "source_reuse_authorized"):
                self.assertNotIn(absent_key, record)


if __name__ == "__main__":
    unittest.main()
