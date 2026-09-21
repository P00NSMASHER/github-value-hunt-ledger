"""Proof-bound manual settlement allocation for Freight Recovery.

This workflow is used only when exact auto-allocation cannot select one unique
claim. It snapshots the relevant immutable settlement evidence and live claim
capacity, produces a deterministic review case, and requires a human decision
bound to that exact case before a reviewed allocation can be written.

V1 deliberately supports one settlement event -> one claim for the full
remaining event amount. Split allocations across multiple claims remain
unsupported here and must not be improvised through this workflow.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from freight.contracts import canonical_hash
from freight.settlement_store import (
    ALREADY_ALLOCATED,
    ALLOCATED,
    REVIEW,
    SettlementStore,
)


@dataclass(frozen=True)
class SettlementClaimCandidate:
    claim_id: str
    reference: str
    payer_id: str
    payee_id: str
    currency: str
    claim_amount_cents: int
    residual_cents: int
    issued_at: str
    source_hash: str
    fee_disqualified: bool
    reference_match: bool
    review_locked: bool
    candidate_hash: str


@dataclass(frozen=True)
class SettlementReviewCase:
    buyer_id: str
    business_unit: str
    event_id: str
    event_reference: str
    payer_id: str
    payee_id: str
    currency: str
    event_amount_cents: int
    event_residual_cents: int
    booked_at: str
    event_source_hash: str
    source_kind: str
    auto_review_reason: str
    exact_auto_candidate_count: int
    candidates: tuple[SettlementClaimCandidate, ...]
    case_hash: str


@dataclass(frozen=True)
class SettlementReviewDecisionInput:
    case_hash: str
    claim_id: str
    reviewer_role: str
    reviewed_at: str
    rationale: str


@dataclass(frozen=True)
class SettlementReviewReceipt:
    buyer_id: str
    business_unit: str
    case_hash: str
    event_id: str
    claim_id: str
    amount_cents: int
    reviewer_role: str
    reviewed_at: str
    rationale: str
    review_hash: str
    allocation_id: str
    allocation_status: str
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


def _reversal_by_allocation(tables: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in tables["reversal_edges"]:
        out[row["allocation_id"]] = out.get(row["allocation_id"], 0) + int(
            row["amount_cents"]
        )
    return out


def _claim_residuals(tables: dict) -> dict[str, int]:
    allocated: dict[str, int] = {}
    reversal_by_alloc = _reversal_by_allocation(tables)
    reversed_by_claim: dict[str, int] = {}
    for row in tables["allocations"]:
        claim_id = row["claim_id"]
        allocated[claim_id] = allocated.get(claim_id, 0) + int(row["amount_cents"])
        reversed_by_claim[claim_id] = reversed_by_claim.get(claim_id, 0) + int(
            reversal_by_alloc.get(row["allocation_id"], 0)
        )
    return {
        row["claim_id"]: int(row["amount_cents"])
        - allocated.get(row["claim_id"], 0)
        + reversed_by_claim.get(row["claim_id"], 0)
        for row in tables["recovery_claims"]
    }


def _build_case_from_snapshot(
    store: SettlementStore,
    *,
    event_id: str,
    snapshot: dict,
) -> SettlementReviewCase:
    event_id = _text("event_id", event_id)
    tables = snapshot["tables"]
    event = next(
        (row for row in tables["settlement_events"] if row["event_id"] == event_id),
        None,
    )
    if event is None:
        raise ValueError("unknown settlement event")

    event_allocations = [
        row for row in tables["allocations"] if row["event_id"] == event_id
    ]
    if event_allocations:
        raise ValueError("settlement event already has allocation; review case is stale")

    event_residual = int(event["amount_cents"])
    if event_residual <= 0:
        raise ValueError("settlement event has no residual amount")

    residuals = _claim_residuals(tables)
    review_locked = {row["claim_id"] for row in tables["review_claims"]}

    identity_claims = []
    exact_auto = []
    for claim in tables["recovery_claims"]:
        residual = int(residuals[claim["claim_id"]])
        if residual <= 0:
            continue
        if (claim["payer_id"], claim["payee_id"], claim["currency"]) != (
            event["payer_id"],
            event["payee_id"],
            event["currency"],
        ):
            continue
        if claim["issued_at"] > event["booked_at"]:
            continue

        reference_match = claim["reference"] == event["reference"]
        locked = claim["claim_id"] in review_locked
        if (
            reference_match
            and not locked
            and residual == event_residual
        ):
            exact_auto.append(claim["claim_id"])

        if residual < event_residual:
            continue

        candidate_body = {
            "schema": 1,
            "event_id": event_id,
            "claim_id": claim["claim_id"],
            "reference": claim["reference"],
            "payer_id": claim["payer_id"],
            "payee_id": claim["payee_id"],
            "currency": claim["currency"],
            "claim_amount_cents": int(claim["amount_cents"]),
            "residual_cents": residual,
            "issued_at": claim["issued_at"],
            "source_hash": claim["source_hash"],
            "fee_disqualified": bool(claim["fee_disqualified"]),
            "reference_match": reference_match,
            "review_locked": locked,
        }
        identity_claims.append(SettlementClaimCandidate(
            claim_id=claim["claim_id"],
            reference=claim["reference"],
            payer_id=claim["payer_id"],
            payee_id=claim["payee_id"],
            currency=claim["currency"],
            claim_amount_cents=int(claim["amount_cents"]),
            residual_cents=residual,
            issued_at=claim["issued_at"],
            source_hash=claim["source_hash"],
            fee_disqualified=bool(claim["fee_disqualified"]),
            reference_match=reference_match,
            review_locked=locked,
            candidate_hash=canonical_hash(candidate_body),
        ))

    exact_count = len(exact_auto)
    if exact_count == 1:
        raise ValueError("settlement event is auto-allocatable; manual review is not allowed")

    candidates = tuple(sorted(
        identity_claims,
        key=lambda item: (not item.reference_match, item.claim_id),
    ))
    auto_reason = f"exact unique candidate count={exact_count}"
    body = {
        "schema": 1,
        "buyer_id": store.buyer_id,
        "business_unit": store.business_unit,
        "event_id": event_id,
        "event_reference": event["reference"],
        "payer_id": event["payer_id"],
        "payee_id": event["payee_id"],
        "currency": event["currency"],
        "event_amount_cents": int(event["amount_cents"]),
        "event_residual_cents": event_residual,
        "booked_at": event["booked_at"],
        "event_source_hash": event["source_hash"],
        "source_kind": event["source_kind"],
        "auto_review_reason": auto_reason,
        "exact_auto_candidate_count": exact_count,
        "candidates": [asdict(candidate) for candidate in candidates],
    }
    return SettlementReviewCase(
        buyer_id=store.buyer_id,
        business_unit=store.business_unit,
        event_id=event_id,
        event_reference=event["reference"],
        payer_id=event["payer_id"],
        payee_id=event["payee_id"],
        currency=event["currency"],
        event_amount_cents=int(event["amount_cents"]),
        event_residual_cents=event_residual,
        booked_at=event["booked_at"],
        event_source_hash=event["source_hash"],
        source_kind=event["source_kind"],
        auto_review_reason=auto_reason,
        exact_auto_candidate_count=exact_count,
        candidates=candidates,
        case_hash=canonical_hash(body),
    )


def build_settlement_review_case(
    store: SettlementStore,
    *,
    event_id: str,
) -> SettlementReviewCase:
    return _build_case_from_snapshot(
        store,
        event_id=event_id,
        snapshot=_snapshot(store),
    )


def _canonical_decision(
    case: SettlementReviewCase,
    decision: SettlementReviewDecisionInput,
) -> tuple[str, datetime, str, str, str, str]:
    if not isinstance(decision, SettlementReviewDecisionInput):
        raise ValueError("decision must be a SettlementReviewDecisionInput")
    if decision.case_hash != case.case_hash:
        raise ValueError("settlement review decision case hash mismatch")
    claim_id = _text("claim_id", decision.claim_id)
    reviewer_role = _text("reviewer_role", decision.reviewer_role)
    reviewed_at, reviewed_dt = _timestamp("reviewed_at", decision.reviewed_at)
    rationale = _text("rationale", decision.rationale)
    booked_dt = datetime.fromisoformat(
        case.booked_at.replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    if reviewed_dt < booked_dt:
        raise ValueError("settlement review cannot predate settlement booking")

    body = {
        "schema": 1,
        "case_hash": case.case_hash,
        "event_id": case.event_id,
        "claim_id": claim_id,
        "amount_cents": case.event_residual_cents,
        "reviewer_role": reviewer_role,
        "reviewed_at": reviewed_at,
        "rationale": rationale,
    }
    review_hash = canonical_hash(body)
    return claim_id, reviewed_dt, reviewer_role, reviewed_at, rationale, review_hash


def apply_settlement_review_decision(
    store: SettlementStore,
    *,
    case: SettlementReviewCase,
    decision: SettlementReviewDecisionInput,
) -> SettlementReviewReceipt:
    canonical = _canonical_decision(case, decision)
    claim_id, _reviewed_dt, reviewer_role, reviewed_at, rationale, review_hash = canonical
    allocation_id = "review:" + review_hash
    amount_cents = case.event_residual_cents

    before = _snapshot(store)
    before_hash = _snapshot_hash(before)
    existing = next(
        (
            row
            for row in before["tables"]["allocations"]
            if row["allocation_id"] == allocation_id
        ),
        None,
    )
    if existing is not None:
        expected = (
            case.event_id,
            claim_id,
            amount_cents,
            REVIEW,
            reviewed_at,
        )
        actual = (
            existing["event_id"],
            existing["claim_id"],
            int(existing["amount_cents"]),
            existing["mode"],
            existing["created_at"],
        )
        if actual != expected:
            raise ValueError("review allocation replay conflicts with immutable allocation")
        status = ALREADY_ALLOCATED
        after = before
        after_hash = before_hash
    else:
        current = _build_case_from_snapshot(
            store,
            event_id=case.event_id,
            snapshot=before,
        )
        if current != case:
            raise ValueError("settlement review case no longer matches current store state")

        candidate = next(
            (item for item in case.candidates if item.claim_id == claim_id),
            None,
        )
        if candidate is None:
            raise ValueError("selected claim is not an eligible settlement-review candidate")
        if candidate.residual_cents < amount_cents:
            raise ValueError("selected claim cannot absorb full settlement event")
        if not case.candidates:
            raise ValueError("settlement review case has no single-claim candidate")

        status = store.review_allocate(
            allocation_id=allocation_id,
            claim_id=claim_id,
            event_id=case.event_id,
            amount_cents=amount_cents,
            created_at=reviewed_at,
        )
        if status not in (ALLOCATED, ALREADY_ALLOCATED):
            raise AssertionError("unexpected reviewed allocation status")
        after = _snapshot(store)
        after_hash = _snapshot_hash(after)

    receipt_body = {
        "schema": 1,
        "buyer_id": store.buyer_id,
        "business_unit": store.business_unit,
        "case_hash": case.case_hash,
        "event_id": case.event_id,
        "claim_id": claim_id,
        "amount_cents": amount_cents,
        "reviewer_role": reviewer_role,
        "reviewed_at": reviewed_at,
        "rationale": rationale,
        "review_hash": review_hash,
        "allocation_id": allocation_id,
        "allocation_status": status,
        "store_snapshot_before_hash": before_hash,
        "store_snapshot_after_hash": after_hash,
    }
    return SettlementReviewReceipt(
        buyer_id=store.buyer_id,
        business_unit=store.business_unit,
        case_hash=case.case_hash,
        event_id=case.event_id,
        claim_id=claim_id,
        amount_cents=amount_cents,
        reviewer_role=reviewer_role,
        reviewed_at=reviewed_at,
        rationale=rationale,
        review_hash=review_hash,
        allocation_id=allocation_id,
        allocation_status=status,
        store_snapshot_before_hash=before_hash,
        store_snapshot_after_hash=after_hash,
        receipt_hash=canonical_hash(receipt_body),
    )


def render_settlement_review_markdown(
    case: SettlementReviewCase,
    receipt: SettlementReviewReceipt | None = None,
) -> str:
    lines = [
        "# Freight Recovery — Settlement Allocation Review",
        "",
        f"- Event: **{case.event_id}**",
        f"- Reference: **{case.event_reference}**",
        f"- Remaining settlement amount: **{case.currency} {case.event_residual_cents / 100:,.2f}**",
        f"- Auto-allocation result: **{case.auto_review_reason}**",
        f"- Review case hash: `{case.case_hash}`",
        "",
        "## Eligible single-claim candidates",
    ]
    if not case.candidates:
        lines.append("- No claim can absorb the full remaining event amount.")
    else:
        for candidate in case.candidates:
            lines.extend([
                f"- **{candidate.claim_id}** — residual {candidate.currency} {candidate.residual_cents / 100:,.2f}",
                f"  - Reference: {candidate.reference}",
                f"  - Reference matches event: {'yes' if candidate.reference_match else 'no'}",
                f"  - Previously review-locked: {'yes' if candidate.review_locked else 'no'}",
                f"  - Candidate hash: `{candidate.candidate_hash}`",
            ])

    lines.extend([
        "",
        "V1 requires one selected claim to absorb the full remaining settlement event. Split allocations are not supported by this review workflow.",
        "This review allocates observed settlement evidence; it does not move money or create a settlement.",
        "",
    ])
    if receipt is not None:
        lines.extend([
            "## Applied review",
            f"- Claim: **{receipt.claim_id}**",
            f"- Amount: **{case.currency} {receipt.amount_cents / 100:,.2f}**",
            f"- Reviewer role: **{receipt.reviewer_role}**",
            f"- Reviewed at: **{receipt.reviewed_at}**",
            f"- Rationale: {receipt.rationale}",
            f"- Review hash: `{receipt.review_hash}`",
            f"- Allocation ID: `{receipt.allocation_id}`",
            f"- Receipt hash: `{receipt.receipt_hash}`",
            "",
        ])
    return "\n".join(lines)
