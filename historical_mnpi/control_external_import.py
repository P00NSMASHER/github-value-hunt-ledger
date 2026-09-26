"""Strict importer for external G4 point-in-time control inputs.

The committed real-corpus packet defines what must be acquired, but licensed or
otherwise authorized source rows must remain external until supplied. This module
accepts only the three builder input tables and converts them into the validated
objects consumed by control_covariates.py.

It does not infer availability timestamps, fill missing covariates, accept
retrospective SampleFirms membership, or enable live use.
"""
from __future__ import annotations

from dataclasses import dataclass
import csv
import io
from typing import Mapping

from .control_covariates import (
    ControlCovariateFact,
    ControlSourceCoverageReceipt,
    ControlSourceFamily,
    PointInTimeControlMembership,
)
from .metadata_resolver import MetadataDataClass, MetadataSourceKind
from .source_registry import canonical_hash, USAGE_SCOPE


MEMBERSHIP_HEADERS = (
    "control_date",
    "universe_id",
    "symbols",
    "availability_timestamp",
    "evidence_id",
    "source_name",
    "source_kind",
    "data_class",
)

COVARIATE_HEADERS = (
    "control_date",
    "symbol",
    "covariate_name",
    "value",
    "effective_date",
    "availability_timestamp",
    "source_family",
    "evidence_id",
    "source_name",
    "data_class",
)

SOURCE_COVERAGE_HEADERS = (
    "control_date",
    "universe_id",
    "source_family",
    "availability_timestamp",
    "complete_for_universe",
    "evidence_id",
    "source_name",
    "data_class",
)

EXPECTED_FILES = {
    "membership.csv": MEMBERSHIP_HEADERS,
    "covariates.csv": COVARIATE_HEADERS,
    "source_coverage.csv": SOURCE_COVERAGE_HEADERS,
}


def _parse_csv(name: str, text: str, headers: tuple[str, ...]) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    if tuple(reader.fieldnames or ()) != headers:
        raise ValueError(
            f"{name} headers must be exactly: " + ",".join(headers)
        )
    rows = []
    for index, row in enumerate(reader, start=2):
        if None in row:
            raise ValueError(f"{name} row {index} has extra columns")
        rows.append({
            key: (value if value is not None else "")
            for key, value in row.items()
        })
    return rows


def _required(name: str, value: str) -> str:
    result = value.strip()
    if not result:
        raise ValueError(f"{name} is required")
    return result


def _historical(value: str) -> MetadataDataClass:
    result = MetadataDataClass(_required("data_class", value))
    if result is not MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL:
        raise ValueError(
            "external control input data_class must be "
            "PUBLIC_OR_AUTHORIZED_HISTORICAL"
        )
    return result


def _strict_bool(name: str, value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"{name} must be exactly true or false")


@dataclass(frozen=True)
class ControlExternalInputImport:
    memberships: tuple[PointInTimeControlMembership, ...]
    covariates: tuple[ControlCovariateFact, ...]
    source_coverage: tuple[ControlSourceCoverageReceipt, ...]
    live_use_allowed: bool = False

    def __post_init__(self) -> None:
        if self.live_use_allowed is not False:
            raise ValueError("external control import cannot enable live use")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "membership_hashes": sorted(
                item.proof_hash for item in self.memberships
            ),
            "covariate_hashes": sorted(
                item.proof_hash for item in self.covariates
            ),
            "source_coverage_hashes": sorted(
                item.proof_hash for item in self.source_coverage
            ),
            "live_use_allowed": False,
        })

    def counts(self) -> dict[str, int | str | bool]:
        return {
            "membership_rows": len(self.memberships),
            "covariate_rows": len(self.covariates),
            "source_coverage_rows": len(self.source_coverage),
            "import_hash": self.proof_hash,
            "live_use_allowed": False,
        }


def import_control_external_inputs(
    files: Mapping[str, str],
) -> ControlExternalInputImport:
    expected = set(EXPECTED_FILES)
    actual = set(files)
    extra = actual - expected
    if extra:
        raise ValueError(
            "unexpected control input files: " + ", ".join(sorted(extra))
        )
    missing = expected - actual
    if missing:
        raise ValueError(
            "missing control input files: " + ", ".join(sorted(missing))
        )

    membership_rows = _parse_csv(
        "membership.csv",
        files["membership.csv"],
        MEMBERSHIP_HEADERS,
    )
    covariate_rows = _parse_csv(
        "covariates.csv",
        files["covariates.csv"],
        COVARIATE_HEADERS,
    )
    coverage_rows = _parse_csv(
        "source_coverage.csv",
        files["source_coverage.csv"],
        SOURCE_COVERAGE_HEADERS,
    )

    memberships = []
    for row in membership_rows:
        kind = MetadataSourceKind(
            _required("source_kind", row["source_kind"])
        )
        if kind is not MetadataSourceKind.POINT_IN_TIME_CONTROL_UNIVERSE:
            raise ValueError(
                "membership source_kind must be "
                "POINT_IN_TIME_CONTROL_UNIVERSE"
            )
        memberships.append(PointInTimeControlMembership(
            control_date=_required("control_date", row["control_date"]),
            universe_id=_required("universe_id", row["universe_id"]),
            symbols=tuple(
                item.strip()
                for item in row["symbols"].split("|")
                if item.strip()
            ),
            availability_timestamp=_required(
                "availability_timestamp",
                row["availability_timestamp"],
            ),
            evidence_id=_required("evidence_id", row["evidence_id"]),
            source_name=_required("source_name", row["source_name"]),
            data_class=_historical(row["data_class"]),
            source_kind=kind,
        ))

    covariates = tuple(
        ControlCovariateFact(
            control_date=_required("control_date", row["control_date"]),
            symbol=_required("symbol", row["symbol"]),
            covariate_name=_required(
                "covariate_name",
                row["covariate_name"],
            ),
            value=_required("value", row["value"]),
            effective_date=_required(
                "effective_date",
                row["effective_date"],
            ),
            availability_timestamp=_required(
                "availability_timestamp",
                row["availability_timestamp"],
            ),
            source_family=ControlSourceFamily(
                _required("source_family", row["source_family"])
            ),
            evidence_id=_required("evidence_id", row["evidence_id"]),
            source_name=_required("source_name", row["source_name"]),
            data_class=_historical(row["data_class"]),
        )
        for row in covariate_rows
    )

    source_coverage = tuple(
        ControlSourceCoverageReceipt(
            control_date=_required("control_date", row["control_date"]),
            universe_id=_required("universe_id", row["universe_id"]),
            source_family=ControlSourceFamily(
                _required("source_family", row["source_family"])
            ),
            availability_timestamp=_required(
                "availability_timestamp",
                row["availability_timestamp"],
            ),
            complete_for_universe=_strict_bool(
                "complete_for_universe",
                row["complete_for_universe"],
            ),
            evidence_id=_required("evidence_id", row["evidence_id"]),
            source_name=_required("source_name", row["source_name"]),
            data_class=_historical(row["data_class"]),
        )
        for row in coverage_rows
    )

    return ControlExternalInputImport(
        memberships=tuple(memberships),
        covariates=covariates,
        source_coverage=source_coverage,
    )


__all__ = [
    "COVARIATE_HEADERS",
    "ControlExternalInputImport",
    "EXPECTED_FILES",
    "MEMBERSHIP_HEADERS",
    "SOURCE_COVERAGE_HEADERS",
    "import_control_external_inputs",
]
