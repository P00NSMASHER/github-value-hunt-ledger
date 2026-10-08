"""Add Phase5C signed-financial evidence to the existing Phase4 control center.

No new dashboard framework or financial ledger. Signed QA snapshot is
frozen, research-only. Creates a local ExperimentLedger INCONCLUSIVE receipt;
never changes the 26 original historical statuses.
"""
from __future__ import annotations
from dataclasses import asdict
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import tempfile
from time import perf_counter_ns

from freight.lab_phase4_control_center import render as render_phase4, snapshot
from freight.lab_assurance import digest
from freight.lab_experiment_ledger import Experiment,ExperimentLedger
from freight.phase5.phase5c_oracle import load_fixture,verify_frozen_finances


def control_center_data() -> dict:
    phase4=snapshot(max_labs=14)
    before=perf_counter_ns()
    proof=verify_frozen_finances(load_fixture())
    elapsed_ms=(perf_counter_ns()-before)//1_000_000
    with tempfile.TemporaryDirectory(prefix="retally-phase5c-research-") as tmp:
        ledger=ExperimentLedger(Path(tmp)/"ledger.sqlite3")
        item=Experiment(
          experiment_id="SIM-P5C-QA-SIGNED-FINANCIAL-REPLAY",
          finding_id="D-07",
          baseline_artifact_sha256=digest({"historical_finding":"D-07","legacy_reproduction":"NOT_PROVEN_THIS_RUN"}),
          candidate_artifact_sha256=digest({"phase5c_signed_fixture_receipt":proof["receipt_sha256"]}),
          frozen_input_sha256=sha256(
            Path(__file__).with_name("phase5c_signed_fixture.json").read_bytes()).hexdigest(),
          independent_test_sha256=digest({"oracle_status":proof["status"],"scope":"OFFLINE_FROZEN_QA_FIXTURE"}),
          original_counterexample_reproduced=False,
          repaired_counterexample_rejected=False,
          known_good_control_passed=True,
          measured_runtime_ms=elapsed_ms,
          execution_scope="REAL_CODE_MOCKED_PROVIDERS"
        )
        ledger.append(item)
        experiment=ledger.read_and_verify()
    source={
      "status":"SIGNED_SYNTHETIC_QA_FINANCIAL_PROOF_ONLY",
      "signed_documents":proof["source_rows"],
      "separate_issuer_public_keys":proof["issuer_public_keys"],
      "qa_cluster":proof["qa_cluster"],
      "actual_recovery_cents":0,
      "actual_retally_revenue_cents":0,
      "historical_original_findings_open":26,
      "historical_finding_closures":0,
      "verified_hosted_production_authentication":False,
      "externally_authorized_bank_carrier_buyer_credentials":False,
      "staged_recovery":proof["totals"],
      "financial_receipt_sha256":proof["receipt_sha256"],
      "phase4_code_execution":phase4["executed_labs"],
      "simulation_customers":phase4["three_customer_pilot"],
      "experiment_director_entry":experiment[0],
      "experiment_limitation":"D-07 original defect NOT reproduced or closed; receipt INCONCLUSIVE",
      "new_qa_replay_repair":"Canonical JSONB document equality, manual failing-before/passing-after in unpublished QA",
      "qa_acceptance_level":"TYPE_SCRIPT_HANDLER_AND_ISOLATED_PG_WITH_FICTIONAL_KEYS",
      "blockers":[
         "Real buyer/carrier/bank-controlled sources and legal contract authority",
         "Full production authentication/schema parity",
         "Original historical D-07 affected-code counterexample proof",
         "Three real application pilot cases; B and C remain Python-only synthetic models",
      ]
    }
    source["dashboard_receipt_sha256"]=digest({k:v for k,v in source.items() if k!="dashboard_receipt_sha256"})
    return {"phase4":phase4,"phase5c":source}


def render_dashboard(dataset: dict) -> str:
    html=render_phase4(dataset["phase4"])
    proof=dataset["phase5c"]; t=proof["staged_recovery"]
    row=[
       ("Carrier credits (fictional)",t["carrier_credits_cents"]),
       ("Customer posted credits (fictional)",t["customer_posted_cents"]),
       ("Reversals (fictional)",-t["reversed_cents"]),
       ("Net synthetic customer recovery",t["net_recovered_cents"]),
       ("Net earned synthetic contingency fee",t["net_earned_fee_cents"]),
       ("Gross fee invoiced",t["gross_invoiced_fee_cents"]),
       ("Fee credit",-t["fee_credit_cents"]),
       ("Gross fee collected",t["gross_fee_collected_cents"]),
       ("Fee refunded",-t["fee_refunded_cents"]),
       ("Open fee receivable",t["open_fee_receivable_cents"]),
       ("Remaining refund liability",t["outstanding_refund_liability_cents"])
    ]
    rows="".join("<tr><th>"+escape(k)+"</th><td>$"+f"{v/100:,.2f}"+"</td></tr>" for k,v in row)
    blockers="".join("<li>"+escape(x)+"</li>" for x in proof["blockers"])
    section=f"""<section class="panel" id="signed-reconciliation">
     <div class="eyebrow">Independent Phase 5C / fictional, signed QA financial evidence</div>
     <h2>Two posted credits, one reversal, reconciled synthetic fee and refund</h2>
     <p>Source: {proof['signed_documents']} externally generated fictional Ed25519 test documents,
        {proof['separate_issuer_public_keys']} independent synthetic signer roles.
        Signed fixture and PostgreSQL application writer are separate research components.
        No real funds received or earned.</p>
     <table><tbody>{rows}</tbody></table>
     <p>Original 26 historical findings: <strong>OPEN_UNVERIFIED</strong>.
        D-07 campaign verdict: <strong>INCONCLUSIVE</strong>, not closed.</p>
     <h3>Release blockers</h3><ul>{blockers}</ul>
     <small>QA cluster {escape(proof['qa_cluster'])}. Proof {escape(proof['financial_receipt_sha256'])}.
       NO genuine buyer, carrier or banking attestation. Zero actual company revenue.</small>
     </section>"""
    marker="</main>"
    if html.count(marker)!=1:
        raise ValueError("PHASE4_DASHBOARD_STRUCTURE_DRIFT")
    return html.replace(marker,section+marker)


def generate(output:Path)->dict:
    output.mkdir(parents=True,exist_ok=True)
    data=control_center_data()
    (output/"phase5c_executive.json").write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    (output/"index.html").write_text(render_dashboard(data))
    return data


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    r=generate(args.out)
    print(json.dumps({"finance":r["phase5c"]["staged_recovery"],
                      "classification":r["phase5c"]["status"],
                      "historic_findings_closed":0},sort_keys=True))
