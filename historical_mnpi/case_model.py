"""Canonical case layer for historical public-record MNPI research.

Step 3 unifies SEC/DOJ/court materials into a single case identity while keeping
all source provenance anchored to retained raw artifacts.

This layer contains no transaction economics and does not infer facts from case
outcomes. It is an identity/provenance structure for already-public historical
records.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Iterable

from .raw_artifacts import RawArtifactManifest, SourceArtifactRef
from .source_registry import (
    SourceAdmissibility,
    SourceRegistry,
    SourceType,
    canonical_hash,
)


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
_CIK_RE = re.compile(r"^[0-9]{1,10}$")


class CaseProceedingStatus(str, Enum):
    OPEN_OR_PENDING = "OPEN_OR_PENDING"
    SETTLED = "SETTLED"
    FINAL_CIVIL_JUDGMENT = "FINAL_CIVIL_JUDGMENT"
    CRIMINAL_CONVICTION = "CRIMINAL_CONVICTION"
    DISMISSED_OR_ACQUITTED = "DISMISSED_OR_ACQUITTED"
    MIXED_OR_PARTIAL = "MIXED_OR_PARTIAL"
    UNKNOWN = "UNKNOWN"


class CaseEventType(str, Enum):
    EARNINGS = "EARNINGS"
    MERGER_ACQUISITION = "MERGER_ACQUISITION"
    REGULATORY_OR_CLINICAL = "REGULATORY_OR_CLINICAL"
    CUSTOMER_CONTRACT = "CUSTOMER_CONTRACT"
    FINANCING_OR_CAPITAL_MARKETS = "FINANCING_OR_CAPITAL_MARKETS"
    OPERATING_EVENT = "OPERATING_EVENT"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class CasePartyRole(str, Enum):
    DEFENDANT = "DEFENDANT"
    TRADER = "TRADER"
    TIPPER = "TIPPER"
    TIPPEE = "TIPPEE"
    INFORMATION_SOURCE = "INFORMATION_SOURCE"
    INTERMEDIARY = "INTERMEDIARY"
    OTHER = "OTHER"


class CaseArtifactRole(str, Enum):
    COMPLAINT = "COMPLAINT"
    INDICTMENT = "INDICTMENT"
    PLEA_OR_STATEMENT = "PLEA_OR_STATEMENT"
    JUDGMENT = "JUDGMENT"
    EXHIBIT = "EXHIBIT"
    LITIGATION_RELEASE = "LITIGATION_RELEASE"
    ADMIN_ORDER = "ADMIN_ORDER"
    FOIA_RELEASE = "FOIA_RELEASE"
    ACADEMIC_RECONSTRUCTION = "ACADEMIC_RECONSTRUCTION"
    PUBLIC_RELEASE = "PUBLIC_RELEASE"
    OTHER = "OTHER"


_ROLE_SOURCE_TYPES = {
    CaseArtifactRole.COMPLAINT: frozenset({SourceType.SEC_COMPLAINT}),
    CaseArtifactRole.INDICTMENT: frozenset({SourceType.DOJ_INDICTMENT}),
    CaseArtifactRole.PLEA_OR_STATEMENT: frozenset({
        SourceType.DOJ_PLEA_OR_STATEMENT,
    }),
    CaseArtifactRole.JUDGMENT: frozenset({SourceType.COURT_JUDGMENT}),
    CaseArtifactRole.EXHIBIT: frozenset({SourceType.COURT_EXHIBIT}),
    CaseArtifactRole.LITIGATION_RELEASE: frozenset({
        SourceType.SEC_LITIGATION_RELEASE,
    }),
    CaseArtifactRole.ADMIN_ORDER: frozenset({SourceType.SEC_ADMIN_ORDER}),
    CaseArtifactRole.FOIA_RELEASE: frozenset({SourceType.FOIA_PUBLIC_RELEASE}),
    CaseArtifactRole.ACADEMIC_RECONSTRUCTION: frozenset({
        SourceType.ACADEMIC_REPLICATION,
    }),
    CaseArtifactRole.PUBLIC_RELEASE: frozenset({
        SourceType.PUBLIC_FILING,
        SourceType.PUBLIC_PRESS_RELEASE,
        SourceType.PUBLIC_REGULATORY_RELEASE,
    }),
    CaseArtifactRole.OTHER: frozenset({
        SourceType.SEC_COMPLAINT,
        SourceType.SEC_LITIGATION_RELEASE,
        SourceType.SEC_ADMIN_ORDER,
        SourceType.DOJ_INDICTMENT,
        SourceType.DOJ_PLEA_OR_STATEMENT,
        SourceType.COURT_JUDGMENT,
        SourceType.COURT_EXHIBIT,
        SourceType.FOIA_PUBLIC_RELEASE,
        SourceType.PUBLIC_FILING,
        SourceType.PUBLIC_PRESS_RELEASE,
        SourceType.PUBLIC_REGULATORY_RELEASE,
    }),
}


@dataclass(frozen=True)
class CaseParty:
    party_id: str
    display_name: str
    roles: tuple[CasePartyRole, ...]

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.party_id):
            raise ValueError("invalid party_id")
        if not self.display_name.strip():
            raise ValueError("display_name is required")
        if not self.roles:
            raise ValueError("case party requires at least one role")
        if len(set(self.roles)) != len(self.roles):
            raise ValueError("duplicate case party role")


@dataclass(frozen=True)
class CaseIssuer:
    issuer_id: str
    legal_name: str
    cik: str | None = None
    ticker_at_case: str | None = None

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.issuer_id):
            raise ValueError("invalid issuer_id")
        if not self.legal_name.strip():
            raise ValueError("legal_name is required")
        if self.cik is not None and not _CIK_RE.fullmatch(self.cik):
            raise ValueError("cik must contain 1-10 digits")
        if self.ticker_at_case is not None and not self.ticker_at_case.strip():
            raise ValueError("ticker_at_case cannot be blank")


@dataclass(frozen=True)
class CaseArtifactLink:
    artifact_role: CaseArtifactRole
    ref: SourceArtifactRef

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "artifact_role": self.artifact_role.value,
            "ref_proof_hash": self.ref.proof_hash,
        })


@dataclass(frozen=True)
class HistoricalCase:
    case_id: str
    title: str
    event_type: CaseEventType
    information_origin: str
    proceeding_status: CaseProceedingStatus
    parties: tuple[CaseParty, ...]
    issuers: tuple[CaseIssuer, ...]
    artifacts: tuple[CaseArtifactLink, ...]
    complaint_or_opened_date: str | None = None
    judgment_or_resolution_date: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.case_id):
            raise ValueError("invalid case_id")
        if not self.title.strip():
            raise ValueError("title is required")
        if not self.information_origin.strip():
            raise ValueError("information_origin is required")
        if not self.parties:
            raise ValueError("historical case requires at least one party")
        if not self.issuers:
            raise ValueError("historical case requires at least one issuer")
        if not self.artifacts:
            raise ValueError("historical case requires at least one artifact")
        if len({item.party_id for item in self.parties}) != len(self.parties):
            raise ValueError("duplicate party_id in case")
        if len({item.issuer_id for item in self.issuers}) != len(self.issuers):
            raise ValueError("duplicate issuer_id in case")
        artifact_keys = {
            (item.ref.source_id, item.ref.artifact_id, item.artifact_role.value)
            for item in self.artifacts
        }
        if len(artifact_keys) != len(self.artifacts):
            raise ValueError("duplicate case artifact link")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "case_id": self.case_id,
            "title": self.title,
            "event_type": self.event_type.value,
            "information_origin": self.information_origin,
            "proceeding_status": self.proceeding_status.value,
            "parties": [
                {
                    "party_id": item.party_id,
                    "display_name": item.display_name,
                    "roles": sorted(role.value for role in item.roles),
                }
                for item in sorted(self.parties, key=lambda item: item.party_id)
            ],
            "issuers": [
                {
                    "issuer_id": item.issuer_id,
                    "legal_name": item.legal_name,
                    "cik": item.cik,
                    "ticker_at_case": item.ticker_at_case,
                }
                for item in sorted(self.issuers, key=lambda item: item.issuer_id)
            ],
            "artifacts": [
                {
                    "artifact_role": item.artifact_role.value,
                    "ref_proof_hash": item.ref.proof_hash,
                }
                for item in sorted(
                    self.artifacts,
                    key=lambda item: (
                        item.ref.source_id,
                        item.ref.artifact_id,
                        item.artifact_role.value,
                    ),
                )
            ],
            "complaint_or_opened_date": self.complaint_or_opened_date,
            "judgment_or_resolution_date": self.judgment_or_resolution_date,
            "notes": self.notes,
        })


class CaseRegistry:
    def __init__(self) -> None:
        self._cases: dict[str, HistoricalCase] = {}

    def register(
        self,
        case: HistoricalCase,
        *,
        source_registry: SourceRegistry,
        artifact_manifest: RawArtifactManifest,
    ) -> HistoricalCase:
        verify_case_provenance(
            case,
            source_registry=source_registry,
            artifact_manifest=artifact_manifest,
        )
        existing = self._cases.get(case.case_id)
        if existing is not None:
            if existing.proof_hash != case.proof_hash:
                raise ValueError("case_id already registered with different content")
            return existing
        self._cases[case.case_id] = case
        return case

    def get(self, case_id: str) -> HistoricalCase:
        try:
            return self._cases[case_id]
        except KeyError as exc:
            raise KeyError("unknown case_id: " + case_id) from exc

    def all(self) -> tuple[HistoricalCase, ...]:
        return tuple(self._cases[key] for key in sorted(self._cases))

    @property
    def registry_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "case_proof_hashes": [item.proof_hash for item in self.all()],
        })


def verify_case_provenance(
    case: HistoricalCase,
    *,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
) -> None:
    if artifact_manifest.source_registry_hash != source_registry.registry_hash:
        raise ValueError("artifact manifest does not match source registry")

    primary_or_academic = 0
    for link in case.artifacts:
        artifact_manifest.resolve_ref(link.ref)
        source = source_registry.get(link.ref.source_id)

        if source.proof_hash != link.ref.source_proof_hash:
            raise ValueError("case artifact source proof mismatch")

        if source.admissibility is SourceAdmissibility.DISCOVERY_ONLY:
            raise ValueError(
                "discovery-only source cannot establish canonical case content"
            )

        allowed_source_types = _ROLE_SOURCE_TYPES[link.artifact_role]
        if source.source_type not in allowed_source_types:
            raise ValueError(
                f"case artifact role {link.artifact_role.value} is incompatible "
                f"with source type {source.source_type.value}"
            )

        primary_or_academic += 1

        if (
            link.artifact_role is CaseArtifactRole.ACADEMIC_RECONSTRUCTION
            and source.admissibility
            is not SourceAdmissibility.PUBLISHED_RESEARCH_RECONSTRUCTION
        ):
            raise ValueError(
                "academic reconstruction role requires academic source"
            )
        if (
            link.artifact_role is not CaseArtifactRole.ACADEMIC_RECONSTRUCTION
            and source.admissibility
            is SourceAdmissibility.PUBLISHED_RESEARCH_RECONSTRUCTION
        ):
            raise ValueError(
                "academic source cannot masquerade as primary case artifact"
            )

    if primary_or_academic == 0:
        raise ValueError("case has no admissible artifacts")


__all__ = [
    "CaseArtifactLink",
    "CaseArtifactRole",
    "CaseEventType",
    "CaseIssuer",
    "CaseParty",
    "CasePartyRole",
    "CaseProceedingStatus",
    "CaseRegistry",
    "HistoricalCase",
    "verify_case_provenance",
]
