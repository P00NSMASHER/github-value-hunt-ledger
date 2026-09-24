"""Immutable RecoveryWorks release and environment-promotion gates.

This is a release-control plane only. It binds code/build/image/deployment
proofs, approvals, validation checks, and rollback targets. It never pushes an
image, changes an environment, starts a container, or deploys infrastructure.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
from pathlib import Path
import re
from typing import Any

from recoveryworks.container_build import ContainerBuildManifest
from recoveryworks.models import (
    canonical_hash,
    normalize_git_commit_sha,
    normalize_sha256,
    normalize_utc_timestamp,
)
from recoveryworks.private_io import atomic_private_write
from recoveryworks.production_deployment import (
    ProductionCheckResult,
    ProductionDeploymentContract,
)


_IMAGE_RE = re.compile(r"^[^@\s]+@sha256:([0-9a-f]{64})$")


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


class ReleaseEnvironment(str, Enum):
    DEVELOPMENT = "DEVELOPMENT"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"


@dataclass(frozen=True)
class RecoveryWorksReleaseManifest:
    release_id: str
    version: str
    source_commit: str
    container_build_manifest_proof_hash: str
    container_image_ref: str
    container_image_digest: str
    production_deployment_proof_hash: str
    created_at: str
    immutable: bool = True
    published: bool = False
    deployed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "version", _text("version", self.version))
        object.__setattr__(
            self,
            "source_commit",
            normalize_git_commit_sha("source_commit", self.source_commit),
        )
        object.__setattr__(
            self,
            "container_build_manifest_proof_hash",
            normalize_sha256(
                "container_build_manifest_proof_hash",
                self.container_build_manifest_proof_hash,
            ),
        )
        match = _IMAGE_RE.fullmatch(self.container_image_ref)
        if match is None:
            raise ValueError("release container image must be digest pinned")
        digest = normalize_sha256("container_image_digest", self.container_image_digest)
        if match.group(1) != digest:
            raise ValueError("container image ref/digest mismatch")
        object.__setattr__(self, "container_image_digest", digest)
        object.__setattr__(
            self,
            "production_deployment_proof_hash",
            normalize_sha256(
                "production_deployment_proof_hash",
                self.production_deployment_proof_hash,
            ),
        )
        object.__setattr__(
            self,
            "created_at",
            normalize_utc_timestamp("created_at", self.created_at),
        )
        if self.immutable is not True:
            raise ValueError("release manifest must be immutable")
        if self.published or self.deployed:
            raise ValueError("step 15a cannot publish or deploy releases")
        expected = "recoveryworks-release:" + canonical_hash(self._identity())
        if self.release_id != expected:
            raise ValueError("release_id does not bind release manifest")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "version": self.version,
            "source_commit": self.source_commit,
            "container_build_manifest_proof_hash":
                self.container_build_manifest_proof_hash,
            "container_image_ref": self.container_image_ref,
            "container_image_digest": self.container_image_digest,
            "production_deployment_proof_hash":
                self.production_deployment_proof_hash,
            "created_at": self.created_at,
            "immutable": True,
            "published": False,
            "deployed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "release_id": self.release_id,
            "proof_hash": self.proof_hash,
            "state": "RELEASE_CANDIDATE_NOT_DEPLOYED",
        }


def build_release_manifest(
    *,
    version: str,
    build_manifest: ContainerBuildManifest,
    deployment: ProductionDeploymentContract,
    container_image_ref: str,
    created_at: str,
) -> RecoveryWorksReleaseManifest:
    if deployment.service.image_ref != container_image_ref:
        raise ValueError(
            "release image must exactly match production deployment image"
        )
    match = _IMAGE_RE.fullmatch(container_image_ref)
    if match is None:
        raise ValueError("release image must be digest pinned")
    identity = {
        "schema": 1,
        "version": _text("version", version),
        "source_commit": build_manifest.source_commit,
        "container_build_manifest_proof_hash": build_manifest.proof_hash,
        "container_image_ref": container_image_ref,
        "container_image_digest": match.group(1),
        "production_deployment_proof_hash": deployment.proof_hash,
        "created_at": normalize_utc_timestamp("created_at", created_at),
        "immutable": True,
        "published": False,
        "deployed": False,
    }
    return RecoveryWorksReleaseManifest(
        release_id="recoveryworks-release:" + canonical_hash(identity),
        version=version,
        source_commit=build_manifest.source_commit,
        container_build_manifest_proof_hash=build_manifest.proof_hash,
        container_image_ref=container_image_ref,
        container_image_digest=match.group(1),
        production_deployment_proof_hash=deployment.proof_hash,
        created_at=created_at,
        immutable=True,
        published=False,
        deployed=False,
    )


@dataclass(frozen=True)
class ReleaseRollbackManifest:
    rollback_id: str
    release_id: str
    release_proof_hash: str
    target_release_id: str
    target_release_proof_hash: str
    target_image_ref: str
    target_source_commit: str
    reason: str
    created_at: str
    rollback_executed: bool = False

    def __post_init__(self) -> None:
        for name in ("release_id", "target_release_id", "reason"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        if self.release_id == self.target_release_id:
            raise ValueError("rollback target must be a different release")
        for name in ("release_proof_hash", "target_release_proof_hash"):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        if _IMAGE_RE.fullmatch(self.target_image_ref) is None:
            raise ValueError("rollback target image must be digest pinned")
        object.__setattr__(
            self,
            "target_source_commit",
            normalize_git_commit_sha(
                "target_source_commit", self.target_source_commit
            ),
        )
        object.__setattr__(
            self,
            "created_at",
            normalize_utc_timestamp("created_at", self.created_at),
        )
        if self.rollback_executed:
            raise ValueError("step 15a cannot execute rollback")
        expected = "recoveryworks-rollback:" + canonical_hash(self._identity())
        if self.rollback_id != expected:
            raise ValueError("rollback_id does not bind rollback manifest")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "target_release_id": self.target_release_id,
            "target_release_proof_hash": self.target_release_proof_hash,
            "target_image_ref": self.target_image_ref,
            "target_source_commit": self.target_source_commit,
            "reason": self.reason,
            "created_at": self.created_at,
            "rollback_executed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_rollback_manifest(
    release: RecoveryWorksReleaseManifest,
    target: RecoveryWorksReleaseManifest,
    *,
    reason: str,
    created_at: str,
) -> ReleaseRollbackManifest:
    identity = {
        "schema": 1,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "target_release_id": target.release_id,
        "target_release_proof_hash": target.proof_hash,
        "target_image_ref": target.container_image_ref,
        "target_source_commit": target.source_commit,
        "reason": _text("reason", reason),
        "created_at": normalize_utc_timestamp("created_at", created_at),
        "rollback_executed": False,
    }
    return ReleaseRollbackManifest(
        rollback_id="recoveryworks-rollback:" + canonical_hash(identity),
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        target_release_id=target.release_id,
        target_release_proof_hash=target.proof_hash,
        target_image_ref=target.container_image_ref,
        target_source_commit=target.source_commit,
        reason=reason,
        created_at=created_at,
        rollback_executed=False,
    )


@dataclass(frozen=True)
class ReleaseApprovalArtifact:
    approval_id: str
    release_id: str
    release_proof_hash: str
    environment: ReleaseEnvironment
    approver_id: str
    role: str
    approved_at: str

    def __post_init__(self) -> None:
        for name in ("release_id", "approver_id", "role"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        object.__setattr__(
            self,
            "release_proof_hash",
            normalize_sha256("release_proof_hash", self.release_proof_hash),
        )
        if not isinstance(self.environment, ReleaseEnvironment):
            raise ValueError("environment must be ReleaseEnvironment")
        object.__setattr__(
            self,
            "approved_at",
            normalize_utc_timestamp("approved_at", self.approved_at),
        )
        expected = "recoveryworks-release-approval:" + canonical_hash(
            self._identity()
        )
        if self.approval_id != expected:
            raise ValueError("approval_id does not bind approval")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "environment": self.environment.value,
            "approver_id": self.approver_id,
            "role": self.role,
            "approved_at": self.approved_at,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def approve_release(
    release: RecoveryWorksReleaseManifest,
    *,
    environment: ReleaseEnvironment,
    approver_id: str,
    role: str,
    approved_at: str,
) -> ReleaseApprovalArtifact:
    identity = {
        "schema": 1,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "environment": environment.value,
        "approver_id": _text("approver_id", approver_id),
        "role": _text("role", role),
        "approved_at": normalize_utc_timestamp("approved_at", approved_at),
    }
    return ReleaseApprovalArtifact(
        approval_id="recoveryworks-release-approval:" + canonical_hash(identity),
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        environment=environment,
        approver_id=approver_id,
        role=role,
        approved_at=approved_at,
    )


@dataclass(frozen=True)
class EnvironmentPromotionGate:
    gate_id: str
    release_id: str
    release_proof_hash: str
    environment: ReleaseEnvironment
    approval_hashes: tuple[str, ...]
    approver_ids: tuple[str, ...]
    health_check_proof_hash: str
    readiness_check_proof_hash: str
    rollback_manifest_proof_hash: str | None
    gate_created_at: str
    promotion_ready: bool
    promotion_execution_enabled: bool = False
    deployment_performed: bool = False

    def __post_init__(self) -> None:
        for name in ("release_id",):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        object.__setattr__(
            self,
            "release_proof_hash",
            normalize_sha256("release_proof_hash", self.release_proof_hash),
        )
        for name in ("health_check_proof_hash", "readiness_check_proof_hash"):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        if self.rollback_manifest_proof_hash is not None:
            object.__setattr__(
                self,
                "rollback_manifest_proof_hash",
                normalize_sha256(
                    "rollback_manifest_proof_hash",
                    self.rollback_manifest_proof_hash,
                ),
            )
        if not isinstance(self.environment, ReleaseEnvironment):
            raise ValueError("environment must be ReleaseEnvironment")
        object.__setattr__(
            self,
            "gate_created_at",
            normalize_utc_timestamp("gate_created_at", self.gate_created_at),
        )
        if not self.promotion_ready:
            raise ValueError("promotion gate must satisfy all readiness checks")
        if self.promotion_execution_enabled or self.deployment_performed:
            raise ValueError("step 15a cannot execute promotion/deployment")
        if len(set(self.approver_ids)) != len(self.approver_ids):
            raise ValueError("promotion gate approvers must be distinct")
        required = (
            2 if self.environment is ReleaseEnvironment.PRODUCTION else 1
        )
        if len(self.approver_ids) < required:
            raise ValueError(
                f"{self.environment.value} promotion requires {required} approval(s)"
            )
        if (
            self.environment is ReleaseEnvironment.PRODUCTION
            and self.rollback_manifest_proof_hash is None
        ):
            raise ValueError("production promotion requires a rollback manifest")
        expected = "recoveryworks-promotion-gate:" + canonical_hash(
            self._identity()
        )
        if self.gate_id != expected:
            raise ValueError("gate_id does not bind promotion gate")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "environment": self.environment.value,
            "approval_hashes": list(self.approval_hashes),
            "approver_ids": list(self.approver_ids),
            "health_check_proof_hash": self.health_check_proof_hash,
            "readiness_check_proof_hash": self.readiness_check_proof_hash,
            "rollback_manifest_proof_hash": self.rollback_manifest_proof_hash,
            "gate_created_at": self.gate_created_at,
            "promotion_ready": True,
            "promotion_execution_enabled": False,
            "deployment_performed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "gate_id": self.gate_id,
            "proof_hash": self.proof_hash,
            "state": "READY_FOR_SEPARATE_PROMOTION_ACTION",
        }


def _check_proof(
    check: ProductionCheckResult,
    expected_check: str,
    deployment_proof_hash: str,
) -> str:
    if check.check != expected_check or not check.passed:
        raise ValueError(f"{expected_check} check did not pass")
    if check.deployment_proof_hash != deployment_proof_hash:
        raise ValueError(f"{expected_check} check deployment proof mismatch")
    return canonical_hash(check.as_dict())


def build_environment_promotion_gate(
    release: RecoveryWorksReleaseManifest,
    *,
    environment: ReleaseEnvironment,
    approvals: tuple[ReleaseApprovalArtifact, ...],
    health_check: ProductionCheckResult,
    readiness_check: ProductionCheckResult,
    rollback_manifest: ReleaseRollbackManifest | None,
    gate_created_at: str,
) -> EnvironmentPromotionGate:
    for approval in approvals:
        if (
            approval.release_id != release.release_id
            or approval.release_proof_hash != release.proof_hash
        ):
            raise ValueError("release approval does not bind release candidate")
        if approval.environment is not environment:
            raise ValueError("release approval environment mismatch")
    approver_ids = tuple(sorted(approval.approver_id for approval in approvals))
    approval_hashes = tuple(sorted(approval.proof_hash for approval in approvals))
    required = 2 if environment is ReleaseEnvironment.PRODUCTION else 1
    if len(set(approver_ids)) < required:
        raise ValueError(
            f"{environment.value} promotion requires {required} distinct approval(s)"
        )

    rollback_hash = None
    if rollback_manifest is not None:
        if (
            rollback_manifest.release_id != release.release_id
            or rollback_manifest.release_proof_hash != release.proof_hash
        ):
            raise ValueError("rollback manifest does not bind release candidate")
        rollback_hash = rollback_manifest.proof_hash
    if environment is ReleaseEnvironment.PRODUCTION and rollback_hash is None:
        raise ValueError("production promotion requires rollback manifest")

    health_hash = _check_proof(
        health_check,
        "health",
        release.production_deployment_proof_hash,
    )
    readiness_hash = _check_proof(
        readiness_check,
        "readiness",
        release.production_deployment_proof_hash,
    )
    identity = {
        "schema": 1,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "environment": environment.value,
        "approval_hashes": list(approval_hashes),
        "approver_ids": list(approver_ids),
        "health_check_proof_hash": health_hash,
        "readiness_check_proof_hash": readiness_hash,
        "rollback_manifest_proof_hash": rollback_hash,
        "gate_created_at": normalize_utc_timestamp(
            "gate_created_at", gate_created_at
        ),
        "promotion_ready": True,
        "promotion_execution_enabled": False,
        "deployment_performed": False,
    }
    return EnvironmentPromotionGate(
        gate_id="recoveryworks-promotion-gate:" + canonical_hash(identity),
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        environment=environment,
        approval_hashes=approval_hashes,
        approver_ids=approver_ids,
        health_check_proof_hash=health_hash,
        readiness_check_proof_hash=readiness_hash,
        rollback_manifest_proof_hash=rollback_hash,
        gate_created_at=gate_created_at,
        promotion_ready=True,
        promotion_execution_enabled=False,
        deployment_performed=False,
    )


def write_release_control_artifacts(
    *,
    release: RecoveryWorksReleaseManifest,
    approvals: tuple[ReleaseApprovalArtifact, ...],
    rollback: ReleaseRollbackManifest | None,
    gate: EnvironmentPromotionGate,
    directory: str | Path,
) -> tuple[Path, Path, Path, Path]:
    target = Path(directory)
    paths = (
        target / "release-manifest.json",
        target / "release-approvals.json",
        target / "rollback-manifest.json",
        target / "promotion-gate.json",
    )
    payloads = (
        release.as_dict(),
        [
            {
                **approval._identity(),
                "approval_id": approval.approval_id,
                "proof_hash": approval.proof_hash,
            }
            for approval in approvals
        ],
        (
            None
            if rollback is None
            else {
                **rollback._identity(),
                "rollback_id": rollback.rollback_id,
                "proof_hash": rollback.proof_hash,
            }
        ),
        gate.as_dict(),
    )
    for path, payload in zip(paths, payloads):
        atomic_private_write(
            path,
            (
                json.dumps(
                    payload,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                )
                + "\n"
            ).encode("utf-8"),
        )
    return paths
