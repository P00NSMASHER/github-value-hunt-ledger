"""Scope-bound append-only audit evidence for Freight Recovery pilots.

This is an application-level hash chain. It detects mutation/reordering within
the supplied record set but does not provide independent external timestamping.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Iterable

from freight.contracts import canonical_hash


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


def _required(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " is required")


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
    _required("buyer_id", buyer_id)
    _required("business_unit", business_unit)
    _required("object_id", object_id)
    _required("occurred_at", occurred_at)

    current = tuple(records)
    if current:
        verify_chain(current, buyer_id=buyer_id, business_unit=business_unit)
        previous_hash = current[-1].event_hash
        sequence = current[-1].sequence + 1
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

    for record in records:
        if (record.buyer_id, record.business_unit) != (buyer_id, business_unit):
            raise ValueError("audit record scope mismatch")
        if record.sequence != expected_sequence:
            raise ValueError("audit sequence gap/reorder detected")
        if record.previous_hash != previous_hash:
            raise ValueError("audit previous_hash mismatch")

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
