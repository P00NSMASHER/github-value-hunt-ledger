"""File ingestion for RebateRecovery programs, purchases, and settlements."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
from typing import Any

from .rebate import (
    RebateMeasurementBasis,
    RebateProgram,
    RebatePurchaseLine,
    RebateSettlement,
    RebateTier,
    RebateTierMode,
)


def _money_to_cents(value: str) -> int:
    text = (value or "").strip().replace("$", "").replace(",", "")
    if not text:
        raise ValueError("money value is required")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"invalid money value: {value!r}") from exc
    if amount < 0:
        raise ValueError("money value must be non-negative")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _rate_bps(tier: dict[str, Any], *, context: str) -> int:
    if "rate_bps" in tier:
        value = tier["rate_bps"]
        if type(value) is not int:
            raise ValueError(f"{context}.rate_bps must be integer")
        return value
    if "rate_pct" not in tier:
        raise ValueError(f"{context} requires rate_bps or rate_pct")
    try:
        pct = Decimal(str(tier["rate_pct"]))
    except InvalidOperation as exc:
        raise ValueError(f"{context}.rate_pct must be numeric") from exc
    bps = pct * Decimal(100)
    if bps != bps.to_integral_value():
        raise ValueError(f"{context}.rate_pct must be precise to 0.01 percentage point")
    return int(bps)


def _read_csv(path: str | Path) -> tuple[Path, str, list[dict[str, str]]]:
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


def _required(row: dict[str, str], column: str, row_number: int) -> str:
    if column not in row:
        raise ValueError(f"missing required CSV column {column!r}")
    value = row.get(column)
    if value is None or not value.strip():
        raise ValueError(f"row {row_number}: {column} is required")
    return value.strip()


def load_rebate_programs_json(
    path: str | Path,
    *,
    verified: bool = False,
) -> tuple[RebateProgram, ...]:
    source = Path(path)
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{source} must be valid UTF-8 JSON") from exc
    entries = payload.get("programs") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        raise ValueError("rebate JSON must be a list or {'programs': [...]}")

    result: list[RebateProgram] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"programs[{index}] must be object")
        if "tier_mode" not in entry:
            raise ValueError(f"programs[{index}].tier_mode is required")
        if "measurement_basis" not in entry:
            raise ValueError(f"programs[{index}].measurement_basis is required")
        raw_tiers = entry.get("tiers")
        if not isinstance(raw_tiers, list) or not raw_tiers:
            raise ValueError(f"programs[{index}].tiers must be non-empty list")

        tiers: list[RebateTier] = []
        for tier_index, tier in enumerate(raw_tiers):
            if not isinstance(tier, dict):
                raise ValueError(
                    f"programs[{index}].tiers[{tier_index}] must be object"
                )
            context = f"programs[{index}].tiers[{tier_index}]"
            minimum = tier.get("min_measure")
            if minimum is None:
                raise ValueError(f"{context}.min_measure is required")
            maximum = tier.get("max_measure")
            tiers.append(RebateTier(
                min_measure=str(minimum),
                max_measure=None if maximum in (None, "") else str(maximum),
                rate_bps=_rate_bps(tier, context=context),
            ))

        try:
            tier_mode = RebateTierMode(str(entry["tier_mode"]).strip().lower())
        except ValueError as exc:
            raise ValueError(
                f"programs[{index}].tier_mode must be retroactive or incremental"
            ) from exc
        try:
            measurement_basis = RebateMeasurementBasis(
                str(entry["measurement_basis"]).strip().lower()
            )
        except ValueError as exc:
            raise ValueError(
                f"programs[{index}].measurement_basis must be units or spend"
            ) from exc

        result.append(RebateProgram(
            supplier_id=str(entry.get("supplier_id") or "").strip(),
            program_id=str(entry.get("program_id") or "").strip(),
            period_start=str(entry.get("period_start") or "").strip(),
            period_end=str(entry.get("period_end") or "").strip(),
            tier_mode=tier_mode,
            measurement_basis=measurement_basis,
            tiers=tuple(tiers),
            source_hash=digest,
            source_locator=f"file://{source.name}#programs[{index}]",
            verified=verified,
            metadata={"source_file": source.name, "program_index": index},
        ))
    return tuple(result)


def load_rebate_purchases_csv(
    path: str | Path,
    *,
    verified: bool = False,
) -> tuple[RebatePurchaseLine, ...]:
    source, digest, rows = _read_csv(path)
    result: list[RebatePurchaseLine] = []
    for row_number, row in enumerate(rows, start=2):
        quantity = _required(row, "Quantity", row_number)
        try:
            qty = Decimal(quantity)
        except InvalidOperation as exc:
            raise ValueError(f"row {row_number}: Quantity must be numeric") from exc
        if qty < 0:
            raise ValueError(f"row {row_number}: Quantity must be non-negative")
        result.append(RebatePurchaseLine(
            purchase_id=_required(row, "Purchase_ID", row_number),
            supplier_id=_required(row, "Supplier", row_number),
            program_id=_required(row, "Program_ID", row_number),
            purchase_date=_required(row, "Purchase_Date", row_number),
            quantity=str(qty),
            net_spend_cents=_money_to_cents(
                _required(row, "Net_Spend", row_number)
            ),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_rebate_settlements_csv(
    path: str | Path,
    *,
    verified: bool = False,
) -> tuple[RebateSettlement, ...]:
    source, digest, rows = _read_csv(path)
    result: list[RebateSettlement] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(RebateSettlement(
            settlement_id=_required(row, "Settlement_ID", row_number),
            supplier_id=_required(row, "Supplier", row_number),
            program_id=_required(row, "Program_ID", row_number),
            amount_received_cents=_money_to_cents(
                _required(row, "Amount_Received", row_number)
            ),
            settlement_date=_required(row, "Settlement_Date", row_number),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)
