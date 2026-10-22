"""Minimal reproductions for October 22 RETALLY red-team round 2.
All sources, reviewer roles, bank events and customers below are SYNTHETIC.
Never connect to actual providers or authorize commercial financial actions.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch
import time
import unittest

from freight.settlement_store import (
    SettlementStore, RecoveryClaim, SettlementEventRecord, CounterEventRecord,
    ALLOCATED, ALREADY_ALLOCATED, REVIEW, REVERSED, ALREADY_REVERSED,
)
from freight.recovery_resilience import RecoveryScenario, evaluate_recovery_scenario
from freight.priority4_adversarial_lab import make_plan, case_receipt, verify_receipt
import freight.payment_orchestration as payments
from freight.currency_reporting import build_currency_settlement_report


def H(s):
    return sha256(s.encode("ascii")).hexdigest()


def T(day):
    return f"2026-09-{day:02d}T12:00:00Z"


def ledger(location):
    return SettlementStore(location, buyer_id="SYN-BUYER", business_unit="SYN-UNIT")


def c(tag, cents):
    return RecoveryClaim(tag, "SYN-REF", "SYN-CARRIER", "SYN-BUYER",
                         "USD", cents, T(1), H("finding"+tag), False)


def e(tag, cents):
    return SettlementEventRecord(tag, "SYN-REF", "SYN-CARRIER", "SYN-BUYER",
                                 "USD", cents, T(10), H("event"+tag), "SYNTHETIC_CREDIT")


def ret(tag, eid, cents):
    return CounterEventRecord(tag, eid, "USD", cents, T(11),
                              H("return"+tag), "SYNTHETIC_RETURN")


def claim_view(tag, cents):
    return RecoveryScenario(
        case_id="SYN-REF", claim_id=tag,
        buyer_id="SYN-BUYER", business_unit="SYN-UNIT",
        payer_id="SYN-CARRIER", payee_id="SYN-BUYER",
        currency="USD", disputed_cents=cents,
        issued_at="2026-09-01T12:00:00.000000Z",
        source_invoice_sha256=H("invoice"+tag),
        source_finding_sha256=H("finding"+tag),
    )


class TestReturnSafety(unittest.TestCase):
    def test_01_full_return_after_partial_allocation_blocks_later_second_claim(self):
        with TemporaryDirectory() as td:
            db=ledger(Path(td)/"case.sqlite3")
            db.create_claim(c("A",6000))
            db.create_claim(c("B",4000))
            db.ingest_event(e("E",10000))
            self.assertEqual(db.review_allocate(allocation_id="A1",claim_id="A",
              event_id="E",amount_cents=6000,created_at=T(10)), ALLOCATED)
            db.ingest_counter(ret("R","E",10000))
            self.assertEqual(db.auto_apply_counter("R",created_at=T(12)).status, REVERSED)
            # Already-known return capacity must control all *future* credits.
            with self.assertRaises(ValueError):
                db.review_allocate(allocation_id="B1",claim_id="B",event_id="E",
                                   amount_cents=4000,created_at=T(13))
            self.assertEqual(db.realized_cents(),0)
            self.assertEqual(db.claim_residual("B"),4000)
            self.assertEqual(db.count("allocations"),1)
            # A 100% return is not fully applied if only 60% was allocated.
            self.assertEqual(db.auto_apply_counter("R",created_at=T(14)).status, REVIEW)
            self.assertEqual(build_currency_settlement_report(db).by_currency[0].unresolved_counter_cents,4000)

    def test_02_return_before_first_allocation_blocks_all_future_credits(self):
        with TemporaryDirectory() as td:
            db=ledger(Path(td)/"test.sqlite3")
            db.create_claim(c("A",10000))
            db.ingest_event(e("E",10000))
            db.ingest_counter(ret("R","E",10000))
            self.assertEqual(db.auto_apply_counter("R",created_at=T(12)).status, REVIEW)
            self.assertEqual(db.auto_allocate("E",created_at=T(13)).status, REVIEW)
            with self.assertRaises(ValueError):
                db.review_allocate(allocation_id="A1",claim_id="A",event_id="E",
                                   amount_cents=10000,created_at=T(13))
            self.assertEqual(db.realized_cents(),0)

    def test_03_partial_return_can_reconcile_then_remaining_valid_credit_can_book(self):
        with TemporaryDirectory() as td:
            db=ledger(Path(td)/"case.sqlite3")
            db.create_claim(c("A",6000))
            db.create_claim(c("B",4000))
            db.ingest_event(e("E",10000))
            db.review_allocate(allocation_id="A1",claim_id="A",event_id="E",
                               amount_cents=6000,created_at=T(10))
            db.ingest_counter(ret("R","E",2000))
            self.assertEqual(db.auto_apply_counter("R",created_at=T(12)).status, REVERSED)
            self.assertEqual(db.auto_apply_counter("R",created_at=T(13)).status,ALREADY_REVERSED)
            # Original 10000 - returned 2000 = 8000 available credit.
            self.assertEqual(db.review_allocate(allocation_id="B1",claim_id="B",event_id="E",
                               amount_cents=4000,created_at=T(14)),ALLOCATED)
            self.assertEqual(db.realized_cents(),8000)
            self.assertEqual(db.fee_eligible_cents(),8000)

    def test_04_two_return_events_cannot_reverse_more_than_original_credit(self):
        with TemporaryDirectory() as td:
            db=ledger(Path(td)/"test.sqlite3")
            db.ingest_event(e("E",10000))
            self.assertTrue(db.ingest_counter(ret("R1","E",7000)))
            with self.assertRaises(ValueError):
                db.ingest_counter(ret("R2","E",4000))
            self.assertEqual(db.count("counter_events"),1)

    def test_05_partially_applied_counter_retry_reverses_remaining_existing_claim(self):
        with TemporaryDirectory() as td:
            db=ledger(Path(td)/"test.sqlite3")
            db.create_claim(c("A",6000))
            db.create_claim(c("B",4000))
            db.ingest_event(e("E",10000))
            db.review_allocate(allocation_id="A1",claim_id="A",event_id="E",
                               amount_cents=6000,created_at=T(10))
            db.review_allocate(allocation_id="B1",claim_id="B",event_id="E",
                               amount_cents=4000,created_at=T(10))
            db.ingest_counter(ret("R","E",10000))
            # Two allocations are already present when full return arrives:
            # exactly 10000 should be reversed, with no phantom remainder.
            self.assertEqual(db.auto_apply_counter("R",created_at=T(12)).status,REVERSED)
            self.assertEqual(db.auto_apply_counter("R",created_at=T(13)).status,ALREADY_REVERSED)
            self.assertEqual(db.realized_cents(),0)
            self.assertEqual(build_currency_settlement_report(db).by_currency[0].unresolved_counter_cents,0)


class TestReceiptIntegrity(unittest.TestCase):
    def test_06_receipt_generation_rejects_fabricated_customer_authorization_and_fees(self):
        for i in range(8):
            plan=make_plan(i+100)
            actual=evaluate_recovery_scenario(
                plan.scenario,events=plan.events,customer_requests=plan.requests,
                assumptions=plan.assumptions,as_of=plan.as_of,
            )
            poison=replace(actual,externally_approved_case=True,
                           carrier_contact_attempts=1,payment_actions_performed=1,
                           independently_verified_cash_cents=1000+i,
                           customer_fee_billable_cents=200+i)
            with self.subTest(case=i):
                with self.assertRaises((AssertionError,ValueError)):
                    case_receipt(plan,poison)
                # Standalone verification also must reject fabricated outputs
                # even if the forged receipt was generated from benign data.
                benign=case_receipt(plan,actual)
                with self.assertRaises((AssertionError,ValueError)):
                    verify_receipt(plan,poison,benign)

    def test_07_mutated_customer_request_evidence_is_bound_to_receipt(self):
        plan=make_plan(7)
        actual=evaluate_recovery_scenario(
            plan.scenario,events=plan.events,customer_requests=plan.requests,
            assumptions=plan.assumptions,as_of=plan.as_of,
        )
        receipt=case_receipt(plan,actual)
        verify_receipt(plan,actual,receipt)
        poisoned=replace(actual,customer_request_triage=(
            replace(actual.customer_request_triage[0],no_money_movement=False),
            actual.customer_request_triage[1],
        ))
        with self.assertRaises((ValueError,AssertionError)):
            case_receipt(plan,poisoned)
        with self.assertRaises((ValueError,AssertionError)):
            verify_receipt(plan,poisoned,receipt)


class TestProviderConcurrency(unittest.TestCase):
    def test_08_two_distinct_simultaneous_first_events_are_atomic_and_replayable(self):
        i=payments.prepare_payment_instruction(
            instruction_id="SYN-RACE",buyer_id="SYN-BUYER",business_unit="SYN-UNIT",
            payer_id="SYN-PAYER",payee_id="SYN-PAYEE",currency="USD",
            amount_cents=1234,purpose="SYNTHETIC_TEST",
            finding_proof_hashes=(H("finding"),),idempotency_key="SYN-IDEMP",
        )
        approval=payments.authorize_payment(
            i,authorized_by="SIMULATED_NOT_A_REAL_PERSON",
            reason="synthetic thread race",authorized_at="2026-10-22T12:00:00Z",
        )
        for iteration in range(12):
            engine=payments.PaymentOrchestrator(i)
            engine.authorize(approval)
            start=Barrier(2)
            previous=payments.canonical_hash
            def slow_hash(data):
                if isinstance(data,dict) and "previous_event_hash" in data:
                    time.sleep(0.04)  # allows racing callers through unsafe prechecks
                return previous(data)
            def submit(tag):
                start.wait(timeout=5)
                try:
                    return engine.record_provider_event(
                        state="SUBMITTED",provider="SYN-PROVIDER",
                        provider_reference=f"R{iteration}-{tag}",
                        amount_cents=1234,
                        source_hash=H(f"src-{iteration}-{tag}"),
                        occurred_at="2026-10-22T12:01:00Z",
                    )
                except ValueError as exc:
                    return exc
            with patch.object(payments,"canonical_hash",side_effect=slow_hash):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    values=list(pool.map(submit,(1,2)))
            with self.subTest(iteration=iteration):
                self.assertEqual(sum(isinstance(x, payments.ProviderPaymentEvent)
                                     for x in values),1)
                self.assertEqual(len(engine.events),1)
                self.assertIsNone(engine.events[0].previous_event_hash)
                payments.verify_payment_snapshot(i,approval,engine.events,engine.snapshot())


class TestSharedReturnAttribution(unittest.TestCase):
    def test_09_shared_counter_is_not_double_counted_per_claim(self):
        with TemporaryDirectory() as td:
            db=ledger(Path(td)/"case.sqlite3")
            db.create_claim(c("A",5000))
            db.create_claim(c("B",5000))
            db.ingest_event(e("E",10000))
            db.review_allocate(allocation_id="A1",claim_id="A",event_id="E",
                               amount_cents=5000,created_at=T(10))
            db.review_allocate(allocation_id="B1",claim_id="B",event_id="E",
                               amount_cents=5000,created_at=T(10))
            db.ingest_counter(ret("R","E",3000))
            a=evaluate_recovery_scenario(claim_view("A",5000),as_of="2026-10-22",store=db)
            b=evaluate_recovery_scenario(claim_view("B",5000),as_of="2026-10-22",store=db)
            self.assertEqual(a.state,"RETURN_REVERSAL_REVIEW_HOLD")
            self.assertEqual(b.state,"RETURN_REVERSAL_REVIEW_HOLD")
            # No arbitrary claim-level allocation; the global report owns
            # exactly one 3000-cent unresolved event-level counter.
            self.assertEqual(a.settlement.outstanding_return_cents,0)
            self.assertEqual(b.settlement.outstanding_return_cents,0)
            self.assertEqual(len(a.settlement.unattributed_shared_return_event_ids),1)
            self.assertEqual(a.settlement.unattributed_shared_return_event_ids,
                             b.settlement.unattributed_shared_return_event_ids)
            self.assertEqual(build_currency_settlement_report(db).by_currency[0].unresolved_counter_cents,3000)
            self.assertEqual(a.independently_verified_cash_cents,0)
            self.assertEqual(b.customer_fee_billable_cents,0)

    def test_10_single_claim_counter_still_reports_exact_pending_amount(self):
        with TemporaryDirectory() as td:
            db=ledger(Path(td)/"test.sqlite3")
            db.create_claim(c("A",5000))
            db.ingest_event(e("E",5000))
            db.review_allocate(allocation_id="A1",claim_id="A",event_id="E",
                               amount_cents=5000,created_at=T(10))
            db.ingest_counter(ret("R","E",3000))
            a=evaluate_recovery_scenario(claim_view("A",5000),as_of="2026-10-22",store=db)
            self.assertEqual(a.settlement.outstanding_return_cents,3000)
            self.assertEqual(a.settlement.unattributed_shared_return_event_ids,())
            self.assertEqual(a.state,"RETURN_REVERSAL_REVIEW_HOLD")


if __name__=="__main__":
    unittest.main(verbosity=2)
