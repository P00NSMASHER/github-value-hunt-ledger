"""RETALLY issuer-original negative control: Boeing VC-25B May 2026 award date.

First-party U.S. Department of War published contracts:
May 6: https://www.war.gov/News/Contracts/Contract/Article/4479042/contracts-for-may-6-2026/
May 12: https://www.war.gov/News/Contracts/Contract/Article/4483936/contracts-for-may-12-2026/

May 6: Boeing Co., Tukwila; FA8625-16-C-6599; modification P00176;
$125,000,000 maximum; $41,925,000 obligated at time of award.
May 12 CORRECTION: May 6 announcement was incorrect; actual award May 8.

Public official search-index transcriptions checked 2026-11-06; direct
HTML read HTTP 403. No original bytes, original SHA, independently reconciled
transaction, solicitation ID, complete modification history, source reuse
rights, customer recovery or payments. Falsifies an *award on May 6* claim
only; NOT A VALIDATED AWARD BENCHMARK. No production actions or D1 reads.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import unittest

ORIGINAL = {
    "publisher": "U.S. Department of War",
    "url": "https://www.war.gov/News/Contracts/Contract/Article/4479042/contracts-for-may-6-2026/",
    "publication": "2026-05-06",
    "issuer": "DEPARTMENT OF THE AIR FORCE",
    "office": "Air Force Life Cycle Management Center, Wright-Patterson AFB",
    "contractor": "The Boeing Co.",
    "city": "Tukwila, Washington",
    "contract": "FA8625-16-C-6599",
    "modification": "P00176",
    "modification_ceiling_usd": 125_000_000,
    "obligated_at_award_usd": 41_925_000,
    "award_date": None,
    "solicitation": None,
}
CORRECTION = {
    "publisher": "U.S. Department of War",
    "url": "https://www.war.gov/News/Contracts/Contract/Article/4483936/contracts-for-may-12-2026/",
    "publication": "2026-05-12",
    "refers_to": "2026-05-06",
    "issuer": "DEPARTMENT OF THE AIR FORCE",
    "contractor": "The Boeing Co.",
    "city": "Tukwila, Washington",
    "contract": "FA8625-16-C-6599",
    "modification": "P00176",
    "modification_ceiling_usd": 125_000_000,
    "corrected_award_date": "2026-05-08",
    "explicit_correction": True,
}
PINNED_A, PINNED_B = deepcopy(ORIGINAL), deepcopy(CORRECTION)
UNKNOWN = "UNKNOWN_NO_ORIGINAL_TRANSACTION_OR_MISMATCHED_IDENTITY"


def adjudicate(original, correction, *, claimed_award_date, observed_asof):
    """Test-only issuer-publication discrepancy; never an award-label admission."""
    if (type(original) is not dict or type(correction) is not dict
            or original != PINNED_A or correction != PINNED_B
            or type(observed_asof) is not date):
        return UNKNOWN
    keys = ("publisher", "issuer", "contractor", "city", "contract",
            "modification", "modification_ceiling_usd")
    if any(original[k] != correction[k] for k in keys):
        return UNKNOWN
    if (correction["refers_to"] != original["publication"]
            or correction["explicit_correction"] is not True):
        return UNKNOWN
    try:
        published = date.fromisoformat(original["publication"])
        corrected = date.fromisoformat(correction["publication"])
        actual = date.fromisoformat(correction["corrected_award_date"])
        claimed = date.fromisoformat(claimed_award_date)
    except (ValueError, TypeError):
        return UNKNOWN
    if not published < actual < corrected:
        return UNKNOWN
    if observed_asof < published:
        return "NOT_YET_PUBLISHED"
    if observed_asof < corrected:
        return "CORRECTION_NOT_YET_KNOWN_ASOF"
    if claimed == published:
        return "FALSIFIED_ANNOUNCEMENT_DATE_AS_AWARD_DATE"
    if claimed == actual:
        return "MATCHES_CORRECTED_PUBLISHER_TEXT_TRANSACTION_UNKNOWN"
    return UNKNOWN


class BoeingVc25bAwardDateCorrection(unittest.TestCase):
    def test_source_correction_falsifies_may_six_award(self):
        self.assertIsNone(ORIGINAL["award_date"])
        self.assertEqual(adjudicate(
            ORIGINAL, CORRECTION, claimed_award_date="2026-05-06",
            observed_asof=date(2026, 11, 6)),
            "FALSIFIED_ANNOUNCEMENT_DATE_AS_AWARD_DATE")
        self.assertEqual(adjudicate(
            ORIGINAL, CORRECTION, claimed_award_date="2026-05-08",
            observed_asof=date(2026, 11, 6)),
            "MATCHES_CORRECTED_PUBLISHER_TEXT_TRANSACTION_UNKNOWN")

    def test_no_correction_leakage_into_past(self):
        self.assertEqual(adjudicate(ORIGINAL, CORRECTION,
            claimed_award_date="2026-05-08", observed_asof=date(2026, 5, 5)),
            "NOT_YET_PUBLISHED")
        for day in (6, 8, 11):
            self.assertEqual(adjudicate(ORIGINAL, CORRECTION,
                claimed_award_date="2026-05-08", observed_asof=date(2026, 5, day)),
                "CORRECTION_NOT_YET_KNOWN_ASOF")

    def test_wrong_issuer_contract_party_mod_or_amount_fails_closed(self):
        mutations = (("issuer", "NAVY"), ("contractor", "Other Supplier"),
                     ("contract", "FA8625-16-C-0000"), ("modification", "P00177"),
                     ("modification_ceiling_usd", 125_000_001))
        for field, value in mutations:
            with self.subTest(field=field):
                altered = deepcopy(CORRECTION)
                altered[field] = value
                self.assertEqual(adjudicate(ORIGINAL, altered,
                    claimed_award_date="2026-05-06",
                    observed_asof=date(2026, 11, 6)), UNKNOWN)

    def test_source_substitution_or_wrong_date_fails_closed(self):
        for field, value in (("url", "https://invalid.example/"),
                             ("refers_to", "2026-05-05"),
                             ("corrected_award_date", "2026-05-05"),
                             ("explicit_correction", False)):
            with self.subTest(field=field):
                altered = deepcopy(CORRECTION)
                altered[field] = value
                self.assertEqual(adjudicate(ORIGINAL, altered,
                    claimed_award_date="2026-05-06",
                    observed_asof=date(2026, 11, 6)), UNKNOWN)
        self.assertEqual(adjudicate(ORIGINAL, CORRECTION,
            claimed_award_date="2026-05-07", observed_asof=date(2026, 11, 6)),
            UNKNOWN)

    def test_modification_face_is_neither_obligation_nor_cash(self):
        self.assertEqual(ORIGINAL["modification_ceiling_usd"], 125_000_000)
        self.assertEqual(ORIGINAL["obligated_at_award_usd"], 41_925_000)
        self.assertEqual(125_000_000 - 41_925_000, 83_075_000)
        self.assertIsNone(ORIGINAL["solicitation"])
        for record in (ORIGINAL, CORRECTION):
            for missing in ("actual_disbursement_usd", "recovered_customer_cash_usd",
                            "original_body_sha256", "verified_issuer_transaction"):
                self.assertNotIn(missing, record)


if __name__ == "__main__":
    unittest.main()
