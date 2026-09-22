"""CSV ingestion for InsuranceRecovery commercial/property claim evidence."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
from pathlib import Path
from typing import Mapping

from .insurance import (
    InsuranceClaimLine,
    InsuranceCoverageAssessment,
    InsuranceSettlement,
)


DEFAULT_CLAIM_COLUMNS = {
    "claim_line_id": "Claim_Line_ID",
    "claimant_id": "Claimant_ID",
    "insurer_id": "Insurer_ID",
    "policy_id": "Policy_ID",
    "loss_date": "Loss_Date",
    "coverage_category": "Coverage_Category",
    "claimed_amount": "Claimed_Amount",
}

DEFAULT_ASSESSMENT_COLUMNS = {
    "assessment_id": "Assessment_ID",
    "claim_line_id": "Claim_Line_ID",
    "policy_id": "Policy_ID",
    "loss_date": "Loss_Date",
    "coverage_category": "Coverage_Category",
    "expected_net_payment": "Expected_Net_Payment",
    "coverage_basis": "Coverage_Basis",
    "policy_effective_from": "Policy_Effective_From",
    "policy_effective_to": "Policy_Effective_To",
    "policy_snapshot_date": "Policy_Snapshot_Date",
    "qualified_reviewer_id": "Qualified_Reviewer_ID",
    "qualification_basis": "Qualification_Basis",
}

DEFAULT_SETTLEMENT_COLUMNS = {
    "settlement_id": "Settlement_ID",
    "claim_line_id": "Claim_Line_ID",
    "amount_paid": "Amount_Paid",
    "payment_date": "Payment_Date",
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


def load_insurance_claim_lines_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_CLAIM_COLUMNS,
) -> tuple[InsuranceClaimLine, ...]:
    source, digest, rows = _read(path)
    result: list[InsuranceClaimLine] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(InsuranceClaimLine(
            claim_line_id=_required(row, columns["claim_line_id"], row_number),
            claimant_id=_required(row, columns["claimant_id"], row_number),
            insurer_id=_required(row, columns["insurer_id"], row_number),
            policy_id=_required(row, columns["policy_id"], row_number),
            loss_date=_required(row, columns["loss_date"], row_number),
            coverage_category=_required(
                row, columns["coverage_category"], row_number
            ),
            claimed_cents=_money_to_cents(
                _required(row, columns["claimed_amount"], row_number),
                field=columns["claimed_amount"],
            ),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_insurance_assessments_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_ASSESSMENT_COLUMNS,
) -> tuple[InsuranceCoverageAssessment, ...]:
    source, digest, rows = _read(path)
    result: list[InsuranceCoverageAssessment] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(InsuranceCoverageAssessment(
            assessment_id=_required(row, columns["assessment_id"], row_number),
            claim_line_id=_required(row, columns["claim_line_id"], row_number),
            policy_id=_required(row, columns["policy_id"], row_number),
            loss_date=_required(row, columns["loss_date"], row_number),
            coverage_category=_required(
                row, columns["coverage_category"], row_number
            ),
            expected_net_payment_cents=_money_to_cents(
                _required(row, columns["expected_net_payment"], row_number),
                field=columns["expected_net_payment"],
            ),
            coverage_basis=_required(
                row, columns["coverage_basis"], row_number
            ),
            policy_effective_from=_required(
                row, columns["policy_effective_from"], row_number
            ),
            policy_effective_to=_optional(
                row, columns.get("policy_effective_to")
            ),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            policy_snapshot_date=_optional(
                row, columns.get("policy_snapshot_date")
            ),
            qualified_reviewer_id=_optional(
                row, columns.get("qualified_reviewer_id")
            ),
            qualification_basis=_optional(
                row, columns.get("qualification_basis")
            ),
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_insurance_settlements_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_SETTLEMENT_COLUMNS,
) -> tuple[InsuranceSettlement, ...]:
    source, digest, rows = _read(path)
    result: list[InsuranceSettlement] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(InsuranceSettlement(
            settlement_id=_required(row, columns["settlement_id"], row_number),
            claim_line_id=_required(row, columns["claim_line_id"], row_number),
            amount_paid_cents=_money_to_cents(
                _required(row, columns["amount_paid"], row_number),
                field=columns["amount_paid"],
            ),
            payment_date=_required(row, columns["payment_date"], row_number),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)
