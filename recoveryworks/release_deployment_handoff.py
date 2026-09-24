"""Governed release-deployment handoff and post-deploy verification.

RecoveryOS prepares and verifies deployment proof artifacts only. A separately
authorized external deployer performs any environment change.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import re
from typing import Any

from recoveryworks.models import (
    canonical_hash,
    normalize_git_commit_sha,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)
from recoveryworks.release_control import (
    EnvironmentPromotionGate,
    RecoveryWorksReleaseManifest,
    ReleaseEnvironment,
)


_IMAGE_RE = re.compile(r"^[^@\s]+@sha256:([0-9a-f]{64})$")


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
class ReleaseDeploymentHandoff:
    handoff_id: str
    release_id: str
    release_proof_hash: str
    promotion_gate_id: str
    promotion_gate_proof_hash: str
    environment: ReleaseEnvironment
    container_image_ref: str
    container_image_digest: str
    source_commit: str
    production_deployment_proof_hash: str
    deployer_id: str
    issued_at: str
    expires_at: str
    external_deployment_authorized: bool = True
    credentials_embedded: bool = False
    deployment_performed_by_recoveryos: bool = False

    def __post_init__(self) -> None:
        for name in ("release_id", "promotion_gate_id", "deployer_id"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "release_proof_hash",
            "promotion_gate_proof_hash",
            "production_deployment_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        if isinstance(self.environment, str):
            try:
                object.__setattr__(
                    self, "environment", ReleaseEnvironment(self.environment)
                )
            except ValueError as exc:
                raise ValueError("environment must be ReleaseEnvironment") from exc
        elif not isinstance(self.environment, ReleaseEnvironment):
            raise ValueError("environment must be ReleaseEnvironment")
        match = _IMAGE_RE.fullmatch(self.container_image_ref)
        if match is None:
            raise ValueError("deployment handoff image must be digest pinned")
        digest = normalize_sha256(
            "container_image_digest", self.container_image_digest
        )
        if match.group(1) != digest:
            raise ValueError("deployment handoff image ref/digest mismatch")
        object.__setattr__(self, "container_image_digest", digest)
        object.__setattr__(
            self,
            "source_commit",
            normalize_git_commit_sha("source_commit", self.source_commit),
        )
        issued = normalize_utc_timestamp("issued_at", self.issued_at)
        expires = normalize_utc_timestamp("expires_at", self.expires_at)
        if _instant(expires) <= _instant(issued):
            raise ValueError("deployment handoff must expire after issuance")
        object.__setattr__(self, "issued_at", issued)
        object.__setattr__(self, "expires_at", expires)
        if self.external_deployment_authorized is not True:
            raise ValueError("deployment handoff must carry explicit authorization")
        if self.credentials_embedded:
            raise ValueError("deployment handoff cannot embed credentials")
        if self.deployment_performed_by_recoveryos:
            raise ValueError("RecoveryOS cannot claim to perform deployment")
        expected = "recoveryworks-deployment-handoff:" + canonical_hash(
            self._identity()
        )
        if self.handoff_id != expected:
            raise ValueError("handoff_id does not bind deployment handoff")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "promotion_gate_id": self.promotion_gate_id,
            "promotion_gate_proof_hash": self.promotion_gate_proof_hash,
            "environment": self.environment.value,
            "container_image_ref": self.container_image_ref,
            "container_image_digest": self.container_image_digest,
            "source_commit": self.source_commit,
            "production_deployment_proof_hash":
                self.production_deployment_proof_hash,
            "deployer_id": self.deployer_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "external_deployment_authorized": True,
            "credentials_embedded": False,
            "deployment_performed_by_recoveryos": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "handoff_id": self.handoff_id,
            "proof_hash": self.proof_hash,
            "state": "READY_FOR_SEPARATE_DEPLOYER",
        }


def prepare_release_deployment_handoff(
    release: RecoveryWorksReleaseManifest,
    gate: EnvironmentPromotionGate,
    *,
    deployer_id: str,
    issued_at: str,
    expires_at: str,
) -> ReleaseDeploymentHandoff:
    if not gate.promotion_ready:
        raise ValueError("promotion gate is not ready")
    if gate.release_id != release.release_id:
        raise ValueError("promotion gate release id mismatch")
    if gate.release_proof_hash != release.proof_hash:
        raise ValueError("promotion gate does not bind release")
    if gate.promotion_execution_enabled or gate.deployment_performed:
        raise ValueError("promotion gate already claims execution")
    identity = {
        "schema": 1,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "promotion_gate_id": gate.gate_id,
        "promotion_gate_proof_hash": gate.proof_hash,
        "environment": gate.environment.value,
        "container_image_ref": release.container_image_ref,
        "container_image_digest": release.container_image_digest,
        "source_commit": release.source_commit,
        "production_deployment_proof_hash":
            release.production_deployment_proof_hash,
        "deployer_id": _text("deployer_id", deployer_id),
        "issued_at": normalize_utc_timestamp("issued_at", issued_at),
        "expires_at": normalize_utc_timestamp("expires_at", expires_at),
        "external_deployment_authorized": True,
        "credentials_embedded": False,
        "deployment_performed_by_recoveryos": False,
    }
    return ReleaseDeploymentHandoff(
        handoff_id="recoveryworks-deployment-handoff:" + canonical_hash(identity),
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        promotion_gate_id=gate.gate_id,
        promotion_gate_proof_hash=gate.proof_hash,
        environment=gate.environment,
        container_image_ref=release.container_image_ref,
        container_image_digest=release.container_image_digest,
        source_commit=release.source_commit,
        production_deployment_proof_hash=
            release.production_deployment_proof_hash,
        deployer_id=deployer_id,
        issued_at=issued_at,
        expires_at=expires_at,
        external_deployment_authorized=True,
        credentials_embedded=False,
        deployment_performed_by_recoveryos=False,
    )


@dataclass(frozen=True)
class ExternalDeploymentReceipt:
    receipt_id: str
    handoff_id: str
    handoff_proof_hash: str
    release_id: str
    release_proof_hash: str
    environment: ReleaseEnvironment
    deployer_id: str
    deployed_at: str
    container_image_ref: str
    container_image_digest: str
    source_commit: str
    production_deployment_proof_hash: str
    external_deployment_id: str
    source_hash: str
    source_locator: str
    verified: bool

    def __post_init__(self) -> None:
        for name in (
            "handoff_id",
            "release_id",
            "deployer_id",
            "external_deployment_id",
            "source_locator",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "handoff_proof_hash",
            "release_proof_hash",
            "production_deployment_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        if isinstance(self.environment, str):
            try:
                object.__setattr__(
                    self, "environment", ReleaseEnvironment(self.environment)
                )
            except ValueError as exc:
                raise ValueError("environment must be ReleaseEnvironment") from exc
        elif not isinstance(self.environment, ReleaseEnvironment):
            raise ValueError("environment must be ReleaseEnvironment")
        match = _IMAGE_RE.fullmatch(self.container_image_ref)
        if match is None:
            raise ValueError("deployment receipt image must be digest pinned")
        digest = normalize_sha256(
            "container_image_digest", self.container_image_digest
        )
        if match.group(1) != digest:
            raise ValueError("deployment receipt image ref/digest mismatch")
        object.__setattr__(self, "container_image_digest", digest)
        object.__setattr__(
            self,
            "source_commit",
            normalize_git_commit_sha("source_commit", self.source_commit),
        )
        object.__setattr__(
            self,
            "deployed_at",
            normalize_utc_timestamp("deployed_at", self.deployed_at),
        )
        object.__setattr__(
            self, "source_hash", normalize_source_hash(self.source_hash)
        )
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        expected = "recoveryworks-deployment-receipt:" + canonical_hash(
            self._identity()
        )
        if self.receipt_id != expected:
            raise ValueError("receipt_id does not bind deployment receipt")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "handoff_id": self.handoff_id,
            "handoff_proof_hash": self.handoff_proof_hash,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "environment": self.environment.value,
            "deployer_id": self.deployer_id,
            "deployed_at": self.deployed_at,
            "container_image_ref": self.container_image_ref,
            "container_image_digest": self.container_image_digest,
            "source_commit": self.source_commit,
            "production_deployment_proof_hash":
                self.production_deployment_proof_hash,
            "external_deployment_id": self.external_deployment_id,
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": self.verified,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


@dataclass(frozen=True)
class DeploymentEnvironmentSnapshot:
    snapshot_id: str
    environment: ReleaseEnvironment
    observed_at: str
    release_id: str
    release_proof_hash: str
    container_image_ref: str
    container_image_digest: str
    source_commit: str
    production_deployment_proof_hash: str
    health_receipt_hash: str
    readiness_receipt_hash: str
    health_passed: bool
    readiness_passed: bool
    source_hash: str
    source_locator: str
    verified: bool

    def __post_init__(self) -> None:
        if isinstance(self.environment, str):
            try:
                object.__setattr__(
                    self, "environment", ReleaseEnvironment(self.environment)
                )
            except ValueError as exc:
                raise ValueError("environment must be ReleaseEnvironment") from exc
        elif not isinstance(self.environment, ReleaseEnvironment):
            raise ValueError("environment must be ReleaseEnvironment")
        for name in ("release_id", "source_locator"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "release_proof_hash",
            "production_deployment_proof_hash",
            "health_receipt_hash",
            "readiness_receipt_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        match = _IMAGE_RE.fullmatch(self.container_image_ref)
        if match is None:
            raise ValueError("environment snapshot image must be digest pinned")
        digest = normalize_sha256(
            "container_image_digest", self.container_image_digest
        )
        if match.group(1) != digest:
            raise ValueError("environment snapshot image ref/digest mismatch")
        object.__setattr__(self, "container_image_digest", digest)
        object.__setattr__(
            self,
            "source_commit",
            normalize_git_commit_sha("source_commit", self.source_commit),
        )
        object.__setattr__(
            self,
            "observed_at",
            normalize_utc_timestamp("observed_at", self.observed_at),
        )
        if type(self.health_passed) is not bool or type(self.readiness_passed) is not bool:
            raise ValueError("environment health/readiness flags must be boolean")
        object.__setattr__(
            self, "source_hash", normalize_source_hash(self.source_hash)
        )
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        expected = "recoveryworks-environment-snapshot:" + canonical_hash(
            self._identity()
        )
        if self.snapshot_id != expected:
            raise ValueError("snapshot_id does not bind environment snapshot")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "environment": self.environment.value,
            "observed_at": self.observed_at,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "container_image_ref": self.container_image_ref,
            "container_image_digest": self.container_image_digest,
            "source_commit": self.source_commit,
            "production_deployment_proof_hash":
                self.production_deployment_proof_hash,
            "health_receipt_hash": self.health_receipt_hash,
            "readiness_receipt_hash": self.readiness_receipt_hash,
            "health_passed": self.health_passed,
            "readiness_passed": self.readiness_passed,
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": self.verified,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


@dataclass(frozen=True)
class ValidatedDeploymentReceipt:
    receipt: ExternalDeploymentReceipt
    environment_snapshot_proof_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "environment_snapshot_proof_hash",
            normalize_sha256(
                "environment_snapshot_proof_hash",
                self.environment_snapshot_proof_hash,
            ),
        )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "deployment_receipt_proof_hash": self.receipt.proof_hash,
            "environment_snapshot_proof_hash":
                self.environment_snapshot_proof_hash,
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            "receipt_proof_hash": self.receipt.proof_hash,
            "environment_snapshot_proof_hash":
                self.environment_snapshot_proof_hash,
            "proof_hash": self.proof_hash,
            "state": "DEPLOYMENT_VERIFIED",
        }


def validate_external_deployment(
    handoff: ReleaseDeploymentHandoff,
    receipt: ExternalDeploymentReceipt,
    snapshot: DeploymentEnvironmentSnapshot,
) -> ValidatedDeploymentReceipt:
    if receipt.handoff_id != handoff.handoff_id:
        raise ValueError("deployment receipt handoff id mismatch")
    if receipt.handoff_proof_hash != handoff.proof_hash:
        raise ValueError("deployment receipt does not bind exact handoff")
    if receipt.release_id != handoff.release_id:
        raise ValueError("deployment receipt release id mismatch")
    if receipt.release_proof_hash != handoff.release_proof_hash:
        raise ValueError("deployment receipt release proof mismatch")
    if receipt.environment is not handoff.environment:
        raise ValueError("deployment receipt environment mismatch")
    if receipt.deployer_id != handoff.deployer_id:
        raise ValueError("deployment receipt deployer mismatch")
    if not receipt.verified:
        raise ValueError("external deployment receipt must be verified")
    deployed = _instant(receipt.deployed_at)
    if deployed < _instant(handoff.issued_at) or deployed > _instant(handoff.expires_at):
        raise ValueError("deployment occurred outside handoff authorization window")
    for name in (
        "container_image_ref",
        "container_image_digest",
        "source_commit",
        "production_deployment_proof_hash",
    ):
        if getattr(receipt, name) != getattr(handoff, name):
            raise ValueError(f"deployment receipt {name} mismatch")

    if not snapshot.verified:
        raise ValueError("post-deployment environment snapshot must be verified")
    if snapshot.environment is not handoff.environment:
        raise ValueError("environment snapshot environment mismatch")
    if snapshot.release_id != handoff.release_id:
        raise ValueError("environment snapshot release id mismatch")
    if snapshot.release_proof_hash != handoff.release_proof_hash:
        raise ValueError("environment snapshot release proof mismatch")
    for name in (
        "container_image_ref",
        "container_image_digest",
        "source_commit",
        "production_deployment_proof_hash",
    ):
        if getattr(snapshot, name) != getattr(handoff, name):
            raise ValueError(f"environment snapshot {name} mismatch")
    if _instant(snapshot.observed_at) < deployed:
        raise ValueError("environment snapshot predates deployment receipt")
    if not snapshot.health_passed or not snapshot.readiness_passed:
        raise ValueError("post-deployment health/readiness verification failed")
    return ValidatedDeploymentReceipt(
        receipt=receipt,
        environment_snapshot_proof_hash=snapshot.proof_hash,
    )
