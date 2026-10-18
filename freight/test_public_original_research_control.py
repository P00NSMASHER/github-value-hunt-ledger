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
        self.assertEqual(data["separate_GAO_1979_improper_setoff_decisions"],1)
        self.assertEqual(data["GAO_1979_applied_but_later_disallowed_offset_cents"],514105)
        self.assertTrue(data["GAO_1979_reversal_reimbursement_not_verified"])
        self.assertTrue(data["GAO_1979_negative_case_not_approved_collection"])
        self.assertTrue(data["GAO_1979_private_setoff_authority_not_established"])
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

    def test_improper_setoff_reversal_cannot_be_reported_as_valid_collected_money(self):
        original=src.verified_historical_reversal()
        for key,bad in [
            ("illegal_postpetition_offset_is_valid_permanent_recovery",True),
            ("independent_carrier_repayment_bank_receipt_obtained",True),
            ("government_final_net_collections_credible_cents",514105),
            ("actual_RETALLY_cash_recovered_cents",514105),
        ]:
            with self.subTest(key=key):
                with patch.object(src,"verified_historical_reversal",return_value={**original,key:bad}):
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
        self.assertIn("GAO decision found $5,141.05",html)
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
