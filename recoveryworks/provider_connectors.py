"""Read-only provider connector contracts and deterministic replay fixtures.

No live provider call or secret persistence is implemented in this step.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping

from recoveryworks.cloud_provider import canonical_cloud_provider
from recoveryworks.models import (
    canonical_hash,
    freeze_json,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)


class CredentialReferenceKind(str, Enum):
    WORKLOAD_IDENTITY = "WORKLOAD_IDENTITY"
    MANAGED_IDENTITY = "MANAGED_IDENTITY"
    ROLE_REFERENCE = "ROLE_REFERENCE"
    SERVICE_ACCOUNT_IMPERSONATION = "SERVICE_ACCOUNT_IMPERSONATION"


class ProviderReadOperation(str, Enum):
    DESCRIBE_IDENTITY = "DESCRIBE_IDENTITY"
    DISCOVER_BILLING_EXPORTS = "DISCOVER_BILLING_EXPORTS"
    DISCOVER_RESOURCES = "DISCOVER_RESOURCES"


class ProviderConnectorErrorCode(str, Enum):
    RATE_LIMITED = "RATE_LIMITED"
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    TIMEOUT = "TIMEOUT"
    TRANSIENT_PROVIDER_ERROR = "TRANSIENT_PROVIDER_ERROR"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    SCOPE_MISMATCH = "SCOPE_MISMATCH"
    FIXTURE_MISS = "FIXTURE_MISS"


_WRITE_MARKERS = (
    "write", "put", "post", "create", "delete", "update", "modify",
    "start", "stop", "attach", "detach", "deploy", "admin", "*",
)


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    lowered = normalized.lower()
    if any(marker in lowered for marker in (
        "password=", "secret=", "token=", "private_key", "access_key="
    )):
        raise ValueError(f"{name} appears to contain secret material")
    if any(ord(ch) < 32 for ch in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


@dataclass(frozen=True)
class CredentialProviderReference:
    reference_id: str
    provider: str
    account_id: str
    kind: CredentialReferenceKind
    principal_reference: str
    source_hash: str
    source_locator: str
    verified: bool
    credential_material_present: bool = False
    secret_persistence_enabled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider", canonical_cloud_provider(self.provider))
        for name in ("account_id", "principal_reference", "source_locator"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        if not isinstance(self.kind, CredentialReferenceKind):
            raise ValueError("kind must be CredentialReferenceKind")
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if self.verified is not True:
            raise ValueError("credential provider reference must be verified")
        if self.credential_material_present or self.secret_persistence_enabled:
            raise ValueError("provider connector readiness cannot contain or persist secrets")
        expected = "provider-credential-reference:" + canonical_hash(self._identity())
        if self.reference_id != expected:
            raise ValueError("reference_id does not bind credential reference")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema":1,
            "provider":self.provider,
            "account_id":self.account_id,
            "kind":self.kind.value,
            "principal_reference":self.principal_reference,
            "source_hash":self.source_hash,
            "source_locator":self.source_locator,
            "verified":True,
            "credential_material_present":False,
            "secret_persistence_enabled":False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_credential_provider_reference(
    *,
    provider: str,
    account_id: str,
    kind: CredentialReferenceKind,
    principal_reference: str,
    source_hash: str,
    source_locator: str,
    verified: bool,
) -> CredentialProviderReference:
    canonical = canonical_cloud_provider(provider)
    identity = {
        "schema":1,
        "provider":canonical,
        "account_id":_text("account_id",account_id),
        "kind":kind.value,
        "principal_reference":_text("principal_reference",principal_reference),
        "source_hash":normalize_source_hash(source_hash),
        "source_locator":_text("source_locator",source_locator),
        "verified":True,
        "credential_material_present":False,
        "secret_persistence_enabled":False,
    }
    if not verified:
        raise ValueError("credential provider reference must be verified")
    return CredentialProviderReference(
        reference_id="provider-credential-reference:"+canonical_hash(identity),
        provider=canonical,account_id=account_id,kind=kind,
        principal_reference=principal_reference,source_hash=source_hash,
        source_locator=source_locator,verified=True,
        credential_material_present=False,secret_persistence_enabled=False,
    )


@dataclass(frozen=True)
class ReadOnlyProviderConnectorContract:
    contract_id: str
    provider: str
    credential_reference_proof_hash: str
    account_id: str
    allowed_operations: tuple[ProviderReadOperation, ...]
    requests_per_minute_limit: int
    live_calls_enabled: bool = False
    write_operations_enabled: bool = False
    secret_persistence_enabled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider", canonical_cloud_provider(self.provider))
        object.__setattr__(
            self,"credential_reference_proof_hash",
            normalize_sha256(
                "credential_reference_proof_hash",
                self.credential_reference_proof_hash
            )
        )
        object.__setattr__(self,"account_id",_text("account_id",self.account_id))
        ops=tuple(sorted(set(self.allowed_operations),key=lambda x:x.value))
        required=set(ProviderReadOperation)
        if set(ops)!=required:
            raise ValueError("connector contract must expose exactly the supported read operations")
        object.__setattr__(self,"allowed_operations",ops)
        if type(self.requests_per_minute_limit) is not int or self.requests_per_minute_limit<=0:
            raise ValueError("requests_per_minute_limit must be positive")
        if self.live_calls_enabled or self.write_operations_enabled or self.secret_persistence_enabled:
            raise ValueError("step 25a connector contract must remain replay-only/read-only")
        expected="readonly-provider-connector:"+canonical_hash(self._identity())
        if self.contract_id!=expected:
            raise ValueError("contract_id does not bind provider connector contract")

    def _identity(self)->dict[str,Any]:
        return {
            "schema":1,"provider":self.provider,
            "credential_reference_proof_hash":self.credential_reference_proof_hash,
            "account_id":self.account_id,
            "allowed_operations":[x.value for x in self.allowed_operations],
            "requests_per_minute_limit":self.requests_per_minute_limit,
            "live_calls_enabled":False,"write_operations_enabled":False,
            "secret_persistence_enabled":False,
        }

    @property
    def proof_hash(self)->str:
        return canonical_hash(self._identity())


def build_readonly_provider_connector(
    credential: CredentialProviderReference,
    *,
    requests_per_minute_limit: int = 60,
)->ReadOnlyProviderConnectorContract:
    operations=tuple(ProviderReadOperation)
    identity={
        "schema":1,"provider":credential.provider,
        "credential_reference_proof_hash":credential.proof_hash,
        "account_id":credential.account_id,
        "allowed_operations":sorted(x.value for x in operations),
        "requests_per_minute_limit":requests_per_minute_limit,
        "live_calls_enabled":False,"write_operations_enabled":False,
        "secret_persistence_enabled":False,
    }
    return ReadOnlyProviderConnectorContract(
        contract_id="readonly-provider-connector:"+canonical_hash(identity),
        provider=credential.provider,
        credential_reference_proof_hash=credential.proof_hash,
        account_id=credential.account_id,
        allowed_operations=operations,
        requests_per_minute_limit=requests_per_minute_limit,
        live_calls_enabled=False,write_operations_enabled=False,
        secret_persistence_enabled=False,
    )


@dataclass(frozen=True)
class ProviderDiscoveryRequest:
    request_id: str
    provider: str
    account_id: str
    operation: ProviderReadOperation
    parameters: Mapping[str, Any]

    def __post_init__(self)->None:
        object.__setattr__(self,"provider",canonical_cloud_provider(self.provider))
        object.__setattr__(self,"account_id",_text("account_id",self.account_id))
        if not isinstance(self.operation,ProviderReadOperation):
            raise ValueError("operation must be ProviderReadOperation")
        frozen=freeze_json(self.parameters,name="parameters")
        for key,value in dict(frozen).items():
            text=f"{key}={value}".lower()
            if any(marker in text for marker in _WRITE_MARKERS):
                raise ValueError("provider discovery request contains mutation semantics")
        object.__setattr__(self,"parameters",frozen)
        expected="provider-discovery-request:"+canonical_hash(self._identity())
        if self.request_id!=expected:
            raise ValueError("request_id does not bind discovery request")

    def _identity(self)->dict[str,Any]:
        return {
            "schema":1,"provider":self.provider,"account_id":self.account_id,
            "operation":self.operation.value,"parameters":dict(self.parameters),
        }

    @property
    def proof_hash(self)->str:
        return canonical_hash(self._identity())


def build_provider_discovery_request(
    *,
    provider:str,
    account_id:str,
    operation:ProviderReadOperation,
    parameters:Mapping[str,Any]|None=None,
)->ProviderDiscoveryRequest:
    canonical=canonical_cloud_provider(provider)
    params=dict(parameters or {})
    identity={
        "schema":1,"provider":canonical,"account_id":_text("account_id",account_id),
        "operation":operation.value,"parameters":params,
    }
    return ProviderDiscoveryRequest(
        request_id="provider-discovery-request:"+canonical_hash(identity),
        provider=canonical,account_id=account_id,operation=operation,
        parameters=params,
    )


@dataclass(frozen=True)
class ProviderReplayFixture:
    fixture_id: str
    provider: str
    account_id: str
    request_proof_hash: str
    observed_at: str
    response_payload: Mapping[str, Any]
    source_hash: str
    source_locator: str
    verified: bool

    def __post_init__(self)->None:
        object.__setattr__(self,"provider",canonical_cloud_provider(self.provider))
        object.__setattr__(self,"account_id",_text("account_id",self.account_id))
        object.__setattr__(
            self,"request_proof_hash",
            normalize_sha256("request_proof_hash",self.request_proof_hash)
        )
        object.__setattr__(
            self,"observed_at",normalize_utc_timestamp("observed_at",self.observed_at)
        )
        object.__setattr__(
            self,"response_payload",freeze_json(self.response_payload,name="response_payload")
        )
        object.__setattr__(self,"source_hash",normalize_source_hash(self.source_hash))
        object.__setattr__(self,"source_locator",_text("source_locator",self.source_locator))
        if self.verified is not True:
            raise ValueError("provider replay fixture must be verified")
        expected="provider-replay-fixture:"+canonical_hash(self._identity())
        if self.fixture_id!=expected:
            raise ValueError("fixture_id does not bind replay fixture")

    def _identity(self)->dict[str,Any]:
        return {
            "schema":1,"provider":self.provider,"account_id":self.account_id,
            "request_proof_hash":self.request_proof_hash,
            "observed_at":self.observed_at,
            "response_payload":dict(self.response_payload),
            "source_hash":self.source_hash,"source_locator":self.source_locator,
            "verified":True,
        }

    @property
    def proof_hash(self)->str:
        return canonical_hash(self._identity())


def build_provider_replay_fixture(
    request:ProviderDiscoveryRequest,
    *,
    observed_at:str,
    response_payload:Mapping[str,Any],
    source_hash:str,
    source_locator:str,
    verified:bool,
)->ProviderReplayFixture:
    if not verified:
        raise ValueError("provider replay fixture must be verified")
    identity={
        "schema":1,"provider":request.provider,"account_id":request.account_id,
        "request_proof_hash":request.proof_hash,
        "observed_at":normalize_utc_timestamp("observed_at",observed_at),
        "response_payload":dict(response_payload),
        "source_hash":normalize_source_hash(source_hash),
        "source_locator":_text("source_locator",source_locator),"verified":True,
    }
    return ProviderReplayFixture(
        fixture_id="provider-replay-fixture:"+canonical_hash(identity),
        provider=request.provider,account_id=request.account_id,
        request_proof_hash=request.proof_hash,observed_at=observed_at,
        response_payload=response_payload,source_hash=source_hash,
        source_locator=source_locator,verified=True,
    )


@dataclass(frozen=True)
class ProviderReplayResult:
    result_id: str
    connector_proof_hash: str
    request_proof_hash: str
    fixture_proof_hash: str
    provider: str
    account_id: str
    operation: ProviderReadOperation
    response_payload: Mapping[str, Any]
    replayed: bool = True
    provider_api_called: bool = False
    secrets_persisted: bool = False

    def __post_init__(self)->None:
        for name in ("connector_proof_hash","request_proof_hash","fixture_proof_hash"):
            object.__setattr__(self,name,normalize_sha256(name,getattr(self,name)))
        object.__setattr__(self,"provider",canonical_cloud_provider(self.provider))
        object.__setattr__(self,"account_id",_text("account_id",self.account_id))
        object.__setattr__(
            self,"response_payload",freeze_json(self.response_payload,name="response_payload")
        )
        if not self.replayed or self.provider_api_called or self.secrets_persisted:
            raise ValueError("provider replay result must remain offline and secret-free")
        expected="provider-replay-result:"+canonical_hash(self._identity())
        if self.result_id!=expected:
            raise ValueError("result_id does not bind replay result")

    def _identity(self)->dict[str,Any]:
        return {
            "schema":1,"connector_proof_hash":self.connector_proof_hash,
            "request_proof_hash":self.request_proof_hash,
            "fixture_proof_hash":self.fixture_proof_hash,
            "provider":self.provider,"account_id":self.account_id,
            "operation":self.operation.value,
            "response_payload":dict(self.response_payload),
            "replayed":True,"provider_api_called":False,"secrets_persisted":False,
        }

    @property
    def proof_hash(self)->str:
        return canonical_hash(self._identity())

    def as_dict(self)->dict[str,Any]:
        return {**self._identity(),"result_id":self.result_id,
                "proof_hash":self.proof_hash,"state":"OFFLINE_REPLAY_VERIFIED"}


def replay_provider_discovery(
    connector:ReadOnlyProviderConnectorContract,
    request:ProviderDiscoveryRequest,
    fixture:ProviderReplayFixture,
)->ProviderReplayResult:
    if connector.provider!=request.provider or connector.account_id!=request.account_id:
        raise ValueError(ProviderConnectorErrorCode.SCOPE_MISMATCH.value)
    if request.operation not in connector.allowed_operations:
        raise ValueError("operation not allowed by connector contract")
    if fixture.provider!=request.provider or fixture.account_id!=request.account_id:
        raise ValueError(ProviderConnectorErrorCode.SCOPE_MISMATCH.value)
    if fixture.request_proof_hash!=request.proof_hash:
        raise ValueError(ProviderConnectorErrorCode.FIXTURE_MISS.value)
    identity={
        "schema":1,"connector_proof_hash":connector.proof_hash,
        "request_proof_hash":request.proof_hash,
        "fixture_proof_hash":fixture.proof_hash,
        "provider":request.provider,"account_id":request.account_id,
        "operation":request.operation.value,
        "response_payload":dict(fixture.response_payload),
        "replayed":True,"provider_api_called":False,"secrets_persisted":False,
    }
    return ProviderReplayResult(
        result_id="provider-replay-result:"+canonical_hash(identity),
        connector_proof_hash=connector.proof_hash,
        request_proof_hash=request.proof_hash,fixture_proof_hash=fixture.proof_hash,
        provider=request.provider,account_id=request.account_id,
        operation=request.operation,response_payload=fixture.response_payload,
        replayed=True,provider_api_called=False,secrets_persisted=False,
    )


def classify_provider_connector_error(
    *,
    http_status:int|None=None,
    error_name:str|None=None,
)->ProviderConnectorErrorCode:
    name=(error_name or "").strip().lower()
    if http_status==429 or "rate" in name and "limit" in name:
        return ProviderConnectorErrorCode.RATE_LIMITED
    if http_status in (401,403) or any(x in name for x in ("unauthorized","forbidden","accessdenied","permission")):
        return ProviderConnectorErrorCode.AUTHORIZATION_FAILED
    if any(x in name for x in ("timeout","timed out","deadline")):
        return ProviderConnectorErrorCode.TIMEOUT
    if http_status is not None and 500<=http_status<=599:
        return ProviderConnectorErrorCode.TRANSIENT_PROVIDER_ERROR
    return ProviderConnectorErrorCode.MALFORMED_RESPONSE
