"""File ingestion for UtilityRecovery bills and deterministic tariff definitions.

The loader accepts explicit scalar, tiered, TOU, daily, and minimum charge
primitives. Free-form formulas and executable conditions are rejected.
"""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .utility import (
    UtilityBill,
    UtilityCharge,
    UtilityChargeKind,
    UtilityTariff,
    UtilityTier,
    normalize_period,
)


DEFAULT_BILL_COLUMNS = {
    "bill_id": "Bill_ID",
    "utility_id": "Utility",
    "account_id": "Account_ID",
    "service_class": "Service_Class",
    "bill_date": "Bill_Date",
    "actual": "Bill_Amount",
    "kwh": "Billed_kWh",
    "demand_kw": "Billed_Demand_kW",
    "reactive_kva": "Billed_rkVA",
    "days_used": "Days_Used",
}

TOU_COLUMN_PREFIX = "Billed_kWh_"


def _decimal(value: Any, *, name: str) -> Decimal:
    text = str(value).strip().replace("$", "").replace(",", "")
    try:
        result = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def dollars_to_cents(value: Any) -> int:
    return int((_decimal(value, name="dollars") * 100).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    ))


def dollars_per_unit_to_micros(value: Any) -> int:
    micros = int((_decimal(value, name="rate") * 1_000_000).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    ))
    if micros <= 0:
        raise ValueError("rate must be positive")
    return micros


def _read_text(path: str | Path) -> tuple[Path, bytes, str]:
    source = Path(path)
    raw = source.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{source} must be UTF-8") from exc
    return source, raw, text


def _optional_value(row: Mapping[str, str], column: str | None) -> str | None:
    if not column:
        return None
    value = row.get(column)
    if value is None or not str(value).strip():
        return None
    return str(value).strip()


def load_utility_bills_csv(
    path: str | Path,
    *,
    verified: bool = False,
    columns: Mapping[str, str] = DEFAULT_BILL_COLUMNS,
) -> tuple[UtilityBill, ...]:
    source, raw, text = _read_text(path)
    digest = hashlib.sha256(raw).hexdigest()
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise ValueError(f"{source} has no CSV header")

    period_columns: dict[str, str] = {}
    reserved_columns = {value for value in columns.values() if value}
    for field in reader.fieldnames:
        if (
            field
            and field.startswith(TOU_COLUMN_PREFIX)
            and field not in reserved_columns
        ):
            raw_period = field[len(TOU_COLUMN_PREFIX):]
            if raw_period:
                period_columns[normalize_period(raw_period)] = field

    result: list[UtilityBill] = []
    for row_number, row in enumerate(reader, start=2):
        def req(key: str) -> str:
            column = columns[key]
            value = row.get(column)
            if value is None or not str(value).strip():
                raise ValueError(f"row {row_number}: {column} is required")
            return str(value).strip()

        days_raw = _optional_value(row, columns.get("days_used"))
        days_used = None
        if days_raw is not None:
            try:
                days_used = int(days_raw)
            except ValueError as exc:
                raise ValueError(
                    f"row {row_number}: {columns.get('days_used')} must be integer"
                ) from exc
            if days_used <= 0:
                raise ValueError(f"row {row_number}: Days_Used must be positive")

        billed_kwh_by_period = {
            period: str(row[column]).strip()
            for period, column in period_columns.items()
            if row.get(column) is not None and str(row[column]).strip()
        }

        result.append(UtilityBill(
            bill_id=req("bill_id"),
            utility_id=req("utility_id"),
            account_id=req("account_id"),
            service_class=req("service_class"),
            bill_date=req("bill_date"),
            actual_cents=dollars_to_cents(req("actual")),
            billed_kwh=_optional_value(row, columns.get("kwh")),
            billed_demand_kw=_optional_value(row, columns.get("demand_kw")),
            billed_reactive_kva=_optional_value(row, columns.get("reactive_kva")),
            days_used=days_used,
            billed_kwh_by_period=billed_kwh_by_period,
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={
                "source_file": source.name,
                "row_number": row_number,
                "tou_columns": dict(period_columns),
            },
        ))
    return tuple(result)


def _load_tiers(
    *,
    tiers: Any,
    tariff_index: int,
    step_name: str,
) -> tuple[UtilityTier, ...]:
    if not isinstance(tiers, list) or not tiers:
        raise ValueError(
            f"tariffs[{tariff_index}] step {step_name!r} requires non-empty tiers list"
        )
    result: list[UtilityTier] = []
    for tier_index, tier in enumerate(tiers):
        if not isinstance(tier, dict):
            raise ValueError(
                f"tariffs[{tariff_index}] step {step_name!r} tiers[{tier_index}] "
                "must be an object"
            )
        if "rate" not in tier:
            raise ValueError(
                f"tariffs[{tariff_index}] step {step_name!r} tiers[{tier_index}] "
                "missing rate"
            )
        upper = tier.get("up_to_kwh")
        result.append(UtilityTier(
            rate_micros_per_unit=dollars_per_unit_to_micros(tier["rate"]),
            up_to_kwh=None if upper in (None, "", "null") else str(upper),
        ))
    return tuple(result)


def load_simple_tariff_definitions_json(
    path: str | Path,
    *,
    utility_id: str,
    verified: bool = False,
    default_effective_from: str,
    jurisdiction: str | None = None,
) -> tuple[UtilityTariff, ...]:
    """Load explicit deterministic tariff steps from JSON extraction output.

    Supported charge_type values:
    - fixed_fee
    - daily_fixed_fee
    - per_kwh / energy_charge
    - tiered_kwh
    - tou_kwh
    - per_kw / demand_charge
    - per_rkva / reactive_demand_fee
    - minimum_charge / minimum_bill

    Tiered example:
      {"charge_type":"tiered_kwh","tiers":[
        {"up_to_kwh":1000,"rate":0.10},
        {"up_to_kwh":null,"rate":0.15}
      ]}

    TOU example:
      {"charge_type":"tou_kwh","period":"on_peak","value":0.20}

    Any executable condition, free-form formula, or unknown charge type fails
    closed rather than silently approximating the bill.
    """
    if not isinstance(utility_id, str) or not utility_id.strip():
        raise ValueError("utility_id is required")
    if not isinstance(default_effective_from, str) or not default_effective_from.strip():
        raise ValueError("default_effective_from is required")

    source, raw, text = _read_text(path)
    digest = hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source} is not valid JSON") from exc

    entries = payload.get("tariffs") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        raise ValueError("tariff JSON must be a list or {'tariffs': [...]}")

    tariffs: list[UtilityTariff] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"tariffs[{index}] must be an object")
        service_class = entry.get("sc_code") or entry.get("service_class")
        if not service_class:
            raise ValueError(f"tariffs[{index}] missing sc_code/service_class")
        effective_from = (
            entry.get("effective_date")
            or (entry.get("metadata") or {}).get("effective_date")
            or default_effective_from
        )
        effective_to = (
            entry.get("effective_to")
            or (entry.get("metadata") or {}).get("effective_to")
        )
        steps = entry.get("logic_steps")
        if not isinstance(steps, list):
            raise ValueError(f"tariffs[{index}] logic_steps must be a list")

        charges: list[UtilityCharge] = []
        minimum_bill_cents = 0
        for step_index, step in enumerate(steps):
            if not isinstance(step, dict):
                raise ValueError(
                    f"tariffs[{index}].logic_steps[{step_index}] must be an object"
                )
            name = str(step.get("step_name") or f"step-{step_index}")
            condition = step.get("condition", "Always")
            if condition != "Always":
                raise ValueError(
                    f"tariffs[{index}] step {name!r} uses unsupported conditional logic"
                )
            if step.get("python_formula") or step.get("formula"):
                raise ValueError(
                    f"tariffs[{index}] step {name!r} uses unsupported free-form formula"
                )
            value = step.get("value")
            kind = str(step.get("charge_type") or "").strip().lower()

            if kind == "fixed_fee":
                charges.append(UtilityCharge(
                    name=name,
                    kind=UtilityChargeKind.FIXED,
                    amount_cents=dollars_to_cents(value or 0),
                ))
            elif kind == "daily_fixed_fee":
                charges.append(UtilityCharge(
                    name=name,
                    kind=UtilityChargeKind.DAILY_FIXED,
                    rate_micros_per_unit=dollars_per_unit_to_micros(value),
                ))
            elif kind in {"per_kwh", "energy_charge"}:
                if isinstance(value, (dict, list)):
                    raise ValueError(
                        f"tariffs[{index}] step {name!r} scalar energy value must be numeric"
                    )
                charges.append(UtilityCharge(
                    name=name,
                    kind=UtilityChargeKind.ENERGY,
                    rate_micros_per_unit=dollars_per_unit_to_micros(value),
                ))
            elif kind == "tiered_kwh":
                charges.append(UtilityCharge(
                    name=name,
                    kind=UtilityChargeKind.TIERED_ENERGY,
                    tiers=_load_tiers(
                        tiers=step.get("tiers"),
                        tariff_index=index,
                        step_name=name,
                    ),
                ))
            elif kind == "tou_kwh":
                period = step.get("period")
                if not isinstance(period, str) or not period.strip():
                    raise ValueError(
                        f"tariffs[{index}] step {name!r} tou_kwh requires period"
                    )
                charges.append(UtilityCharge(
                    name=name,
                    kind=UtilityChargeKind.TOU_ENERGY,
                    rate_micros_per_unit=dollars_per_unit_to_micros(value),
                    period=normalize_period(period),
                ))
            elif kind in {"per_kw", "demand_charge"}:
                charges.append(UtilityCharge(
                    name=name,
                    kind=UtilityChargeKind.DEMAND,
                    rate_micros_per_unit=dollars_per_unit_to_micros(value),
                ))
            elif kind in {"per_rkva", "reactive_demand_fee"}:
                charges.append(UtilityCharge(
                    name=name,
                    kind=UtilityChargeKind.REACTIVE,
                    rate_micros_per_unit=dollars_per_unit_to_micros(value),
                ))
            elif kind in {"minimum_charge", "minimum_bill"}:
                minimum_bill_cents = max(
                    minimum_bill_cents,
                    dollars_to_cents(value or 0),
                )
            else:
                raise ValueError(
                    f"tariffs[{index}] step {name!r} has unsupported charge_type {kind!r}"
                )

        tariffs.append(UtilityTariff(
            utility_id=str(entry.get("utility_id") or utility_id).strip(),
            service_class=str(service_class),
            effective_from=str(effective_from),
            effective_to=None if effective_to in (None, "") else str(effective_to),
            charges=tuple(charges),
            source_hash=digest,
            source_locator=f"file://{source.name}#tariffs[{index}]",
            verified=verified,
            minimum_bill_cents=minimum_bill_cents,
            jurisdiction=jurisdiction,
            metadata={"source_file": source.name, "tariff_index": index},
        ))

    return tuple(tariffs)
