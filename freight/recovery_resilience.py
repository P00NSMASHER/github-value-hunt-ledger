"""Synthetic-only difficult freight recovery decision and feasibility engine.

This is a read-only overlay for the immutable SettlementStore. It never
creates claims, contacts a carrier, sends payment instructions, alters money,
assumes customer permission, signs a contract, or adjudicates freight errors.

Every supposed external occurrence is a *source-declared event* and remains
UNKNOWN until independently authenticated outside this module. A hash, role,
status string or internal approval cannot establish a real bank receipt.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Iterable
import json
import re

from freight.contracts import canonical_hash
from freight.financial_assurance import (
    require_cent_currency, require_exact_cents, canonical_timestamp,
)
from freight.settlement_store import SettlementStore


SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
EVENT_KINDS = frozenset({
    "CARRIER_DISPUTE", "CARRIER_DENIAL", "INSOLVENCY_NOTICE",
    "DELAY_NOTICE", "PARTIAL_OFFER", "ACCOUNT_CREDIT_OFFER",
    "CARRIER_APPEAL_RESPONSE", "APPEAL_PREPARED",
    "CUSTOMER_DISPUTE", "CUSTOMER_WITHDRAWAL",
    "PAYMENT_REVERSAL_NOTICE", "CARRIER_EVIDENCE_REQUEST",
    "CARRIER_OUT_OF_BUSINESS", "CLAIM_TIME_BAR_CONCERN",
})
REQUEST_KINDS = frozenset({
    "GUARANTEED_RECOVERY", "IMMEDIATE_SETTLEMENT", "PAY_AFFILIATE",
    "NEW_PAYEE", "CROSS_TENANT_MERGE", "CUSTOMER_DATA_EXPORT",
    "DELETE_ALL_EVIDENCE", "RETENTION_EXCEPTION", "FEE_WAIVER",
    "DISPUTE_FINDING", "CHANGE_CUSTOMER_SCOPE", "WITHDRAW_CASE",
    "INVOICE_CORRECTION", "SANITIZED_READ_ONLY_SUMMARY",
    "FORCE_RECOVERY_CLAIM", "FAST_TRACK_PROVIDER_PAYMENT",
})
BLOCKING_CARRIER_EVENTS = {
    "CARRIER_DISPUTE", "CARRIER_DENIAL", "INSOLVENCY_NOTICE",
    "CARRIER_OUT_OF_BUSINESS", "CLAIM_TIME_BAR_CONCERN",
    "CUSTOMER_DISPUTE", "CUSTOMER_WITHDRAWAL",
    "PAYMENT_REVERSAL_NOTICE",
}
MONEY_OFFER_KINDS = {"PARTIAL_OFFER", "ACCOUNT_CREDIT_OFFER"}


def _id(name: str, value: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(name + " must be a canonical nonblank string")
    if len(value) > 160 or any(ord(ch) < 32 for ch in value):
        raise ValueError(name + " is not a safe identifier")
    return value


def _sha(name: str, value: str) -> str:
    if not isinstance(value, str) or SHA.fullmatch(value) is None:
        raise ValueError(name + " must be a lowercase SHA-256 digest")
    return value


def _date(name: str, value: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value, re.ASCII):
        raise ValueError(name + " must be a canonical YYYY-MM-DD date")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(name + " is not a real calendar date") from exc
    if result.isoformat() != value:
        raise ValueError(name + " is not canonical")
    return result


@dataclass(frozen=True)
class RecoveryScenario:
    """All IDs/evidence are fixture-scoped. No customer permission is inferred."""
    case_id: str
    buyer_id: str
    business_unit: str
    claim_id: str
    payer_id: str
    payee_id: str
    currency: str
    disputed_cents: int
    issued_at: str
    source_invoice_sha256: str
    source_finding_sha256: str
    simulation_only: bool = True
    expected_settlement_snapshot_sha256: str | None = None

    def __post_init__(self) -> None:
        for name in ("case_id", "buyer_id", "business_unit", "claim_id", "payer_id", "payee_id"):
            _id(name, getattr(self, name))
        require_cent_currency(self.currency)
        require_exact_cents("disputed cents", self.disputed_cents, positive=True)
        _sha("source invoice", self.source_invoice_sha256)
        _sha("source finding", self.source_finding_sha256)
        if self.source_finding_sha256 == self.source_invoice_sha256:
            raise ValueError("original invoice cannot also be independent finding evidence")
        object.__setattr__(self, "issued_at", canonical_timestamp(self.issued_at))
        if self.simulation_only is not True:
            raise ValueError("this model is synthetic-only, not a real-customer recovery service")
        if self.expected_settlement_snapshot_sha256 is not None:
            _sha("expected settlement snapshot", self.expected_settlement_snapshot_sha256)


@dataclass(frozen=True)
class RecoveryEvent:
    """Unverified statement about an event, not a real court/bank assertion."""
    event_id: str
    kind: str
    observed_at: str
    source_sha256: str
    amount_cents: int | None = None
    ref_event_id: str | None = None

    def __post_init__(self) -> None:
        _id("event_id", self.event_id)
        if self.kind not in EVENT_KINDS:
            raise ValueError("unsupported recovery event kind")
        object.__setattr__(self, "observed_at", canonical_timestamp(self.observed_at))
        _sha("event source", self.source_sha256)
        if self.kind in MONEY_OFFER_KINDS:
            require_exact_cents("offer amount", self.amount_cents, positive=True)
        elif self.amount_cents is not None:
            raise ValueError("amount attached to a nonfinancial event")
        if self.ref_event_id is not None:
            _id("ref_event_id", self.ref_event_id)


@dataclass(frozen=True)
class CustomerRequest:
    request_id: str
    kind: str
    requested_at: str
    source_sha256: str
    requested_payee_id: str | None = None

    def __post_init__(self) -> None:
        _id("request id", self.request_id)
        if self.kind not in REQUEST_KINDS:
            raise ValueError("unsupported customer request; human scope clarification required")
        object.__setattr__(self, "requested_at", canonical_timestamp(self.requested_at))
        _sha("customer request source", self.source_sha256)
        if self.requested_payee_id is not None:
            _id("requested payee", self.requested_payee_id)
        if self.kind in {"PAY_AFFILIATE", "NEW_PAYEE"}:
            if self.requested_payee_id is None:
                raise ValueError("payee change requests must identify proposed recipient")
        elif self.requested_payee_id is not None:
            raise ValueError("recipient change requires explicit payee-change request kind")


@dataclass(frozen=True)
class FeasibilityAssumptions:
    """Explicit assumptions, never empirical collection probability."""
    modeled_collection_probability_bps: int | None = None
    modeled_fee_rate_bps: int = 3000
    labor_hours: int = 0
    cost_per_hour_cents: int = 0
    other_delivery_cost_cents: int = 0
    expected_delay_days: int = 0
    target_response_days: int = 30

    def __post_init__(self) -> None:
        for name in ("modeled_collection_probability_bps", "modeled_fee_rate_bps"):
            value = getattr(self, name)
            if value is None and name == "modeled_collection_probability_bps":
                continue
            if type(value) is not int or not 0 <= value <= 10000:
                raise ValueError(name + " must be explicit integer basis points 0..10000")
        for name in ("labor_hours", "cost_per_hour_cents", "other_delivery_cost_cents"):
            require_exact_cents(name, getattr(self, name))
        if self.labor_hours > 1000000:
            raise ValueError("labor hours exceed bounded scenario limits")
        if (self.labor_hours and self.cost_per_hour_cents == 0):
            raise ValueError("labor has to include a positive loaded hourly cost")
        if type(self.expected_delay_days) is not int or not 0 <= self.expected_delay_days <= 3650:
            raise ValueError("delay assumptions must be bounded calendar days")
        if type(self.target_response_days) is not int or not 1 <= self.target_response_days <= 366:
            raise ValueError("response target must be a bounded planning threshold")


@dataclass(frozen=True)
class RequestTriage:
    request_id: str
    kind: str
    decision: str
    blocker: str | None
    no_external_action: bool
    no_money_movement: bool
    request_hash: str


@dataclass(frozen=True)
class SettlementObservation:
    snapshot_sha256: str | None
    source_declared_allocated_cents: int
    source_declared_reversed_cents: int
    source_declared_net_cents: int
    source_declared_candidate_fee_cents: int
    outstanding_return_cents: int
    unallocated_claim_residual_cents: int
    source_authenticated_payment_cents: int = 0
    real_recovered_cash_cents: int = 0
    fee_disqualified: bool = False
    dispute_hold_active: bool = False
    # Shared-event returns have no defensible per-claim amount allocation.
    # Expose hash references only; the globally counted amount is available
    # exactly once from the currency-partitioned settlement report.
    unattributed_shared_return_event_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class FeasibilityResult:
    probabilities_empirically_calibrated: bool
    assumption_probability_bps: int | None
    modeled_collectible_cents: int | None
    modeled_contingency_fee_cents: int | None
    modeled_delivery_cost_cents: int
    modeled_net_fee_after_cost_cents: int | None
    economic_route: str
    no_billable_fee_authority: bool
    result_hash: str


@dataclass(frozen=True)
class RecoveryScenarioResult:
    case_id: str
    state: str
    blockers: tuple[str, ...]
    events_seen: int
    requests_seen: int
    last_observed_event_at: str | None
    days_since_claim: int
    overdue_response_days: int
    evidence_hash: str
    settlement: SettlementObservation
    feasibility: FeasibilityResult
    customer_request_triage: tuple[RequestTriage, ...]
    next_safe_actions: tuple[str, ...]
    externally_approved_case: bool
    carrier_contact_attempts: int
    payment_actions_performed: int
    independently_verified_cash_cents: int
    customer_fee_billable_cents: int
    report_hash: str


def _settlement_read_only(
    scenario: RecoveryScenario,
    store: SettlementStore | None,
) -> SettlementObservation:
    if store is None:
        if scenario.expected_settlement_snapshot_sha256 is not None:
            raise ValueError("a pinned settlement snapshot requires the actual isolated store")
        return SettlementObservation(None, 0, 0, 0, 0, 0, scenario.disputed_cents)
    if not isinstance(store, SettlementStore):
        raise ValueError("read-only settlement interface requires a SettlementStore")
    if (store.buyer_id, store.business_unit) != (scenario.buyer_id, scenario.business_unit):
        raise ValueError("settlement store customer scope mismatch")
    # The store produces a read-transaction snapshot, without mutating cash
    # records. This includes all relevant allocations and reversal counters.
    data = json.loads(store.report_snapshot_json())
    if (data.get("buyer_id"), data.get("business_unit")) != (
        scenario.buyer_id, scenario.business_unit
    ):
        raise ValueError("settlement read snapshot has inconsistent customer identity")
    snapshot_sha = canonical_hash(data)
    if (scenario.expected_settlement_snapshot_sha256 is not None and
        scenario.expected_settlement_snapshot_sha256 != snapshot_sha):
        raise ValueError("underlying settlement snapshot changed; start a new review")
    tables = data["tables"]
    claims = [c for c in tables["recovery_claims"] if c["claim_id"] == scenario.claim_id]
    if len(claims) != 1:
        raise ValueError("recovery scenario must bind one existing claim in settlement store")
    claim = claims[0]
    if (claim["reference"], claim["payer_id"], claim["payee_id"], claim["currency"],
        claim["amount_cents"], claim["issued_at"], claim["source_hash"]) != (
        scenario.case_id, scenario.payer_id, scenario.payee_id,
        scenario.currency, scenario.disputed_cents,
        scenario.issued_at, scenario.source_finding_sha256,
    ):
        raise ValueError("settlement claim does not match frozen recovery scenario")
    active_dispute_hold = any(
        x["claim_id"] == scenario.claim_id
        for x in tables.get("claim_dispute_holds", ())
    )
    allocations = [a for a in tables["allocations"] if a["claim_id"] == scenario.claim_id]
    by_event = {e["event_id"]: e for e in tables["settlement_events"]}
    by_alloc = {a["allocation_id"]: a for a in allocations}
    reversal_by_allocation: dict[str, int] = {}
    for edge in tables["reversal_edges"]:
        alloc_id = edge["allocation_id"]
        reversal_by_allocation[alloc_id] = reversal_by_allocation.get(alloc_id, 0) + edge["amount_cents"]
    for edge in tables["reversal_edges"]:
        if edge["allocation_id"] not in by_alloc:
            continue
        if edge["amount_cents"] <= 0:
            raise ValueError("nonpositive reversal in scoped immutable source")
    total = reverted = fee = 0
    linked_event_ids = set()
    for a in allocations:
        e = by_event.get(a["event_id"])
        if e is None:
            raise ValueError("settlement allocation is missing original event")
        if (e["currency"], e["payer_id"], e["payee_id"]) != (
            scenario.currency, scenario.payer_id, scenario.payee_id
        ):
            raise ValueError("settlement allocation has inconsistent payer/payee/currency")
        amount = require_exact_cents("allocated", a["amount_cents"], positive=True)
        reverse = reversal_by_allocation.get(a["allocation_id"], 0)
        if reverse > amount:
            raise ValueError("reversal exceeds claimed allocation")
        eligible = require_exact_cents("fee-base", a["fee_eligible_cents"])
        if eligible not in (0, amount) or (claim["fee_disqualified"] and eligible):
            raise ValueError("source-declared fee eligibility is inconsistent")
        total += amount
        reverted += reverse
        if eligible and not active_dispute_hold:
            fee += amount - reverse
        linked_event_ids.add(a["event_id"])
    if total > scenario.disputed_cents or reverted > total:
        raise ValueError("declared recovery exceeds frozen claim capacity")
    # Unapplied counter-events may still reverse an allocation. HOLD the
    # candidate amount; they must never quietly count as settled cash.
    pending = 0
    shared_event_return_ids = set()
    for counter in tables["counter_events"]:
        event_id = counter["original_event_id"]
        if event_id not in linked_event_ids:
            continue
        used = sum(x["amount_cents"] for x in tables["reversal_edges"]
                   if x["counter_id"] == counter["counter_id"])
        if used > counter["amount_cents"]:
            raise ValueError("counter evidence was over-consumed")
        residual = counter["amount_cents"] - used
        if not residual:
            continue
        # A counter funds the settlement event, NOT one particular claim. If
        # that event was allocated to multiple claims, showing its full
        # residual within each claim would make aggregate reports overstate
        # a single return. Keep the amount only in event-wide reporting.
        claim_ids = {a["claim_id"] for a in tables["allocations"]
                     if a["event_id"] == event_id}
        if len(claim_ids) > 1:
            shared_event_return_ids.add(canonical_hash({
                "schema": 1, "counter_id": counter["counter_id"],
                "event_id": event_id, "buyer": scenario.buyer_id,
                "business_unit": scenario.business_unit,
            }))
        else:
            pending += residual
    net = total - reverted
    return SettlementObservation(
        snapshot_sha, total, reverted, net,
        fee, pending, scenario.disputed_cents - net,
        0, 0, bool(claim["fee_disqualified"]),
        active_dispute_hold, tuple(sorted(shared_event_return_ids)),
    )


def _request_triage(request: CustomerRequest, scenario: RecoveryScenario) -> RequestTriage:
    if request.kind in {"GUARANTEED_RECOVERY", "FORCE_RECOVERY_CLAIM"}:
        decision, blocker = "DENY_UNSUPPORTED_FINANCIAL_CLAIM", "NO_INDEPENDENT_RECOVERY_PROOF"
    elif request.kind in {"IMMEDIATE_SETTLEMENT", "FAST_TRACK_PROVIDER_PAYMENT"}:
        decision, blocker = "HOLD_FOR_VALID_CUSTOMER_AUTHORIZATION", "NO_PAYMENT_RAILS_OR_VERIFIED_AUTHORITY"
    elif request.kind in {"PAY_AFFILIATE", "NEW_PAYEE"}:
        decision, blocker = "REAUTHORIZE_NEW_VERIFIED_RECIPIENT", "EXISTING_PAYEE_BINDING_NOT_TRANSFERABLE"
    elif request.kind == "CROSS_TENANT_MERGE":
        decision, blocker = "DENY_CROSS_CUSTOMER_ACCESS", "SEPARATE_TENANT_SCOPES_REQUIRED"
    elif request.kind in {"DELETE_ALL_EVIDENCE", "RETENTION_EXCEPTION"}:
        decision, blocker = "PRIVACY_AND_RETENTION_LEGAL_HOLD", "LAWFUL_RETENTION_AND_DELETION_DUTIES_UNVERIFIED"
    elif request.kind in {"CUSTOMER_DATA_EXPORT", "INVOICE_CORRECTION"}:
        decision, blocker = "REQUIRE_PRIVATE_RIGHTS_REVIEW", "CUSTOMER_DATA_RIGHTS_NOT_ESTABLISHED"
    elif request.kind == "FEE_WAIVER":
        decision, blocker = "COMMERCIAL_TERMS_REVIEW_ONLY", "NO_AUTHENTICATED_FEE_AMENDMENT"
    elif request.kind == "DISPUTE_FINDING":
        decision, blocker = "SUSPEND_FINDING_FOR_SOURCE_ADJUDICATION", "CUSTOMER_DISPUTE_REVIEW_PENDING"
    elif request.kind == "CHANGE_CUSTOMER_SCOPE":
        decision, blocker = "REJECT_SCOPE_REUSE_AND_RESTART", "NEW_CUSTOMER_IDENTITY_REQUIRES_NEW_CASE"
    elif request.kind == "WITHDRAW_CASE":
        decision, blocker = "HOLD_CLAIM_FOR_AUTHENTICATED_WITHDRAWAL", "AUTHENTICATED_CUSTOMER_INSTRUCTION_MISSING"
    elif request.kind == "SANITIZED_READ_ONLY_SUMMARY":
        decision, blocker = "PREVIEW_NONCUSTOMER_SYNTHETIC_SUMMARY", None
    else:
        raise ValueError("unsupported request type")
    body = {
        "schema": 1, "request": asdict(request), "scenario": scenario.case_id,
        "decision": decision, "blocker": blocker, "no_external_action": True,
    }
    return RequestTriage(request.request_id, request.kind, decision, blocker,
                         True, True, canonical_hash(body))


def _feasibility(
    amount: int,
    inputs: FeasibilityAssumptions,
    *,
    financial_blockers: set[str],
    fee_disqualified: bool,
) -> FeasibilityResult:
    """Planning what-if, never a charge or calibrated recovery forecast."""
    costs = inputs.labor_hours * inputs.cost_per_hour_cents + inputs.other_delivery_cost_cents
    if costs > 2**63 - 1:
        raise ValueError("labor and delivery costs overflow exact cents")
    probability = inputs.modeled_collection_probability_bps
    if probability is None:
        modeled_gross = modeled_fee = modeled_net = None
        route = "PROBABILITY_NOT_ESTABLISHED"
    else:
        modeled_gross = amount * probability // 10000
        modeled_fee = 0 if fee_disqualified else modeled_gross * inputs.modeled_fee_rate_bps // 10000
        modeled_net = modeled_fee - costs
        route = "ECONOMIC_REVIEW_CANDIDATE" if modeled_net > 0 else "ECONOMIC_HOLD_NEGATIVE_OR_ZERO"
    if financial_blockers:
        route = "SOURCE_OR_DISPUTE_HOLD" if route == "ECONOMIC_REVIEW_CANDIDATE" else route
    body = {
        "schema": 1, "assumptions": asdict(inputs), "denominator": amount,
        "modeled_gross": modeled_gross, "modeled_fee": modeled_fee,
        "modeled_net": modeled_net, "costs": costs, "route": route,
        "fee_disqualified": fee_disqualified,
        "billable": 0, "externally_calibrated": False,
    }
    return FeasibilityResult(False, probability, modeled_gross, modeled_fee,
                             costs, modeled_net, route, True, canonical_hash(body))


def evaluate_recovery_scenario(
    scenario: RecoveryScenario,
    *,
    events: Iterable[RecoveryEvent] = (),
    customer_requests: Iterable[CustomerRequest] = (),
    assumptions: FeasibilityAssumptions | None = None,
    as_of: str,
    store: SettlementStore | None = None,
) -> RecoveryScenarioResult:
    """Run actual scoped settlement accounting then classify safely, read-only."""
    if not isinstance(scenario, RecoveryScenario):
        raise ValueError("typed recovery scenario required")
    today = _date("as_of", as_of)
    issued = datetime.fromisoformat(scenario.issued_at.replace("Z", "+00:00")).date()
    if today < issued:
        raise ValueError("scenario evaluation cannot precede claim issuance")
    event_list = tuple(events)
    request_list = tuple(customer_requests)
    if not all(type(x) is RecoveryEvent for x in event_list):
        raise ValueError("event list requires typed RecoveryEvent records")
    if not all(type(x) is CustomerRequest for x in request_list):
        raise ValueError("request list requires typed CustomerRequest records")
    ids = [x.event_id for x in event_list] + [x.request_id for x in request_list]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate event/request id in one scenario")
    original_sources = {scenario.source_invoice_sha256, scenario.source_finding_sha256}
    hashes = [x.source_sha256 for x in (*event_list, *request_list)]
    if len(hashes) != len(set(hashes)) or any(x in original_sources for x in hashes):
        raise ValueError("reused or nonindependent event/approval source proof")
    for event in event_list:
        observed = datetime.fromisoformat(event.observed_at.replace("Z", "+00:00")).date()
        if observed < issued or observed > today:
            raise ValueError("recovery event chronology out of claim/evaluation bounds")
        if event.kind in MONEY_OFFER_KINDS and event.amount_cents > scenario.disputed_cents:
            raise ValueError("offered value exceeds original disputed claim")
    for request in request_list:
        observed = datetime.fromisoformat(request.requested_at.replace("Z", "+00:00")).date()
        if observed < issued or observed > today:
            raise ValueError("customer request chronology out of bounds")
    by_id = {e.event_id: e for e in event_list}
    for event in event_list:
        if event.kind == "APPEAL_PREPARED":
            predecessor = by_id.get(event.ref_event_id)
            if (predecessor is None or predecessor.kind not in {"CARRIER_DISPUTE", "CARRIER_DENIAL"}
                    or predecessor.observed_at > event.observed_at):
                raise ValueError("appeal without earlier disputed/denied claim")
        elif event.ref_event_id is not None and event.ref_event_id not in by_id:
            raise ValueError("recovery event links to unknown earlier evidence")
        if event.ref_event_id == event.event_id:
            raise ValueError("recovery event cannot refer to itself")
    sorted_events = tuple(sorted(event_list, key=lambda x: (x.observed_at, x.event_id)))
    sorted_requests = tuple(sorted(request_list, key=lambda x: (x.requested_at, x.request_id)))
    evidence = canonical_hash({
        "schema": 1,
        "case": asdict(scenario),
        "events": [asdict(x) for x in sorted_events],
        "requests": [asdict(x) for x in sorted_requests],
        "as_of": as_of,
    })
    settlement = _settlement_read_only(scenario, store)
    assumptions = assumptions or FeasibilityAssumptions()
    if not isinstance(assumptions, FeasibilityAssumptions):
        raise ValueError("typed feasibility assumptions required")
    triage = tuple(_request_triage(x, scenario) for x in sorted_requests)
    kinds = {e.kind for e in event_list}
    request_kinds = {r.kind for r in request_list}
    blockers = {
        "NO_INDEPENDENT_FREIGHT_ADJUDICATION",
        "NO_VERIFIED_CUSTOMER_RECOVERY_CONSENT",
        "SETTLEMENT_PROVIDER_OR_BANK_AUTHENTICATION_MISSING",
        "NO_ACTUAL_RECOVERY_OR_FEE_AUTHORITY",
    }
    for t in triage:
        if t.blocker:
            blockers.add(t.blocker)
    if settlement.dispute_hold_active:
        blockers.add("DURABLE_DISPUTE_HOLD_FORBIDS_VALIDATED_RECOVERY_AND_FEE")
    if settlement.outstanding_return_cents:
        blockers.add("UNAPPLIED_RETURN_COULD_CHANGE_DECLARED_RECOVERY")
    if settlement.unattributed_shared_return_event_ids:
        blockers.add("SHARED_EVENT_RETURN_REQUIRES_NONADDITIVE_ALLOCATION_REVIEW")
    if any(e.kind in {"INSOLVENCY_NOTICE", "CARRIER_OUT_OF_BUSINESS"} for e in event_list):
        blockers.add("INSOLVENCY_OR_NONPAYMENT_LEGAL_REVIEW")
    if "CLAIM_TIME_BAR_CONCERN" in kinds:
        blockers.add("POTENTIAL_FILING_OR_CONTRACTUAL_DEADLINE_REVIEW")
    if "CARRIER_DENIAL" in kinds or "CARRIER_DISPUTE" in kinds:
        blockers.add("CARRIER_DISPUTE_AWAITING_ADJUDICATION")
    if "CUSTOMER_DISPUTE" in kinds:
        blockers.add("BUYER_DISPUTED_ORIGINAL_FINDING")
    if "CUSTOMER_WITHDRAWAL" in kinds:
        blockers.add("BUYER_WITHDRAWAL_NEEDS_AUTHENTICATED_DIRECTIVE")
    if "PAYMENT_REVERSAL_NOTICE" in kinds:
        blockers.add("SOURCE_DECLARED_REVERSAL_AWAITING_ALLOCATION_PROOF")
    if "CARRIER_EVIDENCE_REQUEST" in kinds:
        blockers.add("CARRIER_SUPPORTING_EVIDENCE_REQUESTED")
    if "DELAY_NOTICE" in kinds:
        blockers.add("CARRIER_DELAY_NOTICE_NOT_VERIFIED")
    if "FEE_WAIVER" in request_kinds:
        blockers.add("CUSTOMER_FEE_AMENDMENT_PENDING")
    if "DISPUTE_FINDING" in request_kinds:
        blockers.add("CUSTOMER_FINDING_REVIEW_PENDING")
    overdue = max((today - issued).days - assumptions.target_response_days, 0)
    if overdue:
        blockers.add("PLANNING_RESPONSE_TARGET_EXCEEDED_NOT_LEGAL_DEADLINE")
    if any(x.kind in MONEY_OFFER_KINDS for x in event_list):
        blockers.add("UNVERIFIED_OFFER_NOT_REAL_SETTLEMENT")
    feasible_remaining = max(scenario.disputed_cents - settlement.source_declared_net_cents, 0)
    result = _feasibility(
        feasible_remaining, assumptions, financial_blockers=blockers,
        fee_disqualified=settlement.fee_disqualified or settlement.dispute_hold_active,
    )
    if "INSOLVENCY_NOTICE" in kinds or "CARRIER_OUT_OF_BUSINESS" in kinds:
        state = "INSOLVENCY_LEGAL_HOLD"
    elif "CLAIM_TIME_BAR_CONCERN" in kinds:
        state = "CONTRACTUAL_TIME_BAR_REVIEW_HOLD"
    elif "CUSTOMER_WITHDRAWAL" in kinds or "WITHDRAW_CASE" in request_kinds:
        state = "CUSTOMER_WITHDRAWAL_REVIEW_HOLD"
    elif (settlement.dispute_hold_active
          or "CARRIER_DISPUTE" in kinds or "CARRIER_DENIAL" in kinds
          or "CUSTOMER_DISPUTE" in kinds):
        state = "DISPUTED_EVIDENCE_HOLD"
    elif (settlement.outstanding_return_cents
          or settlement.unattributed_shared_return_event_ids
          or "PAYMENT_REVERSAL_NOTICE" in kinds):
        state = "RETURN_REVERSAL_REVIEW_HOLD"
    elif "DELETE_ALL_EVIDENCE" in request_kinds or "RETENTION_EXCEPTION" in request_kinds:
        state = "RETENTION_PRIVACY_REVIEW_HOLD"
    elif settlement.source_declared_net_cents == scenario.disputed_cents:
        state = "SOURCE_DECLARED_FULLY_SETTLED_UNVERIFIED"
    elif settlement.source_declared_net_cents > 0:
        state = "SOURCE_DECLARED_PARTIALLY_SETTLED_UNVERIFIED"
    elif any(x.kind in MONEY_OFFER_KINDS for x in event_list):
        state = "UNVERIFIED_CARRIER_OFFER_REVIEW"
    elif "DELAY_NOTICE" in kinds or overdue:
        state = "DELAY_AND_AGING_REVIEW_HOLD"
    else:
        state = "AWAITING_SOURCE_EVIDENCE_REVIEW"
    actions = {"REVIEW_READ_ONLY_EVIDENCE_CUSTODY", "PRESERVE_ORIGINAL_CUSTOMER_APPROVAL_GATES"}
    if overdue:
        actions.add("VERIFY_APPLICABLE_DEADLINE_WITH_AUTHORIZED_RIGHTS_REVIEW")
    if "CARRIER_DISPUTE" in kinds or "CARRIER_DENIAL" in kinds:
        actions.add("PREPARE_PRIVATE_DISPUTE_EVIDENCE_FOR_AUTHORIZED_REVIEW")
    if "INSOLVENCY_NOTICE" in kinds or "CARRIER_OUT_OF_BUSINESS" in kinds:
        actions.add("REFER_TO_AUTHORIZED_INSOLVENCY_AND_CONTRACT_COUNSEL")
    if "FEE_WAIVER" in request_kinds:
        actions.add("REVIEW_CONTRACT_AMENDMENT_WITH_PROPER_COMMERCIAL_AUTHORITY")
    if settlement.outstanding_return_cents or "PAYMENT_REVERSAL_NOTICE" in kinds:
        actions.add("VERIFY_CREDIT_RETURN_AGAINST_INDEPENDENT_SETTLEMENT_SOURCE")
    if request_kinds & {"PAY_AFFILIATE", "NEW_PAYEE"}:
        actions.add("REQUIRE_NEW_INDEPENDENT_PAYEE_IDENTITY_AND_PAYMENT_APPROVAL")
    if request_kinds & {"DELETE_ALL_EVIDENCE", "RETENTION_EXCEPTION"}:
        actions.add("RECONCILE_PRIVACY_DELETION_WITH_APPLICABLE_RETENTION_DUTIES")
    body = {
        "schema": 1, "scenario": asdict(scenario), "evidence": evidence,
        "status": state, "blockers": sorted(blockers),
        # Preserve the exact legacy report digest for cases without any
        # shared event-level return, including the pinned Priority-4 baseline.
        "settlement": {
            k: v for k, v in asdict(settlement).items()
            if (k != "unattributed_shared_return_event_ids"
                or settlement.unattributed_shared_return_event_ids)
            and (k != "dispute_hold_active" or settlement.dispute_hold_active)
        },
        "feasibility": asdict(result),
        "requests": [asdict(r) for r in triage],
        "actions": sorted(actions),
        "verified_cash": 0, "fee_billable": 0, "external_actions": 0,
    }
    return RecoveryScenarioResult(
        scenario.case_id, state, tuple(sorted(blockers)),
        len(sorted_events), len(sorted_requests),
        sorted_events[-1].observed_at if sorted_events else None,
        (today - issued).days, overdue, evidence,
        settlement, result, triage, tuple(sorted(actions)),
        False, 0, 0, 0, 0, canonical_hash(body),
    )


def record_recovery_dispute_notice(
    store: SettlementStore,
    *,
    scenario: RecoveryScenario,
    notice: RecoveryEvent,
) -> bool:
    """Durably register *source-declared* contested recovery before allocation.

    This is the enforced intake entry point; evaluate_recovery_scenario is
    intentionally read-only. A document SHA or textual carrier denial never
    proves customer consent, executed rights or bank-settled funds.
    """
    if not isinstance(store, SettlementStore):
        raise ValueError("dispute source admission requires an isolated settlement store")
    if not isinstance(scenario, RecoveryScenario) or not isinstance(notice, RecoveryEvent):
        raise ValueError("typed bound scenario and dispute notice required")
    if (store.buyer_id, store.business_unit) != (
        scenario.buyer_id, scenario.business_unit
    ):
        raise ValueError("dispute store tenant scope mismatch")
    kinds = {
        "CARRIER_DISPUTE", "CARRIER_DENIAL", "CUSTOMER_DISPUTE",
        "CUSTOMER_WITHDRAWAL", "INSOLVENCY_NOTICE",
        "CARRIER_OUT_OF_BUSINESS", "CLAIM_TIME_BAR_CONCERN",
    }
    if notice.kind not in kinds:
        raise ValueError("not a permitted durable dispute/hold notice")
    if notice.amount_cents is not None:
        raise ValueError("dispute notice cannot invent monetary evidence")
    if notice.source_sha256 in {
        scenario.source_finding_sha256, scenario.source_invoice_sha256
    }:
        raise ValueError("dispute notice must have an independent source")
    claim = next(
        (x for x in json.loads(store.report_snapshot_json())["tables"]["recovery_claims"]
         if x["claim_id"] == scenario.claim_id),
        None,
    )
    if claim is None:
        raise ValueError("unknown recovery claim")
    if (
        claim["reference"],claim["payer_id"],claim["payee_id"],claim["currency"],
        claim["amount_cents"],claim["issued_at"],claim["source_hash"]
    ) != (
        scenario.case_id,scenario.payer_id,scenario.payee_id,scenario.currency,
        scenario.disputed_cents,scenario.issued_at,scenario.source_finding_sha256,
    ):
        raise ValueError("claim source/currency/identity/amount mismatch")
    return store.place_claim_dispute_hold(
        claim_id=scenario.claim_id,
        kind=notice.kind,
        source_hash=notice.source_sha256,
        observed_at=notice.observed_at,
        expected_claim_source_sha256=scenario.source_finding_sha256,
    )
