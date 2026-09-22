import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.utility import (
    UtilityBill,
    UtilityCharge,
    UtilityChargeKind,
    UtilityTariff,
    audit_utility_bills,
    calculate_expected_bill,
    normalize_service_class,
)


def bill(*, actual=3000, bill_date="2026-07-15", verified=True, bill_id="b1"):
    return UtilityBill(
        bill_id=bill_id,
        utility_id="Utility A",
        account_id="acct-1",
        service_class="SC-2 D",
        bill_date=bill_date,
        actual_cents=actual,
        billed_kwh="100",
        billed_demand_kw="2",
        billed_reactive_kva="0",
        source_hash=f"billhash-{bill_id}",
        source_locator=f"file://bills.csv#{bill_id}",
        verified=verified,
    )


def tariff(
    *,
    energy_micros=100000,
    effective_from="2026-01-01",
    effective_to=None,
    verified=True,
    minimum=0,
):
    return UtilityTariff(
        utility_id="Utility A",
        service_class="SC2D",
        effective_from=effective_from,
        effective_to=effective_to,
        charges=(
            UtilityCharge("customer", UtilityChargeKind.FIXED, amount_cents=500),
            UtilityCharge(
                "energy", UtilityChargeKind.ENERGY,
                rate_micros_per_unit=energy_micros,
            ),
            UtilityCharge(
                "demand", UtilityChargeKind.DEMAND,
                rate_micros_per_unit=5_000_000,
            ),
        ),
        source_hash=f"tariffhash-{effective_from}",
        source_locator=f"file://tariff#{effective_from}",
        verified=verified,
        minimum_bill_cents=minimum,
        jurisdiction="NY",
    )


class UtilityBranchTests(unittest.TestCase):
    def test_service_class_normalization(self):
        self.assertEqual(normalize_service_class(" sc-2 d "), "SC2D")

    def test_fixed_energy_and_demand_math(self):
        expected, trace = calculate_expected_bill(bill(), tariff())
        self.assertEqual(expected, 2500)
        self.assertEqual([line["amount_cents"] for line in trace], [500, 1000, 1000])

    def test_minimum_bill_enforced(self):
        expected, trace = calculate_expected_bill(bill(), tariff(minimum=4000))
        self.assertEqual(expected, 4000)
        self.assertEqual(trace[-1]["kind"], "minimum")
        self.assertEqual(trace[-1]["amount_cents"], 1500)

    def test_verified_tariff_and_bill_produce_validated_overcharge(self):
        batch = audit_utility_bills(
            client_id="client",
            bills=(bill(actual=3000),),
            tariffs=(tariff(),),
        )
        self.assertEqual(batch.exceptions, ())
        self.assertEqual(len(batch.observations), 1)
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.potential_recovery_cents, 500)
        self.assertEqual(finding.expected_cents, 2500)
        self.assertEqual(finding.actual_cents, 3000)

    def test_unverified_tariff_or_bill_stays_review(self):
        batch = audit_utility_bills(
            client_id="client",
            bills=(bill(actual=3000, verified=True),),
            tariffs=(tariff(verified=False),),
        )
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)

    def test_effective_date_selects_correct_version(self):
        old = tariff(
            energy_micros=100000,
            effective_from="2026-01-01",
            effective_to="2026-06-30",
        )
        new = tariff(
            energy_micros=200000,
            effective_from="2026-07-01",
        )
        batch = audit_utility_bills(
            client_id="client",
            bills=(bill(actual=4000, bill_date="2026-07-15"),),
            tariffs=(old, new),
        )
        self.assertEqual(len(batch.observations), 1)
        self.assertEqual(batch.observations[0].expected_cents, 3500)

    def test_overlapping_versions_fail_closed(self):
        a = tariff(effective_from="2026-01-01")
        b = tariff(effective_from="2026-06-01")
        batch = audit_utility_bills(
            client_id="client",
            bills=(bill(actual=5000),),
            tariffs=(a, b),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "OVERLAPPING_TARIFF_VERSIONS")

    def test_missing_tariff_is_explicit_exception(self):
        batch = audit_utility_bills(
            client_id="client",
            bills=(bill(actual=5000),),
            tariffs=(),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "NO_TARIFF_VERSION")

    def test_no_overcharge_produces_no_observation(self):
        batch = audit_utility_bills(
            client_id="client",
            bills=(bill(actual=2500),),
            tariffs=(tariff(),),
        )
        self.assertEqual(batch.observations, ())


if __name__ == "__main__":
    unittest.main()
