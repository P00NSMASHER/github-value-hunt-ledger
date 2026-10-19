"""Regression checks: collected offsets are not an unpaid award or RETALLY cash."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from freight import public_gao_historical_collection_v1 as source


class GAOHistoricalGovernmentCollections(unittest.TestCase):
    def test_agency_reported_collections_are_not_retally_cash(self):
        report=source.public_collection_report()
        self.assertEqual(report["historical_distinct_decisions"],7)
        self.assertEqual(report["gao_reported_collection_events"],9)
        self.assertEqual(report["agency_reported_collection_modes"],{
            "CARRIER_VOLUNTARILY_REFUNDED_GOVERNMENT":3,
            "GOVERNMENT_APPLIED_SET_OFF":6,
        })
        self.assertEqual(report["cases_with_uncollected_future_deduction"],1)
        self.assertEqual(report["cases_with_carrier_refund_authorized_but_unverified_paid"],1)
        self.assertEqual(report["cases_with_disputed_amount_variants"],1)
        self.assertTrue(report["source_transcribed_historical_collection_report_not_payment_bank_proof"])
        self.assertFalse(report["actual_carrier_account_bank_or_Treasury_posting_independently_verified"])
        self.assertIsNone(report["final_unreversed_net_government_recovery_total_cents"])
        self.assertEqual(report["real_RETALLY_customer_recoveries_cents"],0)
        self.assertEqual(report["real_RETALLY_customer_invoices_examined"],0)
        self.assertTrue(report["different_government_vs_private_shipper_legal_authority"])
        self.assertEqual(report["commercial_claim_clearance"],"NO_GO")

    def test_mixed_voluntary_refund_and_applied_offset_match_allowable_freight(self):
        x={row["case_id"]:row for row in source.verified_gao_cases()}["B-152324"]
        self.assertEqual(x["originally_paid_cents"],183525)
        self.assertEqual(x["final_agency_assessed_overcharge_cents"],125477)
        self.assertEqual(x["gao_reported_collection_events"],[
            {"kind":"CARRIER_VOLUNTARILY_REFUNDED_GOVERNMENT","amount_cents":51450},
            {"kind":"GOVERNMENT_APPLIED_SET_OFF","amount_cents":74027},
        ])
        self.assertEqual(183525-51450-74027,58048)

    def test_direct_original_1980_GAO_pdf_refund_plus_final_setoff(self):
        case={x["case_id"]:x for x in source.verified_gao_cases()}["B-197658"]
        self.assertEqual(case["decision_date"],"1980-08-25")
        self.assertEqual(case["source_url"],"https://www.gao.gov/assets/b-197658.pdf")
        self.assertEqual(case["originally_paid_cents"],782042)
        self.assertEqual(case["final_agency_assessed_overcharge_cents"],164979)
        self.assertEqual(case["gao_reported_collection_events"],[
            {"kind":"CARRIER_VOLUNTARILY_REFUNDED_GOVERNMENT","amount_cents":110967},
            {"kind":"GOVERNMENT_APPLIED_SET_OFF","amount_cents":54012},
        ])
        self.assertEqual(782042-110967-54012,617063)
        self.assertFalse(case["original_bill_of_lading_independently_examined"])

    def test_original_1980_GAO_pdf_partial_refund_cannot_be_counted_twice(self):
        self._tamper(lambda x:x["cases"][6]["gao_reported_collection_events"].append(
            {"kind":"GOVERNMENT_APPLIED_SET_OFF","amount_cents":54012}))
        self._tamper(lambda x:x["cases"][6]["gao_reported_collection_events"][0].update(
            {"amount_cents":164979}))
        self._tamper(lambda x:x["cases"][6].update(
            {"source_url":"https://www.gao.gov/products/b-197658"}))

    def test_uncollected_future_overcharge_cannot_be_counted_as_offset(self):
        x={row["case_id"]:row for row in source.verified_gao_cases()}["A-14046"]
        self.assertEqual(x["final_agency_assessed_overcharge_cents"],12775)
        self.assertEqual(x["gao_reported_collection_events"][0]["amount_cents"],8358)
        self.assertEqual(x["outstanding_or_future_collection_cents"],4417)
        self.assertEqual(8358+4417,12775)

    def test_authorized_carrier_repayment_is_not_confirmed_paid(self):
        x={row["case_id"]:row for row in source.verified_gao_cases()}["B-166167"]
        self.assertEqual(x["gao_reported_collection_events"][0]["amount_cents"],301632)
        self.assertEqual(x["carrier_reimbursement_authorized_but_payment_unverified_cents"],105083)
        self.assertIsNone(source.public_collection_report()["final_unreversed_net_government_recovery_total_cents"])

    def test_conflicting_claim_figure_is_separate_from_deducted_amount(self):
        x={row["case_id"]:row for row in source.verified_gao_cases()}["B-146511"]
        self.assertEqual(x["gao_reported_collection_events"][0]["amount_cents"],2074)
        self.assertEqual(x["supplemental_carrier_claim_amount_variants_cents"],[2070,2076])

    def _tamper(self,mutation):
        original=json.loads(source.SOURCE.read_text(encoding="utf-8"))
        mutation(original)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"tampered.json"
            p.write_text(json.dumps(original),encoding="utf-8")
            with patch.object(source,"SOURCE",p):
                with self.assertRaisesRegex(ValueError,"GAO_COLLECTION_PROOF_"):
                    source.verified_gao_cases()

    def test_forged_refund_and_uncollected_balance_are_rejected(self):
        self._tamper(lambda x:x["cases"][2]["gao_reported_collection_events"][1].update(
            {"amount_cents":125477}))
        self._tamper(lambda x:x["cases"][3].update(
            {"outstanding_or_future_collection_cents":0}))
        self._tamper(lambda x:x["cases"][4].update(
            {"carrier_reimbursement_authorized_but_payment_unverified_cents":0}))

    def test_false_original_invoice_and_real_retally_recovery_fields_fail(self):
        self._tamper(lambda x:x.update({"actual_retally_customer_recoveries_cents":457107}))
        self._tamper(lambda x:x["cases"][1].update({"original_bill_of_lading_independently_examined":True}))
        self._tamper(lambda x:x.update({"independent_Treasury_or_carrier_bank_transaction_statements_examined":1}))

    def test_unknown_source_host_double_count_and_extra_claim_field_rejected(self):
        self._tamper(lambda x:x["cases"][0].update(
            {"source_url":"https://not-government.example/products/b-148465"}))
        self._tamper(lambda x:x["cases"][2]["gao_reported_collection_events"].append(
            {"kind":"GOVERNMENT_APPLIED_SET_OFF","amount_cents":74027}))
        self._tamper(lambda x:x["cases"][3].update({"customer_invoice_usd":127.75}))
        self._tamper(lambda x:x["cases"][0].update({"case_id":"B-152324"}))

    def test_non_money_source_narratives_cannot_be_rewritten_as_retally_sales(self):
        self._tamper(lambda x:x["cases"][0].update({
            "historical_context":"RETALLY recovered funds from a modern customer invoice, cash already settled."
        }))
        self._tamper(lambda x:x["cases"][5].update({
            "historical_context":"All parties agree every historical reimbursement was paid and final."
        }))

    def test_missing_original_source_limitations_fail_closed(self):
        self._tamper(lambda x:x["explicit_source_limits"].__setitem__(
            0,"A bank and every carrier invoice were independently checked and verified.")
        )
        self._tamper(lambda x:x["explicit_source_limits"].__setitem__(
            4,"This sample represents current private freight contracts and proves savings.")
        )

    def test_fmc_adjudicated_award_is_a_distinct_lower_settlement_tier(self):
        from freight.public_fmc_adjudication_v1 import verified_public_order
        court=verified_public_order()
        agency=source.public_collection_report()
        self.assertEqual(court["documented_final_reparations_order_cents"],965451)
        self.assertIsNone(court["actual_payment_verified_cents"])
        self.assertTrue(agency["source_transcribed_historical_collection_report_not_payment_bank_proof"])
        self.assertEqual(agency["real_RETALLY_customer_recoveries_cents"],0)


    def test_real_1980_GAO_one_tender_versus_three_bills_rates_reconcile(self):
        math=source.verify_gao_1980_original_rating_arithmetic()
        self.assertEqual(math["original_paid_cents"],782042)
        self.assertEqual(math["real_one_tendered_lot_lb"],107129)
        self.assertEqual(math["carrier_proposed_two_bill_load_lb"],80506)
        self.assertEqual(math["carrier_proposed_third_bill_minimum_lb"],36000)
        self.assertEqual(math["historical_source_quoted_rate_cents_per_100lb"],576)
        self.assertEqual(math["GAO_correct_one_lot_charge_cents"],617063)
        self.assertEqual(math["carrier_competing_multiple_bill_charge_cents"],671075)
        self.assertEqual(math["carrier_voluntary_refund_cents"],110967)
        self.assertEqual(math["GAO_remaining_applied_setoff_cents"],54012)
        self.assertEqual(math["sum_original_historical_collections_cents"],164979)
        self.assertEqual(782042-110967-54012,617063)

    def test_competing_historical_BOL_grouping_cannot_fabricate_a_valid_rate(self):
        baseline=source.GAO_B197658_PUBLISHED_RATING
        for field,bad_value in [
            ("number_of_distinct_original_tendered_shipments",3),
            ("total_one_tendered_lot_lb",107128),
            ("minimum_weight_if_third_trailer_separate_lb",26623),
            ("historical_quoted_rate_cents_per_100lb",575),
            ("carrier_separate_trailers_claim_cents",617063),
        ]:
            with self.subTest(changed_field=field):
                altered={**baseline,field:bad_value}
                with patch.object(source,"GAO_B197658_PUBLISHED_RATING",altered):
                    with self.assertRaisesRegex(
                        ValueError,"GAO_COLLECTION_PROOF_1980_RATING_ORIGINAL_SOURCE_CHANGED"
                    ):
                        source.verify_gao_1980_original_rating_arithmetic()

    def test_original_PDF_source_math_is_not_original_tariff_or_cash_recovery_proof(self):
        result=source.verify_gao_1980_original_rating_arithmetic()
        self.assertFalse(result["quoted_historical_tariff_original_pages_examined"])
        self.assertFalse(result["original_bills_of_lading_images_examined"])
        self.assertFalse(result["independent_bank_or_Treasury_receipt_examined"])
        self.assertTrue(result["GAO_decision_PDF_text_read_but_complete_sha256_unverified"])
        self.assertEqual(result["real_RETALLY_customer_invoices"],0)
        self.assertEqual(result["real_RETALLY_recovery_cents"],0)
        self.assertEqual(result["commercial_claim_clearance"],"NO_GO")


if __name__=="__main__":
    unittest.main()
