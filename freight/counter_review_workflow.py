"""Proof-bound reviewed reversal attribution for Freight Recovery.

This workflow is used when a counter-event (return/reversal) cannot be
unambiguously auto-applied across live settlement allocation edges. It creates
an immutable review case from current store evidence, requires a human decision
bound to that exact case, revalidates current state, and then uses the narrow
reviewed-reversal store primitive.

V1 supports one counter-event -> one allocation edge for the full remaining
counter amount. Splitting one counter-event across multiple allocation edges is
not supported here.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from freight.money import format_cents
from freight.contracts import canonical_hash
from freight.settlement_store import (
    ALREADY_REVERSED,
    REVERSED,
    SettlementStore,
)


@dataclass(frozen=True)
class CounterAllocationCandidate:
    allocation_id: str
    claim_id: str
    event_id: str
    allocation_amount_cents: int
    live_cents: int
    fee_eligible_cents: int
    mode: str
    created_at: str
    claim_reference: str
    claim_source_hash: str
    candidate_hash: str


@dataclass(frozen=True)
class CounterReviewCase:
    buyer_id: str
    business_unit: str
    counter_id: str
    original_event_id: str
    currency: str
    counter_amount_cents: int
    counter_residual_cents: int
    observed_at: str
    counter_source_hash: str
    source_kind: str
    original_event_amount_cents: int
    auto_review_reason: str
    live_allocation_count: int
    candidates: tuple[CounterAllocationCandidate, ...]
    case_hash: str


@dataclass(frozen=True)
class CounterReviewDecisionInput:
    case_hash: str
    allocation_id: str
    reviewer_role: str
    reviewed_at: str
    rationale: str


@dataclass(frozen=True)
class CounterReviewReceipt:
    buyer_id: str
    business_unit: str
    case_hash: str
    counter_id: str
    allocation_id: str
    amount_cents: int
    reviewer_role: str
    reviewed_at: str
    rationale: str
    review_hash: str
    reversal_id: str
    reversal_status: str
    store_snapshot_before_hash: str
    store_snapshot_after_hash: str
    receipt_hash: str


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " is required")
    return value.strip()


def _timestamp(name: str, value: str) -> tuple[str, datetime]:
    text = _text(name, value)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(name + " must be timezone-aware ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(name + " must be timezone-aware ISO-8601")
    parsed = parsed.astimezone(timezone.utc)
    return (
        parsed.isoformat(timespec="microseconds").replace("+00:00", "Z"),
        parsed,
    )


def _snapshot(store: SettlementStore) -> dict:
    value = json.loads(store.report_snapshot_json())
    if (value.get("buyer_id"), value.get("business_unit")) != (
        store.buyer_id,
        store.business_unit,
    ):
        raise ValueError("settlement snapshot scope mismatch")
    return value


def _snapshot_hash(snapshot: dict) -> str:
    return canonical_hash(snapshot)


def _reversed_by_allocation(tables: dict) -> dict[str, int]:
    totals: dict[str, int] = {}
    for row in tables["reversal_edges"]:
        allocation_id = row["allocation_id"]
        totals[allocation_id] = totals.get(allocation_id, 0) + int(
            row["amount_cents"]
        )
    return totals


def _build_case_from_snapshot(
    store: SettlementStore,
    *,
    counter_id: str,
    snapshot: dict,
) -> CounterReviewCase:
    counter_id = _text("counter_id", counter_id)
    tables = snapshot["tables"]
    counter = next(
        (row for row in tables["counter_events"] if row["counter_id"] == counter_id),
        None,
    )
    if counter is None:
        raise ValueError("unknown counter event")

    existing_for_counter = [
        row for row in tables["reversal_edges"] if row["counter_id"] == counter_id
    ]
    if existing_for_counter:
        raise ValueError(
            "counter event already has reversal edge; review case is stale"
        )

    event = next(
        (
            row
            for row in tables["settlement_events"]
            if row["event_id"] == counter["original_event_id"]
        ),
        None,
    )
    if event is None:
        raise ValueError("counter references unknown settlement event")
    if event["currency"] != counter["currency"]:
        raise ValueError("counter currency mismatch with original event")

    reversed_by_allocation = _reversed_by_allocation(tables)
    claim_index = {
        row["claim_id"]: row for row in tables["recovery_claims"]
    }

    live_rows: list[tuple[dict, int]] = []
    for allocation in tables["allocations"]:
        if allocation["event_id"] != counter["original_event_id"]:
            continue
        live_cents = int(allocation["amount_cents"]) - int(
            reversed_by_allocation.get(allocation["allocation_id"], 0)
        )
        if live_cents > 0:
            live_rows.append((allocation, live_cents))

    counter_residual = int(counter["amount_cents"])
    if counter_residual <= 0:
        raise ValueError("counter event has no residual amount")

    if not live_rows:
        auto_reason = "original event has no live realized allocation"
    else:
        total_live = sum(live for _allocation, live in live_rows)
        if counter_residual in (int(event["amount_cents"]), total_live):
            raise ValueError(
                "counter event is auto-reversible; manual review is not allowed"
            )
        if len(live_rows) == 1 and counter_residual <= live_rows[0][1]:
            raise ValueError(
                "counter event is auto-reversible; manual review is not allowed"
            )
        auto_reason = "partial return is ambiguous across live allocation edges"

    candidates: list[CounterAllocationCandidate] = []
    for allocation, live_cents in live_rows:
        if live_cents < counter_residual:
            continue
        claim = claim_index.get(allocation["claim_id"])
        if claim is None:
            raise ValueError("allocation references unknown recovery claim")
        body = {
            "schema": 1,
            "counter_id": counter_id,
            "allocation_id": allocation["allocation_id"],
            "claim_id": allocation["claim_id"],
            "event_id": allocation["event_id"],
            "allocation_amount_cents": int(allocation["amount_cents"]),
            "live_cents": live_cents,
            "fee_eligible_cents": int(allocation["fee_eligible_cents"]),
            "mode": allocation["mode"],
            "created_at": allocation["created_at"],
            "claim_reference": claim["reference"],
            "claim_source_hash": claim["source_hash"],
        }
        candidates.append(CounterAllocationCandidate(
            allocation_id=allocation["allocation_id"],
            claim_id=allocation["claim_id"],
            event_id=allocation["event_id"],
            allocation_amount_cents=int(allocation["amount_cents"]),
            live_cents=live_cents,
            fee_eligible_cents=int(allocation["fee_eligible_cents"]),
            mode=allocation["mode"],
            created_at=allocation["created_at"],
            claim_reference=claim["reference"],
            claim_source_hash=claim["source_hash"],
            candidate_hash=canonical_hash(body),
        ))

    candidates_tuple = tuple(sorted(candidates, key=lambda item: item.allocation_id))
    body = {
        "schema": 1,
        "buyer_id": store.buyer_id,
        "business_unit": store.business_unit,
        "counter_id": counter_id,
        "original_event_id": counter["original_event_id"],
        "currency": counter["currency"],
        "counter_amount_cents": int(counter["amount_cents"]),
        "counter_residual_cents": counter_residual,
        "observed_at": counter["observed_at"],
        "counter_source_hash": counter["source_hash"],
        "source_kind": counter["source_kind"],
        "original_event_amount_cents": int(event["amount_cents"]),
        "auto_review_reason": auto_reason,
        "live_allocation_count": len(live_rows),
        "candidates": [asdict(candidate) for candidate in candidates_tuple],
    }
    return CounterReviewCase(
        buyer_id=store.buyer_id,
        business_unit=store.business_unit,
        counter_id=counter_id,
        original_event_id=counter["original_event_id"],
        currency=counter["currency"],
        counter_amount_cents=int(counter["amount_cents"]),
        counter_residual_cents=counter_residual,
        observed_at=counter["observed_at"],
        counter_source_hash=counter["source_hash"],
        source_kind=counter["source_kind"],
        original_event_amount_cents=int(event["amount_cents"]),
        auto_review_reason=auto_reason,
        live_allocation_count=len(live_rows),
        candidates=candidates_tuple,
        case_hash=canonical_hash(body),
    )


def build_counter_review_case(
    store: SettlementStore,
    *,
    counter_id: str,
) -> CounterReviewCase:
    return _build_case_from_snapshot(
        store,
        counter_id=counter_id,
        snapshot=_snapshot(store),
    )


def _canonical_decision(
    case: CounterReviewCase,
    decision: CounterReviewDecisionInput,
) -> tuple[str, datetime, str, str, str, str]:
    if not isinstance(decision, CounterReviewDecisionInput):
        raise ValueError("decision must be a CounterReviewDecisionInput")
    if decision.case_hash != case.case_hash:
        raise ValueError("counter review decision case hash mismatch")
    allocation_id = _text("allocation_id", decision.allocation_id)
    reviewer_role = _text("reviewer_role", decision.reviewer_role)
    reviewed_at, reviewed_dt = _timestamp("reviewed_at", decision.reviewed_at)
    rationale = _text("rationale", decision.rationale)

    observed_dt = datetime.fromisoformat(
        case.observed_at.replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    if reviewed_dt < observed_dt:
        raise ValueError("counter review cannot predate counter observation")

    body = {
        "schema": 1,
        "case_hash": case.case_hash,
        "counter_id": case.counter_id,
        "allocation_id": allocation_id,
        "amount_cents": case.counter_residual_cents,
        "reviewer_role": reviewer_role,
        "reviewed_at": reviewed_at,
        "rationale": rationale,
    }
    review_hash = canonical_hash(body)
    return allocation_id, reviewed_dt, reviewer_role, reviewed_at, rationale, review_hash


def apply_counter_review_decision(
    store: SettlementStore,
    *,
    case: CounterReviewCase,
    decision: CounterReviewDecisionInput,
) -> CounterReviewReceipt:
    (
        allocation_id,
        _reviewed_dt,
        reviewer_role,
        reviewed_at,
        rationale,
        review_hash,
    ) = _canonical_decision(case, decision)
    reversal_id = "review-reversal:" + review_hash
    amount_cents = case.counter_residual_cents

    before = _snapshot(store)
    before_hash = _snapshot_hash(before)

    existing = next(
        (
            row
            for row in before["tables"]["reversal_edges"]
            if row["reversal_id"] == reversal_id
        ),
        None,
    )
    if existing is not None:
        expected = (
            case.counter_id,
            allocation_id,
            amount_cents,
            reviewed_at,
        )
        actual = (
            existing["counter_id"],
            existing["allocation_id"],
            int(existing["amount_cents"]),
            existing["created_at"],
        )
        if actual != expected:
            raise ValueError(
                "review reversal replay conflicts with immutable reversal edge"
            )
        status = ALREADY_REVERSED
        after = before
        after_hash = before_hash
    else:
        current = _build_case_from_snapshot(
            store,
            counter_id=case.counter_id,
            snapshot=before,
        )
        if current != case:
            raise ValueError("counter review case no longer matches current store state")

        candidate = next(
            (
                item
                for item in case.candidates
                if item.allocation_id == allocation_id
            ),
            None,
        )
        if candidate is None:
            raise ValueError(
                "selected allocation is not an eligible counter-review candidate"
            )
        if candidate.live_cents < amount_cents:
            raise ValueError(
                "selected allocation cannot absorb full counter event"
            )
        if not case.candidates:
            raise ValueError(
                "counter review case has no single-allocation candidate"
            )

        status = store.review_reverse(
            reversal_id=reversal_id,
            counter_id=case.counter_id,
            allocation_id=allocation_id,
            amount_cents=amount_cents,
            created_at=reviewed_at,
        )
        if status not in (REVERSED, ALREADY_REVERSED):
            raise AssertionError("unexpected reviewed reversal status")
        after = _snapshot(store)
        after_hash = _snapshot_hash(after)

    receipt_body = {
        "schema": 1,
        "buyer_id": store.buyer_id,
        "business_unit": store.business_unit,
        "case_hash": case.case_hash,
        "counter_id": case.counter_id,
        "allocation_id": allocation_id,
        "amount_cents": amount_cents,
        "reviewer_role": reviewer_role,
        "reviewed_at": reviewed_at,
        "rationale": rationale,
        "review_hash": review_hash,
        "reversal_id": reversal_id,
        "reversal_status": status,
        "store_snapshot_before_hash": before_hash,
        "store_snapshot_after_hash": after_hash,
    }
    return CounterReviewReceipt(
        buyer_id=store.buyer_id,
        business_unit=store.business_unit,
        case_hash=case.case_hash,
        counter_id=case.counter_id,
        allocation_id=allocation_id,
        amount_cents=amount_cents,
        reviewer_role=reviewer_role,
        reviewed_at=reviewed_at,
        rationale=rationale,
        review_hash=review_hash,
        reversal_id=reversal_id,
        reversal_status=status,
        store_snapshot_before_hash=before_hash,
        store_snapshot_after_hash=after_hash,
        receipt_hash=canonical_hash(receipt_body),
    )


def render_counter_review_markdown(
    case: CounterReviewCase,
    receipt: CounterReviewReceipt | None = None,
) -> str:
    lines = [
        "# Freight Recovery — Counter/Reversal Review",
        "",
        f"- Counter event: **{case.counter_id}**",
        f"- Original settlement event: **{case.original_event_id}**",
        f"- Remaining return amount: **{format_cents(case.currency, case.counter_residual_cents)}**",
        f"- Auto-reversal result: **{case.auto_review_reason}**",
        f"- Live allocation edges: **{case.live_allocation_count}**",
        f"- Review case hash: `{case.case_hash}`",
        "",
        "## Eligible single-allocation candidates",
    ]
    if not case.candidates:
        lines.append("- No live allocation can absorb the full remaining counter amount.")
    else:
        for candidate in case.candidates:
            lines.extend([
                f"- **{candidate.allocation_id}** — live {format_cents(case.currency, candidate.live_cents)}",
                f"  - Claim: {candidate.claim_id}",
                f"  - Claim reference: {candidate.claim_reference}",
                f"  - Allocation mode: {candidate.mode}",
                f"  - Candidate hash: `{candidate.candidate_hash}`",
            ])

    lines.extend([
        "",
        "V1 requires one selected allocation to absorb the full remaining counter event. Split reviewed reversals are not supported.",
        "This review changes attribution of already-observed settlement evidence. It does not move money or create a bank return.",
        "",
    ])
    if receipt is not None:
        lines.extend([
            "## Applied review",
            f"- Allocation: **{receipt.allocation_id}**",
            f"- Reversed amount: **{format_cents(case.currency, receipt.amount_cents)}**",
            f"- Reviewer role: **{receipt.reviewer_role}**",
            f"- Reviewed at: **{receipt.reviewed_at}**",
            f"- Rationale: {receipt.rationale}",
            f"- Review hash: `{receipt.review_hash}`",
            f"- Reversal ID: `{receipt.reversal_id}`",
            f"- Receipt hash: `{receipt.receipt_hash}`",
            "",
        ])
    return "\n".join(lines)
