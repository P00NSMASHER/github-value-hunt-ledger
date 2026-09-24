"""Deterministic human-review queue for historical normalized transactions.

Step 8 makes review an explicit gate between parser candidates and the accepted
transaction registry. Candidate extraction cannot approve itself.

Approval re-verifies:
- canonical case identity and case proof;
- event identity/public-release provenance;
- source/artifact proofs;
- transaction legal/factual status evidence;
- candidate excerpts and parsed-field hashes;
- normalized row hash;
- conflicts and deterministic blockers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Iterable

from .case_model import CaseRegistry
from .event_model import EventRegistry, InformationEvent, verify_event_provenance
from .extractors import (
    CandidateFieldStatus,
    CandidateKind,
    CandidateRecord,
)
from .raw_artifacts import RawArtifactManifest
from .source_registry import SourceRegistry, canonical_hash
from .transaction_model import (
    FactStatus,
    HistoricalTransaction,
    TimePrecision,
    TransactionRegistry,
    verify_transaction_provenance,
)


class ReviewDecision(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
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
    public_release_hash: str

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "case_id": self.case_id,
            "case_title": self.case_title,
            "trader_party_id": self.trader_party_id,
            "trader_name": self.trader_name,
            "issuer_id": self.issuer_id,
            "issuer_name": self.issuer_name,
            "event_id": self.event_id,
            "event_summary": self.event_summary,
            "public_release_hash": self.public_release_hash,
        })


@dataclass(frozen=True)
class ReviewQueueItem:
    review_id: str
    proposed_transaction: HistoricalTransaction
    event_id: str
    event_proof_hash: str
    identity: ReviewIdentitySnapshot
    candidates: tuple[CandidateRecord, ...]
    conflicts: tuple[ReviewConflict, ...]
    blockers: tuple[str, ...]
    normalized_row_hash: str
    created_at: str
    created_by: str
    review_item_hash: str

    def integrity_body(self) -> dict:
        return {
            "schema": 1,
            "proposed_transaction_hash": self.proposed_transaction.proof_hash,
            "event_id": self.event_id,
            "event_proof_hash": self.event_proof_hash,
            "identity_hash": self.identity.proof_hash,
            "candidate_hashes": sorted(item.proof_hash for item in self.candidates),
            "conflict_hashes": sorted(item.proof_hash for item in self.conflicts),
            "blockers": sorted(self.blockers),
            "normalized_row_hash": self.normalized_row_hash,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }

    def verify_integrity(self) -> None:
        expected = canonical_hash(self.integrity_body())
        if expected != self.review_item_hash:
            raise ValueError("review item hash mismatch")
        if self.review_id != "review:" + expected:
            raise ValueError("review id/hash mismatch")
        if self.normalized_row_hash != self.proposed_transaction.proof_hash:
            raise ValueError("normalized row hash mismatch")


@dataclass(frozen=True)
class ReviewDecisionRecord:
    review_id: str
    review_item_hash: str
    decision: ReviewDecision
    reviewer_id: str
    reviewed_at: str
    rationale: str
    accepted_transaction_hash: str | None
    decision_hash: str

    def integrity_body(self) -> dict:
        return {
            "schema": 1,
            "review_id": self.review_id,
            "review_item_hash": self.review_item_hash,
            "decision": self.decision.value,
            "reviewer_id": self.reviewer_id,
            "reviewed_at": self.reviewed_at,
            "rationale": self.rationale,
            "accepted_transaction_hash": self.accepted_transaction_hash,
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.decision_hash:
            raise ValueError("review decision hash mismatch")


def _iso(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("review timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("review timestamp must include timezone")
    return value


def detect_candidate_conflicts(
    candidates: Iterable[CandidateRecord],
) -> tuple[ReviewConflict, ...]:
    by_field: dict[str, dict[str, list[str]]] = {}
    for candidate in candidates:
        for field in candidate.fields:
            if field.parsed_value is None:
                continue
            bucket = by_field.setdefault(field.name, {})
            bucket.setdefault(field.parsed_value, []).append(candidate.proof_hash)

    conflicts = []
    for field_name, values in sorted(by_field.items()):
        if len(values) <= 1:
            continue
        conflicts.append(ReviewConflict(
            field_name=field_name,
            values=tuple(sorted(values)),
            candidate_hashes=tuple(sorted({
                candidate_hash
                for hashes in values.values()
                for candidate_hash in hashes
            })),
        ))
    return tuple(conflicts)


def _deterministic_blockers(
    transaction: HistoricalTransaction,
    candidates: tuple[CandidateRecord, ...],
    conflicts: tuple[ReviewConflict, ...],
) -> tuple[str, ...]:
    blockers = {f"CONFLICT:{item.field_name}" for item in conflicts}

    for candidate in candidates:
        for field in candidate.fields:
            if field.status is CandidateFieldStatus.AMBIGUOUS:
                blockers.add(
                    f"AMBIGUOUS_FIELD:{candidate.candidate_id}:{field.name}"
                )

        warnings = set(candidate.warnings)
        if "PDF_TEXT_LAYER_NOT_RAW_VISUAL_VERIFICATION" in warnings:
            blockers.add(
                f"RAW_VISUAL_VERIFICATION_REQUIRED:{candidate.candidate_id}"
            )

        if (
            "TIMEZONE_NOT_ENCODED_IN_SOURCE_COLUMN" in warnings
            and transaction.time_precision is TimePrecision.EXACT_TIMESTAMP
        ):
            blockers.add(
                f"TIMEZONE_REQUIRED_FOR_EXACT_TIMESTAMP:{candidate.candidate_id}"
            )

        if (
            "FIRST_TRADE_TIME_IS_NOT_COMPLETE_TRADE_ECONOMICS" in warnings
            and any(
                value is not None
                for value in (
                    transaction.quantity,
                    transaction.execution_price,
                    transaction.trade_amount,
                    transaction.documented_profit,
                )
            )
        ):
            blockers.add(
                f"CANDIDATE_DOES_NOT_SUPPORT_TRADE_ECONOMICS:{candidate.candidate_id}"
            )

        if (
            "ACADEMIC_RECONSTRUCTION" in warnings
            and transaction.fact_status is not FactStatus.ACADEMIC_RECONSTRUCTION
        ):
            blockers.add(
                f"ACADEMIC_SOURCE_STATUS_MISMATCH:{candidate.candidate_id}"
            )

    return tuple(sorted(blockers))


def build_transaction_review_item(
    proposed_transaction: HistoricalTransaction,
    *,
    event: InformationEvent,
    candidates: Iterable[CandidateRecord],
    cases: CaseRegistry,
    events: EventRegistry,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
    created_at: str,
    created_by: str,
) -> ReviewQueueItem:
    created_at = _iso(created_at)
    if not created_by.strip():
        raise ValueError("created_by is required")

    verify_transaction_provenance(
        proposed_transaction,
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
    registered_event = events.get(event.event_id)
    if registered_event.proof_hash != event.proof_hash:
        raise ValueError("event is not the registered event revision")
    if event.case_id != proposed_transaction.case_id:
        raise ValueError("transaction/event case mismatch")
    if proposed_transaction.issuer_id not in event.issuer_ids:
        raise ValueError("transaction issuer is not covered by information event")

    candidate_tuple = tuple(sorted(
        candidates,
        key=lambda item: (item.source_ref.proof_hash, item.candidate_id),
    ))
    if not candidate_tuple:
        raise ValueError("review item requires at least one candidate")
    if not any(item.kind is CandidateKind.TRANSACTION for item in candidate_tuple):
        raise ValueError("review item requires a transaction candidate")

    case = cases.get(proposed_transaction.case_id)
    case_ref_hashes = {link.ref.proof_hash for link in case.artifacts}
    for candidate in candidate_tuple:
        if candidate.case_id not in {None, proposed_transaction.case_id}:
            raise ValueError("candidate belongs to a different case")
        artifact_manifest.resolve_ref(candidate.source_ref)
        if candidate.source_ref.proof_hash not in case_ref_hashes:
            raise ValueError("candidate source is not linked to canonical case")

    if proposed_transaction.source_ref.proof_hash not in {
        item.source_ref.proof_hash for item in candidate_tuple
    }:
        raise ValueError(
            "proposed transaction source is not represented by candidate evidence"
        )

    parties = {item.party_id: item for item in case.parties}
    issuers = {item.issuer_id: item for item in case.issuers}
    identity = ReviewIdentitySnapshot(
        case_id=case.case_id,
        case_title=case.title,
        trader_party_id=proposed_transaction.trader_party_id,
        trader_name=parties[proposed_transaction.trader_party_id].display_name,
        issuer_id=proposed_transaction.issuer_id,
        issuer_name=issuers[proposed_transaction.issuer_id].legal_name,
        event_id=event.event_id,
        event_summary=event.information_summary,
        public_release_hash=event.public_release.proof_hash,
    )

    conflicts = detect_candidate_conflicts(candidate_tuple)
    blockers = _deterministic_blockers(
        proposed_transaction,
        candidate_tuple,
        conflicts,
    )

    body = {
        "schema": 1,
        "proposed_transaction_hash": proposed_transaction.proof_hash,
        "event_id": event.event_id,
        "event_proof_hash": event.proof_hash,
        "identity_hash": identity.proof_hash,
        "candidate_hashes": sorted(item.proof_hash for item in candidate_tuple),
        "conflict_hashes": sorted(item.proof_hash for item in conflicts),
        "blockers": sorted(blockers),
        "normalized_row_hash": proposed_transaction.proof_hash,
        "created_at": created_at,
        "created_by": created_by.strip(),
    }
    item_hash = canonical_hash(body)
    return ReviewQueueItem(
        review_id="review:" + item_hash,
        proposed_transaction=proposed_transaction,
        event_id=event.event_id,
        event_proof_hash=event.proof_hash,
        identity=identity,
        candidates=candidate_tuple,
        conflicts=conflicts,
        blockers=blockers,
        normalized_row_hash=proposed_transaction.proof_hash,
        created_at=created_at,
        created_by=created_by.strip(),
        review_item_hash=item_hash,
    )


def verify_review_item(
    item: ReviewQueueItem,
    *,
    cases: CaseRegistry,
    events: EventRegistry,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
) -> None:
    item.verify_integrity()
    event = events.get(item.event_id)
    if event.proof_hash != item.event_proof_hash:
        raise ValueError("review item event proof mismatch")
    rebuilt = build_transaction_review_item(
        item.proposed_transaction,
        event=event,
        candidates=item.candidates,
        cases=cases,
        events=events,
        source_registry=source_registry,
        artifact_manifest=artifact_manifest,
        created_at=item.created_at,
        created_by=item.created_by,
    )
    if rebuilt.review_item_hash != item.review_item_hash:
        raise ValueError("review item does not deterministically rebuild")


def decide_review_item(
    item: ReviewQueueItem,
    *,
    decision: ReviewDecision,
    reviewer_id: str,
    reviewed_at: str,
    rationale: str,
    cases: CaseRegistry,
    events: EventRegistry,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
) -> ReviewDecisionRecord:
    if decision is ReviewDecision.PENDING:
        raise ValueError("PENDING is not a completed review decision")
    if not reviewer_id.strip() or not rationale.strip():
        raise ValueError("reviewer_id and rationale are required")
    reviewed_at = _iso(reviewed_at)

    verify_review_item(
        item,
        cases=cases,
        events=events,
        source_registry=source_registry,
        artifact_manifest=artifact_manifest,
    )

    if decision is ReviewDecision.APPROVED and item.blockers:
        raise ValueError(
            "blocked review item cannot be approved: " + ", ".join(item.blockers)
        )

    accepted = (
        item.normalized_row_hash
        if decision is ReviewDecision.APPROVED
        else None
    )
    body = {
        "schema": 1,
        "review_id": item.review_id,
        "review_item_hash": item.review_item_hash,
        "decision": decision.value,
        "reviewer_id": reviewer_id.strip(),
        "reviewed_at": reviewed_at,
        "rationale": rationale.strip(),
        "accepted_transaction_hash": accepted,
    }
    return ReviewDecisionRecord(
        review_id=item.review_id,
        review_item_hash=item.review_item_hash,
        decision=decision,
        reviewer_id=reviewer_id.strip(),
        reviewed_at=reviewed_at,
        rationale=rationale.strip(),
        accepted_transaction_hash=accepted,
        decision_hash=canonical_hash(body),
    )


def accept_reviewed_transaction(
    item: ReviewQueueItem,
    review: ReviewDecisionRecord,
    *,
    transactions: TransactionRegistry,
    cases: CaseRegistry,
    events: EventRegistry,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
) -> HistoricalTransaction:
    review.verify_integrity()
    verify_review_item(
        item,
        cases=cases,
        events=events,
        source_registry=source_registry,
        artifact_manifest=artifact_manifest,
    )
    if review.review_id != item.review_id:
        raise ValueError("review decision item mismatch")
    if review.review_item_hash != item.review_item_hash:
        raise ValueError("review decision proof mismatch")
    if review.decision is not ReviewDecision.APPROVED:
        raise ValueError("only APPROVED review decisions can enter accepted corpus")
    if review.accepted_transaction_hash != item.normalized_row_hash:
        raise ValueError("accepted transaction hash mismatch")
    if item.blockers:
        raise ValueError("review item still has blockers")

    return transactions.register(
        item.proposed_transaction,
        cases=cases,
        source_registry=source_registry,
        artifact_manifest=artifact_manifest,
    )


def render_review_item_markdown(item: ReviewQueueItem) -> str:
    lines = [
        "# Historical MNPI Transaction Review",
        "",
        f"- Review ID: `{item.review_id}`",
        f"- Normalized row hash: `{item.normalized_row_hash}`",
        f"- Case: **{item.identity.case_title}** (`{item.identity.case_id}`)",
        f"- Trader: **{item.identity.trader_name}** (`{item.identity.trader_party_id}`)",
        f"- Issuer: **{item.identity.issuer_name}** (`{item.identity.issuer_id}`)",
        f"- Event: **{item.identity.event_summary}** (`{item.identity.event_id}`)",
        f"- Public-release boundary hash: `{item.identity.public_release_hash}`",
        f"- Fact status: **{item.proposed_transaction.fact_status.value}**",
        f"- Transaction source locator: `{item.proposed_transaction.source_ref.locator}`",
        f"- Status source locator: `{item.proposed_transaction.status_ref.locator}`",
        "",
        "## Proposed normalized values",
        "",
        f"- Time precision: **{item.proposed_transaction.time_precision.value}**",
        f"- Trade timestamp: {item.proposed_transaction.trade_timestamp or '—'}",
        f"- Trade date: {item.proposed_transaction.trade_date or '—'}",
        f"- Quantity: {item.proposed_transaction.quantity or '—'}",
        f"- Execution price: {item.proposed_transaction.execution_price or '—'}",
        f"- Trade amount: {item.proposed_transaction.trade_amount or '—'}",
        f"- Documented profit: {item.proposed_transaction.documented_profit or '—'}",
        "",
        "## Candidate evidence",
        "",
    ]
    for candidate in item.candidates:
        lines.extend([
            f"### {candidate.candidate_id}",
            f"- Extractor: `{candidate.extractor_id}@{candidate.extractor_version}`",
            f"- Locator: `{candidate.source_ref.locator}`",
            f"- Excerpt SHA-256: `{candidate.excerpt_sha256}`",
            f"- Excerpt: {candidate.raw_excerpt}",
        ])
        for field in candidate.fields:
            lines.append(
                f"- {field.name}: raw=`{field.raw_value}`; "
                f"parsed=`{field.parsed_value if field.parsed_value is not None else 'NULL'}`; "
                f"status={field.status.value}"
            )
        if candidate.warnings:
            lines.append("- Warnings: " + ", ".join(candidate.warnings))
        lines.append("")

    lines.extend([
        "## Conflicts / blockers",
        "",
        (
            "- Conflicts: " + ", ".join(item.field_name for item in item.conflicts)
            if item.conflicts else "- Conflicts: none"
        ),
        (
            "- Blockers: " + ", ".join(item.blockers)
            if item.blockers else "- Blockers: none"
        ),
        "",
        "A parser candidate is not accepted corpus data until an explicit review decision approves this exact normalized-row hash.",
    ])
    return "\n".join(lines)


__all__ = [
    "ReviewConflict",
    "ReviewDecision",
    "ReviewDecisionRecord",
    "ReviewIdentitySnapshot",
    "ReviewQueueItem",
    "accept_reviewed_transaction",
    "build_transaction_review_item",
    "decide_review_item",
    "detect_candidate_conflicts",
    "render_review_item_markdown",
    "verify_review_item",
]
