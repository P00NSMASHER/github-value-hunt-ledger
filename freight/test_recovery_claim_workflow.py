from dataclasses import replace

import pytest

from freight.audit_workflow import RuleCSVInput, run_audit_workflow
from freight.buyer_review_workflow import (
    BuyerReviewDecisionInput,
    build_buyer_review_batch,
)
from freight.contracts import open_incumbent_output, seal_incumbent_submission
from freight.pilot_reporting import ReviewDisposition
from freight.recovery_claim_workflow import (
    RecoveryClaimBatchState,
    build_recovery_claim_batch,
    persist_recovery_claim_batch,
    render_recovery_claim_batch_markdown,
)
from freight.settlement_store import SettlementStore


INVOICE_HEADER = "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,charge_code,service_date,quantity_units,billed_cents\n"
RULE_HEADER = "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"


def setup(dispositions=(ReviewDisposition.CONFIRMED, ReviewDisposition.CONFIRMED), decisions_complete=True):
    result = run_audit_workflow(
        invoice_filename="charges.csv",
        invoice_data=(INVOICE_HEADER
                      + "I1,S1,C,K,USD,X1,A,2026-09-10,1,12000\n"
                      + "I2,S2,C,K,USD,X2,B,2026-09-10,1,13000\n").encode(),
        buyer_id="buyer",
        business_unit="unit",
        selection_rule="period",
        rule_inputs=(
            RuleCSVInput("a.csv",(RULE_HEADER+"A,FIXED,2026-09-01,,10000,\n").encode(),"C","K","USD","a","a"*64,True),
            RuleCSVInput("b.csv",(RULE_HEADER+"B,FIXED,2026-09-01,,10000,\n").encode(),"C","K","USD","b","b"*64,True),
        ),
    )
    artifacts = result.artifacts
    assert artifacts is not None
    hashes = artifacts.review_routing.buyer_review_case_hashes
    decisions = [
        BuyerReviewDecisionInput(hashes[0], dispositions[0], 2, "2026-09-21T09:00:00Z"),
    ]
    if decisions_complete:
        decisions.append(
            BuyerReviewDecisionInput(hashes[1], dispositions[1], 3, "2026-09-21T09:01:00Z")
        )
    buyer_review = build_buyer_review_batch(
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        truth=artifacts.factory.truth,
        reviewer_role="Buyer Controller",
        decisions=tuple(decisions),
    )
    population = artifacts.population_build.population
    sealed = seal_incumbent_submission(population, "incumbent-source")
    incumbent = open_incumbent_output(
        population=population,
        truth=artifacts.factory.truth,
        submission=sealed,
        finding_ids=(buyer_review.records[1].finding_id,) if len(buyer_review.records) > 1 else (),
    )
    return artifacts, buyer_review, incumbent


def test_confirmed_reviews_create_exact_claims_and_incumbent_fee_disqualification():
    artifacts, review, incumbent = setup()
    batch = build_recovery_claim_batch(
        truth=artifacts.factory.truth,
        incumbent=incumbent,
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        buyer_review=review,
        issued_at="2026-09-21T10:00:00-04:00",
    )
    assert batch.state == RecoveryClaimBatchState.CLAIMS_READY.value
    assert batch.claim_count == 2
    assert batch.confirmed_review_count == 2
    assert batch.fee_disqualified_count == 1
    assert [claim.fee_disqualified for claim in batch.claims] == [False, True]
    assert {binding.finding_id for binding in batch.bindings} == {
        record.finding_id for record in review.records
    }
    assert all(claim.source_hash == binding.finding_proof_hash
               for claim, binding in zip(batch.claims, batch.bindings, strict=True))
    assert all(claim.amount_cents > 0 for claim in batch.claims)
    assert len(batch.batch_hash) == 64


def test_false_positive_and_unresolved_reviews_never_create_recovery_claims():
    artifacts, review, incumbent = setup(
        dispositions=(ReviewDisposition.FALSE_POSITIVE, ReviewDisposition.UNRESOLVED)
    )
    batch = build_recovery_claim_batch(
        truth=artifacts.factory.truth,
        incumbent=incumbent,
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        buyer_review=review,
        issued_at="2026-09-21T10:00:00Z",
    )
    assert batch.state == RecoveryClaimBatchState.NO_CONFIRMED_CLAIMS.value
    assert batch.claim_count == 0
    assert batch.claims == ()
    assert batch.bindings == ()


def test_partial_buyer_review_cannot_issue_claims():
    artifacts, review, incumbent = setup(decisions_complete=False)
    with pytest.raises(ValueError, match="must be COMPLETE"):
        build_recovery_claim_batch(
            truth=artifacts.factory.truth,
            incumbent=incumbent,
            review_packet=artifacts.review_packet,
            review_routing=artifacts.review_routing,
            buyer_review=review,
            issued_at="2026-09-21T10:00:00Z",
        )


def test_claim_issue_time_cannot_precede_buyer_review():
    artifacts, review, incumbent = setup()
    with pytest.raises(ValueError, match="before buyer review"):
        build_recovery_claim_batch(
            truth=artifacts.factory.truth,
            incumbent=incumbent,
            review_packet=artifacts.review_packet,
            review_routing=artifacts.review_routing,
            buyer_review=review,
            issued_at="2026-09-21T08:59:59Z",
        )


def test_tampered_buyer_review_batch_is_rejected():
    artifacts, review, incumbent = setup()
    bad = replace(review, batch_hash="0"*64)
    with pytest.raises(ValueError, match="does not match current review proofs"):
        build_recovery_claim_batch(
            truth=artifacts.factory.truth,
            incumbent=incumbent,
            review_packet=artifacts.review_packet,
            review_routing=artifacts.review_routing,
            buyer_review=bad,
            issued_at="2026-09-21T10:00:00Z",
        )


def test_tampered_incumbent_output_is_rejected():
    artifacts, review, incumbent = setup()
    bad = replace(incumbent, output_hash="0"*64)
    with pytest.raises(ValueError, match="incumbent output hash mismatch"):
        build_recovery_claim_batch(
            truth=artifacts.factory.truth,
            incumbent=bad,
            review_packet=artifacts.review_packet,
            review_routing=artifacts.review_routing,
            buyer_review=review,
            issued_at="2026-09-21T10:00:00Z",
        )


def test_claim_batch_is_deterministic_for_same_review_and_issue_time():
    artifacts, review, incumbent = setup()
    kwargs = dict(
        truth=artifacts.factory.truth,
        incumbent=incumbent,
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        buyer_review=review,
        issued_at="2026-09-21T10:00:00Z",
    )
    assert build_recovery_claim_batch(**kwargs) == build_recovery_claim_batch(**kwargs)


def test_renderer_states_fee_and_settlement_boundaries():
    artifacts, review, incumbent = setup()
    batch = build_recovery_claim_batch(
        truth=artifacts.factory.truth,
        incumbent=incumbent,
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        buyer_review=review,
        issued_at="2026-09-21T10:00:00Z",
    )
    text = render_recovery_claim_batch_markdown(batch)
    assert "Recovery Claim Batch" in text
    assert "fee-disqualified automatically" in text
    assert "does not prove settlement" in text


def test_atomic_persistence_receipt_creates_all_then_replays_idempotently(tmp_path):
    artifacts, review, incumbent = setup()
    batch = build_recovery_claim_batch(
        truth=artifacts.factory.truth,
        incumbent=incumbent,
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        buyer_review=review,
        issued_at="2026-09-21T10:00:00Z",
    )
    store = SettlementStore(
        tmp_path / "claims.sqlite3",
        buyer_id=batch.buyer_id,
        business_unit=batch.business_unit,
    )
    first = persist_recovery_claim_batch(store, batch)
    assert first.attempted_claim_count == 2
    assert first.created_claim_count == 2
    assert first.already_present_count == 0
    assert store.count("recovery_claims") == 2
    assert len(first.receipt_hash) == 64

    replay = persist_recovery_claim_batch(store, batch)
    assert replay.attempted_claim_count == 2
    assert replay.created_claim_count == 0
    assert replay.already_present_count == 2
    assert replay.claim_ids == first.claim_ids
    assert store.count("recovery_claims") == 2


def test_persistence_rejects_wrong_store_scope(tmp_path):
    artifacts, review, incumbent = setup()
    batch = build_recovery_claim_batch(
        truth=artifacts.factory.truth,
        incumbent=incumbent,
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        buyer_review=review,
        issued_at="2026-09-21T10:00:00Z",
    )
    store = SettlementStore(
        tmp_path / "wrong.sqlite3",
        buyer_id="other",
        business_unit=batch.business_unit,
    )
    with pytest.raises(ValueError, match="scope mismatch"):
        persist_recovery_claim_batch(store, batch)
    assert store.count("recovery_claims") == 0


def test_persistence_rejects_tampered_claim_before_writing(tmp_path):
    artifacts, review, incumbent = setup()
    batch = build_recovery_claim_batch(
        truth=artifacts.factory.truth,
        incumbent=incumbent,
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        buyer_review=review,
        issued_at="2026-09-21T10:00:00Z",
    )
    tampered_claim = replace(batch.claims[0], amount_cents=1)
    bad = replace(batch, claims=(tampered_claim,) + batch.claims[1:])
    store = SettlementStore(
        tmp_path / "tampered.sqlite3",
        buyer_id=batch.buyer_id,
        business_unit=batch.business_unit,
    )
    with pytest.raises(ValueError, match="does not match persisted claim"):
        persist_recovery_claim_batch(store, bad)
    assert store.count("recovery_claims") == 0
