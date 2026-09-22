import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.engines.utility import (
    UtilityTariff,
    EnergyTier,
    bill,
    calculate_expected_bill,
    detect_utility_variance,
    tariff,
    tier,
)


class UtilityRecoveryEngineTests(unittest.TestCase):
    def test_flat_energy_plus_fixed_charge(self):
        t = tariff(
            tariff_id="t1", effective_from="2026-01-01", effective_to=None,
            fixed_charge_cents=1000,
            energy_tiers=(tier(None, "10"),),
            demand_rate_cents_per_kw="0",
            source_hash="thash", locator="source://tariff", verified=True,
        )
        b = bill(
            bill_id="b1", bill_date="2026-06-01", usage_kwh="100", demand_kw="0",
            billed_cents=2500, currency="USD", source_hash="bhash",
            locator="source://bill", verified=True,
        )
        calc = calculate_expected_bill(t, b)
        self.assertEqual(calc.total_cents, 2000)
        finding = RecoveryEngine().evaluate(
            detect_utility_variance(client_id="client", utility_id="utility", tariff=t, bill=b)
        )
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.potential_recovery_cents, 500)

    def test_tier_and_demand_math(self):
        t = tariff(
            tariff_id="t2", effective_from="2026-01-01", effective_to=None,
            fixed_charge_cents=500,
            energy_tiers=(tier("100", "10"), tier(None, "20")),
            demand_rate_cents_per_kw="150.5",
            source_hash="thash", locator="source://tariff", verified=True,
        )
        b = bill(
            bill_id="b2", bill_date="2026-06-01", usage_kwh="150", demand_kw="2",
            billed_cents=4000, currency="USD", source_hash="bhash",
            locator="source://bill", verified=True,
        )
        calc = calculate_expected_bill(t, b)
        self.assertEqual(calc.energy_cents, 2000)
        self.assertEqual(calc.demand_cents, 301)
        self.assertEqual(calc.total_cents, 2801)

    def test_fractional_rates_round_only_at_charge_boundary(self):
        t = tariff(
            tariff_id="t3", effective_from="2026-01-01", effective_to=None,
            fixed_charge_cents=0,
            energy_tiers=(tier(None, "12.345"),),
            demand_rate_cents_per_kw="0",
            source_hash="thash", locator="source://tariff", verified=True,
        )
        b = bill(
            bill_id="b3", bill_date="2026-06-01", usage_kwh="10", demand_kw="0",
            billed_cents=124, currency="USD", source_hash="bhash",
            locator="source://bill", verified=True,
        )
        self.assertEqual(calculate_expected_bill(t, b).total_cents, 123)

    def test_unverified_bill_keeps_finding_in_review(self):
        t = tariff(
            tariff_id="t4", effective_from="2026-01-01", effective_to=None,
            fixed_charge_cents=0, energy_tiers=(tier(None, "10"),),
            demand_rate_cents_per_kw="0", source_hash="thash",
            locator="source://tariff", verified=True,
        )
        b = bill(
            bill_id="b4", bill_date="2026-06-01", usage_kwh="100", demand_kw="0",
            billed_cents=1500, currency="USD", source_hash="bhash",
            locator="source://bill", verified=False,
        )
        finding = RecoveryEngine().evaluate(
            detect_utility_variance(client_id="client", utility_id="utility", tariff=t, bill=b)
        )
        self.assertIs(finding.state, FindingState.REVIEW)

    def test_out_of_period_tariff_is_review_only(self):
        t = tariff(
            tariff_id="old", effective_from="2025-01-01", effective_to="2025-12-31",
            fixed_charge_cents=0, energy_tiers=(tier(None, "10"),),
            demand_rate_cents_per_kw="0", source_hash="thash",
            locator="source://tariff", verified=True,
        )
        b = bill(
            bill_id="b5", bill_date="2026-06-01", usage_kwh="100", demand_kw="0",
            billed_cents=1500, currency="USD", source_hash="bhash",
            locator="source://bill", verified=True,
        )
        finding = RecoveryEngine().evaluate(
            detect_utility_variance(client_id="client", utility_id="utility", tariff=t, bill=b)
        )
        self.assertIs(finding.state, FindingState.REVIEW)

    def test_nonincreasing_tiers_fail_closed(self):
        with self.assertRaises(ValueError):
            UtilityTariff(
                tariff_id="bad", effective_from="2026-01-01", effective_to=None,
                fixed_charge_cents=0,
                energy_tiers=(
                    tier("100", "10"),
                    tier("50", "20"),
                ),
                demand_rate_cents_per_kw=tier(None, "0").rate_cents_per_kwh,
                source_hash="h", locator="source://t", verified=True,
            )


if __name__ == "__main__":
    unittest.main()
