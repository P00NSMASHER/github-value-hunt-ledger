from recoveryworks.test_support import source_hash as H
import unittest

from recoveryworks import Branch, FindingState, RecoveryEngine
from recoveryworks.branches.contract_billing import (
    ContractRate,
    InvoiceCharge,
    UsageRecord,
    audit_contract_billing,
)


def rate(*, verified=True, start="2026-01-01", end=None, fixed=1000, included="0", unit=2_000_000):
    return ContractRate(
        counterparty_id="Vendor",
        service_id="svc",
        effective_from=start,
        effective_to=end,
        fixed_cents=fixed,
        included_units=included,
        unit_rate_micros=unit,
        source_hash=H(f"rate-{start}-{end}"),
        source_locator=f"file://rates.csv#{start}",
        verified=verified,
    )


def charge(cid="C-1", *, actual=4000, verified=True, when="2026-08-31"):
    return InvoiceCharge(
        charge_id=cid,
        counterparty_id="Vendor",
        account_id="acct",
        service_id="svc",
        service_date=when,
        actual_cents=actual,
        source_hash=H(f"charge-{cid}"),
        source_locator=f"file://charges.csv#{cid}",
        verified=verified,
    )


def usage(cid="C-1", units="10", *, verified=True):
    return UsageRecord(
        charge_id=cid,
        units=units,
        source_hash=H(f"usage-{cid}"),
        source_locator=f"file://usage.csv#{cid}",
        verified=verified,
    )


class ContractBillingTests(unittest.TestCase):
    def test_saas_expected_vs_actual_math(self):
        batch = audit_contract_billing(
            branch=Branch.SAAS,
            client_id="client",
            charges=(charge(),),
            rates=(rate(),),
            usage=(usage(),),
        )
        self.assertEqual(batch.exceptions, ())
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.expected_cents, 3000)
        self.assertEqual(finding.potential_recovery_cents, 1000)

    def test_unverified_quantity_keeps_candidate_in_review(self):
        batch = audit_contract_billing(
            branch=Branch.SAAS,
            client_id="client",
            charges=(charge(),),
            rates=(rate(),),
            usage=(usage(verified=False),),
        )
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)

    def test_missing_usage_fails_closed(self):
        batch = audit_contract_billing(
            branch=Branch.TELECOM,
            client_id="client",
            charges=(charge(),),
            rates=(rate(),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "MISSING_USAGE")

    def test_duplicate_charge_ids_are_all_excluded(self):
        batch = audit_contract_billing(
            branch=Branch.SAAS,
            client_id="client",
            charges=(charge("DUP"), charge("DUP")),
            rates=(rate(),),
            usage=(usage("DUP"),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "DUPLICATE_CHARGE_ID")

    def test_overlapping_rates_fail_closed(self):
        batch = audit_contract_billing(
            branch=Branch.TELECOM,
            client_id="client",
            charges=(charge(),),
            rates=(
                rate(start="2026-01-01"),
                rate(start="2026-07-01"),
            ),
            usage=(usage(),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "OVERLAPPING_CONTRACT_RATES")

    def test_fixed_only_contract_does_not_require_usage(self):
        batch = audit_contract_billing(
            branch=Branch.SAAS,
            client_id="client",
            charges=(charge(actual=1500),),
            rates=(rate(fixed=1000, included="0", unit=0),),
        )
        self.assertEqual(batch.exceptions, ())
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertEqual(finding.potential_recovery_cents, 500)

    def test_included_units_only_rate_charges_overage(self):
        batch = audit_contract_billing(
            branch=Branch.TELECOM,
            client_id="client",
            charges=(charge(actual=3000),),
            rates=(rate(fixed=2000, included="100", unit=100_000),),
            usage=(usage(units="150"),),
        )
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertEqual(finding.expected_cents, 2500)
        self.assertEqual(finding.potential_recovery_cents, 500)


if __name__ == "__main__":
    unittest.main()
