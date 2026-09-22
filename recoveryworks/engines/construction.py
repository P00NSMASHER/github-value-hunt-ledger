"""ConstructionRecovery proof bridge for change and delay entitlements.

RecoveryWorks does not independently decide legal entitlement or schedule
causation here. It accepts reviewed entitlement evidence and, when delay
causation is required, a verified forensic schedule-impact artifact.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from recoveryworks.branches.construction import from_construction_entitlement
from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import EvidenceRef, RuleRef, canonical_hash


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


@dataclass(frozen=True)
class ScheduleImpact:
    analysis_id: str
    method: str
    impact_days: int
    analysis_hash: str
    locator: str
    baseline_hash: str
    comparison_hash: str
    verified: bool = False

    def __post_init__(self) -> None:
        for name in (
            "analysis_id", "method", "analysis_hash", "locator",
            "baseline_hash", "comparison_hash",
        ):
            _text(name, getattr(self, name))
        if type(self.impact_days) is not int:
            raise ValueError("impact_days must be integer days")
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")


@dataclass(frozen=True)
class ConstructionEntitlement:
    event_id: str
    event_date: str
    entitled_cents: int
    paid_cents: int
    currency: str
    rule: RuleRef
    evidence: tuple[EvidenceRef, ...]
    entitlement_type: str = "change"

    def __post_init__(self) -> None:
        for name in ("event_id", "event_date", "currency", "entitlement_type"):
            _text(name, getattr(self, name))
        for name in ("entitled_cents", "paid_cents"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be non-negative integer cents")
        if not isinstance(self.rule, RuleRef):
            raise ValueError("rule must be RuleRef")
        if not self.evidence:
            raise ValueError("entitlement evidence is required")


def detect_construction_recovery(
    *,
    client_id: str,
    counterparty_id: str,
    entitlement: ConstructionEntitlement,
    schedule_impact: ScheduleImpact | None = None,
    require_schedule_impact: bool = False,
) -> RecoveryObservation:
    client_id = _text("client_id", client_id)
    counterparty_id = _text("counterparty_id", counterparty_id)

    evidence = list(entitlement.evidence)
    if schedule_impact is not None:
        evidence.append(EvidenceRef(
            evidence_id=f"schedule-impact:{schedule_impact.analysis_id}",
            source_hash=schedule_impact.analysis_hash,
            locator=schedule_impact.locator,
            kind="forensic_schedule_impact",
            verified=schedule_impact.verified,
            metadata={
                "method": schedule_impact.method,
                "impact_days": schedule_impact.impact_days,
                "baseline_hash": schedule_impact.baseline_hash,
                "comparison_hash": schedule_impact.comparison_hash,
            },
        ))
    elif require_schedule_impact:
        missing_hash = canonical_hash({
            "schema": 1,
            "event_id": entitlement.event_id,
            "missing": "forensic_schedule_impact",
        })
        evidence.append(EvidenceRef(
            evidence_id=f"schedule-impact-missing:{entitlement.event_id}",
            source_hash=missing_hash,
            locator="recoveryworks://missing/forensic-schedule-impact",
            kind="required_schedule_impact",
            verified=False,
            metadata={"missing": True},
        ))

    reason = (
        "CONSTRUCTION_DELAY_ENTITLEMENT"
        if require_schedule_impact
        else "CONSTRUCTION_CHANGE_ENTITLEMENT"
    )
    basis = "reviewed contract entitlement evidence"
    if require_schedule_impact:
        basis += " + verified forensic schedule impact required"

    return from_construction_entitlement(
        client_id=client_id,
        counterparty_id=counterparty_id,
        event_id=entitlement.event_id,
        event_date=entitlement.event_date,
        entitled_cents=entitlement.entitled_cents,
        paid_cents=entitlement.paid_cents,
        rule=entitlement.rule,
        evidence=tuple(evidence),
        currency=entitlement.currency,
        reason=reason,
        confidence_basis=basis,
        metadata={
            "entitlement_type": entitlement.entitlement_type,
            "schedule_impact_required": require_schedule_impact,
            "schedule_analysis_id": schedule_impact.analysis_id if schedule_impact else None,
        },
    )
