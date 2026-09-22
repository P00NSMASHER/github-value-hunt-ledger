"""UtilityRecovery deterministic tariff audit adapter.

The first production slice intentionally supports only explicit, deterministic
charge primitives. Unsupported or overlapping tariff logic is surfaced for
review rather than evaluated dynamically.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from typing import Any, Iterable, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef, canonical_hash


class UtilityChargeKind(str, Enum):
    FIXED = "fixed"
    ENERGY = "energy"
    DEMAND = "demand"
    REACTIVE = "reactive"


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _nonnegative_cents(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be non-negative integer cents")
    return value


def _positive_int(name: str, value: int) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def normalize_service_class(value: str) -> str:
    return _required("service_class", value).upper().replace(" ", "").replace("-", "")


def _iso_date(name: str, value: str) -> date:
    text = _required(name, value)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _quantity(name: str, value: str | int | float | Decimal) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


@dataclass(frozen=True)
class UtilityCharge:
    name: str
    kind: UtilityChargeKind
    amount_cents: int | None = None
    rate_micros_per_unit: int | None = None

    def __post_init__(self) -> None:
        _required("name", self.name)
        if self.kind is UtilityChargeKind.FIXED:
            if self.amount_cents is None:
                raise ValueError("fixed charge requires amount_cents")
            _nonnegative_cents("amount_cents", self.amount_cents)
            if self.rate_micros_per_unit is not None:
                raise ValueError("fixed charge cannot define rate_micros_per_unit")
        else:
            if self.rate_micros_per_unit is None:
                raise ValueError(f"{self.kind.value} charge requires rate_micros_per_unit")
            _positive_int("rate_micros_per_unit", self.rate_micros_per_unit)
            if self.amount_cents is not None:
                raise ValueError("rate charge cannot define amount_cents")


@dataclass(frozen=True)
class UtilityTariff:
    utility_id: str
    service_class: str
    effective_from: str
    effective_to: str | None
    charges: tuple[UtilityCharge, ...]
    source_hash: str
    source_locator: str
    verified: bool
    minimum_bill_cents: int = 0
    jurisdiction: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("utility_id", "service_class", "effective_from", "source_hash", "source_locator"):
            _required(name, getattr(self, name))
        _iso_date("effective_from", self.effective_from)
        if self.effective_to is not None:
            if _iso_date("effective_to", self.effective_to) < _iso_date(
                "effective_from", self.effective_from
            ):
                raise ValueError("effective_to cannot precede effective_from")
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        _nonnegative_cents("minimum_bill_cents", self.minimum_bill_cents)
        if not self.charges and self.minimum_bill_cents == 0:
            raise ValueError("tariff requires at least one charge or a minimum bill")

    @property
    def normalized_service_class(self) -> str:
        return normalize_service_class(self.service_class)

    def covers(self, bill_date: str) -> bool:
        when = _iso_date("bill_date", bill_date)
        start = _iso_date("effective_from", self.effective_from)
        end = _iso_date("effective_to", self.effective_to) if self.effective_to else None
        return when >= start and (end is None or when <= end)

    def rule_ref(self) -> RuleRef:
        identity = {
            "schema": 1,
            "utility_id": self.utility_id,
            "service_class": self.normalized_service_class,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "minimum_bill_cents": self.minimum_bill_cents,
            "charges": [
                {
                    "name": c.name,
                    "kind": c.kind.value,
                    "amount_cents": c.amount_cents,
                    "rate_micros_per_unit": c.rate_micros_per_unit,
                }
                for c in self.charges
            ],
            "source_hash": self.source_hash,
        }
        return RuleRef(
            rule_id="utility-tariff:" + canonical_hash(identity),
            source_hash=self.source_hash,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            verified_controlling=self.verified,
            source_locator=self.source_locator,
            jurisdiction=self.jurisdiction,
            metadata={
                "kind": "utility_tariff",
                "utility_id": self.utility_id,
                "service_class": self.normalized_service_class,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class UtilityBill:
    bill_id: str
    utility_id: str
    account_id: str
    service_class: str
    bill_date: str
    actual_cents: int
    billed_kwh: str = "0"
    billed_demand_kw: str = "0"
    billed_reactive_kva: str = "0"
    source_hash: str = ""
    source_locator: str = ""
    verified: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "bill_id", "utility_id", "account_id", "service_class",
            "bill_date", "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _iso_date("bill_date", self.bill_date)
        _nonnegative_cents("actual_cents", self.actual_cents)
        _quantity("billed_kwh", self.billed_kwh)
        _quantity("billed_demand_kw", self.billed_demand_kw)
        _quantity("billed_reactive_kva", self.billed_reactive_kva)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def normalized_service_class(self) -> str:
        return normalize_service_class(self.service_class)

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"utility-bill:{self.bill_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="utility_bill",
            verified=self.verified,
            metadata={
                "utility_id": self.utility_id,
                "account_id": self.account_id,
                "service_class": self.normalized_service_class,
                "bill_date": self.bill_date,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class UtilityAuditException:
    bill_id: str
    code: str
    detail: str


@dataclass(frozen=True)
class UtilityAuditBatch:
    observations: tuple[RecoveryObservation, ...]
    exceptions: tuple[UtilityAuditException, ...]


def _rate_charge_cents(rate_micros_per_unit: int, quantity: Decimal) -> int:
    # 1 currency unit = 1,000,000 micros = 100 cents, so micros / 10,000 = cents.
    raw_cents = Decimal(rate_micros_per_unit) * quantity / Decimal(10000)
    return int(raw_cents.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calculate_expected_bill(
    bill: UtilityBill,
    tariff: UtilityTariff,
) -> tuple[int, tuple[dict[str, Any], ...]]:
    if bill.utility_id != tariff.utility_id:
        raise ValueError("bill utility does not match tariff utility")
    if bill.normalized_service_class != tariff.normalized_service_class:
        raise ValueError("bill service class does not match tariff service class")
    if not tariff.covers(bill.bill_date):
        raise ValueError("tariff does not cover bill date")

    quantities = {
        UtilityChargeKind.ENERGY: _quantity("billed_kwh", bill.billed_kwh),
        UtilityChargeKind.DEMAND: _quantity("billed_demand_kw", bill.billed_demand_kw),
        UtilityChargeKind.REACTIVE: _quantity(
            "billed_reactive_kva", bill.billed_reactive_kva
        ),
    }
    total = 0
    trace: list[dict[str, Any]] = []
    for charge in tariff.charges:
        if charge.kind is UtilityChargeKind.FIXED:
            cents = charge.amount_cents or 0
            quantity = None
        else:
            quantity = quantities[charge.kind]
            cents = _rate_charge_cents(charge.rate_micros_per_unit or 0, quantity)
        total += cents
        trace.append({
            "name": charge.name,
            "kind": charge.kind.value,
            "quantity": None if quantity is None else str(quantity),
            "amount_cents": cents,
            "rate_micros_per_unit": charge.rate_micros_per_unit,
        })

    if total < tariff.minimum_bill_cents:
        trace.append({
            "name": "minimum_bill",
            "kind": "minimum",
            "amount_cents": tariff.minimum_bill_cents - total,
            "pre_minimum_cents": total,
        })
        total = tariff.minimum_bill_cents

    return total, tuple(trace)


def audit_utility_bills(
    *,
    client_id: str,
    bills: Iterable[UtilityBill],
    tariffs: Iterable[UtilityTariff],
    currency: str = "USD",
) -> UtilityAuditBatch:
    client_id = _required("client_id", client_id)
    currency = _required("currency", currency).upper()

    tariff_index: dict[tuple[str, str], list[UtilityTariff]] = {}
    for tariff in tariffs:
        tariff_index.setdefault(
            (tariff.utility_id, tariff.normalized_service_class), []
        ).append(tariff)

    observations: list[RecoveryObservation] = []
    exceptions: list[UtilityAuditException] = []

    for bill in sorted(bills, key=lambda b: b.bill_id):
        candidates = [
            tariff
            for tariff in tariff_index.get(
                (bill.utility_id, bill.normalized_service_class), []
            )
            if tariff.covers(bill.bill_date)
        ]
        if not candidates:
            exceptions.append(UtilityAuditException(
                bill.bill_id,
                "NO_TARIFF_VERSION",
                "no tariff version covers the bill date/service class",
            ))
            continue
        if len(candidates) > 1:
            exceptions.append(UtilityAuditException(
                bill.bill_id,
                "OVERLAPPING_TARIFF_VERSIONS",
                f"{len(candidates)} tariff versions cover the same bill",
            ))
            continue

        tariff = candidates[0]
        expected_cents, trace = calculate_expected_bill(bill, tariff)
        if bill.actual_cents <= expected_cents:
            continue

        observations.append(RecoveryObservation(
            branch=Branch.UTILITY,
            client_id=client_id,
            counterparty_id=bill.utility_id,
            reference=bill.bill_id,
            currency=currency,
            expected_cents=expected_cents,
            actual_cents=bill.actual_cents,
            rule=tariff.rule_ref(),
            evidence=(bill.evidence(),),
            reason="UTILITY_TARIFF_OVERCHARGE",
            confidence_basis=(
                "verified effective-dated tariff + verified bill"
                if tariff.verified and bill.verified
                else "tariff/bill source requires verification"
            ),
            metadata={
                "account_id": bill.account_id,
                "service_class": bill.normalized_service_class,
                "bill_date": bill.bill_date,
                "calculation_trace": list(trace),
                "tariff_source_hash": tariff.source_hash,
            },
        ))

    return UtilityAuditBatch(tuple(observations), tuple(exceptions))
