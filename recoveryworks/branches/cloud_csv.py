"""CloudRecovery raw metering aggregation."""
from __future__ import annotations

import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path

from .contract_billing import UsageRecord


def load_cloud_meter_csv(
    path: str | Path,
    *,
    verified: bool = False,
    charge_column: str = "Charge_ID",
    record_column: str = "Meter_Record_ID",
    units_column: str = "Usage_Units",
) -> tuple[UsageRecord, ...]:
    """Aggregate raw cloud meter records into independent units per charge.

    Duplicate Meter_Record_ID values within a Charge_ID fail closed instead of
    double counting usage.
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
    for required in (charge_column, record_column, units_column):
        if required not in reader.fieldnames:
            raise ValueError(f"missing required CSV column {required!r}")

    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    rows_by_charge: dict[str, list[int]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()

    for row_number, row in enumerate(reader, start=2):
        charge_id = (row.get(charge_column) or "").strip()
        meter_id = (row.get(record_column) or "").strip()
        raw_units = (row.get(units_column) or "").strip()
        if not charge_id:
            raise ValueError(f"row {row_number}: {charge_column} is required")
        if not meter_id:
            raise ValueError(f"row {row_number}: {record_column} is required")
        key = (charge_id, meter_id)
        if key in seen:
            raise ValueError(
                f"row {row_number}: duplicate meter record {meter_id!r} "
                f"for charge {charge_id!r}"
            )
        seen.add(key)
        try:
            units = Decimal(raw_units)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"row {row_number}: {units_column} must be numeric") from exc
        if units < 0:
            raise ValueError(f"row {row_number}: {units_column} must be non-negative")
        totals[charge_id] += units
        rows_by_charge[charge_id].append(row_number)

    result: list[UsageRecord] = []
    for charge_id in sorted(rows_by_charge):
        result.append(UsageRecord(
            charge_id=charge_id,
            units=str(totals[charge_id]),
            source_hash=digest,
            source_locator=f"file://{source.name}#charge_id={charge_id}",
            verified=verified,
            metadata={
                "source_file": source.name,
                "meter_rows": rows_by_charge[charge_id],
                "meter_record_count": len(rows_by_charge[charge_id]),
                "quantity_basis": "aggregated_cloud_meter_usage",
            },
        ))
    return tuple(result)
