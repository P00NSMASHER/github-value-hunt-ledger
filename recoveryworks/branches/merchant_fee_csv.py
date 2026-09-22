"""CSV ingestion for MerchantFeeRecovery."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
from pathlib import Path
from typing import Mapping

from .merchant_fee import (
    MerchantFeeAgreement,
    MerchantFeeStatement,
    MerchantTransactionSummary,
)


DEFAULT_AGREEMENT_COLUMNS = {
    "processor_id": "Processor",
    "fee_plan_id": "Fee_Plan_ID",
    "effective_from": "Effective_From",
    "effective_to": "Effective_To",
    "fixed_fee": "Fixed_Fee",
    "markup_bps": "Markup_BPS",
    "per_transaction": "Per_Transaction_Fee",
}

DEFAULT_STATEMENT_COLUMNS = {
    "statement_id": "Statement_ID",
    "processor_id": "Processor",
    "account_id": "Account_ID",
    "fee_plan_id": "Fee_Plan_ID",
    "statement_date": "Statement_Date",
    "actual_processor_fee": "Processor_Controlled_Fees",
    "scope_reviewer_id": "Scope_Reviewer_ID",
}

DEFAULT_TRANSACTION_COLUMNS = {
    "statement_id": "Statement_ID",
    "gross_sales": "Gross_Sales",
    "transaction_count": "Transaction_Count",
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


def _money_to_cents(value: str, *, allow_blank: bool = False) -> int:
    text = (value or "").strip().replace("$", "").replace(",", "")
    if not text and allow_blank:
        return 0
    if not text:
        raise ValueError("money value is required")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"invalid money value: {value!r}") from exc
    if amount < 0:
        raise ValueError("money value must be non-negative")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _nonnegative_int(value: str, *, field: str, allow_blank: bool = False) -> int:
    text = (value or "").strip().replace(",", "")
    if not text and allow_blank:
        return 0
    if not text:
        raise ValueError(f"{field} is required")
    try:
        result = int(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be integer") from exc
    if result < 0:
        raise ValueError(f"{field} must be non-negative")
    return result


def load_merchant_fee_agreements_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_AGREEMENT_COLUMNS,
) -> tuple[MerchantFeeAgreement, ...]:
    source, digest, rows = _read(path)
    result: list[MerchantFeeAgreement] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(MerchantFeeAgreement(
            processor_id=_required(row, columns["processor_id"], row_number),
            fee_plan_id=_required(row, columns["fee_plan_id"], row_number),
            effective_from=_required(row, columns["effective_from"], row_number),
            effective_to=_optional(row, columns.get("effective_to")),
            fixed_fee_cents=_money_to_cents(
                _optional(row, columns.get("fixed_fee")) or "",
                allow_blank=True,
            ),
            markup_bps=_nonnegative_int(
                _optional(row, columns.get("markup_bps")) or "",
                field="Markup_BPS",
                allow_blank=True,
            ),
            per_transaction_cents=_money_to_cents(
                _optional(row, columns.get("per_transaction")) or "",
                allow_blank=True,
            ),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_merchant_fee_statements_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_STATEMENT_COLUMNS,
) -> tuple[MerchantFeeStatement, ...]:
    source, digest, rows = _read(path)
    result: list[MerchantFeeStatement] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(MerchantFeeStatement(
            statement_id=_required(row, columns["statement_id"], row_number),
            processor_id=_required(row, columns["processor_id"], row_number),
            account_id=_required(row, columns["account_id"], row_number),
            fee_plan_id=_required(row, columns["fee_plan_id"], row_number),
            statement_date=_required(row, columns["statement_date"], row_number),
            actual_processor_fee_cents=_money_to_cents(
                _required(row, columns["actual_processor_fee"], row_number)
            ),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            scope_reviewer_id=_optional(row, columns.get("scope_reviewer_id")),
            metadata={
                "source_file": source.name,
                "row_number": row_number,
                "fee_scope": "processor_controlled_only",
            },
        ))
    return tuple(result)


def load_merchant_transaction_summaries_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_TRANSACTION_COLUMNS,
) -> tuple[MerchantTransactionSummary, ...]:
    source, digest, rows = _read(path)
    result: list[MerchantTransactionSummary] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(MerchantTransactionSummary(
            statement_id=_required(row, columns["statement_id"], row_number),
            gross_sales_cents=_money_to_cents(
                _required(row, columns["gross_sales"], row_number)
            ),
            transaction_count=_nonnegative_int(
                _required(row, columns["transaction_count"], row_number),
                field="Transaction_Count",
            ),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)
