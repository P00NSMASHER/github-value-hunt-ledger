import pytest

from freight.settlement_lifecycle_workflow import (
    ALREADY_PRESENT,
    COMPLETE,
    INGESTED,
    REVIEW_REQUIRED,
    process_settlement_evidence,
)
from freight.settlement_store import (
    ALLOCATED,
    REVIEW,
    REVERSED,
    RecoveryClaim,
    SettlementEventRecord,
    SettlementStore,
)


SETTLEMENT_HEADER = (
    "event_id,reference,payer_id,payee_id,currency,amount_cents,"
    "booked_at,source_kind\n"
)
COUNTER_HEADER = (
    "counter_id,original_event_id,currency,amount_cents,observed_at,source_kind\n"
)


def store(tmp_path):
    return SettlementStore(
        tmp_path / "lifecycle.sqlite3",
        buyer_id="buyer",
        business_unit="unit",
    )


def claim(claim_id, reference, amount, source):
    return RecoveryClaim(
        claim_id=claim_id,
        reference=reference,
        payer_id="carrier",
        payee_id="customer",
        currency="USD",
        amount_cents=amount,
        issued_at="2026-09-20T10:00:00Z",
        source_hash=source,
    )


def settlement_bytes(rows):
    return (SETTLEMENT_HEADER + rows).encode()


def counter_bytes(rows):
    return (COUNTER_HEADER + rows).encode()


def test_mixed_settlement_batch_auto_allocates_safe_row_and_routes_partial_to_review(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim("c1","INV-1",2500,"claim-1"))
    s.create_claim(claim("c2","INV-2",2500,"claim-2"))

    result=process_settlement_evidence(
        s,
        processed_at="2026-09-21T11:00:00-04:00",
        settlement_filename="settlements.csv",
        settlement_data=settlement_bytes(
            "e1,INV-1,carrier,customer,USD,2500,2026-09-21T10:00:00Z,CREDIT-MEMO\n"
            "e2,INV-2,carrier,customer,USD,2000,2026-09-21T10:01:00Z,CREDIT-MEMO\n"
        ),
    )

    assert result.state==REVIEW_REQUIRED
    assert result.processed_at=="2026-09-21T15:00:00.000000Z"
    assert [x.ingest_status for x in result.settlement_events]==[INGESTED,INGESTED]
    assert [x.effective_status for x in result.settlement_events]==[ALLOCATED,REVIEW]
    assert result.settlement_events[0].review_case_hash is None
    assert result.settlement_events[1].review_case_hash
    assert len(result.settlement_review_cases)==1
    assert result.settlement_review_cases[0].event_id=="e2"
    assert result.review_case_count==1
    assert s.realized_cents()==2500
    assert s.event_residual("e2")==2000
    assert len(result.state_hash)==64
    assert len(result.execution_hash)==64


def test_ambiguous_partial_counter_is_routed_to_counter_review(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim("c1","I1",30000,"claim-1"))
    s.create_claim(claim("c2","I2",20000,"claim-2"))
    s.ingest_event(SettlementEventRecord(
        "e1","BATCH","carrier","customer","USD",50000,
        "2026-09-21T10:00:00Z","settlement-source","CREDIT-MEMO",
    ))
    s.review_allocate(
        allocation_id="a1",claim_id="c1",event_id="e1",
        amount_cents=30000,created_at="2026-09-21T11:00:00Z",
    )
    s.review_allocate(
        allocation_id="a2",claim_id="c2",event_id="e1",
        amount_cents=20000,created_at="2026-09-21T11:01:00Z",
    )

    result=process_settlement_evidence(
        s,
        processed_at="2026-09-22T11:00:00Z",
        counter_filename="returns.csv",
        counter_data=counter_bytes(
            "r1,e1,USD,10000,2026-09-22T10:00:00Z,BANK-RETURN\n"
        ),
    )

    assert result.state==REVIEW_REQUIRED
    assert len(result.counter_events)==1
    assert result.counter_events[0].effective_status==REVIEW
    assert result.counter_events[0].review_case_hash
    assert len(result.counter_review_cases)==1
    case=result.counter_review_cases[0]
    assert case.counter_id=="r1"
    assert [c.allocation_id for c in case.candidates]==["a1","a2"]
    assert s.realized_cents()==50000
    assert s.count("reversal_edges")==0


def test_settlement_and_full_counter_can_process_in_one_call_and_replay_stably(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim("c1","INV-1",2500,"claim-1"))
    settlement=settlement_bytes(
        "e1,INV-1,carrier,customer,USD,2500,2026-09-21T10:00:00Z,CREDIT-MEMO\n"
    )
    counters=counter_bytes(
        "r1,e1,USD,2500,2026-09-22T10:00:00Z,BANK-RETURN\n"
    )

    first=process_settlement_evidence(
        s,
        processed_at="2026-09-22T11:00:00Z",
        settlement_filename="settlements.csv",
        settlement_data=settlement,
        counter_filename="returns.csv",
        counter_data=counters,
    )
    assert first.state==COMPLETE
    assert first.settlement_events[0].effective_status==ALLOCATED
    assert first.counter_events[0].effective_status==REVERSED
    assert first.review_case_count==0
    assert s.realized_cents()==0

    replay=process_settlement_evidence(
        s,
        processed_at="2026-09-22T12:00:00Z",
        settlement_filename="settlements.csv",
        settlement_data=settlement,
        counter_filename="returns.csv",
        counter_data=counters,
    )
    assert replay.state==COMPLETE
    assert replay.settlement_events[0].ingest_status==ALREADY_PRESENT
    assert replay.counter_events[0].ingest_status==ALREADY_PRESENT
    assert replay.settlement_events[0].effective_status==ALLOCATED
    assert replay.counter_events[0].effective_status==REVERSED
    assert replay.state_hash==first.state_hash
    assert replay.store_snapshot_after_hash==first.store_snapshot_after_hash
    assert replay.execution_hash!=first.execution_hash
    assert s.count("allocations")==1
    assert s.count("reversal_edges")==1


def test_bad_counter_csv_is_rejected_before_valid_settlement_file_writes(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim("c1","INV-1",2500,"claim-1"))
    with pytest.raises(ValueError,match="CSV schema mismatch"):
        process_settlement_evidence(
            s,
            processed_at="2026-09-21T11:00:00Z",
            settlement_filename="settlements.csv",
            settlement_data=settlement_bytes(
                "e1,INV-1,carrier,customer,USD,2500,2026-09-21T10:00:00Z,CREDIT-MEMO\n"
            ),
            counter_filename="bad.csv",
            counter_data=b"counter_id,wrong\nr1,x\n",
        )
    assert s.count("settlement_events")==0
    assert s.count("allocations")==0


def test_unknown_counter_reference_is_preflighted_before_incoming_settlement_write(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim("c1","INV-1",2500,"claim-1"))
    with pytest.raises(ValueError,match="counter references unknown settlement event"):
        process_settlement_evidence(
            s,
            processed_at="2026-09-22T11:00:00Z",
            settlement_filename="settlements.csv",
            settlement_data=settlement_bytes(
                "e1,INV-1,carrier,customer,USD,2500,2026-09-21T10:00:00Z,CREDIT-MEMO\n"
            ),
            counter_filename="returns.csv",
            counter_data=counter_bytes(
                "r1,missing,USD,2500,2026-09-22T10:00:00Z,BANK-RETURN\n"
            ),
        )
    assert s.count("settlement_events")==0
    assert s.count("counter_events")==0


def test_conflicting_existing_settlement_replay_is_preflighted_before_writes(tmp_path):
    s=store(tmp_path)
    existing=SettlementEventRecord(
        "e1","INV-1","carrier","customer","USD",2500,
        "2026-09-21T10:00:00Z","existing-source","CREDIT-MEMO",
    )
    s.ingest_event(existing)
    with pytest.raises(ValueError,match="replay conflicts"):
        process_settlement_evidence(
            s,
            processed_at="2026-09-21T11:00:00Z",
            settlement_filename="settlements.csv",
            settlement_data=settlement_bytes(
                "e1,INV-1,carrier,customer,USD,3000,2026-09-21T10:00:00Z,CREDIT-MEMO\n"
            ),
        )
    assert s.count("settlement_events")==1
    assert s.count("allocations")==0


def test_counter_can_reference_settlement_row_from_same_input_package(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim("c1","INV-1",2500,"claim-1"))
    result=process_settlement_evidence(
        s,
        processed_at="2026-09-22T11:00:00Z",
        settlement_filename="settlements.csv",
        settlement_data=settlement_bytes(
            "e1,INV-1,carrier,customer,USD,2500,2026-09-21T10:00:00Z,CREDIT-MEMO\n"
        ),
        counter_filename="returns.csv",
        counter_data=counter_bytes(
            "r1,e1,USD,2500,2026-09-22T10:00:00Z,BANK-RETURN\n"
        ),
    )
    assert result.state==COMPLETE
    assert result.counter_events[0].effective_status==REVERSED


def test_requires_at_least_one_evidence_file_and_timezone_aware_processing_time(tmp_path):
    s=store(tmp_path)
    with pytest.raises(ValueError,match="at least one"):
        process_settlement_evidence(s,processed_at="2026-09-21T11:00:00Z")
    with pytest.raises(ValueError,match="timezone-aware"):
        process_settlement_evidence(
            s,
            processed_at="2026-09-21T11:00:00",
            settlement_filename="settlements.csv",
            settlement_data=settlement_bytes(
                "e1,INV-1,carrier,customer,USD,2500,2026-09-21T10:00:00Z,CREDIT-MEMO\n"
            ),
        )


def test_scope_is_always_taken_from_bound_store(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim("c1","INV-1",2500,"claim-1"))
    result=process_settlement_evidence(
        s,
        processed_at="2026-09-21T11:00:00Z",
        settlement_filename="settlements.csv",
        settlement_data=settlement_bytes(
            "e1,INV-1,carrier,customer,USD,2500,2026-09-21T10:00:00Z,CREDIT-MEMO\n"
        ),
    )
    assert result.buyer_id=="buyer"
    assert result.business_unit=="unit"
