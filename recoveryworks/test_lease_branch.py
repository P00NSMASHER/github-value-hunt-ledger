from recoveryworks.test_support import source_hash as H
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.contract_billing import ContractRate, InvoiceCharge, UsageRecord
from recoveryworks.branches.lease import audit_lease_billing


def rate(*, verified=True, fixed=100000, unit_rate=2500000):
    return ContractRate(
        counterparty_id="Landlord A",
        service_id="CAM-2026",
        effective_from="2026-01-01",
        effective_to=None,
        fixed_cents=fixed,
        included_units="0",
        unit_rate_micros=unit_rate,
        source_hash=H("lease-rate-hash"),
        source_locator="file://lease_rates.csv#row=2",
        verified=verified,
    )


def charge(*, verified=True, actual=140000):
    return InvoiceCharge(
        charge_id="LEASE-1",
        counterparty_id="Landlord A",
        account_id="SITE-1",
        service_id="CAM-2026",
        service_date="2026-08-31",
        actual_cents=actual,
        source_hash=H("lease-charge-hash"),
        source_locator="file://lease_charges.csv#row=2",
        verified=verified,
    )


def area(*, verified=True, units="100"):
    return UsageRecord(
        charge_id="LEASE-1",
        units=units,
        source_hash=H("area-hash"),
        source_locator="file://area.csv#row=2",
        verified=verified,
        metadata={"quantity_kind": "area_sqft"},
    )


class LeaseRecoveryTests(unittest.TestCase):
    def test_area_based_lease_charge_is_validated(self):
        batch = audit_lease_billing(
            client_id="client",
            charges=(charge(),),
            rates=(rate(),),
            area=(area(),),
        )
        self.assertEqual(batch.exceptions, ())
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.expected_cents, 125000)
        self.assertEqual(finding.potential_recovery_cents, 15000)

    def test_missing_area_fails_closed_for_area_rate(self):
        batch = audit_lease_billing(
            client_id="client",
            charges=(charge(),),
            rates=(rate(),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "MISSING_USAGE")

    def test_unverified_area_keeps_finding_in_review(self):
        batch = audit_lease_billing(
            client_id="client",
            charges=(charge(),),
            rates=(rate(),),
            area=(area(verified=False),),
        )
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)


if __name__ == "__main__":
    unittest.main()
