"""Run a tiny, isolated RETALLY financial journey, not a real carrier workflow.

Usage: PYTHONPATH=. python -m freight.lab_phase2_demo --output /tmp/retally-phase2
All outputs are synthetic, no network access, no real invoices/fees/payments.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
import json
import tempfile

from freight.test_lab_assurance import BUYER,BU,populate,assertions_and_fees,verifier
from freight.test_lab_operations_intelligence import journey
from freight.lab_assurance import verify_settlement
from freight.lab_operations_intelligence import CostAssumptions
from freight.lab_phase2_pipeline import evaluate_read_only_phase2,render_owner_report
from freight.lab_customer_scenarios import CustomerPersona,simulate_customer_reactions
from freight.lab_experiment_ledger import Experiment,ExperimentLedger
from freight.lab_assurance import digest
from freight.test_lab_phase2_pipeline import StoreAdapter


def build_demo():
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/"simulated_only.sqlite"
        populate(path)
        evidence,fee_events=assertions_and_fees()
        signer=verifier()
        proof=verify_settlement(path,buyer_id=BUYER,business_unit=BU,
                                assertions=evidence,fee_events=fee_events,verifier=signer)
        route=journey(proof.receipt_hash)
        packet=evaluate_read_only_phase2(
            StoreAdapter(path), assertions=evidence,fee_events=fee_events,verifier=signer,
            assumptions=CostAssumptions("USD",150,70,15,1000,4000,2000,120,40),
            journey=route)
        concerns=simulate_customer_reactions(route,CustomerPersona("enterprise-controller",7,2,True),
                refund_due_cents=0,as_of="2026-12-20T00:00:00Z")
        ledger=ExperimentLedger(Path(d)/"experiment_receipts.sqlite")
        illustrative=Experiment(
            experiment_id="PHASE2-SYNTHETIC-CLAIMS-01",
            finding_id="LAB-P1-07",
            source_head_sha=digest({"fixture":"original baseline before partial credit repair"}),
            candidate_head_sha=digest({"fixture":"phase2 patched lab test"}),
            frozen_input_sha256=digest({"fixture":"synthetic two credit and return"}),
            independent_test_sha256=digest({"fixture":"separate finance verifier"}),
            original_counterexample_reproduced=True,
            repaired_counterexample_rejected=True,
            known_good_control_passed=True,
            measured_runtime_ms=0,
            execution_scope="SYNTHETIC_OFFLINE",
        )
        ledger.append(illustrative)
        payload={"scope":"FICTIONAL_DEMONSTRATION_ONLY",
                 "source_authority":"PUBLIC_TEST_HMAC_NOT_ACTUAL_BUYER_SIGNATURE",
                 "financial":asdict(packet),"customer_reactions":concerns,
                 "experiment_receipts":ledger.read_and_verify(),
                 "historical_finding_closure":"NONE; 26 original findings remain OPEN_UNVERIFIED",
                 "production_deployed":False,"carrier_or_bank_activity":False}
        payload["demo_sha256"]=digest(payload)
        return payload,render_owner_report(packet)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    payload,report=build_demo()
    if args.output:
        args.output.mkdir(parents=True,exist_ok=True)
        (args.output/"phase2_example.json").write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
        (args.output/"owner_report.md").write_text(report+"\n")
    print(json.dumps({"demo_sha256":payload["demo_sha256"],
                      "status":payload["financial"]["status"],
                      "modeled_current_margin_cents":payload["financial"]["business_decision"]["modeled_current_margin_cents"],
                      "lab_work_items":len(payload["financial"]["routed_lab_work"]["lab_work_items"]),
                      "customer_model_hypotheses":len(payload["customer_reactions"]["reactions"]),
                      "financially_certified":False},sort_keys=True))

if __name__=="__main__":main()
