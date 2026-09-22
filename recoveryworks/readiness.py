"""Mandatory seven-figure authorization readiness for RecoveryOS.

This module turns the hostile-examination/custody controls into an enforceable
authorization gate. It does not perform external KMS/PKI verification itself.
Instead, provider-specific adapters must verify asymmetric signatures,
timestamps, and object-lock state, then record the provider verification
receipts here. RecoveryOS cryptographically binds those verified receipts into
one readiness package.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Iterable, Mapping

from .assurance import (
    CaseProofBundle,
    ClientActionAuthorization,
    HostileExaminationPacket,
    SEVEN_FIGURE_CENTS,
    verify_action_authorization,
    verify_case_bundle,
)
from .custody import (
    BuildProvenanceAttestation,
    CaseCompletenessManifest,
    NegativeEvidenceSearch,
    PopulationSegment,
    PublicVerificationRecord,
    RetainedSourceObject,
    SourceRetentionManifest,
    hostile_packet_hash,
    verify_build_provenance,
    verify_case_completeness,
    verify_public_verification_record,
    verify_source_retention,
)
from .models import canonical_hash


ASYMMETRIC_SIGNATURE_ALGORITHMS = frozenset({
    "RSA_PSS_SHA256",
    "RSA_PKCS1_SHA256",
    "ECDSA_SHA256",
    "ED25519",
})

TRUSTED_TIMESTAMP_STANDARDS = frozenset({"RFC3161"})

APPROVED_IMMUTABLE_RETENTION_MODES = frozenset({
    "OBJECT_LOCK_COMPLIANCE",
    "WORM_COMPLIANCE",
    "AZURE_IMMUTABLE_LOCKED",
    "GCS_BUCKET_LOCK",
})

LEGAL_HOLD_STATUSES = frozenset({"ON", "OFF"})

REQUIRED_READINESS_CHECKS = (
    "BUILD_PROVENANCE_VERIFIED",
    "CASE_COMPLETENESS_VERIFIED",
    "EXTERNAL_ASYMMETRIC_SIGNATURE_VERIFIED",
    "EXTERNAL_TIMESTAMP_VERIFIED",
    "HOSTILE_EXAM_PACKET_BOUND",
    "IMMUTABLE_SOURCE_RETENTION_VERIFIED",
    "OBJECT_LOCK_PROVIDER_RECEIPTS_VERIFIED",
    "PUBLIC_TRANSPARENCY_RECORD_VERIFIED",
)


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _iso(name: str, value: str) -> str:
    text = _required(name, value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include timezone")
    return text


def _dt(name: str, value: str) -> datetime:
    return datetime.fromisoformat(_iso(name, value).replace("Z", "+00:00"))


@dataclass(frozen=True)
class ExternalSignatureEvidence:
    """Evidence that an external KMS/PKI verifier accepted an asymmetric signature."""

    signature_id: str
    payload_kind: str
    payload_hash: str
    provider: str
    key_id: str
    algorithm: str
    public_key_fingerprint: str
    signature_hash: str
    provider_request_id: str
    verification_receipt_hash: str
    signed_at: str
    verified_at: str
    verified_by_adapter: str
    provider_verified: bool
    evidence_hash: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "signature_id",
            "payload_kind",
            "payload_hash",
            "provider",
            "key_id",
            "algorithm",
            "public_key_fingerprint",
            "signature_hash",
            "provider_request_id",
            "verification_receipt_hash",
            "verified_by_adapter",
            "evidence_hash",
        ):
            _required(name, getattr(self, name))
        if self.algorithm not in ASYMMETRIC_SIGNATURE_ALGORITHMS:
            raise ValueError("external signature must use an approved asymmetric algorithm")
        signed = _dt("signed_at", self.signed_at)
        verified = _dt("verified_at", self.verified_at)
        if verified < signed:
            raise ValueError("signature verification cannot predate signing")
        if type(self.provider_verified) is not bool:
            raise ValueError("provider_verified must be boolean")

    def integrity_body(self) -> dict[str, Any]:
        return {
            "schema": 1,
            **{
                key: value
                for key, value in asdict(self).items()
                if key != "evidence_hash"
            },
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.evidence_hash:
            raise ValueError("external signature evidence hash mismatch")


def record_external_signature_verification(
    *,
    signature_id: str,
    payload_kind: str,
    payload_hash: str,
    provider: str,
    key_id: str,
    algorithm: str,
    public_key_fingerprint: str,
    signature_hash: str,
    provider_request_id: str,
    verification_receipt_hash: str,
    signed_at: str,
    verified_at: str,
    verified_by_adapter: str,
    provider_verified: bool,
    metadata: Mapping[str, Any] | None = None,
) -> ExternalSignatureEvidence:
    """Record the result of a provider-specific asymmetric signature verification."""
    if algorithm not in ASYMMETRIC_SIGNATURE_ALGORITHMS:
        raise ValueError("external signature must use an approved asymmetric algorithm")
    if provider_verified:
        _required("verification_receipt_hash", verification_receipt_hash)
        _required("provider_request_id", provider_request_id)
    body = {
        "schema": 1,
        "signature_id": _required("signature_id", signature_id),
        "payload_kind": _required("payload_kind", payload_kind),
        "payload_hash": _required("payload_hash", payload_hash),
        "provider": _required("provider", provider),
        "key_id": _required("key_id", key_id),
        "algorithm": algorithm,
        "public_key_fingerprint": _required(
            "public_key_fingerprint", public_key_fingerprint
        ),
        "signature_hash": _required("signature_hash", signature_hash),
        "provider_request_id": _required("provider_request_id", provider_request_id),
        "verification_receipt_hash": _required(
            "verification_receipt_hash", verification_receipt_hash
        ),
        "signed_at": _iso("signed_at", signed_at),
        "verified_at": _iso("verified_at", verified_at),
        "verified_by_adapter": _required("verified_by_adapter", verified_by_adapter),
        "provider_verified": provider_verified,
        "metadata": dict(metadata or {}),
    }
    if _dt("verified_at", body["verified_at"]) < _dt("signed_at", body["signed_at"]):
        raise ValueError("signature verification cannot predate signing")
    return ExternalSignatureEvidence(
        **{key: value for key, value in body.items() if key != "schema"},
        evidence_hash=canonical_hash(body),
    )


def verify_external_signature_evidence(
    evidence: ExternalSignatureEvidence,
    *,
    expected_payload_hash: str,
) -> None:
    evidence.verify_integrity()
    if not evidence.provider_verified:
        raise ValueError("external signature was not provider-verified")
    if evidence.payload_hash != expected_payload_hash:
        raise ValueError("external signature payload hash mismatch")
    if evidence.algorithm not in ASYMMETRIC_SIGNATURE_ALGORITHMS:
        raise ValueError("external signature algorithm is not asymmetric/approved")


@dataclass(frozen=True)
class ExternalTimestampEvidence:
    """Evidence that a trusted timestamp service verified a timestamp token."""

    timestamp_id: str
    subject_hash: str
    authority: str
    standard: str
    token_hash: str
    serial_number: str
    provider_request_id: str
    verification_receipt_hash: str
    timestamped_at: str
    verified_at: str
    verified_by_adapter: str
    provider_verified: bool
    evidence_hash: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "timestamp_id",
            "subject_hash",
            "authority",
            "standard",
            "token_hash",
            "serial_number",
            "provider_request_id",
            "verification_receipt_hash",
            "verified_by_adapter",
            "evidence_hash",
        ):
            _required(name, getattr(self, name))
        if self.standard not in TRUSTED_TIMESTAMP_STANDARDS:
            raise ValueError("external timestamp standard is not approved")
        timestamped = _dt("timestamped_at", self.timestamped_at)
        verified = _dt("verified_at", self.verified_at)
        if verified < timestamped:
            raise ValueError("timestamp verification cannot predate trusted timestamp")
        if type(self.provider_verified) is not bool:
            raise ValueError("provider_verified must be boolean")

    def integrity_body(self) -> dict[str, Any]:
        return {
            "schema": 1,
            **{
                key: value
                for key, value in asdict(self).items()
                if key != "evidence_hash"
            },
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.evidence_hash:
            raise ValueError("external timestamp evidence hash mismatch")


def record_external_timestamp_verification(
    *,
    timestamp_id: str,
    subject_hash: str,
    authority: str,
    standard: str,
    token_hash: str,
    serial_number: str,
    provider_request_id: str,
    verification_receipt_hash: str,
    timestamped_at: str,
    verified_at: str,
    verified_by_adapter: str,
    provider_verified: bool,
    metadata: Mapping[str, Any] | None = None,
) -> ExternalTimestampEvidence:
    if provider_verified:
        _required("verification_receipt_hash", verification_receipt_hash)
        _required("provider_request_id", provider_request_id)
    body = {
        "schema": 1,
        "timestamp_id": _required("timestamp_id", timestamp_id),
        "subject_hash": _required("subject_hash", subject_hash),
        "authority": _required("authority", authority),
        "standard": _required("standard", standard),
        "token_hash": _required("token_hash", token_hash),
        "serial_number": _required("serial_number", serial_number),
        "provider_request_id": _required("provider_request_id", provider_request_id),
        "verification_receipt_hash": _required(
            "verification_receipt_hash", verification_receipt_hash
        ),
        "timestamped_at": _iso("timestamped_at", timestamped_at),
        "verified_at": _iso("verified_at", verified_at),
        "verified_by_adapter": _required("verified_by_adapter", verified_by_adapter),
        "provider_verified": provider_verified,
        "metadata": dict(metadata or {}),
    }
    if _dt("verified_at", body["verified_at"]) < _dt(
        "timestamped_at", body["timestamped_at"]
    ):
        raise ValueError("timestamp verification cannot predate trusted timestamp")
    return ExternalTimestampEvidence(
        **{key: value for key, value in body.items() if key != "schema"},
        evidence_hash=canonical_hash(body),
    )


def verify_external_timestamp_evidence(
    evidence: ExternalTimestampEvidence,
    *,
    expected_subject_hash: str,
) -> None:
    evidence.verify_integrity()
    if not evidence.provider_verified:
        raise ValueError("external timestamp was not provider-verified")
    if evidence.subject_hash != expected_subject_hash:
        raise ValueError("external timestamp subject hash mismatch")


@dataclass(frozen=True)
class ObjectLockVerificationReceipt:
    """Provider verification of object-lock/WORM state for one retained source."""

    source_id: str
    role: str
    source_hash: str
    provider: str
    object_version_id: str
    retention_control_id: str
    retention_mode: str
    retain_until: str
    legal_hold_status: str
    checked_at: str
    provider_request_id: str
    provider_response_hash: str
    verified_by_adapter: str
    provider_verified: bool
    receipt_hash: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "source_id",
            "role",
            "source_hash",
            "provider",
            "object_version_id",
            "retention_control_id",
            "retention_mode",
            "legal_hold_status",
            "provider_request_id",
            "provider_response_hash",
            "verified_by_adapter",
            "receipt_hash",
        ):
            _required(name, getattr(self, name))
        if self.role not in {"authority", "evidence"}:
            raise ValueError("object-lock receipt role must be authority or evidence")
        if self.retention_mode not in APPROVED_IMMUTABLE_RETENTION_MODES:
            raise ValueError("object-lock receipt retention mode is not approved")
        if self.legal_hold_status not in LEGAL_HOLD_STATUSES:
            raise ValueError("object-lock receipt legal hold status is invalid")
        retain_until = _dt("retain_until", self.retain_until)
        checked_at = _dt("checked_at", self.checked_at)
        if retain_until <= checked_at:
            raise ValueError("object-lock retention must extend beyond verification time")
        if type(self.provider_verified) is not bool:
            raise ValueError("provider_verified must be boolean")

    def integrity_body(self) -> dict[str, Any]:
        return {
            "schema": 1,
            **{
                key: value
                for key, value in asdict(self).items()
                if key != "receipt_hash"
            },
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.receipt_hash:
            raise ValueError("object-lock verification receipt hash mismatch")


def record_object_lock_verification(
    *,
    source_id: str,
    role: str,
    source_hash: str,
    provider: str,
    object_version_id: str,
    retention_control_id: str,
    retention_mode: str,
    retain_until: str,
    legal_hold_status: str,
    checked_at: str,
    provider_request_id: str,
    provider_response_hash: str,
    verified_by_adapter: str,
    provider_verified: bool,
    metadata: Mapping[str, Any] | None = None,
) -> ObjectLockVerificationReceipt:
    if retention_mode not in APPROVED_IMMUTABLE_RETENTION_MODES:
        raise ValueError("object-lock receipt retention mode is not approved")
    if legal_hold_status not in LEGAL_HOLD_STATUSES:
        raise ValueError("object-lock receipt legal hold status is invalid")
    if _dt("retain_until", retain_until) <= _dt("checked_at", checked_at):
        raise ValueError("object-lock retention must extend beyond verification time")
    body = {
        "schema": 1,
        "source_id": _required("source_id", source_id),
        "role": _required("role", role),
        "source_hash": _required("source_hash", source_hash),
        "provider": _required("provider", provider),
        "object_version_id": _required("object_version_id", object_version_id),
        "retention_control_id": _required(
            "retention_control_id", retention_control_id
        ),
        "retention_mode": _required("retention_mode", retention_mode),
        "retain_until": _iso("retain_until", retain_until),
        "legal_hold_status": _required("legal_hold_status", legal_hold_status),
        "checked_at": _iso("checked_at", checked_at),
        "provider_request_id": _required("provider_request_id", provider_request_id),
        "provider_response_hash": _required(
            "provider_response_hash", provider_response_hash
        ),
        "verified_by_adapter": _required("verified_by_adapter", verified_by_adapter),
        "provider_verified": provider_verified,
        "metadata": dict(metadata or {}),
    }
    return ObjectLockVerificationReceipt(
        **{key: value for key, value in body.items() if key != "schema"},
        receipt_hash=canonical_hash(body),
    )


def verify_object_lock_receipts(
    receipts: Iterable[ObjectLockVerificationReceipt],
    retention: SourceRetentionManifest,
) -> tuple[ObjectLockVerificationReceipt, ...]:
    """Verify exact provider receipts for every retained high-value source."""
    retention.verify_integrity()
    receipt_tuple = tuple(sorted(
        receipts,
        key=lambda item: (item.role, item.source_id),
    ))
    by_key: dict[tuple[str, str], ObjectLockVerificationReceipt] = {}
    for item in receipt_tuple:
        item.verify_integrity()
        key = (item.role, item.source_id)
        if key in by_key:
            raise ValueError(f"duplicate object-lock receipt: {key!r}")
        if not item.provider_verified:
            raise ValueError("object-lock receipt was not provider-verified")
        by_key[key] = item

    expected = {
        (item.role, item.source_id): item
        for item in retention.entries
    }
    if set(by_key) != set(expected):
        raise ValueError("object-lock receipt source set mismatch")

    for key, retained in expected.items():
        receipt = by_key[key]
        if receipt.source_hash != retained.source_hash:
            raise ValueError("object-lock receipt source hash mismatch")
        if receipt.retention_control_id != retained.retention_control_id:
            raise ValueError("object-lock receipt retention control mismatch")
        if receipt.retention_mode != retained.retention_mode:
            raise ValueError("object-lock receipt retention mode mismatch")
        if retained.provider_attestation_hash != receipt.provider_response_hash:
            raise ValueError("object-lock provider response hash mismatch")
        if retained.retain_until is None:
            raise ValueError("seven-figure retained source requires retain_until")
        if _dt("receipt.retain_until", receipt.retain_until) < _dt(
            "retained.retain_until", retained.retain_until
        ):
            raise ValueError("object-lock provider retention is shorter than manifest")
        if _dt("receipt.checked_at", receipt.checked_at) < _dt(
            "retention.created_at", retention.created_at
        ):
            raise ValueError("object-lock provider receipt predates retention manifest")
    return receipt_tuple


@dataclass(frozen=True)
class SevenFigureReadinessPackage:
    """Authorization-blocking assurance package for a seven-figure finding."""

    gate_version: str
    case_bundle_hash: str
    finding_proof_hash: str
    hostile_packet_hash: str
    retention_manifest_hash: str
    completeness_manifest_hash: str
    build_attestation_hash: str
    public_record_hash: str
    journal_head_hash: str
    external_signature: ExternalSignatureEvidence
    external_timestamp: ExternalTimestampEvidence
    object_lock_receipts: tuple[ObjectLockVerificationReceipt, ...]
    checks: tuple[str, ...]
    evaluated_at: str
    evaluated_by: str
    package_hash: str

    def __post_init__(self) -> None:
        for name in (
            "gate_version",
            "case_bundle_hash",
            "finding_proof_hash",
            "hostile_packet_hash",
            "retention_manifest_hash",
            "completeness_manifest_hash",
            "build_attestation_hash",
            "public_record_hash",
            "journal_head_hash",
            "evaluated_by",
            "package_hash",
        ):
            _required(name, getattr(self, name))
        _iso("evaluated_at", self.evaluated_at)
        if self.gate_version != "seven-figure-v1":
            raise ValueError("unsupported seven-figure readiness gate version")

    def integrity_body(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "gate_version": self.gate_version,
            "case_bundle_hash": self.case_bundle_hash,
            "finding_proof_hash": self.finding_proof_hash,
            "hostile_packet_hash": self.hostile_packet_hash,
            "retention_manifest_hash": self.retention_manifest_hash,
            "completeness_manifest_hash": self.completeness_manifest_hash,
            "build_attestation_hash": self.build_attestation_hash,
            "public_record_hash": self.public_record_hash,
            "journal_head_hash": self.journal_head_hash,
            "external_signature": asdict(self.external_signature),
            "external_timestamp": asdict(self.external_timestamp),
            "object_lock_receipts": [
                asdict(item)
                for item in sorted(
                    self.object_lock_receipts,
                    key=lambda item: (item.role, item.source_id),
                )
            ],
            "checks": sorted(self.checks),
            "evaluated_at": self.evaluated_at,
            "evaluated_by": self.evaluated_by,
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.package_hash:
            raise ValueError("seven-figure readiness package hash mismatch")


def build_seven_figure_readiness(
    bundle: CaseProofBundle,
    packet: HostileExaminationPacket,
    retention: SourceRetentionManifest,
    completeness: CaseCompletenessManifest,
    build: BuildProvenanceAttestation,
    public_record: PublicVerificationRecord,
    external_signature: ExternalSignatureEvidence,
    external_timestamp: ExternalTimestampEvidence,
    object_lock_receipts: Iterable[ObjectLockVerificationReceipt],
    *,
    journal_head_hash: str,
    evaluated_at: str,
    evaluated_by: str,
) -> SevenFigureReadinessPackage:
    """Evaluate every mandatory assurance check and freeze the authorization gate."""
    verify_case_bundle(bundle)
    if bundle.finding.potential_recovery_cents < SEVEN_FIGURE_CENTS:
        raise ValueError("seven-figure readiness gate only applies to seven-figure findings")

    verify_source_retention(retention, bundle, require_immutable=True)
    verify_case_completeness(completeness, bundle)
    verify_build_provenance(build, bundle)
    verify_public_verification_record(
        public_record,
        bundle,
        packet,
        retention,
        completeness,
        build,
        journal_head_hash=journal_head_hash,
    )
    expected_packet_hash = hostile_packet_hash(packet)
    if public_record.hostile_packet_hash != expected_packet_hash:
        raise ValueError("public record hostile packet hash mismatch")

    verify_external_signature_evidence(
        external_signature,
        expected_payload_hash=public_record.record_hash,
    )
    if _dt("signature.signed_at", external_signature.signed_at) < _dt(
        "public_record.published_at", public_record.published_at
    ):
        raise ValueError("external signature predates public verification record")

    verify_external_timestamp_evidence(
        external_timestamp,
        expected_subject_hash=external_signature.signature_hash,
    )
    if _dt("timestamp.timestamped_at", external_timestamp.timestamped_at) < _dt(
        "signature.signed_at", external_signature.signed_at
    ):
        raise ValueError("trusted timestamp predates external signature")

    receipt_tuple = verify_object_lock_receipts(object_lock_receipts, retention)

    evaluated_at = _iso("evaluated_at", evaluated_at)
    evaluated_by = _required("evaluated_by", evaluated_by)
    latest_component = max(
        _dt("signature.verified_at", external_signature.verified_at),
        _dt("timestamp.verified_at", external_timestamp.verified_at),
        *(
            _dt("object_lock.checked_at", item.checked_at)
            for item in receipt_tuple
        ),
    )
    if _dt("evaluated_at", evaluated_at) < latest_component:
        raise ValueError("readiness evaluation predates a mandatory verification")

    checks = tuple(sorted(REQUIRED_READINESS_CHECKS))
    body = {
        "schema": 1,
        "gate_version": "seven-figure-v1",
        "case_bundle_hash": bundle.bundle_hash,
        "finding_proof_hash": bundle.finding.proof_hash,
        "hostile_packet_hash": expected_packet_hash,
        "retention_manifest_hash": retention.manifest_hash,
        "completeness_manifest_hash": completeness.manifest_hash,
        "build_attestation_hash": build.attestation_hash,
        "public_record_hash": public_record.record_hash,
        "journal_head_hash": _required("journal_head_hash", journal_head_hash),
        "external_signature": asdict(external_signature),
        "external_timestamp": asdict(external_timestamp),
        "object_lock_receipts": [asdict(item) for item in receipt_tuple],
        "checks": list(checks),
        "evaluated_at": evaluated_at,
        "evaluated_by": evaluated_by,
    }
    return SevenFigureReadinessPackage(
        gate_version="seven-figure-v1",
        case_bundle_hash=bundle.bundle_hash,
        finding_proof_hash=bundle.finding.proof_hash,
        hostile_packet_hash=expected_packet_hash,
        retention_manifest_hash=retention.manifest_hash,
        completeness_manifest_hash=completeness.manifest_hash,
        build_attestation_hash=build.attestation_hash,
        public_record_hash=public_record.record_hash,
        journal_head_hash=journal_head_hash,
        external_signature=external_signature,
        external_timestamp=external_timestamp,
        object_lock_receipts=receipt_tuple,
        checks=checks,
        evaluated_at=evaluated_at,
        evaluated_by=evaluated_by,
        package_hash=canonical_hash(body),
    )


def verify_seven_figure_readiness(
    package: SevenFigureReadinessPackage,
    bundle: CaseProofBundle,
    *,
    expected_journal_head_hash: str | None = None,
) -> None:
    """Verify the authorization-blocking package against the frozen case."""
    verify_case_bundle(bundle)
    if bundle.finding.potential_recovery_cents < SEVEN_FIGURE_CENTS:
        raise ValueError("seven-figure readiness package used for sub-seven-figure case")
    package.verify_integrity()
    if package.case_bundle_hash != bundle.bundle_hash:
        raise ValueError("readiness package case bundle mismatch")
    if package.finding_proof_hash != bundle.finding.proof_hash:
        raise ValueError("readiness package finding proof mismatch")
    if tuple(sorted(package.checks)) != tuple(sorted(REQUIRED_READINESS_CHECKS)):
        raise ValueError("readiness package does not contain all required checks")
    if expected_journal_head_hash is not None:
        if package.journal_head_hash != expected_journal_head_hash:
            raise ValueError("readiness package journal head is stale")

    verify_external_signature_evidence(
        package.external_signature,
        expected_payload_hash=package.public_record_hash,
    )
    verify_external_timestamp_evidence(
        package.external_timestamp,
        expected_subject_hash=package.external_signature.signature_hash,
    )

    expected_sources = {
        ("authority", bundle.authority.authority_id): bundle.authority.source_hash,
        **{
            ("evidence", item.evidence_id): item.source_hash
            for item in bundle.source_attestations
        },
    }
    observed_sources: dict[tuple[str, str], str] = {}
    for receipt in package.object_lock_receipts:
        receipt.verify_integrity()
        if not receipt.provider_verified:
            raise ValueError("readiness contains unverified object-lock receipt")
        key = (receipt.role, receipt.source_id)
        if key in observed_sources:
            raise ValueError("readiness contains duplicate object-lock receipt")
        observed_sources[key] = receipt.source_hash
    if observed_sources != expected_sources:
        raise ValueError("readiness object-lock source set/hash mismatch")

    latest_component = max(
        _dt("signature.verified_at", package.external_signature.verified_at),
        _dt("timestamp.verified_at", package.external_timestamp.verified_at),
        *(
            _dt("object_lock.checked_at", item.checked_at)
            for item in package.object_lock_receipts
        ),
    )
    if _dt("package.evaluated_at", package.evaluated_at) < latest_component:
        raise ValueError("readiness evaluation predates mandatory verification")


def readiness_to_payload(package: SevenFigureReadinessPackage) -> dict[str, Any]:
    package.verify_integrity()
    return {
        **package.integrity_body(),
        "package_hash": package.package_hash,
    }


def readiness_from_payload(payload: Mapping[str, Any]) -> SevenFigureReadinessPackage:
    signature = ExternalSignatureEvidence(**dict(payload["external_signature"]))
    timestamp = ExternalTimestampEvidence(**dict(payload["external_timestamp"]))
    receipts = tuple(
        ObjectLockVerificationReceipt(**dict(item))
        for item in payload.get("object_lock_receipts", [])
    )
    package = SevenFigureReadinessPackage(
        gate_version=payload["gate_version"],
        case_bundle_hash=payload["case_bundle_hash"],
        finding_proof_hash=payload["finding_proof_hash"],
        hostile_packet_hash=payload["hostile_packet_hash"],
        retention_manifest_hash=payload["retention_manifest_hash"],
        completeness_manifest_hash=payload["completeness_manifest_hash"],
        build_attestation_hash=payload["build_attestation_hash"],
        public_record_hash=payload["public_record_hash"],
        journal_head_hash=payload["journal_head_hash"],
        external_signature=signature,
        external_timestamp=timestamp,
        object_lock_receipts=receipts,
        checks=tuple(payload.get("checks", ())),
        evaluated_at=payload["evaluated_at"],
        evaluated_by=payload["evaluated_by"],
        package_hash=payload["package_hash"],
    )
    package.verify_integrity()
    return package


@dataclass(frozen=True)
class SevenFigureAuthorizationDossier:
    """Full replayable evidence set required to authorize a seven-figure case."""

    dossier_version: str
    readiness: SevenFigureReadinessPackage
    hostile_packet: HostileExaminationPacket
    retention: SourceRetentionManifest
    completeness: CaseCompletenessManifest
    build: BuildProvenanceAttestation
    public_record: PublicVerificationRecord
    assembled_at: str
    assembled_by: str
    dossier_hash: str

    def __post_init__(self) -> None:
        for name in ("dossier_version", "assembled_by", "dossier_hash"):
            _required(name, getattr(self, name))
        _iso("assembled_at", self.assembled_at)
        if self.dossier_version != "seven-figure-dossier-v1":
            raise ValueError("unsupported seven-figure authorization dossier version")

    def integrity_body(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "dossier_version": self.dossier_version,
            "readiness": asdict(self.readiness),
            "hostile_packet": asdict(self.hostile_packet),
            "retention": asdict(self.retention),
            "completeness": asdict(self.completeness),
            "build": asdict(self.build),
            "public_record": asdict(self.public_record),
            "assembled_at": self.assembled_at,
            "assembled_by": self.assembled_by,
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.dossier_hash:
            raise ValueError("seven-figure authorization dossier hash mismatch")


def _verify_dossier_components(
    *,
    readiness: SevenFigureReadinessPackage,
    hostile_packet: HostileExaminationPacket,
    retention: SourceRetentionManifest,
    completeness: CaseCompletenessManifest,
    build: BuildProvenanceAttestation,
    public_record: PublicVerificationRecord,
    bundle: CaseProofBundle,
    journal_head_hash: str,
) -> None:
    verify_seven_figure_readiness(
        readiness,
        bundle,
        expected_journal_head_hash=journal_head_hash,
    )
    verify_source_retention(retention, bundle, require_immutable=True)
    verify_case_completeness(completeness, bundle)
    verify_build_provenance(build, bundle)
    verify_object_lock_receipts(readiness.object_lock_receipts, retention)
    verify_public_verification_record(
        public_record,
        bundle,
        hostile_packet,
        retention,
        completeness,
        build,
        journal_head_hash=journal_head_hash,
    )

    expected_packet_hash = hostile_packet_hash(hostile_packet)
    component_hashes = {
        "hostile_packet_hash": expected_packet_hash,
        "retention_manifest_hash": retention.manifest_hash,
        "completeness_manifest_hash": completeness.manifest_hash,
        "build_attestation_hash": build.attestation_hash,
        "public_record_hash": public_record.record_hash,
        "journal_head_hash": journal_head_hash,
    }
    for field_name, expected in component_hashes.items():
        if getattr(readiness, field_name) != expected:
            raise ValueError(f"readiness {field_name} does not match dossier component")


def build_seven_figure_authorization_dossier(
    readiness: SevenFigureReadinessPackage,
    hostile_packet: HostileExaminationPacket,
    retention: SourceRetentionManifest,
    completeness: CaseCompletenessManifest,
    build: BuildProvenanceAttestation,
    public_record: PublicVerificationRecord,
    bundle: CaseProofBundle,
    *,
    journal_head_hash: str,
    assembled_at: str,
    assembled_by: str,
) -> SevenFigureAuthorizationDossier:
    """Freeze the full evidence set that must be replayed at authorization time."""
    _verify_dossier_components(
        readiness=readiness,
        hostile_packet=hostile_packet,
        retention=retention,
        completeness=completeness,
        build=build,
        public_record=public_record,
        bundle=bundle,
        journal_head_hash=journal_head_hash,
    )
    assembled_at = _iso("assembled_at", assembled_at)
    assembled_by = _required("assembled_by", assembled_by)
    if _dt("assembled_at", assembled_at) < _dt(
        "readiness.evaluated_at", readiness.evaluated_at
    ):
        raise ValueError("authorization dossier cannot predate readiness evaluation")

    body = {
        "schema": 1,
        "dossier_version": "seven-figure-dossier-v1",
        "readiness": asdict(readiness),
        "hostile_packet": asdict(hostile_packet),
        "retention": asdict(retention),
        "completeness": asdict(completeness),
        "build": asdict(build),
        "public_record": asdict(public_record),
        "assembled_at": assembled_at,
        "assembled_by": assembled_by,
    }
    return SevenFigureAuthorizationDossier(
        dossier_version="seven-figure-dossier-v1",
        readiness=readiness,
        hostile_packet=hostile_packet,
        retention=retention,
        completeness=completeness,
        build=build,
        public_record=public_record,
        assembled_at=assembled_at,
        assembled_by=assembled_by,
        dossier_hash=canonical_hash(body),
    )


def verify_seven_figure_authorization_dossier(
    dossier: SevenFigureAuthorizationDossier,
    bundle: CaseProofBundle,
    *,
    expected_journal_head_hash: str,
) -> None:
    """Re-run all underlying assurance verifiers before authorization/replay."""
    dossier.verify_integrity()
    _verify_dossier_components(
        readiness=dossier.readiness,
        hostile_packet=dossier.hostile_packet,
        retention=dossier.retention,
        completeness=dossier.completeness,
        build=dossier.build,
        public_record=dossier.public_record,
        bundle=bundle,
        journal_head_hash=expected_journal_head_hash,
    )
    if _dt("dossier.assembled_at", dossier.assembled_at) < _dt(
        "readiness.evaluated_at", dossier.readiness.evaluated_at
    ):
        raise ValueError("authorization dossier predates readiness evaluation")


def authorization_dossier_to_payload(
    dossier: SevenFigureAuthorizationDossier,
) -> dict[str, Any]:
    dossier.verify_integrity()
    return {
        **dossier.integrity_body(),
        "dossier_hash": dossier.dossier_hash,
    }


def authorization_dossier_from_payload(
    payload: Mapping[str, Any],
) -> SevenFigureAuthorizationDossier:
    readiness = readiness_from_payload(payload["readiness"])
    hostile_packet = HostileExaminationPacket(**dict(payload["hostile_packet"]))

    retention_raw = dict(payload["retention"])
    retention = SourceRetentionManifest(
        case_bundle_hash=retention_raw["case_bundle_hash"],
        finding_proof_hash=retention_raw["finding_proof_hash"],
        entries=tuple(
            RetainedSourceObject(**dict(item))
            for item in retention_raw.get("entries", [])
        ),
        created_at=retention_raw["created_at"],
        created_by=retention_raw["created_by"],
        manifest_hash=retention_raw["manifest_hash"],
    )

    completeness_raw = dict(payload["completeness"])
    completeness = CaseCompletenessManifest(
        case_bundle_hash=completeness_raw["case_bundle_hash"],
        finding_proof_hash=completeness_raw["finding_proof_hash"],
        input_manifest_hash=completeness_raw["input_manifest_hash"],
        populations=tuple(
            PopulationSegment(**dict(item))
            for item in completeness_raw.get("populations", [])
        ),
        negative_searches=tuple(
            NegativeEvidenceSearch(
                **{
                    **dict(item),
                    "searched_source_hashes": tuple(item.get("searched_source_hashes", ())),
                    "contrary_evidence_hashes": tuple(item.get("contrary_evidence_hashes", ())),
                }
            )
            for item in completeness_raw.get("negative_searches", [])
        ),
        created_at=completeness_raw["created_at"],
        created_by=completeness_raw["created_by"],
        manifest_hash=completeness_raw["manifest_hash"],
    )

    build = BuildProvenanceAttestation(**dict(payload["build"]))
    public_record = PublicVerificationRecord(**dict(payload["public_record"]))

    dossier = SevenFigureAuthorizationDossier(
        dossier_version=payload["dossier_version"],
        readiness=readiness,
        hostile_packet=hostile_packet,
        retention=retention,
        completeness=completeness,
        build=build,
        public_record=public_record,
        assembled_at=payload["assembled_at"],
        assembled_by=payload["assembled_by"],
        dossier_hash=payload["dossier_hash"],
    )
    dossier.verify_integrity()
    return dossier



@dataclass(frozen=True)
class BuildProviderVerificationReceipt:
    """Provider-verified CI/build receipt for the frozen calculator artifact."""

    build_attestation_hash: str
    provider: str
    workflow_run_id: str
    code_commit_sha: str
    source_tree_hash: str
    build_artifact_hash: str
    tests_passed: bool
    checked_at: str
    provider_request_id: str
    provider_response_hash: str
    verified_by_adapter: str
    provider_verified: bool
    receipt_hash: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "build_attestation_hash",
            "provider",
            "workflow_run_id",
            "code_commit_sha",
            "source_tree_hash",
            "build_artifact_hash",
            "provider_request_id",
            "provider_response_hash",
            "verified_by_adapter",
            "receipt_hash",
        ):
            _required(name, getattr(self, name))
        _iso("checked_at", self.checked_at)
        if type(self.tests_passed) is not bool:
            raise ValueError("tests_passed must be boolean")
        if type(self.provider_verified) is not bool:
            raise ValueError("provider_verified must be boolean")

    def integrity_body(self) -> dict[str, Any]:
        return {
            "schema": 1,
            **{
                key: value
                for key, value in asdict(self).items()
                if key != "receipt_hash"
            },
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.receipt_hash:
            raise ValueError("build provider verification receipt hash mismatch")


def record_build_provider_verification(
    build: BuildProvenanceAttestation,
    *,
    provider: str,
    workflow_run_id: str,
    code_commit_sha: str,
    source_tree_hash: str,
    build_artifact_hash: str,
    tests_passed: bool,
    checked_at: str,
    provider_request_id: str,
    provider_response_hash: str,
    verified_by_adapter: str,
    provider_verified: bool,
    metadata: Mapping[str, Any] | None = None,
) -> BuildProviderVerificationReceipt:
    """Record a CI/provider verification result for an existing build attestation."""
    build.verify_integrity()
    body = {
        "schema": 1,
        "build_attestation_hash": build.attestation_hash,
        "provider": _required("provider", provider),
        "workflow_run_id": _required("workflow_run_id", workflow_run_id),
        "code_commit_sha": _required("code_commit_sha", code_commit_sha),
        "source_tree_hash": _required("source_tree_hash", source_tree_hash),
        "build_artifact_hash": _required("build_artifact_hash", build_artifact_hash),
        "tests_passed": tests_passed,
        "checked_at": _iso("checked_at", checked_at),
        "provider_request_id": _required("provider_request_id", provider_request_id),
        "provider_response_hash": _required(
            "provider_response_hash", provider_response_hash
        ),
        "verified_by_adapter": _required("verified_by_adapter", verified_by_adapter),
        "provider_verified": provider_verified,
        "metadata": dict(metadata or {}),
    }
    return BuildProviderVerificationReceipt(
        **{key: value for key, value in body.items() if key != "schema"},
        receipt_hash=canonical_hash(body),
    )


def verify_build_provider_verification(
    receipt: BuildProviderVerificationReceipt,
    build: BuildProvenanceAttestation,
) -> None:
    build.verify_integrity()
    receipt.verify_integrity()
    if not receipt.provider_verified:
        raise ValueError("build provenance was not provider-verified")
    if not receipt.tests_passed:
        raise ValueError("provider build verification reports failed tests")
    fields = {
        "build_attestation_hash": build.attestation_hash,
        "workflow_run_id": build.workflow_run_id,
        "code_commit_sha": build.code_commit_sha,
        "source_tree_hash": build.source_tree_hash,
        "build_artifact_hash": build.build_artifact_hash,
        "tests_passed": build.tests_passed,
    }
    for name, expected in fields.items():
        if getattr(receipt, name) != expected:
            raise ValueError(f"build provider verification {name} mismatch")
    if _dt("build_provider.checked_at", receipt.checked_at) < _dt(
        "build.attested_at", build.attested_at
    ):
        raise ValueError("build provider verification predates build attestation")


def seven_figure_consent_payload_hash(
    authorization: ClientActionAuthorization,
    bundle: CaseProofBundle,
    dossier: SevenFigureAuthorizationDossier,
    *,
    consented_at: str,
    note: str,
) -> str:
    verify_action_authorization(bundle, authorization)
    verify_seven_figure_authorization_dossier(
        dossier,
        bundle,
        expected_journal_head_hash=dossier.readiness.journal_head_hash,
    )
    consented_at = _iso("consented_at", consented_at)
    note = _required("note", note)
    if _dt("consented_at", consented_at) < _dt(
        "dossier.assembled_at", dossier.assembled_at
    ):
        raise ValueError("client dossier consent cannot predate final dossier")
    body = {
        "schema": 1,
        "consent_version": "seven-figure-consent-v1",
        "authorization_id": authorization.authorization_id,
        "authorization_hash": authorization.proof_hash,
        "case_bundle_hash": bundle.bundle_hash,
        "finding_proof_hash": bundle.finding.proof_hash,
        "readiness_package_hash": dossier.readiness.package_hash,
        "readiness_dossier_hash": dossier.dossier_hash,
        "client_actor_id": authorization.client_actor_id,
        "approved_action_type": authorization.approved_action_type,
        "maximum_amount_cents": authorization.maximum_amount_cents,
        "consented_at": consented_at,
        "note": note,
    }
    return canonical_hash(body)


@dataclass(frozen=True)
class SevenFigureDossierConsent:
    """Client consent explicitly bound to the final seven-figure dossier."""

    consent_version: str
    authorization_id: str
    authorization_hash: str
    case_bundle_hash: str
    finding_proof_hash: str
    readiness_package_hash: str
    readiness_dossier_hash: str
    client_actor_id: str
    approved_action_type: str
    maximum_amount_cents: int
    consented_at: str
    note: str
    client_signature: ExternalSignatureEvidence
    consent_payload_hash: str
    consent_hash: str

    def __post_init__(self) -> None:
        for name in (
            "consent_version",
            "authorization_id",
            "authorization_hash",
            "case_bundle_hash",
            "finding_proof_hash",
            "readiness_package_hash",
            "readiness_dossier_hash",
            "client_actor_id",
            "approved_action_type",
            "note",
            "consent_payload_hash",
            "consent_hash",
        ):
            _required(name, getattr(self, name))
        _iso("consented_at", self.consented_at)
        if self.consent_version != "seven-figure-consent-v1":
            raise ValueError("unsupported seven-figure client consent version")
        if type(self.maximum_amount_cents) is not int or self.maximum_amount_cents < 0:
            raise ValueError("maximum_amount_cents must be non-negative integer")

    def integrity_body(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "consent_version": self.consent_version,
            "authorization_id": self.authorization_id,
            "authorization_hash": self.authorization_hash,
            "case_bundle_hash": self.case_bundle_hash,
            "finding_proof_hash": self.finding_proof_hash,
            "readiness_package_hash": self.readiness_package_hash,
            "readiness_dossier_hash": self.readiness_dossier_hash,
            "client_actor_id": self.client_actor_id,
            "approved_action_type": self.approved_action_type,
            "maximum_amount_cents": self.maximum_amount_cents,
            "consented_at": self.consented_at,
            "note": self.note,
            "client_signature": asdict(self.client_signature),
            "consent_payload_hash": self.consent_payload_hash,
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.consent_hash:
            raise ValueError("seven-figure dossier consent hash mismatch")


def bind_seven_figure_dossier_consent(
    authorization: ClientActionAuthorization,
    bundle: CaseProofBundle,
    dossier: SevenFigureAuthorizationDossier,
    client_signature: ExternalSignatureEvidence,
    *,
    consented_at: str,
    note: str,
) -> SevenFigureDossierConsent:
    """Bind explicit client consent and external signature to the exact final dossier."""
    payload_hash = seven_figure_consent_payload_hash(
        authorization,
        bundle,
        dossier,
        consented_at=consented_at,
        note=note,
    )
    verify_external_signature_evidence(
        client_signature,
        expected_payload_hash=payload_hash,
    )
    if _dt("client_signature.signed_at", client_signature.signed_at) < _dt(
        "dossier.assembled_at", dossier.assembled_at
    ):
        raise ValueError("client signature predates final dossier")
    body = {
        "schema": 1,
        "consent_version": "seven-figure-consent-v1",
        "authorization_id": authorization.authorization_id,
        "authorization_hash": authorization.proof_hash,
        "case_bundle_hash": bundle.bundle_hash,
        "finding_proof_hash": bundle.finding.proof_hash,
        "readiness_package_hash": dossier.readiness.package_hash,
        "readiness_dossier_hash": dossier.dossier_hash,
        "client_actor_id": authorization.client_actor_id,
        "approved_action_type": authorization.approved_action_type,
        "maximum_amount_cents": authorization.maximum_amount_cents,
        "consented_at": _iso("consented_at", consented_at),
        "note": _required("note", note),
        "client_signature": asdict(client_signature),
        "consent_payload_hash": payload_hash,
    }
    return SevenFigureDossierConsent(
        consent_version=body["consent_version"],
        authorization_id=body["authorization_id"],
        authorization_hash=body["authorization_hash"],
        case_bundle_hash=body["case_bundle_hash"],
        finding_proof_hash=body["finding_proof_hash"],
        readiness_package_hash=body["readiness_package_hash"],
        readiness_dossier_hash=body["readiness_dossier_hash"],
        client_actor_id=body["client_actor_id"],
        approved_action_type=body["approved_action_type"],
        maximum_amount_cents=body["maximum_amount_cents"],
        consented_at=body["consented_at"],
        note=body["note"],
        client_signature=client_signature,
        consent_payload_hash=body["consent_payload_hash"],
        consent_hash=canonical_hash(body),
    )


def verify_seven_figure_dossier_consent(
    consent: SevenFigureDossierConsent,
    authorization: ClientActionAuthorization,
    bundle: CaseProofBundle,
    dossier: SevenFigureAuthorizationDossier,
) -> None:
    consent.verify_integrity()
    expected_payload_hash = seven_figure_consent_payload_hash(
        authorization,
        bundle,
        dossier,
        consented_at=consent.consented_at,
        note=consent.note,
    )
    fields = {
        "authorization_id": authorization.authorization_id,
        "authorization_hash": authorization.proof_hash,
        "case_bundle_hash": bundle.bundle_hash,
        "finding_proof_hash": bundle.finding.proof_hash,
        "readiness_package_hash": dossier.readiness.package_hash,
        "readiness_dossier_hash": dossier.dossier_hash,
        "client_actor_id": authorization.client_actor_id,
        "approved_action_type": authorization.approved_action_type,
        "maximum_amount_cents": authorization.maximum_amount_cents,
        "consent_payload_hash": expected_payload_hash,
    }
    for name, expected in fields.items():
        if getattr(consent, name) != expected:
            raise ValueError(f"seven-figure dossier consent {name} mismatch")
    verify_external_signature_evidence(
        consent.client_signature,
        expected_payload_hash=expected_payload_hash,
    )
    if _dt("consent.client_signature.signed_at", consent.client_signature.signed_at) < _dt(
        "dossier.assembled_at", dossier.assembled_at
    ):
        raise ValueError("client signature predates final dossier")


@dataclass(frozen=True)
class SevenFigureAuthorizationSeal:
    """Final authorization gate binding provider build proof and client dossier consent."""

    seal_version: str
    case_bundle_hash: str
    finding_proof_hash: str
    authorization_hash: str
    readiness_package_hash: str
    readiness_dossier_hash: str
    journal_head_hash: str
    build_provider_receipt: BuildProviderVerificationReceipt
    client_consent: SevenFigureDossierConsent
    sealed_at: str
    sealed_by: str
    seal_hash: str

    def __post_init__(self) -> None:
        for name in (
            "seal_version",
            "case_bundle_hash",
            "finding_proof_hash",
            "authorization_hash",
            "readiness_package_hash",
            "readiness_dossier_hash",
            "journal_head_hash",
            "sealed_by",
            "seal_hash",
        ):
            _required(name, getattr(self, name))
        _iso("sealed_at", self.sealed_at)
        if self.seal_version != "seven-figure-authorization-seal-v1":
            raise ValueError("unsupported seven-figure authorization seal version")

    def integrity_body(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "seal_version": self.seal_version,
            "case_bundle_hash": self.case_bundle_hash,
            "finding_proof_hash": self.finding_proof_hash,
            "authorization_hash": self.authorization_hash,
            "readiness_package_hash": self.readiness_package_hash,
            "readiness_dossier_hash": self.readiness_dossier_hash,
            "journal_head_hash": self.journal_head_hash,
            "build_provider_receipt": asdict(self.build_provider_receipt),
            "client_consent": asdict(self.client_consent),
            "sealed_at": self.sealed_at,
            "sealed_by": self.sealed_by,
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.seal_hash:
            raise ValueError("seven-figure authorization seal hash mismatch")


def build_seven_figure_authorization_seal(
    authorization: ClientActionAuthorization,
    bundle: CaseProofBundle,
    dossier: SevenFigureAuthorizationDossier,
    build_provider_receipt: BuildProviderVerificationReceipt,
    client_consent: SevenFigureDossierConsent,
    *,
    journal_head_hash: str,
    sealed_at: str,
    sealed_by: str,
) -> SevenFigureAuthorizationSeal:
    verify_seven_figure_authorization_dossier(
        dossier,
        bundle,
        expected_journal_head_hash=journal_head_hash,
    )
    verify_action_authorization(bundle, authorization)
    verify_build_provider_verification(build_provider_receipt, dossier.build)
    verify_seven_figure_dossier_consent(
        client_consent,
        authorization,
        bundle,
        dossier,
    )
    sealed_at = _iso("sealed_at", sealed_at)
    sealed_by = _required("sealed_by", sealed_by)
    latest = max(
        _dt("dossier.assembled_at", dossier.assembled_at),
        _dt("build_provider.checked_at", build_provider_receipt.checked_at),
        _dt("client_signature.verified_at", client_consent.client_signature.verified_at),
    )
    if _dt("sealed_at", sealed_at) < latest:
        raise ValueError("seven-figure authorization seal predates a bound verification")
    body = {
        "schema": 1,
        "seal_version": "seven-figure-authorization-seal-v1",
        "case_bundle_hash": bundle.bundle_hash,
        "finding_proof_hash": bundle.finding.proof_hash,
        "authorization_hash": authorization.proof_hash,
        "readiness_package_hash": dossier.readiness.package_hash,
        "readiness_dossier_hash": dossier.dossier_hash,
        "journal_head_hash": _required("journal_head_hash", journal_head_hash),
        "build_provider_receipt": asdict(build_provider_receipt),
        "client_consent": asdict(client_consent),
        "sealed_at": sealed_at,
        "sealed_by": sealed_by,
    }
    return SevenFigureAuthorizationSeal(
        **{key: value for key, value in body.items() if key != "schema"},
        seal_hash=canonical_hash(body),
    )


def verify_seven_figure_authorization_seal(
    seal: SevenFigureAuthorizationSeal,
    authorization: ClientActionAuthorization,
    bundle: CaseProofBundle,
    dossier: SevenFigureAuthorizationDossier,
    *,
    expected_journal_head_hash: str,
) -> None:
    seal.verify_integrity()
    verify_seven_figure_authorization_dossier(
        dossier,
        bundle,
        expected_journal_head_hash=expected_journal_head_hash,
    )
    verify_action_authorization(bundle, authorization)
    verify_build_provider_verification(seal.build_provider_receipt, dossier.build)
    verify_seven_figure_dossier_consent(
        seal.client_consent,
        authorization,
        bundle,
        dossier,
    )
    fields = {
        "case_bundle_hash": bundle.bundle_hash,
        "finding_proof_hash": bundle.finding.proof_hash,
        "authorization_hash": authorization.proof_hash,
        "readiness_package_hash": dossier.readiness.package_hash,
        "readiness_dossier_hash": dossier.dossier_hash,
        "journal_head_hash": expected_journal_head_hash,
    }
    for name, expected in fields.items():
        if getattr(seal, name) != expected:
            raise ValueError(f"seven-figure authorization seal {name} mismatch")
    latest = max(
        _dt("dossier.assembled_at", dossier.assembled_at),
        _dt("build_provider.checked_at", seal.build_provider_receipt.checked_at),
        _dt("client_signature.verified_at", seal.client_consent.client_signature.verified_at),
    )
    if _dt("seal.sealed_at", seal.sealed_at) < latest:
        raise ValueError("seven-figure authorization seal predates bound verification")


def authorization_seal_to_payload(
    seal: SevenFigureAuthorizationSeal,
) -> dict[str, Any]:
    seal.verify_integrity()
    return {**seal.integrity_body(), "seal_hash": seal.seal_hash}


def authorization_seal_from_payload(
    payload: Mapping[str, Any],
) -> SevenFigureAuthorizationSeal:
    build_receipt = BuildProviderVerificationReceipt(
        **dict(payload["build_provider_receipt"])
    )
    consent_raw = dict(payload["client_consent"])
    client_signature = ExternalSignatureEvidence(**dict(consent_raw["client_signature"]))
    client_consent = SevenFigureDossierConsent(
        consent_version=consent_raw["consent_version"],
        authorization_id=consent_raw["authorization_id"],
        authorization_hash=consent_raw["authorization_hash"],
        case_bundle_hash=consent_raw["case_bundle_hash"],
        finding_proof_hash=consent_raw["finding_proof_hash"],
        readiness_package_hash=consent_raw["readiness_package_hash"],
        readiness_dossier_hash=consent_raw["readiness_dossier_hash"],
        client_actor_id=consent_raw["client_actor_id"],
        approved_action_type=consent_raw["approved_action_type"],
        maximum_amount_cents=consent_raw["maximum_amount_cents"],
        consented_at=consent_raw["consented_at"],
        note=consent_raw["note"],
        client_signature=client_signature,
        consent_payload_hash=consent_raw["consent_payload_hash"],
        consent_hash=consent_raw["consent_hash"],
    )
    seal = SevenFigureAuthorizationSeal(
        seal_version=payload["seal_version"],
        case_bundle_hash=payload["case_bundle_hash"],
        finding_proof_hash=payload["finding_proof_hash"],
        authorization_hash=payload["authorization_hash"],
        readiness_package_hash=payload["readiness_package_hash"],
        readiness_dossier_hash=payload["readiness_dossier_hash"],
        journal_head_hash=payload["journal_head_hash"],
        build_provider_receipt=build_receipt,
        client_consent=client_consent,
        sealed_at=payload["sealed_at"],
        sealed_by=payload["sealed_by"],
        seal_hash=payload["seal_hash"],
    )
    seal.verify_integrity()
    return seal
