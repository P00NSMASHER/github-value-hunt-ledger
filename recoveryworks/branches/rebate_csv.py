"""CSV ingestion for RebateRecovery."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
from pathlib import Path
from typing import Mapping

from .rebate import RebateActivity, RebateAgreement, RebateBasis, RebateCredit


DEFAULT_AGREEMENT_COLUMNS = {
    "agreement_id": "Agreement_ID",
    "vendor_id": "Vendor",
    "basis": "Basis",
    "effective_from": "Effective_From",
    "effective_to": "Effective_To",
    "threshold_amount": "Threshold_Amount",
    "threshold_units": "Threshold_Units",
    "rate_bps": "Rate_BPS",
    "rate_per_unit": "Rate_Per_Unit",
    "fixed_bonus": "Fixed_Bonus",
}

DEFAULT_ACTIVITY_COLUMNS = {
    "agreement_id": "Agreement_ID",
    "period_id": "Period_ID",
    "period_end": "Period_End",
    "eligible_spend": "Eligible_Spend",
    "eligible_units": "Eligible_Units",
}

DEFAULT_CREDIT_COLUMNS = {
    "credit_id": "Credit_ID",
    "agreement_id": "Agreement_ID",
    "period_id": "Period_ID",
    "amount": "Amount",
}


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


def _required(row: Mapping[str, str], column: str, *, row_number: int) -> str:
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


def _decimal(value: str | None, *, name: str, blank_zero: bool = True) -> Decimal:
    text = (value or "").strip().replace("$", "").replace(",", "")
    if not text and blank_zero:
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


def _money_cents(value: str | None, *, name: str) -> int:
    amount = _decimal(value, name=name)
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _int_value(value: str | None, *, name: str) -> int:
    amount = _decimal(value, name=name)
    integral = amount.to_integral_value()
    if amount != integral:
        raise ValueError(f"{name} must be an integer")
    return int(integral)


def load_rebate_agreements_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_AGREEMENT_COLUMNS,
) -> tuple[RebateAgreement, ...]:
    source, digest, rows = _read_rows(path)
    result: list[RebateAgreement] = []
    for row_number, row in enumerate(rows, start=2):
        basis_raw = _required(row, columns["basis"], row_number=row_number).lower()
        try:
            basis = RebateBasis(basis_raw)
        except ValueError as exc:
            raise ValueError(
                f"row {row_number}: Basis must be spend_bps or unit_cents"
            ) from exc

        result.append(RebateAgreement(
            agreement_id=_required(
                row, columns["agreement_id"], row_number=row_number
            ),
            vendor_id=_required(row, columns["vendor_id"], row_number=row_number),
            basis=basis,
            effective_from=_required(
                row, columns["effective_from"], row_number=row_number
            ),
            effective_to=_optional(row, columns.get("effective_to")),
            threshold_spend_cents=_money_cents(
                _optional(row, columns.get("threshold_amount")),
                name="threshold amount",
            ),
            threshold_units=str(_decimal(
                _optional(row, columns.get("threshold_units")),
                name="threshold units",
            )),
            rate_bps=_int_value(
                _optional(row, columns.get("rate_bps")),
                name="rate bps",
            ),
            rate_cents_per_unit=_money_cents(
                _optional(row, columns.get("rate_per_unit")),
                name="rate per unit",
            ),
            fixed_bonus_cents=_money_cents(
                _optional(row, columns.get("fixed_bonus")),
                name="fixed bonus",
            ),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_rebate_activity_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_ACTIVITY_COLUMNS,
) -> tuple[RebateActivity, ...]:
    source, digest, rows = _read_rows(path)
    result: list[RebateActivity] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(RebateActivity(
            agreement_id=_required(
                row, columns["agreement_id"], row_number=row_number
            ),
            period_id=_required(row, columns["period_id"], row_number=row_number),
            period_end=_required(row, columns["period_end"], row_number=row_number),
            eligible_spend_cents=_money_cents(
                _optional(row, columns.get("eligible_spend")),
                name="eligible spend",
            ),
            eligible_units=str(_decimal(
                _optional(row, columns.get("eligible_units")),
                name="eligible units",
            )),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_rebate_credits_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_CREDIT_COLUMNS,
) -> tuple[RebateCredit, ...]:
    source, digest, rows = _read_rows(path)
    result: list[RebateCredit] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(RebateCredit(
            credit_id=_required(row, columns["credit_id"], row_number=row_number),
            agreement_id=_required(
                row, columns["agreement_id"], row_number=row_number
            ),
            period_id=_required(row, columns["period_id"], row_number=row_number),
            amount_cents=_money_cents(
                _required(row, columns["amount"], row_number=row_number),
                name="credit amount",
            ),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)
