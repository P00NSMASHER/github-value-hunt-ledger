"""Deterministic commercial utility tariff calculator and overcharge detector."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable

from recoveryworks.branches.utility import from_utility_variance
from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import EvidenceRef, RuleRef


def _dec(name: str, value: str | int | Decimal) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be decimal-compatible") from exc
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


@dataclass(frozen=True)
class EnergyTier:
    up_to_kwh: Decimal | None
    rate_cents_per_kwh: Decimal

    def __post_init__(self) -> None:
        if self.up_to_kwh is not None and self.up_to_kwh <= 0:
            raise ValueError("up_to_kwh must be positive or None")
        if self.rate_cents_per_kwh < 0:
            raise ValueError("rate_cents_per_kwh must be non-negative")


@dataclass(frozen=True)
class UtilityTariff:
    tariff_id: str
    effective_from: str
    effective_to: str | None
    fixed_charge_cents: int
    energy_tiers: tuple[EnergyTier, ...]
    demand_rate_cents_per_kw: Decimal
    source_hash: str
    locator: str
    verified: bool = False
    jurisdiction: str | None = None

    def __post_init__(self) -> None:
        for name in ("tariff_id", "effective_from", "source_hash", "locator"):
            _text(name, getattr(self, name))
        if type(self.fixed_charge_cents) is not int or self.fixed_charge_cents < 0:
            raise ValueError("fixed_charge_cents must be non-negative integer cents")
        if self.demand_rate_cents_per_kw < 0:
            raise ValueError("demand_rate_cents_per_kw must be non-negative")
        if not self.energy_tiers:
            raise ValueError("at least one energy tier is required")
        previous = Decimal("0")
        saw_open = False
        for index, tier in enumerate(self.energy_tiers):
            if saw_open:
                raise ValueError("open-ended energy tier must be last")
            if tier.up_to_kwh is None:
                saw_open = True
            else:
                if tier.up_to_kwh <= previous:
                    raise ValueError("energy tier limits must increase")
                previous = tier.up_to_kwh
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")


@dataclass(frozen=True)
class UtilityBill:
    bill_id: str
    bill_date: str
    usage_kwh: Decimal
    demand_kw: Decimal
    billed_cents: int
    currency: str
    source_hash: str
    locator: str
    verified: bool = False

    def __post_init__(self) -> None:
        for name in ("bill_id", "bill_date", "currency", "source_hash", "locator"):
            _text(name, getattr(self, name))
        if self.usage_kwh < 0 or self.demand_kw < 0:
            raise ValueError("usage and demand must be non-negative")
        if type(self.billed_cents) is not int or self.billed_cents < 0:
            raise ValueError("billed_cents must be non-negative integer cents")
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")


@dataclass(frozen=True)
class UtilityCalculation:
    fixed_cents: int
    energy_cents: int
    demand_cents: int
    total_cents: int
    tier_trace: tuple[dict[str, str], ...]


def _round_cents(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calculate_expected_bill(tariff: UtilityTariff, bill: UtilityBill) -> UtilityCalculation:
    remaining = bill.usage_kwh
    previous_limit = Decimal("0")
    energy_raw = Decimal("0")
    trace: list[dict[str, str]] = []

    for tier in tariff.energy_tiers:
        if remaining <= 0:
            break
        if tier.up_to_kwh is None:
            tier_kwh = remaining
        else:
            width = tier.up_to_kwh - previous_limit
            tier_kwh = min(remaining, width)
        charge = tier_kwh * tier.rate_cents_per_kwh
        energy_raw += charge
        trace.append({
            "kwh": format(tier_kwh, "f"),
            "rate_cents_per_kwh": format(tier.rate_cents_per_kwh, "f"),
            "charge_cents_raw": format(charge, "f"),
        })
        remaining -= tier_kwh
        if tier.up_to_kwh is not None:
            previous_limit = tier.up_to_kwh

    if remaining > 0:
        raise ValueError("tariff tiers do not cover total usage")

    energy_cents = _round_cents(energy_raw)
    demand_cents = _round_cents(bill.demand_kw * tariff.demand_rate_cents_per_kw)
    total = tariff.fixed_charge_cents + energy_cents + demand_cents
    return UtilityCalculation(
        fixed_cents=tariff.fixed_charge_cents,
        energy_cents=energy_cents,
        demand_cents=demand_cents,
        total_cents=total,
        tier_trace=tuple(trace),
    )


def detect_utility_variance(
    *,
    client_id: str,
    utility_id: str,
    tariff: UtilityTariff,
    bill: UtilityBill,
) -> RecoveryObservation:
    calculation = calculate_expected_bill(tariff, bill)
    rule = RuleRef(
        rule_id=f"utility-tariff:{tariff.tariff_id}",
        source_hash=tariff.source_hash,
        effective_from=tariff.effective_from,
        effective_to=tariff.effective_to,
        verified_controlling=tariff.verified,
        source_locator=tariff.locator,
        jurisdiction=tariff.jurisdiction,
        metadata={
            "fixed_charge_cents": tariff.fixed_charge_cents,
            "demand_rate_cents_per_kw": format(tariff.demand_rate_cents_per_kw, "f"),
        },
    )
    evidence = (
        EvidenceRef(
            evidence_id=f"utility-tariff:{tariff.tariff_id}",
            source_hash=tariff.source_hash,
            locator=tariff.locator,
            kind="utility_tariff",
            verified=tariff.verified,
        ),
        EvidenceRef(
            evidence_id=f"utility-bill:{bill.bill_id}",
            source_hash=bill.source_hash,
            locator=bill.locator,
            kind="utility_bill",
            verified=bill.verified,
            metadata={
                "usage_kwh": format(bill.usage_kwh, "f"),
                "demand_kw": format(bill.demand_kw, "f"),
                "billed_cents": bill.billed_cents,
            },
        ),
    )
    return from_utility_variance(
        client_id=client_id,
        utility_id=utility_id,
        bill_id=bill.bill_id,
        bill_date=bill.bill_date,
        expected_cents=calculation.total_cents,
        billed_cents=bill.billed_cents,
        rule=rule,
        evidence=evidence,
        currency=bill.currency,
        reason="UTILITY_RECALCULATION_VARIANCE",
        confidence_basis="Decimal tariff calculation with explicit tier and demand trace",
        metadata={
            "tariff_id": tariff.tariff_id,
            "fixed_cents": calculation.fixed_cents,
            "energy_cents": calculation.energy_cents,
            "demand_cents": calculation.demand_cents,
            "tier_trace": list(calculation.tier_trace),
        },
    )


def tier(up_to_kwh: str | int | Decimal | None, rate_cents_per_kwh: str | int | Decimal) -> EnergyTier:
    return EnergyTier(
        up_to_kwh=None if up_to_kwh is None else _dec("up_to_kwh", up_to_kwh),
        rate_cents_per_kwh=_dec("rate_cents_per_kwh", rate_cents_per_kwh),
    )


def tariff(
    *,
    tariff_id: str,
    effective_from: str,
    effective_to: str | None,
    fixed_charge_cents: int,
    energy_tiers: Iterable[EnergyTier],
    demand_rate_cents_per_kw: str | int | Decimal,
    source_hash: str,
    locator: str,
    verified: bool = False,
    jurisdiction: str | None = None,
) -> UtilityTariff:
    return UtilityTariff(
        tariff_id=tariff_id,
        effective_from=effective_from,
        effective_to=effective_to,
        fixed_charge_cents=fixed_charge_cents,
        energy_tiers=tuple(energy_tiers),
        demand_rate_cents_per_kw=_dec("demand_rate_cents_per_kw", demand_rate_cents_per_kw),
        source_hash=source_hash,
        locator=locator,
        verified=verified,
        jurisdiction=jurisdiction,
    )


def bill(
    *,
    bill_id: str,
    bill_date: str,
    usage_kwh: str | int | Decimal,
    demand_kw: str | int | Decimal,
    billed_cents: int,
    currency: str,
    source_hash: str,
    locator: str,
    verified: bool = False,
) -> UtilityBill:
    return UtilityBill(
        bill_id=bill_id,
        bill_date=bill_date,
        usage_kwh=_dec("usage_kwh", usage_kwh),
        demand_kw=_dec("demand_kw", demand_kw),
        billed_cents=billed_cents,
        currency=currency,
        source_hash=source_hash,
        locator=locator,
        verified=verified,
    )
