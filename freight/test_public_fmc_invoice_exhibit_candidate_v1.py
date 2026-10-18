"""A filed invoice reproduction may support OCR arithmetic, not actual recovery."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from freight import public_fmc_invoice_exhibit_candidate_v1 as f

class FMCPublicExhibitInvoiceCandidate(unittest.TestCase):
    def test_publicly_filed_invoice_line_items_are_exact_mathematical_candidates(self):
        r=f.report()
        self.assertEqual(r["federal_public_filing_docket"],"17-05")
        self.assertEqual(r["distinct_charge_labels"],4)
        self.assertEqual(r["candidate_OCR_line_total_cents"],918593)
        self.assertEqual(r["candidate_OCR_extracted_invoice_total_cents"],918593)
        self.assertTrue(r["candidate_OCR_arithmetic_reconciles"])
        self.assertEqual([row["cents"] for row in f.verified_candidate()["charges"]],
                         [540000,171293,112300,95000])

    def test_duplicate_exhibit_renditions_are_not_two_paid_invoices(self):
        r=f.report()
        self.assertEqual(r["source_exhibit_pdf_page_number_zero_based"],19)
        self.assertTrue(r["adjacent_OCR_rendition_uncertain"])
        self.assertTrue(r["one_candidate_invoice_not_two_independent_invoices"])
        self.assertFalse(r["unique_actual_source_invoice_verified"])

    def test_pleading_allegations_are_not_carrier_fault_or_overcharge_proof(self):
        r=f.report()
        self.assertTrue(r["mode_mismatch_is_LITIGANT_ALLEGATION_only"])
        self.assertFalse(r["original_bill_of_lading_cross_match_verified"])
        self.assertFalse(r["invoice_actually_paid_verified"])
        self.assertFalse(r["carrier_specific_contract_and_tariff_verified"])
        self.assertFalse(r["adjudicated_charge_invalidity_proven"])
        self.assertIsNone(r["invoice_overcharge_cents"])
        self.assertIsNone(r["actual_cash_received_cents"])
        self.assertEqual(r["real_RETALLY_customer_recoveries_cents"],0)
        self.assertEqual(r["commercial_claim_clearance"],"NO_GO")

    def _forgery(self,mutate):
        raw=json.loads(f.SOURCE.read_text(encoding="utf-8"))
        mutate(raw)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"altered.json";path.write_text(json.dumps(raw))
            with patch.object(f,"SOURCE",path):
                with self.assertRaisesRegex(ValueError,"FMC_ORIGINAL_INVOICE_CANDIDATE_"):
                    f.verified_candidate()

    def test_forged_line_item_total_and_fee_description_rejected(self):
        self._forgery(lambda x:x["charges"][0].update({"cents":550000}))
        self._forgery(lambda x:x.update({"publicly_indexed_page19_total_cents":900000}))
        self._forgery(lambda x:x["charges"][0].update({"label":"CONFIRMED FRAUD"}))

    def test_ocr_text_cannot_be_recast_as_visual_authentication(self):
        self._forgery(lambda x:x.update({"source_indexed_pdf_invoice_image_visually_inspected_independently":True}))
        self._forgery(lambda x:x.update({"original_carrier_issued_document_independently_authenticated":True}))
        self._forgery(lambda x:x.update({"page20_OCR_duplicate_rendering_has_inconsistent_total_glyphs":False}))

    def test_fabricated_customer_or_paid_invoice_proof_fails_closed(self):
        self._forgery(lambda x:x.update({"original_payment_or_bank_receipt_authenticated":True}))
        self._forgery(lambda x:x.update({"current_RETALLY_customer_relationship_or_authorization":True}))
        self._forgery(lambda x:x.update({"real_RETALLY_customer_recovered_cents":918593}))
        self._forgery(lambda x:x.update({"recoverable_amount_cents":540000}))
        self._forgery(lambda x:x.update({"actual_invoice_overcharge_independently_proven":True}))

    def test_source_page_and_original_ship_mode_authority_not_forged(self):
        self._forgery(lambda x:x.update({"published_document_url":"https://non-government.example/invoice.pdf"}))
        self._forgery(lambda x:x.update({"fmc_docket":"17-50"}))
        self._forgery(lambda x:x.update({"original_public_pdf_exhibit_page_indices_zero_based":[19,20,21]}))
        self._forgery(lambda x:x.update({"directly_applicable_signed_freight_contract_or_tariff_obtained":True}))
        self._forgery(lambda x:x["source_limitations"].__setitem__(
           0,"Litigant-filed invoice pages prove guaranteed RETALLY customer recovery and a bank-paid fee."))

    def test_unrelated_invoice_or_container_cannot_be_added_to_single_candidate(self):
        self._forgery(lambda x:x["charges"].append({"label":"OTHER SHIPMENT","cents":540000}))
        self._forgery(lambda x:x.update({"second_invoice_paid_cents":918593}))

if __name__=="__main__":
    unittest.main()
