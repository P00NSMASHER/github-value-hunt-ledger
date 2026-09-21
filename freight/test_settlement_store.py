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
def E(eid="e1", ref="INV-1", amt=50000, booked="2026-09-02T10:00:00Z", currency="USD"):
    return SettlementEventRecord(eid, ref, "carrier", "buyer", currency, amt, booked, f"settle-src-{eid}", "X12-820")
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
    assert s.auto_allocate("e1",created_at="x").status==REVIEW
    assert s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=60000,created_at="y")==ALLOCATED
    assert (s.realized_cents("c1"),s.claim_residual("c1"))==(60000,40000)


def test_03_duplicate_invoice_reference_is_ambiguous(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","INV-X",30000)); s.create_claim(C("c2","INV-X",30000)); s.ingest_event(E(ref="INV-X",amt=30000))
    d=s.auto_allocate("e1",created_at="x"); assert d.status==REVIEW and "count=2" in d.reason and s.realized_cents()==0


def test_04_preissue_event_stays_zero_later_event_can_settle(tmp_path):
    s=S(tmp_path); s.create_claim(C(amt=30000,issued="2026-09-05T10:00:00Z")); s.ingest_event(E("early",amt=30000,booked="2026-09-04T10:00:00Z"))
    assert s.auto_allocate("early",created_at="x").status==REVIEW
    s.ingest_event(E("late",amt=30000,booked="2026-09-06T10:00:00Z")); assert s.auto_allocate("late",created_at="x").status==ALLOCATED


def test_05_overpayment_preserves_event_residual(tmp_path):
    s=S(tmp_path); s.create_claim(C(amt=70000)); s.ingest_event(E(amt=75000)); assert s.auto_allocate("e1",created_at="x").status==REVIEW
    s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=70000,created_at="y")
    assert (s.realized_cents(),s.event_residual("e1"))==(70000,5000)


def test_06_orphan_is_review(tmp_path):
    s=S(tmp_path); s.create_claim(C(ref="OTHER",amt=30000)); s.ingest_event(E(ref="NONE",amt=30000)); assert s.auto_allocate("e1",created_at="x").status==REVIEW


def test_07_split_settlement_stays_review_only(tmp_path):
    s=S(tmp_path); s.create_claim(C(amt=90000)); s.ingest_event(E("e1",amt=40000)); s.ingest_event(E("e2",amt=50000))
    assert s.auto_allocate("e1",created_at="x").status==REVIEW
    s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=40000,created_at="y")
    assert s.auto_allocate("e2",created_at="z").status==REVIEW
    s.review_allocate(allocation_id="a2",claim_id="c1",event_id="e2",amount_cents=50000,created_at="z"); assert s.realized_cents()==90000


def test_08_duplicate_settlement_replay_is_idempotent(tmp_path):
    s=S(tmp_path); s.create_claim(C()); e=E(); assert s.ingest_event(e) and not s.ingest_event(e)
    assert s.auto_allocate("e1",created_at="x").status==ALLOCATED and s.auto_allocate("e1",created_at="x").status==ALREADY_ALLOCATED
    assert s.count("settlement_events")==1 and s.count("allocations")==1


def test_09_full_return_claws_back_and_only_claim_reopens(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E()); s.auto_allocate("e1",created_at="x"); s.ingest_counter(R())
    assert s.auto_apply_counter("r1",created_at="y").status==REVERSED
    assert (s.realized_cents(),s.claim_residual("c1"),s.event_residual("e1"))==(0,50000,0)
    s.ingest_event(E("e2",booked="2026-09-04T10:00:00Z")); assert s.auto_allocate("e2",created_at="z").status==ALLOCATED


def test_10_duplicate_return_is_idempotent(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E()); s.auto_allocate("e1",created_at="x"); r=R(); assert s.ingest_counter(r) and not s.ingest_counter(r)
    assert s.auto_apply_counter("r1",created_at="y").status==REVERSED and s.auto_apply_counter("r1",created_at="y").status==ALREADY_REVERSED
    assert s.count("reversal_edges")==1 and s.realized_cents()==0


def test_11_partial_return_across_two_edges_is_review(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","I1",30000)); s.create_claim(C("c2","I2",20000)); s.ingest_event(E(ref="BATCH",amt=50000))
    s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=30000,created_at="x"); s.review_allocate(allocation_id="a2",claim_id="c2",event_id="e1",amount_cents=20000,created_at="x")
    s.ingest_counter(R(amt=10000)); assert s.auto_apply_counter("r1",created_at="y").status==REVIEW and s.realized_cents()==50000


def test_12_second_payment_after_satisfied_claim_is_review(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E("e1")); s.ingest_event(E("e2",booked="2026-09-03T10:00:00Z")); s.auto_allocate("e1",created_at="x")
    assert s.auto_allocate("e2",created_at="y").status==REVIEW and s.realized_cents()==50000


def test_13_same_event_cannot_be_consumed_twice(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","I1")); s.create_claim(C("c2","I2")); s.ingest_event(E(ref="BATCH")); s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at="x")
    with pytest.raises(ValueError,match="settlement event capacity exceeded"): s.review_allocate(allocation_id="a2",claim_id="c2",event_id="e1",amount_cents=1,created_at="y")


def test_14_wrong_currency_never_realizes(tmp_path):
    s=S(tmp_path); s.create_claim(C(currency="USD")); s.ingest_event(E(currency="EUR")); assert s.auto_allocate("e1",created_at="x").status==REVIEW
    with pytest.raises(ValueError,match="currency mismatch"): s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at="y")


def test_15_review_path_rejects_preissue_settlement(tmp_path):
    s=S(tmp_path); s.create_claim(C(issued="2026-09-05T10:00:00Z")); s.ingest_event(E(booked="2026-09-04T10:00:00Z")); assert s.auto_allocate("e1",created_at="x").status==REVIEW
    with pytest.raises(ValueError,match="predates issued claim"): s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at="y")


def test_fee_eligibility_tracks_active_edge_and_disqualification(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E()); s.auto_allocate("e1",created_at="x"); assert s.fee_eligible_cents()==50000
    s.ingest_counter(R()); s.auto_apply_counter("r1",created_at="y"); assert s.fee_eligible_cents()==0
    s2=SettlementStore(tmp_path/"d2.sqlite3", buyer_id="TEST_BUYER", business_unit="TEST_BU"); s2.create_claim(C(disq=True)); s2.ingest_event(E()); s2.auto_allocate("e1",created_at="x"); assert s2.realized_cents()==50000 and s2.fee_eligible_cents()==0


def test_concurrent_duplicate_ingest_and_auto_allocate_once(tmp_path):
    s=S(tmp_path); s.create_claim(C()); e=E()
    def w(_): s.ingest_event(e); return s.auto_allocate("e1",created_at="x").status
    with ThreadPoolExecutor(max_workers=8) as p: states=list(p.map(w,range(16)))
    assert states.count(ALLOCATED)==1 and set(states)<={ALLOCATED,ALREADY_ALLOCATED}; assert s.count("allocations")==1 and s.realized_cents()==50000


def test_concurrent_two_events_cannot_overconsume_claim(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E("e1")); s.ingest_event(E("e2",booked="2026-09-02T10:00:01Z"))
    with ThreadPoolExecutor(max_workers=2) as p: states=list(p.map(lambda eid:s.auto_allocate(eid,created_at="x").status,["e1","e2"]))
    assert states.count(ALLOCATED)==1 and states.count(REVIEW)==1 and s.realized_cents()==50000 and s.count("allocations")==1


def test_concurrent_review_edges_cannot_overconsume_event(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","I1")); s.create_claim(C("c2","I2")); s.ingest_event(E(ref="BATCH"))
    def w(pair):
        try: return s.review_allocate(allocation_id=pair[0],claim_id=pair[1],event_id="e1",amount_cents=50000,created_at="x")
        except (ValueError,sqlite3.IntegrityError) as exc: return str(exc)
    with ThreadPoolExecutor(max_workers=2) as p: out=list(p.map(w,[("a1","c1"),("a2","c2")]))
    assert out.count(ALLOCATED)==1 and s.count("allocations")==1 and s.realized_cents()==50000


def test_concurrent_duplicate_counter_reverses_once(tmp_path):
    s=S(tmp_path); s.create_claim(C()); s.ingest_event(E()); s.auto_allocate("e1",created_at="x"); r=R()
    def w(_): s.ingest_counter(r); return s.auto_apply_counter("r1",created_at="y").status
    with ThreadPoolExecutor(max_workers=8) as p: states=list(p.map(w,range(16)))
    assert states.count(REVERSED)==1 and set(states)<={REVERSED,ALREADY_REVERSED}; assert s.count("reversal_edges")==1 and s.realized_cents()==0


def test_sql_triggers_block_direct_overconsume_and_mutation(tmp_path):
    s=S(tmp_path); s.create_claim(C("c1","I1")); s.create_claim(C("c2","I2")); s.ingest_event(E(ref="BATCH")); s.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at="x")
    conn=sqlite3.connect(s.path); conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(sqlite3.IntegrityError,match="settlement event capacity exceeded"):
        conn.execute("""INSERT INTO allocations
          (buyer_id,business_unit,allocation_id,claim_id,event_id,amount_cents,mode,fee_eligible_cents,created_at)
          VALUES('TEST_BUYER','TEST_BU','bypass','c2','e1',1,'REVIEW',1,'x')""")
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
    assert a.auto_allocate("e1",created_at="x").status==ALLOCATED
    assert b.auto_allocate("e1",created_at="x").status==ALLOCATED
    assert a.realized_cents()==50000 and b.realized_cents()==50000
    assert a.count("allocations")==1 and b.count("allocations")==1


def test_cross_tenant_event_cannot_match_other_tenant_claim(tmp_path):
    path=tmp_path/"shared.sqlite3"
    a=SettlementStore(path,buyer_id="BUYER-A",business_unit="OPS")
    b=SettlementStore(path,buyer_id="BUYER-B",business_unit="OPS")
    a.create_claim(C())
    b.ingest_event(E())
    d=b.auto_allocate("e1",created_at="x")
    assert d.status==REVIEW and "count=0" in d.reason
    assert a.realized_cents()==0 and b.realized_cents()==0
    with pytest.raises(ValueError,match="existing claim and settlement event"):
        b.review_allocate(allocation_id="a1",claim_id="c1",event_id="e1",amount_cents=50000,created_at="x")


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
          VALUES('BUYER-B','OPS','x','c1','e1',50000,'REVIEW',50000,'x')""")
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
