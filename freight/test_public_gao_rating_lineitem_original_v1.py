"""Regression controls for original GAO billed-rate and wrong-origin correction decisions."""
from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from freight import public_gao_rating_lineitem_original_v1 as rate

class TwoGAODecisionRatingAndSourceControls(unittest.TestCase):
    def test_1967_genuine_bill_line_arithmetic_exact_cent(self):
        x=rate.reviewed_source()["sources"][0]
        self.assertEqual(x["actual_reported_weight_pounds"],1485)
        self.assertEqual(rate._bill_cents(1485,1853),27517)
        self.assertEqual(rate._bill_cents(1485,938),13929)
        self.assertEqual(x["freight_claimed_original_paid_cents"],27517)
        self.assertEqual(x["government_audited_allowable_cents"],13929)
        self.assertEqual(x["government_applied_setoff_cents"],13588)
        self.assertEqual(27517-13929,13588)

    def test_change_to_nmfc_came_after_original_paid_shipment(self):
        x=rate.reviewed_source()["sources"][0]
        self.assertEqual(x["source_shipment_date"],"1962-12-19")
        self.assertEqual(x["freight_paid_month"],"1963-03")
        self.assertEqual(x["later_government_bill_of_lading_correction_month"],"1964-02")
        self.assertEqual(x["setoff_date"],"1965-12")
        self.assertTrue(x["later_document_correction_is_after_original_payment"])
        self.assertFalse(x["original_bol_scan_independently_inspected"])
        self.assertFalse(x["contract_nmfc_original_page_independently_inspected"])
        self.assertTrue(x["historical_federal_decision_not_current_tariff_authority"])

    def test_gao_1976_two_gbls_not_one_overcharge_or_same_shipment(self):
        a,b=rate.reviewed_source()["sources"][1]["issues"]
        self.assertEqual(a["original_bill_of_lading"],"D-8271398")
        self.assertEqual(a["government_reported_offset_cents"],5765)
        self.assertEqual(a["subsequently_issued_carrier_settlement_certificate_cents"],2290)
        self.assertFalse(a["certificate_actual_payment_or_carrier_receipt_verified"])
        self.assertEqual(b["original_bill_of_lading"],"F-7349731")
        self.assertEqual(b["government_reported_original_paid_cents"],39816)
        self.assertEqual(b["government_reported_offset_cents"],13328)
        self.assertTrue(a["separate_transaction_not_part_of_chair_shipment"])

    def test_genuine_corroboration_defeats_quoted_bol_origin_and_offset(self):
        x=rate.reviewed_source()["sources"][1]["issues"][1]
        self.assertEqual(x["bill_of_lading_origin"],"Washington DC")
        self.assertEqual(x["corroborated_actual_origin"],"Canton Mississippi")
        self.assertTrue(x["original_bill_of_lading_origin_rebutted"])
        self.assertFalse(x["government_claimed_overcharge_is_still_valid_after_ruling"])
        self.assertEqual(x["GAO_decision"],
                         "GSA SHOULD ALLOW carrier claim for $133.28 IF OTHERWISE CORRECT")
        self.assertFalse(x["carrier_repayment_bank_receipt_verified"])
        self.assertTrue(x["origin_correction_does_not_prove_other_customer_rate"])

    def test_report_preserves_only_government_historical_cases(self):
        x=rate.report()
        self.assertEqual(x["original_GAO_published_decisions_reviewed"],2)
        self.assertEqual(x["distinct_GBL_references_in_decisions"],3)
        self.assertEqual(x["government_B160344_claimed_paid_cents"],27517)
        self.assertEqual(x["government_B160344_allowable_cents"],13929)
        self.assertEqual(x["government_B160344_reported_collection_by_setoff_cents"],13588)
        self.assertTrue(x["government_B186603_chair_13328_setoff_later_disallowed_in_source"])
        self.assertTrue(x["all_event_net_cash_totals_explicitly_UNVERIFIED"])
        self.assertFalse(x["government_B186603_chair_repayment_bank_receipt_verified"])
        self.assertEqual(x["real_RETALLY_client_invoices"],0)
        self.assertEqual(x["real_RETALLY_customer_recoveries_cents"],0)
        self.assertEqual(x["commercial_release"],"NO_GO")

    def _alter(self,fn):
        x=json.loads(rate.SOURCE.read_text(encoding="utf-8"))
        fn(x)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"altered.json"
            p.write_text(json.dumps(x))
            with patch.object(rate,"SOURCE",p):
                with self.assertRaisesRegex(ValueError,"GAO_RATING_SOURCE_"):
                    rate.reviewed_source()

    def test_forged_original_paid_or_legal_rate_denied(self):
        self._alter(lambda x:x["sources"][0].update(
            {"freight_claimed_original_paid_cents":27518}))
        self._alter(lambda x:x["sources"][0].update(
            {"government_accepted_rate_cents_per_100_pounds":937}))
        self._alter(lambda x:x["sources"][0].update(
            {"government_applied_setoff_cents":13587}))
        self._alter(lambda x:x["sources"][0].update(
            {"original_claimed_nmfc_item":"12400"}))

    def test_source_correction_cannot_be_backdated_or_relabelled(self):
        self._alter(lambda x:x["sources"][0].update(
            {"later_government_bill_of_lading_correction_month":"1962-01"}))
        self._alter(lambda x:x["sources"][0].update(
            {"later_document_correction_is_after_original_payment":False}))
        self._alter(lambda x:x["sources"][1]["issues"][1].update(
            {"government_claimed_overcharge_is_still_valid_after_ruling":True}))

    def test_same_decision_two_bills_cannot_be_merged_to_grow_recovery(self):
        self._alter(lambda x:x["sources"][1]["issues"][0].update(
            {"original_bill_of_lading":"F-7349731"}))
        self._alter(lambda x:x["sources"][1]["issues"][0].update(
            {"government_reported_offset_cents":19093}))
        self._alter(lambda x:x["sources"][1]["issues"].append(
            x["sources"][1]["issues"][0].copy()))

    def test_false_bank_or_private_client_evidence_denied(self):
        self._alter(lambda x:x.update({"retally_verified_recoveries_cents":13588}))
        self._alter(lambda x:x.update({"bank_or_treasury_receipts_independently_examined":1}))
        self._alter(lambda x:x.update({"verified_commercial_recovery_clearance":True}))
        self._alter(lambda x:x["sources"][1]["issues"][1].update(
            {"carrier_repayment_bank_receipt_verified":True}))
        self._alter(lambda x:x["sources"][0].update(
            {"private_customer_tariff":"CURRENT"}))

    def test_publisher_source_hostname_and_existence_bound(self):
        self._alter(lambda x:x["sources"][0].update(
            {"url":"https://fake.example/products/b-160344"}))
        self._alter(lambda x:x["sources"][1].update(
            {"url":"https://fake.example/products/b-186603"}))
        self._alter(lambda x:x["sources"].pop())

if __name__=="__main__":
    unittest.main()
