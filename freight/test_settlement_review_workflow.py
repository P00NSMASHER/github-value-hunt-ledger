import pytest

from freight.settlement_review_workflow import (
    SettlementReviewDecisionInput,
    apply_settlement_review_decision,
    build_settlement_review_case,
    render_settlement_review_markdown,
)
from freight.settlement_store import (
    ALREADY_ALLOCATED,
    ALLOCATED,
    REVIEW,
    RecoveryClaim,
    SettlementEventRecord,
    SettlementStore,
)


def store(tmp_path):
    return SettlementStore(
        tmp_path / "settlement.sqlite3",
        buyer_id="buyer",
        business_unit="unit",
    )


def claim(
    *,
    claim_id="c1",
    reference="INV-1",
    amount=2500,
    issued="2026-09-20T10:00:00Z",
    payer="carrier",
    payee="customer",
    currency="USD",
    source="finding-proof-1",
    fee_disqualified=False,
):
    return RecoveryClaim(
        claim_id=claim_id,
        reference=reference,
        payer_id=payer,
        payee_id=payee,
        currency=currency,
        amount_cents=amount,
        issued_at=issued,
        source_hash=source,
        fee_disqualified=fee_disqualified,
    )


def event(
    *,
    event_id="e1",
    reference="INV-1",
    amount=2000,
    booked="2026-09-21T10:00:00Z",
    payer="carrier",
    payee="customer",
    currency="USD",
    source="settlement-proof-1",
):
    return SettlementEventRecord(
        event_id=event_id,
        reference=reference,
        payer_id=payer,
        payee_id=payee,
        currency=currency,
        amount_cents=amount,
        booked_at=booked,
        source_hash=source,
        source_kind="CREDIT-MEMO",
    )


def decision(case, *, claim_id="c1", at="2026-09-21T11:00:00-04:00"):
    return SettlementReviewDecisionInput(
        case_hash=case.case_hash,
        claim_id=claim_id,
        reviewer_role="Buyer Controller",
        reviewed_at=at,
        rationale="Carrier credit is documented against this recovery claim.",
    )


def test_partial_credit_requires_review_and_produces_proof_bound_allocation(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim())
    s.ingest_event(event())
    auto=s.auto_allocate("e1",created_at="2026-09-21T10:30:00Z")
    assert auto.status == REVIEW

    case=build_settlement_review_case(s,event_id="e1")
    assert case.event_residual_cents == 2000
    assert case.exact_auto_candidate_count == 0
    assert case.auto_review_reason == "exact unique candidate count=0"
    assert [c.claim_id for c in case.candidates] == ["c1"]
    assert case.candidates[0].reference_match is True
    assert case.candidates[0].residual_cents == 2500
    assert len(case.case_hash) == 64

    receipt=apply_settlement_review_decision(
        s,case=case,decision=decision(case)
    )
    assert receipt.allocation_status == ALLOCATED
    assert receipt.amount_cents == 2000
    assert receipt.claim_id == "c1"
    assert receipt.event_id == "e1"
    assert receipt.reviewed_at == "2026-09-21T15:00:00.000000Z"
    assert len(receipt.review_hash) == 64
    assert len(receipt.receipt_hash) == 64
    assert s.realized_cents("c1") == 2000
    assert s.event_residual("e1") == 0


def test_manual_review_is_rejected_when_exact_auto_allocation_is_available(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim(amount=2000))
    s.ingest_event(event(amount=2000))
    with pytest.raises(ValueError,match="auto-allocatable"):
        build_settlement_review_case(s,event_id="e1")


def test_selected_claim_must_be_bound_candidate(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim())
    s.create_claim(claim(
        claim_id="wrong",
        payer="other-carrier",
        source="finding-proof-2",
    ))
    s.ingest_event(event())
    case=build_settlement_review_case(s,event_id="e1")
    with pytest.raises(ValueError,match="not an eligible"):
        apply_settlement_review_decision(
            s,case=case,decision=decision(case,claim_id="wrong")
        )
    assert s.count("allocations") == 0


def test_stale_case_is_rejected_after_claim_capacity_changes(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim(amount=3000))
    s.ingest_event(event(event_id="e1",amount=2000,source="settlement-proof-1"))
    case=build_settlement_review_case(s,event_id="e1")

    s.ingest_event(event(
        event_id="e2",
        amount=1500,
        source="settlement-proof-2",
        booked="2026-09-21T10:05:00Z",
    ))
    assert s.review_allocate(
        allocation_id="manual-other",
        claim_id="c1",
        event_id="e2",
        amount_cents=1500,
        created_at="2026-09-21T10:10:00Z",
    ) == ALLOCATED

    with pytest.raises(ValueError,match="no longer matches"):
        apply_settlement_review_decision(
            s,case=case,decision=decision(case)
        )
    assert s.event_residual("e1") == 2000


def test_reference_mismatch_can_be_review_candidate_for_batch_credit(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim(reference="INV-1",amount=2500))
    s.ingest_event(event(reference="BATCH-CREDIT",amount=1000))
    case=build_settlement_review_case(s,event_id="e1")
    assert len(case.candidates) == 1
    assert case.candidates[0].reference_match is False

    receipt=apply_settlement_review_decision(
        s,
        case=case,
        decision=SettlementReviewDecisionInput(
            case_hash=case.case_hash,
            claim_id="c1",
            reviewer_role="Buyer Controller",
            reviewed_at="2026-09-21T11:00:00Z",
            rationale="Batch credit detail links this carrier credit to INV-1.",
        ),
    )
    assert receipt.allocation_status == ALLOCATED
    assert s.realized_cents("c1") == 1000


def test_review_timestamp_cannot_predate_settlement_booking(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim())
    s.ingest_event(event())
    case=build_settlement_review_case(s,event_id="e1")
    with pytest.raises(ValueError,match="cannot predate settlement booking"):
        apply_settlement_review_decision(
            s,
            case=case,
            decision=decision(case,at="2026-09-21T09:59:59Z"),
        )


def test_exact_replay_is_idempotently_recognized(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim())
    s.ingest_event(event())
    case=build_settlement_review_case(s,event_id="e1")
    d=decision(case)
    first=apply_settlement_review_decision(s,case=case,decision=d)
    replay=apply_settlement_review_decision(s,case=case,decision=d)

    assert first.allocation_status == ALLOCATED
    assert replay.allocation_status == ALREADY_ALLOCATED
    assert replay.review_hash == first.review_hash
    assert replay.allocation_id == first.allocation_id
    assert s.count("allocations") == 1


def test_case_with_no_single_claim_capacity_cannot_be_applied(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim(claim_id="c1",amount=1000,source="a"))
    s.create_claim(claim(claim_id="c2",amount=1000,source="b"))
    s.ingest_event(event(amount=1500))
    case=build_settlement_review_case(s,event_id="e1")
    assert case.candidates == ()
    with pytest.raises(ValueError,match="not an eligible|no single-claim"):
        apply_settlement_review_decision(
            s,case=case,decision=decision(case,claim_id="c1")
        )


def test_review_decision_requires_rationale_and_reviewer_role(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim())
    s.ingest_event(event())
    case=build_settlement_review_case(s,event_id="e1")

    with pytest.raises(ValueError,match="reviewer_role"):
        apply_settlement_review_decision(
            s,
            case=case,
            decision=SettlementReviewDecisionInput(
                case.case_hash,"c1"," ","2026-09-21T11:00:00Z","reason"
            ),
        )
    with pytest.raises(ValueError,match="rationale"):
        apply_settlement_review_decision(
            s,
            case=case,
            decision=SettlementReviewDecisionInput(
                case.case_hash,"c1","Buyer Controller","2026-09-21T11:00:00Z"," "
            ),
        )


def test_rendered_review_is_human_readable_and_not_money_movement(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim())
    s.ingest_event(event())
    case=build_settlement_review_case(s,event_id="e1")
    receipt=apply_settlement_review_decision(
        s,case=case,decision=decision(case)
    )
    text=render_settlement_review_markdown(case,receipt)
    assert "Settlement Allocation Review" in text
    assert "Eligible single-claim candidates" in text
    assert "Reviewer role" in text
    assert "does not move money" in text
    assert receipt.review_hash in text
