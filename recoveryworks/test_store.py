from recoveryworks.test_support import source_hash as H
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import time
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
from recoveryworks.private_io import private_permissions_verified


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
            source_hash=H("rulehash"),
            effective_from="2026-01-01",
            effective_to=None,
            verified_controlling=True,
            source_locator="source://vendor-statement#1",
        ),
        evidence=(EvidenceRef(
            evidence_id="ev-1",
            source_hash=H("evhash"),
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
            self.assertTrue(private_permissions_verified(path))
            self.assertTrue(private_permissions_verified(store.lock_path))

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

    def test_compare_and_swap_serializes_concurrent_writers(self):
        class SlowHeadStore(LocalBundleStore):
            def current_head_hash(self):
                head = super().current_head_hash()
                time.sleep(0.1)
                return head

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "recoveryworks.json"
            initial_store = LocalBundleStore(path)
            initial = DurableRecoveryLedger()
            f = finding()
            initial.add(f)
            initial_head = initial_store.save(initial)

            first = initial_store.load()
            second = initial_store.load()
            first.approve(f.finding_id, "reviewer-1", "verified one")
            second.approve(f.finding_id, "reviewer-2", "verified two")
            barrier = threading.Barrier(2)

            def save(ledger):
                barrier.wait(timeout=2)
                try:
                    return SlowHeadStore(path).save(
                        ledger,
                        expected_head_hash=initial_head,
                    )
                except StoreConflictError:
                    return "CONFLICT"

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(save, (first, second)))

            self.assertEqual(results.count("CONFLICT"), 1)
            self.assertEqual(len([value for value in results if value != "CONFLICT"]), 1)

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
