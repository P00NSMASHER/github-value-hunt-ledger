"""Orchestrated settlement-evidence processing for Freight Recovery.

This is the operational boundary above settlement CSV ingestion, safe automatic
allocation/reversal, and proof-bound human-review case generation.

All supplied CSV inputs are parsed and cross-referenced before any write. The
workflow never auto-resolves a human-review case.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from freight.contracts import canonical_hash
from freight.counter_review_workflow import (
    CounterReviewCase,
    _build_case_from_snapshot as _build_counter_review_case_from_snapshot,
)
from freight.settlement_csv_adapter import (
    CounterEventCSVBatch,
    SettlementEventCSVBatch,
    parse_counter_event_csv,
    parse_settlement_event_csv,
)
from freight.settlement_review_workflow import (
    SettlementReviewCase,
    _build_case_from_snapshot as _build_settlement_review_case_from_snapshot,
)
from freight.settlement_store import (
    ALLOCATED,
    ALREADY_ALLOCATED,
    ALREADY_REVERSED,
    REVIEW,
    REVERSED,
    SettlementStore,
)


COMPLETE = "COMPLETE"
REVIEW_REQUIRED = "REVIEW_REQUIRED"

INGESTED = "INGESTED"
ALREADY_PRESENT = "ALREADY_PRESENT"


@dataclass(frozen=True)
class SettlementEventProcessing:
    event_id: str
    ingest_status: str
    decision_status: str
    effective_status: str
    edge_ids: tuple[str, ...]
    reason: str
    review_case_hash: str | None


@dataclass(frozen=True)
class CounterEventProcessing:
    counter_id: str
    ingest_status: str
    decision_status: str
    effective_status: str
    edge_ids: tuple[str, ...]
    reason: str
    review_case_hash: str | None


@dataclass(frozen=True)
class SettlementLifecycleResult:
    buyer_id: str
    business_unit: str
    state: str
    processed_at: str
    settlement_adapter_hash: str | None
    settlement_file_sha256: str | None
    counter_adapter_hash: str | None
    counter_file_sha256: str | None
    settlement_events: tuple[SettlementEventProcessing, ...]
    counter_events: tuple[CounterEventProcessing, ...]
    settlement_review_cases: tuple[SettlementReviewCase, ...]
    counter_review_cases: tuple[CounterReviewCase, ...]
    review_case_count: int
    store_snapshot_before_hash: str
    store_snapshot_after_hash: str
    state_hash: str
    execution_hash: str


def _timestamp(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("processed_at is required")
    text = value.strip()
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("processed_at must be timezone-aware ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("processed_at must be timezone-aware ISO-8601")
    return (
        parsed.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _snapshot(store: SettlementStore) -> dict:
    value = json.loads(store.report_snapshot_json())
    if (value.get("buyer_id"), value.get("business_unit")) != (
        store.buyer_id,
        store.business_unit,
    ):
        raise ValueError("settlement snapshot scope mismatch")
    return value


def _snapshot_hash(value: dict) -> str:
    return canonical_hash(value)


def _effective_allocation(status: str) -> str:
    if status in (ALLOCATED, ALREADY_ALLOCATED):
        return ALLOCATED
    if status == REVIEW:
        return REVIEW
    raise ValueError("unexpected allocation decision status: " + status)


def _effective_reversal(status: str) -> str:
    if status in (REVERSED, ALREADY_REVERSED):
        return REVERSED
    if status == REVIEW:
        return REVIEW
    raise ValueError("unexpected reversal decision status: " + status)


def _parse_inputs(
    store: SettlementStore,
    *,
    settlement_filename: str | None,
    settlement_data: bytes | None,
    counter_filename: str | None,
    counter_data: bytes | None,
) -> tuple[SettlementEventCSVBatch | None, CounterEventCSVBatch | None]:
    if (settlement_filename is None) != (settlement_data is None):
        raise ValueError("settlement filename/data must be supplied together")
    if (counter_filename is None) != (counter_data is None):
        raise ValueError("counter filename/data must be supplied together")
    if settlement_data is None and counter_data is None:
        raise ValueError("at least one settlement or counter CSV is required")

    settlement_batch = None
    counter_batch = None
    if settlement_data is not None:
        assert settlement_filename is not None
        settlement_batch = parse_settlement_event_csv(
            filename=settlement_filename,
            data=settlement_data,
            buyer_id=store.buyer_id,
            business_unit=store.business_unit,
        )
    if counter_data is not None:
        assert counter_filename is not None
        counter_batch = parse_counter_event_csv(
            filename=counter_filename,
            data=counter_data,
            buyer_id=store.buyer_id,
            business_unit=store.business_unit,
        )
    return settlement_batch, counter_batch


def _preflight(
    store: SettlementStore,
    *,
    before: dict,
    processed_at: str,
    settlement_batch: SettlementEventCSVBatch | None,
    counter_batch: CounterEventCSVBatch | None,
) -> None:
    tables = before["tables"]
    existing_events = {
        row["event_id"]: row for row in tables["settlement_events"]
    }
    existing_event_sources = {
        row["source_hash"]: row["event_id"] for row in tables["settlement_events"]
    }
    existing_counters = {
        row["counter_id"]: row for row in tables["counter_events"]
    }
    existing_counter_sources = {
        row["source_hash"]: row["counter_id"] for row in tables["counter_events"]
    }

    incoming_events = {}
    if settlement_batch is not None:
        for event in settlement_batch.events:
            if processed_at < event.booked_at:
                raise ValueError(
                    "processed_at cannot predate settlement booking: " + event.event_id
                )
            incoming_events[event.event_id] = event
            old = existing_events.get(event.event_id)
            if old is not None:
                expected = {
                    "event_id": event.event_id,
                    "reference": event.reference,
                    "payer_id": event.payer_id,
                    "payee_id": event.payee_id,
                    "currency": event.currency,
                    "amount_cents": event.amount_cents,
                    "booked_at": event.booked_at,
                    "source_hash": event.source_hash,
                    "source_kind": event.source_kind,
                }
                if any(old[key] != value for key, value in expected.items()):
                    raise ValueError(
                        "settlement event replay conflicts with immutable store event: "
                        + event.event_id
                    )
            used_by = existing_event_sources.get(event.source_hash)
            if used_by is not None and used_by != event.event_id:
                raise ValueError("settlement source_hash already used")

    event_evidence = dict(existing_events)
    for event_id, event in incoming_events.items():
        event_evidence[event_id] = {
            "event_id": event.event_id,
            "currency": event.currency,
            "booked_at": event.booked_at,
        }

    if counter_batch is not None:
        for counter in counter_batch.events:
            if processed_at < counter.observed_at:
                raise ValueError(
                    "processed_at cannot predate counter observation: " + counter.counter_id
                )
            old = existing_counters.get(counter.counter_id)
            if old is not None:
                expected = {
                    "counter_id": counter.counter_id,
                    "original_event_id": counter.original_event_id,
                    "currency": counter.currency,
                    "amount_cents": counter.amount_cents,
                    "observed_at": counter.observed_at,
                    "source_hash": counter.source_hash,
                    "source_kind": counter.source_kind,
                }
                if any(old[key] != value for key, value in expected.items()):
                    raise ValueError(
                        "counter event replay conflicts with immutable store event: "
                        + counter.counter_id
                    )
            used_by = existing_counter_sources.get(counter.source_hash)
            if used_by is not None and used_by != counter.counter_id:
                raise ValueError("counter source_hash already used")

            original = event_evidence.get(counter.original_event_id)
            if original is None:
                raise ValueError(
                    "counter references unknown settlement event: "
                    + counter.original_event_id
                )
            if original["currency"] != counter.currency:
                raise ValueError(
                    "counter currency mismatch with original settlement event"
                )
            if counter.observed_at < original["booked_at"]:
                raise ValueError("counter event predates original settlement")


def process_settlement_evidence(
    store: SettlementStore,
    *,
    processed_at: str,
    settlement_filename: str | None = None,
    settlement_data: bytes | None = None,
    counter_filename: str | None = None,
    counter_data: bytes | None = None,
) -> SettlementLifecycleResult:
    processed_at = _timestamp(processed_at)

    # Parse every provided file before touching persistent state.
    settlement_batch, counter_batch = _parse_inputs(
        store,
        settlement_filename=settlement_filename,
        settlement_data=settlement_data,
        counter_filename=counter_filename,
        counter_data=counter_data,
    )
    # Advisory preflight gives fast, human-readable package errors. The store
    # repeats authoritative invariants inside one BEGIN IMMEDIATE transaction.
    advisory_before = _snapshot(store)
    _preflight(
        store,
        before=advisory_before,
        processed_at=processed_at,
        settlement_batch=settlement_batch,
        counter_batch=counter_batch,
    )

    package = store.process_evidence_package(
        settlement_events=(
            settlement_batch.events if settlement_batch is not None else ()
        ),
        counter_events=(
            counter_batch.events if counter_batch is not None else ()
        ),
        created_at=processed_at,
    )
    before = package.store_snapshot_before
    after = package.store_snapshot_after
    before_hash = _snapshot_hash(before)
    after_hash = _snapshot_hash(after)

    settlement_results: list[SettlementEventProcessing] = []
    settlement_cases: list[SettlementReviewCase] = []
    for outcome in package.settlement_outcomes:
        decision = outcome.decision
        case_hash = None
        if decision.status == REVIEW:
            case = _build_settlement_review_case_from_snapshot(
                store,
                event_id=outcome.event_id,
                snapshot=after,
            )
            settlement_cases.append(case)
            case_hash = case.case_hash
        settlement_results.append(SettlementEventProcessing(
            event_id=outcome.event_id,
            ingest_status=INGESTED if outcome.created else ALREADY_PRESENT,
            decision_status=decision.status,
            effective_status=_effective_allocation(decision.status),
            edge_ids=tuple(decision.edge_ids),
            reason=decision.reason,
            review_case_hash=case_hash,
        ))

    counter_results: list[CounterEventProcessing] = []
    counter_cases: list[CounterReviewCase] = []
    for outcome in package.counter_outcomes:
        decision = outcome.decision
        case_hash = None
        if decision.status == REVIEW:
            case = _build_counter_review_case_from_snapshot(
                store,
                counter_id=outcome.counter_id,
                snapshot=after,
            )
            counter_cases.append(case)
            case_hash = case.case_hash
        counter_results.append(CounterEventProcessing(
            counter_id=outcome.counter_id,
            ingest_status=INGESTED if outcome.created else ALREADY_PRESENT,
            decision_status=decision.status,
            effective_status=_effective_reversal(decision.status),
            edge_ids=tuple(decision.edge_ids),
            reason=decision.reason,
            review_case_hash=case_hash,
        ))

    settlement_results_tuple = tuple(settlement_results)
    counter_results_tuple = tuple(counter_results)
    settlement_cases_tuple = tuple(settlement_cases)
    counter_cases_tuple = tuple(counter_cases)
    review_count = len(settlement_cases_tuple) + len(counter_cases_tuple)
    state = REVIEW_REQUIRED if review_count else COMPLETE

    stable_body = {
        "schema": 1,
        "buyer_id": store.buyer_id,
        "business_unit": store.business_unit,
        "settlement_adapter_hash": (
            settlement_batch.adapter_hash if settlement_batch else None
        ),
        "counter_adapter_hash": (
            counter_batch.adapter_hash if counter_batch else None
        ),
        "settlement_outcomes": [
            {
                "event_id": item.event_id,
                "effective_status": item.effective_status,
                "edge_ids": item.edge_ids,
                "reason": item.reason if item.effective_status == REVIEW else "",
                "review_case_hash": item.review_case_hash,
            }
            for item in settlement_results_tuple
        ],
        "counter_outcomes": [
            {
                "counter_id": item.counter_id,
                "effective_status": item.effective_status,
                "edge_ids": item.edge_ids,
                "reason": item.reason if item.effective_status == REVIEW else "",
                "review_case_hash": item.review_case_hash,
            }
            for item in counter_results_tuple
        ],
        "settlement_review_case_hashes": [
            item.case_hash for item in settlement_cases_tuple
        ],
        "counter_review_case_hashes": [
            item.case_hash for item in counter_cases_tuple
        ],
        "store_snapshot_after_hash": after_hash,
    }
    state_hash = canonical_hash(stable_body)

    execution_body = {
        "schema": 1,
        "state_hash": state_hash,
        "processed_at": processed_at,
        "store_snapshot_before_hash": before_hash,
        "store_snapshot_after_hash": after_hash,
        "settlement_events": [asdict(item) for item in settlement_results_tuple],
        "counter_events": [asdict(item) for item in counter_results_tuple],
    }
    return SettlementLifecycleResult(
        buyer_id=store.buyer_id,
        business_unit=store.business_unit,
        state=state,
        processed_at=processed_at,
        settlement_adapter_hash=(
            settlement_batch.adapter_hash if settlement_batch else None
        ),
        settlement_file_sha256=(
            settlement_batch.file_sha256 if settlement_batch else None
        ),
        counter_adapter_hash=(
            counter_batch.adapter_hash if counter_batch else None
        ),
        counter_file_sha256=(
            counter_batch.file_sha256 if counter_batch else None
        ),
        settlement_events=settlement_results_tuple,
        counter_events=counter_results_tuple,
        settlement_review_cases=settlement_cases_tuple,
        counter_review_cases=counter_cases_tuple,
        review_case_count=review_count,
        store_snapshot_before_hash=before_hash,
        store_snapshot_after_hash=after_hash,
        state_hash=state_hash,
        execution_hash=canonical_hash(execution_body),
    )
