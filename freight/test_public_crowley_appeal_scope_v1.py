"""Original 2025 D.C. Circuit federal freight-audit authority is not savings proof."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from freight import public_crowley_appeal_scope_v1 as source

class OriginalFederalAppellateScopeTest(unittest.TestCase):
    def test_original_crowley_scope_holding_without_any_recovery_proof(self):
        x=source.report()
        self.assertEqual(x["original_published_decisions"],1)
        self.assertEqual(x["official_opinion_date"],"2025-07-18")
        self.assertTrue(x["court_reversed_lower_GSA_audit_scope_holding"])
        self.assertTrue(x["court_remanded_for_further_proceedings"])
        self.assertTrue(x["court_did_not_award_individual_damages"])
        self.assertEqual(x["published_minimum_notices_of_overcharge_alleged_exceeds"],50000)
        self.assertEqual(x["published_alleged_gross_amount_approx_usd"],37000000)
        self.assertFalse(x["historical_notices_are_customer_errors_confirmed"])
        self.assertEqual(x["contemporaneous_court_of_federal_claims_demand_usd_not_paid"],11800000)
        self.assertFalse(x["later_litigation_or_payment_2026_outcome_verified"])
        self.assertFalse(x["no_private_commercial_freight_setoff_authority"])
        self.assertEqual(x["retally_real_customer_invoice_count"],0)
        self.assertEqual(x["retally_recovered_cents"],0)
        self.assertEqual(x["commercial_claim_clearance"],"NO_GO")

    def _mutate(self,edit):
        facts=json.loads(source.SOURCE.read_text(encoding="utf-8"))
        edit(facts)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"tampered.json"
            p.write_text(json.dumps(facts),encoding="utf-8")
            with patch.object(source,"SOURCE",p):
                with self.assertRaisesRegex(ValueError,"CROWLEY_APPEAL_ORIGINAL_SOURCE_"):
                    source.report()

    def test_alleged_nocs_cannot_become_valid_customer_overcharges(self):
        self._mutate(lambda x:x.update({"notices_are_allegations_not_validated_errors":False}))
        self._mutate(lambda x:x.update({"original_opinion_alleged_overcharge_approx_usd":99900000}))
        self._mutate(lambda x:x.update({"verified_overcharge_invoices":50000}))

    def test_separate_11_8m_damage_demand_is_not_court_award_or_paid(self):
        self._mutate(lambda x:x.update({"damages_demand_bank_payment_received_proven":True}))
        self._mutate(lambda x:x.update({"opinion_does_not_award_11_8m_damages":False}))
        self._mutate(lambda x:x.update({"damages_demand_current_2026_resolution_independently_checked":True}))

    def test_no_private_setoff_authority_or_customer_account_access(self):
        self._mutate(lambda x:x.update({"contract_specific_no_general_private_setoff_authority":False}))
        self._mutate(lambda x:x.update({"real_retally_customer_invoices_examined":1}))
        self._mutate(lambda x:x.update({"real_retally_customer_recoveries_cents":1180000000}))

    def test_provenance_original_court_pdf_and_date_cannot_be_forged(self):
        self._mutate(lambda x:x.update({"official_opinion_pdf":"https://untrusted.example/scope.pdf"}))
        self._mutate(lambda x:x.update({"majority_opinion_date":"2026-07-18"}))
        self._mutate(lambda x:x.update({"independent_full_pdf_original_sha256_verified":True}))

    def test_gsa_2023_vendor_payment_is_distinct_from_unawarded_2025_damages_claim(self):
        from freight.public_gsa_false_positive_payment_v1 import report as fund
        older=fund()
        appellate=source.report()
        self.assertEqual(older["publisher_reported_vendor_payment_approx_cents"],2960000000)
        self.assertEqual(appellate["contemporaneous_court_of_federal_claims_demand_usd_not_paid"],11800000)
        self.assertFalse(appellate["court_did_not_award_individual_damages"] is False)
        self.assertEqual(older["validated_RETALLY_customer_cash_cents"],0)

if __name__=="__main__":
    unittest.main()
