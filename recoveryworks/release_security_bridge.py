"""Standard SBOM export and external security-receipt verification."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from recoveryworks.models import (
    canonical_hash,
    freeze_json,
    normalize_git_commit_sha,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)
from recoveryworks.private_io import atomic_private_write
from recoveryworks.release_control import RecoveryWorksReleaseManifest
from recoveryworks.release_security import (
    ContainerAttestationInput,
    RecoveryWorksSBOM,
    ReleaseSecurityGate,
    VulnerabilityScanReceipt,
)


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


@dataclass(frozen=True)
class StandardSBOMExport:
    export_id: str
    release_id: str
    release_proof_hash: str
    recoveryworks_sbom_proof_hash: str
    format_name: str
    spec_version: str
    document_sha256: str
    generated_at: str

    def __post_init__(self) -> None:
        for name in ("release_id", "format_name", "spec_version"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "release_proof_hash",
            "recoveryworks_sbom_proof_hash",
            "document_sha256",
        ):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        object.__setattr__(
            self, "generated_at",
            normalize_utc_timestamp("generated_at", self.generated_at)
        )
        expected = "recoveryworks-standard-sbom:" + canonical_hash(self._identity())
        if self.export_id != expected:
            raise ValueError("export_id does not bind standard SBOM export")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "recoveryworks_sbom_proof_hash": self.recoveryworks_sbom_proof_hash,
            "format_name": self.format_name,
            "spec_version": self.spec_version,
            "document_sha256": self.document_sha256,
            "generated_at": self.generated_at,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def _cyclonedx_document(
    release: RecoveryWorksReleaseManifest,
    sbom: RecoveryWorksSBOM,
) -> dict[str, Any]:
    components = []
    for component in sbom.components:
        component_type = (
            "container"
            if component.component_type == "container-base"
            else "library"
        )
        properties = [
            {"name": "recoveryworks:component_type", "value": component.component_type},
            {"name": "recoveryworks:source", "value": component.source},
        ]
        if component.file_count is not None:
            properties.append(
                {"name": "recoveryworks:file_count", "value": str(component.file_count)}
            )
        components.append({
            "type": component_type,
            "bom-ref": component.proof_hash,
            "name": component.name,
            "version": component.version,
            "hashes": [{"alg": "SHA-256", "content": component.digest}],
            "properties": properties,
        })
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": "urn:uuid:" + sbom.proof_hash[:32],
        "version": 1,
        "metadata": {
            "timestamp": sbom.generated_at,
            "component": {
                "type": "application",
                "bom-ref": release.release_id,
                "name": "RecoveryWorks Cloud Pilot",
                "version": release.version,
                "hashes": [
                    {"alg": "SHA-256", "content": release.container_image_digest}
                ],
                "properties": [
                    {"name": "recoveryworks:release_proof_hash", "value": release.proof_hash},
                    {"name": "recoveryworks:source_commit", "value": release.source_commit},
                    {"name": "recoveryworks:build_manifest_proof_hash",
                     "value": release.container_build_manifest_proof_hash},
                ],
            },
        },
        "components": components,
    }


def write_cyclonedx_sbom(
    release: RecoveryWorksReleaseManifest,
    sbom: RecoveryWorksSBOM,
    *,
    path: str | Path,
) -> StandardSBOMExport:
    if sbom.release_id != release.release_id or sbom.release_proof_hash != release.proof_hash:
        raise ValueError("SBOM does not bind release")
    document = _cyclonedx_document(release, sbom)
    raw = (
        json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")
    digest = __import__("hashlib").sha256(raw).hexdigest()
    identity = {
        "schema": 1,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "recoveryworks_sbom_proof_hash": sbom.proof_hash,
        "format_name": "CycloneDX",
        "spec_version": "1.5",
        "document_sha256": digest,
        "generated_at": sbom.generated_at,
    }
    export = StandardSBOMExport(
        export_id="recoveryworks-standard-sbom:" + canonical_hash(identity),
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        recoveryworks_sbom_proof_hash=sbom.proof_hash,
        format_name="CycloneDX",
        spec_version="1.5",
        document_sha256=digest,
        generated_at=sbom.generated_at,
    )
    atomic_private_write(Path(path), raw)
    return export


@dataclass(frozen=True)
class ExternalSignatureVerificationReceipt:
    receipt_id: str
    release_id: str
    release_proof_hash: str
    container_image_digest: str
    signer_identity: str
    signature_algorithm: str
    signature_artifact_hash: str
    verified_at: str
    verifier_id: str
    source_hash: str
    source_locator: str
    verified: bool

    def __post_init__(self) -> None:
        for name in (
            "release_id", "signer_identity", "signature_algorithm",
            "verifier_id", "source_locator",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "release_proof_hash", "container_image_digest",
            "signature_artifact_hash",
        ):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        object.__setattr__(
            self, "verified_at", normalize_utc_timestamp("verified_at", self.verified_at)
        )
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if self.verified is not True:
            raise ValueError("signature verification receipt must be verified")
        expected = "recoveryworks-signature-verification:" + canonical_hash(
            self._identity()
        )
        if self.receipt_id != expected:
            raise ValueError("receipt_id does not bind signature verification")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "container_image_digest": self.container_image_digest,
            "signer_identity": self.signer_identity,
            "signature_algorithm": self.signature_algorithm,
            "signature_artifact_hash": self.signature_artifact_hash,
            "verified_at": self.verified_at,
            "verifier_id": self.verifier_id,
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": True,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


@dataclass(frozen=True)
class ExternalProvenanceVerificationReceipt:
    receipt_id: str
    release_id: str
    release_proof_hash: str
    container_image_digest: str
    source_commit: str
    container_build_manifest_proof_hash: str
    sbom_proof_hash: str
    predicate_type: str
    attestation_artifact_hash: str
    verified_at: str
    verifier_id: str
    source_hash: str
    source_locator: str
    verified: bool

    def __post_init__(self) -> None:
        for name in (
            "release_id", "predicate_type", "verifier_id", "source_locator"
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "release_proof_hash", "container_image_digest",
            "container_build_manifest_proof_hash", "sbom_proof_hash",
            "attestation_artifact_hash",
        ):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        object.__setattr__(
            self, "source_commit",
            normalize_git_commit_sha("source_commit", self.source_commit)
        )
        object.__setattr__(
            self, "verified_at", normalize_utc_timestamp("verified_at", self.verified_at)
        )
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if self.verified is not True:
            raise ValueError("provenance verification receipt must be verified")
        expected = "recoveryworks-provenance-verification:" + canonical_hash(
            self._identity()
        )
        if self.receipt_id != expected:
            raise ValueError("receipt_id does not bind provenance verification")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "container_image_digest": self.container_image_digest,
            "source_commit": self.source_commit,
            "container_build_manifest_proof_hash":
                self.container_build_manifest_proof_hash,
            "sbom_proof_hash": self.sbom_proof_hash,
            "predicate_type": self.predicate_type,
            "attestation_artifact_hash": self.attestation_artifact_hash,
            "verified_at": self.verified_at,
            "verifier_id": self.verifier_id,
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": True,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


@dataclass(frozen=True)
class VerifiedReleaseSecurityEvidence:
    evidence_id: str
    release_id: str
    release_proof_hash: str
    security_gate_proof_hash: str
    standard_sbom_export_proof_hash: str
    vulnerability_scan_proof_hash: str
    signature_verification_proof_hash: str
    provenance_verification_proof_hash: str
    container_image_digest: str
    source_commit: str
    verified: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "release_id", _text("release_id", self.release_id))
        for name in (
            "release_proof_hash", "security_gate_proof_hash",
            "standard_sbom_export_proof_hash", "vulnerability_scan_proof_hash",
            "signature_verification_proof_hash", "provenance_verification_proof_hash",
            "container_image_digest",
        ):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        object.__setattr__(
            self, "source_commit",
            normalize_git_commit_sha("source_commit", self.source_commit)
        )
        if self.verified is not True:
            raise ValueError("security evidence bundle must be verified")
        expected = "recoveryworks-verified-security-evidence:" + canonical_hash(
            self._identity()
        )
        if self.evidence_id != expected:
            raise ValueError("evidence_id does not bind verified security evidence")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "security_gate_proof_hash": self.security_gate_proof_hash,
            "standard_sbom_export_proof_hash": self.standard_sbom_export_proof_hash,
            "vulnerability_scan_proof_hash": self.vulnerability_scan_proof_hash,
            "signature_verification_proof_hash":
                self.signature_verification_proof_hash,
            "provenance_verification_proof_hash":
                self.provenance_verification_proof_hash,
            "container_image_digest": self.container_image_digest,
            "source_commit": self.source_commit,
            "verified": True,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "evidence_id": self.evidence_id,
            "proof_hash": self.proof_hash,
            "state": "EXTERNAL_SECURITY_EVIDENCE_VERIFIED",
        }


def verify_external_release_security_evidence(
    release: RecoveryWorksReleaseManifest,
    security_gate: ReleaseSecurityGate,
    standard_sbom: StandardSBOMExport,
    scan: VulnerabilityScanReceipt,
    signature: ExternalSignatureVerificationReceipt,
    provenance: ExternalProvenanceVerificationReceipt,
) -> VerifiedReleaseSecurityEvidence:
    if security_gate.release_id != release.release_id:
        raise ValueError("security gate release mismatch")
    if security_gate.release_proof_hash != release.proof_hash:
        raise ValueError("security gate release proof mismatch")
    if standard_sbom.release_id != release.release_id:
        raise ValueError("standard SBOM release mismatch")
    if standard_sbom.release_proof_hash != release.proof_hash:
        raise ValueError("standard SBOM release proof mismatch")
    if scan.container_image_digest != release.container_image_digest:
        raise ValueError("scan image digest mismatch")
    if not scan.verified:
        raise ValueError("scan receipt is not verified")
    if signature.release_id != release.release_id:
        raise ValueError("signature receipt release mismatch")
    if signature.release_proof_hash != release.proof_hash:
        raise ValueError("signature receipt release proof mismatch")
    if signature.container_image_digest != release.container_image_digest:
        raise ValueError("signature receipt image mismatch")
    if provenance.release_id != release.release_id:
        raise ValueError("provenance receipt release mismatch")
    if provenance.release_proof_hash != release.proof_hash:
        raise ValueError("provenance receipt release proof mismatch")
    if provenance.container_image_digest != release.container_image_digest:
        raise ValueError("provenance receipt image mismatch")
    if provenance.source_commit != release.source_commit:
        raise ValueError("provenance receipt source commit mismatch")
    if (
        provenance.container_build_manifest_proof_hash
        != release.container_build_manifest_proof_hash
    ):
        raise ValueError("provenance receipt build proof mismatch")
    if provenance.predicate_type != "https://slsa.dev/provenance/v1":
        raise ValueError("unsupported provenance predicate type")
    identity = {
        "schema": 1,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "security_gate_proof_hash": security_gate.proof_hash,
        "standard_sbom_export_proof_hash": standard_sbom.proof_hash,
        "vulnerability_scan_proof_hash": scan.proof_hash,
        "signature_verification_proof_hash": signature.proof_hash,
        "provenance_verification_proof_hash": provenance.proof_hash,
        "container_image_digest": release.container_image_digest,
        "source_commit": release.source_commit,
        "verified": True,
    }
    return VerifiedReleaseSecurityEvidence(
        evidence_id="recoveryworks-verified-security-evidence:"
        + canonical_hash(identity),
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        security_gate_proof_hash=security_gate.proof_hash,
        standard_sbom_export_proof_hash=standard_sbom.proof_hash,
        vulnerability_scan_proof_hash=scan.proof_hash,
        signature_verification_proof_hash=signature.proof_hash,
        provenance_verification_proof_hash=provenance.proof_hash,
        container_image_digest=release.container_image_digest,
        source_commit=release.source_commit,
        verified=True,
    )
