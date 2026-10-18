"""First-party federal court/source chronology and cash-settlement segregation."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from freight import public_crowley_court_money_lineage_v1 as court


class CrowleyCourtOriginalTimeline(unittest.TestCase):
    def test_district_court_letter_GSA_budget_payment_and_appeal_are_not_three_recoveries(self):
        r=court.report()
        self.assertEqual(r["source_documents"],3)
        self.assertEqual(r["source_timeline_events"],4)
        self.assertTrue(r["2023_DFTS_29_6m_refund_promise_and_GSA_paid_report_same_money"])
        self.assertEqual(r["GSA_FY2023_reported_vendor_refund_approx_cents"],2960000000)
        self.assertFalse(r["GSA_FY2023_bank_transfer_receipt_independently_authenticated"])
        self.assertTrue(r["must_not_double_count_29_6m_as_59_2m"])
        self.assertEqual(r["RETALLY_customer_cash_recovered_cents"],0)
        self.assertEqual(r["commercial_claim_clearance"],"NO_GO")

    def test_separate_Ocean_contract_promised_amount_not_recognized_as_paid(self):
        r=court.report()
        self.assertEqual(r["2023_separate_Ocean_USC9_refund_only_promised_cents"],3584043)
        self.assertFalse(r["2023_Ocean_USC9_bank_payment_verified"])

    def test_2025_11_8m_Crowley_claim_not_damages_award_or_verified_paid(self):
        r=court.report()
        self.assertEqual(r["2025_11_8m_Claims_Court_damages_claim_cents"],1180000000)
        self.assertFalse(r["2025_11_8m_claim_was_awarded_or_paid_by_appeal"])
        self.assertIsNone(r["current_2026_parallel_docket_resolution"])

    def test_statutory_Crowley_GSA_scope_not_new_private_recovery_authority(self):
        r=court.report()
        self.assertTrue(r["DCCircuit_2025_limited_GSA_audit_to_carriers_and_freight_forwarders"])
        self.assertTrue(r["Crowley_this_case_not_a_carrier_or_forwarder"])
        self.assertFalse(r["private_RETALLY_can_issue_statutory_GSA_offsets"])

    def _forge(self,change):
        original=json.loads(court.SRC.read_text(encoding="utf-8"))
        change(original)
        with tempfile.TemporaryDirectory() as td:
            dest=Path(td)/"forged.json";dest.write_text(json.dumps(original))
            with patch.object(court,"SRC",dest):
                with self.assertRaisesRegex(ValueError,"COURT_MONEY_EVIDENCE_"):
                    court.verified_original_court_money_timeline()

    def test_no_fake_court_grant_of_11800000_cash(self):
        self._forge(lambda x:x["appellate_decision"].update(
            {"dollar_damages_awarded_in_this_appeal_cents":1180000000}))
        self._forge(lambda x:x["publisher_reported_events"][3].update(
            {"claim_paid_by_government_as_of_opinion_verified":True}))
        self._forge(lambda x:x["appellate_decision"].update(
            {"parallel_11_8m_damages_claim_resolved_by_this_appeal":True}))

    def test_cannot_double_count_2023_promise_and_FY2023_report_as_two_payments(self):
        self._forge(lambda x:x["duplicate_and_netting_policy"].update(
            {"must_not_sum_these_two_as_59_2m":False}))
        self._forge(lambda x:x["duplicate_and_netting_policy"].update(
            {"APR2023_promise_and_FY2023_reported_payment_same_underlying_29_6m":False}))
        self._forge(lambda x:x["publisher_reported_events"][0].update(
            {"amount_cents":5920000000}))

    def test_other_contract_35840_43_promise_not_authorized_bank_refund(self):
        self._forge(lambda x:x["publisher_reported_events"][2].update(
            {"actual_payment_verified":True}))
        self._forge(lambda x:x["publisher_reported_events"][2].update(
            {"money_scope":"All RETALLY private customer transportation invoices"}))

    def test_source_domain_forged_GSA_document_date_invented_or_publisher_digest_claim_fail(self):
        self._forge(lambda x:x["source_documents"][0].update(
            {"official_url":"https://untrusted.example/third-party-retyped.pdf"}))
        self._forge(lambda x:x["source_documents"][1].update(
            {"decided":"2024-03-01"}))
        self._forge(lambda x:x["source_documents"][2].update(
            {"full_original_source_pdf_downloaded_and_sha_verified":True}))

    def test_actual_private_customer_or_external_bank_custody_cannot_be_forged(self):
        self._forge(lambda x:x["proof_limits"].update(
            {"actual_bank_or_Treasury_transfer_statement_examined":True}))
        self._forge(lambda x:x["proof_limits"].update(
            {"RETALLY_customer_verified_recovered_cents":2960000000}))
        self._forge(lambda x:x["proof_limits"].update(
            {"complete_2026_case_docket_checked":True}))
        self._forge(lambda x:x["proof_limits"].update(
            {"published_statutory_holding_does_not_authorize_private_carrier_offsets":False}))

    def test_court_dissent_and_holding_cannot_be_changed_to_grant_auditor_power(self):
        self._forge(lambda x:x["appellate_decision"].update(
            {"private_company_auditing_authority_granted":True}))
        self._forge(lambda x:x["appellate_decision"].update(
            {"holding_limited_to":"Any private recovery company may audit and deduct from carrier accounts"}))
        self._forge(lambda x:x["appellate_decision"].update(
            {"remanded_for_further_proceedings":False}))

if __name__=="__main__":
    unittest.main()
