"""Durable entity resolution for historical public-record MNPI research.

Step 9 separates case-local names/tickers from durable canonical identities.
Resolution is explicit: RESOLVED, AMBIGUOUS, or UNRESOLVED. The module never
merges entities merely because names or tickers match.

Ticker/identifier bindings are source-backed and historical where applicable.
Overlapping confirmed ticker bindings to different issuers fail closed rather
than silently choosing one.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
import re
from typing import Iterable

from .case_model import CaseRegistry
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


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")


class EntityKind(str, Enum):
    PERSON = "PERSON"
    ISSUER = "ISSUER"
    ORGANIZATION = "ORGANIZATION"


class ResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


class IdentifierScheme(str, Enum):
    CIK = "CIK"
    TICKER = "TICKER"
    GVKEY = "GVKEY"
    PERMNO = "PERMNO"
    LEI = "LEI"
    OTHER = "OTHER"


def _day(name: str, value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _norm_identifier(scheme: IdentifierScheme, value: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError("identifier value is required")
    if scheme is IdentifierScheme.CIK:
        if not re.fullmatch(r"^[0-9]{1,10}$", text):
            raise ValueError("CIK must contain 1-10 digits")
        return text.lstrip("0") or "0"
    if scheme is IdentifierScheme.TICKER:
        return text.upper()
    return text


@dataclass(frozen=True)
class CanonicalEntity:
    entity_id: str
    kind: EntityKind
    display_name: str
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.entity_id):
            raise ValueError("invalid entity_id")
        if not self.display_name.strip():
            raise ValueError("display_name is required")
        normalized_aliases = tuple(
            sorted({item.strip() for item in self.aliases if item.strip()})
        )
        object.__setattr__(self, "aliases", normalized_aliases)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "entity_id": self.entity_id,
            "kind": self.kind.value,
            "display_name": self.display_name,
            "aliases": list(self.aliases),
        })


@dataclass(frozen=True)
class IdentifierBinding:
    binding_id: str
    entity_id: str
    scheme: IdentifierScheme
    value: str
    source_ref: SourceArtifactRef
    valid_from: str | None = None
    valid_to: str | None = None
    exchange: str | None = None

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.binding_id):
            raise ValueError("invalid binding_id")
        if not _ID_RE.fullmatch(self.entity_id):
            raise ValueError("invalid entity_id")
        object.__setattr__(
            self,
            "value",
            _norm_identifier(self.scheme, self.value),
        )
        start = _day("valid_from", self.valid_from)
        end = _day("valid_to", self.valid_to)
        if start is not None and end is not None and end < start:
            raise ValueError("identifier valid_to cannot precede valid_from")
        if self.exchange is not None and not self.exchange.strip():
            raise ValueError("exchange cannot be blank")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "binding_id": self.binding_id,
            "entity_id": self.entity_id,
            "scheme": self.scheme.value,
            "value": self.value,
            "source_ref_hash": self.source_ref.proof_hash,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "exchange": self.exchange,
        })


@dataclass(frozen=True)
class CaseEntityResolution:
    resolution_id: str
    case_id: str
    case_proof_hash: str
    local_id: str
    entity_kind: EntityKind
    status: ResolutionStatus
    evidence_refs: tuple[SourceArtifactRef, ...]
    canonical_entity_id: str | None = None
    candidate_entity_ids: tuple[str, ...] = ()
    rationale: str | None = None

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.resolution_id):
            raise ValueError("invalid resolution_id")
        if not _ID_RE.fullmatch(self.case_id):
            raise ValueError("invalid case_id")
        if not _ID_RE.fullmatch(self.local_id):
            raise ValueError("invalid local_id")
        if not re.fullmatch(r"^[0-9a-f]{64}$", self.case_proof_hash):
            raise ValueError("case_proof_hash must be SHA-256")
        candidates = tuple(sorted(set(self.candidate_entity_ids)))
        object.__setattr__(self, "candidate_entity_ids", candidates)

        if self.status is ResolutionStatus.RESOLVED:
            if self.canonical_entity_id is None:
                raise ValueError("RESOLVED requires canonical_entity_id")
            if candidates and candidates != (self.canonical_entity_id,):
                raise ValueError("RESOLVED candidates must be empty or canonical entity")
            if not self.evidence_refs:
                raise ValueError("RESOLVED requires evidence")
        elif self.status is ResolutionStatus.AMBIGUOUS:
            if self.canonical_entity_id is not None:
                raise ValueError("AMBIGUOUS cannot select canonical entity")
            if len(candidates) < 2:
                raise ValueError("AMBIGUOUS requires at least two candidates")
            if not self.evidence_refs:
                raise ValueError("AMBIGUOUS requires evidence")
        else:
            if self.canonical_entity_id is not None or candidates:
                raise ValueError("UNRESOLVED cannot select or propose entities")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "resolution_id": self.resolution_id,
            "case_id": self.case_id,
            "case_proof_hash": self.case_proof_hash,
            "local_id": self.local_id,
            "entity_kind": self.entity_kind.value,
            "status": self.status.value,
            "evidence_ref_hashes": sorted(
                item.proof_hash for item in self.evidence_refs
            ),
            "canonical_entity_id": self.canonical_entity_id,
            "candidate_entity_ids": list(self.candidate_entity_ids),
            "rationale": self.rationale,
        })


def _ranges_overlap(
    left_start: str | None,
    left_end: str | None,
    right_start: str | None,
    right_end: str | None,
) -> bool:
    minimum = date.min
    maximum = date.max
    ls = _day("left_start", left_start) or minimum
    le = _day("left_end", left_end) or maximum
    rs = _day("right_start", right_start) or minimum
    re_ = _day("right_end", right_end) or maximum
    return ls <= re_ and rs <= le


class EntityRegistry:
    def __init__(self) -> None:
        self._entities: dict[str, CanonicalEntity] = {}
        self._bindings: dict[str, IdentifierBinding] = {}
        self._resolutions: dict[str, CaseEntityResolution] = {}

    def register_entity(self, entity: CanonicalEntity) -> CanonicalEntity:
        existing = self._entities.get(entity.entity_id)
        if existing is not None:
            if existing.proof_hash != entity.proof_hash:
                raise ValueError("entity_id already registered with different content")
            return existing
        self._entities[entity.entity_id] = entity
        return entity

    def register_binding(
        self,
        binding: IdentifierBinding,
        *,
        source_registry: SourceRegistry,
        artifact_manifest: RawArtifactManifest,
    ) -> IdentifierBinding:
        entity = self.get_entity(binding.entity_id)
        if binding.scheme in {IdentifierScheme.CIK, IdentifierScheme.TICKER}:
            if entity.kind is not EntityKind.ISSUER:
                raise ValueError("CIK/ticker binding requires issuer entity")

        artifact_manifest.resolve_ref(binding.source_ref)
        source = source_registry.get(binding.source_ref.source_id)
        if source.proof_hash != binding.source_ref.source_proof_hash:
            raise ValueError("identifier binding source proof mismatch")
        if source.admissibility is SourceAdmissibility.DISCOVERY_ONLY:
            raise ValueError("discovery-only source cannot establish identifier binding")

        for current in self._bindings.values():
            if (
                current.scheme is binding.scheme
                and current.value == binding.value
                and current.entity_id != binding.entity_id
            ):
                if binding.scheme is IdentifierScheme.TICKER:
                    if _ranges_overlap(
                        current.valid_from,
                        current.valid_to,
                        binding.valid_from,
                        binding.valid_to,
                    ):
                        raise ValueError(
                            "overlapping ticker binding is ambiguous; "
                            "record an explicit AMBIGUOUS resolution"
                        )
                else:
                    raise ValueError(
                        "identifier already bound to a different entity"
                    )

        existing = self._bindings.get(binding.binding_id)
        if existing is not None:
            if existing.proof_hash != binding.proof_hash:
                raise ValueError("binding_id already registered with different content")
            return existing
        self._bindings[binding.binding_id] = binding
        return binding

    def register_case_resolution(
        self,
        resolution: CaseEntityResolution,
        *,
        cases: CaseRegistry,
        source_registry: SourceRegistry,
        artifact_manifest: RawArtifactManifest,
    ) -> CaseEntityResolution:
        case = cases.get(resolution.case_id)
        if case.proof_hash != resolution.case_proof_hash:
            raise ValueError("entity resolution case proof mismatch")

        party_ids = {item.party_id for item in case.parties}
        issuer_ids = {item.issuer_id for item in case.issuers}
        if resolution.entity_kind in {
            EntityKind.PERSON,
            EntityKind.ORGANIZATION,
        }:
            if resolution.local_id not in party_ids:
                raise ValueError(
                    "person/organization resolution local_id is not a case party"
                )
        elif resolution.entity_kind is EntityKind.ISSUER:
            if resolution.local_id not in issuer_ids:
                raise ValueError("issuer resolution local_id is not a case issuer")

        referenced_ids = set(resolution.candidate_entity_ids)
        if resolution.canonical_entity_id is not None:
            referenced_ids.add(resolution.canonical_entity_id)
        for entity_id in referenced_ids:
            entity = self.get_entity(entity_id)
            if entity.kind is not resolution.entity_kind:
                raise ValueError("resolution entity kind mismatch")

        for ref in resolution.evidence_refs:
            artifact_manifest.resolve_ref(ref)
            source = source_registry.get(ref.source_id)
            if source.proof_hash != ref.source_proof_hash:
                raise ValueError("entity resolution source proof mismatch")
            if source.admissibility is SourceAdmissibility.DISCOVERY_ONLY:
                raise ValueError(
                    "discovery-only source cannot establish entity resolution"
                )
            if not any(
                same_retained_artifact(ref, link.ref)
                for link in case.artifacts
            ):
                raise ValueError(
                    "entity resolution evidence is not linked to canonical case"
                )

        existing = self._resolutions.get(resolution.resolution_id)
        if existing is not None:
            if existing.proof_hash != resolution.proof_hash:
                raise ValueError(
                    "resolution_id already registered with different content"
                )
            return existing
        self._resolutions[resolution.resolution_id] = resolution
        return resolution

    def get_entity(self, entity_id: str) -> CanonicalEntity:
        try:
            return self._entities[entity_id]
        except KeyError as exc:
            raise KeyError("unknown entity_id: " + entity_id) from exc

    def get_resolution(self, resolution_id: str) -> CaseEntityResolution:
        try:
            return self._resolutions[resolution_id]
        except KeyError as exc:
            raise KeyError("unknown resolution_id: " + resolution_id) from exc

    def resolutions_for_local(
        self,
        case_id: str,
        local_id: str,
        entity_kind: EntityKind,
    ) -> tuple[CaseEntityResolution, ...]:
        return tuple(sorted(
            (
                item for item in self._resolutions.values()
                if item.case_id == case_id
                and item.local_id == local_id
                and item.entity_kind is entity_kind
            ),
            key=lambda item: item.resolution_id,
        ))

    def resolved_entity_for(
        self,
        case_id: str,
        local_id: str,
        entity_kind: EntityKind,
    ) -> CanonicalEntity:
        matches = self.resolutions_for_local(case_id, local_id, entity_kind)
        if not matches:
            raise ValueError("local identity has no resolution record")
        if any(item.status is not ResolutionStatus.RESOLVED for item in matches):
            raise ValueError(
                "local identity has unresolved or ambiguous resolution evidence"
            )
        entity_ids = {
            item.canonical_entity_id
            for item in matches
            if item.canonical_entity_id is not None
        }
        if len(entity_ids) != 1:
            raise ValueError(
                "local identity does not resolve to exactly one canonical entity"
            )
        return self.get_entity(next(iter(entity_ids)))

    def bindings_for(self, entity_id: str) -> tuple[IdentifierBinding, ...]:
        self.get_entity(entity_id)
        return tuple(sorted(
            (
                item for item in self._bindings.values()
                if item.entity_id == entity_id
            ),
            key=lambda item: item.binding_id,
        ))

    def resolve_identifier(
        self,
        scheme: IdentifierScheme,
        value: str,
        *,
        as_of_date: str | None = None,
    ) -> tuple[ResolutionStatus, tuple[str, ...]]:
        normalized = _norm_identifier(scheme, value)
        as_of = _day("as_of_date", as_of_date)
        matches = []
        for binding in self._bindings.values():
            if binding.scheme is not scheme or binding.value != normalized:
                continue
            if as_of is not None:
                start = _day("valid_from", binding.valid_from)
                end = _day("valid_to", binding.valid_to)
                if start is not None and as_of < start:
                    continue
                if end is not None and as_of > end:
                    continue
            matches.append(binding.entity_id)
        unique = tuple(sorted(set(matches)))
        if len(unique) == 1:
            return ResolutionStatus.RESOLVED, unique
        if len(unique) > 1:
            return ResolutionStatus.AMBIGUOUS, unique
        return ResolutionStatus.UNRESOLVED, ()

    @property
    def registry_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "entities": sorted(
                item.proof_hash for item in self._entities.values()
            ),
            "bindings": sorted(
                item.proof_hash for item in self._bindings.values()
            ),
            "resolutions": sorted(
                item.proof_hash for item in self._resolutions.values()
            ),
        })


__all__ = [
    "CanonicalEntity",
    "CaseEntityResolution",
    "EntityKind",
    "EntityRegistry",
    "IdentifierBinding",
    "IdentifierScheme",
    "ResolutionStatus",
]
