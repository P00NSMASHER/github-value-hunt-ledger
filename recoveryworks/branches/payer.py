"""PayerRecovery de-identified service-line underpayment adapter.

The shared RecoveryWorks layer never needs patient names, member IDs, DOBs, or
other direct identifiers. Upstream systems should map claims to surrogate IDs
before this adapter is invoked.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef, canonical_hash


_FORBIDDEN_METADATA_KEYS = {
    "patient_name",
    "member_id",
    "patient_id",
    "date_of_birth",
    "dob",
    "ssn",
    "subscriber_id",
}


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


def _nonnegative_cents(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be non-negative integer cents")
    return value


def _positive_int(name: str, value: int) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be positive integer")
    return value


def _guard_metadata(metadata: Mapping[str, Any]) -> None:
    bad = {str(key).strip().lower() for key in metadata} & _FORBIDDEN_METADATA_KEYS
    if bad:
        raise ValueError(
            "payer common-ledger metadata contains prohibited direct identifiers: "
            + ", ".join(sorted(bad))
        )


def normalize_procedure_code(value: str) -> str:
    return _required("procedure_code", value).upper().replace(" ", "")


def normalize_modifier(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    return str(value).strip().upper()


def normalize_pos(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    return str(value).strip().upper()


@dataclass(frozen=True)
class PayerServiceLine:
    line_id: str
    claim_surrogate_id: str
    payer_id: str
    service_date: str
    billed_procedure: str
    paid_cents: int
    units: int
    source_hash: str
    source_locator: str
    verified: bool
    paid_procedure: str | None = None
    modifier: str | None = None
    place_of_service: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "line_id", "claim_surrogate_id", "payer_id", "service_date",
            "billed_procedure", "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _iso_date("service_date", self.service_date)
        _nonnegative_cents("paid_cents", self.paid_cents)
        _positive_int("units", self.units)
        normalize_procedure_code(self.billed_procedure)
        if self.paid_procedure:
            normalize_procedure_code(self.paid_procedure)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        _guard_metadata(self.metadata)

    @property
    def billed_code(self) -> str:
        return normalize_procedure_code(self.billed_procedure)

    @property
    def paid_code(self) -> str | None:
        return (
            normalize_procedure_code(self.paid_procedure)
            if self.paid_procedure else None
        )

    @property
    def normalized_modifier(self) -> str | None:
        return normalize_modifier(self.modifier)

    @property
    def normalized_pos(self) -> str | None:
        return normalize_pos(self.place_of_service)

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"payer-line:{self.line_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="payer_remittance_line",
            verified=self.verified,
            metadata={
                "claim_surrogate_id": self.claim_surrogate_id,
                "payer_id": self.payer_id,
                "service_date": self.service_date,
                "billed_procedure": self.billed_code,
                "paid_procedure": self.paid_code,
                "units": self.units,
                "modifier": self.normalized_modifier,
                "place_of_service": self.normalized_pos,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class PayerRate:
    payer_id: str
    procedure_code: str
    allowed_cents_per_unit: int
    effective_from: str
    effective_to: str | None
    source_hash: str
    source_locator: str
    verified: bool
    modifier: str | None = None
    place_of_service: str | None = None
    jurisdiction: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "payer_id", "procedure_code", "effective_from",
            "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _positive_int("allowed_cents_per_unit", self.allowed_cents_per_unit)
        start = _iso_date("effective_from", self.effective_from)
        if self.effective_to is not None:
            end = _iso_date("effective_to", self.effective_to)
            if end < start:
                raise ValueError("effective_to cannot precede effective_from")
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        normalize_procedure_code(self.procedure_code)
        _guard_metadata(self.metadata)

    @property
    def code(self) -> str:
        return normalize_procedure_code(self.procedure_code)

    @property
    def normalized_modifier(self) -> str | None:
        return normalize_modifier(self.modifier)

    @property
    def normalized_pos(self) -> str | None:
        return normalize_pos(self.place_of_service)

    def covers(self, service_date: str) -> bool:
        when = _iso_date("service_date", service_date)
        start = _iso_date("effective_from", self.effective_from)
        end = _iso_date("effective_to", self.effective_to) if self.effective_to else None
        return when >= start and (end is None or when <= end)

    def matches_line(self, line: PayerServiceLine) -> bool:
        if self.payer_id != line.payer_id or self.code != line.billed_code:
            return False
        if not self.covers(line.service_date):
            return False
        if self.normalized_modifier is not None and self.normalized_modifier != line.normalized_modifier:
            return False
        if self.normalized_pos is not None and self.normalized_pos != line.normalized_pos:
            return False
        return True

    @property
    def specificity(self) -> int:
        return int(self.normalized_modifier is not None) + int(self.normalized_pos is not None)

    def rule_ref(self) -> RuleRef:
        identity = {
            "schema": 1,
            "payer_id": self.payer_id,
            "procedure_code": self.code,
            "allowed_cents_per_unit": self.allowed_cents_per_unit,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "modifier": self.normalized_modifier,
            "place_of_service": self.normalized_pos,
            "source_hash": self.source_hash,
        }
        return RuleRef(
            rule_id="payer-rate:" + canonical_hash(identity),
            source_hash=self.source_hash,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            verified_controlling=self.verified,
            source_locator=self.source_locator,
            jurisdiction=self.jurisdiction,
            metadata={
                "kind": "payer_rate",
                "payer_id": self.payer_id,
                "procedure_code": self.code,
                "modifier": self.normalized_modifier,
                "place_of_service": self.normalized_pos,
                "allowed_cents_per_unit": self.allowed_cents_per_unit,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class PayerAuditException:
    line_id: str
    claim_surrogate_id: str
    code: str
    detail: str


@dataclass(frozen=True)
class PayerAuditBatch:
    observations: tuple[RecoveryObservation, ...]
    exceptions: tuple[PayerAuditException, ...]


def audit_payer_lines(
    *,
    client_id: str,
    lines: Iterable[PayerServiceLine],
    rates: Iterable[PayerRate],
    currency: str = "USD",
) -> PayerAuditBatch:
    client_id = _required("client_id", client_id)
    currency = _required("currency", currency).upper()
    rate_list = tuple(rates)

    observations: list[RecoveryObservation] = []
    exceptions: list[PayerAuditException] = []

    for line in sorted(lines, key=lambda item: item.line_id):
        matches = [rate for rate in rate_list if rate.matches_line(line)]
        if not matches:
            exceptions.append(PayerAuditException(
                line.line_id,
                line.claim_surrogate_id,
                "NO_RATE",
                "no effective rate matches payer/procedure/modifier/place of service",
            ))
            continue

        max_specificity = max(rate.specificity for rate in matches)
        best = [rate for rate in matches if rate.specificity == max_specificity]
        if len(best) != 1:
            exceptions.append(PayerAuditException(
                line.line_id,
                line.claim_surrogate_id,
                "AMBIGUOUS_RATE",
                f"{len(best)} equally specific effective rates match the service line",
            ))
            continue

        rate = best[0]
        expected_cents = rate.allowed_cents_per_unit * line.units
        if line.paid_cents >= expected_cents:
            continue

        downcoded = bool(line.paid_code and line.paid_code != line.billed_code)
        observations.append(RecoveryObservation(
            branch=Branch.PAYER,
            client_id=client_id,
            counterparty_id=line.payer_id,
            reference=f"{line.claim_surrogate_id}:{line.line_id}",
            currency=currency,
            expected_cents=expected_cents,
            actual_cents=line.paid_cents,
            rule=rate.rule_ref(),
            evidence=(line.evidence(),),
            reason="PAYER_DOWNCODE_UNDERPAYMENT" if downcoded else "PAYER_UNDERPAYMENT",
            confidence_basis=(
                "verified effective rate + verified de-identified remittance line"
                if rate.verified and line.verified
                else "rate/remittance source requires verification"
            ),
            metadata={
                "claim_surrogate_id": line.claim_surrogate_id,
                "line_id": line.line_id,
                "billed_procedure": line.billed_code,
                "paid_procedure": line.paid_code,
                "units": line.units,
                "modifier": line.normalized_modifier,
                "place_of_service": line.normalized_pos,
                "downcoded": downcoded,
            },
        ))

    return PayerAuditBatch(tuple(observations), tuple(exceptions))
