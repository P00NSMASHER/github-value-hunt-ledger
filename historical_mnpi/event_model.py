"""Information-event and public-release boundary model.

Step 6 separates the underlying historical information event from trade rows.
The event binds a case/issuer set to the public-release boundary and, when
available, the earlier private-information start or tip boundary.

No temporal precision is invented. Exact timestamps, dates, and ranges remain
separate representations.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
import re

from .case_model import CaseArtifactRole, CaseEventType, CaseRegistry
from .raw_artifacts import RawArtifactManifest, SourceArtifactRef
from .source_registry import SourceAdmissibility, SourceRegistry, canonical_hash


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")


class BoundaryPrecision(str, Enum):
    EXACT_TIMESTAMP = "EXACT_TIMESTAMP"
    DATE_ONLY = "DATE_ONLY"
    DATE_RANGE = "DATE_RANGE"


@dataclass(frozen=True)
class TemporalBoundary:
    ref: SourceArtifactRef
    timestamp: str | None = None
    date_value: str | None = None
    date_range_start: str | None = None
    date_range_end: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        present = sum(
            item is not None
            for item in (
                self.timestamp,
                self.date_value,
                self.date_range_start,
                self.date_range_end,
            )
        )
        if present == 0:
            raise ValueError("temporal boundary requires time/date information")

        if self.timestamp is not None:
            if present != 1:
                raise ValueError("exact timestamp cannot be combined with date fields")
            try:
                parsed = datetime.fromisoformat(
                    self.timestamp.replace("Z", "+00:00")
                )
            except ValueError as exc:
                raise ValueError("timestamp must be ISO-8601") from exc
            if parsed.tzinfo is None:
                raise ValueError("timestamp must include timezone")

        if self.date_value is not None:
            if present != 1:
                raise ValueError("date-only boundary cannot be combined with other time fields")
            try:
                date.fromisoformat(self.date_value)
            except ValueError as exc:
                raise ValueError("date_value must be YYYY-MM-DD") from exc

        has_start = self.date_range_start is not None
        has_end = self.date_range_end is not None
        if has_start != has_end:
            raise ValueError("date range requires both start and end")
        if has_start and has_end:
            if present != 2:
                raise ValueError("date range cannot be combined with other time fields")
            try:
                start = date.fromisoformat(self.date_range_start or "")
                end = date.fromisoformat(self.date_range_end or "")
            except ValueError as exc:
                raise ValueError("date range values must be YYYY-MM-DD") from exc
            if end < start:
                raise ValueError("date range end cannot precede start")

    @property
    def precision(self) -> BoundaryPrecision:
        if self.timestamp is not None:
            return BoundaryPrecision.EXACT_TIMESTAMP
        if self.date_value is not None:
            return BoundaryPrecision.DATE_ONLY
        return BoundaryPrecision.DATE_RANGE

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "ref_proof_hash": self.ref.proof_hash,
            "precision": self.precision.value,
            "timestamp": self.timestamp,
            "date_value": self.date_value,
            "date_range_start": self.date_range_start,
            "date_range_end": self.date_range_end,
            "description": self.description,
        })


@dataclass(frozen=True)
class InformationEvent:
    event_id: str
    case_id: str
    case_proof_hash: str
    event_type: CaseEventType
    issuer_ids: tuple[str, ...]
    information_summary: str
    public_release: TemporalBoundary
    private_information_start: TemporalBoundary | None = None
    tip_or_transfer_boundaries: tuple[TemporalBoundary, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.event_id):
            raise ValueError("invalid event_id")
        if not _ID_RE.fullmatch(self.case_id):
            raise ValueError("invalid case_id")
        if not re.fullmatch(r"^[0-9a-f]{64}$", self.case_proof_hash):
            raise ValueError("case_proof_hash must be SHA-256")
        if not self.issuer_ids:
            raise ValueError("information event requires issuer_ids")
        if len(set(self.issuer_ids)) != len(self.issuer_ids):
            raise ValueError("duplicate issuer_id in information event")
        if not self.information_summary.strip():
            raise ValueError("information_summary is required")

        if (
            self.private_information_start is not None
            and self.private_information_start.precision
            is BoundaryPrecision.EXACT_TIMESTAMP
            and self.public_release.precision
            is BoundaryPrecision.EXACT_TIMESTAMP
        ):
            private_dt = datetime.fromisoformat(
                (self.private_information_start.timestamp or "").replace("Z", "+00:00")
            )
            public_dt = datetime.fromisoformat(
                (self.public_release.timestamp or "").replace("Z", "+00:00")
            )
            if private_dt > public_dt:
                raise ValueError("private information start cannot follow public release")

        if (
            self.private_information_start is not None
            and self.private_information_start.precision
            is BoundaryPrecision.DATE_ONLY
            and self.public_release.precision
            is BoundaryPrecision.DATE_ONLY
        ):
            private_day = date.fromisoformat(
                self.private_information_start.date_value or ""
            )
            public_day = date.fromisoformat(self.public_release.date_value or "")
            if private_day > public_day:
                raise ValueError("private information date cannot follow public release date")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "event_id": self.event_id,
            "case_id": self.case_id,
            "case_proof_hash": self.case_proof_hash,
            "event_type": self.event_type.value,
            "issuer_ids": sorted(self.issuer_ids),
            "information_summary": self.information_summary,
            "public_release_hash": self.public_release.proof_hash,
            "private_information_start_hash": (
                self.private_information_start.proof_hash
                if self.private_information_start is not None
                else None
            ),
            "tip_or_transfer_hashes": sorted(
                item.proof_hash for item in self.tip_or_transfer_boundaries
            ),
            "notes": self.notes,
        })


class EventRegistry:
    def __init__(self) -> None:
        self._by_id: dict[str, InformationEvent] = {}

    def register(
        self,
        event: InformationEvent,
        *,
        cases: CaseRegistry,
        source_registry: SourceRegistry,
        artifact_manifest: RawArtifactManifest,
    ) -> InformationEvent:
        verify_event_provenance(
            event,
            cases=cases,
            source_registry=source_registry,
            artifact_manifest=artifact_manifest,
        )
        existing = self._by_id.get(event.event_id)
        if existing is not None:
            if existing.proof_hash != event.proof_hash:
                raise ValueError("event_id already registered with different content")
            return existing
        self._by_id[event.event_id] = event
        return event

    def get(self, event_id: str) -> InformationEvent:
        try:
            return self._by_id[event_id]
        except KeyError as exc:
            raise KeyError("unknown event_id: " + event_id) from exc

    def all(self) -> tuple[InformationEvent, ...]:
        return tuple(self._by_id[key] for key in sorted(self._by_id))

    @property
    def registry_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "event_proof_hashes": [item.proof_hash for item in self.all()],
        })


def verify_event_provenance(
    event: InformationEvent,
    *,
    cases: CaseRegistry,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
) -> None:
    case = cases.get(event.case_id)
    if case.proof_hash != event.case_proof_hash:
        raise ValueError("event case proof mismatch")

    case_issuer_ids = {item.issuer_id for item in case.issuers}
    if not set(event.issuer_ids).issubset(case_issuer_ids):
        raise ValueError("event issuer is not part of canonical case")

    case_links = {link.ref.proof_hash: link for link in case.artifacts}

    all_boundaries = [event.public_release]
    if event.private_information_start is not None:
        all_boundaries.append(event.private_information_start)
    all_boundaries.extend(event.tip_or_transfer_boundaries)

    for boundary in all_boundaries:
        artifact_manifest.resolve_ref(boundary.ref)
        source = source_registry.get(boundary.ref.source_id)
        if source.proof_hash != boundary.ref.source_proof_hash:
            raise ValueError("event boundary source proof mismatch")
        if boundary.ref.proof_hash not in case_links:
            raise ValueError("event boundary artifact is not linked to canonical case")

    public_source = source_registry.get(event.public_release.ref.source_id)
    public_link = case_links[event.public_release.ref.proof_hash]
    if public_source.admissibility is not SourceAdmissibility.PRIMARY_PUBLIC_RECORD:
        raise ValueError("public release boundary requires primary public record")
    if public_link.artifact_role is not CaseArtifactRole.PUBLIC_RELEASE:
        raise ValueError("public release boundary requires PUBLIC_RELEASE artifact role")


__all__ = [
    "BoundaryPrecision",
    "EventRegistry",
    "InformationEvent",
    "TemporalBoundary",
    "verify_event_provenance",
]
