from dataclasses import replace

import pytest

from freight.audit_workflow import RuleCSVInput, run_audit_workflow
from freight.buyer_review_workflow import (
    BuyerReviewDecisionInput,
    BuyerReviewState,
    build_buyer_review_batch,
    render_buyer_review_markdown,
)
from freight.pilot_reporting import ReviewDisposition


INVOICE_HEADER = "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,charge_code,service_date,quantity_units,billed_cents\n"
RULE_HEADER = "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"


def workflow(*, only_remediation=False):
    invoice_rows = (
        "I1,S1,C,K,USD,X1,DETENTION,2026-09-10,1,12500\n"
        "I2,S2,C,K,USD,X2,MISC,2026-09-10,1,15000\n"
        "I3,S3,C,K,USD,X3,UNKNOWN,2026-09-10,1,9000\n"
    )
    rules = []
    if not only_remediation:
        rules.append(RuleCSVInput(
            filename="verified.csv",
            data=(RULE_HEADER + "DETENTION,FIXED,2026-09-01,,10000,\n").encode(),
            customer_id="C", carrier_id="K", currency="USD",
            authority_document_id="rate", source_document_sha256="a"*64,
            verified_controlling_authority=True,
        ))
    rules.append(RuleCSVInput(
        filename="candidate.csv",
        data=(RULE_HEADER + "MISC,FIXED,2026-09-01,,10000,\n").encode(),
        customer_id="C", carrier_id="K", currency="USD",
        authority_document_id="candidate", source_document_sha256="b"*64,
        verified_controlling_authority=False,
    ))
    result = run_audit_workflow(
        invoice_filename="charges.csv",
        invoice_data=(INVOICE_HEADER + invoice_rows).encode(),
        buyer_id="buyer",
        business_unit="unit",
        selection_rule="period",
        rule_inputs=tuple(rules),
    )
    assert result.artifacts is not None
    return result.artifacts


def decision(case_hash, disposition=ReviewDisposition.CONFIRMED, minutes=5, at="2026-09-21T09:00:00-04:00"):
    return BuyerReviewDecisionInput(
        case_hash=case_hash,
        disposition=disposition,
        reviewer_minutes=minutes,
        reviewed_at=at,
    )


def test_complete_batch_creates_proof_bound_reviews_for_buyer_ready_cases_only():
    artifacts = workflow()
    buyer_hashes = artifacts.review_routing.buyer_review_case_hashes
    assert len(buyer_hashes) == 1
    batch = build_buyer_review_batch(
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        truth=artifacts.factory.truth,
        reviewer_role="Buyer Controller",
        decisions=(decision(buyer_hashes[0]),),
    )
    assert batch.state == BuyerReviewState.COMPLETE.value
    assert batch.buyer_review_case_count == 1
    assert batch.submitted_decision_count == 1
    assert batch.confirmed_count == 1
    assert batch.false_positive_count == 0
    assert batch.unresolved_count == 0
    assert batch.pending_case_hashes == ()
    assert len(batch.finding_reviews) == 1
    assert batch.finding_reviews[0].review_hash == batch.records[0].review_hash
    assert len(batch.batch_hash) == 64


def test_partial_batch_preserves_pending_case_order():
    artifacts = run_audit_workflow(
        invoice_filename="charges.csv",
        invoice_data=(INVOICE_HEADER
                      + "I1,S1,C,K,USD,X1,A,2026-09-10,1,12000\n"
                      + "I2,S2,C,K,USD,X2,B,2026-09-10,1,13000\n").encode(),
        buyer_id="buyer", business_unit="unit", selection_rule="period",
        rule_inputs=(
            RuleCSVInput("a.csv",(RULE_HEADER+"A,FIXED,2026-09-01,,10000,\n").encode(),"C","K","USD","a","a"*64,True),
            RuleCSVInput("b.csv",(RULE_HEADER+"B,FIXED,2026-09-01,,10000,\n").encode(),"C","K","USD","b","b"*64,True),
        ),
    ).artifacts
    assert artifacts is not None
    hashes = artifacts.review_routing.buyer_review_case_hashes
    batch = build_buyer_review_batch(
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        truth=artifacts.factory.truth,
        reviewer_role="Buyer Controller",
        decisions=(decision(hashes[1]),),
    )
    assert batch.state == BuyerReviewState.PARTIAL.value
    assert batch.pending_case_hashes == (hashes[0],)
    assert batch.records[0].case_hash == hashes[1]


def test_decision_on_remediation_case_is_rejected_and_requires_rerun():
    artifacts = workflow()
    remediation = artifacts.review_routing.remediation_case_hashes[0]
    with pytest.raises(ValueError, match="remediation and audit rerun"):
        build_buyer_review_batch(
            review_packet=artifacts.review_packet,
            review_routing=artifacts.review_routing,
            truth=artifacts.factory.truth,
            reviewer_role="Buyer Controller",
            decisions=(decision(remediation),),
        )


def test_duplicate_decision_is_rejected():
    artifacts = workflow()
    case_hash = artifacts.review_routing.buyer_review_case_hashes[0]
    with pytest.raises(ValueError, match="duplicate buyer review decision"):
        build_buyer_review_batch(
            review_packet=artifacts.review_packet,
            review_routing=artifacts.review_routing,
            truth=artifacts.factory.truth,
            reviewer_role="Buyer Controller",
            decisions=(decision(case_hash), decision(case_hash)),
        )


def test_tampered_routing_is_rejected():
    artifacts = workflow()
    bad = replace(artifacts.review_routing, routing_hash="0"*64)
    with pytest.raises(ValueError, match="routing does not match"):
        build_buyer_review_batch(
            review_packet=artifacts.review_packet,
            review_routing=bad,
            truth=artifacts.factory.truth,
            reviewer_role="Buyer Controller",
        )


def test_tampered_truth_is_rejected():
    artifacts = workflow()
    bad = replace(artifacts.factory.truth, truth_hash="0"*64)
    with pytest.raises(ValueError, match="truth hash"):
        build_buyer_review_batch(
            review_packet=artifacts.review_packet,
            review_routing=artifacts.review_routing,
            truth=bad,
            reviewer_role="Buyer Controller",
        )


def test_all_supported_dispositions_remain_bound_to_exact_finding_proof():
    artifacts = workflow()
    case_hash = artifacts.review_routing.buyer_review_case_hashes[0]
    for disposition in ReviewDisposition:
        batch = build_buyer_review_batch(
            review_packet=artifacts.review_packet,
            review_routing=artifacts.review_routing,
            truth=artifacts.factory.truth,
            reviewer_role="Buyer Controller",
            decisions=(decision(case_hash, disposition=disposition),),
        )
        review = batch.finding_reviews[0]
        assert review.disposition is disposition
        assert review.finding_proof_hash == batch.records[0].finding_proof_hash
        assert review.review_hash


def test_no_buyer_ready_cases_returns_explicit_no_review_state():
    artifacts = workflow(only_remediation=True)
    assert artifacts.review_routing.buyer_review_case_hashes == ()
    batch = build_buyer_review_batch(
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        truth=artifacts.factory.truth,
        reviewer_role="Buyer Controller",
    )
    assert batch.state == BuyerReviewState.NO_BUYER_REVIEW_READY.value
    assert batch.records == ()
    assert batch.finding_reviews == ()


def test_decision_order_does_not_change_batch_proof():
    result = run_audit_workflow(
        invoice_filename="charges.csv",
        invoice_data=(INVOICE_HEADER
                      + "I1,S1,C,K,USD,X1,A,2026-09-10,1,12000\n"
                      + "I2,S2,C,K,USD,X2,B,2026-09-10,1,13000\n").encode(),
        buyer_id="buyer", business_unit="unit", selection_rule="period",
        rule_inputs=(
            RuleCSVInput("a.csv",(RULE_HEADER+"A,FIXED,2026-09-01,,10000,\n").encode(),"C","K","USD","a","a"*64,True),
            RuleCSVInput("b.csv",(RULE_HEADER+"B,FIXED,2026-09-01,,10000,\n").encode(),"C","K","USD","b","b"*64,True),
        ),
    )
    artifacts = result.artifacts
    assert artifacts is not None
    h1,h2 = artifacts.review_routing.buyer_review_case_hashes
    d1=decision(h1, minutes=2, at="2026-09-21T09:00:00Z")
    d2=decision(h2, disposition=ReviewDisposition.UNRESOLVED, minutes=3, at="2026-09-21T09:01:00Z")
    a=build_buyer_review_batch(
        review_packet=artifacts.review_packet, review_routing=artifacts.review_routing,
        truth=artifacts.factory.truth, reviewer_role="Buyer Controller",
        decisions=(d1,d2),
    )
    b=build_buyer_review_batch(
        review_packet=artifacts.review_packet, review_routing=artifacts.review_routing,
        truth=artifacts.factory.truth, reviewer_role="Buyer Controller",
        decisions=(d2,d1),
    )
    assert a == b


def test_renderer_states_decision_and_authorization_boundaries():
    artifacts = workflow()
    h = artifacts.review_routing.buyer_review_case_hashes[0]
    batch = build_buyer_review_batch(
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        truth=artifacts.factory.truth,
        reviewer_role="Buyer Controller",
        decisions=(decision(h),),
    )
    text = render_buyer_review_markdown(batch)
    assert "Buyer Review Decisions" in text
    assert "CONFIRMED" in text
    assert "remediated upstream and rerun" in text
    assert "does not authorize carrier contact" in text
