from concurrent.futures import ThreadPoolExecutor
import sqlite3
import pytest

from freight.settlement_store import (
    ALLOCATED, ALREADY_ALLOCATED, ALREADY_REVERSED, REVIEW, REVERSED,
    CounterEventRecord, RecoveryClaim, SettlementEventRecord, SettlementStore,
)


def S(tmp_path, *, buyer_id="TEST_BUYER", business_unit="TEST_BU"):
    return SettlementStore(tmp_path / "settlement.sqlite3", buyer_id=buyer_id, business_unit=business_unit)

def C(cid="c1", ref="INV-1", amt=50000, issued="2026-09-01T10:00:00Z", currency="USD", disq=False):
    return RecoveryClaim(cid, ref, "carrier", "buyer", currency, amt, issued, f"claim-src-{cid}", disq)
def E(eid="e1", ref="INV-1", amt=50000, booked="2026-09-02T10:00:00Z", currency="USD", payer="carrier", payee="buyer"):
    return SettlementEventRecord(eid, ref, payer, payee, currency, amt, booked, f"settle-src-{eid}", "X12-820")
def R(rid="r1", original="e1", amt=50000, currency="USD"):
    return CounterEventRecord(rid, original, currency, amt, "2026-09-03T10:00:00Z", f"return-src-{rid}", "BANK-RETURN")


def test_01_multi_rmr_invoice_grain(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","INV-1",15000)); s.create_claim(C("c2","INV-2",20000))
    s.ingest_event(E("e1","INV-1",15000)); s.ingest_event(E("e2","INV-2",20000))
    assert s.auto_allocate("e1",created_at="2026-09-02T11:00:00Z").status==ALLOCATED
    assert s.auto_allocate("e2",created_at="2026-09-02T11:00:00Z").status==ALLOCATED
    assert s.realized_cents()==35000


def test_02_partial_payment_is_reviewed(tmp_path):
    s=S(tmp_path); s.create_claim(C(amt=100000)); s.ingest_event(E(amt=60000))
    assert s.auto_allocate("e1",created_at="2026-10-01T10:00:00Z").status==REVIEW
    assert s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=60000,created_at="2026-10-01T10:01:00Z")==ALLOCATED
    assert (s.realized_cents("c1"),s.claim_residual("c1"))==(60000,40000)


def test_03_duplicate_invoice_reference_is_ambiguous(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","INV-X",30000)); s.create_claim(C("c2","INV-X",30000)); s.ingest_event(E(ref="INV-X",amt=30000))
    d=s.auto_allocate("e1",created_at="2026-10-01T10:00:00Z"); assert d.status==REVIEW and "count=2" in d.reason and s.realized_cents()==0


def test_04_preissue_event_stays_zero_later_event_can_settle(tmp_path):
    s=S(tmp_path); s.create_claim(C(amt=30000,issued="2026-09-05T10:00:00Z")); s.ingest_event(E("early",amt=30000,booked="2026-09-04T10:00:00Z"))
    assert s.auto_allocate("early",created_at="2026-10-01T10:00:00Z").status==REVIEW
    s.ingest_event(E("late",amt=30000,booked="2026-09-06T10:00:00Z")); assert s.auto_allocate("late",created_at="2026-10-01T10:00:00Z").status==ALLOCATED


def test_05_overpayment_preserves_event_residual(tmp_path):
    s=S(tmp_path); s.create_claim(C(amt=70000)); s.ingest_event(E(amt=75000)); assert s.auto_allocate("e1",created_at="2026-10-01T10:00:00Z").status==REVIEW
    s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=70000,created_at="2026-10-01T10:01:00Z")
    assert (s.realized_cents(),s.event_residual("e1"))==(70000,5000)


def test_06_orphan_is_review(tmp_path):
    s=S(tmp_path); s.create_claim(C(ref="OTHER",amt=30000)); s.ingest_event(E(ref="NONE",amt=30000)); assert s.auto_allocate("e1",created_at="2026-10-01T10:00:00Z").status==REVIEW


def test_07_split_settlement_stays_review_only(tmp_path):
    s=S(tmp_path); s.create_claim(C(amt=90000)); s.ingest_event(E("e1",amt=40000)); s.ingest_event(E("e2",amt=50000))
    assert s.auto_allocate("e1",created_at="2026-10-01T10:00:00Z").status==REVIEW
    s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=40000,created_at="2026-10-01T10:01:00Z")
    assert s.auto_allocate("e2",created_at="2026-10-01T10:02:00Z").status==REVIEW
    s.review_allocate(allocation_id="a2",claim_id="c1",event_id="e2",amount_cents=50000,created_at="2026-10-01T10:02:00Z"); assert s.realized_cents()==90000


def test_08_duplicate_settlement_replay_is_idempotent(tmp_path):
    s=S(tmp_path); s.create_claim(C()); e=E(); assert s.ingest_event(e) and not s.ingest_event(e)
    assert s.auto_allocate("e1",created_at="2026-10-01T10:00:00Z").status==ALLOCATED and s.auto_allocate("e1",created_at="2026-10-01T10:00:00Z").status==ALREADY_ALLOCATED
    assert s.count("settlement_events")==1 and s.count("allocations")==1


def test_09_full_return_claws_back_and_only_claim_reopens(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E()); s.auto_allocate("e1",created_at="2026-10-01T10:00:00Z"); s.ingest_counter(R())
    assert s.auto_apply_counter("r1",created_at="2026-10-01T10:01:00Z").status==REVERSED
    assert (s.realized_cents(),s.claim_residual("c1"),s.event_residual("e1"))==(0,50000,0)
    s.ingest_event(E("e2",booked="2026-09-04T10:00:00Z")); assert s.auto_allocate("e2",created_at="2026-10-01T10:02:00Z").status==ALLOCATED


def test_10_duplicate_return_is_idempotent(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E()); s.auto_allocate("e1",created_at="2026-10-01T10:00:00Z"); r=R(); assert s.ingest_counter(r) and not s.ingest_counter(r)
    assert s.auto_apply_counter("r1",created_at="2026-10-01T10:01:00Z").status==REVERSED and s.auto_apply_counter("r1",created_at="2026-10-01T10:01:00Z").status==ALREADY_REVERSED
    assert s.count("reversal_edges")==1 and s.realized_cents()==0


def test_11_partial_return_across_two_edges_is_review(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","I1",30000)); s.create_claim(C("c2","I2",20000)); s.ingest_event(E(ref="BATCH",amt=50000))
    s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=30000,created_at="2026-10-01T10:00:00Z"); s.review_allocate(allocation_id="a2",claim_id="c2",event_id="e1",amount_cents=20000,created_at="2026-10-01T10:00:00Z")
    s.ingest_counter(R(amt=10000)); assert s.auto_apply_counter("r1",created_at="2026-10-01T10:01:00Z").status==REVIEW and s.realized_cents()==50000


def test_12_second_payment_after_satisfied_claim_is_review(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E("e1")); s.ingest_event(E("e2",booked="2026-09-03T10:00:00Z")); s.auto_allocate("e1",created_at="2026-10-01T10:00:00Z")
    assert s.auto_allocate("e2",created_at="2026-10-01T10:01:00Z").status==REVIEW and s.realized_cents()==50000


def test_13_same_event_cannot_be_consumed_twice(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","I1")); s.create_claim(C("c2","I2")); s.ingest_event(E(ref="BATCH")); s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at="2026-10-01T10:00:00Z")
    with pytest.raises(ValueError,match="settlement event capacity exceeded"): s.review_allocate(allocation_id="a2",claim_id="c2",event_id="e1",amount_cents=1,created_at="2026-10-01T10:01:00Z")


def test_14_wrong_currency_never_realizes(tmp_path):
    s=S(tmp_path); s.create_claim(C(currency="USD")); s.ingest_event(E(currency="EUR")); assert s.auto_allocate("e1",created_at="2026-10-01T10:00:00Z").status==REVIEW
    with pytest.raises(ValueError,match="currency mismatch"): s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at="2026-10-01T10:01:00Z")


def test_15_review_path_rejects_preissue_settlement(tmp_path):
    s=S(tmp_path); s.create_claim(C(issued="2026-09-05T10:00:00Z")); s.ingest_event(E(booked="2026-09-04T10:00:00Z")); assert s.auto_allocate("e1",created_at="2026-10-01T10:00:00Z").status==REVIEW
    with pytest.raises(ValueError,match="predates issued claim"): s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at="2026-10-01T10:01:00Z")


def test_16_review_path_rejects_counterparty_mismatch(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E(payer="other-carrier"))
    assert s.auto_allocate("e1",created_at="2026-10-01T10:00:00Z").status==REVIEW
    with pytest.raises(ValueError,match="payer/payee mismatch"):
        s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at="2026-10-01T10:01:00Z")
    assert s.realized_cents()==0


def test_17_timezone_offsets_are_normalized_before_ordering(tmp_path):
    s=S(tmp_path)
    s.create_claim(C(issued="2026-09-01T06:00:00-04:00"))
    s.ingest_event(E(booked="2026-09-01T09:59:59Z"))
    assert s.auto_allocate("e1",created_at="2026-10-01T10:00:00Z").status==REVIEW
    with pytest.raises(ValueError,match="predates issued claim"):
        s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at="2026-10-01T10:01:00Z")


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
          VALUES('TEST_BUYER','TEST_BU','a1','c1','e1',50000,'REVIEW',50000,'2026-09-02T11:00:00Z')""")
    conn.close()

    s2=SettlementStore(tmp_path/"review-lock.sqlite3", buyer_id="TEST_BUYER", business_unit="TEST_BU")
    s2.create_claim(C()); s2.ingest_event(E(amt=25000))
    s2.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=25000,created_at="2026-10-01T10:00:00Z")
    conn=sqlite3.connect(s2.path)
    with pytest.raises(sqlite3.IntegrityError,match="review claim is immutable"):
        conn.execute("DELETE FROM review_claims WHERE buyer_id='TEST_BUYER' AND business_unit='TEST_BU' AND claim_id='c1'")
    conn.close()


def test_fee_eligibility_tracks_active_edge_and_disqualification(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E()); s.auto_allocate("e1",created_at="2026-10-01T10:00:00Z"); assert s.fee_eligible_cents()==50000
    s.ingest_counter(R()); s.auto_apply_counter("r1",created_at="2026-10-01T10:01:00Z"); assert s.fee_eligible_cents()==0
    s2=SettlementStore(tmp_path/"d2.sqlite3", buyer_id="TEST_BUYER", business_unit="TEST_BU"); s2.create_claim(C(disq=True)); s2.ingest_event(E()); s2.auto_allocate("e1",created_at="2026-10-01T10:00:00Z"); assert s2.realized_cents()==50000 and s2.fee_eligible_cents()==0


def test_concurrent_duplicate_ingest_and_auto_allocate_once(tmp_path):
    s=S(tmp_path); s.create_claim(C()); e=E()
    def w(_): s.ingest_event(e); return s.auto_allocate("e1",created_at="2026-10-01T10:00:00Z").status
    with ThreadPoolExecutor(max_workers=8) as p: states=list(p.map(w,range(16)))
    assert states.count(ALLOCATED)==1 and set(states)<={ALLOCATED,ALREADY_ALLOCATED}; assert s.count("allocations")==1 and s.realized_cents()==50000


def test_concurrent_two_events_cannot_overconsume_claim(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E("e1")); s.ingest_event(E("e2",booked="2026-09-02T10:00:01Z"))
    with ThreadPoolExecutor(max_workers=2) as p: states=list(p.map(lambda eid:s.auto_allocate(eid,created_at="2026-10-01T10:00:00Z").status,["e1","e2"]))
    assert states.count(ALLOCATED)==1 and states.count(REVIEW)==1 and s.realized_cents()==50000 and s.count("allocations")==1


def test_concurrent_review_edges_cannot_overconsume_event(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","I1")); s.create_claim(C("c2","I2")); s.ingest_event(E(ref="BATCH"))
    def w(pair):
        try: return s.review_allocate(allocation_id=pair[0],claim_id=pair[1],event_id="e1",amount_cents=50000,created_at="2026-10-01T10:00:00Z")
        except (ValueError,sqlite3.IntegrityError) as exc: return str(exc)
    with ThreadPoolExecutor(max_workers=2) as p: out=list(p.map(w,[("a1","c1"),("a2","c2")]))
    assert out.count(ALLOCATED)==1 and s.count("allocations")==1 and s.realized_cents()==50000


def test_concurrent_duplicate_counter_reverses_once(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E()); s.auto_allocate("e1",created_at="2026-10-01T10:00:00Z"); r=R()
    def w(_): s.ingest_counter(r); return s.auto_apply_counter("r1",created_at="2026-10-01T10:01:00Z").status
    with ThreadPoolExecutor(max_workers=8) as p: states=list(p.map(w,range(16)))
    assert states.count(REVERSED)==1 and set(states)<={REVERSED,ALREADY_REVERSED}; assert s.count("reversal_edges")==1 and s.realized_cents()==0


def test_sql_triggers_block_direct_overconsume_and_mutation(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","I1")); s.create_claim(C("c2","I2")); s.ingest_event(E(ref="BATCH")); s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at="2026-10-01T10:00:00Z")
    conn=sqlite3.connect(s.path); conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(sqlite3.IntegrityError,match="settlement event capacity exceeded"):
        conn.execute("""INSERT INTO allocations
          (buyer_id,business_unit,allocation_id,claim_id,event_id,amount_cents,mode,fee_eligible_cents,created_at)
          VALUES('TEST_BUYER','TEST_BU','bypass','c2','e1',1,'REVIEW',1,'2026-09-02T11:00:00Z')""")
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
    assert a.auto_allocate("e1",created_at="2026-10-01T10:00:00Z").status==ALLOCATED
    assert b.auto_allocate("e1",created_at="2026-10-01T10:00:00Z").status==ALLOCATED
    assert a.realized_cents()==50000 and b.realized_cents()==50000
    assert a.count("allocations")==1 and b.count("allocations")==1


def test_cross_tenant_event_cannot_match_other_tenant_claim(tmp_path):
    path=tmp_path/"shared.sqlite3"
    a=SettlementStore(path,buyer_id="BUYER-A",business_unit="OPS")
    b=SettlementStore(path,buyer_id="BUYER-B",business_unit="OPS")
    a.create_claim(C())
    b.ingest_event(E())
    d=b.auto_allocate("e1",created_at="2026-10-01T10:00:00Z")
    assert d.status==REVIEW and "count=0" in d.reason
    assert a.realized_cents()==0 and b.realized_cents()==0
    with pytest.raises(ValueError,match="existing claim and settlement event"):
        b.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at="2026-10-01T10:00:00Z")


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
          VALUES('BUYER-B','OPS','x','c1','e1',50000,'REVIEW',50000,'2026-09-02T11:00:00Z')""")
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
    s.auto_allocate("e1",created_at="2026-09-02T11:00:00Z")
    s.auto_allocate("e2",created_at="2026-09-02T11:00:00Z")
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
    s.auto_allocate("e1",created_at="2026-09-02T11:00:00Z")
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
    s.auto_allocate("e1",created_at="2026-09-02T11:00:00Z")
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
    s.auto_allocate("e1",created_at="2026-09-02T11:00:00Z")
    s.ingest_counter(R(amt=10000))
    with pytest.raises(ValueError,match="timezone-aware|required"):
        s.review_reverse(
            reversal_id="rr1",counter_id="r1",allocation_id="auto:e1:c1",
            amount_cents=10000,created_at=timestamp,
        )


def test_allocation_created_at_requires_timezone_and_cannot_predate_settlement(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E())
    with pytest.raises(ValueError,match="timezone-aware"):
        s.auto_allocate("e1",created_at="2026-09-02T11:00:00")
    with pytest.raises(ValueError,match="cannot predate settlement booking"):
        s.auto_allocate("e1",created_at="2026-09-02T09:59:59Z")
    assert s.count("allocations")==0


def test_review_allocation_normalizes_equivalent_offset_and_replay(tmp_path):
    s=S(tmp_path); s.create_claim(C(amt=60000)); s.ingest_event(E(amt=50000))
    assert s.auto_allocate("e1",created_at="2026-09-02T11:00:00Z").status==REVIEW
    assert s.review_allocate(
        allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,
        created_at="2026-09-02T07:00:00-04:00",
    )==ALLOCATED
    assert s.review_allocate(
        allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,
        created_at="2026-09-02T11:00:00Z",
    )==ALREADY_ALLOCATED


def test_auto_reversal_created_at_cannot_predate_counter_or_allocation(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E())
    assert s.auto_allocate("e1",created_at="2026-09-04T12:00:00Z").status==ALLOCATED
    s.ingest_counter(R())
    with pytest.raises(ValueError,match="predate counter observation"):
        s.auto_apply_counter("r1",created_at="2026-09-03T09:59:59Z")
    with pytest.raises(ValueError,match="predate allocation"):
        s.auto_apply_counter("r1",created_at="2026-09-04T11:59:59Z")
    assert s.count("reversal_edges")==0


def test_review_reversal_created_at_cannot_predate_counter_or_allocation(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E())
    assert s.auto_allocate("e1",created_at="2026-09-04T12:00:00Z").status==ALLOCATED
    s.ingest_counter(R(amt=10000))
    with pytest.raises(ValueError,match="predate counter observation"):
        s.review_reverse(
            reversal_id="r-edge-1",counter_id="r1",allocation_id="auto:e1:c1",
            amount_cents=10000,created_at="2026-09-03T09:59:59Z",
        )
    with pytest.raises(ValueError,match="predate allocation"):
        s.review_reverse(
            reversal_id="r-edge-2",counter_id="r1",allocation_id="auto:e1:c1",
            amount_cents=10000,created_at="2026-09-04T11:59:59Z",
        )


def test_sql_triggers_reject_invalid_or_impossible_edge_timestamps(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E())
    conn=sqlite3.connect(s.path); conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(sqlite3.IntegrityError,match="valid UTC timestamp"):
        conn.execute("""INSERT INTO allocations
          (buyer_id,business_unit,allocation_id,claim_id,event_id,amount_cents,mode,fee_eligible_cents,created_at)
          VALUES('TEST_BUYER','TEST_BU','bad-time','c1','e1',50000,'AUTO',50000,'not-a-time')""")
    with pytest.raises(sqlite3.IntegrityError,match="predates settlement booking"):
        conn.execute("""INSERT INTO allocations
          (buyer_id,business_unit,allocation_id,claim_id,event_id,amount_cents,mode,fee_eligible_cents,created_at)
          VALUES('TEST_BUYER','TEST_BU','too-early','c1','e1',50000,'AUTO',50000,'2026-09-02T09:59:59Z')""")
    conn.close()


def test_sql_timestamp_guards_cover_claim_event_counter_and_reversal(tmp_path):
    s=S(tmp_path)
    conn=sqlite3.connect(s.path); conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(sqlite3.IntegrityError,match="claim issued_at"):
        conn.execute("""INSERT INTO recovery_claims
          (buyer_id,business_unit,claim_id,reference,payer_id,payee_id,currency,amount_cents,issued_at,source_hash,fee_disqualified)
          VALUES('TEST_BUYER','TEST_BU','bad-c','I','carrier','buyer','USD',1,'2026-09-01 10:00:00','bad-c-src',0)""")
    with pytest.raises(sqlite3.IntegrityError,match="settlement booked_at"):
        conn.execute("""INSERT INTO settlement_events
          (buyer_id,business_unit,event_id,reference,payer_id,payee_id,currency,amount_cents,booked_at,source_hash,source_kind)
          VALUES('TEST_BUYER','TEST_BU','bad-e','I','carrier','buyer','USD',1,'2026-09-02 10:00:00','bad-e-src','X12')""")
    conn.close()

    s.create_claim(C()); s.ingest_event(E())
    conn=sqlite3.connect(s.path); conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(sqlite3.IntegrityError,match="counter observed_at"):
        conn.execute("""INSERT INTO counter_events
          (buyer_id,business_unit,counter_id,original_event_id,currency,amount_cents,observed_at,source_hash,source_kind)
          VALUES('TEST_BUYER','TEST_BU','bad-counter','e1','USD',10000,'2026-09-03 10:00:00','bad-counter-src','RETURN')""")
    conn.close()

    assert s.auto_allocate("e1",created_at="2026-09-04T12:00:00Z").status==ALLOCATED
    s.ingest_counter(R(amt=10000))
    conn=sqlite3.connect(s.path); conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(sqlite3.IntegrityError,match="predates counter observation"):
        conn.execute("""INSERT INTO reversal_edges
          (buyer_id,business_unit,reversal_id,counter_id,allocation_id,amount_cents,created_at)
          VALUES('TEST_BUYER','TEST_BU','bad-r','r1','auto:e1:c1',10000,'2026-09-03T09:59:59Z')""")
    conn.close()


def test_sql_allocation_cannot_bind_preissue_event_to_later_claim(tmp_path):
    s=S(tmp_path)
    s.create_claim(C(issued="2026-09-05T10:00:00Z"))
    s.ingest_event(E(booked="2026-09-04T10:00:00Z"))
    conn=sqlite3.connect(s.path); conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(sqlite3.IntegrityError,match="predates issued claim"):
        conn.execute("""INSERT INTO allocations
          (buyer_id,business_unit,allocation_id,claim_id,event_id,amount_cents,mode,fee_eligible_cents,created_at)
          VALUES('TEST_BUYER','TEST_BU','bad-preissue','c1','e1',50000,'REVIEW',50000,'2026-09-06T10:00:00Z')""")
    conn.close()


def test_sql_counter_currency_cannot_poison_later_reversal(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E())
    assert s.auto_allocate("e1",created_at="2026-09-02T11:00:00Z").status==ALLOCATED
    conn=sqlite3.connect(s.path); conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(sqlite3.IntegrityError,match="counter currency mismatch"):
        conn.execute("""INSERT INTO counter_events
          (buyer_id,business_unit,counter_id,original_event_id,currency,amount_cents,observed_at,source_hash,source_kind)
          VALUES('TEST_BUYER','TEST_BU','bad-currency','e1','EUR',10000,'2026-09-03T10:00:00Z','bad-currency-src','RETURN')""")
    conn.close()


def test_review_claim_flag_timestamp_cannot_be_invalid_direct_sql(tmp_path):
    s=S(tmp_path); s.create_claim(C())
    conn=sqlite3.connect(s.path); conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(sqlite3.IntegrityError,match="review claim flagged_at"):
        conn.execute("""INSERT INTO review_claims
          (buyer_id,business_unit,claim_id,flagged_at)
          VALUES('TEST_BUYER','TEST_BU','c1','not-a-time')""")
    conn.close()


def test_atomic_evidence_package_rolls_back_earlier_writes_on_late_counter_failure(tmp_path):
    s=S(tmp_path); s.create_claim(C())
    event=E()
    bad_counter=CounterEventRecord(
        "bad-r","e1","EUR",10000,"2026-09-03T10:00:00Z",
        "bad-r-source","BANK-RETURN",
    )
    with pytest.raises(ValueError,match="counter currency mismatch"):
        s.process_evidence_package(
            settlement_events=(event,),
            counter_events=(bad_counter,),
            created_at="2026-09-03T11:00:00Z",
        )
    assert s.count("settlement_events")==0
    assert s.count("allocations")==0
    assert s.count("counter_events")==0
    assert s.count("reversal_edges")==0


def test_atomic_evidence_package_returns_before_and_after_snapshots_from_same_transaction(tmp_path):
    s=S(tmp_path); s.create_claim(C())
    out=s.process_evidence_package(
        settlement_events=(E(),),
        created_at="2026-09-02T11:00:00Z",
    )
    assert out.store_snapshot_before["tables"]["settlement_events"]==[]
    assert out.store_snapshot_before["tables"]["allocations"]==[]
    assert len(out.store_snapshot_after["tables"]["settlement_events"])==1
    assert len(out.store_snapshot_after["tables"]["allocations"])==1
    assert out.settlement_outcomes[0].created is True
    assert out.settlement_outcomes[0].decision.status==ALLOCATED


def test_atomic_package_rechecks_reviewed_settlement_after_counter_restores_capacity(tmp_path):
    s=S(tmp_path)
    s.create_claim(C())
    s.ingest_event(E(eid="old",ref="INV-1",amt=50000,booked="2026-09-02T10:00:00Z"))
    assert s.auto_allocate("old",created_at="2026-09-02T11:00:00Z").status==ALLOCATED
    new_event=E(
        eid="new",ref="INV-1",amt=50000,
        booked="2026-09-03T10:00:00Z",
    )
    counter=CounterEventRecord(
        "restore","old","USD",50000,"2026-09-04T10:00:00Z",
        "restore-source","BANK-RETURN",
    )
    out=s.process_evidence_package(
        settlement_events=(new_event,),
        counter_events=(counter,),
        created_at="2026-09-04T11:00:00Z",
    )
    assert out.settlement_outcomes[0].decision.status==ALLOCATED
    assert out.counter_outcomes[0].decision.status==REVERSED
    assert s.realized_cents()==50000
    assert s.event_residual("new")==0


def test_full_return_reserves_event_capacity_before_any_allocation(tmp_path):
    s=S(tmp_path)
    s.create_claim(C(amt=8000))
    s.ingest_event(E(amt=10000))
    s.ingest_counter(R(amt=10000))
    assert s.event_residual("e1") == 0
    with pytest.raises(ValueError, match="settlement event capacity exceeded"):
        s.review_allocate(
            allocation_id="late-a",
            claim_id="c1",
            event_id="e1",
            amount_cents=8000,
            created_at="2026-09-04T10:00:00Z",
        )
    assert s.realized_cents() == 0
    assert s.fee_eligible_cents() == 0


def test_full_return_after_partial_allocation_leaves_no_reusable_event_capacity(tmp_path):
    s=S(tmp_path)
    s.create_claim(C(amt=8000))
    s.ingest_event(E(amt=10000))
    s.review_allocate(
        allocation_id="a1",
        claim_id="c1",
        event_id="e1",
        amount_cents=8000,
        created_at="2026-09-02T11:00:00Z",
    )
    s.ingest_counter(R(amt=10000))
    assert s.auto_apply_counter(
        "r1", created_at="2026-09-03T11:00:00Z"
    ).status == REVERSED
    assert s.realized_cents() == 0
    assert s.event_residual("e1") == 0


def test_allocation_created_after_known_return_uses_only_net_event_capacity_and_is_not_reversed_twice(tmp_path):
    s=S(tmp_path)
    s.create_claim(C(amt=5000))
    s.ingest_event(E(amt=10000))
    s.ingest_counter(R(amt=5000))
    assert s.event_residual("e1") == 5000
    assert s.review_allocate(
        allocation_id="net-a",
        claim_id="c1",
        event_id="e1",
        amount_cents=5000,
        created_at="2026-09-04T10:00:00Z",
    ) == ALLOCATED
    assert s.event_residual("e1") == 0
    assert s.auto_apply_counter(
        "r1", created_at="2026-09-04T11:00:00Z"
    ).status == REVIEW
    with pytest.raises(ValueError, match="counter predates allocation"):
        s.review_reverse(
            reversal_id="double-return",
            counter_id="r1",
            allocation_id="net-a",
            amount_cents=5000,
            created_at="2026-09-04T11:00:00Z",
        )
    assert s.realized_cents() == 5000


def test_total_counter_evidence_cannot_exceed_original_settlement(tmp_path):
    s=S(tmp_path)
    s.ingest_event(E(amt=10000))
    s.ingest_counter(R(rid="r1", amt=6000))
    with pytest.raises(ValueError, match="exceed original settlement capacity"):
        s.ingest_counter(R(rid="r2", amt=5000))


def test_sql_allocation_capacity_reserves_unapplied_return_amount(tmp_path):
    s=S(tmp_path)
    s.create_claim(C(amt=8000))
    s.ingest_event(E(amt=10000))
    s.ingest_counter(R(amt=10000))
    conn=sqlite3.connect(s.path)
    conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(sqlite3.IntegrityError, match="settlement event capacity exceeded"):
        conn.execute("""INSERT INTO allocations
          (buyer_id,business_unit,allocation_id,claim_id,event_id,amount_cents,mode,fee_eligible_cents,created_at)
          VALUES('TEST_BUYER','TEST_BU','sql-late','c1','e1',8000,'REVIEW',8000,'2026-09-04T10:00:00Z')""")
    conn.close()


def test_sql_counter_capacity_cannot_exceed_original_settlement(tmp_path):
    s=S(tmp_path)
    s.ingest_event(E(amt=10000))
    conn=sqlite3.connect(s.path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("""INSERT INTO counter_events
      (buyer_id,business_unit,counter_id,original_event_id,currency,amount_cents,observed_at,source_hash,source_kind)
      VALUES('TEST_BUYER','TEST_BU','sql-r1','e1','USD',6000,'2026-09-03T10:00:00Z','sql-r1-src','RETURN')""")
    with pytest.raises(sqlite3.IntegrityError, match="exceed original settlement capacity"):
        conn.execute("""INSERT INTO counter_events
          (buyer_id,business_unit,counter_id,original_event_id,currency,amount_cents,observed_at,source_hash,source_kind)
          VALUES('TEST_BUYER','TEST_BU','sql-r2','e1','USD',5000,'2026-09-03T11:00:00Z','sql-r2-src','RETURN')""")
    conn.close()
