"""Final, fail-closed RETALLY laboratory acceptance from EXISTING research.

This is NOT production financial certification. Frozen synthetic artifacts are
independently checked; real hosted Floot credentials, external authorities and
historical finding closures remain explicit release blockers.
"""
from __future__ import annotations
from hashlib import sha1
from html import escape
from pathlib import Path
import json
import os

from freight.phase5.phase5h_control_overlay import phase5h_snapshot,render_phase5h
from freight.phase5.phase5c_oracle import load_fixture,verify_frozen_finances
from freight.phase5.test_phase5d_bc_qa import verify_bc

PHASE=Path(__file__).parent
FREIGHT=PHASE.parent
REPO=FREIGHT.parent
QA_CLUSTER="7694294930552894346"
PRODUCTION_CLUSTER="7693746749463444100"
PR_CHAIN=(279,284,286,288,295,297,301,304,309,310,314,316,322,328)
SOURCE_OBJECTS={
 "freight/phase5/phase5c_signed_fixture.json":"3075ee529b45850b0b58fe50d5cd168b26663091",
 "freight/phase5/phase5d_bc_qa_fixtures.json":"f29149afe358bc3d4023e42a8df6a67b2c224337",
 "freight/phase5/phase5d_d07_offline_receipt.json":"e554711c82313d65a71e49ae14b4da8ae503531b",
 "freight/phase5/phase5h_acceptance_receipt.json":"60a58e1dd88132d9490386fae50e4415916e205f",
 "freight/research/LAB_FINDINGS_CUMULATIVE.json":"8a97b74432b82b34468bbb57cbc14d869258b77c",
}


class InvalidReleaseEvidence(ValueError):
    pass


def require(condition:bool,code:str)->None:
    if not condition:
        raise InvalidReleaseEvidence(code)


def immutable_sources()->dict[str,str]:
    results={}
    for name,expected in SOURCE_OBJECTS.items():
        content=(REPO/name).read_bytes()
        actual=sha1(b"blob "+str(len(content)).encode()+b"\0"+content).hexdigest()
        require(actual==expected,"HISTORICAL_EVIDENCE_TAMPERED:"+name)
        results[name]=actual
    return results


def original_findings()->dict:
    register=json.loads((FREIGHT/"research/LAB_FINDINGS_CUMULATIVE.json").read_text())
    opened=[x for x in register["entries"] if x.get("remediation")=="OPEN_UNVERIFIED"]
    require(len(opened)==26,"HISTORICAL_FINDING_REGISTER_CHANGED")
    require(any(x["id"]=="D-07" for x in opened),"D07_MISSING")
    d07=json.loads((PHASE/"phase5d_d07_offline_receipt.json").read_text())
    require(d07["status"]=="REPAIRED_IN_OFFLINE_RESEARCH_ONLY","D07_REPAIR_SCOPE_CHANGED")
    require(d07["original_historical_register_status"]=="OPEN_UNVERIFIED",
            "FALSE_ORIGINAL_FINDING_CLOSURE")
    return {"register_total":len(register["entries"]),"historical_open":26,
            "d07_offline_original_repair":True,"d07_product_certified":False}


def gates()->list[dict]:
    rows=[
      ("ORIGINAL_SOURCE_AND_HISTORICAL_PROVENANCE","VERIFIED_RESEARCH","Frozen signed fixtures, pinned source objects and original D-07 scope independently checked"),
      ("FOURTEEN_PYTHON_LABS","VERIFIED_RESEARCH","Fourteen existing governed Python pathways run; not fourteen hosted production services"),
      ("ISOLATED_RECOVERYOS_QA","VERIFIED_QA_SCOPE","Separate PostgreSQL cluster and copied payment handler, with fictional auth and reduced schema"),
      ("FICTIONAL_CUSTOMER_A_CASH_AND_FEES","VERIFIED_QA_SCOPE","Two customer-posted credits, reversal, contractual fee and refund, independently reconstructed from synthetic signatures"),
      ("FICTIONAL_CUSTOMERS_B_AND_C","VERIFIED_QA_SCOPE","Two signed no-recovery contracts; unsupported credit/fee attempts rejected; C stopping decision remains modeled"),
      ("DISPOSABLE_INDEPENDENT_VERIFIER_RLS","VERIFIED_DISPOSABLE_ONLY","Distinct ephemeral PostgreSQL logins, signed fictional CONTRACT admission, current_user tenant RLS"),
      ("HOSTED_RESTRICTED_DB_PRINCIPAL","BLOCKED","Actual unpublished Floot QA still connects as neondb_owner, the financial-table owner"),
      ("HOSTED_INDEPENDENT_CRYPTO_ADMISSION","BLOCKED","No separately hosted verifier running with protected restricted credentials; direct-SQL bypass remains"),
      ("GENUINE_BUYER_CARRIER_BANK_AUTHORITY","BLOCKED","All signatures and accounting records are fictional; no independent real-world issuer permission"),
      ("PRODUCTION_EQUIVALENT_AUTH_SCHEMA","BLOCKED","Staging auth and financial tables differ from published RecoveryOS"),
      ("TWENTY_SIX_HISTORIC_FINDING_CLOSURES","BLOCKED","D-07 original offline research repaired only; twenty-six historical findings still formally open"),
      ("REAL_CLIENT_RECOVERY_AND_REVENUE","NOT_TESTED","No customer funds, claims, banking actions or actual revenue in these phases"),
    ]
    return [{"id":k,"status":s,"evidence":e} for k,s,e in rows]


def acceptance()->dict:
    hashes=immutable_sources()
    findings=original_findings()
    finance=verify_frozen_finances(load_fixture())
    bc=verify_bc(json.loads((PHASE/"phase5d_bc_qa_fixtures.json").read_text()))
    dashboard=phase5h_snapshot()
    p=dashboard["phase5h"]
    require(len(dashboard["phase4"]["executed_labs"])==14,"LABORATORY_COUNT_DRIFT")
    totals=finance["totals"]
    require((totals["net_recovered_cents"],totals["net_earned_fee_cents"],
             totals["fee_refunded_cents"])==(500,150,100),"SYNTHETIC_CASH_NOT_RECONCILED")
    require(bc["customers"]==2 and bc["simulated_customer_recovered_cents"]==0,
            "B_C_ECONOMIC_STATUS_CHANGED")
    require(p["hosted_floot_qa_cluster"]==QA_CLUSTER and p["production_cluster"]==PRODUCTION_CLUSTER,
            "CLUSTER_SCOPE_MISMATCH")
    require(p["hosted_floot_runtime_uses_owner"] is True,
            "REVERIFY_ACTUAL_HOSTED_DB_USER")
    require(p["hosted_floot_restricted_credential_proven"] is False,
            "REVERIFY_RUNTIME_CREDENTIALS")
    require(p["independent_hosted_verifier_service_proven"] is False,
            "REVERIFY_HOSTED_VERIFIER")
    require(dashboard["phase5g"]["historical_findings_closed"]==0 and
            dashboard["phase5h"]["actual_customer_revenue_cents"]==0,
            "FALSE_FINANCIAL_OR_HISTORICAL_CLOSURE")
    rows=gates()
    blocked=[g["id"] for g in rows if g["status"] in ("BLOCKED","NOT_TESTED")]
    require(len(blocked)==6,"RELEASE_GATE_CENSUS_CHANGED")
    return {
       "schema":1,"as_of_date":"2026-10-08",
       "release_status":"FINAL_RESEARCH_INTEGRATION_ACCEPTED_PRODUCTION_FINANCIAL_RELEASE_BLOCKED",
       "release_decision":"DO_NOT_RELEASE_FINANCIAL_PRODUCTION",
       "pr_chain":list(PR_CHAIN),
       "source_branch":"research/retally-phase5h-principal-tenant-rls-20261008",
       "ci_head":os.getenv("RETALLY_CANDIDATE_SHA","LOCAL_REPRODUCIBLE_NOT_CI_ATTESTED"),
       "frozen_source_git_blobs":hashes,
       "qa_postgres_system_id":QA_CLUSTER,"prod_postgres_system_id":PRODUCTION_CLUSTER,
       "hosted_qa_db_principal":"neondb_owner",
       "live_floot_verified_during_this_ci":False,
       "original_findings":findings,
       "synthetic_customer_A_financials":totals,
       "synthetic_customers_BC":bc,
       "actual_company_revenue_cents":0,"actual_customer_recovery_cents":0,
       "research_labs_executed":len(dashboard["phase4"]["executed_labs"]),
       "release_gates":rows,"blocked_gates":blocked,
       "final_handoff_actions":[
          "Establish distinct, non-owner Floot runtime credentials and verify actual connected principal.",
          "Deploy independent Ed25519 admission under separately protected database identity.",
          "Acquire genuine buyer, carrier and bank/accounting authority with explicit data permissions.",
          "Revalidate tenant boundaries and complete signed claims-to-cash against production-equivalent QA schema/auth.",
          "Reproduce and independently close historical findings against original affected source; keep D-07 offline scope distinct.",
          "Complete legal identity, customer confidentiality, insurance and commercial pilot approval before any real engagement."
       ],
       "operations_not_performed":[
          "No PR merges","No app publishing","No production database writes",
          "No customer/carrier contacts","No real bank actions or transfers",
          "No scheduled task changes"
       ],
    }


def render(report:dict)->str:
    base=render_phase5h(phase5h_snapshot())
    rows="".join("<tr><th>"+escape(x["id"].replace("_"," ").title())+
        "</th><td>"+escape(x["status"])+
        "</td><td>"+escape(x["evidence"])+"</td></tr>" for x in report["release_gates"])
    section="""<section class="panel" id="final-retally-release-acceptance">
      <div class="eyebrow">RETALLY / Final independent laboratory release adjudication</div>
      <h2>Laboratory research integrated. Financial production release BLOCKED.</h2>
      <p>All amounts are fictional. Signed QA invoices are not authentic buyer,
      carrier or bank statements. Disposed test databases do not prove actual
      hosted Floot runtime restrictions.</p>
      <table><thead><tr><th>Gate</th><th>Status</th><th>Evidence / limitation</th></tr></thead>
      <tbody>"""+rows+"""</tbody></table>
      <p><strong>DO NOT RELEASE FINANCIAL PRODUCTION.</strong> Actual QA
      remains neondb_owner; independently controlled issuer trust and external
      financial reconciliations are missing. Twenty-six historical findings
      remain OPEN_UNVERIFIED. Actual RETALLY revenue and customer recovery $0.</p>
      <small>Exact CI source: """+escape(report["ci_head"])+"""</small>
    </section>"""
    require(base.count("</main>")==1,"CHANGED_DASHBOARD_STRUCTURE")
    return base.replace("</main>",section+"</main>")


def export(output:Path)->dict:
    output.mkdir(parents=True,exist_ok=True)
    data=acceptance()
    (output/"final_acceptance.json").write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    (output/"index.html").write_text(render(data))
    text=[
      "# RETALLY final laboratory and financial acceptance",
      "",
      "**Final decision: DO NOT RELEASE FINANCIAL PRODUCTION.**",
      "",
      "The research stack and fictional QA cases were integrated and checked.",
      "The hosted owner-level evidence bypass and genuine external financial",
      "authority remain unresolved. All 26 historical findings remain open.",
      "Actual customer recovery and RETALLY revenue: $0.",
      "",
      "## Release gates",
      "",
      "| Gate | Status | Evidence |",
      "|---|---|---|",
    ]
    text.extend("| "+g["id"]+" | "+g["status"]+" | "+g["evidence"]+" |" for g in data["release_gates"])
    text.extend(["","## Final accountable handoff actions",""])
    text.extend(str(i)+". "+s for i,s in enumerate(data["final_handoff_actions"],1))
    text.extend(["","## Reproducibility","", "Exact CI source: "+data["ci_head"],
                 "Inputs pinned to Git object hashes; see final_acceptance.json."])
    (output/"FINAL_ENGINEERING_HANDOFF.md").write_text("\n".join(text)+"\n")
    return data


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    v=export(p.parse_args().out)
    print(json.dumps({"status":v["release_decision"],
                      "blocked":len(v["blocked_gates"]),
                      "research_labs":v["research_labs_executed"],
                      "open_findings":v["original_findings"]["historical_open"],
                      "real_revenue_cents":0},sort_keys=True))
