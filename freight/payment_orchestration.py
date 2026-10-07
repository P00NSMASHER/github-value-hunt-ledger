"""Provider-neutral payment orchestration for RecoveryOS phase 2.

This module coordinates payment intent, human authorization, provider submission,
settlement evidence and reversals. It does not implement banking rails or custody.
A payment is never reported as settled until an observed provider SETTLED event
exists, and a later REVERSED event returns settled value to zero.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable

from freight.contracts import canonical_hash

MAX_CENTS = 2**63 - 1
PROVIDER_STATES = {"SUBMITTED", "ACCEPTED", "SETTLED", "FAILED", "REVERSED"}
TRANSITIONS = {
    "AUTHORIZED": {"SUBMITTED"},
    "SUBMITTED": {"ACCEPTED", "FAILED"},
    "ACCEPTED": {"SETTLED", "FAILED"},
    "SETTLED": {"REVERSED"},
    "FAILED": set(),
    "REVERSED": set(),
}


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    value = value.strip()
    if any(ord(ch) < 32 for ch in value):
        raise ValueError(f"{name} contains control characters")
    return value


def _cents(name: str, value: int, *, positive: bool = False) -> int:
    minimum = 1 if positive else 0
    if type(value) is not int or value < minimum or value > MAX_CENTS:
        raise ValueError(f"{name} must be integer cents >= {minimum}")
    return value


def _timestamp(name: str, value: str) -> str:
    value = _text(name, value)
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be timezone-aware ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware ISO-8601")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class PaymentInstruction:
    instruction_id: str
    buyer_id: str
    business_unit: str
    payer_id: str
    payee_id: str
    currency: str
    amount_cents: int
    purpose: str
    finding_proof_hashes: tuple[str, ...]
    idempotency_key: str
    instruction_hash: str


@dataclass(frozen=True)
class PaymentAuthorization:
    instruction_hash: str
    authorized_cents: int
    authorized_by: str
    reason: str
    authorized_at: str
    authorization_hash: str


@dataclass(frozen=True)
class ProviderPaymentEvent:
    instruction_hash: str
    state: str
    provider: str
    provider_reference: str
    amount_cents: int
    source_hash: str
    occurred_at: str
    previous_event_hash: str | None
    event_hash: str


@dataclass(frozen=True)
class PaymentSnapshot:
    instruction_hash: str
    authorization_hash: str | None
    current_state: str
    settled_cents: int
    event_hashes: tuple[str, ...]
    snapshot_hash: str


def prepare_payment_instruction(
    *,
    instruction_id: str,
    buyer_id: str,
    business_unit: str,
    payer_id: str,
    payee_id: str,
    currency: str,
    amount_cents: int,
    purpose: str,
    finding_proof_hashes: Iterable[str],
    idempotency_key: str,
) -> PaymentInstruction:
    fields = {
        "instruction_id": _text("instruction_id", instruction_id),
        "buyer_id": _text("buyer_id", buyer_id),
        "business_unit": _text("business_unit", business_unit),
        "payer_id": _text("payer_id", payer_id),
        "payee_id": _text("payee_id", payee_id),
        "currency": _text("currency", currency).upper(),
        "amount_cents": _cents("amount_cents", amount_cents, positive=True),
        "purpose": _text("purpose", purpose),
        "idempotency_key": _text("idempotency_key", idempotency_key),
    }
    if len(fields["currency"]) != 3 or not fields["currency"].isalpha():
        raise ValueError("currency must be three letters")
    proofs = tuple(sorted({_text("finding_proof_hash", x) for x in finding_proof_hashes}))
    if not proofs:
        raise ValueError("payment instruction requires at least one finding proof")
    body = {"schema": 1, **fields, "finding_proof_hashes": proofs}
    return PaymentInstruction(
        **fields,
        finding_proof_hashes=proofs,
        instruction_hash=canonical_hash(body),
    )


def authorize_payment(
    instruction: PaymentInstruction,
    *,
    authorized_by: str,
    reason: str,
    authorized_at: str,
) -> PaymentAuthorization:
    authorized_by = _text("authorized_by", authorized_by)
    reason = _text("reason", reason)
    authorized_at = _timestamp("authorized_at", authorized_at)
    body = {
        "schema": 1,
        "instruction_hash": instruction.instruction_hash,
        "authorized_cents": instruction.amount_cents,
        "authorized_by": authorized_by,
        "reason": reason,
        "authorized_at": authorized_at,
    }
    return PaymentAuthorization(
        instruction_hash=instruction.instruction_hash,
        authorized_cents=instruction.amount_cents,
        authorized_by=authorized_by,
        reason=reason,
        authorized_at=authorized_at,
        authorization_hash=canonical_hash(body),
    )


class PaymentOrchestrator:
    def __init__(self, instruction: PaymentInstruction):
        self.instruction = instruction
        self.authorization: PaymentAuthorization | None = None
        self.events: list[ProviderPaymentEvent] = []

    @property
    def current_state(self) -> str:
        if self.events:
            return self.events[-1].state
        return "AUTHORIZED" if self.authorization is not None else "PREPARED"

    def authorize(self, authorization: PaymentAuthorization) -> None:
        if self.authorization is not None:
            if self.authorization.authorization_hash == authorization.authorization_hash:
                return
            raise ValueError("payment instruction already authorized differently")
        if authorization.instruction_hash != self.instruction.instruction_hash:
            raise ValueError("authorization is not bound to this instruction")
        if authorization.authorized_cents != self.instruction.amount_cents:
            raise ValueError("authorization amount mismatch")
        self.authorization = authorization

    def record_provider_event(
        self,
        *,
        state: str,
        provider: str,
        provider_reference: str,
        amount_cents: int,
        source_hash: str,
        occurred_at: str,
    ) -> ProviderPaymentEvent:
        if self.authorization is None:
            raise ValueError("provider payment event requires prior human authorization")
        if state not in PROVIDER_STATES:
            raise ValueError("unsupported provider payment state")
        prior = self.current_state
        if state not in TRANSITIONS.get(prior, set()):
            raise ValueError(f"invalid payment transition {prior} -> {state}")
        provider = _text("provider", provider)
        provider_reference = _text("provider_reference", provider_reference)
        source_hash = _text("source_hash", source_hash)
        occurred_at = _timestamp("occurred_at", occurred_at)
        amount_cents = _cents("amount_cents", amount_cents, positive=True)
        if amount_cents != self.instruction.amount_cents:
            raise ValueError("provider event amount must match payment instruction")
        if self.events and occurred_at < self.events[-1].occurred_at:
            raise ValueError("provider event predates prior event")
        previous = self.events[-1].event_hash if self.events else None
        body = {
            "schema": 1,
            "instruction_hash": self.instruction.instruction_hash,
            "state": state,
            "provider": provider,
            "provider_reference": provider_reference,
            "amount_cents": amount_cents,
            "source_hash": source_hash,
            "occurred_at": occurred_at,
            "previous_event_hash": previous,
        }
        event = ProviderPaymentEvent(
            instruction_hash=self.instruction.instruction_hash,
            state=state,
            provider=provider,
            provider_reference=provider_reference,
            amount_cents=amount_cents,
            source_hash=source_hash,
            occurred_at=occurred_at,
            previous_event_hash=previous,
            event_hash=canonical_hash(body),
        )
        self.events.append(event)
        return event

    def snapshot(self) -> PaymentSnapshot:
        state = self.current_state
        settled = self.instruction.amount_cents if state == "SETTLED" else 0
        body = {
            "schema": 1,
            "instruction_hash": self.instruction.instruction_hash,
            "authorization_hash": self.authorization.authorization_hash if self.authorization else None,
            "current_state": state,
            "settled_cents": settled,
            "event_hashes": [event.event_hash for event in self.events],
        }
        return PaymentSnapshot(
            instruction_hash=self.instruction.instruction_hash,
            authorization_hash=self.authorization.authorization_hash if self.authorization else None,
            current_state=state,
            settled_cents=settled,
            event_hashes=tuple(event.event_hash for event in self.events),
            snapshot_hash=canonical_hash(body),
        )


def verify_payment_snapshot(
    instruction: PaymentInstruction,
    authorization: PaymentAuthorization | None,
    events: Iterable[ProviderPaymentEvent],
    expected: PaymentSnapshot,
) -> None:
    orchestrator = PaymentOrchestrator(instruction)
    if authorization is not None:
        orchestrator.authorize(authorization)
    for event in events:
        replay = orchestrator.record_provider_event(
            state=event.state,
            provider=event.provider,
            provider_reference=event.provider_reference,
            amount_cents=event.amount_cents,
            source_hash=event.source_hash,
            occurred_at=event.occurred_at,
        )
        if replay.event_hash != event.event_hash:
            raise ValueError("payment event hash mismatch")
    if orchestrator.snapshot() != expected:
        raise ValueError("payment snapshot mismatch")
