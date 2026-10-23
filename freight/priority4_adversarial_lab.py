"""Deterministic adversarial freight-recovery laboratory.

Uses actual RETALLY recovery/settlement modules on deliberately fictional
customers, invoices, carrier credits and requests. Nothing is sent, collected,
authorized, booked against a real customer, or promoted to independent truth.
No Work, paid external services, customer files or privileged issuer keys.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import json
import random
import tempfile
from typing import Iterable

from freight.contracts import canonical_hash
from freight.recovery_resilience import (
    CustomerRequest, FeasibilityAssumptions, RecoveryEvent, RecoveryScenario,
    RecoveryScenarioResult, evaluate_recovery_scenario,
)
from freight.settlement_store import (
    ALLOCATED, ALREADY_ALLOCATED, REVERSED, SettlementStore, RecoveryClaim,
    SettlementEventRecord, CounterEventRecord,
)

SEED = 20261022
SCHEMA = "retally-priority4-synthetic-stress-v1"
PERSONAS = (
    "rural-hospital-network", "cross-border-wholesaler",
    "pharmaceutical-distributor", "high-volume-ecommerce",
    "regional-manufacturer", "municipal-works-fleet",
    "frozen-food-cooperative", "disaster-relief-logistics",
    "building-contractor", "multi-brand-retailer",
    "port-freight-forwarder", "small-family-business",
)
CURRENCIES = ("USD", "EUR", "GBP")
MODES = ("LTL", "PARCEL", "TL", "INTERMODAL", "AIR", "OCEAN")
CREDIT_MODES = (
    "NO_SETTLEMENT", "PARTIAL_CREDIT", "SPLIT_CREDITS",
    "FULL_CREDIT", "PARTIAL_REVERSAL", "PENDING_RETURN",
    "FULL_REVERSAL", "REPLAY_STORM",
)
EVENT_COMBINATIONS = (
    ("CARRIER_DENIAL", "CARRIER_EVIDENCE_REQUEST"),
    ("INSOLVENCY_NOTICE", "CLAIM_TIME_BAR_CONCERN"),
    ("CARRIER_DISPUTE", "APPEAL_PREPARED"),
    ("DELAY_NOTICE", "PARTIAL_OFFER"),
    ("ACCOUNT_CREDIT_OFFER", "CUSTOMER_DISPUTE"),
    ("CARRIER_OUT_OF_BUSINESS", "CARRIER_DENIAL"),
    ("PAYMENT_REVERSAL_NOTICE", "DELAY_NOTICE"),
    ("CUSTOMER_WITHDRAWAL", "CARRIER_EVIDENCE_REQUEST"),
    ("CLAIM_TIME_BAR_CONCERN", "CARRIER_EVIDENCE_REQUEST"),
    ("PARTIAL_OFFER", "CARRIER_DENIAL"),
    ("CUSTOMER_DISPUTE", "INSOLVENCY_NOTICE"),
    ("CARRIER_EVIDENCE_REQUEST", "ACCOUNT_CREDIT_OFFER"),
)
REQUEST_COMBINATIONS = (
    ("GUARANTEED_RECOVERY", "FAST_TRACK_PROVIDER_PAYMENT"),
    ("PAY_AFFILIATE", "CUSTOMER_DATA_EXPORT"),
    ("DELETE_ALL_EVIDENCE", "FEE_WAIVER"),
    ("IMMEDIATE_SETTLEMENT", "CHANGE_CUSTOMER_SCOPE"),
    ("DISPUTE_FINDING", "INVOICE_CORRECTION"),
    ("CROSS_TENANT_MERGE", "RETENTION_EXCEPTION"),
    ("WITHDRAW_CASE", "GUARANTEED_RECOVERY"),
    ("NEW_PAYEE", "SANITIZED_READ_ONLY_SUMMARY"),
    ("FORCE_RECOVERY_CLAIM", "FEE_WAIVER"),
    ("CUSTOMER_DATA_EXPORT", "DISPUTE_FINDING"),
    ("RETENTION_EXCEPTION", "PAY_AFFILIATE"),
    ("SANITIZED_READ_ONLY_SUMMARY", "IMMEDIATE_SETTLEMENT"),
)
ISSUED = "2026-09-01T10:00:00.000000Z"
OBSERVED_ONE = "2026-09-10T12:00:00.000000Z"
OBSERVED_TWO = "2026-09-12T12:00:00.000000Z"
REQUEST_TIME = "2026-09-14T12:00:00.000000Z"
AS_OF = "2028-10-22"  # Aging past two years is deliberate, not a legal deadline.
MAX_CENTS = 2**63 - 1


def h(value: str) -> str:
    return sha256(value.encode("ascii")).hexdigest()


def digest(value: object) -> str:
    return canonical_hash({"schema": SCHEMA, "payload": value})


@dataclass(frozen=True)
class SyntheticCustomer:
    persona: str
    customer_id: str
    business_unit: str
    carrier_id: str
    currency: str
    mode: str


@dataclass(frozen=True)
class StressPlan:
    ordinal: int
    seed: int
    customer: SyntheticCustomer
    scenario: RecoveryScenario
    events: tuple[RecoveryEvent, ...]
    requests: tuple[CustomerRequest, ...]
    assumptions: FeasibilityAssumptions
    credit_mode: str
    as_of: str
    input_sha256: str


@dataclass(frozen=True)
class ReplayOracle:
    settlement_credit_cents: int
    settled_net_cents: int
    reversed_cents: int
    pending_return_cents: int
    fee_base_cents: int
    claim_residual_cents: int


@dataclass(frozen=True)
class CaseReceipt:
    case_id: str
    ordinal: int
    input_sha256: str
    prediction_state: str
    recovery_report_hash: str
    settlement_snapshot_sha256: str | None
    source_declared_net_cents: int
    unverified_return_cents: int
    no_external_actions: bool
    customer_fee_billable_cents: int
    independent_cash_verified_cents: int
    case_receipt_sha256: str


def make_plan(i: int, *, seed: int = SEED) -> StressPlan:
    if type(i) is not int or i < 0 or i > 100000:
        raise ValueError("scenario ordinal out of bounds")
    if type(seed) is not int or not 0 <= seed < 2**31:
        raise ValueError("scenario seed must be integer")
    rng = random.Random(seed + i * 7919)
    persona = PERSONAS[i % len(PERSONAS)]
    currency = CURRENCIES[(i // (len(PERSONAS) * len(MODES)) + i // 2) % len(CURRENCIES)]
    customer = SyntheticCustomer(
        persona, f"SYN-CLIENT-{i:05d}", f"SYN-UNIT-{i % 9}",
        f"SYN-CARRIER-{(i * 7) % 13}", currency, MODES[(i // len(PERSONAS) + i) % len(MODES)],
    )
    disputed = rng.randint(10_000, 5_000_000)
    scenario = RecoveryScenario(
        case_id=f"SYN-CASE-{i:05d}", claim_id=f"SYN-CLAIM-{i:05d}",
        buyer_id=customer.customer_id, business_unit=customer.business_unit,
        payer_id=customer.carrier_id, payee_id=customer.customer_id,
        currency=currency, disputed_cents=disputed, issued_at=ISSUED,
        source_invoice_sha256=h(f"ORIGINAL-INVOICE-{seed}-{i}"),
        source_finding_sha256=h(f"HYPOTHETICAL-FINDING-{seed}-{i}"),
    )
    kinds = EVENT_COMBINATIONS[(i // len(PERSONAS) + i * 5) % len(EVENT_COMBINATIONS)]
    events = []
    for j, kind in enumerate(kinds):
        offer = min(disputed, rng.randint(1, disputed)) if kind in (
            "PARTIAL_OFFER", "ACCOUNT_CREDIT_OFFER",
        ) else None
        ref = events[-1].event_id if kind == "APPEAL_PREPARED" else None
        events.append(RecoveryEvent(
            event_id=f"SYN-CARRIER-E-{i:05d}-{j}",
            kind=kind,
            observed_at=OBSERVED_ONE if j == 0 else OBSERVED_TWO,
            source_sha256=h(f"CARRIER-DECLARATION-{seed}-{i}-{j}"),
            amount_cents=offer, ref_event_id=ref,
        ))
    requests = []
    for j, kind in enumerate(REQUEST_COMBINATIONS[(i // len(PERSONAS) * 7 + i * 3) % len(REQUEST_COMBINATIONS)]):
        requests.append(CustomerRequest(
            request_id=f"SYN-BUYER-R-{i:05d}-{j}",
            kind=kind,
            requested_at=REQUEST_TIME,
            source_sha256=h(f"BUYER-DECLARATION-{seed}-{i}-{j}"),
            requested_payee_id=f"SYN-AFFILIATE-{i:05d}" if kind in (
                "PAY_AFFILIATE", "NEW_PAYEE",
            ) else None,
        ))
    assumptions = FeasibilityAssumptions(
        modeled_collection_probability_bps=(
            None if i % 5 == 0 else rng.randint(0, 10000)
        ),
        modeled_fee_rate_bps=3000,  # Hypothetical rate, not a contract.
        labor_hours=rng.randint(2, 160),
        cost_per_hour_cents=rng.randint(1800, 14000),
        other_delivery_cost_cents=rng.randint(0, 25000),
        expected_delay_days=rng.choice((0, 90, 180, 365, 730)),
        target_response_days=rng.choice((7, 15, 30, 60, 120)),
    )
    mode = CREDIT_MODES[(i // 3) % len(CREDIT_MODES)]
    body = {
        "ordinal": i, "seed": seed, "customer": asdict(customer),
        "scenario": asdict(scenario),
        "events": [asdict(e) for e in events],
        "requests": [asdict(q) for q in requests],
        "assumptions": asdict(assumptions),
        "credit_mode": mode, "as_of": AS_OF,
    }
    return StressPlan(
        i, seed, customer, scenario, tuple(events), tuple(requests),
        assumptions, mode, AS_OF, digest(body),
    )


def _assert_plan_integrity(plan: StressPlan) -> None:
    if not isinstance(plan, StressPlan):
        raise ValueError("typed immutable plan required")
    expected = make_plan(plan.ordinal, seed=plan.seed)
    if plan != expected:
        raise ValueError("scenario plan differs from original seeded fixture")
    if plan.customer.currency != plan.scenario.currency:
        raise ValueError("customer/scenario currency mismatch")


def _credit_parts(plan: StressPlan) -> tuple[int, ...]:
    amount = plan.scenario.disputed_cents
    mode = plan.credit_mode
    if mode == "NO_SETTLEMENT":
        return ()
    if mode == "FULL_CREDIT":
        return (amount,)
    if mode == "SPLIT_CREDITS":
        a = max(1, amount // 3)
        return (a, amount - a)
    half = max(1, amount // 2)
    if mode == "REPLAY_STORM":
        return (half,)
    if mode in {"PARTIAL_CREDIT", "PARTIAL_REVERSAL", "PENDING_RETURN", "FULL_REVERSAL"}:
        return (half,)
    raise ValueError("unrecognized credit pattern")


def independent_oracle(plan: StressPlan) -> ReplayOracle:
    """Calculate cash-conservation expectations from inputs, not engine output."""
    _assert_plan_integrity(plan)
    credits = _credit_parts(plan)
    credit = sum(credits)
    reversed_cents = 0
    pending = 0
    if plan.credit_mode == "PARTIAL_REVERSAL":
        reversed_cents = max(1, credits[0] // 2)
    if plan.credit_mode == "FULL_REVERSAL":
        reversed_cents = credits[0]
    if plan.credit_mode == "PENDING_RETURN":
        pending = max(1, credits[0] // 2)
    net = credit - reversed_cents
    # Alternate between first-party and incumbent/disqualified fee bases.
    disqualified = plan.ordinal % 11 == 0
    return ReplayOracle(
        credit, net, reversed_cents, pending,
        # Independently hold the fee base when an event-level source return
        # is registered but not yet fully applied. Do not infer bank cash or
        # split a pending source return arbitrarily across claim allocations.
        0 if disqualified or pending else net,
        plan.scenario.disputed_cents - net,
    )


def expected_state(plan: StressPlan, oracle: ReplayOracle) -> str:
    """Independent state oracle from source events, requests and ledger inputs."""
    types = {x.kind for x in plan.events}
    requests = {x.kind for x in plan.requests}
    if types & {"INSOLVENCY_NOTICE", "CARRIER_OUT_OF_BUSINESS"}:
        return "INSOLVENCY_LEGAL_HOLD"
    if "CLAIM_TIME_BAR_CONCERN" in types:
        return "CONTRACTUAL_TIME_BAR_REVIEW_HOLD"
    if "CUSTOMER_WITHDRAWAL" in types or "WITHDRAW_CASE" in requests:
        return "CUSTOMER_WITHDRAWAL_REVIEW_HOLD"
    if types & {"CARRIER_DISPUTE", "CARRIER_DENIAL", "CUSTOMER_DISPUTE"}:
        return "DISPUTED_EVIDENCE_HOLD"
    if oracle.pending_return_cents or "PAYMENT_REVERSAL_NOTICE" in types:
        return "RETURN_REVERSAL_REVIEW_HOLD"
    if requests & {"DELETE_ALL_EVIDENCE", "RETENTION_EXCEPTION"}:
        return "RETENTION_PRIVACY_REVIEW_HOLD"
    if oracle.settled_net_cents == plan.scenario.disputed_cents:
        return "SOURCE_DECLARED_FULLY_SETTLED_UNVERIFIED"
    if oracle.settled_net_cents:
        return "SOURCE_DECLARED_PARTIALLY_SETTLED_UNVERIFIED"
    if types & {"PARTIAL_OFFER", "ACCOUNT_CREDIT_OFFER"}:
        return "UNVERIFIED_CARRIER_OFFER_REVIEW"
    if "DELAY_NOTICE" in types or plan.as_of >= "2026-12-31":
        return "DELAY_AND_AGING_REVIEW_HOLD"
    return "AWAITING_SOURCE_EVIDENCE_REVIEW"


def _reopened_store(path: Path, plan: StressPlan) -> SettlementStore:
    return SettlementStore(
        path, buyer_id=plan.scenario.buyer_id,
        business_unit=plan.scenario.business_unit,
    )


def execute_case(plan: StressPlan, *, root: Path) -> tuple[RecoveryScenarioResult, ReplayOracle]:
    """Drive the actual SQLite lifecycle; isolate case data and test crash reopens."""
    _assert_plan_integrity(plan)
    oracle = independent_oracle(plan)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"p4-case-{plan.ordinal:05d}.sqlite3"
    if path.exists():
        raise ValueError("refusing a prior case database; one run one custody root")
    store = _reopened_store(path, plan)
    sc = plan.scenario
    claim = RecoveryClaim(
        sc.claim_id, sc.case_id, sc.payer_id, sc.payee_id, sc.currency,
        sc.disputed_cents, sc.issued_at, sc.source_finding_sha256,
        plan.ordinal % 11 == 0,
    )
    assert store.create_claim(claim) is True
    assert store.create_claim(claim) is False  # exact claim replay is inert
    parts = _credit_parts(plan)
    for j, amount in enumerate(parts):
        event_id = f"SYN-CREDIT-{plan.ordinal:05d}-{j}"
        source = SettlementEventRecord(
            event_id, sc.case_id, sc.payer_id, sc.payee_id, sc.currency,
            amount, "2026-09-20T12:00:00Z",
            h(f"CREDIT-{plan.seed}-{plan.ordinal}-{j}"),
            "SYNTHETIC_CARRIER_CREDIT_NOT_BANK_CLEARED",
        )
        store = _reopened_store(path, plan)  # simulate restart before ingest
        assert store.ingest_event(source) is True
        assert store.ingest_event(source) is False
        created = store.review_allocate(
            allocation_id=f"SYN-ALLOCATION-{plan.ordinal:05d}-{j}",
            claim_id=sc.claim_id, event_id=event_id,
            amount_cents=amount, created_at="2026-09-21T12:00:00Z",
        )
        assert created == ALLOCATED
        # Repeating the same instruction after a restart cannot add a credit.
        store = _reopened_store(path, plan)
        assert store.review_allocate(
            allocation_id=f"SYN-ALLOCATION-{plan.ordinal:05d}-{j}",
            claim_id=sc.claim_id, event_id=event_id,
            amount_cents=amount, created_at="2026-09-21T12:00:00Z",
        ) == ALREADY_ALLOCATED
    mode = plan.credit_mode
    if mode in {"PARTIAL_REVERSAL", "FULL_REVERSAL", "PENDING_RETURN"}:
        ret = oracle.reversed_cents or oracle.pending_return_cents
        counter_id = f"SYN-RETURN-{plan.ordinal:05d}"
        assert store.ingest_counter(CounterEventRecord(
            counter_id, f"SYN-CREDIT-{plan.ordinal:05d}-0",
            sc.currency, ret, "2026-09-25T12:00:00Z",
            h(f"RETURN-{plan.seed}-{plan.ordinal}"),
            "SYNTHETIC_RETURN_NOT_BANK_CLEARED",
        )) is True
        if mode != "PENDING_RETURN":
            assert store.auto_apply_counter(
                counter_id, created_at="2026-09-26T12:00:00Z",
            ).status == REVERSED
    store = _reopened_store(path, plan)
    before = store.report_snapshot_json()
    result = evaluate_recovery_scenario(
        sc, events=plan.events, customer_requests=plan.requests,
        assumptions=plan.assumptions, as_of=plan.as_of, store=store,
    )
    after = store.report_snapshot_json()
    if before != after:
        raise AssertionError("read-only auditor mutated financial source")
    assert_independent_invariants(plan, result, oracle)
    return result, oracle


def assert_independent_invariants(
    plan: StressPlan,
    result: RecoveryScenarioResult,
    oracle: ReplayOracle,
) -> None:
    """Independent expected ledger amounts and no-commercial-action oracle.

    Also used as a mutation detector: tampered fields must fail assertions.
    """
    _assert_plan_integrity(plan)
    if type(result) is not RecoveryScenarioResult or type(oracle) is not ReplayOracle:
        raise AssertionError("invalid typed financial evidence receipt")
    if result.case_id != plan.scenario.case_id:
        raise AssertionError("wrong customer's recovery case")
    if result.state != expected_state(plan, oracle):
        raise AssertionError("complex recovery state differs from independent oracle")
    observed = result.settlement
    expected = (
        oracle.settlement_credit_cents, oracle.settled_net_cents,
        oracle.reversed_cents, oracle.pending_return_cents,
        oracle.fee_base_cents, oracle.claim_residual_cents,
    )
    got = (
        observed.source_declared_allocated_cents,
        observed.source_declared_net_cents,
        observed.source_declared_reversed_cents,
        observed.outstanding_return_cents,
        observed.source_declared_candidate_fee_cents,
        observed.unallocated_claim_residual_cents,
    )
    if got != expected:
        raise AssertionError("independent monetary conservation oracle mismatch")
    if (result.externally_approved_case or result.carrier_contact_attempts
            or result.payment_actions_performed or result.independently_verified_cash_cents
            or result.customer_fee_billable_cents
            or observed.real_recovered_cash_cents
            or observed.source_authenticated_payment_cents):
        raise AssertionError("fabricated customer authority or real cash")
    if not result.feasibility.no_billable_fee_authority:
        raise AssertionError("unverified fee quote promoted to billable cash")
    if result.feasibility.probabilities_empirically_calibrated:
        raise AssertionError("synthetic probability represented as calibrated")
    if (len(result.customer_request_triage) != len(plan.requests)
            or result.requests_seen != len(plan.requests)
            or result.events_seen != len(plan.events)):
        raise AssertionError("source events or customer requests dropped")
    if any(not x.no_external_action or not x.no_money_movement
           for x in result.customer_request_triage):
        raise AssertionError("external action slipped through customer request gate")
    if (not result.report_hash or len(result.report_hash) != 64
            or not observed.snapshot_sha256):
        raise AssertionError("incomplete source-bound receipt")


def _assert_safe_receipt_result(result: RecoveryScenarioResult) -> None:
    """A receipt cannot certify prohibited financial/customer assertions.

    The original stress oracle guards ordinary execute_case(), but the public
    receipt creator and verifier also need independent fail-closed checks:
    callers must not be able to bypass the oracle by minting a new receipt.
    """
    if not isinstance(result, RecoveryScenarioResult):
        raise AssertionError("typed recovery result required for synthetic receipt")
    if (result.externally_approved_case or result.carrier_contact_attempts
            or result.payment_actions_performed or result.independently_verified_cash_cents
            or result.customer_fee_billable_cents
            or result.settlement.real_recovered_cash_cents
            or result.settlement.source_authenticated_payment_cents
            or result.feasibility.probabilities_empirically_calibrated
            or not result.feasibility.no_billable_fee_authority):
        raise AssertionError("financial actions, fees, verified cash or approvals forbidden in synthetic receipt")
    if any(not t.no_external_action or not t.no_money_movement
           for t in result.customer_request_triage):
        raise AssertionError("synthetic receipt contains executable customer request")
    if not result.report_hash or len(result.report_hash) != 64:
        raise AssertionError("synthetic receipt lacks a valid source hash")


def case_receipt(plan: StressPlan, result: RecoveryScenarioResult) -> CaseReceipt:
    _assert_plan_integrity(plan)
    _assert_safe_receipt_result(result)
    fields = {
        "case_id": result.case_id,
        "ordinal": plan.ordinal,
        "input": plan.input_sha256,
        "state": result.state,
        "report": result.report_hash,
        "snapshot": result.settlement.snapshot_sha256,
        "net": result.settlement.source_declared_net_cents,
        "unapplied_return": result.settlement.outstanding_return_cents,
        "external_actions": result.carrier_contact_attempts + result.payment_actions_performed,
        "billable_fee": result.customer_fee_billable_cents,
        "verified_cash": result.independently_verified_cash_cents,
    }
    return CaseReceipt(
        result.case_id, plan.ordinal, plan.input_sha256, result.state,
        result.report_hash, result.settlement.snapshot_sha256,
        result.settlement.source_declared_net_cents,
        result.settlement.outstanding_return_cents,
        True, 0, 0, digest(fields),
    )


def verify_receipt(plan: StressPlan, result: RecoveryScenarioResult, receipt: CaseReceipt) -> None:
    _assert_safe_receipt_result(result)
    if not isinstance(receipt, CaseReceipt) or receipt != case_receipt(plan, result):
        raise AssertionError("tampered/replayed stress receipt does not match source inputs")
    if receipt.input_sha256 != plan.input_sha256 or not receipt.no_external_actions:
        raise AssertionError("wrong stress evidence or real financial action")
