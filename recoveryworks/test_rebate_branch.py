import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.rebate import (
    RebateActivity,
    RebateAgreement,
    RebateBasis,
    RebateCredit,
    audit_rebates,
    expected_rebate_cents,
)


def agreement(*, basis=RebateBasis.SPEND_BPS, verified=True, start="2026-01-01", end=None):
    return RebateAgreement(
        agreement_id="AGR-1",
        vendor_id="Vendor A",
        basis=basis,
        effective_from=start,
        effective_to=end,
        threshold_spend_cents=5000000,
        threshold_units="1000",
        rate_bps=200 if basis is RebateBasis.SPEND_BPS else 0,
        rate_cents_per_unit=25 if basis is RebateBasis.UNIT_CENTS else 0,
        fixed_bonus_cents=50000,
        source_hash=f"agreement-{start}-{end}",
        source_locator=f"file://agreements.csv#{start}",
        verified=verified,
    )


def activity(*, spend=10000000, units="2000", verified=True):
    return RebateActivity(
        agreement_id="AGR-1",
        period_id="2026-Q3",
        period_end="2026-09-30",
        eligible_spend_cents=spend,
        eligible_units=units,
        source_hash="activity-hash",
        source_locator="file://activity.csv#row=2",
        verified=verified,
    )


def credit(cid="CR-1", amount=150000, *, verified=True):
    return RebateCredit(
        credit_id=cid,
        agreement_id="AGR-1",
        period_id="2026-Q3",
        amount_cents=amount,
        source_hash=f"credit-{cid}",
        source_locator=f"file://credits.csv#{cid}",
        verified=verified,
    )


class RebateRecoveryTests(unittest.TestCase):
    def test_spend_rebate_underpayment_is_validated(self):
        batch = audit_rebates(
            client_id="client",
            agreements=(agreement(),),
            activities=(activity(),),
            credits=(credit(),),
        )
        self.assertEqual(batch.exceptions, ())
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.expected_cents, 250000)
        self.assertEqual(finding.actual_cents, 150000)
        self.assertEqual(finding.potential_recovery_cents, 100000)

    def test_zero_credit_row_supports_unpaid_rebate_without_inferring_absence(self):
        batch = audit_rebates(
            client_id="client",
            agreements=(agreement(),),
            activities=(activity(),),
            credits=(credit(amount=0),),
        )
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.potential_recovery_cents, 250000)

    def test_missing_credit_row_is_exception_not_recovery(self):
        batch = audit_rebates(
            client_id="client",
            agreements=(agreement(),),
            activities=(activity(),),
            credits=(),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "MISSING_CREDIT_LEDGER_ROW")

    def test_unit_rebate_math(self):
        agr = agreement(basis=RebateBasis.UNIT_CENTS)
        act = activity(units="2000")
        self.assertEqual(expected_rebate_cents(agr, act), 100000)

    def test_threshold_not_met_produces_no_recovery(self):
        batch = audit_rebates(
            client_id="client",
            agreements=(agreement(),),
            activities=(activity(spend=4000000),),
            credits=(credit(amount=0),),
        )
        self.assertEqual(batch.observations, ())

    def test_overlapping_agreements_fail_closed(self):
        batch = audit_rebates(
            client_id="client",
            agreements=(
                agreement(start="2026-01-01"),
                agreement(start="2026-07-01"),
            ),
            activities=(activity(),),
            credits=(credit(),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "OVERLAPPING_REBATE_AGREEMENTS")

    def test_unverified_credit_keeps_candidate_in_review(self):
        batch = audit_rebates(
            client_id="client",
            agreements=(agreement(),),
            activities=(activity(),),
            credits=(credit(verified=False),),
        )
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)


if __name__ == "__main__":
    unittest.main()
