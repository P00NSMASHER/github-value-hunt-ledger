"""Final immutable RecoveryWorks production-hardening certification dossier."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from recoveryworks.container_build import ContainerBuildManifest
from recoveryworks.models import (
    canonical_hash,
    normalize_git_commit_sha,
    normalize_sha256,
    normalize_utc_timestamp,
)
from recoveryworks.private_io import atomic_private_write
from recoveryworks.production_admission import ProductionAdmissionGate
from recoveryworks.production_adversarial_certification import (
    AdversarialCertificationState,
    ProductionAdversarialCertification,
    current_repository_revision,
)
from recoveryworks.production_chain_certification import (
    ProductionChainAdversarialCertification,
    ProductionChainInvariantReport,
    ProductionChainState,
)
from recoveryworks.release_control import (
    EnvironmentPromotionGate,
    RecoveryWorksReleaseManifest,
    ReleaseEnvironment,
)
from recoveryworks.release_deployment_handoff import (
    ReleaseDeploymentHandoff,
    ValidatedDeploymentReceipt,
)
from recoveryworks.release_package_integrity import ReleasePackageIntegrityReceipt


@dataclass(frozen=True)
class FinalProductionCertificationDossier:
    dossier_id: str
    source_revision: str
    release_id: str
    release_proof_hash: str
    container_build_manifest_proof_hash: str
    container_image_digest: str
    commercial_adversarial_certification_proof_hash: str
    release_package_integrity_proof_hash: str
    promotion_gate_proof_hash: str
    production_admission_proof_hash: str
    deployment_handoff_proof_hash: str
    post_deployment_verification_proof_hash: str
    production_chain_invariant_report_proof_hash: str
    production_chain_adversarial_certification_proof_hash: str
    certified_at: str
    production_hardening_certified: bool = True
    deployment_performed_by_recoveryworks: bool = False
    external_actions_performed: bool = False
    automatic_repair_performed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_revision",
            normalize_git_commit_sha("source_revision", self.source_revision),
        )
        for name in (
            "release_proof_hash",
            "container_build_manifest_proof_hash",
            "container_image_digest",
            "commercial_adversarial_certification_proof_hash",
            "release_package_integrity_proof_hash",
            "promotion_gate_proof_hash",
            "production_admission_proof_hash",
            "deployment_handoff_proof_hash",
            "post_deployment_verification_proof_hash",
            "production_chain_invariant_report_proof_hash",
            "production_chain_adversarial_certification_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self,
            "certified_at",
            normalize_utc_timestamp("certified_at", self.certified_at),
        )
        if self.production_hardening_certified is not True:
            raise ValueError("final dossier must certify production hardening")
        if (
            self.deployment_performed_by_recoveryworks
            or self.external_actions_performed
            or self.automatic_repair_performed
        ):
            raise ValueError(
                "final dossier cannot claim RecoveryWorks deployment, external actions, or repair"
            )
        expected = "recoveryworks-final-production-certification:" + canonical_hash(
            self._identity()
        )
        if self.dossier_id != expected:
            raise ValueError("dossier_id does not bind final production certification")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "source_revision": self.source_revision,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "container_build_manifest_proof_hash":
                self.container_build_manifest_proof_hash,
            "container_image_digest": self.container_image_digest,
            "commercial_adversarial_certification_proof_hash":
                self.commercial_adversarial_certification_proof_hash,
            "release_package_integrity_proof_hash":
                self.release_package_integrity_proof_hash,
            "promotion_gate_proof_hash": self.promotion_gate_proof_hash,
            "production_admission_proof_hash":
                self.production_admission_proof_hash,
            "deployment_handoff_proof_hash":
                self.deployment_handoff_proof_hash,
            "post_deployment_verification_proof_hash":
                self.post_deployment_verification_proof_hash,
            "production_chain_invariant_report_proof_hash":
                self.production_chain_invariant_report_proof_hash,
            "production_chain_adversarial_certification_proof_hash":
                self.production_chain_adversarial_certification_proof_hash,
            "certified_at": self.certified_at,
            "production_hardening_certified": True,
            "deployment_performed_by_recoveryworks": False,
            "external_actions_performed": False,
            "automatic_repair_performed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "dossier_id": self.dossier_id,
            "proof_hash": self.proof_hash,
            "state": "PRODUCTION_HARDENING_CERTIFIED",
        }


def build_final_production_certification_dossier(
    *,
    build_manifest: ContainerBuildManifest,
    commercial_certification: ProductionAdversarialCertification,
    release: RecoveryWorksReleaseManifest,
    package_integrity: ReleasePackageIntegrityReceipt,
    promotion_gate: EnvironmentPromotionGate,
    admission: ProductionAdmissionGate,
    handoff: ReleaseDeploymentHandoff,
    post_deployment: ValidatedDeploymentReceipt,
    chain_report: ProductionChainInvariantReport,
    chain_adversarial_certification: ProductionChainAdversarialCertification,
    certified_at: str,
) -> FinalProductionCertificationDossier:
    source_revision = current_repository_revision()
    if build_manifest.source_commit != source_revision:
        raise ValueError("final dossier build manifest is not current repository revision")
    if build_manifest.proof_hash != release.container_build_manifest_proof_hash:
        raise ValueError("final dossier build manifest does not bind release")
    if release.source_commit != source_revision:
        raise ValueError("final dossier release is not current repository revision")
    if (
        commercial_certification.state is not AdversarialCertificationState.PASS
        or commercial_certification.false_negative_count != 0
    ):
        raise ValueError("commercial adversarial certification is not passing")
    if commercial_certification.source_revision != source_revision:
        raise ValueError("commercial certification source revision mismatch")
    if (
        commercial_certification.container_build_manifest_proof_hash
        != build_manifest.proof_hash
    ):
        raise ValueError("commercial certification build manifest mismatch")
    if (
        package_integrity.release_id != release.release_id
        or package_integrity.release_proof_hash != release.proof_hash
        or package_integrity.promotion_gate_proof_hash != promotion_gate.proof_hash
        or package_integrity.adversarial_certification_proof_hash
        != commercial_certification.proof_hash
    ):
        raise ValueError("release package integrity does not bind final release chain")
    if (
        promotion_gate.environment is not ReleaseEnvironment.PRODUCTION
        or not promotion_gate.promotion_ready
        or promotion_gate.promotion_execution_enabled
        or promotion_gate.deployment_performed
    ):
        raise ValueError("production promotion gate is not final-certification eligible")
    if (
        admission.release_id != release.release_id
        or admission.release_proof_hash != release.proof_hash
        or admission.promotion_gate_proof_hash != promotion_gate.proof_hash
        or admission.release_package_integrity_proof_hash
        != package_integrity.proof_hash
        or admission.container_image_digest != release.container_image_digest
        or admission.source_commit != source_revision
        or not admission.admitted
        or admission.deployment_execution_enabled
    ):
        raise ValueError("production admission does not bind final release chain")
    if (
        handoff.release_id != release.release_id
        or handoff.release_proof_hash != release.proof_hash
        or handoff.production_admission_id != admission.admission_id
        or handoff.production_admission_proof_hash != admission.proof_hash
        or handoff.promotion_gate_proof_hash != promotion_gate.proof_hash
        or handoff.container_image_digest != release.container_image_digest
        or handoff.source_commit != source_revision
        or handoff.credentials_embedded
        or handoff.deployment_performed_by_recoveryos
    ):
        raise ValueError("deployment handoff does not bind final release chain")
    if (
        not post_deployment.verified
        or post_deployment.external_actions_performed
        or post_deployment.handoff_id != handoff.handoff_id
        or post_deployment.handoff_proof_hash != handoff.proof_hash
        or post_deployment.production_admission_id != admission.admission_id
        or post_deployment.production_admission_proof_hash != admission.proof_hash
        or post_deployment.release_id != release.release_id
        or post_deployment.release_proof_hash != release.proof_hash
        or post_deployment.container_image_digest != release.container_image_digest
        or post_deployment.source_commit != source_revision
    ):
        raise ValueError("post-deployment verification does not bind final release chain")
    if (
        chain_report.state is not ProductionChainState.PASS
        or chain_report.failed_codes
        or chain_report.release_id != release.release_id
        or chain_report.release_proof_hash != release.proof_hash
        or chain_report.external_actions_performed
        or chain_report.automatic_repair_performed
    ):
        raise ValueError("production chain invariant report did not pass")
    if (
        chain_adversarial_certification.false_negative_count != 0
        or chain_adversarial_certification.source_revision != source_revision
        or chain_adversarial_certification.baseline_report_proof_hash
        != chain_report.proof_hash
        or chain_adversarial_certification.external_actions_performed
        or chain_adversarial_certification.automatic_repair_performed
    ):
        raise ValueError("production chain adversarial certification did not pass")

    identity = {
        "schema": 1,
        "source_revision": source_revision,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "container_build_manifest_proof_hash": build_manifest.proof_hash,
        "container_image_digest": release.container_image_digest,
        "commercial_adversarial_certification_proof_hash":
            commercial_certification.proof_hash,
        "release_package_integrity_proof_hash": package_integrity.proof_hash,
        "promotion_gate_proof_hash": promotion_gate.proof_hash,
        "production_admission_proof_hash": admission.proof_hash,
        "deployment_handoff_proof_hash": handoff.proof_hash,
        "post_deployment_verification_proof_hash": post_deployment.proof_hash,
        "production_chain_invariant_report_proof_hash": chain_report.proof_hash,
        "production_chain_adversarial_certification_proof_hash":
            chain_adversarial_certification.proof_hash,
        "certified_at": normalize_utc_timestamp("certified_at", certified_at),
        "production_hardening_certified": True,
        "deployment_performed_by_recoveryworks": False,
        "external_actions_performed": False,
        "automatic_repair_performed": False,
    }
    return FinalProductionCertificationDossier(
        dossier_id="recoveryworks-final-production-certification:"
        + canonical_hash(identity),
        source_revision=source_revision,
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        container_build_manifest_proof_hash=build_manifest.proof_hash,
        container_image_digest=release.container_image_digest,
        commercial_adversarial_certification_proof_hash=
            commercial_certification.proof_hash,
        release_package_integrity_proof_hash=package_integrity.proof_hash,
        promotion_gate_proof_hash=promotion_gate.proof_hash,
        production_admission_proof_hash=admission.proof_hash,
        deployment_handoff_proof_hash=handoff.proof_hash,
        post_deployment_verification_proof_hash=post_deployment.proof_hash,
        production_chain_invariant_report_proof_hash=chain_report.proof_hash,
        production_chain_adversarial_certification_proof_hash=
            chain_adversarial_certification.proof_hash,
        certified_at=certified_at,
        production_hardening_certified=True,
        deployment_performed_by_recoveryworks=False,
        external_actions_performed=False,
        automatic_repair_performed=False,
    )


def write_final_production_certification_dossier(
    dossier: FinalProductionCertificationDossier,
    path: str | Path,
) -> None:
    atomic_private_write(
        Path(path),
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
