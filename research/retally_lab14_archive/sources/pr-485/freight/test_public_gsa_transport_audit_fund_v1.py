"""Public FY2023 GSA Transportation Audits fund accounting isn't customer recovery."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from freight import public_gsa_transport_audit_fund_v1 as g


class GSAOriginalTransportFund(unittest.TestCase):
    def test_official_accounting_rows_are_separate_from_carrier_recovery(self):
        r=g.verified_accounting()
        self.assertEqual(r["accounting_fact_rows"],7)
        self.assertEqual(r["FY2023_ACTUAL_fund_receipts_thousand_USD"],12354)
        self.assertEqual(r["FY2024_PLAN_fund_receipts_thousand_USD"],4168)
        self.assertEqual(r["FY2025_PLAN_fund_receipts_thousand_USD"],12506)
        self.assertEqual(r["FY2023_ACTUAL_transfer_TO_suspense_thousand_USD"],-20674)
        self.assertEqual(r["FY2023_ACTUAL_annual_obligations_thousand_USD"],10960)
        self.assertEqual(r["FY2023_vendor_corrective_payment_APPROX_million_USD"],"29.6")
        self.assertTrue(r["rounding_narrative_NOT_exact_transaction_voucher"])
        self.assertTrue(r["transfer_cannot_be_deducted_from_same_year_receipts_to_compute_recovery_rate"])
        self.assertTrue(r["no_customer_recovery_performance_forecast"])
        self.assertTrue(r["no_customer_freight_invoice_verification"])
        self.assertEqual(r["no_actual_RETALLY_customer_cash_cents"],0)
        self.assertEqual(r["commercial_claim_clearance"],"NO_GO")

    def _modify(self,fn):
        data=json.loads(g.SOURCE.read_text())
        fn(data)
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"edited.json"
            p.write_text(json.dumps(data),encoding="utf-8")
            with patch.object(g,"SOURCE",p):
                with self.assertRaisesRegex(ValueError,"GSA_TRANSPORT_AUDIT_FUND_"):
                    g.verified_accounting()

    def test_plan_year_cannot_be_mislabeled_an_actual_receipt(self):
        self._modify(lambda d:d["facts"][1].update({"budget_status":"ACTUAL"}))
        self._modify(lambda d:d["facts"][2].update({"fiscal_year":2023}))

    def test_fake_added_2023_collections_and_wrong_units_fail(self):
        self._modify(lambda d:d["facts"][0].update({"value_thousands_usd":29600}))
        self._modify(lambda d:d.update({"original_source_table_unit":"USD MILLIONS"}))
        self._modify(lambda d:d.update({"verified_actual_recovered_RETALLY_money_cents":1235400000}))

    def test_wrong_transfer_sign_and_source_pdf_fail(self):
        self._modify(lambda d:d["facts"][3].update({"value_thousands_usd":20674}))
        self._modify(lambda d:d.update({"source_url":"https://untrusted.example/report.pdf"}))
        self._modify(lambda d:d.update({"source_report_pdf_page_zero_based":292}))

    def test_rounded_20_7_vs_precise_20_674_not_called_discrepancy(self):
        self.assertEqual(g.verified_accounting()["FY2023_ACTUAL_transfer_TO_suspense_thousand_USD"],-20674)
        self._modify(lambda d:d.update({
            "source_narrative_receipts_portion_approx_million_usd":"20.6"}))
        self._modify(lambda d:d.update({
            "source_receipt_transfer_exact_table_thousands_usd":-20675}))

    def test_bank_confirmations_and_wrong_vendor_payment_tier_fail(self):
        self._modify(lambda d:d.update({"independent_bank_Treasury_electronic_transfer_examined":True}))
        self._modify(lambda d:d.update({"reported_vendor_payment_is_refund_TO_vendor_for_erroneous_NOCs":False}))
        self._modify(lambda d:d.update({"no_customer_invoice_or_recovered_funds":False}))

if __name__=="__main__":
    unittest.main()
