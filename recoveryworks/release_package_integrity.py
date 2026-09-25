"""Independent integrity verification for durable RecoveryWorks release packages."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, TYPE_CHECKING

from recoveryworks.models import canonical_hash, normalize_sha256, normalize_utc_timestamp
from recoveryworks.release_control import (
    EnvironmentPromotionGate,
    RecoveryWorksReleaseManifest,
    ReleaseApprovalArtifact,
    ReleaseEnvironment,
    ReleaseRollbackManifest,
)

if TYPE_CHECKING:
    from recoveryworks.production_adversarial_certification import (
        ProductionAdversarialCertification,
    )


_REQUIRED_FILES = (
    "release-manifest.json",
    "release-approvals.json",
    "rollback-manifest.json",
    "promotion-gate.json",
    "adversarial-certification.json",
)


@dataclass(frozen=True)
class ReleasePackageIntegrityReceipt:
    receipt_id: str
    release_id: str
    release_proof_hash: str
    promotion_gate_proof_hash: str
    adversarial_certification_proof_hash: str
    approval_proof_hashes: tuple[str, ...]
    rollback_manifest_proof_hash: str
    artifact_sha256: tuple[tuple[str, str], ...]
    verified_at: str
    verified: bool = True
    external_actions_performed: bool = False

    def __post_init__(self) -> None:
        for name in (
            "release_proof_hash",
            "promotion_gate_proof_hash",
            "adversarial_certification_proof_hash",
            "rollback_manifest_proof_hash",
        ):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        approvals = tuple(sorted(normalize_sha256("approval_proof_hash", value) for value in self.approval_proof_hashes))
        object.__setattr__(self, "approval_proof_hashes", approvals)
        artifacts = tuple(sorted(
            (name, normalize_sha256("artifact_sha256", digest))
            for name, digest in self.artifact_sha256
        ))
        if tuple(name for name, _ in artifacts) != tuple(sorted(_REQUIRED_FILES)):
            raise ValueError("release package artifact set is incomplete")
        object.__setattr__(self, "artifact_sha256", artifacts)
        object.__setattr__(
            self, "verified_at", normalize_utc_timestamp("verified_at", self.verified_at)
        )
        if self.verified is not True or self.external_actions_performed:
            raise ValueError("release package verification must be verified and read-only")
        expected = "recoveryworks-release-package-integrity:" + canonical_hash(self._identity())
        if self.receipt_id != expected:
            raise ValueError("receipt_id does not bind release package integrity")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "promotion_gate_proof_hash": self.promotion_gate_proof_hash,
            "adversarial_certification_proof_hash": self.adversarial_certification_proof_hash,
            "approval_proof_hashes": list(self.approval_proof_hashes),
            "rollback_manifest_proof_hash": self.rollback_manifest_proof_hash,
            "artifact_sha256": [list(item) for item in self.artifact_sha256],
            "verified_at": self.verified_at,
            "verified": True,
            "external_actions_performed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "receipt_id": self.receipt_id,
            "proof_hash": self.proof_hash,
            "state": "RELEASE_PACKAGE_VERIFIED",
        }


def _approval_payload(approvals: tuple[ReleaseApprovalArtifact, ...]) -> list[dict[str, Any]]:
    return [
        {
            **approval._identity(),
            "approval_id": approval.approval_id,
            "proof_hash": approval.proof_hash,
        }
        for approval in approvals
    ]


def _rollback_payload(rollback: ReleaseRollbackManifest) -> dict[str, Any]:
    return {
        **rollback._identity(),
        "rollback_id": rollback.rollback_id,
        "proof_hash": rollback.proof_hash,
    }


def verify_release_control_package(
    *,
    directory: str | Path,
    release: RecoveryWorksReleaseManifest,
    approvals: tuple[ReleaseApprovalArtifact, ...],
    rollback: ReleaseRollbackManifest,
    gate: EnvironmentPromotionGate,
    adversarial_certification: "ProductionAdversarialCertification",
    verified_at: str,
) -> ReleasePackageIntegrityReceipt:
    from recoveryworks.production_adversarial_certification import (
        AdversarialCertificationState,
        ProductionAdversarialCertification,
    )

    if gate.environment is not ReleaseEnvironment.PRODUCTION:
        raise ValueError("release package verifier currently requires PRODUCTION gate")
    if not isinstance(adversarial_certification, ProductionAdversarialCertification):
        raise ValueError("invalid adversarial certification artifact")
    if adversarial_certification.state is not AdversarialCertificationState.PASS:
        raise ValueError("adversarial certification did not pass")
    if gate.release_id != release.release_id or gate.release_proof_hash != release.proof_hash:
        raise ValueError("promotion gate does not bind release")
    if gate.adversarial_certification_proof_hash != adversarial_certification.proof_hash:
        raise ValueError("adversarial certification does not bind promotion gate")
    if rollback.release_id != release.release_id or rollback.release_proof_hash != release.proof_hash:
        raise ValueError("rollback manifest does not bind release")
    expected_approval_hashes = tuple(sorted(approval.proof_hash for approval in approvals))
    if tuple(sorted(gate.approval_hashes)) != expected_approval_hashes:
        raise ValueError("approval set does not bind promotion gate")
    if gate.rollback_manifest_proof_hash != rollback.proof_hash:
        raise ValueError("rollback manifest does not bind promotion gate")

    target = Path(directory)
    expected_payloads = {
        "release-manifest.json": release.as_dict(),
        "release-approvals.json": _approval_payload(approvals),
        "rollback-manifest.json": _rollback_payload(rollback),
        "promotion-gate.json": gate.as_dict(),
        "adversarial-certification.json": adversarial_certification.as_dict(),
    }
    artifact_hashes: list[tuple[str, str]] = []
    for name in _REQUIRED_FILES:
        path = target / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"release package artifact missing or unsafe: {name}")
        raw = path.read_bytes()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"release package artifact is invalid JSON: {name}") from exc
        if payload != expected_payloads[name]:
            raise ValueError(f"release package artifact mismatch: {name}")
        artifact_hashes.append((name, hashlib.sha256(raw).hexdigest()))

    identity = {
        "schema": 1,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "promotion_gate_proof_hash": gate.proof_hash,
        "adversarial_certification_proof_hash": adversarial_certification.proof_hash,
        "approval_proof_hashes": list(expected_approval_hashes),
        "rollback_manifest_proof_hash": rollback.proof_hash,
        "artifact_sha256": [list(item) for item in sorted(artifact_hashes)],
        "verified_at": normalize_utc_timestamp("verified_at", verified_at),
        "verified": True,
        "external_actions_performed": False,
    }
    return ReleasePackageIntegrityReceipt(
        receipt_id="recoveryworks-release-package-integrity:" + canonical_hash(identity),
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        promotion_gate_proof_hash=gate.proof_hash,
        adversarial_certification_proof_hash=adversarial_certification.proof_hash,
        approval_proof_hashes=expected_approval_hashes,
        rollback_manifest_proof_hash=rollback.proof_hash,
        artifact_sha256=tuple(artifact_hashes),
        verified_at=verified_at,
        verified=True,
        external_actions_performed=False,
    )


def assert_release_package_subject(
    receipt: ReleasePackageIntegrityReceipt,
    *,
    release: RecoveryWorksReleaseManifest,
    gate: EnvironmentPromotionGate,
    adversarial_certification: "ProductionAdversarialCertification",
    previously_consumed_receipt_proof_hashes: tuple[str, ...] = (),
) -> None:
    """Fail closed on cross-release substitution or an explicitly consumed package receipt."""
    if receipt.release_id != release.release_id or receipt.release_proof_hash != release.proof_hash:
        raise ValueError("release package receipt does not bind expected release")
    if receipt.promotion_gate_proof_hash != gate.proof_hash:
        raise ValueError("release package receipt does not bind expected promotion gate")
    if receipt.adversarial_certification_proof_hash != adversarial_certification.proof_hash:
        raise ValueError("release package receipt does not bind expected certification")
    consumed = {normalize_sha256("consumed_receipt_proof_hash", value) for value in previously_consumed_receipt_proof_hashes}
    if receipt.proof_hash in consumed:
        raise ValueError("release package receipt has already been consumed")
