"""Governed production incident detection and rollback handoff verification."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from recoveryworks.models import (
    canonical_hash,
    normalize_git_commit_sha,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)
from recoveryworks.release_control import (
    RecoveryWorksReleaseManifest,
    ReleaseEnvironment,
    ReleaseRollbackManifest,
)
from recoveryworks.release_deployment_handoff import (
    DeploymentEnvironmentSnapshot,
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


class ProductionIncidentReason(str, Enum):
    HEALTH_FAILURE = "HEALTH_FAILURE"
    READINESS_FAILURE = "READINESS_FAILURE"
    RELEASE_DRIFT = "RELEASE_DRIFT"
    IMAGE_DRIFT = "IMAGE_DRIFT"
    SOURCE_DRIFT = "SOURCE_DRIFT"
    DEPLOYMENT_CONTRACT_DRIFT = "DEPLOYMENT_CONTRACT_DRIFT"


@dataclass(frozen=True)
class ProductionIncidentAssessment:
    incident_id: str
    environment: ReleaseEnvironment
    expected_release_id: str
    expected_release_proof_hash: str
    observed_snapshot_proof_hash: str
    detected_at: str
    reasons: tuple[ProductionIncidentReason, ...]
    rollback_recommended: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.environment, ReleaseEnvironment):
            raise ValueError("environment must be ReleaseEnvironment")
        object.__setattr__(
            self, "expected_release_id",
            _text("expected_release_id", self.expected_release_id)
        )
        for name in (
            "expected_release_proof_hash",
            "observed_snapshot_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self, "detected_at",
            normalize_utc_timestamp("detected_at", self.detected_at)
        )
        reasons = tuple(sorted(set(self.reasons), key=lambda item: item.value))
        if not reasons:
            raise ValueError("incident assessment requires at least one reason")
        if not all(isinstance(reason, ProductionIncidentReason) for reason in reasons):
            raise ValueError("invalid production incident reason")
        object.__setattr__(self, "reasons", reasons)
        if self.rollback_recommended is not True:
            raise ValueError("incident artifact represents rollback-required incidents")
        expected = "recoveryworks-production-incident:" + canonical_hash(
            self._identity()
        )
        if self.incident_id != expected:
            raise ValueError("incident_id does not bind incident assessment")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "environment": self.environment.value,
            "expected_release_id": self.expected_release_id,
            "expected_release_proof_hash": self.expected_release_proof_hash,
            "observed_snapshot_proof_hash": self.observed_snapshot_proof_hash,
            "detected_at": self.detected_at,
            "reasons": [reason.value for reason in self.reasons],
            "rollback_recommended": True,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "incident_id": self.incident_id,
            "proof_hash": self.proof_hash,
            "state": "ROLLBACK_REVIEW_REQUIRED",
        }


def assess_post_deployment_incident(
    expected_release: RecoveryWorksReleaseManifest,
    snapshot: DeploymentEnvironmentSnapshot,
    *,
    detected_at: str,
) -> ProductionIncidentAssessment:
    if not snapshot.verified:
        raise ValueError("incident assessment requires verified environment snapshot")
    reasons: list[ProductionIncidentReason] = []
    if not snapshot.health_passed:
        reasons.append(ProductionIncidentReason.HEALTH_FAILURE)
    if not snapshot.readiness_passed:
        reasons.append(ProductionIncidentReason.READINESS_FAILURE)
    if (
        snapshot.release_id != expected_release.release_id
        or snapshot.release_proof_hash != expected_release.proof_hash
    ):
        reasons.append(ProductionIncidentReason.RELEASE_DRIFT)
    if (
        snapshot.container_image_ref != expected_release.container_image_ref
        or snapshot.container_image_digest != expected_release.container_image_digest
    ):
        reasons.append(ProductionIncidentReason.IMAGE_DRIFT)
    if snapshot.source_commit != expected_release.source_commit:
        reasons.append(ProductionIncidentReason.SOURCE_DRIFT)
    if (
        snapshot.production_deployment_proof_hash
        != expected_release.production_deployment_proof_hash
    ):
        reasons.append(ProductionIncidentReason.DEPLOYMENT_CONTRACT_DRIFT)
    if not reasons:
        raise ValueError("verified environment snapshot does not indicate an incident")
    identity = {
        "schema": 1,
        "environment": snapshot.environment.value,
        "expected_release_id": expected_release.release_id,
        "expected_release_proof_hash": expected_release.proof_hash,
        "observed_snapshot_proof_hash": snapshot.proof_hash,
        "detected_at": normalize_utc_timestamp("detected_at", detected_at),
        "reasons": sorted(reason.value for reason in reasons),
        "rollback_recommended": True,
    }
    return ProductionIncidentAssessment(
        incident_id="recoveryworks-production-incident:" + canonical_hash(identity),
        environment=snapshot.environment,
        expected_release_id=expected_release.release_id,
        expected_release_proof_hash=expected_release.proof_hash,
        observed_snapshot_proof_hash=snapshot.proof_hash,
        detected_at=detected_at,
        reasons=tuple(reasons),
        rollback_recommended=True,
    )


@dataclass(frozen=True)
class RollbackApproval:
    approval_id: str
    incident_id: str
    incident_proof_hash: str
    rollback_manifest_proof_hash: str
    target_release_id: str
    target_release_proof_hash: str
    approver_id: str
    role: str
    approved_at: str

    def __post_init__(self) -> None:
        for name in ("incident_id", "target_release_id", "approver_id", "role"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "incident_proof_hash",
            "rollback_manifest_proof_hash",
            "target_release_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self, "approved_at",
            normalize_utc_timestamp("approved_at", self.approved_at)
        )
        expected = "recoveryworks-rollback-approval:" + canonical_hash(
            self._identity()
        )
        if self.approval_id != expected:
            raise ValueError("approval_id does not bind rollback approval")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "incident_id": self.incident_id,
            "incident_proof_hash": self.incident_proof_hash,
            "rollback_manifest_proof_hash": self.rollback_manifest_proof_hash,
            "target_release_id": self.target_release_id,
            "target_release_proof_hash": self.target_release_proof_hash,
            "approver_id": self.approver_id,
            "role": self.role,
            "approved_at": self.approved_at,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def approve_production_rollback(
    incident: ProductionIncidentAssessment,
    rollback: ReleaseRollbackManifest,
    target_release: RecoveryWorksReleaseManifest,
    *,
    approver_id: str,
    role: str,
    approved_at: str,
) -> RollbackApproval:
    if rollback.release_id != incident.expected_release_id:
        raise ValueError("rollback manifest current release mismatch")
    if rollback.release_proof_hash != incident.expected_release_proof_hash:
        raise ValueError("rollback manifest current release proof mismatch")
    if rollback.target_release_id != target_release.release_id:
        raise ValueError("rollback target release mismatch")
    if rollback.target_release_proof_hash != target_release.proof_hash:
        raise ValueError("rollback target release proof mismatch")
    identity = {
        "schema": 1,
        "incident_id": incident.incident_id,
        "incident_proof_hash": incident.proof_hash,
        "rollback_manifest_proof_hash": rollback.proof_hash,
        "target_release_id": target_release.release_id,
        "target_release_proof_hash": target_release.proof_hash,
        "approver_id": _text("approver_id", approver_id),
        "role": _text("role", role),
        "approved_at": normalize_utc_timestamp("approved_at", approved_at),
    }
    return RollbackApproval(
        approval_id="recoveryworks-rollback-approval:" + canonical_hash(identity),
        incident_id=incident.incident_id,
        incident_proof_hash=incident.proof_hash,
        rollback_manifest_proof_hash=rollback.proof_hash,
        target_release_id=target_release.release_id,
        target_release_proof_hash=target_release.proof_hash,
        approver_id=approver_id,
        role=role,
        approved_at=approved_at,
    )


@dataclass(frozen=True)
class RollbackDeploymentHandoff:
    handoff_id: str
    incident_id: str
    incident_proof_hash: str
    rollback_manifest_proof_hash: str
    target_release_id: str
    target_release_proof_hash: str
    target_image_ref: str
    target_image_digest: str
    target_source_commit: str
    target_deployment_proof_hash: str
    environment: ReleaseEnvironment
    approval_hashes: tuple[str, ...]
    approver_ids: tuple[str, ...]
    deployer_id: str
    issued_at: str
    expires_at: str
    external_rollback_authorized: bool = True
    rollback_performed_by_recoveryos: bool = False

    def __post_init__(self) -> None:
        for name in ("incident_id", "target_release_id", "deployer_id"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "incident_proof_hash",
            "rollback_manifest_proof_hash",
            "target_release_proof_hash",
            "target_image_digest",
            "target_deployment_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self, "target_source_commit",
            normalize_git_commit_sha("target_source_commit", self.target_source_commit)
        )
        if not isinstance(self.environment, ReleaseEnvironment):
            raise ValueError("environment must be ReleaseEnvironment")
        if len(set(self.approver_ids)) != len(self.approver_ids):
            raise ValueError("rollback approvers must be distinct")
        required = 2 if self.environment is ReleaseEnvironment.PRODUCTION else 1
        if len(self.approver_ids) < required:
            raise ValueError(
                f"{self.environment.value} rollback requires {required} approval(s)"
            )
        issued = normalize_utc_timestamp("issued_at", self.issued_at)
        expires = normalize_utc_timestamp("expires_at", self.expires_at)
        if _instant(expires) <= _instant(issued):
            raise ValueError("rollback handoff must expire after issuance")
        object.__setattr__(self, "issued_at", issued)
        object.__setattr__(self, "expires_at", expires)
        if self.external_rollback_authorized is not True:
            raise ValueError("rollback handoff must carry explicit authorization")
        if self.rollback_performed_by_recoveryos:
            raise ValueError("RecoveryOS cannot claim it performed rollback")
        expected = "recoveryworks-rollback-handoff:" + canonical_hash(
            self._identity()
        )
        if self.handoff_id != expected:
            raise ValueError("handoff_id does not bind rollback handoff")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "incident_id": self.incident_id,
            "incident_proof_hash": self.incident_proof_hash,
            "rollback_manifest_proof_hash": self.rollback_manifest_proof_hash,
            "target_release_id": self.target_release_id,
            "target_release_proof_hash": self.target_release_proof_hash,
            "target_image_ref": self.target_image_ref,
            "target_image_digest": self.target_image_digest,
            "target_source_commit": self.target_source_commit,
            "target_deployment_proof_hash": self.target_deployment_proof_hash,
            "environment": self.environment.value,
            "approval_hashes": list(self.approval_hashes),
            "approver_ids": list(self.approver_ids),
            "deployer_id": self.deployer_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "external_rollback_authorized": True,
            "rollback_performed_by_recoveryos": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "handoff_id": self.handoff_id,
            "proof_hash": self.proof_hash,
            "state": "READY_FOR_SEPARATE_ROLLBACK_DEPLOYER",
        }


def prepare_rollback_handoff(
    incident: ProductionIncidentAssessment,
    rollback: ReleaseRollbackManifest,
    target_release: RecoveryWorksReleaseManifest,
    approvals: tuple[RollbackApproval, ...],
    *,
    deployer_id: str,
    issued_at: str,
    expires_at: str,
) -> RollbackDeploymentHandoff:
    for approval in approvals:
        if approval.incident_id != incident.incident_id:
            raise ValueError("rollback approval incident mismatch")
        if approval.incident_proof_hash != incident.proof_hash:
            raise ValueError("rollback approval incident proof mismatch")
        if approval.rollback_manifest_proof_hash != rollback.proof_hash:
            raise ValueError("rollback approval manifest mismatch")
        if approval.target_release_id != target_release.release_id:
            raise ValueError("rollback approval target mismatch")
        if approval.target_release_proof_hash != target_release.proof_hash:
            raise ValueError("rollback approval target proof mismatch")
    approver_ids = tuple(sorted(approval.approver_id for approval in approvals))
    approval_hashes = tuple(sorted(approval.proof_hash for approval in approvals))
    required = 2 if incident.environment is ReleaseEnvironment.PRODUCTION else 1
    if len(set(approver_ids)) < required:
        raise ValueError(
            f"{incident.environment.value} rollback requires {required} distinct approval(s)"
        )
    if rollback.target_release_id != target_release.release_id:
        raise ValueError("rollback manifest target release mismatch")
    if rollback.target_release_proof_hash != target_release.proof_hash:
        raise ValueError("rollback manifest target release proof mismatch")
    identity = {
        "schema": 1,
        "incident_id": incident.incident_id,
        "incident_proof_hash": incident.proof_hash,
        "rollback_manifest_proof_hash": rollback.proof_hash,
        "target_release_id": target_release.release_id,
        "target_release_proof_hash": target_release.proof_hash,
        "target_image_ref": target_release.container_image_ref,
        "target_image_digest": target_release.container_image_digest,
        "target_source_commit": target_release.source_commit,
        "target_deployment_proof_hash":
            target_release.production_deployment_proof_hash,
        "environment": incident.environment.value,
        "approval_hashes": list(approval_hashes),
        "approver_ids": list(approver_ids),
        "deployer_id": _text("deployer_id", deployer_id),
        "issued_at": normalize_utc_timestamp("issued_at", issued_at),
        "expires_at": normalize_utc_timestamp("expires_at", expires_at),
        "external_rollback_authorized": True,
        "rollback_performed_by_recoveryos": False,
    }
    return RollbackDeploymentHandoff(
        handoff_id="recoveryworks-rollback-handoff:" + canonical_hash(identity),
        incident_id=incident.incident_id,
        incident_proof_hash=incident.proof_hash,
        rollback_manifest_proof_hash=rollback.proof_hash,
        target_release_id=target_release.release_id,
        target_release_proof_hash=target_release.proof_hash,
        target_image_ref=target_release.container_image_ref,
        target_image_digest=target_release.container_image_digest,
        target_source_commit=target_release.source_commit,
        target_deployment_proof_hash=
            target_release.production_deployment_proof_hash,
        environment=incident.environment,
        approval_hashes=approval_hashes,
        approver_ids=approver_ids,
        deployer_id=deployer_id,
        issued_at=issued_at,
        expires_at=expires_at,
        external_rollback_authorized=True,
        rollback_performed_by_recoveryos=False,
    )


@dataclass(frozen=True)
class ExternalRollbackReceipt:
    receipt_id: str
    handoff_id: str
    handoff_proof_hash: str
    deployer_id: str
    rolled_back_at: str
    target_release_id: str
    target_release_proof_hash: str
    target_image_ref: str
    target_image_digest: str
    target_source_commit: str
    target_deployment_proof_hash: str
    external_deployment_id: str
    source_hash: str
    source_locator: str
    verified: bool

    def __post_init__(self) -> None:
        for name in (
            "handoff_id", "deployer_id", "target_release_id",
            "external_deployment_id", "source_locator",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "handoff_proof_hash", "target_release_proof_hash",
            "target_image_digest", "target_deployment_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self, "target_source_commit",
            normalize_git_commit_sha("target_source_commit", self.target_source_commit)
        )
        object.__setattr__(
            self, "rolled_back_at",
            normalize_utc_timestamp("rolled_back_at", self.rolled_back_at)
        )
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if self.verified is not True:
            raise ValueError("rollback receipt must be externally verified")
        expected = "recoveryworks-rollback-receipt:" + canonical_hash(
            self._identity()
        )
        if self.receipt_id != expected:
            raise ValueError("receipt_id does not bind rollback receipt")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "handoff_id": self.handoff_id,
            "handoff_proof_hash": self.handoff_proof_hash,
            "deployer_id": self.deployer_id,
            "rolled_back_at": self.rolled_back_at,
            "target_release_id": self.target_release_id,
            "target_release_proof_hash": self.target_release_proof_hash,
            "target_image_ref": self.target_image_ref,
            "target_image_digest": self.target_image_digest,
            "target_source_commit": self.target_source_commit,
            "target_deployment_proof_hash": self.target_deployment_proof_hash,
            "external_deployment_id": self.external_deployment_id,
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": True,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


@dataclass(frozen=True)
class ValidatedRollbackReceipt:
    receipt: ExternalRollbackReceipt
    post_rollback_snapshot_proof_hash: str

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "rollback_receipt_proof_hash": self.receipt.proof_hash,
            "post_rollback_snapshot_proof_hash":
                self.post_rollback_snapshot_proof_hash,
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            "rollback_receipt_proof_hash": self.receipt.proof_hash,
            "post_rollback_snapshot_proof_hash":
                self.post_rollback_snapshot_proof_hash,
            "proof_hash": self.proof_hash,
            "state": "ROLLBACK_VERIFIED",
        }


def validate_external_rollback(
    handoff: RollbackDeploymentHandoff,
    receipt: ExternalRollbackReceipt,
    post_snapshot: DeploymentEnvironmentSnapshot,
) -> ValidatedRollbackReceipt:
    if receipt.handoff_id != handoff.handoff_id:
        raise ValueError("rollback receipt handoff id mismatch")
    if receipt.handoff_proof_hash != handoff.proof_hash:
        raise ValueError("rollback receipt does not bind exact handoff")
    if receipt.deployer_id != handoff.deployer_id:
        raise ValueError("rollback receipt deployer mismatch")
    rolled = _instant(receipt.rolled_back_at)
    if rolled < _instant(handoff.issued_at) or rolled > _instant(handoff.expires_at):
        raise ValueError("rollback occurred outside authorized handoff window")
    for name in (
        "target_release_id", "target_release_proof_hash", "target_image_ref",
        "target_image_digest", "target_source_commit", "target_deployment_proof_hash",
    ):
        if getattr(receipt, name) != getattr(handoff, name):
            raise ValueError(f"rollback receipt {name} mismatch")
    if not post_snapshot.verified:
        raise ValueError("post-rollback environment snapshot must be verified")
    if post_snapshot.environment is not handoff.environment:
        raise ValueError("post-rollback environment mismatch")
    mapping = {
        "release_id": "target_release_id",
        "release_proof_hash": "target_release_proof_hash",
        "container_image_ref": "target_image_ref",
        "container_image_digest": "target_image_digest",
        "source_commit": "target_source_commit",
        "production_deployment_proof_hash": "target_deployment_proof_hash",
    }
    for snapshot_name, handoff_name in mapping.items():
        if getattr(post_snapshot, snapshot_name) != getattr(handoff, handoff_name):
            raise ValueError(f"post-rollback {snapshot_name} mismatch")
    if not post_snapshot.health_passed or not post_snapshot.readiness_passed:
        raise ValueError("post-rollback health/readiness verification failed")
    if _instant(post_snapshot.observed_at) < rolled:
        raise ValueError("post-rollback snapshot predates rollback receipt")
    return ValidatedRollbackReceipt(
        receipt=receipt,
        post_rollback_snapshot_proof_hash=post_snapshot.proof_hash,
    )
