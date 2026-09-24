"""Unissued billing/payment draft for a finalized RecoveryWorks pilot agreement.

This artifact prepares arithmetic for human review only. It is not an invoice,
does not assert payment due, contains no payment instructions, and is never sent
or collected by RecoveryWorks.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

from recoveryworks.commercial_agreement_gate import (
    CommercialFeeDraftReadiness,
    FinalizedCommercialAgreementReceipt,
)
from recoveryworks.models import canonical_hash, normalize_sha256, normalize_utc_timestamp
from recoveryworks.private_io import atomic_private_write


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(
        normalize_utc_timestamp("timestamp", value).replace("Z", "+00:00")
    )


@dataclass(frozen=True)
class DraftBillingLineItem:
    code: str
    description: str
    amount_cents: int
    basis: str
    source_proof_hash: str

    def __post_init__(self) -> None:
        for name in ("code", "description", "basis"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        if type(self.amount_cents) is not int or self.amount_cents < 0:
            raise ValueError("amount_cents must be non-negative integer")
        object.__setattr__(
            self,
            "source_proof_hash",
            normalize_sha256("source_proof_hash", self.source_proof_hash),
        )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class UnissuedBillingDraft:
    draft_id: str
    agreement_reference: str
    agreement_receipt_proof_hash: str
    fee_readiness_proof_hash: str
    engagement_id: str
    buyer_id: str
    currency: str
    draft_reference: str
    created_at: str
    proposed_due_at: str
    payment_terms_days: int
    line_items: tuple[DraftBillingLineItem, ...]
    total_cents: int
    monthly_assurance_option_cents: int
    monthly_assurance_separately_accepted: bool
    issued: bool = False
    sent: bool = False
    payment_due_asserted: bool = False
    payment_received: bool = False
    payment_instructions_included: bool = False
    external_commitment_created: bool = False

    def __post_init__(self) -> None:
        for name in (
            "agreement_reference", "engagement_id", "buyer_id",
            "currency", "draft_reference",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in ("agreement_receipt_proof_hash", "fee_readiness_proof_hash"):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self, "created_at", normalize_utc_timestamp("created_at", self.created_at)
        )
        object.__setattr__(
            self,
            "proposed_due_at",
            normalize_utc_timestamp("proposed_due_at", self.proposed_due_at),
        )
        if _instant(self.proposed_due_at) <= _instant(self.created_at):
            raise ValueError("proposed_due_at must follow draft creation")
        if type(self.payment_terms_days) is not int or not 1 <= self.payment_terms_days <= 365:
            raise ValueError("payment_terms_days must be in 1..365")
        items = tuple(self.line_items)
        if not items:
            raise ValueError("billing draft requires at least one line item")
        if len({item.code for item in items}) != len(items):
            raise ValueError("billing draft line item codes must be unique")
        object.__setattr__(self, "line_items", items)
        if self.total_cents != sum(item.amount_cents for item in items):
            raise ValueError("billing draft total does not equal line items")
        if type(self.monthly_assurance_option_cents) is not int or self.monthly_assurance_option_cents < 0:
            raise ValueError("monthly assurance option must be non-negative integer")
        if (
            self.issued
            or self.sent
            or self.payment_due_asserted
            or self.payment_received
            or self.payment_instructions_included
            or self.external_commitment_created
        ):
            raise ValueError("billing draft cannot claim issuance/payment/external commitment")
        expected = "recoveryworks-unissued-billing-draft:" + canonical_hash(
            self._identity()
        )
        if self.draft_id != expected:
            raise ValueError("draft_id does not bind billing draft")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "agreement_reference": self.agreement_reference,
            "agreement_receipt_proof_hash": self.agreement_receipt_proof_hash,
            "fee_readiness_proof_hash": self.fee_readiness_proof_hash,
            "engagement_id": self.engagement_id,
            "buyer_id": self.buyer_id,
            "currency": self.currency,
            "draft_reference": self.draft_reference,
            "created_at": self.created_at,
            "proposed_due_at": self.proposed_due_at,
            "payment_terms_days": self.payment_terms_days,
            "line_item_hashes": [item.proof_hash for item in self.line_items],
            "total_cents": self.total_cents,
            "monthly_assurance_option_cents": self.monthly_assurance_option_cents,
            "monthly_assurance_separately_accepted":
                self.monthly_assurance_separately_accepted,
            "issued": False,
            "sent": False,
            "payment_due_asserted": False,
            "payment_received": False,
            "payment_instructions_included": False,
            "external_commitment_created": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "draft_id": self.draft_id,
            "proof_hash": self.proof_hash,
            "line_items": [
                {**asdict(item), "proof_hash": item.proof_hash}
                for item in self.line_items
            ],
            "state": "DRAFT_NOT_ISSUED",
        }

    def to_markdown(self) -> str:
        lines = [
            "# RecoveryWorks Billing Draft — NOT ISSUED",
            "",
            f"Draft reference: {self.draft_reference}",
            f"Currency: {self.currency}",
            f"Created: {self.created_at}",
            f"Proposed due date (if separately issued): {self.proposed_due_at}",
            "",
            "## Draft line items",
            "",
        ]
        for item in self.line_items:
            lines.append(
                f"- {item.code}: {item.description} — {item.amount_cents} cents"
            )
            lines.append(f"  - basis: {item.basis}")
        lines.extend([
            "",
            f"Draft total: {self.total_cents} cents",
            "",
            "## Monthly assurance option",
            "",
            f"Monthly option: {self.monthly_assurance_option_cents} cents",
            f"Separately accepted: {self.monthly_assurance_separately_accepted}",
            "",
            "This is an internal draft only. It has not been issued or sent, "
            "does not assert payment due, contains no payment instructions, "
            "and creates no external commitment.",
            "",
        ])
        return "\n".join(lines)


def build_unissued_billing_draft(
    agreement: FinalizedCommercialAgreementReceipt,
    readiness: CommercialFeeDraftReadiness,
    *,
    draft_reference: str,
    created_at: str,
) -> UnissuedBillingDraft:
    if readiness.agreement_receipt_proof_hash != agreement.proof_hash:
        raise ValueError("fee readiness does not bind finalized agreement")
    if readiness.engagement_id != agreement.engagement_id:
        raise ValueError("fee readiness engagement mismatch")
    if readiness.buyer_id != agreement.buyer_id:
        raise ValueError("fee readiness buyer mismatch")
    if readiness.currency != agreement.currency:
        raise ValueError("fee readiness currency mismatch")
    if not readiness.invoice_draft_allowed:
        raise ValueError("fee readiness does not allow draft preparation")

    items: list[DraftBillingLineItem] = []
    if readiness.diagnostic_fee_cents_agreed:
        items.append(DraftBillingLineItem(
            code="PILOT_DIAGNOSTIC_FEE",
            description="Pilot diagnostic fee per finalized agreement",
            amount_cents=readiness.diagnostic_fee_cents_agreed,
            basis="Finalized agreement diagnostic-fee term",
            source_proof_hash=agreement.proof_hash,
        ))
    if readiness.recovered_cash_success_fee_cents:
        items.append(DraftBillingLineItem(
            code="VERIFIED_RECOVERED_CASH_SUCCESS_FEE",
            description="Success fee on verified recovered cash only",
            amount_cents=readiness.recovered_cash_success_fee_cents,
            basis=(
                f"{readiness.recovered_cash_cents} recovered cents × "
                f"{readiness.recovered_cash_success_fee_bps_agreed} bps / 10000"
            ),
            source_proof_hash=readiness.proof_hash,
        ))
    if not items:
        items.append(DraftBillingLineItem(
            code="NO_CLOSEOUT_FEE",
            description="No closeout fee amount under finalized agreement terms",
            amount_cents=0,
            basis="Finalized agreement and verified closeout arithmetic",
            source_proof_hash=readiness.proof_hash,
        ))

    created = normalize_utc_timestamp("created_at", created_at)
    proposed_due = (
        _instant(created) + timedelta(days=readiness.payment_terms_days)
    ).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    total = sum(item.amount_cents for item in items)
    identity = {
        "schema": 1,
        "agreement_reference": agreement.agreement_reference,
        "agreement_receipt_proof_hash": agreement.proof_hash,
        "fee_readiness_proof_hash": readiness.proof_hash,
        "engagement_id": readiness.engagement_id,
        "buyer_id": readiness.buyer_id,
        "currency": readiness.currency,
        "draft_reference": _text("draft_reference", draft_reference),
        "created_at": created,
        "proposed_due_at": proposed_due,
        "payment_terms_days": readiness.payment_terms_days,
        "line_item_hashes": [item.proof_hash for item in items],
        "total_cents": total,
        "monthly_assurance_option_cents":
            readiness.monthly_assurance_fee_cents_agreed,
        "monthly_assurance_separately_accepted":
            readiness.monthly_assurance_separately_accepted,
        "issued": False,
        "sent": False,
        "payment_due_asserted": False,
        "payment_received": False,
        "payment_instructions_included": False,
        "external_commitment_created": False,
    }
    return UnissuedBillingDraft(
        draft_id="recoveryworks-unissued-billing-draft:" + canonical_hash(identity),
        agreement_reference=agreement.agreement_reference,
        agreement_receipt_proof_hash=agreement.proof_hash,
        fee_readiness_proof_hash=readiness.proof_hash,
        engagement_id=readiness.engagement_id,
        buyer_id=readiness.buyer_id,
        currency=readiness.currency,
        draft_reference=draft_reference,
        created_at=created,
        proposed_due_at=proposed_due,
        payment_terms_days=readiness.payment_terms_days,
        line_items=tuple(items),
        total_cents=total,
        monthly_assurance_option_cents=readiness.monthly_assurance_fee_cents_agreed,
        monthly_assurance_separately_accepted=
            readiness.monthly_assurance_separately_accepted,
        issued=False,
        sent=False,
        payment_due_asserted=False,
        payment_received=False,
        payment_instructions_included=False,
        external_commitment_created=False,
    )


def write_unissued_billing_draft(
    draft: UnissuedBillingDraft,
    *,
    json_path: str | Path,
    markdown_path: str | Path,
) -> None:
    atomic_private_write(
        Path(json_path),
        (
            json.dumps(
                draft.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8"),
    )
    atomic_private_write(
        Path(markdown_path),
        (draft.to_markdown() + "\n").encode("utf-8"),
    )
