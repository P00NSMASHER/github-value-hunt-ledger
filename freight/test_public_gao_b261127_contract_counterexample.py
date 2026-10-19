"""Original 1996 GAO decision makes math-only freight recovery claims unsafe."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from freight import public_gao_b261127_contract_counterexample as source

class GAOOppositeContractInterpretationTests(unittest.TestCase):
    def test_original_freight_charge_and_government_alternative_both_reconcile(self):
        r=source.verify_1996_original_source()
        self.assertEqual(r["original_government_bill_of_lading_number"],"C-8,141,261")
        self.assertEqual(63*2500+2850+5590,165940)
        self.assertEqual(14320*200//100,28640)
        self.assertEqual(r["carrier_reported_note12_charges_cents"],165940)
        self.assertEqual(r["government_proposed_note12_charges_cents"],28640)
        self.assertEqual(r["numerical_difference_cents"],137300)

    def test_approved_prior_TCN_billing_invalidated_government_note12_overcharge(self):
        r=source.verify_1996_original_source()
        self.assertTrue(r["gaomajority_note12_carrier_billing_upheld"])
        self.assertTrue(r["gaodecision_note14_additional_charges_denied_as_duplicate"])
        self.assertTrue(r["prebilling_government_guidance_controls_specific_contract_interpretation"])
        self.assertTrue(r["course_of_performance_requires_contextual_review"])
        self.assertFalse(r["GAO_sustained_alleged_note12_overcharge"])
        self.assertEqual(r["GAO_case_supported_recoverable_note12_overcharge_cents"],0)
        self.assertFalse(r["real_original_invoice_or_signed_contract_scans_examined"])
        self.assertFalse(r["independent_bank_settlement_record_examined"])
        self.assertEqual(r["retally_real_recovery_cents"],0)

    def test_two_original_decisions_prove_billing_unit_not_a_universal_rule(self):
        r=source.compare_opposite_contract_interpretations()
        self.assertEqual(r["historical_1980_government_reported_refund_and_setoff_cents"],164979)
        self.assertEqual(r["historical_1996_apparent_charge_difference_cents"],137300)
        self.assertEqual(r["historical_1996_GAO_sustained_note12_overcharge_cents"],0)
        self.assertFalse(r["same_source_authority_or_tariff_in_both_cases"])
        self.assertFalse(r["one_bill_of_lading_always_equals_a_single_chargeable_shipment"])
        self.assertTrue(r["contract_effective_terms_must_be_independently_proven"])
        self.assertEqual(r["verified_RETALLY_recoveries_cents"],0)
        self.assertFalse(r["retally_prospect_contact_or_recovery_authorized"])
        self.assertEqual(r["commercial_claim_clearance"],"NO_GO")

    def _alter(self,fn):
        original=json.loads(source.SOURCE.read_text(encoding="utf-8"))
        fn(original)
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"bad.json"
            f.write_text(json.dumps(original))
            with patch.object(source,"SOURCE",f):
                with self.assertRaisesRegex(ValueError,"GAO_CONTRACT_INTERPRETATION_"):
                    source.verify_1996_original_source()

    def test_forged_invoice_disallowed_refund_or_false_recovery_is_rejected(self):
        self._alter(lambda x:x.update({"GAO_historical_result_note12":"GOVERNMENT_OVERCHARGE_UPHELD"}))
        self._alter(lambda x:x.update({"recoverable_overcharge_cents_under_GAO_note12_ruling":137300}))
        self._alter(lambda x:x.update({"original_carrier_invoice_image_independently_examined":True}))
        self._alter(lambda x:x.update({"retally_recovered_cents":137300}))

    def test_forged_charges_and_tcn_counts_are_rejected(self):
        self._alter(lambda x:x.update({"reported_actual_carrier_note12_charge_cents":165941}))
        self._alter(lambda x:x["historically_billed_note12_tcn_counts"].update({"minimum_charged_tcns":64}))
        self._alter(lambda x:x.update({"government_proposed_gbl_weight_pounds":14319}))
        self._alter(lambda x:x.update({"arithmetic_difference_cents_between_billing_methods":137301}))

    def test_government_pricing_guidance_cannot_be_ignored_or_invented(self):
        self._alter(lambda x:x.update({"agency_qualified_personnel_approved_TCN_billing_before_first_invoice":False}))
        self._alter(lambda x:x.update({"agency_no_objection_course_of_performance_over_three_years":False}))
        self._alter(lambda x:x.update({"contract_ambiguous_shipment_term":False}))
        self._alter(lambda x:x.update({"original_rate_tender_signed_copy_independently_examined":True}))

    def test_note14_extra_charges_remain_denied_even_when_note12_valid(self):
        self._alter(lambda x:x.update({"GAO_historical_result_note14":"APPROVED_EXTRA_TERMINAL_FEES"}))

    def test_no_wildcard_customer_data_or_source_replacement(self):
        self._alter(lambda x:x.update({"customer_invoice_cents":165940}))
        self._alter(lambda x:x.update({"source_url":"https://unknown.example/b-261127"}))
        self._alter(lambda x:x.update({"carrier_reported_1062_GBLs_billed_using_TCN_method_not_independently_verified":False}))

    def test_false_1980_bank_attestation_cannot_bypass_case_comparison(self):
        baseline=source.verify_gao_1980_original_rating_arithmetic()
        with patch.object(source,"verify_gao_1980_original_rating_arithmetic",return_value={
            **baseline,"independent_bank_or_Treasury_receipt_examined":True,
        }):
            with self.assertRaisesRegex(ValueError,"GAO_CONTRACT_INTERPRETATION_"):
                source.compare_opposite_contract_interpretations()

if __name__=="__main__":
    unittest.main()
