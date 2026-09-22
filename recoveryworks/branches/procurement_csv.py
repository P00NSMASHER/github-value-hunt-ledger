"""CSV ingestion for ProcurementRecovery."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
from pathlib import Path
from typing import Mapping

from .procurement import (
    ProcurementAuthority,
    ProcurementInvoiceLine,
    ProcurementQuantityApproval,
)


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


def _optional(row: Mapping[str, str], column: str) -> str | None:
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


def load_procurement_invoice_lines_csv(
    path: str | Path,
    *,
    verified: bool = False,
) -> tuple[ProcurementInvoiceLine, ...]:
    source, digest, rows = _read(path)
    result: list[ProcurementInvoiceLine] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(ProcurementInvoiceLine(
            invoice_line_id=_required(row, "Invoice_Line_ID", row_number),
            invoice_id=_required(row, "Invoice_ID", row_number),
            purchaser_id=_required(row, "Purchaser_ID", row_number),
            supplier_id=_required(row, "Supplier_ID", row_number),
            po_line_id=_required(row, "PO_Line_ID", row_number),
            sku=_required(row, "SKU", row_number),
            invoice_date=_required(row, "Invoice_Date", row_number),
            invoiced_quantity=_required(row, "Invoiced_Quantity", row_number),
            actual_line_cents=_money_to_cents(
                _required(row, "Actual_Line_Amount", row_number),
                field="Actual_Line_Amount",
            ),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_procurement_authorities_csv(
    path: str | Path,
    *,
    verified: bool = False,
) -> tuple[ProcurementAuthority, ...]:
    source, digest, rows = _read(path)
    result: list[ProcurementAuthority] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(ProcurementAuthority(
            authority_id=_required(row, "Authority_ID", row_number),
            supplier_id=_required(row, "Supplier_ID", row_number),
            po_line_id=_required(row, "PO_Line_ID", row_number),
            sku=_required(row, "SKU", row_number),
            effective_from=_required(row, "Effective_From", row_number),
            effective_to=_optional(row, "Effective_To"),
            contracted_unit_price_cents=_money_to_cents(
                _required(row, "Contracted_Unit_Price", row_number),
                field="Contracted_Unit_Price",
            ),
            price_basis=_required(row, "Price_Basis", row_number),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_procurement_quantities_csv(
    path: str | Path,
    *,
    verified: bool = False,
) -> tuple[ProcurementQuantityApproval, ...]:
    source, digest, rows = _read(path)
    result: list[ProcurementQuantityApproval] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(ProcurementQuantityApproval(
            invoice_line_id=_required(row, "Invoice_Line_ID", row_number),
            approved_billable_quantity=_required(
                row, "Approved_Billable_Quantity", row_number
            ),
            quantity_basis=_required(row, "Quantity_Basis", row_number),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)
