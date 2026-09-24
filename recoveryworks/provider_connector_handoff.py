"""Separate-runner handoff and receipt verification for read-only provider discovery."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from recoveryworks.models import (
    canonical_hash,
    freeze_json,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)
from recoveryworks.provider_connectors import (
    CredentialProviderReference,
    ProviderDiscoveryRequest,
    ProviderReadOperation,
    ReadOnlyProviderConnectorContract,
)


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(ch) < 32 for ch in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    lowered = normalized.lower()
    if any(marker in lowered for marker in (
        "password=", "secret=", "token=", "private_key", "access_key="
    )):
        raise ValueError(f"{name} appears to contain secret material")
    return normalized


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(
        normalize_utc_timestamp("timestamp", value).replace("Z", "+00:00")
    )


@dataclass(frozen=True)
class ProviderDiscoveryHandoffPolicy:
    ttl_seconds: int = 300

    def __post_init__(self) -> None:
        if type(self.ttl_seconds) is not int or not 1 <= self.ttl_seconds <= 3600:
            raise ValueError("ttl_seconds must be in 1..3600")


@dataclass(frozen=True)
class ProviderDiscoveryHandoff:
    handoff_id: str
    connector_proof_hash: str
    credential_reference_proof_hash: str
    request_id: str
    request_proof_hash: str
    provider: str
    account_id: str
    operation: ProviderReadOperation
    runner_id: str
    issued_at: str
    expires_at: str
    credential_material_embedded: bool = False
    provider_api_called_by_recoveryworks: bool = False
    provider_mutation_allowed: bool = False

    def __post_init__(self) -> None:
        for name in (
            "connector_proof_hash",
            "credential_reference_proof_hash",
            "request_proof_hash",
        ):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        for name in ("request_id", "provider", "account_id", "runner_id"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        if not isinstance(self.operation, ProviderReadOperation):
            raise ValueError("operation must be ProviderReadOperation")
        object.__setattr__(
            self, "issued_at", normalize_utc_timestamp("issued_at", self.issued_at)
        )
        object.__setattr__(
            self, "expires_at", normalize_utc_timestamp("expires_at", self.expires_at)
        )
        if _instant(self.expires_at) <= _instant(self.issued_at):
            raise ValueError("provider discovery handoff must expire after issuance")
        if (
            self.credential_material_embedded
            or self.provider_api_called_by_recoveryworks
            or self.provider_mutation_allowed
        ):
            raise ValueError("provider discovery handoff must remain credential-free and read-only")
        expected = "provider-discovery-handoff:" + canonical_hash(self._identity())
        if self.handoff_id != expected:
            raise ValueError("handoff_id does not bind provider discovery handoff")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "connector_proof_hash": self.connector_proof_hash,
            "credential_reference_proof_hash": self.credential_reference_proof_hash,
            "request_id": self.request_id,
            "request_proof_hash": self.request_proof_hash,
            "provider": self.provider,
            "account_id": self.account_id,
            "operation": self.operation.value,
            "runner_id": self.runner_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "credential_material_embedded": False,
            "provider_api_called_by_recoveryworks": False,
            "provider_mutation_allowed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "handoff_id": self.handoff_id,
            "proof_hash": self.proof_hash,
            "state": "READY_FOR_SEPARATE_READONLY_CONNECTOR_RUNNER",
        }


def prepare_provider_discovery_handoff(
    connector: ReadOnlyProviderConnectorContract,
    credential: CredentialProviderReference,
    request: ProviderDiscoveryRequest,
    *,
    runner_id: str,
    issued_at: str,
    policy: ProviderDiscoveryHandoffPolicy = ProviderDiscoveryHandoffPolicy(),
) -> ProviderDiscoveryHandoff:
    if connector.credential_reference_proof_hash != credential.proof_hash:
        raise ValueError("connector does not bind credential reference")
    if connector.provider != credential.provider or connector.account_id != credential.account_id:
        raise ValueError("connector/credential scope mismatch")
    if request.provider != connector.provider or request.account_id != connector.account_id:
        raise ValueError("request scope does not match connector")
    if request.operation not in connector.allowed_operations:
        raise ValueError("request operation not allowed by connector")
    issued = normalize_utc_timestamp("issued_at", issued_at)
    expires = (
        _instant(issued) + timedelta(seconds=policy.ttl_seconds)
    ).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    identity = {
        "schema": 1,
        "connector_proof_hash": connector.proof_hash,
        "credential_reference_proof_hash": credential.proof_hash,
        "request_id": request.request_id,
        "request_proof_hash": request.proof_hash,
        "provider": request.provider,
        "account_id": request.account_id,
        "operation": request.operation.value,
        "runner_id": _text("runner_id", runner_id),
        "issued_at": issued,
        "expires_at": expires,
        "credential_material_embedded": False,
        "provider_api_called_by_recoveryworks": False,
        "provider_mutation_allowed": False,
    }
    return ProviderDiscoveryHandoff(
        handoff_id="provider-discovery-handoff:" + canonical_hash(identity),
        connector_proof_hash=connector.proof_hash,
        credential_reference_proof_hash=credential.proof_hash,
        request_id=request.request_id,
        request_proof_hash=request.proof_hash,
        provider=request.provider,
        account_id=request.account_id,
        operation=request.operation,
        runner_id=runner_id,
        issued_at=issued,
        expires_at=expires,
        credential_material_embedded=False,
        provider_api_called_by_recoveryworks=False,
        provider_mutation_allowed=False,
    )


@dataclass(frozen=True)
class ExternalProviderDiscoveryReceipt:
    receipt_id: str
    handoff_id: str
    handoff_proof_hash: str
    request_proof_hash: str
    provider: str
    account_id: str
    operation: ProviderReadOperation
    runner_id: str
    observed_at: str
    provider_request_id: str
    response_payload: Mapping[str, Any]
    response_hash: str
    source_hash: str
    source_locator: str
    verified: bool
    provider_api_called_by_external_runner: bool = True
    provider_mutation_performed: bool = False
    credential_material_returned: bool = False

    def __post_init__(self) -> None:
        for name in ("handoff_proof_hash", "request_proof_hash", "response_hash"):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        for name in (
            "handoff_id", "provider", "account_id", "runner_id",
            "provider_request_id", "source_locator",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        if not isinstance(self.operation, ProviderReadOperation):
            raise ValueError("operation must be ProviderReadOperation")
        object.__setattr__(
            self, "observed_at", normalize_utc_timestamp("observed_at", self.observed_at)
        )
        frozen = freeze_json(self.response_payload, name="response_payload")
        object.__setattr__(self, "response_payload", frozen)
        expected_response_hash = canonical_hash(dict(frozen))
        if self.response_hash != expected_response_hash:
            raise ValueError("response_hash does not match provider response payload")
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if self.verified is not True:
            raise ValueError("provider discovery receipt must be externally verified")
        if self.provider_api_called_by_external_runner is not True:
            raise ValueError("receipt must represent a separately performed provider read")
        if self.provider_mutation_performed or self.credential_material_returned:
            raise ValueError("provider discovery receipt must remain read-only and secret-free")
        expected = "provider-discovery-receipt:" + canonical_hash(self._identity())
        if self.receipt_id != expected:
            raise ValueError("receipt_id does not bind provider discovery receipt")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "handoff_id": self.handoff_id,
            "handoff_proof_hash": self.handoff_proof_hash,
            "request_proof_hash": self.request_proof_hash,
            "provider": self.provider,
            "account_id": self.account_id,
            "operation": self.operation.value,
            "runner_id": self.runner_id,
            "observed_at": self.observed_at,
            "provider_request_id": self.provider_request_id,
            "response_payload": dict(self.response_payload),
            "response_hash": self.response_hash,
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": True,
            "provider_api_called_by_external_runner": True,
            "provider_mutation_performed": False,
            "credential_material_returned": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


@dataclass(frozen=True)
class VerifiedProviderDiscoveryEvidence:
    evidence_id: str
    handoff_proof_hash: str
    receipt_proof_hash: str
    request_proof_hash: str
    provider: str
    account_id: str
    operation: ProviderReadOperation
    response_hash: str
    observed_at: str

    def __post_init__(self) -> None:
        for name in (
            "handoff_proof_hash", "receipt_proof_hash",
            "request_proof_hash", "response_hash",
        ):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        object.__setattr__(self, "observed_at", normalize_utc_timestamp(
            "observed_at", self.observed_at
        ))
        expected = "verified-provider-discovery:" + canonical_hash(self._identity())
        if self.evidence_id != expected:
            raise ValueError("evidence_id does not bind verified provider discovery")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "handoff_proof_hash": self.handoff_proof_hash,
            "receipt_proof_hash": self.receipt_proof_hash,
            "request_proof_hash": self.request_proof_hash,
            "provider": self.provider,
            "account_id": self.account_id,
            "operation": self.operation.value,
            "response_hash": self.response_hash,
            "observed_at": self.observed_at,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "evidence_id": self.evidence_id,
            "proof_hash": self.proof_hash,
            "state": "EXTERNAL_READONLY_DISCOVERY_VERIFIED",
        }


def validate_external_provider_discovery(
    handoff: ProviderDiscoveryHandoff,
    receipt: ExternalProviderDiscoveryReceipt,
) -> VerifiedProviderDiscoveryEvidence:
    if receipt.handoff_id != handoff.handoff_id:
        raise ValueError("provider discovery receipt handoff id mismatch")
    if receipt.handoff_proof_hash != handoff.proof_hash:
        raise ValueError("provider discovery receipt does not bind exact handoff")
    if receipt.request_proof_hash != handoff.request_proof_hash:
        raise ValueError("provider discovery receipt request mismatch")
    if receipt.provider != handoff.provider or receipt.account_id != handoff.account_id:
        raise ValueError("provider discovery receipt scope mismatch")
    if receipt.operation is not handoff.operation:
        raise ValueError("provider discovery receipt operation mismatch")
    if receipt.runner_id != handoff.runner_id:
        raise ValueError("provider discovery receipt runner mismatch")
    observed = _instant(receipt.observed_at)
    if observed < _instant(handoff.issued_at) or observed > _instant(handoff.expires_at):
        raise ValueError("provider discovery occurred outside handoff window")
    identity = {
        "schema": 1,
        "handoff_proof_hash": handoff.proof_hash,
        "receipt_proof_hash": receipt.proof_hash,
        "request_proof_hash": handoff.request_proof_hash,
        "provider": handoff.provider,
        "account_id": handoff.account_id,
        "operation": handoff.operation.value,
        "response_hash": receipt.response_hash,
        "observed_at": receipt.observed_at,
    }
    return VerifiedProviderDiscoveryEvidence(
        evidence_id="verified-provider-discovery:" + canonical_hash(identity),
        handoff_proof_hash=handoff.proof_hash,
        receipt_proof_hash=receipt.proof_hash,
        request_proof_hash=handoff.request_proof_hash,
        provider=handoff.provider,
        account_id=handoff.account_id,
        operation=handoff.operation,
        response_hash=receipt.response_hash,
        observed_at=receipt.observed_at,
    )
