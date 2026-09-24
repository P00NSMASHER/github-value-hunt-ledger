"""Governed external activation handoff and receipt verification.

RecoveryWorks prepares/validates proof artifacts only. A named separate deployer
performs any provider-side deployment.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from recoveryworks.environment_activation import (
    CredentialScopeAttestation,
    DeploymentActivationSimulation,
    EnvironmentStateDiscovery,
)
from recoveryworks.models import (
    canonical_hash,
    normalize_git_commit_sha,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)
from recoveryworks.production_admission import ProductionAdmissionGate
from recoveryworks.release_control import RecoveryWorksReleaseManifest


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
class ActivationHandoffPolicy:
    max_recheck_age_seconds: int = 300
    handoff_ttl_seconds: int = 300

    def __post_init__(self) -> None:
        for name in ("max_recheck_age_seconds", "handoff_ttl_seconds"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class ExternalActivationHandoff:
    handoff_id: str
    simulation_id: str
    simulation_proof_hash: str
    release_id: str
    release_proof_hash: str
    production_admission_proof_hash: str
    credential_scope_proof_hash: str
    provider: str
    account_id: str
    environment_id: str
    current_release_id: str | None
    current_image_digest: str | None
    target_image_digest: str
    target_source_commit: str
    recheck_discovery_proof_hash: str
    recheck_observed_at: str
    deployer_id: str
    issued_at: str
    expires_at: str
    credentials_embedded: bool = False
    deployment_performed_by_recoveryworks: bool = False

    def __post_init__(self) -> None:
        for name in (
            "simulation_id", "release_id", "provider", "account_id",
            "environment_id", "deployer_id",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "simulation_proof_hash", "release_proof_hash",
            "production_admission_proof_hash", "credential_scope_proof_hash",
            "target_image_digest", "recheck_discovery_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        if self.current_image_digest is not None:
            object.__setattr__(
                self, "current_image_digest",
                normalize_sha256("current_image_digest", self.current_image_digest)
            )
        object.__setattr__(
            self, "target_source_commit",
            normalize_git_commit_sha("target_source_commit", self.target_source_commit)
        )
        for name in ("recheck_observed_at", "issued_at", "expires_at"):
            object.__setattr__(
                self, name, normalize_utc_timestamp(name, getattr(self, name))
            )
        if _instant(self.expires_at) <= _instant(self.issued_at):
            raise ValueError("activation handoff must expire after issuance")
        if self.credentials_embedded:
            raise ValueError("activation handoff cannot embed credentials")
        if self.deployment_performed_by_recoveryworks:
            raise ValueError("RecoveryWorks cannot claim it performed deployment")
        expected = "recoveryworks-activation-handoff:" + canonical_hash(self._identity())
        if self.handoff_id != expected:
            raise ValueError("handoff_id does not bind activation handoff")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "simulation_id": self.simulation_id,
            "simulation_proof_hash": self.simulation_proof_hash,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "production_admission_proof_hash": self.production_admission_proof_hash,
            "credential_scope_proof_hash": self.credential_scope_proof_hash,
            "provider": self.provider,
            "account_id": self.account_id,
            "environment_id": self.environment_id,
            "current_release_id": self.current_release_id,
            "current_image_digest": self.current_image_digest,
            "target_image_digest": self.target_image_digest,
            "target_source_commit": self.target_source_commit,
            "recheck_discovery_proof_hash": self.recheck_discovery_proof_hash,
            "recheck_observed_at": self.recheck_observed_at,
            "deployer_id": self.deployer_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "credentials_embedded": False,
            "deployment_performed_by_recoveryworks": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "handoff_id": self.handoff_id,
            "proof_hash": self.proof_hash,
            "state": "READY_FOR_SEPARATE_ACTIVATION_DEPLOYER",
        }


def prepare_external_activation_handoff(
    simulation: DeploymentActivationSimulation,
    release: RecoveryWorksReleaseManifest,
    admission: ProductionAdmissionGate,
    credential_scope: CredentialScopeAttestation,
    fresh_discovery: EnvironmentStateDiscovery,
    *,
    deployer_id: str,
    issued_at: str,
    policy: ActivationHandoffPolicy = ActivationHandoffPolicy(),
) -> ExternalActivationHandoff:
    if simulation.release_id != release.release_id:
        raise ValueError("activation simulation release mismatch")
    if simulation.release_proof_hash != release.proof_hash:
        raise ValueError("activation simulation release proof mismatch")
    if simulation.production_admission_proof_hash != admission.proof_hash:
        raise ValueError("activation simulation admission mismatch")
    if admission.release_id != release.release_id:
        raise ValueError("production admission release mismatch")
    if admission.release_proof_hash != release.proof_hash:
        raise ValueError("production admission release proof mismatch")
    if credential_scope.proof_hash != simulation.credential_scope_proof_hash:
        raise ValueError("activation credential scope mismatch")
    if (
        fresh_discovery.provider != simulation.provider
        or fresh_discovery.account_id != simulation.account_id
        or fresh_discovery.environment_id != simulation.environment_id
    ):
        raise ValueError("fresh environment discovery scope mismatch")
    if not fresh_discovery.verified:
        raise ValueError("fresh environment discovery must be verified")
    if (
        fresh_discovery.current_release_id != simulation.current_release_id
        or fresh_discovery.current_image_digest != simulation.current_image_digest
    ):
        raise ValueError("environment changed since activation simulation")

    issued_at = normalize_utc_timestamp("issued_at", issued_at)
    observed = _instant(fresh_discovery.observed_at)
    issued = _instant(issued_at)
    if observed > issued:
        raise ValueError("fresh discovery cannot postdate handoff issuance")
    if int((issued - observed).total_seconds()) > policy.max_recheck_age_seconds:
        raise ValueError("fresh environment discovery is too stale")
    expiry = (
        issued + timedelta(seconds=policy.handoff_ttl_seconds)
    ).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    identity = {
        "schema": 1,
        "simulation_id": simulation.simulation_id,
        "simulation_proof_hash": simulation.proof_hash,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "production_admission_proof_hash": admission.proof_hash,
        "credential_scope_proof_hash": credential_scope.proof_hash,
        "provider": simulation.provider,
        "account_id": simulation.account_id,
        "environment_id": simulation.environment_id,
        "current_release_id": simulation.current_release_id,
        "current_image_digest": simulation.current_image_digest,
        "target_image_digest": release.container_image_digest,
        "target_source_commit": release.source_commit,
        "recheck_discovery_proof_hash": fresh_discovery.proof_hash,
        "recheck_observed_at": fresh_discovery.observed_at,
        "deployer_id": _text("deployer_id", deployer_id),
        "issued_at": issued_at,
        "expires_at": expiry,
        "credentials_embedded": False,
        "deployment_performed_by_recoveryworks": False,
    }
    return ExternalActivationHandoff(
        handoff_id="recoveryworks-activation-handoff:" + canonical_hash(identity),
        simulation_id=simulation.simulation_id,
        simulation_proof_hash=simulation.proof_hash,
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        production_admission_proof_hash=admission.proof_hash,
        credential_scope_proof_hash=credential_scope.proof_hash,
        provider=simulation.provider,
        account_id=simulation.account_id,
        environment_id=simulation.environment_id,
        current_release_id=simulation.current_release_id,
        current_image_digest=simulation.current_image_digest,
        target_image_digest=release.container_image_digest,
        target_source_commit=release.source_commit,
        recheck_discovery_proof_hash=fresh_discovery.proof_hash,
        recheck_observed_at=fresh_discovery.observed_at,
        deployer_id=deployer_id,
        issued_at=issued_at,
        expires_at=expiry,
        credentials_embedded=False,
        deployment_performed_by_recoveryworks=False,
    )


@dataclass(frozen=True)
class ExternalActivationReceipt:
    receipt_id: str
    handoff_id: str
    handoff_proof_hash: str
    deployer_id: str
    provider: str
    account_id: str
    environment_id: str
    release_id: str
    release_proof_hash: str
    target_image_digest: str
    target_source_commit: str
    deployed_at: str
    external_deployment_id: str
    source_hash: str
    source_locator: str
    verified: bool

    def __post_init__(self) -> None:
        for name in (
            "handoff_id", "deployer_id", "provider", "account_id",
            "environment_id", "release_id", "external_deployment_id",
            "source_locator",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "handoff_proof_hash", "release_proof_hash", "target_image_digest"
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self, "target_source_commit",
            normalize_git_commit_sha("target_source_commit", self.target_source_commit)
        )
        object.__setattr__(
            self, "deployed_at",
            normalize_utc_timestamp("deployed_at", self.deployed_at)
        )
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if self.verified is not True:
            raise ValueError("external activation receipt must be verified")
        expected = "recoveryworks-activation-receipt:" + canonical_hash(self._identity())
        if self.receipt_id != expected:
            raise ValueError("receipt_id does not bind activation receipt")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "handoff_id": self.handoff_id,
            "handoff_proof_hash": self.handoff_proof_hash,
            "deployer_id": self.deployer_id,
            "provider": self.provider,
            "account_id": self.account_id,
            "environment_id": self.environment_id,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "target_image_digest": self.target_image_digest,
            "target_source_commit": self.target_source_commit,
            "deployed_at": self.deployed_at,
            "external_deployment_id": self.external_deployment_id,
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": True,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


@dataclass(frozen=True)
class ValidatedActivationReceipt:
    receipt: ExternalActivationReceipt
    post_discovery_proof_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "post_discovery_proof_hash",
            normalize_sha256("post_discovery_proof_hash", self.post_discovery_proof_hash),
        )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "activation_receipt_proof_hash": self.receipt.proof_hash,
            "post_discovery_proof_hash": self.post_discovery_proof_hash,
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            "activation_receipt_proof_hash": self.receipt.proof_hash,
            "post_discovery_proof_hash": self.post_discovery_proof_hash,
            "proof_hash": self.proof_hash,
            "state": "ACTIVATION_VERIFIED",
        }


def validate_external_activation(
    handoff: ExternalActivationHandoff,
    receipt: ExternalActivationReceipt,
    post_discovery: EnvironmentStateDiscovery,
) -> ValidatedActivationReceipt:
    if receipt.handoff_id != handoff.handoff_id:
        raise ValueError("activation receipt handoff id mismatch")
    if receipt.handoff_proof_hash != handoff.proof_hash:
        raise ValueError("activation receipt does not bind exact handoff")
    if receipt.deployer_id != handoff.deployer_id:
        raise ValueError("activation receipt deployer mismatch")
    for name in ("provider", "account_id", "environment_id", "release_id",
                 "release_proof_hash", "target_image_digest", "target_source_commit"):
        if getattr(receipt, name) != getattr(handoff, name):
            raise ValueError(f"activation receipt {name} mismatch")
    deployed = _instant(receipt.deployed_at)
    if deployed < _instant(handoff.issued_at) or deployed > _instant(handoff.expires_at):
        raise ValueError("activation occurred outside authorized handoff window")

    if not post_discovery.verified:
        raise ValueError("post-activation discovery must be verified")
    if (
        post_discovery.provider != handoff.provider
        or post_discovery.account_id != handoff.account_id
        or post_discovery.environment_id != handoff.environment_id
    ):
        raise ValueError("post-activation discovery scope mismatch")
    if post_discovery.current_release_id != handoff.release_id:
        raise ValueError("post-activation release does not match target")
    if post_discovery.current_image_digest != handoff.target_image_digest:
        raise ValueError("post-activation image does not match target")
    if _instant(post_discovery.observed_at) < deployed:
        raise ValueError("post-activation discovery predates external deployment")
    return ValidatedActivationReceipt(
        receipt=receipt,
        post_discovery_proof_hash=post_discovery.proof_hash,
    )
