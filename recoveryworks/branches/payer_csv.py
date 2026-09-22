"""CSV ingestion for de-identified PayerRecovery service lines and rates."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
from pathlib import Path
from typing import Mapping

from .payer import PayerRate, PayerServiceLine


DEFAULT_LINE_COLUMNS = {
    "line_id": "Line_ID",
    "claim_surrogate_id": "Claim_Surrogate_ID",
    "payer_id": "Payer",
    "service_date": "Service_Date",
    "billed_procedure": "Billed_Procedure",
    "paid_procedure": "Paid_Procedure",
    "units": "Units",
    "paid_amount": "Paid_Amount",
    "modifier": "Modifier",
    "place_of_service": "Place_Of_Service",
}

DEFAULT_RATE_COLUMNS = {
    "payer_id": "Payer",
    "procedure_code": "Procedure_Code",
    "allowed_amount_per_unit": "Allowed_Amount_Per_Unit",
    "effective_from": "Effective_From",
    "effective_to": "Effective_To",
    "modifier": "Modifier",
    "place_of_service": "Place_Of_Service",
}

_FORBIDDEN_PHI_HEADERS = {
    "patientname",
    "patient_name",
    "memberid",
    "member_id",
    "patientid",
    "patient_id",
    "dob",
    "dateofbirth",
    "date_of_birth",
    "ssn",
    "subscriberid",
    "subscriber_id",
}


def _header_key(value: str) -> str:
    return value.strip().lower().replace(" ", "").replace("-", "")


def _money_to_cents(value: str) -> int:
    text = (value or "").strip().replace("$", "").replace(",", "")
    try:
        amount = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid money amount: {value!r}") from exc
    if amount < 0:
        raise ValueError("payer amount cannot be negative")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _read_csv(path: str | Path, *, reject_phi_headers: bool) -> tuple[Path, str, list[dict[str, str]]]:
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
    if reject_phi_headers:
        bad = {
            header for header in reader.fieldnames
            if _header_key(header) in {
                _header_key(item) for item in _FORBIDDEN_PHI_HEADERS
            }
        }
        if bad:
            raise ValueError(
                "payer common-ledger input contains prohibited PHI columns: "
                + ", ".join(sorted(bad))
            )
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


def load_payer_lines_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_LINE_COLUMNS,
) -> tuple[PayerServiceLine, ...]:
    source, digest, rows = _read_csv(path, reject_phi_headers=True)
    result: list[PayerServiceLine] = []
    for row_number, row in enumerate(rows, start=2):
        units_raw = _required(row, columns["units"], row_number=row_number)
        try:
            units = int(units_raw)
        except ValueError as exc:
            raise ValueError(f"row {row_number}: Units must be integer") from exc
        result.append(PayerServiceLine(
            line_id=_required(row, columns["line_id"], row_number=row_number),
            claim_surrogate_id=_required(
                row, columns["claim_surrogate_id"], row_number=row_number
            ),
            payer_id=_required(row, columns["payer_id"], row_number=row_number),
            service_date=_required(row, columns["service_date"], row_number=row_number),
            billed_procedure=_required(
                row, columns["billed_procedure"], row_number=row_number
            ),
            paid_procedure=_optional(row, columns.get("paid_procedure")),
            units=units,
            paid_cents=_money_to_cents(
                _required(row, columns["paid_amount"], row_number=row_number)
            ),
            modifier=_optional(row, columns.get("modifier")),
            place_of_service=_optional(row, columns.get("place_of_service")),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_payer_rates_csv(
    path: str | Path,
    *,
    verified: bool = False,
    default_effective_from: str,
    jurisdiction: str | None = None,
    columns: Mapping[str, str] = DEFAULT_RATE_COLUMNS,
) -> tuple[PayerRate, ...]:
    if not isinstance(default_effective_from, str) or not default_effective_from.strip():
        raise ValueError("default_effective_from is required")
    source, digest, rows = _read_csv(path, reject_phi_headers=False)
    result: list[PayerRate] = []
    for row_number, row in enumerate(rows, start=2):
        effective_from = (
            _optional(row, columns.get("effective_from"))
            or default_effective_from.strip()
        )
        result.append(PayerRate(
            payer_id=_required(row, columns["payer_id"], row_number=row_number),
            procedure_code=_required(
                row, columns["procedure_code"], row_number=row_number
            ),
            allowed_cents_per_unit=_money_to_cents(
                _required(
                    row,
                    columns["allowed_amount_per_unit"],
                    row_number=row_number,
                )
            ),
            effective_from=effective_from,
            effective_to=_optional(row, columns.get("effective_to")),
            modifier=_optional(row, columns.get("modifier")),
            place_of_service=_optional(row, columns.get("place_of_service")),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            jurisdiction=jurisdiction,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)
