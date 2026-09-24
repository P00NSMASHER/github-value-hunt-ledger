"""Enterprise diligence control/evidence map.

Framework labels are reference mappings for questionnaires only. This module
does not assert or create SOC 2, ISO 27001, PCI DSS, HIPAA, FedRAMP, or other
third-party certifications/attestations.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Any

from recoveryworks.commercial_pilot import CloudCommercialPilotPackage
from recoveryworks.environment_activation import CredentialScopeAttestation
from recoveryworks.models import canonical_hash, normalize_sha256, normalize_utc_timestamp
from recoveryworks.private_io import atomic_private_write
from recoveryworks.production_admission import ProductionAdmissionGate
from recoveryworks.production_assurance_continuous import ContinuousProductionAssurance
from recoveryworks.production_launch_dossier import ProductionLaunchDossier
from recoveryworks.production_resilience import (
    DisasterRecoveryRehearsal,
    ProductionBackupManifest,
)
from recoveryworks.release_control import RecoveryWorksReleaseManifest
from recoveryworks.release_security_bridge import VerifiedReleaseSecurityEvidence


class EnterpriseControlStatus(str, Enum):
    INTERNAL_EVIDENCE = "INTERNAL_EVIDENCE"
    CONTROL_IMPLEMENTED_NO_EVENT = "CONTROL_IMPLEMENTED_NO_EVENT"
    EXTERNAL_VALIDATION_REQUIRED = "EXTERNAL_VALIDATION_REQUIRED"


@dataclass(frozen=True)
class ControlEvidenceReference:
    evidence_type: str
    proof_hash: str
    description: str
    limitation: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "proof_hash", normalize_sha256("proof_hash", self.proof_hash)
        )
        for name in ("evidence_type", "description", "limitation"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")

    @property
    def proof_hash_of_reference(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class EnterpriseControlEntry:
    control_id: str
    domain: str
    title: str
    status: EnterpriseControlStatus
    description: str
    evidence: tuple[ControlEvidenceReference, ...]
    framework_references: tuple[str, ...]
    questionnaire_topics: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("control_id", "domain", "title", "description"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        if not isinstance(self.status, EnterpriseControlStatus):
            raise ValueError("status must be EnterpriseControlStatus")
        evidence = tuple(self.evidence)
        if self.status is EnterpriseControlStatus.INTERNAL_EVIDENCE and not evidence:
            raise ValueError("internally evidenced controls require evidence")
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(
            self,
            "framework_references",
            tuple(sorted(set(self.framework_references))),
        )
        object.__setattr__(
            self,
            "questionnaire_topics",
            tuple(sorted(set(self.questionnaire_topics))),
        )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "control_id": self.control_id,
            "domain": self.domain,
            "title": self.title,
            "status": self.status.value,
            "description": self.description,
            "evidence_hashes": [
                item.proof_hash_of_reference for item in self.evidence
            ],
            "framework_references": list(self.framework_references),
            "questionnaire_topics": list(self.questionnaire_topics),
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            "control_id": self.control_id,
            "domain": self.domain,
            "title": self.title,
            "status": self.status.value,
            "description": self.description,
            "evidence": [
                {
                    **asdict(item),
                    "reference_proof_hash": item.proof_hash_of_reference,
                }
                for item in self.evidence
            ],
            "framework_references": list(self.framework_references),
            "questionnaire_topics": list(self.questionnaire_topics),
            "proof_hash": self.proof_hash,
        }


@dataclass(frozen=True)
class EnterpriseControlEvidenceMap:
    map_id: str
    release_id: str
    release_proof_hash: str
    generated_at: str
    controls: tuple[EnterpriseControlEntry, ...]
    certification_claims: tuple[str, ...]
    framework_mappings_are_reference_only: bool
    third_party_audit_completed: bool
    buyer_diligence_ready: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "release_proof_hash",
            normalize_sha256("release_proof_hash", self.release_proof_hash)
        )
        object.__setattr__(
            self, "generated_at",
            normalize_utc_timestamp("generated_at", self.generated_at)
        )
        controls = tuple(sorted(self.controls, key=lambda item: item.control_id))
        if len({item.control_id for item in controls}) != len(controls):
            raise ValueError("enterprise control ids must be unique")
        object.__setattr__(self, "controls", controls)
        if self.certification_claims:
            raise ValueError("enterprise control map cannot claim certifications")
        if self.framework_mappings_are_reference_only is not True:
            raise ValueError("framework mappings must be reference-only")
        if self.third_party_audit_completed:
            raise ValueError("third-party audit completion cannot be asserted")
        if self.buyer_diligence_ready is not True:
            raise ValueError("control map must be ready for diligence review")
        expected = "recoveryworks-enterprise-control-map:" + canonical_hash(
            self._identity()
        )
        if self.map_id != expected:
            raise ValueError("map_id does not bind control map")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "release_id": self.release_id,
            "release_proof_hash": self.release_proof_hash,
            "generated_at": self.generated_at,
            "control_hashes": [control.proof_hash for control in self.controls],
            "certification_claims": [],
            "framework_mappings_are_reference_only": True,
            "third_party_audit_completed": False,
            "buyer_diligence_ready": True,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "controls": [control.as_dict() for control in self.controls],
            "map_id": self.map_id,
            "proof_hash": self.proof_hash,
            "disclaimer": (
                "Framework references are questionnaire mappings only. "
                "No SOC 2, ISO 27001, PCI DSS, HIPAA, FedRAMP, or other "
                "third-party certification/attestation is claimed."
            ),
            "state": "BUYER_DILIGENCE_CONTROL_MAP_READY",
        }

    def to_markdown(self) -> str:
        lines = [
            "# Enterprise Control & Evidence Map",
            "",
            f"Release: {self.release_id}",
            f"Proof: {self.proof_hash}",
            "",
            "> Framework references are for questionnaire mapping only. "
            "No SOC 2, ISO 27001, PCI DSS, HIPAA, FedRAMP, or other "
            "third-party certification/attestation is claimed.",
            "",
        ]
        for control in self.controls:
            lines.extend([
                f"## {control.control_id} — {control.title}",
                "",
                f"- Domain: {control.domain}",
                f"- Status: {control.status.value}",
                f"- Description: {control.description}",
                "- Reference mappings: "
                + (", ".join(control.framework_references) or "none"),
                "- Evidence:",
            ])
            if not control.evidence:
                lines.append("  - No event-specific evidence yet.")
            for evidence in control.evidence:
                lines.extend([
                    f"  - {evidence.evidence_type}: {evidence.proof_hash}",
                    f"    - {evidence.description}",
                    f"    - Limitation: {evidence.limitation}",
                ])
            lines.append("")
        return "\n".join(lines)


def _evidence(
    evidence_type: str,
    proof_hash: str,
    description: str,
    limitation: str,
) -> ControlEvidenceReference:
    return ControlEvidenceReference(
        evidence_type=evidence_type,
        proof_hash=proof_hash,
        description=description,
        limitation=limitation,
    )


def build_enterprise_control_evidence_map(
    *,
    release: RecoveryWorksReleaseManifest,
    admission: ProductionAdmissionGate,
    security_evidence: VerifiedReleaseSecurityEvidence,
    dr_rehearsal: DisasterRecoveryRehearsal,
    backup: ProductionBackupManifest,
    continuous_assurance: ContinuousProductionAssurance,
    launch_dossier: ProductionLaunchDossier,
    credential_scope: CredentialScopeAttestation,
    commercial_pilot: CloudCommercialPilotPackage,
    incident_journal_head_hash: str | None,
    generated_at: str,
) -> EnterpriseControlEvidenceMap:
    if admission.release_id != release.release_id:
        raise ValueError("admission release mismatch")
    if admission.release_proof_hash != release.proof_hash:
        raise ValueError("admission release proof mismatch")
    if security_evidence.release_id != release.release_id:
        raise ValueError("security evidence release mismatch")
    if launch_dossier.release_id != release.release_id:
        raise ValueError("launch dossier release mismatch")
    if continuous_assurance.release_id != release.release_id:
        raise ValueError("continuous assurance release mismatch")
    if launch_dossier.commercial_pilot_package_proof_hash != commercial_pilot.proof_hash:
        raise ValueError("commercial pilot proof mismatch")
    if launch_dossier.production_admission_proof_hash != admission.proof_hash:
        raise ValueError("launch dossier admission proof mismatch")
    if launch_dossier.security_evidence_proof_hash != security_evidence.proof_hash:
        raise ValueError("launch dossier security proof mismatch")
    if launch_dossier.dr_rehearsal_proof_hash != dr_rehearsal.proof_hash:
        raise ValueError("launch dossier DR proof mismatch")

    incident_evidence: tuple[ControlEvidenceReference, ...]
    incident_status: EnterpriseControlStatus
    if incident_journal_head_hash is None:
        incident_evidence = (
            _evidence(
                "launch-dossier",
                launch_dossier.proof_hash,
                "Rollback readiness and incident-response boundaries are included in launch review.",
                "No incident-specific journal event is represented in this map.",
            ),
        )
        incident_status = EnterpriseControlStatus.CONTROL_IMPLEMENTED_NO_EVENT
    else:
        incident_evidence = (
            _evidence(
                "incident-journal-head",
                incident_journal_head_hash,
                "Tamper-evident incident lifecycle journal head.",
                "Evidence covers recorded internal lifecycle events only.",
            ),
        )
        incident_status = EnterpriseControlStatus.INTERNAL_EVIDENCE

    controls = (
        EnterpriseControlEntry(
            control_id="AC-01",
            domain="Access Control",
            title="Read-only cloud credential scope",
            status=EnterpriseControlStatus.INTERNAL_EVIDENCE,
            description=(
                "Provider access is modeled with verified principal/account scope, "
                "read/discovery permissions, no embedded credentials, and no write capability."
            ),
            evidence=(
                _evidence(
                    "credential-scope-attestation",
                    credential_scope.proof_hash,
                    "Verified provider/account/principal permission scope.",
                    "Does not prove identity-provider governance outside the supplied attestation.",
                ),
            ),
            framework_references=("SOC2 CC6 (reference)", "ISO27001 access control (reference)"),
            questionnaire_topics=("least privilege", "cloud access", "credential handling"),
        ),
        EnterpriseControlEntry(
            control_id="DP-01",
            domain="Data Protection",
            title="Private state and deterministic backup",
            status=EnterpriseControlStatus.INTERNAL_EVIDENCE,
            description=(
                "Sensitive ledgers, receipts, reports, history, and backup artifacts use "
                "private local storage controls and hash-bound backup manifests."
            ),
            evidence=(
                _evidence(
                    "production-backup",
                    backup.proof_hash,
                    "Private backup binds state artifacts, archive integrity, retention, and RPO.",
                    "Does not assert external storage encryption/KMS unless separately evidenced.",
                ),
                _evidence(
                    "dr-rehearsal",
                    dr_rehearsal.proof_hash,
                    "Semantic restore rehearsal verifies recoverability and RTO.",
                    "Represents the specific rehearsal artifact supplied to this map.",
                ),
            ),
            framework_references=("SOC2 CC6/CC7 (reference)", "ISO27001 backup/continuity (reference)"),
            questionnaire_topics=("data at rest", "backup", "retention", "recovery"),
        ),
        EnterpriseControlEntry(
            control_id="SDLC-01",
            domain="Secure SDLC",
            title="Immutable build/release admission",
            status=EnterpriseControlStatus.INTERNAL_EVIDENCE,
            description=(
                "Production admission binds release, source commit, image digest, build provenance, "
                "security evidence, promotion approval, and DR freshness."
            ),
            evidence=(
                _evidence(
                    "production-admission",
                    admission.proof_hash,
                    "Single production-admission choke point.",
                    "Does not itself prove that an external deployment occurred.",
                ),
                _evidence(
                    "release-security-evidence",
                    security_evidence.proof_hash,
                    "Verified scan/signature/provenance evidence for exact release.",
                    "Relies on externally supplied verification receipts.",
                ),
            ),
            framework_references=("SOC2 CC8 (reference)", "ISO27001 secure development/change (reference)"),
            questionnaire_topics=("change management", "code provenance", "release approval"),
        ),
        EnterpriseControlEntry(
            control_id="SC-01",
            domain="Supply Chain",
            title="SBOM, image provenance, vulnerability evidence",
            status=EnterpriseControlStatus.INTERNAL_EVIDENCE,
            description=(
                "Release security evidence binds component inventory, image digest, vulnerability "
                "scan, signature verification, and provenance verification."
            ),
            evidence=(
                _evidence(
                    "verified-security-evidence",
                    security_evidence.proof_hash,
                    "Exact release/image/source security evidence bundle.",
                    "No third-party certification is implied.",
                ),
            ),
            framework_references=("SOC2 CC7/CC8 (reference)", "ISO27001 supplier/secure development (reference)"),
            questionnaire_topics=("SBOM", "vulnerability management", "software supply chain"),
        ),
        EnterpriseControlEntry(
            control_id="BCP-01",
            domain="Business Continuity",
            title="Disaster recovery rehearsal",
            status=EnterpriseControlStatus.INTERNAL_EVIDENCE,
            description="Backup/restore controls are semantically rehearsed against RPO/RTO objectives.",
            evidence=(
                _evidence(
                    "dr-rehearsal",
                    dr_rehearsal.proof_hash,
                    "Passing DR rehearsal with semantic state verification.",
                    "Currentness is separately monitored by continuous assurance.",
                ),
            ),
            framework_references=("SOC2 A1 (reference)", "ISO27001 ICT continuity (reference)"),
            questionnaire_topics=("business continuity", "RPO", "RTO", "disaster recovery"),
        ),
        EnterpriseControlEntry(
            control_id="IR-01",
            domain="Incident Response",
            title="Tamper-evident incident/rollback lifecycle",
            status=incident_status,
            description=(
                "Incident detection, acknowledgement, escalation, rollback approvals/handoffs, "
                "closure, and review use proof-bound lifecycle controls."
            ),
            evidence=incident_evidence,
            framework_references=("SOC2 CC7 (reference)", "ISO27001 incident management (reference)"),
            questionnaire_topics=("incident response", "rollback", "post-incident review"),
        ),
        EnterpriseControlEntry(
            control_id="AU-01",
            domain="Auditability",
            title="Continuous assurance and tamper-evident history",
            status=EnterpriseControlStatus.INTERNAL_EVIDENCE,
            description=(
                "Continuous assurance checks drift/freshness/integrity while automatic remediation "
                "and external actions remain disabled."
            ),
            evidence=(
                _evidence(
                    "continuous-production-assurance",
                    continuous_assurance.proof_hash,
                    "Current release/security/DR/backup/history/cloud-evidence assurance snapshot.",
                    "Represents the point-in-time assurance check supplied to this map.",
                ),
            ),
            framework_references=("SOC2 CC4/CC7 (reference)", "ISO27001 logging/monitoring (reference)"),
            questionnaire_topics=("audit logs", "monitoring", "control evidence"),
        ),
        EnterpriseControlEntry(
            control_id="FIN-01",
            domain="Financial Integrity",
            title="Deterministic recovery proof boundary",
            status=EnterpriseControlStatus.INTERNAL_EVIDENCE,
            description=(
                "Recovery dollars require verified controlling authority and verified load-bearing "
                "evidence; prospective savings/anomalies remain separate."
            ),
            evidence=(
                _evidence(
                    "launch-readiness-dossier",
                    launch_dossier.proof_hash,
                    "CFO/CTO/security/operations readiness package preserves financial boundaries.",
                    "Does not prove customer revenue, traction, or guaranteed economics.",
                ),
                _evidence(
                    "commercial-pilot-package",
                    commercial_pilot.proof_hash,
                    "Pricing hypothesis and recovered-cash-only success-fee basis.",
                    "Not a contract, invoice, or customer acceptance.",
                ),
            ),
            framework_references=(),
            questionnaire_topics=("financial controls", "calculation integrity", "revenue recognition boundaries"),
        ),
        EnterpriseControlEntry(
            control_id="EXT-01",
            domain="External Actions",
            title="Separation of authorization from mutation",
            status=EnterpriseControlStatus.INTERNAL_EVIDENCE,
            description=(
                "RecoveryWorks prepares/validates handoffs and receipts; provider mutation and "
                "external recovery actions remain separate authorized actors."
            ),
            evidence=(
                _evidence(
                    "production-admission",
                    admission.proof_hash,
                    "Admission is proof-only and deployment execution remains disabled.",
                    "External deployer controls require separate operational evidence.",
                ),
                _evidence(
                    "credential-scope-attestation",
                    credential_scope.proof_hash,
                    "Activation credential scope contains no write capability.",
                    "Does not attest unrelated credentials outside this scope.",
                ),
            ),
            framework_references=("SOC2 CC6/CC8 (reference)", "ISO27001 segregation/change control (reference)"),
            questionnaire_topics=("separation of duties", "production access", "change authorization"),
        ),
    )

    generated_at = normalize_utc_timestamp("generated_at", generated_at)
    control_hashes = [control.proof_hash for control in sorted(controls, key=lambda x:x.control_id)]
    identity = {
        "schema": 1,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "generated_at": generated_at,
        "control_hashes": control_hashes,
        "certification_claims": [],
        "framework_mappings_are_reference_only": True,
        "third_party_audit_completed": False,
        "buyer_diligence_ready": True,
    }
    return EnterpriseControlEvidenceMap(
        map_id="recoveryworks-enterprise-control-map:" + canonical_hash(identity),
        release_id=release.release_id,
        release_proof_hash=release.proof_hash,
        generated_at=generated_at,
        controls=controls,
        certification_claims=(),
        framework_mappings_are_reference_only=True,
        third_party_audit_completed=False,
        buyer_diligence_ready=True,
    )


def write_enterprise_control_evidence_map(
    control_map: EnterpriseControlEvidenceMap,
    *,
    json_path: str | Path,
    markdown_path: str | Path,
) -> None:
    atomic_private_write(
        Path(json_path),
        (
            json.dumps(
                control_map.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8"),
    )
    atomic_private_write(
        Path(markdown_path),
        (control_map.to_markdown() + "\n").encode("utf-8"),
    )
