"""Enterprise diligence export package with redaction, gaps, and evidence-room index."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Any, Mapping

from recoveryworks.enterprise_controls import (
    EnterpriseControlEvidenceMap,
    EnterpriseControlStatus,
)
from recoveryworks.models import canonical_hash, freeze_json, normalize_sha256, normalize_utc_timestamp
from recoveryworks.private_io import atomic_private_write


class DiligenceGapSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class DiligenceRedactionPolicy:
    expose_internal_paths: bool = False
    expose_source_locators: bool = False
    expose_actor_identifiers: bool = False
    expose_raw_metadata: bool = False

    def __post_init__(self) -> None:
        if (
            self.expose_internal_paths
            or self.expose_source_locators
            or self.expose_actor_identifiers
            or self.expose_raw_metadata
        ):
            raise ValueError("customer-safe diligence export must keep sensitive fields redacted")


@dataclass(frozen=True)
class QuestionnaireAnswer:
    question_id: str
    topic: str
    answer: str
    control_ids: tuple[str, ...]
    evidence_proof_hashes: tuple[str, ...]
    qualification: str

    def __post_init__(self) -> None:
        for name in ("question_id", "topic", "answer", "qualification"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        object.__setattr__(self, "control_ids", tuple(sorted(set(self.control_ids))))
        object.__setattr__(
            self,
            "evidence_proof_hashes",
            tuple(sorted(normalize_sha256("evidence_proof_hash", h) for h in self.evidence_proof_hashes)),
        )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "question_id": self.question_id,
            "topic": self.topic,
            "answer": self.answer,
            "control_ids": list(self.control_ids),
            "evidence_proof_hashes": list(self.evidence_proof_hashes),
            "qualification": self.qualification,
        })


@dataclass(frozen=True)
class DiligenceGap:
    gap_id: str
    control_id: str
    severity: DiligenceGapSeverity
    description: str
    owner_id: str
    due_at: str
    remediation_plan: str
    externally_validated: bool = False

    def __post_init__(self) -> None:
        for name in ("gap_id", "control_id", "description", "owner_id", "remediation_plan"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        if not isinstance(self.severity, DiligenceGapSeverity):
            raise ValueError("severity must be DiligenceGapSeverity")
        object.__setattr__(self, "due_at", normalize_utc_timestamp("due_at", self.due_at))
        if self.externally_validated:
            raise ValueError("gap register cannot claim external validation")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "gap_id": self.gap_id,
            "control_id": self.control_id,
            "severity": self.severity.value,
            "description": self.description,
            "owner_id": self.owner_id,
            "due_at": self.due_at,
            "remediation_plan": self.remediation_plan,
            "externally_validated": False,
        })


@dataclass(frozen=True)
class EvidenceRoomItem:
    evidence_id: str
    control_id: str
    evidence_type: str
    proof_hash: str
    customer_safe_description: str
    limitation: str

    def __post_init__(self) -> None:
        for name in ("evidence_id", "control_id", "evidence_type", "customer_safe_description", "limitation"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        object.__setattr__(self, "proof_hash", normalize_sha256("proof_hash", self.proof_hash))

    @property
    def reference_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class EnterpriseDiligencePackage:
    package_id: str
    release_id: str
    control_map_proof_hash: str
    generated_at: str
    redaction_policy: DiligenceRedactionPolicy
    questionnaire_answers: tuple[QuestionnaireAnswer, ...]
    evidence_room_items: tuple[EvidenceRoomItem, ...]
    gaps: tuple[DiligenceGap, ...]
    certifications_claimed: tuple[str, ...] = ()
    externally_shared: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "control_map_proof_hash", normalize_sha256(
            "control_map_proof_hash", self.control_map_proof_hash
        ))
        object.__setattr__(self, "generated_at", normalize_utc_timestamp("generated_at", self.generated_at))
        answers = tuple(sorted(self.questionnaire_answers, key=lambda x: x.question_id))
        evidence = tuple(sorted(self.evidence_room_items, key=lambda x: x.evidence_id))
        gaps = tuple(sorted(self.gaps, key=lambda x: x.gap_id))
        if len({x.question_id for x in answers}) != len(answers):
            raise ValueError("questionnaire answer ids must be unique")
        if len({x.evidence_id for x in evidence}) != len(evidence):
            raise ValueError("evidence room item ids must be unique")
        if len({x.gap_id for x in gaps}) != len(gaps):
            raise ValueError("gap ids must be unique")
        object.__setattr__(self, "questionnaire_answers", answers)
        object.__setattr__(self, "evidence_room_items", evidence)
        object.__setattr__(self, "gaps", gaps)
        if self.certifications_claimed:
            raise ValueError("diligence package cannot claim certifications")
        if self.externally_shared:
            raise ValueError("package object cannot claim it was externally shared")
        expected = "recoveryworks-diligence-package:" + canonical_hash(self._identity())
        if self.package_id != expected:
            raise ValueError("package_id does not bind diligence package")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "release_id": self.release_id,
            "control_map_proof_hash": self.control_map_proof_hash,
            "generated_at": self.generated_at,
            "redaction_policy": asdict(self.redaction_policy),
            "answer_hashes": [x.proof_hash for x in self.questionnaire_answers],
            "evidence_hashes": [x.reference_hash for x in self.evidence_room_items],
            "gap_hashes": [x.proof_hash for x in self.gaps],
            "certifications_claimed": [],
            "externally_shared": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "package_id": self.package_id,
            "proof_hash": self.proof_hash,
            "questionnaire_answers": [
                {
                    "question_id": a.question_id,
                    "topic": a.topic,
                    "answer": a.answer,
                    "control_ids": list(a.control_ids),
                    "evidence_proof_hashes": list(a.evidence_proof_hashes),
                    "qualification": a.qualification,
                    "proof_hash": a.proof_hash,
                }
                for a in self.questionnaire_answers
            ],
            "evidence_room_items": [
                {**asdict(item), "reference_hash": item.reference_hash}
                for item in self.evidence_room_items
            ],
            "gaps": [
                {
                    "gap_id": gap.gap_id,
                    "control_id": gap.control_id,
                    "severity": gap.severity.value,
                    "description": gap.description,
                    "owner_id": "[REDACTED_OWNER]",
                    "due_at": gap.due_at,
                    "remediation_plan": gap.remediation_plan,
                    "externally_validated": False,
                    "proof_hash": gap.proof_hash,
                }
                for gap in self.gaps
            ],
            "certification_disclaimer": (
                "No SOC 2, ISO 27001, PCI DSS, HIPAA, FedRAMP, or other certification "
                "is claimed by this package."
            ),
            "state": "CUSTOMER_SAFE_DILIGENCE_PACKAGE_READY",
        }

    def to_markdown(self) -> str:
        lines = [
            "# Enterprise Diligence Package",
            "",
            f"Release: {self.release_id}",
            f"Package proof: {self.proof_hash}",
            "",
            "> Customer-safe export. Internal paths, raw source locators, actor identifiers, "
            "and raw metadata are not included.",
            "> No SOC 2, ISO 27001, PCI DSS, HIPAA, FedRAMP, or other certification is claimed.",
            "",
            "## Questionnaire responses",
            "",
        ]
        for answer in self.questionnaire_answers:
            lines.extend([
                f"### {answer.question_id} — {answer.topic}",
                "",
                answer.answer,
                "",
                f"Qualification: {answer.qualification}",
                f"Controls: {', '.join(answer.control_ids)}",
                "",
            ])
        lines.extend(["## Evidence-room index", ""])
        for item in self.evidence_room_items:
            lines.extend([
                f"- {item.evidence_id} / {item.control_id} / {item.evidence_type}",
                f"  - proof: {item.proof_hash}",
                f"  - {item.customer_safe_description}",
                f"  - limitation: {item.limitation}",
            ])
        lines.extend(["", "## Open gaps", ""])
        if not self.gaps:
            lines.append("- No internal gaps recorded in this package.")
        for gap in self.gaps:
            lines.extend([
                f"- {gap.gap_id} [{gap.severity.value}] {gap.control_id}: {gap.description}",
                f"  - due: {gap.due_at}",
                f"  - remediation: {gap.remediation_plan}",
                "  - owner: [REDACTED_OWNER]",
            ])
        lines.append("")
        return "\n".join(lines)


_DEFAULT_QUESTIONS = (
    ("Q-ACCESS", "Access control", "How do you restrict cloud and production access?"),
    ("Q-DATA", "Data protection", "How do you protect, retain, and recover customer data?"),
    ("Q-SDLC", "Secure SDLC", "How are changes built, approved, and admitted to production?"),
    ("Q-SUPPLY", "Software supply chain", "Do you maintain SBOM and provenance evidence?"),
    ("Q-DR", "Business continuity", "What DR/RPO/RTO evidence exists?"),
    ("Q-IR", "Incident response", "How are incidents and rollbacks governed?"),
    ("Q-AUDIT", "Auditability", "What monitoring and tamper-evident history exists?"),
    ("Q-FIN", "Financial integrity", "How are recovery amounts prevented from being model-invented?"),
    ("Q-CERT", "Certifications", "Which third-party certifications do you hold?"),
)


def build_enterprise_diligence_package(
    control_map: EnterpriseControlEvidenceMap,
    *,
    generated_at: str,
    gap_owners: Mapping[str, str] | None = None,
    gap_due_at: Mapping[str, str] | None = None,
) -> EnterpriseDiligencePackage:
    controls = {c.control_id: c for c in control_map.controls}
    by_topic: dict[str, list[str]] = {}
    for control in control_map.controls:
        for topic in control.questionnaire_topics:
            by_topic.setdefault(topic.lower(), []).append(control.control_id)

    evidence_items: list[EvidenceRoomItem] = []
    for control in control_map.controls:
        for index, evidence in enumerate(control.evidence, start=1):
            evidence_items.append(EvidenceRoomItem(
                evidence_id=f"{control.control_id}-E{index:02d}",
                control_id=control.control_id,
                evidence_type=evidence.evidence_type,
                proof_hash=evidence.proof_hash,
                customer_safe_description=evidence.description,
                limitation=evidence.limitation,
            ))

    topic_to_control = {
        "Access control": ("AC-01",),
        "Data protection": ("DP-01",),
        "Secure SDLC": ("SDLC-01",),
        "Software supply chain": ("SC-01",),
        "Business continuity": ("BCP-01",),
        "Incident response": ("IR-01",),
        "Auditability": ("AU-01",),
        "Financial integrity": ("FIN-01",),
    }
    answers: list[QuestionnaireAnswer] = []
    for qid, topic, _question in _DEFAULT_QUESTIONS:
        if topic == "Certifications":
            answers.append(QuestionnaireAnswer(
                question_id=qid,
                topic=topic,
                answer=(
                    "No SOC 2, ISO 27001, PCI DSS, HIPAA, FedRAMP, or other "
                    "third-party certification is claimed in the supplied evidence."
                ),
                control_ids=(),
                evidence_proof_hashes=(),
                qualification=(
                    "Internal control evidence and reference mappings are not a substitute "
                    "for an independent certification or audit report."
                ),
            ))
            continue
        control_ids = topic_to_control[topic]
        selected = [controls[cid] for cid in control_ids]
        proof_hashes = tuple(
            evidence.proof_hash
            for control in selected
            for evidence in control.evidence
        )
        answer = " ".join(control.description for control in selected)
        qualification = " ".join(
            evidence.limitation
            for control in selected
            for evidence in control.evidence
        ) or "No additional qualification recorded."
        answers.append(QuestionnaireAnswer(
            question_id=qid,
            topic=topic,
            answer=answer,
            control_ids=control_ids,
            evidence_proof_hashes=proof_hashes,
            qualification=qualification,
        ))

    owners = gap_owners or {}
    due = gap_due_at or {}
    gaps: list[DiligenceGap] = []
    for control in control_map.controls:
        if control.status is EnterpriseControlStatus.INTERNAL_EVIDENCE:
            continue
        owner = owners.get(control.control_id, "UNASSIGNED_INTERNAL_OWNER")
        deadline = due.get(control.control_id, "2026-12-31T23:59:59Z")
        severity = (
            DiligenceGapSeverity.MEDIUM
            if control.status is EnterpriseControlStatus.CONTROL_IMPLEMENTED_NO_EVENT
            else DiligenceGapSeverity.HIGH
        )
        gaps.append(DiligenceGap(
            gap_id=f"GAP-{control.control_id}",
            control_id=control.control_id,
            severity=severity,
            description=(
                "Control lacks event-specific or external validation evidence for this diligence package."
            ),
            owner_id=owner,
            due_at=deadline,
            remediation_plan=(
                "Collect the missing event-specific or third-party validation evidence and "
                "regenerate the diligence package."
            ),
            externally_validated=False,
        ))

    policy = DiligenceRedactionPolicy()
    generated = normalize_utc_timestamp("generated_at", generated_at)
    answers_sorted = tuple(sorted(answers, key=lambda x: x.question_id))
    evidence_sorted = tuple(sorted(evidence_items, key=lambda x: x.evidence_id))
    gaps_sorted = tuple(sorted(gaps, key=lambda x: x.gap_id))
    identity = {
        "schema": 1,
        "release_id": control_map.release_id,
        "control_map_proof_hash": control_map.proof_hash,
        "generated_at": generated,
        "redaction_policy": asdict(policy),
        "answer_hashes": [x.proof_hash for x in answers_sorted],
        "evidence_hashes": [x.reference_hash for x in evidence_sorted],
        "gap_hashes": [x.proof_hash for x in gaps_sorted],
        "certifications_claimed": [],
        "externally_shared": False,
    }
    return EnterpriseDiligencePackage(
        package_id="recoveryworks-diligence-package:" + canonical_hash(identity),
        release_id=control_map.release_id,
        control_map_proof_hash=control_map.proof_hash,
        generated_at=generated,
        redaction_policy=policy,
        questionnaire_answers=answers_sorted,
        evidence_room_items=evidence_sorted,
        gaps=gaps_sorted,
        certifications_claimed=(),
        externally_shared=False,
    )


def write_enterprise_diligence_package(
    package: EnterpriseDiligencePackage,
    *,
    json_path: str | Path,
    markdown_path: str | Path,
) -> None:
    atomic_private_write(
        Path(json_path),
        (
            json.dumps(
                package.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ) + "\n"
        ).encode("utf-8"),
    )
    atomic_private_write(
        Path(markdown_path),
        (package.to_markdown() + "\n").encode("utf-8"),
    )
