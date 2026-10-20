"""Financial integrity layer: immutable invoice cash/credit ledger and proof gate.

This module deliberately distinguishes *invoice math* from cash settlement and
adjudicated recoveries. Typed original-invoice discounts live in canonical
schema v2; bank/refund events live here and never rewrite original charges.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Iterable, Literal

from freight.canonical_schema import CanonicalFreightRecord, verify_record
from freight.contracts import canonical_hash
from freight.rating_engine import RATED, RatingResult

MAX_CENTS = 2**63 - 1
MOVEMENT_KINDS = frozenset({
    "PAYMENT", "CREDIT_APPLIED", "REFUND",
    "PAYMENT_REVERSAL", "CREDIT_REVERSAL", "REFUND_REVERSAL",
})
ORIGINAL_KINDS = {
    "PAYMENT_REVERSAL": "PAYMENT",
    "CREDIT_REVERSAL": "CREDIT_APPLIED",
    "REFUND_REVERSAL": "REFUND",
}
PROVENANCE_TYPES = frozenset({
    "CUSTOMER_STATEMENT", "BANK_CLEARED", "CARRIER_CREDIT",
    "SETTLEMENT_PROVIDER", "PUBLIC_DISCLOSURE",
})


def _required(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value):
        raise ValueError(name + " must be nonempty printable text")
    return value.strip()


def _cents(value: int, name: str) -> int:
    if type(value) is not int or not 0 < value <= MAX_CENTS:
        raise ValueError(name + " must be a positive exact integer cents amount")
    return value


def _sha(value: str, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(name + " must be a lowercase SHA-256")
    return value


@dataclass(frozen=True)
class FinancialMovement:
    movement_id: str
    kind: str
    amount_cents: int
    occurred_on: str
    source_sha256: str
    provenance_type: str
    independently_verified: bool = False
    reverses_movement_id: str | None = None

    def __post_init__(self) -> None:
        _required(self.movement_id, "movement_id")
        if self.kind not in MOVEMENT_KINDS:
            raise ValueError("unsupported financial movement kind")
        _cents(self.amount_cents, "amount_cents")
        try:
            if date.fromisoformat(self.occurred_on).isoformat() != self.occurred_on:
                raise ValueError("movement date must be canonical YYYY-MM-DD")
        except (TypeError, ValueError) as exc:
            raise ValueError("movement date must be YYYY-MM-DD") from exc
        _sha(self.source_sha256, "source_sha256")
        if self.provenance_type not in PROVENANCE_TYPES:
            raise ValueError("unsupported financial provenance type")
        if type(self.independently_verified) is not bool:
            raise ValueError("independently_verified must be boolean")
        if self.kind in ORIGINAL_KINDS:
            _required(self.reverses_movement_id, "reverses_movement_id")
        elif self.reverses_movement_id is not None:
            raise ValueError("ordinary movement cannot reverse another movement")
        if self.independently_verified and self.provenance_type not in {
            "BANK_CLEARED", "SETTLEMENT_PROVIDER", "CARRIER_CREDIT",
        }:
            raise ValueError("same-source declarations cannot be independently verified")


@dataclass(frozen=True)
class FinancialBalance:
    invoice_id: str
    original_invoice_net_cents: int
    gross_charges_cents: int
    original_discount_and_credit_cents: int
    declared_net_cash_cents: int
    verified_net_cash_cents: int
    declared_net_postinvoice_credits_cents: int
    verified_net_postinvoice_credits_cents: int
    remaining_balance_cents: int
    status: str
    blockers: tuple[str, ...]
    movement_count: int
    receipt_hash: str


def replay_financial_movements(
    record: CanonicalFreightRecord,
    movements: Iterable[FinancialMovement],
) -> FinancialBalance:
    """Rebuild balances from immutable original invoice + independent movements.

    Original billed net = positive charges - original typed discounts/credits.
    Payments and refunds affect cash; post-invoice credit notes affect debt.
    Reversals exactly cancel ONE prior matching movement, never a revised invoice.
    A negative/open balance is not independently adjudicated recovered cash.
    """
    verify_record(record)
    events = tuple(movements)
    if any(not isinstance(e, FinancialMovement) for e in events):
        raise ValueError("financial movements must be typed")
    seen: dict[str, FinancialMovement] = {}
    reversed_ids: set[str] = set()
    net_cash = net_credit = checked_cash = checked_credit = 0
    for event in events:
        if event.movement_id in seen:
            raise ValueError("duplicate financial movement id")
        if event.source_sha256 in {s.sha256 for s in record.sources} and event.independently_verified:
            raise ValueError("original invoice cannot independently prove cash settlement")
        sign = 1
        base_kind = event.kind
        if event.kind in ORIGINAL_KINDS:
            previous = seen.get(event.reverses_movement_id)
            if previous is None:
                raise ValueError("reversal requires an earlier event")
            if previous.kind != ORIGINAL_KINDS[event.kind]:
                raise ValueError("reversal must target the corresponding movement type")
            if previous.movement_id in reversed_ids:
                raise ValueError("original movement has already been reversed")
            if previous.amount_cents != event.amount_cents:
                raise ValueError("partial reversals require their own separately linked credit")
            if not event.independently_verified and previous.independently_verified:
                raise ValueError("verified movement cannot be reversed by unverified evidence")
            reversed_ids.add(previous.movement_id)
            sign = -1
            base_kind = previous.kind
        if base_kind == "PAYMENT":
            net_cash += sign * event.amount_cents
            if event.independently_verified:
                checked_cash += sign * event.amount_cents
        elif base_kind == "REFUND":
            net_cash -= sign * event.amount_cents
            if event.independently_verified:
                checked_cash -= sign * event.amount_cents
        else:
            net_credit += sign * event.amount_cents
            if event.independently_verified:
                checked_credit += sign * event.amount_cents
        seen[event.movement_id] = event
    outstanding = record.billed_total_cents - net_cash - net_credit
    blockers = set()
    if any(not e.independently_verified for e in events):
        blockers.add("SETTLEMENT_EVIDENCE_NOT_ALL_INDEPENDENT")
    if outstanding < 0:
        blockers.add("NEGATIVE_BALANCE_REQUIRES_INDEPENDENT_REVIEW")
    status = "REVIEW_REQUIRED" if blockers else "BALANCE_RECONCILED"
    body = {
        "schema": 1, "record_hash": record.record_hash,
        "movement_hashes": [canonical_hash(asdict(e)) for e in events],
        "net_cash": net_cash, "net_credit": net_credit,
        "verified_cash": checked_cash, "verified_credit": checked_credit,
        "outstanding": outstanding, "status": status,
        "blockers": sorted(blockers),
    }
    return FinancialBalance(
        invoice_id=record.invoice_id,
        original_invoice_net_cents=record.billed_total_cents,
        gross_charges_cents=record.gross_charge_cents,
        original_discount_and_credit_cents=record.adjustment_total_cents,
        declared_net_cash_cents=net_cash,
        verified_net_cash_cents=checked_cash,
        declared_net_postinvoice_credits_cents=net_credit,
        verified_net_postinvoice_credits_cents=checked_credit,
        remaining_balance_cents=outstanding,
        status=status, blockers=tuple(sorted(blockers)),
        movement_count=len(events), receipt_hash=canonical_hash(body),
    )


@dataclass(frozen=True)
class FinancialClaimGate:
    invoice_id: str
    rated_discrepancy_cents: int | None
    validated_discrepancy_cents: int
    realized_recovery_cents: int
    status: str
    blockers: tuple[str, ...]
    gate_hash: str


def financial_claim_gate(
    record: CanonicalFreightRecord,
    rating: RatingResult,
    balance: FinancialBalance,
    *,
    independent_adjudication_sha256: str | None = None,
    human_release_approved: bool = False,
) -> FinancialClaimGate:
    """Fail closed: rating is not adjudication; same-source payment is not cash."""
    verify_record(record)
    if record.record_hash != rating.record_hash or record.invoice_id != balance.invoice_id:
        raise ValueError("rating and balance must refer to this exact original invoice")
    _sha(balance.receipt_hash, "balance receipt_hash")
    if type(human_release_approved) is not bool:
        raise ValueError("human_release_approved must be boolean")
    if independent_adjudication_sha256 is not None:
        _sha(independent_adjudication_sha256, "independent_adjudication_sha256")
        if independent_adjudication_sha256 in {s.sha256 for s in record.sources}:
            raise ValueError("invoice source cannot also serve as independent adjudication")
    candidate = (
        rating.variance_cents if rating.status == RATED and rating.authority_verified
        else None
    )
    blockers = set(balance.blockers)
    if rating.status != RATED or not rating.authority_verified:
        blockers.add("NO_VERIFIED_RATING_AUTHORITY")
    if independent_adjudication_sha256 is None:
        blockers.add("MISSING_INDEPENDENT_ADJUDICATION")
    if not human_release_approved:
        blockers.add("HUMAN_RELEASE_NOT_APPROVED")
    if candidate is None or candidate <= 0:
        blockers.add("NO_POSITIVE_RATE_DISCREPANCY")
    if balance.verified_net_cash_cents <= 0:
        blockers.add("NO_INDEPENDENT_BANK_CLEARED_PAYMENT")
    # Even if the evidentiary gates are clear, invoice-to-payment only proves
    # paid exposure; a separately observed carrier refund must establish cash
    # actually recovered. Never infer realized recovery from rated variance.
    validated = candidate if not blockers and candidate is not None else 0
    realized = 0
    status = "VALIDATED_OPPORTUNITY" if validated else "REVIEW_REQUIRED"
    body = {
        "schema": 1, "record_hash": record.record_hash,
        "rating_hash": rating.rating_hash, "balance_hash": balance.receipt_hash,
        "adjudication_source": independent_adjudication_sha256,
        "human_release": human_release_approved, "validated": validated,
        "realized": realized, "status": status, "blockers": sorted(blockers),
    }
    return FinancialClaimGate(
        record.invoice_id, candidate, validated, realized, status,
        tuple(sorted(blockers)), canonical_hash(body),
    )
