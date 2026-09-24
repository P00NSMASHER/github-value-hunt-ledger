"""Source registry for a historical, public-record MNPI research corpus.

This module intentionally does *not* ingest trade rows or live information.
It establishes the provenance boundary that every later raw artifact must cross.

Design rules:
- only already-public sources may be registered;
- every source is SHA-256 bound before it can support normalized facts;
- discovery-only sources can lead to primary evidence but cannot establish facts;
- academic reconstructions remain distinct from primary SEC/DOJ/court records;
- the entire registry is deterministically hashable and replayable;
- intended use is historical research/compliance, not trading on nonpublic data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import urlparse


USAGE_SCOPE = "HISTORICAL_RESEARCH_COMPLIANCE_ONLY"
_SCHEMA_VERSION = 1
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")


class SourceType(str, Enum):
    SEC_COMPLAINT = "SEC_COMPLAINT"
    SEC_LITIGATION_RELEASE = "SEC_LITIGATION_RELEASE"
    SEC_ADMIN_ORDER = "SEC_ADMIN_ORDER"
    DOJ_INDICTMENT = "DOJ_INDICTMENT"
    DOJ_PLEA_OR_STATEMENT = "DOJ_PLEA_OR_STATEMENT"
    COURT_JUDGMENT = "COURT_JUDGMENT"
    COURT_EXHIBIT = "COURT_EXHIBIT"
    ACADEMIC_REPLICATION = "ACADEMIC_REPLICATION"
    FOIA_PUBLIC_RELEASE = "FOIA_PUBLIC_RELEASE"
    SECONDARY_INDEX = "SECONDARY_INDEX"


class SourceAdmissibility(str, Enum):
    PRIMARY_PUBLIC_RECORD = "PRIMARY_PUBLIC_RECORD"
    PUBLISHED_RESEARCH_RECONSTRUCTION = "PUBLISHED_RESEARCH_RECONSTRUCTION"
    DISCOVERY_ONLY = "DISCOVERY_ONLY"


_PRIMARY_TYPES = frozenset({
    SourceType.SEC_COMPLAINT,
    SourceType.SEC_LITIGATION_RELEASE,
    SourceType.SEC_ADMIN_ORDER,
    SourceType.DOJ_INDICTMENT,
    SourceType.DOJ_PLEA_OR_STATEMENT,
    SourceType.COURT_JUDGMENT,
    SourceType.COURT_EXHIBIT,
    SourceType.FOIA_PUBLIC_RELEASE,
})


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def canonical_hash(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({
            str(key): _freeze_json(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        })
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"metadata value is not JSON-compatible: {type(value)!r}")


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _parse_date(value: str) -> None:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("publication_date must be YYYY-MM-DD") from exc


def _parse_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("retrieved_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("retrieved_at must include a timezone offset")


def _validate_https_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("url must be an absolute https URL")


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    source_type: SourceType
    admissibility: SourceAdmissibility
    publisher: str
    title: str
    url: str
    publication_date: str
    sha256: str
    retrieved_at: str
    public_release_confirmed: bool
    case_id: str | None = None
    docket_id: str | None = None
    notes: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _SOURCE_ID_RE.fullmatch(self.source_id):
            raise ValueError(
                "source_id must be 3-128 characters using letters, numbers, "
                "dot, underscore, colon, or hyphen"
            )
        if not self.publisher.strip():
            raise ValueError("publisher is required")
        if not self.title.strip():
            raise ValueError("title is required")
        _validate_https_url(self.url)
        _parse_date(self.publication_date)
        _parse_timestamp(self.retrieved_at)

        digest = self.sha256.strip().lower()
        if not _SHA256_RE.fullmatch(digest):
            raise ValueError("sha256 must be a lowercase 64-character SHA-256")
        object.__setattr__(self, "sha256", digest)

        if self.public_release_confirmed is not True:
            raise ValueError(
                "historical MNPI registry accepts only already-public source artifacts"
            )

        if self.source_type is SourceType.SECONDARY_INDEX:
            if self.admissibility is not SourceAdmissibility.DISCOVERY_ONLY:
                raise ValueError(
                    "SECONDARY_INDEX sources must be DISCOVERY_ONLY"
                )
        elif self.source_type is SourceType.ACADEMIC_REPLICATION:
            if self.admissibility is not SourceAdmissibility.PUBLISHED_RESEARCH_RECONSTRUCTION:
                raise ValueError(
                    "ACADEMIC_REPLICATION sources must remain "
                    "PUBLISHED_RESEARCH_RECONSTRUCTION"
                )
        elif self.source_type in _PRIMARY_TYPES:
            if self.admissibility is not SourceAdmissibility.PRIMARY_PUBLIC_RECORD:
                raise ValueError(
                    f"{self.source_type.value} must be PRIMARY_PUBLIC_RECORD"
                )
        else:
            raise ValueError(f"unsupported source type: {self.source_type!r}")

        object.__setattr__(self, "metadata", _freeze_json(self.metadata))

    @property
    def fact_capabilities(self) -> tuple[str, ...]:
        if self.admissibility is SourceAdmissibility.PRIMARY_PUBLIC_RECORD:
            return (
                "CASE_FACT",
                "PUBLICATION_BOUNDARY_FACT",
                "TRADE_FACT_CANDIDATE",
            )
        if (
            self.admissibility
            is SourceAdmissibility.PUBLISHED_RESEARCH_RECONSTRUCTION
        ):
            return ("ACADEMIC_RECONSTRUCTION_CANDIDATE",)
        return ()

    @property
    def can_establish_trade_fact(self) -> bool:
        return "TRADE_FACT_CANDIDATE" in self.fact_capabilities

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self.to_dict(include_proof_hash=False))

    def to_dict(self, *, include_proof_hash: bool = True) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": _SCHEMA_VERSION,
            "usage_scope": USAGE_SCOPE,
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "admissibility": self.admissibility.value,
            "publisher": self.publisher,
            "title": self.title,
            "url": self.url,
            "publication_date": self.publication_date,
            "sha256": self.sha256,
            "retrieved_at": self.retrieved_at,
            "public_release_confirmed": self.public_release_confirmed,
            "case_id": self.case_id,
            "docket_id": self.docket_id,
            "notes": self.notes,
            "metadata": _thaw_json(self.metadata),
            "fact_capabilities": list(self.fact_capabilities),
        }
        if include_proof_hash:
            body["proof_hash"] = canonical_hash(body)
        return body

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceRecord":
        if payload.get("schema") != _SCHEMA_VERSION:
            raise ValueError("unsupported source-record schema")
        if payload.get("usage_scope") != USAGE_SCOPE:
            raise ValueError("source record is outside historical research scope")

        public_release_confirmed = payload.get("public_release_confirmed")
        if type(public_release_confirmed) is not bool:
            raise ValueError("public_release_confirmed must be a boolean")

        record = cls(
            source_id=str(payload["source_id"]),
            source_type=SourceType(str(payload["source_type"])),
            admissibility=SourceAdmissibility(str(payload["admissibility"])),
            publisher=str(payload["publisher"]),
            title=str(payload["title"]),
            url=str(payload["url"]),
            publication_date=str(payload["publication_date"]),
            sha256=str(payload["sha256"]),
            retrieved_at=str(payload["retrieved_at"]),
            public_release_confirmed=public_release_confirmed,
            case_id=(
                str(payload["case_id"])
                if payload.get("case_id") is not None
                else None
            ),
            docket_id=(
                str(payload["docket_id"])
                if payload.get("docket_id") is not None
                else None
            ),
            notes=(
                str(payload["notes"])
                if payload.get("notes") is not None
                else None
            ),
            metadata=payload.get("metadata") or {},
        )
        supplied_hash = payload.get("proof_hash")
        if supplied_hash is not None and supplied_hash != record.proof_hash:
            raise ValueError("source record proof hash mismatch")
        return record


class SourceRegistry:
    def __init__(self) -> None:
        self._by_id: dict[str, SourceRecord] = {}
        self._artifact_keys: dict[tuple[str, str], str] = {}

    def register(self, record: SourceRecord) -> SourceRecord:
        existing = self._by_id.get(record.source_id)
        if existing is not None:
            if existing.proof_hash != record.proof_hash:
                raise ValueError(
                    f"source_id already registered with different content: "
                    f"{record.source_id}"
                )
            return existing

        artifact_key = (record.url, record.sha256)
        existing_id = self._artifact_keys.get(artifact_key)
        if existing_id is not None:
            raise ValueError(
                "same source artifact is already registered as "
                + existing_id
            )

        self._by_id[record.source_id] = record
        self._artifact_keys[artifact_key] = record.source_id
        return record

    def get(self, source_id: str) -> SourceRecord:
        try:
            return self._by_id[source_id]
        except KeyError as exc:
            raise KeyError(f"unknown source_id: {source_id}") from exc

    def all(self) -> tuple[SourceRecord, ...]:
        return tuple(
            self._by_id[source_id]
            for source_id in sorted(self._by_id)
        )

    @property
    def registry_hash(self) -> str:
        return canonical_hash({
            "schema": _SCHEMA_VERSION,
            "usage_scope": USAGE_SCOPE,
            "source_proof_hashes": [
                record.proof_hash for record in self.all()
            ],
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": _SCHEMA_VERSION,
            "usage_scope": USAGE_SCOPE,
            "source_count": len(self._by_id),
            "sources": [record.to_dict() for record in self.all()],
            "registry_hash": self.registry_hash,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceRegistry":
        if payload.get("schema") != _SCHEMA_VERSION:
            raise ValueError("unsupported source-registry schema")
        if payload.get("usage_scope") != USAGE_SCOPE:
            raise ValueError("source registry is outside historical research scope")

        registry = cls()
        for raw in payload.get("sources", []):
            if not isinstance(raw, Mapping):
                raise ValueError("source registry contains a non-object source")
            registry.register(SourceRecord.from_dict(raw))

        if payload.get("source_count") != len(registry._by_id):
            raise ValueError("source_count does not match registered sources")
        if payload.get("registry_hash") != registry.registry_hash:
            raise ValueError("source registry hash mismatch")
        return registry

    @classmethod
    def from_json(cls, payload: str) -> "SourceRegistry":
        parsed = json.loads(payload)
        if not isinstance(parsed, Mapping):
            raise ValueError("source registry JSON must contain an object")
        return cls.from_dict(parsed)


__all__ = [
    "SourceAdmissibility",
    "SourceRecord",
    "SourceRegistry",
    "SourceType",
    "USAGE_SCOPE",
    "canonical_hash",
]
