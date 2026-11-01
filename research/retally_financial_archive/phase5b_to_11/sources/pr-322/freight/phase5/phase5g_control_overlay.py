"""Extend existing RETALLY Phase5E operator view without inventing certifications."""
from __future__ import annotations
from html import escape
import json
from pathlib import Path

from freight.phase5.phase5e_control_overlay import phase5e_snapshot,render_phase5e

HERE=Path(__file__).parent


def phase5g_snapshot():
    data=phase5e_snapshot()
    receipt=json.loads((HERE/"phase5g_disposable_acceptance.json").read_text())
    if (receipt["scope"]!="DISPOSABLE_POSTGRESQL_ONLY_NOT_FLOOT_RUNTIME"
        or receipt["ci_verifier_tests_passed"]!=11
        or receipt["db_owner_signature_bypass_fixed_in_hosted_floot"] is not False
        or receipt["verifier_db_credential_direct_sql_bypass_closed"] is not False
        or receipt["restricted_financial_admission_hosted_in_floot"] is not False
        or receipt["real_customer_revenue_cents"]!=0
        or receipt["historical_findings_closed"]!=0):
        raise ValueError("UNSUPPORTED_SECURITY_CERTIFICATION")
    data["phase5g"]=receipt
    return data


def render_phase5g(dataset:dict)->str:
    html=render_phase5e(dataset)
    r=dataset["phase5g"]
    body="""<section class="panel" id="phase5g-independent-admission">
      <div class="eyebrow">Phase 5G / Separate credential research (disposable PostgreSQL only)</div>
      <h2>Signed evidence admission using separate PostgreSQL identities</h2>
      <p>Eleven verifier acceptance tests passed with two different ephemeral login
      credentials, an untrusted application with zero financial table write rights,
      and an independently executable Ed25519 contract verifier.</p>
      <p>Real hosted Floot application credential separation:
      <strong>BLOCKED / NOT DEPLOYED</strong>. Its financial table owner continues
      to possess bypass privileges.</p>
      <p>Direct SQL using a stolen verifier credential:
      <strong>OPEN SECURITY EXPOSURE</strong>. Restrict credential ownership and
      instrument its use before authorizing commercial financial evidence.</p>
      <p>Supported independent admission: fictional CONTRACT documents only.
      Bank/carrier settlement authentication and full signed cash admission remain
      unverified outside the earlier fictional staging integration.</p>
      <small>Evidence scope: """+escape(r["scope"])+""".
      No real RETALLY revenue, no historical defect closure, no production writes.</small>
      </section>"""
    if html.count("</main>")!=1:
        raise ValueError("PRIOR_DASHBOARD_STRUCTURE_DRIFT")
    return html.replace("</main>",body+"</main>")


def export(target:Path)->dict:
    target.mkdir(parents=True,exist_ok=True)
    dataset=phase5g_snapshot()
    (target/"index.html").write_text(render_phase5g(dataset),encoding="utf8")
    (target/"phase5g_executive.json").write_text(
        json.dumps(dataset,indent=2,sort_keys=True)+"\n",encoding="utf8")
    return dataset


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True,type=Path)
    data=export(parser.parse_args().out)
    print(json.dumps({
        "disposable_verifier_tests":data["phase5g"]["ci_verifier_tests_passed"],
        "hosted_floot_credential_separation":data["phase5g"]["restricted_financial_admission_hosted_in_floot"],
        "owner_bypass_closed":data["phase5g"]["db_owner_signature_bypass_fixed_in_hosted_floot"],
        "historic_findings_closed":0
    },sort_keys=True))
