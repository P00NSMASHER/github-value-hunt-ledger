"""Strict CSV adapters for Freight Recovery settlement evidence.

These adapters normalize external settlement/remittance events and later
counter-events (returns/reversals) into the persistent settlement-store record
types. Buyer/business-unit scope comes from trusted caller context, never CSV
columns.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from freight.contracts import canonical_hash
from freight.input_guard import assert_accepted
from freight.settlement_store import CounterEventRecord, SettlementEventRecord


SETTLEMENT_COLUMNS = (
    "event_id",
    "reference",
    "payer_id",
    "payee_id",
    "currency",
    "amount_cents",
    "booked_at",
    "source_kind",
)
COUNTER_COLUMNS = (
    "counter_id",
    "original_event_id",
    "currency",
    "amount_cents",
    "observed_at",
    "source_kind",
)
INTEGER_RE = re.compile(r"^[1-9][0-9]*$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
MAX_CENTS = 2**63 - 1


@dataclass(frozen=True)
class SettlementEventCSVBatch:
    buyer_id: str
    business_unit: str
    filename: str
    file_sha256: str
    events: tuple[SettlementEventRecord, ...]
    adapter_hash: str


@dataclass(frozen=True)
class CounterEventCSVBatch:
    buyer_id: str
    business_unit: str
    filename: str
    file_sha256: str
    events: tuple[CounterEventRecord, ...]
    adapter_hash: str


def _scope_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " is required")
    return value.strip()


def _cell(name: str, value: str | None, row_number: int) -> str:
    if value is None or not isinstance(value, str) or not value.strip():
        raise ValueError(f"row {row_number}: {name} is required")
    return value.strip()


def _positive_cents(value: str | None, row_number: int) -> int:
    text = _cell("amount_cents", value, row_number)
    if not INTEGER_RE.fullmatch(text):
        raise ValueError(
            f"row {row_number}: amount_cents must be exact positive integer cents"
        )
    parsed = int(text)
    if parsed > MAX_CENTS:
        raise ValueError(f"row {row_number}: amount_cents exceeds integer range")
    return parsed


def _timestamp(name: str, value: str | None, row_number: int) -> str:
    text = _cell(name, value, row_number)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(
            f"row {row_number}: {name} must be timezone-aware ISO-8601"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"row {row_number}: {name} must be timezone-aware ISO-8601")
    return (
        parsed.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _reader(
    *,
    filename: str,
    data: bytes,
    expected_columns: tuple[str, ...],
):
    inspection = assert_accepted(filename, data)
    if inspection.detected_format != "csv":
        raise ValueError("settlement evidence adapter requires a .csv input")
    text = bytes(data).decode("utf-8-sig", errors="strict")
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    headers = reader.fieldnames
    if headers is None:
        raise ValueError("CSV header row is required")
    if len(headers) != len(set(headers)):
        raise ValueError("duplicate CSV header")
    if set(headers) != set(expected_columns) or len(headers) != len(expected_columns):
        missing = sorted(set(expected_columns) - set(headers))
        extra = sorted(set(headers) - set(expected_columns))
        raise ValueError(
            "CSV schema mismatch; missing=" + ",".join(missing)
            + "; extra=" + ",".join(extra)
        )
    return inspection, reader


def parse_settlement_event_csv(
    *,
    filename: str,
    data: bytes,
    buyer_id: str,
    business_unit: str,
) -> SettlementEventCSVBatch:
    buyer_id = _scope_text("buyer_id", buyer_id)
    business_unit = _scope_text("business_unit", business_unit)
    inspection, reader = _reader(
        filename=filename,
        data=data,
        expected_columns=SETTLEMENT_COLUMNS,
    )

    events: list[SettlementEventRecord] = []
    seen: set[str] = set()
    for row in reader:
        row_number = reader.line_num
        if None in row:
            raise ValueError(f"row {row_number}: unexpected extra CSV cells")
        if all(value is None or not str(value).strip() for value in row.values()):
            continue
        if any(value is None for value in row.values()):
            raise ValueError(f"row {row_number}: missing CSV cell")

        event_id = _cell("event_id", row["event_id"], row_number)
        reference = _cell("reference", row["reference"], row_number)
        payer_id = _cell("payer_id", row["payer_id"], row_number)
        payee_id = _cell("payee_id", row["payee_id"], row_number)
        currency = _cell("currency", row["currency"], row_number).upper()
        amount_cents = _positive_cents(row["amount_cents"], row_number)
        booked_at = _timestamp("booked_at", row["booked_at"], row_number)
        source_kind = _cell("source_kind", row["source_kind"], row_number).upper()

        if not CURRENCY_RE.fullmatch(currency):
            raise ValueError(f"row {row_number}: currency must be a three-letter code")
        if event_id in seen:
            raise ValueError(f"row {row_number}: duplicate event_id: {event_id}")
        seen.add(event_id)

        normalized = {
            "event_id": event_id,
            "reference": reference,
            "payer_id": payer_id,
            "payee_id": payee_id,
            "currency": currency,
            "amount_cents": amount_cents,
            "booked_at": booked_at,
            "source_kind": source_kind,
        }
        source_hash = canonical_hash({
            "schema": 1,
            "buyer_id": buyer_id,
            "business_unit": business_unit,
            "file_sha256": inspection.sha256,
            "row_number": row_number,
            "row": normalized,
        })
        events.append(SettlementEventRecord(
            source_hash=source_hash,
            **normalized,
        ))

    if not events:
        raise ValueError("CSV must contain at least one settlement event row")

    events_tuple = tuple(events)
    body = {
        "schema": 1,
        "buyer_id": buyer_id,
        "business_unit": business_unit,
        "filename": filename,
        "file_sha256": inspection.sha256,
        "events": [asdict(event) for event in events_tuple],
    }
    return SettlementEventCSVBatch(
        buyer_id=buyer_id,
        business_unit=business_unit,
        filename=filename,
        file_sha256=inspection.sha256,
        events=events_tuple,
        adapter_hash=canonical_hash(body),
    )


def parse_counter_event_csv(
    *,
    filename: str,
    data: bytes,
    buyer_id: str,
    business_unit: str,
) -> CounterEventCSVBatch:
    buyer_id = _scope_text("buyer_id", buyer_id)
    business_unit = _scope_text("business_unit", business_unit)
    inspection, reader = _reader(
        filename=filename,
        data=data,
        expected_columns=COUNTER_COLUMNS,
    )

    events: list[CounterEventRecord] = []
    seen: set[str] = set()
    for row in reader:
        row_number = reader.line_num
        if None in row:
            raise ValueError(f"row {row_number}: unexpected extra CSV cells")
        if all(value is None or not str(value).strip() for value in row.values()):
            continue
        if any(value is None for value in row.values()):
            raise ValueError(f"row {row_number}: missing CSV cell")

        counter_id = _cell("counter_id", row["counter_id"], row_number)
        original_event_id = _cell(
            "original_event_id", row["original_event_id"], row_number
        )
        currency = _cell("currency", row["currency"], row_number).upper()
        amount_cents = _positive_cents(row["amount_cents"], row_number)
        observed_at = _timestamp("observed_at", row["observed_at"], row_number)
        source_kind = _cell("source_kind", row["source_kind"], row_number).upper()

        if not CURRENCY_RE.fullmatch(currency):
            raise ValueError(f"row {row_number}: currency must be a three-letter code")
        if counter_id in seen:
            raise ValueError(f"row {row_number}: duplicate counter_id: {counter_id}")
        seen.add(counter_id)

        normalized = {
            "counter_id": counter_id,
            "original_event_id": original_event_id,
            "currency": currency,
            "amount_cents": amount_cents,
            "observed_at": observed_at,
            "source_kind": source_kind,
        }
        source_hash = canonical_hash({
            "schema": 1,
            "buyer_id": buyer_id,
            "business_unit": business_unit,
            "file_sha256": inspection.sha256,
            "row_number": row_number,
            "row": normalized,
        })
        events.append(CounterEventRecord(
            source_hash=source_hash,
            **normalized,
        ))

    if not events:
        raise ValueError("CSV must contain at least one counter event row")

    events_tuple = tuple(events)
    body = {
        "schema": 1,
        "buyer_id": buyer_id,
        "business_unit": business_unit,
        "filename": filename,
        "file_sha256": inspection.sha256,
        "events": [asdict(event) for event in events_tuple],
    }
    return CounterEventCSVBatch(
        buyer_id=buyer_id,
        business_unit=business_unit,
        filename=filename,
        file_sha256=inspection.sha256,
        events=events_tuple,
        adapter_hash=canonical_hash(body),
    )
