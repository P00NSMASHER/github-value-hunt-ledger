"""Coverage planner and real-data readiness audit.

Step 16 converts a historical first-trade event corpus into a deterministic,
calendar-aware acquisition/import plan. It does not fetch, purchase, or ingest
market/reference data.

For each event, the planner requires the event session plus up to 21 prior
supported XNYS sessions. Unsupported early-close sessions may be skipped from the
baseline window, but the planner fails closed when it cannot assemble the
requested baseline coverage.

The readiness audit tracks five real-corpus gates:
- exact first-public announcement timestamp;
- required market-file coverage;
- historical primary-listing metadata;
- effective-dated shares outstanding;
- same-day point-in-time matched-control metadata.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
import csv
import io
import json
from typing import Iterable

from .source_registry import USAGE_SCOPE, canonical_hash


BASELINE_SESSIONS = 21


class MarketSourceFamily(str, Enum):
    TAQ_MASTER = "TAQ_MASTER"
    TAQ_TRADES_QUOTES = "TAQ_TRADES_QUOTES"
    OPTIONS = "OPTIONS"
    CONDITIONAL_ITCH = "CONDITIONAL_ITCH"


class CoverageGate(str, Enum):
    EXACT_ANNOUNCEMENT = "EXACT_ANNOUNCEMENT"
    MARKET_FILES = "MARKET_FILES"
    LISTING_HISTORY = "LISTING_HISTORY"
    SHARES_OUTSTANDING = "SHARES_OUTSTANDING"
    CONTROL_METADATA = "CONTROL_METADATA"
    BASELINE_CALENDAR = "BASELINE_CALENDAR"


@dataclass(frozen=True)
class HistoricalFirstTradeEvent:
    event_id: str
    symbol: str
    first_trade_date: str

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id is required")
        normalized = self.symbol.strip().upper()
        if not normalized:
            raise ValueError("symbol is required")
        object.__setattr__(self, "symbol", normalized)
        date.fromisoformat(self.first_trade_date)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "event_id": self.event_id,
            "symbol": self.symbol,
            "first_trade_date": self.first_trade_date,
        })


@dataclass(frozen=True)
class XNYSSession:
    session_date: str
    is_early_close: bool = False
    supported_for_baseline: bool = True

    def __post_init__(self) -> None:
        date.fromisoformat(self.session_date)
        if self.is_early_close and not self.supported_for_baseline:
            return
        if type(self.is_early_close) is not bool:
            raise ValueError("is_early_close must be boolean")
        if type(self.supported_for_baseline) is not bool:
            raise ValueError("supported_for_baseline must be boolean")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "session_date": self.session_date,
            "is_early_close": self.is_early_close,
            "supported_for_baseline": self.supported_for_baseline,
        })


@dataclass(frozen=True)
class CoverageEvidence:
    exact_announcement_event_ids: frozenset[str] = frozenset()
    market_source_dates: frozenset[tuple[MarketSourceFamily, str]] = frozenset()
    listing_symbol_dates: frozenset[tuple[str, str]] = frozenset()
    shares_symbol_dates: frozenset[tuple[str, str]] = frozenset()
    control_dates: frozenset[str] = frozenset()

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "exact_announcement_event_ids": sorted(
                self.exact_announcement_event_ids
            ),
            "market_source_dates": sorted(
                [family.value, day]
                for family, day in self.market_source_dates
            ),
            "listing_symbol_dates": sorted(
                [symbol, day] for symbol, day in self.listing_symbol_dates
            ),
            "shares_symbol_dates": sorted(
                [symbol, day] for symbol, day in self.shares_symbol_dates
            ),
            "control_dates": sorted(self.control_dates),
        })


@dataclass(frozen=True)
class SymbolDateRequirement:
    symbol: str
    session_date: str
    event_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        date.fromisoformat(self.session_date)
        if not self.symbol:
            raise ValueError("symbol-date requirement requires symbol")
        if not self.event_ids:
            raise ValueError("symbol-date requirement requires event_ids")
        if tuple(sorted(set(self.event_ids))) != self.event_ids:
            raise ValueError("event_ids must be unique and sorted")

    @property
    def key(self) -> tuple[str, str]:
        return self.symbol, self.session_date

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "symbol": self.symbol,
            "session_date": self.session_date,
            "event_ids": list(self.event_ids),
        })


@dataclass(frozen=True)
class SourceDateRequirement:
    source_family: MarketSourceFamily
    session_date: str

    def __post_init__(self) -> None:
        date.fromisoformat(self.session_date)

    @property
    def key(self) -> tuple[MarketSourceFamily, str]:
        return self.source_family, self.session_date

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "source_family": self.source_family.value,
            "session_date": self.session_date,
        })


@dataclass(frozen=True)
class EventCoveragePlan:
    event_id: str
    symbol: str
    event_session_date: str
    baseline_session_dates: tuple[str, ...]
    skipped_early_close_dates: tuple[str, ...]

    def __post_init__(self) -> None:
        date.fromisoformat(self.event_session_date)
        if len(self.baseline_session_dates) > BASELINE_SESSIONS:
            raise ValueError("baseline exceeds configured session count")
        for day in self.baseline_session_dates + self.skipped_early_close_dates:
            date.fromisoformat(day)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "event_id": self.event_id,
            "symbol": self.symbol,
            "event_session_date": self.event_session_date,
            "baseline_session_dates": list(self.baseline_session_dates),
            "skipped_early_close_dates": list(self.skipped_early_close_dates),
        })


@dataclass(frozen=True)
class UnresolvedCoverageGate:
    gate: CoverageGate
    key: str
    event_id: str | None = None
    symbol: str | None = None
    session_date: str | None = None
    source_family: MarketSourceFamily | None = None
    detail: str | None = None

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "gate": self.gate.value,
            "key": self.key,
            "event_id": self.event_id,
            "symbol": self.symbol,
            "session_date": self.session_date,
            "source_family": (
                self.source_family.value
                if self.source_family is not None
                else None
            ),
            "detail": self.detail,
        })


@dataclass(frozen=True)
class CoveragePlan:
    events: tuple[HistoricalFirstTradeEvent, ...]
    event_plans: tuple[EventCoveragePlan, ...]
    symbol_date_requirements: tuple[SymbolDateRequirement, ...]
    source_date_requirements: tuple[SourceDateRequirement, ...]
    announcement_event_ids: tuple[str, ...]
    control_dates: tuple[str, ...]
    unresolved_gates: tuple[UnresolvedCoverageGate, ...]
    evidence_hash: str
    baseline_sessions: int = BASELINE_SESSIONS
    live_use_allowed: bool = False

    def __post_init__(self) -> None:
        if self.live_use_allowed is not False:
            raise ValueError("coverage plan cannot enable live use")
        if self.baseline_sessions != BASELINE_SESSIONS:
            raise ValueError("unexpected baseline session count")

    @property
    def ready(self) -> bool:
        return not self.unresolved_gates

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "event_hashes": sorted(item.proof_hash for item in self.events),
            "event_plan_hashes": sorted(
                item.proof_hash for item in self.event_plans
            ),
            "symbol_date_hashes": sorted(
                item.proof_hash for item in self.symbol_date_requirements
            ),
            "source_date_hashes": sorted(
                item.proof_hash for item in self.source_date_requirements
            ),
            "announcement_event_ids": list(self.announcement_event_ids),
            "control_dates": list(self.control_dates),
            "unresolved_gate_hashes": sorted(
                item.proof_hash for item in self.unresolved_gates
            ),
            "evidence_hash": self.evidence_hash,
            "baseline_sessions": self.baseline_sessions,
            "live_use_allowed": False,
        })

    def summary(self) -> dict:
        by_gate = {
            gate.value: sum(
                1 for item in self.unresolved_gates if item.gate is gate
            )
            for gate in CoverageGate
        }
        return {
            "scope": USAGE_SCOPE,
            "ready": self.ready,
            "event_count": len(self.events),
            "symbol_date_requirement_count": len(
                self.symbol_date_requirements
            ),
            "source_date_requirement_count": len(
                self.source_date_requirements
            ),
            "announcement_requirement_count": len(
                self.announcement_event_ids
            ),
            "control_date_count": len(self.control_dates),
            "unresolved_gate_count": len(self.unresolved_gates),
            "unresolved_by_gate": by_gate,
            "baseline_sessions": self.baseline_sessions,
            "plan_hash": self.proof_hash,
            "live_use_allowed": False,
        }

    def render_artifacts(self) -> dict[str, str]:
        def csv_text(headers: list[str], rows: list[list[object]]) -> str:
            output = io.StringIO()
            writer = csv.writer(output, lineterminator="\n")
            writer.writerow(headers)
            writer.writerows(rows)
            return output.getvalue()

        event_csv = csv_text(
            [
                "event_id",
                "symbol",
                "event_session_date",
                "baseline_session_dates",
                "skipped_early_close_dates",
            ],
            [
                [
                    item.event_id,
                    item.symbol,
                    item.event_session_date,
                    "|".join(item.baseline_session_dates),
                    "|".join(item.skipped_early_close_dates),
                ]
                for item in self.event_plans
            ],
        )
        symbol_csv = csv_text(
            ["symbol", "session_date", "event_ids"],
            [
                [item.symbol, item.session_date, "|".join(item.event_ids)]
                for item in self.symbol_date_requirements
            ],
        )
        source_csv = csv_text(
            ["source_family", "session_date"],
            [
                [item.source_family.value, item.session_date]
                for item in self.source_date_requirements
            ],
        )
        announcement_csv = csv_text(
            ["event_id"],
            [[event_id] for event_id in self.announcement_event_ids],
        )
        gates_csv = csv_text(
            [
                "gate",
                "key",
                "event_id",
                "symbol",
                "session_date",
                "source_family",
                "detail",
            ],
            [
                [
                    item.gate.value,
                    item.key,
                    item.event_id or "",
                    item.symbol or "",
                    item.session_date or "",
                    item.source_family.value
                    if item.source_family is not None
                    else "",
                    item.detail or "",
                ]
                for item in self.unresolved_gates
            ],
        )

        acquisition_plan = {
            "scope": USAGE_SCOPE,
            "fetch_or_purchase_performed": False,
            "source_dates": {
                family.value: [
                    item.session_date
                    for item in self.source_date_requirements
                    if item.source_family is family
                ]
                for family in MarketSourceFamily
            },
            "symbols": sorted({
                item.symbol for item in self.symbol_date_requirements
            }),
            "control_dates": list(self.control_dates),
            "plan_hash": self.proof_hash,
        }
        return {
            "event_coverage_plan.csv": event_csv,
            "symbol_date_requirements.csv": symbol_csv,
            "source_date_requirements.csv": source_csv,
            "announcement_timestamp_requirements.csv": announcement_csv,
            "unresolved_gates.csv": gates_csv,
            "coverage_summary.json": json.dumps(
                self.summary(),
                indent=2,
                sort_keys=True,
            ) + "\n",
            "acquisition_import_plan.json": json.dumps(
                acquisition_plan,
                indent=2,
                sort_keys=True,
            ) + "\n",
        }


def _session_index(
    sessions: Iterable[XNYSSession],
) -> tuple[tuple[XNYSSession, ...], dict[str, int]]:
    ordered = tuple(sorted(sessions, key=lambda item: item.session_date))
    dates = [item.session_date for item in ordered]
    if len(set(dates)) != len(dates):
        raise ValueError("duplicate XNYS session date")
    return ordered, {day: index for index, day in enumerate(dates)}


def _event_plan(
    event: HistoricalFirstTradeEvent,
    sessions: tuple[XNYSSession, ...],
    index: dict[str, int],
) -> tuple[EventCoveragePlan, UnresolvedCoverageGate | None]:
    if event.first_trade_date not in index:
        return (
            EventCoveragePlan(
                event_id=event.event_id,
                symbol=event.symbol,
                event_session_date=event.first_trade_date,
                baseline_session_dates=(),
                skipped_early_close_dates=(),
            ),
            UnresolvedCoverageGate(
                gate=CoverageGate.BASELINE_CALENDAR,
                key=event.event_id,
                event_id=event.event_id,
                symbol=event.symbol,
                session_date=event.first_trade_date,
                detail="EVENT_SESSION_NOT_IN_SUPPLIED_XNYS_CALENDAR",
            ),
        )

    event_index = index[event.first_trade_date]
    baseline: list[str] = []
    skipped: list[str] = []
    cursor = event_index - 1
    while cursor >= 0 and len(baseline) < BASELINE_SESSIONS:
        session = sessions[cursor]
        if session.is_early_close and not session.supported_for_baseline:
            skipped.append(session.session_date)
        elif session.supported_for_baseline:
            baseline.append(session.session_date)
        cursor -= 1

    baseline.reverse()
    skipped.sort()
    gate = None
    if len(baseline) < BASELINE_SESSIONS:
        gate = UnresolvedCoverageGate(
            gate=CoverageGate.BASELINE_CALENDAR,
            key=event.event_id,
            event_id=event.event_id,
            symbol=event.symbol,
            session_date=event.first_trade_date,
            detail=(
                f"ONLY_{len(baseline)}_OF_{BASELINE_SESSIONS}_"
                "SUPPORTED_PRIOR_SESSIONS_AVAILABLE"
            ),
        )
    return (
        EventCoveragePlan(
            event_id=event.event_id,
            symbol=event.symbol,
            event_session_date=event.first_trade_date,
            baseline_session_dates=tuple(baseline),
            skipped_early_close_dates=tuple(skipped),
        ),
        gate,
    )


def build_coverage_plan(
    events: Iterable[HistoricalFirstTradeEvent],
    *,
    xnys_sessions: Iterable[XNYSSession],
    evidence: CoverageEvidence = CoverageEvidence(),
    source_families: tuple[MarketSourceFamily, ...] = (
        MarketSourceFamily.TAQ_MASTER,
        MarketSourceFamily.TAQ_TRADES_QUOTES,
        MarketSourceFamily.OPTIONS,
        MarketSourceFamily.CONDITIONAL_ITCH,
    ),
) -> CoveragePlan:
    event_tuple = tuple(sorted(events, key=lambda item: item.event_id))
    if not event_tuple:
        raise ValueError("coverage planner requires at least one event")
    if len({item.event_id for item in event_tuple}) != len(event_tuple):
        raise ValueError("duplicate event_id in coverage corpus")

    sessions, session_index = _session_index(xnys_sessions)
    event_plans: list[EventCoveragePlan] = []
    unresolved: list[UnresolvedCoverageGate] = []
    symbol_events: dict[tuple[str, str], set[str]] = {}

    for event in event_tuple:
        plan, calendar_gate = _event_plan(
            event,
            sessions,
            session_index,
        )
        event_plans.append(plan)
        if calendar_gate is not None:
            unresolved.append(calendar_gate)

        for day in plan.baseline_session_dates + (
            plan.event_session_date,
        ):
            symbol_events.setdefault(
                (event.symbol, day),
                set(),
            ).add(event.event_id)

    symbol_dates = tuple(
        SymbolDateRequirement(
            symbol=symbol,
            session_date=day,
            event_ids=tuple(sorted(event_ids)),
        )
        for (symbol, day), event_ids in sorted(symbol_events.items())
    )
    source_dates = tuple(
        SourceDateRequirement(family, day)
        for family in source_families
        for day in sorted({
            item.session_date for item in symbol_dates
        })
    )
    announcement_event_ids = tuple(
        item.event_id for item in event_tuple
    )
    control_dates = tuple(sorted({
        item.first_trade_date for item in event_tuple
    }))

    for event in event_tuple:
        if event.event_id not in evidence.exact_announcement_event_ids:
            unresolved.append(UnresolvedCoverageGate(
                gate=CoverageGate.EXACT_ANNOUNCEMENT,
                key=event.event_id,
                event_id=event.event_id,
                symbol=event.symbol,
                session_date=event.first_trade_date,
                detail="MISSING_EXACT_FIRST_PUBLIC_ANNOUNCEMENT_TIMESTAMP",
            ))

    for requirement in source_dates:
        if requirement.key not in evidence.market_source_dates:
            unresolved.append(UnresolvedCoverageGate(
                gate=CoverageGate.MARKET_FILES,
                key=(
                    requirement.source_family.value
                    + ":"
                    + requirement.session_date
                ),
                session_date=requirement.session_date,
                source_family=requirement.source_family,
                detail="MISSING_AUTHORIZED_OR_PUBLIC_MARKET_SOURCE_DATE",
            ))

    for requirement in symbol_dates:
        if requirement.key not in evidence.listing_symbol_dates:
            unresolved.append(UnresolvedCoverageGate(
                gate=CoverageGate.LISTING_HISTORY,
                key=requirement.symbol + ":" + requirement.session_date,
                symbol=requirement.symbol,
                session_date=requirement.session_date,
                detail="MISSING_HISTORICAL_PRIMARY_LISTING_METADATA",
            ))
        if requirement.key not in evidence.shares_symbol_dates:
            unresolved.append(UnresolvedCoverageGate(
                gate=CoverageGate.SHARES_OUTSTANDING,
                key=requirement.symbol + ":" + requirement.session_date,
                symbol=requirement.symbol,
                session_date=requirement.session_date,
                detail="MISSING_EFFECTIVE_DATED_SHARES_OUTSTANDING",
            ))

    for day in control_dates:
        if day not in evidence.control_dates:
            unresolved.append(UnresolvedCoverageGate(
                gate=CoverageGate.CONTROL_METADATA,
                key=day,
                session_date=day,
                detail="MISSING_SAME_DAY_POINT_IN_TIME_CONTROL_METADATA",
            ))

    return CoveragePlan(
        events=event_tuple,
        event_plans=tuple(event_plans),
        symbol_date_requirements=symbol_dates,
        source_date_requirements=tuple(sorted(
            source_dates,
            key=lambda item: (
                item.source_family.value,
                item.session_date,
            ),
        )),
        announcement_event_ids=announcement_event_ids,
        control_dates=control_dates,
        unresolved_gates=tuple(sorted(
            unresolved,
            key=lambda item: (
                item.gate.value,
                item.key,
                item.event_id or "",
            ),
        )),
        evidence_hash=evidence.proof_hash,
        baseline_sessions=BASELINE_SESSIONS,
        live_use_allowed=False,
    )


__all__ = [
    "BASELINE_SESSIONS",
    "CoverageEvidence",
    "CoverageGate",
    "CoveragePlan",
    "EventCoveragePlan",
    "HistoricalFirstTradeEvent",
    "MarketSourceFamily",
    "SourceDateRequirement",
    "SymbolDateRequirement",
    "UnresolvedCoverageGate",
    "XNYSSession",
    "build_coverage_plan",
]
