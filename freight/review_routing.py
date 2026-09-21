"""Deterministic routing for Freight Recovery review cases.

Routing separates buyer-review-ready validated findings from cases that need
authority/rule/evidence remediation before those cases can become final.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass

from freight.contracts import canonical_hash
from freight.review_packet import (
    ADD_APPLICABLE_RULE,
    INVESTIGATE_EVIDENCE,
    RESOLVE_RULE_AMBIGUITY,
    REVIEW_VALIDATED_FINDING,
    VERIFY_CONTROLLING_AUTHORITY,
    ReviewPacket,
)


NO_REVIEW = "NO_REVIEW"
BUYER_REVIEW_READY = "BUYER_REVIEW_READY"
EVIDENCE_REMEDIATION_REQUIRED = "EVIDENCE_REMEDIATION_REQUIRED"
MIXED_REVIEW_AND_REMEDIATION = "MIXED_REVIEW_AND_REMEDIATION"

REMEDIATION_ACTIONS = frozenset({
    VERIFY_CONTROLLING_AUTHORITY,
    ADD_APPLICABLE_RULE,
    RESOLVE_RULE_AMBIGUITY,
    INVESTIGATE_EVIDENCE,
})


@dataclass(frozen=True)
class ReviewRouting:
    review_packet_hash: str
    route: str
    buyer_review_case_hashes: tuple[str, ...]
    remediation_case_hashes: tuple[str, ...]
    remediation_action_counts: tuple[tuple[str, int], ...]
    buyer_review_case_count: int
    evidence_remediation_case_count: int
    rerun_required: bool
    routing_hash: str


def _verify_packet_hash(packet: ReviewPacket) -> None:
    body = {
        "schema": 1,
        "buyer_id": packet.buyer_id,
        "business_unit": packet.business_unit,
        "factory_hash": packet.factory_hash,
        "queue_hash": packet.queue_hash,
        "truth_hash": packet.truth_hash,
        "cases": [asdict(case) for case in packet.cases],
    }
    if canonical_hash(body) != packet.packet_hash:
        raise ValueError("review packet hash mismatch")


def route_review_packet(packet: ReviewPacket) -> ReviewRouting:
    _verify_packet_hash(packet)

    buyer_cases = []
    remediation_cases = []
    remediation_actions = Counter()

    for case in packet.cases:
        if case.action_hint == REVIEW_VALIDATED_FINDING:
            buyer_cases.append(case.case_hash)
            continue
        if case.action_hint not in REMEDIATION_ACTIONS:
            raise ValueError("unsupported review action hint: " + case.action_hint)
        remediation_cases.append(case.case_hash)
        remediation_actions[case.action_hint] += 1

    buyer_hashes = tuple(buyer_cases)
    remediation_hashes = tuple(remediation_cases)
    action_counts = tuple(sorted(remediation_actions.items()))

    if not buyer_hashes and not remediation_hashes:
        route = NO_REVIEW
    elif buyer_hashes and remediation_hashes:
        route = MIXED_REVIEW_AND_REMEDIATION
    elif buyer_hashes:
        route = BUYER_REVIEW_READY
    else:
        route = EVIDENCE_REMEDIATION_REQUIRED

    body = {
        "schema": 1,
        "review_packet_hash": packet.packet_hash,
        "route": route,
        "buyer_review_case_hashes": buyer_hashes,
        "remediation_case_hashes": remediation_hashes,
        "remediation_action_counts": action_counts,
        "buyer_review_case_count": len(buyer_hashes),
        "evidence_remediation_case_count": len(remediation_hashes),
        "rerun_required": bool(remediation_hashes),
    }
    return ReviewRouting(
        review_packet_hash=packet.packet_hash,
        route=route,
        buyer_review_case_hashes=buyer_hashes,
        remediation_case_hashes=remediation_hashes,
        remediation_action_counts=action_counts,
        buyer_review_case_count=len(buyer_hashes),
        evidence_remediation_case_count=len(remediation_hashes),
        rerun_required=bool(remediation_hashes),
        routing_hash=canonical_hash(body),
    )
