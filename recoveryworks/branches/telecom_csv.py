"""TelecomRecovery CDR/usage aggregation ingestion."""
from __future__ import annotations

import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path

from .contract_billing import UsageRecord


def load_cdr_usage_csv(
    path: str | Path,
    *,
    verified: bool = False,
    charge_column: str = "Charge_ID",
    cdr_column: str = "CDR_ID",
    units_column: str = "Usage_Units",
) -> tuple[UsageRecord, ...]:
    """Aggregate raw CDR-style records to usage units per invoice charge.

    Duplicate CDR_ID values within a Charge_ID fail closed rather than double
    counting usage.
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
    for required in (charge_column, cdr_column, units_column):
        if required not in reader.fieldnames:
            raise ValueError(f"missing required CSV column {required!r}")

    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    rows_by_charge: dict[str, list[int]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()

    for row_number, row in enumerate(reader, start=2):
        charge_id = (row.get(charge_column) or "").strip()
        cdr_id = (row.get(cdr_column) or "").strip()
        raw_units = (row.get(units_column) or "").strip()
        if not charge_id:
            raise ValueError(f"row {row_number}: {charge_column} is required")
        if not cdr_id:
            raise ValueError(f"row {row_number}: {cdr_column} is required")
        key = (charge_id, cdr_id)
        if key in seen:
            raise ValueError(
                f"row {row_number}: duplicate CDR {cdr_id!r} for charge {charge_id!r}"
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
                "cdr_rows": rows_by_charge[charge_id],
                "cdr_count": len(rows_by_charge[charge_id]),
                "quantity_basis": "aggregated_cdr_usage",
            },
        ))
    return tuple(result)
