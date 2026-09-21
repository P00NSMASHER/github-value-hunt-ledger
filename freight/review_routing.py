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


def _verify_case_hash(packet: ReviewPacket, case) -> None:
    charge = {
        "buyer_id": packet.buyer_id,
        "business_unit": packet.business_unit,
        "invoice_id": case.invoice_id,
        "shipment_id": case.shipment_id,
        "customer_id": case.customer_id,
        "carrier_id": case.carrier_id,
        "currency": case.currency,
        "charge_id": case.charge_id,
        "charge_code": case.charge_code,
        "service_date": case.service_date,
        "quantity_units": case.quantity_units,
        "billed_cents": case.billed_cents,
        "source_hash": case.charge_source_hash,
    }
    body = {
        "schema": 1,
        "factory_hash": packet.factory_hash,
        "queue_hash": packet.queue_hash,
        "queue_position": case.queue_position,
        "priority_class": case.priority_class,
        "action_hint": case.action_hint,
        "charge": charge,
        "charge_hash": case.charge_hash,
        "expected_cents": case.expected_cents,
        "variance_cents": case.variance_cents,
        "decision": case.decision,
        "reason": case.reason,
        "rule_evidence": [asdict(rule) for rule in case.rule_evidence],
        "finding_id": case.finding_id,
        "finding_proof_hash": case.finding_proof_hash,
        "derivation_hash": case.derivation_hash,
        "queue_item_hash": case.queue_item_hash,
    }
    if canonical_hash(body) != case.case_hash:
        raise ValueError("review case hash mismatch: " + case.charge_id)


def _verify_packet_hash(packet: ReviewPacket) -> None:
    for case in packet.cases:
        _verify_case_hash(packet, case)
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
