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
