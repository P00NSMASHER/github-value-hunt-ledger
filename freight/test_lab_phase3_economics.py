import unittest
from dataclasses import replace
from freight.lab_phase3_economics import (
    ContingencyAssumptions, EconomicsRejected, analyze_contingency,
    fixed_default_contingency_bps, compare_scenarios,
)


def assumption(**overrides):
    values=dict(opportunity_cents=150000,probability_valid_bps=5000,
        probability_customer_recovery_bps=6000,probability_fee_collection_bps=8000,
        expected_reversal_bps=1000,contingency_rate_bps=fixed_default_contingency_bps(),
        free_audit_minutes=150,recovery_work_minutes_if_valid=120,
        loaded_analyst_hourly_cents=4500,acquisition_cost_cents=2000,
        other_delivery_cost_cents=3000,recovery_delay_days=75)
    values.update(overrides)
    return ContingencyAssumptions(**values)


class EconomicsTests(unittest.TestCase):
    def test_free_audit_negative_margin_remains(self):
        r=analyze_contingency(assumption())
        self.assertEqual(r.upfront_audit_revenue_cents,0)
        self.assertEqual(r.expected_net_margin_cents,-11030)
        self.assertEqual(r.assessment,"MODELED_UNECONOMIC_HOLD")
        self.assertGreater(r.break_even_potential_recovery_cents,150000)
        self.assertEqual(r.scope,"UNCALIBRATED_SIMULATED_CONTINGENCY_MODEL")

    def test_reported_break_even_is_exact_at_cent_level(self):
        # The old continuous-rate approximation said 320,217 cents was enough,
        # but the same model's discrete fee path collected only 20,749 cents.
        under = analyze_contingency(assumption(opportunity_cents=320217))
        self.assertEqual(under.expected_net_margin_cents, -1)
        threshold = under.break_even_potential_recovery_cents
        self.assertEqual(threshold, 320220)
        below = analyze_contingency(assumption(opportunity_cents=threshold - 1))
        at = analyze_contingency(assumption(opportunity_cents=threshold))
        self.assertLess(below.expected_net_margin_cents, 0)
        self.assertGreaterEqual(at.expected_net_margin_cents, 0)

    def test_fractional_expected_recovery_labor_is_not_rounded_away(self):
        a = assumption(
            opportunity_cents=0, free_audit_minutes=0,
            recovery_work_minutes_if_valid=1, probability_valid_bps=5000,
            loaded_analyst_hourly_cents=6000,
            acquisition_cost_cents=0, other_delivery_cost_cents=0,
        )
        decision = analyze_contingency(a)
        self.assertEqual(decision.expected_recovery_work_cost_cents, 50)
        self.assertEqual(decision.expected_net_margin_cents, -50)

    def test_breakeven_unreachable_within_supported_input_cap(self):
        a = assumption(acquisition_cost_cents=2**63 - 1)
        decision = analyze_contingency(a)
        self.assertIsNone(decision.break_even_potential_recovery_cents)
        self.assertEqual(decision.assessment, "MODELED_UNECONOMIC_HOLD")

    def test_break_even_is_zero_when_no_cost_at_all(self):
        a = assumption(
            free_audit_minutes=0, recovery_work_minutes_if_valid=0,
            loaded_analyst_hourly_cents=0, acquisition_cost_cents=0,
            other_delivery_cost_cents=0,
        )
        decision = analyze_contingency(a)
        self.assertEqual(decision.break_even_potential_recovery_cents, 0)
        self.assertEqual(decision.expected_net_margin_cents, decision.expected_collected_fee_cents)

    def test_default_rate_matches_existing_commercial_terms(self):
        self.assertEqual(fixed_default_contingency_bps(),3000)

    def test_zero_recovery_means_zero_fee_not_zero_cost(self):
        r=analyze_contingency(assumption(opportunity_cents=0))
        self.assertEqual((r.expected_gross_fee_cents,r.expected_collected_fee_cents),(0,0))
        self.assertLess(r.expected_net_margin_cents,0)

    def test_full_reversal_eliminates_fee(self):
        r=analyze_contingency(assumption(expected_reversal_bps=10000))
        self.assertEqual(r.expected_collected_fee_cents,0)
        self.assertIsNone(r.break_even_potential_recovery_cents)

    def test_no_fee_collection_eliminates_margin(self):
        r=analyze_contingency(assumption(probability_fee_collection_bps=0))
        self.assertLess(r.expected_net_margin_cents,0)

    def test_parameter_limits(self):
        for change in [dict(probability_valid_bps=10001),dict(free_audit_minutes=True),
                       dict(contingency_rate_bps=10000),dict(currency="EUR")]:
            with self.assertRaises(EconomicsRejected): assumption(**change)

    def test_scenarios_are_separated_from_actual_results(self):
        r=compare_scenarios({"base":assumption(),"no_recovery":assumption(opportunity_cents=0)})
        self.assertEqual(r["scope"],"MODELED_PILOT_NO_REAL_CUSTOMERS")
        self.assertLess(r["scenarios"]["no_recovery"]["expected_net_margin_cents"],0)

    def test_immutable_receipt_changes_on_assumptions(self):
        x=analyze_contingency(assumption())
        y=analyze_contingency(assumption(acquisition_cost_cents=2001))
        self.assertNotEqual(x.receipt_sha256,y.receipt_sha256)

if __name__=="__main__":unittest.main()
