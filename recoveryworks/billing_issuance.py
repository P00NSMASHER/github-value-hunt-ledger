"""Governed invoice issuance handoff and external issuance verification.

RecoveryWorks prepares an exact billing handoff only. A separately authorized
billing system/operator performs issuance and delivery. RecoveryWorks accepts
invoice state only from a verified external issuance/delivery receipt.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from recoveryworks.billing_draft import UnissuedBillingDraft
from recoveryworks.commercial_agreement_gate import (
    CommercialFeeDraftReadiness,
    FinalizedCommercialAgreementReceipt,
)
from recoveryworks.models import (
    canonical_hash,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    value = value.strip()
    if any(ord(ch) < 32 for ch in value):
        raise ValueError(f"{name} cannot contain control characters")
    return value


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(
        normalize_utc_timestamp("timestamp", value).replace("Z", "+00:00")
    )


@dataclass(frozen=True)
class InvoiceIssuanceHandoff:
    handoff_id: str
    draft_id: str
    draft_proof_hash: str
    agreement_receipt_proof_hash: str
    fee_readiness_proof_hash: str
    engagement_id: str
    buyer_id: str
    currency: str
    invoice_total_cents: int
    line_item_proof_hashes: tuple[str, ...]
    due_at: str
    issuer_id: str
    issued_at: str
    expires_at: str
    issuance_performed_by_recoveryworks: bool = False
    payment_collection_enabled: bool = False
    payment_instructions_embedded: bool = False

    def __post_init__(self) -> None:
        for name in (
            "draft_id", "engagement_id", "buyer_id", "currency", "issuer_id"
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "draft_proof_hash",
            "agreement_receipt_proof_hash",
            "fee_readiness_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        hashes = tuple(
            normalize_sha256("line_item_proof_hash", x)
            for x in self.line_item_proof_hashes
        )
        if not hashes:
            raise ValueError("invoice issuance handoff requires line items")
        object.__setattr__(self, "line_item_proof_hashes", hashes)
        if type(self.invoice_total_cents) is not int or self.invoice_total_cents < 0:
            raise ValueError("invoice_total_cents must be non-negative integer")
        for name in ("due_at", "issued_at", "expires_at"):
            object.__setattr__(
                self, name, normalize_utc_timestamp(name, getattr(self, name))
            )
        if _instant(self.expires_at) <= _instant(self.issued_at):
            raise ValueError("issuance handoff must expire after creation")
        if _instant(self.due_at) <= _instant(self.issued_at):
            raise ValueError("invoice due date must follow handoff creation")
        if (
            self.issuance_performed_by_recoveryworks
            or self.payment_collection_enabled
            or self.payment_instructions_embedded
        ):
            raise ValueError(
                "issuance handoff cannot perform issuance/payment collection"
            )
        expected = "recoveryworks-invoice-issuance-handoff:" + canonical_hash(
            self._identity()
        )
        if self.handoff_id != expected:
            raise ValueError("handoff_id does not bind invoice issuance handoff")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "draft_id": self.draft_id,
            "draft_proof_hash": self.draft_proof_hash,
            "agreement_receipt_proof_hash": self.agreement_receipt_proof_hash,
            "fee_readiness_proof_hash": self.fee_readiness_proof_hash,
            "engagement_id": self.engagement_id,
            "buyer_id": self.buyer_id,
            "currency": self.currency,
            "invoice_total_cents": self.invoice_total_cents,
            "line_item_proof_hashes": list(self.line_item_proof_hashes),
            "due_at": self.due_at,
            "issuer_id": self.issuer_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "issuance_performed_by_recoveryworks": False,
            "payment_collection_enabled": False,
            "payment_instructions_embedded": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "handoff_id": self.handoff_id,
            "proof_hash": self.proof_hash,
            "state": "READY_FOR_SEPARATE_BILLING_ISSUER",
        }


def prepare_invoice_issuance_handoff(
    draft: UnissuedBillingDraft,
    agreement: FinalizedCommercialAgreementReceipt,
    readiness: CommercialFeeDraftReadiness,
    *,
    issuer_id: str,
    issued_at: str,
    ttl_seconds: int = 900,
) -> InvoiceIssuanceHandoff:
    if not 1 <= ttl_seconds <= 86400:
        raise ValueError("ttl_seconds must be in 1..86400")
    if draft.agreement_receipt_proof_hash != agreement.proof_hash:
        raise ValueError("billing draft does not bind finalized agreement")
    if draft.fee_readiness_proof_hash != readiness.proof_hash:
        raise ValueError("billing draft does not bind fee readiness")
    if readiness.agreement_receipt_proof_hash != agreement.proof_hash:
        raise ValueError("fee readiness does not bind finalized agreement")
    if (
        draft.engagement_id != agreement.engagement_id
        or draft.buyer_id != agreement.buyer_id
        or draft.currency != agreement.currency
    ):
        raise ValueError("billing draft commercial scope mismatch")
    if draft.total_cents != readiness.closeout_fee_total_cents:
        raise ValueError("billing draft total no longer matches fee readiness")
    if not readiness.invoice_draft_allowed:
        raise ValueError("fee readiness does not permit invoice draft")
    issued = normalize_utc_timestamp("issued_at", issued_at)
    expires = (
        _instant(issued) + timedelta(seconds=ttl_seconds)
    ).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    identity = {
        "schema": 1,
        "draft_id": draft.draft_id,
        "draft_proof_hash": draft.proof_hash,
        "agreement_receipt_proof_hash": agreement.proof_hash,
        "fee_readiness_proof_hash": readiness.proof_hash,
        "engagement_id": draft.engagement_id,
        "buyer_id": draft.buyer_id,
        "currency": draft.currency,
        "invoice_total_cents": draft.total_cents,
        "line_item_proof_hashes": [x.proof_hash for x in draft.line_items],
        "due_at": draft.proposed_due_at,
        "issuer_id": _text("issuer_id", issuer_id),
        "issued_at": issued,
        "expires_at": expires,
        "issuance_performed_by_recoveryworks": False,
        "payment_collection_enabled": False,
        "payment_instructions_embedded": False,
    }
    return InvoiceIssuanceHandoff(
        handoff_id="recoveryworks-invoice-issuance-handoff:"
        + canonical_hash(identity),
        draft_id=draft.draft_id,
        draft_proof_hash=draft.proof_hash,
        agreement_receipt_proof_hash=agreement.proof_hash,
        fee_readiness_proof_hash=readiness.proof_hash,
        engagement_id=draft.engagement_id,
        buyer_id=draft.buyer_id,
        currency=draft.currency,
        invoice_total_cents=draft.total_cents,
        line_item_proof_hashes=tuple(x.proof_hash for x in draft.line_items),
        due_at=draft.proposed_due_at,
        issuer_id=issuer_id,
        issued_at=issued,
        expires_at=expires,
        issuance_performed_by_recoveryworks=False,
        payment_collection_enabled=False,
        payment_instructions_embedded=False,
    )


@dataclass(frozen=True)
class ExternalInvoiceIssuanceReceipt:
    receipt_id: str
    handoff_id: str
    handoff_proof_hash: str
    issuer_id: str
    external_invoice_id: str
    external_invoice_reference: str
    issued_at: str
    delivered_at: str
    due_at: str
    currency: str
    total_cents: int
    line_item_proof_hashes: tuple[str, ...]
    delivery_evidence_hash: str
    source_hash: str
    source_locator: str
    verified: bool
    issued_by_external_system: bool
    delivered_to_buyer: bool
    payment_due_asserted_by_external_system: bool
    payment_received: bool = False
    payment_collection_performed_by_recoveryworks: bool = False

    def __post_init__(self) -> None:
        for name in (
            "handoff_id", "issuer_id", "external_invoice_id",
            "external_invoice_reference", "currency", "source_locator",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "handoff_proof_hash", "delivery_evidence_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        hashes = tuple(
            normalize_sha256("line_item_proof_hash", x)
            for x in self.line_item_proof_hashes
        )
        object.__setattr__(self, "line_item_proof_hashes", hashes)
        for name in ("issued_at", "delivered_at", "due_at"):
            object.__setattr__(
                self, name, normalize_utc_timestamp(name, getattr(self, name))
            )
        if _instant(self.delivered_at) < _instant(self.issued_at):
            raise ValueError("delivery cannot predate invoice issuance")
        if _instant(self.due_at) <= _instant(self.issued_at):
            raise ValueError("invoice due date must follow issuance")
        if type(self.total_cents) is not int or self.total_cents < 0:
            raise ValueError("invoice total must be non-negative integer")
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if not self.verified:
            raise ValueError("invoice issuance receipt must be externally verified")
        if (
            not self.issued_by_external_system
            or not self.delivered_to_buyer
            or not self.payment_due_asserted_by_external_system
        ):
            raise ValueError(
                "verified invoice requires external issuance, delivery, and due assertion"
            )
        if self.payment_received or self.payment_collection_performed_by_recoveryworks:
            raise ValueError("invoice issuance receipt cannot claim payment collection")
        expected = "recoveryworks-external-invoice-receipt:" + canonical_hash(
            self._identity()
        )
        if self.receipt_id != expected:
            raise ValueError("receipt_id does not bind invoice issuance receipt")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "handoff_id": self.handoff_id,
            "handoff_proof_hash": self.handoff_proof_hash,
            "issuer_id": self.issuer_id,
            "external_invoice_id": self.external_invoice_id,
            "external_invoice_reference": self.external_invoice_reference,
            "issued_at": self.issued_at,
            "delivered_at": self.delivered_at,
            "due_at": self.due_at,
            "currency": self.currency,
            "total_cents": self.total_cents,
            "line_item_proof_hashes": list(self.line_item_proof_hashes),
            "delivery_evidence_hash": self.delivery_evidence_hash,
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": True,
            "issued_by_external_system": True,
            "delivered_to_buyer": True,
            "payment_due_asserted_by_external_system": True,
            "payment_received": False,
            "payment_collection_performed_by_recoveryworks": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


@dataclass(frozen=True)
class VerifiedIssuedInvoice:
    issued_invoice_id: str
    handoff_proof_hash: str
    issuance_receipt_proof_hash: str
    external_invoice_id: str
    external_invoice_reference: str
    engagement_id: str
    buyer_id: str
    currency: str
    total_cents: int
    issued_at: str
    delivered_at: str
    due_at: str
    payment_due_verified: bool = True
    payment_received: bool = False

    def __post_init__(self) -> None:
        for name in ("handoff_proof_hash", "issuance_receipt_proof_hash"):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        if self.payment_due_verified is not True or self.payment_received:
            raise ValueError("issued invoice state is due-but-unpaid")
        expected = "recoveryworks-verified-issued-invoice:" + canonical_hash(
            self._identity()
        )
        if self.issued_invoice_id != expected:
            raise ValueError("issued_invoice_id does not bind verified invoice")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "handoff_proof_hash": self.handoff_proof_hash,
            "issuance_receipt_proof_hash": self.issuance_receipt_proof_hash,
            "external_invoice_id": self.external_invoice_id,
            "external_invoice_reference": self.external_invoice_reference,
            "engagement_id": self.engagement_id,
            "buyer_id": self.buyer_id,
            "currency": self.currency,
            "total_cents": self.total_cents,
            "issued_at": self.issued_at,
            "delivered_at": self.delivered_at,
            "due_at": self.due_at,
            "payment_due_verified": True,
            "payment_received": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "issued_invoice_id": self.issued_invoice_id,
            "proof_hash": self.proof_hash,
            "state": "ISSUED_INVOICE_VERIFIED",
        }


def verify_external_invoice_issuance(
    handoff: InvoiceIssuanceHandoff,
    receipt: ExternalInvoiceIssuanceReceipt,
) -> VerifiedIssuedInvoice:
    if receipt.handoff_id != handoff.handoff_id:
        raise ValueError("invoice receipt handoff id mismatch")
    if receipt.handoff_proof_hash != handoff.proof_hash:
        raise ValueError("invoice receipt does not bind exact handoff")
    if receipt.issuer_id != handoff.issuer_id:
        raise ValueError("invoice receipt issuer mismatch")
    if receipt.currency != handoff.currency:
        raise ValueError("invoice receipt currency mismatch")
    if receipt.total_cents != handoff.invoice_total_cents:
        raise ValueError("invoice receipt total mismatch")
    if tuple(receipt.line_item_proof_hashes) != tuple(handoff.line_item_proof_hashes):
        raise ValueError("invoice receipt line items mismatch")
    if receipt.due_at != handoff.due_at:
        raise ValueError("invoice receipt due date mismatch")
    issued = _instant(receipt.issued_at)
    if issued < _instant(handoff.issued_at) or issued > _instant(handoff.expires_at):
        raise ValueError("invoice issuance occurred outside handoff window")
    identity = {
        "schema": 1,
        "handoff_proof_hash": handoff.proof_hash,
        "issuance_receipt_proof_hash": receipt.proof_hash,
        "external_invoice_id": receipt.external_invoice_id,
        "external_invoice_reference": receipt.external_invoice_reference,
        "engagement_id": handoff.engagement_id,
        "buyer_id": handoff.buyer_id,
        "currency": handoff.currency,
        "total_cents": handoff.invoice_total_cents,
        "issued_at": receipt.issued_at,
        "delivered_at": receipt.delivered_at,
        "due_at": receipt.due_at,
        "payment_due_verified": True,
        "payment_received": False,
    }
    return VerifiedIssuedInvoice(
        issued_invoice_id="recoveryworks-verified-issued-invoice:"
        + canonical_hash(identity),
        handoff_proof_hash=handoff.proof_hash,
        issuance_receipt_proof_hash=receipt.proof_hash,
        external_invoice_id=receipt.external_invoice_id,
        external_invoice_reference=receipt.external_invoice_reference,
        engagement_id=handoff.engagement_id,
        buyer_id=handoff.buyer_id,
        currency=handoff.currency,
        total_cents=handoff.invoice_total_cents,
        issued_at=receipt.issued_at,
        delivered_at=receipt.delivered_at,
        due_at=receipt.due_at,
        payment_due_verified=True,
        payment_received=False,
    )
