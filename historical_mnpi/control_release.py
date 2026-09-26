"""Atomic G4 point-in-time control release gate.

This module connects the strict external control-input contract to the existing
control-universe builder and metadata importer. It deliberately produces no
partial control_metadata.csv payload: every expected control date must resolve
before a releasable CSV exists.
"""
from __future__ import annotations

from dataclasses import dataclass
import csv
import io
from typing import Iterable, Mapping

from .control_covariates import (
    ControlUniverseBuildResult,
    build_point_in_time_control_universe,
)
from .control_external_import import (
    ControlExternalInputImport,
    import_control_external_inputs,
)
from .metadata_resolver import ControlUniverseEvidence
from .real_corpus_import import CONTROL_HEADERS
from .source_registry import USAGE_SCOPE, canonical_hash


RELEASE_CONTRACT_VERSION = "g4-control-release-v1"


def control_dates_from_events_csv(events_csv: str) -> tuple[str, ...]:
    reader = csv.DictReader(io.StringIO(events_csv))
    if reader.fieldnames is None:
        raise ValueError("events.csv requires a header")
    if "first_trade_date" not in reader.fieldnames:
        raise ValueError("events.csv requires first_trade_date")
    dates = []
    for row in reader:
        day = (row.get("first_trade_date") or "").strip()
        if not day:
            raise ValueError("events.csv contains empty first_trade_date")
        dates.append(day)
    return tuple(sorted(set(dates)))


def _serialize_control_metadata(
    evidence: Iterable[ControlUniverseEvidence],
) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CONTROL_HEADERS)
    for item in sorted(evidence, key=lambda value: value.control_date):
        writer.writerow((
            item.control_date,
            item.universe_id,
            "|".join(item.symbols),
            item.availability_timestamp or "",
            "true" if item.complete_pre_event_covariates else "false",
            item.evidence.evidence_id,
            item.evidence.source_kind.value,
            item.evidence.source_name,
            item.evidence.data_class.value,
        ))
    return buffer.getvalue()


@dataclass(frozen=True)
class ControlReleaseGateResult:
    expected_control_dates: tuple[str, ...]
    build_results: tuple[ControlUniverseBuildResult, ...]
    evidence: tuple[ControlUniverseEvidence, ...]
    control_metadata_csv: str | None
    rejection_reasons: tuple[str, ...]
    live_use_allowed: bool = False

    def __post_init__(self) -> None:
        if self.live_use_allowed is not False:
            raise ValueError("control release gate cannot enable live use")
        if tuple(sorted(set(self.expected_control_dates))) != (
            self.expected_control_dates
        ):
            raise ValueError(
                "expected_control_dates must be unique and sorted"
            )

    @property
    def ready(self) -> bool:
        return (
            self.control_metadata_csv is not None
            and not self.rejection_reasons
            and len(self.evidence) == len(self.expected_control_dates)
        )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "contract_version": RELEASE_CONTRACT_VERSION,
            "scope": USAGE_SCOPE,
            "expected_control_dates": list(self.expected_control_dates),
            "build_result_hashes": sorted(
                item.proof_hash for item in self.build_results
            ),
            "evidence_hashes": sorted(
                item.proof_hash for item in self.evidence
            ),
            "control_metadata_csv": self.control_metadata_csv,
            "rejection_reasons": list(self.rejection_reasons),
            "live_use_allowed": False,
        })


def build_control_release_gate(
    expected_control_dates: Iterable[str],
    external_inputs: ControlExternalInputImport,
) -> ControlReleaseGateResult:
    raw_expected = tuple(expected_control_dates)
    expected = tuple(sorted(set(raw_expected)))
    if len(expected) != len(raw_expected):
        raise ValueError("expected_control_dates contains duplicates")
    if not expected:
        raise ValueError("expected_control_dates cannot be empty")

    expected_set = set(expected)
    external_dates = {
        *(item.control_date for item in external_inputs.memberships),
        *(item.control_date for item in external_inputs.covariates),
        *(item.control_date for item in external_inputs.source_coverage),
    }
    reasons = [
        f"UNEXPECTED_EXTERNAL_DATE:{day}"
        for day in sorted(external_dates - expected_set)
    ]

    memberships_by_date = {}
    for item in external_inputs.memberships:
        memberships_by_date.setdefault(item.control_date, []).append(item)

    builds = []
    evidence = []
    for day in expected:
        memberships = memberships_by_date.get(day, [])
        if not memberships:
            reasons.append(f"MISSING_MEMBERSHIP:{day}")
            continue
        if len(memberships) != 1:
            reasons.append(f"AMBIGUOUS_MEMBERSHIP:{day}")
            continue

        result = build_point_in_time_control_universe(
            memberships[0],
            external_inputs.covariates,
            external_inputs.source_coverage,
        )
        builds.append(result)
        if not result.resolved:
            reasons.append(f"UNRESOLVED_CONTROL_DATE:{day}")
            continue
        if result.evidence is None:
            raise AssertionError("resolved control build lacks evidence")
        evidence.append(result.evidence)

    evidence_dates = {item.control_date for item in evidence}
    missing_release_dates = expected_set - evidence_dates
    for day in sorted(missing_release_dates):
        marker = f"UNRESOLVED_CONTROL_DATE:{day}"
        if (
            f"MISSING_MEMBERSHIP:{day}" not in reasons
            and f"AMBIGUOUS_MEMBERSHIP:{day}" not in reasons
            and marker not in reasons
        ):
            reasons.append(marker)

    reasons_tuple = tuple(sorted(set(reasons)))
    evidence_tuple = tuple(sorted(
        evidence,
        key=lambda item: item.control_date,
    ))
    release_csv = None
    if not reasons_tuple and len(evidence_tuple) == len(expected):
        release_csv = _serialize_control_metadata(evidence_tuple)

    return ControlReleaseGateResult(
        expected_control_dates=expected,
        build_results=tuple(sorted(
            builds,
            key=lambda item: item.control_date,
        )),
        evidence=evidence_tuple,
        control_metadata_csv=release_csv,
        rejection_reasons=reasons_tuple,
    )


def build_control_release_from_csv(
    events_csv: str,
    external_files: Mapping[str, str],
) -> ControlReleaseGateResult:
    return build_control_release_gate(
        control_dates_from_events_csv(events_csv),
        import_control_external_inputs(external_files),
    )


__all__ = [
    "ControlReleaseGateResult",
    "RELEASE_CONTRACT_VERSION",
    "build_control_release_from_csv",
    "build_control_release_gate",
    "control_dates_from_events_csv",
]
