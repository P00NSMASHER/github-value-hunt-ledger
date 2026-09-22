"""CSV ingestion for Warranty/CreditRecovery."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
from pathlib import Path
from typing import Mapping

from .warranty_credit import WarrantyCreditEntitlement, WarrantyCreditSettlement


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


def load_warranty_credit_entitlements_csv(
    path: str | Path,
    *,
    verified: bool = False,
) -> tuple[WarrantyCreditEntitlement, ...]:
    source, digest, rows = _read(path)
    result: list[WarrantyCreditEntitlement] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(WarrantyCreditEntitlement(
            entitlement_id=_required(row, "Entitlement_ID", row_number),
            client_id=_required(row, "Client_ID", row_number),
            supplier_id=_required(row, "Supplier_ID", row_number),
            reference_id=_required(row, "Reference_ID", row_number),
            credit_category=_required(row, "Credit_Category", row_number),
            entitled_cents=_money_to_cents(
                _required(row, "Entitled_Amount", row_number),
                field="Entitled_Amount",
            ),
            effective_date=_required(row, "Effective_Date", row_number),
            entitlement_basis=_required(row, "Entitlement_Basis", row_number),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            entitlement_reviewer_id=_optional(row, "Entitlement_Reviewer_ID"),
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_warranty_credit_settlements_csv(
    path: str | Path,
    *,
    verified: bool = False,
) -> tuple[WarrantyCreditSettlement, ...]:
    source, digest, rows = _read(path)
    result: list[WarrantyCreditSettlement] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(WarrantyCreditSettlement(
            settlement_id=_required(row, "Settlement_ID", row_number),
            entitlement_id=_required(row, "Entitlement_ID", row_number),
            amount_received_cents=_money_to_cents(
                _required(row, "Amount_Received", row_number),
                field="Amount_Received",
            ),
            settlement_date=_required(row, "Settlement_Date", row_number),
            settlement_kind=_required(row, "Settlement_Kind", row_number),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)
