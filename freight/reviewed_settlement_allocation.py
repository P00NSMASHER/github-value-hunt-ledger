"""Proof-bound workflow for human-reviewed settlement allocations.

This layer replaces raw manual calls to SettlementStore.review_allocate for
partial, batched, or otherwise ambiguous external settlement evidence. A human
allocation decision is bound to the exact pre-allocation settlement snapshot,
claim proof, event proof, reviewer identity, timestamp, amount, and reason.

It does not create recovery claims, move money, or infer settlement ownership
without a human decision.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from freight.contracts import canonical_hash
from freight.recovery_claim_workflow import (
    RecoveryClaimBatch,
    verify_recovery_claim_batch,
)
from freight.settlement_store import (
    ALLOCATED,
    ALREADY_ALLOCATED,
    REVIEW,
    SettlementStore,
)


@dataclass(frozen=True)
class ReviewedSettlementAllocationDecision:
    buyer_id: str
    business_unit: str
    claim_batch_hash: str
    claim_id: str
    finding_id: str
    finding_proof_hash: str
    claim_record_hash: str
    event_id: str
    event_source_hash: str
    currency: str
    amount_cents: int
    reviewer_role: str
    reviewed_at: str
    reason: str
    pre_snapshot_hash: str
    allocation_id: str
    decision_hash: str


@dataclass(frozen=True)
class ReviewedSettlementAllocationReceipt:
    buyer_id: str
    business_unit: str
    decision_hash: str
    allocation_id: str
    status: str
    pre_snapshot_hash: str
    post_snapshot_hash: str
    receipt_hash: str


def _timestamp(name: str, value: str) -> tuple[str, datetime]:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " is required")
    text = value.strip()
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


def _snapshot(store: SettlementStore) -> tuple[dict, str]:
    payload = json.loads(store.report_snapshot_json())
    return payload, canonical_hash(payload)


def _residuals(snapshot: dict, claim_id: str, event_id: str) -> tuple[int, int]:
    tables = snapshot["tables"]
    claims = {row["claim_id"]: row for row in tables["recovery_claims"]}
    events = {row["event_id"]: row for row in tables["settlement_events"]}
    claim = claims.get(claim_id)
    event = events.get(event_id)
    if claim is None:
        raise ValueError("unknown recovery claim")
    if event is None:
        raise ValueError("unknown settlement event")

    allocations = tables["allocations"]
    reversals = tables["reversal_edges"]
    allocation_by_id = {row["allocation_id"]: row for row in allocations}
    claim_allocated = sum(
        row["amount_cents"] for row in allocations if row["claim_id"] == claim_id
    )
    claim_reversed = sum(
        row["amount_cents"]
        for row in reversals
        if allocation_by_id.get(row["allocation_id"], {}).get("claim_id") == claim_id
    )
    event_allocated = sum(
        row["amount_cents"] for row in allocations if row["event_id"] == event_id
    )
    return (
        claim["amount_cents"] - claim_allocated + claim_reversed,
        event["amount_cents"] - event_allocated,
    )


def _decision_body(decision: ReviewedSettlementAllocationDecision) -> dict:
    return {
        "schema": 1,
        "buyer_id": decision.buyer_id,
        "business_unit": decision.business_unit,
        "claim_batch_hash": decision.claim_batch_hash,
        "claim_id": decision.claim_id,
        "finding_id": decision.finding_id,
        "finding_proof_hash": decision.finding_proof_hash,
        "claim_record_hash": decision.claim_record_hash,
        "event_id": decision.event_id,
        "event_source_hash": decision.event_source_hash,
        "currency": decision.currency,
        "amount_cents": decision.amount_cents,
        "reviewer_role": decision.reviewer_role,
        "reviewed_at": decision.reviewed_at,
        "reason": decision.reason,
        "pre_snapshot_hash": decision.pre_snapshot_hash,
    }


def verify_reviewed_settlement_allocation_decision(
    decision: ReviewedSettlementAllocationDecision,
) -> None:
    body = _decision_body(decision)
    digest = canonical_hash(body)
    if digest != decision.decision_hash:
        raise ValueError("reviewed settlement allocation decision hash mismatch")
    if decision.allocation_id != "review:" + digest:
        raise ValueError("reviewed settlement allocation_id mismatch")


def build_reviewed_settlement_allocation_decision(
    *,
    store: SettlementStore,
    claim_batch: RecoveryClaimBatch,
    claim_id: str,
    event_id: str,
    amount_cents: int,
    reviewer_role: str,
    reviewed_at: str,
    reason: str,
) -> ReviewedSettlementAllocationDecision:
    verify_recovery_claim_batch(claim_batch)
    if (store.buyer_id, store.business_unit) != (
        claim_batch.buyer_id,
        claim_batch.business_unit,
    ):
        raise ValueError("settlement store scope mismatch with recovery claim batch")
    if type(amount_cents) is not int or amount_cents <= 0:
        raise ValueError("amount_cents must be positive integer cents")
    if not isinstance(reviewer_role, str) or not reviewer_role.strip():
        raise ValueError("reviewer_role is required")
    reviewer_role = reviewer_role.strip()
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("review reason is required")
    reason = reason.strip()
    canonical_reviewed_at, reviewed_dt = _timestamp("reviewed_at", reviewed_at)

    snapshot, snapshot_hash = _snapshot(store)
    tables = snapshot["tables"]
    stored_claims = {row["claim_id"]: row for row in tables["recovery_claims"]}
    stored_events = {row["event_id"]: row for row in tables["settlement_events"]}
    stored_claim = stored_claims.get(claim_id)
    event = stored_events.get(event_id)
    if stored_claim is None:
        raise ValueError("unknown recovery claim")
    if event is None:
        raise ValueError("unknown settlement event")

    batch_index = {
        record.claim_id: (record, claim)
        for record, claim in zip(claim_batch.records, claim_batch.claims, strict=True)
    }
    pair = batch_index.get(claim_id)
    if pair is None:
        raise ValueError("recovery claim is not part of the verified claim batch")
    record, claim = pair

    expected_claim = {
        "reference": claim.reference,
        "payer_id": claim.payer_id,
        "payee_id": claim.payee_id,
        "currency": claim.currency,
        "amount_cents": claim.amount_cents,
        "issued_at": claim.issued_at,
        "source_hash": claim.source_hash,
        "fee_disqualified": int(claim.fee_disqualified),
    }
    if any(stored_claim[key] != value for key, value in expected_claim.items()):
        raise ValueError("persisted recovery claim does not match verified claim batch")

    if (event["payer_id"], event["payee_id"], event["currency"]) != (
        stored_claim["payer_id"],
        stored_claim["payee_id"],
        stored_claim["currency"],
    ):
        raise ValueError("settlement event identity/currency mismatch with claim")
    if event["booked_at"] < stored_claim["issued_at"]:
        raise ValueError("settlement event predates issued claim")

    event_dt = datetime.fromisoformat(event["booked_at"].replace("Z", "+00:00"))
    if reviewed_dt < event_dt:
        raise ValueError("reviewed_at cannot precede settlement event")

    claim_residual, event_residual = _residuals(snapshot, claim_id, event_id)
    if amount_cents > claim_residual:
        raise ValueError("reviewed allocation exceeds recovery claim residual")
    if amount_cents > event_residual:
        raise ValueError("reviewed allocation exceeds settlement event residual")

    provisional = ReviewedSettlementAllocationDecision(
        buyer_id=store.buyer_id,
        business_unit=store.business_unit,
        claim_batch_hash=claim_batch.batch_hash,
        claim_id=claim_id,
        finding_id=record.finding_id,
        finding_proof_hash=record.finding_proof_hash,
        claim_record_hash=record.record_hash,
        event_id=event_id,
        event_source_hash=event["source_hash"],
        currency=event["currency"],
        amount_cents=amount_cents,
        reviewer_role=reviewer_role,
        reviewed_at=canonical_reviewed_at,
        reason=reason,
        pre_snapshot_hash=snapshot_hash,
        allocation_id="",
        decision_hash="",
    )
    digest = canonical_hash(_decision_body(provisional))
    return ReviewedSettlementAllocationDecision(
        **{
            **asdict(provisional),
            "allocation_id": "review:" + digest,
            "decision_hash": digest,
        }
    )


def persist_reviewed_settlement_allocation(
    store: SettlementStore,
    decision: ReviewedSettlementAllocationDecision,
) -> ReviewedSettlementAllocationReceipt:
    verify_reviewed_settlement_allocation_decision(decision)
    if (store.buyer_id, store.business_unit) != (
        decision.buyer_id,
        decision.business_unit,
    ):
        raise ValueError("settlement store scope mismatch with reviewed allocation")

    current, current_hash = _snapshot(store)
    allocations = {
        row["allocation_id"]: row for row in current["tables"]["allocations"]
    }
    existing = allocations.get(decision.allocation_id)
    if existing is not None:
        expected = {
            "claim_id": decision.claim_id,
            "event_id": decision.event_id,
            "amount_cents": decision.amount_cents,
            "mode": REVIEW,
            "created_at": decision.reviewed_at,
        }
        if any(existing[key] != value for key, value in expected.items()):
            raise ValueError("reviewed allocation_id conflicts with persisted allocation")
        status = ALREADY_ALLOCATED
        post_hash = current_hash
    else:
        if current_hash != decision.pre_snapshot_hash:
            raise ValueError(
                "settlement snapshot changed after review decision; rebuild reviewed allocation"
            )
        status = store.review_allocate(
            allocation_id=decision.allocation_id,
            claim_id=decision.claim_id,
            event_id=decision.event_id,
            amount_cents=decision.amount_cents,
            created_at=decision.reviewed_at,
        )
        if status not in {ALLOCATED, ALREADY_ALLOCATED}:
            raise ValueError("unexpected reviewed settlement allocation status")
        _, post_hash = _snapshot(store)

    body = {
        "schema": 1,
        "buyer_id": decision.buyer_id,
        "business_unit": decision.business_unit,
        "decision_hash": decision.decision_hash,
        "allocation_id": decision.allocation_id,
        "status": status,
        "pre_snapshot_hash": decision.pre_snapshot_hash,
        "post_snapshot_hash": post_hash,
    }
    return ReviewedSettlementAllocationReceipt(
        buyer_id=decision.buyer_id,
        business_unit=decision.business_unit,
        decision_hash=decision.decision_hash,
        allocation_id=decision.allocation_id,
        status=status,
        pre_snapshot_hash=decision.pre_snapshot_hash,
        post_snapshot_hash=post_hash,
        receipt_hash=canonical_hash(body),
    )


def render_reviewed_settlement_allocation_markdown(
    decision: ReviewedSettlementAllocationDecision,
) -> str:
    verify_reviewed_settlement_allocation_decision(decision)
    return "\n".join([
        "# Freight Recovery — Reviewed Settlement Allocation",
        "",
        f"- Claim: `{decision.claim_id}`",
        f"- Finding: `{decision.finding_id}`",
        f"- Settlement event: `{decision.event_id}`",
        f"- Amount: **{decision.currency} {decision.amount_cents / 100:,.2f}**",
        f"- Reviewer role: **{decision.reviewer_role}**",
        f"- Reviewed at: **{decision.reviewed_at}**",
        f"- Reason: {decision.reason}",
        f"- Finding proof: `{decision.finding_proof_hash}`",
        f"- Settlement event proof: `{decision.event_source_hash}`",
        f"- Pre-allocation snapshot: `{decision.pre_snapshot_hash}`",
        f"- Decision hash: `{decision.decision_hash}`",
        "",
        "This decision records human allocation of existing settlement evidence.",
        "It does not create money movement and does not by itself prove realized recovery.",
        "",
    ])
