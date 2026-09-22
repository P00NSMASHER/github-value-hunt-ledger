import json
import os
from pathlib import Path
import tempfile
import unittest

from recoveryworks import (
    Branch,
    DurableRecoveryLedger,
    EvidenceRef,
    RecoveryEngine,
    RecoveryObservation,
    RuleRef,
)
from recoveryworks.store import BundleIntegrityError, LocalBundleStore, StoreConflictError


def finding():
    return RecoveryEngine().evaluate(RecoveryObservation(
        branch=Branch.AP,
        client_id="client-1",
        counterparty_id="vendor-1",
        reference="inv-1",
        currency="USD",
        expected_cents=10000,
        actual_cents=12000,
        rule=RuleRef(
            rule_id="rule-1",
            source_hash="rulehash",
            effective_from="2026-01-01",
            effective_to=None,
            verified_controlling=True,
            source_locator="source://vendor-statement#1",
        ),
        evidence=(EvidenceRef(
            evidence_id="ev-1",
            source_hash="evhash",
            locator="source://payment#1",
            kind="payment",
            verified=True,
        ),),
        reason="DUPLICATE_PAYMENT",
        confidence_basis="verified ledger + payment evidence",
    ))


class StoreTests(unittest.TestCase):
    def test_atomic_store_round_trip_and_private_mode(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "recoveryworks.json"
            store = LocalBundleStore(path)
            ledger = DurableRecoveryLedger()
            f = finding()
            ledger.add(f)
            head = store.save(ledger)

            self.assertEqual(head, ledger.journal.head_hash)
            restored = store.load()
            self.assertEqual(restored.rollup(), ledger.rollup())
            self.assertEqual(store.current_head_hash(), head)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

    def test_compare_and_swap_rejects_stale_writer(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "recoveryworks.json"
            store = LocalBundleStore(path)
            first = DurableRecoveryLedger()
            f = finding()
            first.add(f)
            head1 = store.save(first)

            second = store.load()
            second.approve(f.finding_id, "reviewer", "verified")
            head2 = store.save(second, expected_head_hash=head1)
            self.assertNotEqual(head1, head2)

            stale = DurableRecoveryLedger.from_bundle(first.export_bundle())
            stale.approve(f.finding_id, "other-reviewer", "also verified")
            with self.assertRaises(StoreConflictError):
                store.save(stale, expected_head_hash=head1)

    def test_compare_and_swap_can_require_store_to_remain_empty(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "recoveryworks.json"
            store = LocalBundleStore(path)
            first = DurableRecoveryLedger()
            first.add(finding())
            store.save(first)

            second = DurableRecoveryLedger()
            second.add(finding())
            with self.assertRaises(StoreConflictError):
                store.save(second, expected_head_hash=None, enforce_expected=True)

    def test_bundle_hash_tampering_is_rejected_before_replay(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "recoveryworks.json"
            store = LocalBundleStore(path)
            ledger = DurableRecoveryLedger()
            ledger.add(finding())
            store.save(ledger)

            envelope = json.loads(path.read_text())
            envelope["bundle"]["rollup"]["totals"]["potential_cents"] = 1
            path.write_text(json.dumps(envelope))

            with self.assertRaises(BundleIntegrityError):
                store.load()


if __name__ == "__main__":
    unittest.main()
