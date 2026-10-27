"""Severe source-bound RETALLY acceptance tests; no customer financial actions.

Uses deterministic independent oracles and deliberate receipt/engine-output
mutations. Runs on both Linux and Windows without a stochastic external service,
paid agent, connected customer app, bank API, OCR source or privileged key.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from freight.currency_reporting import (
    assert_currency_report_current, build_currency_settlement_report,
)
from freight.payment_orchestration import (
    PaymentOrchestrator, authorize_payment, prepare_payment_instruction,
    verify_payment_snapshot,
)
from freight.priority4_adversarial_lab import (
    CREDIT_MODES, CURRENCIES, EVENT_COMBINATIONS, MODES, REQUEST_COMBINATIONS, SEED, ReplayOracle, make_plan, independent_oracle, expected_state, execute_case,
    assert_independent_invariants, case_receipt, verify_receipt, digest, h,
)
from freight.recovery_resilience import (
    evaluate_recovery_scenario,
)
from freight.scoped_reconciliation import ScopedTxn
from freight.priority2_evidence import reconcile_invoice_evidence
from freight.settlement_store import (
    SettlementStore, RecoveryClaim, SettlementEventRecord, CounterEventRecord,
    ALLOCATED, ALREADY_ALLOCATED,
)
from recoveryworks.reconciliation_kernel import ReconTxn


HERE = Path(__file__).resolve().parent
BASELINE = HERE / "fixtures" / "priority4_synthetic_stress_baseline_v1.json"
ANALYSIS_COUNT = 3072
SQLITE_COUNT = 120
PAYMENT_COUNT = 240


def _empty_oracle(p) -> ReplayOracle:
    return ReplayOracle(0, 0, 0, 0, 0, p.scenario.disputed_cents)


def _no_real_claim(r) -> None:
    assert r.externally_approved_case is False
    assert r.carrier_contact_attempts == 0
    assert r.payment_actions_performed == 0
    assert r.independently_verified_cash_cents == 0
    assert r.customer_fee_billable_cents == 0
    assert r.settlement.real_recovered_cash_cents == 0
    assert r.settlement.source_authenticated_payment_cents == 0
    assert r.feasibility.probabilities_empirically_calibrated is False
    assert r.feasibility.no_billable_fee_authority is True
    assert r.events_seen == 2
    assert r.requests_seen == 2
    assert all(x.no_money_movement and x.no_external_action
               for x in r.customer_request_triage)
    assert "NO_INDEPENDENT_FREIGHT_ADJUDICATION" in r.blockers
    assert "NO_VERIFIED_CUSTOMER_RECOVERY_CONSENT" in r.blockers


def _manifest_3072():
    cases = []
    persona_currency_mode = defaultdict(set)
    persona_events = defaultdict(set)
    persona_requests = defaultdict(set)
    credit_modes = Counter()
    modes = Counter()
    states = Counter()
    all_input_hashes = set()
    for i in range(ANALYSIS_COUNT):
        p = make_plan(i)
        r = evaluate_recovery_scenario(
            p.scenario, events=p.events, customer_requests=p.requests,
            assumptions=p.assumptions, as_of=p.as_of,
        )
        _no_real_claim(r)
        if r.state != expected_state(p, _empty_oracle(p)):
            raise AssertionError("independent state oracle disagrees with engine")
        if r.settlement.snapshot_sha256 is not None:
            raise AssertionError("source-free run fabricated settlement evidence")
        if p.input_sha256 in all_input_hashes:
            raise AssertionError("colliding synthetic case input receipt")
        all_input_hashes.add(p.input_sha256)
        persona_currency_mode[p.customer.persona].add((p.customer.currency, p.customer.mode))
        persona_events[p.customer.persona].add(tuple(e.kind for e in p.events))
        persona_requests[p.customer.persona].add(tuple(q.kind for q in p.requests))
        credit_modes[p.credit_mode] += 1
        modes[p.customer.mode] += 1
        states[r.state] += 1
        cases.append({
            "input": p.input_sha256,
            "state": r.state,
            "report": r.report_hash,
            "assumptions": r.feasibility.result_hash,
        })
    return {
        "schema": "retally-priority4-manifest-v1",
        "seed": SEED,
        "population": ANALYSIS_COUNT,
        "input_receipt_count": len(all_input_hashes),
        "personas": len(persona_currency_mode),
        "currencies": len(CURRENCIES),
        "freight_modes": len(MODES),
        "scenario_event_combinations": len(EVENT_COMBINATIONS),
        "scenario_request_combinations": len(REQUEST_COMBINATIONS),
        "credit_patterns": dict(sorted(credit_modes.items())),
        "states": dict(sorted(states.items())),
        "persona_currency_mode_min": min(map(len, persona_currency_mode.values())),
        "persona_event_pattern_min": min(map(len, persona_events.values())),
        "persona_request_pattern_min": min(map(len, persona_requests.values())),
        "receipt_list_sha256": digest(cases),
        "classification": "SYNTHETIC_NO_REAL_FREIGHT_ACCURACY",
        "actual_customer_financial_actions": 0,
        "independently_adjudicated_freight_labels": 0,
    }


def _claim_and_event(store: SettlementStore, *, case: str, currency: str = "USD",
                     cents: int = 10000) -> None:
    store.create_claim(RecoveryClaim(
        "claim:"+case, case, "SYN-CARRIER", "SYN-BUYER", currency, cents,
        "2026-09-01T10:00:00Z", h("claim-source-"+case),
    ))
    store.ingest_event(SettlementEventRecord(
        "settle:"+case, case, "SYN-CARRIER", "SYN-BUYER", currency, cents,
        "2026-09-10T12:00:00Z", h("settlement-source-"+case), "SYNTHETIC",
    ))


class TestPriority4Adversarial(unittest.TestCase):
    def test_01_3072_complex_customer_cases_have_no_silent_real_accuracy(self):
        metrics = _manifest_3072()
        self.assertEqual(metrics["population"], ANALYSIS_COUNT)
        self.assertEqual(metrics["input_receipt_count"], ANALYSIS_COUNT)
        self.assertEqual(metrics["personas"], 12)
        self.assertEqual(metrics["freight_modes"], 6)
        self.assertEqual(len(metrics["credit_patterns"]), 8)
        self.assertEqual(sum(metrics["states"].values()), ANALYSIS_COUNT)
        # Every persona explores many independent combinations, not one
        # fixed difficult-case archetype.
        self.assertGreaterEqual(metrics["persona_event_pattern_min"], 10)
        self.assertGreaterEqual(metrics["persona_request_pattern_min"], 10)
        self.assertGreaterEqual(metrics["persona_currency_mode_min"], 12)
        self.assertEqual(metrics["actual_customer_financial_actions"], 0)
        self.assertEqual(metrics["independently_adjudicated_freight_labels"], 0)
        self.assertEqual(metrics, json.loads(BASELINE.read_text(encoding="utf-8")))

    def test_02_120_exact_native_sqlite_recovery_lifecycles_and_original_hashes(self):
        receipts = []
        statuses = Counter()
        credits = Counter()
        with tempfile.TemporaryDirectory(prefix="retally-p4-") as td:
            root = Path(td)
            for i in range(SQLITE_COUNT):
                p = make_plan(i)
                r, oracle = execute_case(p, root=root)
                if r.state != expected_state(p, oracle):
                    raise AssertionError(f"state mismatch on case {i}: {r.state}")
                _no_real_claim(r)
                rec = case_receipt(p, r)
                verify_receipt(p, r, rec)
                self.assertEqual(rec.customer_fee_billable_cents, 0)
                self.assertNotEqual(r.settlement.snapshot_sha256, None)
                self.assertGreaterEqual(r.settlement.source_declared_net_cents, 0)
                self.assertGreaterEqual(r.settlement.unallocated_claim_residual_cents, 0)
                receipts.append(rec.case_receipt_sha256)
                statuses[r.state] += 1
                credits[p.credit_mode] += 1
        self.assertEqual(len(receipts), SQLITE_COUNT)
        self.assertEqual(len(set(receipts)), SQLITE_COUNT)
        self.assertEqual(len(credits), len(CREDIT_MODES))
        self.assertEqual(sum(statuses.values()), SQLITE_COUNT)

    def test_03_mutations_of_financial_outputs_are_rejected_by_independent_oracle(self):
        with tempfile.TemporaryDirectory(prefix="retally-p4-mutant-") as td:
            # Use fee-eligible partial allocation and a complex dispute.
            p = make_plan(3)
            r, oracle = execute_case(p, root=Path(td))
            good = case_receipt(p, r)
            verify_receipt(p, r, good)
            changes = [
                replace(r, case_id="SYN-OTHER-CLIENT"),
                replace(r, externally_approved_case=True),
                replace(r, payment_actions_performed=1),
                replace(r, carrier_contact_attempts=1),
                replace(r, customer_fee_billable_cents=300),
                replace(r, independently_verified_cash_cents=500),
                replace(r, settlement=replace(
                    r.settlement, source_declared_net_cents=oracle.settled_net_cents+1)),
                replace(r, settlement=replace(
                    r.settlement, unallocated_claim_residual_cents=oracle.claim_residual_cents+1)),
                replace(r, settlement=replace(
                    r.settlement, real_recovered_cash_cents=100)),
                replace(r, settlement=replace(
                    r.settlement, source_authenticated_payment_cents=100)),
                replace(r, feasibility=replace(
                    r.feasibility, probabilities_empirically_calibrated=True)),
                replace(r, feasibility=replace(
                    r.feasibility, no_billable_fee_authority=False)),
                replace(r, events_seen=1),
                replace(r, requests_seen=1),
                replace(r, customer_request_triage=tuple()),
                replace(r, customer_request_triage=(
                    replace(r.customer_request_triage[0], no_external_action=False),
                    r.customer_request_triage[1],
                )),
                replace(r, customer_request_triage=(
                    replace(r.customer_request_triage[0], no_money_movement=False),
                    r.customer_request_triage[1],
                )),
                replace(r, report_hash="0"*64),
            ]
            # Independent monetary/authorization oracle must expose each bad
            # state before any receipt re-hashing or private workflow action.
            failures = 0
            for mutant in changes:
                with self.subTest(mutant=failures):
                    try:
                        assert_independent_invariants(p, mutant, oracle)
                    except AssertionError:
                        failures += 1
                    else:
                        # Cryptographic-only mutation is detected separately:
                        # the financial invariant does not recompute report SHA.
                        if mutant.report_hash == "0"*64:
                            with self.assertRaises(AssertionError):
                                verify_receipt(p, mutant, good)
                            failures += 1
                        else:
                            self.fail("deliberate safety mutation escaped")
            self.assertEqual(failures, len(changes))
            for poisoned in (
                replace(good, case_id="WRONG-CUSTOMER"),
                replace(good, source_declared_net_cents=good.source_declared_net_cents+1),
                replace(good, independent_cash_verified_cents=99),
                replace(good, case_receipt_sha256="0"*64),
            ):
                with self.assertRaises(AssertionError):
                    verify_receipt(p, r, poisoned)

    def test_04_failed_original_source_revision_is_detected_at_case_receipt(self):
        p = make_plan(48)
        with tempfile.TemporaryDirectory(prefix="retally-p4-input-") as td:
            r, oracle = execute_case(p, root=Path(td))
            assert_independent_invariants(p, r, oracle)
            receipt = case_receipt(p, r)
            changed = replace(p, scenario=replace(
                p.scenario, source_finding_sha256=h("altered-finding")))
            with self.assertRaises(ValueError):
                verify_receipt(changed, r, receipt)
            changed = replace(p, customer=replace(
                p.customer, customer_id="CROSS-TENANT"))
            with self.assertRaises(ValueError):
                verify_receipt(changed, r, receipt)
            changed = replace(p, assumptions=replace(
                p.assumptions, modeled_fee_rate_bps=10000))
            with self.assertRaises(ValueError):
                verify_receipt(changed, r, receipt)
            changed = replace(p, requests=(
                replace(p.requests[0], source_sha256=h("changed-private-request")),
                p.requests[1],
            ))
            with self.assertRaises(ValueError):
                verify_receipt(changed, r, receipt)

    def test_05_crash_rollbacks_leave_zero_ghost_claims_or_credits(self):
        with tempfile.TemporaryDirectory(prefix="retally-p4-crash-") as td:
            for i in range(30):
                path = Path(td) / f"synthetic-crash-{i}.sqlite3"
                s = SettlementStore(path, buyer_id=f"SYN-BUYER-{i}",
                                     business_unit="SYN-UNIT")
                conn = sqlite3.connect(str(path), isolation_level=None)
                try:
                    conn.execute("PRAGMA foreign_keys=ON")
                    conn.execute("BEGIN IMMEDIATE")
                    conn.execute(
                        "INSERT INTO recovery_claims "
                        "(buyer_id,business_unit,claim_id,reference,payer_id,payee_id,"
                        "currency,amount_cents,issued_at,source_hash,fee_disqualified)"
                        " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (f"SYN-BUYER-{i}", "SYN-UNIT", "SYN-CRASH-CLAIM",
                         "SYN-REF", "SYN-CARRIER", "SYN-CLIENT",
                         "USD", 10000, "2026-09-01T10:00:00.000000Z",
                         h(f"synthetic-claim-{i}"), 0),
                    )
                    self.assertEqual(s.count("recovery_claims"), 0 if False else 0)
                    # Concurrent readers cannot see uncommitted rows. Drop
                    # the connection without a COMMIT to simulate crash.
                    conn.rollback()
                finally:
                    conn.close()
                reopened = SettlementStore(path, buyer_id=f"SYN-BUYER-{i}",
                                           business_unit="SYN-UNIT")
                self.assertEqual(reopened.count("recovery_claims"), 0)
                self.assertEqual(reopened.count("settlement_events"), 0)
                self.assertEqual(reopened.count("allocations"), 0)

    def test_06_twenty_four_parallel_duplicate_credit_claims_only_allocate_once(self):
        with tempfile.TemporaryDirectory(prefix="retally-p4-race-") as td:
            for i in range(24):
                path = Path(td) / f"race-{i}.sqlite3"
                s = SettlementStore(path, buyer_id="SYN-BUYER",business_unit="SYN-UNIT")
                name=f"race-{i}"
                _claim_and_event(s,case=name,cents=10000+i)
                def worker(_):
                    return s.auto_allocate(
                        "settle:"+name, created_at="2026-09-11T12:00:00Z").status
                with ThreadPoolExecutor(max_workers=8) as pool:
                    statuses = list(pool.map(worker, range(12)))
                self.assertEqual(statuses.count(ALLOCATED), 1)
                self.assertEqual(statuses.count(ALREADY_ALLOCATED), 11)
                self.assertEqual(s.realized_cents(), 10000+i)
                self.assertEqual(s.fee_eligible_cents(), 10000+i)
                self.assertEqual(s.count("allocations"), 1)

    def test_07_stale_currency_reports_cannot_hide_new_return_events(self):
        with tempfile.TemporaryDirectory(prefix="retally-p4-report-") as td:
            for i,currency in enumerate(CURRENCIES):
                s = SettlementStore(Path(td)/f"stale-{i}.sqlite3",
                                    buyer_id="SYN-BUYER", business_unit="SYN-UNIT")
                name=f"report-{i}"
                _claim_and_event(s,case=name,cents=10000+i,currency=currency)
                self.assertEqual(s.auto_allocate(
                    "settle:"+name,created_at="2026-09-11T12:00:00Z").status, ALLOCATED)
                old = build_currency_settlement_report(s)
                assert_currency_report_current(old,s)
                counter_id=f"return-{i}"
                s.ingest_counter(CounterEventRecord(
                    counter_id, "settle:"+name, currency, 3000,
                    "2026-09-12T12:00:00Z", h("return-proof-"+name),
                    "SYNTHETIC_RETURN_NOT_BANK_CLEARED",
                ))
                with self.assertRaises(ValueError):
                    assert_currency_report_current(old,s)
                s.auto_apply_counter(counter_id,created_at="2026-09-13T12:00:00Z")
                fresh = build_currency_settlement_report(s)
                assert_currency_report_current(fresh,s)
                self.assertNotEqual(old.snapshot_hash,fresh.snapshot_hash)
                self.assertEqual(fresh.by_currency[0].declared_net_allocated_cents,7000+i)
                self.assertFalse(fresh.external_settlement_verified)
                self.assertIsNone(fresh.single_aggregated_total_cents)

    def test_08_240_complex_payment_state_machines_reject_impossible_replays(self):
        for i in range(PAYMENT_COUNT):
            ident=f"SYN-P4-PAYMENT-{i:04d}"
            amount=100+i*17
            inst=prepare_payment_instruction(
                instruction_id=ident,buyer_id=f"SYN-BUYER-{i}",
                business_unit="SYN-UNIT",payer_id="SYN-CARRIER",
                payee_id=f"SYN-PAYEE-{i}",currency="USD",
                amount_cents=amount,purpose="SIMULATION_ONLY",
                finding_proof_hashes=(h(f"source-{i}"),),
                idempotency_key=f"SYN-REPLAY-{i}",
            )
            auth=authorize_payment(
                inst,authorized_by="SYNTHETIC-NOT-A-REAL-REVIEWER",
                reason="simulated state-machine test",
                authorized_at="2026-10-22T12:00:00Z",
            )
            engine=PaymentOrchestrator(inst)
            with self.assertRaises(ValueError):
                engine.record_provider_event(
                    state="SUBMITTED",provider="SYN-PROVIDER",
                    provider_reference=ident,amount_cents=amount,
                    source_hash=h(ident+"-before"),occurred_at="2026-10-22T12:01:00Z",
                )
            engine.authorize(auth)
            with self.assertRaises(ValueError):
                engine.record_provider_event(
                    state="SETTLED",provider="SYN-PROVIDER",
                    provider_reference=ident,amount_cents=amount,
                    source_hash=h(ident+"-skip"),
                    occurred_at="2026-10-22T12:01:00Z",
                )
            with self.assertRaises(ValueError):
                engine.record_provider_event(
                    state="SUBMITTED",provider="SYN-PROVIDER",
                    provider_reference=ident,amount_cents=amount,
                    source_hash=h(ident+"-early"),
                    occurred_at="2026-10-22T11:59:59Z",
                )
            states=("SUBMITTED","ACCEPTED","SETTLED","REVERSED")
            for step,state in enumerate(states):
                args={
                    "state":state, "provider":"SYN-PROVIDER",
                    "provider_reference":ident, "amount_cents":amount,
                    "source_hash":h(ident+"-"+state),
                    "occurred_at":f"2026-10-22T12:0{step+1}:00Z",
                }
                e=engine.record_provider_event(**args)
                self.assertEqual(engine.record_provider_event(**args),e)
                with self.assertRaises(ValueError):
                    engine.record_provider_event(**{**args,
                        "source_hash":h(ident+"-mutated-"+state)})
            self.assertEqual(len(engine.events),4)
            self.assertEqual(engine.current_state,"REVERSED")
            self.assertEqual(engine.snapshot().settled_cents,0)
            verify_payment_snapshot(inst,auth,engine.events,engine.snapshot())
            with self.assertRaises(ValueError):
                PaymentOrchestrator(replace(inst,payee_id="UNAUTHORIZED-PAYEE"))
            with self.assertRaises(ValueError):
                verify_payment_snapshot(inst,replace(auth,reason="tampered"),
                                        engine.events,engine.snapshot())

    def test_09_unsupported_money_currency_or_overcapacity_fail_closed(self):
        for i in range(200):
            p=make_plan(i)
            with self.assertRaises(ValueError):
                replace(p.scenario,simulation_only=False)
            with self.assertRaises(ValueError):
                replace(p.scenario,currency="JPY")
            with self.assertRaises(ValueError):
                replace(p.scenario,disputed_cents=-1)
            with self.assertRaises(ValueError):
                replace(p.scenario,disputed_cents=True)
            with self.assertRaises(ValueError):
                replace(p.scenario,disputed_cents=2**63)
            with self.assertRaises(ValueError):
                replace(p.events[0],source_sha256="UNSAFE-PROOF")
            with self.assertRaises(ValueError):
                replace(p.events[0],observed_at="2026-02-31T14:00:00Z")
            with self.assertRaises(ValueError):
                evaluate_recovery_scenario(
                    p.scenario,events=(p.events[0],p.events[0]),
                    customer_requests=p.requests,assumptions=p.assumptions,as_of=p.as_of,
                )

    def test_10_120_reconciliation_reference_collisions_do_not_cross_customers(self):
        for i in range(120):
            a=f"buyer-{i}"
            other=f"other-{i}"
            invoice=ScopedTxn(ReconTxn(
                f"SYN-I-{i}","150.00","2026-09-01","USD",
                "COMMON-REMITTANCE"),a,"unit","carrier","ORIGINAL_INVOICE")
            same=ScopedTxn(ReconTxn(
                f"SYN-P-{i}","150.00","2026-09-02","USD",
                "COMMON-REMITTANCE"),a,"unit","carrier","CUSTOMER_DECLARATION")
            foreign=replace(same,buyer_id=other,txn=replace(same.txn,id=f"SYN-OUT-{i}"))
            valid=reconcile_invoice_evidence((invoice,),(same,))
            invalid=reconcile_invoice_evidence((invoice,),(foreign,))
            self.assertEqual(valid.source_declared_matches,1)
            self.assertFalse(valid.authentic_bank_proof_established)
            self.assertIsNone(valid.real_freight_detection_accuracy)
            self.assertEqual(invalid.source_declared_matches,0)
            self.assertEqual(invalid.invoice_unknown,1)
            self.assertEqual(invalid.counterpart_unknown,1)
            self.assertNotEqual(valid.receipt_sha256,invalid.receipt_sha256)

    def test_11_source_revision_and_request_fingerprints_change_deterministically(self):
        for i in range(250):
            p=make_plan(i)
            reversed_event = replace(
                p.events[0],source_sha256=h("revised-carrier-"+str(i)))
            mutated=replace(p,events=(reversed_event, *p.events[1:]))
            with self.assertRaises(ValueError):
                independent_oracle(mutated)
            swapped=replace(p,requests=(p.requests[1],p.requests[0]))
            with self.assertRaises(ValueError):
                independent_oracle(swapped)
            self.assertNotEqual(p.input_sha256,make_plan(i,seed=SEED+1).input_sha256)

    def test_12_engine_never_proves_bank_clearance_using_self_labeled_data(self):
        for i in range(64):
            p=make_plan(i)
            r=evaluate_recovery_scenario(
                p.scenario,events=p.events,customer_requests=p.requests,
                assumptions=p.assumptions,as_of=p.as_of,
            )
            self.assertFalse(r.externally_approved_case)
            self.assertEqual(r.customer_fee_billable_cents,0)
            self.assertEqual(r.independently_verified_cash_cents,0)
            self.assertIsNone(r.settlement.snapshot_sha256)
            if p.assumptions.modeled_collection_probability_bps is None:
                self.assertIsNone(r.feasibility.modeled_collectible_cents)
                self.assertIsNone(r.feasibility.modeled_contingency_fee_cents)
                self.assertIsNone(r.feasibility.modeled_net_fee_after_cost_cents)

    def test_13_eight_live_harness_mutations_fail_before_evidence_receipt(self):
        # Inject corrupted outputs directly at the audited engine boundary.
        # The real engine source and all customer/payment workflows stay intact.
        p=make_plan(23)
        with tempfile.TemporaryDirectory(prefix="retally-p4-boundary-mutations-") as td:
            good,_ = execute_case(p,root=Path(td)/"baseline")
            poison = [
                replace(good, state="SOURCE_DECLARED_FULLY_SETTLED_UNVERIFIED"),
                replace(good, case_id="SYN-CROSS-CUSTOMER"),
                replace(good, independently_verified_cash_cents=100),
                replace(good, customer_fee_billable_cents=100),
                replace(good, externally_approved_case=True),
                replace(good, events_seen=1),
                replace(good, settlement=replace(
                    good.settlement,
                    source_declared_net_cents=good.settlement.source_declared_net_cents+1)),
                replace(good, customer_request_triage=(
                    replace(good.customer_request_triage[0],no_money_movement=False),
                    good.customer_request_triage[1],
                )),
            ]
            self.assertEqual(len(poison),8)
            for index,mutant in enumerate(poison):
                with self.subTest(patched_engine=index):
                    with patch(
                        "freight.priority4_adversarial_lab.evaluate_recovery_scenario",
                        return_value=mutant,
                    ):
                        with self.assertRaises(AssertionError):
                            execute_case(p,root=Path(td)/f"mutant-{index}")

    def test_14_no_private_customer_fixture_or_credentials_in_source(self):
        source=Path(__file__).with_name("priority4_adversarial_lab.py").read_text()
        self.assertIn("SYN-CLIENT-",source)
        self.assertIn("SYNTHETIC_CARRIER_CREDIT_NOT_BANK_CLEARED",source)
        self.assertNotIn("https://",source)
        self.assertNotIn("BEGIN PRIVATE KEY",source)
        self.assertNotIn("sk-proj-",source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
