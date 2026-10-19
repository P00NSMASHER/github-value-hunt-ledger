import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from freight import public_gsa_false_positive_payment_v1 as gsa

class GSA2023ErroneousTransportAuditCorrection(unittest.TestCase):
    def test_publisher_says_paid_back_to_vendor_not_retally_revenue(self):
        r=gsa.report()
        self.assertTrue(r["source_reports_FY2023_vendor_payment_made"])
        self.assertEqual(r["publisher_reported_vendor_payment_approx_cents"],2960000000)
        self.assertTrue(r["reported_payment_FROM_government_TO_vendor"])
        self.assertTrue(r["notices_of_overcharge_declared_erroneous"])
        self.assertEqual(r["possible_additional_payment_limit_cents_NOT_PROVEN"],1180000000)
        self.assertFalse(r["possible_additional_payment_executed"])
        self.assertFalse(r["is_recovered_overcharge_by_RETALLY"])
        self.assertEqual(r["validated_RETALLY_customer_cash_cents"],0)
        self.assertFalse(r["independent_vendor_bank_statement_seen"])
        self.assertFalse(r["original_source_PDF_all_bytes_hashed"])
        self.assertEqual(r["commercial_recovery_claim"],"NO_GO")

    def test_funding_components_match_original_reported_payment(self):
        x=gsa.PINNED
        self.assertEqual(
            x["amount_reported_returned_from_receipts_account_approx_cents"]
            +x["amount_reported_paid_from_suspense_account_approx_cents"],
            x["amount_reported_paid_TO_DoD_transportation_vendor_cents"])

    def _tamper(self,change):
        source=json.loads(gsa.SOURCE.read_text(encoding="utf-8"))
        change(source)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"tampered.json"
            p.write_text(json.dumps(source))
            with patch.object(gsa,"SOURCE",p):
                with self.assertRaisesRegex(ValueError,"GSA_FALSE_POSITIVE_"):
                    gsa.report()

    def test_pending_litigation_amount_cannot_be_called_paid(self):
        self._tamper(lambda x:x.update({"possible_additional_vendor_payment_already_proven":True}))
        self._tamper(lambda x:x.update({"potential_additional_disputed_vendor_payment_upper_bound_cents":0}))

    def test_fake_original_invoice_or_bank_statement_does_not_change_proof_tier(self):
        self._tamper(lambda x:x.update({"separate_vendor_bank_posting_independently_inspected":True}))
        self._tamper(lambda x:x.update({"original_billing_invoices_and_contracts_independently_examined":True}))
        self._tamper(lambda x:x.update({"complete_PDF_bytes_sha256_independently_recorded":True}))

    def test_no_refund_back_to_vendor_can_be_called_retally_profit(self):
        self._tamper(lambda x:x.update({"RETALLY_customer_overcharges_recovered_cents":2960000000}))
        self._tamper(lambda x:x.update({"erroneous_notices_must_not_be_treated_as_valid_customer_savings":False}))
        self._tamper(lambda x:x.update({"case_net_recovery_usd":29600000}))

    def test_wrong_funding_direction_and_source_url_are_rejected(self):
        self._tamper(lambda x:x.update({"amount_reported_paid_TO_DoD_transportation_vendor_cents":0}))
        self._tamper(lambda x:x.update({"source_url":"https://not-government.example/forged-case.pdf"}))

if __name__=="__main__":
    unittest.main()
