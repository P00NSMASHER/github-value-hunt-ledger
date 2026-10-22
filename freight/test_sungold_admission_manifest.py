"""No source bytes: test court-supported SAME BOL research hold metadata only."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

SOURCE=Path(__file__).resolve().parent/"research"/"sungold_same_shipment_admission_manifest.json"


class TestSungoldUnadmittedSourceCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case=json.loads(SOURCE.read_text(encoding="utf-8"))

    def test_exact_legal_case_and_bol_identity(self):
        c=self.case
        self.assertEqual(c["shipment_ref"],"AMC1912992")
        self.assertEqual(c["cnr"],"DLWT-01-014066-2025")
        self.assertEqual(c["court_judgment_date"],"2026-09-17")

    def test_all_original_trial_exhibit_bytes_absent(self):
        c=self.case
        self.assertEqual(len(c["exhibits"]),4)
        self.assertEqual({x["exhibit"] for x in c["exhibits"]},
                         {"Ex.PW2/1","Ex.PW2/2","Ex.PW2/3","Ex.PW1/12"})
        for evidence in c["exhibits"]:
            self.assertFalse(evidence["bytes_ingested"])
            self.assertIsNone(evidence["original_pdf_sha256"])
            self.assertEqual(evidence["status"],
                             "COURT_CITED_ORIGINAL_NOT_DOWNLOADED")

    def test_judged_money_arithmetic_pauses_recovery(self):
        c=self.case
        self.assertEqual(c["currency"],"INR")
        self.assertEqual(c["monetary_units"],"paise")
        self.assertEqual(c["original_detention_invoice_minor_units"],68969585)
        self.assertEqual(c["original_credit_to_forwarder_minor_units"],61933926)
        self.assertEqual(c["no_original_credit_evidence_for_minor_units"],7035659)
        self.assertEqual(61933926+7035659,68969585)
        self.assertEqual(c["retally_verified_recovered_minor_units"],0)

    def test_carrier_credit_is_not_shipper_bank_settlement(self):
        c=self.case
        self.assertEqual(c["carrier_credit"]["to"],c["forwarder"])
        self.assertNotEqual(c["carrier_credit"]["to"],
                            c["shipper_and_original_payer"])
        recovery=c["final_customer_recovery"]
        self.assertEqual(recovery["event_status"],
                         "JUDGMENT_ORDER_NOT_BANK_SETTLEMENT")
        self.assertEqual(recovery["verified_settled_amount_minor_units"],0)
        self.assertIsNone(recovery["independent_bank_clearing_receipt_sha256"])
        self.assertFalse(recovery["original_customer_bank_receipt_bytes_ingested"])

    def test_2022_detention_links_have_no_valid_source_bytes_or_ship_rate(self):
        c=self.case
        self.assertEqual(len(c["original_2022_rate_sources"]),3)
        for e in c["original_2022_rate_sources"]:
            self.assertEqual(e["published_effective_date"],"2022-01-20")
            self.assertEqual(e["charge_type"],"DETENTION")
            self.assertTrue(e["url"].startswith("https://www.cma-cgm.com/"))
            self.assertTrue(e["indexed_rate_source"])
            self.assertIsNone(e["source_byte_sha256"])
            self.assertFalse(e["original_bytes_ingested"])
            self.assertFalse(e["shipment_specific_applicability_verified"])
            self.assertEqual(e["fetch_status"],"SOURCE_ORIGIN_UNAVAILABLE")

    def test_unverified_court_and_external_rights_never_authorize_release(self):
        c=self.case
        self.assertTrue(c["legal_source_user_authorized_download"])
        self.assertFalse(c["third_party_commercial_redistribution_rights_verified"])
        self.assertFalse(c["source_original_four_document_chain_complete"])
        self.assertFalse(c["original_pdfs_republished_to_github"])
        self.assertFalse(c["original_private_customer_files_imported"])


if __name__=="__main__":
    unittest.main()
