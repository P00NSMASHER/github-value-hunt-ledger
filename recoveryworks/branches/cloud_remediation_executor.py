"""Dry-run-only remediation executor boundary.

This module validates exact remediation authorization artifacts, a verified
read-only resource snapshot, an allowlisted action contract, and explicit
preconditions. It produces a dry-run plan only. It contains no cloud SDK,
provider API call, shell command, or live mutation function.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from recoveryworks.models import (
    canonical_hash,
    freeze_json,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)
from .cloud_remediation import (
    CloudRemediationAction,
    CloudRemediationApproval,
    CloudRemediationEnvelope,
    CloudRemediationPlan,
)


_ACTION_CONTRACTS: dict[str, dict[str, Any]] = {
    "resize_instance": {
        "required_parameters": ("target_instance_type",),
        "optional_parameters": ("maintenance_window", "change_ticket_id"),
        "risk_level": "MODIFY",
        "resource_required": True,
    },
    "remove_idle_resource": {
        "required_parameters": ("dependency_review_id",),
        "optional_parameters": ("change_ticket_id",),
        "risk_level": "DESTRUCTIVE",
        "resource_required": True,
    },
}


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


@dataclass(frozen=True)
class CloudResourceSnapshot:
    provider: str
    account_id: str
    resource_id: str
    resource_type: str
    observed_at: str
    attributes: Mapping[str, Any]
    source_hash: str
    source_locator: str
    verified: bool

    def __post_init__(self) -> None:
        for name in ("provider", "account_id", "resource_id", "resource_type", "source_locator"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        object.__setattr__(
            self,
            "observed_at",
            normalize_utc_timestamp("observed_at", self.observed_at),
        )
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        object.__setattr__(
            self,
            "attributes",
            freeze_json(self.attributes, name="attributes"),
        )
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def state_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "provider": self.provider,
            "account_id": self.account_id,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "attributes": dict(self.attributes),
        })

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            **asdict(self),
        })


@dataclass(frozen=True)
class CloudRemediationDryRunRequest:
    action_id: str
    envelope_proof_hash: str
    expected_resource_state_hash: str
    parameters: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "action_id", _text("action_id", self.action_id))
        object.__setattr__(
            self,
            "envelope_proof_hash",
            normalize_sha256("envelope_proof_hash", self.envelope_proof_hash),
        )
        object.__setattr__(
            self,
            "expected_resource_state_hash",
            normalize_sha256(
                "expected_resource_state_hash", self.expected_resource_state_hash
            ),
        )
        object.__setattr__(
            self,
            "parameters",
            freeze_json(self.parameters, name="parameters"),
        )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "action_id": self.action_id,
            "envelope_proof_hash": self.envelope_proof_hash,
            "expected_resource_state_hash": self.expected_resource_state_hash,
            "parameters": dict(self.parameters),
        })


@dataclass(frozen=True)
class CloudRemediationExecutorPolicy:
    allowed_action_types: tuple[str, ...] = (
        "resize_instance",
        "remove_idle_resource",
    )

    def __post_init__(self) -> None:
        normalized = tuple(sorted({_text("allowed_action_type", value) for value in self.allowed_action_types}))
        if not normalized:
            raise ValueError("at least one remediation action type must be allowlisted")
        unknown = set(normalized) - set(_ACTION_CONTRACTS)
        if unknown:
            raise ValueError(
                "executor policy contains unsupported action types: "
                + ", ".join(sorted(unknown))
            )
        object.__setattr__(self, "allowed_action_types", normalized)


@dataclass(frozen=True)
class CloudRemediationDryRunPlan:
    dry_run_plan_id: str
    action_id: str
    action_type: str
    provider: str
    account_id: str
    resource_id: str
    resource_type: str
    envelope_proof_hash: str
    approval_hash: str
    resource_snapshot_proof_hash: str
    resource_state_hash: str
    request_proof_hash: str
    risk_level: str
    parameters: Mapping[str, Any]
    preconditions: tuple[str, ...]
    live_execution_allowed: bool = False
    mutation_performed: bool = False
    provider_api_operation: str | None = None

    def __post_init__(self) -> None:
        if self.live_execution_allowed or self.mutation_performed:
            raise ValueError("dry-run remediation plan cannot permit or record mutation")
        if self.provider_api_operation is not None:
            raise ValueError("dry-run remediation plan cannot contain a provider API operation")
        for name in (
            "envelope_proof_hash",
            "approval_hash",
            "resource_snapshot_proof_hash",
            "resource_state_hash",
            "request_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self,
            "parameters",
            freeze_json(self.parameters, name="parameters"),
        )
        expected = "cloud-remediation-dry-run:" + canonical_hash(self._identity())
        if self.dry_run_plan_id != expected:
            raise ValueError("dry_run_plan_id does not bind the dry-run plan")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "action_id": self.action_id,
            "action_type": self.action_type,
            "provider": self.provider,
            "account_id": self.account_id,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "envelope_proof_hash": self.envelope_proof_hash,
            "approval_hash": self.approval_hash,
            "resource_snapshot_proof_hash": self.resource_snapshot_proof_hash,
            "resource_state_hash": self.resource_state_hash,
            "request_proof_hash": self.request_proof_hash,
            "risk_level": self.risk_level,
            "parameters": dict(self.parameters),
            "preconditions": list(self.preconditions),
            "live_execution_allowed": False,
            "mutation_performed": False,
            "provider_api_operation": None,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "dry_run_plan_id": self.dry_run_plan_id,
            "proof_hash": self.proof_hash,
            "state": "DRY_RUN_VALIDATED",
        }


def _bound_action(
    plan: CloudRemediationPlan,
    approval: CloudRemediationApproval,
    envelope: CloudRemediationEnvelope,
) -> CloudRemediationAction:
    if approval.plan_id != plan.plan_id or approval.plan_proof_hash != plan.proof_hash:
        raise ValueError("remediation approval does not bind the supplied plan")
    if envelope.plan_id != plan.plan_id or envelope.approval_hash != approval.proof_hash:
        raise ValueError("remediation envelope does not bind the supplied approval")
    if envelope.action_id not in approval.approved_action_ids:
        raise ValueError("remediation envelope action was not approved")
    matches = [action for action in plan.actions if action.action_id == envelope.action_id]
    if len(matches) != 1:
        raise ValueError("remediation action is missing or ambiguous in plan")
    action = matches[0]
    if (
        envelope.provider != action.provider
        or envelope.account_id != action.account_id
        or envelope.resource_id != action.resource_id
        or envelope.action_type != action.action_type
        or envelope.proposed_change != action.proposed_change
    ):
        raise ValueError("remediation envelope fields do not match the approved action")
    return action


def prepare_cloud_remediation_dry_run(
    *,
    plan: CloudRemediationPlan,
    approval: CloudRemediationApproval,
    envelope: CloudRemediationEnvelope,
    snapshot: CloudResourceSnapshot,
    request: CloudRemediationDryRunRequest,
    policy: CloudRemediationExecutorPolicy = CloudRemediationExecutorPolicy(),
) -> CloudRemediationDryRunPlan:
    """Validate exact authorization + state and return a non-executable plan."""
    action = _bound_action(plan, approval, envelope)
    if request.action_id != action.action_id:
        raise ValueError("dry-run request action_id mismatch")
    if request.envelope_proof_hash != envelope.proof_hash:
        raise ValueError("dry-run request does not bind the exact envelope")
    if action.action_type not in policy.allowed_action_types:
        raise ValueError("remediation action type is not allowlisted")
    contract = _ACTION_CONTRACTS[action.action_type]

    if not snapshot.verified:
        raise ValueError("resource snapshot must be independently verified")
    if (
        snapshot.provider != action.provider
        or snapshot.account_id != action.account_id
        or snapshot.resource_id != action.resource_id
    ):
        raise ValueError("resource snapshot identity does not match remediation action")
    if request.expected_resource_state_hash != snapshot.state_hash:
        raise ValueError("resource state changed or dry-run request is stale")

    parameters = dict(request.parameters)
    required = set(contract["required_parameters"])
    optional = set(contract["optional_parameters"])
    missing = sorted(required - set(parameters))
    unknown = sorted(set(parameters) - required - optional)
    if missing:
        raise ValueError(
            "dry-run request missing required parameters: " + ", ".join(missing)
        )
    if unknown:
        raise ValueError(
            "dry-run request contains unsupported parameters: " + ", ".join(unknown)
        )
    for key in required:
        _text(f"parameters.{key}", parameters[key])
    for key in optional & set(parameters):
        _text(f"parameters.{key}", parameters[key])

    preconditions = (
        "exact plan approval verified",
        "exact NOT_EXECUTED envelope verified",
        "action type present in executor allowlist",
        "verified read-only resource snapshot",
        "provider/account/resource identity matched",
        "resource state hash matched request",
        "required action parameters present",
        "no provider mutation implementation loaded",
    )
    identity = {
        "schema": 1,
        "action_id": action.action_id,
        "action_type": action.action_type,
        "provider": action.provider,
        "account_id": action.account_id,
        "resource_id": snapshot.resource_id,
        "resource_type": snapshot.resource_type,
        "envelope_proof_hash": envelope.proof_hash,
        "approval_hash": approval.proof_hash,
        "resource_snapshot_proof_hash": snapshot.proof_hash,
        "resource_state_hash": snapshot.state_hash,
        "request_proof_hash": request.proof_hash,
        "risk_level": contract["risk_level"],
        "parameters": parameters,
        "preconditions": list(preconditions),
        "live_execution_allowed": False,
        "mutation_performed": False,
        "provider_api_operation": None,
    }
    return CloudRemediationDryRunPlan(
        dry_run_plan_id="cloud-remediation-dry-run:" + canonical_hash(identity),
        action_id=action.action_id,
        action_type=action.action_type,
        provider=action.provider,
        account_id=action.account_id,
        resource_id=snapshot.resource_id,
        resource_type=snapshot.resource_type,
        envelope_proof_hash=envelope.proof_hash,
        approval_hash=approval.proof_hash,
        resource_snapshot_proof_hash=snapshot.proof_hash,
        resource_state_hash=snapshot.state_hash,
        request_proof_hash=request.proof_hash,
        risk_level=contract["risk_level"],
        parameters=parameters,
        preconditions=preconditions,
        live_execution_allowed=False,
        mutation_performed=False,
        provider_api_operation=None,
    )
