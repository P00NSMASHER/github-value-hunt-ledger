"""Issue #609: five deterministic Priority-0 financial-integrity regressions.

All amounts, parties, events and authorities are explicitly synthetic.
These tests cannot authorize an actual financial transaction or a release.
"""
from dataclasses import asdict, replace
from hashlib import sha256
from math import inf, nan
import unittest

from freight.payment_orchestration import (
    PaymentOrchestrator, authorize_payment, prepare_payment_instruction,
    verify_payment_snapshot,
)
from freight.scoped_reconciliation import ScopedTxn, reconcile_scoped
from recoveryworks.reconciliation_kernel import ReconTxn


def sha(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def fictional_instruction():
    return prepare_payment_instruction(
        instruction_id="SYN-I-001",
        buyer_id="SYN-BUYER",
        business_unit="SYN-UNIT",
        payer_id="SYN-CARRIER",
        payee_id="SYN-CUSTOMER",
        currency="USD",
        amount_cents=101,
        purpose="SYNTHETIC_ONLY",
        finding_proof_hashes=(sha("frozen-synthetic-proof"),),
        idempotency_key="SYN-KEY",
    )


def fictional_authorization(instruction):
    return authorize_payment(
        instruction,
        authorized_by="SYNTHETIC_ACTOR_NOT_REAL_APPROVAL",
        reason="fictional test only",
        authorized_at="2026-10-22T12:00:00Z",
    )


def accepted_payment_flow(inst=None, auth=None, times=None):
    inst = inst if inst is not None else fictional_instruction()
    auth = auth if auth is not None else fictional_authorization(inst)
    times = times or [
        "2026-10-22T12:00:00Z",
        "2026-10-22T12:00:01Z",
        "2026-10-22T12:00:02Z",
    ]
    engine = PaymentOrchestrator(inst)
    engine.authorize(auth)
    for n, (state, when) in enumerate(zip(("SUBMITTED", "ACCEPTED", "SETTLED"), times)):
        engine.record_provider_event(
            state=state,
            provider="SYNTHETIC_PROVIDER",
            provider_reference="SYN-REF",
            amount_cents=inst.amount_cents,
            source_hash=sha("fake-provider-" + str(n)),
            occurred_at=when,
        )
    snapshot = engine.snapshot()
    verify_payment_snapshot(inst, auth, engine.events, snapshot)
    return engine, snapshot


def scoped_invoice(amount="1.00", reference="SYN-REFERENCE",
                   date="2026-09-01", currency="USD",
                   metadata=None, txn_id="SYN-I", counterparty="SYN-CARRIER"):
    return ScopedTxn(
        ReconTxn(txn_id, amount, date, currency, reference,
                 metadata=metadata or {}),
        buyer_id="SYN-BUYER", business_unit="SYN-UNIT",
        counterparty_id=counterparty, origin="ORIGINAL_INVOICE",
    )


def declared_payment(amount="1.00", reference="SYN-REFERENCE",
                     txn_id="SYN-P"):
    return ScopedTxn(
        ReconTxn(txn_id, amount, "2026-09-02", "USD", reference),
        buyer_id="SYN-BUYER", business_unit="SYN-UNIT",
        counterparty_id="SYN-CARRIER", origin="CUSTOMER_DECLARATION",
    )


class PriorityZeroPaymentTests(unittest.TestCase):
    def test_01_complete_positive_flow_and_exact_timestamp_boundary(self):
        _, result = accepted_payment_flow()
        self.assertEqual(result.current_state, "SETTLED")
        self.assertEqual(result.settled_cents, 101)
        self.assertEqual(len(result.event_hashes), 3)

    def test_02_rejects_provider_events_before_authorization_in_utc(self):
        instruction = fictional_instruction()
        authorization = fictional_authorization(instruction)
        engine = PaymentOrchestrator(instruction)
        engine.authorize(authorization)
        with self.assertRaises(ValueError):
            engine.record_provider_event(
                state="SUBMITTED", provider="SYN", provider_reference="R",
                amount_cents=101, source_hash=sha("provider"),
                occurred_at="2026-10-22T11:59:59Z",
            )
        self.assertEqual(engine.current_state, "AUTHORIZED")
        self.assertEqual(engine.events, [])

    def test_03_rejects_provider_events_before_authorization_in_offset(self):
        instruction = fictional_instruction()
        auth = fictional_authorization(instruction)
        engine = PaymentOrchestrator(instruction)
        engine.authorize(auth)
        with self.assertRaises(ValueError):
            engine.record_provider_event(
                state="SUBMITTED", provider="SYN", provider_reference="R",
                amount_cents=101, source_hash=sha("provider"),
                occurred_at="2026-10-22T07:59:59-04:00",
            )

    def test_04_accepts_equivalent_timezone_timestamp(self):
        _, result = accepted_payment_flow(times=[
            "2026-10-22T08:00:00-04:00",
            "2026-10-22T12:00:01+00:00",
            "2026-10-22T12:00:02Z",
        ])
        self.assertEqual(result.settled_cents, 101)

    def test_05_rejects_mutated_instruction_fields_even_if_old_hash_is_unchanged(self):
        fields = {
            "instruction_id": "SYN-I-OTHER",
            "buyer_id": "SYN-OTHER",
            "business_unit": "SYN-OTHER",
            "payer_id": "SYN-AFFILIATE",
            "payee_id": "SYN-AFFILIATE",
            "currency": "EUR",
            "amount_cents": 102,
            "purpose": "UNAUTHORIZED_CHANGE",
            "finding_proof_hashes": (sha("different"),),
            "idempotency_key": "SYN-OTHER",
            "instruction_hash": "0" * 64,
        }
        for field, value in fields.items():
            with self.subTest(field=field):
                instruction = replace(fictional_instruction(), **{field: value})
                with self.assertRaises(ValueError):
                    PaymentOrchestrator(instruction)

    def test_06_rejects_modified_authorization_with_original_seal(self):
        original = fictional_instruction()
        good = fictional_authorization(original)
        fields = {
            "instruction_hash": sha("other instruction"),
            "authorized_cents": 102,
            "authorized_by": "ANOTHER_FAKE_ACTOR",
            "reason": "different reason",
            "authorized_at": "2026-10-23T12:00:00Z",
            "authorization_hash": "f" * 64,
        }
        for field, value in fields.items():
            with self.subTest(field=field):
                modified = replace(good, **{field: value})
                engine = PaymentOrchestrator(original)
                with self.assertRaises(ValueError):
                    engine.authorize(modified)
                self.assertIsNone(engine.authorization)

    def test_07_identical_authorization_replay_is_idempotent(self):
        inst = fictional_instruction()
        auth = fictional_authorization(inst)
        p = PaymentOrchestrator(inst)
        p.authorize(auth)
        p.authorize(auth)
        self.assertEqual(p.authorization, auth)

    def test_08_change_after_authorization_fails_before_provider_event(self):
        inst = fictional_instruction()
        p = PaymentOrchestrator(inst)
        p.authorize(fictional_authorization(inst))
        p.instruction = replace(inst, payee_id="SYN-AFFILIATE")
        with self.assertRaises(ValueError):
            p.record_provider_event(
                state="SUBMITTED", provider="SYN", provider_reference="R",
                amount_cents=101, source_hash=sha("one"),
                occurred_at="2026-10-22T12:00:01Z",
            )

    def test_09_replay_refuses_modified_authorization(self):
        engine, snapshot = accepted_payment_flow()
        bad = replace(engine.authorization, reason="changed")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            verify_payment_snapshot(engine.instruction, bad, engine.events, snapshot)


class PriorityZeroReconciliationTests(unittest.TestCase):
    def test_10_unmatched_amount_is_cryptographically_bound(self):
        first = reconcile_scoped([scoped_invoice("1.00")], [])
        second = reconcile_scoped([scoped_invoice("999.99")], [])
        self.assertNotEqual(first.result_hash, second.result_hash)
        self.assertEqual(first.unmatched_internal, 1)
        self.assertEqual(first.proven_cleared_payment_count, 0)
        self.assertIsNone(first.independent_payment_accuracy)

    def test_11_all_unmatched_input_fields_are_bound(self):
        a = scoped_invoice()
        baseline = reconcile_scoped([a], []).result_hash
        mutations = (
            scoped_invoice(date="2026-09-02"),
            scoped_invoice(currency="EUR"),
            scoped_invoice(counterparty="SYN-OTHER"),
            scoped_invoice(reference="SYN-OTHER"),
            scoped_invoice(reference=None),
            scoped_invoice(metadata={"origin": "changed"}),
        )
        for mutation in mutations:
            with self.subTest(mutation=str(mutation)[:80]):
                changed = reconcile_scoped([mutation], []).result_hash
                self.assertNotEqual(baseline, changed)

    def test_12_missing_reference_malformed_money_rejected(self):
        for bad in ("NaN", "1e3", "-Infinity", "1,00.00"):
            with self.subTest(amount=bad):
                with self.assertRaises(ValueError):
                    reconcile_scoped([scoped_invoice(bad, reference=None)], [])

    def test_13_orphaned_malformed_amounts_are_rejected(self):
        bads = ("NaN", "1e3", "-Infinity", "1,00.00",
                "１２３.４５", "١٢٣.٤٥", float("inf"), float("nan"), True)
        for bad in bads:
            with self.subTest(amount=str(bad)):
                with self.assertRaises(ValueError):
                    reconcile_scoped([scoped_invoice(bad)], [])

    def test_14_oversize_group_cannot_skip_validation(self):
        values = [
            scoped_invoice("1.00", txn_id="SYN-I-1"),
            scoped_invoice("NaN", txn_id="SYN-I-2"),
            scoped_invoice("2.00", txn_id="SYN-I-3"),
        ]
        with self.assertRaises(ValueError):
            reconcile_scoped(values, [declared_payment("3.00")], group_size_limit=2)

    def test_15_orphaned_malformed_date_is_rejected(self):
        for when in ("not-a-date", "2026-02-30", "09/01/2026"):
            with self.subTest(date=when):
                with self.assertRaises(ValueError):
                    reconcile_scoped([scoped_invoice(date=when)], [])

    def test_16_raw_unmatched_reference_and_removed_row_affect_receipt(self):
        one = scoped_invoice()
        another = scoped_invoice("2.00", txn_id="SYN-I-2")
        a = reconcile_scoped([one, another], [])
        b = reconcile_scoped([one], [])
        c = reconcile_scoped([another, one], [])
        self.assertNotEqual(a.result_hash, b.result_hash)
        self.assertEqual(a.result_hash, c.result_hash)

    def test_17_config_binding_without_matching_rows(self):
        a = scoped_invoice()
        first = reconcile_scoped([a], [], date_window_days=30, group_size_limit=32)
        second = reconcile_scoped([a], [], date_window_days=31, group_size_limit=32)
        third = reconcile_scoped([a], [], date_window_days=30, group_size_limit=33)
        self.assertNotEqual(first.result_hash, second.result_hash)
        self.assertNotEqual(first.result_hash, third.result_hash)

    def test_18_source_declared_join_does_not_prove_real_payment(self):
        r = reconcile_scoped([scoped_invoice()], [declared_payment()])
        self.assertEqual(r.matched_internal, 1)
        self.assertEqual(r.matched_counterparts, 1)
        self.assertEqual(r.proven_cleared_payment_count, 0)
        self.assertIsNone(r.independent_payment_accuracy)

    def test_19_reordering_matched_and_unmatched_rows_is_stable(self):
        a = scoped_invoice("1.00")
        b = scoped_invoice("2.00", txn_id="SYN-I-2", reference=None)
        c = scoped_invoice("3.00", txn_id="SYN-I-3", reference="OTHER")
        p = declared_payment("1.00")
        first = reconcile_scoped([a,b,c], [p])
        second = reconcile_scoped([c,a,b], [p])
        self.assertEqual(first.result_hash, second.result_hash)


if __name__ == "__main__":
    unittest.main(verbosity=2)
