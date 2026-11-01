"""Regression tests for illustrative, no-upfront recovery economics."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import json
import unittest
from freight.commercial.zero_upfront_underwriting import model_scenario

FIXTURE=json.loads((Path(__file__).parent/"fixtures"/"zero_upfront_synthetic_example.json").read_text())

class NoUpfrontUnderwriting(unittest.TestCase):
    def scenario(self, **override):
        s=deepcopy(FIXTURE)
        s.update(override)
        return s

    def test_zero_recovery_still_costs_money(self):
        r=model_scenario(self.scenario())
        self.assertEqual(r["cost"]["delivery_cost_usd"],"2500.00")
        self.assertEqual(r["cost"]["zero_recovery_fee_usd"],"0.00")
        self.assertEqual(r["cost"]["zero_recovery_loss_usd"],"2500.00")
        self.assertFalse(r["customer_kickoff_authorized"])

    def test_no_unapproved_fee_is_entered_as_binding(self):
        r=model_scenario(self.scenario())
        self.assertFalse(r["customer_price_or_approved_rate"])
        self.assertIn("actual_rate_approved_in_signed_terms",r["blocking_reasons"])
        self.assertEqual(r["risk_decision"],"HOLD")

    def test_arithmetic_and_actual_receipt_breakeven(self):
        r=model_scenario(self.scenario())
        v=r["illustrative_only"]
        self.assertEqual(v["modeled_expected_fee_usd"],"4680.00")
        self.assertEqual(v["modeled_expected_contribution_usd"],"2180.00")
        self.assertEqual(v["break_even_actual_fee_eligible_receipts_usd"],"12500.00")
        self.assertEqual(v["break_even_supported_opportunity_usd"],"26709.40")

    def test_all_hypothetical_approvals_do_not_authorize_kickoff(self):
        s=self.scenario(**{
            "actual_rate_approved_in_signed_terms":True,
            "buyer_specific_scope_authorized":True,
            "buyer_data_controls_verified":True,
            "independent_reviewer_reserved":True,
        })
        r=model_scenario(s)
        self.assertEqual(r["risk_decision"],"HUMAN_REVIEW_REQUIRED_NOT_KICKOFF_AUTHORIZED")
        self.assertFalse(r["customer_kickoff_authorized"])

    def test_too_many_review_hours_blocks(self):
        r=model_scenario(self.scenario(analyst_hours="20"))
        self.assertIn("planned_hours_exceed_cap",r["blocking_reasons"])

    def test_worst_case_loss_exceeds_cap_blocks(self):
        r=model_scenario(self.scenario(max_authorized_loss_usd="2000"))
        self.assertIn("zero_recovery_cash_loss_exceeds_cap",r["blocking_reasons"])

    def test_fee_expectation_below_margin_blocks(self):
        r=model_scenario(self.scenario(realization_fraction="0.10"))
        self.assertIn("hypothetical_margin_below_target",r["blocking_reasons"])

    def test_no_recovery_probability_blocks(self):
        r=model_scenario(self.scenario(realization_fraction="0"))
        self.assertIn("no_probability_adjusted_fee",r["blocking_reasons"])
        self.assertEqual(r["illustrative_only"]["break_even_supported_opportunity_usd"],None)

    def test_three_pilot_downside_is_counted(self):
        r=model_scenario(self.scenario())
        self.assertEqual(r["cost"]["founder_program_pilot_slots"],3)
        self.assertEqual(r["cost"]["program_zero_recovery_loss_usd"],"7500.00")
        self.assertEqual(r["cost"]["program_maximum_loss_cap_usd"],"8000.00")

    def test_portfolio_cap_blocks_even_if_individual_cap_passes(self):
        r=model_scenario(self.scenario(max_program_zero_recovery_loss_usd="7000.00"))
        self.assertIn("program_zero_recovery_loss_exceeds_cap",r["blocking_reasons"])
        self.assertNotIn("zero_recovery_cash_loss_exceeds_cap",r["blocking_reasons"])

    def test_founder_slots_are_bounded_to_three(self):
        for val in (0, 4, "3", True):
            with self.subTest(val=val), self.assertRaisesRegex(ValueError,"max_founder_program_pilots"):
                model_scenario(self.scenario(max_founder_program_pilots=val))

    def test_owner_labor_cannot_be_free(self):
        with self.assertRaisesRegex(ValueError,"founder/reviewer"):
            model_scenario(self.scenario(loaded_hourly_cost_usd="0"))

    def test_nan_and_negative_inputs_fail(self):
        for bad in ("NaN","Infinity","-1",True):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                model_scenario(self.scenario(analyst_hours=bad))

    def test_over_one_probability_fails(self):
        with self.assertRaisesRegex(ValueError,"realization_fraction"):
            model_scenario(self.scenario(realization_fraction="1.01"))

    def test_rate_must_be_bounded(self):
        for bad in ("0","1","1.01"):
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,"hypothetical_contingency_rate"):
                model_scenario(self.scenario(hypothetical_contingency_rate=bad))

    def test_real_data_not_admitted_into_public_fixture(self):
        with self.assertRaisesRegex(ValueError,"real customer inputs"):
            model_scenario(self.scenario(is_synthetic=False))

    def test_unknown_fields_fail_closed(self):
        s=self.scenario(actual_rate="0.99")
        with self.assertRaisesRegex(ValueError,"schema mismatch"):
            model_scenario(s)

    def test_invalid_approval_flag_rejected(self):
        with self.assertRaisesRegex(ValueError,"boolean"):
            model_scenario(self.scenario(actual_rate_approved_in_signed_terms="true"))

if __name__=="__main__":
    unittest.main()
