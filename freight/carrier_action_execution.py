"""Proof objects for executing an already-authorized carrier action.

This module does not send external actions. It creates a deterministic pre-send
intent (including a stable idempotency key) and records post-attempt evidence.
Authorization, submission and delivery remain distinct states.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable

from freight.carrier_action_payload import (
    CarrierActionPayload,
    verify_carrier_action_payload,
)
from freight.carrier_action_workflow import CarrierActionProposal
from freight.contracts import canonical_hash
from freight.external_action_authorization import (
    ActionType,
    AuthorizationRevocation,
    ExternalActionAuthorization,
    assert_action_allowed,
)
from freight.recovery_claim_workflow import RecoveryClaimBatch


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ExecutionChannel(str, Enum):
    EMAIL = "EMAIL"
    CARRIER_PORTAL = "CARRIER_PORTAL"
    API = "API"
    MANUAL = "MANUAL"


class ExecutionOutcome(str, Enum):
    FAILED = "FAILED"
    SUBMITTED = "SUBMITTED"
    DELIVERED = "DELIVERED"


@dataclass(frozen=True)
class CarrierActionExecutionIntent:
    execution_key: str
    authorization_id: str
    authorization_hash: str
    proposal_hash: str
    payload_hash: str
    recipient_reference_hash: str
    action_type: str
    target_carrier_id: str
    target_customer_id: str
    currency: str
    requested_cents: int
    finding_ids: tuple[str, ...]
    prepared_at: str
    subject: str
    body_text: str
    intent_hash: str


@dataclass(frozen=True)
class CarrierActionExecutionEvidence:
    execution_key: str
    outcome: ExecutionOutcome
    channel: ExecutionChannel
    external_reference_hash: str
    evidence_source_hash: str
    executed_at: str
    executor_role: str


@dataclass(frozen=True)
class CarrierActionExecutionReceipt:
    execution_key: str
    intent_hash: str
    authorization_id: str
    authorization_hash: str
    proposal_hash: str
    payload_hash: str
    recipient_reference_hash: str
    action_type: str
    target_carrier_id: str
    target_customer_id: str
    currency: str
    requested_cents: int
    finding_ids: tuple[str, ...]
    prepared_at: str
    executed_at: str
    channel: str
    outcome: str
    external_reference_hash: str
    evidence_source_hash: str
    executor_role: str
    action_submitted: bool
    delivery_confirmed: bool
    receipt_hash: str


def _sha(name: str, value: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ValueError(name + " must be lowercase SHA-256")
    return value


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


def _verify_authorization_payload_scope(
    *,
    authorization: ExternalActionAuthorization,
    proposal: CarrierActionProposal,
    payload: CarrierActionPayload,
) -> None:
    if authorization.authorization_hash is None:
        raise ValueError("authorization hash is required")
    _sha("authorization_hash", authorization.authorization_hash)
    if authorization.action_payload_hash != payload.payload_hash:
        raise ValueError("authorization payload hash mismatch")
    if authorization.action_type != payload.action_type:
        raise ValueError("authorization action type mismatch")
    if authorization.target_carrier_id != payload.target_carrier_id:
        raise ValueError("authorization carrier mismatch")
    if authorization.target_customer_id != payload.target_customer_id:
        raise ValueError("authorization customer mismatch")
    if authorization.currency != payload.currency:
        raise ValueError("authorization currency mismatch")
    if authorization.finding_ids != tuple(sorted(proposal.finding_ids)):
        raise ValueError("authorization finding set mismatch")
    if authorization.authorized_cents != payload.requested_cents:
        raise ValueError("authorization amount does not equal canonical payload amount")
    if payload.proposal_hash != proposal.proposal_hash:
        raise ValueError("payload proposal hash mismatch")


def build_carrier_action_execution_intent(
    *,
    authorization: ExternalActionAuthorization,
    proposal: CarrierActionProposal,
    payload: CarrierActionPayload,
    recovery_claims: RecoveryClaimBatch,
    prepared_at: str,
    revocations: tuple[AuthorizationRevocation, ...] = (),
) -> CarrierActionExecutionIntent:
    verify_carrier_action_payload(
        payload,
        proposal=proposal,
        recovery_claims=recovery_claims,
    )
    _verify_authorization_payload_scope(
        authorization=authorization,
        proposal=proposal,
        payload=payload,
    )
    canonical_prepared_at, prepared_dt = _timestamp("prepared_at", prepared_at)

    assert_action_allowed(
        authorization,
        as_of_date=prepared_dt.date().isoformat(),
        action_type=ActionType(payload.action_type),
        target_carrier_id=payload.target_carrier_id,
        target_customer_id=payload.target_customer_id,
        recipient_reference_hash=authorization.recipient_reference_hash,
        action_payload_hash=payload.payload_hash,
        finding_ids=proposal.finding_ids,
        currency=payload.currency,
        requested_cents=payload.requested_cents,
        revocations=revocations,
    )

    execution_key_body = {
        "schema": 1,
        "authorization_hash": authorization.authorization_hash,
        "proposal_hash": proposal.proposal_hash,
        "payload_hash": payload.payload_hash,
        "recipient_reference_hash": authorization.recipient_reference_hash,
        "action_type": payload.action_type,
        "target_carrier_id": payload.target_carrier_id,
        "target_customer_id": payload.target_customer_id,
        "currency": payload.currency,
        "finding_ids": tuple(sorted(proposal.finding_ids)),
        "requested_cents": payload.requested_cents,
    }
    execution_key = canonical_hash(execution_key_body)
    body = {
        "schema": 1,
        "execution_key": execution_key,
        "authorization_id": authorization.authorization_id,
        "authorization_hash": authorization.authorization_hash,
        "proposal_hash": proposal.proposal_hash,
        "payload_hash": payload.payload_hash,
        "recipient_reference_hash": authorization.recipient_reference_hash,
        "action_type": payload.action_type,
        "target_carrier_id": payload.target_carrier_id,
        "target_customer_id": payload.target_customer_id,
        "currency": payload.currency,
        "requested_cents": payload.requested_cents,
        "finding_ids": tuple(sorted(proposal.finding_ids)),
        "prepared_at": canonical_prepared_at,
        "subject": payload.subject,
        "body_text": payload.body_text,
    }
    return CarrierActionExecutionIntent(
        execution_key=execution_key,
        authorization_id=authorization.authorization_id,
        authorization_hash=authorization.authorization_hash,
        proposal_hash=proposal.proposal_hash,
        payload_hash=payload.payload_hash,
        recipient_reference_hash=authorization.recipient_reference_hash,
        action_type=payload.action_type,
        target_carrier_id=payload.target_carrier_id,
        target_customer_id=payload.target_customer_id,
        currency=payload.currency,
        requested_cents=payload.requested_cents,
        finding_ids=tuple(sorted(proposal.finding_ids)),
        prepared_at=canonical_prepared_at,
        subject=payload.subject,
        body_text=payload.body_text,
        intent_hash=canonical_hash(body),
    )


def verify_carrier_action_execution_intent(
    intent: CarrierActionExecutionIntent,
    *,
    authorization: ExternalActionAuthorization,
    proposal: CarrierActionProposal,
    payload: CarrierActionPayload,
    recovery_claims: RecoveryClaimBatch,
    revocations: tuple[AuthorizationRevocation, ...] = (),
) -> None:
    expected = build_carrier_action_execution_intent(
        authorization=authorization,
        proposal=proposal,
        payload=payload,
        recovery_claims=recovery_claims,
        prepared_at=intent.prepared_at,
        revocations=revocations,
    )
    if intent != expected:
        raise ValueError("carrier action execution intent does not match current proofs")


def record_carrier_action_execution(
    *,
    intent: CarrierActionExecutionIntent,
    authorization: ExternalActionAuthorization,
    proposal: CarrierActionProposal,
    payload: CarrierActionPayload,
    recovery_claims: RecoveryClaimBatch,
    evidence: CarrierActionExecutionEvidence,
    revocations: tuple[AuthorizationRevocation, ...] = (),
) -> CarrierActionExecutionReceipt:
    verify_carrier_action_execution_intent(
        intent,
        authorization=authorization,
        proposal=proposal,
        payload=payload,
        recovery_claims=recovery_claims,
        revocations=revocations,
    )
    if not isinstance(evidence, CarrierActionExecutionEvidence):
        raise ValueError("evidence must be CarrierActionExecutionEvidence")
    if evidence.execution_key != intent.execution_key:
        raise ValueError("execution evidence key mismatch")
    if not isinstance(evidence.outcome, ExecutionOutcome):
        raise ValueError("execution outcome must be ExecutionOutcome")
    if not isinstance(evidence.channel, ExecutionChannel):
        raise ValueError("execution channel must be ExecutionChannel")
    external_reference_hash = _sha(
        "external_reference_hash", evidence.external_reference_hash
    )
    evidence_source_hash = _sha(
        "evidence_source_hash", evidence.evidence_source_hash
    )
    executor_role = _text("executor_role", evidence.executor_role)
    canonical_executed_at, executed_dt = _timestamp("executed_at", evidence.executed_at)
    prepared_dt = datetime.fromisoformat(
        intent.prepared_at.replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    if executed_dt < prepared_dt:
        raise ValueError("executed_at cannot precede prepared_at")

    # Re-check authorization at the actual execution date. A revoked/expired
    # authorization must not become a successful receipt merely because an
    # earlier intent was prepared.
    assert_action_allowed(
        authorization,
        as_of_date=executed_dt.date().isoformat(),
        action_type=ActionType(payload.action_type),
        target_carrier_id=payload.target_carrier_id,
        target_customer_id=payload.target_customer_id,
        recipient_reference_hash=authorization.recipient_reference_hash,
        action_payload_hash=payload.payload_hash,
        finding_ids=proposal.finding_ids,
        currency=payload.currency,
        requested_cents=payload.requested_cents,
        revocations=revocations,
    )

    if evidence_source_hash in {
        authorization.authorization_hash,
        payload.payload_hash,
        proposal.proposal_hash,
    }:
        raise ValueError("execution evidence source must be external to existing proof objects")

    action_submitted = evidence.outcome in {
        ExecutionOutcome.SUBMITTED,
        ExecutionOutcome.DELIVERED,
    }
    delivery_confirmed = evidence.outcome is ExecutionOutcome.DELIVERED

    body = {
        "schema": 1,
        "execution_key": intent.execution_key,
        "intent_hash": intent.intent_hash,
        "authorization_id": authorization.authorization_id,
        "authorization_hash": authorization.authorization_hash,
        "proposal_hash": proposal.proposal_hash,
        "payload_hash": payload.payload_hash,
        "recipient_reference_hash": authorization.recipient_reference_hash,
        "action_type": payload.action_type,
        "target_carrier_id": payload.target_carrier_id,
        "target_customer_id": payload.target_customer_id,
        "currency": payload.currency,
        "requested_cents": payload.requested_cents,
        "finding_ids": tuple(sorted(proposal.finding_ids)),
        "prepared_at": intent.prepared_at,
        "executed_at": canonical_executed_at,
        "channel": evidence.channel.value,
        "outcome": evidence.outcome.value,
        "external_reference_hash": external_reference_hash,
        "evidence_source_hash": evidence_source_hash,
        "executor_role": executor_role,
        "action_submitted": action_submitted,
        "delivery_confirmed": delivery_confirmed,
    }
    return CarrierActionExecutionReceipt(
        execution_key=intent.execution_key,
        intent_hash=intent.intent_hash,
        authorization_id=authorization.authorization_id,
        authorization_hash=authorization.authorization_hash,
        proposal_hash=proposal.proposal_hash,
        payload_hash=payload.payload_hash,
        recipient_reference_hash=authorization.recipient_reference_hash,
        action_type=payload.action_type,
        target_carrier_id=payload.target_carrier_id,
        target_customer_id=payload.target_customer_id,
        currency=payload.currency,
        requested_cents=payload.requested_cents,
        finding_ids=tuple(sorted(proposal.finding_ids)),
        prepared_at=intent.prepared_at,
        executed_at=canonical_executed_at,
        channel=evidence.channel.value,
        outcome=evidence.outcome.value,
        external_reference_hash=external_reference_hash,
        evidence_source_hash=evidence_source_hash,
        executor_role=executor_role,
        action_submitted=action_submitted,
        delivery_confirmed=delivery_confirmed,
        receipt_hash=canonical_hash(body),
    )


def validate_execution_history(
    receipts: Iterable[CarrierActionExecutionReceipt],
) -> None:
    submitted_keys: set[str] = set()
    seen_receipts: set[str] = set()
    for receipt in receipts:
        if not isinstance(receipt, CarrierActionExecutionReceipt):
            raise ValueError("history must contain CarrierActionExecutionReceipt values")
        _sha("receipt_hash", receipt.receipt_hash)
        _sha("execution_key", receipt.execution_key)
        if receipt.receipt_hash in seen_receipts:
            raise ValueError("duplicate execution receipt")
        seen_receipts.add(receipt.receipt_hash)
        if receipt.action_submitted:
            if receipt.execution_key in submitted_keys:
                raise ValueError("multiple submitted executions share one idempotency key")
            submitted_keys.add(receipt.execution_key)


def render_execution_intent_markdown(intent: CarrierActionExecutionIntent) -> str:
    return "\n".join([
        "# Freight Recovery — Carrier Action Execution Intent",
        "",
        f"- Action: **{intent.action_type}**",
        f"- Carrier / customer: **{intent.target_carrier_id} / {intent.target_customer_id}**",
        f"- Amount: **{intent.currency} {intent.requested_cents / 100:,.2f}**",
        f"- Prepared at: **{intent.prepared_at}**",
        f"- Idempotency key: `{intent.execution_key}`",
        f"- Intent hash: `{intent.intent_hash}`",
        "",
        "This is a pre-send proof object. It does not mean the action was submitted or delivered.",
        "",
        "## Subject",
        "",
        intent.subject,
        "",
        "## Body",
        "",
        intent.body_text,
        "",
    ])


def render_execution_receipt_markdown(receipt: CarrierActionExecutionReceipt) -> str:
    return "\n".join([
        "# Freight Recovery — Carrier Action Execution Receipt",
        "",
        f"- Outcome: **{receipt.outcome}**",
        f"- Channel: **{receipt.channel}**",
        f"- Executed at: **{receipt.executed_at}**",
        f"- Action submitted: **{'yes' if receipt.action_submitted else 'no'}**",
        f"- Delivery confirmed: **{'yes' if receipt.delivery_confirmed else 'no'}**",
        f"- Idempotency key: `{receipt.execution_key}`",
        f"- Authorization: `{receipt.authorization_hash}`",
        f"- Payload: `{receipt.payload_hash}`",
        f"- External reference proof: `{receipt.external_reference_hash}`",
        f"- Execution evidence proof: `{receipt.evidence_source_hash}`",
        f"- Receipt hash: `{receipt.receipt_hash}`",
        "",
        "SUBMITTED does not mean delivery was confirmed. DELIVERED requires external delivery evidence.",
        "This receipt does not prove settlement, credit issuance, recovery, or realized savings.",
        "",
    ])
