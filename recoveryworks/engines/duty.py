"""Deterministic customs-duty screening engine.

Scope is intentionally explicit: exact HTS code, effective-dated ad-valorem rate,
and optional specific duty. AD/CVD, quota, origin programs, valuation disputes,
and classification judgment remain outside this calculator unless implemented as
separate verified rule modules.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from recoveryworks.branches.duty import from_duty_variance
from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import EvidenceRef, RuleRef


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _iso(value: str, name: str) -> date:
    try:
        return date.fromisoformat(_text(name, value))
    except ValueError as exc:
        raise ValueError(f"{name} must be ISO YYYY-MM-DD") from exc


def _nonnegative_decimal(name: str, value: Decimal) -> Decimal:
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


@dataclass(frozen=True)
class DutyRate:
    rate_id: str
    hts_code: str
    effective_from: str
    effective_to: str | None
    ad_valorem_bps: int
    specific_cents_per_unit: Decimal
    source_hash: str
    locator: str
    verified: bool = False
    jurisdiction: str = "US"

    def __post_init__(self) -> None:
        for name in ("rate_id", "hts_code", "effective_from", "source_hash", "locator", "jurisdiction"):
            _text(name, getattr(self, name))
        start = _iso(self.effective_from, "effective_from")
        if self.effective_to is not None:
            end = _iso(self.effective_to, "effective_to")
            if end < start:
                raise ValueError("effective_to cannot precede effective_from")
        if type(self.ad_valorem_bps) is not int or self.ad_valorem_bps < 0:
            raise ValueError("ad_valorem_bps must be a non-negative integer")
        _nonnegative_decimal("specific_cents_per_unit", self.specific_cents_per_unit)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")


@dataclass(frozen=True)
class ImportEntryLine:
    entry_id: str
    line_id: str
    entry_date: str
    hts_code: str
    customs_value_cents: int
    quantity: Decimal
    paid_duty_cents: int
    currency: str
    source_hash: str
    locator: str
    verified: bool = False

    def __post_init__(self) -> None:
        for name in (
            "entry_id", "line_id", "entry_date", "hts_code", "currency",
            "source_hash", "locator",
        ):
            _text(name, getattr(self, name))
        _iso(self.entry_date, "entry_date")
        if type(self.customs_value_cents) is not int or self.customs_value_cents < 0:
            raise ValueError("customs_value_cents must be non-negative integer cents")
        if type(self.paid_duty_cents) is not int or self.paid_duty_cents < 0:
            raise ValueError("paid_duty_cents must be non-negative integer cents")
        _nonnegative_decimal("quantity", self.quantity)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")


def _applies(rate: DutyRate, entry_date: str) -> bool:
    day = _iso(entry_date, "entry_date")
    start = _iso(rate.effective_from, "effective_from")
    end = _iso(rate.effective_to, "effective_to") if rate.effective_to else None
    return day >= start and (end is None or day <= end)


def expected_duty_cents(rate: DutyRate, line: ImportEntryLine) -> int:
    ad_valorem = (Decimal(line.customs_value_cents) * Decimal(rate.ad_valorem_bps)) / Decimal(10000)
    specific = line.quantity * rate.specific_cents_per_unit
    return int((ad_valorem + specific).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def detect_duty_overpayments(
    *,
    client_id: str,
    customs_counterparty_id: str,
    rates: Iterable[DutyRate],
    lines: Iterable[ImportEntryLine],
) -> tuple[RecoveryObservation, ...]:
    client_id = _text("client_id", client_id)
    customs_counterparty_id = _text("customs_counterparty_id", customs_counterparty_id)

    rate_index: dict[str, list[DutyRate]] = {}
    for rate in rates:
        rate_index.setdefault(rate.hts_code, []).append(rate)

    observations: list[RecoveryObservation] = []
    for line in sorted(lines, key=lambda x: (x.entry_date, x.entry_id, x.line_id)):
        candidates = [rate for rate in rate_index.get(line.hts_code, ()) if _applies(rate, line.entry_date)]
        if not candidates:
            continue
        if len(candidates) > 1:
            signatures = {
                (rate.ad_valorem_bps, str(rate.specific_cents_per_unit), rate.source_hash, rate.rate_id)
                for rate in candidates
            }
            if len(signatures) > 1:
                raise ValueError(f"conflicting applicable duty rates for {line.hts_code}")
            candidates = [sorted(candidates, key=lambda x: x.rate_id)[0]]

        rate = candidates[0]
        expected = expected_duty_cents(rate, line)
        if line.paid_duty_cents <= expected:
            continue

        rule = RuleRef(
            rule_id=f"duty-rate:{rate.rate_id}",
            source_hash=rate.source_hash,
            effective_from=rate.effective_from,
            effective_to=rate.effective_to,
            verified_controlling=rate.verified,
            source_locator=rate.locator,
            jurisdiction=rate.jurisdiction,
            metadata={
                "hts_code": rate.hts_code,
                "ad_valorem_bps": rate.ad_valorem_bps,
                "specific_cents_per_unit": str(rate.specific_cents_per_unit),
                "scope_excludes": ["AD/CVD", "quota", "origin-program judgment", "classification judgment"],
            },
        )
        evidence = (
            EvidenceRef(
                evidence_id=f"duty-rate:{rate.rate_id}",
                source_hash=rate.source_hash,
                locator=rate.locator,
                kind="hts_tariff_rule",
                verified=rate.verified,
            ),
            EvidenceRef(
                evidence_id=f"entry-line:{line.entry_id}:{line.line_id}",
                source_hash=line.source_hash,
                locator=line.locator,
                kind="customs_entry_line",
                verified=line.verified,
                metadata={
                    "hts_code": line.hts_code,
                    "customs_value_cents": line.customs_value_cents,
                    "quantity": str(line.quantity),
                    "paid_duty_cents": line.paid_duty_cents,
                },
            ),
        )
        observations.append(from_duty_variance(
            client_id=client_id,
            customs_counterparty_id=customs_counterparty_id,
            entry_id=f"{line.entry_id}:{line.line_id}",
            entry_date=line.entry_date,
            expected_cents=expected,
            paid_cents=line.paid_duty_cents,
            rule=rule,
            evidence=evidence,
            currency=line.currency,
            reason="DUTY_EXACT_RATE_OVERPAYMENT",
            confidence_basis="exact HTS/date arithmetic; classification and special regimes excluded",
            metadata={
                "entry_id": line.entry_id,
                "line_id": line.line_id,
                "hts_code": line.hts_code,
                "rate_id": rate.rate_id,
            },
        ))

    return tuple(observations)
