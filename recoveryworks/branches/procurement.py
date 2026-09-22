"""ProcurementRecovery PO/contract price and approved-quantity reconciliation."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef, canonical_hash


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _iso_date(name: str, value: str) -> date:
    text = _required(name, value)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _decimal(name: str, value: str | int | float | Decimal) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _cents(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be non-negative integer cents")
    return value


def normalize_sku(value: str) -> str:
    return _required("sku", value).upper().replace(" ", "")


def _extended_cents(unit_price_cents: int, quantity: Decimal) -> int:
    raw = Decimal(unit_price_cents) * quantity
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class ProcurementInvoiceLine:
    invoice_line_id: str
    invoice_id: str
    purchaser_id: str
    supplier_id: str
    po_line_id: str
    sku: str
    invoice_date: str
    invoiced_quantity: str
    actual_line_cents: int
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "invoice_line_id", "invoice_id", "purchaser_id", "supplier_id",
            "po_line_id", "sku", "invoice_date", "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _iso_date("invoice_date", self.invoice_date)
        normalize_sku(self.sku)
        _decimal("invoiced_quantity", self.invoiced_quantity)
        _cents("actual_line_cents", self.actual_line_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def normalized_sku(self) -> str:
        return normalize_sku(self.sku)

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"procurement-invoice:{self.invoice_line_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="procurement_invoice_line",
            verified=self.verified,
            metadata={
                "invoice_id": self.invoice_id,
                "purchaser_id": self.purchaser_id,
                "supplier_id": self.supplier_id,
                "po_line_id": self.po_line_id,
                "sku": self.normalized_sku,
                "invoice_date": self.invoice_date,
                "invoiced_quantity": str(_decimal("invoiced_quantity", self.invoiced_quantity)),
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class ProcurementAuthority:
    authority_id: str
    supplier_id: str
    po_line_id: str
    sku: str
    effective_from: str
    effective_to: str | None
    contracted_unit_price_cents: int
    price_basis: str
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "authority_id", "supplier_id", "po_line_id", "sku",
            "effective_from", "price_basis", "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        start = _iso_date("effective_from", self.effective_from)
        if self.effective_to is not None:
            end = _iso_date("effective_to", self.effective_to)
            if end < start:
                raise ValueError("effective_to cannot precede effective_from")
        normalize_sku(self.sku)
        _cents("contracted_unit_price_cents", self.contracted_unit_price_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def normalized_sku(self) -> str:
        return normalize_sku(self.sku)

    def covers(self, invoice_date: str) -> bool:
        when = _iso_date("invoice_date", invoice_date)
        start = _iso_date("effective_from", self.effective_from)
        end = _iso_date("effective_to", self.effective_to) if self.effective_to else None
        return when >= start and (end is None or when <= end)

    def rule_ref(self) -> RuleRef:
        identity = {
            "schema": 1,
            "authority_id": self.authority_id,
            "supplier_id": self.supplier_id,
            "po_line_id": self.po_line_id,
            "sku": self.normalized_sku,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "contracted_unit_price_cents": self.contracted_unit_price_cents,
            "price_basis": self.price_basis,
            "source_hash": self.source_hash,
        }
        return RuleRef(
            rule_id="procurement-authority:" + canonical_hash(identity),
            source_hash=self.source_hash,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            verified_controlling=self.verified,
            source_locator=self.source_locator,
            metadata={
                "kind": "procurement_price_authority",
                "authority_id": self.authority_id,
                "supplier_id": self.supplier_id,
                "po_line_id": self.po_line_id,
                "sku": self.normalized_sku,
                "contracted_unit_price_cents": self.contracted_unit_price_cents,
                "price_basis": self.price_basis,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class ProcurementQuantityApproval:
    invoice_line_id: str
    approved_billable_quantity: str
    quantity_basis: str
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _required("invoice_line_id", self.invoice_line_id)
        _decimal("approved_billable_quantity", self.approved_billable_quantity)
        _required("quantity_basis", self.quantity_basis)
        _required("source_hash", self.source_hash)
        _required("source_locator", self.source_locator)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def quantity(self) -> Decimal:
        return _decimal("approved_billable_quantity", self.approved_billable_quantity)

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id="procurement-quantity:" + canonical_hash({
                "invoice_line_id": self.invoice_line_id,
                "approved_billable_quantity": str(self.quantity),
                "quantity_basis": self.quantity_basis,
                "source_hash": self.source_hash,
                "source_locator": self.source_locator,
            }),
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="procurement_approved_quantity",
            verified=self.verified,
            metadata={
                "invoice_line_id": self.invoice_line_id,
                "approved_billable_quantity": str(self.quantity),
                "quantity_basis": self.quantity_basis,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class ProcurementAuditException:
    reference: str
    code: str
    detail: str


@dataclass(frozen=True)
class ProcurementAuditBatch:
    observations: tuple[RecoveryObservation, ...]
    exceptions: tuple[ProcurementAuditException, ...]


def audit_procurement_lines(
    *,
    client_id: str,
    invoice_lines: Iterable[ProcurementInvoiceLine],
    authorities: Iterable[ProcurementAuthority],
    quantity_approvals: Iterable[ProcurementQuantityApproval],
    currency: str = "USD",
) -> ProcurementAuditBatch:
    client_id = _required("client_id", client_id)
    currency = _required("currency", currency).upper()

    line_groups: dict[str, list[ProcurementInvoiceLine]] = defaultdict(list)
    for line in invoice_lines:
        line_groups[line.invoice_line_id].append(line)

    authority_index: dict[tuple[str, str, str], list[ProcurementAuthority]] = defaultdict(list)
    for authority in authorities:
        authority_index[
            (authority.supplier_id, authority.po_line_id, authority.normalized_sku)
        ].append(authority)

    quantity_groups: dict[str, list[ProcurementQuantityApproval]] = defaultdict(list)
    for approval in quantity_approvals:
        quantity_groups[approval.invoice_line_id].append(approval)

    observations: list[RecoveryObservation] = []
    exceptions: list[ProcurementAuditException] = []

    for line_id in sorted(line_groups):
        values = line_groups[line_id]
        if len(values) != 1:
            exceptions.append(ProcurementAuditException(
                line_id, "DUPLICATE_PROCUREMENT_INVOICE_LINE_ID",
                f"invoice_line_id appears {len(values)} times; excluded",
            ))
            continue
        line = values[0]
        if line.purchaser_id != client_id:
            exceptions.append(ProcurementAuditException(
                line_id, "PURCHASER_SCOPE_MISMATCH",
                "purchaser_id does not match Scan 360 client_id",
            ))
            continue

        candidates = [
            authority
            for authority in authority_index.get(
                (line.supplier_id, line.po_line_id, line.normalized_sku), []
            )
            if authority.covers(line.invoice_date)
        ]
        if not candidates:
            exceptions.append(ProcurementAuditException(
                line_id, "NO_PROCUREMENT_AUTHORITY",
                "no effective PO/contract price authority covers this invoice line",
            ))
            continue
        if len(candidates) != 1:
            exceptions.append(ProcurementAuditException(
                line_id, "OVERLAPPING_PROCUREMENT_AUTHORITIES",
                f"{len(candidates)} price authorities cover this invoice line",
            ))
            continue
        authority = candidates[0]

        approvals = quantity_groups.get(line_id, [])
        if not approvals:
            exceptions.append(ProcurementAuditException(
                line_id, "NO_APPROVED_BILLABLE_QUANTITY",
                "no independent approved billable quantity is bound to this line",
            ))
            continue
        if len(approvals) != 1:
            exceptions.append(ProcurementAuditException(
                line_id, "CONFLICTING_APPROVED_QUANTITIES",
                f"{len(approvals)} approved quantities are bound to this line",
            ))
            continue
        approval = approvals[0]

        expected_cents = _extended_cents(
            authority.contracted_unit_price_cents,
            approval.quantity,
        )
        if line.actual_line_cents <= expected_cents:
            continue

        observations.append(RecoveryObservation(
            branch=Branch.PROCUREMENT,
            client_id=client_id,
            counterparty_id=line.supplier_id,
            reference=line.invoice_line_id,
            currency=currency,
            expected_cents=expected_cents,
            actual_cents=line.actual_line_cents,
            rule=authority.rule_ref(),
            evidence=(line.evidence(), approval.evidence()),
            reason="PROCUREMENT_PRICE_OR_QUANTITY_OVERCHARGE",
            confidence_basis=(
                "verified invoice + effective PO/contract price + approved billable quantity"
                if line.verified and authority.verified and approval.verified
                else "invoice/price authority/quantity evidence requires verification"
            ),
            metadata={
                "invoice_id": line.invoice_id,
                "po_line_id": line.po_line_id,
                "sku": line.normalized_sku,
                "invoice_date": line.invoice_date,
                "invoiced_quantity": str(_decimal("invoiced_quantity", line.invoiced_quantity)),
                "approved_billable_quantity": str(approval.quantity),
                "contracted_unit_price_cents": authority.contracted_unit_price_cents,
                "authority_id": authority.authority_id,
                "price_basis": authority.price_basis,
                "quantity_basis": approval.quantity_basis,
            },
        ))

    exceptions.sort(key=lambda x: (x.code, x.reference, x.detail))
    observations.sort(key=lambda x: (x.counterparty_id, x.reference))
    return ProcurementAuditBatch(tuple(observations), tuple(exceptions))
