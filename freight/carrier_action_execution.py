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
    buyer_id: str
    business_unit: str
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
    buyer_id: str
    business_unit: str
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


@dataclass(frozen=True)
class CarrierActionDeliveryEvidence:
    execution_key: str
    submitted_receipt_hash: str
    delivered_at: str
    delivery_reference_hash: str
    evidence_source_hash: str
    verifier_role: str


@dataclass(frozen=True)
class CarrierActionDeliveryReceipt:
    execution_key: str
    buyer_id: str
    business_unit: str
    submitted_receipt_hash: str
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
    submitted_at: str
    delivered_at: str
    channel: str
    submission_external_reference_hash: str
    delivery_reference_hash: str
    delivery_evidence_source_hash: str
    verifier_role: str
    delivery_confirmed: bool
    delivery_receipt_hash: str


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
    if (authorization.buyer_id, authorization.business_unit) != (
        proposal.buyer_id, proposal.business_unit,
    ):
        raise ValueError("authorization scope mismatch with carrier action proposal")
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
        "buyer_id": authorization.buyer_id,
        "business_unit": authorization.business_unit,
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
        "buyer_id": authorization.buyer_id,
        "business_unit": authorization.business_unit,
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
        buyer_id=authorization.buyer_id,
        business_unit=authorization.business_unit,
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


def verify_carrier_action_execution_intent_proof(
    intent: CarrierActionExecutionIntent,
) -> None:
    if not isinstance(intent, CarrierActionExecutionIntent):
        raise ValueError("intent must be a CarrierActionExecutionIntent")
    for name in (
        "execution_key",
        "authorization_hash",
        "proposal_hash",
        "payload_hash",
        "recipient_reference_hash",
        "intent_hash",
    ):
        _sha(name, getattr(intent, name))
    for name in (
        "buyer_id",
        "business_unit",
        "authorization_id",
        "action_type",
        "target_carrier_id",
        "target_customer_id",
        "currency",
        "subject",
        "body_text",
    ):
        _text(name, getattr(intent, name))
    if type(intent.requested_cents) is not int or intent.requested_cents <= 0:
        raise ValueError("requested_cents must be a positive integer")
    if not intent.finding_ids or len(intent.finding_ids) != len(set(intent.finding_ids)):
        raise ValueError("finding_ids must be a non-empty unique tuple")
    if intent.finding_ids != tuple(sorted(intent.finding_ids)):
        raise ValueError("finding_ids must be in canonical sorted order")
    canonical_prepared_at, _ = _timestamp("prepared_at", intent.prepared_at)
    if canonical_prepared_at != intent.prepared_at:
        raise ValueError("prepared_at must be canonical UTC")

    execution_key_body = {
        "schema": 1,
        "buyer_id": intent.buyer_id,
        "business_unit": intent.business_unit,
        "authorization_hash": intent.authorization_hash,
        "proposal_hash": intent.proposal_hash,
        "payload_hash": intent.payload_hash,
        "recipient_reference_hash": intent.recipient_reference_hash,
        "action_type": intent.action_type,
        "target_carrier_id": intent.target_carrier_id,
        "target_customer_id": intent.target_customer_id,
        "currency": intent.currency,
        "finding_ids": tuple(sorted(intent.finding_ids)),
        "requested_cents": intent.requested_cents,
    }
    if canonical_hash(execution_key_body) != intent.execution_key:
        raise ValueError("execution intent idempotency key mismatch")

    body = {
        "schema": 1,
        "execution_key": intent.execution_key,
        "buyer_id": intent.buyer_id,
        "business_unit": intent.business_unit,
        "authorization_id": intent.authorization_id,
        "authorization_hash": intent.authorization_hash,
        "proposal_hash": intent.proposal_hash,
        "payload_hash": intent.payload_hash,
        "recipient_reference_hash": intent.recipient_reference_hash,
        "action_type": intent.action_type,
        "target_carrier_id": intent.target_carrier_id,
        "target_customer_id": intent.target_customer_id,
        "currency": intent.currency,
        "requested_cents": intent.requested_cents,
        "finding_ids": tuple(sorted(intent.finding_ids)),
        "prepared_at": intent.prepared_at,
        "subject": intent.subject,
        "body_text": intent.body_text,
    }
    if canonical_hash(body) != intent.intent_hash:
        raise ValueError("execution intent hash mismatch")


def verify_carrier_action_execution_intent(
    intent: CarrierActionExecutionIntent,
    *,
    authorization: ExternalActionAuthorization,
    proposal: CarrierActionProposal,
    payload: CarrierActionPayload,
    recovery_claims: RecoveryClaimBatch,
    revocations: tuple[AuthorizationRevocation, ...] = (),
) -> None:
    verify_carrier_action_execution_intent_proof(intent)
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
        "buyer_id": authorization.buyer_id,
        "business_unit": authorization.business_unit,
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
        buyer_id=authorization.buyer_id,
        business_unit=authorization.business_unit,
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


def verify_carrier_action_execution_receipt(
    receipt: CarrierActionExecutionReceipt,
) -> None:
    if not isinstance(receipt, CarrierActionExecutionReceipt):
        raise ValueError("receipt must be a CarrierActionExecutionReceipt")
    _sha("execution_key", receipt.execution_key)
    _sha("intent_hash", receipt.intent_hash)
    _sha("authorization_hash", receipt.authorization_hash)
    _sha("proposal_hash", receipt.proposal_hash)
    _sha("payload_hash", receipt.payload_hash)
    _sha("recipient_reference_hash", receipt.recipient_reference_hash)
    _sha("external_reference_hash", receipt.external_reference_hash)
    _sha("evidence_source_hash", receipt.evidence_source_hash)
    _sha("receipt_hash", receipt.receipt_hash)
    _text("buyer_id", receipt.buyer_id)
    _text("business_unit", receipt.business_unit)
    _text("authorization_id", receipt.authorization_id)
    _text("target_carrier_id", receipt.target_carrier_id)
    _text("target_customer_id", receipt.target_customer_id)
    _text("currency", receipt.currency)
    _text("executor_role", receipt.executor_role)
    _timestamp("prepared_at", receipt.prepared_at)
    _timestamp("executed_at", receipt.executed_at)
    try:
        outcome = ExecutionOutcome(receipt.outcome)
    except ValueError as exc:
        raise ValueError("invalid execution receipt outcome") from exc
    try:
        ExecutionChannel(receipt.channel)
    except ValueError as exc:
        raise ValueError("invalid execution receipt channel") from exc
    expected_submitted = outcome in {
        ExecutionOutcome.SUBMITTED,
        ExecutionOutcome.DELIVERED,
    }
    expected_delivered = outcome is ExecutionOutcome.DELIVERED
    if receipt.action_submitted is not expected_submitted:
        raise ValueError("execution receipt submitted flag mismatch")
    if receipt.delivery_confirmed is not expected_delivered:
        raise ValueError("execution receipt delivery flag mismatch")
    fields = asdict(receipt)
    digest = fields.pop("receipt_hash")
    body = {"schema": 1, **fields}
    if canonical_hash(body) != digest:
        raise ValueError("execution receipt hash mismatch")


def record_carrier_action_delivery_confirmation(
    *,
    submitted_receipt: CarrierActionExecutionReceipt,
    evidence: CarrierActionDeliveryEvidence,
) -> CarrierActionDeliveryReceipt:
    verify_carrier_action_execution_receipt(submitted_receipt)
    if not submitted_receipt.action_submitted:
        raise ValueError("delivery confirmation requires a submitted execution receipt")
    if submitted_receipt.delivery_confirmed:
        raise ValueError("execution receipt already confirms delivery")
    if not isinstance(evidence, CarrierActionDeliveryEvidence):
        raise ValueError("evidence must be CarrierActionDeliveryEvidence")
    if evidence.execution_key != submitted_receipt.execution_key:
        raise ValueError("delivery evidence execution key mismatch")
    if evidence.submitted_receipt_hash != submitted_receipt.receipt_hash:
        raise ValueError("delivery evidence submitted receipt hash mismatch")

    delivery_reference_hash = _sha(
        "delivery_reference_hash", evidence.delivery_reference_hash
    )
    delivery_evidence_source_hash = _sha(
        "delivery evidence_source_hash", evidence.evidence_source_hash
    )
    verifier_role = _text("verifier_role", evidence.verifier_role)
    canonical_delivered_at, delivered_dt = _timestamp(
        "delivered_at", evidence.delivered_at
    )
    submitted_dt = datetime.fromisoformat(
        submitted_receipt.executed_at.replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    if delivered_dt < submitted_dt:
        raise ValueError("delivered_at cannot precede submitted execution time")

    if delivery_evidence_source_hash in {
        submitted_receipt.receipt_hash,
        submitted_receipt.authorization_hash,
        submitted_receipt.proposal_hash,
        submitted_receipt.payload_hash,
        submitted_receipt.evidence_source_hash,
    }:
        raise ValueError("delivery evidence source must be external and new")

    body = {
        "schema": 1,
        "execution_key": submitted_receipt.execution_key,
        "buyer_id": submitted_receipt.buyer_id,
        "business_unit": submitted_receipt.business_unit,
        "submitted_receipt_hash": submitted_receipt.receipt_hash,
        "authorization_hash": submitted_receipt.authorization_hash,
        "proposal_hash": submitted_receipt.proposal_hash,
        "payload_hash": submitted_receipt.payload_hash,
        "recipient_reference_hash": submitted_receipt.recipient_reference_hash,
        "action_type": submitted_receipt.action_type,
        "target_carrier_id": submitted_receipt.target_carrier_id,
        "target_customer_id": submitted_receipt.target_customer_id,
        "currency": submitted_receipt.currency,
        "requested_cents": submitted_receipt.requested_cents,
        "finding_ids": submitted_receipt.finding_ids,
        "submitted_at": submitted_receipt.executed_at,
        "delivered_at": canonical_delivered_at,
        "channel": submitted_receipt.channel,
        "submission_external_reference_hash": submitted_receipt.external_reference_hash,
        "delivery_reference_hash": delivery_reference_hash,
        "delivery_evidence_source_hash": delivery_evidence_source_hash,
        "verifier_role": verifier_role,
        "delivery_confirmed": True,
    }
    return CarrierActionDeliveryReceipt(
        execution_key=submitted_receipt.execution_key,
        buyer_id=submitted_receipt.buyer_id,
        business_unit=submitted_receipt.business_unit,
        submitted_receipt_hash=submitted_receipt.receipt_hash,
        authorization_hash=submitted_receipt.authorization_hash,
        proposal_hash=submitted_receipt.proposal_hash,
        payload_hash=submitted_receipt.payload_hash,
        recipient_reference_hash=submitted_receipt.recipient_reference_hash,
        action_type=submitted_receipt.action_type,
        target_carrier_id=submitted_receipt.target_carrier_id,
        target_customer_id=submitted_receipt.target_customer_id,
        currency=submitted_receipt.currency,
        requested_cents=submitted_receipt.requested_cents,
        finding_ids=submitted_receipt.finding_ids,
        submitted_at=submitted_receipt.executed_at,
        delivered_at=canonical_delivered_at,
        channel=submitted_receipt.channel,
        submission_external_reference_hash=submitted_receipt.external_reference_hash,
        delivery_reference_hash=delivery_reference_hash,
        delivery_evidence_source_hash=delivery_evidence_source_hash,
        verifier_role=verifier_role,
        delivery_confirmed=True,
        delivery_receipt_hash=canonical_hash(body),
    )


def verify_carrier_action_delivery_receipt(
    receipt: CarrierActionDeliveryReceipt,
) -> None:
    if not isinstance(receipt, CarrierActionDeliveryReceipt):
        raise ValueError("receipt must be a CarrierActionDeliveryReceipt")
    for name in (
        "execution_key",
        "submitted_receipt_hash",
        "authorization_hash",
        "proposal_hash",
        "payload_hash",
        "recipient_reference_hash",
        "submission_external_reference_hash",
        "delivery_reference_hash",
        "delivery_evidence_source_hash",
        "delivery_receipt_hash",
    ):
        _sha(name, getattr(receipt, name))
    for name in (
        "buyer_id",
        "business_unit",
        "action_type",
        "target_carrier_id",
        "target_customer_id",
        "currency",
        "channel",
        "verifier_role",
    ):
        _text(name, getattr(receipt, name))
    _, submitted_dt = _timestamp("submitted_at", receipt.submitted_at)
    _, delivered_dt = _timestamp("delivered_at", receipt.delivered_at)
    if delivered_dt < submitted_dt:
        raise ValueError("delivery receipt predates submission")
    if receipt.delivery_confirmed is not True:
        raise ValueError("delivery receipt must confirm delivery")
    fields = asdict(receipt)
    digest = fields.pop("delivery_receipt_hash")
    body = {"schema": 1, **fields}
    if canonical_hash(body) != digest:
        raise ValueError("delivery receipt hash mismatch")


def validate_delivery_history(
    receipts: Iterable[CarrierActionDeliveryReceipt],
) -> None:
    seen_execution_keys: set[str] = set()
    seen_submission_receipts: set[str] = set()
    seen_delivery_receipts: set[str] = set()
    for receipt in receipts:
        verify_carrier_action_delivery_receipt(receipt)
        if receipt.delivery_receipt_hash in seen_delivery_receipts:
            raise ValueError("duplicate delivery receipt")
        seen_delivery_receipts.add(receipt.delivery_receipt_hash)
        if receipt.execution_key in seen_execution_keys:
            raise ValueError("multiple delivery confirmations share one execution key")
        seen_execution_keys.add(receipt.execution_key)
        if receipt.submitted_receipt_hash in seen_submission_receipts:
            raise ValueError("multiple delivery confirmations reference one submission")
        seen_submission_receipts.add(receipt.submitted_receipt_hash)


def validate_execution_history(
    receipts: Iterable[CarrierActionExecutionReceipt],
) -> None:
    submitted_keys: set[str] = set()
    seen_receipts: set[str] = set()
    for receipt in receipts:
        verify_carrier_action_execution_receipt(receipt)
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
        f"- Buyer / business unit: **{intent.buyer_id} / {intent.business_unit}**",
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


def render_delivery_receipt_markdown(receipt: CarrierActionDeliveryReceipt) -> str:
    return "\n".join([
        "# Freight Recovery — Carrier Action Delivery Confirmation",
        "",
        f"- Buyer / business unit: **{receipt.buyer_id} / {receipt.business_unit}**",
        f"- Carrier / customer: **{receipt.target_carrier_id} / {receipt.target_customer_id}**",
        f"- Channel: **{receipt.channel}**",
        f"- Submitted at: **{receipt.submitted_at}**",
        f"- Delivered at: **{receipt.delivered_at}**",
        "- Delivery confirmed: **yes**",
        f"- Execution key: `{receipt.execution_key}`",
        f"- Submission receipt: `{receipt.submitted_receipt_hash}`",
        f"- Delivery reference proof: `{receipt.delivery_reference_hash}`",
        f"- Delivery evidence proof: `{receipt.delivery_evidence_source_hash}`",
        f"- Delivery receipt hash: `{receipt.delivery_receipt_hash}`",
        "",
        "Delivery confirmation does not prove settlement, credit issuance, recovery, or realized savings.",
        "",
    ])


def render_execution_receipt_markdown(receipt: CarrierActionExecutionReceipt) -> str:
    return "\n".join([
        "# Freight Recovery — Carrier Action Execution Receipt",
        "",
        f"- Outcome: **{receipt.outcome}**",
        f"- Buyer / business unit: **{receipt.buyer_id} / {receipt.business_unit}**",
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
