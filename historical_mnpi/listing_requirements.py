"""Compact real-corpus listing requirement index.

The recovered G2 index stores one row per historical symbol with an explicit
ordered list of required session dates. This module validates and expands that
compact representation into exact (symbol, session_date) observations.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import csv
import io

from .source_registry import USAGE_SCOPE, canonical_hash


SOURCE_REQUIREMENTS_SHA256 = (
    "58e05613603b95b806eedb49ede774fce763f5ca7519487bed66282e4fe0a3fb"
)
EXPECTED_EXPANDED_PAIR_SHA256 = (
    "cb00a9c2983c5ffb0f37ef3aff84ce8bcf328bd56565664e01abe0dfadde64af"
)


@dataclass(frozen=True)
class CompactListingRequirement:
    historical_symbol: str
    requirement_count: int
    first_date: str
    last_date: str
    required_dates: tuple[str, ...]

    def __post_init__(self) -> None:
        symbol = self.historical_symbol.strip().upper()
        if not symbol:
            raise ValueError("historical_symbol is required")
        if self.requirement_count <= 0:
            raise ValueError("requirement_count must be positive")
        parsed = tuple(date.fromisoformat(day).isoformat() for day in self.required_dates)
        if len(parsed) != self.requirement_count:
            raise ValueError("requirement_count does not match required_dates")
        if len(set(parsed)) != len(parsed):
            raise ValueError("required_dates contains duplicates")
        if tuple(sorted(parsed)) != parsed:
            raise ValueError("required_dates must be sorted")
        if parsed[0] != date.fromisoformat(self.first_date).isoformat():
            raise ValueError("first_date does not match required_dates")
        if parsed[-1] != date.fromisoformat(self.last_date).isoformat():
            raise ValueError("last_date does not match required_dates")
        object.__setattr__(self, "historical_symbol", symbol)
        object.__setattr__(self, "required_dates", parsed)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "historical_symbol": self.historical_symbol,
            "requirement_count": self.requirement_count,
            "first_date": self.first_date,
            "last_date": self.last_date,
            "required_dates": list(self.required_dates),
        })


def parse_listing_requirement_index(
    text: str,
) -> tuple[CompactListingRequirement, ...]:
    reader = csv.DictReader(io.StringIO(text))
    expected = (
        "historical_symbol",
        "requirement_count",
        "first_date",
        "last_date",
        "required_dates",
    )
    if tuple(reader.fieldnames or ()) != expected:
        raise ValueError("listing requirement index has unexpected headers")

    result = []
    for line_number, row in enumerate(reader, start=2):
        try:
            count = int(row["requirement_count"])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"invalid requirement_count at line {line_number}"
            ) from exc
        dates = tuple(
            value.strip()
            for value in (row["required_dates"] or "").split("|")
            if value.strip()
        )
        result.append(CompactListingRequirement(
            historical_symbol=row["historical_symbol"] or "",
            requirement_count=count,
            first_date=row["first_date"] or "",
            last_date=row["last_date"] or "",
            required_dates=dates,
        ))

    if not result:
        raise ValueError("listing requirement index is empty")
    symbols = [item.historical_symbol for item in result]
    if len(set(symbols)) != len(symbols):
        raise ValueError("listing requirement index contains duplicate symbols")
    if tuple(sorted(symbols)) != tuple(symbols):
        raise ValueError("listing requirement index symbols must be sorted")
    return tuple(result)


def expand_listing_requirements(
    rows: tuple[CompactListingRequirement, ...],
) -> tuple[tuple[str, str], ...]:
    result = tuple(
        (row.historical_symbol, session_date)
        for row in rows
        for session_date in row.required_dates
    )
    if len(set(result)) != len(result):
        raise ValueError("expanded listing requirements contain duplicates")
    return result


def expanded_pair_sha256(
    rows: tuple[CompactListingRequirement, ...],
) -> str:
    import hashlib

    payload = "".join(
        f"{symbol},{session_date}\n"
        for symbol, session_date in sorted(
            expand_listing_requirements(rows)
        )
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def listing_requirement_index_hash(
    rows: tuple[CompactListingRequirement, ...],
) -> str:
    return canonical_hash({
        "schema": 1,
        "scope": USAGE_SCOPE,
        "row_hashes": [row.proof_hash for row in rows],
    })


__all__ = [
    "CompactListingRequirement",
    "EXPECTED_EXPANDED_PAIR_SHA256",
    "SOURCE_REQUIREMENTS_SHA256",
    "expand_listing_requirements",
    "expanded_pair_sha256",
    "listing_requirement_index_hash",
    "parse_listing_requirement_index",
]
