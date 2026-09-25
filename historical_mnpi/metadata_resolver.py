"""Point-in-time metadata resolver for the real historical corpus.

Step 17 closes four metadata gates without weakening provenance or temporal
semantics:
- exact first-public announcement timestamp;
- historical primary listing exchange;
- effective-dated shares outstanding;
- same-day point-in-time control-universe metadata.

This module resolves only supplied public/authorized historical metadata. It does
not fetch data, connect to brokers, ingest live confidential information, or
authorize trading.

Safety boundary: metadata evidence/contracts reject live stolen information,
leaked credentials, accidental private disclosures, unauthorized private data,
and credential-like fields.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime, timezone
from enum import Enum
from typing import Iterable

from .coverage_planner import (
    CoverageEvidence,
    CoveragePlan,
    MarketSourceFamily,
)
from .source_registry import USAGE_SCOPE, canonical_hash


class MetadataDataClass(str, Enum):
    PUBLIC_OR_AUTHORIZED_HISTORICAL = "PUBLIC_OR_AUTHORIZED_HISTORICAL"
    LIVE_STOLEN_INFORMATION = "LIVE_STOLEN_INFORMATION"
    LEAKED_CREDENTIALS = "LEAKED_CREDENTIALS"
    ACCIDENTAL_PRIVATE_DISCLOSURE = "ACCIDENTAL_PRIVATE_DISCLOSURE"
    UNAUTHORIZED_PRIVATE_DATA = "UNAUTHORIZED_PRIVATE_DATA"


class MetadataSourceKind(str, Enum):
    ISSUER_PUBLIC_RELEASE = "ISSUER_PUBLIC_RELEASE"
    OFFICIAL_PUBLIC_NEWSWIRE = "OFFICIAL_PUBLIC_NEWSWIRE"
    EDGAR_ACCEPTANCE_DATETIME_PROXY = "EDGAR_ACCEPTANCE_DATETIME_PROXY"
    NYSE_DAILY_TAQ_MASTER = "NYSE_DAILY_TAQ_MASTER"
    OFFICIAL_LISTING_HISTORY = "OFFICIAL_LISTING_HISTORY"
    PUBLIC_EFFECTIVE_DATED_SHARES = "PUBLIC_EFFECTIVE_DATED_SHARES"
    RETROSPECTIVE_SAMPLE_FIRMS = "RETROSPECTIVE_SAMPLE_FIRMS"
    POINT_IN_TIME_CONTROL_UNIVERSE = "POINT_IN_TIME_CONTROL_UNIVERSE"


class ResolutionState(str, Enum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    CONFLICT = "CONFLICT"


_CREDENTIAL_FIELD_FRAGMENTS = (
    "password",
    "passwd",
    "credential",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "private_key",
    "session_cookie",
    "auth_cookie",
)


def _aware_timestamp(name: str, value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include timezone")
    return parsed


def _utc(value: str) -> datetime:
    return _aware_timestamp("timestamp", value).astimezone(timezone.utc)


def _validate_data_class(data_class: MetadataDataClass) -> None:
    if data_class is not MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL:
        raise ValueError(
            "metadata evidence class is prohibited for historical MNPI research: "
            + data_class.value
        )


def validate_metadata_contract_fields(field_names: Iterable[str]) -> None:
    for field_name in field_names:
        lowered = field_name.strip().lower()
        if any(fragment in lowered for fragment in _CREDENTIAL_FIELD_FRAGMENTS):
            raise ValueError(
                "credential-like metadata contract field is prohibited: "
                + field_name
            )


@dataclass(frozen=True)
class MetadataEvidenceRef:
    evidence_id: str
    source_kind: MetadataSourceKind
    source_name: str
    data_class: MetadataDataClass = (
        MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL
    )

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("evidence_id is required")
        if not self.source_name.strip():
            raise ValueError("source_name is required")
        _validate_data_class(self.data_class)
        validate_metadata_contract_fields(
            field.name for field in fields(self)
        )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "evidence_id": self.evidence_id,
            "source_kind": self.source_kind.value,
            "source_name": self.source_name,
            "data_class": self.data_class.value,
        })


@dataclass(frozen=True)
class AnnouncementTimestampEvidence:
    event_id: str
    timestamp: str
    evidence: MetadataEvidenceRef
    proves_first_public_release: bool

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id is required")
        _aware_timestamp("announcement timestamp", self.timestamp)
        if (
            self.evidence.source_kind
            is MetadataSourceKind.EDGAR_ACCEPTANCE_DATETIME_PROXY
            and self.proves_first_public_release
        ):
            raise ValueError(
                "EDGAR ACCEPTANCE-DATETIME is only a public proxy and "
                "cannot prove first public release"
            )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "event_id": self.event_id,
            "timestamp_utc": _utc(self.timestamp).isoformat(),
            "evidence_hash": self.evidence.proof_hash,
            "proves_first_public_release": self.proves_first_public_release,
        })


@dataclass(frozen=True)
class ListingExchangeEvidence:
    symbol: str
    session_date: str
    primary_exchange: str
    evidence: MetadataEvidenceRef

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        exchange = self.primary_exchange.strip().upper()
        if not symbol or not exchange:
            raise ValueError("listing evidence requires symbol/exchange")
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "primary_exchange", exchange)
        date.fromisoformat(self.session_date)
        if self.evidence.source_kind not in {
            MetadataSourceKind.NYSE_DAILY_TAQ_MASTER,
            MetadataSourceKind.OFFICIAL_LISTING_HISTORY,
        }:
            raise ValueError(
                "listing exchange evidence requires TAQ Master or "
                "official listing history"
            )

    @property
    def key(self) -> tuple[str, str]:
        return self.symbol, self.session_date

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "symbol": self.symbol,
            "session_date": self.session_date,
            "primary_exchange": self.primary_exchange,
            "evidence_hash": self.evidence.proof_hash,
        })


@dataclass(frozen=True)
class SharesOutstandingEvidence:
    symbol: str
    effective_date: str
    shares_outstanding: str
    public_availability_timestamp: str
    evidence: MetadataEvidenceRef

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        if not symbol:
            raise ValueError("shares evidence requires symbol")
        object.__setattr__(self, "symbol", symbol)
        date.fromisoformat(self.effective_date)
        availability = _aware_timestamp(
            "public_availability_timestamp",
            self.public_availability_timestamp,
        )
        try:
            shares = int(self.shares_outstanding)
        except ValueError as exc:
            raise ValueError("shares_outstanding must be integer text") from exc
        if shares <= 0:
            raise ValueError("shares_outstanding must be positive")
        object.__setattr__(self, "shares_outstanding", str(shares))
        if self.evidence.source_kind not in {
            MetadataSourceKind.NYSE_DAILY_TAQ_MASTER,
            MetadataSourceKind.PUBLIC_EFFECTIVE_DATED_SHARES,
        }:
            raise ValueError("unsupported shares-outstanding source kind")
        if availability.tzinfo is None:
            raise ValueError("availability timestamp must include timezone")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "symbol": self.symbol,
            "effective_date": self.effective_date,
            "shares_outstanding": self.shares_outstanding,
            "public_availability_utc": _utc(
                self.public_availability_timestamp
            ).isoformat(),
            "evidence_hash": self.evidence.proof_hash,
        })


@dataclass(frozen=True)
class ControlUniverseEvidence:
    control_date: str
    universe_id: str
    symbols: tuple[str, ...]
    availability_timestamp: str | None
    complete_pre_event_covariates: bool
    evidence: MetadataEvidenceRef

    def __post_init__(self) -> None:
        date.fromisoformat(self.control_date)
        if not self.universe_id.strip():
            raise ValueError("universe_id is required")
        normalized = tuple(sorted({
            item.strip().upper() for item in self.symbols if item.strip()
        }))
        if not normalized:
            raise ValueError("control universe requires symbols")
        object.__setattr__(self, "symbols", normalized)
        if self.availability_timestamp is not None:
            _aware_timestamp(
                "control availability timestamp",
                self.availability_timestamp,
            )
        if (
            self.evidence.source_kind
            is MetadataSourceKind.RETROSPECTIVE_SAMPLE_FIRMS
            and self.availability_timestamp is None
        ):
            raise ValueError(
                "retrospective SampleFirms evidence requires a point-in-time "
                "availability timestamp"
            )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "control_date": self.control_date,
            "universe_id": self.universe_id,
            "symbols": list(self.symbols),
            "availability_utc": (
                _utc(self.availability_timestamp).isoformat()
                if self.availability_timestamp is not None
                else None
            ),
            "complete_pre_event_covariates": (
                self.complete_pre_event_covariates
            ),
            "evidence_hash": self.evidence.proof_hash,
        })


@dataclass(frozen=True)
class AnnouncementResolution:
    event_id: str
    state: ResolutionState
    timestamp_utc: str | None
    evidence_hashes: tuple[str, ...]
    rejection_reasons: tuple[str, ...] = ()

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "event_id": self.event_id,
            "state": self.state.value,
            "timestamp_utc": self.timestamp_utc,
            "evidence_hashes": list(self.evidence_hashes),
            "rejection_reasons": list(self.rejection_reasons),
        })


@dataclass(frozen=True)
class ListingResolution:
    symbol: str
    session_date: str
    state: ResolutionState
    primary_exchange: str | None
    evidence_hashes: tuple[str, ...]

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "symbol": self.symbol,
            "session_date": self.session_date,
            "state": self.state.value,
            "primary_exchange": self.primary_exchange,
            "evidence_hashes": list(self.evidence_hashes),
        })


@dataclass(frozen=True)
class SharesResolution:
    symbol: str
    session_date: str
    state: ResolutionState
    shares_outstanding: str | None
    effective_date: str | None
    evidence_hashes: tuple[str, ...]
    rejected_future_evidence_hashes: tuple[str, ...]

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "symbol": self.symbol,
            "session_date": self.session_date,
            "state": self.state.value,
            "shares_outstanding": self.shares_outstanding,
            "effective_date": self.effective_date,
            "evidence_hashes": list(self.evidence_hashes),
            "rejected_future_evidence_hashes": list(
                self.rejected_future_evidence_hashes
            ),
        })


@dataclass(frozen=True)
class ControlUniverseResolution:
    control_date: str
    state: ResolutionState
    universe_id: str | None
    symbols: tuple[str, ...]
    evidence_hashes: tuple[str, ...]
    rejection_reasons: tuple[str, ...] = ()

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "control_date": self.control_date,
            "state": self.state.value,
            "universe_id": self.universe_id,
            "symbols": list(self.symbols),
            "evidence_hashes": list(self.evidence_hashes),
            "rejection_reasons": list(self.rejection_reasons),
        })


def resolve_announcement_timestamp(
    event_id: str,
    evidence: Iterable[AnnouncementTimestampEvidence],
) -> AnnouncementResolution:
    matching = tuple(
        item for item in evidence if item.event_id == event_id
    )
    qualifying = tuple(
        item for item in matching if item.proves_first_public_release
    )
    proxy_hashes = tuple(sorted(
        item.proof_hash
        for item in matching
        if (
            item.evidence.source_kind
            is MetadataSourceKind.EDGAR_ACCEPTANCE_DATETIME_PROXY
        )
    ))
    if not qualifying:
        reasons = ()
        if proxy_hashes:
            reasons = ("EDGAR_ACCEPTANCE_IS_PROXY_ONLY",)
        return AnnouncementResolution(
            event_id=event_id,
            state=ResolutionState.UNRESOLVED,
            timestamp_utc=None,
            evidence_hashes=tuple(sorted(
                item.proof_hash for item in matching
            )),
            rejection_reasons=reasons,
        )

    timestamps = {
        _utc(item.timestamp).isoformat() for item in qualifying
    }
    if len(timestamps) != 1:
        return AnnouncementResolution(
            event_id=event_id,
            state=ResolutionState.CONFLICT,
            timestamp_utc=None,
            evidence_hashes=tuple(sorted(
                item.proof_hash for item in qualifying
            )),
            rejection_reasons=(
                "CONFLICTING_FIRST_PUBLIC_ANNOUNCEMENT_TIMESTAMPS",
            ),
        )
    return AnnouncementResolution(
        event_id=event_id,
        state=ResolutionState.RESOLVED,
        timestamp_utc=next(iter(timestamps)),
        evidence_hashes=tuple(sorted(
            item.proof_hash for item in qualifying
        )),
    )


def resolve_listing_exchange(
    symbol: str,
    session_date: str,
    evidence: Iterable[ListingExchangeEvidence],
) -> ListingResolution:
    symbol = symbol.strip().upper()
    date.fromisoformat(session_date)
    matching = tuple(
        item
        for item in evidence
        if item.symbol == symbol and item.session_date == session_date
    )
    values = {item.primary_exchange for item in matching}
    if not matching:
        state = ResolutionState.UNRESOLVED
        value = None
    elif len(values) != 1:
        state = ResolutionState.CONFLICT
        value = None
    else:
        state = ResolutionState.RESOLVED
        value = next(iter(values))
    return ListingResolution(
        symbol=symbol,
        session_date=session_date,
        state=state,
        primary_exchange=value,
        evidence_hashes=tuple(sorted(
            item.proof_hash for item in matching
        )),
    )


def resolve_shares_outstanding(
    symbol: str,
    session_date: str,
    evidence: Iterable[SharesOutstandingEvidence],
) -> SharesResolution:
    symbol = symbol.strip().upper()
    target_day = date.fromisoformat(session_date)
    matching = tuple(
        item for item in evidence if item.symbol == symbol
    )

    eligible = []
    rejected_future = []
    for item in matching:
        effective_day = date.fromisoformat(item.effective_date)
        available_day = _utc(
            item.public_availability_timestamp
        ).date()
        if effective_day > target_day or available_day > target_day:
            rejected_future.append(item)
            continue
        eligible.append(item)

    if not eligible:
        return SharesResolution(
            symbol=symbol,
            session_date=session_date,
            state=ResolutionState.UNRESOLVED,
            shares_outstanding=None,
            effective_date=None,
            evidence_hashes=(),
            rejected_future_evidence_hashes=tuple(sorted(
                item.proof_hash for item in rejected_future
            )),
        )

    latest_effective = max(
        date.fromisoformat(item.effective_date)
        for item in eligible
    )
    latest = tuple(
        item for item in eligible
        if date.fromisoformat(item.effective_date) == latest_effective
    )
    values = {item.shares_outstanding for item in latest}
    if len(values) != 1:
        state = ResolutionState.CONFLICT
        shares = None
        effective = None
    else:
        state = ResolutionState.RESOLVED
        shares = next(iter(values))
        effective = latest_effective.isoformat()
    return SharesResolution(
        symbol=symbol,
        session_date=session_date,
        state=state,
        shares_outstanding=shares,
        effective_date=effective,
        evidence_hashes=tuple(sorted(
            item.proof_hash for item in latest
        )),
        rejected_future_evidence_hashes=tuple(sorted(
            item.proof_hash for item in rejected_future
        )),
    )


def resolve_control_universe(
    control_date: str,
    evidence: Iterable[ControlUniverseEvidence],
) -> ControlUniverseResolution:
    target_day = date.fromisoformat(control_date)
    matching = tuple(
        item for item in evidence if item.control_date == control_date
    )
    eligible = []
    reasons = []
    for item in matching:
        if item.availability_timestamp is None:
            reasons.append("MISSING_POINT_IN_TIME_AVAILABILITY")
            continue
        available_day = _utc(item.availability_timestamp).date()
        if available_day > target_day:
            reasons.append("CONTROL_UNIVERSE_AVAILABLE_ONLY_IN_FUTURE")
            continue
        if not item.complete_pre_event_covariates:
            reasons.append("INCOMPLETE_PRE_EVENT_COVARIATES")
            continue
        eligible.append(item)

    if not eligible:
        return ControlUniverseResolution(
            control_date=control_date,
            state=ResolutionState.UNRESOLVED,
            universe_id=None,
            symbols=(),
            evidence_hashes=tuple(sorted(
                item.proof_hash for item in matching
            )),
            rejection_reasons=tuple(sorted(set(reasons))),
        )

    content = {
        (item.universe_id, item.symbols) for item in eligible
    }
    if len(content) != 1:
        return ControlUniverseResolution(
            control_date=control_date,
            state=ResolutionState.CONFLICT,
            universe_id=None,
            symbols=(),
            evidence_hashes=tuple(sorted(
                item.proof_hash for item in eligible
            )),
            rejection_reasons=("CONFLICTING_POINT_IN_TIME_CONTROL_UNIVERSES",),
        )
    universe_id, symbols = next(iter(content))
    return ControlUniverseResolution(
        control_date=control_date,
        state=ResolutionState.RESOLVED,
        universe_id=universe_id,
        symbols=symbols,
        evidence_hashes=tuple(sorted(
            item.proof_hash for item in eligible
        )),
    )


@dataclass(frozen=True)
class MetadataResolutionBundle:
    coverage_plan_hash: str
    announcements: tuple[AnnouncementResolution, ...]
    listings: tuple[ListingResolution, ...]
    shares: tuple[SharesResolution, ...]
    controls: tuple[ControlUniverseResolution, ...]
    market_source_dates: frozenset[tuple[MarketSourceFamily, str]]
    live_use_allowed: bool = False

    def __post_init__(self) -> None:
        if self.live_use_allowed is not False:
            raise ValueError("metadata resolver cannot enable live use")

    @property
    def ready_metadata_gates(self) -> bool:
        return all(
            item.state is ResolutionState.RESOLVED
            for group in (
                self.announcements,
                self.listings,
                self.shares,
                self.controls,
            )
            for item in group
        )

    def coverage_evidence(self) -> CoverageEvidence:
        return CoverageEvidence(
            exact_announcement_event_ids=frozenset(
                item.event_id
                for item in self.announcements
                if item.state is ResolutionState.RESOLVED
            ),
            market_source_dates=self.market_source_dates,
            listing_symbol_dates=frozenset(
                (item.symbol, item.session_date)
                for item in self.listings
                if item.state is ResolutionState.RESOLVED
            ),
            shares_symbol_dates=frozenset(
                (item.symbol, item.session_date)
                for item in self.shares
                if item.state is ResolutionState.RESOLVED
            ),
            control_dates=frozenset(
                item.control_date
                for item in self.controls
                if item.state is ResolutionState.RESOLVED
            ),
        )

    def readiness_summary(self) -> dict:
        def count_resolved(items) -> int:
            return sum(
                item.state is ResolutionState.RESOLVED
                for item in items
            )

        return {
            "scope": USAGE_SCOPE,
            "coverage_plan_hash": self.coverage_plan_hash,
            "announcement_resolved": count_resolved(self.announcements),
            "announcement_total": len(self.announcements),
            "listing_resolved": count_resolved(self.listings),
            "listing_total": len(self.listings),
            "shares_resolved": count_resolved(self.shares),
            "shares_total": len(self.shares),
            "control_resolved": count_resolved(self.controls),
            "control_total": len(self.controls),
            "market_source_date_count": len(self.market_source_dates),
            "ready_metadata_gates": self.ready_metadata_gates,
            "bundle_hash": self.proof_hash,
            "live_use_allowed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "coverage_plan_hash": self.coverage_plan_hash,
            "announcement_hashes": sorted(
                item.proof_hash for item in self.announcements
            ),
            "listing_hashes": sorted(
                item.proof_hash for item in self.listings
            ),
            "shares_hashes": sorted(
                item.proof_hash for item in self.shares
            ),
            "control_hashes": sorted(
                item.proof_hash for item in self.controls
            ),
            "market_source_dates": sorted(
                [family.value, day]
                for family, day in self.market_source_dates
            ),
            "live_use_allowed": False,
        })


def resolve_metadata_for_plan(
    plan: CoveragePlan,
    *,
    announcement_evidence: Iterable[
        AnnouncementTimestampEvidence
    ] = (),
    listing_evidence: Iterable[ListingExchangeEvidence] = (),
    shares_evidence: Iterable[SharesOutstandingEvidence] = (),
    control_evidence: Iterable[ControlUniverseEvidence] = (),
    market_source_dates: frozenset[
        tuple[MarketSourceFamily, str]
    ] = frozenset(),
) -> MetadataResolutionBundle:
    announcements_input = tuple(announcement_evidence)
    listings_input = tuple(listing_evidence)
    shares_input = tuple(shares_evidence)
    controls_input = tuple(control_evidence)

    announcements = tuple(
        resolve_announcement_timestamp(
            event_id,
            announcements_input,
        )
        for event_id in plan.announcement_event_ids
    )
    listings = tuple(
        resolve_listing_exchange(
            requirement.symbol,
            requirement.session_date,
            listings_input,
        )
        for requirement in plan.symbol_date_requirements
    )
    shares = tuple(
        resolve_shares_outstanding(
            requirement.symbol,
            requirement.session_date,
            shares_input,
        )
        for requirement in plan.symbol_date_requirements
    )
    controls = tuple(
        resolve_control_universe(
            control_date,
            controls_input,
        )
        for control_date in plan.control_dates
    )
    return MetadataResolutionBundle(
        coverage_plan_hash=plan.proof_hash,
        announcements=announcements,
        listings=listings,
        shares=shares,
        controls=controls,
        market_source_dates=market_source_dates,
        live_use_allowed=False,
    )


__all__ = [
    "AnnouncementResolution",
    "AnnouncementTimestampEvidence",
    "ControlUniverseEvidence",
    "ControlUniverseResolution",
    "ListingExchangeEvidence",
    "ListingResolution",
    "MetadataDataClass",
    "MetadataEvidenceRef",
    "MetadataResolutionBundle",
    "MetadataSourceKind",
    "ResolutionState",
    "SharesOutstandingEvidence",
    "SharesResolution",
    "resolve_announcement_timestamp",
    "resolve_control_universe",
    "resolve_listing_exchange",
    "resolve_metadata_for_plan",
    "resolve_shares_outstanding",
    "validate_metadata_contract_fields",
]
