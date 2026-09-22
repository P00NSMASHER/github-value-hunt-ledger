"""CSV ingestion for DutyRecovery entry lines and reviewed assessments."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
from pathlib import Path
from typing import Mapping

from .duty import DutyAssessment, DutyEntryLine


DEFAULT_ENTRY_COLUMNS = {
    "entry_line_id": "Entry_Line_ID",
    "entry_id": "Entry_ID",
    "importer_id": "Importer_ID",
    "broker_id": "Broker_ID",
    "import_date": "Import_Date",
    "hts_code": "HTS_Code",
    "origin_country": "Origin_Country",
    "actual_total": "Actual_Duty_And_Fees",
}

DEFAULT_ASSESSMENT_COLUMNS = {
    "assessment_id": "Assessment_ID",
    "entry_line_id": "Entry_Line_ID",
    "import_date": "Import_Date",
    "hts_code": "HTS_Code",
    "origin_country": "Origin_Country",
    "base_duty": "Expected_Base_Duty",
    "additional_duty": "Expected_Additional_Duty",
    "mpf": "Expected_MPF",
    "hmf": "Expected_HMF",
    "other": "Expected_Other",
    "schedule_snapshot_date": "Schedule_Snapshot_Date",
    "professional_reviewer_id": "Professional_Reviewer_ID",
}


def _money_to_cents(value: str, *, field: str) -> int:
    text = (value or "").strip().replace("$", "").replace(",", "")
    if not text:
        return 0
    try:
        amount = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} has invalid money value {value!r}") from exc
    if amount < 0:
        raise ValueError(f"{field} cannot be negative")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _read(path: str | Path) -> tuple[Path, str, list[dict[str, str]]]:
    source = Path(path)
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{source} must be UTF-8 CSV") from exc
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise ValueError(f"{source} has no CSV header")
    return source, digest, list(reader)


def _required(row: Mapping[str, str], column: str, row_number: int) -> str:
    if column not in row:
        raise ValueError(f"missing required CSV column {column!r}")
    value = row.get(column)
    if value is None or not str(value).strip():
        raise ValueError(f"row {row_number}: {column} is required")
    return str(value).strip()


def _optional(row: Mapping[str, str], column: str | None) -> str | None:
    if not column:
        return None
    value = row.get(column)
    if value is None or not str(value).strip():
        return None
    return str(value).strip()


def load_duty_entries_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_ENTRY_COLUMNS,
) -> tuple[DutyEntryLine, ...]:
    source, digest, rows = _read(path)
    result: list[DutyEntryLine] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(DutyEntryLine(
            entry_line_id=_required(row, columns["entry_line_id"], row_number),
            entry_id=_required(row, columns["entry_id"], row_number),
            importer_id=_required(row, columns["importer_id"], row_number),
            broker_id=_required(row, columns["broker_id"], row_number),
            import_date=_required(row, columns["import_date"], row_number),
            hts_code=_required(row, columns["hts_code"], row_number),
            origin_country=_required(row, columns["origin_country"], row_number),
            actual_total_cents=_money_to_cents(
                _required(row, columns["actual_total"], row_number),
                field=columns["actual_total"],
            ),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_duty_assessments_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_ASSESSMENT_COLUMNS,
) -> tuple[DutyAssessment, ...]:
    source, digest, rows = _read(path)
    result: list[DutyAssessment] = []
    for row_number, row in enumerate(rows, start=2):
        reviewer = _optional(row, columns.get("professional_reviewer_id"))
        result.append(DutyAssessment(
            assessment_id=_required(row, columns["assessment_id"], row_number),
            entry_line_id=_required(row, columns["entry_line_id"], row_number),
            import_date=_required(row, columns["import_date"], row_number),
            hts_code=_required(row, columns["hts_code"], row_number),
            origin_country=_required(row, columns["origin_country"], row_number),
            base_duty_cents=_money_to_cents(
                _required(row, columns["base_duty"], row_number),
                field=columns["base_duty"],
            ),
            additional_duty_cents=_money_to_cents(
                _optional(row, columns.get("additional_duty")) or "0",
                field=columns.get("additional_duty", "additional_duty"),
            ),
            mpf_cents=_money_to_cents(
                _optional(row, columns.get("mpf")) or "0",
                field=columns.get("mpf", "mpf"),
            ),
            hmf_cents=_money_to_cents(
                _optional(row, columns.get("hmf")) or "0",
                field=columns.get("hmf", "hmf"),
            ),
            other_cents=_money_to_cents(
                _optional(row, columns.get("other")) or "0",
                field=columns.get("other", "other"),
            ),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            schedule_snapshot_date=_optional(
                row, columns.get("schedule_snapshot_date")
            ),
            professional_reviewer_id=reviewer,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)
