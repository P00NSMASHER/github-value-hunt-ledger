"""Source-priority and contradiction policy for historical public-record research.

Step 10 resolves competing claims without deleting any claim. Priority is
fact-domain-aware: the strongest source depends on what is being established.
Equal-priority disagreement remains AMBIGUOUS.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re

from .case_model import CaseArtifactRole, CaseRegistry
from .raw_artifacts import RawArtifactManifest, SourceArtifactRef, same_retained_artifact
from .source_registry import SourceAdmissibility, SourceRegistry, canonical_hash


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")


class FactDomain(str, Enum):
    LEGAL_STATUS = "LEGAL_STATUS"
    TRANSACTION_DETAIL = "TRANSACTION_DETAIL"
    PUBLICATION_BOUNDARY = "PUBLICATION_BOUNDARY"
    IDENTITY = "IDENTITY"
    OTHER = "OTHER"


class ConflictDisposition(str, Enum):
    SELECTED = "SELECTED"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class FactClaim:
    claim_id: str
    case_id: str
    case_proof_hash: str
    fact_key: str
    fact_domain: FactDomain
    value: str
    source_ref: SourceArtifactRef
    notes: str | None = None

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.claim_id):
            raise ValueError("invalid claim_id")
        if not _ID_RE.fullmatch(self.case_id):
            raise ValueError("invalid case_id")
        if not re.fullmatch(r"^[0-9a-f]{64}$", self.case_proof_hash):
            raise ValueError("case_proof_hash must be SHA-256")
        if not self.fact_key.strip():
            raise ValueError("fact_key is required")
        if not self.value.strip():
            raise ValueError("claim value is required")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "claim_id": self.claim_id,
            "case_id": self.case_id,
            "case_proof_hash": self.case_proof_hash,
            "fact_key": self.fact_key,
            "fact_domain": self.fact_domain.value,
            "value": self.value,
            "source_ref_hash": self.source_ref.proof_hash,
            "notes": self.notes,
        })


@dataclass(frozen=True)
class ClaimAssessment:
    claim: FactClaim
    artifact_role: CaseArtifactRole
    priority: int

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "claim_hash": self.claim.proof_hash,
            "artifact_role": self.artifact_role.value,
            "priority": self.priority,
        })


@dataclass(frozen=True)
class ConflictResolution:
    fact_key: str
    fact_domain: FactDomain
    disposition: ConflictDisposition
    selected_value: str | None
    controlling_claim_ids: tuple[str, ...]
    conflicting_claim_ids: tuple[str, ...]
    assessments: tuple[ClaimAssessment, ...]
    policy_id: str
    policy_proof_hash: str
    resolution_hash: str

    def verify_integrity(self) -> None:
        if self.resolution_hash != canonical_hash(self.integrity_body()):
            raise ValueError("conflict resolution hash mismatch")

    def integrity_body(self) -> dict:
        return {
            "schema": 1,
            "fact_key": self.fact_key,
            "fact_domain": self.fact_domain.value,
            "disposition": self.disposition.value,
            "selected_value": self.selected_value,
            "controlling_claim_ids": list(self.controlling_claim_ids),
            "conflicting_claim_ids": list(self.conflicting_claim_ids),
            "assessment_hashes": sorted(x.proof_hash for x in self.assessments),
            "policy_id": self.policy_id,
            "policy_proof_hash": self.policy_proof_hash,
        }


class SourcePriorityPolicy:
    policy_id = "historical-public-record-source-priority-v2"

    _DEFAULT = {
        CaseArtifactRole.JUDGMENT: 700,
        CaseArtifactRole.PLEA_OR_STATEMENT: 650,
        CaseArtifactRole.ADMIN_ORDER: 625,
        CaseArtifactRole.EXHIBIT: 600,
        CaseArtifactRole.COMPLAINT: 500,
        CaseArtifactRole.INDICTMENT: 500,
        CaseArtifactRole.LITIGATION_RELEASE: 450,
        CaseArtifactRole.PUBLIC_RELEASE: 425,
        CaseArtifactRole.FOIA_RELEASE: 350,
        CaseArtifactRole.ACADEMIC_RECONSTRUCTION: 300,
        CaseArtifactRole.OTHER: 200,
    }

    _OVERRIDES = {
        FactDomain.PUBLICATION_BOUNDARY: {
            CaseArtifactRole.PUBLIC_RELEASE: 800,
            CaseArtifactRole.JUDGMENT: 700,
            CaseArtifactRole.EXHIBIT: 650,
            CaseArtifactRole.COMPLAINT: 550,
            CaseArtifactRole.INDICTMENT: 550,
            CaseArtifactRole.ACADEMIC_RECONSTRUCTION: 300,
        },
        FactDomain.LEGAL_STATUS: {
            CaseArtifactRole.JUDGMENT: 800,
            CaseArtifactRole.PLEA_OR_STATEMENT: 775,
            CaseArtifactRole.ADMIN_ORDER: 725,
            CaseArtifactRole.LITIGATION_RELEASE: 500,
            CaseArtifactRole.COMPLAINT: 400,
            CaseArtifactRole.INDICTMENT: 400,
            CaseArtifactRole.ACADEMIC_RECONSTRUCTION: 250,
        },
        FactDomain.IDENTITY: {
            CaseArtifactRole.PUBLIC_RELEASE: 650,
            CaseArtifactRole.JUDGMENT: 700,
            CaseArtifactRole.EXHIBIT: 675,
            CaseArtifactRole.COMPLAINT: 650,
            CaseArtifactRole.INDICTMENT: 650,
            CaseArtifactRole.ACADEMIC_RECONSTRUCTION: 300,
        },
    }

    def priority(self, domain: FactDomain, role: CaseArtifactRole) -> int:
        return self._OVERRIDES.get(domain, {}).get(
            role,
            self._DEFAULT.get(role, 0),
        )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 2,
            "policy_id": self.policy_id,
            "default": {
                role.value: value
                for role, value in sorted(
                    self._DEFAULT.items(), key=lambda item: item[0].value
                )
            },
            "overrides": {
                domain.value: {
                    role.value: value
                    for role, value in sorted(
                        mapping.items(), key=lambda item: item[0].value
                    )
                }
                for domain, mapping in sorted(
                    self._OVERRIDES.items(),
                    key=lambda item: item[0].value,
                )
            },
        })


def _role_for_claim(claim: FactClaim, case) -> CaseArtifactRole:
    matches = {
        link.artifact_role
        for link in case.artifacts
        if same_retained_artifact(link.ref, claim.source_ref)
    }
    if not matches:
        raise ValueError("claim source is not linked to canonical case")
    if len(matches) != 1:
        raise ValueError(
            "claim source has ambiguous case artifact roles"
        )
    return next(iter(matches))


def resolve_fact_conflict(
    claims: tuple[FactClaim, ...] | list[FactClaim],
    *,
    cases: CaseRegistry,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
    policy: SourcePriorityPolicy | None = None,
) -> ConflictResolution:
    claim_tuple = tuple(claims)
    if artifact_manifest.source_registry_hash != source_registry.registry_hash:
        raise ValueError("artifact manifest/source registry mismatch")
    if not claim_tuple:
        raise ValueError("at least one fact claim is required")
    first = claim_tuple[0]
    if any(x.case_id != first.case_id for x in claim_tuple):
        raise ValueError("all claims must belong to one case")
    if any(x.fact_key != first.fact_key for x in claim_tuple):
        raise ValueError("all claims must share fact_key")
    if any(x.fact_domain is not first.fact_domain for x in claim_tuple):
        raise ValueError("all claims must share fact_domain")
    if len({x.claim_id for x in claim_tuple}) != len(claim_tuple):
        raise ValueError("duplicate claim_id")

    case = cases.get(first.case_id)
    if case.proof_hash != first.case_proof_hash:
        raise ValueError("claim case proof mismatch")
    selected_policy = policy or SourcePriorityPolicy()

    assessments = []
    for claim in claim_tuple:
        if claim.case_proof_hash != case.proof_hash:
            raise ValueError("claim case proof mismatch")
        artifact_manifest.resolve_ref(claim.source_ref)
        source = source_registry.get(claim.source_ref.source_id)
        if source.proof_hash != claim.source_ref.source_proof_hash:
            raise ValueError("claim source proof mismatch")
        if source.admissibility is SourceAdmissibility.DISCOVERY_ONLY:
            raise ValueError("discovery-only source cannot establish a fact claim")
        role = _role_for_claim(claim, case)
        assessments.append(ClaimAssessment(
            claim=claim,
            artifact_role=role,
            priority=selected_policy.priority(claim.fact_domain, role),
        ))

    top = max(x.priority for x in assessments)
    controlling = tuple(
        sorted((x for x in assessments if x.priority == top), key=lambda x: x.claim.claim_id)
    )
    top_values = {x.claim.value for x in controlling}
    if len(top_values) == 1:
        disposition = ConflictDisposition.SELECTED
        selected_value = next(iter(top_values))
        controlling_ids = tuple(x.claim.claim_id for x in controlling)
        conflicting_ids = tuple(sorted(
            x.claim.claim_id
            for x in assessments
            if x.claim.value != selected_value
        ))
    else:
        disposition = ConflictDisposition.AMBIGUOUS
        selected_value = None
        controlling_ids = tuple(x.claim.claim_id for x in controlling)
        conflicting_ids = tuple(sorted(x.claim.claim_id for x in assessments))

    body = {
        "schema": 1,
        "fact_key": first.fact_key,
        "fact_domain": first.fact_domain.value,
        "disposition": disposition.value,
        "selected_value": selected_value,
        "controlling_claim_ids": list(controlling_ids),
        "conflicting_claim_ids": list(conflicting_ids),
        "assessment_hashes": sorted(x.proof_hash for x in assessments),
        "policy_id": selected_policy.policy_id,
        "policy_proof_hash": selected_policy.proof_hash,
    }
    return ConflictResolution(
        fact_key=first.fact_key,
        fact_domain=first.fact_domain,
        disposition=disposition,
        selected_value=selected_value,
        controlling_claim_ids=controlling_ids,
        conflicting_claim_ids=conflicting_ids,
        assessments=tuple(sorted(assessments, key=lambda x: x.claim.claim_id)),
        policy_id=selected_policy.policy_id,
        policy_proof_hash=selected_policy.proof_hash,
        resolution_hash=canonical_hash(body),
    )


__all__ = [
    "ClaimAssessment",
    "ConflictDisposition",
    "ConflictResolution",
    "FactClaim",
    "FactDomain",
    "SourcePriorityPolicy",
    "resolve_fact_conflict",
]
