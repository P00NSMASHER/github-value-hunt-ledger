"""Authoritative commercial prelaunch gate for RecoveryWorks pilots.

The gate binds internal readiness evidence only. It can authorize a buyer-safe
handoff artifact, but it cannot authorize customer-data processing, kickoff,
cloud mutation, recovery claims, outreach, or any external action.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from recoveryworks.capacity_matrix import (
    ConservativeOperatingEnvelope,
    enforce_operating_envelope,
)
from recoveryworks.commercial_pilot import CloudCommercialPilotPackage
from recoveryworks.enterprise_diligence_package import (
    DiligenceGapSeverity,
    EnterpriseDiligencePackage,
)
from recoveryworks.models import canonical_hash, normalize_sha256, normalize_utc_timestamp
from recoveryworks.operator_rehearsal import OperatorRehearsalResult
from recoveryworks.production_service_levels import (
    InternalCapacityDemand,
    InternalServiceLevelSnapshot,
    ServicePressureState,
)


class PilotLaunchStatus(str, Enum):
    READY = "READY"
    CONDITIONAL = "CONDITIONAL"
    BLOCKED = "BLOCKED"


class PilotLaunchRoute(str, Enum):
    BUYER_SAFE_PRELAUNCH = "BUYER_SAFE_PRELAUNCH"
    INTERNAL_REMEDIATION = "INTERNAL_REMEDIATION"


@dataclass(frozen=True)
class PilotLaunchDecision:
    decision_id: str
    status: PilotLaunchStatus
    route: PilotLaunchRoute
    checked_at: str
    commercial_package_proof_hash: str
    operator_rehearsal_proof_hash: str
    diligence_package_proof_hash: str
    service_level_proof_hash: str
    capacity_envelope_proof_hash: str
    demand: InternalCapacityDemand
    blockers: tuple[str, ...]
    conditions: tuple[str, ...]
    warnings: tuple[str, ...]
    buyer_handoff_allowed: bool
    customer_data_authorized: bool = False
    kickoff_authorized: bool = False
    outreach_authorized: bool = False
    external_actions_authorized: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.status, PilotLaunchStatus):
            raise ValueError("status must be PilotLaunchStatus")
        if not isinstance(self.route, PilotLaunchRoute):
            raise ValueError("route must be PilotLaunchRoute")
        object.__setattr__(
            self, "checked_at", normalize_utc_timestamp("checked_at", self.checked_at)
        )
        for name in (
            "commercial_package_proof_hash",
            "operator_rehearsal_proof_hash",
            "diligence_package_proof_hash",
            "service_level_proof_hash",
            "capacity_envelope_proof_hash",
        ):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        blockers = tuple(sorted(set(self.blockers)))
        conditions = tuple(sorted(set(self.conditions)))
        warnings = tuple(sorted(set(self.warnings)))
        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(self, "conditions", conditions)
        object.__setattr__(self, "warnings", warnings)
        if self.buyer_handoff_allowed != (self.status is not PilotLaunchStatus.BLOCKED):
            raise ValueError("buyer_handoff_allowed does not match launch status")
        if (
            self.customer_data_authorized
            or self.kickoff_authorized
            or self.outreach_authorized
            or self.external_actions_authorized
        ):
            raise ValueError("prelaunch decision cannot authorize consequential actions")
        expected = "recoveryworks-pilot-launch:" + canonical_hash(self._identity())
        if self.decision_id != expected:
            raise ValueError("decision_id does not bind launch decision")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "status": self.status.value,
            "route": self.route.value,
            "checked_at": self.checked_at,
            "commercial_package_proof_hash": self.commercial_package_proof_hash,
            "operator_rehearsal_proof_hash": self.operator_rehearsal_proof_hash,
            "diligence_package_proof_hash": self.diligence_package_proof_hash,
            "service_level_proof_hash": self.service_level_proof_hash,
            "capacity_envelope_proof_hash": self.capacity_envelope_proof_hash,
            "demand": asdict(self.demand),
            "blockers": list(self.blockers),
            "conditions": list(self.conditions),
            "warnings": list(self.warnings),
            "buyer_handoff_allowed": self.buyer_handoff_allowed,
            "customer_data_authorized": False,
            "kickoff_authorized": False,
            "outreach_authorized": False,
            "external_actions_authorized": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "decision_id": self.decision_id,
            "proof_hash": self.proof_hash,
            "state": "AUTHORITATIVE_PILOT_PRELAUNCH_DECISION",
        }


def evaluate_pilot_launch_gate(
    *,
    commercial_package: CloudCommercialPilotPackage,
    operator_rehearsal: OperatorRehearsalResult,
    diligence_package: EnterpriseDiligencePackage,
    service_level: InternalServiceLevelSnapshot,
    capacity_envelope: ConservativeOperatingEnvelope,
    demand: InternalCapacityDemand,
    checked_at: str,
) -> PilotLaunchDecision:
    blockers: list[str] = []
    conditions: list[str] = []
    warnings: list[str] = []

    if (
        operator_rehearsal.customer_contacted
        or operator_rehearsal.real_customer_onboarded
        or operator_rehearsal.external_actions_performed
    ):
        blockers.append("operator_rehearsal_boundary_failed")

    capacity = enforce_operating_envelope(
        capacity_envelope,
        billing_rows=demand.billing_rows,
        provider_count=demand.provider_count,
        tenant_count=demand.tenant_count,
        evidence_bytes=demand.evidence_bytes,
    )
    if not capacity["admitted"]:
        blockers.append("requested_scope_exceeds_measured_capacity")

    if service_level.state is ServicePressureState.BLOCKED:
        blockers.append("internal_service_blocked")
    elif service_level.state is ServicePressureState.THROTTLED:
        blockers.append("internal_service_throttled")
    elif service_level.state is ServicePressureState.PRESSURE:
        conditions.append("internal_service_under_pressure")

    if not service_level.capacity_admitted:
        blockers.append("service_level_capacity_not_admitted")
    if service_level.admission_throttled:
        blockers.append("service_level_admission_throttled")

    for gap in diligence_package.gaps:
        if gap.severity is DiligenceGapSeverity.HIGH:
            blockers.append("high_diligence_gap:" + gap.control_id)
        else:
            conditions.append("diligence_gap:" + gap.control_id)

    if commercial_package.pricing.pricing_is_hypothesis is not True:
        blockers.append("commercial_pricing_not_marked_hypothesis")
    if commercial_package.scope.cloud_mutation_in_scope:
        blockers.append("cloud_mutation_in_scope")
    if commercial_package.scope.external_recovery_actions_in_scope:
        blockers.append("external_recovery_actions_in_scope")

    if not commercial_package.acceptance_criteria:
        blockers.append("commercial_acceptance_criteria_missing")
    if not commercial_package.deliverables:
        blockers.append("commercial_deliverables_missing")

    if diligence_package.certifications_claimed:
        blockers.append("unsupported_certification_claim")
    if diligence_package.externally_shared:
        warnings.append("diligence_package_already_marked_externally_shared")

    blockers = sorted(set(blockers))
    conditions = sorted(set(conditions))
    warnings = sorted(set(warnings))
    if blockers:
        status = PilotLaunchStatus.BLOCKED
        route = PilotLaunchRoute.INTERNAL_REMEDIATION
    elif conditions:
        status = PilotLaunchStatus.CONDITIONAL
        route = PilotLaunchRoute.BUYER_SAFE_PRELAUNCH
    else:
        status = PilotLaunchStatus.READY
        route = PilotLaunchRoute.BUYER_SAFE_PRELAUNCH

    checked = normalize_utc_timestamp("checked_at", checked_at)
    identity = {
        "schema": 1,
        "status": status.value,
        "route": route.value,
        "checked_at": checked,
        "commercial_package_proof_hash": commercial_package.proof_hash,
        "operator_rehearsal_proof_hash": operator_rehearsal.proof_hash,
        "diligence_package_proof_hash": diligence_package.proof_hash,
        "service_level_proof_hash": service_level.proof_hash,
        "capacity_envelope_proof_hash": capacity_envelope.proof_hash,
        "demand": asdict(demand),
        "blockers": blockers,
        "conditions": conditions,
        "warnings": warnings,
        "buyer_handoff_allowed": status is not PilotLaunchStatus.BLOCKED,
        "customer_data_authorized": False,
        "kickoff_authorized": False,
        "outreach_authorized": False,
        "external_actions_authorized": False,
    }
    return PilotLaunchDecision(
        decision_id="recoveryworks-pilot-launch:" + canonical_hash(identity),
        status=status,
        route=route,
        checked_at=checked,
        commercial_package_proof_hash=commercial_package.proof_hash,
        operator_rehearsal_proof_hash=operator_rehearsal.proof_hash,
        diligence_package_proof_hash=diligence_package.proof_hash,
        service_level_proof_hash=service_level.proof_hash,
        capacity_envelope_proof_hash=capacity_envelope.proof_hash,
        demand=demand,
        blockers=tuple(blockers),
        conditions=tuple(conditions),
        warnings=tuple(warnings),
        buyer_handoff_allowed=status is not PilotLaunchStatus.BLOCKED,
        customer_data_authorized=False,
        kickoff_authorized=False,
        outreach_authorized=False,
        external_actions_authorized=False,
    )
