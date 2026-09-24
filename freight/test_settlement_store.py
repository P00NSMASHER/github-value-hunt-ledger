from concurrent.futures import ThreadPoolExecutor
import hashlib
import sqlite3
import pytest

from freight.settlement_store import (
    ALLOCATED, ALREADY_ALLOCATED, ALREADY_REVERSED, REVIEW, REVERSED,
    CounterEventRecord, RecoveryClaim, SettlementEventRecord, SettlementStore,
)


def S(tmp_path, *, buyer_id="TEST_BUYER", business_unit="TEST_BU"):
    return SettlementStore(tmp_path / "settlement.sqlite3", buyer_id=buyer_id, business_unit=business_unit)

def H(value):
    return hashlib.sha256(value.encode()).hexdigest()

def C(cid="c1", ref="INV-1", amt=50000, issued="2026-09-01T10:00:00Z", currency="USD", disq=False):
    return RecoveryClaim(cid, ref, "carrier", "buyer", currency, amt, issued, H(f"claim-src-{cid}"), disq)
def E(eid="e1", ref="INV-1", amt=50000, booked="2026-09-02T10:00:00Z", currency="USD", payer="carrier", payee="buyer"):
    return SettlementEventRecord(eid, ref, payer, payee, currency, amt, booked, H(f"settle-src-{eid}"), "X12-820")
def R(rid="r1", original="e1", amt=50000, currency="USD"):
    return CounterEventRecord(rid, original, currency, amt, "2026-09-03T10:00:00Z", H(f"return-src-{rid}"), "BANK-RETURN")

ALLOCATED_AT="2026-09-02T11:00:00Z"
COUNTER_AT="2026-09-03T11:00:00Z"
LATER_AT="2026-09-04T11:00:00Z"


def test_01_multi_rmr_invoice_grain(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","INV-1",15000)); s.create_claim(C("c2","INV-2",20000))
    s.ingest_event(E("e1","INV-1",15000)); s.ingest_event(E("e2","INV-2",20000))
    assert s.auto_allocate("e1",created_at="2026-09-02T11:00:00Z").status==ALLOCATED
    assert s.auto_allocate("e2",created_at="2026-09-02T11:00:00Z").status==ALLOCATED
    assert s.realized_cents()==35000


def test_02_partial_payment_is_reviewed(tmp_path):
    s=S(tmp_path); s.create_claim(C(amt=100000)); s.ingest_event(E(amt=60000))
    assert s.auto_allocate("e1",created_at=ALLOCATED_AT).status==REVIEW
    assert s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=60000,created_at=COUNTER_AT)==ALLOCATED
    assert (s.realized_cents("c1"),s.claim_residual("c1"))==(60000,40000)


def test_03_duplicate_invoice_reference_is_ambiguous(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","INV-X",30000)); s.create_claim(C("c2","INV-X",30000)); s.ingest_event(E(ref="INV-X",amt=30000))
    d=s.auto_allocate("e1",created_at=ALLOCATED_AT); assert d.status==REVIEW and "count=2" in d.reason and s.realized_cents()==0


def test_04_preissue_event_stays_zero_later_event_can_settle(tmp_path):
    s=S(tmp_path); s.create_claim(C(amt=30000,issued="2026-09-05T10:00:00Z")); s.ingest_event(E("early",amt=30000,booked="2026-09-04T10:00:00Z"))
    assert s.auto_allocate("early",created_at="2026-09-04T11:00:00Z").status==REVIEW
    s.ingest_event(E("late",amt=30000,booked="2026-09-06T10:00:00Z")); assert s.auto_allocate("late",created_at="2026-09-06T11:00:00Z").status==ALLOCATED


def test_05_overpayment_preserves_event_residual(tmp_path):
    s=S(tmp_path); s.create_claim(C(amt=70000)); s.ingest_event(E(amt=75000)); assert s.auto_allocate("e1",created_at=ALLOCATED_AT).status==REVIEW
    s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=70000,created_at=COUNTER_AT)
    assert (s.realized_cents(),s.event_residual("e1"))==(70000,5000)


def test_06_orphan_is_review(tmp_path):
    s=S(tmp_path); s.create_claim(C(ref="OTHER",amt=30000)); s.ingest_event(E(ref="NONE",amt=30000)); assert s.auto_allocate("e1",created_at=ALLOCATED_AT).status==REVIEW


def test_07_split_settlement_stays_review_only(tmp_path):
    s=S(tmp_path); s.create_claim(C(amt=90000)); s.ingest_event(E("e1",amt=40000)); s.ingest_event(E("e2",amt=50000))
    assert s.auto_allocate("e1",created_at=ALLOCATED_AT).status==REVIEW
    s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=40000,created_at=COUNTER_AT)
    assert s.auto_allocate("e2",created_at=LATER_AT).status==REVIEW
    s.review_allocate(allocation_id="a2",claim_id="c1",event_id="e2",amount_cents=50000,created_at=LATER_AT); assert s.realized_cents()==90000


def test_08_duplicate_settlement_replay_is_idempotent(tmp_path):
    s=S(tmp_path); s.create_claim(C()); e=E(); assert s.ingest_event(e) and not s.ingest_event(e)
    assert s.auto_allocate("e1",created_at=ALLOCATED_AT).status==ALLOCATED and s.auto_allocate("e1",created_at=ALLOCATED_AT).status==ALREADY_ALLOCATED
    assert s.count("settlement_events")==1 and s.count("allocations")==1


def test_09_full_return_claws_back_and_only_claim_reopens(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E()); s.auto_allocate("e1",created_at=ALLOCATED_AT); s.ingest_counter(R())
    assert s.auto_apply_counter("r1",created_at=COUNTER_AT).status==REVERSED
    assert (s.realized_cents(),s.claim_residual("c1"),s.event_residual("e1"))==(0,50000,0)
    s.ingest_event(E("e2",booked="2026-09-04T10:00:00Z")); assert s.auto_allocate("e2",created_at=LATER_AT).status==ALLOCATED


def test_10_duplicate_return_is_idempotent(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E()); s.auto_allocate("e1",created_at=ALLOCATED_AT); r=R(); assert s.ingest_counter(r) and not s.ingest_counter(r)
    assert s.auto_apply_counter("r1",created_at=COUNTER_AT).status==REVERSED and s.auto_apply_counter("r1",created_at=COUNTER_AT).status==ALREADY_REVERSED
    assert s.count("reversal_edges")==1 and s.realized_cents()==0


def test_11_partial_return_across_two_edges_is_review(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","I1",30000)); s.create_claim(C("c2","I2",20000)); s.ingest_event(E(ref="BATCH",amt=50000))
    s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=30000,created_at=ALLOCATED_AT); s.review_allocate(allocation_id="a2",claim_id="c2",event_id="e1",amount_cents=20000,created_at=ALLOCATED_AT)
    s.ingest_counter(R(amt=10000)); assert s.auto_apply_counter("r1",created_at=COUNTER_AT).status==REVIEW and s.realized_cents()==50000


def test_12_second_payment_after_satisfied_claim_is_review(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E("e1")); s.ingest_event(E("e2",booked="2026-09-03T10:00:00Z")); s.auto_allocate("e1",created_at=ALLOCATED_AT)
    assert s.auto_allocate("e2",created_at=COUNTER_AT).status==REVIEW and s.realized_cents()==50000


def test_13_same_event_cannot_be_consumed_twice(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","I1")); s.create_claim(C("c2","I2")); s.ingest_event(E(ref="BATCH")); s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at=ALLOCATED_AT)
    with pytest.raises(ValueError,match="settlement event capacity exceeded"): s.review_allocate(allocation_id="a2",claim_id="c2",event_id="e1",amount_cents=1,created_at=COUNTER_AT)


def test_14_wrong_currency_never_realizes(tmp_path):
    s=S(tmp_path); s.create_claim(C(currency="USD")); s.ingest_event(E(currency="EUR")); assert s.auto_allocate("e1",created_at=ALLOCATED_AT).status==REVIEW
    with pytest.raises(ValueError,match="currency mismatch"): s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at=COUNTER_AT)


def test_15_review_path_rejects_preissue_settlement(tmp_path):
    s=S(tmp_path); s.create_claim(C(issued="2026-09-05T10:00:00Z")); s.ingest_event(E(booked="2026-09-04T10:00:00Z")); assert s.auto_allocate("e1",created_at=LATER_AT).status==REVIEW
    with pytest.raises(ValueError,match="predates issued claim"): s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at="2026-09-05T11:00:00Z")


def test_16_review_path_rejects_counterparty_mismatch(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E(payer="other-carrier"))
    assert s.auto_allocate("e1",created_at=ALLOCATED_AT).status==REVIEW
    with pytest.raises(ValueError,match="payer/payee mismatch"):
        s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at=COUNTER_AT)
    assert s.realized_cents()==0


def test_17_timezone_offsets_are_normalized_before_ordering(tmp_path):
    s=S(tmp_path)
    s.create_claim(C(issued="2026-09-01T06:00:00-04:00"))
    s.ingest_event(E(booked="2026-09-01T09:59:59Z"))
    assert s.auto_allocate("e1",created_at=ALLOCATED_AT).status==REVIEW
    with pytest.raises(ValueError,match="predates issued claim"):
        s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at=COUNTER_AT)


@pytest.mark.parametrize("bad_timestamp", ["2026-09-01T10:00:00", "not-a-time", ""])
def test_18_settlement_timestamps_require_timezone_awareness(tmp_path, bad_timestamp):
    s=S(tmp_path)
    with pytest.raises(ValueError,match="timestamp|required"):
        s.create_claim(C(issued=bad_timestamp))


def test_19_sql_trigger_blocks_counterparty_mismatch_and_review_lock_mutation(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","I1")); s.ingest_event(E(ref="BATCH",payer="other-carrier"))
    conn=sqlite3.connect(s.path); conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(sqlite3.IntegrityError,match="payer/payee mismatch"):
        conn.execute("""INSERT INTO allocations
          (buyer_id,business_unit,allocation_id,claim_id,event_id,amount_cents,mode,fee_eligible_cents,created_at)
          VALUES('TEST_BUYER','TEST_BU','a1','c1','e1',50000,'REVIEW',50000,'2026-09-02T11:00:00.000000Z')""")
    conn.close()

    s2=SettlementStore(tmp_path/"review-lock.sqlite3", buyer_id="TEST_BUYER", business_unit="TEST_BU")
    s2.create_claim(C()); s2.ingest_event(E(amt=25000))
    s2.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=25000,created_at=ALLOCATED_AT)
    conn=sqlite3.connect(s2.path)
    with pytest.raises(sqlite3.IntegrityError,match="review claim is immutable"):
        conn.execute("DELETE FROM review_claims WHERE buyer_id='TEST_BUYER' AND business_unit='TEST_BU' AND claim_id='c1'")
    conn.close()


def test_fee_eligibility_tracks_active_edge_and_disqualification(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E()); s.auto_allocate("e1",created_at=ALLOCATED_AT); assert s.fee_eligible_cents()==50000
    s.ingest_counter(R()); s.auto_apply_counter("r1",created_at=COUNTER_AT); assert s.fee_eligible_cents()==0
    s2=SettlementStore(tmp_path/"d2.sqlite3", buyer_id="TEST_BUYER", business_unit="TEST_BU"); s2.create_claim(C(disq=True)); s2.ingest_event(E()); s2.auto_allocate("e1",created_at=ALLOCATED_AT); assert s2.realized_cents()==50000 and s2.fee_eligible_cents()==0


def test_concurrent_duplicate_ingest_and_auto_allocate_once(tmp_path):
    s=S(tmp_path); s.create_claim(C()); e=E()
    def w(_): s.ingest_event(e); return s.auto_allocate("e1",created_at=ALLOCATED_AT).status
    with ThreadPoolExecutor(max_workers=8) as p: states=list(p.map(w,range(16)))
    assert states.count(ALLOCATED)==1 and set(states)<={ALLOCATED,ALREADY_ALLOCATED}; assert s.count("allocations")==1 and s.realized_cents()==50000


def test_concurrent_two_events_cannot_overconsume_claim(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E("e1")); s.ingest_event(E("e2",booked="2026-09-02T10:00:01Z"))
    with ThreadPoolExecutor(max_workers=2) as p: states=list(p.map(lambda eid:s.auto_allocate(eid,created_at=ALLOCATED_AT).status,["e1","e2"]))
    assert states.count(ALLOCATED)==1 and states.count(REVIEW)==1 and s.realized_cents()==50000 and s.count("allocations")==1


def test_concurrent_review_edges_cannot_overconsume_event(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","I1")); s.create_claim(C("c2","I2")); s.ingest_event(E(ref="BATCH"))
    def w(pair):
        try: return s.review_allocate(allocation_id=pair[0],claim_id=pair[1],event_id="e1",amount_cents=50000,created_at=ALLOCATED_AT)
        except (ValueError,sqlite3.IntegrityError) as exc: return str(exc)
    with ThreadPoolExecutor(max_workers=2) as p: out=list(p.map(w,[("a1","c1"),("a2","c2")]))
    assert out.count(ALLOCATED)==1 and s.count("allocations")==1 and s.realized_cents()==50000


def test_concurrent_duplicate_counter_reverses_once(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E()); s.auto_allocate("e1",created_at=ALLOCATED_AT); r=R()
    def w(_): s.ingest_counter(r); return s.auto_apply_counter("r1",created_at=COUNTER_AT).status
    with ThreadPoolExecutor(max_workers=8) as p: states=list(p.map(w,range(16)))
    assert states.count(REVERSED)==1 and set(states)<={REVERSED,ALREADY_REVERSED}; assert s.count("reversal_edges")==1 and s.realized_cents()==0


def test_sql_triggers_block_direct_overconsume_and_mutation(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","I1")); s.create_claim(C("c2","I2")); s.ingest_event(E(ref="BATCH")); s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at=ALLOCATED_AT)
    conn=sqlite3.connect(s.path); conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(sqlite3.IntegrityError,match="settlement event capacity exceeded"):
        conn.execute("""INSERT INTO allocations
          (buyer_id,business_unit,allocation_id,claim_id,event_id,amount_cents,mode,fee_eligible_cents,created_at)
          VALUES('TEST_BUYER','TEST_BU','bypass','c2','e1',1,'REVIEW',1,'2026-09-02T11:00:00.000000Z')""")
    with pytest.raises(sqlite3.IntegrityError,match="recovery claim is immutable"):
        conn.execute("UPDATE recovery_claims SET amount_cents=1 WHERE buyer_id='TEST_BUYER' AND business_unit='TEST_BU' AND claim_id='c1'")
    conn.close()


def test_cross_tenant_same_local_ids_and_hashes_are_isolated(tmp_path):
    path=tmp_path/"shared.sqlite3"
    a=SettlementStore(path,buyer_id="BUYER-A",business_unit="OPS")
    b=SettlementStore(path,buyer_id="BUYER-B",business_unit="OPS")
    # Same local identifiers and source hashes are legal because scope is part of identity.
    assert a.create_claim(C())
    assert b.create_claim(C())
    assert a.ingest_event(E())
    assert b.ingest_event(E())
    assert a.auto_allocate("e1",created_at=ALLOCATED_AT).status==ALLOCATED
    assert b.auto_allocate("e1",created_at=ALLOCATED_AT).status==ALLOCATED
    assert a.realized_cents()==50000 and b.realized_cents()==50000
    assert a.count("allocations")==1 and b.count("allocations")==1


def test_cross_tenant_event_cannot_match_other_tenant_claim(tmp_path):
    path=tmp_path/"shared.sqlite3"
    a=SettlementStore(path,buyer_id="BUYER-A",business_unit="OPS")
    b=SettlementStore(path,buyer_id="BUYER-B",business_unit="OPS")
    a.create_claim(C())
    b.ingest_event(E())
    d=b.auto_allocate("e1",created_at=ALLOCATED_AT)
    assert d.status==REVIEW and "count=0" in d.reason
    assert a.realized_cents()==0 and b.realized_cents()==0
    with pytest.raises(ValueError,match="existing claim and settlement event"):
        b.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at=ALLOCATED_AT)


def test_cross_tenant_reads_are_scope_bound(tmp_path):
    path=tmp_path/"shared.sqlite3"
    a=SettlementStore(path,buyer_id="BUYER-A",business_unit="OPS")
    b=SettlementStore(path,buyer_id="BUYER-B",business_unit="OPS")
    a.create_claim(C()); a.ingest_event(E())
    assert a.count("settlement_events")==1 and b.count("settlement_events")==0
    with pytest.raises(ValueError,match="unknown recovery claim"):
        b.claim_residual("c1")
    with pytest.raises(ValueError,match="unknown settlement event"):
        b.event_residual("e1")


def test_direct_sql_cannot_cross_scope_allocation(tmp_path):
    path=tmp_path/"shared.sqlite3"
    a=SettlementStore(path,buyer_id="BUYER-A",business_unit="OPS")
    b=SettlementStore(path,buyer_id="BUYER-B",business_unit="OPS")
    a.create_claim(C()); b.ingest_event(E())
    conn=sqlite3.connect(path); conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(sqlite3.IntegrityError,match="FOREIGN KEY constraint failed"):
        conn.execute("""INSERT INTO allocations
          (buyer_id,business_unit,allocation_id,claim_id,event_id,amount_cents,mode,fee_eligible_cents,created_at)
          VALUES('BUYER-B','OPS','x','c1','e1',50000,'REVIEW',50000,'2026-09-02T11:00:00.000000Z')""")
    conn.close()


def test_legacy_unscoped_schema_fails_closed(tmp_path):
    path=tmp_path/"legacy.sqlite3"
    conn=sqlite3.connect(path)
    conn.execute("CREATE TABLE recovery_claims (claim_id TEXT PRIMARY KEY)")
    conn.commit(); conn.close()
    with pytest.raises((RuntimeError,sqlite3.OperationalError)):
        SettlementStore(path,buyer_id="BUYER-A",business_unit="OPS")


@pytest.mark.parametrize("amount", [100.9, 100.0, "100", True, False, float("nan"), float("inf"), 0, -1, 2**63])
@pytest.mark.parametrize("operation", ["claim", "settlement", "counter", "allocation"])
def test_input_amounts_require_exact_integer_cents(tmp_path, operation, amount):
    s = S(tmp_path)
    s.create_claim(C())
    s.ingest_event(E())
    with pytest.raises(ValueError, match="positive integer cents"):
        if operation == "claim":
            s.create_claim(C(cid="invalid", amt=amount))
        elif operation == "settlement":
            s.ingest_event(E(eid="invalid", amt=amount))
        elif operation == "counter":
            s.ingest_counter(R(rid="invalid", amt=amount))
        else:
            s.review_allocate(allocation_id="invalid", claim_id="c1", event_id="e1", amount_cents=amount, created_at="2026-09-02T11:00:00Z")
    assert s.realized_cents() == 0
    assert s.count("settlement_events") == 1
    assert s.count("counter_events") == 0
    assert s.count("allocations") == 0


@pytest.mark.parametrize("flag", [0, 1, 0.5, "false", "true", None])
def test_claim_fee_disqualification_requires_a_boolean(tmp_path, flag):
    with pytest.raises(ValueError, match="fee_disqualified must be a boolean"):
        S(tmp_path).create_claim(C(disq=flag))


def test_atomic_claim_batch_inserts_all_and_replays_idempotently(tmp_path):
    s=S(tmp_path)
    claims=(C("c1","I1",10000), C("c2","I2",20000))
    assert s.create_claims(claims)==(True,True)
    assert s.count("recovery_claims")==2
    assert s.create_claims(claims)==(False,False)
    assert s.count("recovery_claims")==2


def test_atomic_claim_batch_rolls_back_earlier_insert_when_later_claim_conflicts(tmp_path):
    s=S(tmp_path)
    s.create_claim(C("c2","I2",9999))
    before=s.count("recovery_claims")
    with pytest.raises(ValueError,match="replay conflicts"):
        s.create_claims((C("c1","I1",10000),C("c2","I2",20000)))
    assert s.count("recovery_claims")==before
    with pytest.raises(ValueError,match="unknown recovery claim"):
        s.claim_residual("c1")


def test_atomic_claim_batch_rejects_duplicate_claim_or_source_before_writing(tmp_path):
    s=S(tmp_path)
    with pytest.raises(ValueError,match="duplicate claim_id"):
        s.create_claims((C("c1","I1",10000),C("c1","I2",20000)))
    assert s.count("recovery_claims")==0

    a=C("a","I1",10000)
    b=RecoveryClaim("b","I2","carrier","buyer","USD",20000,
                    "2026-09-01T10:00:00Z",a.source_hash,False)
    with pytest.raises(ValueError,match="duplicate source_hash"):
        s.create_claims((a,b))
    assert s.count("recovery_claims")==0



def test_review_reverse_applies_selected_partial_counter_edge(tmp_path):
    s=S(tmp_path)
    s.create_claim(C("c1","I1",30000))
    s.create_claim(C("c2","I2",20000))
    s.ingest_event(E(ref="BATCH",amt=50000))
    s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=30000,created_at="2026-09-02T11:00:00Z")
    s.review_allocate(allocation_id="a2",claim_id="c2",event_id="e1",amount_cents=20000,created_at="2026-09-02T11:00:00Z")
    s.ingest_counter(R(amt=10000))
    assert s.auto_apply_counter("r1",created_at="2026-09-03T11:00:00Z").status==REVIEW

    assert s.review_reverse(
        reversal_id="rr1",
        counter_id="r1",
        allocation_id="a2",
        amount_cents=10000,
        created_at="2026-09-03T12:00:00-04:00",
    )==REVERSED
    assert s.realized_cents()==40000
    assert s.count("reversal_edges")==1


def test_review_reverse_exact_replay_is_idempotent(tmp_path):
    s=S(tmp_path)
    s.create_claim(C())
    s.ingest_event(E())
    s.auto_allocate("e1",created_at="2026-09-02T11:00:00Z")
    s.ingest_counter(R(amt=10000))
    args=dict(
        reversal_id="rr1",
        counter_id="r1",
        allocation_id="auto:e1:c1",
        amount_cents=10000,
        created_at="2026-09-03T12:00:00-04:00",
    )
    assert s.review_reverse(**args)==REVERSED
    assert s.review_reverse(**args)==ALREADY_REVERSED
    assert s.count("reversal_edges")==1
    assert s.realized_cents()==40000


def test_review_reverse_conflicting_replay_is_rejected(tmp_path):
    s=S(tmp_path)
    s.create_claim(C())
    s.ingest_event(E())
    s.auto_allocate("e1",created_at="2026-09-02T11:00:00Z")
    s.ingest_counter(R(amt=10000))
    s.review_reverse(
        reversal_id="rr1",counter_id="r1",allocation_id="auto:e1:c1",
        amount_cents=10000,created_at="2026-09-03T12:00:00Z",
    )
    with pytest.raises(ValueError,match="replay conflicts"):
        s.review_reverse(
            reversal_id="rr1",counter_id="r1",allocation_id="auto:e1:c1",
            amount_cents=9999,created_at="2026-09-03T12:00:00Z",
        )


def test_review_reverse_rejects_wrong_event_allocation(tmp_path):
    s=S(tmp_path)
    s.create_claim(C("c1","I1",20000))
    s.create_claim(C("c2","I2",20000))
    s.ingest_event(E("e1","I1",20000))
    s.ingest_event(E("e2","I2",20000,booked="2026-09-02T10:01:00Z"))
    s.auto_allocate("e1",created_at=ALLOCATED_AT)
    s.auto_allocate("e2",created_at=ALLOCATED_AT)
    s.ingest_counter(R(original="e1",amt=10000))
    with pytest.raises(ValueError,match="does not fund allocation"):
        s.review_reverse(
            reversal_id="rr1",counter_id="r1",allocation_id="auto:e2:c2",
            amount_cents=10000,created_at="2026-09-03T12:00:00Z",
        )


def test_review_reverse_enforces_allocation_and_counter_capacity(tmp_path):
    s=S(tmp_path)
    s.create_claim(C())
    s.ingest_event(E())
    s.auto_allocate("e1",created_at=ALLOCATED_AT)
    s.ingest_counter(R(amt=15000))
    with pytest.raises(ValueError,match="counter event capacity exceeded"):
        s.review_reverse(
            reversal_id="too-much-counter",counter_id="r1",allocation_id="auto:e1:c1",
            amount_cents=15001,created_at="2026-09-03T12:00:00Z",
        )
    assert s.review_reverse(
        reversal_id="rr1",counter_id="r1",allocation_id="auto:e1:c1",
        amount_cents=10000,created_at="2026-09-03T12:00:00Z",
    )==REVERSED
    with pytest.raises(ValueError,match="counter event capacity exceeded"):
        s.review_reverse(
            reversal_id="rr2",counter_id="r1",allocation_id="auto:e1:c1",
            amount_cents=6000,created_at="2026-09-03T12:01:00Z",
        )

    s.ingest_counter(R(rid="r2",amt=50000))
    with pytest.raises(ValueError,match="allocation reversal capacity exceeded"):
        s.review_reverse(
            reversal_id="rr3",counter_id="r2",allocation_id="auto:e1:c1",
            amount_cents=40001,created_at="2026-09-03T12:02:00Z",
        )


@pytest.mark.parametrize("amount", [100.5, "100", True, 0, -1, 2**63])
def test_review_reverse_requires_exact_positive_integer_cents(tmp_path, amount):
    s=S(tmp_path)
    s.create_claim(C())
    s.ingest_event(E())
    s.auto_allocate("e1",created_at=ALLOCATED_AT)
    s.ingest_counter(R(amt=10000))
    with pytest.raises(ValueError,match="positive integer cents"):
        s.review_reverse(
            reversal_id="rr1",counter_id="r1",allocation_id="auto:e1:c1",
            amount_cents=amount,created_at="2026-09-03T12:00:00Z",
        )


@pytest.mark.parametrize("timestamp", ["2026-09-03T12:00:00","not-a-time",""])
def test_review_reverse_requires_timezone_aware_timestamp(tmp_path, timestamp):
    s=S(tmp_path)
    s.create_claim(C())
    s.ingest_event(E())
    s.auto_allocate("e1",created_at=ALLOCATED_AT)
    s.ingest_counter(R(amt=10000))
    with pytest.raises(ValueError,match="timezone-aware|required"):
        s.review_reverse(
            reversal_id="rr1",counter_id="r1",allocation_id="auto:e1:c1",
            amount_cents=10000,created_at=timestamp,
        )


@pytest.mark.parametrize("timeout", [True, False, 0, -1, 60_001, "5000", 5.5])
def test_busy_timeout_rejects_non_integer_or_unsafe_values(tmp_path, timeout):
    with pytest.raises(ValueError, match="busy_timeout_ms"):
        SettlementStore(
            tmp_path / "timeout.sqlite3",
            buyer_id="buyer",
            business_unit="unit",
            busy_timeout_ms=timeout,
        )


@pytest.mark.parametrize("kind", ["claim", "settlement", "counter"])
def test_source_evidence_requires_sha256(tmp_path, kind):
    s=S(tmp_path)
    if kind == "claim":
        record=RecoveryClaim(
            "bad","INV","carrier","buyer","USD",1,
            "2026-09-01T10:00:00Z","not-a-hash",
        )
        operation=lambda: s.create_claim(record)
    elif kind == "settlement":
        record=SettlementEventRecord(
            "bad","INV","carrier","buyer","USD",1,
            "2026-09-02T10:00:00Z","not-a-hash",
        )
        operation=lambda: s.ingest_event(record)
    else:
        s.ingest_event(E())
        record=CounterEventRecord(
            "bad","e1","USD",1,"2026-09-03T10:00:00Z","not-a-hash",
        )
        operation=lambda: s.ingest_counter(record)
    with pytest.raises(ValueError,match="SHA-256"):
        operation()


@pytest.mark.parametrize("bad", ["not-a-time", "2026-09-02T11:00:00", ""])
def test_all_allocation_and_reversal_paths_require_timestamps(tmp_path, bad):
    s=S(tmp_path)
    s.create_claim(C())
    s.ingest_event(E())
    with pytest.raises(ValueError,match="timezone-aware|required"):
        s.auto_allocate("e1",created_at=bad)
    with pytest.raises(ValueError,match="timezone-aware|required"):
        s.review_allocate(
            allocation_id="a1",claim_id="c1",event_id="e1",
            amount_cents=50000,created_at=bad,
        )
    s.auto_allocate("e1",created_at=ALLOCATED_AT)
    s.ingest_counter(R())
    with pytest.raises(ValueError,match="timezone-aware|required"):
        s.auto_apply_counter("r1",created_at=bad)


def test_allocation_and_reversal_chronology_fails_closed(tmp_path):
    s=S(tmp_path)
    s.create_claim(C())
    s.ingest_event(E())
    with pytest.raises(ValueError,match="predate settlement"):
        s.auto_allocate("e1",created_at="2026-09-02T09:59:59Z")
    with pytest.raises(ValueError,match="predate settlement"):
        s.review_allocate(
            allocation_id="a1",claim_id="c1",event_id="e1",
            amount_cents=50000,created_at="2026-09-02T09:59:59Z",
        )
    s.auto_allocate("e1",created_at=ALLOCATED_AT)
    s.ingest_counter(R())
    with pytest.raises(ValueError,match="predate counter"):
        s.auto_apply_counter("r1",created_at="2026-09-03T09:59:59Z")


def test_sql_triggers_enforce_canonical_time_and_chronology(tmp_path):
    s=S(tmp_path)
    s.create_claim(C())
    s.ingest_event(E())
    conn=sqlite3.connect(s.path)
    conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(sqlite3.IntegrityError,match="predates settlement"):
        conn.execute("""INSERT INTO allocations
          (buyer_id,business_unit,allocation_id,claim_id,event_id,amount_cents,mode,fee_eligible_cents,created_at)
          VALUES('TEST_BUYER','TEST_BU','early','c1','e1',50000,'REVIEW',50000,'2026-09-02T09:59:59.000000Z')""")
    with pytest.raises(sqlite3.IntegrityError,match="canonical UTC"):
        conn.execute("""INSERT INTO allocations
          (buyer_id,business_unit,allocation_id,claim_id,event_id,amount_cents,mode,fee_eligible_cents,created_at)
          VALUES('TEST_BUYER','TEST_BU','bad-time','c1','e1',50000,'REVIEW',50000,'x')""")
    with pytest.raises(sqlite3.IntegrityError,match="canonical UTC"):
        conn.execute("""INSERT INTO review_claims
          (buyer_id,business_unit,claim_id,flagged_at)
          VALUES('TEST_BUYER','TEST_BU','c1','x')""")
    with pytest.raises(sqlite3.IntegrityError,match="canonical UTC"):
        conn.execute("""INSERT INTO settlement_events
          (buyer_id,business_unit,event_id,reference,payer_id,payee_id,currency,
           amount_cents,booked_at,source_hash,source_kind)
          VALUES('TEST_BUYER','TEST_BU','bad-calendar','INV-1','carrier','buyer',
           'USD',1,'2026-02-30T10:00:00.000000Z',?,'DIRECT')""",
          (H("bad-calendar"),),
        )
    conn.close()


def test_reopen_rejects_broken_foreign_key_evidence(tmp_path):
    path=tmp_path/"orphan.sqlite3"
    SettlementStore(path,buyer_id="TEST_BUYER",business_unit="TEST_BU")
    conn=sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("""INSERT INTO review_claims
      (buyer_id,business_unit,claim_id,flagged_at)
      VALUES('TEST_BUYER','TEST_BU','missing','2026-09-02T10:00:00.000000Z')""")
    conn.commit()
    conn.close()
    with pytest.raises(RuntimeError,match="broken foreign-key evidence"):
        SettlementStore(path,buyer_id="TEST_BUYER",business_unit="TEST_BU")


def test_reopen_rejects_legacy_noncanonical_evidence(tmp_path):
    path=tmp_path/"legacy-invalid.sqlite3"
    s=SettlementStore(path,buyer_id="TEST_BUYER",business_unit="TEST_BU")
    s.create_claim(C())
    conn=sqlite3.connect(path)
    conn.execute("DROP TRIGGER settlement_input_guard")
    conn.execute("""INSERT INTO settlement_events
      (buyer_id,business_unit,event_id,reference,payer_id,payee_id,currency,amount_cents,booked_at,source_hash,source_kind)
      VALUES('TEST_BUYER','TEST_BU','legacy','INV-1','carrier','buyer','USD',1,
       '2026-02-30T10:00:00.000000Z',?,'LEGACY')""",
      (H("legacy-event"),),
    )
    conn.commit()
    conn.close()
    with pytest.raises(RuntimeError,match="noncanonical settlement_events"):
        SettlementStore(path,buyer_id="TEST_BUYER",business_unit="TEST_BU")
