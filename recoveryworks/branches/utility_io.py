"""File ingestion for UtilityRecovery bills and simple tariff definitions.

The tariff loader accepts the simple logic-step shape used by the discovered
utility-billing prototype, but rejects formulas, conditions, tier dictionaries,
and unknown charge types. Those need an explicit future DSL implementation.
"""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .utility import UtilityBill, UtilityCharge, UtilityChargeKind, UtilityTariff


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
}


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

    result: list[UtilityBill] = []
    for row_number, row in enumerate(reader, start=2):
        def req(key: str) -> str:
            column = columns[key]
            value = row.get(column)
            if value is None or not str(value).strip():
                raise ValueError(f"row {row_number}: {column} is required")
            return str(value).strip()

        def optional(key: str, default: str = "0") -> str:
            column = columns.get(key)
            if not column:
                return default
            value = row.get(column)
            return str(value).strip() if value is not None and str(value).strip() else default

        result.append(UtilityBill(
            bill_id=req("bill_id"),
            utility_id=req("utility_id"),
            account_id=req("account_id"),
            service_class=req("service_class"),
            bill_date=req("bill_date"),
            actual_cents=dollars_to_cents(req("actual")),
            billed_kwh=optional("kwh"),
            billed_demand_kw=optional("demand_kw"),
            billed_reactive_kva=optional("reactive_kva"),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
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
    """Load deterministic scalar tariff steps from a JSON extraction output.

    Supported charge_type values:
    fixed_fee, per_kwh/energy_charge, per_kw/demand_charge,
    per_rkva/reactive_demand_fee, minimum_charge/minimum_bill.

    Any condition other than "Always", formula, dict-valued tier, or unknown
    charge type fails closed.
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
                raise ValueError(f"tariffs[{index}].logic_steps[{step_index}] must be an object")
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
            if isinstance(value, dict):
                raise ValueError(
                    f"tariffs[{index}] step {name!r} uses unsupported tier/voltage dictionary"
                )
            kind = str(step.get("charge_type") or "").strip().lower()

            if kind == "fixed_fee":
                charges.append(UtilityCharge(
                    name=name,
                    kind=UtilityChargeKind.FIXED,
                    amount_cents=dollars_to_cents(value or 0),
                ))
            elif kind in {"per_kwh", "energy_charge"}:
                charges.append(UtilityCharge(
                    name=name,
                    kind=UtilityChargeKind.ENERGY,
                    rate_micros_per_unit=dollars_per_unit_to_micros(value),
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
                minimum_bill_cents = max(minimum_bill_cents, dollars_to_cents(value or 0))
            else:
                raise ValueError(
                    f"tariffs[{index}] step {name!r} has unsupported charge_type {kind!r}"
                )

        tariffs.append(UtilityTariff(
            utility_id=utility_id.strip(),
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
