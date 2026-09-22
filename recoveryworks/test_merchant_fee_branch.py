import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.merchant_fee import (
    MerchantFeeAgreement,
    MerchantFeeStatement,
    MerchantTransactionSummary,
    audit_merchant_fees,
)


def agreement(*, fixed=1000, markup=20, per_tx=10, verified=True):
    return MerchantFeeAgreement(
        processor_id="Processor A",
        fee_plan_id="PLAN-1",
        effective_from="2026-01-01",
        effective_to=None,
        fixed_fee_cents=fixed,
        markup_bps=markup,
        per_transaction_cents=per_tx,
        source_hash="agreement-hash",
        source_locator="file://agreement.csv#row=2",
        verified=verified,
    )


def statement(*, actual=25000, verified=True, sid="S-1"):
    return MerchantFeeStatement(
        statement_id=sid,
        processor_id="Processor A",
        account_id="merchant-1",
        fee_plan_id="PLAN-1",
        statement_date="2026-08-31",
        actual_processor_fee_cents=actual,
        source_hash=f"statement-{sid}",
        source_locator=f"file://statement.csv#{sid}",
        verified=verified,
        scope_reviewer_id="fee-reviewer-1" if verified else None,
    )


def tx(*, verified=True, sid="S-1", gross=10_000_000, count=100):
    return MerchantTransactionSummary(
        statement_id=sid,
        gross_sales_cents=gross,
        transaction_count=count,
        source_hash=f"transactions-{sid}",
        source_locator=f"file://transactions.csv#{sid}",
        verified=verified,
    )


class MerchantFeeRecoveryTests(unittest.TestCase):
    def test_processor_controlled_fee_math_is_validated(self):
        batch = audit_merchant_fees(
            client_id="client",
            statements=(statement(),),
            agreements=(agreement(),),
            transaction_summaries=(tx(),),
        )
        self.assertEqual(batch.exceptions, ())
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.expected_cents, 22000)
        self.assertEqual(finding.actual_cents, 25000)
        self.assertEqual(finding.potential_recovery_cents, 3000)
        self.assertEqual(finding.metadata["fee_scope"], "processor_controlled_only")

    def test_verified_statement_requires_scope_reviewer(self):
        with self.assertRaises(ValueError):
            MerchantFeeStatement(
                statement_id="S",
                processor_id="P",
                account_id="A",
                fee_plan_id="F",
                statement_date="2026-08-31",
                actual_processor_fee_cents=100,
                source_hash="h",
                source_locator="file://x",
                verified=True,
                scope_reviewer_id=None,
            )

    def test_missing_transaction_summary_fails_closed_for_variable_fees(self):
        batch = audit_merchant_fees(
            client_id="client",
            statements=(statement(),),
            agreements=(agreement(),),
            transaction_summaries=(),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "MISSING_TRANSACTION_SUMMARY")

    def test_fixed_only_fee_can_be_audited_without_transaction_summary(self):
        batch = audit_merchant_fees(
            client_id="client",
            statements=(statement(actual=1500),),
            agreements=(agreement(fixed=1000, markup=0, per_tx=0),),
            transaction_summaries=(),
        )
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertEqual(finding.potential_recovery_cents, 500)

    def test_duplicate_statement_ids_are_all_excluded(self):
        batch = audit_merchant_fees(
            client_id="client",
            statements=(statement(sid="D"), statement(sid="D")),
            agreements=(agreement(),),
            transaction_summaries=(tx(sid="D"),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "DUPLICATE_STATEMENT_ID")

    def test_unverified_transaction_summary_keeps_candidate_review(self):
        batch = audit_merchant_fees(
            client_id="client",
            statements=(statement(),),
            agreements=(agreement(),),
            transaction_summaries=(tx(verified=False),),
        )
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)


if __name__ == "__main__":
    unittest.main()
