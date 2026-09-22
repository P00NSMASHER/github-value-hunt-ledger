"""CSV ingestion for TaxRecovery transaction lines and reviewed assessments."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
from pathlib import Path
from typing import Mapping

from .tax import TaxAssessment, TaxTransactionLine


DEFAULT_TAX_LINE_COLUMNS = {
    "tax_line_id": "Tax_Line_ID",
    "invoice_id": "Invoice_ID",
    "purchaser_id": "Purchaser_ID",
    "vendor_id": "Vendor_ID",
    "transaction_date": "Transaction_Date",
    "jurisdiction": "Jurisdiction",
    "tax_category": "Tax_Category",
    "taxable_basis": "Taxable_Basis",
    "actual_tax": "Actual_Tax",
}

DEFAULT_ASSESSMENT_COLUMNS = {
    "assessment_id": "Assessment_ID",
    "tax_line_id": "Tax_Line_ID",
    "transaction_date": "Transaction_Date",
    "jurisdiction": "Jurisdiction",
    "tax_category": "Tax_Category",
    "expected_tax": "Expected_Tax",
    "taxability_basis": "Taxability_Basis",
    "rule_snapshot_date": "Rule_Snapshot_Date",
    "professional_reviewer_id": "Professional_Reviewer_ID",
}


def _money_to_cents(value: str, *, field: str) -> int:
    text = (value or "").strip().replace("$", "").replace(",", "")
    if not text:
        raise ValueError(f"{field} is required")
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


def load_tax_lines_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_TAX_LINE_COLUMNS,
) -> tuple[TaxTransactionLine, ...]:
    source, digest, rows = _read(path)
    result: list[TaxTransactionLine] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(TaxTransactionLine(
            tax_line_id=_required(row, columns["tax_line_id"], row_number),
            invoice_id=_required(row, columns["invoice_id"], row_number),
            purchaser_id=_required(row, columns["purchaser_id"], row_number),
            vendor_id=_required(row, columns["vendor_id"], row_number),
            transaction_date=_required(row, columns["transaction_date"], row_number),
            jurisdiction=_required(row, columns["jurisdiction"], row_number),
            tax_category=_required(row, columns["tax_category"], row_number),
            taxable_basis_cents=_money_to_cents(
                _required(row, columns["taxable_basis"], row_number),
                field=columns["taxable_basis"],
            ),
            actual_tax_cents=_money_to_cents(
                _required(row, columns["actual_tax"], row_number),
                field=columns["actual_tax"],
            ),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_tax_assessments_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_ASSESSMENT_COLUMNS,
) -> tuple[TaxAssessment, ...]:
    source, digest, rows = _read(path)
    result: list[TaxAssessment] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(TaxAssessment(
            assessment_id=_required(row, columns["assessment_id"], row_number),
            tax_line_id=_required(row, columns["tax_line_id"], row_number),
            transaction_date=_required(
                row, columns["transaction_date"], row_number
            ),
            jurisdiction=_required(row, columns["jurisdiction"], row_number),
            tax_category=_required(row, columns["tax_category"], row_number),
            expected_tax_cents=_money_to_cents(
                _required(row, columns["expected_tax"], row_number),
                field=columns["expected_tax"],
            ),
            taxability_basis=_required(
                row, columns["taxability_basis"], row_number
            ),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            rule_snapshot_date=_optional(
                row, columns.get("rule_snapshot_date")
            ),
            professional_reviewer_id=_optional(
                row, columns.get("professional_reviewer_id")
            ),
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)
