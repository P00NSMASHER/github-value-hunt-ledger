"""Finalized commercial agreement receipt and fee-draft readiness gate.

RecoveryWorks records a separately finalized agreement and computes arithmetic
from that agreement plus verified recovered cash. It does not issue an invoice,
assert payment due, collect money, or create a contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from recoveryworks.models import (
    canonical_hash,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)
from recoveryworks.pilot_charter import RecoveryWorksPilotCharter
from recoveryworks.pilot_closeout import PilotCloseoutSnapshot
from recoveryworks.pilot_closeout_acknowledgment import PilotCloseoutAcknowledgment


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


@dataclass(frozen=True)
class FinalizedCommercialAgreementReceipt:
    agreement_receipt_id: str
    agreement_reference: str
    engagement_id: str
    buyer_id: str
    charter_id: str
    charter_proof_hash: str
    closeout_acknowledgment_proof_hash: str
    currency: str
    diagnostic_fee_cents: int
    recovered_cash_success_fee_bps: int
    monthly_assurance_fee_cents: int
    payment_terms_days: int
    diagnostic_fee_applicable: bool
    success_fee_applicable: bool
    monthly_assurance_separately_accepted: bool
    effective_at: str
    source_hash: str
    source_locator: str
    verified: bool
    externally_finalized: bool
    created_by_recoveryworks: bool = False
    invoice_issued: bool = False
    payment_due_asserted: bool = False
    payment_collected: bool = False

    def __post_init__(self) -> None:
        for name in (
            "agreement_reference", "engagement_id", "buyer_id",
            "charter_id", "currency", "source_locator",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in ("charter_proof_hash", "closeout_acknowledgment_proof_hash"):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        for name in ("diagnostic_fee_cents", "monthly_assurance_fee_cents"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if (
            type(self.recovered_cash_success_fee_bps) is not int
            or not 0 <= self.recovered_cash_success_fee_bps <= 10000
        ):
            raise ValueError("recovered_cash_success_fee_bps must be in 0..10000")
        if type(self.payment_terms_days) is not int or not 1 <= self.payment_terms_days <= 365:
            raise ValueError("payment_terms_days must be in 1..365")
        for name in (
            "diagnostic_fee_applicable", "success_fee_applicable",
            "monthly_assurance_separately_accepted", "verified",
            "externally_finalized",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")
        if not self.verified:
            raise ValueError("commercial agreement receipt must be externally verified")
        if not self.externally_finalized:
            raise ValueError("commercial agreement receipt must represent finalized external agreement")
        object.__setattr__(
            self, "effective_at",
            normalize_utc_timestamp("effective_at", self.effective_at),
        )
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if (
            self.created_by_recoveryworks
            or self.invoice_issued
            or self.payment_due_asserted
            or self.payment_collected
        ):
            raise ValueError("agreement receipt cannot manufacture contract/billing/payment events")
        expected = "recoveryworks-finalized-agreement:" + canonical_hash(
            self._identity()
        )
        if self.agreement_receipt_id != expected:
            raise ValueError("agreement_receipt_id does not bind finalized agreement")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "agreement_reference": self.agreement_reference,
            "engagement_id": self.engagement_id,
            "buyer_id": self.buyer_id,
            "charter_id": self.charter_id,
            "charter_proof_hash": self.charter_proof_hash,
            "closeout_acknowledgment_proof_hash":
                self.closeout_acknowledgment_proof_hash,
            "currency": self.currency,
            "diagnostic_fee_cents": self.diagnostic_fee_cents,
            "recovered_cash_success_fee_bps":
                self.recovered_cash_success_fee_bps,
            "monthly_assurance_fee_cents": self.monthly_assurance_fee_cents,
            "payment_terms_days": self.payment_terms_days,
            "diagnostic_fee_applicable": self.diagnostic_fee_applicable,
            "success_fee_applicable": self.success_fee_applicable,
            "monthly_assurance_separately_accepted":
                self.monthly_assurance_separately_accepted,
            "effective_at": self.effective_at,
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": True,
            "externally_finalized": True,
            "created_by_recoveryworks": False,
            "invoice_issued": False,
            "payment_due_asserted": False,
            "payment_collected": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_external_finalized_commercial_agreement(
    charter: RecoveryWorksPilotCharter,
    closeout_ack: PilotCloseoutAcknowledgment,
    *,
    agreement_reference: str,
    currency: str,
    diagnostic_fee_cents: int,
    recovered_cash_success_fee_bps: int,
    monthly_assurance_fee_cents: int,
    payment_terms_days: int,
    diagnostic_fee_applicable: bool,
    success_fee_applicable: bool,
    monthly_assurance_separately_accepted: bool,
    effective_at: str,
    source_hash: str,
    source_locator: str,
    verified: bool,
    externally_finalized: bool,
) -> FinalizedCommercialAgreementReceipt:
    if closeout_ack.engagement_id != charter.engagement_id:
        raise ValueError("closeout acknowledgment engagement mismatch")
    if closeout_ack.buyer_id != charter.buyer_id:
        raise ValueError("closeout acknowledgment buyer mismatch")
    identity = {
        "schema": 1,
        "agreement_reference": _text("agreement_reference", agreement_reference),
        "engagement_id": charter.engagement_id,
        "buyer_id": charter.buyer_id,
        "charter_id": charter.charter_id,
        "charter_proof_hash": charter.proof_hash,
        "closeout_acknowledgment_proof_hash": closeout_ack.proof_hash,
        "currency": _text("currency", currency).upper(),
        "diagnostic_fee_cents": diagnostic_fee_cents,
        "recovered_cash_success_fee_bps": recovered_cash_success_fee_bps,
        "monthly_assurance_fee_cents": monthly_assurance_fee_cents,
        "payment_terms_days": payment_terms_days,
        "diagnostic_fee_applicable": diagnostic_fee_applicable,
        "success_fee_applicable": success_fee_applicable,
        "monthly_assurance_separately_accepted":
            monthly_assurance_separately_accepted,
        "effective_at": normalize_utc_timestamp("effective_at", effective_at),
        "source_hash": normalize_source_hash(source_hash),
        "source_locator": _text("source_locator", source_locator),
        "verified": verified,
        "externally_finalized": externally_finalized,
        "created_by_recoveryworks": False,
        "invoice_issued": False,
        "payment_due_asserted": False,
        "payment_collected": False,
    }
    return FinalizedCommercialAgreementReceipt(
        agreement_receipt_id="recoveryworks-finalized-agreement:"
        + canonical_hash(identity),
        agreement_reference=agreement_reference,
        engagement_id=charter.engagement_id,
        buyer_id=charter.buyer_id,
        charter_id=charter.charter_id,
        charter_proof_hash=charter.proof_hash,
        closeout_acknowledgment_proof_hash=closeout_ack.proof_hash,
        currency=currency.upper(),
        diagnostic_fee_cents=diagnostic_fee_cents,
        recovered_cash_success_fee_bps=recovered_cash_success_fee_bps,
        monthly_assurance_fee_cents=monthly_assurance_fee_cents,
        payment_terms_days=payment_terms_days,
        diagnostic_fee_applicable=diagnostic_fee_applicable,
        success_fee_applicable=success_fee_applicable,
        monthly_assurance_separately_accepted=
            monthly_assurance_separately_accepted,
        effective_at=effective_at,
        source_hash=source_hash,
        source_locator=source_locator,
        verified=verified,
        externally_finalized=externally_finalized,
        created_by_recoveryworks=False,
        invoice_issued=False,
        payment_due_asserted=False,
        payment_collected=False,
    )


@dataclass(frozen=True)
class CommercialFeeDraftReadiness:
    readiness_id: str
    agreement_receipt_proof_hash: str
    closeout_acknowledgment_proof_hash: str
    closeout_proof_hash: str
    engagement_id: str
    buyer_id: str
    currency: str
    recovered_cash_cents: int
    diagnostic_fee_cents_agreed: int
    recovered_cash_success_fee_bps_agreed: int
    recovered_cash_success_fee_cents: int
    closeout_fee_total_cents: int
    monthly_assurance_fee_cents_agreed: int
    monthly_assurance_separately_accepted: bool
    payment_terms_days: int
    pricing_differs_from_charter_hypothesis: bool
    invoice_draft_allowed: bool = True
    invoice_issuance_performed: bool = False
    payment_due_asserted: bool = False
    payment_collected: bool = False
    external_action_performed: bool = False

    def __post_init__(self) -> None:
        for name in (
            "agreement_receipt_proof_hash",
            "closeout_acknowledgment_proof_hash",
            "closeout_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        cents_fields = (
            "recovered_cash_cents", "diagnostic_fee_cents_agreed",
            "recovered_cash_success_fee_cents", "closeout_fee_total_cents",
            "monthly_assurance_fee_cents_agreed",
        )
        for name in cents_fields:
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be non-negative integer")
        expected_success = (
            self.recovered_cash_cents
            * self.recovered_cash_success_fee_bps_agreed
        ) // 10000
        if self.recovered_cash_success_fee_cents != expected_success:
            raise ValueError("success fee must use recovered cash only")
        if self.closeout_fee_total_cents != (
            self.diagnostic_fee_cents_agreed
            + self.recovered_cash_success_fee_cents
        ):
            raise ValueError("closeout fee total arithmetic mismatch")
        if not self.invoice_draft_allowed:
            raise ValueError("fee readiness artifact must allow draft preparation")
        if (
            self.invoice_issuance_performed
            or self.payment_due_asserted
            or self.payment_collected
            or self.external_action_performed
        ):
            raise ValueError("fee readiness cannot create billing/payment action")
        expected = "recoveryworks-fee-draft-readiness:" + canonical_hash(
            self._identity()
        )
        if self.readiness_id != expected:
            raise ValueError("readiness_id does not bind fee readiness")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "agreement_receipt_proof_hash": self.agreement_receipt_proof_hash,
            "closeout_acknowledgment_proof_hash":
                self.closeout_acknowledgment_proof_hash,
            "closeout_proof_hash": self.closeout_proof_hash,
            "engagement_id": self.engagement_id,
            "buyer_id": self.buyer_id,
            "currency": self.currency,
            "recovered_cash_cents": self.recovered_cash_cents,
            "diagnostic_fee_cents_agreed": self.diagnostic_fee_cents_agreed,
            "recovered_cash_success_fee_bps_agreed":
                self.recovered_cash_success_fee_bps_agreed,
            "recovered_cash_success_fee_cents":
                self.recovered_cash_success_fee_cents,
            "closeout_fee_total_cents": self.closeout_fee_total_cents,
            "monthly_assurance_fee_cents_agreed":
                self.monthly_assurance_fee_cents_agreed,
            "monthly_assurance_separately_accepted":
                self.monthly_assurance_separately_accepted,
            "payment_terms_days": self.payment_terms_days,
            "pricing_differs_from_charter_hypothesis":
                self.pricing_differs_from_charter_hypothesis,
            "invoice_draft_allowed": True,
            "invoice_issuance_performed": False,
            "payment_due_asserted": False,
            "payment_collected": False,
            "external_action_performed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "readiness_id": self.readiness_id,
            "proof_hash": self.proof_hash,
            "state": "COMMERCIAL_FEE_DRAFT_READY",
        }


def build_commercial_fee_draft_readiness(
    charter: RecoveryWorksPilotCharter,
    closeout: PilotCloseoutSnapshot,
    closeout_ack: PilotCloseoutAcknowledgment,
    agreement: FinalizedCommercialAgreementReceipt,
) -> CommercialFeeDraftReadiness:
    if closeout.charter_id != charter.charter_id or closeout.charter_proof_hash != charter.proof_hash:
        raise ValueError("closeout does not bind charter")
    if agreement.charter_id != charter.charter_id or agreement.charter_proof_hash != charter.proof_hash:
        raise ValueError("agreement does not bind charter")
    if agreement.closeout_acknowledgment_proof_hash != closeout_ack.proof_hash:
        raise ValueError("agreement does not bind closeout acknowledgment")
    if agreement.engagement_id != charter.engagement_id or agreement.buyer_id != charter.buyer_id:
        raise ValueError("agreement engagement/buyer mismatch")
    if agreement.currency != closeout.currency:
        raise ValueError("agreement currency does not match closeout")
    diagnostic = agreement.diagnostic_fee_cents if agreement.diagnostic_fee_applicable else 0
    success_bps = agreement.recovered_cash_success_fee_bps if agreement.success_fee_applicable else 0
    success = (closeout.recovered_cash_cents * success_bps) // 10000
    total = diagnostic + success
    differs = (
        agreement.diagnostic_fee_cents != charter.diagnostic_fee_cents
        or agreement.recovered_cash_success_fee_bps
        != charter.recovered_cash_success_fee_bps
        or agreement.monthly_assurance_fee_cents
        != charter.monthly_assurance_fee_cents
    )
    identity = {
        "schema": 1,
        "agreement_receipt_proof_hash": agreement.proof_hash,
        "closeout_acknowledgment_proof_hash": closeout_ack.proof_hash,
        "closeout_proof_hash": closeout.proof_hash,
        "engagement_id": charter.engagement_id,
        "buyer_id": charter.buyer_id,
        "currency": closeout.currency,
        "recovered_cash_cents": closeout.recovered_cash_cents,
        "diagnostic_fee_cents_agreed": diagnostic,
        "recovered_cash_success_fee_bps_agreed": success_bps,
        "recovered_cash_success_fee_cents": success,
        "closeout_fee_total_cents": total,
        "monthly_assurance_fee_cents_agreed":
            agreement.monthly_assurance_fee_cents,
        "monthly_assurance_separately_accepted":
            agreement.monthly_assurance_separately_accepted,
        "payment_terms_days": agreement.payment_terms_days,
        "pricing_differs_from_charter_hypothesis": differs,
        "invoice_draft_allowed": True,
        "invoice_issuance_performed": False,
        "payment_due_asserted": False,
        "payment_collected": False,
        "external_action_performed": False,
    }
    return CommercialFeeDraftReadiness(
        readiness_id="recoveryworks-fee-draft-readiness:"
        + canonical_hash(identity),
        agreement_receipt_proof_hash=agreement.proof_hash,
        closeout_acknowledgment_proof_hash=closeout_ack.proof_hash,
        closeout_proof_hash=closeout.proof_hash,
        engagement_id=charter.engagement_id,
        buyer_id=charter.buyer_id,
        currency=closeout.currency,
        recovered_cash_cents=closeout.recovered_cash_cents,
        diagnostic_fee_cents_agreed=diagnostic,
        recovered_cash_success_fee_bps_agreed=success_bps,
        recovered_cash_success_fee_cents=success,
        closeout_fee_total_cents=total,
        monthly_assurance_fee_cents_agreed=agreement.monthly_assurance_fee_cents,
        monthly_assurance_separately_accepted=
            agreement.monthly_assurance_separately_accepted,
        payment_terms_days=agreement.payment_terms_days,
        pricing_differs_from_charter_hypothesis=differs,
        invoice_draft_allowed=True,
        invoice_issuance_performed=False,
        payment_due_asserted=False,
        payment_collected=False,
        external_action_performed=False,
    )
