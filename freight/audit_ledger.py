"""Scope-bound append-only audit evidence for Freight Recovery pilots.

This is an application-level hash chain. It detects mutation/reordering within
the supplied record set but does not provide independent external timestamping.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable

from freight.contracts import canonical_hash


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class AuditEventType(str, Enum):
    SOURCE_PRESENT = "SOURCE_PRESENT"
    SOURCE_VERIFIED_EMPTY = "SOURCE_VERIFIED_EMPTY"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    PACKAGE_SEALED = "PACKAGE_SEALED"
    TRUTH_FROZEN = "TRUTH_FROZEN"
    INCUMBENT_OPENED = "INCUMBENT_OPENED"
    REPORT_ISSUED = "REPORT_ISSUED"
    DELETE_REQUESTED = "DELETE_REQUESTED"
    DELETE_CONFIRMED = "DELETE_CONFIRMED"
    DELETE_UNKNOWN = "DELETE_UNKNOWN"


@dataclass(frozen=True)
class AuditRecord:
    sequence: int
    buyer_id: str
    business_unit: str
    event_type: AuditEventType
    object_id: str
    occurred_at: str
    evidence_hash: str | None
    previous_hash: str | None
    event_hash: str


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(name + " cannot contain control characters")
    return normalized


def _timestamp(value: str) -> str:
    text = _required("occurred_at", value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("occurred_at must be a timezone-aware ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("occurred_at must be timezone-aware")
    return (
        parsed.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _evidence_hash(value: str | None) -> None:
    if value is not None and not SHA256_RE.fullmatch(value):
        raise ValueError("evidence_hash must be lowercase SHA-256")


def append_record(
    records: Iterable[AuditRecord],
    *,
    buyer_id: str,
    business_unit: str,
    event_type: AuditEventType,
    object_id: str,
    occurred_at: str,
    evidence_hash: str | None = None,
) -> tuple[AuditRecord, ...]:
    buyer_id = _required("buyer_id", buyer_id)
    business_unit = _required("business_unit", business_unit)
    object_id = _required("object_id", object_id)
    occurred_at = _timestamp(occurred_at)
    if not isinstance(event_type, AuditEventType):
        raise ValueError("event_type must be an AuditEventType")
    _evidence_hash(evidence_hash)

    current = tuple(records)
    if current:
        verify_chain(current, buyer_id=buyer_id, business_unit=business_unit)
        previous_hash = current[-1].event_hash
        sequence = current[-1].sequence + 1
        if occurred_at < current[-1].occurred_at:
            raise ValueError("audit occurred_at values must be nondecreasing")
    else:
        previous_hash = None
        sequence = 1

    body = {
        "schema": 1,
        "sequence": sequence,
        "buyer_id": buyer_id,
        "business_unit": business_unit,
        "event_type": event_type.value,
        "object_id": object_id,
        "occurred_at": occurred_at,
        "evidence_hash": evidence_hash,
        "previous_hash": previous_hash,
    }
    record = AuditRecord(
        sequence=sequence,
        buyer_id=buyer_id,
        business_unit=business_unit,
        event_type=event_type,
        object_id=object_id,
        occurred_at=occurred_at,
        evidence_hash=evidence_hash,
        previous_hash=previous_hash,
        event_hash=canonical_hash(body),
    )
    return current + (record,)


def verify_chain(
    records: Iterable[AuditRecord],
    *,
    buyer_id: str,
    business_unit: str,
) -> None:
    previous_hash = None
    expected_sequence = 1
    previous_time = None

    for record in records:
        if (record.buyer_id, record.business_unit) != (buyer_id, business_unit):
            raise ValueError("audit record scope mismatch")
        if record.sequence != expected_sequence:
            raise ValueError("audit sequence gap/reorder detected")
        if record.previous_hash != previous_hash:
            raise ValueError("audit previous_hash mismatch")
        if not isinstance(record.event_type, AuditEventType):
            raise ValueError("audit event type is invalid")
        canonical_time = _timestamp(record.occurred_at)
        if canonical_time != record.occurred_at:
            raise ValueError("audit occurred_at is not canonical UTC")
        if previous_time is not None and canonical_time < previous_time:
            raise ValueError("audit occurred_at values must be nondecreasing")
        _evidence_hash(record.evidence_hash)

        body = {
            "schema": 1,
            "sequence": record.sequence,
            "buyer_id": record.buyer_id,
            "business_unit": record.business_unit,
            "event_type": record.event_type.value,
            "object_id": record.object_id,
            "occurred_at": record.occurred_at,
            "evidence_hash": record.evidence_hash,
            "previous_hash": record.previous_hash,
        }
        if canonical_hash(body) != record.event_hash:
            raise ValueError("audit event hash mismatch")

        previous_hash = record.event_hash
        previous_time = canonical_time
        expected_sequence += 1


def chain_head(records: Iterable[AuditRecord]) -> str | None:
    current = tuple(records)
    return current[-1].event_hash if current else None


def export_records(records: Iterable[AuditRecord]) -> list[dict]:
    return [
        {
            **asdict(record),
            "event_type": record.event_type.value,
        }
        for record in records
    ]
