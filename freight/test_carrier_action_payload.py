import json
from dataclasses import asdict, replace

import pytest

from freight.audit_workflow import RuleCSVInput, run_audit_workflow
from freight.buyer_review_workflow import BuyerReviewDecisionInput, build_buyer_review_batch
from freight.carrier_action_payload import (
    authorize_carrier_action_payload,
    build_carrier_action_payload,
    render_carrier_action_payload_markdown,
    verify_carrier_action_payload,
)
from freight.carrier_action_workflow import (
    CarrierActionApprovalInput,
    build_carrier_action_proposal_batch,
)
from freight.contracts import open_incumbent_output, seal_incumbent_submission
from freight.engagement_state import resolve_engagement
from freight.external_action_authorization import ActionType, assert_action_allowed
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
            "engagement_id": "ENG-PAYLOAD-1",
            "buyer_id": "buyer",
            "business_unit": "unit",
            "population_rule": "period",
            "source_date_start": "2026-09-01",
            "source_date_end": "2026-09-30",
            "carrier_scope": ["K"],
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


def setup(*, invoice_id="I1"):
    result = run_audit_workflow(
        invoice_filename="charges.csv",
        invoice_data=(
            INVOICE_HEADER
            + f"{invoice_id},S1,C,K,USD,X1,A,2026-09-10,1,12500\n"
        ).encode(),
        buyer_id="buyer",
        business_unit="unit",
        selection_rule="period",
        rule_inputs=(
            RuleCSVInput(
                "a.csv",
                (RULE_HEADER + "A,FIXED,2026-09-01,,10000,\n").encode(),
                "C","K","USD","a","a"*64,True,
            ),
        ),
    )
    artifacts = result.artifacts
    assert artifacts is not None
    case_hash = artifacts.review_routing.buyer_review_case_hashes[0]
    review = build_buyer_review_batch(
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        truth=artifacts.factory.truth,
        reviewer_role="Buyer Controller",
        decisions=(
            BuyerReviewDecisionInput(
                case_hash,
                ReviewDisposition.CONFIRMED,
                2,
                "2026-09-21T09:00:00Z",
            ),
        ),
    )
    population = artifacts.population_build.population
    incumbent = open_incumbent_output(
        population=population,
        truth=artifacts.factory.truth,
        submission=seal_incumbent_submission(population, "incumbent-source"),
        finding_ids=(),
    )
    claims = build_recovery_claim_batch(
        truth=artifacts.factory.truth,
        incumbent=incumbent,
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        buyer_review=review,
        issued_at="2026-09-21T10:00:00Z",
    )
    proposal = build_carrier_action_proposal_batch(
        recovery_claims=claims
    ).proposals[0]
    return artifacts, review, claims, proposal


def test_payload_is_deterministic_and_contains_exact_claim_reference_and_amount():
    _, _, claims, proposal = setup()
    a = build_carrier_action_payload(
        proposal=proposal,
        recovery_claims=claims,
        action_type=ActionType.REQUEST_CREDIT_REVIEW,
    )
    b = build_carrier_action_payload(
        proposal=proposal,
        recovery_claims=claims,
        action_type=ActionType.REQUEST_CREDIT_REVIEW,
    )
    assert a == b
    assert a.target_carrier_id == "K"
    assert a.target_customer_id == "C"
    assert a.currency == "USD"
    assert a.requested_cents == 2500
    assert a.line_count == 1
    assert a.lines[0].reference == "I1"
    assert "Reference I1: USD 25.00" in a.body_text
    assert "Total amount in this request: USD 25.00" in a.body_text
    assert len(a.payload_hash) == 64


@pytest.mark.parametrize("action_type", list(ActionType))
def test_each_action_type_has_distinct_canonical_payload(action_type):
    _, _, claims, proposal = setup()
    payload = build_carrier_action_payload(
        proposal=proposal,
        recovery_claims=claims,
        action_type=action_type,
    )
    assert payload.action_type == action_type.value
    assert payload.subject
    assert payload.body_text

    other = (
        ActionType.REQUEST_STATUS
        if action_type is not ActionType.REQUEST_STATUS
        else ActionType.REQUEST_DOCUMENTATION
    )
    other_payload = build_carrier_action_payload(
        proposal=proposal,
        recovery_claims=claims,
        action_type=other,
    )
    assert payload.payload_hash != other_payload.payload_hash


def test_tampered_payload_is_rejected():
    _, _, claims, proposal = setup()
    payload = build_carrier_action_payload(
        proposal=proposal,
        recovery_claims=claims,
        action_type=ActionType.SUBMIT_DISPUTE,
    )
    bad = replace(payload, body_text=payload.body_text + "\nChanged")
    with pytest.raises(ValueError, match="does not match"):
        verify_carrier_action_payload(
            bad,
            proposal=proposal,
            recovery_claims=claims,
        )


def test_external_text_control_character_injection_is_rejected():
    _, _, claims, proposal = setup(invoice_id="I1\tBcc")
    with pytest.raises(ValueError, match="control characters"):
        build_carrier_action_payload(
            proposal=proposal,
            recovery_claims=claims,
            action_type=ActionType.REQUEST_CREDIT_REVIEW,
        )


def test_exact_payload_hash_is_required_for_buyer_authorization():
    artifacts, review, claims, proposal = setup()
    payload = build_carrier_action_payload(
        proposal=proposal,
        recovery_claims=claims,
        action_type=ActionType.REQUEST_CREDIT_REVIEW,
    )
    charter = active_charter()
    resolution = resolve_engagement(charter)
    approval = CarrierActionApprovalInput(
        proposal_hash=proposal.proposal_hash,
        authorization_id="ACT-PAYLOAD-1",
        action_type=ActionType.REQUEST_CREDIT_REVIEW,
        recipient_reference_hash="d"*64,
        action_payload_hash=payload.payload_hash,
        approver_role="VP Supply Chain",
        issued_on="2026-09-21",
        expires_on="2026-09-30",
    )
    auth = authorize_carrier_action_payload(
        resolution=resolution,
        operative_charter=charter,
        truth=artifacts.factory.truth,
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        buyer_review=review,
        recovery_claims=claims,
        proposal=proposal,
        payload=payload,
        approval=approval,
    )
    assert auth.action_payload_hash == payload.payload_hash
    assert auth.target_customer_id == payload.target_customer_id
    assert auth.authorized_cents == payload.requested_cents

    assert_action_allowed(
        auth,
        as_of_date="2026-09-22",
        action_type=ActionType.REQUEST_CREDIT_REVIEW,
        target_carrier_id=payload.target_carrier_id,
        target_customer_id=payload.target_customer_id,
        recipient_reference_hash="d"*64,
        action_payload_hash=payload.payload_hash,
        finding_ids=proposal.finding_ids,
        currency=payload.currency,
        requested_cents=payload.requested_cents,
    )


def test_approval_for_different_payload_hash_is_rejected():
    artifacts, review, claims, proposal = setup()
    payload = build_carrier_action_payload(
        proposal=proposal,
        recovery_claims=claims,
        action_type=ActionType.REQUEST_CREDIT_REVIEW,
    )
    charter = active_charter()
    with pytest.raises(ValueError, match="payload hash"):
        authorize_carrier_action_payload(
            resolution=resolve_engagement(charter),
            operative_charter=charter,
            truth=artifacts.factory.truth,
            review_packet=artifacts.review_packet,
            review_routing=artifacts.review_routing,
            buyer_review=review,
            recovery_claims=claims,
            proposal=proposal,
            payload=payload,
            approval=CarrierActionApprovalInput(
                proposal_hash=proposal.proposal_hash,
                authorization_id="ACT-PAYLOAD-BAD",
                action_type=ActionType.REQUEST_CREDIT_REVIEW,
                recipient_reference_hash="d"*64,
                action_payload_hash="f"*64,
                approver_role="VP Supply Chain",
                issued_on="2026-09-21",
                expires_on="2026-09-30",
            ),
        )


def test_approval_action_type_must_match_payload():
    artifacts, review, claims, proposal = setup()
    payload = build_carrier_action_payload(
        proposal=proposal,
        recovery_claims=claims,
        action_type=ActionType.REQUEST_CREDIT_REVIEW,
    )
    charter = active_charter()
    with pytest.raises(ValueError, match="action type"):
        authorize_carrier_action_payload(
            resolution=resolve_engagement(charter),
            operative_charter=charter,
            truth=artifacts.factory.truth,
            review_packet=artifacts.review_packet,
            review_routing=artifacts.review_routing,
            buyer_review=review,
            recovery_claims=claims,
            proposal=proposal,
            payload=payload,
            approval=CarrierActionApprovalInput(
                proposal_hash=proposal.proposal_hash,
                authorization_id="ACT-PAYLOAD-BAD-TYPE",
                action_type=ActionType.REQUEST_STATUS,
                recipient_reference_hash="d"*64,
                action_payload_hash=payload.payload_hash,
                approver_role="VP Supply Chain",
                issued_on="2026-09-21",
                expires_on="2026-09-30",
            ),
        )


def test_renderer_is_preview_only():
    _, _, claims, proposal = setup()
    payload = build_carrier_action_payload(
        proposal=proposal,
        recovery_claims=claims,
        action_type=ActionType.SUBMIT_DISPUTE,
    )
    text = render_carrier_action_payload_markdown(payload)
    assert "Carrier Action Payload Preview" in text
    assert "Preview only" in text
    assert "does not authorize or send" in text
