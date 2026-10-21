from dataclasses import replace
import unittest
from recoveryworks.durable_ledger import DurableRecoveryLedger
from recoveryworks.financial_events import CashEvent
from recoveryworks.test_durable_ledger import verified_finding, settlement
from recoveryworks.test_support import source_hash as H


class CashLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.ledger = DurableRecoveryLedger()
        self.finding = verified_finding()
        self.ledger.add(self.finding)
        self.ledger.approve(self.finding.finding_id, 'reviewer', 'verified')
        self.ledger.authorize(self.finding.finding_id, 'authorization')
        self.ledger.mark_claimed(self.finding.finding_id)

    def event(self, identity, amount, fee=0, reverses=None):
        return CashEvent(identity, self.finding.finding_id, amount, fee, 'USD',
                         H(identity), 'bank://'+identity, self.ledger.get(self.finding.finding_id).updated_at,
                         True, reverses)

    def test_partial_receipts_and_reversal_preserve_net_economics_and_replay(self):
        first = self.event('receipt-1', 2000, 600)
        self.ledger.post_cash_event(first)
        head = self.ledger.journal.head_hash
        self.ledger.post_cash_event(first)
        self.assertEqual(head, self.ledger.journal.head_hash)
        self.ledger.post_cash_event(self.event('receipt-2', 3000, 900))
        self.ledger.post_cash_event(self.event('reversal', -1000, -300, 'receipt-1'))
        restored = DurableRecoveryLedger.from_bundle(self.ledger.export_bundle())
        record = restored.get(self.finding.finding_id)
        self.assertEqual((record.recovered_cents, record.fee_cents), (4000, 1200))
        self.assertEqual(restored.journal.head_hash, self.ledger.journal.head_hash)

    def test_reversal_cannot_exceed_original_even_when_case_has_more_cash(self):
        self.ledger.post_cash_event(self.event('receipt-1', 1000))
        self.ledger.post_cash_event(self.event('receipt-2', 3000))
        with self.assertRaisesRegex(ValueError, 'exceeds original'):
            self.ledger.post_cash_event(self.event('reversal', -2000, 0, 'receipt-1'))

    def test_legacy_receipt_can_be_reversed(self):
        self.ledger.mark_recovered(self.finding.finding_id, settlement(self.ledger, self.finding.finding_id, 1000), 300)
        self.ledger.post_cash_event(self.event('reversal', -1000, -300, 'settlement-1'))
        self.assertEqual(DurableRecoveryLedger.from_bundle(self.ledger.export_bundle()).get(self.finding.finding_id).recovered_cents, 0)

    def test_reuse_currency_missing_original_and_unverified_fail(self):
        event = self.event('receipt', 2000)
        self.ledger.post_cash_event(event)
        for bad in (replace(event, amount_cents=1000), self.event('rev', -1, reverses='missing'),
                    replace(self.event('new', 10), currency='EUR'), replace(self.event('new', 10), verified=False)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.ledger.post_cash_event(bad)

    def test_hold_resolution_requires_independent_current_review(self):
        self.ledger.hold_for_reconciliation(self.finding.finding_id, 'new source conflicts')
        kwargs = dict(reviewer_id='a', independent_reviewer_id='b', evidence_hash=H('resolution'),
                      expected_record_hash=self.ledger.get(self.finding.finding_id).record_hash,
                      expected_hold_hash=self.ledger.reconciliation_hold_hash(self.finding.finding_id), note='retained original after reconciliation')
        with self.assertRaises(ValueError):
            self.ledger.resolve_reconciliation(self.finding.finding_id, **{**kwargs, 'independent_reviewer_id': 'a'})
        with self.assertRaises(ValueError):
            self.ledger.resolve_reconciliation(self.finding.finding_id, **{**kwargs, 'expected_record_hash': H('stale')})
        self.ledger.resolve_reconciliation(self.finding.finding_id, **kwargs)
        restored = DurableRecoveryLedger.from_bundle(self.ledger.export_bundle())
        self.assertEqual(restored.reconciliation_holds(), {})
        restored.post_cash_event(self.event('receipt', 1000))

    def test_revision_preserves_history_and_does_not_double_count(self):
        ledger = DurableRecoveryLedger()
        original = verified_finding()
        ledger.add(original)
        ledger.approve(original.finding_id, 'r', 'original review')
        ledger.authorize(original.finding_id, 'old authorization')
        ledger.hold_for_reconciliation(original.finding_id, 'corrected amount')
        revised = replace(original, finding_id='replacement', actual_cents=14000)
        ledger.revise_held_case(original.finding_id, revised, reviewer_id='r',
            independent_reviewer_id='i', evidence_hash=H('review'),
            expected_record_hash=ledger.get(original.finding_id).record_hash,
            expected_hold_hash=ledger.reconciliation_hold_hash(original.finding_id), note='corrected invoice')
        restored = DurableRecoveryLedger.from_bundle(ledger.export_bundle())
        self.assertEqual(len(restored.records()), 2)
        self.assertEqual(len(restored.active_records()), 1)
        self.assertEqual(restored.rollup()['totals']['potential_cents'], 4000)
        self.assertIsNone(restored.get('replacement').authorization_id)
        with self.assertRaises(ValueError):
            restored.mark_claimed('replacement')
