"""Research-only DCRB issuer-original amendment-ID negative control.

Public first-party PDF sources, visually cross-checked on 2026-11-06:
A0001: https://dcrb.dc.gov/sites/default/files/dc/sites/dcrb/publication/attachments/A0001-%20Amendment%20to%20the%20BAPS%20RFP%20DCRB-2025-RFP-0500_v1_08.29.2025.pdf
A0002: https://dcrb.dc.gov/sites/default/files/dc/sites/dcrb/publication/attachments/A0002%20-%20Amendment%20to%20the%20BAPS%20RFP%20DCRB-2025-RFP-0500_v2_Signed%2009.08.2025.pdf
Original RFP, p1: https://dcrb.dc.gov/sites/default/files/dc/sites/dcrb/publication/attachments/REQUEST%20FOR%20PROPOSAL%20-%20DCRB-2025-RFP-0500_DCRB%20BAPS_RFP_Final%202025.08.01.pdf
Award notice: https://dcrb.dc.gov/publication/dcrb-2025-rfp-0500-dcrb-benefits-administration-pension-system

Both amendment PDFs show 2025-RFP-0500 in p1 blocks 1 and 9A but
2024-RFP-0500 in p1 item 14 and 2024-RFP-0300 on p2. The source is
internally inconsistent. This test proves a counterexample to naive
first/last/majority ID extraction; it does NOT adjudicate a transaction,
verify raw source bytes, establish source rights or validate a benchmark.
No network, Cloudflare, customer data, production code or release effects.
"""
from __future__ import annotations

import copy
from datetime import date
from urllib.parse import urlsplit
import unittest

ORIGINAL_RFP_ID = "DCRB-2025-RFP-0500"
ORIGINAL_RFP_DATE = "2025-08-01"
AWARD_DATE = "2026-05-26"
ISSUER = "District of Columbia Retirement Board"

AMENDMENTS = (
    {
        "amendment": "A0001",
        "url": "https://dcrb.dc.gov/sites/default/files/dc/sites/dcrb/publication/attachments/A0001-%20Amendment%20to%20the%20BAPS%20RFP%20DCRB-2025-RFP-0500_v1_08.29.2025.pdf",
        "issuer": ISSUER,
        "page1_block1_id": ORIGINAL_RFP_ID,
        "page1_block9a_id": ORIGINAL_RFP_ID,
        "page1_item14_id": "DCRB-2024-RFP-0500",
        "page2_header_id": "DCRB-2024-RFP-0300",
        "page1_block10a_contract_number": None,
        "signed_date": "2025-09-05",
        "source_sha256": None,
    },
    {
        "amendment": "A0002",
        "url": "https://dcrb.dc.gov/sites/default/files/dc/sites/dcrb/publication/attachments/A0002%20-%20Amendment%20to%20the%20BAPS%20RFP%20DCRB-2025-RFP-0500_v2_Signed%2009.08.2025.pdf",
        "issuer": ISSUER,
        "page1_block1_id": ORIGINAL_RFP_ID,
        "page1_block9a_id": ORIGINAL_RFP_ID,
        "page1_item14_id": "DCRB-2024-RFP-0500",
        "page2_header_id": "DCRB-2024-RFP-0300",
        "page1_block10a_contract_number": None,
        "signed_date": "2025-09-08",
        "source_sha256": None,
    },
)


def assess_amendment_identity(row: dict) -> tuple[str, bool]:
    """Return a fail-closed research finding and independent-award proof flag."""
    parsed = urlsplit(row["url"])
    if parsed.scheme != "https" or parsed.hostname != "dcrb.dc.gov" or not parsed.path.endswith(".pdf"):
        return "REJECT_UNTRUSTED_SOURCE_OR_PROTOCOL", False
    if row["issuer"] != ISSUER:
        return "REJECT_ISSUER_DISAGREEMENT", False
    if row["page1_block1_id"] != ORIGINAL_RFP_ID or row["page1_block9a_id"] != ORIGINAL_RFP_ID:
        return "UNKNOWN_CONTROLLING_HEADER_ID_CONFLICT", False
    if not date.fromisoformat(ORIGINAL_RFP_DATE) < date.fromisoformat(row["signed_date"]) < date.fromisoformat(AWARD_DATE):
        return "UNKNOWN_NOT_PROVEN_PREAWARD_AMENDMENT", False
    if row["page1_block10a_contract_number"] is not None:
        return "UNKNOWN_CONTRACT_MODIFICATION_FIELD_PRESENT", False
    if (row["page1_item14_id"] != ORIGINAL_RFP_ID or
            row["page2_header_id"] != ORIGINAL_RFP_ID):
        return "PREAWARD_RFP_AMENDMENT_WITH_INTERNAL_ID_CONFLICT_REVIEW", False
    return "PREAWARD_RFP_AMENDMENT_CONSISTENT_IDS_NOT_AWARD", False


class DCRBOfficialAmendmentIdentityNegativeControls(unittest.TestCase):
    def test_two_actual_first_party_amendments_have_same_three_conflicting_ids(self):
        self.assertEqual({x["amendment"] for x in AMENDMENTS}, {"A0001", "A0002"})
        for row in AMENDMENTS:
            self.assertEqual(row["page1_block1_id"], ORIGINAL_RFP_ID)
            self.assertEqual(row["page1_block9a_id"], ORIGINAL_RFP_ID)
            self.assertEqual(row["page1_item14_id"], "DCRB-2024-RFP-0500")
            self.assertEqual(row["page2_header_id"], "DCRB-2024-RFP-0300")
            self.assertEqual(assess_amendment_identity(row),
                             ("PREAWARD_RFP_AMENDMENT_WITH_INTERNAL_ID_CONFLICT_REVIEW", False))

    def test_naive_last_occurrence_falsified_by_actual_pdfs(self):
        for row in AMENDMENTS:
            all_ordered_ids = [row[k] for k in (
                "page1_block1_id", "page1_block9a_id", "page1_item14_id", "page2_header_id")]
            self.assertNotEqual(all_ordered_ids[-1], ORIGINAL_RFP_ID)
            self.assertNotEqual(all_ordered_ids[2], ORIGINAL_RFP_ID)
            self.assertFalse(assess_amendment_identity(row)[1])

    def test_synthetic_header_corruption_cannot_be_normalized_from_narrative(self):
        for row in AMENDMENTS:
            wrong = copy.deepcopy(row)
            wrong["page1_block9a_id"] = wrong["page1_item14_id"]
            self.assertEqual(assess_amendment_identity(wrong),
                             ("UNKNOWN_CONTROLLING_HEADER_ID_CONFLICT", False))

    def test_synthetic_wrong_issuer_and_url_rejected(self):
        for field, value in (("issuer", "Other Agency"),
                             ("url", "https://dcrb.dc.gov.evil.example/a.pdf"),
                             ("url", "http://dcrb.dc.gov/a.pdf")):
            row = copy.deepcopy(AMENDMENTS[0])
            row[field] = value
            self.assertTrue(assess_amendment_identity(row)[0].startswith("REJECT_"))

    def test_synthetic_post_award_date_or_contract_modification_stays_unknown(self):
        for field, value, expected in (
            ("signed_date", "2026-06-01", "UNKNOWN_NOT_PROVEN_PREAWARD_AMENDMENT"),
            ("page1_block10a_contract_number", "DCRB-2026-C-0100", "UNKNOWN_CONTRACT_MODIFICATION_FIELD_PRESENT"),
        ):
            row = copy.deepcopy(AMENDMENTS[1])
            row[field] = value
            self.assertEqual(assess_amendment_identity(row), (expected, False))

    def test_consistent_ids_still_do_not_validate_award_payment_or_cash(self):
        row = copy.deepcopy(AMENDMENTS[0])
        row["page1_item14_id"] = ORIGINAL_RFP_ID
        row["page2_header_id"] = ORIGINAL_RFP_ID
        self.assertEqual(assess_amendment_identity(row),
                         ("PREAWARD_RFP_AMENDMENT_CONSISTENT_IDS_NOT_AWARD", False))
        self.assertIsNone(row["source_sha256"])


if __name__ == "__main__":
    unittest.main()
