"""Proof-bound production launch/readiness review dossier."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from recoveryworks.commercial_pilot import CloudCommercialPilotPackage
from recoveryworks.models import canonical_hash, normalize_sha256, normalize_utc_timestamp
from recoveryworks.private_io import atomic_private_write
from recoveryworks.production_admission import ProductionAdmissionGate
from recoveryworks.production_observability import (
    ProductionRunManifest,
    ProductionRunStatus,
)
from recoveryworks.production_resilience import DisasterRecoveryRehearsal
from recoveryworks.release_control import (
    RecoveryWorksReleaseManifest,
    ReleaseRollbackManifest,
)
from recoveryworks.release_security_bridge import VerifiedReleaseSecurityEvidence


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


@dataclass(frozen=True)
class ProductionLaunchDossier:
    dossier_id: str
    release_id: str
    release_proof_hash: str
    production_admission_proof_hash: str
    security_evidence_proof_hash: str
    dr_rehearsal_proof_hash: str
    observability_run_manifest_proof_hash: str
    rollback_manifest_proof_hash: str
    commercial_pilot_package_proof_hash: str
    reviewed_at: str
    cfo_summary: dict[str, Any]
    cto_summary: dict[str, Any]
    security_summary: dict[str, Any]
    operational_summary: dict[str, Any]
    assumptions: tuple[str, ...]
    externally_deployed: bool = False
    customer_contract_signed: bool = False
    customer_revenue_verified: bool = False
    economics_guaranteed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "release_id", _text("release_id", self.release_id))
        for name in (
            "release_proof_hash",
            "production_admission_proof_hash",
            "security_evidence_proof_hash",
            "dr_rehearsal_proof_hash",
            "observability_run_manifest_proof_hash",
            "rollback_manifest_proof_hash",
            "commercial_pilot_package_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self, "reviewed_at",
            normalize_utc_timestamp("reviewed_at", self.reviewed_at)
        )
        if not all(self.assumptions):
            raise ValueError("launch dossier assumptions must be non-empty")
        for name in (
            "externally_deployed",
            "customer_contract_signed",
            "customer_revenue_verified",
            "economics_guaranteed",
        ):
            if getattr(self, name):
                raise ValueError(f"{name} must remain false in readiness dossier")
        expected = "recoveryworks-launch-dossier:" + canonical_hash(self._identity())
        if self.dossier_id != expected:
            raise ValueError("dossier_id does not bind launch dossier")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "production_admission_proof_hash": self.production_admission_proof_hash,
            "security_evidence_proof_hash": self.security_evidence_proof_hash,
            "dr_rehearsal_proof_hash": self.dr_rehearsal_proof_hash,
            "observability_run_manifest_proof_hash":
                self.observability_run_manifest_proof_hash,
            "rollback_manifest_proof_hash": self.rollback_manifest_proof_hash,
            "commercial_pilot_package_proof_hash":
                self.commercial_pilot_package_proof_hash,
            "reviewed_at": self.reviewed_at,
            "cfo_summary": self.cfo_summary,
            "cto_summary": self.cto_summary,
            "security_summary": self.security_summary,
            "operational_summary": self.operational_summary,
            "assumptions": list(self.assumptions),
            "externally_deployed": False,
            "customer_contract_signed": False,
            "customer_revenue_verified": False,
            "economics_guaranteed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "dossier_id": self.dossier_id,
            "proof_hash": self.proof_hash,
            "state": "PRODUCTION_REVIEW_DOSSIER_READY",
        }

    def to_markdown(self) -> str:
        lines = [
            "# RecoveryWorks Production Launch Readiness Dossier",
            "",
            f"Release: {self.release_id}",
            f"Dossier proof: {self.proof_hash}",
            f"Reviewed at: {self.reviewed_at}",
            "",
            "## CFO review",
            "",
        ]
        for key, value in self.cfo_summary.items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## CTO review", ""])
        for key, value in self.cto_summary.items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Security review", ""])
        for key, value in self.security_summary.items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Operations review", ""])
        for key, value in self.operational_summary.items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Assumptions / limitations", ""])
        lines.extend(f"- {item}" for item in self.assumptions)
        lines.extend([
            "",
            "This dossier proves internal readiness artifacts only. It does not prove a signed customer contract, verified customer revenue, external production deployment, or guaranteed economics.",
            "",
        ])
        return "\n".join(lines)


def build_production_launch_dossier(
    *,
    release: RecoveryWorksReleaseManifest,
    admission: ProductionAdmissionGate,
    security_evidence: VerifiedReleaseSecurityEvidence,
    dr_rehearsal: DisasterRecoveryRehearsal,
    observability_run: ProductionRunManifest,
    rollback_manifest: ReleaseRollbackManifest,
    commercial_pilot: CloudCommercialPilotPackage,
    reviewed_at: str,
) -> ProductionLaunchDossier:
    if admission.release_id != release.release_id:
        raise ValueError("admission release mismatch")
    if admission.release_proof_hash != release.proof_hash:
        raise ValueError("admission release proof mismatch")
    if security_evidence.release_id != release.release_id:
        raise ValueError("security evidence release mismatch")
    if security_evidence.release_proof_hash != release.proof_hash:
        raise ValueError("security evidence release proof mismatch")
    if rollback_manifest.release_id != release.release_id:
        raise ValueError("rollback manifest release mismatch")
    if rollback_manifest.release_proof_hash != release.proof_hash:
        raise ValueError("rollback manifest release proof mismatch")
    if observability_run.status is not ProductionRunStatus.SUCCEEDED:
        raise ValueError("launch dossier requires a successful production-style run")
    if observability_run.failure_code is not None:
        raise ValueError("successful observability run cannot have failure code")
    if (
        observability_run.container_build_manifest_proof_hash
        != admission.container_build_manifest_proof_hash
    ):
        raise ValueError("observability/build provenance mismatch")
    if dr_rehearsal.passed is not True:
        raise ValueError("launch dossier requires passing DR rehearsal")

    pricing = commercial_pilot.pricing
    cfo = {
        "offer_name": commercial_pilot.offer_name,
        "buyer_profile": commercial_pilot.buyer_profile,
        "pricing_currency": pricing.currency,
        "diagnostic_fee_cents_hypothesis": pricing.diagnostic_fee_cents,
        "recovered_cash_success_fee_bps_hypothesis":
            pricing.recovered_cash_success_fee_bps,
        "monthly_assurance_fee_cents_hypothesis":
            pricing.monthly_assurance_fee_cents,
        "pricing_is_hypothesis": pricing.pricing_is_hypothesis,
        "success_fee_basis": "verified recovered cash only",
        "customer_revenue_verified": False,
    }
    cto = {
        "release_source_commit": release.source_commit,
        "container_image_digest": release.container_image_digest,
        "production_admission_ready": admission.admitted,
        "observability_run_status": observability_run.status.value,
        "rollback_target_release_id": rollback_manifest.target_release_id,
        "dr_rpo_seconds": dr_rehearsal.rpo_seconds,
        "dr_rto_seconds": dr_rehearsal.rto_seconds,
    }
    security = {
        "external_security_evidence_verified": security_evidence.verified,
        "security_evidence_proof_hash": security_evidence.proof_hash,
        "container_image_digest": security_evidence.container_image_digest,
        "source_commit": security_evidence.source_commit,
        "production_admission_proof_hash": admission.proof_hash,
        "cloud_mutation_in_commercial_scope":
            commercial_pilot.scope.cloud_mutation_in_scope,
    }
    operations = {
        "observability_manifest_id": observability_run.manifest_id,
        "observability_proof_hash": observability_run.proof_hash,
        "dr_rehearsal_state": "PASSED",
        "rollback_manifest_ready": True,
        "production_admission_state": "READY",
        "external_deployment_performed": False,
        "external_actions_in_commercial_scope":
            commercial_pilot.scope.external_recovery_actions_in_scope,
    }
    assumptions = (
        "Commercial pricing is an internal hypothesis until a separately finalized agreement exists.",
        "No customer contract, payment, revenue, or traction is represented by this dossier.",
        "Production admission and security proofs are internal readiness evidence, not proof of external deployment.",
        "Recovery success fees apply only to independently verified recovered cash.",
        "Prospective savings and diagnostic exposure remain separate from recovery revenue.",
    )
    identity = {
        "schema": 1,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "production_admission_proof_hash": admission.proof_hash,
        "security_evidence_proof_hash": security_evidence.proof_hash,
        "dr_rehearsal_proof_hash": dr_rehearsal.proof_hash,
        "observability_run_manifest_proof_hash": observability_run.proof_hash,
        "rollback_manifest_proof_hash": rollback_manifest.proof_hash,
        "commercial_pilot_package_proof_hash": commercial_pilot.proof_hash,
        "reviewed_at": normalize_utc_timestamp("reviewed_at", reviewed_at),
        "cfo_summary": cfo,
        "cto_summary": cto,
        "security_summary": security,
        "operational_summary": operations,
        "assumptions": list(assumptions),
        "externally_deployed": False,
        "customer_contract_signed": False,
        "customer_revenue_verified": False,
        "economics_guaranteed": False,
    }
    return ProductionLaunchDossier(
        dossier_id="recoveryworks-launch-dossier:" + canonical_hash(identity),
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        production_admission_proof_hash=admission.proof_hash,
        security_evidence_proof_hash=security_evidence.proof_hash,
        dr_rehearsal_proof_hash=dr_rehearsal.proof_hash,
        observability_run_manifest_proof_hash=observability_run.proof_hash,
        rollback_manifest_proof_hash=rollback_manifest.proof_hash,
        commercial_pilot_package_proof_hash=commercial_pilot.proof_hash,
        reviewed_at=reviewed_at,
        cfo_summary=cfo,
        cto_summary=cto,
        security_summary=security,
        operational_summary=operations,
        assumptions=assumptions,
        externally_deployed=False,
        customer_contract_signed=False,
        customer_revenue_verified=False,
        economics_guaranteed=False,
    )


def write_production_launch_dossier(
    dossier: ProductionLaunchDossier,
    *,
    json_path: str | Path,
    markdown_path: str | Path,
) -> None:
    atomic_private_write(
        Path(json_path),
        (
            json.dumps(
                dossier.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8"),
    )
    atomic_private_write(
        Path(markdown_path),
        (dossier.to_markdown() + "\n").encode("utf-8"),
    )
