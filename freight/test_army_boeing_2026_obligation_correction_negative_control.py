"""First-party issuer correction: original obligation claim is superseded.

U.S. Department of War / Army contract announcements:
Aug 14, 2026: https://www.war.gov/News/Contracts/Contract/Article/4574365/contracts-for-aug-14-2026/
Aug 17, 2026: https://www.war.gov/News/Contracts/Contract/Article/4575681/contracts-for-aug-17-2026/

The later original-publisher correction for the exact Boeing / Army contract
W58RGZ-24-C-0028 and modification PZ0022 changes reported FY2026 Army
working-capital obligation at award from $506,314,739 to $82,091,260.
The modification's FACE value remains $636,110,315; the cumulative contract
face remains $1,128,815,031. Neither face amount represents cash recovered.

Human-transcribed government search-index record; original HTML bytes/digest
were NOT retained. No independent FPDS/USAspending transaction reconciliation,
source-reuse approval, actual disbursement or customer recovery. This test
falsifies a superseded *issuer-published statement*, NOT contract payment or
a validated award-prediction benchmark. No production D1 or external effects.
"""
import copy
import unittest
from datetime import date

ORIGINAL = {
    "publisher": "U.S. Department of War",
    "issuer": "DEPARTMENT OF THE ARMY",
    "office": "ARMY CONTRACTING COMMAND, REDSTONE ARSENAL",
    "contractor": "THE BOEING CO.",
    "contract": "W58RGZ-24-C-0028",
    "modification": "PZ0022",
    "date": "2026-08-14",
    "face_usd": 636_110_315,
    "cumulative_face_usd": 1_128_815_031,
    "obligation_usd": 506_314_739,
}
CORRECTION = {
    "publisher": "U.S. Department of War",
    "issuer": "DEPARTMENT OF THE ARMY",
    "office": "ARMY CONTRACTING COMMAND, REDSTONE ARSENAL",
    "contractor": "THE BOEING CO.",
    "contract": "W58RGZ-24-C-0028",
    "modification": "PZ0022",
    "date": "2026-08-17",
    "refers_to_date": "2026-08-14",
    "face_usd": 636_110_315,
    "corrected_obligation_usd": 82_091_260,
    "explicit_funding_correction": True,
}
PROVENANCE = {
    "first_party_publisher_pages_found": True,
    "raw_primary_bytes_retained": False,
    "raw_primary_sha256": None,
    "independent_contract_transaction_verified": False,
    "commercial_reuse_approved": False,
    "validated_benchmark": False,
    "verified_customer_recovery_usd": None,
}


def gate(original, correction, candidate_usd, observed_on):
    """Check issuer-published correction against candidate, fail closed."""
    if type(original) is not dict or type(correction) is not dict:
        return "UNKNOWN_MALFORMED_SOURCE"
    identity = ("publisher", "issuer", "office", "contractor", "contract",
                "modification")
    if any(not isinstance(original.get(k), str)
           or not original[k].strip() or original[k] != correction.get(k)
           for k in identity):
        return "UNKNOWN_CORRECTION_IDENTITY_MISMATCH"
    if any(type(original.get(k)) is not int or original[k] <= 0
           for k in ("face_usd", "cumulative_face_usd", "obligation_usd")):
        return "UNKNOWN_ORIGINAL_FINANCIAL_FIELDS"
    if (type(correction.get("face_usd")) is not int
            or correction["face_usd"] != original["face_usd"]):
        return "UNKNOWN_MODIFICATION_FACE_MISMATCH"
    if (type(correction.get("corrected_obligation_usd")) is not int
            or correction["corrected_obligation_usd"] < 0
            or correction.get("explicit_funding_correction") is not True):
        return "UNKNOWN_CORRECTION_ORIGINALITY"
    try:
        old = date.fromisoformat(original["date"])
        new = date.fromisoformat(correction["date"])
        referenced = date.fromisoformat(correction["refers_to_date"])
        observed = date.fromisoformat(observed_on)
    except (ValueError, KeyError, TypeError):
        return "UNKNOWN_CHRONOLOGY"
    if referenced != old or new <= old:
        return "UNKNOWN_CORRECTION_CHRONOLOGY"
    if observed < old:
        return "NO_NOTICE_YET_ASOF"
    if observed < new:
        return "OLD_PUBLICATION_ONLY_NOT_CORRECTED_ASOF"
    if type(candidate_usd) is not int:
        return "UNKNOWN_CANDIDATE_AMOUNT"
    if (candidate_usd == original["obligation_usd"]
            and candidate_usd != correction["corrected_obligation_usd"]):
        return "FALSIFIED_SUPERSEDED_ISSUER_OBLIGATION"
    if candidate_usd == correction["corrected_obligation_usd"]:
        return "MATCHES_CORRECTED_ISSUER_TEXT_TRANSACTION_UNKNOWN"
    return "UNKNOWN_UNSUPPORTED_AMOUNT"


class ArmyBoeingCorrectionNegativeControl(unittest.TestCase):
    def test_superseded_obligation_falsified(self):
        self.assertEqual(gate(ORIGINAL, CORRECTION, 506_314_739, "2026-11-06"),
                         "FALSIFIED_SUPERSEDED_ISSUER_OBLIGATION")
        self.assertEqual(506_314_739 - 82_091_260, 424_223_479)

    def test_corrected_publication_is_not_cash(self):
        self.assertEqual(gate(ORIGINAL, CORRECTION, 82_091_260, "2026-11-06"),
                         "MATCHES_CORRECTED_ISSUER_TEXT_TRANSACTION_UNKNOWN")
        self.assertNotEqual(ORIGINAL["face_usd"], 82_091_260)
        self.assertFalse(PROVENANCE["independent_contract_transaction_verified"])
        self.assertFalse(PROVENANCE["validated_benchmark"])
        self.assertIsNone(PROVENANCE["verified_customer_recovery_usd"])

    def test_no_future_leakage_from_correction(self):
        self.assertEqual(gate(ORIGINAL, CORRECTION, 506_314_739, "2026-08-16"),
                         "OLD_PUBLICATION_ONLY_NOT_CORRECTED_ASOF")
        self.assertEqual(gate(ORIGINAL, CORRECTION, 506_314_739, "2026-08-13"),
                         "NO_NOTICE_YET_ASOF")

    def test_other_issuer_recipient_contract_mod_or_office_cannot_join(self):
        for field, wrong in (("issuer", "OTHER AGENCY"),
                             ("contractor", "UNRELATED VENDOR LLC"),
                             ("contract", "W58RGZ-24-C-9999"),
                             ("modification", "PZ0023"),
                             ("office", "OTHER OFFICE")):
            with self.subTest(field=field):
                changed = copy.deepcopy(CORRECTION)
                changed[field] = wrong
                self.assertEqual(gate(ORIGINAL, changed, 506_314_739,
                                      "2026-11-06"),
                                 "UNKNOWN_CORRECTION_IDENTITY_MISMATCH")

    def test_altered_face_date_or_non_correction_fails_closed(self):
        for field, wrong, expected in (
            ("face_usd", 636_110_314, "UNKNOWN_MODIFICATION_FACE_MISMATCH"),
            ("refers_to_date", "2026-08-13", "UNKNOWN_CORRECTION_CHRONOLOGY"),
            ("date", "2026-08-12", "UNKNOWN_CORRECTION_CHRONOLOGY"),
            ("explicit_funding_correction", False, "UNKNOWN_CORRECTION_ORIGINALITY"),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(CORRECTION)
                changed[field] = wrong
                self.assertEqual(gate(ORIGINAL, changed, 506_314_739,
                                      "2026-11-06"), expected)

    def test_unrelated_amount_or_missing_identity_remains_unknown(self):
        self.assertEqual(gate(ORIGINAL, CORRECTION, 100, "2026-11-06"),
                         "UNKNOWN_UNSUPPORTED_AMOUNT")
        invalid = copy.deepcopy(ORIGINAL)
        invalid["contractor"] = ""
        self.assertEqual(gate(invalid, CORRECTION, 506_314_739, "2026-11-06"),
                         "UNKNOWN_CORRECTION_IDENTITY_MISMATCH")


if __name__ == "__main__":
    unittest.main()
