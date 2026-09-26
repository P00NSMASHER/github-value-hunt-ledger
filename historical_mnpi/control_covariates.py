"""Fail-closed G4 point-in-time control-universe builder.

The historical replication repository contains a retrospective SampleFirms file,
but the real-corpus control gate requires same-day point-in-time control evidence
with complete pre-event covariates. This module defines the external input
contract and converts only fully admissible inputs into ControlUniverseEvidence.

It never treats retrospective sample membership as point-in-time evidence and it
never fills or imputes missing covariates.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
import math
from typing import Iterable

from .metadata_resolver import (
    ControlUniverseEvidence,
    MetadataDataClass,
    MetadataEvidenceRef,
    MetadataSourceKind,
)
from .source_registry import USAGE_SCOPE, canonical_hash


class ControlSourceFamily(str, Enum):
    CRSP = "CRSP"
    IBES = "IBES"
    TAQ = "TAQ"
    RAVENPACK = "RAVENPACK"
    MARKIT = "MARKIT"
    OPTIONMETRICS = "OPTIONMETRICS"
    THOMSON_REUTERS_13F = "THOMSON_REUTERS_13F"


REQUIRED_SOURCE_FAMILIES = tuple(item.value for item in ControlSourceFamily)

REQUIRED_VARIABLE_ANCHORS = (
    "lnMCAP",
    "Beta_SPY",
    "invPRC",
    "lnnumest",
    "ln_Story_Count_Relevant",
    "DCBS",
    "IO",
)

CONTRACT_VERSION = "g4-point-in-time-v1"


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


def _require_historical(data_class: MetadataDataClass) -> None:
    if data_class is not MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL:
        raise ValueError(
            "control inputs must be public/authorized historical"
        )


def _availability_day(timestamp: str) -> date:
    return _utc(timestamp).date()


@dataclass(frozen=True)
class PointInTimeControlMembership:
    control_date: str
    universe_id: str
    symbols: tuple[str, ...]
    availability_timestamp: str
    evidence_id: str
    source_name: str
    data_class: MetadataDataClass = (
        MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL
    )
    source_kind: MetadataSourceKind = (
        MetadataSourceKind.POINT_IN_TIME_CONTROL_UNIVERSE
    )

    def __post_init__(self) -> None:
        target = date.fromisoformat(self.control_date)
        if not self.universe_id.strip():
            raise ValueError("universe_id is required")
        symbols = tuple(sorted({
            item.strip().upper()
            for item in self.symbols
            if item.strip()
        }))
        if not symbols:
            raise ValueError("point-in-time control membership requires symbols")
        if not self.evidence_id.strip():
            raise ValueError("membership evidence_id is required")
        if not self.source_name.strip():
            raise ValueError("membership source_name is required")
        _require_historical(self.data_class)
        if (
            self.source_kind
            is not MetadataSourceKind.POINT_IN_TIME_CONTROL_UNIVERSE
        ):
            raise ValueError(
                "membership source_kind must be POINT_IN_TIME_CONTROL_UNIVERSE"
            )
        _aware_timestamp(
            "membership availability_timestamp",
            self.availability_timestamp,
        )
        if _availability_day(self.availability_timestamp) > target:
            raise ValueError(
                "membership evidence must be available by control_date"
            )
        object.__setattr__(self, "symbols", symbols)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "contract_version": CONTRACT_VERSION,
            "scope": USAGE_SCOPE,
            "control_date": self.control_date,
            "universe_id": self.universe_id,
            "symbols": list(self.symbols),
            "availability_utc": _utc(
                self.availability_timestamp
            ).isoformat(),
            "evidence_id": self.evidence_id,
            "source_name": self.source_name,
            "data_class": self.data_class.value,
            "source_kind": self.source_kind.value,
        })


@dataclass(frozen=True)
class ControlSourceCoverageReceipt:
    control_date: str
    universe_id: str
    source_family: ControlSourceFamily
    availability_timestamp: str
    complete_for_universe: bool
    evidence_id: str
    source_name: str
    data_class: MetadataDataClass = (
        MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL
    )

    def __post_init__(self) -> None:
        target = date.fromisoformat(self.control_date)
        if not self.universe_id.strip():
            raise ValueError("universe_id is required")
        if type(self.complete_for_universe) is not bool:
            raise ValueError("complete_for_universe must be boolean")
        if not self.evidence_id.strip():
            raise ValueError("coverage evidence_id is required")
        if not self.source_name.strip():
            raise ValueError("coverage source_name is required")
        _require_historical(self.data_class)
        _aware_timestamp(
            "coverage availability_timestamp",
            self.availability_timestamp,
        )
        if _availability_day(self.availability_timestamp) > target:
            raise ValueError(
                "source-family coverage must be available by control_date"
            )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "contract_version": CONTRACT_VERSION,
            "scope": USAGE_SCOPE,
            "control_date": self.control_date,
            "universe_id": self.universe_id,
            "source_family": self.source_family.value,
            "availability_utc": _utc(
                self.availability_timestamp
            ).isoformat(),
            "complete_for_universe": self.complete_for_universe,
            "evidence_id": self.evidence_id,
            "source_name": self.source_name,
            "data_class": self.data_class.value,
        })


@dataclass(frozen=True)
class ControlCovariateFact:
    control_date: str
    symbol: str
    covariate_name: str
    value: str
    effective_date: str
    availability_timestamp: str
    source_family: ControlSourceFamily
    evidence_id: str
    source_name: str
    data_class: MetadataDataClass = (
        MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL
    )

    def __post_init__(self) -> None:
        target = date.fromisoformat(self.control_date)
        effective = date.fromisoformat(self.effective_date)
        symbol = self.symbol.strip().upper()
        if not symbol:
            raise ValueError("covariate fact requires symbol")
        if self.covariate_name not in REQUIRED_VARIABLE_ANCHORS:
            raise ValueError("unsupported control covariate_name")
        try:
            numeric = float(self.value)
        except ValueError as exc:
            raise ValueError("control covariate value must be numeric") from exc
        if not math.isfinite(numeric):
            raise ValueError("control covariate value must be finite")
        if effective > target:
            raise ValueError("covariate effective_date exceeds control_date")
        _aware_timestamp(
            "covariate availability_timestamp",
            self.availability_timestamp,
        )
        if _availability_day(self.availability_timestamp) > target:
            raise ValueError(
                "covariate evidence must be available by control_date"
            )
        if not self.evidence_id.strip():
            raise ValueError("covariate evidence_id is required")
        if not self.source_name.strip():
            raise ValueError("covariate source_name is required")
        _require_historical(self.data_class)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "value", format(numeric, ".17g"))

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "contract_version": CONTRACT_VERSION,
            "scope": USAGE_SCOPE,
            "control_date": self.control_date,
            "symbol": self.symbol,
            "covariate_name": self.covariate_name,
            "value": self.value,
            "effective_date": self.effective_date,
            "availability_utc": _utc(
                self.availability_timestamp
            ).isoformat(),
            "source_family": self.source_family.value,
            "evidence_id": self.evidence_id,
            "source_name": self.source_name,
            "data_class": self.data_class.value,
        })


@dataclass(frozen=True)
class ControlUniverseBuildResult:
    control_date: str
    universe_id: str
    evidence: ControlUniverseEvidence | None
    missing_source_families: tuple[str, ...]
    incomplete_source_families: tuple[str, ...]
    missing_covariates: tuple[tuple[str, str], ...]
    conflicting_covariates: tuple[tuple[str, str], ...]
    input_proof_hashes: tuple[str, ...]
    live_use_allowed: bool = False

    def __post_init__(self) -> None:
        if self.live_use_allowed is not False:
            raise ValueError("control builder cannot enable live use")

    @property
    def resolved(self) -> bool:
        return self.evidence is not None

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "contract_version": CONTRACT_VERSION,
            "scope": USAGE_SCOPE,
            "control_date": self.control_date,
            "universe_id": self.universe_id,
            "evidence_hash": (
                self.evidence.proof_hash
                if self.evidence is not None
                else None
            ),
            "missing_source_families": list(
                self.missing_source_families
            ),
            "incomplete_source_families": list(
                self.incomplete_source_families
            ),
            "missing_covariates": [
                list(item) for item in self.missing_covariates
            ],
            "conflicting_covariates": [
                list(item) for item in self.conflicting_covariates
            ],
            "input_proof_hashes": list(self.input_proof_hashes),
            "live_use_allowed": False,
        })


def build_point_in_time_control_universe(
    membership: PointInTimeControlMembership,
    covariate_facts: Iterable[ControlCovariateFact],
    source_coverage: Iterable[ControlSourceCoverageReceipt],
) -> ControlUniverseBuildResult:
    target = membership.control_date
    universe_id = membership.universe_id

    facts = tuple(
        item
        for item in covariate_facts
        if item.control_date == target
        and item.symbol in membership.symbols
    )
    coverage = tuple(
        item
        for item in source_coverage
        if item.control_date == target
        and item.universe_id == universe_id
    )

    coverage_by_family: dict[str, list[ControlSourceCoverageReceipt]] = {}
    for item in coverage:
        coverage_by_family.setdefault(
            item.source_family.value,
            [],
        ).append(item)

    missing_families = tuple(sorted(
        family
        for family in REQUIRED_SOURCE_FAMILIES
        if family not in coverage_by_family
    ))
    incomplete_families = tuple(sorted(
        family
        for family, rows in coverage_by_family.items()
        if family in REQUIRED_SOURCE_FAMILIES
        and not any(row.complete_for_universe for row in rows)
    ))

    missing_covariates: list[tuple[str, str]] = []
    conflicting_covariates: list[tuple[str, str]] = []

    for symbol in membership.symbols:
        for name in REQUIRED_VARIABLE_ANCHORS:
            candidates = [
                item
                for item in facts
                if item.symbol == symbol
                and item.covariate_name == name
            ]
            if not candidates:
                missing_covariates.append((symbol, name))
                continue
            latest_date = max(item.effective_date for item in candidates)
            latest = [
                item
                for item in candidates
                if item.effective_date == latest_date
            ]
            values = {item.value for item in latest}
            if len(values) != 1:
                conflicting_covariates.append((symbol, name))

    input_hashes = tuple(sorted({
        membership.proof_hash,
        *(item.proof_hash for item in facts),
        *(item.proof_hash for item in coverage),
    }))

    if (
        missing_families
        or incomplete_families
        or missing_covariates
        or conflicting_covariates
    ):
        return ControlUniverseBuildResult(
            control_date=target,
            universe_id=universe_id,
            evidence=None,
            missing_source_families=missing_families,
            incomplete_source_families=incomplete_families,
            missing_covariates=tuple(sorted(missing_covariates)),
            conflicting_covariates=tuple(
                sorted(conflicting_covariates)
            ),
            input_proof_hashes=input_hashes,
        )

    provenance_hash = canonical_hash({
        "membership_hash": membership.proof_hash,
        "fact_hashes": sorted(item.proof_hash for item in facts),
        "coverage_hashes": sorted(
            item.proof_hash for item in coverage
        ),
    })
    ref = MetadataEvidenceRef(
        evidence_id=(
            f"controls:{target}:{provenance_hash[:20]}"
        ),
        source_kind=MetadataSourceKind.POINT_IN_TIME_CONTROL_UNIVERSE,
        source_name=(
            "G4 point-in-time control universe built from "
            f"membership={membership.evidence_id}; "
            f"contract={CONTRACT_VERSION}; "
            f"provenance_sha256={provenance_hash}"
        ),
        data_class=MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL,
    )
    evidence = ControlUniverseEvidence(
        control_date=target,
        universe_id=universe_id,
        symbols=membership.symbols,
        availability_timestamp=membership.availability_timestamp,
        complete_pre_event_covariates=True,
        evidence=ref,
    )
    return ControlUniverseBuildResult(
        control_date=target,
        universe_id=universe_id,
        evidence=evidence,
        missing_source_families=(),
        incomplete_source_families=(),
        missing_covariates=(),
        conflicting_covariates=(),
        input_proof_hashes=input_hashes,
    )


__all__ = [
    "CONTRACT_VERSION",
    "ControlCovariateFact",
    "ControlSourceCoverageReceipt",
    "ControlSourceFamily",
    "ControlUniverseBuildResult",
    "PointInTimeControlMembership",
    "REQUIRED_SOURCE_FAMILIES",
    "REQUIRED_VARIABLE_ANCHORS",
    "build_point_in_time_control_universe",
]
