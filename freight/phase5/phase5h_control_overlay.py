"""Phase 5H source-backed overlay on existing Phase 5G operator dashboard.

Keeps disposable tenant RLS separate from actual Floot hosted credential proof.
"""
from __future__ import annotations
from html import escape
import json
from pathlib import Path

from freight.phase5.phase5g_control_overlay import phase5g_snapshot,render_phase5g


def phase5h_snapshot() -> dict:
    data=phase5g_snapshot()
    receipt=json.loads((Path(__file__).parent/"phase5h_acceptance_receipt.json").read_text())
    if (receipt["scope"]!="DISPOSABLE_POSTGRESQL16_PRINCIPAL_BOUND_TENANT_RLS_ONLY"
        or receipt["phase5g_and_phase5h_verifier_tests_passed"]!=14
        or receipt["new_tenant_isolation_tests_passed"]!=3
        or receipt["hosted_floot_restricted_credential_proven"] is not False
        or receipt["independent_hosted_verifier_service_proven"] is not False
        or receipt["stolen_verifier_credential_direct_sql_bypass_fixed"] is not False
        or receipt["actual_customer_revenue_cents"]!=0
        or receipt["historical_findings_closed"]!=0):
        raise ValueError("INVALID_PHASE5H_PROVENANCE_OR_CERTIFICATION")
    data["phase5h"]=receipt
    return data


def render_phase5h(data:dict)->str:
    html=render_phase5g(data)
    receipt=data["phase5h"]
    section="""<section class="panel" id="phase5h-principal-rls">
    <div class="eyebrow">Phase 5H / Disposable PostgreSQL authenticated principal RLS</div>
    <h2>Tenant isolation verified for restricted verifier login</h2>
    <p>The verifier may read and admit signed fictional CONTRACT records for
    its DBA-assigned tenant. Actual PostgreSQL row-level security denies
    records from another tenant and rejects direct foreign-tenant inserts.
    The verifier cannot modify its principal-to-tenant mapping.</p>
    <p><strong>14 verifier tests passed</strong>, including three new principal
    scope checks. The policy derives authorization from the authenticated
    PostgreSQL current_user, not an HTTP tenant claim or a client-controlled
    session variable.</p>
    <h3>Hosted Floot trust boundary remains BLOCKED</h3>
    <p>The published and QA Floot clusters are distinct, but the unpublished
    QA application still connects as neondb_owner. It has not adopted this
    disposable principal RLS or separately deployed verifier credentials.</p>
    <p><strong>Still open:</strong> the privileged hosted SQL-owner signature
    bypass and the ability of someone with the verifier credential to issue
    direct SQL. No authentic buyer/bank/carrier source authority established.</p>
    <small>Evidence scope: """+escape(receipt["scope"])+""" · GitHub run """+str(receipt["disposable_acceptance_run_id"])+""".
    Zero real RETALLY revenue; 26 historical findings remain OPEN_UNVERIFIED.</small>
    </section>"""
    if html.count("</main>")!=1:
        raise ValueError("PRIOR_DASHBOARD_STRUCTURE_DRIFT")
    return html.replace("</main>",section+"</main>")


def export(path:Path)->dict:
    path.mkdir(parents=True,exist_ok=True)
    d=phase5h_snapshot()
    (path/"index.html").write_text(render_phase5h(d),encoding="utf8")
    (path/"phase5h_executive.json").write_text(json.dumps(d,sort_keys=True,indent=2)+"\n")
    return d


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True,type=Path)
    d=export(parser.parse_args().out)
    p=d["phase5h"]
    print(json.dumps({"verified_disposable_rls_tests":p["phase5g_and_phase5h_verifier_tests_passed"],
                      "hosted_restricted_credential_proven":p["hosted_floot_restricted_credential_proven"],
                      "historical_findings_closed":p["historical_findings_closed"]},sort_keys=True))
