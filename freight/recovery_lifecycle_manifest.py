"""End-to-end proof manifest for one Freight Recovery case lifecycle.

The manifest binds the pre-review audit through buyer decisions, recovery
claims, carrier action proof, ordered settlement-state transitions, and the
current persistent report. It validates cross-links rather than merely
collecting hashes.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Iterable

from freight.audit_run_manifest import AuditRunManifest
from freight.buyer_review_workflow import BuyerReviewBatch, verify_buyer_review_batch
from freight.carrier_action_execution import (
    CarrierActionDeliveryReceipt,
    CarrierActionExecutionIntent,
    CarrierActionExecutionReceipt,
    verify_carrier_action_delivery_receipt,
    verify_carrier_action_execution_intent,
    verify_carrier_action_execution_receipt,
)
from freight.carrier_action_payload import (
    CarrierActionPayload,
    verify_carrier_action_payload,
)
from freight.carrier_action_workflow import (
    CarrierActionProposal,
    CarrierActionProposalBatch,
    build_carrier_action_proposal_batch,
)
from freight.contracts import IncumbentOutput, TruthManifest, canonical_hash
from freight.counter_review_workflow import CounterReviewReceipt
from freight.external_action_authorization import ExternalActionAuthorization
from freight.recovery_claim_workflow import (
    RecoveryClaimBatch,
    RecoveryClaimPersistenceReceipt,
    verify_recovery_claim_batch,
)
from freight.remediation_plan import RemediationPlan, build_remediation_plan
from freight.review_packet import ReviewPacket
from freight.review_routing import ReviewRouting, route_review_packet
from freight.settlement_lifecycle_workflow import (
    SettlementLifecycleResult,
    verify_settlement_lifecycle_result,
)
from freight.settlement_report import PersistentPilotReport
from freight.settlement_review_workflow import SettlementReviewReceipt


LIFECYCLE = "LIFECYCLE"
SETTLEMENT_REVIEW = "SETTLEMENT_REVIEW"
COUNTER_REVIEW = "COUNTER_REVIEW"


@dataclass(frozen=True)
class CarrierActionLifecycleInput:
    proposal: CarrierActionProposal
    payload: CarrierActionPayload
    authorization: ExternalActionAuthorization
    intent: CarrierActionExecutionIntent
    execution_receipt: CarrierActionExecutionReceipt
    delivery_receipt: CarrierActionDeliveryReceipt | None = None


@dataclass(frozen=True)
class CarrierActionLifecycleProof:
    execution_key: str
    proposal_hash: str
    payload_hash: str
    authorization_hash: str
    intent_hash: str
    execution_receipt_hash: str
    delivery_receipt_hash: str | None
    action_submitted: bool
    delivery_confirmed: bool
    requested_cents: int
    finding_ids: tuple[str, ...]
    proof_hash: str


@dataclass(frozen=True)
class SettlementStateTransition:
    transition_type: str
    proof_hash: str
    stable_state_hash: str | None
    store_snapshot_before_hash: str
    store_snapshot_after_hash: str
    transition_hash: str


@dataclass(frozen=True)
class RecoveryLifecycleManifest:
    buyer_id: str
    business_unit: str
    audit_run_hash: str
    truth_hash: str
    population_hash: str
    incumbent_output_hash: str
    review_packet_hash: str
    review_routing_hash: str
    remediation_plan_hash: str
    buyer_review_batch_hash: str
    recovery_claim_batch_hash: str
    recovery_claim_persistence_receipt_hash: str
    carrier_proposal_batch_hash: str
    carrier_action_proofs: tuple[CarrierActionLifecycleProof, ...]
    carrier_proposal_count: int
    carrier_action_count: int
    submitted_action_count: int
    delivered_action_count: int
    unsubmitted_proposal_hashes: tuple[str, ...]
    settlement_transitions: tuple[SettlementStateTransition, ...]
    pending_settlement_review_case_hashes: tuple[str, ...]
    audit_remediation_case_count: int
    settlement_snapshot_hash: str
    report_hash: str
    realized_cents: int
    fee_eligible_realized_cents: int
    manifest_hash: str


def _verify_audit_run(audit_run: AuditRunManifest) -> None:
    fields = asdict(audit_run)
    digest = fields.pop("run_hash")
    if canonical_hash({"schema": 1, **fields}) != digest:
        raise ValueError("audit run hash mismatch")


def _verify_truth(truth: TruthManifest) -> None:
    body = {
        "schema": 3,
        "buyer_id": truth.buyer_id,
        "business_unit": truth.business_unit,
        "population_hash": truth.population_hash,
        "authorities": [asdict(item) for item in truth.authorities],
        "findings": [asdict(item) for item in truth.findings],
    }
    if canonical_hash(body) != truth.truth_hash:
        raise ValueError("truth hash mismatch")


def _verify_incumbent(incumbent: IncumbentOutput) -> None:
    body = {"schema": 2, **asdict(incumbent)}
    digest = body.pop("output_hash")
    if canonical_hash(body) != digest:
        raise ValueError("incumbent output hash mismatch")


def _verify_persistence(
    receipt: RecoveryClaimPersistenceReceipt,
    claims: RecoveryClaimBatch,
) -> None:
    if (receipt.buyer_id, receipt.business_unit) != (
        claims.buyer_id,
        claims.business_unit,
    ):
        raise ValueError("claim persistence scope mismatch")
    if receipt.claim_batch_hash != claims.batch_hash:
        raise ValueError("claim persistence batch hash mismatch")
    claim_ids = tuple(item.claim_id for item in claims.claims)
    if receipt.claim_ids != claim_ids:
        raise ValueError("claim persistence claim IDs mismatch")
    if receipt.attempted_claim_count != claims.claim_count:
        raise ValueError("claim persistence attempted count mismatch")
    if (
        receipt.created_claim_count + receipt.already_present_count
        != receipt.attempted_claim_count
    ):
        raise ValueError("claim persistence count arithmetic mismatch")
    body = {
        "schema": 1,
        "buyer_id": receipt.buyer_id,
        "business_unit": receipt.business_unit,
        "claim_batch_hash": receipt.claim_batch_hash,
        "attempted_claim_count": receipt.attempted_claim_count,
        "created_claim_count": receipt.created_claim_count,
        "already_present_count": receipt.already_present_count,
        "claim_ids": receipt.claim_ids,
    }
    if canonical_hash(body) != receipt.receipt_hash:
        raise ValueError("claim persistence receipt hash mismatch")


def _verify_authorization(auth: ExternalActionAuthorization) -> None:
    body = asdict(auth)
    digest = body.pop("authorization_hash")
    if canonical_hash(body) != digest:
        raise ValueError("carrier authorization hash mismatch")
    for field in (
        "money_movement_authorized",
        "settlement_acceptance_authorized",
        "account_change_authorized",
        "credential_use_authorized",
        "general_contact_authorized",
        "automatic_execution_authorized",
    ):
        if getattr(auth, field) is not False:
            raise ValueError(field + " must remain false")


def _action_proof(
    item: CarrierActionLifecycleInput,
    *,
    proposal_index: dict[str, CarrierActionProposal],
    recovery_claims: RecoveryClaimBatch,
) -> CarrierActionLifecycleProof:
    proposal = proposal_index.get(item.proposal.proposal_hash)
    if proposal is None or proposal != item.proposal:
        raise ValueError("carrier action references non-canonical proposal")

    verify_carrier_action_payload(
        item.payload,
        proposal=item.proposal,
        recovery_claims=recovery_claims,
    )
    _verify_authorization(item.authorization)
    if (item.authorization.buyer_id, item.authorization.business_unit) != (
        recovery_claims.buyer_id,
        recovery_claims.business_unit,
    ):
        raise ValueError("carrier authorization scope mismatch")
    if item.authorization.action_payload_hash != item.payload.payload_hash:
        raise ValueError("carrier authorization payload hash mismatch")
    if item.authorization.target_carrier_id != item.proposal.target_carrier_id:
        raise ValueError("carrier authorization carrier mismatch")
    if item.authorization.target_customer_id != item.proposal.target_customer_id:
        raise ValueError("carrier authorization customer mismatch")
    if item.authorization.currency != item.proposal.currency:
        raise ValueError("carrier authorization currency mismatch")
    if item.authorization.finding_ids != tuple(sorted(item.proposal.finding_ids)):
        raise ValueError("carrier authorization finding set mismatch")
    if item.authorization.authorized_cents != item.payload.requested_cents:
        raise ValueError("carrier authorization amount mismatch")

    verify_carrier_action_execution_intent(
        item.intent,
        authorization=item.authorization,
        proposal=item.proposal,
        payload=item.payload,
        recovery_claims=recovery_claims,
    )
    verify_carrier_action_execution_receipt(item.execution_receipt)
    receipt = item.execution_receipt
    if (
        receipt.execution_key != item.intent.execution_key
        or receipt.intent_hash != item.intent.intent_hash
        or receipt.authorization_hash != item.authorization.authorization_hash
        or receipt.proposal_hash != item.proposal.proposal_hash
        or receipt.payload_hash != item.payload.payload_hash
    ):
        raise ValueError("carrier execution receipt proof links mismatch")

    delivery_hash = None
    delivery_confirmed = receipt.delivery_confirmed
    if item.delivery_receipt is not None:
        verify_carrier_action_delivery_receipt(item.delivery_receipt)
        delivery = item.delivery_receipt
        if (
            delivery.execution_key != receipt.execution_key
            or delivery.submitted_receipt_hash != receipt.receipt_hash
            or delivery.authorization_hash != receipt.authorization_hash
            or delivery.proposal_hash != receipt.proposal_hash
            or delivery.payload_hash != receipt.payload_hash
        ):
            raise ValueError("carrier delivery receipt proof links mismatch")
        delivery_hash = delivery.delivery_receipt_hash
        delivery_confirmed = True

    body = {
        "schema": 1,
        "execution_key": receipt.execution_key,
        "proposal_hash": item.proposal.proposal_hash,
        "payload_hash": item.payload.payload_hash,
        "authorization_hash": item.authorization.authorization_hash,
        "intent_hash": item.intent.intent_hash,
        "execution_receipt_hash": receipt.receipt_hash,
        "delivery_receipt_hash": delivery_hash,
        "action_submitted": receipt.action_submitted,
        "delivery_confirmed": delivery_confirmed,
        "requested_cents": receipt.requested_cents,
        "finding_ids": receipt.finding_ids,
    }
    return CarrierActionLifecycleProof(
        execution_key=receipt.execution_key,
        proposal_hash=item.proposal.proposal_hash,
        payload_hash=item.payload.payload_hash,
        authorization_hash=item.authorization.authorization_hash,
        intent_hash=item.intent.intent_hash,
        execution_receipt_hash=receipt.receipt_hash,
        delivery_receipt_hash=delivery_hash,
        action_submitted=receipt.action_submitted,
        delivery_confirmed=delivery_confirmed,
        requested_cents=receipt.requested_cents,
        finding_ids=receipt.finding_ids,
        proof_hash=canonical_hash(body),
    )


def _verify_settlement_review_receipt(receipt: SettlementReviewReceipt) -> None:
    review_body = {
        "schema": 1,
        "case_hash": receipt.case_hash,
        "event_id": receipt.event_id,
        "claim_id": receipt.claim_id,
        "amount_cents": receipt.amount_cents,
        "reviewer_role": receipt.reviewer_role,
        "reviewed_at": receipt.reviewed_at,
        "rationale": receipt.rationale,
    }
    if canonical_hash(review_body) != receipt.review_hash:
        raise ValueError("settlement review hash mismatch")
    body = {
        "schema": 1,
        "buyer_id": receipt.buyer_id,
        "business_unit": receipt.business_unit,
        "case_hash": receipt.case_hash,
        "event_id": receipt.event_id,
        "claim_id": receipt.claim_id,
        "amount_cents": receipt.amount_cents,
        "reviewer_role": receipt.reviewer_role,
        "reviewed_at": receipt.reviewed_at,
        "rationale": receipt.rationale,
        "review_hash": receipt.review_hash,
        "allocation_id": receipt.allocation_id,
        "allocation_status": receipt.allocation_status,
        "store_snapshot_before_hash": receipt.store_snapshot_before_hash,
        "store_snapshot_after_hash": receipt.store_snapshot_after_hash,
    }
    if canonical_hash(body) != receipt.receipt_hash:
        raise ValueError("settlement review receipt hash mismatch")


def _verify_counter_review_receipt(receipt: CounterReviewReceipt) -> None:
    review_body = {
        "schema": 1,
        "case_hash": receipt.case_hash,
        "counter_id": receipt.counter_id,
        "allocation_id": receipt.allocation_id,
        "amount_cents": receipt.amount_cents,
        "reviewer_role": receipt.reviewer_role,
        "reviewed_at": receipt.reviewed_at,
        "rationale": receipt.rationale,
    }
    if canonical_hash(review_body) != receipt.review_hash:
        raise ValueError("counter review hash mismatch")
    body = {
        "schema": 1,
        "buyer_id": receipt.buyer_id,
        "business_unit": receipt.business_unit,
        "case_hash": receipt.case_hash,
        "counter_id": receipt.counter_id,
        "allocation_id": receipt.allocation_id,
        "amount_cents": receipt.amount_cents,
        "reviewer_role": receipt.reviewer_role,
        "reviewed_at": receipt.reviewed_at,
        "rationale": receipt.rationale,
        "review_hash": receipt.review_hash,
        "reversal_id": receipt.reversal_id,
        "reversal_status": receipt.reversal_status,
        "store_snapshot_before_hash": receipt.store_snapshot_before_hash,
        "store_snapshot_after_hash": receipt.store_snapshot_after_hash,
    }
    if canonical_hash(body) != receipt.receipt_hash:
        raise ValueError("counter review receipt hash mismatch")


def _transition(value: object) -> SettlementStateTransition:
    if isinstance(value, SettlementLifecycleResult):
        verify_settlement_lifecycle_result(value)
        transition_type = LIFECYCLE
        proof_hash = value.execution_hash
        stable_state_hash = value.state_hash
        before = value.store_snapshot_before_hash
        after = value.store_snapshot_after_hash
    elif isinstance(value, SettlementReviewReceipt):
        _verify_settlement_review_receipt(value)
        transition_type = SETTLEMENT_REVIEW
        proof_hash = value.receipt_hash
        stable_state_hash = None
        before = value.store_snapshot_before_hash
        after = value.store_snapshot_after_hash
    elif isinstance(value, CounterReviewReceipt):
        _verify_counter_review_receipt(value)
        transition_type = COUNTER_REVIEW
        proof_hash = value.receipt_hash
        stable_state_hash = None
        before = value.store_snapshot_before_hash
        after = value.store_snapshot_after_hash
    else:
        raise ValueError("unsupported settlement transition proof type")

    body = {
        "schema": 1,
        "transition_type": transition_type,
        "proof_hash": proof_hash,
        "stable_state_hash": stable_state_hash,
        "store_snapshot_before_hash": before,
        "store_snapshot_after_hash": after,
    }
    return SettlementStateTransition(
        transition_type=transition_type,
        proof_hash=proof_hash,
        stable_state_hash=stable_state_hash,
        store_snapshot_before_hash=before,
        store_snapshot_after_hash=after,
        transition_hash=canonical_hash(body),
    )


def _verify_report(
    report: PersistentPilotReport,
    *,
    truth: TruthManifest,
    incumbent: IncumbentOutput,
    buyer_review: BuyerReviewBatch,
    recovery_claims: RecoveryClaimBatch,
) -> None:
    if report.truth_hash != truth.truth_hash:
        raise ValueError("report truth hash mismatch")
    if report.population_hash != truth.population_hash:
        raise ValueError("report population hash mismatch")
    if report.incumbent_output_hash != incumbent.output_hash:
        raise ValueError("report incumbent output hash mismatch")
    if recovery_claims.incumbent_output_hash != incumbent.output_hash:
        raise ValueError("recovery claims incumbent output mismatch")

    bindings_hash = canonical_hash([
        asdict(item)
        for item in sorted(recovery_claims.bindings, key=lambda item: item.claim_id)
    ])
    if report.bindings_hash != bindings_hash:
        raise ValueError("report claim-binding hash mismatch")
    reviews_hash = canonical_hash([
        asdict(item)
        for item in sorted(
            buyer_review.finding_reviews,
            key=lambda item: item.finding_id,
        )
    ])
    if report.reviews_hash != reviews_hash:
        raise ValueError("report buyer-review hash mismatch")

    snapshot = json.loads(report.settlement_snapshot_json)
    if canonical_hash(snapshot) != report.settlement_snapshot_hash:
        raise ValueError("report settlement snapshot hash mismatch")
    if (snapshot.get("buyer_id"), snapshot.get("business_unit")) != (
        truth.buyer_id,
        truth.business_unit,
    ):
        raise ValueError("report settlement snapshot scope mismatch")

    body = {
        "schema": 1,
        "metrics": asdict(report.metrics),
        "truth_hash": report.truth_hash,
        "population_hash": report.population_hash,
        "incumbent_output_hash": report.incumbent_output_hash,
        "settlement_snapshot_hash": report.settlement_snapshot_hash,
        "bindings_hash": report.bindings_hash,
        "reviews_hash": report.reviews_hash,
        "certificates": [asdict(item) for item in report.certificates],
    }
    if canonical_hash(body) != report.report_hash:
        raise ValueError("persistent report hash mismatch")


def build_recovery_lifecycle_manifest(
    *,
    audit_run: AuditRunManifest,
    truth: TruthManifest,
    incumbent: IncumbentOutput,
    review_packet: ReviewPacket,
    review_routing: ReviewRouting,
    remediation_plan: RemediationPlan,
    buyer_review: BuyerReviewBatch,
    recovery_claims: RecoveryClaimBatch,
    claim_persistence: RecoveryClaimPersistenceReceipt,
    proposal_batch: CarrierActionProposalBatch,
    carrier_actions: Iterable[CarrierActionLifecycleInput] = (),
    settlement_transitions: Iterable[object] = (),
    report: PersistentPilotReport,
) -> RecoveryLifecycleManifest:
    _verify_audit_run(audit_run)
    _verify_truth(truth)
    _verify_incumbent(incumbent)

    scope = (audit_run.buyer_id, audit_run.business_unit)
    if scope != (truth.buyer_id, truth.business_unit):
        raise ValueError("audit/truth scope mismatch")
    if audit_run.truth_hash != truth.truth_hash:
        raise ValueError("audit/truth hash mismatch")
    if audit_run.population_hash != truth.population_hash:
        raise ValueError("audit/truth population mismatch")
    if audit_run.review_packet_hash != review_packet.packet_hash:
        raise ValueError("audit review-packet hash mismatch")
    if (incumbent.buyer_id, incumbent.business_unit) != scope:
        raise ValueError("incumbent scope mismatch")
    if incumbent.truth_hash != truth.truth_hash:
        raise ValueError("incumbent truth hash mismatch")
    if incumbent.population_hash != truth.population_hash:
        raise ValueError("incumbent population hash mismatch")

    canonical_routing = route_review_packet(review_packet)
    if review_routing != canonical_routing:
        raise ValueError("review routing does not match review packet")
    canonical_remediation = build_remediation_plan(review_packet, review_routing)
    if remediation_plan != canonical_remediation:
        raise ValueError("remediation plan does not match review proofs")

    verify_buyer_review_batch(
        batch=buyer_review,
        review_packet=review_packet,
        review_routing=review_routing,
        truth=truth,
    )
    verify_recovery_claim_batch(recovery_claims)
    if recovery_claims.truth_hash != truth.truth_hash:
        raise ValueError("recovery claim truth hash mismatch")
    if recovery_claims.buyer_review_batch_hash != buyer_review.batch_hash:
        raise ValueError("recovery claim buyer-review hash mismatch")
    if recovery_claims.incumbent_output_hash != incumbent.output_hash:
        raise ValueError("recovery claim incumbent hash mismatch")
    _verify_persistence(claim_persistence, recovery_claims)

    canonical_proposals = build_carrier_action_proposal_batch(
        recovery_claims=recovery_claims
    )
    if proposal_batch != canonical_proposals:
        raise ValueError("carrier proposal batch does not match recovery claims")
    proposal_index = {
        item.proposal_hash: item for item in proposal_batch.proposals
    }

    action_proofs: list[CarrierActionLifecycleProof] = []
    seen_execution_keys: set[str] = set()
    for item in tuple(carrier_actions):
        if not isinstance(item, CarrierActionLifecycleInput):
            raise ValueError("carrier_actions must contain CarrierActionLifecycleInput")
        proof = _action_proof(
            item,
            proposal_index=proposal_index,
            recovery_claims=recovery_claims,
        )
        if proof.execution_key in seen_execution_keys:
            raise ValueError("duplicate carrier action execution key")
        seen_execution_keys.add(proof.execution_key)
        action_proofs.append(proof)
    action_proofs_tuple = tuple(sorted(
        action_proofs,
        key=lambda item: item.execution_key,
    ))

    submitted_proposals = {
        item.proposal_hash
        for item in action_proofs_tuple
        if item.action_submitted
    }
    unsubmitted = tuple(sorted(
        set(proposal_index) - submitted_proposals
    ))

    transition_inputs = tuple(settlement_transitions)
    transitions = tuple(_transition(item) for item in transition_inputs)
    for previous, current in zip(transitions, transitions[1:]):
        if previous.store_snapshot_after_hash != current.store_snapshot_before_hash:
            raise ValueError("settlement transition chain is discontinuous")

    lifecycle_review_cases: list[str] = []
    for item in transition_inputs:
        if isinstance(item, SettlementLifecycleResult):
            lifecycle_review_cases.extend(
                case.case_hash for case in item.settlement_review_cases
            )
            lifecycle_review_cases.extend(
                case.case_hash for case in item.counter_review_cases
            )
    resolved_review_cases = {
        item.case_hash
        for item in transition_inputs
        if isinstance(item, (SettlementReviewReceipt, CounterReviewReceipt))
    }
    pending_review_cases = tuple(
        case_hash
        for case_hash in lifecycle_review_cases
        if case_hash not in resolved_review_cases
    )

    _verify_report(
        report,
        truth=truth,
        incumbent=incumbent,
        buyer_review=buyer_review,
        recovery_claims=recovery_claims,
    )
    if transitions:
        if transitions[-1].store_snapshot_after_hash != report.settlement_snapshot_hash:
            raise ValueError(
                "final settlement transition does not match persistent report snapshot"
            )
    elif report.metrics.realized_cents or report.metrics.fee_eligible_realized_cents:
        raise ValueError("realized report requires settlement transition proof")

    if (report.metrics.buyer_id, report.metrics.business_unit) != scope:
        raise ValueError("report scope mismatch")

    body = {
        "schema": 1,
        "buyer_id": scope[0],
        "business_unit": scope[1],
        "audit_run_hash": audit_run.run_hash,
        "truth_hash": truth.truth_hash,
        "population_hash": truth.population_hash,
        "incumbent_output_hash": incumbent.output_hash,
        "review_packet_hash": review_packet.packet_hash,
        "review_routing_hash": review_routing.routing_hash,
        "remediation_plan_hash": remediation_plan.plan_hash,
        "buyer_review_batch_hash": buyer_review.batch_hash,
        "recovery_claim_batch_hash": recovery_claims.batch_hash,
        "recovery_claim_persistence_receipt_hash": claim_persistence.receipt_hash,
        "carrier_proposal_batch_hash": proposal_batch.batch_hash,
        "carrier_action_proofs": [asdict(item) for item in action_proofs_tuple],
        "carrier_proposal_count": proposal_batch.proposal_count,
        "carrier_action_count": len(action_proofs_tuple),
        "submitted_action_count": sum(item.action_submitted for item in action_proofs_tuple),
        "delivered_action_count": sum(item.delivery_confirmed for item in action_proofs_tuple),
        "unsubmitted_proposal_hashes": unsubmitted,
        "settlement_transitions": [asdict(item) for item in transitions],
        "pending_settlement_review_case_hashes": pending_review_cases,
        "audit_remediation_case_count": remediation_plan.remediation_case_count,
        "settlement_snapshot_hash": report.settlement_snapshot_hash,
        "report_hash": report.report_hash,
        "realized_cents": report.metrics.realized_cents,
        "fee_eligible_realized_cents": report.metrics.fee_eligible_realized_cents,
    }
    return RecoveryLifecycleManifest(
        buyer_id=scope[0],
        business_unit=scope[1],
        audit_run_hash=audit_run.run_hash,
        truth_hash=truth.truth_hash,
        population_hash=truth.population_hash,
        incumbent_output_hash=incumbent.output_hash,
        review_packet_hash=review_packet.packet_hash,
        review_routing_hash=review_routing.routing_hash,
        remediation_plan_hash=remediation_plan.plan_hash,
        buyer_review_batch_hash=buyer_review.batch_hash,
        recovery_claim_batch_hash=recovery_claims.batch_hash,
        recovery_claim_persistence_receipt_hash=claim_persistence.receipt_hash,
        carrier_proposal_batch_hash=proposal_batch.batch_hash,
        carrier_action_proofs=action_proofs_tuple,
        carrier_proposal_count=proposal_batch.proposal_count,
        carrier_action_count=len(action_proofs_tuple),
        submitted_action_count=sum(item.action_submitted for item in action_proofs_tuple),
        delivered_action_count=sum(item.delivery_confirmed for item in action_proofs_tuple),
        unsubmitted_proposal_hashes=unsubmitted,
        settlement_transitions=transitions,
        pending_settlement_review_case_hashes=pending_review_cases,
        audit_remediation_case_count=remediation_plan.remediation_case_count,
        settlement_snapshot_hash=report.settlement_snapshot_hash,
        report_hash=report.report_hash,
        realized_cents=report.metrics.realized_cents,
        fee_eligible_realized_cents=report.metrics.fee_eligible_realized_cents,
        manifest_hash=canonical_hash(body),
    )


def verify_recovery_lifecycle_manifest(
    manifest: RecoveryLifecycleManifest,
    **kwargs,
) -> None:
    expected = build_recovery_lifecycle_manifest(**kwargs)
    if manifest != expected:
        raise ValueError("recovery lifecycle manifest does not match current proof chain")
