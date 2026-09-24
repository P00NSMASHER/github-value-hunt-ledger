"""Deterministic commitment-benefit entitlement audit for CloudRecovery.

This module does not value unused commitments. It only compares billed cost to
the reviewed rate that should apply to independently evidenced units allocated
to a specific charge.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef, canonical_hash, freeze_json, normalize_source_hash
from .contract_billing import ContractBillingBatch, ContractBillingException, ContractRate, InvoiceCharge, UsageRecord


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


@dataclass(frozen=True)
class CloudCommitmentAuthority:
    counterparty_id: str
    account_id: str | None
    service_id: str
    effective_from: str
    effective_to: str | None
    commitment_type: str
    committed_unit_rate_micros: int
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("counterparty_id", "service_id", "effective_from", "commitment_type", "source_locator"):
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
        if type(self.committed_unit_rate_micros) is not int or self.committed_unit_rate_micros < 0:
            raise ValueError("committed_unit_rate_micros must be a non-negative integer")
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
            "kind":"cloud_commitment_benefit",
            "base_rate_rule_hash":base_rate.rule_ref(branch=Branch.CLOUD).proof_hash,
            "base_rate_source_hash":base_rate.source_hash,
            "commitment_source_hash":self.source_hash,
            "counterparty_id":self.counterparty_id,
            "account_id":self.account_id,
            "service_id":self.service_id,
            "effective_from":self.effective_from,
            "effective_to":self.effective_to,
            "commitment_type":self.commitment_type,
            "committed_unit_rate_micros":self.committed_unit_rate_micros,
        }
        digest=canonical_hash(identity)
        effective_ends = [
            value for value in (base_rate.effective_to, self.effective_to) if value
        ]
        return RuleRef(
            rule_id=f"cloud-commitment:{digest}",
            source_hash=digest,
            effective_from=max(base_rate.effective_from, self.effective_from),
            effective_to=min(effective_ends) if effective_ends else None,
            verified_controlling=base_rate.verified and self.verified,
            source_locator=f"composite://cloud-commitment/{digest}",
            metadata={
                **identity,
                "base_rate_source_locator":base_rate.source_locator,
                "commitment_source_locator":self.source_locator,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class CommitmentAllocation:
    charge_id: str
    entitled_units: str
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "charge_id", _required("charge_id", self.charge_id))
        object.__setattr__(self, "entitled_units", str(_decimal("entitled_units", self.entitled_units)))
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        object.__setattr__(self, "source_locator", _required("source_locator", self.source_locator))
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        object.__setattr__(self, "metadata", freeze_json(self.metadata, name="metadata"))

    def evidence(self) -> EvidenceRef:
        identity={
            "charge_id":self.charge_id,
            "entitled_units":self.entitled_units,
            "source_hash":self.source_hash,
            "source_locator":self.source_locator,
        }
        return EvidenceRef(
            evidence_id="cloud-commitment-allocation:"+canonical_hash(identity),
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="cloud_commitment_allocation",
            verified=self.verified,
            metadata={"charge_id":self.charge_id,"entitled_units":self.entitled_units,**dict(self.metadata)},
        )


def _one_by_charge(rows: Iterable[Any], code: str):
    grouped={}
    for row in rows:
        grouped.setdefault(row.charge_id,[]).append(row)
    result,issues={},[]
    for charge_id in sorted(grouped):
        items=grouped[charge_id]
        if len(items)!=1:
            issues.append(ContractBillingException(charge_id,code,f"{len(items)} records exist for charge"))
        else:
            result[charge_id]=items[0]
    return result,issues


def audit_cloud_commitment_billing(*, client_id: str, charges: Iterable[InvoiceCharge], rates: Iterable[ContractRate], commitments: Iterable[CloudCommitmentAuthority], allocations: Iterable[CommitmentAllocation], usage: Iterable[UsageRecord], currency: str="USD") -> ContractBillingBatch:
    client_id=_required("client_id",client_id); currency=_required("currency",currency).upper()
    rates,commitments=tuple(rates),tuple(commitments)
    charge_by_id,issues=_one_by_charge(charges,"DUPLICATE_CHARGE_ID")
    usage_by_id,usage_issues=_one_by_charge(usage,"CONFLICTING_USAGE_RECORDS")
    allocation_by_id,allocation_issues=_one_by_charge(allocations,"CONFLICTING_COMMITMENT_ALLOCATIONS")
    issues.extend(usage_issues); issues.extend(allocation_issues)
    observations=[]

    for charge_id in sorted(charge_by_id):
        charge=charge_by_id[charge_id]
        matching_rates=[r for r in rates if r.counterparty_id==charge.counterparty_id and r.service_id==charge.service_id and r.covers(charge.service_date)]
        if not matching_rates:
            issues.append(ContractBillingException(charge_id,"NO_CONTRACT_RATE","no effective on-demand/base rate covers this charge")); continue
        if len(matching_rates)>1:
            issues.append(ContractBillingException(charge_id,"OVERLAPPING_CONTRACT_RATES",f"{len(matching_rates)} base rates cover this charge")); continue
        matching_commitments=[c for c in commitments if c.covers(charge)]
        if not matching_commitments:
            issues.append(ContractBillingException(charge_id,"NO_COMMITMENT_AUTHORITY","no reviewed commitment authority covers this charge")); continue
        if len(matching_commitments)>1:
            issues.append(ContractBillingException(charge_id,"OVERLAPPING_COMMITMENT_AUTHORITIES",f"{len(matching_commitments)} commitment authorities cover this charge")); continue
        usage_row=usage_by_id.get(charge_id)
        if usage_row is None:
            issues.append(ContractBillingException(charge_id,"MISSING_USAGE","commitment benefit requires independent usage")); continue
        allocation=allocation_by_id.get(charge_id)
        if allocation is None:
            issues.append(ContractBillingException(charge_id,"MISSING_COMMITMENT_ALLOCATION","commitment benefit requires independently evidenced allocated units")); continue

        rate=matching_rates[0]; commitment=matching_commitments[0]
        if rate.unit_rate_micros<=0:
            issues.append(ContractBillingException(charge_id,"NON_UNIT_BASE_RATE","commitment benefit requires a positive base unit rate")); continue
        if commitment.committed_unit_rate_micros>rate.unit_rate_micros:
            issues.append(ContractBillingException(charge_id,"COMMITMENT_RATE_EXCEEDS_BASE_RATE","reviewed committed rate exceeds reviewed base rate")); continue

        usage_units=_decimal("usage.units",usage_row.units)
        included=_decimal("included_units",rate.included_units)
        billable_units=max(usage_units-included,Decimal("0"))
        entitled_units=_decimal("allocation.entitled_units",allocation.entitled_units)
        covered_units=min(billable_units,entitled_units)
        uncovered_units=billable_units-covered_units
        expected_cents=rate.fixed_cents+_rate_cents(commitment.committed_unit_rate_micros,covered_units)+_rate_cents(rate.unit_rate_micros,uncovered_units)
        if charge.actual_cents<=expected_cents:
            continue

        evidence=(charge.evidence(branch=Branch.CLOUD),usage_row.evidence(branch=Branch.CLOUD),allocation.evidence())
        observations.append(RecoveryObservation(
            branch=Branch.CLOUD,
            client_id=client_id,
            counterparty_id=charge.counterparty_id,
            reference=charge.charge_id,
            currency=currency,
            expected_cents=expected_cents,
            actual_cents=charge.actual_cents,
            rule=commitment.composite_rule(rate),
            evidence=evidence,
            reason="CLOUD_COMMITMENT_BENEFIT_OMISSION",
            confidence_basis="reviewed base/commitment rates + verified invoice/usage/allocation" if rate.verified and commitment.verified and all(e.verified for e in evidence) else "base/commitment/invoice/usage/allocation requires verification",
            metadata={
                "account_id":charge.account_id,
                "service_id":charge.service_id,
                "service_date":charge.service_date,
                "commitment_type":commitment.commitment_type,
                "usage_units":str(usage_units),
                "included_units":str(included),
                "billable_units":str(billable_units),
                "entitled_units":str(entitled_units),
                "covered_units":str(covered_units),
                "uncovered_units":str(uncovered_units),
                "unused_entitled_units":str(max(entitled_units-billable_units,Decimal("0"))),
                "base_unit_rate_micros":rate.unit_rate_micros,
                "committed_unit_rate_micros":commitment.committed_unit_rate_micros,
                "detection_basis":"reviewed_commitment_benefit_expected_vs_invoice_actual",
                "unused_commitment_is_not_recovery":True,
            },
        ))
    issues.sort(key=lambda x:(x.code,x.reference,x.detail))
    return ContractBillingBatch(tuple(observations),tuple(issues))
