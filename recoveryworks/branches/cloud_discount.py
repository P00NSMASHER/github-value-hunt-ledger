"""Deterministic contract-discount omission audit for CloudRecovery."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from typing import Any, Iterable, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, RuleRef, canonical_hash, freeze_json, normalize_source_hash
from .contract_billing import ContractBillingBatch, ContractBillingException, ContractRate, InvoiceCharge, UsageRecord


class DiscountAppliesTo(str, Enum):
    VARIABLE = "VARIABLE"
    ALL = "ALL"


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _date(name: str, value: str) -> date:
    try:
        return date.fromisoformat(_required(name, value))
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _decimal(name: str, value: str | Decimal) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _rate_cents(rate_micros: int, units: Decimal) -> int:
    raw = Decimal(rate_micros) * units / Decimal(10000)
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _discount_cents(amount_cents: int, bps: int) -> int:
    raw = Decimal(amount_cents) * Decimal(bps) / Decimal(10000)
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class CloudDiscountAuthority:
    counterparty_id: str
    account_id: str | None
    service_id: str
    effective_from: str
    effective_to: str | None
    discount_bps: int
    applies_to: DiscountAppliesTo
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("counterparty_id", "service_id", "effective_from", "source_locator"):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        start = _date("effective_from", self.effective_from)
        object.__setattr__(self, "effective_from", start.isoformat())
        if self.effective_to is not None:
            end = _date("effective_to", self.effective_to)
            if end < start:
                raise ValueError("effective_to cannot precede effective_from")
            object.__setattr__(self, "effective_to", end.isoformat())
        if self.account_id is not None:
            object.__setattr__(self, "account_id", _required("account_id", self.account_id))
        if type(self.discount_bps) is not int or not 0 < self.discount_bps <= 10000:
            raise ValueError("discount_bps must be an integer in 1..10000")
        if not isinstance(self.applies_to, DiscountAppliesTo):
            raise ValueError("applies_to must be DiscountAppliesTo")
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        object.__setattr__(self, "metadata", freeze_json(self.metadata, name="metadata"))

    def covers(self, charge: InvoiceCharge) -> bool:
        when = _date("service_date", charge.service_date)
        start = _date("effective_from", self.effective_from)
        end = _date("effective_to", self.effective_to) if self.effective_to else None
        return (
            charge.counterparty_id == self.counterparty_id
            and charge.service_id == self.service_id
            and (self.account_id is None or charge.account_id == self.account_id)
            and when >= start and (end is None or when <= end)
        )

    def composite_rule(self, base_rate: ContractRate) -> RuleRef:
        identity = {
            "schema":1,
            "kind":"cloud_contract_discount",
            "base_rate_rule_hash":base_rate.rule_ref(branch=Branch.CLOUD).proof_hash,
            "base_rate_source_hash":base_rate.source_hash,
            "discount_source_hash":self.source_hash,
            "counterparty_id":self.counterparty_id,
            "account_id":self.account_id,
            "service_id":self.service_id,
            "effective_from":self.effective_from,
            "effective_to":self.effective_to,
            "discount_bps":self.discount_bps,
            "applies_to":self.applies_to.value,
        }
        digest = canonical_hash(identity)
        effective_ends = [
            value for value in (base_rate.effective_to, self.effective_to) if value
        ]
        return RuleRef(
            rule_id=f"cloud-discount:{digest}",
            source_hash=digest,
            effective_from=max(base_rate.effective_from, self.effective_from),
            effective_to=min(effective_ends) if effective_ends else None,
            verified_controlling=base_rate.verified and self.verified,
            source_locator=f"composite://cloud-discount/{digest}",
            metadata={
                **identity,
                "base_rate_source_locator":base_rate.source_locator,
                "discount_source_locator":self.source_locator,
                **dict(self.metadata),
            },
        )


def _unique_charges(charges: Iterable[InvoiceCharge]):
    grouped = {}
    for charge in charges:
        grouped.setdefault(charge.charge_id, []).append(charge)
    accepted, issues = [], []
    for charge_id in sorted(grouped):
        items = grouped[charge_id]
        if len(items) != 1:
            issues.append(ContractBillingException(charge_id,"DUPLICATE_CHARGE_ID",f"charge_id appears {len(items)} times; all copies excluded from recovery math"))
        else:
            accepted.append(items[0])
    return accepted, issues


def _usage_index(usage: Iterable[UsageRecord]):
    grouped = {}
    for row in usage:
        grouped.setdefault(row.charge_id, []).append(row)
    result, issues = {}, []
    for charge_id in sorted(grouped):
        items = grouped[charge_id]
        unique = {(i.units,i.source_hash,i.source_locator) for i in items}
        if len(unique) != 1:
            issues.append(ContractBillingException(charge_id,"CONFLICTING_USAGE_RECORDS",f"{len(items)} contradictory usage records exist for charge"))
        else:
            result[charge_id] = items[0]
    return result, issues


def audit_cloud_discount_billing(*, client_id: str, charges: Iterable[InvoiceCharge], rates: Iterable[ContractRate], discounts: Iterable[CloudDiscountAuthority], usage: Iterable[UsageRecord]=(), currency: str="USD") -> ContractBillingBatch:
    client_id = _required("client_id", client_id)
    currency = _required("currency", currency).upper()
    rates, discounts = tuple(rates), tuple(discounts)
    accepted, issues = _unique_charges(charges)
    usage_by_charge, usage_issues = _usage_index(usage)
    issues.extend(usage_issues)
    observations = []

    for charge in sorted(accepted, key=lambda x:x.charge_id):
        matching_rates = [r for r in rates if r.counterparty_id==charge.counterparty_id and r.service_id==charge.service_id and r.covers(charge.service_date)]
        if not matching_rates:
            issues.append(ContractBillingException(charge.charge_id,"NO_CONTRACT_RATE","no effective base contract rate covers this charge")); continue
        if len(matching_rates)>1:
            issues.append(ContractBillingException(charge.charge_id,"OVERLAPPING_CONTRACT_RATES",f"{len(matching_rates)} base contract versions cover this charge")); continue
        matching_discounts = [d for d in discounts if d.covers(charge)]
        if not matching_discounts:
            issues.append(ContractBillingException(charge.charge_id,"NO_DISCOUNT_AUTHORITY","no reviewed discount authority covers this charge")); continue
        if len(matching_discounts)>1:
            issues.append(ContractBillingException(charge.charge_id,"OVERLAPPING_DISCOUNT_AUTHORITIES",f"{len(matching_discounts)} discount authorities cover this charge")); continue

        rate, discount = matching_rates[0], matching_discounts[0]
        usage_units, overage_units = Decimal("0"), Decimal("0")
        variable_cents = 0
        evidence = [charge.evidence(branch=Branch.CLOUD)]
        if rate.unit_rate_micros > 0:
            usage_row = usage_by_charge.get(charge.charge_id)
            if usage_row is None:
                issues.append(ContractBillingException(charge.charge_id,"MISSING_USAGE","discounted unit pricing requires independent usage")); continue
            usage_units = _decimal("usage.units", usage_row.units)
            included = _decimal("included_units", rate.included_units)
            overage_units = max(usage_units-included, Decimal("0"))
            variable_cents = _rate_cents(rate.unit_rate_micros, overage_units)
            evidence.append(usage_row.evidence(branch=Branch.CLOUD))

        base_expected = rate.fixed_cents + variable_cents
        discountable = variable_cents if discount.applies_to is DiscountAppliesTo.VARIABLE else base_expected
        discount_amount = _discount_cents(discountable, discount.discount_bps)
        expected_cents = max(base_expected-discount_amount, 0)
        if charge.actual_cents <= expected_cents:
            continue

        observations.append(RecoveryObservation(
            branch=Branch.CLOUD,
            client_id=client_id,
            counterparty_id=charge.counterparty_id,
            reference=charge.charge_id,
            currency=currency,
            expected_cents=expected_cents,
            actual_cents=charge.actual_cents,
            rule=discount.composite_rule(rate),
            evidence=tuple(evidence),
            reason="CLOUD_CONTRACT_DISCOUNT_OMISSION",
            confidence_basis="reviewed base rate + reviewed discount authority + verified invoice/usage" if rate.verified and discount.verified and all(e.verified for e in evidence) else "base rate/discount/invoice/usage requires verification",
            metadata={
                "account_id":charge.account_id,
                "service_id":charge.service_id,
                "service_date":charge.service_date,
                "base_expected_cents":base_expected,
                "discount_bps":discount.discount_bps,
                "discount_applies_to":discount.applies_to.value,
                "discount_cents":discount_amount,
                "usage_units":str(usage_units),
                "overage_units":str(overage_units),
                "detection_basis":"reviewed_contract_discount_expected_vs_invoice_actual",
            },
        ))
    issues.sort(key=lambda x:(x.code,x.reference,x.detail))
    return ContractBillingBatch(tuple(observations), tuple(issues))
