"""APRecovery ingestion and deterministic overpayment detection.

This adapter is deliberately conservative:
- verified obligation + verified payment evidence can produce VALIDATED dollars;
- duplicate-looking payments without a verified obligation stay REVIEW;
- grouping is exact on vendor + normalized invoice identity, never fuzzy vendor matching.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import re
from typing import Any, Iterable, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef, canonical_hash


_SUFFIX = re.compile(r"[-_]?(R|DUP|COPY|REV|REVERSAL)[-_]?$", re.IGNORECASE)


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _positive_cents(name: str, value: int) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be positive integer cents")
    return value


def normalize_invoice_number(value: str) -> str:
    """Normalize one known duplicate/reversal suffix without stripping digits."""
    text = _required("invoice_number", value).upper().replace(" ", "")
    return _SUFFIX.sub("", text)


@dataclass(frozen=True)
class APPayment:
    payment_id: str
    vendor_id: str
    invoice_number: str
    amount_cents: int
    source_hash: str
    source_locator: str
    verified: bool
    payment_date: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("payment_id", "vendor_id", "invoice_number", "source_hash", "source_locator"):
            _required(name, getattr(self, name))
        _positive_cents("amount_cents", self.amount_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def normalized_invoice(self) -> str:
        return normalize_invoice_number(self.invoice_number)

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"ap-payment:{self.payment_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="ap_payment",
            verified=self.verified,
            metadata={
                "vendor_id": self.vendor_id,
                "invoice_number": self.invoice_number,
                "payment_date": self.payment_date,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class APObligation:
    vendor_id: str
    invoice_number: str
    expected_cents: int
    source_hash: str
    source_locator: str
    effective_from: str
    verified: bool
    effective_to: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "vendor_id", "invoice_number", "source_hash",
            "source_locator", "effective_from",
        ):
            _required(name, getattr(self, name))
        _positive_cents("expected_cents", self.expected_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def normalized_invoice(self) -> str:
        return normalize_invoice_number(self.invoice_number)

    @property
    def key(self) -> tuple[str, str]:
        return (self.vendor_id, self.normalized_invoice)

    def rule_ref(self) -> RuleRef:
        identity = {
            "schema": 1,
            "vendor_id": self.vendor_id,
            "invoice_number": self.normalized_invoice,
            "expected_cents": self.expected_cents,
            "source_hash": self.source_hash,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
        }
        return RuleRef(
            rule_id="ap-obligation:" + canonical_hash(identity),
            source_hash=self.source_hash,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            verified_controlling=self.verified,
            source_locator=self.source_locator,
            metadata={
                "kind": "ap_obligation",
                "vendor_id": self.vendor_id,
                "invoice_number": self.invoice_number,
                "expected_cents": self.expected_cents,
                **dict(self.metadata),
            },
        )


def _obligation_index(obligations: Iterable[APObligation]) -> dict[tuple[str, str], APObligation]:
    result: dict[tuple[str, str], APObligation] = {}
    for obligation in obligations:
        existing = result.get(obligation.key)
        if existing is None:
            result[obligation.key] = obligation
            continue
        if existing == obligation:
            continue
        raise ValueError(
            "conflicting AP obligations for "
            f"{obligation.vendor_id}/{obligation.normalized_invoice}"
        )
    return result


def build_ap_observations(
    *,
    client_id: str,
    payments: Iterable[APPayment],
    obligations: Iterable[APObligation] = (),
    currency: str = "USD",
) -> tuple[RecoveryObservation, ...]:
    """Build AP overpayment observations from payment and obligation exports.

    For invoice keys with an obligation, all payments are summed and compared to
    the verified expected liability. For keys without an obligation, only exact
    same-amount duplicate clusters are emitted, and they intentionally carry no
    RuleRef so RecoveryEngine keeps them in REVIEW.
    """
    client_id = _required("client_id", client_id)
    currency = _required("currency", currency).upper()

    payment_groups: dict[tuple[str, str], list[APPayment]] = defaultdict(list)
    for payment in payments:
        payment_groups[(payment.vendor_id, payment.normalized_invoice)].append(payment)

    obligation_by_key = _obligation_index(obligations)
    observations: list[RecoveryObservation] = []

    for key in sorted(payment_groups):
        vendor_id, normalized_invoice = key
        items = sorted(payment_groups[key], key=lambda p: p.payment_id)
        obligation = obligation_by_key.get(key)

        if obligation is not None:
            actual_cents = sum(p.amount_cents for p in items)
            if actual_cents <= obligation.expected_cents:
                continue
            observations.append(RecoveryObservation(
                branch=Branch.AP,
                client_id=client_id,
                counterparty_id=vendor_id,
                reference=normalized_invoice,
                currency=currency,
                expected_cents=obligation.expected_cents,
                actual_cents=actual_cents,
                rule=obligation.rule_ref(),
                evidence=tuple(p.evidence() for p in items),
                reason="AP_OBLIGATION_OVERPAYMENT",
                confidence_basis=(
                    "verified obligation and payment evidence"
                    if obligation.verified and all(p.verified for p in items)
                    else "obligation/payment evidence requires verification"
                ),
                metadata={
                    "normalized_invoice": normalized_invoice,
                    "payment_ids": [p.payment_id for p in items],
                    "payment_count": len(items),
                    "detection_basis": "obligation_vs_total_payments",
                },
            ))
            continue

        by_amount: dict[int, list[APPayment]] = defaultdict(list)
        for payment in items:
            by_amount[payment.amount_cents].append(payment)

        for amount_cents in sorted(by_amount):
            duplicates = sorted(by_amount[amount_cents], key=lambda p: p.payment_id)
            if len(duplicates) < 2:
                continue
            observations.append(RecoveryObservation(
                branch=Branch.AP,
                client_id=client_id,
                counterparty_id=vendor_id,
                reference=f"{normalized_invoice}:{amount_cents}",
                currency=currency,
                expected_cents=amount_cents,
                actual_cents=amount_cents * len(duplicates),
                rule=None,
                evidence=tuple(p.evidence() for p in duplicates),
                reason="SUSPECTED_DUPLICATE_PAYMENT",
                confidence_basis=(
                    "same vendor + normalized invoice + exact payment amount; "
                    "verified obligation still required"
                ),
                metadata={
                    "normalized_invoice": normalized_invoice,
                    "payment_ids": [p.payment_id for p in duplicates],
                    "payment_count": len(duplicates),
                    "duplicate_amount_cents": amount_cents,
                    "detection_basis": "exact_invoice_amount_duplicate",
                },
            ))

    return tuple(observations)
