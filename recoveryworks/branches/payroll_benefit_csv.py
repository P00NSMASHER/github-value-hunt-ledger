"""Privacy-minimized unit ingestion for Payroll/BenefitBillingRecovery."""
from __future__ import annotations

import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path

from .contract_billing import UsageRecord


FORBIDDEN_DIRECT_IDENTIFIER_HEADERS = {
    "employee_name",
    "first_name",
    "last_name",
    "full_name",
    "member_name",
    "dependent_name",
    "ssn",
    "social_security_number",
    "social_security",
    "dob",
    "date_of_birth",
    "email",
    "email_address",
    "phone",
    "phone_number",
    "address",
    "home_address",
}


def _normalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def load_payroll_benefit_units_csv(
    path: str | Path,
    *,
    verified: bool = False,
    charge_column: str = "Charge_ID",
    record_column: str = "Record_ID",
    units_column: str = "Units",
) -> tuple[UsageRecord, ...]:
    """Aggregate deidentified employer billing units by invoice charge.

    Record_ID must be an opaque/surrogate record key. Common direct-identifier
    columns are rejected from this ingestion surface.
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

    normalized_headers = {_normalize_header(field) for field in reader.fieldnames if field}
    forbidden = sorted(normalized_headers & FORBIDDEN_DIRECT_IDENTIFIER_HEADERS)
    if forbidden:
        raise ValueError(
            "payroll/benefit unit input contains direct-identifier column(s): "
            + ", ".join(forbidden)
        )

    for required in (charge_column, record_column, units_column):
        if required not in reader.fieldnames:
            raise ValueError(f"missing required CSV column {required!r}")

    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    rows_by_charge: dict[str, list[int]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()

    for row_number, row in enumerate(reader, start=2):
        charge_id = (row.get(charge_column) or "").strip()
        record_id = (row.get(record_column) or "").strip()
        raw_units = (row.get(units_column) or "").strip()
        if not charge_id:
            raise ValueError(f"row {row_number}: {charge_column} is required")
        if not record_id:
            raise ValueError(f"row {row_number}: {record_column} is required")
        key = (charge_id, record_id)
        if key in seen:
            raise ValueError(
                f"row {row_number}: duplicate Record_ID {record_id!r} "
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
                "record_rows": rows_by_charge[charge_id],
                "record_count": len(rows_by_charge[charge_id]),
                "quantity_basis": "deidentified_employer_billing_units",
            },
        ))
    return tuple(result)
