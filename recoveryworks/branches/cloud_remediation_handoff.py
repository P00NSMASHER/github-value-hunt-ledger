"""Governed external-executor handoff and execution-receipt validation.

RecoveryOS still performs no provider mutation here. This module binds an exact
dry-run plan to explicit customer/executor authorization, requires a fresh
verified state recheck immediately before handoff, and validates a downstream
execution receipt against verified post-state evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Mapping

from recoveryworks.models import (
    canonical_hash,
    freeze_json,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)
from .cloud_remediation import CloudRemediationApproval
from .cloud_remediation_executor import (
    CloudRemediationDryRunPlan,
    CloudResourceSnapshot,
)


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(
        normalize_utc_timestamp("timestamp", value).replace("Z", "+00:00")
    )


@dataclass(frozen=True)
class CloudRemediationExecutionPolicy:
    max_recheck_age_seconds: int = 300
    handoff_ttl_seconds: int = 300

    def __post_init__(self) -> None:
        for name in ("max_recheck_age_seconds", "handoff_ttl_seconds"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class CloudRemediationExecutionAuthorization:
    authorization_id: str
    action_id: str
    dry_run_plan_proof_hash: str
    approval_hash: str
    customer_authorization_id: str
    authorizer_id: str
    executor_id: str
    authorized_at: str
    expires_at: str

    def __post_init__(self) -> None:
        for name in (
            "action_id",
            "customer_authorization_id",
            "authorizer_id",
            "executor_id",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in ("dry_run_plan_proof_hash", "approval_hash"):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        authorized = normalize_utc_timestamp("authorized_at", self.authorized_at)
        expires = normalize_utc_timestamp("expires_at", self.expires_at)
        if _instant(expires) <= _instant(authorized):
            raise ValueError("execution authorization must expire after authorization")
        object.__setattr__(self, "authorized_at", authorized)
        object.__setattr__(self, "expires_at", expires)
        expected = "cloud-remediation-execution-auth:" + canonical_hash(
            self._identity()
        )
        if self.authorization_id != expected:
            raise ValueError(
                "authorization_id does not bind the execution authorization"
            )

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "action_id": self.action_id,
            "dry_run_plan_proof_hash": self.dry_run_plan_proof_hash,
            "approval_hash": self.approval_hash,
            "customer_authorization_id": self.customer_authorization_id,
            "authorizer_id": self.authorizer_id,
            "executor_id": self.executor_id,
            "authorized_at": self.authorized_at,
            "expires_at": self.expires_at,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {**self._identity(), "authorization_id": self.authorization_id,
                "proof_hash": self.proof_hash}


def authorize_cloud_remediation_execution(
    dry_run: CloudRemediationDryRunPlan,
    approval: CloudRemediationApproval,
    *,
    authorizer_id: str,
    executor_id: str,
    authorized_at: str,
    expires_at: str,
) -> CloudRemediationExecutionAuthorization:
    if dry_run.approval_hash != approval.proof_hash:
        raise ValueError("dry-run plan does not bind the supplied approval")
    if dry_run.action_id not in approval.approved_action_ids:
        raise ValueError("dry-run action is not customer-approved")
    authorized_at = normalize_utc_timestamp("authorized_at", authorized_at)
    expires_at = normalize_utc_timestamp("expires_at", expires_at)
    identity = {
        "schema": 1,
        "action_id": dry_run.action_id,
        "dry_run_plan_proof_hash": dry_run.proof_hash,
        "approval_hash": approval.proof_hash,
        "customer_authorization_id": approval.customer_authorization_id,
        "authorizer_id": _text("authorizer_id", authorizer_id),
        "executor_id": _text("executor_id", executor_id),
        "authorized_at": authorized_at,
        "expires_at": expires_at,
    }
    return CloudRemediationExecutionAuthorization(
        authorization_id="cloud-remediation-execution-auth:"
        + canonical_hash(identity),
        action_id=dry_run.action_id,
        dry_run_plan_proof_hash=dry_run.proof_hash,
        approval_hash=approval.proof_hash,
        customer_authorization_id=approval.customer_authorization_id,
        authorizer_id=authorizer_id,
        executor_id=executor_id,
        authorized_at=authorized_at,
        expires_at=expires_at,
    )


@dataclass(frozen=True)
class CloudRemediationExecutionHandoff:
    handoff_id: str
    action_id: str
    executor_id: str
    dry_run_plan_proof_hash: str
    execution_authorization_proof_hash: str
    customer_authorization_id: str
    provider: str
    account_id: str
    resource_id: str
    recheck_snapshot_proof_hash: str
    recheck_state_hash: str
    prepared_at: str
    expires_at: str
    parameters: Mapping[str, Any]
    external_execution_authorized: bool = True
    mutation_performed_by_recoveryos: bool = False

    def __post_init__(self) -> None:
        for name in (
            "action_id",
            "executor_id",
            "customer_authorization_id",
            "provider",
            "account_id",
            "resource_id",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "dry_run_plan_proof_hash",
            "execution_authorization_proof_hash",
            "recheck_snapshot_proof_hash",
            "recheck_state_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        prepared = normalize_utc_timestamp("prepared_at", self.prepared_at)
        expires = normalize_utc_timestamp("expires_at", self.expires_at)
        if _instant(expires) <= _instant(prepared):
            raise ValueError("handoff must expire after preparation")
        object.__setattr__(self, "prepared_at", prepared)
        object.__setattr__(self, "expires_at", expires)
        object.__setattr__(
            self, "parameters", freeze_json(self.parameters, name="parameters")
        )
        if self.external_execution_authorized is not True:
            raise ValueError("execution handoff must represent explicit authorization")
        if self.mutation_performed_by_recoveryos:
            raise ValueError("RecoveryOS cannot claim it performed provider mutation")
        expected = "cloud-remediation-handoff:" + canonical_hash(self._identity())
        if self.handoff_id != expected:
            raise ValueError("handoff_id does not bind the handoff payload")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "action_id": self.action_id,
            "executor_id": self.executor_id,
            "dry_run_plan_proof_hash": self.dry_run_plan_proof_hash,
            "execution_authorization_proof_hash":
                self.execution_authorization_proof_hash,
            "customer_authorization_id": self.customer_authorization_id,
            "provider": self.provider,
            "account_id": self.account_id,
            "resource_id": self.resource_id,
            "recheck_snapshot_proof_hash": self.recheck_snapshot_proof_hash,
            "recheck_state_hash": self.recheck_state_hash,
            "prepared_at": self.prepared_at,
            "expires_at": self.expires_at,
            "parameters": dict(self.parameters),
            "external_execution_authorized": True,
            "mutation_performed_by_recoveryos": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "handoff_id": self.handoff_id,
            "proof_hash": self.proof_hash,
            "state": "READY_FOR_SEPARATELY_AUTHORIZED_EXECUTOR",
        }


def prepare_cloud_remediation_execution_handoff(
    dry_run: CloudRemediationDryRunPlan,
    authorization: CloudRemediationExecutionAuthorization,
    recheck_snapshot: CloudResourceSnapshot,
    *,
    prepared_at: str,
    policy: CloudRemediationExecutionPolicy = CloudRemediationExecutionPolicy(),
) -> CloudRemediationExecutionHandoff:
    if authorization.action_id != dry_run.action_id:
        raise ValueError("execution authorization action mismatch")
    if authorization.dry_run_plan_proof_hash != dry_run.proof_hash:
        raise ValueError("execution authorization does not bind the dry-run plan")
    prepared_at = normalize_utc_timestamp("prepared_at", prepared_at)
    prepared = _instant(prepared_at)
    if prepared < _instant(authorization.authorized_at):
        raise ValueError("handoff cannot predate execution authorization")
    if prepared >= _instant(authorization.expires_at):
        raise ValueError("execution authorization expired before handoff")

    if not recheck_snapshot.verified:
        raise ValueError("fresh resource recheck must be independently verified")
    if (
        recheck_snapshot.provider != dry_run.provider
        or recheck_snapshot.account_id != dry_run.account_id
        or recheck_snapshot.resource_id != dry_run.resource_id
    ):
        raise ValueError("fresh resource recheck identity mismatch")
    if recheck_snapshot.state_hash != dry_run.resource_state_hash:
        raise ValueError("resource state changed since dry-run validation")

    observed = _instant(recheck_snapshot.observed_at)
    if observed > prepared:
        raise ValueError("resource recheck cannot be observed after handoff preparation")
    age_seconds = int((prepared - observed).total_seconds())
    if age_seconds > policy.max_recheck_age_seconds:
        raise ValueError("resource recheck is too stale for execution handoff")

    expiry = min(
        _instant(authorization.expires_at),
        prepared + timedelta(seconds=policy.handoff_ttl_seconds),
    )
    expires_at = expiry.astimezone(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")
    identity = {
        "schema": 1,
        "action_id": dry_run.action_id,
        "executor_id": authorization.executor_id,
        "dry_run_plan_proof_hash": dry_run.proof_hash,
        "execution_authorization_proof_hash": authorization.proof_hash,
        "customer_authorization_id": authorization.customer_authorization_id,
        "provider": dry_run.provider,
        "account_id": dry_run.account_id,
        "resource_id": dry_run.resource_id,
        "recheck_snapshot_proof_hash": recheck_snapshot.proof_hash,
        "recheck_state_hash": recheck_snapshot.state_hash,
        "prepared_at": prepared_at,
        "expires_at": expires_at,
        "parameters": dict(dry_run.parameters),
        "external_execution_authorized": True,
        "mutation_performed_by_recoveryos": False,
    }
    return CloudRemediationExecutionHandoff(
        handoff_id="cloud-remediation-handoff:" + canonical_hash(identity),
        action_id=dry_run.action_id,
        executor_id=authorization.executor_id,
        dry_run_plan_proof_hash=dry_run.proof_hash,
        execution_authorization_proof_hash=authorization.proof_hash,
        customer_authorization_id=authorization.customer_authorization_id,
        provider=dry_run.provider,
        account_id=dry_run.account_id,
        resource_id=dry_run.resource_id,
        recheck_snapshot_proof_hash=recheck_snapshot.proof_hash,
        recheck_state_hash=recheck_snapshot.state_hash,
        prepared_at=prepared_at,
        expires_at=expires_at,
        parameters=dry_run.parameters,
        external_execution_authorized=True,
        mutation_performed_by_recoveryos=False,
    )


class CloudRemediationExecutionStatus(str, Enum):
    APPLIED = "APPLIED"
    NOOP = "NOOP"
    FAILED = "FAILED"


@dataclass(frozen=True)
class CloudRemediationExecutionReceipt:
    receipt_id: str
    handoff_id: str
    handoff_proof_hash: str
    action_id: str
    executor_id: str
    executed_at: str
    status: CloudRemediationExecutionStatus
    before_state_hash: str
    after_state_hash: str
    provider_request_id: str | None
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        for name in (
            "handoff_id",
            "action_id",
            "executor_id",
            "source_locator",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "handoff_proof_hash",
            "before_state_hash",
            "after_state_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self, "executed_at",
            normalize_utc_timestamp("executed_at", self.executed_at),
        )
        if not isinstance(self.status, CloudRemediationExecutionStatus):
            raise ValueError("status must be a CloudRemediationExecutionStatus")
        if self.provider_request_id is not None:
            object.__setattr__(
                self,
                "provider_request_id",
                _text("provider_request_id", self.provider_request_id),
            )
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        object.__setattr__(
            self, "metadata", freeze_json(self.metadata, name="metadata")
        )
        expected = "cloud-remediation-execution-receipt:" + canonical_hash(
            self._identity()
        )
        if self.receipt_id != expected:
            raise ValueError("receipt_id does not bind the execution receipt")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "handoff_id": self.handoff_id,
            "handoff_proof_hash": self.handoff_proof_hash,
            "action_id": self.action_id,
            "executor_id": self.executor_id,
            "executed_at": self.executed_at,
            "status": self.status.value,
            "before_state_hash": self.before_state_hash,
            "after_state_hash": self.after_state_hash,
            "provider_request_id": self.provider_request_id,
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": self.verified,
            "metadata": dict(self.metadata),
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


@dataclass(frozen=True)
class ValidatedCloudRemediationReceipt:
    receipt: CloudRemediationExecutionReceipt
    post_snapshot_proof_hash: str
    post_state_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "post_snapshot_proof_hash",
            normalize_sha256(
                "post_snapshot_proof_hash", self.post_snapshot_proof_hash
            ),
        )
        object.__setattr__(
            self, "post_state_hash", normalize_sha256(
                "post_state_hash", self.post_state_hash
            )
        )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "receipt_proof_hash": self.receipt.proof_hash,
            "post_snapshot_proof_hash": self.post_snapshot_proof_hash,
            "post_state_hash": self.post_state_hash,
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            "receipt": {
                **self.receipt._identity(),
                "receipt_id": self.receipt.receipt_id,
                "proof_hash": self.receipt.proof_hash,
            },
            "post_snapshot_proof_hash": self.post_snapshot_proof_hash,
            "post_state_hash": self.post_state_hash,
            "proof_hash": self.proof_hash,
            "state": "EXECUTION_RECEIPT_VERIFIED",
        }


def validate_cloud_remediation_execution_receipt(
    handoff: CloudRemediationExecutionHandoff,
    receipt: CloudRemediationExecutionReceipt,
    post_snapshot: CloudResourceSnapshot,
) -> ValidatedCloudRemediationReceipt:
    if receipt.handoff_id != handoff.handoff_id:
        raise ValueError("execution receipt handoff id mismatch")
    if receipt.handoff_proof_hash != handoff.proof_hash:
        raise ValueError("execution receipt does not bind the exact handoff")
    if receipt.action_id != handoff.action_id:
        raise ValueError("execution receipt action mismatch")
    if receipt.executor_id != handoff.executor_id:
        raise ValueError("execution receipt executor mismatch")
    executed = _instant(receipt.executed_at)
    if executed < _instant(handoff.prepared_at) or executed > _instant(
        handoff.expires_at
    ):
        raise ValueError("execution receipt is outside the authorized handoff window")
    if not receipt.verified:
        raise ValueError("execution receipt must be externally verified")
    if receipt.before_state_hash != handoff.recheck_state_hash:
        raise ValueError("execution receipt before-state mismatch")

    if not post_snapshot.verified:
        raise ValueError("post-execution resource snapshot must be verified")
    if (
        post_snapshot.provider != handoff.provider
        or post_snapshot.account_id != handoff.account_id
        or post_snapshot.resource_id != handoff.resource_id
    ):
        raise ValueError("post-execution resource identity mismatch")
    if receipt.after_state_hash != post_snapshot.state_hash:
        raise ValueError("execution receipt after-state does not match post snapshot")

    if receipt.status is CloudRemediationExecutionStatus.APPLIED:
        if receipt.before_state_hash == receipt.after_state_hash:
            raise ValueError("APPLIED receipt must show a changed resource state")
        if not receipt.provider_request_id:
            raise ValueError("APPLIED receipt requires a provider request id")
    elif receipt.status is CloudRemediationExecutionStatus.NOOP:
        if receipt.before_state_hash != receipt.after_state_hash:
            raise ValueError("NOOP receipt cannot claim a changed resource state")

    return ValidatedCloudRemediationReceipt(
        receipt=receipt,
        post_snapshot_proof_hash=post_snapshot.proof_hash,
        post_state_hash=post_snapshot.state_hash,
    )
