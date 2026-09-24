"""Durable entity-resolution primitives for historical public-record MNPI research.

Step 9.1 introduces cross-case issuer/trader identities without silently resolving
ambiguity. Identity evidence remains provenance-bound to retained, already-public
artifacts. Case-local identity linkage is intentionally deferred to the next
increment so this module can be tested in isolation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
import re

from .case_model import CasePartyRole, CaseRegistry
from .raw_artifacts import RawArtifactManifest, SourceArtifactRef
from .source_registry import (
    SourceAdmissibility,
    SourceRegistry,
    canonical_hash,
)


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
_TICKER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\\-]{0,15}$")


class EntityKind(str, Enum):
    ISSUER = "ISSUER"
    TRADER = "TRADER"


class HistoricalIdentifierType(str, Enum):
    CIK = "CIK"
    TICKER = "TICKER"


class ResolutionState(str, Enum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


def _normalized_name(value: str) -> str:
    text = " ".join(value.split())
    if not text:
        raise ValueError("identity name/alias cannot be blank")
    return text.casefold()


def _date_or_none(name: str, value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _normalize_identifier(
    identifier_type: HistoricalIdentifierType,
    value: str,
) -> str:
    text = value.strip()
    if identifier_type is HistoricalIdentifierType.CIK:
        if not re.fullmatch(r"^[0-9]{1,10}$", text):
            raise ValueError("CIK must contain 1-10 digits")
        number = int(text)
        if number <= 0:
            raise ValueError("CIK must be greater than zero")
        return str(number)
    if identifier_type is HistoricalIdentifierType.TICKER:
        if not _TICKER_RE.fullmatch(text):
            raise ValueError("invalid ticker")
        return text.upper()
    raise ValueError("unsupported historical identifier type")


@dataclass(frozen=True)
class IdentityAlias:
    value: str
    ref: SourceArtifactRef

    def __post_init__(self) -> None:
        cleaned = " ".join(self.value.split())
        if not cleaned:
            raise ValueError("alias cannot be blank")
        object.__setattr__(self, "value", cleaned)

    @property
    def normalized_value(self) -> str:
        return _normalized_name(self.value)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "value": self.value,
            "normalized_value": self.normalized_value,
            "ref_proof_hash": self.ref.proof_hash,
        })


@dataclass(frozen=True)
class HistoricalIdentifier:
    identifier_type: HistoricalIdentifierType
    value: str
    ref: SourceArtifactRef
    valid_from: str | None = None
    valid_to: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _normalize_identifier(self.identifier_type, self.value),
        )
        start = _date_or_none("valid_from", self.valid_from)
        end = _date_or_none("valid_to", self.valid_to)
        if start is not None and end is not None and end < start:
            raise ValueError("identifier valid_to cannot precede valid_from")

    def active_on(self, as_of: str | None) -> bool:
        if as_of is None:
            return True
        day = _date_or_none("as_of", as_of)
        assert day is not None
        start = _date_or_none("valid_from", self.valid_from)
        end = _date_or_none("valid_to", self.valid_to)
        if start is not None and day < start:
            return False
        if end is not None and day > end:
            return False
        return True

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "identifier_type": self.identifier_type.value,
            "value": self.value,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "ref_proof_hash": self.ref.proof_hash,
        })


@dataclass(frozen=True)
class IssuerIdentity:
    entity_id: str
    canonical_name: str
    canonical_name_ref: SourceArtifactRef
    aliases: tuple[IdentityAlias, ...] = ()
    identifiers: tuple[HistoricalIdentifier, ...] = ()

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.entity_id):
            raise ValueError("invalid issuer entity_id")
        cleaned = " ".join(self.canonical_name.split())
        if not cleaned:
            raise ValueError("canonical_name is required")
        object.__setattr__(self, "canonical_name", cleaned)
        if len({item.proof_hash for item in self.aliases}) != len(self.aliases):
            raise ValueError("duplicate issuer alias evidence")
        if len({item.proof_hash for item in self.identifiers}) != len(self.identifiers):
            raise ValueError("duplicate issuer identifier evidence")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "kind": EntityKind.ISSUER.value,
            "entity_id": self.entity_id,
            "canonical_name": self.canonical_name,
            "canonical_name_ref": self.canonical_name_ref.proof_hash,
            "alias_hashes": sorted(item.proof_hash for item in self.aliases),
            "identifier_hashes": sorted(
                item.proof_hash for item in self.identifiers
            ),
        })


@dataclass(frozen=True)
class TraderIdentity:
    entity_id: str
    canonical_name: str
    canonical_name_ref: SourceArtifactRef
    aliases: tuple[IdentityAlias, ...] = ()

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.entity_id):
            raise ValueError("invalid trader entity_id")
        cleaned = " ".join(self.canonical_name.split())
        if not cleaned:
            raise ValueError("canonical_name is required")
        object.__setattr__(self, "canonical_name", cleaned)
        if len({item.proof_hash for item in self.aliases}) != len(self.aliases):
            raise ValueError("duplicate trader alias evidence")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "kind": EntityKind.TRADER.value,
            "entity_id": self.entity_id,
            "canonical_name": self.canonical_name,
            "canonical_name_ref": self.canonical_name_ref.proof_hash,
            "alias_hashes": sorted(item.proof_hash for item in self.aliases),
        })


@dataclass(frozen=True)
class EntityResolutionResult:
    entity_kind: EntityKind
    query_type: str
    query_value: str
    as_of_date: str | None
    state: ResolutionState
    matched_entity_ids: tuple[str, ...]
    evidence_hashes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.as_of_date is not None:
            _date_or_none("as_of_date", self.as_of_date)
        if tuple(sorted(set(self.matched_entity_ids))) != self.matched_entity_ids:
            raise ValueError("matched_entity_ids must be unique and sorted")
        if tuple(sorted(set(self.evidence_hashes))) != self.evidence_hashes:
            raise ValueError("evidence_hashes must be unique and sorted")
        count = len(self.matched_entity_ids)
        expected = (
            ResolutionState.UNRESOLVED
            if count == 0
            else ResolutionState.RESOLVED
            if count == 1
            else ResolutionState.AMBIGUOUS
        )
        if self.state is not expected:
            raise ValueError("resolution state does not match match count")

    @property
    def resolved_entity_id(self) -> str | None:
        if self.state is ResolutionState.RESOLVED:
            return self.matched_entity_ids[0]
        return None

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "entity_kind": self.entity_kind.value,
            "query_type": self.query_type,
            "query_value": self.query_value,
            "as_of_date": self.as_of_date,
            "state": self.state.value,
            "matched_entity_ids": list(self.matched_entity_ids),
            "evidence_hashes": list(self.evidence_hashes),
        })


def _verify_identity_ref(
    ref: SourceArtifactRef,
    *,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
) -> None:
    if artifact_manifest.source_registry_hash != source_registry.registry_hash:
        raise ValueError("artifact manifest does not match source registry")
    artifact_manifest.resolve_ref(ref)
    source = source_registry.get(ref.source_id)
    if source.proof_hash != ref.source_proof_hash:
        raise ValueError("identity source proof mismatch")
    if source.admissibility is SourceAdmissibility.DISCOVERY_ONLY:
        raise ValueError("discovery-only source cannot establish durable identity")


def verify_issuer_identity(
    identity: IssuerIdentity,
    *,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
) -> None:
    refs = [identity.canonical_name_ref]
    refs.extend(item.ref for item in identity.aliases)
    refs.extend(item.ref for item in identity.identifiers)
    for ref in refs:
        _verify_identity_ref(
            ref,
            source_registry=source_registry,
            artifact_manifest=artifact_manifest,
        )


def verify_trader_identity(
    identity: TraderIdentity,
    *,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
) -> None:
    refs = [identity.canonical_name_ref]
    refs.extend(item.ref for item in identity.aliases)
    for ref in refs:
        _verify_identity_ref(
            ref,
            source_registry=source_registry,
            artifact_manifest=artifact_manifest,
        )


class EntityResolutionRegistry:
    """Append-only-in-identity registry with ambiguity-preserving lookup."""

    def __init__(self) -> None:
        self._issuers: dict[str, IssuerIdentity] = {}
        self._traders: dict[str, TraderIdentity] = {}

    def register_issuer(
        self,
        identity: IssuerIdentity,
        *,
        source_registry: SourceRegistry,
        artifact_manifest: RawArtifactManifest,
    ) -> IssuerIdentity:
        verify_issuer_identity(
            identity,
            source_registry=source_registry,
            artifact_manifest=artifact_manifest,
        )
        existing = self._issuers.get(identity.entity_id)
        if existing is not None:
            if existing.proof_hash != identity.proof_hash:
                raise ValueError("issuer entity_id already registered with different content")
            return existing
        self._issuers[identity.entity_id] = identity
        return identity

    def register_trader(
        self,
        identity: TraderIdentity,
        *,
        source_registry: SourceRegistry,
        artifact_manifest: RawArtifactManifest,
    ) -> TraderIdentity:
        verify_trader_identity(
            identity,
            source_registry=source_registry,
            artifact_manifest=artifact_manifest,
        )
        existing = self._traders.get(identity.entity_id)
        if existing is not None:
            if existing.proof_hash != identity.proof_hash:
                raise ValueError("trader entity_id already registered with different content")
            return existing
        self._traders[identity.entity_id] = identity
        return identity

    def issuer(self, entity_id: str) -> IssuerIdentity:
        try:
            return self._issuers[entity_id]
        except KeyError as exc:
            raise KeyError("unknown issuer entity_id: " + entity_id) from exc

    def trader(self, entity_id: str) -> TraderIdentity:
        try:
            return self._traders[entity_id]
        except KeyError as exc:
            raise KeyError("unknown trader entity_id: " + entity_id) from exc

    @staticmethod
    def _result(
        *,
        kind: EntityKind,
        query_type: str,
        query_value: str,
        as_of_date: str | None,
        matches: dict[str, set[str]],
    ) -> EntityResolutionResult:
        ids = tuple(sorted(matches))
        evidence = tuple(sorted({
            proof
            for entity_proofs in matches.values()
            for proof in entity_proofs
        }))
        state = (
            ResolutionState.UNRESOLVED
            if not ids
            else ResolutionState.RESOLVED
            if len(ids) == 1
            else ResolutionState.AMBIGUOUS
        )
        return EntityResolutionResult(
            entity_kind=kind,
            query_type=query_type,
            query_value=query_value,
            as_of_date=as_of_date,
            state=state,
            matched_entity_ids=ids,
            evidence_hashes=evidence,
        )

    def resolve_issuer_identifier(
        self,
        identifier_type: HistoricalIdentifierType,
        value: str,
        *,
        as_of_date: str | None = None,
    ) -> EntityResolutionResult:
        normalized = _normalize_identifier(identifier_type, value)
        if as_of_date is not None:
            _date_or_none("as_of_date", as_of_date)
        matches: dict[str, set[str]] = {}
        for entity_id, issuer in self._issuers.items():
            for identifier in issuer.identifiers:
                if (
                    identifier.identifier_type is identifier_type
                    and identifier.value == normalized
                    and identifier.active_on(as_of_date)
                ):
                    matches.setdefault(entity_id, set()).add(identifier.proof_hash)
        return self._result(
            kind=EntityKind.ISSUER,
            query_type=identifier_type.value,
            query_value=normalized,
            as_of_date=as_of_date,
            matches=matches,
        )

    def resolve_issuer_name(self, value: str) -> EntityResolutionResult:
        normalized = _normalized_name(value)
        matches: dict[str, set[str]] = {}
        for entity_id, issuer in self._issuers.items():
            if _normalized_name(issuer.canonical_name) == normalized:
                matches.setdefault(entity_id, set()).add(
                    issuer.canonical_name_ref.proof_hash
                )
            for alias in issuer.aliases:
                if alias.normalized_value == normalized:
                    matches.setdefault(entity_id, set()).add(alias.proof_hash)
        return self._result(
            kind=EntityKind.ISSUER,
            query_type="NAME_OR_ALIAS",
            query_value=normalized,
            as_of_date=None,
            matches=matches,
        )

    def resolve_trader_name(self, value: str) -> EntityResolutionResult:
        normalized = _normalized_name(value)
        matches: dict[str, set[str]] = {}
        for entity_id, trader in self._traders.items():
            if _normalized_name(trader.canonical_name) == normalized:
                matches.setdefault(entity_id, set()).add(
                    trader.canonical_name_ref.proof_hash
                )
            for alias in trader.aliases:
                if alias.normalized_value == normalized:
                    matches.setdefault(entity_id, set()).add(alias.proof_hash)
        return self._result(
            kind=EntityKind.TRADER,
            query_type="NAME_OR_ALIAS",
            query_value=normalized,
            as_of_date=None,
            matches=matches,
        )

    @property
    def registry_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "issuer_hashes": sorted(
                item.proof_hash for item in self._issuers.values()
            ),
            "trader_hashes": sorted(
                item.proof_hash for item in self._traders.values()
            ),
        })


@dataclass(frozen=True)
class CaseEntityCrosswalk:
    """Proof-pinned mapping from a case-local identity to one durable identity."""

    case_id: str
    case_proof_hash: str
    entity_kind: EntityKind
    local_id: str
    durable_entity_id: str
    durable_entity_proof_hash: str
    resolution: EntityResolutionResult

    def __post_init__(self) -> None:
        for name in ("case_id", "local_id", "durable_entity_id"):
            if not _ID_RE.fullmatch(getattr(self, name)):
                raise ValueError(f"invalid {name}")
        for name in ("case_proof_hash", "durable_entity_proof_hash"):
            if not re.fullmatch(r"^[0-9a-f]{64}$", getattr(self, name)):
                raise ValueError(f"{name} must be SHA-256")
        if self.resolution.entity_kind is not self.entity_kind:
            raise ValueError("crosswalk resolution entity kind mismatch")
        if self.resolution.state is not ResolutionState.RESOLVED:
            raise ValueError("crosswalk requires one uniquely resolved entity")
        if self.resolution.resolved_entity_id != self.durable_entity_id:
            raise ValueError("crosswalk target does not match resolved entity")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "case_id": self.case_id,
            "case_proof_hash": self.case_proof_hash,
            "entity_kind": self.entity_kind.value,
            "local_id": self.local_id,
            "durable_entity_id": self.durable_entity_id,
            "durable_entity_proof_hash": self.durable_entity_proof_hash,
            "resolution_hash": self.resolution.proof_hash,
        })


def verify_case_entity_crosswalk(
    crosswalk: CaseEntityCrosswalk,
    *,
    cases: CaseRegistry,
    entities: EntityResolutionRegistry,
) -> None:
    case = cases.get(crosswalk.case_id)
    if case.proof_hash != crosswalk.case_proof_hash:
        raise ValueError("crosswalk case proof mismatch")

    if crosswalk.entity_kind is EntityKind.ISSUER:
        local = next(
            (item for item in case.issuers if item.issuer_id == crosswalk.local_id),
            None,
        )
        if local is None:
            raise ValueError("crosswalk local issuer is not part of the case")
        durable = entities.issuer(crosswalk.durable_entity_id)
        if durable.proof_hash != crosswalk.durable_entity_proof_hash:
            raise ValueError("crosswalk durable issuer proof mismatch")

        if crosswalk.resolution.query_type == HistoricalIdentifierType.CIK.value:
            if local.cik is None:
                raise ValueError("case-local issuer has no CIK for this crosswalk")
            expected = _normalize_identifier(
                HistoricalIdentifierType.CIK,
                local.cik,
            )
            if crosswalk.resolution.query_value != expected:
                raise ValueError("crosswalk CIK query does not match case-local issuer")
            recomputed = entities.resolve_issuer_identifier(
                HistoricalIdentifierType.CIK,
                expected,
                as_of_date=crosswalk.resolution.as_of_date,
            )
        elif crosswalk.resolution.query_type == HistoricalIdentifierType.TICKER.value:
            if local.ticker_at_case is None:
                raise ValueError("case-local issuer has no ticker for this crosswalk")
            if crosswalk.resolution.as_of_date is None:
                raise ValueError("historical ticker crosswalk requires as_of_date")
            expected = _normalize_identifier(
                HistoricalIdentifierType.TICKER,
                local.ticker_at_case,
            )
            if crosswalk.resolution.query_value != expected:
                raise ValueError("crosswalk ticker query does not match case-local issuer")
            recomputed = entities.resolve_issuer_identifier(
                HistoricalIdentifierType.TICKER,
                expected,
                as_of_date=crosswalk.resolution.as_of_date,
            )
        elif crosswalk.resolution.query_type == "NAME_OR_ALIAS":
            expected = _normalized_name(local.legal_name)
            if crosswalk.resolution.query_value != expected:
                raise ValueError("crosswalk name query does not match case-local issuer")
            if crosswalk.resolution.as_of_date is not None:
                raise ValueError("issuer name crosswalk cannot carry as_of_date")
            recomputed = entities.resolve_issuer_name(local.legal_name)
        else:
            raise ValueError("unsupported issuer crosswalk query type")

    elif crosswalk.entity_kind is EntityKind.TRADER:
        local = next(
            (item for item in case.parties if item.party_id == crosswalk.local_id),
            None,
        )
        if local is None:
            raise ValueError("crosswalk local party is not part of the case")
        if CasePartyRole.TRADER not in local.roles:
            raise ValueError("case-local party is not a trader")
        durable = entities.trader(crosswalk.durable_entity_id)
        if durable.proof_hash != crosswalk.durable_entity_proof_hash:
            raise ValueError("crosswalk durable trader proof mismatch")
        if crosswalk.resolution.query_type != "NAME_OR_ALIAS":
            raise ValueError("trader crosswalk requires name/alias resolution")
        expected = _normalized_name(local.display_name)
        if crosswalk.resolution.query_value != expected:
            raise ValueError("crosswalk name query does not match case-local trader")
        if crosswalk.resolution.as_of_date is not None:
            raise ValueError("trader name crosswalk cannot carry as_of_date")
        recomputed = entities.resolve_trader_name(local.display_name)
    else:
        raise ValueError("unsupported crosswalk entity kind")

    if recomputed.proof_hash != crosswalk.resolution.proof_hash:
        raise ValueError("crosswalk resolution proof does not recompute")
    if recomputed.state is not ResolutionState.RESOLVED:
        raise ValueError("crosswalk resolution is no longer unique")
    if recomputed.resolved_entity_id != crosswalk.durable_entity_id:
        raise ValueError("crosswalk resolution target changed")


class CaseEntityCrosswalkRegistry:
    """Append-only case-local to durable-identity mappings."""

    def __init__(self) -> None:
        self._by_local: dict[tuple[str, str, str], CaseEntityCrosswalk] = {}

    def register(
        self,
        crosswalk: CaseEntityCrosswalk,
        *,
        cases: CaseRegistry,
        entities: EntityResolutionRegistry,
    ) -> CaseEntityCrosswalk:
        verify_case_entity_crosswalk(
            crosswalk,
            cases=cases,
            entities=entities,
        )
        key = (
            crosswalk.case_id,
            crosswalk.entity_kind.value,
            crosswalk.local_id,
        )
        existing = self._by_local.get(key)
        if existing is not None:
            if existing.proof_hash != crosswalk.proof_hash:
                raise ValueError(
                    "case-local identity already crosswalked with different content"
                )
            return existing
        self._by_local[key] = crosswalk
        return crosswalk

    def get(
        self,
        case_id: str,
        entity_kind: EntityKind,
        local_id: str,
    ) -> CaseEntityCrosswalk:
        key = (case_id, entity_kind.value, local_id)
        try:
            return self._by_local[key]
        except KeyError as exc:
            raise KeyError("unknown case-local entity crosswalk") from exc

    def all(self) -> tuple[CaseEntityCrosswalk, ...]:
        return tuple(
            self._by_local[key]
            for key in sorted(self._by_local)
        )

    @property
    def registry_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "crosswalk_hashes": [
                item.proof_hash for item in self.all()
            ],
        })


__all__ = [
    "CaseEntityCrosswalk",
    "CaseEntityCrosswalkRegistry",
    "EntityKind",
    "EntityResolutionRegistry",
    "EntityResolutionResult",
    "HistoricalIdentifier",
    "HistoricalIdentifierType",
    "IdentityAlias",
    "IssuerIdentity",
    "ResolutionState",
    "TraderIdentity",
    "verify_case_entity_crosswalk",
    "verify_issuer_identity",
    "verify_trader_identity",
]
