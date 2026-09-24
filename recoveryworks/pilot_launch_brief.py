"""Actionable brief derived only from the authoritative RecoveryWorks launch gate."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from recoveryworks.models import canonical_hash, normalize_sha256
from recoveryworks.pilot_launch_gate import PilotLaunchDecision, PilotLaunchStatus


@dataclass(frozen=True)
class PilotLaunchAction:
    priority: str
    owner: str
    code: str
    title: str
    evidence_required: tuple[str, ...]
    unlocks: str

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class PilotLaunchBrief:
    brief_id: str
    launch_decision_id: str
    launch_decision_proof_hash: str
    status: PilotLaunchStatus
    summary: str
    actions: tuple[PilotLaunchAction, ...]
    warnings: tuple[str, ...]
    can_override_gate: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "launch_decision_proof_hash",
            normalize_sha256(
                "launch_decision_proof_hash", self.launch_decision_proof_hash
            ),
        )
        if self.can_override_gate:
            raise ValueError("launch brief cannot override authoritative gate")
        expected = "recoveryworks-pilot-launch-brief:" + canonical_hash(
            self._identity()
        )
        if self.brief_id != expected:
            raise ValueError("brief_id does not bind launch brief")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "launch_decision_id": self.launch_decision_id,
            "launch_decision_proof_hash": self.launch_decision_proof_hash,
            "status": self.status.value,
            "summary": self.summary,
            "action_hashes": [a.proof_hash for a in self.actions],
            "warnings": list(self.warnings),
            "can_override_gate": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "brief_id": self.brief_id,
            "proof_hash": self.proof_hash,
            "actions": [
                {
                    **asdict(a),
                    "evidence_required": list(a.evidence_required),
                    "proof_hash": a.proof_hash,
                }
                for a in self.actions
            ],
            "state": "PILOT_LAUNCH_BRIEF_READY",
        }


_ACTIONS = {
    "requested_scope_exceeds_measured_capacity": PilotLaunchAction(
        "P0", "PLATFORM OPERATIONS",
        "requested_scope_exceeds_measured_capacity",
        "Narrow the proposed pilot scope to the measured internal operating envelope.",
        ("measured capacity matrix", "updated billing-row/provider/tenant/evidence-size scope"),
        "Capacity admission can be reevaluated.",
    ),
    "internal_service_blocked": PilotLaunchAction(
        "P0", "PLATFORM OPERATIONS",
        "internal_service_blocked",
        "Clear internal service-level blockers before buyer handoff.",
        ("fresh internal SLO snapshot with no blocking alerts",),
        "Buyer-safe prelaunch can be reevaluated.",
    ),
    "internal_service_throttled": PilotLaunchAction(
        "P0", "PLATFORM OPERATIONS",
        "internal_service_throttled",
        "Reduce queue/capacity pressure before buyer handoff.",
        ("fresh internal SLO snapshot below throttle threshold",),
        "Buyer-safe prelaunch can be reevaluated.",
    ),
    "internal_service_under_pressure": PilotLaunchAction(
        "P1", "PLATFORM OPERATIONS",
        "internal_service_under_pressure",
        "Close current internal service-pressure alerts or narrow pilot demand.",
        ("fresh SLO snapshot", "capacity demand review"),
        "Conditional prelaunch can become READY.",
    ),
}


def _action_for(code: str) -> PilotLaunchAction:
    if code in _ACTIONS:
        return _ACTIONS[code]
    if code.startswith("high_diligence_gap:"):
        control = code.split(":", 1)[1]
        return PilotLaunchAction(
            "P0", "SECURITY / COMPLIANCE",
            code,
            "Close the high-severity diligence gap before buyer handoff.",
            (f"updated evidence for control {control}", "regenerated diligence package"),
            "Launch gate can clear the diligence blocker.",
        )
    if code.startswith("diligence_gap:"):
        control = code.split(":", 1)[1]
        return PilotLaunchAction(
            "P1", "SECURITY / COMPLIANCE",
            code,
            "Resolve or explicitly disposition the diligence gap.",
            (f"event-specific or validated evidence for control {control}",),
            "Conditional prelaunch can become READY.",
        )
    return PilotLaunchAction(
        "P0", "PRODUCT / OPERATIONS REVIEW",
        code,
        "Resolve this authoritative launch-gate item with source evidence.",
        ("root-cause record", "updated proof artifact", "rerun of authoritative gate"),
        "Launch gate can be reevaluated.",
    )


def build_pilot_launch_brief(decision: PilotLaunchDecision) -> PilotLaunchBrief:
    codes = tuple(dict.fromkeys((*decision.blockers, *decision.conditions)))
    actions = tuple(
        sorted(
            (_action_for(code) for code in codes),
            key=lambda a: (0 if a.priority == "P0" else 1, a.code),
        )
    )
    if decision.status is PilotLaunchStatus.READY:
        summary = (
            "Internal pilot controls are READY for a buyer-safe prelaunch handoff. "
            "This does not authorize customer data, kickoff, outreach, or external action."
        )
    elif decision.status is PilotLaunchStatus.CONDITIONAL:
        summary = (
            "Buyer-safe prelaunch is CONDITIONAL. Close the listed proof conditions "
            "before treating the pilot as internally READY."
        )
    else:
        summary = (
            "Buyer-safe prelaunch is BLOCKED. Close all P0 items and rerun the "
            "authoritative RecoveryWorks launch gate."
        )
    identity = {
        "schema": 1,
        "launch_decision_id": decision.decision_id,
        "launch_decision_proof_hash": decision.proof_hash,
        "status": decision.status.value,
        "summary": summary,
        "action_hashes": [a.proof_hash for a in actions],
        "warnings": list(decision.warnings),
        "can_override_gate": False,
    }
    return PilotLaunchBrief(
        brief_id="recoveryworks-pilot-launch-brief:" + canonical_hash(identity),
        launch_decision_id=decision.decision_id,
        launch_decision_proof_hash=decision.proof_hash,
        status=decision.status,
        summary=summary,
        actions=actions,
        warnings=decision.warnings,
        can_override_gate=False,
    )
