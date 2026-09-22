"""Shared deterministic contract-billing engine for recurring-service recovery.

Used by SaaSRecovery and TelecomRecovery. It compares an invoice charge to the
expected amount derived from an effective-dated contract plus independently
supplied usage/seat quantities when the contract is usage based.
"""
from __future__ import annotations

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


def _nonnegative_cents(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be non-negative integer cents")
    return value


def _nonnegative_decimal(name: str, value: str | int | float | Decimal) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _rate_charge_cents(rate_micros_per_unit: int, units: Decimal) -> int:
    if type(rate_micros_per_unit) is not int or rate_micros_per_unit < 0:
        raise ValueError("rate_micros_per_unit must be non-negative integer")
    raw_cents = Decimal(rate_micros_per_unit) * units / Decimal(10000)
    return int(raw_cents.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class ContractRate:
    counterparty_id: str
    service_id: str
    effective_from: str
    effective_to: str | None
    fixed_cents: int
    included_units: str
    unit_rate_micros: int
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "counterparty_id", "service_id", "effective_from",
            "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        start = _iso_date("effective_from", self.effective_from)
        if self.effective_to is not None:
            end = _iso_date("effective_to", self.effective_to)
            if end < start:
                raise ValueError("effective_to cannot precede effective_from")
        _nonnegative_cents("fixed_cents", self.fixed_cents)
        _nonnegative_decimal("included_units", self.included_units)
        if type(self.unit_rate_micros) is not int or self.unit_rate_micros < 0:
            raise ValueError("unit_rate_micros must be non-negative integer")
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        if self.fixed_cents == 0 and self.unit_rate_micros == 0:
            raise ValueError("contract rate must contain fixed or unit pricing")

    def covers(self, service_date: str) -> bool:
        when = _iso_date("service_date", service_date)
        start = _iso_date("effective_from", self.effective_from)
        end = _iso_date("effective_to", self.effective_to) if self.effective_to else None
        return when >= start and (end is None or when <= end)

    def rule_ref(self, *, branch: Branch) -> RuleRef:
        identity = {
            "schema": 1,
            "branch": branch.value,
            "counterparty_id": self.counterparty_id,
            "service_id": self.service_id,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "fixed_cents": self.fixed_cents,
            "included_units": self.included_units,
            "unit_rate_micros": self.unit_rate_micros,
            "source_hash": self.source_hash,
        }
        return RuleRef(
            rule_id=f"{branch.value}-contract-rate:" + canonical_hash(identity),
            source_hash=self.source_hash,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            verified_controlling=self.verified,
            source_locator=self.source_locator,
            metadata={
                "kind": "recurring_service_contract",
                "service_id": self.service_id,
                "counterparty_id": self.counterparty_id,
                "fixed_cents": self.fixed_cents,
                "included_units": self.included_units,
                "unit_rate_micros": self.unit_rate_micros,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class InvoiceCharge:
    charge_id: str
    counterparty_id: str
    account_id: str
    service_id: str
    service_date: str
    actual_cents: int
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "charge_id", "counterparty_id", "account_id", "service_id",
            "service_date", "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _iso_date("service_date", self.service_date)
        _nonnegative_cents("actual_cents", self.actual_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    def evidence(self, *, branch: Branch) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"{branch.value}-invoice:{self.charge_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind=f"{branch.value}_invoice_charge",
            verified=self.verified,
            metadata={
                "account_id": self.account_id,
                "service_id": self.service_id,
                "service_date": self.service_date,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class UsageRecord:
    charge_id: str
    units: str
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _required("charge_id", self.charge_id)
        _nonnegative_decimal("units", self.units)
        _required("source_hash", self.source_hash)
        _required("source_locator", self.source_locator)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    def evidence(self, *, branch: Branch) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"{branch.value}-usage:" + canonical_hash({
                "charge_id": self.charge_id,
                "units": self.units,
                "source_hash": self.source_hash,
                "locator": self.source_locator,
            }),
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind=f"{branch.value}_usage",
            verified=self.verified,
            metadata={
                "charge_id": self.charge_id,
                "units": self.units,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class ContractBillingException:
    reference: str
    code: str
    detail: str


@dataclass(frozen=True)
class ContractBillingBatch:
    observations: tuple[RecoveryObservation, ...]
    exceptions: tuple[ContractBillingException, ...]


def _usage_index(
    usage: Iterable[UsageRecord],
) -> tuple[dict[str, UsageRecord], tuple[ContractBillingException, ...]]:
    grouped: dict[str, list[UsageRecord]] = {}
    for item in usage:
        grouped.setdefault(item.charge_id, []).append(item)
    result: dict[str, UsageRecord] = {}
    exceptions: list[ContractBillingException] = []
    for charge_id in sorted(grouped):
        items = grouped[charge_id]
        if len(items) == 1:
            result[charge_id] = items[0]
            continue
        unique = {(item.units, item.source_hash, item.source_locator) for item in items}
        if len(unique) == 1:
            result[charge_id] = items[0]
            continue
        exceptions.append(ContractBillingException(
            charge_id,
            "CONFLICTING_USAGE_RECORDS",
            f"{len(items)} contradictory usage records exist for charge",
        ))
    return result, tuple(exceptions)


def audit_contract_billing(
    *,
    branch: Branch,
    client_id: str,
    charges: Iterable[InvoiceCharge],
    rates: Iterable[ContractRate],
    usage: Iterable[UsageRecord] = (),
    currency: str = "USD",
) -> ContractBillingBatch:
    if branch not in {Branch.SAAS, Branch.TELECOM}:
        raise ValueError("contract billing engine only supports SaaS/telecom branches")
    client_id = _required("client_id", client_id)
    currency = _required("currency", currency).upper()

    rate_index: dict[tuple[str, str], list[ContractRate]] = {}
    for rate in rates:
        rate_index.setdefault((rate.counterparty_id, rate.service_id), []).append(rate)

    usage_by_charge, usage_exceptions = _usage_index(usage)
    observations: list[RecoveryObservation] = []
    exceptions = list(usage_exceptions)

    charge_groups: dict[str, list[InvoiceCharge]] = {}
    for charge in charges:
        charge_groups.setdefault(charge.charge_id, []).append(charge)

    accepted_charges: list[InvoiceCharge] = []
    for charge_id in sorted(charge_groups):
        group = charge_groups[charge_id]
        if len(group) != 1:
            exceptions.append(ContractBillingException(
                charge_id,
                "DUPLICATE_CHARGE_ID",
                f"charge_id appears {len(group)} times; all copies excluded from recovery math",
            ))
            continue
        accepted_charges.append(group[0])

    for charge in sorted(accepted_charges, key=lambda item: item.charge_id):
        candidates = [
            rate
            for rate in rate_index.get((charge.counterparty_id, charge.service_id), [])
            if rate.covers(charge.service_date)
        ]
        if not candidates:
            exceptions.append(ContractBillingException(
                charge.charge_id,
                "NO_CONTRACT_RATE",
                "no effective contract rate covers this charge",
            ))
            continue
        if len(candidates) > 1:
            exceptions.append(ContractBillingException(
                charge.charge_id,
                "OVERLAPPING_CONTRACT_RATES",
                f"{len(candidates)} contract versions cover this charge",
            ))
            continue

        rate = candidates[0]
        expected_cents = rate.fixed_cents
        evidence = [charge.evidence(branch=branch)]
        usage_record = usage_by_charge.get(charge.charge_id)
        usage_units = Decimal("0")
        overage_units = Decimal("0")

        if rate.unit_rate_micros > 0:
            if usage_record is None:
                exceptions.append(ContractBillingException(
                    charge.charge_id,
                    "MISSING_USAGE",
                    "contract requires usage/seat quantity but none was supplied",
                ))
                continue
            usage_units = _nonnegative_decimal("usage.units", usage_record.units)
            included = _nonnegative_decimal("included_units", rate.included_units)
            overage_units = max(usage_units - included, Decimal("0"))
            expected_cents += _rate_charge_cents(rate.unit_rate_micros, overage_units)
            evidence.append(usage_record.evidence(branch=branch))

        if charge.actual_cents <= expected_cents:
            continue

        verified = rate.verified and all(ref.verified for ref in evidence)
        observations.append(RecoveryObservation(
            branch=branch,
            client_id=client_id,
            counterparty_id=charge.counterparty_id,
            reference=charge.charge_id,
            currency=currency,
            expected_cents=expected_cents,
            actual_cents=charge.actual_cents,
            rule=rate.rule_ref(branch=branch),
            evidence=tuple(evidence),
            reason=f"{branch.value.upper()}_CONTRACT_BILLING_OVERCHARGE",
            confidence_basis=(
                "verified contract + invoice + independent quantity evidence"
                if verified
                else "contract/invoice/quantity evidence requires verification"
            ),
            metadata={
                "account_id": charge.account_id,
                "service_id": charge.service_id,
                "service_date": charge.service_date,
                "fixed_cents": rate.fixed_cents,
                "included_units": rate.included_units,
                "usage_units": str(usage_units),
                "overage_units": str(overage_units),
                "unit_rate_micros": rate.unit_rate_micros,
                "detection_basis": "effective_contract_expected_vs_invoice_actual",
            },
        ))

    exceptions.sort(key=lambda x: (x.code, x.reference, x.detail))
    return ContractBillingBatch(tuple(observations), tuple(exceptions))
