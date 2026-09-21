"""End-to-end synthetic rehearsal of the Freight Recovery commercial path.

This proves workflow consistency only. It must never be recorded as realized
customer value or revenue.
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from freight.audit_result_bundle import build_audit_result_bundle, verify_audit_result_bundle
from freight.audit_workflow import RuleCSVInput, render_workflow_summary, run_audit_workflow
from freight.contracts import (
    open_incumbent_output,
    seal_incumbent_submission,
)
from freight.deal_economics import DealProfile, qualify_deal
from freight.pilot_reporting import (
    ReviewDisposition,
    make_finding_review,
)
from freight.review_packet import render_review_packet_markdown
from freight.readiness import PilotReadinessInput, assess_readiness
from freight.settlement_report import (
    ClaimFindingBinding,
    assert_report_current,
    build_persistent_pilot_report,
    render_persistent_markdown,
)
from freight.settlement_store import (
    ALLOCATED,
    REVERSED,
    CounterEventRecord,
    RecoveryClaim,
    SettlementEventRecord,
    SettlementStore,
)


BUYER = "buyer-synthetic"
BU = "bu-synthetic"


def run_rehearsal() -> dict:
    readiness = assess_readiness(
        PilotReadinessInput(
            authorization_documented=True,
            read_only_access=True,
            population_reproducible=True,
            incumbent_output_sealable=True,
            settlement_observable=True,
            material_authority_reconstructable=True,
            customer_identity_stable=True,
            carrier_identity_stable=True,
            retention_defined=True,
            deletion_defined=True,
            invoice_source_coverage=1.0,
            authority_source_coverage=0.96,
            shipment_evidence_coverage=0.92,
        )
    )

    deal = qualify_deal(
        readiness,
        DealProfile(
            annual_transport_spend_usd=8_000_000,
            invoices_per_month=1200,
            carrier_count=8,
            diagnostic_fee_usd=6250,
            pilot_fee_usd=20000,
            diagnostic_analyst_hours=20,
            pilot_analyst_hours=60,
            loaded_hourly_cost_usd=100,
            diagnostic_other_cost_usd=500,
            pilot_other_cost_usd=2000,
            target_gross_margin=0.50,
        ),
    )

    invoice_csv = (
        "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,"
        "charge_code,service_date,quantity_units,billed_cents\n"
        "inv-1,shp-1,cust,carrier,USD,charge-1,DETENTION,2026-09-15,1,12500\n"
        "inv-2,shp-2,cust,carrier,USD,charge-2,ACCESSORIAL,2026-09-15,1,12500\n"
        "inv-3,shp-3,cust,carrier,USD,charge-3,MISC,2026-09-15,1,15000\n"
    ).encode("utf-8")
    verified_rules_csv = (
        "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"
        "DETENTION,FIXED,2026-09-01,2026-09-30,10000,\n"
        "ACCESSORIAL,FIXED,2026-09-01,2026-09-30,10000,\n"
    ).encode("utf-8")
    review_rules_csv = (
        "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"
        "MISC,FIXED,2026-09-01,2026-09-30,10000,\n"
    ).encode("utf-8")
    workflow = run_audit_workflow(
        invoice_filename="synthetic-freight-charges.csv",
        invoice_data=invoice_csv,
        buyer_id=BUYER,
        business_unit=BU,
        selection_rule="three synthetic invoices",
        rule_inputs=(
            RuleCSVInput(
                filename="rate-confirmation-rules.csv",
                data=verified_rules_csv,
                customer_id="cust",
                carrier_id="carrier",
                currency="USD",
                authority_document_id="rate-confirmation",
                source_document_sha256="a" * 64,
                verified_controlling_authority=True,
            ),
            RuleCSVInput(
                filename="candidate-addendum-rules.csv",
                data=review_rules_csv,
                customer_id="cust",
                carrier_id="carrier",
                currency="USD",
                authority_document_id="candidate-addendum",
                source_document_sha256="b" * 64,
                verified_controlling_authority=False,
            ),
        ),
    )
    if workflow.state != "REVIEW_REQUIRED" or workflow.artifacts is None:
        raise AssertionError("synthetic audit workflow did not reach review-required state")

    artifacts = workflow.artifacts
    invoice_batch = artifacts.invoice_batch
    population_build = artifacts.population_build
    population = population_build.population
    charges = invoice_batch.charges
    verified_rule_batch, review_rule_batch = artifacts.rule_batches
    rules = verified_rule_batch.rules + review_rule_batch.rules
    factory = artifacts.factory
    review_queue = artifacts.review_queue
    review_packet = artifacts.review_packet
    audit_run = artifacts.manifest
    truth = factory.truth
    by_charge = {
        derivation.charge_id: derivation.finding
        for derivation in factory.derivations
        if derivation.finding is not None
    }
    f1, f2, f3 = by_charge["charge-1"], by_charge["charge-2"], by_charge["charge-3"]
    sealed = seal_incumbent_submission(population, "synthetic-incumbent-source-hash")
    incumbent = open_incumbent_output(
        population=population,
        truth=truth,
        submission=sealed,
        finding_ids=(f2.finding_id,),
    )

    reviews = (
        make_finding_review(
            f1, ReviewDisposition.CONFIRMED,
            reviewer_role="Buyer Controller",
            reviewed_at="2026-09-20T09:00:00-04:00",
            reviewer_minutes=20,
        ),
        make_finding_review(
            f2, ReviewDisposition.CONFIRMED,
            reviewer_role="Buyer Controller",
            reviewed_at="2026-09-20T09:10:00-04:00",
            reviewer_minutes=10,
        ),
        make_finding_review(
            f3, ReviewDisposition.UNRESOLVED,
            reviewer_role="Buyer Controller",
            reviewed_at="2026-09-20T09:20:00-04:00",
            reviewer_minutes=5,
        ),
    )
    findings = {finding.finding_id: finding for finding in truth.findings}
    bindings = tuple(
        ClaimFindingBinding(item.finding_id, item.finding_id, item.proof_hash)
        for item in (f1, f2)
    )

    with tempfile.TemporaryDirectory() as td:
        audit_bundle_path = Path(td) / "synthetic-audit-result.zip"
        audit_bundle_receipt = build_audit_result_bundle(workflow, audit_bundle_path)
        verify_audit_result_bundle(workflow, audit_bundle_path)

        store = SettlementStore(
            Path(td) / "settlement.sqlite3",
            buyer_id=BUYER,
            business_unit=BU,
        )
        store.create_claim(
            RecoveryClaim(
                f1.finding_id,"inv-1","carrier","cust","USD",2500,
                "2026-09-20T10:00:00Z",f1.proof_hash,False,
            )
        )
        store.create_claim(
            RecoveryClaim(
                f2.finding_id,"inv-2","carrier","cust","USD",2500,
                "2026-09-20T10:00:00Z",f2.proof_hash,True,
            )
        )
        store.ingest_event(
            SettlementEventRecord(
                "e-1","inv-1","carrier","cust","USD",2000,
                "2026-09-21T10:00:00Z","store-settle-1","CREDIT-MEMO",
            )
        )
        store.review_allocate(
            allocation_id="a-1", claim_id=f1.finding_id, event_id="e-1",
            amount_cents=2000, created_at="2026-09-21T11:00:00Z",
        )
        store.ingest_event(
            SettlementEventRecord(
                "e-2","inv-2","carrier","cust","USD",2500,
                "2026-09-21T10:00:00Z","store-settle-2","CREDIT-MEMO",
            )
        )
        status = store.auto_allocate(
            "e-2", created_at="2026-09-21T11:00:00Z"
        ).status
        assert status == ALLOCATED

        before_return = build_persistent_pilot_report(truth, incumbent, store, bindings, reviews)
        store.ingest_counter(CounterEventRecord(
            "return-1", "e-1", "USD", 500, "2026-09-22T10:00:00Z",
            "synthetic-bank-return-source", "BANK-RETURN",
        ))
        assert store.auto_apply_counter(
            "return-1", created_at="2026-09-22T11:00:00Z",
        ).status == REVERSED
        stale_report_rejected = False
        try:
            assert_report_current(before_return, store)
        except ValueError as exc:
            if "snapshot changed" not in str(exc):
                raise
            stale_report_rejected = True
        assert stale_report_rejected

        report = build_persistent_pilot_report(truth, incumbent, store, bindings, reviews)
        assert_report_current(report, store)
        metrics = report.metrics
        store_realized = store.realized_cents()
        store_fee = store.fee_eligible_cents()

    if store_realized != metrics.realized_cents:
        raise AssertionError("persistent settlement store disagrees with pilot report")
    if store_fee != metrics.fee_eligible_realized_cents:
        raise AssertionError("persistent fee attribution disagrees with pilot report")

    return {
        "synthetic": True,
        "buyer_id": BUYER,
        "business_unit": BU,
        "readiness_status": readiness.status.value,
        "readiness_score": readiness.score,
        "deal_route": deal.route.value,
        "pilot_fixed_fee_usd": deal.economics.fee_usd,
        "pilot_delivery_cost_usd": deal.economics.delivery_cost_usd,
        "pilot_gross_margin": deal.economics.gross_margin,
        "population_hash": population.manifest_hash,
        "audit_workflow_state": workflow.state,
        "audit_workflow_summary": render_workflow_summary(workflow),
        "audit_run_hash": audit_run.run_hash,
        "audit_result_bundle_sha256": audit_bundle_receipt.bundle_sha256,
        "audit_result_bundle_manifest_sha256": audit_bundle_receipt.manifest_sha256,
        "audit_result_bundle_entry_count": audit_bundle_receipt.entry_count,
        "population_builder_hash": population_build.builder_hash,
        "population_invoice_count": population_build.invoice_count,
        "population_charge_count": population_build.charge_count,
        "incumbent_submission_hash": sealed.sealed_hash,
        "truth_hash": truth.truth_hash,
        "invoice_csv_adapter_hash": invoice_batch.adapter_hash,
        "invoice_csv_file_sha256": invoice_batch.file_sha256,
        "verified_rule_adapter_hash": verified_rule_batch.adapter_hash,
        "review_rule_adapter_hash": review_rule_batch.adapter_hash,
        "finding_factory_hash": factory.factory_hash,
        "finding_factory_decisions": [item.decision for item in factory.derivations],
        "review_queue_hash": review_queue.queue_hash,
        "review_packet_hash": review_packet.packet_hash,
        "review_packet_markdown": render_review_packet_markdown(review_packet),
        "review_queue": [
            {
                "charge_id": item.charge_id,
                "priority_class": item.priority_class,
                "decision": item.decision,
            }
            for item in review_queue.items
        ],
        "buyer_review_hashes": [review.review_hash for review in reviews],
        "incumbent_output_hash": incumbent.output_hash,
        "metrics": asdict(metrics),
        "persistent_store": {
            "realized_cents": store_realized,
            "fee_eligible_cents": store_fee,
        },
        "persistent_reporting": {
            "settlement_snapshot_hash": report.settlement_snapshot_hash,
            "report_hash": report.report_hash,
            "pre_return_snapshot_hash": before_return.settlement_snapshot_hash,
            "pre_return_report_hash": before_return.report_hash,
            "pre_return_realized_cents": before_return.metrics.realized_cents,
            "pre_return_fee_eligible_cents": before_return.metrics.fee_eligible_realized_cents,
            "return_cents": 500,
            "stale_report_rejected": stale_report_rejected,
        },
        "report_markdown": render_persistent_markdown(report),
        "commercial_value_claimed": False,
    }


if __name__ == "__main__":
    print(json.dumps(run_rehearsal(), indent=2))
