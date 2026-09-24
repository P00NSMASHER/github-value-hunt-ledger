"""Unified production admission gate for RecoveryWorks releases."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from recoveryworks.container_build import ContainerBuildManifest
from recoveryworks.models import canonical_hash, normalize_sha256, normalize_utc_timestamp
from recoveryworks.production_resilience import DisasterRecoveryRehearsal
from recoveryworks.release_control import (
    EnvironmentPromotionGate,
    RecoveryWorksReleaseManifest,
    ReleaseEnvironment,
)
from recoveryworks.release_security_bridge import VerifiedReleaseSecurityEvidence


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(
        normalize_utc_timestamp("timestamp", value).replace("Z", "+00:00")
    )


@dataclass(frozen=True)
class ProductionAdmissionPolicy:
    max_dr_age_seconds: int = 7 * 24 * 60 * 60

    def __post_init__(self) -> None:
        if type(self.max_dr_age_seconds) is not int or self.max_dr_age_seconds <= 0:
            raise ValueError("max_dr_age_seconds must be a positive integer")


@dataclass(frozen=True)
class ProductionAdmissionGate:
    admission_id: str
    release_id: str
    release_proof_hash: str
    promotion_gate_proof_hash: str
    security_evidence_proof_hash: str
    dr_rehearsal_proof_hash: str
    container_build_manifest_proof_hash: str
    container_image_digest: str
    source_commit: str
    admitted_at: str
    policy: ProductionAdmissionPolicy
    admitted: bool = True
    deployment_execution_enabled: bool = False

    def __post_init__(self) -> None:
        for name in (
            "release_proof_hash",
            "promotion_gate_proof_hash",
            "security_evidence_proof_hash",
            "dr_rehearsal_proof_hash",
            "container_build_manifest_proof_hash",
            "container_image_digest",
        ):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        object.__setattr__(
            self, "admitted_at",
            normalize_utc_timestamp("admitted_at", self.admitted_at)
        )
        if self.admitted is not True:
            raise ValueError("production admission gate must be admitted")
        if self.deployment_execution_enabled:
            raise ValueError("production admission gate cannot execute deployment")
        expected = "recoveryworks-production-admission:" + canonical_hash(
            self._identity()
        )
        if self.admission_id != expected:
            raise ValueError("admission_id does not bind production admission")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "promotion_gate_proof_hash": self.promotion_gate_proof_hash,
            "security_evidence_proof_hash": self.security_evidence_proof_hash,
            "dr_rehearsal_proof_hash": self.dr_rehearsal_proof_hash,
            "container_build_manifest_proof_hash":
                self.container_build_manifest_proof_hash,
            "container_image_digest": self.container_image_digest,
            "source_commit": self.source_commit,
            "admitted_at": self.admitted_at,
            "policy": asdict(self.policy),
            "admitted": True,
            "deployment_execution_enabled": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "admission_id": self.admission_id,
            "proof_hash": self.proof_hash,
            "state": "PRODUCTION_ADMISSION_READY",
        }


def build_production_admission_gate(
    release: RecoveryWorksReleaseManifest,
    promotion_gate: EnvironmentPromotionGate,
    security_evidence: VerifiedReleaseSecurityEvidence,
    dr_rehearsal: DisasterRecoveryRehearsal,
    build_manifest: ContainerBuildManifest,
    *,
    admitted_at: str,
    policy: ProductionAdmissionPolicy = ProductionAdmissionPolicy(),
) -> ProductionAdmissionGate:
    admitted_at = normalize_utc_timestamp("admitted_at", admitted_at)
    if promotion_gate.environment is not ReleaseEnvironment.PRODUCTION:
        raise ValueError("production admission requires PRODUCTION promotion gate")
    if not promotion_gate.promotion_ready:
        raise ValueError("promotion gate is not ready")
    if (
        promotion_gate.release_id != release.release_id
        or promotion_gate.release_proof_hash != release.proof_hash
    ):
        raise ValueError("promotion gate does not bind release")
    if (
        security_evidence.release_id != release.release_id
        or security_evidence.release_proof_hash != release.proof_hash
    ):
        raise ValueError("security evidence does not bind release")
    if security_evidence.container_image_digest != release.container_image_digest:
        raise ValueError("security evidence image digest mismatch")
    if security_evidence.source_commit != release.source_commit:
        raise ValueError("security evidence source commit mismatch")
    if build_manifest.source_commit != release.source_commit:
        raise ValueError("build manifest source commit mismatch")
    if build_manifest.proof_hash != release.container_build_manifest_proof_hash:
        raise ValueError("build manifest proof mismatch")
    if not dr_rehearsal.passed:
        raise ValueError("DR rehearsal did not pass")
    completed = _instant(dr_rehearsal.completed_at)
    admitted = _instant(admitted_at)
    if completed > admitted:
        raise ValueError("DR rehearsal cannot complete after admission")
    age = int((admitted - completed).total_seconds())
    if age > policy.max_dr_age_seconds:
        raise ValueError("DR rehearsal is too old for production admission")

    identity = {
        "schema": 1,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "promotion_gate_proof_hash": promotion_gate.proof_hash,
        "security_evidence_proof_hash": security_evidence.proof_hash,
        "dr_rehearsal_proof_hash": dr_rehearsal.proof_hash,
        "container_build_manifest_proof_hash": build_manifest.proof_hash,
        "container_image_digest": release.container_image_digest,
        "source_commit": release.source_commit,
        "admitted_at": admitted_at,
        "policy": asdict(policy),
        "admitted": True,
        "deployment_execution_enabled": False,
    }
    return ProductionAdmissionGate(
        admission_id="recoveryworks-production-admission:" + canonical_hash(identity),
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        promotion_gate_proof_hash=promotion_gate.proof_hash,
        security_evidence_proof_hash=security_evidence.proof_hash,
        dr_rehearsal_proof_hash=dr_rehearsal.proof_hash,
        container_build_manifest_proof_hash=build_manifest.proof_hash,
        container_image_digest=release.container_image_digest,
        source_commit=release.source_commit,
        admitted_at=admitted_at,
        policy=policy,
        admitted=True,
        deployment_execution_enabled=False,
    )
