"""Independent RT05 second-wave financial-integrity red-team matrix.

Varies credit chronology, multiple disputes, stale reports, tenant collisions,
immutable SQL triggers, forged reviewer labels and concurrent intake races.
All identities, contracts, amounts, receipts and customers are synthetic.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from threading import Barrier
import json
import sqlite3

import pytest

from freight.currency_reporting import build_currency_settlement_report
from freight.recovery_resilience import (
    RecoveryScenario, RecoveryEvent, CustomerRequest,
    record_recovery_dispute_notice, evaluate_recovery_scenario,
)
from freight.settlement_store import (
    SettlementStore, RecoveryClaim, SettlementEventRecord,
    ALLOCATED, REVIEW,
)


def H(s: str) -> str:
    return sha256(s.encode("ascii")).hexdigest()


def setup(tmp_path, index, *, amount, held_reason, post_credited):
    db=SettlementStore(tmp_path / f"hold-{index}.sqlite3",
                       buyer_id=f"SYN-BUYER-{index}",business_unit="SYN-UNIT")
    reference=f"SYN-I-{index}"
    original_hash=H("origin:"+str(index))
    finding_hash=H("finding:"+str(index))
    claim_id=f"SYN-C-{index}"
    db.create_claim(RecoveryClaim(
        claim_id,reference,"SYN-CARRIER",f"SYN-BUYER-{index}",
        "USD",amount,"2026-09-01T10:00:00Z",finding_hash,
        index%17==0,
    ))
    sc=RecoveryScenario(
        case_id=reference,buyer_id=f"SYN-BUYER-{index}",business_unit="SYN-UNIT",
        claim_id=claim_id,payer_id="SYN-CARRIER",payee_id=f"SYN-BUYER-{index}",
        currency="USD",disputed_cents=amount,
        issued_at="2026-09-01T10:00:00.000000Z",
        source_invoice_sha256=original_hash,source_finding_sha256=finding_hash,
    )
    if post_credited:
        db.ingest_event(SettlementEventRecord(
            f"SYN-E-{index}",reference,"SYN-CARRIER",f"SYN-BUYER-{index}",
            "USD",amount,"2026-09-02T10:00:00Z",H("credit:"+str(index)),
            "SYNTHETIC_CREDIT_NOT_BANK_CLEARED",
        ))
        assert db.auto_allocate(f"SYN-E-{index}",created_at="2026-09-02T11:00:00Z").status==ALLOCATED
    evt=RecoveryEvent(
        event_id=f"SYN-NOTICE-{index}",kind=held_reason,
        observed_at="2026-09-03T12:00:00Z",
        source_sha256=H("separate-claim-notice:"+str(index)),
    )
    assert record_recovery_dispute_notice(db,scenario=sc,notice=evt) is True
    return db,sc,evt


@pytest.mark.parametrize("i",list(range(120)))
def test_matrix_120_complex_source_dispute_and_credit_chronologies(tmp_path,i):
    kinds=(
        "CARRIER_DENIAL","CARRIER_DISPUTE","CUSTOMER_DISPUTE",
        "CUSTOMER_WITHDRAWAL","INSOLVENCY_NOTICE",
        "CARRIER_OUT_OF_BUSINESS","CLAIM_TIME_BAR_CONCERN",
    )
    amount=10000+i*37
    post_credited=i%2==0
    store,sc,evt=setup(tmp_path,i,amount=amount,held_reason=kinds[i%len(kinds)],
                       post_credited=post_credited)
    if not post_credited:
        store.ingest_event(SettlementEventRecord(
            f"SYN-E-{i}",sc.case_id,sc.payer_id,sc.payee_id,
            "USD",amount,"2026-09-02T10:00:00Z",H("credit:"+str(i)),
            "SYNTHETIC_SOURCE_NOT_BANK_CLEARED",
        ))
        assert store.auto_allocate(f"SYN-E-{i}",
                                   created_at="2026-09-03T13:00:00Z").status==REVIEW
        with pytest.raises(ValueError,match="dispute"):
            store.review_allocate(
                allocation_id=f"SYN-A-{i}",claim_id=sc.claim_id,
                event_id=f"SYN-E-{i}",amount_cents=amount,
                created_at="2026-09-03T13:00:00Z",
            )
    assert store.fee_eligible_cents()==0
    assert store.fee_eligible_cents(sc.claim_id)==0
    assert store.realized_cents()==(amount if post_credited else 0)
    assert store.count("claim_dispute_holds")==1
    assert store.count("settlement_events")==1
    result=evaluate_recovery_scenario(
        sc,as_of="2026-10-22",store=store,
        customer_requests=(CustomerRequest(
            request_id="SYN-REQUEST",kind="GUARANTEED_RECOVERY",
            requested_at="2026-09-04T12:00:00Z",
            source_sha256=H("buyer-demand:"+str(i)),
        ),),
    )
    assert result.settlement.dispute_hold_active is True
    assert result.settlement.source_declared_candidate_fee_cents==0
    assert result.feasibility.no_billable_fee_authority
    assert result.customer_fee_billable_cents==0
    assert result.independently_verified_cash_cents==0
    assert result.payment_actions_performed==0
    assert result.carrier_contact_attempts==0
    assert "DURABLE_DISPUTE_HOLD_FORBIDS_VALIDATED_RECOVERY_AND_FEE" in result.blockers
    report=build_currency_settlement_report(store)
    row=report.by_currency[0]
    assert row.declared_net_allocated_cents==(amount if post_credited else 0)
    assert row.declared_fee_eligible_net_cents==0
    assert not report.external_settlement_verified


def test_fifty_competing_hold_vs_auto_allocate_threads_preserve_fee_quarantine(tmp_path):
    for i in range(50):
        path=tmp_path/f"race-{i}"
        path.mkdir()
        db=SettlementStore(path/"recovery.sqlite3",
                           buyer_id="SYN-B",business_unit="SYN-UNIT")
        id=f"CLAIM-{i}"
        db.create_claim(RecoveryClaim(
            id,f"REF-{i}","SYN-CARRIER","SYN-PAYEE","USD",5000+i,
            "2026-09-01T10:00:00Z",H("claim:"+str(i)),False,
        ))
        db.ingest_event(SettlementEventRecord(
            f"EVENT-{i}",f"REF-{i}","SYN-CARRIER","SYN-PAYEE","USD",5000+i,
            "2026-09-02T10:00:00Z",H("event:"+str(i)),"SYNTHETIC",
        ))
        barrier=Barrier(2)
        def allocate():
            barrier.wait(timeout=10)
            return db.auto_allocate(f"EVENT-{i}",
                                    created_at="2026-09-03T13:00:00Z")
        def hold():
            barrier.wait(timeout=10)
            return db.place_claim_dispute_hold(
                claim_id=id,kind="CARRIER_DENIAL",
                source_hash=H("denial:"+str(i)),
                observed_at="2026-09-03T12:00:00Z",
                expected_claim_source_sha256=H("claim:"+str(i)),
            )
        with ThreadPoolExecutor(max_workers=2) as ex:
            a=ex.submit(allocate)
            b=ex.submit(hold)
            admission=a.result()
            assert b.result() is True
        assert admission.status in (ALLOCATED,REVIEW)
        assert db.dispute_hold_active(id)
        assert db.fee_eligible_cents()==0
        row=build_currency_settlement_report(db).by_currency[0]
        assert row.declared_fee_eligible_net_cents==0
        assert row.declared_net_allocated_cents in (0,5000+i)
        assert db.count("settlement_events")==1


def test_immutable_hold_source_cannot_be_deleted_or_modified_in_sql(tmp_path):
    db,sc,evt=setup(tmp_path,999,amount=10000,held_reason="CARRIER_DISPUTE",
                    post_credited=True)
    with sqlite3.connect(db.path) as conn:
        with pytest.raises(sqlite3.IntegrityError,match="immutable"):
            conn.execute(
                "UPDATE claim_dispute_holds SET kind='CUSTOMER_DISPUTE' "
                "WHERE buyer_id=? AND business_unit=?",
                (db.buyer_id,db.business_unit),
            )
        with pytest.raises(sqlite3.IntegrityError,match="immutable"):
            conn.execute(
                "DELETE FROM claim_dispute_holds WHERE buyer_id=? AND business_unit=?",
                (db.buyer_id,db.business_unit),
            )
    assert db.dispute_hold_active(sc.claim_id)
    assert db.fee_eligible_cents()==0


def test_duplicate_conflicting_notice_cannot_mint_release_or_billable_fee(tmp_path):
    db,sc,evt=setup(tmp_path,201,amount=17000,held_reason="CARRIER_DENIAL",
                    post_credited=True)
    original=db.report_snapshot_json()
    assert record_recovery_dispute_notice(db,scenario=sc,notice=evt) is False
    assert db.report_snapshot_json()==original
    changed=replace(evt,kind="CUSTOMER_DISPUTE")
    with pytest.raises(ValueError,match="source"):
        record_recovery_dispute_notice(db,scenario=sc,notice=changed)
    assert not hasattr(db,"release_claim_dispute_hold")
    assert db.fee_eligible_cents()==0


def test_foreign_scope_and_reforged_dispute_cannot_quarantine_other_customer(tmp_path):
    db,sc,evt=setup(tmp_path,301,amount=18000,held_reason="CARRIER_DISPUTE",
                    post_credited=True)
    changed=replace(sc,business_unit="OTHER-UNIT")
    with pytest.raises(ValueError,match="scope"):
        record_recovery_dispute_notice(db,scenario=changed,notice=evt)
    changed=replace(sc,claim_id="OTHER-CLAIM")
    with pytest.raises(ValueError,match="unknown"):
        record_recovery_dispute_notice(db,scenario=changed,
          notice=replace(evt,source_sha256=H("independent-other")))
    assert db.count("claim_dispute_holds")==1
    assert db.fee_eligible_cents()==0


def test_dispute_registered_after_already_credited_claim_invalidates_fee_snapshot(tmp_path):
    db,sc,evt=setup(tmp_path,402,amount=12500,held_reason="INSOLVENCY_NOTICE",
                    post_credited=True)
    data=json.loads(db.report_snapshot_json())
    assert data["tables"]["claim_dispute_holds"][0]["claim_id"]==sc.claim_id
    assert len(data["tables"]["allocations"])==1
    assert data["tables"]["allocations"][0]["fee_eligible_cents"]==12500
    # The immutable historical allocation row isn't edited. Live/current
    # fee eligibility derives to zero from the appended hold source.
    assert db.fee_eligible_cents()==0
    result=evaluate_recovery_scenario(sc,as_of="2026-10-22",store=db)
    assert result.state=="DISPUTED_EVIDENCE_HOLD"
    assert result.settlement.source_declared_net_cents==12500
    assert result.settlement.source_declared_candidate_fee_cents==0
