"""Provider-neutral external-environment activation simulation.

This is a contract/simulation layer only. It does not embed credentials, call
provider APIs, provision infrastructure, start containers, or mutate resources.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from recoveryworks.cloud_provider import canonical_cloud_provider
from recoveryworks.models import (
    canonical_hash,
    freeze_json,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)
from recoveryworks.production_admission import ProductionAdmissionGate
from recoveryworks.release_control import RecoveryWorksReleaseManifest


_DISCOVERY_PERMISSIONS = {
    "aws": ("billing:read", "compute:describe", "identity:get"),
    "azure": ("billing:read", "resource:read", "identity:read"),
    "gcp": ("billing:read", "resource:read", "identity:read"),
}
_MUTATION_MARKERS = (
    "write", "create", "delete", "update", "modify", "start", "stop",
    "resize", "attach", "detach", "deploy", "admin", "*",
)


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


@dataclass(frozen=True)
class CredentialScopeAttestation:
    attestation_id: str
    provider: str
    account_id: str
    principal_id: str
    granted_permissions: tuple[str, ...]
    observed_at: str
    source_hash: str
    source_locator: str
    verified: bool
    credentials_embedded: bool = False
    provider_write_capability_present: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "provider", canonical_cloud_provider(self.provider)
        )
        for name in ("account_id", "principal_id", "source_locator"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        permissions = tuple(
            sorted({_text("permission", value).lower() for value in self.granted_permissions})
        )
        if not permissions:
            raise ValueError("credential scope must contain permissions")
        object.__setattr__(self, "granted_permissions", permissions)
        object.__setattr__(
            self, "observed_at",
            normalize_utc_timestamp("observed_at", self.observed_at)
        )
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if self.verified is not True:
            raise ValueError("credential scope attestation must be verified")
        if self.credentials_embedded:
            raise ValueError("credential scope attestation cannot embed credentials")
        if self.provider_write_capability_present:
            raise ValueError("activation simulation forbids provider write capability")
        for permission in permissions:
            if any(marker in permission for marker in _MUTATION_MARKERS):
                raise ValueError(
                    f"credential scope contains mutation-capable permission: {permission}"
                )
        expected = "recoveryworks-credential-scope:" + canonical_hash(
            self._identity()
        )
        if self.attestation_id != expected:
            raise ValueError("attestation_id does not bind credential scope")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "provider": self.provider,
            "account_id": self.account_id,
            "principal_id": self.principal_id,
            "granted_permissions": list(self.granted_permissions),
            "observed_at": self.observed_at,
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": True,
            "credentials_embedded": False,
            "provider_write_capability_present": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_credential_scope_attestation(
    *,
    provider: str,
    account_id: str,
    principal_id: str,
    granted_permissions: tuple[str, ...],
    observed_at: str,
    source_hash: str,
    source_locator: str,
    verified: bool,
) -> CredentialScopeAttestation:
    canonical = canonical_cloud_provider(provider)
    identity = {
        "schema": 1,
        "provider": canonical,
        "account_id": _text("account_id", account_id),
        "principal_id": _text("principal_id", principal_id),
        "granted_permissions": sorted(
            {_text("permission", value).lower() for value in granted_permissions}
        ),
        "observed_at": normalize_utc_timestamp("observed_at", observed_at),
        "source_hash": normalize_source_hash(source_hash),
        "source_locator": _text("source_locator", source_locator),
        "verified": True,
        "credentials_embedded": False,
        "provider_write_capability_present": False,
    }
    if not verified:
        raise ValueError("credential scope attestation must be verified")
    return CredentialScopeAttestation(
        attestation_id="recoveryworks-credential-scope:" + canonical_hash(identity),
        provider=canonical,
        account_id=account_id,
        principal_id=principal_id,
        granted_permissions=granted_permissions,
        observed_at=observed_at,
        source_hash=source_hash,
        source_locator=source_locator,
        verified=True,
        credentials_embedded=False,
        provider_write_capability_present=False,
    )


@dataclass(frozen=True)
class EnvironmentStateDiscovery:
    discovery_id: str
    provider: str
    account_id: str
    environment_id: str
    observed_at: str
    current_release_id: str | None
    current_image_digest: str | None
    resource_summary: Mapping[str, Any]
    source_hash: str
    source_locator: str
    verified: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "provider", canonical_cloud_provider(self.provider)
        )
        for name in ("account_id", "environment_id", "source_locator"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        object.__setattr__(
            self, "observed_at",
            normalize_utc_timestamp("observed_at", self.observed_at)
        )
        if self.current_release_id is not None:
            object.__setattr__(
                self, "current_release_id",
                _text("current_release_id", self.current_release_id),
            )
        if self.current_image_digest is not None:
            object.__setattr__(
                self,
                "current_image_digest",
                normalize_sha256(
                    "current_image_digest", self.current_image_digest
                ),
            )
        object.__setattr__(
            self,
            "resource_summary",
            freeze_json(self.resource_summary, name="resource_summary"),
        )
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if self.verified is not True:
            raise ValueError("environment state discovery must be verified")
        expected = "recoveryworks-environment-discovery:" + canonical_hash(
            self._identity()
        )
        if self.discovery_id != expected:
            raise ValueError("discovery_id does not bind environment discovery")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "provider": self.provider,
            "account_id": self.account_id,
            "environment_id": self.environment_id,
            "observed_at": self.observed_at,
            "current_release_id": self.current_release_id,
            "current_image_digest": self.current_image_digest,
            "resource_summary": dict(self.resource_summary),
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": True,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_environment_state_discovery(
    *,
    provider: str,
    account_id: str,
    environment_id: str,
    observed_at: str,
    current_release_id: str | None,
    current_image_digest: str | None,
    resource_summary: Mapping[str, Any],
    source_hash: str,
    source_locator: str,
    verified: bool,
) -> EnvironmentStateDiscovery:
    canonical = canonical_cloud_provider(provider)
    normalized_digest = (
        None
        if current_image_digest is None
        else normalize_sha256("current_image_digest", current_image_digest)
    )
    identity = {
        "schema": 1,
        "provider": canonical,
        "account_id": _text("account_id", account_id),
        "environment_id": _text("environment_id", environment_id),
        "observed_at": normalize_utc_timestamp("observed_at", observed_at),
        "current_release_id": (
            None if current_release_id is None
            else _text("current_release_id", current_release_id)
        ),
        "current_image_digest": normalized_digest,
        "resource_summary": dict(resource_summary),
        "source_hash": normalize_source_hash(source_hash),
        "source_locator": _text("source_locator", source_locator),
        "verified": True,
    }
    if not verified:
        raise ValueError("environment state discovery must be verified")
    return EnvironmentStateDiscovery(
        discovery_id="recoveryworks-environment-discovery:"
        + canonical_hash(identity),
        provider=canonical,
        account_id=account_id,
        environment_id=environment_id,
        observed_at=observed_at,
        current_release_id=current_release_id,
        current_image_digest=normalized_digest,
        resource_summary=resource_summary,
        source_hash=source_hash,
        source_locator=source_locator,
        verified=True,
    )


@dataclass(frozen=True)
class ProviderNeutralActivationAdapter:
    adapter_id: str
    provider: str
    credential_scope_proof_hash: str
    environment_discovery_proof_hash: str
    supported_operations: tuple[str, ...]
    mutation_operations_supported: bool = False
    credentials_stored: bool = False
    provider_api_calls_performed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "provider", canonical_cloud_provider(self.provider)
        )
        for name in (
            "credential_scope_proof_hash",
            "environment_discovery_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        operations = tuple(sorted(set(self.supported_operations)))
        required = (
            "DISCOVER_STATE",
            "VALIDATE_CREDENTIAL_SCOPE",
            "SIMULATE_DEPLOYMENT",
        )
        if operations != tuple(sorted(required)):
            raise ValueError("activation adapter supports only the simulation contract")
        object.__setattr__(self, "supported_operations", operations)
        if (
            self.mutation_operations_supported
            or self.credentials_stored
            or self.provider_api_calls_performed
        ):
            raise ValueError("activation adapter must remain simulation-only")
        expected = "recoveryworks-activation-adapter:" + canonical_hash(
            self._identity()
        )
        if self.adapter_id != expected:
            raise ValueError("adapter_id does not bind activation adapter")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "provider": self.provider,
            "credential_scope_proof_hash": self.credential_scope_proof_hash,
            "environment_discovery_proof_hash":
                self.environment_discovery_proof_hash,
            "supported_operations": list(self.supported_operations),
            "mutation_operations_supported": False,
            "credentials_stored": False,
            "provider_api_calls_performed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_activation_adapter(
    credential_scope: CredentialScopeAttestation,
    discovery: EnvironmentStateDiscovery,
) -> ProviderNeutralActivationAdapter:
    if credential_scope.provider != discovery.provider:
        raise ValueError("credential/discovery provider mismatch")
    if credential_scope.account_id != discovery.account_id:
        raise ValueError("credential/discovery account mismatch")
    # Require at least one provider-specific discovery permission. Additional
    # harmless read permissions are allowed.
    expected = set(_DISCOVERY_PERMISSIONS[credential_scope.provider])
    if not expected.intersection(credential_scope.granted_permissions):
        raise ValueError("credential scope lacks provider discovery permission")
    operations = (
        "DISCOVER_STATE",
        "VALIDATE_CREDENTIAL_SCOPE",
        "SIMULATE_DEPLOYMENT",
    )
    identity = {
        "schema": 1,
        "provider": credential_scope.provider,
        "credential_scope_proof_hash": credential_scope.proof_hash,
        "environment_discovery_proof_hash": discovery.proof_hash,
        "supported_operations": sorted(operations),
        "mutation_operations_supported": False,
        "credentials_stored": False,
        "provider_api_calls_performed": False,
    }
    return ProviderNeutralActivationAdapter(
        adapter_id="recoveryworks-activation-adapter:" + canonical_hash(identity),
        provider=credential_scope.provider,
        credential_scope_proof_hash=credential_scope.proof_hash,
        environment_discovery_proof_hash=discovery.proof_hash,
        supported_operations=operations,
        mutation_operations_supported=False,
        credentials_stored=False,
        provider_api_calls_performed=False,
    )


@dataclass(frozen=True)
class DeploymentActivationSimulation:
    simulation_id: str
    provider: str
    account_id: str
    environment_id: str
    release_id: str
    release_proof_hash: str
    production_admission_proof_hash: str
    adapter_proof_hash: str
    credential_scope_proof_hash: str
    discovery_proof_hash: str
    current_release_id: str | None
    current_image_digest: str | None
    target_image_digest: str
    simulated_changes: tuple[str, ...]
    simulated_at: str
    live_mutation_allowed: bool = False
    deployment_performed: bool = False
    provider_api_calls_performed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "provider", canonical_cloud_provider(self.provider)
        )
        for name in ("account_id", "environment_id", "release_id"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "release_proof_hash",
            "production_admission_proof_hash",
            "adapter_proof_hash",
            "credential_scope_proof_hash",
            "discovery_proof_hash",
            "target_image_digest",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        if self.current_image_digest is not None:
            object.__setattr__(
                self, "current_image_digest",
                normalize_sha256(
                    "current_image_digest", self.current_image_digest
                ),
            )
        object.__setattr__(
            self, "simulated_at",
            normalize_utc_timestamp("simulated_at", self.simulated_at)
        )
        if not self.simulated_changes:
            raise ValueError("activation simulation must describe proposed changes")
        if (
            self.live_mutation_allowed
            or self.deployment_performed
            or self.provider_api_calls_performed
        ):
            raise ValueError("activation simulation cannot perform live deployment")
        expected = "recoveryworks-activation-simulation:" + canonical_hash(
            self._identity()
        )
        if self.simulation_id != expected:
            raise ValueError("simulation_id does not bind activation simulation")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "provider": self.provider,
            "account_id": self.account_id,
            "environment_id": self.environment_id,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "production_admission_proof_hash":
                self.production_admission_proof_hash,
            "adapter_proof_hash": self.adapter_proof_hash,
            "credential_scope_proof_hash": self.credential_scope_proof_hash,
            "discovery_proof_hash": self.discovery_proof_hash,
            "current_release_id": self.current_release_id,
            "current_image_digest": self.current_image_digest,
            "target_image_digest": self.target_image_digest,
            "simulated_changes": list(self.simulated_changes),
            "simulated_at": self.simulated_at,
            "live_mutation_allowed": False,
            "deployment_performed": False,
            "provider_api_calls_performed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "simulation_id": self.simulation_id,
            "proof_hash": self.proof_hash,
            "state": "SIMULATION_ONLY",
        }


def simulate_external_environment_activation(
    release: RecoveryWorksReleaseManifest,
    admission: ProductionAdmissionGate,
    credential_scope: CredentialScopeAttestation,
    discovery: EnvironmentStateDiscovery,
    adapter: ProviderNeutralActivationAdapter,
    *,
    simulated_at: str,
) -> DeploymentActivationSimulation:
    if admission.release_id != release.release_id:
        raise ValueError("production admission release mismatch")
    if admission.release_proof_hash != release.proof_hash:
        raise ValueError("production admission release proof mismatch")
    if admission.container_image_digest != release.container_image_digest:
        raise ValueError("production admission image digest mismatch")
    if admission.source_commit != release.source_commit:
        raise ValueError("production admission source commit mismatch")
    if adapter.provider != credential_scope.provider or adapter.provider != discovery.provider:
        raise ValueError("activation provider mismatch")
    if adapter.credential_scope_proof_hash != credential_scope.proof_hash:
        raise ValueError("activation adapter credential proof mismatch")
    if adapter.environment_discovery_proof_hash != discovery.proof_hash:
        raise ValueError("activation adapter discovery proof mismatch")
    if discovery.account_id != credential_scope.account_id:
        raise ValueError("activation account mismatch")

    changes = []
    if discovery.current_release_id != release.release_id:
        changes.append(
            f"release: {discovery.current_release_id or 'none'} -> {release.release_id}"
        )
    if discovery.current_image_digest != release.container_image_digest:
        changes.append(
            "image_digest: "
            f"{discovery.current_image_digest or 'none'} -> "
            f"{release.container_image_digest}"
        )
    if not changes:
        changes.append("no-op: environment already matches admitted release")
    identity = {
        "schema": 1,
        "provider": discovery.provider,
        "account_id": discovery.account_id,
        "environment_id": discovery.environment_id,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "production_admission_proof_hash": admission.proof_hash,
        "adapter_proof_hash": adapter.proof_hash,
        "credential_scope_proof_hash": credential_scope.proof_hash,
        "discovery_proof_hash": discovery.proof_hash,
        "current_release_id": discovery.current_release_id,
        "current_image_digest": discovery.current_image_digest,
        "target_image_digest": release.container_image_digest,
        "simulated_changes": changes,
        "simulated_at": normalize_utc_timestamp("simulated_at", simulated_at),
        "live_mutation_allowed": False,
        "deployment_performed": False,
        "provider_api_calls_performed": False,
    }
    return DeploymentActivationSimulation(
        simulation_id="recoveryworks-activation-simulation:"
        + canonical_hash(identity),
        provider=discovery.provider,
        account_id=discovery.account_id,
        environment_id=discovery.environment_id,
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        production_admission_proof_hash=admission.proof_hash,
        adapter_proof_hash=adapter.proof_hash,
        credential_scope_proof_hash=credential_scope.proof_hash,
        discovery_proof_hash=discovery.proof_hash,
        current_release_id=discovery.current_release_id,
        current_image_digest=discovery.current_image_digest,
        target_image_digest=release.container_image_digest,
        simulated_changes=tuple(changes),
        simulated_at=simulated_at,
        live_mutation_allowed=False,
        deployment_performed=False,
        provider_api_calls_performed=False,
    )
