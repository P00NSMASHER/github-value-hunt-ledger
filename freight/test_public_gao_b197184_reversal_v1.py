"""Original 1980 GAO wrongful setoff is not a verified carrier repayment."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from freight import public_gao_b197184_reversal_v1 as s

class GAAOriginal1980WrongfulSetoff(unittest.TestCase):
    def test_real_offset_followed_by_GSA_admission_and_moot_GAO_review(self):
        r=s.verified_improper_offset()
        self.assertEqual(r["original_offset_reported_applied_cents"],47536)
        self.assertTrue(r["published_original_GAO_letter_and_memo_verified_text"])
        self.assertTrue(r["GSA_later_admitted_setoff_wrong"])
        self.assertTrue(r["GAO_review_closed_as_moot"])
        self.assertTrue(r["GAO_claim_allowable_subject_to_other_propriety"])
        self.assertFalse(r["carrier_actual_repayment_confirmed"])
        self.assertIsNone(r["confirmed_carrier_bank_disbursement_cents"])
        self.assertIsNone(r["permanent_legally_retained_government_collection_cents"])
        self.assertEqual(r["real_RETALLY_cash_recovered_cents"],0)
        self.assertEqual(r["commercial_claim_clearance"],"NO_GO")

    def _tamper(self,modify):
        x=json.loads(s.SOURCE.read_text(encoding="utf-8"))
        modify(x)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"fake-reversal.json"
            path.write_text(json.dumps(x))
            with patch.object(s,"SOURCE",path):
                with self.assertRaisesRegex(ValueError,"GAO_B197184_SOURCE_FACT_OR_REPAYMENT_STATUS_CHANGED"):
                    s.verified_improper_offset()

    def test_cannot_change_original_deduction_amount_or_shipment_identity(self):
        self._tamper(lambda x:x.update({"deduction_reported_already_applied_cents":47537}))
        self._tamper(lambda x:x.update({"billed_government_bill_of_lading":"K-5405057"}))
        self._tamper(lambda x:x.update({"original_document_date":"1980-03-25"}))

    def test_cannot_count_conditionally_allowable_carrier_claim_as_money_paid(self):
        self._tamper(lambda x:x.update({"original_claim_payment_to_carrier_actually_verified":True}))
        self._tamper(lambda x:x.update({"actual_payment_back_to_carrier_cents":47536}))
        self._tamper(lambda x:x.update({"independent_treasury_or_bank_disbursement_seen":True}))

    def test_cannot_claim_retally_recovery_or_separately_authenticated_bol(self):
        self._tamper(lambda x:x.update({"RETALLY_real_customer_recoveries_cents":47536}))
        self._tamper(lambda x:x.update({"original_invoice_or_bill_of_lading_independently_examined":True}))
        self._tamper(lambda x:x.update({"customer_invoice_id":"real-client-123"}))

    def test_cannot_relabel_GSA_admission_as_upheld_collection(self):
        self._tamper(lambda x:x.update({"GSA_acknowledged_original_setoff_improper":False}))
        self._tamper(lambda x:x.update({"GAO_review_dismissed_as_moot":False}))
        self._tamper(lambda x:x.update({"legally_retained_government_net_recovery_cents":47536}))
        self._tamper(lambda x:x.update({"source_full_pdf_bytes_sha256_verified":True}))

    def test_two_distinct_original_wrongful_offset_cases_remain_separate(self):
        from freight.public_gao_setoff_reversal_v1 import verified_historical_reversal
        first=verified_historical_reversal()
        second=s.verified_improper_offset()
        self.assertEqual(first["postpetition_GOVERNMENT_applied_offset_LATER_DISALLOWED_cents"],514105)
        self.assertEqual(second["original_offset_reported_applied_cents"],47536)
        self.assertTrue(second["distinct_from_GAO_B192974_larger_improper_setoff"])
        self.assertFalse(second["carrier_actual_repayment_confirmed"])
        self.assertFalse(first["independent_carrier_repayment_bank_receipt_obtained"])

if __name__=="__main__":
    unittest.main()
