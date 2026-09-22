"""Deterministic cross-branch RecoveryWorks operator queues."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ledger import LedgerRecord, RecoveryLedger
from .models import Branch, CaseState, FindingState

EVIDENCE_REVIEW = "EVIDENCE_REVIEW"
HUMAN_REVIEW = "HUMAN_REVIEW"
AWAITING_AUTHORIZATION = "AWAITING_AUTHORIZATION"
READY_TO_SUBMIT = "READY_TO_SUBMIT"
AWAITING_OUTCOME = "AWAITING_OUTCOME"
COMPLETED = "COMPLETED"
REJECTED = "REJECTED"


@dataclass(frozen=True)
class ReviewQueueItem:
    finding_id: str
    client_id: str
    branch: str
    currency: str
    potential_recovery_cents: int
    case_state: str
    queue: str
    blockers: tuple[str, ...]
    rank_in_queue_currency: int = 0


def _classify(record: LedgerRecord) -> tuple[str, tuple[str, ...]]:
    finding = record.finding
    blockers: list[str] = []

    if record.case_state is CaseState.REJECTED:
        return REJECTED, ()

    if finding.state is FindingState.REVIEW:
        if finding.rule is None:
            blockers.append("MISSING_CONTROLLING_RULE")
        elif not finding.rule.verified_controlling:
            blockers.append("UNVERIFIED_CONTROLLING_RULE")
        if not all(ref.verified for ref in finding.evidence):
            blockers.append("UNVERIFIED_EVIDENCE")
        if not blockers:
            blockers.append("REVIEW_REQUIRED")
        return EVIDENCE_REVIEW, tuple(blockers)

    if record.case_state is CaseState.VALIDATED:
        if not record.reviewer_approved:
            return HUMAN_REVIEW, ("HUMAN_REVIEW_REQUIRED",)
        if not record.authorization_id:
            return AWAITING_AUTHORIZATION, ("CUSTOMER_AUTHORIZATION_REQUIRED",)

    if record.case_state is CaseState.AUTHORIZED:
        return READY_TO_SUBMIT, ()

    if record.case_state is CaseState.CLAIMED:
        return AWAITING_OUTCOME, ("SETTLEMENT_OR_DENIAL_OUTCOME_PENDING",)

    if record.case_state is CaseState.RECOVERED:
        return COMPLETED, ()

    return EVIDENCE_REVIEW, ("UNRECOGNIZED_LIFECYCLE_STATE",)


def build_review_queue(
    ledger: RecoveryLedger,
    *,
    client_id: str | None = None,
    branch: Branch | None = None,
    currency: str | None = None,
) -> tuple[ReviewQueueItem, ...]:
    rows: list[ReviewQueueItem] = []
    for record in ledger.records():
        finding = record.finding
        if client_id is not None and finding.client_id != client_id:
            continue
        if branch is not None and finding.branch is not branch:
            continue
        if currency is not None and finding.currency != currency:
            continue
        queue, blockers = _classify(record)
        rows.append(ReviewQueueItem(
            finding_id=finding.finding_id,
            client_id=finding.client_id,
            branch=finding.branch.value,
            currency=finding.currency,
            potential_recovery_cents=finding.potential_recovery_cents,
            case_state=record.case_state.value,
            queue=queue,
            blockers=blockers,
        ))

    order = {
        READY_TO_SUBMIT: 0,
        HUMAN_REVIEW: 1,
        AWAITING_AUTHORIZATION: 2,
        EVIDENCE_REVIEW: 3,
        AWAITING_OUTCOME: 4,
        COMPLETED: 5,
        REJECTED: 6,
    }
    rows.sort(key=lambda row: (
        order[row.queue],
        row.currency,
        -row.potential_recovery_cents,
        row.finding_id,
    ))

    ranks: dict[tuple[str, str], int] = {}
    ranked: list[ReviewQueueItem] = []
    for row in rows:
        key = (row.queue, row.currency)
        rank = ranks.get(key, 0) + 1
        ranks[key] = rank
        ranked.append(ReviewQueueItem(
            finding_id=row.finding_id,
            client_id=row.client_id,
            branch=row.branch,
            currency=row.currency,
            potential_recovery_cents=row.potential_recovery_cents,
            case_state=row.case_state,
            queue=row.queue,
            blockers=row.blockers,
            rank_in_queue_currency=rank,
        ))
    return tuple(ranked)


def review_queue_summary(items: tuple[ReviewQueueItem, ...]) -> dict[str, Any]:
    queues: dict[str, dict[str, Any]] = {}
    for item in items:
        queue = queues.setdefault(item.queue, {"cases": 0, "currencies": {}})
        queue["cases"] += 1
        bucket = queue["currencies"].setdefault(
            item.currency,
            {"cases": 0, "potential_recovery_cents": 0},
        )
        bucket["cases"] += 1
        bucket["potential_recovery_cents"] += item.potential_recovery_cents
    return {
        "cases": len(items),
        "queues": queues,
    }
