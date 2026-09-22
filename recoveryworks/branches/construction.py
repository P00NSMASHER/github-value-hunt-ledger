"""ConstructionRecovery proof-bound entitlement and delay-impact engine.

The engine separates five proof planes:
1. reviewed contract/change-order entitlement and dollar amount;
2. contemporaneous delay event evidence;
3. explicit event-to-schedule-activity mapping;
4. versioned CPM schedule impact;
5. qualified causation review.

CPM math is deterministic and does not decide legal/contract causation. A
construction finding can become VALIDATED only when the entitlement source,
event/mapping, both schedule versions, qualified causation review, and settlement
evidence are all verified.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef, canonical_hash

CPM_ENGINE_ID = "recoveryworks.fs_cpm"
CPM_ENGINE_VERSION = "1"
CPM_METHOD = "finish_to_start_integer_day_cpm"


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _iso_date(name: str, value: str) -> date:
    text = _required(name, value)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _cents(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be non-negative integer cents")
    return value


def _days(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be non-negative integer days")
    return value


@dataclass(frozen=True)
class ScheduleActivity:
    activity_id: str
    name: str
    duration_days: int

    def __post_init__(self) -> None:
        _required("activity_id", self.activity_id)
        _required("name", self.name)
        _days("duration_days", self.duration_days)


@dataclass(frozen=True)
class ScheduleRelationship:
    predecessor_id: str
    successor_id: str
    lag_days: int = 0
    relationship_type: str = "FS"

    def __post_init__(self) -> None:
        _required("predecessor_id", self.predecessor_id)
        _required("successor_id", self.successor_id)
        if self.predecessor_id == self.successor_id:
            raise ValueError("schedule relationship cannot be self-referential")
        _days("lag_days", self.lag_days)
        if self.relationship_type != "FS":
            raise ValueError("only finish-to-start (FS) relationships are supported")


@dataclass(frozen=True)
class ScheduleVersion:
    version_id: str
    project_id: str
    data_date: str
    activities: tuple[ScheduleActivity, ...]
    relationships: tuple[ScheduleRelationship, ...]
    source_hash: str
    source_locator: str
    verified: bool
    label: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("version_id", "project_id", "data_date", "source_hash", "source_locator"):
            _required(name, getattr(self, name))
        _iso_date("data_date", self.data_date)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        if not self.activities:
            raise ValueError("schedule version requires at least one activity")
        ids = [activity.activity_id for activity in self.activities]
        if len(ids) != len(set(ids)):
            raise ValueError("schedule version contains duplicate activity_id")
        valid_ids = set(ids)
        for rel in self.relationships:
            if rel.predecessor_id not in valid_ids:
                raise ValueError(
                    f"relationship predecessor {rel.predecessor_id!r} is missing"
                )
            if rel.successor_id not in valid_ids:
                raise ValueError(
                    f"relationship successor {rel.successor_id!r} is missing"
                )

    @property
    def topology_hash(self) -> str:
        """Canonical network fingerprint for this normalized schedule version."""
        return canonical_hash({
            "schema": 1,
            "activities": [
                {
                    "activity_id": activity.activity_id,
                    "duration_days": activity.duration_days,
                }
                for activity in sorted(self.activities, key=lambda item: item.activity_id)
            ],
            "relationships": [
                {
                    "predecessor_id": rel.predecessor_id,
                    "successor_id": rel.successor_id,
                    "relationship_type": rel.relationship_type,
                    "lag_days": rel.lag_days,
                }
                for rel in sorted(
                    self.relationships,
                    key=lambda item: (
                        item.predecessor_id,
                        item.successor_id,
                        item.relationship_type,
                        item.lag_days,
                    ),
                )
            ],
        })

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"construction-schedule:{self.version_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="construction_schedule_version",
            verified=self.verified,
            metadata={
                "project_id": self.project_id,
                "version_id": self.version_id,
                "data_date": self.data_date,
                "label": self.label,
                "activity_count": len(self.activities),
                "relationship_count": len(self.relationships),
                "topology_hash": self.topology_hash,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class CPMActivityResult:
    activity_id: str
    earliest_start: int
    earliest_finish: int
    latest_start: int
    latest_finish: int
    total_float: int
    critical: bool


@dataclass(frozen=True)
class CPMResult:
    version_id: str
    project_duration_days: int
    activities: Mapping[str, CPMActivityResult]
    critical_activity_ids: tuple[str, ...]
    manifest: Mapping[str, Any]


def calculate_cpm(version: ScheduleVersion) -> CPMResult:
    """Calculate deterministic finish-to-start CPM dates in integer project days."""
    by_id = {activity.activity_id: activity for activity in version.activities}
    incoming: dict[str, list[ScheduleRelationship]] = {
        activity_id: [] for activity_id in by_id
    }
    outgoing: dict[str, list[ScheduleRelationship]] = {
        activity_id: [] for activity_id in by_id
    }
    indegree = {activity_id: 0 for activity_id in by_id}

    seen_relationships: set[tuple[str, str, int, str]] = set()
    for rel in version.relationships:
        identity = (
            rel.predecessor_id,
            rel.successor_id,
            rel.lag_days,
            rel.relationship_type,
        )
        if identity in seen_relationships:
            continue
        seen_relationships.add(identity)
        incoming[rel.successor_id].append(rel)
        outgoing[rel.predecessor_id].append(rel)
        indegree[rel.successor_id] += 1

    ready = sorted(activity_id for activity_id, degree in indegree.items() if degree == 0)
    order: list[str] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for rel in sorted(
            outgoing[current],
            key=lambda item: (item.successor_id, item.lag_days),
        ):
            indegree[rel.successor_id] -= 1
            if indegree[rel.successor_id] == 0:
                ready.append(rel.successor_id)
                ready.sort()

    if len(order) != len(by_id):
        raise ValueError("schedule contains a relationship cycle")

    earliest_start: dict[str, int] = {}
    earliest_finish: dict[str, int] = {}
    for activity_id in order:
        starts = [
            earliest_finish[rel.predecessor_id] + rel.lag_days
            for rel in incoming[activity_id]
        ]
        es = max(starts, default=0)
        ef = es + by_id[activity_id].duration_days
        earliest_start[activity_id] = es
        earliest_finish[activity_id] = ef

    project_duration = max(earliest_finish.values(), default=0)
    latest_start: dict[str, int] = {}
    latest_finish: dict[str, int] = {}

    for activity_id in reversed(order):
        successors = outgoing[activity_id]
        if successors:
            lf = min(
                latest_start[rel.successor_id] - rel.lag_days
                for rel in successors
            )
        else:
            lf = project_duration
        ls = lf - by_id[activity_id].duration_days
        latest_finish[activity_id] = lf
        latest_start[activity_id] = ls

    results: dict[str, CPMActivityResult] = {}
    critical: list[str] = []
    for activity_id in order:
        total_float = latest_start[activity_id] - earliest_start[activity_id]
        is_critical = total_float == 0
        if is_critical:
            critical.append(activity_id)
        results[activity_id] = CPMActivityResult(
            activity_id=activity_id,
            earliest_start=earliest_start[activity_id],
            earliest_finish=earliest_finish[activity_id],
            latest_start=latest_start[activity_id],
            latest_finish=latest_finish[activity_id],
            total_float=total_float,
            critical=is_critical,
        )

    return CPMResult(
        version_id=version.version_id,
        project_duration_days=project_duration,
        activities=results,
        critical_activity_ids=tuple(sorted(critical)),
        manifest={
            "engine_id": CPM_ENGINE_ID,
            "engine_version": CPM_ENGINE_VERSION,
            "method": CPM_METHOD,
            "schedule_version_id": version.version_id,
            "schedule_source_hash": version.source_hash,
            "topology_hash": version.topology_hash,
            "data_date": version.data_date,
            "activity_count": len(version.activities),
            "relationship_count": len(version.relationships),
        },
    )


@dataclass(frozen=True)
class ConstructionEntitlement:
    entitlement_id: str
    claimant_id: str
    project_id: str
    counterparty_id: str
    change_id: str
    event_id: str
    entitled_cents: int
    effective_date: str
    entitlement_basis: str
    source_hash: str
    source_locator: str
    verified: bool
    entitlement_reviewer_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "entitlement_id", "claimant_id", "project_id", "counterparty_id", "change_id",
            "event_id", "effective_date", "entitlement_basis",
            "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _iso_date("effective_date", self.effective_date)
        _cents("entitled_cents", self.entitled_cents)
        if self.entitled_cents <= 0:
            raise ValueError("entitled_cents must be positive")
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        if self.verified and not (
            isinstance(self.entitlement_reviewer_id, str)
            and self.entitlement_reviewer_id.strip()
        ):
            raise ValueError(
                "verified construction entitlement requires entitlement_reviewer_id"
            )

    def rule_ref(self) -> RuleRef:
        identity = {
            "schema": 1,
            "entitlement_id": self.entitlement_id,
            "claimant_id": self.claimant_id,
            "project_id": self.project_id,
            "counterparty_id": self.counterparty_id,
            "change_id": self.change_id,
            "event_id": self.event_id,
            "entitled_cents": self.entitled_cents,
            "effective_date": self.effective_date,
            "entitlement_basis": self.entitlement_basis,
            "source_hash": self.source_hash,
            "entitlement_reviewer_id": self.entitlement_reviewer_id,
        }
        return RuleRef(
            rule_id="construction-entitlement:" + canonical_hash(identity),
            source_hash=self.source_hash,
            effective_from=self.effective_date,
            effective_to=None,
            verified_controlling=self.verified,
            source_locator=self.source_locator,
            metadata={
                "kind": "reviewed_construction_entitlement",
                "claimant_id": self.claimant_id,
                "project_id": self.project_id,
                "change_id": self.change_id,
                "event_id": self.event_id,
                "entitled_cents": self.entitled_cents,
                "entitlement_basis": self.entitlement_basis,
                "entitlement_reviewer_id": self.entitlement_reviewer_id,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class ConstructionEvent:
    event_id: str
    project_id: str
    event_date: str
    description: str
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "event_id", "project_id", "event_date", "description",
            "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _iso_date("event_date", self.event_date)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"construction-event:{self.event_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="construction_delay_event",
            verified=self.verified,
            metadata={
                "project_id": self.project_id,
                "event_date": self.event_date,
                "description": self.description,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class EventActivityMapping:
    mapping_id: str
    event_id: str
    baseline_activity_id: str
    update_activity_id: str
    mapping_basis: str
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "mapping_id", "event_id", "baseline_activity_id",
            "update_activity_id", "mapping_basis", "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"construction-mapping:{self.mapping_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="construction_event_activity_mapping",
            verified=self.verified,
            metadata={
                "event_id": self.event_id,
                "baseline_activity_id": self.baseline_activity_id,
                "update_activity_id": self.update_activity_id,
                "mapping_basis": self.mapping_basis,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class CausationReview:
    review_id: str
    entitlement_id: str
    event_id: str
    baseline_version_id: str
    update_version_id: str
    accepted_causation: bool
    accepted_delay_days: int
    review_date: str
    source_hash: str
    source_locator: str
    verified: bool
    qualified_reviewer_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "review_id", "entitlement_id", "event_id", "baseline_version_id",
            "update_version_id", "review_date", "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _iso_date("review_date", self.review_date)
        if type(self.accepted_causation) is not bool:
            raise ValueError("accepted_causation must be boolean")
        _days("accepted_delay_days", self.accepted_delay_days)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        if self.verified and not (
            isinstance(self.qualified_reviewer_id, str)
            and self.qualified_reviewer_id.strip()
        ):
            raise ValueError(
                "verified causation review requires qualified_reviewer_id"
            )
        if self.baseline_version_id == self.update_version_id:
            raise ValueError("baseline and update schedule versions must differ")
        if self.accepted_causation and self.accepted_delay_days <= 0:
            raise ValueError(
                "accepted causation requires positive accepted_delay_days"
            )

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"construction-causation:{self.review_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="qualified_construction_causation_review",
            verified=self.verified,
            metadata={
                "entitlement_id": self.entitlement_id,
                "event_id": self.event_id,
                "baseline_version_id": self.baseline_version_id,
                "update_version_id": self.update_version_id,
                "accepted_causation": self.accepted_causation,
                "accepted_delay_days": self.accepted_delay_days,
                "qualified_reviewer_id": self.qualified_reviewer_id,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class ConstructionSettlement:
    settlement_id: str
    entitlement_id: str
    amount_received_cents: int
    settlement_date: str
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "settlement_id", "entitlement_id", "settlement_date",
            "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _iso_date("settlement_date", self.settlement_date)
        _cents("amount_received_cents", self.amount_received_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"construction-settlement:{self.settlement_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="construction_settlement",
            verified=self.verified,
            metadata={
                "entitlement_id": self.entitlement_id,
                "settlement_date": self.settlement_date,
                "amount_received_cents": self.amount_received_cents,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class ConstructionAuditException:
    reference: str
    code: str
    detail: str


@dataclass(frozen=True)
class ConstructionAuditBatch:
    observations: tuple[RecoveryObservation, ...]
    exceptions: tuple[ConstructionAuditException, ...]


def _unique_index(
    items: Iterable[Any],
    *,
    key_attr: str,
    duplicate_code: str,
) -> tuple[dict[str, Any], list[ConstructionAuditException]]:
    grouped: dict[str, list[Any]] = defaultdict(list)
    for item in items:
        grouped[getattr(item, key_attr)].append(item)
    result: dict[str, Any] = {}
    exceptions: list[ConstructionAuditException] = []
    for key in sorted(grouped):
        values = grouped[key]
        if len(values) != 1:
            exceptions.append(ConstructionAuditException(
                key,
                duplicate_code,
                f"{key_attr} appears {len(values)} times; ambiguous records excluded",
            ))
            continue
        result[key] = values[0]
    return result, exceptions


def audit_construction_recovery(
    *,
    client_id: str,
    entitlements: Iterable[ConstructionEntitlement],
    events: Iterable[ConstructionEvent],
    mappings: Iterable[EventActivityMapping],
    schedules: Iterable[ScheduleVersion],
    causation_reviews: Iterable[CausationReview],
    settlements: Iterable[ConstructionSettlement],
    currency: str = "USD",
) -> ConstructionAuditBatch:
    client_id = _required("client_id", client_id)
    currency = _required("currency", currency).upper()

    entitlement_by_id, exceptions = _unique_index(
        entitlements,
        key_attr="entitlement_id",
        duplicate_code="DUPLICATE_ENTITLEMENT_ID",
    )
    event_by_id, more = _unique_index(
        events,
        key_attr="event_id",
        duplicate_code="DUPLICATE_EVENT_ID",
    )
    exceptions.extend(more)
    mapping_by_event, more = _unique_index(
        mappings,
        key_attr="event_id",
        duplicate_code="AMBIGUOUS_EVENT_ACTIVITY_MAPPING",
    )
    exceptions.extend(more)
    schedule_by_id, more = _unique_index(
        schedules,
        key_attr="version_id",
        duplicate_code="DUPLICATE_SCHEDULE_VERSION_ID",
    )
    exceptions.extend(more)
    review_by_entitlement, more = _unique_index(
        causation_reviews,
        key_attr="entitlement_id",
        duplicate_code="AMBIGUOUS_CAUSATION_REVIEW",
    )
    exceptions.extend(more)

    settlements_by_entitlement: dict[str, list[ConstructionSettlement]] = defaultdict(list)
    seen_settlements: set[str] = set()
    duplicate_settlements: set[str] = set()
    for settlement in settlements:
        if settlement.settlement_id in seen_settlements:
            duplicate_settlements.add(settlement.settlement_id)
        seen_settlements.add(settlement.settlement_id)
        settlements_by_entitlement[settlement.entitlement_id].append(settlement)
    for settlement_id in sorted(duplicate_settlements):
        exceptions.append(ConstructionAuditException(
            settlement_id,
            "DUPLICATE_SETTLEMENT_ID",
            "duplicate settlement ID prevents reliable received-amount calculation",
        ))

    cpm_cache: dict[str, CPMResult] = {}
    observations: list[RecoveryObservation] = []

    for entitlement_id in sorted(entitlement_by_id):
        entitlement = entitlement_by_id[entitlement_id]
        if entitlement.claimant_id != client_id:
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "CLAIMANT_SCOPE_MISMATCH",
                "entitlement claimant_id does not match Scan 360 client_id",
            ))
            continue

        event = event_by_id.get(entitlement.event_id)
        if event is None:
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "NO_EVENT_EVIDENCE",
                f"no event evidence found for {entitlement.event_id}",
            ))
            continue
        if event.project_id != entitlement.project_id:
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "EVENT_PROJECT_MISMATCH",
                "event project_id does not match entitlement project_id",
            ))
            continue

        mapping = mapping_by_event.get(entitlement.event_id)
        if mapping is None:
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "NO_EVENT_ACTIVITY_MAPPING",
                "no unique event-to-activity mapping exists",
            ))
            continue

        review = review_by_entitlement.get(entitlement_id)
        if review is None:
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "NO_CAUSATION_REVIEW",
                "no qualified causation review exists",
            ))
            continue
        if review.event_id != entitlement.event_id:
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "CAUSATION_EVENT_MISMATCH",
                "causation review event_id does not match entitlement event_id",
            ))
            continue
        if not review.accepted_causation:
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "CAUSATION_NOT_ACCEPTED",
                "qualified causation review did not accept this event as causal",
            ))
            continue

        baseline = schedule_by_id.get(review.baseline_version_id)
        update = schedule_by_id.get(review.update_version_id)
        if baseline is None or update is None:
            missing = [
                version_id
                for version_id, value in (
                    (review.baseline_version_id, baseline),
                    (review.update_version_id, update),
                )
                if value is None
            ]
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "MISSING_SCHEDULE_VERSION",
                "missing schedule version(s): " + ", ".join(missing),
            ))
            continue
        if baseline.project_id != entitlement.project_id or update.project_id != entitlement.project_id:
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "SCHEDULE_PROJECT_MISMATCH",
                "schedule version project_id does not match entitlement project_id",
            ))
            continue
        if _iso_date("update data_date", update.data_date) < _iso_date(
            "baseline data_date", baseline.data_date
        ):
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "SCHEDULE_VERSION_ORDER_INVALID",
                "update data_date precedes baseline data_date",
            ))
            continue
        if _iso_date("review_date", review.review_date) < _iso_date(
            "update data_date", update.data_date
        ):
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "CAUSATION_REVIEW_PRECEDES_UPDATE",
                "qualified causation review predates the update schedule data_date",
            ))
            continue
        if _iso_date("review_date", review.review_date) < _iso_date(
            "event_date", event.event_date
        ):
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "CAUSATION_REVIEW_PRECEDES_EVENT",
                "qualified causation review predates the delay event",
            ))
            continue

        try:
            if baseline.version_id not in cpm_cache:
                cpm_cache[baseline.version_id] = calculate_cpm(baseline)
            if update.version_id not in cpm_cache:
                cpm_cache[update.version_id] = calculate_cpm(update)
        except ValueError as exc:
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "CPM_CALCULATION_ERROR",
                str(exc),
            ))
            continue

        baseline_cpm = cpm_cache[baseline.version_id]
        update_cpm = cpm_cache[update.version_id]

        baseline_activity = baseline_cpm.activities.get(mapping.baseline_activity_id)
        update_activity = update_cpm.activities.get(mapping.update_activity_id)
        if baseline_activity is None or update_activity is None:
            missing = []
            if baseline_activity is None:
                missing.append(f"baseline:{mapping.baseline_activity_id}")
            if update_activity is None:
                missing.append(f"update:{mapping.update_activity_id}")
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "MAPPED_ACTIVITY_MISSING",
                "mapped activity missing from schedule: " + ", ".join(missing),
            ))
            continue

        project_delay_days = max(
            update_cpm.project_duration_days - baseline_cpm.project_duration_days,
            0,
        )
        mapped_finish_delay_days = max(
            update_activity.earliest_finish - baseline_activity.earliest_finish,
            0,
        )
        if project_delay_days <= 0:
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "NO_CPM_PROJECT_DELAY",
                "update schedule does not extend deterministic CPM project duration",
            ))
            continue
        if mapped_finish_delay_days <= 0:
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "MAPPED_ACTIVITY_NO_DELAY",
                "mapped activity does not show positive earliest-finish delay",
            ))
            continue
        if review.accepted_delay_days > project_delay_days:
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "ACCEPTED_DELAY_EXCEEDS_CPM_IMPACT",
                (
                    f"review accepted {review.accepted_delay_days} days but deterministic "
                    f"project-duration delta is {project_delay_days} days"
                ),
            ))
            continue

        group_settlements = settlements_by_entitlement.get(entitlement_id, [])
        if any(s.settlement_id in duplicate_settlements for s in group_settlements):
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "ENTITLEMENT_BLOCKED_BY_DUPLICATE_SETTLEMENT",
                "duplicate settlement IDs prevent reliable actual received amount",
            ))
            continue
        if not group_settlements:
            exceptions.append(ConstructionAuditException(
                entitlement_id,
                "NO_SETTLEMENT_EVIDENCE",
                "actual compensation received cannot be established",
            ))
            continue

        actual_cents = sum(s.amount_received_cents for s in group_settlements)
        if entitlement.entitled_cents <= actual_cents:
            continue

        evidence = (
            event.evidence(),
            mapping.evidence(),
            baseline.evidence(),
            update.evidence(),
            review.evidence(),
            *tuple(
                settlement.evidence()
                for settlement in sorted(
                    group_settlements, key=lambda item: item.settlement_id
                )
            ),
        )

        fully_verified = entitlement.verified and all(ref.verified for ref in evidence)
        observations.append(RecoveryObservation(
            branch=Branch.CONSTRUCTION,
            client_id=client_id,
            counterparty_id=entitlement.counterparty_id,
            reference=entitlement.entitlement_id,
            currency=currency,
            expected_cents=entitlement.entitled_cents,
            actual_cents=actual_cents,
            rule=entitlement.rule_ref(),
            evidence=evidence,
            reason="CONSTRUCTION_ENTITLEMENT_UNDERPAYMENT",
            confidence_basis=(
                "reviewed entitlement + verified schedule versions + qualified causation review"
                if fully_verified
                else "construction entitlement/schedule/causation evidence requires verification"
            ),
            metadata={
                "project_id": entitlement.project_id,
                "change_id": entitlement.change_id,
                "event_id": entitlement.event_id,
                "entitlement_basis": entitlement.entitlement_basis,
                "baseline_version_id": baseline.version_id,
                "baseline_source_hash": baseline.source_hash,
                "baseline_data_date": baseline.data_date,
                "update_version_id": update.version_id,
                "update_source_hash": update.source_hash,
                "update_data_date": update.data_date,
                "baseline_project_duration_days": baseline_cpm.project_duration_days,
                "update_project_duration_days": update_cpm.project_duration_days,
                "cpm_project_delay_days": project_delay_days,
                "mapped_baseline_activity_id": mapping.baseline_activity_id,
                "mapped_update_activity_id": mapping.update_activity_id,
                "mapped_activity_finish_delay_days": mapped_finish_delay_days,
                "baseline_activity_critical": baseline_activity.critical,
                "update_activity_critical": update_activity.critical,
                "accepted_delay_days": review.accepted_delay_days,
                "qualified_reviewer_id": review.qualified_reviewer_id,
                "entitlement_reviewer_id": entitlement.entitlement_reviewer_id,
                "settlement_ids": [
                    settlement.settlement_id for settlement in group_settlements
                ],
            },
        ))

    exceptions.sort(key=lambda item: (item.code, item.reference, item.detail))
    observations.sort(key=lambda item: (item.counterparty_id, item.reference))
    return ConstructionAuditBatch(tuple(observations), tuple(exceptions))
