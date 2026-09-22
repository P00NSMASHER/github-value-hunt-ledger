"""SaaSRecovery seat/license snapshot ingestion."""
from __future__ import annotations

import csv
from collections import defaultdict
import hashlib
from pathlib import Path

from .contract_billing import UsageRecord


TRUTHY = {"1", "true", "yes", "y", "billable", "active"}
FALSY = {"0", "false", "no", "n", "nonbillable", "inactive"}


def _flag(value: str, *, row_number: int) -> bool:
    text = (value or "").strip().lower()
    if text in TRUTHY:
        return True
    if text in FALSY:
        return False
    raise ValueError(f"row {row_number}: Billable must be boolean-like")


def load_billable_seat_snapshot_csv(
    path: str | Path,
    *,
    verified: bool = False,
    charge_column: str = "Charge_ID",
    seat_column: str = "Seat_ID",
    billable_column: str = "Billable",
) -> tuple[UsageRecord, ...]:
    """Aggregate one seat/license snapshot into billable units per invoice charge.

    Duplicate Seat_ID values within the same Charge_ID fail closed to prevent
    duplicated exports from inflating expected usage.
    """
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
    for required in (charge_column, seat_column, billable_column):
        if required not in reader.fieldnames:
            raise ValueError(f"missing required CSV column {required!r}")

    counts: dict[str, int] = defaultdict(int)
    rows_by_charge: dict[str, list[int]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()

    for row_number, row in enumerate(reader, start=2):
        charge_id = (row.get(charge_column) or "").strip()
        seat_id = (row.get(seat_column) or "").strip()
        if not charge_id:
            raise ValueError(f"row {row_number}: {charge_column} is required")
        if not seat_id:
            raise ValueError(f"row {row_number}: {seat_column} is required")
        key = (charge_id, seat_id)
        if key in seen:
            raise ValueError(
                f"row {row_number}: duplicate seat {seat_id!r} for charge {charge_id!r}"
            )
        seen.add(key)
        rows_by_charge[charge_id].append(row_number)
        if _flag(row.get(billable_column) or "", row_number=row_number):
            counts[charge_id] += 1

    result: list[UsageRecord] = []
    for charge_id in sorted(rows_by_charge):
        result.append(UsageRecord(
            charge_id=charge_id,
            units=str(counts[charge_id]),
            source_hash=digest,
            source_locator=f"file://{source.name}#charge_id={charge_id}",
            verified=verified,
            metadata={
                "source_file": source.name,
                "seat_rows": rows_by_charge[charge_id],
                "billable_seat_count": counts[charge_id],
                "quantity_basis": "billable_seat_snapshot",
            },
        ))
    return tuple(result)
