"""Canonical carrier-facing payloads for Freight Recovery.

This module creates deterministic, preview-only action payloads from one exact
CarrierActionProposal plus its proof-bound RecoveryClaimBatch. It never sends
anything. A separate buyer approval must bind the resulting payload hash before
the existing external-action authorization can become active.
"""
from __future__ import annotations

import unicodedata
from dataclasses import asdict, dataclass

from freight.carrier_action_workflow import (
    CarrierActionApprovalInput,
    CarrierActionProposal,
    authorize_carrier_action_proposal,
)
from freight.buyer_review_workflow import BuyerReviewBatch
from freight.contracts import TruthManifest, canonical_hash
from freight.engagement_state import EngagementResolution
from freight.external_action_authorization import ActionType, ExternalActionAuthorization
from freight.recovery_claim_workflow import RecoveryClaimBatch, verify_recovery_claim_batch
from freight.review_packet import ReviewPacket
from freight.review_routing import ReviewRouting


MAX_EXTERNAL_FIELD_CHARS = 256


@dataclass(frozen=True)
class CarrierActionPayloadLine:
    claim_id: str
    finding_id: str
    reference: str
    amount_cents: int
    finding_proof_hash: str
    review_hash: str
    claim_record_hash: str
    line_hash: str


@dataclass(frozen=True)
class CarrierActionPayload:
    proposal_hash: str
    recovery_claim_batch_hash: str
    action_type: str
    target_carrier_id: str
    target_customer_id: str
    currency: str
    requested_cents: int
    line_count: int
    lines: tuple[CarrierActionPayloadLine, ...]
    subject: str
    body_text: str
    payload_hash: str


def _external_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " is required")
    text = value.strip()
    if len(text) > MAX_EXTERNAL_FIELD_CHARS:
        raise ValueError(name + " exceeds external payload length limit")
    if any(unicodedata.category(ch).startswith("C") for ch in text):
        raise ValueError(name + " contains control characters")
    return text


def _verb(action_type: ActionType) -> tuple[str, str]:
    if action_type is ActionType.SUBMIT_DISPUTE:
        return (
            "Freight charge dispute review",
            "Please review the disputed freight charges listed below.",
        )
    if action_type is ActionType.REQUEST_CREDIT_REVIEW:
        return (
            "Freight credit review request",
            "Please review the freight charges listed below for credit consideration.",
        )
    if action_type is ActionType.REQUEST_DOCUMENTATION:
        return (
            "Freight charge documentation request",
            "Please provide supporting documentation for the freight charges listed below.",
        )
    if action_type is ActionType.REQUEST_STATUS:
        return (
            "Freight claim status request",
            "Please provide the current status of the freight claim items listed below.",
        )
    raise ValueError("unsupported carrier action type")


def build_carrier_action_payload(
    *,
    proposal: CarrierActionProposal,
    recovery_claims: RecoveryClaimBatch,
    action_type: ActionType,
) -> CarrierActionPayload:
    if not isinstance(action_type, ActionType):
        raise ValueError("action_type must be an ActionType")
    verify_recovery_claim_batch(recovery_claims)

    if proposal.recovery_claim_batch_hash != recovery_claims.batch_hash:
        raise ValueError("proposal recovery claim batch hash mismatch")
    if (proposal.buyer_id, proposal.business_unit) != (
        recovery_claims.buyer_id,
        recovery_claims.business_unit,
    ):
        raise ValueError("proposal scope mismatch with recovery claim batch")

    record_index = {record.claim_id: record for record in recovery_claims.records}
    if len(record_index) != len(recovery_claims.records):
        raise ValueError("duplicate recovery claim record ID")

    proposal_claim_ids = tuple(proposal.claim_ids)
    if len(proposal_claim_ids) != len(set(proposal_claim_ids)):
        raise ValueError("duplicate claim_id in carrier action proposal")

    carrier = _external_text("target_carrier_id", proposal.target_carrier_id)
    customer = _external_text("target_customer_id", proposal.target_customer_id)
    currency = _external_text("currency", proposal.currency)

    lines: list[CarrierActionPayloadLine] = []
    total = 0
    finding_ids: list[str] = []
    proof_hashes: list[str] = []
    review_hashes: list[str] = []

    for claim_id in proposal_claim_ids:
        record = record_index.get(claim_id)
        if record is None:
            raise ValueError("proposal references unknown recovery claim: " + claim_id)
        if (record.payer_id, record.payee_id, record.currency) != (
            proposal.target_carrier_id,
            proposal.target_customer_id,
            proposal.currency,
        ):
            raise ValueError("proposal claim identity mismatch")
        reference = _external_text("claim reference", record.reference)
        safe_claim_id = _external_text("claim_id", record.claim_id)
        safe_finding_id = _external_text("finding_id", record.finding_id)
        line_body = {
            "schema": 1,
            "proposal_hash": proposal.proposal_hash,
            "claim_id": safe_claim_id,
            "finding_id": safe_finding_id,
            "reference": reference,
            "amount_cents": record.amount_cents,
            "finding_proof_hash": record.finding_proof_hash,
            "review_hash": record.review_hash,
            "claim_record_hash": record.record_hash,
        }
        lines.append(CarrierActionPayloadLine(
            claim_id=safe_claim_id,
            finding_id=safe_finding_id,
            reference=reference,
            amount_cents=record.amount_cents,
            finding_proof_hash=record.finding_proof_hash,
            review_hash=record.review_hash,
            claim_record_hash=record.record_hash,
            line_hash=canonical_hash(line_body),
        ))
        total += record.amount_cents
        finding_ids.append(record.finding_id)
        proof_hashes.append(record.finding_proof_hash)
        review_hashes.append(record.review_hash)

    if tuple(finding_ids) != proposal.finding_ids:
        raise ValueError("proposal finding IDs do not match recovery claims")
    if tuple(proof_hashes) != proposal.finding_proof_hashes:
        raise ValueError("proposal finding proofs do not match recovery claims")
    if tuple(review_hashes) != proposal.finding_review_hashes:
        raise ValueError("proposal review proofs do not match recovery claims")
    if total != proposal.total_claim_cents:
        raise ValueError("proposal total does not match recovery claims")
    if not lines:
        raise ValueError("carrier action payload requires at least one claim")

    title, request_sentence = _verb(action_type)
    subject = f"{title} — {customer} — {len(lines)} item" + ("" if len(lines) == 1 else "s")
    body_lines = [
        request_sentence,
        "",
        f"Customer/payee: {customer}",
        f"Carrier/payer: {carrier}",
        f"Currency: {currency}",
        "",
        "Items:",
    ]
    for line in lines:
        body_lines.append(
            f"- Reference {line.reference}: {currency} {line.amount_cents / 100:,.2f}"
        )
    body_lines.extend([
        "",
        f"Total amount in this request: {currency} {total / 100:,.2f}",
        "",
        "This request does not accept settlement terms, authorize payment, or authorize account changes.",
    ])
    body_text = "\n".join(body_lines)

    lines_tuple = tuple(lines)
    body = {
        "schema": 1,
        "proposal_hash": proposal.proposal_hash,
        "recovery_claim_batch_hash": recovery_claims.batch_hash,
        "action_type": action_type.value,
        "target_carrier_id": proposal.target_carrier_id,
        "target_customer_id": proposal.target_customer_id,
        "currency": proposal.currency,
        "requested_cents": total,
        "line_count": len(lines_tuple),
        "lines": [asdict(line) for line in lines_tuple],
        "subject": subject,
        "body_text": body_text,
    }
    return CarrierActionPayload(
        proposal_hash=proposal.proposal_hash,
        recovery_claim_batch_hash=recovery_claims.batch_hash,
        action_type=action_type.value,
        target_carrier_id=proposal.target_carrier_id,
        target_customer_id=proposal.target_customer_id,
        currency=proposal.currency,
        requested_cents=total,
        line_count=len(lines_tuple),
        lines=lines_tuple,
        subject=subject,
        body_text=body_text,
        payload_hash=canonical_hash(body),
    )


def verify_carrier_action_payload(
    payload: CarrierActionPayload,
    *,
    proposal: CarrierActionProposal,
    recovery_claims: RecoveryClaimBatch,
) -> None:
    expected = build_carrier_action_payload(
        proposal=proposal,
        recovery_claims=recovery_claims,
        action_type=ActionType(payload.action_type),
    )
    if payload != expected:
        raise ValueError("carrier action payload does not match proposal/recovery claims")


def authorize_carrier_action_payload(
    *,
    resolution: EngagementResolution,
    operative_charter: dict,
    truth: TruthManifest,
    review_packet: ReviewPacket,
    review_routing: ReviewRouting,
    buyer_review: BuyerReviewBatch,
    recovery_claims: RecoveryClaimBatch,
    proposal: CarrierActionProposal,
    payload: CarrierActionPayload,
    approval: CarrierActionApprovalInput,
) -> ExternalActionAuthorization:
    verify_carrier_action_payload(
        payload,
        proposal=proposal,
        recovery_claims=recovery_claims,
    )
    if approval.proposal_hash != payload.proposal_hash:
        raise ValueError("approval proposal hash does not match carrier action payload")
    if approval.action_type.value != payload.action_type:
        raise ValueError("approval action type does not match carrier action payload")
    if approval.action_payload_hash != payload.payload_hash:
        raise ValueError("approval payload hash does not match carrier action payload")
    if (
        approval.authorized_cents is not None
        and approval.authorized_cents != payload.requested_cents
    ):
        raise ValueError(
            "approved amount must equal the canonical carrier action payload amount"
        )

    return authorize_carrier_action_proposal(
        resolution=resolution,
        operative_charter=operative_charter,
        truth=truth,
        review_packet=review_packet,
        review_routing=review_routing,
        buyer_review=buyer_review,
        recovery_claims=recovery_claims,
        proposal=proposal,
        approval=approval,
    )


def render_carrier_action_payload_markdown(payload: CarrierActionPayload) -> str:
    lines = [
        "# Freight Recovery — Carrier Action Payload Preview",
        "",
        f"- Action: **{payload.action_type}**",
        f"- Carrier: **{payload.target_carrier_id}**",
        f"- Customer/payee: **{payload.target_customer_id}**",
        f"- Amount: **{payload.currency} {payload.requested_cents / 100:,.2f}**",
        f"- Payload hash: `{payload.payload_hash}`",
        "",
        "## Subject",
        "",
        payload.subject,
        "",
        "## Body",
        "",
        payload.body_text,
        "",
        "Preview only. This artifact does not authorize or send an external action.",
        "",
    ]
    return "\n".join(lines)
