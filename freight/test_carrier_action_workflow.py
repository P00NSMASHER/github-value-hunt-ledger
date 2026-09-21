import json
from dataclasses import asdict, replace

import pytest

from freight.audit_workflow import RuleCSVInput, run_audit_workflow
from freight.buyer_review_workflow import (
    BuyerReviewDecisionInput,
    build_buyer_review_batch,
)
from freight.carrier_action_workflow import (
    CarrierActionApprovalInput,
    CarrierActionProposalBatchState,
    authorize_carrier_action_proposal,
    build_carrier_action_proposal_batch,
    render_carrier_action_proposals_markdown,
)
from freight.contracts import open_incumbent_output, seal_incumbent_submission
from freight.engagement_state import resolve_engagement
from freight.external_action_authorization import (
    ActionType,
    assert_action_allowed,
)
from freight.pilot_activation_packet import build_packet
from freight.pilot_charter import build_charter, from_dict as charter_from_dict
from freight.pilot_reporting import ReviewDisposition
from freight.recovery_claim_workflow import build_recovery_claim_batch


INVOICE_HEADER = "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,charge_code,service_date,quantity_units,billed_cents\n"
RULE_HEADER = "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"


def active_charter():
    readiness = {
        "authorization_documented": True,
        "read_only_access": True,
        "population_reproducible": True,
        "incumbent_output_sealable": True,
        "settlement_observable": True,
        "material_authority_reconstructable": True,
        "customer_identity_stable": True,
        "carrier_identity_stable": True,
        "retention_defined": True,
        "deletion_defined": True,
        "invoice_source_coverage": 1.0,
        "authority_source_coverage": 1.0,
        "shipment_evidence_coverage": 1.0,
    }
    packet = build_packet(
        readiness,
        {
            "status": "READY",
            "route": "CONTROLLED_MANUAL_BLIND_PILOT",
            "blockers": [],
            "conditions": [],
            "warnings": [],
        },
    )
    request = charter_from_dict(
        {
            "engagement_id": "ENG-CA-1",
            "buyer_id": "buyer",
            "business_unit": "unit",
            "population_rule": "September accepted charges",
            "source_date_start": "2026-09-01",
            "source_date_end": "2026-09-30",
            "carrier_scope": ["K1"],
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
    return json.loads(json.dumps(asdict(build_charter(json.loads(json.dumps(asdict(packet))), request))))


def setup(disposition=ReviewDisposition.CONFIRMED):
    result = run_audit_workflow(
        invoice_filename="charges.csv",
        invoice_data=(
            INVOICE_HEADER
            + "I1,S1,C1,K1,USD,X1,A,2026-09-10,1,12000\n"
            + "I2,S2,C1,K1,USD,X2,B,2026-09-10,1,13000\n"
            + "I3,S3,C2,K1,USD,X3,C,2026-09-10,1,14000\n"
        ).encode(),
        buyer_id="buyer",
        business_unit="unit",
        selection_rule="September accepted charges",
        rule_inputs=(
            RuleCSVInput("a.csv",(RULE_HEADER+"A,FIXED,2026-09-01,,10000,\n").encode(),"C1","K1","USD","a","a"*64,True),
            RuleCSVInput("b.csv",(RULE_HEADER+"B,FIXED,2026-09-01,,10000,\n").encode(),"C1","K1","USD","b","b"*64,True),
            RuleCSVInput("c.csv",(RULE_HEADER+"C,FIXED,2026-09-01,,10000,\n").encode(),"C2","K1","USD","c","c"*64,True),
        ),
    )
    artifacts = result.artifacts
    assert artifacts is not None
    decisions = tuple(
        BuyerReviewDecisionInput(
            case_hash=case_hash,
            disposition=disposition,
            reviewer_minutes=2,
            reviewed_at=f"2026-09-21T09:0{idx}:00Z",
        )
        for idx, case_hash in enumerate(artifacts.review_routing.buyer_review_case_hashes)
    )
    buyer_review = build_buyer_review_batch(
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        truth=artifacts.factory.truth,
        reviewer_role="Buyer Controller",
        decisions=decisions,
    )
    population = artifacts.population_build.population
    sealed = seal_incumbent_submission(population, "incumbent-source")
    incumbent = open_incumbent_output(
        population=population,
        truth=artifacts.factory.truth,
        submission=sealed,
        finding_ids=(),
    )
    claims = build_recovery_claim_batch(
        truth=artifacts.factory.truth,
        incumbent=incumbent,
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        buyer_review=buyer_review,
        issued_at="2026-09-21T10:00:00Z",
    )
    return artifacts, buyer_review, claims


def test_proposals_group_by_carrier_customer_and_currency_not_carrier_alone():
    _, _, claims = setup()
    batch = build_carrier_action_proposal_batch(recovery_claims=claims)
    assert batch.state == CarrierActionProposalBatchState.PROPOSALS_READY.value
    assert batch.proposal_count == 2
    assert batch.claim_count == 3
    assert batch.total_claim_cents == 9000

    by_customer = {proposal.target_customer_id: proposal for proposal in batch.proposals}
    assert by_customer["C1"].target_carrier_id == "K1"
    assert by_customer["C1"].currency == "USD"
    assert len(by_customer["C1"].claim_ids) == 2
    assert by_customer["C1"].total_claim_cents == 5000
    assert len(by_customer["C2"].claim_ids) == 1
    assert by_customer["C2"].total_claim_cents == 4000
    assert all(len(proposal.proposal_hash) == 64 for proposal in batch.proposals)
    assert len(batch.batch_hash) == 64


def test_no_confirmed_claims_produces_no_action_proposals():
    _, _, claims = setup(disposition=ReviewDisposition.FALSE_POSITIVE)
    batch = build_carrier_action_proposal_batch(recovery_claims=claims)
    assert batch.state == CarrierActionProposalBatchState.NO_CLAIMS.value
    assert batch.proposal_count == 0
    assert batch.proposals == ()


def test_tampered_recovery_claim_batch_is_rejected_before_proposal():
    _, _, claims = setup()
    bad = replace(claims, batch_hash="0" * 64)
    with pytest.raises(ValueError, match="batch hash mismatch"):
        build_carrier_action_proposal_batch(recovery_claims=bad)


def test_exact_proposal_can_receive_separate_buyer_authorization():
    artifacts, buyer_review, claims = setup()
    proposal = next(
        p for p in build_carrier_action_proposal_batch(recovery_claims=claims).proposals
        if p.target_customer_id == "C1"
    )
    charter = active_charter()
    resolution = resolve_engagement(charter)
    authorization = authorize_carrier_action_proposal(
        resolution=resolution,
        operative_charter=charter,
        truth=artifacts.factory.truth,
        buyer_review=buyer_review,
        recovery_claims=claims,
        proposal=proposal,
        approval=CarrierActionApprovalInput(
            proposal_hash=proposal.proposal_hash,
            authorization_id="ACT-C1",
            action_type=ActionType.SUBMIT_DISPUTE,
            recipient_reference_hash="d" * 64,
            action_payload_hash="e" * 64,
            approver_role="VP Supply Chain",
            issued_on="2026-09-21",
            expires_on="2026-09-30",
        ),
    )
    assert authorization.target_carrier_id == "K1"
    assert authorization.target_customer_id == "C1"
    assert authorization.finding_ids == tuple(sorted(proposal.finding_ids))
    assert authorization.authorized_cents == proposal.total_claim_cents
    assert authorization.money_movement_authorized is False
    assert authorization.automatic_execution_authorized is False

    assert_action_allowed(
        authorization,
        as_of_date="2026-09-22",
        action_type=ActionType.SUBMIT_DISPUTE,
        target_carrier_id="K1",
        target_customer_id="C1",
        recipient_reference_hash="d" * 64,
        action_payload_hash="e" * 64,
        finding_ids=proposal.finding_ids,
        currency="USD",
        requested_cents=proposal.total_claim_cents,
    )


def test_authorization_cannot_be_replayed_for_other_customer():
    artifacts, buyer_review, claims = setup()
    proposal = next(
        p for p in build_carrier_action_proposal_batch(recovery_claims=claims).proposals
        if p.target_customer_id == "C1"
    )
    charter = active_charter()
    authorization = authorize_carrier_action_proposal(
        resolution=resolve_engagement(charter),
        operative_charter=charter,
        truth=artifacts.factory.truth,
        buyer_review=buyer_review,
        recovery_claims=claims,
        proposal=proposal,
        approval=CarrierActionApprovalInput(
            proposal_hash=proposal.proposal_hash,
            authorization_id="ACT-C1",
            action_type=ActionType.REQUEST_CREDIT_REVIEW,
            recipient_reference_hash="d" * 64,
            action_payload_hash="e" * 64,
            approver_role="VP Supply Chain",
            issued_on="2026-09-21",
            expires_on="2026-09-30",
        ),
    )
    with pytest.raises(ValueError, match="target customer"):
        assert_action_allowed(
            authorization,
            as_of_date="2026-09-22",
            action_type=ActionType.REQUEST_CREDIT_REVIEW,
            target_carrier_id="K1",
            target_customer_id="C2",
            recipient_reference_hash="d" * 64,
            action_payload_hash="e" * 64,
            finding_ids=proposal.finding_ids,
            currency="USD",
            requested_cents=proposal.total_claim_cents,
        )


def test_approval_must_bind_exact_proposal_and_amount_cannot_exceed_it():
    artifacts, buyer_review, claims = setup()
    proposal = build_carrier_action_proposal_batch(recovery_claims=claims).proposals[0]
    charter = active_charter()
    kwargs = dict(
        resolution=resolve_engagement(charter),
        operative_charter=charter,
        truth=artifacts.factory.truth,
        buyer_review=buyer_review,
        recovery_claims=claims,
        proposal=proposal,
    )
    with pytest.raises(ValueError, match="proposal_hash mismatch"):
        authorize_carrier_action_proposal(
            **kwargs,
            approval=CarrierActionApprovalInput(
                proposal_hash="f" * 64,
                authorization_id="ACT-BAD",
                action_type=ActionType.SUBMIT_DISPUTE,
                recipient_reference_hash="d" * 64,
                action_payload_hash="e" * 64,
                approver_role="VP Supply Chain",
                issued_on="2026-09-21",
                expires_on="2026-09-30",
            ),
        )
    with pytest.raises(ValueError, match="proposal total"):
        authorize_carrier_action_proposal(
            **kwargs,
            approval=CarrierActionApprovalInput(
                proposal_hash=proposal.proposal_hash,
                authorization_id="ACT-BAD-AMOUNT",
                action_type=ActionType.SUBMIT_DISPUTE,
                recipient_reference_hash="d" * 64,
                action_payload_hash="e" * 64,
                approver_role="VP Supply Chain",
                issued_on="2026-09-21",
                expires_on="2026-09-30",
                authorized_cents=proposal.total_claim_cents + 1,
            ),
        )


def test_renderer_states_proposal_is_not_execution_authority():
    _, _, claims = setup()
    text = render_carrier_action_proposals_markdown(
        build_carrier_action_proposal_batch(recovery_claims=claims)
    )
    assert "Carrier Action Proposals" in text
    assert "grouped by carrier, customer/payee and currency" in text
    assert "do not authorize or execute carrier contact" in text
