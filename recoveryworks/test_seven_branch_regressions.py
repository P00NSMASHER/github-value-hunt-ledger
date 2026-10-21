"""Adversarial regressions; all fixtures are synthetic, never launch evidence."""
from dataclasses import replace
from types import SimpleNamespace
import unittest

from recoveryworks import RecoveryEngine
from recoveryworks.branches.ap import audit_ap_recovery
from recoveryworks.branches.procurement import audit_procurement_lines
from recoveryworks.branches.utility import audit_utility_bills
from recoveryworks.branches.rebate import audit_rebates
from recoveryworks.financial_events import net_settlements
from recoveryworks.ledger import RecoveryLedger, EconomicLossConflict
from recoveryworks.test_ap_branch import payment, obligation
from recoveryworks.test_procurement_branch import line, authority, quantity
from recoveryworks.test_utility_branch import bill, tariff
from recoveryworks.test_rebate_branch import program, purchase, settlement


class SevenBranchRegressions(unittest.TestCase):
    def test_suffix_is_a_distinct_invoice_not_a_duplicate(self):
        result = audit_ap_recovery(client_id='client', payments=(
            payment('p1', 'v', '100', 10000), payment('p2', 'v', '100R', 10000)),
            obligations=(obligation('v', '100', 10000), obligation('v', '100R', 10000)))
        self.assertEqual(result.observations, ())

    def test_ap_refund_removes_apparent_overpayment(self):
        result = audit_ap_recovery(client_id='client', payments=(
            payment('p1', 'v', '100', 20000),
            replace(payment('r1', 'v', '100', 10000), amount_cents=-10000, reverses_id='p1')),
            obligations=(obligation('v', '100', 10000),))
        self.assertEqual(result.observations, ())
        self.assertEqual(result.exceptions, ())

    def test_fractional_unit_price_rounds_after_extension(self):
        result = audit_procurement_lines(client_id='client-1',
            invoice_lines=(replace(line(actual=50000), invoiced_quantity='100000'),),
            authorities=(replace(authority(price=0), contracted_unit_price='0.0049'),),
            quantity_approvals=(quantity(qty='100000'),))
        self.assertEqual(result.observations[0].expected_cents, 49000)

    def test_conflicting_utility_bill_cannot_validate(self):
        result = audit_utility_bills(client_id='client', bills=(bill(), bill(actual=4000)), tariffs=(tariff(),))
        self.assertEqual(result.observations, ())
        self.assertEqual(result.exceptions[0].code, 'DUPLICATE_UTILITY_BILL')

    def test_changed_proof_does_not_create_second_economic_loss(self):
        result = audit_utility_bills(client_id='client', bills=(bill(),), tariffs=(tariff(),))
        finding = RecoveryEngine().evaluate(result.observations[0])
        ledger = RecoveryLedger()
        ledger.add(finding)
        with self.assertRaises(EconomicLossConflict):
            ledger.add(replace(finding, finding_id=finding.finding_id + '-changed'))

    def test_rebate_not_due_is_excluded(self):
        result = audit_rebates(client_id='client',
            programs=(replace(program(), payment_due_date='2026-11-01'),),
            purchases=(purchase(),), settlements=(settlement(),), as_of_date='2026-10-18')
        self.assertEqual(result.observations, ())
        self.assertEqual(result.exceptions[0].code, 'REBATE_NOT_YET_DUE_OR_ASOF_MISSING')

    def test_return_requires_explicit_program_policy(self):
        returned = replace(purchase('R', qty='50', spend=50000), quantity='-50',
                           net_spend_cents=-50000, return_of_purchase_id='P-1')
        result = audit_rebates(client_id='client', programs=(program(),),
                              purchases=(purchase(), returned), settlements=(settlement(),))
        self.assertEqual(result.observations, ())
        self.assertEqual(result.exceptions[0].code, 'INVALID_RETURN_LINEAGE')

    def test_reviewed_return_reduces_rebate_entitlement(self):
        returned = replace(purchase('R', qty='50', spend=50000), quantity='-50',
                           net_spend_cents=-50000, return_of_purchase_id='P-1')
        result = audit_rebates(client_id='client',
            programs=(replace(program(), return_policy='restates_original_purchase'),),
            purchases=(purchase(), returned), settlements=(settlement(0),))
        self.assertEqual(result.exceptions, ())
        self.assertEqual(result.observations[0].expected_cents, 5000)

    def test_nonfinite_quantities_are_rejected(self):
        for value in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                replace(purchase(), quantity=value)

    def test_reversal_lineage_is_bounded_and_scoped(self):
        def event(identity, amount, original=None, when='2026-10-01'):
            return SimpleNamespace(settlement_id=identity, amount=amount,
                                   reverses_id=original, settlement_date=when)
        original = event('s', 100)
        self.assertEqual(net_settlements((original, event('r', -40, 's')), amount_field='amount'), 60)
        for invalid in (event('r', -101, 's'), event('r', -10, 'missing'),
                        event('r', -10, 's', '2026-09-01'), event('r', 10, 's')):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                net_settlements((original, invalid), amount_field='amount')
        with self.assertRaises(ValueError):
            net_settlements((original, event('r1', -60, 's'), event('r2', -60, 's')), amount_field='amount')

    def test_reconciliation_hold_survives_replay_and_blocks_claim(self):
        from recoveryworks.durable_ledger import DurableRecoveryLedger
        from recoveryworks.test_durable_ledger import verified_finding
        ledger = DurableRecoveryLedger()
        finding = verified_finding()
        ledger.add(finding)
        ledger.approve(finding.finding_id, 'reviewer', 'verified')
        ledger.authorize(finding.finding_id, 'authorization')
        ledger.hold_for_reconciliation(finding.finding_id, 'changed evidence')
        restored = DurableRecoveryLedger.from_bundle(ledger.export_bundle())
        self.assertEqual(restored.reconciliation_holds(), {finding.finding_id: 'changed evidence'})
        with self.assertRaisesRegex(ValueError, 'held for evidence reconciliation'):
            restored.mark_claimed(finding.finding_id)
