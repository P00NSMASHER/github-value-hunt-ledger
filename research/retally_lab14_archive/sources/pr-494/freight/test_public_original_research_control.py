"""Lab 14 original public source corpus must never self-promote recovery claims."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from freight import public_original_research_control as src


class Lab14PublicSourceCensusTests(unittest.TestCase):
    def test_fixed_source_census_without_any_first_party_customer_recovery(self):
        data=src.snapshot()
        self.assertEqual(data["total_bounded_observations"],307)
        self.assertEqual(len(data["original_public_source_record_counts"]),5)
        self.assertEqual(data["standalone_official_publisher_examples"],1)
        self.assertEqual(data["separate_original_SEC_historical_carrier_agreements"],2)
        self.assertTrue(data["SEC_contracts_not_in_307_public_observation_count"])
        self.assertTrue(data["SEC_2007_local_vs_2005_national_index_distinct"])
        self.assertTrue(data["SEC_no_original_customer_invoices_or_2026_contract_applicability"])
        self.assertEqual(data["separate_Crowley_GSA_2023_2025_original_source_documents"],3)
        self.assertEqual(data["separate_Crowley_GSA_financial_timeline_events"],4)
        self.assertTrue(data["court_original_2023_DFTS_refund_promise_is_same_29_6m_as_GSA_reported_payment"])
        self.assertTrue(data["court_budget_pair_not_two_independent_29_6m_payments"])
        self.assertTrue(data["court_separate_Ocean_USC9_refund_35840_43_PROMISE_NOT_PAID"])
        self.assertTrue(data["court_11_8m_claim_as_of_2025_NOT_AN_APPELLATE_AWARD_OR_PAID"])
        self.assertFalse(data["court_private_statutory_setoff_right_for_RETALLY"])
        self.assertEqual(data["standalone_external_adjudication_records"],1)
        self.assertEqual(data["separate_original_GAO_historical_collection_decisions"],7)
        self.assertEqual(data["separate_GAO_reported_historical_collection_events"],9)
        self.assertEqual(data["GAO_original_reported_refunds"],3)
        self.assertEqual(data["GAO_original_reported_applied_setoffs"],6)
        self.assertTrue(data["GAO_decisions_are_external_historical_not_307_source_observations"])
        self.assertTrue(data["GAO_reported_collections_not_independently_Treasury_bank_verified"])
        self.assertIsNone(data["GAO_final_unreversed_net_government_recovery_total_cents"])
        self.assertTrue(data["GAO_future_uncollected_or_carrier_reimbursement_unverified"])
        self.assertTrue(data["GAO_1980_original_one_lot_vs_multiple_BOL_rate_reconciliation"])
        self.assertEqual(data["GAO_1980_one_lot_allowed_charge_cents"],617063)
        self.assertEqual(data["GAO_1980_multiple_BOL_carrier_rate_cents"],671075)
        self.assertEqual(data["GAO_1980_voluntary_carrier_refund_cents"],110967)
        self.assertEqual(data["GAO_1980_remainder_setoff_cents"],54012)
        self.assertTrue(data["GAO_1980_no_original_tariff_or_Treasury_receipt_examined"])
        self.assertEqual(data["separate_GSA_false_positive_correction_public_report_records"],1)
        self.assertEqual(data["GSA_historical_FY2023_VENDOR_REPAYMENT_approx_cents"],2960000000)
        self.assertTrue(data["GSA_payment_direction_government_to_vendor_NOT_RETALLY"])
        self.assertTrue(data["GSA_potential_additional_11_8m_vendor_repayment_UNVERIFIED"])
        self.assertTrue(data["government_NOCs_may_be_erroneous_and_collections_reversed"])
        self.assertEqual(data["census_official_md_origin_pums_record_count"],612317)
        self.assertEqual(data["census_official_md_origin_gvf_cv_percent"],"9.74")
        self.assertTrue(data["fmc_award_actual_cash_received_verified"] is False)
        self.assertEqual(data["real_RETALLY_customer_invoices_seen"],0)
        self.assertEqual(data["actual_RETALLY_cash_recovered_cents"],0)
        self.assertEqual(data["original_historical_findings_still_open"],26)
        self.assertEqual(data["independent_first_customer_human_gates_unmet"],18)
        self.assertEqual(data["commercial_claim_clearance"],"NO_GO")

    def test_locally_recomputable_digest_does_not_claim_external_signature(self):
        r=src.snapshot()
        claimed=r.pop("local_content_sha256")
        self.assertTrue(r.pop("local_hash_not_an_external_original_source_signature"))
        observed=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        self.assertEqual(claimed,observed)

    def test_forged_payment_is_never_counted_as_a_recovery(self):
        original=src.verified_public_order()
        with patch.object(src,"verified_public_order",return_value={
            **original,"actual_payment_verified_cents":965451}):
            with self.assertRaisesRegex(ValueError,"LAB14_PUBLIC_EVIDENCE_INVALID_CUSTOMER_CLAIM"):
                src.snapshot()

    def test_census_prefix_cannot_be_promoted_to_full_statistical_estimate(self):
        original=src.cfs_prefix()
        with patch.object(src,"cfs_prefix",return_value={
            **original,"national_estimate_authorized":True}):
            with self.assertRaisesRegex(ValueError,"LAB14_PUBLIC_EVIDENCE_INVALID_CUSTOMER_CLAIM"):
                src.snapshot()

    def test_stb_2024_accounting_period_cannot_relabel_2018_waybills(self):
        original=src.stb_prefix()
        with patch.object(src,"stb_prefix",return_value={
            **original,"waybill_year_histogram":{"2024":100}}):
            with self.assertRaisesRegex(ValueError,"LAB14_PUBLIC_EVIDENCE_INVALID_CUSTOMER_CLAIM"):
                src.snapshot()

    def test_source_counts_cannot_silently_add_forged_records(self):
        original=src.public_context_report()
        with patch.object(src,"public_context_report",return_value={
            **original,"faf6_source_rows_in_snapshot":79}):
            with self.assertRaisesRegex(ValueError,"LAB14_PUBLIC_EVIDENCE_SOURCE_COUNTS"):
                src.snapshot()

    def test_false_independent_gao_bank_settlement_is_rejected(self):
        original=src.public_collection_report()
        with patch.object(src,"public_collection_report",return_value={
            **original,
            "actual_carrier_account_bank_or_Treasury_posting_independently_verified":True,
        }):
            with self.assertRaisesRegex(ValueError,"LAB14_PUBLIC_EVIDENCE_INVALID_CUSTOMER_CLAIM"):
                src.snapshot()

    def test_forged_gao_net_collection_or_incorrect_event_count_fails(self):
        original=src.public_collection_report()
        for key,change in [
            ("final_unreversed_net_government_recovery_total_cents",457107),
            ("gao_reported_collection_events",8),
            ("real_RETALLY_customer_recoveries_cents",457107),
        ]:
            with self.subTest(key=key):
                with patch.object(src,"public_collection_report",return_value={
                    **original,key:change,
                }):
                    with self.assertRaisesRegex(ValueError,"LAB14_PUBLIC_EVIDENCE_INVALID_CUSTOMER_CLAIM"):
                        src.snapshot()

    def test_gsa_real_vendor_repayment_cannot_be_counted_as_retally_savings(self):
        original=src.gsa_false_positive_refund()
        for field,bad_value in [
            ("is_recovered_overcharge_by_RETALLY",True),
            ("reported_payment_FROM_government_TO_vendor",False),
            ("validated_RETALLY_customer_cash_cents",2960000000),
            ("possible_additional_payment_executed",True),
        ]:
            with self.subTest(field=field):
                with patch.object(src,"gsa_false_positive_refund",
                                  return_value={**original,field:bad_value}):
                    with self.assertRaisesRegex(
                        ValueError,"LAB14_PUBLIC_EVIDENCE_INVALID_CUSTOMER_CLAIM"
                    ):
                        src.snapshot()

    def test_GAO_1980_competing_trailer_rate_cannot_fake_modern_recovery(self):
        original=src.public_collection_report()
        for field,new in [
            ("original_GAO_1980_one_tender_correct_charge_cents",617064),
            ("original_GAO_1980_carrier_multiple_BOL_competing_charge_cents",617063),
            ("original_GAO_1980_carrier_partial_refund_cents",164979),
            ("original_GAO_1980_remaining_government_setoff_cents",0),
            ("original_GAO_1980_no_original_bill_or_tariff_scans",False),
        ]:
            with self.subTest(field=field):
                with patch.object(src,"public_collection_report",return_value={
                    **original,field:new
                }):
                    with self.assertRaisesRegex(
                        ValueError,"LAB14_PUBLIC_EVIDENCE_INVALID_CUSTOMER_CLAIM"
                    ):
                        src.snapshot()

    def test_source_census_rejects_2026_eia_substitution_for_local_2007_rate(self):
        original=src.original_sec_contract_report()
        with patch.object(src,"original_sec_contract_report",return_value={
            **original,"2026_EIA_prices_not_approved_for_2007_local_index":False,
        }):
            with self.assertRaisesRegex(ValueError,"LAB14_PUBLIC_EVIDENCE_INVALID_CUSTOMER_CLAIM"):
                src.snapshot()

    def test_forged_current_customer_contract_or_wrong_2005_fuel_units_fail(self):
        original=src.original_sec_contract_report()
        for change in [
            {"actual_RETALLY_customer_invoices":1},
            {"historical_governing_index_methods":{
                "NEDAK_WESTERN_2007":"DOE_NATIONAL_AVERAGE_DIESEL_MON_OR_FEDERAL_HOLIDAY_TUE",
                "SWIFT_LOAD_SOURCE_2005":"LOCAL_NONAFFILIATED_NO2_DIESEL_RETAIL_O_NEILL_NE",
            }},
            {"NEDAK_illustration_not_actual_invoice":{
                **original["NEDAK_illustration_not_actual_invoice"],
                "hypothetical_unamended_freight_charge_usd":"14.33",
            }},
        ]:
            with self.subTest(changed=list(change)),patch.object(
                src,"original_sec_contract_report",return_value={**original,**change}
            ):
                with self.assertRaisesRegex(ValueError,"LAB14_PUBLIC_EVIDENCE_INVALID_CUSTOMER_CLAIM"):
                    src.snapshot()

    def test_dftsi_2023_original_promise_and_reported_paid_amount_not_double_counted(self):
        original=src.original_court_money_lineage()
        with patch.object(src,"original_court_money_lineage",return_value={
            **original,"GSA_FY2023_reported_vendor_refund_approx_cents":5920000000,
        }):
            with self.assertRaisesRegex(ValueError,"LAB14_PUBLIC_EVIDENCE_INVALID_CUSTOMER_CLAIM"):
                src.snapshot()
        with patch.object(src,"original_court_money_lineage",return_value={
            **original,"must_not_double_count_29_6m_as_59_2m":False,
        }):
            with self.assertRaisesRegex(ValueError,"LAB14_PUBLIC_EVIDENCE_INVALID_CUSTOMER_CLAIM"):
                src.snapshot()

    def test_distinct_ocean_promise_and_claims_court_11800000_not_earned(self):
        original=src.original_court_money_lineage()
        for change in [
            {"2023_Ocean_USC9_bank_payment_verified":True},
            {"2025_11_8m_claim_was_awarded_or_paid_by_appeal":True},
            {"RETALLY_customer_cash_recovered_cents":1180000000},
            {"private_RETALLY_can_issue_statutory_GSA_offsets":True},
        ]:
            with self.subTest(change=change),patch.object(src,"original_court_money_lineage",
                                                          return_value={**original,**change}):
                with self.assertRaisesRegex(ValueError,"LAB14_PUBLIC_EVIDENCE_INVALID_CUSTOMER_CLAIM"):
                    src.snapshot()

    def test_report_contains_no_raw_customer_personal_information(self):
        summary=src.snapshot()
        html=src.html_report(summary)
        self.assertIn("research only",html)
        self.assertIn("NOT verified customer invoices",html)
        self.assertIn("Seven distinct GAO government historical case decisions",html)
        self.assertIn("no original bank/Treasury postings",html)
        self.assertIn("ERRONEOUS notices of overcharge",html)
        self.assertNotIn("Work email:",html)
        self.assertNotIn("SHIPMT_ID,",html)
        self.assertNotIn("Customer recovered",html)

    def test_sanitized_json_and_html_are_written_only_with_explicit_output(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            summary=src.snapshot()
            rendered=src.html_report(summary)
            (d/"index.html").write_text(rendered)
            (d/"public_evidence_census.json").write_text(json.dumps(summary))
            saved=json.loads((d/"public_evidence_census.json").read_text())
            self.assertEqual(saved["total_bounded_observations"],307)
            self.assertTrue((d/"index.html").read_text().startswith("<!doctype html>"))


if __name__=="__main__":
    unittest.main()
