"""File ingestion for ConstructionRecovery entitlement and delay evidence."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .construction import (
    CausationReview,
    ConstructionEntitlement,
    ConstructionEvent,
    ConstructionSettlement,
    EventActivityMapping,
    ScheduleActivity,
    ScheduleRelationship,
    ScheduleVersion,
)


TRUE_VALUES = {"1", "true", "yes", "y", "accepted"}
FALSE_VALUES = {"0", "false", "no", "n", "rejected"}


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


def _boolean(value: str, *, field: str, row_number: int) -> bool:
    text = (value or "").strip().lower()
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    raise ValueError(f"row {row_number}: {field} must be boolean-like")


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


def _required(row: Mapping[str, str], column: str, row_number: int) -> str:
    if column not in row:
        raise ValueError(f"missing required CSV column {column!r}")
    value = row.get(column)
    if value is None or not str(value).strip():
        raise ValueError(f"row {row_number}: {column} is required")
    return str(value).strip()


def _optional(row: Mapping[str, str], column: str) -> str | None:
    value = row.get(column)
    if value is None or not str(value).strip():
        return None
    return str(value).strip()


def load_construction_entitlements_csv(
    path: str | Path,
    *,
    verified: bool = False,
) -> tuple[ConstructionEntitlement, ...]:
    source, digest, rows = _read_csv(path)
    result: list[ConstructionEntitlement] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(ConstructionEntitlement(
            entitlement_id=_required(row, "Entitlement_ID", row_number),
            claimant_id=_required(row, "Claimant_ID", row_number),
            project_id=_required(row, "Project_ID", row_number),
            counterparty_id=_required(row, "Counterparty_ID", row_number),
            change_id=_required(row, "Change_ID", row_number),
            event_id=_required(row, "Event_ID", row_number),
            entitled_cents=_money_to_cents(
                _required(row, "Entitled_Amount", row_number)
            ),
            effective_date=_required(row, "Effective_Date", row_number),
            entitlement_basis=_required(row, "Entitlement_Basis", row_number),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            entitlement_reviewer_id=_optional(row, "Entitlement_Reviewer_ID"),
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_construction_events_csv(
    path: str | Path,
    *,
    verified: bool = False,
) -> tuple[ConstructionEvent, ...]:
    source, digest, rows = _read_csv(path)
    result: list[ConstructionEvent] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(ConstructionEvent(
            event_id=_required(row, "Event_ID", row_number),
            project_id=_required(row, "Project_ID", row_number),
            event_date=_required(row, "Event_Date", row_number),
            description=_required(row, "Description", row_number),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_event_activity_mappings_csv(
    path: str | Path,
    *,
    verified: bool = False,
) -> tuple[EventActivityMapping, ...]:
    source, digest, rows = _read_csv(path)
    result: list[EventActivityMapping] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(EventActivityMapping(
            mapping_id=_required(row, "Mapping_ID", row_number),
            event_id=_required(row, "Event_ID", row_number),
            baseline_activity_id=_required(
                row, "Baseline_Activity_ID", row_number
            ),
            update_activity_id=_required(row, "Update_Activity_ID", row_number),
            mapping_basis=_required(row, "Mapping_Basis", row_number),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_schedule_versions_json(
    path: str | Path,
    *,
    verified: bool = False,
) -> tuple[ScheduleVersion, ...]:
    source = Path(path)
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{source} must be valid UTF-8 JSON") from exc

    versions = payload.get("versions") if isinstance(payload, dict) else payload
    if not isinstance(versions, list):
        raise ValueError("schedule JSON must be a list or {'versions': [...]}")

    result: list[ScheduleVersion] = []
    for version_index, raw_version in enumerate(versions):
        if not isinstance(raw_version, dict):
            raise ValueError(f"versions[{version_index}] must be an object")
        raw_activities = raw_version.get("activities")
        raw_relationships = raw_version.get("relationships", [])
        if not isinstance(raw_activities, list) or not raw_activities:
            raise ValueError(
                f"versions[{version_index}].activities must be non-empty list"
            )
        if not isinstance(raw_relationships, list):
            raise ValueError(
                f"versions[{version_index}].relationships must be a list"
            )

        activities: list[ScheduleActivity] = []
        for activity_index, raw_activity in enumerate(raw_activities):
            if not isinstance(raw_activity, dict):
                raise ValueError(
                    f"versions[{version_index}].activities[{activity_index}] "
                    "must be an object"
                )
            duration = raw_activity.get("duration_days")
            if type(duration) is not int:
                raise ValueError(
                    f"versions[{version_index}].activities[{activity_index}]."
                    "duration_days must be integer"
                )
            activities.append(ScheduleActivity(
                activity_id=str(raw_activity.get("activity_id") or "").strip(),
                name=str(raw_activity.get("name") or "").strip(),
                duration_days=duration,
            ))

        relationships: list[ScheduleRelationship] = []
        for rel_index, raw_rel in enumerate(raw_relationships):
            if not isinstance(raw_rel, dict):
                raise ValueError(
                    f"versions[{version_index}].relationships[{rel_index}] "
                    "must be an object"
                )
            lag = raw_rel.get("lag_days", 0)
            if type(lag) is not int:
                raise ValueError(
                    f"versions[{version_index}].relationships[{rel_index}]."
                    "lag_days must be integer"
                )
            relationships.append(ScheduleRelationship(
                predecessor_id=str(
                    raw_rel.get("predecessor_id") or ""
                ).strip(),
                successor_id=str(raw_rel.get("successor_id") or "").strip(),
                lag_days=lag,
                relationship_type=str(
                    raw_rel.get("relationship_type") or "FS"
                ).strip().upper(),
            ))

        result.append(ScheduleVersion(
            version_id=str(raw_version.get("version_id") or "").strip(),
            project_id=str(raw_version.get("project_id") or "").strip(),
            data_date=str(raw_version.get("data_date") or "").strip(),
            label=(
                None
                if raw_version.get("label") in (None, "")
                else str(raw_version.get("label")).strip()
            ),
            activities=tuple(activities),
            relationships=tuple(relationships),
            source_hash=digest,
            source_locator=f"file://{source.name}#versions[{version_index}]",
            verified=verified,
            metadata={
                "source_file": source.name,
                "version_index": version_index,
            },
        ))
    return tuple(result)


def load_causation_reviews_csv(
    path: str | Path,
    *,
    verified: bool = False,
) -> tuple[CausationReview, ...]:
    source, digest, rows = _read_csv(path)
    result: list[CausationReview] = []
    for row_number, row in enumerate(rows, start=2):
        raw_delay = _required(row, "Accepted_Delay_Days", row_number)
        try:
            delay_days = int(raw_delay)
        except ValueError as exc:
            raise ValueError(
                f"row {row_number}: Accepted_Delay_Days must be integer"
            ) from exc
        result.append(CausationReview(
            review_id=_required(row, "Review_ID", row_number),
            entitlement_id=_required(row, "Entitlement_ID", row_number),
            event_id=_required(row, "Event_ID", row_number),
            baseline_version_id=_required(
                row, "Baseline_Version_ID", row_number
            ),
            update_version_id=_required(row, "Update_Version_ID", row_number),
            accepted_causation=_boolean(
                _required(row, "Accepted_Causation", row_number),
                field="Accepted_Causation",
                row_number=row_number,
            ),
            accepted_delay_days=delay_days,
            review_date=_required(row, "Review_Date", row_number),
            source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}",
            verified=verified,
            qualified_reviewer_id=_optional(row, "Qualified_Reviewer_ID"),
            metadata={"source_file": source.name, "row_number": row_number},
        ))
    return tuple(result)


def load_construction_settlements_csv(
    path: str | Path,
    *,
    verified: bool = False,
) -> tuple[ConstructionSettlement, ...]:
    source, digest, rows = _read_csv(path)
    result: list[ConstructionSettlement] = []
    for row_number, row in enumerate(rows, start=2):
        result.append(ConstructionSettlement(
            settlement_id=_required(row, "Settlement_ID", row_number),
            entitlement_id=_required(row, "Entitlement_ID", row_number),
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
