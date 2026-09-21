from dataclasses import replace
from pathlib import Path

import pytest

from freight.audit_workflow import RuleCSVInput, run_audit_workflow
from freight.buyer_review_workflow import BuyerReviewDecisionInput, build_buyer_review_batch
from freight.carrier_action_workflow import build_carrier_action_proposal_batch
from freight.contracts import open_incumbent_output, seal_incumbent_submission
from freight.pilot_reporting import ReviewDisposition
from freight.recovery_claim_workflow import (
    build_recovery_claim_batch,
    persist_recovery_claim_batch,
)
from freight.recovery_lifecycle_manifest import (
    build_recovery_lifecycle_manifest,
    verify_recovery_lifecycle_manifest,
)
from freight.settlement_lifecycle_workflow import process_settlement_evidence
from freight.settlement_report import build_persistent_pilot_report
from freight.settlement_store import SettlementStore


INVOICE_HEADER = (
    "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,"
    "charge_code,service_date,quantity_units,billed_cents\n"
)
RULE_HEADER = (
    "charge_code,pricing_model,effective_from,effective_to,"
    "fixed_cents,unit_rate_cents\n"
)
SETTLEMENT_HEADER = (
    "event_id,reference,payer_id,payee_id,currency,amount_cents,"
    "booked_at,source_kind\n"
)


def build_case(tmp_path):
    workflow = run_audit_workflow(
        invoice_filename="charges.csv",
        invoice_data=(
            INVOICE_HEADER
            + "INV-1,SHP-1,CUST,CARRIER,USD,CH-1,DETENTION,2026-09-10,1,12500\n"
        ).encode(),
        buyer_id="buyer",
        business_unit="unit",
        selection_rule="one invoice",
        rule_inputs=(
            RuleCSVInput(
                filename="rules.csv",
                data=(
                    RULE_HEADER
                    + "DETENTION,FIXED,2026-09-01,,10000,\n"
                ).encode(),
                customer_id="CUST",
                carrier_id="CARRIER",
                currency="USD",
                authority_document_id="rate",
                source_document_sha256="a" * 64,
                verified_controlling_authority=True,
            ),
        ),
    )
    assert workflow.state == "REVIEW_REQUIRED"
    artifacts = workflow.artifacts
    assert artifacts is not None

    truth = artifacts.factory.truth
    finding = truth.findings[0]
    incumbent_submission = seal_incumbent_submission(
        artifacts.population_build.population,
        "incumbent-source",
    )
    incumbent = open_incumbent_output(
        population=artifacts.population_build.population,
        truth=truth,
        submission=incumbent_submission,
        finding_ids=(),
    )

    case = artifacts.review_packet.cases[0]
    buyer_review = build_buyer_review_batch(
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        truth=truth,
        reviewer_role="Buyer Controller",
        decisions=(
            BuyerReviewDecisionInput(
                case_hash=case.case_hash,
                disposition=ReviewDisposition.CONFIRMED,
                reviewer_minutes=3,
                reviewed_at="2026-09-20T12:00:00Z",
            ),
        ),
    )
    claims = build_recovery_claim_batch(
        truth=truth,
        incumbent=incumbent,
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        buyer_review=buyer_review,
        issued_at="2026-09-20T13:00:00Z",
    )

    store = SettlementStore(
        tmp_path / "lifecycle.sqlite3",
        buyer_id="buyer",
        business_unit="unit",
    )
    persistence = persist_recovery_claim_batch(store, claims)
    lifecycle = process_settlement_evidence(
        store,
        processed_at="2026-09-21T11:00:00Z",
        settlement_filename="settlements.csv",
        settlement_data=(
            SETTLEMENT_HEADER
            + "e1,INV-1,CARRIER,CUST,USD,2500,2026-09-21T10:00:00Z,CREDIT-MEMO\n"
        ).encode(),
    )
    assert lifecycle.state == "COMPLETE"
    report = build_persistent_pilot_report(
        truth,
        incumbent,
        store,
        claims.bindings,
        buyer_review.finding_reviews,
    )
    proposal_batch = build_carrier_action_proposal_batch(
        recovery_claims=claims
    )

    kwargs = dict(
        audit_run=artifacts.manifest,
        truth=truth,
        incumbent=incumbent,
        review_packet=artifacts.review_packet,
        review_routing=artifacts.review_routing,
        remediation_plan=artifacts.remediation_plan,
        buyer_review=buyer_review,
        recovery_claims=claims,
        claim_persistence=persistence,
        proposal_batch=proposal_batch,
        carrier_actions=(),
        settlement_transitions=(lifecycle,),
        report=report,
    )
    return kwargs, store, finding


def test_manifest_binds_audit_review_claim_settlement_and_report(tmp_path):
    kwargs, _store, finding = build_case(tmp_path)
    manifest = build_recovery_lifecycle_manifest(**kwargs)

    assert manifest.audit_run_hash == kwargs["audit_run"].run_hash
    assert manifest.truth_hash == kwargs["truth"].truth_hash
    assert manifest.buyer_review_batch_hash == kwargs["buyer_review"].batch_hash
    assert manifest.recovery_claim_batch_hash == kwargs["recovery_claims"].batch_hash
    assert manifest.carrier_proposal_count == 1
    assert manifest.carrier_action_count == 0
    assert manifest.submitted_action_count == 0
    assert manifest.delivered_action_count == 0
    assert manifest.unsubmitted_proposal_hashes == (
        kwargs["proposal_batch"].proposals[0].proposal_hash,
    )
    assert len(manifest.settlement_transitions) == 1
    assert manifest.pending_settlement_review_case_hashes == ()
    assert manifest.audit_remediation_case_count == 0
    assert manifest.realized_cents == finding.validated_cents == 2500
    assert manifest.fee_eligible_realized_cents == 2500
    assert manifest.settlement_snapshot_hash == kwargs["report"].settlement_snapshot_hash
    assert len(manifest.manifest_hash) == 64

    verify_recovery_lifecycle_manifest(manifest, **kwargs)


def test_manifest_rejects_discontinuous_settlement_transition_chain(tmp_path):
    kwargs, _store, _finding = build_case(tmp_path / "one")

    # Independently valid lifecycle result from a different store has an
    # unrelated before snapshot and therefore cannot be appended to this chain.
    other_store = SettlementStore(
        tmp_path / "two" / "other.sqlite3",
        buyer_id="buyer",
        business_unit="unit",
    )
    for claim in kwargs["recovery_claims"].claims:
        other_store.create_claim(claim)
    other = process_settlement_evidence(
        other_store,
        processed_at="2026-09-21T12:00:00Z",
        settlement_filename="settlements.csv",
        settlement_data=(
            SETTLEMENT_HEADER
            + "e1,INV-1,CARRIER,CUST,USD,2500,2026-09-21T10:00:00Z,CREDIT-MEMO\n"
        ).encode(),
    )

    with pytest.raises(ValueError, match="transition chain is discontinuous"):
        build_recovery_lifecycle_manifest(
            **{
                **kwargs,
                "settlement_transitions": (
                    kwargs["settlement_transitions"][0],
                    other,
                ),
            }
        )


def test_manifest_rejects_report_not_at_final_settlement_state(tmp_path):
    kwargs, _store, _finding = build_case(tmp_path)
    report = replace(
        kwargs["report"],
        settlement_snapshot_hash="0" * 64,
    )
    with pytest.raises(ValueError, match="snapshot hash mismatch"):
        build_recovery_lifecycle_manifest(**{**kwargs, "report": report})


def test_manifest_rejects_tampered_buyer_review_chain(tmp_path):
    kwargs, _store, _finding = build_case(tmp_path)
    bad_review = replace(
        kwargs["buyer_review"],
        batch_hash="0" * 64,
    )
    with pytest.raises(ValueError, match="buyer review batch"):
        build_recovery_lifecycle_manifest(
            **{**kwargs, "buyer_review": bad_review}
        )


def test_manifest_rejects_claim_persistence_from_other_batch(tmp_path):
    kwargs, _store, _finding = build_case(tmp_path)
    bad = replace(
        kwargs["claim_persistence"],
        claim_batch_hash="0" * 64,
    )
    with pytest.raises(ValueError, match="persistence batch hash"):
        build_recovery_lifecycle_manifest(
            **{**kwargs, "claim_persistence": bad}
        )


def test_manifest_hash_changes_with_report_state(tmp_path):
    kwargs, store, _finding = build_case(tmp_path)
    first = build_recovery_lifecycle_manifest(**kwargs)

    # A later counter changes settlement state, so the old report cannot simply
    # be relabeled as the new lifecycle state.
    counter_result = process_settlement_evidence(
        store,
        processed_at="2026-09-22T11:00:00Z",
        counter_filename="returns.csv",
        counter_data=(
            "counter_id,original_event_id,currency,amount_cents,observed_at,source_kind\n"
            "r1,e1,USD,2500,2026-09-22T10:00:00Z,BANK-RETURN\n"
        ).encode(),
    )
    new_report = build_persistent_pilot_report(
        kwargs["truth"],
        kwargs["incumbent"],
        store,
        kwargs["recovery_claims"].bindings,
        kwargs["buyer_review"].finding_reviews,
    )
    second = build_recovery_lifecycle_manifest(
        **{
            **kwargs,
            "settlement_transitions": (
                kwargs["settlement_transitions"][0],
                counter_result,
            ),
            "report": new_report,
        }
    )
    assert first.manifest_hash != second.manifest_hash
    assert first.realized_cents == 2500
    assert second.realized_cents == 0
