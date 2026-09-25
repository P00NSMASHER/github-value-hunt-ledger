"""Effective-dated listing interval evidence for historical G2 resolution.

This module converts conservative, source-backed listing intervals into the
exact daily ListingExchangeEvidence rows consumed by the Step-17 metadata
resolver.

An interval requires two dated public/authorized boundary sources that identify
the same historical primary exchange for the same symbol. The interval is only
used for requirement dates inside those boundaries. Conflicting overlapping
intervals fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import csv
import io
from typing import Iterable

from .metadata_resolver import (
    ListingExchangeEvidence,
    MetadataDataClass,
    MetadataEvidenceRef,
    MetadataSourceKind,
)
from .source_registry import USAGE_SCOPE, canonical_hash


@dataclass(frozen=True)
class ListingIntervalEvidence:
    interval_id: str
    symbol: str
    primary_exchange: str
    valid_from: str
    valid_through: str
    start_evidence_url: str
    end_evidence_url: str
    source_name: str
    data_class: MetadataDataClass = (
        MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL
    )

    def __post_init__(self) -> None:
        if not self.interval_id.strip():
            raise ValueError("interval_id is required")
        symbol = self.symbol.strip().upper()
        exchange = self.primary_exchange.strip().upper()
        if not symbol:
            raise ValueError("symbol is required")
        if not exchange:
            raise ValueError("primary_exchange is required")
        start = date.fromisoformat(self.valid_from)
        end = date.fromisoformat(self.valid_through)
        if start > end:
            raise ValueError("valid_from must be <= valid_through")
        if not self.start_evidence_url.strip():
            raise ValueError("start_evidence_url is required")
        if not self.end_evidence_url.strip():
            raise ValueError("end_evidence_url is required")
        if not self.source_name.strip():
            raise ValueError("source_name is required")
        if (
            self.data_class
            is not MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL
        ):
            raise ValueError(
                "listing interval evidence must be public/authorized historical"
            )
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "primary_exchange", exchange)

    def covers(self, symbol: str, session_date: str) -> bool:
        target = date.fromisoformat(session_date)
        return (
            symbol.strip().upper() == self.symbol
            and date.fromisoformat(self.valid_from)
            <= target
            <= date.fromisoformat(self.valid_through)
        )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "interval_id": self.interval_id,
            "symbol": self.symbol,
            "primary_exchange": self.primary_exchange,
            "valid_from": self.valid_from,
            "valid_through": self.valid_through,
            "start_evidence_url": self.start_evidence_url,
            "end_evidence_url": self.end_evidence_url,
            "source_name": self.source_name,
            "data_class": self.data_class.value,
        })

    def as_daily_evidence(
        self,
        session_date: str,
    ) -> ListingExchangeEvidence:
        if not self.covers(self.symbol, session_date):
            raise ValueError("session date is outside listing interval")
        source = MetadataEvidenceRef(
            evidence_id=self.interval_id,
            source_kind=MetadataSourceKind.OFFICIAL_LISTING_HISTORY,
            source_name=(
                f"{self.source_name}; "
                f"start={self.start_evidence_url}; "
                f"end={self.end_evidence_url}"
            ),
            data_class=self.data_class,
        )
        return ListingExchangeEvidence(
            symbol=self.symbol,
            session_date=session_date,
            primary_exchange=self.primary_exchange,
            evidence=source,
        )


def parse_listing_interval_csv(
    text: str,
) -> tuple[ListingIntervalEvidence, ...]:
    expected = (
        "interval_id",
        "symbol",
        "primary_exchange",
        "valid_from",
        "valid_through",
        "start_evidence_url",
        "end_evidence_url",
        "source_name",
        "data_class",
    )
    reader = csv.DictReader(io.StringIO(text))
    if tuple(reader.fieldnames or ()) != expected:
        raise ValueError("listing interval CSV has unexpected headers")

    result = []
    for line_number, row in enumerate(reader, start=2):
        if None in row:
            raise ValueError(
                f"listing interval CSV line {line_number} has extra columns"
            )
        try:
            data_class = MetadataDataClass(row["data_class"])
        except ValueError as exc:
            raise ValueError(
                f"invalid data_class at line {line_number}"
            ) from exc
        result.append(ListingIntervalEvidence(
            interval_id=row["interval_id"],
            symbol=row["symbol"],
            primary_exchange=row["primary_exchange"],
            valid_from=row["valid_from"],
            valid_through=row["valid_through"],
            start_evidence_url=row["start_evidence_url"],
            end_evidence_url=row["end_evidence_url"],
            source_name=row["source_name"],
            data_class=data_class,
        ))

    if not result:
        raise ValueError("listing interval CSV is empty")
    return tuple(result)


@dataclass(frozen=True)
class ListingIntervalExpansion:
    resolved: tuple[ListingExchangeEvidence, ...]
    unresolved: tuple[tuple[str, str], ...]
    interval_hashes: tuple[str, ...]
    live_use_allowed: bool = False

    def __post_init__(self) -> None:
        if self.live_use_allowed is not False:
            raise ValueError("listing interval expansion cannot enable live use")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "resolved_hashes": sorted(
                item.proof_hash for item in self.resolved
            ),
            "unresolved": [
                [symbol, day] for symbol, day in self.unresolved
            ],
            "interval_hashes": list(self.interval_hashes),
            "live_use_allowed": False,
        })


parse_listing_intervals_csv = parse_listing_interval_csv

def expand_listing_intervals(
    requirements: Iterable[tuple[str, str]],
    intervals: Iterable[ListingIntervalEvidence],
) -> ListingIntervalExpansion:
    interval_tuple = tuple(intervals)
    seen_interval_ids: dict[str, str] = {}
    for interval in interval_tuple:
        prior = seen_interval_ids.get(interval.interval_id)
        if prior is not None and prior != interval.proof_hash:
            raise ValueError(
                "same listing interval_id cannot identify different evidence"
            )
        seen_interval_ids[interval.interval_id] = interval.proof_hash

    resolved: list[ListingExchangeEvidence] = []
    unresolved: list[tuple[str, str]] = []

    normalized_requirements = sorted({
        (symbol.strip().upper(), date.fromisoformat(day).isoformat())
        for symbol, day in requirements
    })

    for symbol, day in normalized_requirements:
        covering = tuple(
            interval
            for interval in interval_tuple
            if interval.covers(symbol, day)
        )
        if not covering:
            unresolved.append((symbol, day))
            continue

        exchanges = {
            interval.primary_exchange for interval in covering
        }
        if len(exchanges) != 1:
            raise ValueError(
                f"conflicting listing intervals for {symbol} on {day}"
            )

        # Multiple agreeing intervals are permitted, but choose the most
        # specific deterministically so daily rows have stable provenance.
        chosen = sorted(
            covering,
            key=lambda item: (
                (
                    date.fromisoformat(item.valid_through)
                    - date.fromisoformat(item.valid_from)
                ).days,
                item.interval_id,
            ),
        )[0]
        resolved.append(chosen.as_daily_evidence(day))

    return ListingIntervalExpansion(
        resolved=tuple(resolved),
        unresolved=tuple(unresolved),
        interval_hashes=tuple(sorted(
            interval.proof_hash for interval in interval_tuple
        )),
        live_use_allowed=False,
    )


__all__ = [
    "ListingIntervalEvidence",
    "ListingIntervalExpansion",
    "expand_listing_intervals",
    "parse_listing_intervals_csv",
    "parse_listing_interval_csv",
]
