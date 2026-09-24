"""Governed, plan-only cloud remediation workflow.

This module deliberately has no cloud-provider write/execute function.
Approval creates a cryptographically bound authorization record and exact
not-executed envelopes for downstream, separately authorized infrastructure.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from recoveryworks.models import canonical_hash, normalize_sha256
from .cloud_signals import CloudSignal, CloudSignalType


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


def _expected_action_id(
    *,
    signal_id: str,
    source_signal_hash: str,
    action_type: str,
    proposed_change: str,
) -> str:
    identity = {
        "signal_id": signal_id,
        "source_signal_hash": source_signal_hash,
        "action_type": action_type,
        "proposed_change": proposed_change,
    }
    return "cloud-remediation:" + canonical_hash(identity)


@dataclass(frozen=True)
class CloudRemediationAction:
    action_id: str
    signal_id: str
    provider: str
    account_id: str
    service_id: str
    resource_id: str | None
    action_type: str
    proposed_change: str
    estimated_savings_cents: int
    source_signal_hash: str

    def __post_init__(self) -> None:
        for name in (
            "signal_id",
            "provider",
            "account_id",
            "service_id",
            "action_type",
            "proposed_change",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        if self.resource_id is not None:
            object.__setattr__(
                self, "resource_id", _text("resource_id", self.resource_id)
            )
        object.__setattr__(
            self,
            "source_signal_hash",
            normalize_sha256("source_signal_hash", self.source_signal_hash),
        )
        if type(self.estimated_savings_cents) is not int or self.estimated_savings_cents < 0:
            raise ValueError("estimated_savings_cents must be a non-negative integer")
        expected = _expected_action_id(
            signal_id=self.signal_id,
            source_signal_hash=self.source_signal_hash,
            action_type=self.action_type,
            proposed_change=self.proposed_change,
        )
        if self.action_id != expected:
            raise ValueError("action_id does not bind the remediation action payload")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class CloudRemediationPlan:
    plan_id: str
    actions: tuple[CloudRemediationAction, ...]

    def __post_init__(self) -> None:
        actions = tuple(self.actions)
        if not all(isinstance(action, CloudRemediationAction) for action in actions):
            raise ValueError("actions must contain CloudRemediationAction values")
        actions = tuple(sorted(actions, key=lambda action: action.action_id))
        if len({action.action_id for action in actions}) != len(actions):
            raise ValueError("remediation plan contains duplicate action ids")
        object.__setattr__(self, "actions", actions)
        expected = "cloud-remediation-plan:" + canonical_hash({
            "action_hashes": [action.proof_hash for action in actions],
        })
        if self.plan_id != expected:
            raise ValueError("plan_id does not bind the exact remediation actions")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "plan_id": self.plan_id,
            "action_hashes": [action.proof_hash for action in self.actions],
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "proof_hash": self.proof_hash,
            "state": "DRAFT",
            "execution_allowed": False,
            "actions": [
                {**asdict(action), "proof_hash": action.proof_hash}
                for action in self.actions
            ],
        }


@dataclass(frozen=True)
class CloudRemediationApproval:
    plan_id: str
    plan_proof_hash: str
    reviewer_id: str
    customer_authorization_id: str
    approved_action_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", _text("plan_id", self.plan_id))
        object.__setattr__(
            self,
            "plan_proof_hash",
            normalize_sha256("plan_proof_hash", self.plan_proof_hash),
        )
        object.__setattr__(self, "reviewer_id", _text("reviewer_id", self.reviewer_id))
        object.__setattr__(
            self,
            "customer_authorization_id",
            _text("customer_authorization_id", self.customer_authorization_id),
        )
        selected = tuple(
            sorted({_text("approved_action_id", value) for value in self.approved_action_ids})
        )
        if not selected:
            raise ValueError("at least one remediation action must be approved")
        object.__setattr__(self, "approved_action_ids", selected)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "proof_hash": self.proof_hash,
            "execution_allowed": False,
        }


@dataclass(frozen=True)
class CloudRemediationEnvelope:
    action_id: str
    plan_id: str
    approval_hash: str
    provider: str
    account_id: str
    resource_id: str | None
    action_type: str
    proposed_change: str
    execution_status: str = "NOT_EXECUTED"

    def __post_init__(self) -> None:
        for name in (
            "action_id",
            "plan_id",
            "provider",
            "account_id",
            "action_type",
            "proposed_change",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        if self.resource_id is not None:
            object.__setattr__(
                self, "resource_id", _text("resource_id", self.resource_id)
            )
        object.__setattr__(
            self,
            "approval_hash",
            normalize_sha256("approval_hash", self.approval_hash),
        )
        if self.execution_status != "NOT_EXECUTED":
            raise ValueError(
                "RecoveryOS remediation envelopes are plan-only and must remain NOT_EXECUTED"
            )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


def build_cloud_remediation_plan(
    signals: Iterable[CloudSignal],
) -> CloudRemediationPlan:
    actions: list[CloudRemediationAction] = []
    for signal in signals:
        if signal.signal_type is not CloudSignalType.SAVINGS_OPPORTUNITY:
            continue
        action_type = str(signal.metadata.get("remediation_action") or "").strip()
        proposed_change = str(signal.metadata.get("recommendation") or "").strip()
        if not action_type or not proposed_change:
            continue
        amount = signal.estimated_impact_cents or 0
        actions.append(CloudRemediationAction(
            action_id=_expected_action_id(
                signal_id=signal.signal_id,
                source_signal_hash=signal.proof_hash,
                action_type=action_type,
                proposed_change=proposed_change,
            ),
            signal_id=signal.signal_id,
            provider=signal.provider,
            account_id=signal.account_id,
            service_id=signal.service_id,
            resource_id=signal.resource_id,
            action_type=action_type,
            proposed_change=proposed_change,
            estimated_savings_cents=amount,
            source_signal_hash=signal.proof_hash,
        ))
    actions.sort(key=lambda item: item.action_id)
    plan_identity = {
        "action_hashes": [action.proof_hash for action in actions],
    }
    return CloudRemediationPlan(
        plan_id="cloud-remediation-plan:" + canonical_hash(plan_identity),
        actions=tuple(actions),
    )


def approve_cloud_remediation_plan(
    plan: CloudRemediationPlan,
    *,
    reviewer_id: str,
    customer_authorization_id: str,
    approved_action_ids: Iterable[str] | None = None,
) -> CloudRemediationApproval:
    reviewer = reviewer_id.strip()
    authorization = customer_authorization_id.strip()
    if not reviewer:
        raise ValueError("reviewer_id is required")
    if not authorization:
        raise ValueError("customer_authorization_id is required")
    available = {action.action_id for action in plan.actions}
    selected = (
        tuple(sorted(available))
        if approved_action_ids is None
        else tuple(sorted(set(approved_action_ids)))
    )
    unknown = set(selected) - available
    if unknown:
        raise ValueError(
            "approval contains unknown remediation action ids: "
            + ", ".join(sorted(unknown))
        )
    if not selected:
        raise ValueError("at least one remediation action must be approved")
    return CloudRemediationApproval(
        plan_id=plan.plan_id,
        plan_proof_hash=plan.proof_hash,
        reviewer_id=reviewer,
        customer_authorization_id=authorization,
        approved_action_ids=selected,
    )


def prepare_cloud_remediation_envelopes(
    plan: CloudRemediationPlan,
    approval: CloudRemediationApproval,
) -> tuple[CloudRemediationEnvelope, ...]:
    if approval.plan_id != plan.plan_id or approval.plan_proof_hash != plan.proof_hash:
        raise ValueError("remediation approval does not bind this exact plan")
    approved = set(approval.approved_action_ids)
    actions = {action.action_id: action for action in plan.actions}
    if not approved.issubset(actions):
        raise ValueError("approval references an action not present in the plan")
    return tuple(
        CloudRemediationEnvelope(
            action_id=action_id,
            plan_id=plan.plan_id,
            approval_hash=approval.proof_hash,
            provider=actions[action_id].provider,
            account_id=actions[action_id].account_id,
            resource_id=actions[action_id].resource_id,
            action_type=actions[action_id].action_type,
            proposed_change=actions[action_id].proposed_change,
        )
        for action_id in sorted(approved)
    )
