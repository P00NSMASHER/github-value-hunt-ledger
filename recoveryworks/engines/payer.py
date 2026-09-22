"""Deterministic payer fee-schedule underpayment detector.

This is intentionally narrow: it prices exact procedure-code service lines against
an exact effective-dated fee schedule. Modifier, bundling, multiple-procedure,
capitation, and contract-specific logic must be added as explicit rule modules;
they are never inferred by an LLM.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from recoveryworks.branches.payer import from_payer_variance
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


@dataclass(frozen=True)
class FeeScheduleRate:
    payer_id: str
    rate_id: str
    procedure_code: str
    effective_from: str
    effective_to: str | None
    allowed_cents_per_unit: int
    source_hash: str
    locator: str
    verified: bool = False

    def __post_init__(self) -> None:
        for name in (
            "payer_id", "rate_id", "procedure_code", "effective_from",
            "source_hash", "locator",
        ):
            _text(name, getattr(self, name))
        start = _iso(self.effective_from, "effective_from")
        if self.effective_to is not None:
            end = _iso(self.effective_to, "effective_to")
            if end < start:
                raise ValueError("effective_to cannot precede effective_from")
        if type(self.allowed_cents_per_unit) is not int or self.allowed_cents_per_unit < 0:
            raise ValueError("allowed_cents_per_unit must be non-negative integer cents")
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")


@dataclass(frozen=True)
class PayerServiceLine:
    claim_id: str
    service_line_id: str
    service_date: str
    procedure_code: str
    units: int
    paid_cents: int
    currency: str
    source_hash: str
    locator: str
    verified: bool = False

    def __post_init__(self) -> None:
        for name in (
            "claim_id", "service_line_id", "service_date", "procedure_code",
            "currency", "source_hash", "locator",
        ):
            _text(name, getattr(self, name))
        _iso(self.service_date, "service_date")
        if type(self.units) is not int or self.units <= 0:
            raise ValueError("units must be a positive integer")
        if type(self.paid_cents) is not int or self.paid_cents < 0:
            raise ValueError("paid_cents must be non-negative integer cents")
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")


def _applies(rate: FeeScheduleRate, service_date: str) -> bool:
    day = _iso(service_date, "service_date")
    start = _iso(rate.effective_from, "effective_from")
    end = _iso(rate.effective_to, "effective_to") if rate.effective_to else None
    return day >= start and (end is None or day <= end)


def detect_payer_underpayments(
    *,
    client_id: str,
    payer_id: str,
    rates: Iterable[FeeScheduleRate],
    service_lines: Iterable[PayerServiceLine],
) -> tuple[RecoveryObservation, ...]:
    client_id = _text("client_id", client_id)
    payer_id = _text("payer_id", payer_id)

    rate_index: dict[str, list[FeeScheduleRate]] = {}
    for rate in rates:
        if rate.payer_id != payer_id:
            continue
        rate_index.setdefault(rate.procedure_code, []).append(rate)

    observations: list[RecoveryObservation] = []
    for line in sorted(service_lines, key=lambda x: (x.service_date, x.claim_id, x.service_line_id)):
        candidates = [
            rate for rate in rate_index.get(line.procedure_code, ())
            if _applies(rate, line.service_date)
        ]
        if not candidates:
            continue
        if len(candidates) > 1:
            distinct = {
                (rate.allowed_cents_per_unit, rate.source_hash, rate.rate_id)
                for rate in candidates
            }
            if len(distinct) > 1:
                raise ValueError(
                    f"conflicting applicable rates for {line.procedure_code} on {line.service_date}"
                )
            candidates = [sorted(candidates, key=lambda x: x.rate_id)[0]]

        rate = candidates[0]
        expected_cents = rate.allowed_cents_per_unit * line.units
        if expected_cents <= line.paid_cents:
            continue

        rule = RuleRef(
            rule_id=f"payer-rate:{rate.payer_id}:{rate.rate_id}",
            source_hash=rate.source_hash,
            effective_from=rate.effective_from,
            effective_to=rate.effective_to,
            verified_controlling=rate.verified,
            source_locator=rate.locator,
            metadata={
                "procedure_code": rate.procedure_code,
                "allowed_cents_per_unit": rate.allowed_cents_per_unit,
            },
        )
        evidence = (
            EvidenceRef(
                evidence_id=f"payer-rate:{rate.rate_id}",
                source_hash=rate.source_hash,
                locator=rate.locator,
                kind="payer_fee_schedule",
                verified=rate.verified,
            ),
            EvidenceRef(
                evidence_id=f"payer-line:{line.claim_id}:{line.service_line_id}",
                source_hash=line.source_hash,
                locator=line.locator,
                kind="payer_service_line",
                verified=line.verified,
                metadata={
                    "procedure_code": line.procedure_code,
                    "units": line.units,
                    "paid_cents": line.paid_cents,
                },
            ),
        )
        observations.append(from_payer_variance(
            client_id=client_id,
            payer_id=payer_id,
            claim_id=f"{line.claim_id}:{line.service_line_id}",
            service_date=line.service_date,
            expected_cents=expected_cents,
            paid_cents=line.paid_cents,
            rule=rule,
            evidence=evidence,
            currency=line.currency,
            reason="PAYER_FEE_SCHEDULE_UNDERPAYMENT",
            confidence_basis="exact procedure/date fee schedule lookup × integer units",
            metadata={
                "claim_id": line.claim_id,
                "service_line_id": line.service_line_id,
                "procedure_code": line.procedure_code,
                "units": line.units,
                "rate_id": rate.rate_id,
            },
        ))

    return tuple(observations)
