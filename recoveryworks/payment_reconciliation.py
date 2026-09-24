"""External cash-settlement receipts and invoice payment reconciliation.

Invoice-provider/accounting status is not accepted as cash truth. Payment state
requires separately verified settlement evidence for the exact issued invoice.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from recoveryworks.billing_issuance import VerifiedIssuedInvoice
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


class SettlementEventType(str, Enum):
    CREDIT = "CREDIT"
    REVERSAL = "REVERSAL"


class InvoiceSettlementState(str, Enum):
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"


@dataclass(frozen=True)
class ExternalPaymentSettlementReceipt:
    receipt_id: str
    issued_invoice_id: str
    issued_invoice_proof_hash: str
    external_invoice_id: str
    buyer_id: str
    currency: str
    event_type: SettlementEventType
    settlement_reference: str
    observed_at: str
    gross_cents: int
    fee_cents: int
    net_settled_cents: int
    invoice_applied_delta_cents: int
    reverses_settlement_reference: str | None
    source_hash: str
    source_locator: str
    verified: bool
    externally_observed: bool
    settlement_final: bool
    provider_accounting_only: bool = False
    created_by_recoveryworks: bool = False

    def __post_init__(self) -> None:
        for name in (
            "issued_invoice_id", "external_invoice_id", "buyer_id",
            "currency", "settlement_reference", "source_locator",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        object.__setattr__(
            self,
            "issued_invoice_proof_hash",
            normalize_sha256(
                "issued_invoice_proof_hash", self.issued_invoice_proof_hash
            ),
        )
        if isinstance(self.event_type, str):
            object.__setattr__(
                self, "event_type", SettlementEventType(self.event_type)
            )
        if type(self.gross_cents) is not int or self.gross_cents <= 0:
            raise ValueError("gross_cents must be a positive integer")
        if type(self.fee_cents) is not int or self.fee_cents < 0:
            raise ValueError("fee_cents must be a non-negative integer")
        if type(self.net_settled_cents) is not int:
            raise ValueError("net_settled_cents must be integer")
        if type(self.invoice_applied_delta_cents) is not int:
            raise ValueError("invoice_applied_delta_cents must be integer")
        if self.event_type is SettlementEventType.CREDIT:
            if self.fee_cents > self.gross_cents:
                raise ValueError("payment fee cannot exceed gross amount")
            if self.net_settled_cents != self.gross_cents - self.fee_cents:
                raise ValueError("credit net settlement arithmetic mismatch")
            if not 0 < self.invoice_applied_delta_cents <= self.gross_cents:
                raise ValueError("credit applied amount must be in 1..gross")
            if self.reverses_settlement_reference is not None:
                raise ValueError("credit cannot reverse another settlement")
        else:
            if self.fee_cents != 0:
                raise ValueError("reversal receipt cannot introduce a new fee")
            if self.net_settled_cents != -self.gross_cents:
                raise ValueError("reversal net settlement must be negative gross")
            if self.invoice_applied_delta_cents != -self.gross_cents:
                raise ValueError("reversal applied delta must equal negative gross")
            if self.reverses_settlement_reference is None:
                raise ValueError("reversal must identify original settlement")
            object.__setattr__(
                self,
                "reverses_settlement_reference",
                _text(
                    "reverses_settlement_reference",
                    self.reverses_settlement_reference,
                ),
            )
        object.__setattr__(
            self, "observed_at", normalize_utc_timestamp("observed_at", self.observed_at)
        )
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if not self.verified:
            raise ValueError("settlement receipt must be externally verified")
        if not self.externally_observed or not self.settlement_final:
            raise ValueError("settlement receipt requires final external cash evidence")
        if self.provider_accounting_only:
            raise ValueError("provider accounting status is not cash-settlement evidence")
        if self.created_by_recoveryworks:
            raise ValueError("RecoveryWorks cannot manufacture settlement evidence")
        expected = "recoveryworks-payment-settlement:" + canonical_hash(
            self._identity()
        )
        if self.receipt_id != expected:
            raise ValueError("receipt_id does not bind settlement receipt")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "issued_invoice_id": self.issued_invoice_id,
            "issued_invoice_proof_hash": self.issued_invoice_proof_hash,
            "external_invoice_id": self.external_invoice_id,
            "buyer_id": self.buyer_id,
            "currency": self.currency,
            "event_type": self.event_type.value,
            "settlement_reference": self.settlement_reference,
            "observed_at": self.observed_at,
            "gross_cents": self.gross_cents,
            "fee_cents": self.fee_cents,
            "net_settled_cents": self.net_settled_cents,
            "invoice_applied_delta_cents": self.invoice_applied_delta_cents,
            "reverses_settlement_reference": self.reverses_settlement_reference,
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": True,
            "externally_observed": True,
            "settlement_final": True,
            "provider_accounting_only": False,
            "created_by_recoveryworks": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_external_payment_settlement_receipt(
    invoice: VerifiedIssuedInvoice,
    *,
    event_type: SettlementEventType,
    settlement_reference: str,
    observed_at: str,
    gross_cents: int,
    fee_cents: int,
    invoice_applied_delta_cents: int,
    reverses_settlement_reference: str | None,
    source_hash: str,
    source_locator: str,
    verified: bool,
) -> ExternalPaymentSettlementReceipt:
    if not verified:
        raise ValueError("settlement receipt must be externally verified")
    if event_type is SettlementEventType.CREDIT:
        net = gross_cents - fee_cents
    else:
        net = -gross_cents
    identity = {
        "schema": 1,
        "issued_invoice_id": invoice.issued_invoice_id,
        "issued_invoice_proof_hash": invoice.proof_hash,
        "external_invoice_id": invoice.external_invoice_id,
        "buyer_id": invoice.buyer_id,
        "currency": invoice.currency,
        "event_type": event_type.value,
        "settlement_reference": _text("settlement_reference", settlement_reference),
        "observed_at": normalize_utc_timestamp("observed_at", observed_at),
        "gross_cents": gross_cents,
        "fee_cents": fee_cents,
        "net_settled_cents": net,
        "invoice_applied_delta_cents": invoice_applied_delta_cents,
        "reverses_settlement_reference": reverses_settlement_reference,
        "source_hash": normalize_source_hash(source_hash),
        "source_locator": _text("source_locator", source_locator),
        "verified": True,
        "externally_observed": True,
        "settlement_final": True,
        "provider_accounting_only": False,
        "created_by_recoveryworks": False,
    }
    return ExternalPaymentSettlementReceipt(
        receipt_id="recoveryworks-payment-settlement:" + canonical_hash(identity),
        issued_invoice_id=invoice.issued_invoice_id,
        issued_invoice_proof_hash=invoice.proof_hash,
        external_invoice_id=invoice.external_invoice_id,
        buyer_id=invoice.buyer_id,
        currency=invoice.currency,
        event_type=event_type,
        settlement_reference=settlement_reference,
        observed_at=observed_at,
        gross_cents=gross_cents,
        fee_cents=fee_cents,
        net_settled_cents=net,
        invoice_applied_delta_cents=invoice_applied_delta_cents,
        reverses_settlement_reference=reverses_settlement_reference,
        source_hash=source_hash,
        source_locator=source_locator,
        verified=True,
        externally_observed=True,
        settlement_final=True,
        provider_accounting_only=False,
        created_by_recoveryworks=False,
    )


@dataclass(frozen=True)
class InvoicePaymentReconciliation:
    reconciliation_id: str
    issued_invoice_id: str
    issued_invoice_proof_hash: str
    external_invoice_id: str
    buyer_id: str
    currency: str
    invoice_total_cents: int
    applied_cents: int
    remaining_cents: int
    gross_credit_cents: int
    settlement_fees_cents: int
    net_cash_cents: int
    settlement_state: InvoiceSettlementState
    settlement_receipt_proof_hashes: tuple[str, ...]
    reconciled_at: str
    independent_cash_evidence_verified: bool = True
    payment_collection_performed_by_recoveryworks: bool = False

    def __post_init__(self) -> None:
        for name in (
            "issued_invoice_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        hashes = tuple(
            normalize_sha256("settlement_receipt_proof_hash", x)
            for x in self.settlement_receipt_proof_hashes
        )
        object.__setattr__(self, "settlement_receipt_proof_hashes", hashes)
        object.__setattr__(
            self, "reconciled_at",
            normalize_utc_timestamp("reconciled_at", self.reconciled_at),
        )
        if not isinstance(self.settlement_state, InvoiceSettlementState):
            raise ValueError("settlement_state must be InvoiceSettlementState")
        if self.remaining_cents != self.invoice_total_cents - self.applied_cents:
            raise ValueError("invoice remaining arithmetic mismatch")
        if not 0 <= self.applied_cents <= self.invoice_total_cents:
            raise ValueError("applied_cents outside invoice bounds")
        expected_state = (
            InvoiceSettlementState.UNPAID
            if self.applied_cents == 0
            else (
                InvoiceSettlementState.PAID
                if self.applied_cents == self.invoice_total_cents
                else InvoiceSettlementState.PARTIALLY_PAID
            )
        )
        if self.settlement_state is not expected_state:
            raise ValueError("settlement state does not match applied balance")
        if not self.independent_cash_evidence_verified:
            raise ValueError("payment reconciliation requires independent cash evidence")
        if self.payment_collection_performed_by_recoveryworks:
            raise ValueError("RecoveryWorks cannot claim payment collection")
        expected = "recoveryworks-invoice-payment-reconciliation:" + canonical_hash(
            self._identity()
        )
        if self.reconciliation_id != expected:
            raise ValueError("reconciliation_id does not bind payment reconciliation")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "issued_invoice_id": self.issued_invoice_id,
            "issued_invoice_proof_hash": self.issued_invoice_proof_hash,
            "external_invoice_id": self.external_invoice_id,
            "buyer_id": self.buyer_id,
            "currency": self.currency,
            "invoice_total_cents": self.invoice_total_cents,
            "applied_cents": self.applied_cents,
            "remaining_cents": self.remaining_cents,
            "gross_credit_cents": self.gross_credit_cents,
            "settlement_fees_cents": self.settlement_fees_cents,
            "net_cash_cents": self.net_cash_cents,
            "settlement_state": self.settlement_state.value,
            "settlement_receipt_proof_hashes":
                list(self.settlement_receipt_proof_hashes),
            "reconciled_at": self.reconciled_at,
            "independent_cash_evidence_verified": True,
            "payment_collection_performed_by_recoveryworks": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "reconciliation_id": self.reconciliation_id,
            "proof_hash": self.proof_hash,
            "state": f"INVOICE_{self.settlement_state.value}",
        }


def reconcile_invoice_payment(
    invoice: VerifiedIssuedInvoice,
    receipts: tuple[ExternalPaymentSettlementReceipt, ...],
    *,
    reconciled_at: str,
) -> InvoicePaymentReconciliation:
    seen = set()
    credits: dict[str, int] = {}
    applied = 0
    gross_credit = 0
    fees = 0
    net_cash = 0
    proof_hashes = []

    ordered = sorted(
        receipts,
        key=lambda x: (x.observed_at, x.settlement_reference, x.event_type.value),
    )
    for receipt in ordered:
        if receipt.settlement_reference in seen:
            raise ValueError("duplicate settlement_reference")
        seen.add(receipt.settlement_reference)
        if (
            receipt.issued_invoice_id != invoice.issued_invoice_id
            or receipt.issued_invoice_proof_hash != invoice.proof_hash
            or receipt.external_invoice_id != invoice.external_invoice_id
            or receipt.buyer_id != invoice.buyer_id
            or receipt.currency != invoice.currency
        ):
            raise ValueError("settlement receipt invoice scope mismatch")

        if receipt.event_type is SettlementEventType.CREDIT:
            credits[receipt.settlement_reference] = receipt.invoice_applied_delta_cents
            gross_credit += receipt.gross_cents
            fees += receipt.fee_cents
        else:
            original = receipt.reverses_settlement_reference
            if original not in credits:
                raise ValueError("reversal references unknown settlement")
            reversal = -receipt.invoice_applied_delta_cents
            if reversal > credits[original]:
                raise ValueError("reversal exceeds unreversed original settlement")
            credits[original] -= reversal

        applied += receipt.invoice_applied_delta_cents
        net_cash += receipt.net_settled_cents
        if applied < 0:
            raise ValueError("settlement events cannot drive invoice applied balance negative")
        if applied > invoice.total_cents:
            raise ValueError("settlement receipts over-allocate invoice")
        proof_hashes.append(receipt.proof_hash)

    state = (
        InvoiceSettlementState.UNPAID
        if applied == 0
        else (
            InvoiceSettlementState.PAID
            if applied == invoice.total_cents
            else InvoiceSettlementState.PARTIALLY_PAID
        )
    )
    reconciled = normalize_utc_timestamp("reconciled_at", reconciled_at)
    identity = {
        "schema": 1,
        "issued_invoice_id": invoice.issued_invoice_id,
        "issued_invoice_proof_hash": invoice.proof_hash,
        "external_invoice_id": invoice.external_invoice_id,
        "buyer_id": invoice.buyer_id,
        "currency": invoice.currency,
        "invoice_total_cents": invoice.total_cents,
        "applied_cents": applied,
        "remaining_cents": invoice.total_cents - applied,
        "gross_credit_cents": gross_credit,
        "settlement_fees_cents": fees,
        "net_cash_cents": net_cash,
        "settlement_state": state.value,
        "settlement_receipt_proof_hashes": proof_hashes,
        "reconciled_at": reconciled,
        "independent_cash_evidence_verified": True,
        "payment_collection_performed_by_recoveryworks": False,
    }
    return InvoicePaymentReconciliation(
        reconciliation_id="recoveryworks-invoice-payment-reconciliation:"
        + canonical_hash(identity),
        issued_invoice_id=invoice.issued_invoice_id,
        issued_invoice_proof_hash=invoice.proof_hash,
        external_invoice_id=invoice.external_invoice_id,
        buyer_id=invoice.buyer_id,
        currency=invoice.currency,
        invoice_total_cents=invoice.total_cents,
        applied_cents=applied,
        remaining_cents=invoice.total_cents - applied,
        gross_credit_cents=gross_credit,
        settlement_fees_cents=fees,
        net_cash_cents=net_cash,
        settlement_state=state,
        settlement_receipt_proof_hashes=tuple(proof_hashes),
        reconciled_at=reconciled,
        independent_cash_evidence_verified=True,
        payment_collection_performed_by_recoveryworks=False,
    )
