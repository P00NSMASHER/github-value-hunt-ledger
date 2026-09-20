"""CENSUS/SCOPE/PROOF data-lifecycle state for Freight Recovery pilots.

Absence is never treated as deletion. Deletion is confirmed only by explicit
external evidence; ambiguous results remain DELETE_UNKNOWN.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Iterable

from freight.contracts import canonical_hash
from freight.pilot_package import DataRoomManifest


class LifecycleState(str, Enum):
    PRESENT = "PRESENT"
    DELETE_REQUESTED = "DELETE_REQUESTED"
    DELETE_CONFIRMED = "DELETE_CONFIRMED"
    DELETE_UNKNOWN = "DELETE_UNKNOWN"


class ObservationStatus(str, Enum):
    PRESENT = "PRESENT"
    VERIFIED_EMPTY = "VERIFIED_EMPTY"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class LifecycleItem:
    buyer_id: str
    business_unit: str
    source_id: str
    source_hash: str
    ingested_at: str
    retention_days: int
    delete_after: str
    state: LifecycleState
    state_evidence_hash: str | None
    state_hash: str


@dataclass(frozen=True)
class SourceObservationReceipt:
    buyer_id: str
    business_unit: str
    source_id: str
    observed_at: str
    status: ObservationStatus
    observation_hash: str
    completeness_evidence_hash: str | None = None


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp is required")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _item_hash(item_without_hash: dict) -> str:
    return canonical_hash({"schema": 1, **item_without_hash})


def _make_item(**kwargs) -> LifecycleItem:
    body = dict(kwargs)
    return LifecycleItem(**body, state_hash=_item_hash({
        **body,
        "state": body["state"].value,
    }))


def build_lifecycle(
    manifest: DataRoomManifest,
    *,
    ingested_at: str,
) -> tuple[LifecycleItem, ...]:
    start = _parse_utc(ingested_at)
    items = []
    for entry in manifest.entries:
        if (entry.buyer_id, entry.business_unit) != (
            manifest.buyer_id,
            manifest.business_unit,
        ):
            raise ValueError("data-room source scope mismatch")
        delete_after = _iso_utc(start + timedelta(days=entry.retention_days))
        items.append(
            _make_item(
                buyer_id=manifest.buyer_id,
                business_unit=manifest.business_unit,
                source_id=entry.source_id,
                source_hash=entry.source_hash,
                ingested_at=_iso_utc(start),
                retention_days=entry.retention_days,
                delete_after=delete_after,
                state=LifecycleState.PRESENT,
                state_evidence_hash=None,
            )
        )
    return tuple(sorted(items, key=lambda x: x.source_id))


def _transition(
    item: LifecycleItem,
    *,
    expected_states: set[LifecycleState],
    new_state: LifecycleState,
    evidence_hash: str | None,
) -> LifecycleItem:
    if item.state not in expected_states:
        raise ValueError(
            f"invalid lifecycle transition {item.state.value}->{new_state.value}"
        )
    return _make_item(
        buyer_id=item.buyer_id,
        business_unit=item.business_unit,
        source_id=item.source_id,
        source_hash=item.source_hash,
        ingested_at=item.ingested_at,
        retention_days=item.retention_days,
        delete_after=item.delete_after,
        state=new_state,
        state_evidence_hash=evidence_hash,
    )


def request_delete(item: LifecycleItem, request_hash: str) -> LifecycleItem:
    if not request_hash:
        raise ValueError("delete request evidence hash required")
    return _transition(
        item,
        expected_states={LifecycleState.PRESENT, LifecycleState.DELETE_UNKNOWN},
        new_state=LifecycleState.DELETE_REQUESTED,
        evidence_hash=request_hash,
    )


def confirm_delete(item: LifecycleItem, confirmation_hash: str) -> LifecycleItem:
    if not confirmation_hash:
        raise ValueError("external deletion confirmation hash required")
    return _transition(
        item,
        expected_states={LifecycleState.DELETE_REQUESTED, LifecycleState.DELETE_UNKNOWN},
        new_state=LifecycleState.DELETE_CONFIRMED,
        evidence_hash=confirmation_hash,
    )


def mark_delete_unknown(item: LifecycleItem, evidence_hash: str | None = None) -> LifecycleItem:
    return _transition(
        item,
        expected_states={LifecycleState.DELETE_REQUESTED},
        new_state=LifecycleState.DELETE_UNKNOWN,
        evidence_hash=evidence_hash,
    )


def retention_due(
    items: Iterable[LifecycleItem],
    *,
    as_of: str,
) -> tuple[LifecycleItem, ...]:
    now = _parse_utc(as_of)
    due = []
    for item in items:
        if item.state is LifecycleState.DELETE_CONFIRMED:
            continue
        if _parse_utc(item.delete_after) <= now:
            due.append(item)
    return tuple(sorted(due, key=lambda x: x.source_id))


def observe_source(
    *,
    buyer_id: str,
    business_unit: str,
    source_id: str,
    observed_at: str,
    status: ObservationStatus,
    evidence_hash: str,
    completeness_evidence_hash: str | None = None,
) -> SourceObservationReceipt:
    _parse_utc(observed_at)
    if not evidence_hash:
        raise ValueError("observation evidence hash required")
    if status is ObservationStatus.VERIFIED_EMPTY and not completeness_evidence_hash:
        raise ValueError("VERIFIED_EMPTY requires completeness evidence")

    body = {
        "schema": 1,
        "buyer_id": buyer_id,
        "business_unit": business_unit,
        "source_id": source_id,
        "observed_at": observed_at,
        "status": status.value,
        "evidence_hash": evidence_hash,
        "completeness_evidence_hash": completeness_evidence_hash,
    }
    return SourceObservationReceipt(
        buyer_id=buyer_id,
        business_unit=business_unit,
        source_id=source_id,
        observed_at=observed_at,
        status=status,
        observation_hash=canonical_hash(body),
        completeness_evidence_hash=completeness_evidence_hash,
    )


def verify_item(item: LifecycleItem) -> None:
    body = asdict(item)
    body.pop("state_hash")
    body["state"] = item.state.value
    if _item_hash(body) != item.state_hash:
        raise ValueError("lifecycle state hash mismatch")
