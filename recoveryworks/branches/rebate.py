"""RebateRecovery deterministic supplier-rebate audit engine.

The contract must state whether tiers are retroactive or incremental. The engine
never defaults between those conventions because they can produce materially
different rebate amounts.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from typing import Any, Iterable, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef, canonical_hash


class RebateTierMode(str, Enum):
    RETROACTIVE = "retroactive"
    INCREMENTAL = "incremental"


class RebateMeasurementBasis(str, Enum):
    UNITS = "units"
    SPEND = "spend"


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


def _rebate_cents(base_dollars: Decimal, rate_bps: int) -> int:
    dollars = base_dollars * Decimal(rate_bps) / Decimal(10000)
    return int((dollars * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class RebateTier:
    min_measure: str
    max_measure: str | None
    rate_bps: int

    def __post_init__(self) -> None:
        minimum = _decimal("min_measure", self.min_measure)
        if self.max_measure is not None:
            maximum = _decimal("max_measure", self.max_measure)
            if maximum <= minimum:
                raise ValueError("max_measure must be greater than min_measure")
        if type(self.rate_bps) is not int or not 0 <= self.rate_bps <= 10000:
            raise ValueError("rate_bps must be integer between 0 and 10000")


@dataclass(frozen=True)
class RebateProgram:
    supplier_id: str
    program_id: str
    period_start: str
    period_end: str
    tier_mode: RebateTierMode
    measurement_basis: RebateMeasurementBasis
    tiers: tuple[RebateTier, ...]
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("supplier_id", "program_id", "source_hash", "source_locator"):
            _required(name, getattr(self, name))
        start = _iso_date("period_start", self.period_start)
        end = _iso_date("period_end", self.period_end)
        if end < start:
            raise ValueError("period_end cannot precede period_start")
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        if not self.tiers:
            raise ValueError("rebate program requires tiers")

        ordered = sorted(self.tiers, key=lambda tier: _decimal("min_measure", tier.min_measure))
        if _decimal("first tier min_measure", ordered[0].min_measure) != 0:
            raise ValueError("rebate tiers must start at zero")
        for index, tier in enumerate(ordered):
            if index == len(ordered) - 1:
                if tier.max_measure is not None:
                    raise ValueError("final rebate tier must be open-ended")
                continue
            if tier.max_measure is None:
                raise ValueError("only final rebate tier may be open-ended")
            current_max = _decimal("max_measure", tier.max_measure)
            next_min = _decimal("next min_measure", ordered[index + 1].min_measure)
            if current_max != next_min:
                raise ValueError("rebate tiers must be contiguous")

    def covers(self, when: str) -> bool:
        value = _iso_date("purchase_date", when)
        return _iso_date("period_start", self.period_start) <= value <= _iso_date(
            "period_end", self.period_end
        )

    @property
    def ordered_tiers(self) -> tuple[RebateTier, ...]:
        return tuple(
            sorted(self.tiers, key=lambda tier: _decimal("min_measure", tier.min_measure))
        )

    def rule_ref(self) -> RuleRef:
        identity = {
            "schema": 1,
            "supplier_id": self.supplier_id,
            "program_id": self.program_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "tier_mode": self.tier_mode.value,
            "measurement_basis": self.measurement_basis.value,
            "tiers": [
                {
                    "min_measure": tier.min_measure,
                    "max_measure": tier.max_measure,
                    "rate_bps": tier.rate_bps,
                }
                for tier in self.ordered_tiers
            ],
            "source_hash": self.source_hash,
        }
        return RuleRef(
            rule_id="rebate-program:" + canonical_hash(identity),
            source_hash=self.source_hash,
            effective_from=self.period_start,
            effective_to=self.period_end,
            verified_controlling=self.verified,
            source_locator=self.source_locator,
            metadata={
                "kind": "rebate_program",
                "supplier_id": self.supplier_id,
                "program_id": self.program_id,
                "tier_mode": self.tier_mode.value,
                "measurement_basis": self.measurement_basis.value,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class RebatePurchaseLine:
    purchase_id: str
    supplier_id: str
    program_id: str
    purchase_date: str
    quantity: str
    net_spend_cents: int
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "purchase_id", "supplier_id", "program_id", "purchase_date",
            "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _iso_date("purchase_date", self.purchase_date)
        _decimal("quantity", self.quantity)
        _cents("net_spend_cents", self.net_spend_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"rebate-purchase:{self.purchase_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="rebate_purchase",
            verified=self.verified,
            metadata={
                "supplier_id": self.supplier_id,
                "program_id": self.program_id,
                "purchase_date": self.purchase_date,
                "quantity": self.quantity,
                "net_spend_cents": self.net_spend_cents,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class RebateSettlement:
    settlement_id: str
    supplier_id: str
    program_id: str
    amount_received_cents: int
    settlement_date: str
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "settlement_id", "supplier_id", "program_id", "settlement_date",
            "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _iso_date("settlement_date", self.settlement_date)
        _cents("amount_received_cents", self.amount_received_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"rebate-settlement:{self.settlement_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="rebate_settlement",
            verified=self.verified,
            metadata={
                "supplier_id": self.supplier_id,
                "program_id": self.program_id,
                "settlement_date": self.settlement_date,
                "amount_received_cents": self.amount_received_cents,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class RebateAuditException:
    reference: str
    code: str
    detail: str


@dataclass(frozen=True)
class RebateCalculation:
    expected_cents: int
    total_quantity: str
    total_spend_cents: int
    breakdown: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class RebateAuditBatch:
    observations: tuple[RecoveryObservation, ...]
    exceptions: tuple[RebateAuditException, ...]


def _overlap(
    low: Decimal,
    high: Decimal,
    band_low: Decimal,
    band_high: Decimal | None,
) -> Decimal:
    upper = high if band_high is None else min(high, band_high)
    lower = max(low, band_low)
    return max(upper - lower, Decimal("0"))


def _containing_tier(program: RebateProgram, measure: Decimal) -> RebateTier:
    chosen = program.ordered_tiers[0]
    for tier in program.ordered_tiers:
        minimum = _decimal("min_measure", tier.min_measure)
        maximum = (
            None if tier.max_measure is None
            else _decimal("max_measure", tier.max_measure)
        )
        if measure >= minimum and (maximum is None or measure < maximum):
            return tier
        if measure >= minimum:
            chosen = tier
    return chosen


def calculate_rebate(
    program: RebateProgram,
    purchases: Iterable[RebatePurchaseLine],
) -> RebateCalculation:
    lines = tuple(sorted(purchases, key=lambda p: (p.purchase_date, p.purchase_id)))
    total_quantity = sum((_decimal("quantity", p.quantity) for p in lines), Decimal("0"))
    total_spend_cents = sum(p.net_spend_cents for p in lines)
    total_spend_dollars = Decimal(total_spend_cents) / Decimal(100)

    if program.measurement_basis is RebateMeasurementBasis.UNITS:
        measure = total_quantity
    else:
        measure = total_spend_dollars

    if program.tier_mode is RebateTierMode.RETROACTIVE:
        tier = _containing_tier(program, measure)
        expected = _rebate_cents(total_spend_dollars, tier.rate_bps)
        return RebateCalculation(
            expected_cents=expected,
            total_quantity=str(total_quantity),
            total_spend_cents=total_spend_cents,
            breakdown=({
                "mode": "retroactive",
                "min_measure": tier.min_measure,
                "max_measure": tier.max_measure,
                "rate_bps": tier.rate_bps,
                "measure": str(measure),
                "rebate_cents": expected,
            },),
        )

    band_spend_dollars: dict[int, Decimal] = {
        index: Decimal("0") for index in range(len(program.ordered_tiers))
    }

    if program.measurement_basis is RebateMeasurementBasis.SPEND:
        for index, tier in enumerate(program.ordered_tiers):
            low = _decimal("min_measure", tier.min_measure)
            high = (
                None if tier.max_measure is None
                else _decimal("max_measure", tier.max_measure)
            )
            band_spend_dollars[index] = _overlap(
                Decimal("0"), total_spend_dollars, low, high
            )
    else:
        running_units = Decimal("0")
        for line in lines:
            qty = _decimal("quantity", line.quantity)
            if qty == 0:
                if line.net_spend_cents != 0:
                    raise ValueError(
                        f"purchase {line.purchase_id} has spend with zero quantity"
                    )
                continue
            line_spend_dollars = Decimal(line.net_spend_cents) / Decimal(100)
            unit_price = line_spend_dollars / qty
            before = running_units
            after = running_units + qty
            for index, tier in enumerate(program.ordered_tiers):
                low = _decimal("min_measure", tier.min_measure)
                high = (
                    None if tier.max_measure is None
                    else _decimal("max_measure", tier.max_measure)
                )
                units_in_band = _overlap(before, after, low, high)
                band_spend_dollars[index] += units_in_band * unit_price
            running_units = after

    raw_total = Decimal("0")
    breakdown: list[dict[str, Any]] = []
    for index, tier in enumerate(program.ordered_tiers):
        band_spend = band_spend_dollars[index]
        raw_rebate_dollars = band_spend * Decimal(tier.rate_bps) / Decimal(10000)
        raw_total += raw_rebate_dollars
        breakdown.append({
            "mode": "incremental",
            "min_measure": tier.min_measure,
            "max_measure": tier.max_measure,
            "rate_bps": tier.rate_bps,
            "dollar_base": str(band_spend),
            "rebate_cents": int(
                (raw_rebate_dollars * 100).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            ),
        })

    expected_cents = int(
        (raw_total * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    return RebateCalculation(
        expected_cents=expected_cents,
        total_quantity=str(total_quantity),
        total_spend_cents=total_spend_cents,
        breakdown=tuple(breakdown),
    )


def _duplicate_ids(
    items: Iterable[Any],
    *,
    id_attr: str,
    code: str,
) -> tuple[set[str], list[RebateAuditException]]:
    counts: dict[str, int] = defaultdict(int)
    for item in items:
        counts[getattr(item, id_attr)] += 1
    duplicates = {key for key, count in counts.items() if count > 1}
    exceptions = [
        RebateAuditException(
            key,
            code,
            f"{id_attr} appears {counts[key]} times; affected program is excluded",
        )
        for key in sorted(duplicates)
    ]
    return duplicates, exceptions


def audit_rebates(
    *,
    client_id: str,
    programs: Iterable[RebateProgram],
    purchases: Iterable[RebatePurchaseLine],
    settlements: Iterable[RebateSettlement],
    currency: str = "USD",
) -> RebateAuditBatch:
    client_id = _required("client_id", client_id)
    currency = _required("currency", currency).upper()
    program_list = tuple(programs)
    purchase_list = tuple(purchases)
    settlement_list = tuple(settlements)

    purchase_dupes, exceptions = _duplicate_ids(
        purchase_list, id_attr="purchase_id", code="DUPLICATE_PURCHASE_ID"
    )
    settlement_dupes, settlement_exceptions = _duplicate_ids(
        settlement_list, id_attr="settlement_id", code="DUPLICATE_SETTLEMENT_ID"
    )
    exceptions.extend(settlement_exceptions)

    programs_by_key: dict[tuple[str, str], list[RebateProgram]] = defaultdict(list)
    for program in program_list:
        programs_by_key[(program.supplier_id, program.program_id)].append(program)

    purchases_by_key: dict[tuple[str, str], list[RebatePurchaseLine]] = defaultdict(list)
    for purchase in purchase_list:
        purchases_by_key[(purchase.supplier_id, purchase.program_id)].append(purchase)

    settlements_by_key: dict[tuple[str, str], list[RebateSettlement]] = defaultdict(list)
    for settlement in settlement_list:
        settlements_by_key[(settlement.supplier_id, settlement.program_id)].append(settlement)

    observations: list[RecoveryObservation] = []

    for key in sorted(programs_by_key):
        versions = programs_by_key[key]
        if len(versions) != 1:
            exceptions.append(RebateAuditException(
                f"{key[0]}/{key[1]}",
                "AMBIGUOUS_PROGRAM_VERSION",
                f"{len(versions)} program definitions share supplier/program ID",
            ))
            continue
        program = versions[0]
        group_purchases = purchases_by_key.get(key, [])
        group_settlements = settlements_by_key.get(key, [])

        if any(p.purchase_id in purchase_dupes for p in group_purchases):
            exceptions.append(RebateAuditException(
                f"{key[0]}/{key[1]}",
                "PROGRAM_BLOCKED_BY_DUPLICATE_PURCHASE",
                "duplicate purchase identifiers prevent reliable rebate calculation",
            ))
            continue
        if any(s.settlement_id in settlement_dupes for s in group_settlements):
            exceptions.append(RebateAuditException(
                f"{key[0]}/{key[1]}",
                "PROGRAM_BLOCKED_BY_DUPLICATE_SETTLEMENT",
                "duplicate settlement identifiers prevent reliable received amount",
            ))
            continue

        in_period: list[RebatePurchaseLine] = []
        for purchase in group_purchases:
            if program.covers(purchase.purchase_date):
                in_period.append(purchase)
            else:
                exceptions.append(RebateAuditException(
                    purchase.purchase_id,
                    "OUT_OF_PERIOD_PURCHASE",
                    "purchase references program but falls outside program period",
                ))

        if not in_period:
            exceptions.append(RebateAuditException(
                f"{key[0]}/{key[1]}",
                "NO_IN_PERIOD_PURCHASES",
                "program has no in-period purchase evidence",
            ))
            continue
        if not group_settlements:
            exceptions.append(RebateAuditException(
                f"{key[0]}/{key[1]}",
                "NO_SETTLEMENT_EVIDENCE",
                "actual rebate received cannot be established",
            ))
            continue

        try:
            calc = calculate_rebate(program, in_period)
        except ValueError as exc:
            exceptions.append(RebateAuditException(
                f"{key[0]}/{key[1]}",
                "REBATE_CALCULATION_ERROR",
                str(exc),
            ))
            continue

        actual_cents = sum(s.amount_received_cents for s in group_settlements)
        if calc.expected_cents <= actual_cents:
            continue

        evidence = tuple(
            [p.evidence() for p in sorted(in_period, key=lambda p: p.purchase_id)]
            + [s.evidence() for s in sorted(group_settlements, key=lambda s: s.settlement_id)]
        )
        observations.append(RecoveryObservation(
            branch=Branch.REBATE,
            client_id=client_id,
            counterparty_id=program.supplier_id,
            reference=program.program_id,
            currency=currency,
            expected_cents=calc.expected_cents,
            actual_cents=actual_cents,
            rule=program.rule_ref(),
            evidence=evidence,
            reason="REBATE_UNDERPAYMENT",
            confidence_basis=(
                "verified rebate program + purchase population + settlement evidence"
                if program.verified and all(ref.verified for ref in evidence)
                else "rebate program/purchase/settlement evidence requires verification"
            ),
            metadata={
                "program_id": program.program_id,
                "period_start": program.period_start,
                "period_end": program.period_end,
                "tier_mode": program.tier_mode.value,
                "measurement_basis": program.measurement_basis.value,
                "total_quantity": calc.total_quantity,
                "total_spend_cents": calc.total_spend_cents,
                "calculation_breakdown": list(calc.breakdown),
                "settlement_ids": [s.settlement_id for s in group_settlements],
            },
        ))

    exceptions.sort(key=lambda x: (x.code, x.reference, x.detail))
    observations.sort(key=lambda x: (x.counterparty_id, x.reference))
    return RebateAuditBatch(tuple(observations), tuple(exceptions))
