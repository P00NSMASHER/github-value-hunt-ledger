import tempfile
import threading
import unittest
from pathlib import Path

from experiments.exp002.authority_ledger import (
    AuthorityError,
    AuthorityLedger,
    CapacityError,
    IdentityError,
    ReceiptAuthorityPolicy,
    StaleWorkerError,
    SyntheticTarget,
)


V1 = "2026-01-01T00:00:00Z"
O1 = "2026-01-02T00:00:00Z"
O2 = "2026-01-10T00:00:00Z"
FUTURE = "9999-12-31T23:59:59Z"


class LedgerCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root / "authority.sqlite"
        self.ledger = AuthorityLedger(self.path)

    def tearDown(self):
        self.ledger.close()
        self.tmp.cleanup()

    def receipt(self, line="L1", qty=10_000, amount=100_00):
        self.ledger.record_authority("r1", line, "RECEIPT", qty, amount, valid_at=V1, observed_at=O1)

    def allocation(self, allocation="A1", line="L1", qty=10_000, amount=100_00):
        self.ledger.allocate_invoice(allocation, line, qty, amount, valid_at=V1, observed_at=O1)

    def test_01_policy_and_source_health_fail_closed(self):
        self.assertEqual(
            ReceiptAuthorityPolicy.decide(line_type="GOODS", evidence_kind="GOODS_RECEIPT", source_state="PRESENT"),
            "ALLOW",
        )
        self.assertEqual(
            ReceiptAuthorityPolicy.decide(line_type="SERVICE", evidence_kind="GOODS_RECEIPT", source_state="PRESENT"),
            "REJECT_WRONG_AUTHORITY_EXPECTED_SERVICE_ENTRY",
        )
        self.assertEqual(
            ReceiptAuthorityPolicy.decide(line_type="SERVICE", evidence_kind=None, source_state="UNAVAILABLE"),
            "REVIEW_SOURCE_UNAVAILABLE",
        )
        self.assertEqual(
            ReceiptAuthorityPolicy.decide(line_type="SERVICE", evidence_kind=None, source_state="UNAVAILABLE", direct_invoice_allowed=True),
            "ALLOW_DIRECT",
        )
        self.assertEqual(
            ReceiptAuthorityPolicy.missing_receipt_assertion(source_state="UNAVAILABLE", candidate_amount=500_00),
            (0, "REVIEW_SOURCE_UNAVAILABLE"),
        )
        self.assertEqual(
            ReceiptAuthorityPolicy.missing_receipt_assertion(source_state="VERIFIED_EMPTY", candidate_amount=500_00),
            (500_00, "ASSERTABLE_EXCEPTION"),
        )

    def test_02_identity_alias_nonmatch_merge_split_and_same_sku(self):
        reg = self.ledger.identity
        reg.record("supplier-a", "VENDOR-1", "MATCH", valid_at=V1, observed_at=O1)
        reg.record("supplier-alias", "VENDOR-1", "MATCH", valid_at=V1, observed_at=O1)
        self.assertEqual(reg.resolve("supplier-alias", valid_at=FUTURE, observed_at=O1), "VENDOR-1")
        reg.record("supplier-a", "VENDOR-1", "NON_MATCH", valid_at=V1, observed_at=O2)
        reg.record("supplier-a", "VENDOR-2", "MATCH", valid_at=V1, observed_at=O2)
        self.assertEqual(reg.resolve("supplier-a", valid_at=FUTURE, observed_at=O1), "VENDOR-1")
        self.assertEqual(reg.resolve("supplier-a", valid_at=FUTURE, observed_at=O2), "VENDOR-2")
        reg.record("ambiguous", "VENDOR-1", "MATCH", valid_at=V1, observed_at=O1)
        reg.record("ambiguous", "VENDOR-2", "MATCH", valid_at=V1, observed_at=O1)
        with self.assertRaisesRegex(IdentityError, "AMBIGUOUS"):
            reg.resolve("ambiguous", valid_at=FUTURE, observed_at=O2)
        with self.assertRaisesRegex(IdentityError, "SAME_SKU"):
            reg.assign_same_sku(["PO-LINE-1", "PO-LINE-2"])

    def test_03_partial_receipt_and_exact_line_conservation(self):
        self.receipt()
        self.ledger.allocate_invoice("A1", "L1", 4_000, 40_00, valid_at=V1, observed_at=O1)
        self.ledger.allocate_invoice("A2", "L1", 6_000, 60_00, valid_at=V1, observed_at=O1)
        with self.assertRaisesRegex(CapacityError, "FORWARD"):
            self.ledger.allocate_invoice("A3", "L1", 1, 1, valid_at=V1, observed_at=O1)
        b = self.ledger.replay("L1", valid_at=FUTURE, observed_at=FUTURE)
        self.assertEqual((b.authority_qty, b.invoiced_qty, b.available_qty), (10_000, 10_000, 0))

    def test_04_mixed_direct_service_rejection_and_precision(self):
        self.ledger.record_authority("direct", "DIRECT", "DIRECT_AUTH", 7_000, 58_33, valid_at=V1, observed_at=O1)
        self.ledger.allocate_invoice("D1", "DIRECT", 7_000, 58_33, valid_at=V1, observed_at=O1)
        self.ledger.record_authority("service", "SVC", "SERVICE_ENTRY", 1_000, 80_00, valid_at=V1, observed_at=O1)
        self.ledger.allocate_invoice("S1", "SVC", 1_000, 80_00, valid_at=V1, observed_at=O1)
        self.ledger.record_authority("rg", "REJECT", "RECEIPT", 10_000, 100_00, valid_at=V1, observed_at=O1)
        self.ledger.record_authority("xg", "REJECT", "REJECT", 2_000, 20_00, valid_at=V1, observed_at=O1)
        with self.assertRaisesRegex(CapacityError, "FORWARD"):
            self.ledger.allocate_invoice("RG", "REJECT", 9_000, 90_00, valid_at=V1, observed_at=O1)
        self.assertEqual(self.ledger.replay("DIRECT", valid_at=FUTURE, observed_at=FUTURE).available_amount, 0)

    def test_05_counter_events_returns_credit_cancel_and_rereceipt(self):
        self.receipt()
        self.allocation()
        self.ledger.record_authority("physical-only", "L1", "PHYSICAL_NONREFUNDING", 3_000, 30_00, valid_at=V1, observed_at=O1)
        self.assertEqual(self.ledger.replay("L1", valid_at=FUTURE, observed_at=FUTURE).invoiced_qty, 10_000)

        credit = self.ledger.reserve_effect("credit-1", "A1", "VENDOR_CREDIT", 2_000, 20_00, {"credit": 1}, valid_at=V1, observed_at=O1)
        self.ledger.dispatch("credit-1", expected_version=credit["version"])
        self.ledger.reconcile("credit-1", "APPLIED", observed_at=O2)
        self.assertEqual(self.ledger.replay("L1", valid_at=FUTURE, observed_at=FUTURE).invoiced_qty, 8_000)

        self.ledger.record_authority("refund-return", "L1", "REFUNDING_RETURN", 3_000, 30_00, valid_at=V1, observed_at=O2)
        returned = self.ledger.reserve_effect("return-credit", "A1", "REFUNDING_RETURN", 3_000, 30_00, {"return": 1}, valid_at=V1, observed_at=O2)
        self.ledger.dispatch("return-credit", expected_version=returned["version"])
        self.ledger.reconcile("return-credit", "APPLIED", observed_at=O2)
        mid = self.ledger.replay("L1", valid_at=FUTURE, observed_at=FUTURE)
        self.assertEqual((mid.authority_qty, mid.invoiced_qty, mid.available_qty), (7_000, 5_000, 2_000))

        cancel = self.ledger.reserve_effect("cancel-rest", "A1", "BILL_CANCEL", 5_000, 50_00, {"cancel": 1}, valid_at=V1, observed_at=O2)
        self.ledger.dispatch("cancel-rest", expected_version=cancel["version"])
        self.ledger.reconcile("cancel-rest", "APPLIED", observed_at=O2)
        self.ledger.record_authority("rereceipt", "L1", "RERECEIPT", 3_000, 30_00, valid_at=V1, observed_at=O2)
        final = self.ledger.replay("L1", valid_at=FUTURE, observed_at=FUTURE)
        self.assertEqual((final.authority_qty, final.invoiced_qty, final.available_qty), (10_000, 0, 10_000))

    def test_06_reverse_residual_is_atomically_reserved(self):
        self.receipt()
        self.allocation()
        barrier = threading.Barrier(2)
        outcomes = []

        def contender(key):
            ledger = AuthorityLedger(self.path)
            barrier.wait()
            try:
                ledger.reserve_effect(key, "A1", "VENDOR_CREDIT", 6_000, 60_00, {"key": key}, valid_at=V1, observed_at=O1)
                outcomes.append("WIN")
            except CapacityError:
                outcomes.append("BLOCKED")
            finally:
                ledger.close()

        threads = [threading.Thread(target=contender, args=(f"op-{i}",)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertCountEqual(outcomes, ["WIN", "BLOCKED"])

    def test_07_crash_after_target_commit_recovers_one_effect(self):
        self.receipt()
        self.allocation()
        target = SyntheticTarget(self.root / "target.sqlite")
        effect = self.ledger.reserve_effect("credit-crash", "A1", "VENDOR_CREDIT", 10_000, 100_00, {"credit": "all"}, valid_at=V1, observed_at=O1)
        dispatch_version, downstream_key, payload_hash = self.ledger.dispatch("credit-crash", expected_version=0)
        target.apply(downstream_key, payload_hash)
        self.ledger.close()  # crash before local receipt
        self.ledger = AuthorityLedger(self.path)
        self.ledger.recover_abandoned_dispatch("credit-crash")
        self.ledger.reconcile("credit-crash", target.probe(downstream_key), observed_at=O2)
        self.assertEqual(target.applied_count(), 1)
        self.assertEqual(self.ledger.event_count("REVERSAL_APPLIED", "credit-crash"), 1)
        self.assertEqual(self.ledger.reconcile("credit-crash", "APPLIED", observed_at=O2), "APPLIED")
        self.assertEqual(self.ledger.event_count("REVERSAL_APPLIED", "credit-crash"), 1)
        with self.assertRaises(CapacityError):
            self.ledger.reserve_effect("fresh-id", "A1", "VENDOR_CREDIT", 1, 1, {"duplicate": True}, valid_at=V1, observed_at=O2)
        with self.assertRaises(StaleWorkerError):
            self.ledger.record_worker_result("credit-crash", expected_version=dispatch_version)

    def test_08_unknown_and_replay_expiry_hold_capacity(self):
        self.receipt()
        self.allocation()
        effect = self.ledger.reserve_effect("unknown", "A1", "VENDOR_CREDIT", 10_000, 100_00, {"credit": "all"}, valid_at=V1, observed_at=O1, replay_expires_at=O2)
        _, downstream_key, _ = self.ledger.dispatch("unknown", expected_version=0)
        self.ledger.recover_abandoned_dispatch("unknown")
        self.assertEqual(self.ledger.reconcile("unknown", "UNKNOWN", observed_at=O1), "MANUAL_REVIEW")
        self.assertTrue(self.ledger.can_redispatch("unknown", now=O1))
        self.assertFalse(self.ledger.can_redispatch("unknown", now=FUTURE))
        with self.assertRaises(CapacityError):
            self.ledger.reserve_effect("new-after-timeout", "A1", "VENDOR_CREDIT", 1, 1, {"new": True}, valid_at=V1, observed_at=O2)
        self.assertEqual(downstream_key, effect["downstream_key"])

    def test_09_only_positive_not_applied_receipt_releases(self):
        self.receipt()
        self.allocation()
        target = SyntheticTarget(self.root / "target.sqlite")
        effect = self.ledger.reserve_effect("definite-no", "A1", "VENDOR_CREDIT", 10_000, 100_00, {"credit": "all"}, valid_at=V1, observed_at=O1)
        self.ledger.dispatch("definite-no", expected_version=0)
        self.ledger.recover_abandoned_dispatch("definite-no")
        self.assertEqual(target.probe(effect["downstream_key"]), "UNKNOWN")
        self.ledger.reconcile("definite-no", "UNKNOWN", observed_at=O1)
        target.record_authoritative_negative(effect["downstream_key"], "provider pre-apply rejection receipt")
        self.ledger.reconcile("definite-no", target.probe(effect["downstream_key"]), observed_at=O2)
        replacement = self.ledger.reserve_effect("replacement", "A1", "VENDOR_CREDIT", 10_000, 100_00, {"replacement": True}, valid_at=V1, observed_at=O2)
        self.assertEqual(replacement["state"], "RESERVED")

    def test_10_payload_binding_rejects_changed_replay(self):
        self.receipt()
        self.allocation()
        self.ledger.reserve_effect("same", "A1", "VENDOR_CREDIT", 1_000, 10_00, {"amount": 10}, valid_at=V1, observed_at=O1)
        with self.assertRaisesRegex(AuthorityError, "PAYLOAD_CONFLICT"):
            self.ledger.reserve_effect("same", "A1", "VENDOR_CREDIT", 1_000, 10_00, {"amount": 11}, valid_at=V1, observed_at=O1)

    def test_11_bitemporal_replay_preserves_then_and_later_valid_truth(self):
        self.receipt()
        self.ledger.record_authority("late-reject", "L1", "REJECT", 2_000, 20_00, valid_at=V1, observed_at=O2)
        then = self.ledger.replay("L1", valid_at=FUTURE, observed_at=O1)
        later = self.ledger.replay("L1", valid_at=FUTURE, observed_at=O2)
        self.assertEqual(then.authority_qty, 10_000)
        self.assertEqual(later.authority_qty, 8_000)

    def test_12_synchronous_receipt_applies_exactly_one_reversal(self):
        self.receipt()
        self.allocation()
        self.ledger.reserve_effect("sync", "A1", "VENDOR_CREDIT", 1_000, 10_00, {"credit": 10}, valid_at=V1, observed_at=O1)
        dispatch_version, _, _ = self.ledger.dispatch("sync", expected_version=0)
        self.ledger.record_worker_result("sync", expected_version=dispatch_version)
        self.assertEqual(self.ledger.effect_state("sync"), "APPLIED")
        self.assertEqual(self.ledger.event_count("REVERSAL_APPLIED", "sync"), 1)
        with self.assertRaises(StaleWorkerError):
            self.ledger.record_worker_result("sync", expected_version=dispatch_version)


if __name__ == "__main__":
    unittest.main(verbosity=2)
