"""CSV ingestion for recurring contract-billing recovery branches."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
from pathlib import Path
from typing import Mapping

from .contract_billing import ContractRate, InvoiceCharge, UsageRecord


DEFAULT_RATE_COLUMNS = {
    "counterparty_id": "Counterparty",
    "service_id": "Service_ID",
    "effective_from": "Effective_From",
    "effective_to": "Effective_To",
    "fixed_fee": "Fixed_Fee",
    "included_units": "Included_Units",
    "unit_rate": "Unit_Rate",
}

DEFAULT_CHARGE_COLUMNS = {
    "charge_id": "Charge_ID",
    "counterparty_id": "Counterparty",
    "account_id": "Account_ID",
    "service_id": "Service_ID",
    "service_date": "Service_Date",
    "actual_amount": "Actual_Amount",
}

DEFAULT_USAGE_COLUMNS = {
    "charge_id": "Charge_ID",
    "units": "Units",
}


def _decimal(value: str, *, name: str, allow_blank: bool = False) -> Decimal:
    text = (value or "").strip().replace("$", "").replace(",", "")
    if not text and allow_blank:
        return Decimal("0")
    if not text:
        raise ValueError(f"{name} is required")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"invalid {name}: {value!r}") from exc
    if amount < 0:
        raise ValueError(f"{name} must be non-negative")
    return amount


def dollars_to_cents(value: str, *, allow_blank: bool = False) -> int:
    amount = _decimal(value, name="money", allow_blank=allow_blank)
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def dollars_per_unit_to_micros(value: str, *, allow_blank: bool = False) -> int:
    amount = _decimal(value, name="unit rate", allow_blank=allow_blank)
    return int((amount * 1_000_000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


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


def _value(row: Mapping[str, str], column: str, *, row_number: int) -> str:
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


def load_contract_rates_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_RATE_COLUMNS,
) -> tuple[ContractRate, ...]:
    source, digest, rows = _read_rows(path)
    result: list[ContractRate] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(ContractRate(
            counterparty_id=_value(
                row, columns["counterparty_id"], row_number=row_number
            ),
            service_id=_value(row, columns["service_id"], row_number=row_number),
            effective_from=_value(
                row, columns["effective_from"], row_number=row_number
            ),
            effective_to=_optional(row, columns.get("effective_to")),
            fixed_cents=dollars_to_cents(
                _optional(row, columns.get("fixed_fee")) or "",
                allow_blank=True,
            ),
            included_units=str(_decimal(
                _optional(row, columns.get("included_units")) or "",
                name="included units",
                allow_blank=True,
            )),
            unit_rate_micros=dollars_per_unit_to_micros(
                _optional(row, columns.get("unit_rate")) or "",
                allow_blank=True,
            ),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_invoice_charges_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_CHARGE_COLUMNS,
) -> tuple[InvoiceCharge, ...]:
    source, digest, rows = _read_rows(path)
    result: list[InvoiceCharge] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(InvoiceCharge(
            charge_id=_value(row, columns["charge_id"], row_number=row_number),
            counterparty_id=_value(
                row, columns["counterparty_id"], row_number=row_number
            ),
            account_id=_value(row, columns["account_id"], row_number=row_number),
            service_id=_value(row, columns["service_id"], row_number=row_number),
            service_date=_value(
                row, columns["service_date"], row_number=row_number
            ),
            actual_cents=dollars_to_cents(
                _value(row, columns["actual_amount"], row_number=row_number)
            ),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_usage_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_USAGE_COLUMNS,
) -> tuple[UsageRecord, ...]:
    source, digest, rows = _read_rows(path)
    result: list[UsageRecord] = []
    for row_number, row in enumerate(rows, start=2):
        units = _decimal(
            _value(row, columns["units"], row_number=row_number),
            name="units",
        )
        result.append(UsageRecord(
            charge_id=_value(row, columns["charge_id"], row_number=row_number),
            units=str(units),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)
