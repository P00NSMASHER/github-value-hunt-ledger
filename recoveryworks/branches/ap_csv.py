"""CSV ingestion for APRecovery source exports."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
from pathlib import Path
from typing import Mapping

from .ap import APObligation, APPayment, APVendorStatementLine


DEFAULT_PAYMENT_COLUMNS = {
    "payment_id": "Payment_Number",
    "vendor_id": "Vendor",
    "invoice_number": "Invoice_Number",
    "amount": "Amount",
    "payment_date": "Payment_Date",
}

DEFAULT_OBLIGATION_COLUMNS = {
    "vendor_id": "Vendor",
    "invoice_number": "Invoice_Number",
    "amount": "Amount",
    "effective_from": "Invoice_Date",
}

DEFAULT_VENDOR_STATEMENT_COLUMNS = {
    "vendor_id": "Vendor",
    "invoice_number": "Invoice_Number",
    "balance": "Balance",
    "statement_date": "Statement_Date",
}


def _parse_money(value: str, *, allow_zero: bool, allow_negative: bool) -> int:
    text = (value or "").strip().replace("$", "").replace(",", "")
    if not text:
        raise ValueError("money value is required")
    parenthetical = text.startswith("(") and text.endswith(")")
    if parenthetical:
        text = text[1:-1].strip()
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"invalid money value: {value!r}") from exc
    if parenthetical:
        amount = -amount
    cents = int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if not allow_negative and cents < 0:
        raise ValueError("negative money value is not allowed")
    if not allow_zero and cents == 0:
        raise ValueError("zero money value is not allowed")
    return cents


def money_to_cents(value: str) -> int:
    cents = _parse_money(value, allow_zero=False, allow_negative=False)
    if cents <= 0:
        raise ValueError("AP payment/obligation amount must be positive")
    return cents


def signed_money_to_cents(value: str) -> int:
    """Parse statement balances, including credits such as -100 or (100)."""
    return _parse_money(value, allow_zero=True, allow_negative=True)


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


def load_payments_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_PAYMENT_COLUMNS,
) -> tuple[APPayment, ...]:
    source, digest, rows = _read_rows(path)
    result: list[APPayment] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(APPayment(
            payment_id=_value(row, columns["payment_id"], row_number=row_number),
            vendor_id=_value(row, columns["vendor_id"], row_number=row_number),
            invoice_number=_value(row, columns["invoice_number"], row_number=row_number),
            amount_cents=money_to_cents(_value(row, columns["amount"], row_number=row_number)),
            payment_date=(row.get(columns.get("payment_date", "")) or "").strip() or None,
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_obligations_csv(
    path: str | Path,
    *,
    verified: bool = False,
    default_effective_from: str,
    columns: Mapping[str, str] = DEFAULT_OBLIGATION_COLUMNS,
) -> tuple[APObligation, ...]:
    if not isinstance(default_effective_from, str) or not default_effective_from.strip():
        raise ValueError("default_effective_from is required")
    source, digest, rows = _read_rows(path)
    result: list[APObligation] = []
    effective_column = columns.get("effective_from")
    for row_number, row in enumerate(rows, start=2):
        effective = (
            (row.get(effective_column) or "").strip()
            if effective_column else ""
        ) or default_effective_from.strip()
        result.append(APObligation(
            vendor_id=_value(row, columns["vendor_id"], row_number=row_number),
            invoice_number=_value(row, columns["invoice_number"], row_number=row_number),
            expected_cents=money_to_cents(_value(row, columns["amount"], row_number=row_number)),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            effective_from=effective,
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_vendor_statements_csv(
    path: str | Path,
    *,
    verified: bool = False,
    default_statement_date: str | None = None,
    columns: Mapping[str, str] = DEFAULT_VENDOR_STATEMENT_COLUMNS,
) -> tuple[APVendorStatementLine, ...]:
    """Load invoice-level vendor statement balances.

    Negative balances or parenthetical amounts represent credits owed to the
    client. If the export omits a statement-date column, default_statement_date
    must be supplied explicitly.
    """
    source, digest, rows = _read_rows(path)
    date_column = columns.get("statement_date")
    result: list[APVendorStatementLine] = []
    for row_number, row in enumerate(rows, start=2):
        statement_date = (
            (row.get(date_column) or "").strip() if date_column else ""
        ) or (default_statement_date or "").strip()
        if not statement_date:
            raise ValueError(
                f"row {row_number}: statement date is required "
                "(column or default_statement_date)"
            )
        result.append(APVendorStatementLine(
            vendor_id=_value(row, columns["vendor_id"], row_number=row_number),
            invoice_number=_value(row, columns["invoice_number"], row_number=row_number),
            balance_cents=signed_money_to_cents(
                _value(row, columns["balance"], row_number=row_number)
            ),
            statement_date=statement_date,
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)
