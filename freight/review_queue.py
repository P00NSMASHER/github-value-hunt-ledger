"""Deterministic reviewer queue for Freight Recovery finding derivations.

The queue does not make review decisions. It orders already-derived work so
reviewers see supported money-bearing findings before weaker or evidence-missing
items, while retaining deterministic provenance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from freight.contracts import REVIEW, VALIDATED, canonical_hash
from freight.finding_factory import (
    CLEAR,
    FindingFactoryBatch,
    verify_finding_factory_batch,
)


VALIDATED_MONEY = "VALIDATED_MONEY"
REVIEW_MONEY = "REVIEW_MONEY"
REVIEW_EVIDENCE = "REVIEW_EVIDENCE"


@dataclass(frozen=True)
class ReviewQueueItem:
    queue_position: int
    charge_id: str
    priority_class: str
    decision: str
    reason: str
    billed_cents: int
    expected_cents: int | None
    variance_cents: int | None
    finding_id: str | None
    finding_proof_hash: str | None
    derivation_hash: str
    item_hash: str


@dataclass(frozen=True)
class ReviewQueue:
    factory_hash: str
    items: tuple[ReviewQueueItem, ...]
    queue_hash: str


def _priority(item) -> tuple[int, int, str]:
    variance = item.variance_cents if item.variance_cents is not None else -1
    if item.decision == VALIDATED:
        bucket = 0
    elif item.decision == REVIEW and variance > 0:
        bucket = 1
    else:
        bucket = 2
    return (bucket, -variance, item.charge_id)


def build_review_queue(batch: FindingFactoryBatch) -> ReviewQueue:
    verify_finding_factory_batch(batch)
    candidates = [item for item in batch.derivations if item.decision != CLEAR]
    candidates.sort(key=_priority)

    items: list[ReviewQueueItem] = []
    for position, derivation in enumerate(candidates, 1):
        variance = derivation.variance_cents
        if derivation.decision == VALIDATED:
            priority_class = VALIDATED_MONEY
        elif variance is not None and variance > 0:
            priority_class = REVIEW_MONEY
        else:
            priority_class = REVIEW_EVIDENCE
        finding = derivation.finding
        body = {
            "schema": 1,
            "factory_hash": batch.factory_hash,
            "queue_position": position,
            "charge_id": derivation.charge_id,
            "priority_class": priority_class,
            "decision": derivation.decision,
            "reason": derivation.reason,
            "billed_cents": derivation.billed_cents,
            "expected_cents": derivation.expected_cents,
            "variance_cents": variance,
            "finding_id": finding.finding_id if finding else None,
            "finding_proof_hash": finding.proof_hash if finding else None,
            "derivation_hash": derivation.derivation_hash,
        }
        items.append(ReviewQueueItem(
            queue_position=position,
            charge_id=derivation.charge_id,
            priority_class=priority_class,
            decision=derivation.decision,
            reason=derivation.reason,
            billed_cents=derivation.billed_cents,
            expected_cents=derivation.expected_cents,
            variance_cents=variance,
            finding_id=finding.finding_id if finding else None,
            finding_proof_hash=finding.proof_hash if finding else None,
            derivation_hash=derivation.derivation_hash,
            item_hash=canonical_hash(body),
        ))

    items_tuple = tuple(items)
    queue_body = {
        "schema": 1,
        "factory_hash": batch.factory_hash,
        "items": [asdict(item) for item in items_tuple],
    }
    return ReviewQueue(
        factory_hash=batch.factory_hash,
        items=items_tuple,
        queue_hash=canonical_hash(queue_body),
    )
