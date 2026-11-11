"""Research-only negative control: DLA/Boeing P-8A June 2026 order-number correction.

Original issuer announcements:
2026-06-18 https://www.war.gov/News/Contracts/Contract/Article/4521873/contracts-for-june-18-2026/
2026-06-23 https://www.war.gov/News/Contracts/Contract/Article/4524437/contracts-for-june-23-2026/
Publisher-indexed official-page text inspected 2026-11-06. Direct source HTML was
not retained or independently SHA-verified. No contract-system transaction, source
reuse permission, solicitation, payment or recovery has been verified. Not a
validated award benchmark. No network, customer data or D1.
"""
from copy import deepcopy
from datetime import date
import unittest

ORIGINAL = {
    "publisher": "U.S. Department of War", "published": "2026-06-18",
    "url": "https://www.war.gov/News/Contracts/Contract/Article/4521873/contracts-for-june-18-2026/",
    "issuer": "Defense Logistics Agency Weapons Support, Philadelphia, Pennsylvania",
    "contractor": "The Boeing Co.", "city": "St. Louis, Missouri",
    "contract": "SPRPA1-23-D-9003", "mod": "P00038",
    "mod_estimate_usd": 55_424_101, "order": "SPRPA1-26-F-0016",
    "order_estimate_usd": 18_474_700, "solicitation": None,
}
CORRECTION = {
    "publisher": "U.S. Department of War", "published": "2026-06-23",
    "url": "https://www.war.gov/News/Contracts/Contract/Article/4524437/contracts-for-june-23-2026/",
    "corrects": "2026-06-18",
    "issuer": "Defense Logistics Agency Weapons Support, Philadelphia, Pennsylvania",
    "contractor": "The Boeing Co.", "city": "St. Louis, Missouri",
    "contract": "SPRPA1-23-D-9003", "mod": "P00038",
    "mod_estimate_usd": 55_424_101,
    "old_order": "SPRPA1-26-F-0016", "new_order": "SPRPA1-26-F-0018",
    "order_estimate_usd": 18_474_700, "is_correction": True,
}
PINNED_A, PINNED_B = deepcopy(ORIGINAL), deepcopy(CORRECTION)
UNKNOWN = "UNKNOWN_IDENTITY_OR_SOURCE_NOT_INDEPENDENTLY_RECONCILED"


def classify(a, b, claimed_order, as_of):
    """Publisher-text contradiction only, not award/entitlement verification."""
    if type(a) is not dict or type(b) is not dict or type(as_of) is not date:
        return UNKNOWN
    if a != PINNED_A or b != PINNED_B:
        return UNKNOWN
    shared = ("publisher", "issuer", "contractor", "city", "contract",
              "mod", "mod_estimate_usd", "order_estimate_usd")
    if (any(a[k] != b[k] for k in shared)
            or b["corrects"] != a["published"]
            or b["old_order"] != a["order"] or b["is_correction"] is not True):
        return UNKNOWN
    original_day, correction_day = date.fromisoformat(a["published"]), date.fromisoformat(b["published"])
    if original_day >= correction_day:
        return UNKNOWN
    if as_of < original_day:
        return "NOT_YET_ANNOUNCED"
    if as_of < correction_day:
        # No contemporaneous capture in custody: cannot claim an as-of June original.
        return "HISTORICAL_ASOF_SOURCE_CUSTODY_UNKNOWN"
    if claimed_order == a["order"]:
        return "FALSIFIED_BY_ISSUER_ORDER_ID_CORRECTION"
    if claimed_order == b["new_order"]:
        return "CORRECTED_PUBLISHER_TEXT_MATCH_TRANSACTION_UNKNOWN"
    return UNKNOWN


class DlaBoeingP8aOrderCorrection(unittest.TestCase):
    def test_original_wrong_order_number_falsified_but_award_not_validated(self):
        self.assertEqual(classify(ORIGINAL, CORRECTION, "SPRPA1-26-F-0016", date(2026, 11, 6)),
                         "FALSIFIED_BY_ISSUER_ORDER_ID_CORRECTION")
        self.assertEqual(classify(ORIGINAL, CORRECTION, "SPRPA1-26-F-0018", date(2026, 11, 6)),
                         "CORRECTED_PUBLISHER_TEXT_MATCH_TRANSACTION_UNKNOWN")

    def test_no_unobserved_historical_backfill(self):
        self.assertEqual(classify(ORIGINAL, CORRECTION, ORIGINAL["order"], date(2026, 6, 17)),
                         "NOT_YET_ANNOUNCED")
        for day in (18, 22):
            self.assertEqual(classify(ORIGINAL, CORRECTION, ORIGINAL["order"], date(2026, 6, day)),
                             "HISTORICAL_ASOF_SOURCE_CUSTODY_UNKNOWN")

    def test_foreign_issuer_order_mod_amount_provenance_fail_closed(self):
        for field, value in (("issuer", "NAVY"), ("contractor", "Other Inc."),
                             ("contract", "SPRPA1-23-D-9999"), ("mod", "P00039"),
                             ("mod_estimate_usd", 55_424_102),
                             ("order_estimate_usd", 18_474_701),
                             ("url", "https://invalid.example/"),
                             ("corrects", "2026-06-17"),
                             ("new_order", "SPRPA1-26-F-0016"), ("is_correction", False)):
            with self.subTest(field=field):
                changed = deepcopy(CORRECTION)
                changed[field] = value
                self.assertEqual(classify(ORIGINAL, changed, ORIGINAL["order"], date(2026, 11, 6)),
                                 UNKNOWN)
        self.assertEqual(classify(ORIGINAL, CORRECTION, "SPRPA1-26-F-9999", date(2026, 11, 6)),
                         UNKNOWN)

    def test_modification_order_and_money_are_distinct(self):
        self.assertNotEqual(ORIGINAL["mod"], ORIGINAL["order"])
        self.assertEqual(ORIGINAL["mod_estimate_usd"], 55_424_101)
        self.assertEqual(ORIGINAL["order_estimate_usd"], 18_474_700)
        self.assertIsNone(ORIGINAL["solicitation"])
        for record in (ORIGINAL, CORRECTION):
            for absent in ("recovered_cash", "paid_amount", "transaction_verified",
                           "source_original_sha256", "independently_validated_award"):
                self.assertNotIn(absent, record)


if __name__ == "__main__":
    unittest.main()
