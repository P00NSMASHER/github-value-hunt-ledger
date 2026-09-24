"""Source-priority and contradiction-preservation policy.

Step 10.1 models conflicting historical public-source claims without overwriting
lower-priority evidence. A preferred value is advisory for later normalization,
not a deletion or mutation of contradictory claims.

Priority is factual-status aware:
- court-established / convicted / found-liable / admitted facts;
- official settlement-status facts when the field itself is legal status;
- primary allegations;
- primary records that expressly settle without admission;
- academic reconstructions;
- discovery-only secondary sources.

Discovery-only claims may be retained for audit/discovery context but can never
establish the preferred canonical value.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Iterable

from .case_model import CaseArtifactRole, CaseRegistry
from .raw_artifacts import (
    RawArtifactManifest,
    SourceArtifactRef,
    same_retained_artifact,
)
from .source_registry import (
    SourceAdmissibility,
    SourceRegistry,
    canonical_hash,
)
from .transaction_model import FactStatus


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")


class ClaimAuthority(str, Enum):
    ESTABLISHED_OR_ADMITTED = "ESTABLISHED_OR_ADMITTED"
    OFFICIAL_NON_ADMISSION_STATUS = "OFFICIAL_NON_ADMISSION_STATUS"
    PRIMARY_ALLEGATION = "PRIMARY_ALLEGATION"
    PRIMARY_NON_ADMISSION = "PRIMARY_NON_ADMISSION"
    ACADEMIC_RECONSTRUCTION = "ACADEMIC_RECONSTRUCTION"
    DISCOVERY_ONLY = "DISCOVERY_ONLY"


_AUTHORITY_RANK = {
    ClaimAuthority.ESTABLISHED_OR_ADMITTED: 500,
    ClaimAuthority.OFFICIAL_NON_ADMISSION_STATUS: 450,
    ClaimAuthority.PRIMARY_ALLEGATION: 300,
    ClaimAuthority.PRIMARY_NON_ADMISSION: 250,
    ClaimAuthority.ACADEMIC_RECONSTRUCTION: 200,
    ClaimAuthority.DISCOVERY_ONLY: 0,
}


class ConflictResolutionState(str, Enum):
    NO_CONFLICT = "NO_CONFLICT"
    PREFERRED_VALUE_WITH_CONTRADICTIONS = "PREFERRED_VALUE_WITH_CONTRADICTIONS"
    UNRESOLVED_TOP_TIER_CONFLICT = "UNRESOLVED_TOP_TIER_CONFLICT"
    NO_CANONICAL_SUPPORT = "NO_CANONICAL_SUPPORT"


@dataclass(frozen=True)
class SourceConflictClaim:
    claim_id: str
    case_id: str
    field_name: str
    value: str
    source_ref: SourceArtifactRef
    artifact_role: CaseArtifactRole | None
    fact_status: FactStatus | None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.claim_id):
            raise ValueError("invalid claim_id")
        if not _ID_RE.fullmatch(self.case_id):
            raise ValueError("invalid case_id")
        if not self.field_name.strip():
            raise ValueError("field_name is required")
        if not self.value.strip():
            raise ValueError("claim value cannot be blank")
        object.__setattr__(self, "field_name", self.field_name.strip())
        object.__setattr__(self, "value", self.value.strip())

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "claim_id": self.claim_id,
            "case_id": self.case_id,
            "field_name": self.field_name,
            "value": self.value,
            "source_ref_proof_hash": self.source_ref.proof_hash,
            "artifact_role": (
                self.artifact_role.value
                if self.artifact_role is not None
                else None
            ),
            "fact_status": (
                self.fact_status.value
                if self.fact_status is not None
                else None
            ),
            "notes": self.notes,
        })


@dataclass(frozen=True)
class AssessedClaim:
    claim: SourceConflictClaim
    authority: ClaimAuthority
    authority_rank: int
    canonical_eligible: bool

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "claim_hash": self.claim.proof_hash,
            "authority": self.authority.value,
            "authority_rank": self.authority_rank,
            "canonical_eligible": self.canonical_eligible,
        })


@dataclass(frozen=True)
class ConflictAssessment:
    case_id: str
    field_name: str
    state: ConflictResolutionState
    claims: tuple[AssessedClaim, ...]
    preferred_value: str | None
    preferred_claim_hashes: tuple[str, ...]
    contradictory_claim_hashes: tuple[str, ...]
    top_authority: ClaimAuthority | None

    def __post_init__(self) -> None:
        if not self.claims:
            raise ValueError("conflict assessment requires claims")
        if tuple(sorted(self.preferred_claim_hashes)) != self.preferred_claim_hashes:
            raise ValueError("preferred_claim_hashes must be sorted")
        if (
            tuple(sorted(self.contradictory_claim_hashes))
            != self.contradictory_claim_hashes
        ):
            raise ValueError("contradictory_claim_hashes must be sorted")
        all_hashes = {item.claim.proof_hash for item in self.claims}
        if not set(self.preferred_claim_hashes).issubset(all_hashes):
            raise ValueError("preferred claim hash is not in assessment")
        if not set(self.contradictory_claim_hashes).issubset(all_hashes):
            raise ValueError("contradictory claim hash is not in assessment")
        if self.state in {
            ConflictResolutionState.UNRESOLVED_TOP_TIER_CONFLICT,
            ConflictResolutionState.NO_CANONICAL_SUPPORT,
        } and self.preferred_value is not None:
            raise ValueError("unresolved assessment cannot have preferred value")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "case_id": self.case_id,
            "field_name": self.field_name,
            "state": self.state.value,
            "assessed_claim_hashes": sorted(
                item.proof_hash for item in self.claims
            ),
            "preferred_value": self.preferred_value,
            "preferred_claim_hashes": list(self.preferred_claim_hashes),
            "contradictory_claim_hashes": list(
                self.contradictory_claim_hashes
            ),
            "top_authority": (
                self.top_authority.value
                if self.top_authority is not None
                else None
            ),
        })


def claim_authority(
    claim: SourceConflictClaim,
    *,
    source_registry: SourceRegistry,
) -> ClaimAuthority:
    source = source_registry.get(claim.source_ref.source_id)

    if source.admissibility is SourceAdmissibility.DISCOVERY_ONLY:
        return ClaimAuthority.DISCOVERY_ONLY

    if (
        source.admissibility
        is SourceAdmissibility.PUBLISHED_RESEARCH_RECONSTRUCTION
        or claim.artifact_role is CaseArtifactRole.ACADEMIC_RECONSTRUCTION
        or claim.fact_status is FactStatus.ACADEMIC_RECONSTRUCTION
    ):
        return ClaimAuthority.ACADEMIC_RECONSTRUCTION

    if claim.fact_status in {
        FactStatus.ADMITTED,
        FactStatus.FOUND_LIABLE,
        FactStatus.CONVICTED,
        FactStatus.COURT_ESTABLISHED,
    }:
        return ClaimAuthority.ESTABLISHED_OR_ADMITTED

    if claim.fact_status is FactStatus.SETTLED_WITHOUT_ADMISSION:
        if claim.field_name in {"fact_status", "proceeding_status"}:
            return ClaimAuthority.OFFICIAL_NON_ADMISSION_STATUS
        return ClaimAuthority.PRIMARY_NON_ADMISSION

    if claim.fact_status is FactStatus.ALLEGED:
        return ClaimAuthority.PRIMARY_ALLEGATION

    # A primary record without a fact-status interpretation may be preserved, but
    # it does not outrank an explicitly alleged/admitted/adjudicated claim.
    return ClaimAuthority.PRIMARY_NON_ADMISSION


def verify_conflict_claim(
    claim: SourceConflictClaim,
    *,
    cases: CaseRegistry,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
) -> None:
    if artifact_manifest.source_registry_hash != source_registry.registry_hash:
        raise ValueError("artifact manifest does not match source registry")

    case = cases.get(claim.case_id)
    artifact_manifest.resolve_ref(claim.source_ref)
    source = source_registry.get(claim.source_ref.source_id)
    if source.proof_hash != claim.source_ref.source_proof_hash:
        raise ValueError("conflict claim source proof mismatch")
    if source.case_id not in {None, claim.case_id}:
        raise ValueError("conflict claim source belongs to different case")

    if source.admissibility is SourceAdmissibility.DISCOVERY_ONLY:
        if claim.artifact_role is not None:
            raise ValueError(
                "discovery-only conflict claim cannot assert canonical artifact role"
            )
        if claim.fact_status is not None:
            raise ValueError(
                "discovery-only conflict claim cannot assert canonical fact status"
            )
        return

    if claim.artifact_role is None:
        raise ValueError("canonical conflict claim requires artifact_role")

    link = next(
        (
            item for item in case.artifacts
            if item.artifact_role is claim.artifact_role
            and same_retained_artifact(item.ref, claim.source_ref)
        ),
        None,
    )
    if link is None:
        raise ValueError(
            "conflict claim artifact/role is not linked to canonical case"
        )

    if (
        source.admissibility
        is SourceAdmissibility.PUBLISHED_RESEARCH_RECONSTRUCTION
    ):
        if claim.artifact_role is not CaseArtifactRole.ACADEMIC_RECONSTRUCTION:
            raise ValueError(
                "academic conflict claim requires academic reconstruction role"
            )
        if claim.fact_status is not FactStatus.ACADEMIC_RECONSTRUCTION:
            raise ValueError(
                "academic conflict claim requires academic reconstruction status"
            )
        return

    if claim.artifact_role is CaseArtifactRole.ACADEMIC_RECONSTRUCTION:
        raise ValueError("primary source cannot use academic reconstruction role")

    established_roles = {
        FactStatus.ADMITTED: {
            CaseArtifactRole.PLEA_OR_STATEMENT,
            CaseArtifactRole.JUDGMENT,
            CaseArtifactRole.ADMIN_ORDER,
        },
        FactStatus.FOUND_LIABLE: {CaseArtifactRole.JUDGMENT},
        FactStatus.CONVICTED: {
            CaseArtifactRole.JUDGMENT,
            CaseArtifactRole.PLEA_OR_STATEMENT,
        },
        FactStatus.COURT_ESTABLISHED: {
            CaseArtifactRole.JUDGMENT,
            CaseArtifactRole.EXHIBIT,
        },
    }
    if claim.fact_status in established_roles:
        if claim.artifact_role not in established_roles[claim.fact_status]:
            raise ValueError(
                "established/admitted claim status is unsupported by artifact role"
            )

    if claim.fact_status is FactStatus.ALLEGED:
        if claim.artifact_role not in {
            CaseArtifactRole.COMPLAINT,
            CaseArtifactRole.INDICTMENT,
            CaseArtifactRole.LITIGATION_RELEASE,
            CaseArtifactRole.ADMIN_ORDER,
            CaseArtifactRole.EXHIBIT,
            CaseArtifactRole.OTHER,
        }:
            raise ValueError("alleged claim is unsupported by artifact role")


def assess_conflicting_claims(
    claims: Iterable[SourceConflictClaim],
    *,
    cases: CaseRegistry,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
) -> ConflictAssessment:
    claim_tuple = tuple(claims)
    if not claim_tuple:
        raise ValueError("conflict assessment requires at least one claim")

    case_ids = {item.case_id for item in claim_tuple}
    field_names = {item.field_name for item in claim_tuple}
    claim_ids = {item.claim_id for item in claim_tuple}
    if len(case_ids) != 1:
        raise ValueError("conflict claims must belong to one case")
    if len(field_names) != 1:
        raise ValueError("conflict claims must address one field")
    if len(claim_ids) != len(claim_tuple):
        raise ValueError("duplicate conflict claim_id")

    assessed = []
    for claim in claim_tuple:
        verify_conflict_claim(
            claim,
            cases=cases,
            source_registry=source_registry,
            artifact_manifest=artifact_manifest,
        )
        authority = claim_authority(
            claim,
            source_registry=source_registry,
        )
        assessed.append(AssessedClaim(
            claim=claim,
            authority=authority,
            authority_rank=_AUTHORITY_RANK[authority],
            canonical_eligible=(
                authority is not ClaimAuthority.DISCOVERY_ONLY
            ),
        ))

    assessed_tuple = tuple(sorted(
        assessed,
        key=lambda item: item.claim.proof_hash,
    ))
    eligible = tuple(
        item for item in assessed_tuple if item.canonical_eligible
    )
    case_id = next(iter(case_ids))
    field_name = next(iter(field_names))

    if not eligible:
        return ConflictAssessment(
            case_id=case_id,
            field_name=field_name,
            state=ConflictResolutionState.NO_CANONICAL_SUPPORT,
            claims=assessed_tuple,
            preferred_value=None,
            preferred_claim_hashes=(),
            contradictory_claim_hashes=(),
            top_authority=None,
        )

    top_rank = max(item.authority_rank for item in eligible)
    top_claims = tuple(
        item for item in eligible if item.authority_rank == top_rank
    )
    top_values = {item.claim.value for item in top_claims}
    top_authority = top_claims[0].authority

    if len(top_values) > 1:
        return ConflictAssessment(
            case_id=case_id,
            field_name=field_name,
            state=ConflictResolutionState.UNRESOLVED_TOP_TIER_CONFLICT,
            claims=assessed_tuple,
            preferred_value=None,
            preferred_claim_hashes=(),
            contradictory_claim_hashes=tuple(sorted(
                item.claim.proof_hash for item in assessed_tuple
            )),
            top_authority=top_authority,
        )

    preferred_value = next(iter(top_values))
    preferred_hashes = tuple(sorted(
        item.claim.proof_hash
        for item in top_claims
        if item.claim.value == preferred_value
    ))
    contradictory = tuple(sorted(
        item.claim.proof_hash
        for item in assessed_tuple
        if item.claim.value != preferred_value
    ))
    state = (
        ConflictResolutionState.NO_CONFLICT
        if not contradictory
        else ConflictResolutionState.PREFERRED_VALUE_WITH_CONTRADICTIONS
    )
    return ConflictAssessment(
        case_id=case_id,
        field_name=field_name,
        state=state,
        claims=assessed_tuple,
        preferred_value=preferred_value,
        preferred_claim_hashes=preferred_hashes,
        contradictory_claim_hashes=contradictory,
        top_authority=top_authority,
    )


__all__ = [
    "AssessedClaim",
    "ClaimAuthority",
    "ConflictAssessment",
    "ConflictResolutionState",
    "SourceConflictClaim",
    "assess_conflicting_claims",
    "claim_authority",
    "verify_conflict_claim",
]
