"""Supply-chain inventory, attestation inputs, and release security gate.

This layer prepares and verifies security artifacts only. It does not sign,
publish, push images, call registries, or run vulnerability scanners.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import re
from typing import Any, Mapping

from recoveryworks.container_build import ContainerBuildManifest
from recoveryworks.models import (
    canonical_hash,
    freeze_json,
    normalize_git_commit_sha,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)
from recoveryworks.release_control import RecoveryWorksReleaseManifest


_IMAGE_RE = re.compile(r"^[^@\s]+@sha256:([0-9a-f]{64})$")


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


def _tree_hash(root: Path) -> tuple[str, int]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"source root must be a directory: {root}")
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        relative = path.relative_to(root).as_posix()
        if "__pycache__" in path.parts or relative.endswith(".pyc"):
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"runtime source root contains unsafe path: {path}")
        raw = path.read_bytes()
        rows.append({
            "path": relative,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
        })
    if not rows:
        raise ValueError(f"source root is empty: {root}")
    return canonical_hash(rows), len(rows)


@dataclass(frozen=True)
class SupplyChainComponent:
    component_type: str
    name: str
    version: str
    digest: str
    source: str
    file_count: int | None = None

    def __post_init__(self) -> None:
        for name in ("component_type", "name", "version", "source"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        object.__setattr__(self, "digest", normalize_sha256("digest", self.digest))
        if self.file_count is not None and (
            type(self.file_count) is not int or self.file_count <= 0
        ):
            raise ValueError("file_count must be a positive integer when present")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class RecoveryWorksSBOM:
    sbom_id: str
    release_id: str
    release_proof_hash: str
    source_commit: str
    container_image_digest: str
    container_build_manifest_proof_hash: str
    components: tuple[SupplyChainComponent, ...]
    generated_at: str
    format_name: str = "RECOVERYWORKS-SBOM"
    format_version: str = "1"

    def __post_init__(self) -> None:
        for name in ("release_id", "format_name", "format_version"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        object.__setattr__(
            self, "release_proof_hash",
            normalize_sha256("release_proof_hash", self.release_proof_hash)
        )
        object.__setattr__(
            self, "source_commit",
            normalize_git_commit_sha("source_commit", self.source_commit)
        )
        object.__setattr__(
            self, "container_image_digest",
            normalize_sha256("container_image_digest", self.container_image_digest)
        )
        object.__setattr__(
            self, "container_build_manifest_proof_hash",
            normalize_sha256(
                "container_build_manifest_proof_hash",
                self.container_build_manifest_proof_hash,
            )
        )
        components = tuple(sorted(self.components, key=lambda item: (
            item.component_type, item.name, item.version, item.digest
        )))
        if len({item.proof_hash for item in components}) != len(components):
            raise ValueError("SBOM contains duplicate components")
        required_types = {item.component_type for item in components}
        if "container-base" not in required_types or "source-root" not in required_types:
            raise ValueError("SBOM must include base image and source roots")
        object.__setattr__(self, "components", components)
        object.__setattr__(
            self, "generated_at",
            normalize_utc_timestamp("generated_at", self.generated_at)
        )
        expected = "recoveryworks-sbom:" + canonical_hash(self._identity())
        if self.sbom_id != expected:
            raise ValueError("sbom_id does not bind SBOM")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "source_commit": self.source_commit,
            "container_image_digest": self.container_image_digest,
            "container_build_manifest_proof_hash":
                self.container_build_manifest_proof_hash,
            "components": [asdict(item) for item in self.components],
            "generated_at": self.generated_at,
            "format_name": self.format_name,
            "format_version": self.format_version,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "sbom_id": self.sbom_id,
            "proof_hash": self.proof_hash,
        }


def build_release_sbom(
    release: RecoveryWorksReleaseManifest,
    build_manifest: ContainerBuildManifest,
    *,
    repository_root: str | Path,
    generated_at: str,
) -> RecoveryWorksSBOM:
    if release.source_commit != build_manifest.source_commit:
        raise ValueError("release/build source commit mismatch")
    if release.container_build_manifest_proof_hash != build_manifest.proof_hash:
        raise ValueError("release does not bind supplied build manifest")

    match = _IMAGE_RE.fullmatch(build_manifest.base_image_ref)
    if match is None:
        raise ValueError("build base image is not digest pinned")
    components: list[SupplyChainComponent] = [
        SupplyChainComponent(
            component_type="container-base",
            name=build_manifest.base_image_ref.split("@", 1)[0],
            version=build_manifest.base_image_ref.split("@", 1)[0].split(":", 1)[-1],
            digest=match.group(1),
            source="digest-pinned-container-base",
        )
    ]
    root = Path(repository_root)
    for source_root in build_manifest.runtime_source_roots:
        digest, count = _tree_hash(root / source_root)
        components.append(SupplyChainComponent(
            component_type="source-root",
            name=source_root,
            version=release.source_commit,
            digest=digest,
            source="repository-runtime-source",
            file_count=count,
        ))
    for dependency in build_manifest.third_party_runtime_dependencies:
        # The current lock is intentionally empty. Future lock entries must be
        # exact and hashed before they may reach this branch.
        components.append(SupplyChainComponent(
            component_type="python-runtime-dependency",
            name=dependency,
            version=dependency,
            digest=hashlib.sha256(dependency.encode("utf-8")).hexdigest(),
            source="requirements.production.lock",
        ))

    identity = {
        "schema": 1,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "source_commit": release.source_commit,
        "container_image_digest": release.container_image_digest,
        "container_build_manifest_proof_hash": build_manifest.proof_hash,
        "components": [
            asdict(item) for item in sorted(
                components, key=lambda item: (
                    item.component_type, item.name, item.version, item.digest
                )
            )
        ],
        "generated_at": normalize_utc_timestamp("generated_at", generated_at),
        "format_name": "RECOVERYWORKS-SBOM",
        "format_version": "1",
    }
    return RecoveryWorksSBOM(
        sbom_id="recoveryworks-sbom:" + canonical_hash(identity),
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        source_commit=release.source_commit,
        container_image_digest=release.container_image_digest,
        container_build_manifest_proof_hash=build_manifest.proof_hash,
        components=tuple(components),
        generated_at=generated_at,
    )


@dataclass(frozen=True)
class ContainerAttestationInput:
    attestation_id: str
    release_id: str
    release_proof_hash: str
    source_commit: str
    container_image_ref: str
    container_image_digest: str
    container_build_manifest_proof_hash: str
    sbom_proof_hash: str
    predicate_type: str
    generated_at: str
    signing_performed: bool = False
    published: bool = False

    def __post_init__(self) -> None:
        for name in ("release_id", "predicate_type"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "release_proof_hash",
            "container_build_manifest_proof_hash",
            "sbom_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self, "source_commit",
            normalize_git_commit_sha("source_commit", self.source_commit)
        )
        match = _IMAGE_RE.fullmatch(self.container_image_ref)
        if match is None:
            raise ValueError("attestation image must be digest pinned")
        digest = normalize_sha256(
            "container_image_digest", self.container_image_digest
        )
        if match.group(1) != digest:
            raise ValueError("attestation image ref/digest mismatch")
        object.__setattr__(self, "container_image_digest", digest)
        object.__setattr__(
            self, "generated_at",
            normalize_utc_timestamp("generated_at", self.generated_at)
        )
        if self.signing_performed or self.published:
            raise ValueError("step 17a cannot sign or publish attestations")
        expected = "recoveryworks-attestation-input:" + canonical_hash(
            self._identity()
        )
        if self.attestation_id != expected:
            raise ValueError("attestation_id does not bind attestation input")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "source_commit": self.source_commit,
            "container_image_ref": self.container_image_ref,
            "container_image_digest": self.container_image_digest,
            "container_build_manifest_proof_hash":
                self.container_build_manifest_proof_hash,
            "sbom_proof_hash": self.sbom_proof_hash,
            "predicate_type": self.predicate_type,
            "generated_at": self.generated_at,
            "signing_performed": False,
            "published": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_container_attestation_input(
    release: RecoveryWorksReleaseManifest,
    build_manifest: ContainerBuildManifest,
    sbom: RecoveryWorksSBOM,
    *,
    generated_at: str,
) -> ContainerAttestationInput:
    if sbom.release_id != release.release_id or sbom.release_proof_hash != release.proof_hash:
        raise ValueError("SBOM does not bind release")
    if build_manifest.proof_hash != release.container_build_manifest_proof_hash:
        raise ValueError("build manifest does not bind release")
    identity = {
        "schema": 1,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "source_commit": release.source_commit,
        "container_image_ref": release.container_image_ref,
        "container_image_digest": release.container_image_digest,
        "container_build_manifest_proof_hash": build_manifest.proof_hash,
        "sbom_proof_hash": sbom.proof_hash,
        "predicate_type": "https://slsa.dev/provenance/v1",
        "generated_at": normalize_utc_timestamp("generated_at", generated_at),
        "signing_performed": False,
        "published": False,
    }
    return ContainerAttestationInput(
        attestation_id="recoveryworks-attestation-input:" + canonical_hash(identity),
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        source_commit=release.source_commit,
        container_image_ref=release.container_image_ref,
        container_image_digest=release.container_image_digest,
        container_build_manifest_proof_hash=build_manifest.proof_hash,
        sbom_proof_hash=sbom.proof_hash,
        predicate_type="https://slsa.dev/provenance/v1",
        generated_at=generated_at,
        signing_performed=False,
        published=False,
    )


@dataclass(frozen=True)
class VulnerabilityScanReceipt:
    scan_id: str
    container_image_digest: str
    scanner_id: str
    scanner_version: str
    vulnerability_database_id: str
    vulnerability_database_digest: str
    scanned_at: str
    severity_counts: Mapping[str, int]
    source_hash: str
    source_locator: str
    verified: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "container_image_digest",
            normalize_sha256("container_image_digest", self.container_image_digest)
        )
        for name in (
            "scanner_id",
            "scanner_version",
            "vulnerability_database_id",
            "source_locator",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        object.__setattr__(
            self, "vulnerability_database_digest",
            normalize_sha256(
                "vulnerability_database_digest",
                self.vulnerability_database_digest,
            )
        )
        object.__setattr__(
            self, "scanned_at",
            normalize_utc_timestamp("scanned_at", self.scanned_at)
        )
        allowed = ("critical", "high", "medium", "low", "unknown")
        counts: dict[str, int] = {}
        for key in allowed:
            value = self.severity_counts.get(key, 0)
            if type(value) is not int or value < 0:
                raise ValueError(f"severity_counts.{key} must be non-negative integer")
            counts[key] = value
        if set(self.severity_counts) - set(allowed):
            raise ValueError("vulnerability receipt has unsupported severity")
        object.__setattr__(
            self, "severity_counts",
            freeze_json(counts, name="severity_counts")
        )
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        expected = "recoveryworks-vulnerability-scan:" + canonical_hash(
            self._identity()
        )
        if self.scan_id != expected:
            raise ValueError("scan_id does not bind vulnerability scan receipt")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "container_image_digest": self.container_image_digest,
            "scanner_id": self.scanner_id,
            "scanner_version": self.scanner_version,
            "vulnerability_database_id": self.vulnerability_database_id,
            "vulnerability_database_digest": self.vulnerability_database_digest,
            "scanned_at": self.scanned_at,
            "severity_counts": dict(self.severity_counts),
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": self.verified,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_vulnerability_scan_receipt(
    *,
    container_image_digest: str,
    scanner_id: str,
    scanner_version: str,
    vulnerability_database_id: str,
    vulnerability_database_digest: str,
    scanned_at: str,
    severity_counts: Mapping[str, int],
    source_hash: str,
    source_locator: str,
    verified: bool,
) -> VulnerabilityScanReceipt:
    normalized_digest = normalize_sha256(
        "container_image_digest", container_image_digest
    )
    normalized_db = normalize_sha256(
        "vulnerability_database_digest", vulnerability_database_digest
    )
    normalized_source = normalize_source_hash(source_hash)
    normalized_time = normalize_utc_timestamp("scanned_at", scanned_at)
    normalized_counts = {
        key: severity_counts.get(key, 0)
        for key in ("critical", "high", "medium", "low", "unknown")
    }
    identity = {
        "schema": 1,
        "container_image_digest": normalized_digest,
        "scanner_id": _text("scanner_id", scanner_id),
        "scanner_version": _text("scanner_version", scanner_version),
        "vulnerability_database_id": _text(
            "vulnerability_database_id", vulnerability_database_id
        ),
        "vulnerability_database_digest": normalized_db,
        "scanned_at": normalized_time,
        "severity_counts": normalized_counts,
        "source_hash": normalized_source,
        "source_locator": _text("source_locator", source_locator),
        "verified": verified,
    }
    return VulnerabilityScanReceipt(
        scan_id="recoveryworks-vulnerability-scan:" + canonical_hash(identity),
        container_image_digest=normalized_digest,
        scanner_id=scanner_id,
        scanner_version=scanner_version,
        vulnerability_database_id=vulnerability_database_id,
        vulnerability_database_digest=normalized_db,
        scanned_at=normalized_time,
        severity_counts=normalized_counts,
        source_hash=normalized_source,
        source_locator=source_locator,
        verified=verified,
    )


@dataclass(frozen=True)
class ReleaseSecurityPolicy:
    max_critical: int = 0
    max_high: int = 0
    verified_scan_required: bool = True

    def __post_init__(self) -> None:
        for name in ("max_critical", "max_high"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.verified_scan_required is not True:
            raise ValueError("release security gate requires verified scan receipts")


@dataclass(frozen=True)
class ReleaseSecurityGate:
    gate_id: str
    release_id: str
    release_proof_hash: str
    sbom_proof_hash: str
    attestation_input_proof_hash: str
    vulnerability_scan_proof_hash: str
    container_image_digest: str
    policy: ReleaseSecurityPolicy
    created_at: str
    security_ready: bool
    signing_performed: bool = False
    attestation_published: bool = False
    image_published: bool = False

    def __post_init__(self) -> None:
        for name in ("release_id",):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "release_proof_hash",
            "sbom_proof_hash",
            "attestation_input_proof_hash",
            "vulnerability_scan_proof_hash",
            "container_image_digest",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self, "created_at",
            normalize_utc_timestamp("created_at", self.created_at)
        )
        if self.security_ready is not True:
            raise ValueError("release security gate must satisfy policy")
        if self.signing_performed or self.attestation_published or self.image_published:
            raise ValueError("step 17a cannot sign/publish release artifacts")
        expected = "recoveryworks-release-security-gate:" + canonical_hash(
            self._identity()
        )
        if self.gate_id != expected:
            raise ValueError("gate_id does not bind release security gate")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "sbom_proof_hash": self.sbom_proof_hash,
            "attestation_input_proof_hash": self.attestation_input_proof_hash,
            "vulnerability_scan_proof_hash": self.vulnerability_scan_proof_hash,
            "container_image_digest": self.container_image_digest,
            "policy": asdict(self.policy),
            "created_at": self.created_at,
            "security_ready": True,
            "signing_performed": False,
            "attestation_published": False,
            "image_published": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "gate_id": self.gate_id,
            "proof_hash": self.proof_hash,
            "state": "SECURITY_GATE_READY",
        }


def build_release_security_gate(
    release: RecoveryWorksReleaseManifest,
    sbom: RecoveryWorksSBOM,
    attestation: ContainerAttestationInput,
    scan: VulnerabilityScanReceipt,
    *,
    policy: ReleaseSecurityPolicy = ReleaseSecurityPolicy(),
    created_at: str,
) -> ReleaseSecurityGate:
    if sbom.release_id != release.release_id or sbom.release_proof_hash != release.proof_hash:
        raise ValueError("SBOM does not bind release")
    if attestation.release_id != release.release_id:
        raise ValueError("attestation input release mismatch")
    if attestation.release_proof_hash != release.proof_hash:
        raise ValueError("attestation input release proof mismatch")
    if attestation.sbom_proof_hash != sbom.proof_hash:
        raise ValueError("attestation input SBOM mismatch")
    if scan.container_image_digest != release.container_image_digest:
        raise ValueError("vulnerability scan image digest mismatch")
    if policy.verified_scan_required and not scan.verified:
        raise ValueError("vulnerability scan receipt must be verified")
    if scan.severity_counts["critical"] > policy.max_critical:
        raise ValueError("critical vulnerability threshold exceeded")
    if scan.severity_counts["high"] > policy.max_high:
        raise ValueError("high vulnerability threshold exceeded")
    identity = {
        "schema": 1,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "sbom_proof_hash": sbom.proof_hash,
        "attestation_input_proof_hash": attestation.proof_hash,
        "vulnerability_scan_proof_hash": scan.proof_hash,
        "container_image_digest": release.container_image_digest,
        "policy": asdict(policy),
        "created_at": normalize_utc_timestamp("created_at", created_at),
        "security_ready": True,
        "signing_performed": False,
        "attestation_published": False,
        "image_published": False,
    }
    return ReleaseSecurityGate(
        gate_id="recoveryworks-release-security-gate:" + canonical_hash(identity),
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        sbom_proof_hash=sbom.proof_hash,
        attestation_input_proof_hash=attestation.proof_hash,
        vulnerability_scan_proof_hash=scan.proof_hash,
        container_image_digest=release.container_image_digest,
        policy=policy,
        created_at=created_at,
        security_ready=True,
        signing_performed=False,
        attestation_published=False,
        image_published=False,
    )
