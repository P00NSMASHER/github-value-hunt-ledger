"""End-to-end synthetic rehearsal of the Freight Recovery commercial path.

This proves workflow consistency only. It must never be recorded as realized
customer value or revenue.
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from freight.audit_result_bundle import build_audit_result_bundle, verify_audit_result_bundle
from freight.audit_workflow import RuleCSVInput, render_workflow_summary, run_audit_workflow
from freight.buyer_review_workflow import (
    BuyerReviewDecisionInput,
    build_buyer_review_batch,
)
from freight.carrier_action_execution import (
    CarrierActionExecutionEvidence,
    ExecutionChannel,
    ExecutionOutcome,
    build_carrier_action_execution_intent,
    record_carrier_action_execution,
)
from freight.carrier_action_payload import (
    authorize_carrier_action_payload,
    build_carrier_action_payload,
)
from freight.carrier_action_workflow import (
    CarrierActionApprovalInput,
    build_carrier_action_proposal_batch,
)
from freight.contracts import (
    open_incumbent_output,
    seal_incumbent_submission,
)
from freight.engagement_state import resolve_engagement
from freight.external_action_authorization import ActionType, assert_action_allowed
from freight.deal_economics import DealProfile, qualify_deal
from freight.pilot_activation_packet import build_packet
from freight.pilot_charter import build_charter, from_dict as charter_from_dict
from freight.pilot_reporting import ReviewDisposition
from freight.recovery_claim_workflow import (
    build_recovery_claim_batch,
    persist_recovery_claim_batch,
)
from freight.review_packet import render_review_packet_markdown
from freight.readiness import PilotReadinessInput, assess_readiness
from freight.settlement_lifecycle_workflow import process_settlement_evidence
from freight.settlement_review_workflow import (
    SettlementReviewDecisionInput,
    apply_settlement_review_decision,
)
from freight.settlement_report import (
    assert_report_current,
    build_persistent_pilot_report,
    render_persistent_markdown,
)
from freight.settlement_store import (
    ALLOCATED,
    REVERSED,
    SettlementStore,
)


BUYER = "buyer-synthetic"
BU = "bu-synthetic"


def run_rehearsal() -> dict:
    readiness_input = PilotReadinessInput(
        authorization_documented=True,
        read_only_access=True,
        population_reproducible=True,
        incumbent_output_sealable=True,
        settlement_observable=True,
        material_authority_reconstructable=True,
        customer_identity_stable=True,
        carrier_identity_stable=True,
        retention_defined=True,
        deletion_defined=True,
        invoice_source_coverage=1.0,
        authority_source_coverage=0.96,
        shipment_evidence_coverage=0.92,
    )
    readiness = assess_readiness(readiness_input)

    deal = qualify_deal(
        readiness,
        DealProfile(
            annual_transport_spend_usd=8_000_000,
            invoices_per_month=1200,
            carrier_count=8,
            diagnostic_fee_usd=6250,
            pilot_fee_usd=20000,
            diagnostic_analyst_hours=20,
            pilot_analyst_hours=60,
            loaded_hourly_cost_usd=100,
            diagnostic_other_cost_usd=500,
            pilot_other_cost_usd=2000,
            target_gross_margin=0.50,
        ),
    )

    activation_packet = build_packet(
        asdict(readiness_input),
        {
            "status": "READY",
            "route": "CONTROLLED_MANUAL_BLIND_PILOT",
            "blockers": [],
            "conditions": [],
            "warnings": [],
        },
    )
    charter_request = charter_from_dict(
        {
            "engagement_id": "ENG-SYNTHETIC",
            "buyer_id": BUYER,
            "business_unit": BU,
            "population_rule": "three synthetic invoices",
            "source_date_start": "2026-09-01",
            "source_date_end": "2026-09-30",
            "carrier_scope": ["carrier"],
            "mode_scope": ["LTL"],
            "fixed_fee_usd": 20000,
            "buyer_truth_owner_role": "Truth Owner",
            "buyer_action_approver_role": "VP Supply Chain",
            "freight_engagement_owner_role": "Pilot Lead",
            "buyer_acknowledges_scope": True,
            "buyer_acknowledges_blind_protocol": True,
            "buyer_acknowledges_report_totals_separate": True,
            "buyer_acknowledges_no_guaranteed_recovery": True,
            "freight_acknowledges_no_external_action_without_buyer_approval": True,
        }
    )
    operative_charter = json.loads(
        json.dumps(
            asdict(
                build_charter(
                    json.loads(json.dumps(asdict(activation_packet))),
                    charter_request,
                )
            )
        )
    )
    engagement_resolution = resolve_engagement(operative_charter)

    invoice_csv = (
        "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,"
        "charge_code,service_date,quantity_units,billed_cents\n"
        "inv-1,shp-1,cust,carrier,USD,charge-1,DETENTION,2026-09-15,1,12500\n"
        "inv-2,shp-2,cust,carrier,USD,charge-2,ACCESSORIAL,2026-09-15,1,12500\n"
        "inv-3,shp-3,cust,carrier,USD,charge-3,MISC,2026-09-15,1,15000\n"
    ).encode("utf-8")
    verified_rules_csv = (
        "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"
        "DETENTION,FIXED,2026-09-01,2026-09-30,10000,\n"
        "ACCESSORIAL,FIXED,2026-09-01,2026-09-30,10000,\n"
    ).encode("utf-8")
    review_rules_csv = (
        "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"
        "MISC,FIXED,2026-09-01,2026-09-30,10000,\n"
    ).encode("utf-8")
    workflow = run_audit_workflow(
        invoice_filename="synthetic-freight-charges.csv",
        invoice_data=invoice_csv,
        buyer_id=BUYER,
        business_unit=BU,
        selection_rule="three synthetic invoices",
        rule_inputs=(
            RuleCSVInput(
                filename="rate-confirmation-rules.csv",
                data=verified_rules_csv,
                customer_id="cust",
                carrier_id="carrier",
                currency="USD",
                authority_document_id="rate-confirmation",
                source_document_sha256=None,
                verified_controlling_authority=True,
                source_document_data=b"synthetic verified authority document",
            ),
            RuleCSVInput(
                filename="candidate-addendum-rules.csv",
                data=review_rules_csv,
                customer_id="cust",
                carrier_id="carrier",
                currency="USD",
                authority_document_id="candidate-addendum",
                source_document_sha256=None,
                verified_controlling_authority=False,
                source_document_data=b"synthetic candidate authority document",
            ),
        ),
    )
    if workflow.state != "REVIEW_REQUIRED" or workflow.artifacts is None:
        raise AssertionError("synthetic audit workflow did not reach review-required state")

    artifacts = workflow.artifacts
    invoice_batch = artifacts.invoice_batch
    population_build = artifacts.population_build
    population = population_build.population
    charges = invoice_batch.charges
    verified_rule_batch, review_rule_batch = artifacts.rule_batches
    rules = verified_rule_batch.rules + review_rule_batch.rules
    factory = artifacts.factory
    review_queue = artifacts.review_queue
    review_packet = artifacts.review_packet
    review_routing = artifacts.review_routing
    remediation_plan = artifacts.remediation_plan
    audit_run = artifacts.manifest
    truth = factory.truth
    by_charge = {
        derivation.charge_id: derivation.finding
        for derivation in factory.derivations
        if derivation.finding is not None
    }
    f1, f2, f3 = by_charge["charge-1"], by_charge["charge-2"], by_charge["charge-3"]
    sealed = seal_incumbent_submission(population, "synthetic-incumbent-source-hash")
    incumbent = open_incumbent_output(
        population=population,
        truth=truth,
        submission=sealed,
        finding_ids=(f2.finding_id,),
    )

    case_by_finding = {
        case.finding_id: case
        for case in review_packet.cases
        if case.finding_id is not None
    }
    buyer_review = build_buyer_review_batch(
        review_packet=review_packet,
        review_routing=review_routing,
        truth=truth,
        reviewer_role="Buyer Controller",
        decisions=(
            BuyerReviewDecisionInput(
                case_hash=case_by_finding[f1.finding_id].case_hash,
                disposition=ReviewDisposition.CONFIRMED,
                reviewer_minutes=20,
                reviewed_at="2026-09-20T09:00:00-04:00",
            ),
            BuyerReviewDecisionInput(
                case_hash=case_by_finding[f2.finding_id].case_hash,
                disposition=ReviewDisposition.CONFIRMED,
                reviewer_minutes=10,
                reviewed_at="2026-09-20T09:10:00-04:00",
            ),
        ),
    )
    reviews = buyer_review.finding_reviews
    recovery_claims = build_recovery_claim_batch(
        truth=truth,
        incumbent=incumbent,
        review_packet=review_packet,
        review_routing=review_routing,
        buyer_review=buyer_review,
        issued_at="2026-09-20T14:00:00Z",
    )
    bindings = recovery_claims.bindings
    action_proposals = build_carrier_action_proposal_batch(
        recovery_claims=recovery_claims
    )
    if action_proposals.proposal_count != 1:
        raise AssertionError("synthetic claims should form one carrier/customer action proposal")
    action_proposal = action_proposals.proposals[0]
    action_payload = build_carrier_action_payload(
        proposal=action_proposal,
        recovery_claims=recovery_claims,
        action_type=ActionType.REQUEST_CREDIT_REVIEW,
    )
    external_authorization = authorize_carrier_action_payload(
        resolution=engagement_resolution,
        operative_charter=operative_charter,
        truth=truth,
        review_packet=review_packet,
        review_routing=review_routing,
        buyer_review=buyer_review,
        recovery_claims=recovery_claims,
        proposal=action_proposal,
        payload=action_payload,
        approval=CarrierActionApprovalInput(
            proposal_hash=action_proposal.proposal_hash,
            authorization_id="ACT-SYNTHETIC-1",
            action_type=ActionType.REQUEST_CREDIT_REVIEW,
            recipient_reference_hash="d" * 64,
            action_payload_hash=action_payload.payload_hash,
            approver_role="VP Supply Chain",
            issued_on="2026-09-21",
            expires_on="2026-09-30",
        ),
    )
    assert_action_allowed(
        external_authorization,
        as_of_date="2026-09-21",
        action_type=ActionType.REQUEST_CREDIT_REVIEW,
        target_carrier_id=action_proposal.target_carrier_id,
        target_customer_id=action_proposal.target_customer_id,
        recipient_reference_hash="d" * 64,
        action_payload_hash=action_payload.payload_hash,
        finding_ids=action_proposal.finding_ids,
        currency=action_proposal.currency,
        requested_cents=action_proposal.total_claim_cents,
    )
    execution_intent = build_carrier_action_execution_intent(
        authorization=external_authorization,
        proposal=action_proposal,
        payload=action_payload,
        recovery_claims=recovery_claims,
        prepared_at="2026-09-21T15:00:00Z",
    )
    execution_receipt = record_carrier_action_execution(
        intent=execution_intent,
        authorization=external_authorization,
        proposal=action_proposal,
        payload=action_payload,
        recovery_claims=recovery_claims,
        evidence=CarrierActionExecutionEvidence(
            execution_key=execution_intent.execution_key,
            outcome=ExecutionOutcome.SUBMITTED,
            channel=ExecutionChannel.EMAIL,
            external_reference_hash="1" * 64,
            evidence_source_hash="2" * 64,
            executed_at="2026-09-21T15:01:00Z",
            executor_role="Synthetic Freight Operator",
        ),
    )

    settlement_csv = (
        "event_id,reference,payer_id,payee_id,currency,amount_cents,booked_at,source_kind\n"
        "e-1,inv-1,carrier,cust,USD,2000,2026-09-21T10:00:00Z,CREDIT-MEMO\n"
        "e-2,inv-2,carrier,cust,USD,2500,2026-09-21T10:00:00Z,CREDIT-MEMO\n"
    ).encode("utf-8")
    counter_csv = (
        "counter_id,original_event_id,currency,amount_cents,observed_at,source_kind\n"
        "return-1,e-1,USD,500,2026-09-22T10:00:00Z,BANK-RETURN\n"
    ).encode("utf-8")
    with tempfile.TemporaryDirectory() as td:
        audit_bundle_path = Path(td) / "synthetic-audit-result.zip"
        audit_bundle_receipt = build_audit_result_bundle(workflow, audit_bundle_path)
        verify_audit_result_bundle(workflow, audit_bundle_path)

        store = SettlementStore(
            Path(td) / "settlement.sqlite3",
            buyer_id=BUYER,
            business_unit=BU,
        )
        claim_persistence = persist_recovery_claim_batch(store, recovery_claims)
        settlement_lifecycle = process_settlement_evidence(
            store,
            processed_at="2026-09-21T10:30:00Z",
            settlement_filename="synthetic-settlements.csv",
            settlement_data=settlement_csv,
        )
        assert settlement_lifecycle.state == "REVIEW_REQUIRED"
        assert len(settlement_lifecycle.settlement_review_cases) == 1
        settlement_review_case = settlement_lifecycle.settlement_review_cases[0]
        settlement_review_receipt = apply_settlement_review_decision(
            store,
            case=settlement_review_case,
            decision=SettlementReviewDecisionInput(
                case_hash=settlement_review_case.case_hash,
                claim_id="claim:" + f1.proof_hash,
                reviewer_role="Buyer Controller",
                reviewed_at="2026-09-21T11:00:00Z",
                rationale="Carrier credit memo is documented against inv-1 and partially satisfies the confirmed recovery claim.",
            ),
        )
        assert settlement_review_receipt.allocation_status == ALLOCATED
        assert settlement_lifecycle.settlement_events[1].effective_status == ALLOCATED

        before_return = build_persistent_pilot_report(truth, incumbent, store, bindings, reviews)
        counter_lifecycle = process_settlement_evidence(
            store,
            processed_at="2026-09-22T11:00:00Z",
            counter_filename="synthetic-returns.csv",
            counter_data=counter_csv,
        )
        assert counter_lifecycle.state == "COMPLETE"
        assert counter_lifecycle.counter_events[0].effective_status == REVERSED
        stale_report_rejected = False
        try:
            assert_report_current(before_return, store)
        except ValueError as exc:
            if "snapshot changed" not in str(exc):
                raise
            stale_report_rejected = True
        assert stale_report_rejected

        report = build_persistent_pilot_report(truth, incumbent, store, bindings, reviews)
        assert_report_current(report, store)
        metrics = report.metrics
        store_realized = store.realized_cents()
        store_fee = store.fee_eligible_cents()

    if store_realized != metrics.realized_cents:
        raise AssertionError("persistent settlement store disagrees with pilot report")
    if store_fee != metrics.fee_eligible_realized_cents:
        raise AssertionError("persistent fee attribution disagrees with pilot report")

    return {
        "synthetic": True,
        "buyer_id": BUYER,
        "business_unit": BU,
        "readiness_status": readiness.status.value,
        "readiness_score": readiness.score,
        "deal_route": deal.route.value,
        "pilot_fixed_fee_usd": deal.economics.fee_usd,
        "pilot_delivery_cost_usd": deal.economics.delivery_cost_usd,
        "pilot_gross_margin": deal.economics.gross_margin,
        "population_hash": population.manifest_hash,
        "audit_workflow_state": workflow.state,
        "audit_workflow_summary": render_workflow_summary(workflow),
        "audit_run_hash": audit_run.run_hash,
        "audit_result_bundle_sha256": audit_bundle_receipt.bundle_sha256,
        "audit_result_bundle_manifest_sha256": audit_bundle_receipt.manifest_sha256,
        "audit_result_bundle_entry_count": audit_bundle_receipt.entry_count,
        "population_builder_hash": population_build.builder_hash,
        "population_invoice_count": population_build.invoice_count,
        "population_charge_count": population_build.charge_count,
        "incumbent_submission_hash": sealed.sealed_hash,
        "truth_hash": truth.truth_hash,
        "invoice_csv_adapter_hash": invoice_batch.adapter_hash,
        "invoice_csv_file_sha256": invoice_batch.file_sha256,
        "verified_rule_adapter_hash": verified_rule_batch.adapter_hash,
        "review_rule_adapter_hash": review_rule_batch.adapter_hash,
        "finding_factory_hash": factory.factory_hash,
        "finding_factory_decisions": [item.decision for item in factory.derivations],
        "review_queue_hash": review_queue.queue_hash,
        "review_packet_hash": review_packet.packet_hash,
        "review_route": review_routing.route,
        "review_routing_hash": review_routing.routing_hash,
        "buyer_review_case_count": review_routing.buyer_review_case_count,
        "evidence_remediation_case_count": review_routing.evidence_remediation_case_count,
        "rerun_required": review_routing.rerun_required,
        "remediation_plan_hash": remediation_plan.plan_hash,
        "remediation_plan_item_count": len(remediation_plan.items),
        "buyer_review_state": buyer_review.state,
        "buyer_review_batch_hash": buyer_review.batch_hash,
        "buyer_review_submitted_decision_count": buyer_review.submitted_decision_count,
        "buyer_review_confirmed_count": buyer_review.confirmed_count,
        "buyer_review_pending_case_count": len(buyer_review.pending_case_hashes),
        "recovery_claim_batch_hash": recovery_claims.batch_hash,
        "recovery_claim_count": recovery_claims.claim_count,
        "recovery_claim_fee_disqualified_count": recovery_claims.fee_disqualified_count,
        "recovery_claim_persistence_receipt_hash": claim_persistence.receipt_hash,
        "recovery_claim_persisted_count": claim_persistence.created_claim_count,
        "carrier_action_proposal_batch_hash": action_proposals.batch_hash,
        "carrier_action_proposal_count": action_proposals.proposal_count,
        "carrier_action_proposal_hash": action_proposal.proposal_hash,
        "carrier_action_target_customer_id": action_proposal.target_customer_id,
        "carrier_action_payload_hash": action_payload.payload_hash,
        "carrier_action_payload_subject": action_payload.subject,
        "external_action_authorization_hash": external_authorization.authorization_hash,
        "external_action_authorized_cents": external_authorization.authorized_cents,
        "external_action_automatic_execution_authorized": external_authorization.automatic_execution_authorized,
        "carrier_action_execution_key": execution_intent.execution_key,
        "carrier_action_execution_intent_hash": execution_intent.intent_hash,
        "carrier_action_execution_receipt_hash": execution_receipt.receipt_hash,
        "carrier_action_execution_outcome": execution_receipt.outcome,
        "carrier_action_submitted": execution_receipt.action_submitted,
        "carrier_action_delivery_confirmed": execution_receipt.delivery_confirmed,
        "recovery_claim_already_present_count": claim_persistence.already_present_count,
        "settlement_csv_adapter_hash": settlement_lifecycle.settlement_adapter_hash,
        "settlement_csv_file_sha256": settlement_lifecycle.settlement_file_sha256,
        "settlement_event_count": len(settlement_lifecycle.settlement_events),
        "settlement_lifecycle_state": settlement_lifecycle.state,
        "settlement_lifecycle_state_hash": settlement_lifecycle.state_hash,
        "settlement_lifecycle_execution_hash": settlement_lifecycle.execution_hash,
        "settlement_review_case_hash": settlement_review_case.case_hash,
        "settlement_review_candidate_count": len(settlement_review_case.candidates),
        "settlement_review_hash": settlement_review_receipt.review_hash,
        "settlement_review_receipt_hash": settlement_review_receipt.receipt_hash,
        "settlement_review_allocation_id": settlement_review_receipt.allocation_id,
        "settlement_review_allocation_status": settlement_review_receipt.allocation_status,
        "counter_csv_adapter_hash": counter_lifecycle.counter_adapter_hash,
        "counter_csv_file_sha256": counter_lifecycle.counter_file_sha256,
        "counter_event_count": len(counter_lifecycle.counter_events),
        "counter_lifecycle_state": counter_lifecycle.state,
        "counter_lifecycle_state_hash": counter_lifecycle.state_hash,
        "counter_lifecycle_execution_hash": counter_lifecycle.execution_hash,
        "review_packet_markdown": render_review_packet_markdown(review_packet),
        "review_queue": [
            {
                "charge_id": item.charge_id,
                "priority_class": item.priority_class,
                "decision": item.decision,
            }
            for item in review_queue.items
        ],
        "buyer_review_hashes": [review.review_hash for review in reviews],
        "incumbent_output_hash": incumbent.output_hash,
        "metrics": asdict(metrics),
        "persistent_store": {
            "realized_cents": store_realized,
            "fee_eligible_cents": store_fee,
        },
        "persistent_reporting": {
            "settlement_snapshot_hash": report.settlement_snapshot_hash,
            "report_hash": report.report_hash,
            "pre_return_snapshot_hash": before_return.settlement_snapshot_hash,
            "pre_return_report_hash": before_return.report_hash,
            "pre_return_realized_cents": before_return.metrics.realized_cents,
            "pre_return_fee_eligible_cents": before_return.metrics.fee_eligible_realized_cents,
            "return_cents": 500,
            "stale_report_rejected": stale_report_rejected,
        },
        "report_markdown": render_persistent_markdown(report),
        "commercial_value_claimed": False,
    }


if __name__ == "__main__":
    print(json.dumps(run_rehearsal(), indent=2))
