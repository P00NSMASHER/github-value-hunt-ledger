import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.contract_billing import ContractRate, InvoiceCharge, UsageRecord
from recoveryworks.branches.procurement import audit_procurement_billing


def rate(*, verified=True, fixed=0, unit=10_000_000):
    return ContractRate(
        counterparty_id="Supplier A",
        service_id="SKU-1",
        effective_from="2026-01-01",
        effective_to=None,
        fixed_cents=fixed,
        included_units="0",
        unit_rate_micros=unit,
        source_hash="rate-hash",
        source_locator="file://rates.csv#row=2",
        verified=verified,
    )


def charge(*, actual=120000, verified=True):
    return InvoiceCharge(
        charge_id="PO-LINE-1",
        counterparty_id="Supplier A",
        account_id="PO-100",
        service_id="SKU-1",
        service_date="2026-08-31",
        actual_cents=actual,
        source_hash="charge-hash",
        source_locator="file://charges.csv#row=2",
        verified=verified,
    )


def quantity(*, units="100", verified=True):
    return UsageRecord(
        charge_id="PO-LINE-1",
        units=units,
        source_hash="quantity-hash",
        source_locator="file://receipts.csv#row=2",
        verified=verified,
        metadata={"quantity_kind": "procurement_received_quantity"},
    )


class ProcurementRecoveryTests(unittest.TestCase):
    def test_contract_unit_price_overcharge_is_validated(self):
        batch = audit_procurement_billing(
            client_id="client",
            charges=(charge(),),
            rates=(rate(),),
            quantities=(quantity(),),
        )
        self.assertEqual(batch.exceptions, ())
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.expected_cents, 100000)
        self.assertEqual(finding.potential_recovery_cents, 20000)

    def test_missing_quantity_fails_closed(self):
        batch = audit_procurement_billing(
            client_id="client",
            charges=(charge(),),
            rates=(rate(),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "MISSING_USAGE")

    def test_unverified_receipt_quantity_keeps_candidate_in_review(self):
        batch = audit_procurement_billing(
            client_id="client",
            charges=(charge(),),
            rates=(rate(),),
            quantities=(quantity(verified=False),),
        )
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)

    def test_fixed_contract_fee_does_not_require_quantity(self):
        batch = audit_procurement_billing(
            client_id="client",
            charges=(charge(actual=12000),),
            rates=(rate(fixed=10000, unit=0),),
        )
        self.assertEqual(batch.exceptions, ())
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertEqual(finding.potential_recovery_cents, 2000)


if __name__ == "__main__":
    unittest.main()
