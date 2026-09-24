import hashlib
import pytest

from freight.counter_review_workflow import (
    CounterReviewDecisionInput,
    apply_counter_review_decision,
    build_counter_review_case,
    render_counter_review_markdown,
)
from freight.settlement_store import (
    ALLOCATED,
    ALREADY_REVERSED,
    REVIEW,
    REVERSED,
    CounterEventRecord,
    RecoveryClaim,
    SettlementEventRecord,
    SettlementStore,
)


def store(tmp_path):
    return SettlementStore(
        tmp_path / "counter-review.sqlite3",
        buyer_id="buyer",
        business_unit="unit",
    )


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def claim(claim_id, reference, amount, source):
    return RecoveryClaim(
        claim_id=claim_id,
        reference=reference,
        payer_id="carrier",
        payee_id="customer",
        currency="USD",
        amount_cents=amount,
        issued_at="2026-09-20T10:00:00Z",
        source_hash=sha(source),
    )


def event(amount=50000):
    return SettlementEventRecord(
        event_id="e1",
        reference="BATCH",
        payer_id="carrier",
        payee_id="customer",
        currency="USD",
        amount_cents=amount,
        booked_at="2026-09-21T10:00:00Z",
        source_hash=sha("settlement-source"),
        source_kind="CREDIT-MEMO",
    )


def counter(counter_id="r1", amount=10000, observed="2026-09-22T10:00:00Z"):
    return CounterEventRecord(
        counter_id=counter_id,
        original_event_id="e1",
        currency="USD",
        amount_cents=amount,
        observed_at=observed,
        source_hash=sha("counter-source-" + counter_id),
        source_kind="BANK-RETURN",
    )


def split_allocated_store(tmp_path, *, a1=30000, a2=20000):
    s=store(tmp_path)
    s.create_claim(claim("c1","I1",a1,"claim-1"))
    s.create_claim(claim("c2","I2",a2,"claim-2"))
    s.ingest_event(event(a1+a2))
    assert s.review_allocate(
        allocation_id="a1",claim_id="c1",event_id="e1",
        amount_cents=a1,created_at="2026-09-21T11:00:00Z",
    )==ALLOCATED
    assert s.review_allocate(
        allocation_id="a2",claim_id="c2",event_id="e1",
        amount_cents=a2,created_at="2026-09-21T11:01:00Z",
    )==ALLOCATED
    return s


def decision(case, allocation_id="a2", at="2026-09-22T11:00:00-04:00"):
    return CounterReviewDecisionInput(
        case_hash=case.case_hash,
        allocation_id=allocation_id,
        reviewer_role="Buyer Controller",
        reviewed_at=at,
        rationale="Bank return detail identifies this allocation as the reversed credit.",
    )


def test_partial_return_across_two_live_edges_requires_proof_bound_review(tmp_path):
    s=split_allocated_store(tmp_path)
    s.ingest_counter(counter(amount=10000))
    auto=s.auto_apply_counter("r1",created_at="2026-09-22T10:30:00Z")
    assert auto.status==REVIEW
    assert "ambiguous" in auto.reason

    case=build_counter_review_case(s,counter_id="r1")
    assert case.counter_residual_cents==10000
    assert case.live_allocation_count==2
    assert [item.allocation_id for item in case.candidates]==["a1","a2"]
    assert [item.live_cents for item in case.candidates]==[30000,20000]
    assert len(case.case_hash)==64

    receipt=apply_counter_review_decision(
        s,case=case,decision=decision(case)
    )
    assert receipt.reversal_status==REVERSED
    assert receipt.allocation_id=="a2"
    assert receipt.amount_cents==10000
    assert receipt.reviewed_at=="2026-09-22T15:00:00.000000Z"
    assert len(receipt.review_hash)==64
    assert len(receipt.receipt_hash)==64
    assert s.realized_cents()==40000


def test_auto_reversible_full_counter_cannot_enter_manual_review(tmp_path):
    s=split_allocated_store(tmp_path)
    s.ingest_counter(counter(amount=50000))
    with pytest.raises(ValueError,match="auto-reversible"):
        build_counter_review_case(s,counter_id="r1")


def test_auto_reversible_single_live_edge_cannot_enter_manual_review(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim("c1","I1",50000,"claim-1"))
    s.ingest_event(event(50000))
    s.review_allocate(
        allocation_id="a1",claim_id="c1",event_id="e1",
        amount_cents=50000,created_at="2026-09-21T11:00:00Z",
    )
    s.ingest_counter(counter(amount=10000))
    with pytest.raises(ValueError,match="auto-reversible"):
        build_counter_review_case(s,counter_id="r1")


def test_selected_allocation_must_be_bound_candidate(tmp_path):
    s=split_allocated_store(tmp_path)
    s.ingest_counter(counter(amount=10000))
    case=build_counter_review_case(s,counter_id="r1")
    with pytest.raises(ValueError,match="not an eligible"):
        apply_counter_review_decision(
            s,case=case,decision=decision(case,allocation_id="missing")
        )
    assert s.count("reversal_edges")==0


def test_stale_counter_case_is_rejected_after_other_reversal_changes_live_state(tmp_path):
    s=split_allocated_store(tmp_path)
    s.ingest_counter(counter("r1",10000))
    case=build_counter_review_case(s,counter_id="r1")

    s.ingest_counter(counter("r2",5000,observed="2026-09-22T10:05:00Z"))
    assert s.review_reverse(
        reversal_id="other-reversal",
        counter_id="r2",
        allocation_id="a1",
        amount_cents=5000,
        created_at="2026-09-22T10:10:00Z",
    )==REVERSED

    with pytest.raises(ValueError,match="no longer matches"):
        apply_counter_review_decision(
            s,case=case,decision=decision(case)
        )
    assert s.realized_cents()==45000


def test_counter_review_timestamp_cannot_predate_observation(tmp_path):
    s=split_allocated_store(tmp_path)
    s.ingest_counter(counter(amount=10000))
    case=build_counter_review_case(s,counter_id="r1")
    with pytest.raises(ValueError,match="cannot predate counter observation"):
        apply_counter_review_decision(
            s,case=case,
            decision=decision(case,at="2026-09-22T09:59:59Z"),
        )


def test_exact_counter_review_replay_is_idempotently_recognized(tmp_path):
    s=split_allocated_store(tmp_path)
    s.ingest_counter(counter(amount=10000))
    case=build_counter_review_case(s,counter_id="r1")
    d=decision(case)

    first=apply_counter_review_decision(s,case=case,decision=d)
    replay=apply_counter_review_decision(s,case=case,decision=d)

    assert first.reversal_status==REVERSED
    assert replay.reversal_status==ALREADY_REVERSED
    assert first.reversal_id==replay.reversal_id
    assert first.review_hash==replay.review_hash
    assert s.count("reversal_edges")==1
    assert s.realized_cents()==40000


def test_no_single_allocation_capacity_produces_no_candidate(tmp_path):
    s=split_allocated_store(tmp_path,a1=40000,a2=60000)
    s.ingest_counter(counter(amount=80000))
    auto=s.auto_apply_counter("r1",created_at="2026-09-22T10:30:00Z")
    assert auto.status==REVIEW
    case=build_counter_review_case(s,counter_id="r1")
    assert case.candidates==()
    with pytest.raises(ValueError,match="not an eligible|no single-allocation"):
        apply_counter_review_decision(
            s,case=case,decision=decision(case,allocation_id="a2")
        )


def test_case_rejected_after_same_counter_already_applied(tmp_path):
    s=split_allocated_store(tmp_path)
    s.ingest_counter(counter(amount=10000))
    case=build_counter_review_case(s,counter_id="r1")
    receipt=apply_counter_review_decision(
        s,case=case,decision=decision(case)
    )
    assert receipt.reversal_status==REVERSED
    with pytest.raises(ValueError,match="already has reversal edge"):
        build_counter_review_case(s,counter_id="r1")


def test_counter_review_requires_reviewer_identity_and_rationale(tmp_path):
    s=split_allocated_store(tmp_path)
    s.ingest_counter(counter(amount=10000))
    case=build_counter_review_case(s,counter_id="r1")

    with pytest.raises(ValueError,match="reviewer_role"):
        apply_counter_review_decision(
            s,case=case,
            decision=CounterReviewDecisionInput(
                case.case_hash,"a1"," ","2026-09-22T11:00:00Z","reason"
            ),
        )
    with pytest.raises(ValueError,match="rationale"):
        apply_counter_review_decision(
            s,case=case,
            decision=CounterReviewDecisionInput(
                case.case_hash,"a1","Buyer Controller","2026-09-22T11:00:00Z"," "
            ),
        )


def test_rendered_counter_review_is_human_readable_and_not_money_movement(tmp_path):
    s=split_allocated_store(tmp_path)
    s.ingest_counter(counter(amount=10000))
    case=build_counter_review_case(s,counter_id="r1")
    receipt=apply_counter_review_decision(
        s,case=case,decision=decision(case)
    )
    text=render_counter_review_markdown(case,receipt)
    assert "Counter/Reversal Review" in text
    assert "Eligible single-allocation candidates" in text
    assert "Reviewer role" in text
    assert "does not move money" in text
    assert receipt.review_hash in text
