"""Governed handoff and verified receipt boundary for cloud remediation.

This module still performs no cloud mutation. It binds an approved dry-run plan
to a named downstream executor, requires a fresh verified state recheck before
handoff consumption, and verifies an externally supplied execution receipt
against the exact handoff/gate/post-state evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from recoveryworks.models import (
    canonical_hash,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)
from .cloud_remediation import (
    CloudRemediationApproval,
    CloudRemediationEnvelope,
)
from .cloud_remediation_executor import (
    CloudRemediationDryRunPlan,
    CloudResourceSnapshot,
)


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class CloudExecutionOutcome(str, Enum):
    APPLIED = "APPLIED"
    NOOP = "NOOP"
    FAILED = "FAILED"


@dataclass(frozen=True)
class CloudRemediationHandoff:
    handoff_id: str
    action_id: str
    dry_run_plan_id: str
    dry_run_plan_proof_hash: str
    envelope_proof_hash: str
    approval_hash: str
    customer_authorization_id: str
    executor_id: str
    handoff_authorizer_id: str
    issued_at: str
    expires_at: str
    expected_resource_state_hash: str
    pre_execution_recheck_required: bool = True
    credentials_embedded: bool = False
    provider_operation_embedded: bool = False

    def __post_init__(self) -> None:
        for name in (
            "action_id",
            "dry_run_plan_id",
            "customer_authorization_id",
            "executor_id",
            "handoff_authorizer_id",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "dry_run_plan_proof_hash",
            "envelope_proof_hash",
            "approval_hash",
            "expected_resource_state_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self, "issued_at", normalize_utc_timestamp("issued_at", self.issued_at)
        )
        object.__setattr__(
            self, "expires_at", normalize_utc_timestamp("expires_at", self.expires_at)
        )
        if _instant(self.expires_at) <= _instant(self.issued_at):
            raise ValueError("handoff expiry must be after issuance")
        if self.pre_execution_recheck_required is not True:
            raise ValueError("pre-execution state recheck is mandatory")
        if self.credentials_embedded:
            raise ValueError("remediation handoff must not embed credentials")
        if self.provider_operation_embedded:
            raise ValueError("remediation handoff must not embed provider operations")
        expected = "cloud-remediation-handoff:" + canonical_hash(self._identity())
        if self.handoff_id != expected:
            raise ValueError("handoff_id does not bind the handoff payload")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "action_id": self.action_id,
            "dry_run_plan_id": self.dry_run_plan_id,
            "dry_run_plan_proof_hash": self.dry_run_plan_proof_hash,
            "envelope_proof_hash": self.envelope_proof_hash,
            "approval_hash": self.approval_hash,
            "customer_authorization_id": self.customer_authorization_id,
            "executor_id": self.executor_id,
            "handoff_authorizer_id": self.handoff_authorizer_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "expected_resource_state_hash": self.expected_resource_state_hash,
            "pre_execution_recheck_required": True,
            "credentials_embedded": False,
            "provider_operation_embedded": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "handoff_id": self.handoff_id,
            "proof_hash": self.proof_hash,
            "state": "READY_FOR_SEPARATE_EXECUTOR",
            "mutation_performed": False,
        }


@dataclass(frozen=True)
class CloudRemediationExecutionGate:
    gate_id: str
    handoff_id: str
    handoff_proof_hash: str
    action_id: str
    executor_id: str
    checked_at: str
    fresh_snapshot_proof_hash: str
    fresh_resource_state_hash: str
    provider: str
    account_id: str
    resource_id: str
    resource_type: str

    def __post_init__(self) -> None:
        for name in (
            "handoff_id",
            "action_id",
            "executor_id",
            "provider",
            "account_id",
            "resource_id",
            "resource_type",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "handoff_proof_hash",
            "fresh_snapshot_proof_hash",
            "fresh_resource_state_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self, "checked_at", normalize_utc_timestamp("checked_at", self.checked_at)
        )
        expected = "cloud-remediation-gate:" + canonical_hash(self._identity())
        if self.gate_id != expected:
            raise ValueError("gate_id does not bind the execution gate")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "handoff_id": self.handoff_id,
            "handoff_proof_hash": self.handoff_proof_hash,
            "action_id": self.action_id,
            "executor_id": self.executor_id,
            "checked_at": self.checked_at,
            "fresh_snapshot_proof_hash": self.fresh_snapshot_proof_hash,
            "fresh_resource_state_hash": self.fresh_resource_state_hash,
            "provider": self.provider,
            "account_id": self.account_id,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "gate_id": self.gate_id,
            "proof_hash": self.proof_hash,
            "state": "RECHECK_PASSED",
            "provider_operation": None,
        }


@dataclass(frozen=True)
class CloudRemediationExecutionReceipt:
    receipt_id: str
    handoff_id: str
    handoff_proof_hash: str
    gate_id: str
    gate_proof_hash: str
    action_id: str
    executor_id: str
    outcome: CloudExecutionOutcome
    started_at: str
    completed_at: str
    pre_resource_state_hash: str
    post_resource_state_hash: str
    post_snapshot_proof_hash: str
    provider_request_id: str | None
    source_hash: str
    source_locator: str
    verified: bool
    mutation_performed: bool

    def __post_init__(self) -> None:
        for name in (
            "handoff_id",
            "gate_id",
            "action_id",
            "executor_id",
            "source_locator",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        if self.provider_request_id is not None:
            object.__setattr__(
                self,
                "provider_request_id",
                _text("provider_request_id", self.provider_request_id),
            )
        for name in (
            "handoff_proof_hash",
            "gate_proof_hash",
            "pre_resource_state_hash",
            "post_resource_state_hash",
            "post_snapshot_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        object.__setattr__(
            self, "started_at", normalize_utc_timestamp("started_at", self.started_at)
        )
        object.__setattr__(
            self,
            "completed_at",
            normalize_utc_timestamp("completed_at", self.completed_at),
        )
        if _instant(self.completed_at) < _instant(self.started_at):
            raise ValueError("execution receipt completion cannot predate start")
        if not isinstance(self.outcome, CloudExecutionOutcome):
            raise ValueError("outcome must be a CloudExecutionOutcome")
        if type(self.verified) is not bool or type(self.mutation_performed) is not bool:
            raise ValueError("verified and mutation_performed must be boolean")
        if self.outcome is CloudExecutionOutcome.APPLIED:
            if not self.mutation_performed:
                raise ValueError("APPLIED outcome requires mutation_performed=true")
            if self.pre_resource_state_hash == self.post_resource_state_hash:
                raise ValueError("APPLIED outcome requires a changed resource state")
        elif self.outcome is CloudExecutionOutcome.NOOP:
            if self.mutation_performed:
                raise ValueError("NOOP outcome cannot claim mutation")
            if self.pre_resource_state_hash != self.post_resource_state_hash:
                raise ValueError("NOOP outcome requires unchanged resource state")
        expected = "cloud-remediation-receipt:" + canonical_hash(self._identity())
        if self.receipt_id != expected:
            raise ValueError("receipt_id does not bind the execution receipt")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "handoff_id": self.handoff_id,
            "handoff_proof_hash": self.handoff_proof_hash,
            "gate_id": self.gate_id,
            "gate_proof_hash": self.gate_proof_hash,
            "action_id": self.action_id,
            "executor_id": self.executor_id,
            "outcome": self.outcome.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "pre_resource_state_hash": self.pre_resource_state_hash,
            "post_resource_state_hash": self.post_resource_state_hash,
            "post_snapshot_proof_hash": self.post_snapshot_proof_hash,
            "provider_request_id": self.provider_request_id,
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": self.verified,
            "mutation_performed": self.mutation_performed,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "receipt_id": self.receipt_id,
            "proof_hash": self.proof_hash,
            "state": "VERIFIED" if self.verified else "REVIEW",
        }


def create_cloud_remediation_handoff(
    *,
    dry_run: CloudRemediationDryRunPlan,
    approval: CloudRemediationApproval,
    envelope: CloudRemediationEnvelope,
    executor_id: str,
    handoff_authorizer_id: str,
    issued_at: str,
    expires_at: str,
) -> CloudRemediationHandoff:
    if dry_run.action_id != envelope.action_id:
        raise ValueError("dry-run action does not match remediation envelope")
    if dry_run.envelope_proof_hash != envelope.proof_hash:
        raise ValueError("dry-run plan does not bind the exact remediation envelope")
    if dry_run.approval_hash != approval.proof_hash:
        raise ValueError("dry-run plan does not bind the exact approval")
    if envelope.approval_hash != approval.proof_hash:
        raise ValueError("remediation envelope does not bind the exact approval")
    if dry_run.live_execution_allowed or dry_run.mutation_performed:
        raise ValueError("only a non-mutating validated dry-run may be handed off")

    issued = normalize_utc_timestamp("issued_at", issued_at)
    expiry = normalize_utc_timestamp("expires_at", expires_at)
    identity = {
        "schema": 1,
        "action_id": dry_run.action_id,
        "dry_run_plan_id": dry_run.dry_run_plan_id,
        "dry_run_plan_proof_hash": dry_run.proof_hash,
        "envelope_proof_hash": envelope.proof_hash,
        "approval_hash": approval.proof_hash,
        "customer_authorization_id": approval.customer_authorization_id,
        "executor_id": executor_id.strip(),
        "handoff_authorizer_id": handoff_authorizer_id.strip(),
        "issued_at": issued,
        "expires_at": expiry,
        "expected_resource_state_hash": dry_run.resource_state_hash,
        "pre_execution_recheck_required": True,
        "credentials_embedded": False,
        "provider_operation_embedded": False,
    }
    return CloudRemediationHandoff(
        handoff_id="cloud-remediation-handoff:" + canonical_hash(identity),
        action_id=dry_run.action_id,
        dry_run_plan_id=dry_run.dry_run_plan_id,
        dry_run_plan_proof_hash=dry_run.proof_hash,
        envelope_proof_hash=envelope.proof_hash,
        approval_hash=approval.proof_hash,
        customer_authorization_id=approval.customer_authorization_id,
        executor_id=executor_id,
        handoff_authorizer_id=handoff_authorizer_id,
        issued_at=issued,
        expires_at=expiry,
        expected_resource_state_hash=dry_run.resource_state_hash,
    )


def recheck_cloud_remediation_handoff(
    handoff: CloudRemediationHandoff,
    *,
    fresh_snapshot: CloudResourceSnapshot,
    checked_at: str,
) -> CloudRemediationExecutionGate:
    checked = normalize_utc_timestamp("checked_at", checked_at)
    if _instant(checked) < _instant(handoff.issued_at):
        raise ValueError("execution recheck cannot predate handoff issuance")
    if _instant(checked) > _instant(handoff.expires_at):
        raise ValueError("remediation handoff has expired")
    if not fresh_snapshot.verified:
        raise ValueError("fresh resource snapshot must be verified")
    if _instant(fresh_snapshot.observed_at) < _instant(handoff.issued_at):
        raise ValueError("fresh resource snapshot predates handoff issuance")
    if _instant(fresh_snapshot.observed_at) > _instant(checked):
        raise ValueError("fresh resource snapshot cannot postdate the recheck")
    if fresh_snapshot.state_hash != handoff.expected_resource_state_hash:
        raise ValueError("resource state changed after dry-run; new review is required")

    identity = {
        "schema": 1,
        "handoff_id": handoff.handoff_id,
        "handoff_proof_hash": handoff.proof_hash,
        "action_id": handoff.action_id,
        "executor_id": handoff.executor_id,
        "checked_at": checked,
        "fresh_snapshot_proof_hash": fresh_snapshot.proof_hash,
        "fresh_resource_state_hash": fresh_snapshot.state_hash,
        "provider": fresh_snapshot.provider,
        "account_id": fresh_snapshot.account_id,
        "resource_id": fresh_snapshot.resource_id,
        "resource_type": fresh_snapshot.resource_type,
    }
    return CloudRemediationExecutionGate(
        gate_id="cloud-remediation-gate:" + canonical_hash(identity),
        handoff_id=handoff.handoff_id,
        handoff_proof_hash=handoff.proof_hash,
        action_id=handoff.action_id,
        executor_id=handoff.executor_id,
        checked_at=checked,
        fresh_snapshot_proof_hash=fresh_snapshot.proof_hash,
        fresh_resource_state_hash=fresh_snapshot.state_hash,
        provider=fresh_snapshot.provider,
        account_id=fresh_snapshot.account_id,
        resource_id=fresh_snapshot.resource_id,
        resource_type=fresh_snapshot.resource_type,
    )


def build_cloud_remediation_execution_receipt(
    *,
    handoff: CloudRemediationHandoff,
    gate: CloudRemediationExecutionGate,
    post_snapshot: CloudResourceSnapshot,
    outcome: CloudExecutionOutcome,
    started_at: str,
    completed_at: str,
    source_hash: str,
    source_locator: str,
    verified: bool,
    mutation_performed: bool,
    provider_request_id: str | None = None,
) -> CloudRemediationExecutionReceipt:
    if gate.handoff_id != handoff.handoff_id or gate.handoff_proof_hash != handoff.proof_hash:
        raise ValueError("execution gate does not bind the remediation handoff")
    if gate.action_id != handoff.action_id or gate.executor_id != handoff.executor_id:
        raise ValueError("execution gate identity does not match handoff")
    if not post_snapshot.verified:
        raise ValueError("post-execution resource snapshot must be verified")
    if (
        post_snapshot.provider != gate.provider
        or post_snapshot.account_id != gate.account_id
        or post_snapshot.resource_id != gate.resource_id
    ):
        raise ValueError("post-execution snapshot identity mismatch")
    if _instant(post_snapshot.observed_at) > _instant(
        normalize_utc_timestamp("completed_at", completed_at)
    ):
        raise ValueError("post-execution snapshot cannot postdate completion")

    started = normalize_utc_timestamp("started_at", started_at)
    completed = normalize_utc_timestamp("completed_at", completed_at)
    identity = {
        "schema": 1,
        "handoff_id": handoff.handoff_id,
        "handoff_proof_hash": handoff.proof_hash,
        "gate_id": gate.gate_id,
        "gate_proof_hash": gate.proof_hash,
        "action_id": handoff.action_id,
        "executor_id": handoff.executor_id,
        "outcome": outcome.value,
        "started_at": started,
        "completed_at": completed,
        "pre_resource_state_hash": gate.fresh_resource_state_hash,
        "post_resource_state_hash": post_snapshot.state_hash,
        "post_snapshot_proof_hash": post_snapshot.proof_hash,
        "provider_request_id": provider_request_id,
        "source_hash": normalize_source_hash(source_hash),
        "source_locator": source_locator.strip(),
        "verified": verified,
        "mutation_performed": mutation_performed,
    }
    return CloudRemediationExecutionReceipt(
        receipt_id="cloud-remediation-receipt:" + canonical_hash(identity),
        handoff_id=handoff.handoff_id,
        handoff_proof_hash=handoff.proof_hash,
        gate_id=gate.gate_id,
        gate_proof_hash=gate.proof_hash,
        action_id=handoff.action_id,
        executor_id=handoff.executor_id,
        outcome=outcome,
        started_at=started,
        completed_at=completed,
        pre_resource_state_hash=gate.fresh_resource_state_hash,
        post_resource_state_hash=post_snapshot.state_hash,
        post_snapshot_proof_hash=post_snapshot.proof_hash,
        provider_request_id=provider_request_id,
        source_hash=source_hash,
        source_locator=source_locator,
        verified=verified,
        mutation_performed=mutation_performed,
    )
