"""Strict CSV adapter for normalized Freight Recovery invoice charges.

This is an input adapter, not a general spreadsheet importer. It accepts one
explicit v1 schema and turns rows into proof-bound InvoiceCharge objects. Buyer
and business-unit scope come from the authenticated caller, never from the CSV.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import asdict, dataclass
from datetime import date

from freight.contracts import canonical_hash
from freight.finding_factory import InvoiceCharge
from freight.input_guard import assert_accepted


REQUIRED_COLUMNS = (
    "invoice_id",
    "shipment_id",
    "customer_id",
    "carrier_id",
    "currency",
    "charge_id",
    "charge_code",
    "service_date",
    "quantity_units",
    "billed_cents",
)
INTEGER_RE = re.compile(r"^(0|[1-9][0-9]*)$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class InvoiceChargeCSVBatch:
    buyer_id: str
    business_unit: str
    filename: str
    file_sha256: str
    charges: tuple[InvoiceCharge, ...]
    adapter_hash: str


def _required(name: str, value: str | None, row_number: int) -> str:
    if value is None or not isinstance(value, str) or not value.strip():
        raise ValueError(f"row {row_number}: {name} is required")
    return value.strip()


def _integer(name: str, value: str | None, row_number: int, *, positive: bool) -> int:
    text = _required(name, value, row_number)
    if not INTEGER_RE.fullmatch(text):
        raise ValueError(f"row {row_number}: {name} must be an exact unsigned integer")
    parsed = int(text)
    if positive and parsed <= 0:
        raise ValueError(f"row {row_number}: {name} must be positive")
    if parsed > 2**63 - 1:
        raise ValueError(f"row {row_number}: {name} exceeds integer range")
    return parsed


def parse_invoice_charge_csv(
    *,
    filename: str,
    data: bytes,
    buyer_id: str,
    business_unit: str,
) -> InvoiceChargeCSVBatch:
    if not isinstance(buyer_id, str) or not buyer_id.strip():
        raise ValueError("buyer_id is required")
    if not isinstance(business_unit, str) or not business_unit.strip():
        raise ValueError("business_unit is required")
    buyer_id = buyer_id.strip()
    business_unit = business_unit.strip()

    inspection = assert_accepted(filename, data)
    if inspection.detected_format != "csv":
        raise ValueError("invoice charge adapter requires a .csv input")

    text = bytes(data).decode("utf-8-sig", errors="strict")
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    headers = reader.fieldnames
    if headers is None:
        raise ValueError("CSV header row is required")
    if len(headers) != len(set(headers)):
        raise ValueError("duplicate CSV header")
    if set(headers) != set(REQUIRED_COLUMNS) or len(headers) != len(REQUIRED_COLUMNS):
        missing = sorted(set(REQUIRED_COLUMNS) - set(headers))
        extra = sorted(set(headers) - set(REQUIRED_COLUMNS))
        raise ValueError(
            "CSV schema mismatch; missing=" + ",".join(missing) + "; extra=" + ",".join(extra)
        )

    charges: list[InvoiceCharge] = []
    seen_charge_ids: set[str] = set()
    for row in reader:
        row_number = reader.line_num
        if None in row:
            raise ValueError(f"row {row_number}: unexpected extra CSV cells")
        if all(value is None or not str(value).strip() for value in row.values()):
            continue
        if any(value is None for value in row.values()):
            raise ValueError(f"row {row_number}: missing CSV cell")

        invoice_id = _required("invoice_id", row["invoice_id"], row_number)
        shipment_id = _required("shipment_id", row["shipment_id"], row_number)
        customer_id = _required("customer_id", row["customer_id"], row_number)
        carrier_id = _required("carrier_id", row["carrier_id"], row_number)
        currency = _required("currency", row["currency"], row_number).upper()
        charge_id = _required("charge_id", row["charge_id"], row_number)
        charge_code = _required("charge_code", row["charge_code"], row_number).upper()
        service_date = _required("service_date", row["service_date"], row_number)
        quantity_units = _integer("quantity_units", row["quantity_units"], row_number, positive=True)
        billed_cents = _integer("billed_cents", row["billed_cents"], row_number, positive=False)

        if not CURRENCY_RE.fullmatch(currency):
            raise ValueError(f"row {row_number}: currency must be a three-letter code")
        try:
            date.fromisoformat(service_date)
        except ValueError as exc:
            raise ValueError(f"row {row_number}: service_date must be YYYY-MM-DD") from exc
        if charge_id in seen_charge_ids:
            raise ValueError(f"row {row_number}: duplicate charge_id: {charge_id}")
        seen_charge_ids.add(charge_id)

        normalized_row = {
            "invoice_id": invoice_id,
            "shipment_id": shipment_id,
            "customer_id": customer_id,
            "carrier_id": carrier_id,
            "currency": currency,
            "charge_id": charge_id,
            "charge_code": charge_code,
            "service_date": service_date,
            "quantity_units": quantity_units,
            "billed_cents": billed_cents,
        }
        source_hash = canonical_hash({
            "schema": 1,
            "file_sha256": inspection.sha256,
            "row_number": row_number,
            "row": normalized_row,
        })
        charges.append(InvoiceCharge(
            buyer_id=buyer_id,
            business_unit=business_unit,
            source_hash=source_hash,
            **normalized_row,
        ))

    if not charges:
        raise ValueError("CSV must contain at least one invoice charge row")

    charges_tuple = tuple(charges)
    body = {
        "schema": 1,
        "buyer_id": buyer_id,
        "business_unit": business_unit,
        "filename": filename,
        "file_sha256": inspection.sha256,
        "charges": [asdict(charge) for charge in charges_tuple],
    }
    return InvoiceChargeCSVBatch(
        buyer_id=buyer_id,
        business_unit=business_unit,
        filename=filename,
        file_sha256=inspection.sha256,
        charges=charges_tuple,
        adapter_hash=canonical_hash(body),
    )
