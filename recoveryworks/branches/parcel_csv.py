"""CSV ingestion for ParcelRecovery invoice lines and reviewed assessments."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
from pathlib import Path
from typing import Mapping

from .parcel import ParcelCharge, ParcelExpectedAssessment


DEFAULT_CHARGE_COLUMNS = {
    "shipment_id": "Shipment_ID",
    "invoice_id": "Invoice_ID",
    "shipper_id": "Shipper_ID",
    "carrier_id": "Carrier_ID",
    "ship_date": "Ship_Date",
    "service_code": "Service_Code",
    "zone": "Zone",
    "billed_weight": "Billed_Weight",
    "actual_total": "Actual_Total",
}

DEFAULT_ASSESSMENT_COLUMNS = {
    "assessment_id": "Assessment_ID",
    "shipment_id": "Shipment_ID",
    "carrier_id": "Carrier_ID",
    "ship_date": "Ship_Date",
    "service_code": "Service_Code",
    "zone": "Zone",
    "billed_weight": "Billed_Weight",
    "expected_total": "Expected_Total",
    "rate_basis": "Rate_Basis",
    "rate_snapshot_date": "Rate_Snapshot_Date",
    "rate_reviewer_id": "Rate_Reviewer_ID",
}


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


def _money_to_cents(value: str, *, field: str) -> int:
    text = (value or "").strip().replace("$", "").replace(",", "")
    if not text:
        raise ValueError(f"{field} is required")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"{field} has invalid money value {value!r}") from exc
    if amount < 0:
        raise ValueError(f"{field} cannot be negative")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def load_parcel_charges_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_CHARGE_COLUMNS,
) -> tuple[ParcelCharge, ...]:
    source, digest, rows = _read(path)
    result: list[ParcelCharge] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(ParcelCharge(
            shipment_id=_required(row, columns["shipment_id"], row_number),
            invoice_id=_required(row, columns["invoice_id"], row_number),
            shipper_id=_required(row, columns["shipper_id"], row_number),
            carrier_id=_required(row, columns["carrier_id"], row_number),
            ship_date=_required(row, columns["ship_date"], row_number),
            service_code=_required(row, columns["service_code"], row_number),
            zone=_required(row, columns["zone"], row_number),
            billed_weight=_required(row, columns["billed_weight"], row_number),
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


def load_parcel_assessments_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_ASSESSMENT_COLUMNS,
) -> tuple[ParcelExpectedAssessment, ...]:
    source, digest, rows = _read(path)
    result: list[ParcelExpectedAssessment] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(ParcelExpectedAssessment(
            assessment_id=_required(row, columns["assessment_id"], row_number),
            shipment_id=_required(row, columns["shipment_id"], row_number),
            carrier_id=_required(row, columns["carrier_id"], row_number),
            ship_date=_required(row, columns["ship_date"], row_number),
            service_code=_required(row, columns["service_code"], row_number),
            zone=_required(row, columns["zone"], row_number),
            billed_weight=_required(row, columns["billed_weight"], row_number),
            expected_total_cents=_money_to_cents(
                _required(row, columns["expected_total"], row_number),
                field=columns["expected_total"],
            ),
            rate_basis=_required(row, columns["rate_basis"], row_number),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            rate_snapshot_date=_optional(row, columns.get("rate_snapshot_date")),
            rate_reviewer_id=_optional(row, columns.get("rate_reviewer_id")),
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)
