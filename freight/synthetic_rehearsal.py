"""End-to-end synthetic rehearsal of the Freight Recovery commercial path.

This proves workflow consistency only. It must never be recorded as realized
customer value or revenue.
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from freight.contracts import (
    AuthorityRef,
    PopulationRow,
    REVIEW,
    VALIDATED,
    freeze_population,
    freeze_truth,
    make_finding,
    open_incumbent_output,
    seal_incumbent_submission,
)
from freight.deal_economics import DealProfile, qualify_deal
from freight.pilot_reporting import (
    FindingReview,
    ReviewDisposition,
)
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

    population = freeze_population(
        BUYER,
        BU,
        "three synthetic invoices",
        (
            PopulationRow("inv-1","shp-1","cust","carrier","USD","src-inv-1"),
            PopulationRow("inv-2","shp-2","cust","carrier","USD","src-inv-2"),
            PopulationRow("inv-3","shp-3","cust","carrier","USD","src-inv-3"),
        ),
    )
    authority = AuthorityRef(
        "auth-1",BUYER,BU,"cust","carrier","USD","src-auth-1"
    )
    truth = freeze_truth(
        population,
        (authority,),
        (
            make_finding(
                finding_id="f-1", buyer_id=BUYER, business_unit=BU,
                invoice_id="inv-1", shipment_id="shp-1", customer_id="cust",
                carrier_id="carrier", currency="USD", authority_id="auth-1",
                expected_cents=10000, actual_cents=12500, status=VALIDATED,
            ),
            make_finding(
                finding_id="f-2", buyer_id=BUYER, business_unit=BU,
                invoice_id="inv-2", shipment_id="shp-2", customer_id="cust",
                carrier_id="carrier", currency="USD", authority_id="auth-1",
                expected_cents=10000, actual_cents=12500, status=VALIDATED,
            ),
            make_finding(
                finding_id="f-3", buyer_id=BUYER, business_unit=BU,
                invoice_id="inv-3", shipment_id="shp-3", customer_id="cust",
                carrier_id="carrier", currency="USD", authority_id=None,
                expected_cents=10000, actual_cents=15000, status=REVIEW,
            ),
        ),
    )
    sealed = seal_incumbent_submission(population, "synthetic-incumbent-source-hash")
    incumbent = open_incumbent_output(
        population=population,
        truth=truth,
        submission=sealed,
        finding_ids=("f-2",),
    )

    reviews = (
        FindingReview("f-1",ReviewDisposition.CONFIRMED,20),
        FindingReview("f-2",ReviewDisposition.CONFIRMED,10),
        FindingReview("f-3",ReviewDisposition.UNRESOLVED,5),
    )
    findings = {finding.finding_id: finding for finding in truth.findings}
    bindings = tuple(ClaimFindingBinding(finding_id, finding_id, findings[finding_id].proof_hash)
                     for finding_id in ("f-1", "f-2"))

    with tempfile.TemporaryDirectory() as td:
        store = SettlementStore(
            Path(td) / "settlement.sqlite3",
            buyer_id=BUYER,
            business_unit=BU,
        )
        store.create_claim(
            RecoveryClaim(
                "f-1","inv-1","carrier","cust","USD",2500,
                "2026-09-20T10:00:00Z",findings["f-1"].proof_hash,False,
            )
        )
        store.create_claim(
            RecoveryClaim(
                "f-2","inv-2","carrier","cust","USD",2500,
                "2026-09-20T10:00:00Z",findings["f-2"].proof_hash,True,
            )
        )
        store.ingest_event(
            SettlementEventRecord(
                "e-1","inv-1","carrier","cust","USD",2000,
                "2026-09-21T10:00:00Z","store-settle-1","CREDIT-MEMO",
            )
        )
        store.review_allocate(
            allocation_id="a-1", claim_id="f-1", event_id="e-1",
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
        "incumbent_submission_hash": sealed.sealed_hash,
        "truth_hash": truth.truth_hash,
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
