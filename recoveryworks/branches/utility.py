"""UtilityRecovery deterministic tariff audit adapter.

The production adapter supports explicit effective-dated charge primitives only.
No Python eval or free-form formula execution is permitted. Missing quantities,
overlapping tariff versions, and unsupported tariff logic fail closed.
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
    DAILY_FIXED = "daily_fixed"
    ENERGY = "energy"
    TIERED_ENERGY = "tiered_energy"
    TOU_ENERGY = "tou_energy"
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


def normalize_period(value: str) -> str:
    return _required("period", value).upper().replace(" ", "_").replace("-", "_")


def _iso_date(name: str, value: str) -> date:
    text = _required(name, value)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _quantity(name: str, value: str | int | float | Decimal | None) -> Decimal:
    if value is None or str(value).strip() == "":
        raise ValueError(f"{name} is required by the selected tariff")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


@dataclass(frozen=True)
class UtilityTier:
    rate_micros_per_unit: int
    up_to_kwh: str | None = None

    def __post_init__(self) -> None:
        _positive_int("rate_micros_per_unit", self.rate_micros_per_unit)
        if self.up_to_kwh is not None:
            threshold = _quantity("up_to_kwh", self.up_to_kwh)
            if threshold <= 0:
                raise ValueError("up_to_kwh must be positive")


@dataclass(frozen=True)
class UtilityCharge:
    name: str
    kind: UtilityChargeKind
    amount_cents: int | None = None
    rate_micros_per_unit: int | None = None
    tiers: tuple[UtilityTier, ...] = ()
    period: str | None = None

    def __post_init__(self) -> None:
        _required("name", self.name)

        if self.kind is UtilityChargeKind.FIXED:
            if self.amount_cents is None:
                raise ValueError("fixed charge requires amount_cents")
            _nonnegative_cents("amount_cents", self.amount_cents)
            if self.rate_micros_per_unit is not None or self.tiers or self.period is not None:
                raise ValueError("fixed charge cannot define rate, tiers, or period")
            return

        if self.kind is UtilityChargeKind.TIERED_ENERGY:
            if self.amount_cents is not None or self.rate_micros_per_unit is not None:
                raise ValueError("tiered energy uses tiers, not scalar amount/rate")
            if not self.tiers:
                raise ValueError("tiered energy requires tiers")
            if self.period is not None:
                raise ValueError("tiered energy cannot define a TOU period")
            previous = Decimal("0")
            open_ended_seen = False
            for index, tier in enumerate(self.tiers):
                if open_ended_seen:
                    raise ValueError("open-ended tier must be final")
                if tier.up_to_kwh is None:
                    open_ended_seen = True
                    if index != len(self.tiers) - 1:
                        raise ValueError("open-ended tier must be final")
                    continue
                threshold = _quantity("up_to_kwh", tier.up_to_kwh)
                if threshold <= previous:
                    raise ValueError("tier thresholds must be strictly increasing")
                previous = threshold
            if not open_ended_seen:
                raise ValueError("tiered energy requires a final open-ended tier")
            return

        if self.rate_micros_per_unit is None:
            raise ValueError(f"{self.kind.value} charge requires rate_micros_per_unit")
        _positive_int("rate_micros_per_unit", self.rate_micros_per_unit)
        if self.amount_cents is not None or self.tiers:
            raise ValueError("rate charge cannot define amount_cents or tiers")

        if self.kind is UtilityChargeKind.TOU_ENERGY:
            normalize_period(self.period or "")
        elif self.period is not None:
            raise ValueError("period is only valid for tou_energy charges")


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
        start = _iso_date("effective_from", self.effective_from)
        if self.effective_to is not None:
            if _iso_date("effective_to", self.effective_to) < start:
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

    def covers_period(self, service_start: str, service_end: str) -> bool:
        start = _iso_date("service_start", service_start)
        end = _iso_date("service_end", service_end)
        tariff_start = _iso_date("effective_from", self.effective_from)
        tariff_end = _iso_date("effective_to", self.effective_to) if self.effective_to else None
        return start >= tariff_start and (tariff_end is None or end <= tariff_end)

    def overlaps_period(self, service_start: str, service_end: str) -> bool:
        start = _iso_date("service_start", service_start)
        end = _iso_date("service_end", service_end)
        tariff_start = _iso_date("effective_from", self.effective_from)
        tariff_end = _iso_date("effective_to", self.effective_to) if self.effective_to else None
        return tariff_start <= end and (tariff_end is None or tariff_end >= start)

    def rule_ref(self) -> RuleRef:
        identity = {
            "schema": 2,
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
                    "period": c.period,
                    "tiers": [
                        {
                            "up_to_kwh": tier.up_to_kwh,
                            "rate_micros_per_unit": tier.rate_micros_per_unit,
                        }
                        for tier in c.tiers
                    ],
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
    billed_kwh: str | None = None
    billed_demand_kw: str | None = None
    billed_reactive_kva: str | None = None
    days_used: int | None = None
    billed_kwh_by_period: Mapping[str, str] = field(default_factory=dict)
    service_start: str | None = None
    service_end: str | None = None
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
        for name, value in (
            ("billed_kwh", self.billed_kwh),
            ("billed_demand_kw", self.billed_demand_kw),
            ("billed_reactive_kva", self.billed_reactive_kva),
        ):
            if value not in (None, ""):
                _quantity(name, value)
        if self.days_used is not None:
            _positive_int("days_used", self.days_used)
        for period, value in self.billed_kwh_by_period.items():
            normalize_period(period)
            _quantity(f"billed_kwh_by_period[{period}]", value)
        if (self.service_start is None) != (self.service_end is None):
            raise ValueError("service_start and service_end must be supplied together")
        if self.service_start is not None and self.service_end is not None:
            start = _iso_date("service_start", self.service_start)
            end = _iso_date("service_end", self.service_end)
            if end < start:
                raise ValueError("service_end cannot precede service_start")
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def normalized_service_class(self) -> str:
        return normalize_service_class(self.service_class)

    @property
    def normalized_period_quantities(self) -> dict[str, str]:
        return {normalize_period(k): v for k, v in self.billed_kwh_by_period.items()}

    @property
    def has_service_period(self) -> bool:
        return self.service_start is not None and self.service_end is not None

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
                "service_start": self.service_start,
                "service_end": self.service_end,
                "days_used": self.days_used,
                "tou_periods": sorted(self.normalized_period_quantities),
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
    raw_cents = Decimal(rate_micros_per_unit) * quantity / Decimal(10000)
    return int(raw_cents.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _tiered_charge_cents(
    quantity: Decimal,
    tiers: tuple[UtilityTier, ...],
) -> tuple[int, list[dict[str, Any]]]:
    remaining = quantity
    lower = Decimal("0")
    total = 0
    details: list[dict[str, Any]] = []

    for index, tier in enumerate(tiers):
        if remaining <= 0:
            break
        if tier.up_to_kwh is None:
            units = remaining
        else:
            upper = _quantity("up_to_kwh", tier.up_to_kwh)
            capacity = max(upper - lower, Decimal("0"))
            units = min(remaining, capacity)
        cents = _rate_charge_cents(tier.rate_micros_per_unit, units)
        total += cents
        details.append({
            "tier": index + 1,
            "from_kwh": str(lower),
            "to_kwh": tier.up_to_kwh,
            "quantity": str(units),
            "rate_micros_per_unit": tier.rate_micros_per_unit,
            "amount_cents": cents,
        })
        remaining -= units
        if tier.up_to_kwh is not None:
            lower = _quantity("up_to_kwh", tier.up_to_kwh)

    if remaining > 0:
        raise ValueError("tier schedule does not cover billed_kwh")
    return total, details


def calculate_expected_bill(
    bill: UtilityBill,
    tariff: UtilityTariff,
) -> tuple[int, tuple[dict[str, Any], ...]]:
    if bill.utility_id != tariff.utility_id:
        raise ValueError("bill utility does not match tariff utility")
    if bill.normalized_service_class != tariff.normalized_service_class:
        raise ValueError("bill service class does not match tariff service class")
    if bill.has_service_period:
        if not tariff.covers_period(bill.service_start or "", bill.service_end or ""):
            raise ValueError("tariff does not cover full service period")
    elif not tariff.covers(bill.bill_date):
        raise ValueError("tariff does not cover bill date")

    period_quantities = bill.normalized_period_quantities
    total = 0
    trace: list[dict[str, Any]] = []

    for charge in tariff.charges:
        quantity: Decimal | None = None
        tier_details: list[dict[str, Any]] | None = None

        if charge.kind is UtilityChargeKind.FIXED:
            cents = charge.amount_cents or 0
        elif charge.kind is UtilityChargeKind.DAILY_FIXED:
            if bill.days_used is None:
                raise ValueError("days_used is required by daily_fixed tariff charge")
            quantity = Decimal(bill.days_used)
            cents = _rate_charge_cents(charge.rate_micros_per_unit or 0, quantity)
        elif charge.kind is UtilityChargeKind.ENERGY:
            quantity = _quantity("billed_kwh", bill.billed_kwh)
            cents = _rate_charge_cents(charge.rate_micros_per_unit or 0, quantity)
        elif charge.kind is UtilityChargeKind.TIERED_ENERGY:
            quantity = _quantity("billed_kwh", bill.billed_kwh)
            cents, tier_details = _tiered_charge_cents(quantity, charge.tiers)
        elif charge.kind is UtilityChargeKind.TOU_ENERGY:
            period = normalize_period(charge.period or "")
            if period not in period_quantities:
                raise ValueError(f"TOU quantity for period {period} is required")
            quantity = _quantity(
                f"billed_kwh_by_period[{period}]",
                period_quantities[period],
            )
            cents = _rate_charge_cents(charge.rate_micros_per_unit or 0, quantity)
        elif charge.kind is UtilityChargeKind.DEMAND:
            quantity = _quantity("billed_demand_kw", bill.billed_demand_kw)
            cents = _rate_charge_cents(charge.rate_micros_per_unit or 0, quantity)
        elif charge.kind is UtilityChargeKind.REACTIVE:
            quantity = _quantity("billed_reactive_kva", bill.billed_reactive_kva)
            cents = _rate_charge_cents(charge.rate_micros_per_unit or 0, quantity)
        else:
            raise ValueError(f"unsupported charge kind: {charge.kind}")

        total += cents
        trace.append({
            "name": charge.name,
            "kind": charge.kind.value,
            "period": charge.period,
            "quantity": None if quantity is None else str(quantity),
            "amount_cents": cents,
            "rate_micros_per_unit": charge.rate_micros_per_unit,
            "tiers": tier_details,
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
        versions = tariff_index.get(
            (bill.utility_id, bill.normalized_service_class), []
        )
        if bill.has_service_period:
            candidates = [
                tariff
                for tariff in versions
                if tariff.covers_period(bill.service_start or "", bill.service_end or "")
            ]
            if not candidates:
                overlaps = [
                    tariff
                    for tariff in versions
                    if tariff.overlaps_period(bill.service_start or "", bill.service_end or "")
                ]
                if len(overlaps) > 1:
                    exceptions.append(UtilityAuditException(
                        bill.bill_id,
                        "SERVICE_PERIOD_SPANS_TARIFF_CHANGE",
                        "service period overlaps multiple tariff versions; interval usage is required",
                    ))
                elif len(overlaps) == 1:
                    exceptions.append(UtilityAuditException(
                        bill.bill_id,
                        "PARTIAL_TARIFF_COVERAGE",
                        "no single tariff version covers the full service period",
                    ))
                else:
                    exceptions.append(UtilityAuditException(
                        bill.bill_id,
                        "NO_TARIFF_VERSION",
                        "no tariff version covers the service period/service class",
                    ))
                continue
        else:
            candidates = [tariff for tariff in versions if tariff.covers(bill.bill_date)]
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
        try:
            expected_cents, trace = calculate_expected_bill(bill, tariff)
        except ValueError as exc:
            exceptions.append(UtilityAuditException(
                bill.bill_id,
                "MISSING_OR_INVALID_BILL_QUANTITY",
                str(exc),
            ))
            continue

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
                "service_start": bill.service_start,
                "service_end": bill.service_end,
                "rate_selection_basis": "service_period" if bill.has_service_period else "bill_date",
                "calculation_trace": list(trace),
                "tariff_source_hash": tariff.source_hash,
            },
        ))

    return UtilityAuditBatch(tuple(observations), tuple(exceptions))
