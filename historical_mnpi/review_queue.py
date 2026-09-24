"""Deterministic human-review gate for historical public-record MNPI research.

Step 8 is the acceptance boundary between parser candidates and normalized
historical corpus records. Parser output cannot approve itself.

This module is deliberately scoped to already-public historical research and
compliance analysis. It never authorizes live trading or order generation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Iterable

from .case_model import CaseRegistry
from .entity_resolution import (
    CaseEntityCrosswalkRegistry,
    EntityKind,
    EntityResolutionRegistry,
    verify_case_entity_crosswalk,
)
from .event_model import EventRegistry, InformationEvent, verify_event_provenance
from .extractors import CandidateFieldStatus, CandidateKind, CandidateRecord
from .raw_artifacts import (
    RawArtifactManifest,
    SourceArtifactRef,
    same_retained_artifact,
)
from .source_registry import SourceRegistry, canonical_hash
from .transaction_model import (
    FactStatus,
    HistoricalTransaction,
    TimePrecision,
    verify_transaction_provenance,
)


_SCOPE = "HISTORICAL_RESEARCH_COMPLIANCE_ONLY"


class ReviewDecision(str, Enum):
    PENDING = "PENDING"
    APPROVED_FOR_HISTORICAL_RESEARCH = "APPROVED_FOR_HISTORICAL_RESEARCH"
    REJECTED = "REJECTED"
    NEEDS_CORROBORATION = "NEEDS_CORROBORATION"


@dataclass(frozen=True)
class ReviewConflict:
    field_name: str
    values: tuple[str, ...]
    candidate_hashes: tuple[str, ...]

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "field_name": self.field_name,
            "values": sorted(self.values),
            "candidate_hashes": sorted(self.candidate_hashes),
        })


@dataclass(frozen=True)
class ReviewIdentitySnapshot:
    case_id: str
    case_title: str
    trader_party_id: str
    trader_name: str
    issuer_id: str
    issuer_name: str
    event_id: str
    event_summary: str


@dataclass(frozen=True)
class ReviewDurableIdentitySnapshot:
    trader_entity_id: str
    trader_entity_proof_hash: str
    trader_crosswalk_hash: str
    issuer_entity_id: str
    issuer_entity_proof_hash: str
    issuer_crosswalk_hash: str

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "trader_entity_id": self.trader_entity_id,
            "trader_entity_proof_hash": self.trader_entity_proof_hash,
            "trader_crosswalk_hash": self.trader_crosswalk_hash,
            "issuer_entity_id": self.issuer_entity_id,
            "issuer_entity_proof_hash": self.issuer_entity_proof_hash,
            "issuer_crosswalk_hash": self.issuer_crosswalk_hash,
        })


@dataclass(frozen=True)
class ReviewTemporalSnapshot:
    trade_time_precision: str
    trade_timestamp: str | None
    trade_date: str | None
    trade_date_range_start: str | None
    trade_date_range_end: str | None
    public_release_precision: str
    public_release_boundary_hash: str


@dataclass(frozen=True)
class ReviewChecks:
    source_evidence_checked: bool
    identity_checked: bool
    temporal_precision_checked: bool
    legal_status_checked: bool
    conflicts_resolved: bool

    def __post_init__(self) -> None:
        for value in (
            self.source_evidence_checked,
            self.identity_checked,
            self.temporal_precision_checked,
            self.legal_status_checked,
            self.conflicts_resolved,
        ):
            if type(value) is not bool:
                raise ValueError("review checks must be boolean")

    @property
    def all_passed(self) -> bool:
        return all((
            self.source_evidence_checked,
            self.identity_checked,
            self.temporal_precision_checked,
            self.legal_status_checked,
            self.conflicts_resolved,
        ))


@dataclass(frozen=True)
class ReviewQueueItem:
    review_id: str
    proposed_record: HistoricalTransaction
    event_id: str
    event_proof_hash: str
    identity: ReviewIdentitySnapshot
    durable_identity: ReviewDurableIdentitySnapshot | None
    temporal: ReviewTemporalSnapshot
    candidates: tuple[CandidateRecord, ...]
    conflicts: tuple[ReviewConflict, ...]
    blockers: tuple[str, ...]
    normalized_row_hash: str
    created_at: str
    created_by: str
    live_trading_allowed: bool
    review_item_hash: str

    def integrity_body(self) -> dict:
        return {
            "schema": 1,
            "scope": _SCOPE,
            "proposed_record_hash": self.proposed_record.proof_hash,
            "event_id": self.event_id,
            "event_proof_hash": self.event_proof_hash,
            "identity": self.identity.__dict__,
            "durable_identity": (
                self.durable_identity.__dict__
                if self.durable_identity is not None
                else None
            ),
            "temporal": self.temporal.__dict__,
            "candidate_hashes": sorted(item.proof_hash for item in self.candidates),
            "conflict_hashes": sorted(item.proof_hash for item in self.conflicts),
            "blockers": sorted(self.blockers),
            "normalized_row_hash": self.normalized_row_hash,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "live_trading_allowed": False,
        }

    def verify_integrity(self) -> None:
        expected = canonical_hash(self.integrity_body())
        if expected != self.review_item_hash:
            raise ValueError("review item hash mismatch")
        if self.review_id != "review:" + expected:
            raise ValueError("review id/hash mismatch")
        if self.live_trading_allowed is not False:
            raise ValueError("historical review item cannot authorize live trading")
        if self.normalized_row_hash != self.proposed_record.proof_hash:
            raise ValueError("normalized row hash mismatch")


@dataclass(frozen=True)
class HistoricalReviewDecision:
    review_id: str
    review_item_hash: str
    normalized_row_hash: str
    durable_identity_hash: str | None
    decision: ReviewDecision
    checks: ReviewChecks
    reviewer_id: str
    reviewed_at: str
    rationale: str
    research_corpus_eligible: bool
    live_trading_allowed: bool
    decision_hash: str

    def integrity_body(self) -> dict:
        return {
            "schema": 1,
            "scope": _SCOPE,
            "review_id": self.review_id,
            "review_item_hash": self.review_item_hash,
            "normalized_row_hash": self.normalized_row_hash,
            "durable_identity_hash": self.durable_identity_hash,
            "decision": self.decision.value,
            "checks": self.checks.__dict__,
            "reviewer_id": self.reviewer_id,
            "reviewed_at": self.reviewed_at,
            "rationale": self.rationale,
            "research_corpus_eligible": self.research_corpus_eligible,
            "live_trading_allowed": False,
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.decision_hash:
            raise ValueError("review decision hash mismatch")
        if self.live_trading_allowed is not False:
            raise ValueError("historical review cannot authorize live trading")
        if self.research_corpus_eligible and self.durable_identity_hash is None:
            raise ValueError(
                "research-eligible review requires durable identity proof"
            )


def _build_durable_identity_snapshot(
    record: HistoricalTransaction,
    *,
    cases: CaseRegistry,
    entities: EntityResolutionRegistry,
    entity_crosswalks: CaseEntityCrosswalkRegistry,
) -> ReviewDurableIdentitySnapshot:
    try:
        trader_crosswalk = entity_crosswalks.get(
            record.case_id,
            EntityKind.TRADER,
            record.trader_party_id,
        )
    except KeyError as exc:
        raise ValueError("missing durable trader identity crosswalk") from exc
    try:
        issuer_crosswalk = entity_crosswalks.get(
            record.case_id,
            EntityKind.ISSUER,
            record.issuer_id,
        )
    except KeyError as exc:
        raise ValueError("missing durable issuer identity crosswalk") from exc

    verify_case_entity_crosswalk(
        trader_crosswalk,
        cases=cases,
        entities=entities,
    )
    verify_case_entity_crosswalk(
        issuer_crosswalk,
        cases=cases,
        entities=entities,
    )

    trader = entities.trader(trader_crosswalk.durable_entity_id)
    issuer = entities.issuer(issuer_crosswalk.durable_entity_id)
    return ReviewDurableIdentitySnapshot(
        trader_entity_id=trader.entity_id,
        trader_entity_proof_hash=trader.proof_hash,
        trader_crosswalk_hash=trader_crosswalk.proof_hash,
        issuer_entity_id=issuer.entity_id,
        issuer_entity_proof_hash=issuer.proof_hash,
        issuer_crosswalk_hash=issuer_crosswalk.proof_hash,
    )


def verify_review_durable_identity(
    item: ReviewQueueItem,
    *,
    cases: CaseRegistry,
    entities: EntityResolutionRegistry,
    entity_crosswalks: CaseEntityCrosswalkRegistry,
) -> None:
    item.verify_integrity()
    if item.durable_identity is None:
        raise ValueError("review item has no durable identity snapshot")
    current = _build_durable_identity_snapshot(
        item.proposed_record,
        cases=cases,
        entities=entities,
        entity_crosswalks=entity_crosswalks,
    )
    if current.proof_hash != item.durable_identity.proof_hash:
        raise ValueError("review durable identity snapshot is stale or changed")


def _iso(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("review timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("review timestamp must include timezone")
    return value


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(_iso(value).replace("Z", "+00:00"))


def _normalize_candidate_value(field_name: str, value: str) -> str:
    if field_name in {"trade_date", "option_expiry"}:
        for pattern in ("%Y-%m-%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, pattern).date().isoformat()
            except ValueError:
                pass
    if field_name == "currency":
        return value.upper()
    return value


def _candidate_support(
    candidates: tuple[CandidateRecord, ...],
) -> dict[str, set[str]]:
    support: dict[str, set[str]] = {}
    for candidate in candidates:
        for field in candidate.fields:
            if field.parsed_value is None:
                continue
            value = _normalize_candidate_value(field.name, field.parsed_value)
            support.setdefault(field.name, set()).add(value)
            if field.name == "instrument_text":
                mapped = {
                    "share": "STOCK",
                    "shares": "STOCK",
                    "call": "CALL_OPTION",
                    "calls": "CALL_OPTION",
                    "put": "PUT_OPTION",
                    "puts": "PUT_OPTION",
                    "contract": "OPTION_OTHER",
                    "contracts": "OPTION_OTHER",
                }.get(field.parsed_value.casefold())
                if mapped is not None:
                    support.setdefault("instrument_type", set()).add(mapped)
    return support


def _proposed_values(record: HistoricalTransaction) -> dict[str, str]:
    out: dict[str, str] = {}
    for field_name in (
        "trade_timestamp",
        "trade_date",
        "trade_date_range_start",
        "trade_date_range_end",
        "ticker_at_trade",
        "currency",
        "quantity",
        "execution_price",
        "trade_amount",
        "option_strike",
        "option_expiry",
        "exit_timestamp",
        "exit_price",
        "documented_profit",
    ):
        value = getattr(record, field_name)
        if value is not None:
            out[field_name] = value
    if record.instrument_type.value != "UNKNOWN":
        out["instrument_type"] = record.instrument_type.value
    if record.side.value != "UNKNOWN":
        out["side"] = record.side.value
    return out


def detect_candidate_conflicts(
    candidates: Iterable[CandidateRecord],
) -> tuple[ReviewConflict, ...]:
    by_field: dict[str, dict[str, list[str]]] = {}
    for candidate in candidates:
        for field in candidate.fields:
            if field.parsed_value is None:
                continue
            normalized = _normalize_candidate_value(
                field.name,
                field.parsed_value,
            )
            by_field.setdefault(field.name, {}).setdefault(
                normalized, []
            ).append(candidate.proof_hash)

    out = []
    for field_name, values in sorted(by_field.items()):
        if len(values) > 1:
            out.append(ReviewConflict(
                field_name=field_name,
                values=tuple(sorted(values)),
                candidate_hashes=tuple(sorted({
                    candidate_hash
                    for hashes in values.values()
                    for candidate_hash in hashes
                })),
            ))
    return tuple(out)


def _blockers(
    record: HistoricalTransaction,
    candidates: tuple[CandidateRecord, ...],
    conflicts: tuple[ReviewConflict, ...],
) -> tuple[str, ...]:
    out = {f"CONFLICT:{item.field_name}" for item in conflicts}
    support = _candidate_support(candidates)
    for field_name, proposed_value in _proposed_values(record).items():
        if proposed_value not in support.get(field_name, set()):
            out.add(f"PROPOSED_VALUE_UNSUPPORTED:{field_name}")

    for candidate in candidates:
        for field in candidate.fields:
            if field.status is CandidateFieldStatus.AMBIGUOUS:
                out.add(
                    f"AMBIGUOUS_FIELD:{candidate.candidate_id}:{field.name}"
                )
            if field.status is CandidateFieldStatus.UNPARSED:
                out.add(
                    f"UNPARSED_FIELD:{candidate.candidate_id}:{field.name}"
                )

        warnings = set(candidate.warnings)
        if "PDF_TEXT_LAYER_NOT_RAW_VISUAL_VERIFICATION" in warnings:
            out.add(
                f"RAW_VISUAL_VERIFICATION_REQUIRED:{candidate.candidate_id}"
            )
        if (
            "TIMEZONE_NOT_ENCODED_IN_SOURCE_COLUMN" in warnings
            and record.time_precision is TimePrecision.EXACT_TIMESTAMP
        ):
            out.add(
                f"TIMEZONE_REQUIRED_FOR_EXACT_TIMESTAMP:{candidate.candidate_id}"
            )
        if (
            "ACADEMIC_RECONSTRUCTION" in warnings
            and record.fact_status is not FactStatus.ACADEMIC_RECONSTRUCTION
        ):
            out.add(
                f"ACADEMIC_SOURCE_STATUS_MISMATCH:{candidate.candidate_id}"
            )
        if (
            "FIRST_TRADE_TIME_IS_NOT_COMPLETE_TRADE_ECONOMICS" in warnings
            and any(value is not None for value in (
                record.quantity,
                record.execution_price,
                record.trade_amount,
                record.documented_profit,
            ))
        ):
            out.add(
                f"CANDIDATE_DOES_NOT_SUPPORT_TRADE_ECONOMICS:"
                f"{candidate.candidate_id}"
            )
    return tuple(sorted(out))


def build_review_item(
    proposed_record: HistoricalTransaction,
    *,
    event: InformationEvent,
    candidates: Iterable[CandidateRecord],
    cases: CaseRegistry,
    events: EventRegistry,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
    created_at: str,
    created_by: str,
    entities: EntityResolutionRegistry | None = None,
    entity_crosswalks: CaseEntityCrosswalkRegistry | None = None,
) -> ReviewQueueItem:
    created_at = _iso(created_at)
    if not created_by.strip():
        raise ValueError("created_by is required")

    verify_transaction_provenance(
        proposed_record,
        cases=cases,
        source_registry=source_registry,
        artifact_manifest=artifact_manifest,
    )
    verify_event_provenance(
        event,
        cases=cases,
        source_registry=source_registry,
        artifact_manifest=artifact_manifest,
    )
    if events.get(event.event_id).proof_hash != event.proof_hash:
        raise ValueError("event is not registered")
    if event.case_id != proposed_record.case_id:
        raise ValueError("record/event case mismatch")
    if proposed_record.issuer_id not in event.issuer_ids:
        raise ValueError("record issuer not covered by event")

    candidate_tuple = tuple(sorted(
        candidates,
        key=lambda item: (item.source_ref.proof_hash, item.candidate_id),
    ))
    if not candidate_tuple:
        raise ValueError("review requires candidate evidence")
    if not any(
        candidate.kind is CandidateKind.TRANSACTION
        for candidate in candidate_tuple
    ):
        raise ValueError("review requires transaction candidate")

    case = cases.get(proposed_record.case_id)
    for candidate in candidate_tuple:
        if candidate.case_id not in {None, proposed_record.case_id}:
            raise ValueError("candidate belongs to different case")
        artifact_manifest.resolve_ref(candidate.source_ref)
        if not any(
            same_retained_artifact(candidate.source_ref, case_link.ref)
            for case_link in case.artifacts
        ):
            raise ValueError(
                "candidate artifact is not linked to canonical case"
            )

    if not any(
        same_retained_artifact(proposed_record.source_ref, candidate.source_ref)
        for candidate in candidate_tuple
    ):
        raise ValueError(
            "normalized transaction source artifact is not represented "
            "by candidate evidence"
        )

    if not any(
        same_retained_artifact(proposed_record.status_ref, candidate.source_ref)
        for candidate in candidate_tuple
    ):
        raise ValueError(
            "normalized status source artifact is not represented "
            "by candidate evidence"
        )

    if (entities is None) != (entity_crosswalks is None):
        raise ValueError(
            "entities and entity_crosswalks must be supplied together"
        )
    durable_identity = (
        _build_durable_identity_snapshot(
            proposed_record,
            cases=cases,
            entities=entities,
            entity_crosswalks=entity_crosswalks,
        )
        if entities is not None and entity_crosswalks is not None
        else None
    )

    parties = {item.party_id: item for item in case.parties}
    issuers = {item.issuer_id: item for item in case.issuers}
    identity = ReviewIdentitySnapshot(
        case_id=case.case_id,
        case_title=case.title,
        trader_party_id=proposed_record.trader_party_id,
        trader_name=parties[proposed_record.trader_party_id].display_name,
        issuer_id=proposed_record.issuer_id,
        issuer_name=issuers[proposed_record.issuer_id].legal_name,
        event_id=event.event_id,
        event_summary=event.information_summary,
    )
    temporal = ReviewTemporalSnapshot(
        trade_time_precision=proposed_record.time_precision.value,
        trade_timestamp=proposed_record.trade_timestamp,
        trade_date=proposed_record.trade_date,
        trade_date_range_start=proposed_record.trade_date_range_start,
        trade_date_range_end=proposed_record.trade_date_range_end,
        public_release_precision=event.public_release.precision.value,
        public_release_boundary_hash=event.public_release.proof_hash,
    )
    conflicts = detect_candidate_conflicts(candidate_tuple)
    blockers = _blockers(proposed_record, candidate_tuple, conflicts)

    body = {
        "schema": 1,
        "scope": _SCOPE,
        "proposed_record_hash": proposed_record.proof_hash,
        "event_id": event.event_id,
        "event_proof_hash": event.proof_hash,
        "identity": identity.__dict__,
        "durable_identity": (
            durable_identity.__dict__
            if durable_identity is not None
            else None
        ),
        "temporal": temporal.__dict__,
        "candidate_hashes": sorted(
            candidate.proof_hash for candidate in candidate_tuple
        ),
        "conflict_hashes": sorted(
            conflict.proof_hash for conflict in conflicts
        ),
        "blockers": sorted(blockers),
        "normalized_row_hash": proposed_record.proof_hash,
        "created_at": created_at,
        "created_by": created_by.strip(),
        "live_trading_allowed": False,
    }
    item_hash = canonical_hash(body)
    return ReviewQueueItem(
        review_id="review:" + item_hash,
        proposed_record=proposed_record,
        event_id=event.event_id,
        event_proof_hash=event.proof_hash,
        identity=identity,
        durable_identity=durable_identity,
        temporal=temporal,
        candidates=candidate_tuple,
        conflicts=conflicts,
        blockers=blockers,
        normalized_row_hash=proposed_record.proof_hash,
        created_at=created_at,
        created_by=created_by.strip(),
        live_trading_allowed=False,
        review_item_hash=item_hash,
    )


def decide_review_item(
    item: ReviewQueueItem,
    *,
    decision: ReviewDecision,
    checks: ReviewChecks,
    reviewer_id: str,
    reviewed_at: str,
    rationale: str,
    cases: CaseRegistry | None = None,
    entities: EntityResolutionRegistry | None = None,
    entity_crosswalks: CaseEntityCrosswalkRegistry | None = None,
) -> HistoricalReviewDecision:
    item.verify_integrity()
    if decision is ReviewDecision.PENDING:
        raise ValueError("PENDING is not a completed decision")
    if not reviewer_id.strip() or not rationale.strip():
        raise ValueError("reviewer_id and rationale are required")
    reviewed_at = _iso(reviewed_at)
    if _dt(reviewed_at) < _dt(item.created_at):
        raise ValueError("review decision cannot predate review item")

    if decision is ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH:
        if item.blockers:
            raise ValueError(
                "blocked item cannot be approved for historical research"
            )
        if not checks.all_passed:
            raise ValueError(
                "historical research approval requires all reviewer checks"
            )
        if item.durable_identity is None:
            raise ValueError(
                "historical research approval requires durable identity crosswalks"
            )
        if cases is None or entities is None or entity_crosswalks is None:
            raise ValueError(
                "historical research approval requires current identity registries"
            )
        verify_review_durable_identity(
            item,
            cases=cases,
            entities=entities,
            entity_crosswalks=entity_crosswalks,
        )

    eligible = (
        decision is ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH
    )
    durable_identity_hash = (
        item.durable_identity.proof_hash
        if item.durable_identity is not None
        else None
    )
    body = {
        "schema": 1,
        "scope": _SCOPE,
        "review_id": item.review_id,
        "review_item_hash": item.review_item_hash,
        "normalized_row_hash": item.normalized_row_hash,
        "durable_identity_hash": durable_identity_hash,
        "decision": decision.value,
        "checks": checks.__dict__,
        "reviewer_id": reviewer_id.strip(),
        "reviewed_at": reviewed_at,
        "rationale": rationale.strip(),
        "research_corpus_eligible": eligible,
        "live_trading_allowed": False,
    }
    return HistoricalReviewDecision(
        review_id=item.review_id,
        review_item_hash=item.review_item_hash,
        normalized_row_hash=item.normalized_row_hash,
        durable_identity_hash=durable_identity_hash,
        decision=decision,
        checks=checks,
        reviewer_id=reviewer_id.strip(),
        reviewed_at=reviewed_at,
        rationale=rationale.strip(),
        research_corpus_eligible=eligible,
        live_trading_allowed=False,
        decision_hash=canonical_hash(body),
    )


class HistoricalReviewQueue:
    """Append-only in-memory review ledger.

    Corrected records create a new review item/hash. An already-decided review
    item cannot be silently re-decided.
    """

    def __init__(self) -> None:
        self._items: dict[str, ReviewQueueItem] = {}
        self._decisions: dict[str, HistoricalReviewDecision] = {}

    def enqueue(self, item: ReviewQueueItem) -> ReviewQueueItem:
        item.verify_integrity()
        existing = self._items.get(item.review_id)
        if existing is not None:
            if existing.review_item_hash != item.review_item_hash:
                raise ValueError("review_id collision with different item")
            return existing
        self._items[item.review_id] = item
        return item

    def decide(
        self,
        review_id: str,
        *,
        decision: ReviewDecision,
        checks: ReviewChecks,
        reviewer_id: str,
        reviewed_at: str,
        rationale: str,
        cases: CaseRegistry | None = None,
        entities: EntityResolutionRegistry | None = None,
        entity_crosswalks: CaseEntityCrosswalkRegistry | None = None,
    ) -> HistoricalReviewDecision:
        try:
            item = self._items[review_id]
        except KeyError as exc:
            raise KeyError("unknown review_id: " + review_id) from exc
        if review_id in self._decisions:
            raise ValueError(
                "review item already has a completed decision; "
                "create a new proposal for corrections"
            )
        record = decide_review_item(
            item,
            decision=decision,
            checks=checks,
            reviewer_id=reviewer_id,
            reviewed_at=reviewed_at,
            rationale=rationale,
            cases=cases,
            entities=entities,
            entity_crosswalks=entity_crosswalks,
        )
        self._decisions[review_id] = record
        return record

    def pending(self) -> tuple[ReviewQueueItem, ...]:
        return tuple(
            item
            for review_id, item in sorted(self._items.items())
            if review_id not in self._decisions
        )

    def approved_normalized_row_hashes(self) -> tuple[str, ...]:
        return tuple(sorted(
            decision.normalized_row_hash
            for decision in self._decisions.values()
            if decision.research_corpus_eligible
        ))

    @property
    def queue_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": _SCOPE,
            "review_item_hashes": sorted(
                item.review_item_hash for item in self._items.values()
            ),
            "decision_hashes": sorted(
                decision.decision_hash
                for decision in self._decisions.values()
            ),
        })


def render_review_item_markdown(item: ReviewQueueItem) -> str:
    lines = [
        "# Historical MNPI Research Review",
        "",
        f"- Review ID: `{item.review_id}`",
        f"- Normalized row hash: `{item.normalized_row_hash}`",
        f"- Case: **{item.identity.case_title}**",
        f"- Trader identity: **{item.identity.trader_name}**",
        (
            "- Durable trader identity: "
            f"**{item.durable_identity.trader_entity_id}**"
            if item.durable_identity is not None
            else "- Durable trader identity: **not attached**"
        ),
        f"- Issuer identity: **{item.identity.issuer_name}**",
        (
            "- Durable issuer identity: "
            f"**{item.durable_identity.issuer_entity_id}**"
            if item.durable_identity is not None
            else "- Durable issuer identity: **not attached**"
        ),
        f"- Event: **{item.identity.event_summary}**",
        f"- Trade-time precision: **{item.temporal.trade_time_precision}**",
        (
            f"- Trade timestamp: **{item.temporal.trade_timestamp}**"
            if item.temporal.trade_timestamp is not None
            else (
                f"- Trade date: **{item.temporal.trade_date}**"
                if item.temporal.trade_date is not None
                else (
                    "- Trade date range: **"
                    f"{item.temporal.trade_date_range_start} to "
                    f"{item.temporal.trade_date_range_end}**"
                )
            )
        ),
        (
            "- Public-release precision: "
            f"**{item.temporal.public_release_precision}**"
        ),
        (
            "- Public-release boundary hash: "
            f"`{item.temporal.public_release_boundary_hash}`"
        ),
        f"- Fact status: **{item.proposed_record.fact_status.value}**",
        f"- Normalized quantity: **{item.proposed_record.quantity}**",
        (
            "- Normalized execution price: "
            f"**{item.proposed_record.execution_price}**"
        ),
        f"- Source locator: `{item.proposed_record.source_ref.locator}`",
        f"- Status locator: `{item.proposed_record.status_ref.locator}`",
        "- Live trading allowed: **no**",
        "",
        "## Candidate evidence",
        "",
    ]
    for candidate in item.candidates:
        lines.extend([
            f"### {candidate.candidate_id}",
            (
                f"- Extractor: "
                f"`{candidate.extractor_id}@{candidate.extractor_version}`"
            ),
            f"- Locator: `{candidate.source_ref.locator}`",
            f"- Excerpt SHA-256: `{candidate.excerpt_sha256}`",
            f"- Excerpt: {candidate.raw_excerpt}",
        ])
        for field in candidate.fields:
            lines.append(
                f"- {field.name}: raw=`{field.raw_value}`; "
                f"parsed=`"
                f"{field.parsed_value if field.parsed_value is not None else 'NULL'}"
                f"`; status={field.status.value}"
            )
        if candidate.warnings:
            lines.append("- Warnings: " + ", ".join(candidate.warnings))
        lines.append("")

    lines.extend([
        "## Conflicts / blockers",
        "",
        "- Conflicts: " + (
            ", ".join(conflict.field_name for conflict in item.conflicts)
            if item.conflicts else "none"
        ),
        "- Blockers: " + (
            ", ".join(item.blockers) if item.blockers else "none"
        ),
        "",
        (
            "Parser output is not historical corpus data until a human "
            "explicitly approves this exact normalized row hash."
        ),
    ])
    return "\n".join(lines)


__all__ = [
    "HistoricalReviewDecision",
    "HistoricalReviewQueue",
    "ReviewChecks",
    "ReviewConflict",
    "ReviewDecision",
    "ReviewDurableIdentitySnapshot",
    "ReviewIdentitySnapshot",
    "ReviewQueueItem",
    "ReviewTemporalSnapshot",
    "build_review_item",
    "decide_review_item",
    "detect_candidate_conflicts",
    "render_review_item_markdown",
    "verify_review_durable_identity",
]
