"""Evidence-labeled Phase 5D overlay on RETALLY's existing control center.

No new financial writer, staging simulator, or real customer claims.
"""
from __future__ import annotations
from html import escape
import json
from pathlib import Path

from freight.lab_assurance import digest
from freight.phase5.phase5c_control_overlay import control_center_data,render_dashboard
from freight.phase5.test_phase5d_bc_qa import verify_bc

ROOT=Path(__file__).parent


def phase5d_snapshot()->dict:
    data=control_center_data()
    frozen=json.loads((ROOT/"phase5d_bc_qa_fixtures.json").read_text())
    result=verify_bc(frozen)
    d07=json.loads((ROOT/"phase5d_d07_offline_receipt.json").read_text())
    data["phase5d"]={
        "status":"STAGED_SYNTHETIC_SIGNED_NO_RECOVERY_AND_ORIGINAL_OFFLINE_D07_REPAIR",
        "d07_repair_scope":d07["status"],
        "d07_historical_register_status":d07["original_historical_register_status"],
        "production_actor_identity_certified":False,
        "accepted_real_customer_count":0,
        "actual_retally_revenue_cents":0,
        "staged_customers_bc":result,
        "customer_B":{"case_id":"SIM-P5D-CASE-B","qa_financial_status":"CONTRACT_VERIFIED_NO_SETTLEMENT",
                      "customer_posted_cents":0,"fee_earned_cents":0,
                      "historical_tariff_validity":"PYTHON_SYNTHETIC_MODEL_ONLY",
                      "commercial_assessment":"NO_RECOVERY_NO_CONTINGENCY_FEE"},
        "customer_C":{"case_id":"SIM-P5D-CASE-C","qa_financial_status":"CONTRACT_VERIFIED_CREDIT_BLOCKED",
                      "customer_posted_cents":0,"fee_earned_cents":0,
                      "carrier_recovery_outcome":"NO_AUTHORIZED_QA_RECOVERY",
                      "commercial_assessment":"MODELED_NEGATIVE_MARGIN_LIMIT_ANALYST_SCOPE"},
        "limits":["Only signed contract and invalid credit/fee attempts executed in hosted QA for B/C",
                  "No live tariff review, customer behavior, bank statements or production recovery established",
                  "D07 original affected offline source repaired; NOT production-carrier actor certification",
                  "All 26 historical findings still formally OPEN_UNVERIFIED"],
    }
    data["phase5d"]["receipt_sha256"]=digest(data["phase5d"])
    return data


def render_phase5d(data:dict)->str:
    html=render_dashboard(data)
    proof=data["phase5d"]
    original=proof["d07_repair_scope"]
    rows=[
        ("A","SIM-MULTISITE-DISTRIBUTOR","SIGNED_SYNTHETIC_CASH_AND_REFUND",
         "Phase 5C staged actual handler, QA-only"),
        ("B","SIM-PARCEL-OPERATOR","NO_RECOVERY_NO_FEE",
         "Signed QA contract; denied unsupported credit and fee; tariff truth unverified in QA"),
        ("C","SIM-INDUSTRIAL-SHIPPER","ZERO_POSTINGS_STOP_RECOMMENDED",
         "Signed QA contract; denied unsupported credit and fee; stopping point is modeled"),
    ]
    table="".join("<tr><th>"+escape(x)+"</th><td>"+escape(y)+"</td><td>"+escape(z)+
                  "</td><td>"+escape(w)+"</td></tr>" for x,y,z,w in rows)
    section="""<section class="panel" id="phase5d-original-defect-and-bc">
    <div class="eyebrow">PHASE 5D / Independent original-source and QA evidence</div>
    <h2>Three distinct fictional customer acceptance boundaries</h2>
    <table><thead><tr><th>Case</th><th>Fictional account</th><th>Result</th><th>Evidence level</th></tr></thead>
    <tbody>"""+table+"""</tbody></table>
    <p>Signed synthetic B/C contracts passed Ed25519 checks. Four unsupported credit or fee attempts
    were rejected. Both have $0 posted/recovered and $0 earned contingency fees.</p>
    <h3>Original D-07 actor replay finding</h3>
    <p>Original offline Unified Laboratory counterexample FAILED before repair and PASSED after actor binding.
    Research scope: """+escape(original)+""". Historical finding: <strong>OPEN_UNVERIFIED</strong>.
    Genuine production actor authority remains untested.</p>
    <p>Original 26 historical findings remain unresolved for global/product certification. Actual
    RETALLY customer recovery and company revenue = $0.</p></section>"""
    if html.count("</main>")!=1:raise ValueError("DASHBOARD_HTML_STRUCTURE_CHANGED")
    return html.replace("</main>",section+"</main>")


def export(destination:Path)->dict:
    destination.mkdir(parents=True,exist_ok=True)
    data=phase5d_snapshot()
    (destination/"index.html").write_text(render_phase5d(data),encoding="utf8")
    (destination/"phase5d_executive.json").write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    return data


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    arg=p.parse_args()
    out=export(arg.out)
    print(json.dumps({"scope":out["phase5d"]["status"],
                      "historical_findings_closed":0,
                      "staged_BC_signatures_verified":out["phase5d"]["staged_customers_bc"]["customers"]},sort_keys=True))
