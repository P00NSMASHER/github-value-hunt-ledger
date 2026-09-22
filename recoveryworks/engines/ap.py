"""Deterministic AP overpayment detector.

This engine compares posted cash against the verified invoice amount for each
vendor/invoice key. It does not infer entitlement from an LLM and does not
contact a vendor. Results still pass through RecoveryEngine and RecoveryLedger.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from recoveryworks.branches.ap import from_ap_variance
from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import EvidenceRef, RuleRef


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _money(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be non-negative integer cents")
    return value


@dataclass(frozen=True)
class APInvoice:
    vendor_id: str
    invoice_id: str
    invoice_date: str
    amount_cents: int
    currency: str
    source_hash: str
    locator: str
    verified: bool = False

    def __post_init__(self) -> None:
        for name in ("vendor_id", "invoice_id", "invoice_date", "currency", "source_hash", "locator"):
            _text(name, getattr(self, name))
        _money("amount_cents", self.amount_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")


@dataclass(frozen=True)
class APPayment:
    vendor_id: str
    invoice_id: str
    payment_id: str
    payment_date: str
    amount_cents: int
    currency: str
    source_hash: str
    locator: str
    verified: bool = False
    posted: bool = True

    def __post_init__(self) -> None:
        for name in (
            "vendor_id", "invoice_id", "payment_id", "payment_date",
            "currency", "source_hash", "locator",
        ):
            _text(name, getattr(self, name))
        _money("amount_cents", self.amount_cents)
        if type(self.verified) is not bool or type(self.posted) is not bool:
            raise ValueError("verified and posted must be boolean")


def detect_ap_overpayments(
    *,
    client_id: str,
    invoices: Iterable[APInvoice],
    payments: Iterable[APPayment],
) -> tuple[RecoveryObservation, ...]:
    """Return one observation per invoice whose posted payments exceed invoice amount."""
    client_id = _text("client_id", client_id)

    invoice_index: dict[tuple[str, str], APInvoice] = {}
    for invoice in invoices:
        key = (invoice.vendor_id, invoice.invoice_id)
        existing = invoice_index.get(key)
        if existing is not None:
            same_authority = (
                existing.amount_cents == invoice.amount_cents
                and existing.currency == invoice.currency
                and existing.source_hash == invoice.source_hash
            )
            if not same_authority:
                raise ValueError(f"conflicting invoice authority for {key!r}")
            continue
        invoice_index[key] = invoice

    payment_groups: dict[tuple[str, str], list[APPayment]] = {}
    seen_payment_ids: set[tuple[str, str]] = set()
    for payment in payments:
        if not payment.posted:
            continue
        identity = (payment.vendor_id, payment.payment_id)
        if identity in seen_payment_ids:
            continue
        seen_payment_ids.add(identity)
        payment_groups.setdefault((payment.vendor_id, payment.invoice_id), []).append(payment)

    observations: list[RecoveryObservation] = []
    for key in sorted(invoice_index):
        invoice = invoice_index[key]
        group = sorted(payment_groups.get(key, []), key=lambda p: (p.payment_date, p.payment_id))
        if not group:
            continue

        currencies = {invoice.currency, *(payment.currency for payment in group)}
        if len(currencies) != 1:
            raise ValueError(f"currency mismatch for vendor/invoice {key!r}")

        actual_cents = sum(payment.amount_cents for payment in group)
        if actual_cents <= invoice.amount_cents:
            continue

        evidence = (
            EvidenceRef(
                evidence_id=f"ap-invoice:{invoice.vendor_id}:{invoice.invoice_id}",
                source_hash=invoice.source_hash,
                locator=invoice.locator,
                kind="ap_invoice",
                verified=invoice.verified,
                metadata={"amount_cents": invoice.amount_cents},
            ),
            *tuple(
                EvidenceRef(
                    evidence_id=f"ap-payment:{payment.vendor_id}:{payment.payment_id}",
                    source_hash=payment.source_hash,
                    locator=payment.locator,
                    kind="ap_payment",
                    verified=payment.verified,
                    metadata={"amount_cents": payment.amount_cents, "posted": payment.posted},
                )
                for payment in group
            ),
        )
        authority = RuleRef(
            rule_id=f"ap-invoice-authority:{invoice.vendor_id}:{invoice.invoice_id}",
            source_hash=invoice.source_hash,
            effective_from=invoice.invoice_date,
            effective_to=None,
            verified_controlling=invoice.verified,
            source_locator=invoice.locator,
            metadata={
                "authority_type": "vendor_invoice_expected_amount",
                "invoice_amount_cents": invoice.amount_cents,
            },
        )
        observations.append(from_ap_variance(
            client_id=client_id,
            vendor_id=invoice.vendor_id,
            transaction_id=invoice.invoice_id,
            transaction_date=group[-1].payment_date,
            expected_cents=invoice.amount_cents,
            paid_cents=actual_cents,
            rule=authority,
            evidence=tuple(evidence),
            currency=invoice.currency,
            reason="AP_PAID_ABOVE_INVOICE",
            confidence_basis="verified invoice amount vs deduplicated posted payment total",
            metadata={
                "invoice_date": invoice.invoice_date,
                "payment_ids": [payment.payment_id for payment in group],
                "payment_count": len(group),
            },
        ))

    return tuple(observations)
