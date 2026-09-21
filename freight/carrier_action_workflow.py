"""Proof-bound carrier-action proposals and authorization handoff.

This layer removes manual re-keying between recovery claims and external action
authorization. Claims are grouped by carrier + customer/payee + currency.
Creating a proposal never authorizes or executes an external action.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import Enum

from freight.buyer_review_workflow import BuyerReviewBatch
from freight.contracts import TruthManifest, canonical_hash
from freight.engagement_state import EngagementResolution
from freight.external_action_authorization import (
    ActionType,
    ExternalActionAuthorization,
    issue_authorization,
)
from freight.pilot_reporting import ReviewDisposition
from freight.recovery_claim_workflow import (
    RecoveryClaimBatch,
    verify_recovery_claim_batch,
)


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CarrierActionProposalBatchState(str, Enum):
    NO_CLAIMS = "NO_CLAIMS"
    PROPOSALS_READY = "PROPOSALS_READY"


@dataclass(frozen=True)
class CarrierActionProposal:
    buyer_id: str
    business_unit: str
    recovery_claim_batch_hash: str
    truth_hash: str
    buyer_review_batch_hash: str
    target_carrier_id: str
    target_customer_id: str
    currency: str
    claim_ids: tuple[str, ...]
    finding_ids: tuple[str, ...]
    finding_proof_hashes: tuple[str, ...]
    finding_review_hashes: tuple[str, ...]
    total_claim_cents: int
    fee_disqualified_claim_count: int
    fee_disqualified_cents: int
    proposal_hash: str


@dataclass(frozen=True)
class CarrierActionProposalBatch:
    buyer_id: str
    business_unit: str
    recovery_claim_batch_hash: str
    state: str
    proposal_count: int
    claim_count: int
    total_claim_cents: int
    proposals: tuple[CarrierActionProposal, ...]
    batch_hash: str


@dataclass(frozen=True)
class CarrierActionApprovalInput:
    proposal_hash: str
    authorization_id: str
    action_type: ActionType
    recipient_reference_hash: str
    action_payload_hash: str
    approver_role: str
    issued_on: str
    expires_on: str
    authorized_cents: int | None = None

    def __post_init__(self):
        if not isinstance(self.proposal_hash, str) or not SHA256_RE.fullmatch(self.proposal_hash):
            raise ValueError("proposal_hash must be lowercase SHA-256")
        if not isinstance(self.authorization_id, str) or not self.authorization_id.strip():
            raise ValueError("authorization_id is required")
        if not isinstance(self.action_type, ActionType):
            raise ValueError("action_type must be an ActionType")
        for name, value in (
            ("recipient_reference_hash", self.recipient_reference_hash),
            ("action_payload_hash", self.action_payload_hash),
        ):
            if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
                raise ValueError(name + " must be lowercase SHA-256")
        if not isinstance(self.approver_role, str) or not self.approver_role.strip():
            raise ValueError("approver_role is required")
        if not isinstance(self.issued_on, str) or not self.issued_on.strip():
            raise ValueError("issued_on is required")
        if not isinstance(self.expires_on, str) or not self.expires_on.strip():
            raise ValueError("expires_on is required")
        if self.authorized_cents is not None and (
            type(self.authorized_cents) is not int or self.authorized_cents <= 0
        ):
            raise ValueError("authorized_cents must be a positive integer or None")


def _verify_buyer_review_link(
    recovery_claims: RecoveryClaimBatch,
    buyer_review: BuyerReviewBatch,
    truth: TruthManifest,
) -> None:
    if recovery_claims.truth_hash != truth.truth_hash:
        raise ValueError("recovery claim batch truth hash mismatch")
    if recovery_claims.buyer_review_batch_hash != buyer_review.batch_hash:
        raise ValueError("recovery claim batch buyer review hash mismatch")
    if buyer_review.truth_hash != truth.truth_hash:
        raise ValueError("buyer review truth hash mismatch")
    if (recovery_claims.buyer_id, recovery_claims.business_unit) != (
        truth.buyer_id, truth.business_unit,
    ):
        raise ValueError("recovery claim batch scope mismatch")
    if (buyer_review.buyer_id, buyer_review.business_unit) != (
        truth.buyer_id, truth.business_unit,
    ):
        raise ValueError("buyer review scope mismatch")

    review_index = {
        record.finding_id: record
        for record in buyer_review.records
        if record.disposition == ReviewDisposition.CONFIRMED.value
    }
    if len(review_index) != buyer_review.confirmed_count:
        raise ValueError("buyer review confirmed-count mismatch")
    for record in recovery_claims.records:
        review = review_index.get(record.finding_id)
        if review is None:
            raise ValueError("recovery claim lacks CONFIRMED buyer review")
        if review.review_hash != record.review_hash:
            raise ValueError("recovery claim buyer review proof mismatch")
        if review.finding_proof_hash != record.finding_proof_hash:
            raise ValueError("recovery claim finding proof mismatch with buyer review")


def build_carrier_action_proposal_batch(
    *,
    recovery_claims: RecoveryClaimBatch,
) -> CarrierActionProposalBatch:
    verify_recovery_claim_batch(recovery_claims)

    groups: dict[tuple[str, str, str], list] = {}
    for record in recovery_claims.records:
        key = (record.payer_id, record.payee_id, record.currency)
        groups.setdefault(key, []).append(record)

    proposals: list[CarrierActionProposal] = []
    for carrier_id, customer_id, currency in sorted(groups):
        records = sorted(groups[(carrier_id, customer_id, currency)], key=lambda r: r.claim_id)
        claim_ids = tuple(record.claim_id for record in records)
        finding_ids = tuple(record.finding_id for record in records)
        finding_proof_hashes = tuple(record.finding_proof_hash for record in records)
        review_hashes = tuple(record.review_hash for record in records)
        total = sum(record.amount_cents for record in records)
        fee_disqualified_count = sum(record.fee_disqualified for record in records)
        fee_disqualified_cents = sum(
            record.amount_cents for record in records if record.fee_disqualified
        )
        body = {
            "schema": 1,
            "buyer_id": recovery_claims.buyer_id,
            "business_unit": recovery_claims.business_unit,
            "recovery_claim_batch_hash": recovery_claims.batch_hash,
            "truth_hash": recovery_claims.truth_hash,
            "buyer_review_batch_hash": recovery_claims.buyer_review_batch_hash,
            "target_carrier_id": carrier_id,
            "target_customer_id": customer_id,
            "currency": currency,
            "claim_ids": claim_ids,
            "finding_ids": finding_ids,
            "finding_proof_hashes": finding_proof_hashes,
            "finding_review_hashes": review_hashes,
            "total_claim_cents": total,
            "fee_disqualified_claim_count": fee_disqualified_count,
            "fee_disqualified_cents": fee_disqualified_cents,
        }
        proposals.append(CarrierActionProposal(
            buyer_id=recovery_claims.buyer_id,
            business_unit=recovery_claims.business_unit,
            recovery_claim_batch_hash=recovery_claims.batch_hash,
            truth_hash=recovery_claims.truth_hash,
            buyer_review_batch_hash=recovery_claims.buyer_review_batch_hash,
            target_carrier_id=carrier_id,
            target_customer_id=customer_id,
            currency=currency,
            claim_ids=claim_ids,
            finding_ids=finding_ids,
            finding_proof_hashes=finding_proof_hashes,
            finding_review_hashes=review_hashes,
            total_claim_cents=total,
            fee_disqualified_claim_count=fee_disqualified_count,
            fee_disqualified_cents=fee_disqualified_cents,
            proposal_hash=canonical_hash(body),
        ))

    proposals_tuple = tuple(proposals)
    state = (
        CarrierActionProposalBatchState.PROPOSALS_READY.value
        if proposals_tuple
        else CarrierActionProposalBatchState.NO_CLAIMS.value
    )
    body = {
        "schema": 1,
        "buyer_id": recovery_claims.buyer_id,
        "business_unit": recovery_claims.business_unit,
        "recovery_claim_batch_hash": recovery_claims.batch_hash,
        "state": state,
        "proposal_count": len(proposals_tuple),
        "claim_count": recovery_claims.claim_count,
        "total_claim_cents": sum(record.amount_cents for record in recovery_claims.records),
        "proposals": [asdict(proposal) for proposal in proposals_tuple],
    }
    return CarrierActionProposalBatch(
        buyer_id=recovery_claims.buyer_id,
        business_unit=recovery_claims.business_unit,
        recovery_claim_batch_hash=recovery_claims.batch_hash,
        state=state,
        proposal_count=len(proposals_tuple),
        claim_count=recovery_claims.claim_count,
        total_claim_cents=sum(record.amount_cents for record in recovery_claims.records),
        proposals=proposals_tuple,
        batch_hash=canonical_hash(body),
    )


def authorize_carrier_action_proposal(
    *,
    resolution: EngagementResolution,
    operative_charter: dict,
    truth: TruthManifest,
    buyer_review: BuyerReviewBatch,
    recovery_claims: RecoveryClaimBatch,
    proposal: CarrierActionProposal,
    approval: CarrierActionApprovalInput,
) -> ExternalActionAuthorization:
    verify_recovery_claim_batch(recovery_claims)
    _verify_buyer_review_link(recovery_claims, buyer_review, truth)

    canonical_batch = build_carrier_action_proposal_batch(recovery_claims=recovery_claims)
    proposal_index = {item.proposal_hash: item for item in canonical_batch.proposals}
    canonical = proposal_index.get(proposal.proposal_hash)
    if canonical is None or canonical != proposal:
        raise ValueError("carrier action proposal does not match recovery claim batch")
    if approval.proposal_hash != proposal.proposal_hash:
        raise ValueError("approval proposal_hash mismatch")

    authorized_cents = (
        proposal.total_claim_cents
        if approval.authorized_cents is None
        else approval.authorized_cents
    )
    if authorized_cents > proposal.total_claim_cents:
        raise ValueError("authorized_cents cannot exceed proposal total")

    return issue_authorization(
        resolution=resolution,
        operative_charter=operative_charter,
        truth=truth,
        reviews=buyer_review.finding_reviews,
        authorization_id=approval.authorization_id,
        action_type=approval.action_type,
        target_carrier_id=proposal.target_carrier_id,
        target_customer_id=proposal.target_customer_id,
        recipient_reference_hash=approval.recipient_reference_hash,
        action_payload_hash=approval.action_payload_hash,
        finding_ids=proposal.finding_ids,
        currency=proposal.currency,
        authorized_cents=authorized_cents,
        approver_role=approval.approver_role,
        issued_on=approval.issued_on,
        expires_on=approval.expires_on,
    )


def render_carrier_action_proposals_markdown(batch: CarrierActionProposalBatch) -> str:
    lines = [
        "# Freight Recovery — Carrier Action Proposals",
        "",
        f"- Buyer: **{batch.buyer_id}**",
        f"- Business unit: **{batch.business_unit}**",
        f"- State: **{batch.state}**",
        f"- Claims: **{batch.claim_count}**",
        f"- Proposals: **{batch.proposal_count}**",
        "- Total claim amount: **$" + format(batch.total_claim_cents / 100, ",.2f") + "**",
        f"- Proposal batch hash: `{batch.batch_hash}`",
        "",
        "Proposals are grouped by carrier, customer/payee and currency.",
        "They do not authorize or execute carrier contact. A separate buyer approval must bind the action type, recipient/routing reference, exact payload, amount and validity window.",
        "",
    ]
    for proposal in batch.proposals:
        lines.extend([
            f"## {proposal.target_carrier_id} / {proposal.target_customer_id} / {proposal.currency}",
            "",
            f"- Claims: **{len(proposal.claim_ids)}**",
            "- Total: **" + proposal.currency + " " + format(proposal.total_claim_cents / 100, ",.2f") + "**",
            "- Fee-disqualified amount: **" + proposal.currency + " " + format(proposal.fee_disqualified_cents / 100, ",.2f") + "**",
            "- Finding IDs: " + ", ".join(proposal.finding_ids),
            f"- Proposal hash: `{proposal.proposal_hash}`",
            "",
        ])
    return "\n".join(lines)
