"""Proof-bound buyer review workflow for Freight Recovery.

This workflow accepts human decisions only for cases that the canonical review
routing marked BUYER_REVIEW_READY. Evidence-remediation cases cannot be
confirmed, rejected, or otherwise promoted here; they must be remediated
upstream and the audit rerun.

The resulting FindingReview objects are bound to the exact frozen finding proof
and can be consumed by downstream reporting and separately authorized external
action controls.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Iterable

from freight.contracts import TruthManifest, VALIDATED, canonical_hash
from freight.pilot_reporting import (
    FindingReview,
    ReviewDisposition,
    make_finding_review,
    verify_finding_review,
)
from freight.review_packet import REVIEW_VALIDATED_FINDING, ReviewPacket
from freight.review_routing import ReviewRouting, route_review_packet


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class BuyerReviewState(str, Enum):
    NO_BUYER_REVIEW_READY = "NO_BUYER_REVIEW_READY"
    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True)
class BuyerReviewDecisionInput:
    case_hash: str
    disposition: ReviewDisposition
    reviewer_minutes: int
    reviewed_at: str

    def __post_init__(self):
        if not isinstance(self.case_hash, str) or not SHA256_RE.fullmatch(self.case_hash):
            raise ValueError("case_hash must be lowercase SHA-256")
        if not isinstance(self.disposition, ReviewDisposition):
            raise ValueError("disposition must be a ReviewDisposition")
        if type(self.reviewer_minutes) is not int or self.reviewer_minutes < 0:
            raise ValueError("reviewer_minutes must be a non-negative integer")
        if not isinstance(self.reviewed_at, str) or not self.reviewed_at.strip():
            raise ValueError("reviewed_at is required")


@dataclass(frozen=True)
class BuyerCaseReview:
    case_hash: str
    finding_id: str
    finding_proof_hash: str
    disposition: str
    reviewer_minutes: int
    reviewed_at: str
    review_hash: str
    record_hash: str


@dataclass(frozen=True)
class BuyerReviewBatch:
    buyer_id: str
    business_unit: str
    review_packet_hash: str
    review_routing_hash: str
    truth_hash: str
    reviewer_role: str
    state: str
    buyer_review_case_count: int
    submitted_decision_count: int
    confirmed_count: int
    false_positive_count: int
    unresolved_count: int
    pending_case_hashes: tuple[str, ...]
    records: tuple[BuyerCaseReview, ...]
    finding_reviews: tuple[FindingReview, ...]
    batch_hash: str


def _verify_truth(truth: TruthManifest) -> None:
    body = {
        "schema": 3,
        "buyer_id": truth.buyer_id,
        "business_unit": truth.business_unit,
        "population_hash": truth.population_hash,
        "authorities": [asdict(authority) for authority in truth.authorities],
        "findings": [asdict(finding) for finding in truth.findings],
    }
    if canonical_hash(body) != truth.truth_hash:
        raise ValueError("truth hash mismatch")

    seen: set[str] = set()
    for finding in truth.findings:
        if finding.finding_id in seen:
            raise ValueError("duplicate finding_id in truth")
        seen.add(finding.finding_id)
        finding_body = {
            "schema": 2,
            "finding_id": finding.finding_id,
            "buyer_id": finding.buyer_id,
            "business_unit": finding.business_unit,
            "invoice_id": finding.invoice_id,
            "shipment_id": finding.shipment_id,
            "customer_id": finding.customer_id,
            "carrier_id": finding.carrier_id,
            "currency": finding.currency,
            "authority_id": finding.authority_id,
            "expected_cents": finding.expected_cents,
            "actual_cents": finding.actual_cents,
            "status": finding.status,
        }
        if canonical_hash(finding_body) != finding.proof_hash:
            raise ValueError("finding proof hash mismatch: " + finding.finding_id)


def build_buyer_review_batch(
    *,
    review_packet: ReviewPacket,
    review_routing: ReviewRouting,
    truth: TruthManifest,
    reviewer_role: str,
    decisions: Iterable[BuyerReviewDecisionInput] = (),
) -> BuyerReviewBatch:
    canonical_routing = route_review_packet(review_packet)
    if review_routing != canonical_routing:
        raise ValueError("review routing does not match canonical review packet")

    if not isinstance(reviewer_role, str) or not reviewer_role.strip():
        raise ValueError("reviewer_role is required")
    reviewer_role = reviewer_role.strip()

    _verify_truth(truth)
    if (truth.buyer_id, truth.business_unit) != (
        review_packet.buyer_id,
        review_packet.business_unit,
    ):
        raise ValueError("truth scope mismatch with review packet")
    if truth.truth_hash != review_packet.truth_hash:
        raise ValueError("truth hash does not match review packet")

    case_index = {case.case_hash: case for case in review_packet.cases}
    if len(case_index) != len(review_packet.cases):
        raise ValueError("duplicate case hash in review packet")
    finding_index = {finding.finding_id: finding for finding in truth.findings}

    allowed = tuple(review_routing.buyer_review_case_hashes)
    allowed_set = set(allowed)
    remediation_set = set(review_routing.remediation_case_hashes)

    decision_index: dict[str, BuyerReviewDecisionInput] = {}
    for decision in tuple(decisions):
        if not isinstance(decision, BuyerReviewDecisionInput):
            raise ValueError("decisions must contain BuyerReviewDecisionInput values")
        if decision.case_hash in decision_index:
            raise ValueError("duplicate buyer review decision: " + decision.case_hash)
        case = case_index.get(decision.case_hash)
        if case is None:
            raise ValueError("buyer review decision references unknown case")
        if decision.case_hash in remediation_set:
            raise ValueError(
                "case is not buyer-review-ready; remediation and audit rerun are required"
            )
        if decision.case_hash not in allowed_set:
            raise ValueError("case is not buyer-review-ready")
        decision_index[decision.case_hash] = decision

    records: list[BuyerCaseReview] = []
    finding_reviews: list[FindingReview] = []

    for case_hash in allowed:
        case = case_index.get(case_hash)
        if case is None:
            raise ValueError("buyer-review-ready case missing from review packet")
        if case.action_hint != REVIEW_VALIDATED_FINDING:
            raise ValueError("buyer-review-ready case has unexpected action hint")
        if not case.finding_id or not case.finding_proof_hash:
            raise ValueError("buyer-review-ready case is missing finding proof")

        finding = finding_index.get(case.finding_id)
        if finding is None:
            raise ValueError("buyer-review-ready case references unknown finding")
        if finding.status != VALIDATED or finding.validated_cents <= 0:
            raise ValueError("buyer review requires a positive VALIDATED finding")
        if finding.proof_hash != case.finding_proof_hash:
            raise ValueError("review case finding proof does not match frozen truth")

        decision = decision_index.get(case_hash)
        if decision is None:
            continue

        review = make_finding_review(
            finding,
            decision.disposition,
            reviewer_role=reviewer_role,
            reviewed_at=decision.reviewed_at,
            reviewer_minutes=decision.reviewer_minutes,
        )
        verify_finding_review(review, finding, require_bound=True)
        assert review.review_hash is not None
        assert review.reviewed_at is not None

        record_body = {
            "schema": 1,
            "review_packet_hash": review_packet.packet_hash,
            "review_routing_hash": review_routing.routing_hash,
            "truth_hash": truth.truth_hash,
            "case_hash": case_hash,
            "finding_id": finding.finding_id,
            "finding_proof_hash": finding.proof_hash,
            "disposition": review.disposition.value,
            "reviewer_minutes": review.reviewer_minutes,
            "reviewer_role": review.reviewer_role,
            "reviewed_at": review.reviewed_at,
            "review_hash": review.review_hash,
        }
        records.append(BuyerCaseReview(
            case_hash=case_hash,
            finding_id=finding.finding_id,
            finding_proof_hash=finding.proof_hash,
            disposition=review.disposition.value,
            reviewer_minutes=review.reviewer_minutes,
            reviewed_at=review.reviewed_at,
            review_hash=review.review_hash,
            record_hash=canonical_hash(record_body),
        ))
        finding_reviews.append(review)

    pending = tuple(case_hash for case_hash in allowed if case_hash not in decision_index)
    if not allowed:
        state = BuyerReviewState.NO_BUYER_REVIEW_READY
    elif pending:
        state = BuyerReviewState.PARTIAL
    else:
        state = BuyerReviewState.COMPLETE

    records_tuple = tuple(records)
    reviews_tuple = tuple(finding_reviews)
    confirmed = sum(
        record.disposition == ReviewDisposition.CONFIRMED.value
        for record in records_tuple
    )
    false_positive = sum(
        record.disposition == ReviewDisposition.FALSE_POSITIVE.value
        for record in records_tuple
    )
    unresolved = sum(
        record.disposition == ReviewDisposition.UNRESOLVED.value
        for record in records_tuple
    )

    body = {
        "schema": 1,
        "buyer_id": truth.buyer_id,
        "business_unit": truth.business_unit,
        "review_packet_hash": review_packet.packet_hash,
        "review_routing_hash": review_routing.routing_hash,
        "truth_hash": truth.truth_hash,
        "reviewer_role": reviewer_role,
        "state": state.value,
        "buyer_review_case_count": len(allowed),
        "submitted_decision_count": len(records_tuple),
        "confirmed_count": confirmed,
        "false_positive_count": false_positive,
        "unresolved_count": unresolved,
        "pending_case_hashes": pending,
        "records": [asdict(record) for record in records_tuple],
    }
    return BuyerReviewBatch(
        buyer_id=truth.buyer_id,
        business_unit=truth.business_unit,
        review_packet_hash=review_packet.packet_hash,
        review_routing_hash=review_routing.routing_hash,
        truth_hash=truth.truth_hash,
        reviewer_role=reviewer_role,
        state=state.value,
        buyer_review_case_count=len(allowed),
        submitted_decision_count=len(records_tuple),
        confirmed_count=confirmed,
        false_positive_count=false_positive,
        unresolved_count=unresolved,
        pending_case_hashes=pending,
        records=records_tuple,
        finding_reviews=reviews_tuple,
        batch_hash=canonical_hash(body),
    )


def verify_buyer_review_batch(
    *,
    batch: BuyerReviewBatch,
    review_packet: ReviewPacket,
    review_routing: ReviewRouting,
    truth: TruthManifest,
) -> None:
    if not isinstance(batch, BuyerReviewBatch):
        raise ValueError("batch must be a BuyerReviewBatch")
    decisions = tuple(
        BuyerReviewDecisionInput(
            case_hash=record.case_hash,
            disposition=ReviewDisposition(record.disposition),
            reviewer_minutes=record.reviewer_minutes,
            reviewed_at=record.reviewed_at,
        )
        for record in batch.records
    )
    expected = build_buyer_review_batch(
        review_packet=review_packet,
        review_routing=review_routing,
        truth=truth,
        reviewer_role=batch.reviewer_role,
        decisions=decisions,
    )
    if expected != batch:
        raise ValueError("buyer review batch does not match current review proofs")


def render_buyer_review_markdown(batch: BuyerReviewBatch) -> str:
    lines = [
        "# Freight Recovery — Buyer Review Decisions",
        "",
        f"- Buyer: **{batch.buyer_id}**",
        f"- Business unit: **{batch.business_unit}**",
        f"- State: **{batch.state}**",
        f"- Reviewer role: **{batch.reviewer_role}**",
        f"- Buyer-review-ready cases: **{batch.buyer_review_case_count}**",
        f"- Decisions submitted: **{batch.submitted_decision_count}**",
        f"- Confirmed: **{batch.confirmed_count}**",
        f"- False positive: **{batch.false_positive_count}**",
        f"- Unresolved: **{batch.unresolved_count}**",
        f"- Pending buyer cases: **{len(batch.pending_case_hashes)}**",
        f"- Batch hash: `{batch.batch_hash}`",
        "",
        "These decisions apply only to cases previously routed as buyer-review-ready.",
        "Evidence-remediation cases are excluded and must be remediated upstream and rerun.",
        "This artifact does not authorize carrier contact, dispute submission, settlement acceptance, or money movement.",
        "",
    ]
    for record in batch.records:
        lines.extend([
            f"## {record.finding_id}",
            "",
            f"- Disposition: **{record.disposition}**",
            f"- Reviewer minutes: **{record.reviewer_minutes}**",
            f"- Reviewed at: **{record.reviewed_at}**",
            f"- Finding proof: `{record.finding_proof_hash}`",
            f"- Review proof: `{record.review_hash}`",
            f"- Case proof: `{record.case_hash}`",
            "",
        ])
    return "\n".join(lines)
