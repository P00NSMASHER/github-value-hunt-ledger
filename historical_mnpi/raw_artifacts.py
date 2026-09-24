"""Content-addressed raw-artifact retention for historical MNPI research.

Step 2 separates retained source bytes from normalized facts.

The store accepts bytes only from an already-registered, already-public source.
It never fetches URLs itself. The exact bytes must hash to the SourceRecord
SHA-256 before they can be retained.

Important boundary:
- local filesystem retention is APPLICATION_ENFORCED_APPEND_ONLY, not WORM;
- provider-verified immutability is a separate, explicit assertion;
- manifests contain hashes/metadata only, never raw source bytes;
- future normalized facts should reference SourceArtifactRef objects rather than
  embedding copied source documents.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Iterable

from .source_registry import SourceRecord, SourceRegistry, USAGE_SCOPE, canonical_hash


_SCHEMA_VERSION = 1
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MEDIA_TYPE_RE = re.compile(r"^[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+$")


class ArtifactImmutability(str, Enum):
    APPLICATION_ENFORCED_APPEND_ONLY = "APPLICATION_ENFORCED_APPEND_ONLY"
    PROVIDER_VERIFIED_IMMUTABLE = "PROVIDER_VERIFIED_IMMUTABLE"


class SourceLocatorKind(str, Enum):
    PAGE = "PAGE"
    PARAGRAPH = "PARAGRAPH"
    TABLE = "TABLE"
    CSV_ROW = "CSV_ROW"
    JSON_POINTER = "JSON_POINTER"
    TEXT_RANGE = "TEXT_RANGE"
    ARCHIVE_MEMBER = "ARCHIVE_MEMBER"
    OTHER = "OTHER"


def _iso(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include timezone")
    return text


def _dt(name: str, value: str) -> datetime:
    return datetime.fromisoformat(_iso(name, value).replace("Z", "+00:00"))


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clean_filename(value: str | None) -> str | None:
    if value is None:
        return None
    name = value.strip()
    if not name:
        return None
    if name != Path(name).name or name in {".", ".."}:
        raise ValueError("original_filename must be a basename only")
    return name


@dataclass(frozen=True)
class RawArtifactRecord:
    source_id: str
    source_proof_hash: str
    artifact_id: str
    sha256: str
    size_bytes: int
    media_type: str
    storage_uri: str
    acquired_at: str
    stored_at: str
    immutability: ArtifactImmutability
    provider_attestation_hash: str | None = None
    original_filename: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        source_proof = self.source_proof_hash.strip().lower()
        if not _SHA256_RE.fullmatch(source_proof):
            raise ValueError("source_proof_hash must be SHA-256")
        object.__setattr__(self, "source_proof_hash", source_proof)
        digest = self.sha256.strip().lower()
        if not _SHA256_RE.fullmatch(digest):
            raise ValueError("sha256 must be a lowercase 64-character SHA-256")
        object.__setattr__(self, "sha256", digest)

        expected_artifact_id = "sha256:" + digest
        if self.artifact_id != expected_artifact_id:
            raise ValueError("artifact_id must equal sha256:<content digest>")
        if type(self.size_bytes) is not int or self.size_bytes < 0:
            raise ValueError("size_bytes must be a non-negative integer")
        if not _MEDIA_TYPE_RE.fullmatch(self.media_type):
            raise ValueError("media_type must be a valid type/subtype token")
        expected_storage_uri = f"cas://sha256/{digest[:2]}/{digest}"
        if self.storage_uri != expected_storage_uri:
            raise ValueError("storage_uri must exactly match artifact SHA-256")
        acquired = _dt("acquired_at", self.acquired_at)
        stored = _dt("stored_at", self.stored_at)
        if stored < acquired:
            raise ValueError("stored_at cannot precede acquired_at")

        object.__setattr__(
            self,
            "original_filename",
            _clean_filename(self.original_filename),
        )

        if self.provider_attestation_hash is not None:
            attestation = self.provider_attestation_hash.strip().lower()
            if not _SHA256_RE.fullmatch(attestation):
                raise ValueError(
                    "provider_attestation_hash must be a lowercase SHA-256"
                )
            object.__setattr__(
                self,
                "provider_attestation_hash",
                attestation,
            )

        if (
            self.immutability
            is ArtifactImmutability.PROVIDER_VERIFIED_IMMUTABLE
            and self.provider_attestation_hash is None
        ):
            raise ValueError(
                "provider-verified immutability requires provider_attestation_hash"
            )

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self.to_dict(include_proof_hash=False))

    def to_dict(self, *, include_proof_hash: bool = True) -> dict:
        body = {
            "schema": _SCHEMA_VERSION,
            "usage_scope": USAGE_SCOPE,
            "source_id": self.source_id,
            "source_proof_hash": self.source_proof_hash,
            "artifact_id": self.artifact_id,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "media_type": self.media_type,
            "storage_uri": self.storage_uri,
            "acquired_at": self.acquired_at,
            "stored_at": self.stored_at,
            "immutability": self.immutability.value,
            "provider_attestation_hash": self.provider_attestation_hash,
            "original_filename": self.original_filename,
        }
        if include_proof_hash:
            body["proof_hash"] = canonical_hash(body)
        return body


@dataclass(frozen=True)
class SourceArtifactRef:
    """Reference from a future normalized fact back to exact retained bytes."""

    source_id: str
    source_proof_hash: str
    artifact_id: str
    artifact_sha256: str
    artifact_record_proof_hash: str
    locator_kind: SourceLocatorKind
    locator: str
    excerpt_sha256: str | None = None

    def __post_init__(self) -> None:
        source_proof = self.source_proof_hash.strip().lower()
        if not _SHA256_RE.fullmatch(source_proof):
            raise ValueError("source_proof_hash must be SHA-256")
        object.__setattr__(self, "source_proof_hash", source_proof)
        digest = self.artifact_sha256.strip().lower()
        if not _SHA256_RE.fullmatch(digest):
            raise ValueError("artifact_sha256 must be SHA-256")
        object.__setattr__(self, "artifact_sha256", digest)
        if self.artifact_id != "sha256:" + digest:
            raise ValueError("artifact_id does not match artifact_sha256")
        artifact_proof = self.artifact_record_proof_hash.strip().lower()
        if not _SHA256_RE.fullmatch(artifact_proof):
            raise ValueError("artifact_record_proof_hash must be SHA-256")
        object.__setattr__(
            self,
            "artifact_record_proof_hash",
            artifact_proof,
        )
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.locator.strip():
            raise ValueError("locator is required")
        if self.excerpt_sha256 is not None:
            excerpt = self.excerpt_sha256.strip().lower()
            if not _SHA256_RE.fullmatch(excerpt):
                raise ValueError("excerpt_sha256 must be SHA-256")
            object.__setattr__(self, "excerpt_sha256", excerpt)

    @property
    def artifact_identity_hash(self) -> str:
        return canonical_hash({
            "schema": _SCHEMA_VERSION,
            "usage_scope": USAGE_SCOPE,
            "source_id": self.source_id,
            "source_proof_hash": self.source_proof_hash,
            "artifact_id": self.artifact_id,
            "artifact_sha256": self.artifact_sha256,
            "artifact_record_proof_hash": self.artifact_record_proof_hash,
        })

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": _SCHEMA_VERSION,
            "usage_scope": USAGE_SCOPE,
            "source_id": self.source_id,
            "source_proof_hash": self.source_proof_hash,
            "artifact_id": self.artifact_id,
            "artifact_sha256": self.artifact_sha256,
            "artifact_record_proof_hash": self.artifact_record_proof_hash,
            "locator_kind": self.locator_kind.value,
            "locator": self.locator,
            "excerpt_sha256": self.excerpt_sha256,
        })


def same_retained_artifact(left: SourceArtifactRef, right: SourceArtifactRef) -> bool:
    """True when two refs point at the same retained bytes/provenance, ignoring locator."""
    return left.artifact_identity_hash == right.artifact_identity_hash


@dataclass(frozen=True)
class RawArtifactManifest:
    source_registry_hash: str
    artifacts: tuple[RawArtifactRecord, ...]
    created_at: str
    created_by: str
    manifest_hash: str

    def __post_init__(self) -> None:
        if not _SHA256_RE.fullmatch(self.source_registry_hash):
            raise ValueError("source_registry_hash must be SHA-256")
        if not self.created_by.strip():
            raise ValueError("created_by is required")
        _iso("created_at", self.created_at)
        if not self.artifacts:
            raise ValueError("raw artifact manifest requires artifacts")

    def integrity_body(self) -> dict:
        return {
            "schema": _SCHEMA_VERSION,
            "usage_scope": USAGE_SCOPE,
            "source_registry_hash": self.source_registry_hash,
            "artifacts": [
                item.to_dict()
                for item in sorted(
                    self.artifacts,
                    key=lambda item: (item.source_id, item.artifact_id),
                )
            ],
            "created_at": self.created_at,
            "created_by": self.created_by,
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.manifest_hash:
            raise ValueError("raw artifact manifest hash mismatch")

    def resolve_ref(self, ref: SourceArtifactRef) -> RawArtifactRecord:
        for item in self.artifacts:
            if (
                item.source_id == ref.source_id
                and item.source_proof_hash == ref.source_proof_hash
                and item.artifact_id == ref.artifact_id
                and item.sha256 == ref.artifact_sha256
                and item.proof_hash == ref.artifact_record_proof_hash
            ):
                return item
        raise ValueError("source artifact reference is not in manifest")

    def to_dict(self) -> dict:
        return {
            **self.integrity_body(),
            "manifest_hash": self.manifest_hash,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        )


class LocalContentAddressedArtifactStore:
    """Application-enforced append-only local CAS.

    This is suitable for deterministic research/test retention. It does not claim
    OS/filesystem storage is provider-level WORM. A later adapter may record
    PROVIDER_VERIFIED_IMMUTABLE only with an external attestation hash.
    """

    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, digest: str) -> Path:
        if not _SHA256_RE.fullmatch(digest):
            raise ValueError("invalid artifact digest")
        return self.root / "sha256" / digest[:2] / digest

    def retain(
        self,
        registry: SourceRegistry,
        source: SourceRecord,
        raw_bytes: bytes,
        *,
        media_type: str,
        acquired_at: str,
        stored_at: str,
        original_filename: str | None = None,
    ) -> RawArtifactRecord:
        if not isinstance(registry, SourceRegistry):
            raise TypeError("registry must be a SourceRegistry")
        registered = registry.get(source.source_id)
        if registered.proof_hash != source.proof_hash:
            raise ValueError(
                "source record does not match the registered source proof"
            )
        if not isinstance(raw_bytes, bytes):
            raise TypeError("raw_bytes must be bytes")
        if source.public_release_confirmed is not True:
            raise ValueError("cannot retain nonpublic source in historical corpus")

        digest = _hash_bytes(raw_bytes)
        if digest != source.sha256:
            raise ValueError(
                "raw artifact bytes do not match registered source SHA-256"
            )

        # Validate the full custody record before any filesystem mutation.
        # A rejected ingestion attempt must not leave bytes behind.
        record = RawArtifactRecord(
            source_id=source.source_id,
            source_proof_hash=source.proof_hash,
            artifact_id="sha256:" + digest,
            sha256=digest,
            size_bytes=len(raw_bytes),
            media_type=media_type,
            storage_uri=f"cas://sha256/{digest[:2]}/{digest}",
            acquired_at=_iso("acquired_at", acquired_at),
            stored_at=_iso("stored_at", stored_at),
            immutability=ArtifactImmutability.APPLICATION_ENFORCED_APPEND_ONLY,
            original_filename=original_filename,
        )

        target = self._path(digest)
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            existing = target.read_bytes()
            if _hash_bytes(existing) != digest or existing != raw_bytes:
                raise ValueError("content-addressed artifact collision/tamper")
        else:
            fd, temporary_name = tempfile.mkstemp(
                dir=str(target.parent),
                prefix=".artifact-",
            )
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(raw_bytes)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary_name, target)
                try:
                    target.chmod(0o444)
                except OSError:
                    # Read-only chmod is defense in depth only; content addressing
                    # and hash verification remain the actual application guard.
                    pass
            finally:
                if os.path.exists(temporary_name):
                    os.unlink(temporary_name)

        return record

    def read(self, record: RawArtifactRecord) -> bytes:
        path = self._path(record.sha256)
        if not path.is_file():
            raise FileNotFoundError(record.storage_uri)
        raw = path.read_bytes()
        if len(raw) != record.size_bytes:
            raise ValueError("retained artifact size mismatch")
        if _hash_bytes(raw) != record.sha256:
            raise ValueError("retained artifact hash mismatch")
        return raw


def freeze_raw_artifact_manifest(
    registry: SourceRegistry,
    artifacts: Iterable[RawArtifactRecord],
    *,
    created_at: str,
    created_by: str,
) -> RawArtifactManifest:
    created = _iso("created_at", created_at)
    if not created_by.strip():
        raise ValueError("created_by is required")

    artifact_tuple = tuple(
        sorted(artifacts, key=lambda item: (item.source_id, item.artifact_id))
    )
    if not artifact_tuple:
        raise ValueError("raw artifact manifest requires artifacts")

    registered = {item.source_id: item for item in registry.all()}
    observed: dict[str, RawArtifactRecord] = {}

    for artifact in artifact_tuple:
        if artifact.source_id in observed:
            raise ValueError(
                "raw artifact manifest requires exactly one artifact per source_id"
            )
        source = registered.get(artifact.source_id)
        if source is None:
            raise ValueError(
                "raw artifact references source not present in source registry"
            )
        if artifact.source_proof_hash != source.proof_hash:
            raise ValueError("raw artifact source proof does not match source registry")
        if artifact.sha256 != source.sha256:
            raise ValueError("raw artifact hash does not match source registry")
        if _dt("artifact.stored_at", artifact.stored_at) > _dt(
            "manifest.created_at", created
        ):
            raise ValueError("artifact cannot postdate raw artifact manifest")
        observed[artifact.source_id] = artifact

    if set(observed) != set(registered):
        missing = sorted(set(registered) - set(observed))
        extra = sorted(set(observed) - set(registered))
        raise ValueError(
            f"raw artifact/source registry set mismatch; missing={missing}; extra={extra}"
        )

    body = {
        "schema": _SCHEMA_VERSION,
        "usage_scope": USAGE_SCOPE,
        "source_registry_hash": registry.registry_hash,
        "artifacts": [item.to_dict() for item in artifact_tuple],
        "created_at": created,
        "created_by": created_by.strip(),
    }
    return RawArtifactManifest(
        source_registry_hash=registry.registry_hash,
        artifacts=artifact_tuple,
        created_at=created,
        created_by=created_by.strip(),
        manifest_hash=canonical_hash(body),
    )


def verify_raw_artifact_manifest(
    manifest: RawArtifactManifest,
    registry: SourceRegistry,
) -> None:
    manifest.verify_integrity()
    if manifest.source_registry_hash != registry.registry_hash:
        raise ValueError("raw artifact manifest source registry mismatch")

    registered = {item.source_id: item for item in registry.all()}
    if len(manifest.artifacts) != len(registered):
        raise ValueError("raw artifact manifest is incomplete")

    seen: set[str] = set()
    for artifact in manifest.artifacts:
        if artifact.source_id in seen:
            raise ValueError("duplicate source_id in raw artifact manifest")
        seen.add(artifact.source_id)
        source = registered.get(artifact.source_id)
        if (
            source is None
            or source.proof_hash != artifact.source_proof_hash
            or source.sha256 != artifact.sha256
        ):
            raise ValueError("raw artifact/source registry proof mismatch")

    if seen != set(registered):
        raise ValueError("raw artifact manifest source set mismatch")


__all__ = [
    "ArtifactImmutability",
    "LocalContentAddressedArtifactStore",
    "RawArtifactManifest",
    "RawArtifactRecord",
    "SourceArtifactRef",
    "SourceLocatorKind",
    "freeze_raw_artifact_manifest",
    "same_retained_artifact",
    "verify_raw_artifact_manifest",
]
