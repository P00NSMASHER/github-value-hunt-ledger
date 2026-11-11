"""First-party federal contract announcement correction: $15B -> $15M.

Primary publisher records, inspected 2026-11-06 through indexed public
Department of War publisher pages (HTML GET returned 403 to this client):
  https://www.war.gov/News/Contracts/Contract/Article/4401832/contracts-for-feb-9-2026/
  https://www.war.gov/News/Contracts/Contract/Article/4406926/contracts-for-feb-13-2026/

The Feb 9 announcement gives a $15,000,000,000 MAXIMUM blanket purchase
agreement (FA8571-26-A-0003) to Alabama Institute for Deaf & Blind;
the Feb 13 first-party correction explicitly says the CORRECT amount was
$15,000,000.  The correction refers to "Feb. 9, 2025", while the matching
published announcement is headed "Feb. 9, 2026". Do NOT silently repair
this reference-date contradiction; award ID/issuer/recipient/erroneous amount
match, but the reference-year field is CONFLICTING/UNKNOWN.

This source-bound publisher-claim falsification is NOT original-byte custody,
an independent award transaction, a modification history, proof of payment,
recovery, solicitation identification, source reuse rights, or a benchmark
ground-truth label. No D1 read, network request, feature or deploy change.
"""
from __future__ import annotations

import copy
import unittest

ORIGINAL_ANNOUNCEMENT = {
    "publisher": "U.S. Department of War",
    "issuer": "Air Force Sustainment Center Installation Maintenance Contracting Division",
    "office": "Robins Air Force Base, Georgia",
    "page_date": "2026-02-09",
    "award_id": "FA8571-26-A-0003",
    "contractor": "Alabama Institute for Deaf & Blind",
    "contract_vehicle": "blanket purchase agreement",
    "reported_maximum_usd": 15_000_000_000,
    "funds_obligated_at_award_usd": 0,
    "solicitation_id": None,
    "contract_modification_number": None,
}
CORRECTION = {
    "publisher": "U.S. Department of War",
    "issuer": "Air Force Sustainment Center Installation Maintenance Contracting Division",
    "office": "Robins Air Force Base, Georgia",
    "page_date": "2026-02-13",
    "referenced_announcement_date": "2025-02-09",
    "award_id": "FA8571-26-A-0003",
    "contractor": "Alabama Institute for Deaf & Blind",
    "original_amount_identified_as_wrong_usd": 15_000_000_000,
    "corrected_maximum_usd": 15_000_000,
    "contract_modification_number": None,
}

# Fixed first-party-page metadata anchors, NOT hashes of original pages.
# Treat any source/claim joint edits as unverified, never as independent proof.
ORIGINAL_ANCHORS = copy.deepcopy(ORIGINAL_ANNOUNCEMENT)
CORRECTION_ANCHORS = copy.deepcopy(CORRECTION)


def adjudicate_publisher_correction(original, correction):
    """Falsify the first announcement's reported ceiling; never award/cash."""
    if not isinstance(original, dict) or not isinstance(correction, dict):
        return "UNKNOWN_SOURCE_NOT_AUTHENTICATED"
    if original != ORIGINAL_ANCHORS or correction != CORRECTION_ANCHORS:
        return "UNKNOWN_SOURCE_NOT_AUTHENTICATED"
    if (original["publisher"] != correction["publisher"]
            or original["issuer"] != correction["issuer"]
            or original["office"] != correction["office"]
            or original["award_id"] != correction["award_id"]
            or original["contractor"] != correction["contractor"]
            or original["reported_maximum_usd"] !=
            correction["original_amount_identified_as_wrong_usd"]):
        return "UNKNOWN_UNMATCHED_RECORD"
    if correction["page_date"] <= original["page_date"]:
        return "UNKNOWN_BAD_CHRONOLOGY"
    if original["reported_maximum_usd"] != correction["corrected_maximum_usd"]:
        return "FALSIFIED_ORIGINAL_ANNOUNCEMENT_CEILING_NOT_AWARD_CASH"
    return "SOURCE_CONSISTENT_NOT_TRANSACTION_VERIFIED"


class AirForceBpaThousandfoldCorrectionNegativeControl(unittest.TestCase):
    def test_official_publisher_corrected_thousandfold_maximum(self):
        self.assertEqual(
            adjudicate_publisher_correction(
                ORIGINAL_ANNOUNCEMENT, CORRECTION
            ),
            "FALSIFIED_ORIGINAL_ANNOUNCEMENT_CEILING_NOT_AWARD_CASH",
        )
        self.assertEqual(
            ORIGINAL_ANNOUNCEMENT["reported_maximum_usd"]
            // CORRECTION["corrected_maximum_usd"],
            1_000,
        )

    def test_same_award_id_but_other_recipient_issuer_or_amount_is_not_a_match(self):
        for key, bad in (
            ("award_id", "FA8571-26-A-9999"),
            ("contractor", "OTHER CONTRACTOR"),
            ("issuer", "Other issuing office"),
            ("reported_maximum_usd", 15_000_000),
            ("funds_obligated_at_award_usd", 15_000_000),
        ):
            with self.subTest(key=key):
                edited = copy.deepcopy(ORIGINAL_ANNOUNCEMENT)
                edited[key] = bad
                self.assertEqual(
                    adjudicate_publisher_correction(edited, CORRECTION),
                    "UNKNOWN_SOURCE_NOT_AUTHENTICATED",
                )

    def test_coordinated_source_and_claim_forgery_cannot_pass(self):
        for key, fake in (
            ("corrected_maximum_usd", 15_000_000_000),
            ("original_amount_identified_as_wrong_usd", 42_000_000_000),
            ("contractor", "FABRICATED VENDOR"),
            ("award_id", "FA8571-26-A-9000"),
        ):
            with self.subTest(key=key):
                original, correction = (copy.deepcopy(ORIGINAL_ANNOUNCEMENT),
                                        copy.deepcopy(CORRECTION))
                correction[key] = fake
                if key == "contractor" or key == "award_id":
                    original[key] = fake
                elif key == "original_amount_identified_as_wrong_usd":
                    original["reported_maximum_usd"] = fake
                self.assertEqual(
                    adjudicate_publisher_correction(original, correction),
                    "UNKNOWN_SOURCE_NOT_AUTHENTICATED",
                )

    def test_correction_reference_year_conflicts_with_actual_page_date(self):
        # The correction literally names 2025, while the matching original
        # publisher article is dated 2026. Never invent a 2025 source capture.
        self.assertEqual(
            CORRECTION["referenced_announcement_date"], "2025-02-09"
        )
        self.assertEqual(ORIGINAL_ANNOUNCEMENT["page_date"], "2026-02-09")
        self.assertNotEqual(
            CORRECTION["referenced_announcement_date"],
            ORIGINAL_ANNOUNCEMENT["page_date"],
        )

    def test_maximum_is_not_obligation_modification_or_recovery(self):
        self.assertEqual(ORIGINAL_ANNOUNCEMENT["contract_vehicle"],
                         "blanket purchase agreement")
        self.assertEqual(ORIGINAL_ANNOUNCEMENT["funds_obligated_at_award_usd"],
                         0)  # Explicitly "no funds" in the original release.
        self.assertIsNone(ORIGINAL_ANNOUNCEMENT["solicitation_id"])
        self.assertIsNone(ORIGINAL_ANNOUNCEMENT["contract_modification_number"])
        self.assertIsNone(CORRECTION["contract_modification_number"])
        self.assertNotIn("customer_recovery_usd", CORRECTION)
        self.assertNotIn("cash_paid_usd", ORIGINAL_ANNOUNCEMENT)
        self.assertNotIn("independent_transaction_verified", CORRECTION)


if __name__ == "__main__":
    unittest.main()
