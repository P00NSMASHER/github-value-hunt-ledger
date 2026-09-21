from dataclasses import replace

import pytest

from freight.audit_workflow import RuleCSVInput, run_audit_workflow
from freight.buyer_review_workflow import BuyerReviewDecisionInput, build_buyer_review_batch
from freight.contracts import open_incumbent_output, seal_incumbent_submission
from freight.pilot_reporting import ReviewDisposition
from freight.recovery_claim_workflow import (
    build_recovery_claim_batch,
    persist_recovery_claim_batch,
)
from freight.reviewed_settlement_allocation import (
    build_reviewed_settlement_allocation_decision,
    persist_reviewed_settlement_allocation,
    render_reviewed_settlement_allocation_markdown,
)
from freight.settlement_csv_adapter import parse_settlement_event_csv
from freight.settlement_store import ALLOCATED, ALREADY_ALLOCATED, RecoveryClaim, SettlementEventRecord, SettlementStore


INVOICE_HEADER = "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,charge_code,service_date,quantity_units,billed_cents\n"
RULE_HEADER = "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"
SETTLEMENT_HEADER = "event_id,reference,payer_id,payee_id,currency,amount_cents,booked_at,source_kind\n"


def setup(tmp_path, *, event_reference="INV-1", event_payer="K", event_amount=2000):
    workflow = run_audit_workflow(
        invoice_filename="charges.csv",
        invoice_data=(INVOICE_HEADER+"INV-1,S1,C,K,USD,X1,A,2026-09-10,1,12500\n").encode(),
        buyer_id="buyer", business_unit="unit", selection_rule="period",
        rule_inputs=(
            RuleCSVInput("a.csv",(RULE_HEADER+"A,FIXED,2026-09-01,,10000,\n").encode(),
                         "C","K","USD","rate","a"*64,True),
        ),
    )
    artifacts=workflow.artifacts
    assert artifacts is not None
    case_hash=artifacts.review_routing.buyer_review_case_hashes[0]
    buyer_review=build_buyer_review_batch(
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        truth=artifacts.factory.truth,
        reviewer_role="Buyer Controller",
        decisions=(BuyerReviewDecisionInput(
            case_hash,ReviewDisposition.CONFIRMED,3,"2026-09-21T09:00:00Z"
        ),),
    )
    population=artifacts.population_build.population
    incumbent=open_incumbent_output(
        population=population,
        truth=artifacts.factory.truth,
        submission=seal_incumbent_submission(population,"incumbent"),
        finding_ids=(),
    )
    claim_batch=build_recovery_claim_batch(
        truth=artifacts.factory.truth,
        incumbent=incumbent,
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        buyer_review=buyer_review,
        issued_at="2026-09-21T09:30:00Z",
    )
    store=SettlementStore(tmp_path/"settlement.sqlite3",buyer_id="buyer",business_unit="unit")
    persist_recovery_claim_batch(store,claim_batch)
    settlement=parse_settlement_event_csv(
        filename="settlements.csv",
        data=(SETTLEMENT_HEADER+
              f"E1,{event_reference},{event_payer},C,USD,{event_amount},2026-09-21T10:00:00Z,CREDIT\n").encode(),
        buyer_id="buyer",business_unit="unit",
    )
    store.ingest_event(settlement.events[0])
    return artifacts,claim_batch,store,settlement.events[0]


def test_reviewed_allocation_is_bound_to_snapshot_claim_event_and_human_review(tmp_path):
    _,claims,store,event=setup(tmp_path)
    decision=build_reviewed_settlement_allocation_decision(
        store=store,
        claim_batch=claims,
        claim_id=claims.claims[0].claim_id,
        event_id=event.event_id,
        amount_cents=2000,
        reviewer_role="Settlement Analyst",
        reviewed_at="2026-09-21T11:00:00Z",
        reason="Partial carrier credit matched to the reviewed invoice.",
    )
    assert decision.event_source_hash==event.source_hash
    assert decision.finding_proof_hash==claims.records[0].finding_proof_hash
    assert decision.allocation_id=="review:"+decision.decision_hash
    assert len(decision.decision_hash)==64
    receipt=persist_reviewed_settlement_allocation(store,decision)
    assert receipt.status==ALLOCATED
    assert store.realized_cents()==2000
    assert store.count("allocations")==1
    assert len(receipt.receipt_hash)==64


def test_reviewed_allocation_replay_is_idempotent(tmp_path):
    _,claims,store,event=setup(tmp_path)
    decision=build_reviewed_settlement_allocation_decision(
        store=store,claim_batch=claims,claim_id=claims.claims[0].claim_id,
        event_id=event.event_id,amount_cents=2000,reviewer_role="Analyst",
        reviewed_at="2026-09-21T11:00:00Z",reason="Reviewed partial credit.",
    )
    first=persist_reviewed_settlement_allocation(store,decision)
    second=persist_reviewed_settlement_allocation(store,decision)
    assert first.status==ALLOCATED
    assert second.status==ALREADY_ALLOCATED
    assert store.count("allocations")==1
    assert store.realized_cents()==2000


def test_stale_review_decision_cannot_apply_after_snapshot_changes(tmp_path):
    _,claims,store,event=setup(tmp_path)
    decision=build_reviewed_settlement_allocation_decision(
        store=store,claim_batch=claims,claim_id=claims.claims[0].claim_id,
        event_id=event.event_id,amount_cents=2000,reviewer_role="Analyst",
        reviewed_at="2026-09-21T11:00:00Z",reason="Reviewed partial credit.",
    )
    store.ingest_event(SettlementEventRecord(
        "E2","OTHER","K","C","USD",100,"2026-09-21T10:30:00Z","other-event","CREDIT"
    ))
    with pytest.raises(ValueError,match="snapshot changed"):
        persist_reviewed_settlement_allocation(store,decision)
    assert store.count("allocations")==0


def test_tampered_decision_is_rejected(tmp_path):
    _,claims,store,event=setup(tmp_path)
    decision=build_reviewed_settlement_allocation_decision(
        store=store,claim_batch=claims,claim_id=claims.claims[0].claim_id,
        event_id=event.event_id,amount_cents=2000,reviewer_role="Analyst",
        reviewed_at="2026-09-21T11:00:00Z",reason="Reviewed partial credit.",
    )
    bad=replace(decision,amount_cents=1)
    with pytest.raises(ValueError,match="decision hash mismatch"):
        persist_reviewed_settlement_allocation(store,bad)


def test_allocation_cannot_exceed_claim_or_event_residual(tmp_path):
    _,claims,store,event=setup(tmp_path,event_amount=3000)
    with pytest.raises(ValueError,match="claim residual"):
        build_reviewed_settlement_allocation_decision(
            store=store,claim_batch=claims,claim_id=claims.claims[0].claim_id,
            event_id=event.event_id,amount_cents=2501,reviewer_role="Analyst",
            reviewed_at="2026-09-21T11:00:00Z",reason="Too much.",
        )

    _,claims2,store2,event2=setup(tmp_path/"other",event_amount=1000)
    with pytest.raises(ValueError,match="event residual"):
        build_reviewed_settlement_allocation_decision(
            store=store2,claim_batch=claims2,claim_id=claims2.claims[0].claim_id,
            event_id=event2.event_id,amount_cents=1001,reviewer_role="Analyst",
            reviewed_at="2026-09-21T11:00:00Z",reason="Too much.",
        )


def test_review_timestamp_cannot_precede_settlement_event(tmp_path):
    _,claims,store,event=setup(tmp_path)
    with pytest.raises(ValueError,match="cannot precede settlement"):
        build_reviewed_settlement_allocation_decision(
            store=store,claim_batch=claims,claim_id=claims.claims[0].claim_id,
            event_id=event.event_id,amount_cents=1000,reviewer_role="Analyst",
            reviewed_at="2026-09-21T09:59:59Z",reason="Impossible review time.",
        )


def test_wrong_counterparty_event_cannot_be_review_allocated(tmp_path):
    _,claims,store,event=setup(tmp_path,event_payer="OTHER")
    with pytest.raises(ValueError,match="identity/currency mismatch"):
        build_reviewed_settlement_allocation_decision(
            store=store,claim_batch=claims,claim_id=claims.claims[0].claim_id,
            event_id=event.event_id,amount_cents=1000,reviewer_role="Analyst",
            reviewed_at="2026-09-21T11:00:00Z",reason="Wrong payer.",
        )


def test_batch_reference_can_be_reviewed_when_identity_and_capacity_are_valid(tmp_path):
    _,claims,store,event=setup(tmp_path,event_reference="BATCH-REMITTANCE")
    decision=build_reviewed_settlement_allocation_decision(
        store=store,claim_batch=claims,claim_id=claims.claims[0].claim_id,
        event_id=event.event_id,amount_cents=2000,reviewer_role="Analyst",
        reviewed_at="2026-09-21T11:00:00Z",
        reason="Batch remittance matched using the carrier credit detail.",
    )
    receipt=persist_reviewed_settlement_allocation(store,decision)
    assert receipt.status==ALLOCATED


def test_renderer_preserves_human_and_money_movement_boundaries(tmp_path):
    _,claims,store,event=setup(tmp_path)
    decision=build_reviewed_settlement_allocation_decision(
        store=store,claim_batch=claims,claim_id=claims.claims[0].claim_id,
        event_id=event.event_id,amount_cents=2000,reviewer_role="Analyst",
        reviewed_at="2026-09-21T11:00:00Z",reason="Reviewed partial credit.",
    )
    text=render_reviewed_settlement_allocation_markdown(decision)
    assert "Reviewed Settlement Allocation" in text
    assert "Reviewed partial credit" in text
    assert "does not create money movement" in text
    assert "does not by itself prove realized recovery" in text
