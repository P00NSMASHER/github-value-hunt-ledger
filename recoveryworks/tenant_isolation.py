"""Shared tenant identity/binding registry for managed RecoveryWorks artifacts."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from recoveryworks.integrations.cletrics_registry import CletricsReceiptRegistry
from recoveryworks.models import canonical_hash, normalize_sha256, normalize_utc_timestamp
from recoveryworks.private_io import atomic_private_write, private_file_lock
from recoveryworks.store import LocalBundleStore


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(ch) < 32 for ch in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


@dataclass(frozen=True)
class TenantIdentity:
    tenant_id: str
    client_id: str
    namespace: str
    created_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "tenant_id", _text("tenant_id", self.tenant_id))
        object.__setattr__(self, "client_id", _text("client_id", self.client_id))
        namespace = str(Path(_text("namespace", self.namespace)).resolve())
        object.__setattr__(self, "namespace", namespace)
        object.__setattr__(
            self, "created_at", normalize_utc_timestamp("created_at", self.created_at)
        )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "tenant_id": self.tenant_id,
            "client_id": self.client_id,
            "namespace": self.namespace,
            "created_at": self.created_at,
        })


@dataclass(frozen=True)
class TenantArtifactBinding:
    artifact_type: str
    artifact_key: str
    path: str | None
    proof_hash: str | None
    bound_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_type", _text("artifact_type", self.artifact_type))
        object.__setattr__(self, "artifact_key", _text("artifact_key", self.artifact_key))
        if self.path is not None:
            object.__setattr__(self, "path", str(Path(self.path).resolve()))
        if self.proof_hash is not None:
            object.__setattr__(
                self, "proof_hash", normalize_sha256("proof_hash", self.proof_hash)
            )
        object.__setattr__(
            self, "bound_at", normalize_utc_timestamp("bound_at", self.bound_at)
        )

    @property
    def binding_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


class TenantBindingRegistry:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.lock_path = self.path.with_name("." + self.path.name + ".lock")

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema": 1, "tenants": {}, "paths": {}, "proofs": {}}
        envelope = json.loads(self.path.read_text(encoding="utf-8"))
        if envelope.get("schema") != 1:
            raise ValueError("unsupported tenant binding registry schema")
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("tenant registry payload missing")
        expected = canonical_hash(payload)
        if envelope.get("state_hash") != expected:
            raise ValueError("tenant binding registry state hash mismatch")
        return payload

    def _write(self, payload: Mapping[str, Any]) -> None:
        envelope = {
            "schema": 1,
            "state_hash": canonical_hash(payload),
            "payload": payload,
        }
        atomic_private_write(
            self.path,
            (
                json.dumps(
                    envelope,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                ) + "\n"
            ).encode("utf-8"),
        )

    def _assert_identity(self, payload: dict[str, Any], identity: TenantIdentity) -> None:
        tenants = payload.setdefault("tenants", {})
        existing = tenants.get(identity.tenant_id)
        row = {
            "client_id": identity.client_id,
            "namespace": identity.namespace,
            "created_at": identity.created_at,
            "tenant_proof_hash": identity.proof_hash,
        }
        for other_tenant_id, other in tenants.items():
            if (
                other_tenant_id != identity.tenant_id
                and other.get("client_id") == identity.client_id
            ):
                raise ValueError(
                    "client_id is already bound to a different tenant identity"
                )
        if existing is None:
            tenants[identity.tenant_id] = row
            return
        if existing != row:
            raise ValueError("tenant identity conflicts with existing tenant binding")

    def reserve_paths(
        self,
        identity: TenantIdentity,
        *,
        artifact_paths: Mapping[str, str | Path],
    ) -> None:
        with private_file_lock(self.lock_path):
            payload = self._read()
            self._assert_identity(payload, identity)
            paths = payload.setdefault("paths", {})
            for artifact_type, raw_path in artifact_paths.items():
                resolved = str(Path(raw_path).resolve())
                existing = paths.get(resolved)
                if existing is not None and existing["tenant_id"] != identity.tenant_id:
                    raise ValueError(
                        f"tenant path collision: {resolved} is already bound to "
                        f"{existing['tenant_id']}"
                    )
                paths[resolved] = {
                    "tenant_id": identity.tenant_id,
                    "client_id": identity.client_id,
                    "artifact_type": artifact_type,
                }
            self._write(payload)

    def bind_artifact(
        self,
        identity: TenantIdentity,
        *,
        artifact_type: str,
        artifact_key: str,
        proof_hash: str,
        bound_at: str,
        path: str | Path | None = None,
    ) -> TenantArtifactBinding:
        binding = TenantArtifactBinding(
            artifact_type=artifact_type,
            artifact_key=artifact_key,
            path=None if path is None else str(Path(path).resolve()),
            proof_hash=proof_hash,
            bound_at=bound_at,
        )
        with private_file_lock(self.lock_path):
            payload = self._read()
            self._assert_identity(payload, identity)
            if binding.path is not None:
                paths = payload.setdefault("paths", {})
                existing = paths.get(binding.path)
                if existing is not None and existing["tenant_id"] != identity.tenant_id:
                    raise ValueError("tenant path collision")
                paths[binding.path] = {
                    "tenant_id": identity.tenant_id,
                    "client_id": identity.client_id,
                    "artifact_type": artifact_type,
                }
            proofs = payload.setdefault("proofs", {})
            existing_proof = proofs.get(binding.proof_hash)
            if existing_proof is not None and existing_proof["tenant_id"] != identity.tenant_id:
                raise ValueError("tenant proof collision")
            proofs[binding.proof_hash] = {
                "tenant_id": identity.tenant_id,
                "client_id": identity.client_id,
                "artifact_type": artifact_type,
                "artifact_key": artifact_key,
                "path": binding.path,
                "binding_hash": binding.binding_hash,
            }
            self._write(payload)
        return binding

    def assert_path_tenant(self, identity: TenantIdentity, path: str | Path) -> None:
        payload = self._read()
        row = payload.get("paths", {}).get(str(Path(path).resolve()))
        if row is None or row["tenant_id"] != identity.tenant_id:
            raise ValueError("artifact path is not bound to tenant")

    def assert_proof_tenant(self, identity: TenantIdentity, proof_hash: str) -> None:
        proof = normalize_sha256("proof_hash", proof_hash)
        payload = self._read()
        row = payload.get("proofs", {}).get(proof)
        if row is None or row["tenant_id"] != identity.tenant_id:
            raise ValueError("artifact proof is not bound to tenant")

    def identity_for_client_id(self, client_id: str) -> TenantIdentity:
        client = _text("client_id", client_id)
        payload = self._read()
        matches = [
            (tenant_id, row)
            for tenant_id, row in payload.get("tenants", {}).items()
            if row.get("client_id") == client
        ]
        if len(matches) != 1:
            raise ValueError("client_id does not resolve to exactly one tenant")
        tenant_id, row = matches[0]
        return TenantIdentity(
            tenant_id=tenant_id,
            client_id=client,
            namespace=row["namespace"],
            created_at=row["created_at"],
        )

    def tenant_id_for_path(self, path: str | Path) -> str:
        payload = self._read()
        row = payload.get("paths", {}).get(str(Path(path).resolve()))
        if row is None:
            raise ValueError("artifact path is not bound to any tenant")
        return row["tenant_id"]

    def identity_for_path(self, path: str | Path) -> TenantIdentity:
        tenant_id = self.tenant_id_for_path(path)
        payload = self._read()
        row = payload["tenants"][tenant_id]
        return TenantIdentity(
            tenant_id=tenant_id,
            client_id=row["client_id"],
            namespace=row["namespace"],
            created_at=row["created_at"],
        )

    def state_hash(self) -> str | None:
        if not self.path.exists():
            return None
        return canonical_hash(self._read())


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_tenant_ledger(identity: TenantIdentity, path: str | Path) -> str:
    ledger = LocalBundleStore(path).load()
    if ledger is None:
        raise ValueError("tenant ledger is empty")
    client_ids = {record.finding.client_id for record in ledger.records()}
    if client_ids and client_ids != {identity.client_id}:
        raise ValueError("ledger contains cross-tenant client ids")
    return file_sha256(path)


def validate_tenant_receipts(identity: TenantIdentity, path: str | Path) -> str:
    receipts = CletricsReceiptRegistry(path).receipts()
    if receipts and {receipt.client_id for receipt in receipts} != {identity.client_id}:
        raise ValueError("Cletrics registry contains cross-tenant client ids")
    return file_sha256(path)


def validate_tenant_assurance_report(identity: TenantIdentity, path: str | Path) -> str:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("client_id") != identity.client_id:
        raise ValueError("assurance report client_id does not match tenant")
    proof = payload.get("proof_hash")
    if not isinstance(proof, str):
        raise ValueError("assurance report proof hash missing")
    normalize_sha256("assurance_report.proof_hash", proof)
    canonical = {key: value for key, value in payload.items() if key != "proof_hash"}
    if canonical_hash(canonical) != proof:
        raise ValueError("assurance report proof hash mismatch")
    return proof


def bind_managed_tenant_artifact(
    registry: TenantBindingRegistry,
    identity: TenantIdentity,
    *,
    artifact_type: str,
    artifact_key: str,
    proof_hash: str,
    path: str | Path | None,
    bound_at: str,
) -> TenantArtifactBinding:
    return registry.bind_artifact(
        identity,
        artifact_type=artifact_type,
        artifact_key=artifact_key,
        proof_hash=proof_hash,
        path=path,
        bound_at=bound_at,
    )


def find_tenant_registry(start: str | Path) -> TenantBindingRegistry | None:
    path = Path(start).resolve()
    cursor = path if path.is_dir() else path.parent
    for parent in (cursor, *cursor.parents):
        candidate = parent / ".recoveryworks-tenant-bindings.json"
        if candidate.is_file():
            return TenantBindingRegistry(candidate)
    return None


def bind_existing_tenant_output(
    *,
    source_path: str | Path,
    output_path: str | Path,
    artifact_type: str,
    artifact_key: str,
    proof_hash: str,
    bound_at: str,
) -> TenantArtifactBinding | None:
    registry = find_tenant_registry(source_path)
    if registry is None:
        return None
    identity = registry.identity_for_path(source_path)
    registry.reserve_paths(
        identity,
        artifact_paths={artifact_type: output_path},
    )
    return registry.bind_artifact(
        identity,
        artifact_type=artifact_type,
        artifact_key=artifact_key,
        proof_hash=proof_hash,
        path=output_path,
        bound_at=bound_at,
    )
