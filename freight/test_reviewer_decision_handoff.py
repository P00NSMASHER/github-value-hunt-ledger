"""Real-pipeline regression tests for multi-export buyer-review handoff."""
import json
from dataclasses import asdict, replace

import pytest
from freight.audit_workflow import RuleCSVInput, run_audit_workflow
from freight.buyer_review_workflow import verify_buyer_review_batch
from freight.reviewer_workbench import import_reviewer_decision_files

IH = "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,charge_code,service_date,quantity_units,billed_cents\n"
RH = "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"


def context(count=2):
    rows = "".join(f"I{i},S{i},C,K,USD,X{i},DETENTION,2026-09-10,1,12500\n" for i in range(count))
    rows += "I-MISSING,S-MISSING,C,K,USD,X-MISSING,UNKNOWN,2026-09-10,1,3000\n"
    result = run_audit_workflow(
        invoice_filename="synthetic.csv", invoice_data=(IH+rows).encode(),
        buyer_id="synthetic", business_unit="qa", selection_rule="synthetic handoff",
        rule_inputs=(RuleCSVInput(
            filename="synthetic-rules.csv", data=(RH+"DETENTION,FIXED,2026-09-01,,10000,\n").encode(),
            customer_id="C", carrier_id="K", currency="USD", authority_document_id="synthetic-rate",
            source_document_sha256="a"*64, verified_controlling_authority=True,
        ),),
    )
    assert result.artifacts is not None, result.error_message
    a = result.artifacts
    return dict(review_packet=a.review_packet, review_routing=a.review_routing, truth=a.factory.truth)


def export(ctx, indices=(0,), **row_change):
    hashes = ctx["review_routing"].buyer_review_case_hashes
    return json.dumps(dict(
        schema_version=1, review_packet_hash=ctx["review_packet"].packet_hash,
        review_routing_hash=ctx["review_routing"].routing_hash, truth_hash=ctx["truth"].truth_hash,
        decisions=[dict(case_hash=hashes[i], disposition="CONFIRMED", reviewer_minutes=3,
                        reviewed_at="2026-09-21T09:00:00-04:00") | row_change for i in indices],
    )).encode()


def ingest(ctx, files, **kwargs):
    return import_reviewer_decision_files(files=files, reviewer_role="Synthetic Controller", **ctx, **kwargs)


def test_real_pipeline_split_exports_produce_one_verified_batch():
    ctx = context()
    batch = ingest(ctx, (export(ctx,(0,)), export(ctx,(1,))))
    assert batch.state == "COMPLETE" and batch.confirmed_count == 2
    assert batch.pending_case_hashes == ()
    verify_buyer_review_batch(batch=batch, **ctx)


def test_previous_verified_batch_is_retained_not_replaced():
    ctx = context()
    first = ingest(ctx, (export(ctx,(0,)),))
    assert first.state == "PARTIAL"
    later = ingest(ctx, (export(ctx,(1,)),), previous_batch=first)
    assert later.confirmed_count == 2 and later.state == "COMPLETE"
    assert set(r.review_hash for r in first.records) <= set(r.review_hash for r in later.records)
    verify_buyer_review_batch(batch=later, **ctx)


def test_exact_replayed_export_and_previous_batch_do_not_duplicate_decisions():
    ctx = context()
    raw = export(ctx,(0,1))
    first = ingest(ctx, (raw,))
    replay = ingest(ctx, (raw,raw), previous_batch=first)
    assert first == replay


def test_conflict_rejects_whole_handoff_and_leaves_previous_unchanged():
    ctx = context()
    previous = ingest(ctx, (export(ctx,(0,)),))
    snapshot = asdict(previous)
    with pytest.raises(ValueError, match="conflicts with previously"):
        ingest(ctx, (export(ctx,(1,)), export(ctx,(0,), disposition="FALSE_POSITIVE")),
               previous_batch=previous)
    assert asdict(previous) == snapshot


def test_previous_batch_cannot_be_relabelled_to_another_role():
    ctx = context()
    previous = ingest(ctx, (export(ctx,(0,)),))
    with pytest.raises(ValueError, match="reviewer role differs"):
        import_reviewer_decision_files(files=(export(ctx,(1,)),), reviewer_role="Other Controller",
                                       previous_batch=previous, **ctx)


def test_stale_previous_batch_is_rejected_by_current_proof_verifier():
    ctx = context()
    previous = ingest(ctx, (export(ctx,(0,)),))
    with pytest.raises(ValueError):
        ingest(ctx, (export(ctx,(1,)),), previous_batch=replace(previous, truth_hash="0"*64))


def test_remediation_export_is_still_blocked_by_existing_buyer_review_workflow():
    ctx = context()
    case_hash = ctx["review_routing"].remediation_case_hashes[0]
    with pytest.raises(ValueError, match="remediation"):
        ingest(ctx, (export(ctx, case_hash=case_hash),))


def test_empty_export_keeps_previous_partial_state_and_proofs():
    ctx = context()
    first = ingest(ctx, (export(ctx,(0,)),))
    assert ingest(ctx, (export(ctx,()),), previous_batch=first) == first


def test_two_thousand_and_one_real_findings_complete_across_two_files():
    ctx = context(2001)
    batch = ingest(ctx, (export(ctx, tuple(range(2000))), export(ctx,(2000,))))
    assert batch.confirmed_count == 2001 and batch.state == "COMPLETE"
    assert len(batch.records) == 2001
    verify_buyer_review_batch(batch=batch, **ctx)
