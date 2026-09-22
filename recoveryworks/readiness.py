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
    ArtifactReplayEntry,
    CalculationReplayReceipt,
    CaseArtifactReplayReceipt,
    CaseProofBundle,
    HostileExaminationPacket,
    ProofSeal,
    SEVEN_FIGURE_CENTS,
    verify_calculation_replay,
    verify_case_artifact_replay,
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
    "HOSTILE_EXAM_PACKET_PROVIDER_VERIFIED",
    "HOSTILE_EXAM_REPLAY_RECEIPTS_VERIFIED",
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
class HostilePacketVerificationEvidence:
    """Provider/KMS verification receipt for the hostile packet and proof seal.

    RecoveryOS does not possess the production HMAC key. A provider-specific
    adapter must verify both HMAC signatures with the managed key, then record
    the provider receipt here. This receipt is itself content-addressed.
    """

    verification_id: str
    hostile_packet_hash: str
    hostile_packet_signature_hash: str
    proof_seal_id: str
    proof_seal_signature_hash: str
    provider: str
    key_id: str
    algorithm: str
    provider_request_id: str
    verification_receipt_hash: str
    verified_at: str
    verified_by_adapter: str
    provider_verified: bool
    evidence_hash: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "verification_id",
            "hostile_packet_hash",
            "hostile_packet_signature_hash",
            "proof_seal_id",
            "proof_seal_signature_hash",
            "provider",
            "key_id",
            "algorithm",
            "provider_request_id",
            "verification_receipt_hash",
            "verified_by_adapter",
            "evidence_hash",
        ):
            _required(name, getattr(self, name))
        _iso("verified_at", self.verified_at)
        if self.algorithm != "HMAC-SHA256":
            raise ValueError("hostile packet provider verification must use HMAC-SHA256")
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
            raise ValueError("hostile packet provider evidence hash mismatch")


def _signature_hex_hash(value: str) -> str:
    return canonical_hash({
        "schema": 1,
        "signature_hex": _required("signature_hex", value),
    })


def record_hostile_packet_provider_verification(
    packet: HostileExaminationPacket,
    proof_seal: ProofSeal,
    *,
    verification_id: str,
    provider: str,
    key_id: str,
    provider_request_id: str,
    verification_receipt_hash: str,
    verified_at: str,
    verified_by_adapter: str,
    provider_verified: bool,
    metadata: Mapping[str, Any] | None = None,
) -> HostilePacketVerificationEvidence:
    """Record a managed-key verification of packet + proof-seal HMAC signatures."""
    if packet.proof_seal_id != proof_seal.seal_id:
        raise ValueError("hostile packet proof seal id mismatch")
    if packet.proof_seal_signature_hex != proof_seal.signature_hex:
        raise ValueError("hostile packet proof seal signature mismatch")
    if packet.key_id != proof_seal.key_id:
        raise ValueError("hostile packet/proof seal key mismatch")
    if packet.algorithm != "HMAC-SHA256" or proof_seal.algorithm != "HMAC-SHA256":
        raise ValueError("hostile packet/proof seal algorithm mismatch")
    if key_id != packet.key_id:
        raise ValueError("provider verification key_id does not match packet key")
    if provider_verified:
        _required("provider_request_id", provider_request_id)
        _required("verification_receipt_hash", verification_receipt_hash)

    body = {
        "schema": 1,
        "verification_id": _required("verification_id", verification_id),
        "hostile_packet_hash": hostile_packet_hash(packet),
        "hostile_packet_signature_hash": _signature_hex_hash(
            packet.packet_signature_hex
        ),
        "proof_seal_id": proof_seal.seal_id,
        "proof_seal_signature_hash": _signature_hex_hash(proof_seal.signature_hex),
        "provider": _required("provider", provider),
        "key_id": _required("key_id", key_id),
        "algorithm": "HMAC-SHA256",
        "provider_request_id": _required("provider_request_id", provider_request_id),
        "verification_receipt_hash": _required(
            "verification_receipt_hash", verification_receipt_hash
        ),
        "verified_at": _iso("verified_at", verified_at),
        "verified_by_adapter": _required(
            "verified_by_adapter", verified_by_adapter
        ),
        "provider_verified": provider_verified,
        "metadata": dict(metadata or {}),
    }
    return HostilePacketVerificationEvidence(
        **{key: value for key, value in body.items() if key != "schema"},
        evidence_hash=canonical_hash(body),
    )


def verify_hostile_packet_provider_evidence(
    evidence: HostilePacketVerificationEvidence,
    packet: HostileExaminationPacket,
    proof_seal: ProofSeal,
) -> None:
    evidence.verify_integrity()
    if not evidence.provider_verified:
        raise ValueError("hostile packet/proof seal were not provider-verified")
    if evidence.hostile_packet_hash != hostile_packet_hash(packet):
        raise ValueError("hostile packet provider receipt packet hash mismatch")
    if evidence.hostile_packet_signature_hash != _signature_hex_hash(
        packet.packet_signature_hex
    ):
        raise ValueError("hostile packet provider receipt signature mismatch")
    if evidence.proof_seal_id != proof_seal.seal_id:
        raise ValueError("hostile packet provider receipt proof seal id mismatch")
    if evidence.proof_seal_signature_hash != _signature_hex_hash(
        proof_seal.signature_hex
    ):
        raise ValueError("hostile packet provider receipt proof seal signature mismatch")
    if evidence.key_id != packet.key_id or evidence.key_id != proof_seal.key_id:
        raise ValueError("hostile packet provider receipt key mismatch")
    if evidence.algorithm != packet.algorithm or evidence.algorithm != proof_seal.algorithm:
        raise ValueError("hostile packet provider receipt algorithm mismatch")


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
    hostile_packet: HostileExaminationPacket
    artifact_replay: CaseArtifactReplayReceipt
    calculation_replay: CalculationReplayReceipt
    proof_seal: ProofSeal
    hostile_packet_verification: HostilePacketVerificationEvidence
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
            "hostile_packet": asdict(self.hostile_packet),
            "artifact_replay": asdict(self.artifact_replay),
            "calculation_replay": asdict(self.calculation_replay),
            "proof_seal": asdict(self.proof_seal),
            "hostile_packet_verification": asdict(
                self.hostile_packet_verification
            ),
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
    artifact_replay: CaseArtifactReplayReceipt,
    calculation_replay: CalculationReplayReceipt,
    proof_seal: ProofSeal,
    hostile_packet_verification: HostilePacketVerificationEvidence,
    journal_head_hash: str,
    evaluated_at: str,
    evaluated_by: str,
) -> SevenFigureReadinessPackage:
    """Evaluate every mandatory assurance check and freeze the authorization gate."""
    verify_case_bundle(bundle)
    if bundle.finding.potential_recovery_cents < SEVEN_FIGURE_CENTS:
        raise ValueError("seven-figure readiness gate only applies to seven-figure findings")

    verify_case_artifact_replay(artifact_replay, bundle)
    verify_calculation_replay(calculation_replay, bundle, artifact_replay)
    if packet.artifact_replay_receipt_hash != artifact_replay.receipt_hash:
        raise ValueError("hostile packet artifact replay receipt mismatch")
    if (
        packet.calculation_replay_receipt_hash
        != calculation_replay.receipt_hash
    ):
        raise ValueError("hostile packet calculation replay receipt mismatch")
    if packet.proof_seal_id != proof_seal.seal_id:
        raise ValueError("hostile packet proof seal id mismatch")
    if packet.proof_seal_signature_hex != proof_seal.signature_hex:
        raise ValueError("hostile packet proof seal signature mismatch")
    if packet.journal_head_hash != journal_head_hash:
        raise ValueError("hostile packet journal head mismatch")
    if proof_seal.case_bundle_hash != bundle.bundle_hash:
        raise ValueError("proof seal case bundle mismatch")
    if proof_seal.finding_proof_hash != bundle.finding.proof_hash:
        raise ValueError("proof seal finding proof mismatch")
    if proof_seal.journal_head_hash != journal_head_hash:
        raise ValueError("proof seal journal head mismatch")
    verify_hostile_packet_provider_evidence(
        hostile_packet_verification,
        packet,
        proof_seal,
    )

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
        _dt(
            "hostile_packet_verification.verified_at",
            hostile_packet_verification.verified_at,
        ),
        _dt("artifact_replay.replayed_at", artifact_replay.replayed_at),
        _dt(
            "calculation_replay.reproduced_at",
            calculation_replay.reproduced_at,
        ),
        _dt("proof_seal.sealed_at", proof_seal.sealed_at),
        _dt("hostile_packet.assembled_at", packet.assembled_at),
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
        "hostile_packet": asdict(packet),
        "artifact_replay": asdict(artifact_replay),
        "calculation_replay": asdict(calculation_replay),
        "proof_seal": asdict(proof_seal),
        "hostile_packet_verification": asdict(hostile_packet_verification),
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
        hostile_packet=packet,
        artifact_replay=artifact_replay,
        calculation_replay=calculation_replay,
        proof_seal=proof_seal,
        hostile_packet_verification=hostile_packet_verification,
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

    if package.hostile_packet_hash != hostile_packet_hash(package.hostile_packet):
        raise ValueError("readiness hostile packet hash mismatch")
    verify_case_artifact_replay(package.artifact_replay, bundle)
    verify_calculation_replay(
        package.calculation_replay,
        bundle,
        package.artifact_replay,
    )
    if (
        package.hostile_packet.artifact_replay_receipt_hash
        != package.artifact_replay.receipt_hash
    ):
        raise ValueError("readiness hostile packet artifact replay mismatch")
    if (
        package.hostile_packet.calculation_replay_receipt_hash
        != package.calculation_replay.receipt_hash
    ):
        raise ValueError("readiness hostile packet calculation replay mismatch")
    if package.hostile_packet.proof_seal_id != package.proof_seal.seal_id:
        raise ValueError("readiness hostile packet proof seal id mismatch")
    if (
        package.hostile_packet.proof_seal_signature_hex
        != package.proof_seal.signature_hex
    ):
        raise ValueError("readiness hostile packet proof seal signature mismatch")
    if package.hostile_packet.journal_head_hash != package.journal_head_hash:
        raise ValueError("readiness hostile packet journal head mismatch")
    if package.proof_seal.case_bundle_hash != bundle.bundle_hash:
        raise ValueError("readiness proof seal case bundle mismatch")
    if package.proof_seal.finding_proof_hash != bundle.finding.proof_hash:
        raise ValueError("readiness proof seal finding mismatch")
    if package.proof_seal.journal_head_hash != package.journal_head_hash:
        raise ValueError("readiness proof seal journal head mismatch")
    verify_hostile_packet_provider_evidence(
        package.hostile_packet_verification,
        package.hostile_packet,
        package.proof_seal,
    )

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
        _dt(
            "hostile_packet_verification.verified_at",
            package.hostile_packet_verification.verified_at,
        ),
        _dt("artifact_replay.replayed_at", package.artifact_replay.replayed_at),
        _dt(
            "calculation_replay.reproduced_at",
            package.calculation_replay.reproduced_at,
        ),
        _dt("proof_seal.sealed_at", package.proof_seal.sealed_at),
        _dt("hostile_packet.assembled_at", package.hostile_packet.assembled_at),
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
    hostile_packet = HostileExaminationPacket(**dict(payload["hostile_packet"]))
    artifact_raw = dict(payload["artifact_replay"])
    artifact_replay = CaseArtifactReplayReceipt(
        case_bundle_hash=artifact_raw["case_bundle_hash"],
        finding_proof_hash=artifact_raw["finding_proof_hash"],
        replayed_at=artifact_raw["replayed_at"],
        replayed_by=artifact_raw["replayed_by"],
        entries=tuple(
            ArtifactReplayEntry(**dict(item))
            for item in artifact_raw.get("entries", [])
        ),
        receipt_hash=artifact_raw["receipt_hash"],
    )
    calculation_replay = CalculationReplayReceipt(
        **dict(payload["calculation_replay"])
    )
    proof_seal = ProofSeal(**dict(payload["proof_seal"]))
    hostile_packet_verification = HostilePacketVerificationEvidence(
        **dict(payload["hostile_packet_verification"])
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
        hostile_packet=hostile_packet,
        artifact_replay=artifact_replay,
        calculation_replay=calculation_replay,
        proof_seal=proof_seal,
        hostile_packet_verification=hostile_packet_verification,
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
    if hostile_packet_hash(readiness.hostile_packet) != hostile_packet_hash(
        hostile_packet
    ):
        raise ValueError("authorization dossier hostile packet differs from readiness")
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
