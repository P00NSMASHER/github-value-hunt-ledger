"""Verified buyer closeout acknowledgment for RecoveryWorks pilots.

This layer records a separately sourced buyer acknowledgment of the exact
closeout surfaces. It cannot create an invoice, assert payment due, authorize
continuation, or perform an external action.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from recoveryworks.models import (
    canonical_hash,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)
from recoveryworks.pilot_charter import RecoveryWorksPilotCharter
from recoveryworks.pilot_closeout import PilotCloseoutSnapshot


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


class ContinuationInterest(str, Enum):
    NO_DECISION = "NO_DECISION"
    STOP_AFTER_PILOT = "STOP_AFTER_PILOT"
    REVIEW_MONTHLY_ASSURANCE = "REVIEW_MONTHLY_ASSURANCE"


@dataclass(frozen=True)
class ExternalBuyerCloseoutReceipt:
    receipt_id: str
    closeout_id: str
    closeout_proof_hash: str
    charter_id: str
    charter_proof_hash: str
    engagement_id: str
    buyer_id: str
    buyer_reviewer_id: str
    acknowledged_at: str
    currency: str
    recovered_cash_cents: int
    validated_recovery_cents: int
    prospective_savings_cents: int
    realized_savings_cents: int
    anomaly_exposure_cents: int
    reconciliation_drift_cents: int
    accepts_recovery_outcomes: bool
    accepts_savings_outcomes: bool
    open_dispute_count: int
    continuation_interest: ContinuationInterest
    source_hash: str
    source_locator: str
    verified: bool
    continuation_authorized: bool = False
    invoice_authorized: bool = False
    payment_due_asserted: bool = False
    external_action_authorized: bool = False

    def __post_init__(self) -> None:
        for name in (
            "closeout_id", "charter_id", "engagement_id", "buyer_id",
            "buyer_reviewer_id", "currency", "source_locator",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in ("closeout_proof_hash", "charter_proof_hash"):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self, "acknowledged_at",
            normalize_utc_timestamp("acknowledged_at", self.acknowledged_at),
        )
        cents_fields = (
            "recovered_cash_cents", "validated_recovery_cents",
            "prospective_savings_cents", "realized_savings_cents",
            "anomaly_exposure_cents", "reconciliation_drift_cents",
        )
        for name in cents_fields:
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        for name in ("accepts_recovery_outcomes", "accepts_savings_outcomes", "verified"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")
        if type(self.open_dispute_count) is not int or self.open_dispute_count < 0:
            raise ValueError("open_dispute_count must be non-negative")
        if not isinstance(self.continuation_interest, ContinuationInterest):
            raise ValueError("continuation_interest must be ContinuationInterest")
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if not self.verified:
            raise ValueError("buyer closeout receipt must be externally verified")
        if (
            self.continuation_authorized
            or self.invoice_authorized
            or self.payment_due_asserted
            or self.external_action_authorized
        ):
            raise ValueError("buyer closeout receipt cannot create commercial commitments")
        expected = "recoveryworks-buyer-closeout-receipt:" + canonical_hash(
            self._identity()
        )
        if self.receipt_id != expected:
            raise ValueError("receipt_id does not bind buyer closeout receipt")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "closeout_id": self.closeout_id,
            "closeout_proof_hash": self.closeout_proof_hash,
            "charter_id": self.charter_id,
            "charter_proof_hash": self.charter_proof_hash,
            "engagement_id": self.engagement_id,
            "buyer_id": self.buyer_id,
            "buyer_reviewer_id": self.buyer_reviewer_id,
            "acknowledged_at": self.acknowledged_at,
            "currency": self.currency,
            "recovered_cash_cents": self.recovered_cash_cents,
            "validated_recovery_cents": self.validated_recovery_cents,
            "prospective_savings_cents": self.prospective_savings_cents,
            "realized_savings_cents": self.realized_savings_cents,
            "anomaly_exposure_cents": self.anomaly_exposure_cents,
            "reconciliation_drift_cents": self.reconciliation_drift_cents,
            "accepts_recovery_outcomes": self.accepts_recovery_outcomes,
            "accepts_savings_outcomes": self.accepts_savings_outcomes,
            "open_dispute_count": self.open_dispute_count,
            "continuation_interest": self.continuation_interest.value,
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": True,
            "continuation_authorized": False,
            "invoice_authorized": False,
            "payment_due_asserted": False,
            "external_action_authorized": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_external_buyer_closeout_receipt(
    closeout: PilotCloseoutSnapshot,
    charter: RecoveryWorksPilotCharter,
    *,
    buyer_reviewer_id: str,
    acknowledged_at: str,
    recovered_cash_cents: int,
    validated_recovery_cents: int,
    prospective_savings_cents: int,
    realized_savings_cents: int,
    anomaly_exposure_cents: int,
    reconciliation_drift_cents: int,
    accepts_recovery_outcomes: bool,
    accepts_savings_outcomes: bool,
    open_dispute_count: int,
    continuation_interest: ContinuationInterest,
    source_hash: str,
    source_locator: str,
    verified: bool,
) -> ExternalBuyerCloseoutReceipt:
    if closeout.charter_id != charter.charter_id:
        raise ValueError("closeout charter id mismatch")
    if closeout.charter_proof_hash != charter.proof_hash:
        raise ValueError("closeout charter proof mismatch")
    values = {
        "recovered_cash_cents": recovered_cash_cents,
        "validated_recovery_cents": validated_recovery_cents,
        "prospective_savings_cents": prospective_savings_cents,
        "realized_savings_cents": realized_savings_cents,
        "anomaly_exposure_cents": anomaly_exposure_cents,
        "reconciliation_drift_cents": reconciliation_drift_cents,
    }
    identity = {
        "schema": 1,
        "closeout_id": closeout.closeout_id,
        "closeout_proof_hash": closeout.proof_hash,
        "charter_id": charter.charter_id,
        "charter_proof_hash": charter.proof_hash,
        "engagement_id": charter.engagement_id,
        "buyer_id": charter.buyer_id,
        "buyer_reviewer_id": _text("buyer_reviewer_id", buyer_reviewer_id),
        "acknowledged_at": normalize_utc_timestamp("acknowledged_at", acknowledged_at),
        "currency": closeout.currency,
        **values,
        "accepts_recovery_outcomes": accepts_recovery_outcomes,
        "accepts_savings_outcomes": accepts_savings_outcomes,
        "open_dispute_count": open_dispute_count,
        "continuation_interest": continuation_interest.value,
        "source_hash": normalize_source_hash(source_hash),
        "source_locator": _text("source_locator", source_locator),
        "verified": verified,
        "continuation_authorized": False,
        "invoice_authorized": False,
        "payment_due_asserted": False,
        "external_action_authorized": False,
    }
    return ExternalBuyerCloseoutReceipt(
        receipt_id="recoveryworks-buyer-closeout-receipt:" + canonical_hash(identity),
        closeout_id=closeout.closeout_id,
        closeout_proof_hash=closeout.proof_hash,
        charter_id=charter.charter_id,
        charter_proof_hash=charter.proof_hash,
        engagement_id=charter.engagement_id,
        buyer_id=charter.buyer_id,
        buyer_reviewer_id=buyer_reviewer_id,
        acknowledged_at=acknowledged_at,
        currency=closeout.currency,
        recovered_cash_cents=recovered_cash_cents,
        validated_recovery_cents=validated_recovery_cents,
        prospective_savings_cents=prospective_savings_cents,
        realized_savings_cents=realized_savings_cents,
        anomaly_exposure_cents=anomaly_exposure_cents,
        reconciliation_drift_cents=reconciliation_drift_cents,
        accepts_recovery_outcomes=accepts_recovery_outcomes,
        accepts_savings_outcomes=accepts_savings_outcomes,
        open_dispute_count=open_dispute_count,
        continuation_interest=continuation_interest,
        source_hash=source_hash,
        source_locator=source_locator,
        verified=verified,
    )


@dataclass(frozen=True)
class PilotCloseoutAcknowledgment:
    acknowledgment_id: str
    closeout_proof_hash: str
    buyer_receipt_proof_hash: str
    engagement_id: str
    buyer_id: str
    continuation_interest: ContinuationInterest
    acknowledged_at: str
    outcome_surfaces_accepted: bool = True
    unresolved_disputes: bool = False
    continuation_authorized: bool = False
    invoice_authorized: bool = False
    payment_due_asserted: bool = False

    def __post_init__(self) -> None:
        for name in ("closeout_proof_hash", "buyer_receipt_proof_hash"):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self, "acknowledged_at",
            normalize_utc_timestamp("acknowledged_at", self.acknowledged_at),
        )
        if not self.outcome_surfaces_accepted or self.unresolved_disputes:
            raise ValueError("acknowledgment requires accepted outcomes and no disputes")
        if self.continuation_authorized or self.invoice_authorized or self.payment_due_asserted:
            raise ValueError("closeout acknowledgment cannot authorize commercial action")
        expected = "recoveryworks-closeout-acknowledgment:" + canonical_hash(
            self._identity()
        )
        if self.acknowledgment_id != expected:
            raise ValueError("acknowledgment_id does not bind closeout acknowledgment")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "closeout_proof_hash": self.closeout_proof_hash,
            "buyer_receipt_proof_hash": self.buyer_receipt_proof_hash,
            "engagement_id": self.engagement_id,
            "buyer_id": self.buyer_id,
            "continuation_interest": self.continuation_interest.value,
            "acknowledged_at": self.acknowledged_at,
            "outcome_surfaces_accepted": True,
            "unresolved_disputes": False,
            "continuation_authorized": False,
            "invoice_authorized": False,
            "payment_due_asserted": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "acknowledgment_id": self.acknowledgment_id,
            "proof_hash": self.proof_hash,
            "state": "PILOT_CLOSEOUT_ACKNOWLEDGED",
        }


def verify_buyer_closeout_acknowledgment(
    closeout: PilotCloseoutSnapshot,
    charter: RecoveryWorksPilotCharter,
    receipt: ExternalBuyerCloseoutReceipt,
) -> PilotCloseoutAcknowledgment:
    if receipt.closeout_id != closeout.closeout_id:
        raise ValueError("buyer receipt closeout id mismatch")
    if receipt.closeout_proof_hash != closeout.proof_hash:
        raise ValueError("buyer receipt closeout proof mismatch")
    if receipt.charter_id != charter.charter_id or receipt.charter_proof_hash != charter.proof_hash:
        raise ValueError("buyer receipt charter mismatch")
    if receipt.engagement_id != charter.engagement_id or receipt.buyer_id != charter.buyer_id:
        raise ValueError("buyer receipt engagement/buyer mismatch")
    if receipt.currency != closeout.currency:
        raise ValueError("buyer receipt currency mismatch")
    comparisons = {
        "recovered_cash_cents": closeout.recovered_cash_cents,
        "validated_recovery_cents": closeout.validated_recovery_cents,
        "prospective_savings_cents": closeout.prospective_savings_cents,
        "realized_savings_cents": closeout.realized_savings_cents,
        "anomaly_exposure_cents": closeout.anomaly_exposure_cents,
        "reconciliation_drift_cents": closeout.reconciliation_drift_cents,
    }
    for name, expected in comparisons.items():
        if getattr(receipt, name) != expected:
            raise ValueError(f"buyer receipt {name} mismatch")
    if not receipt.accepts_recovery_outcomes or not receipt.accepts_savings_outcomes:
        raise ValueError("buyer did not accept all closeout outcome surfaces")
    if receipt.open_dispute_count:
        raise ValueError("buyer closeout receipt has unresolved disputes")
    identity = {
        "schema": 1,
        "closeout_proof_hash": closeout.proof_hash,
        "buyer_receipt_proof_hash": receipt.proof_hash,
        "engagement_id": charter.engagement_id,
        "buyer_id": charter.buyer_id,
        "continuation_interest": receipt.continuation_interest.value,
        "acknowledged_at": receipt.acknowledged_at,
        "outcome_surfaces_accepted": True,
        "unresolved_disputes": False,
        "continuation_authorized": False,
        "invoice_authorized": False,
        "payment_due_asserted": False,
    }
    return PilotCloseoutAcknowledgment(
        acknowledgment_id="recoveryworks-closeout-acknowledgment:"
        + canonical_hash(identity),
        closeout_proof_hash=closeout.proof_hash,
        buyer_receipt_proof_hash=receipt.proof_hash,
        engagement_id=charter.engagement_id,
        buyer_id=charter.buyer_id,
        continuation_interest=receipt.continuation_interest,
        acknowledged_at=receipt.acknowledged_at,
        outcome_surfaces_accepted=True,
        unresolved_disputes=False,
        continuation_authorized=False,
        invoice_authorized=False,
        payment_due_asserted=False,
    )
