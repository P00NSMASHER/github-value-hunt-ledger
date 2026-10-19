"""Original GAO 1976 wrong BOL origin must not create fictitious collections."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from freight import public_gao_b186603_wrong_bol_origin as original

class GAOPublishedWaybillOriginTests(unittest.TestCase):
    def test_13328_wrong_origin_deduction_has_conditional_refund_not_verified_cash(self):
        result=original.verified_original_gao_origin_decision()
        self.assertEqual(result["original_decisions"],1)
        self.assertEqual(result["distinct_GBLs_in_decision"],2)
        self.assertEqual(result["carrier_government_payment_for_chairs_cents"],39816)
        self.assertEqual(result["government_applied_offset_based_on_incorrect_origin_cents"],13328)
        self.assertEqual(result["documented_BOL_origin"],"Washington, D.C.")
        self.assertEqual(result["GAO_established_actual_origin"],"Canton, Mississippi")
        self.assertTrue(result["GAO_rebutted_BOL_presumption_with_independent_shipment_evidence"])
        self.assertEqual(result["GAO_conditional_carrier_reimbursement_claim_cents"],13328)
        self.assertIsNone(result["carrier_repayment_proven_cents"])
        self.assertEqual(result["retally_verified_recovered_cents"],0)
        self.assertFalse(result["original_BOL_scan_or_carrier_PRO_full_bytes_independently_verified"])
        self.assertTrue(result["not_proof_of_current_rate_or_private_right_of_setoff"])

    def test_second_blanket_GBL_certificate_cannot_be_called_paid(self):
        result=original.verified_original_gao_origin_decision()
        self.assertEqual(result["separate_blanket_GBL_applied_setoff_cents"],5765)
        self.assertEqual(result["separate_blanket_settlement_certificate_issued_cents"],2290)
        self.assertFalse(result["separate_blanket_settlement_certificate_paid_verified"])
        self.assertTrue(result["cannot_add_amounts_from_separate_shipments_as_one_recovery"])

    def _alter(self,action):
        sample=json.loads(original.SOURCE.read_text(encoding="utf-8"))
        action(sample)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"bad.json"
            path.write_text(json.dumps(sample))
            with patch.object(original,"SOURCE",path):
                with self.assertRaisesRegex(ValueError,"GAO_BOL_ORIGIN_"):
                    original.verified_original_gao_origin_decision()

    def test_fabricated_actual_origin_and_unsupported_original_BOL_scan_rejected(self):
        self._alter(lambda x:x["historical_shipment_disputes"][0].update(
            {"agency_investigated_actual_origin":"Washington, D.C."}))
        self._alter(lambda x:x["historical_shipment_disputes"][0].update(
            {"independent_original_BOL_or_carrier_PRO_scan_examined":True}))
        self._alter(lambda x:x["historical_shipment_disputes"][0].update(
            {"payment_back_to_carrier_proven":True}))
        self._alter(lambda x:x["historical_shipment_disputes"][0]["documentation_evidence"].__setitem__(
            0,"Washington DC was verified manufacturing origin"))
        self._alter(lambda x:x.update({"note":"Carrier repayment was proven as paid."}))

    def test_forged_deduction_refund_and_pretend_private_cash_rejected(self):
        self._alter(lambda x:x["historical_shipment_disputes"][0].update(
            {"gsa_applied_setoff_cents":13329}))
        self._alter(lambda x:x["historical_shipment_disputes"][1].update(
            {"settlement_certificate_paid_back_to_carrier_verified":True}))
        self._alter(lambda x:x.update({"RETALLY_recoveries_cents":13328}))
        self._alter(lambda x:x.update({"customer_invoice_wins":5}))

    def test_issued_settlement_certificate_is_not_a_new_combined_case_receipt(self):
        self._alter(lambda x:x.update(
            {"two_distinct_GBLs_must_not_be_combined_as_a_single_recovered_balance":False}))
        self._alter(lambda x:x["historical_shipment_disputes"][1].update(
            {"gsa_applied_setoff_cents":0}))

if __name__=="__main__":
    unittest.main()
