"""CSV ingestion helpers for LeaseRecovery."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path
from typing import Mapping

from .contract_billing import UsageRecord


DEFAULT_AREA_COLUMNS = {
    "charge_id": "Charge_ID",
    "area_sqft": "Area_SqFt",
}


def _read_rows(path: str | Path) -> tuple[Path, str, list[dict[str, str]]]:
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


def _required(row: Mapping[str, str], column: str, *, row_number: int) -> str:
    if column not in row:
        raise ValueError(f"missing required CSV column {column!r}")
    value = row.get(column)
    if value is None or not str(value).strip():
        raise ValueError(f"row {row_number}: {column} is required")
    return str(value).strip()


def load_lease_area_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_AREA_COLUMNS,
) -> tuple[UsageRecord, ...]:
    """Load independent billable-area/allocation evidence."""
    source, digest, rows = _read_rows(path)
    result: list[UsageRecord] = []
    for row_number, row in enumerate(rows, start=2):
        raw_area = _required(row, columns["area_sqft"], row_number=row_number)
        try:
            area = Decimal(raw_area.replace(",", ""))
        except InvalidOperation as exc:
            raise ValueError(f"row {row_number}: Area_SqFt must be numeric") from exc
        if area < 0:
            raise ValueError(f"row {row_number}: Area_SqFt must be non-negative")
        result.append(UsageRecord(
            charge_id=_required(row, columns["charge_id"], row_number=row_number),
            units=str(area),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={
                "source_file": source.name,
                "row_number": row_number,
                "quantity_kind": "area_sqft",
            },
        ))
    return tuple(result)
