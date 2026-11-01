"""Add observed Phase5E admission defect and unresolved database write gap
to the existing Phase5D operator dashboard. No new financial model.
"""
from __future__ import annotations

from html import escape
import json
from pathlib import Path

from freight.lab_assurance import digest
from freight.phase5.phase5d_control_overlay import phase5d_snapshot,render_phase5d

ROOT=Path(__file__).parent


def phase5e_snapshot() -> dict:
    data=phase5d_snapshot()
    proof=json.loads((ROOT/"phase5e_revocation_admission_receipt.json").read_text())
    e={
      "scope":"FICTIONAL_ISOLATED_APPLICATION_AND_DISPOSABLE_POSTGRESQL",
      "staged_backdated_revoked_signer_defect":"REPRODUCED_AND_REPAIRED_IN_QA",
      "new_revoked_signer_admission":"REJECTED",
      "previously_admitted_historical_replay":"ALLOWED_IDEMPOTENTLY",
      "direct_owner_sql_signature_bypass":"OPEN_UNMITIGATED",
      "direct_owner_sql_production_impact":"NOT_ESTABLISHED",
      "production_financial_certification":False,
      "real_customer_recovery_cents":0,
      "historical_findings_closed":0,
      "original_findings_open":26,
      "original_observed_test":proof["original_reproduction"]["observed_after_revocation"],
      "repair_observed_test":proof["repair"]["post_fix_new_record"],
      "qa_cluster":proof["environments"]["qa"]["postgres_identifier"],
      "remaining_implementation_gate":
        "Run the financial write-path as a separately limited database identity and "
        "independently prove Ed25519 admission outside the privileged table owner. "
        "PostgreSQL still cannot certify a signature simply because its JSON field exists.",
    }
    e["receipt_sha256"]=digest(e)
    data["phase5e"]=e
    return data


def render_phase5e(data:dict)->str:
    html=render_phase5d(data)
    proof=data["phase5e"]
    section="""<section class="panel" id="phase5e-admission-trust">
      <div class="eyebrow">Phase 5E / Genuine QA defect and remaining database vulnerability</div>
      <h2>Revoked signing keys cannot submit new backdated records</h2>
      <p>Reproduced the original defect in unpublished QA: a new fictional contract
      from an already-revoked issuer initially returned HTTP 200. After the app and
      PostgreSQL repairs, new submissions return HTTP 400; previously admitted
      exact signed record replays remain HTTP 200, without a duplicate posting.</p>
      <h3>OPEN: direct owner SQL bypass of application Ed25519 verification</h3>
      <p>DB table owner is also the QA application connection. The SQL trigger
      checks monetary conservation and key lifecycle, but does not cryptographically
      verify Ed25519 signatures. Disposable PostgreSQL demonstrates direct DML
      accepts an invalid signature-shaped field; that test INSERT is rolled back.
      <strong>This exposure remains OPEN_UNMITIGATED.</strong></p>
      <p>Next required control: """+escape(proof["remaining_implementation_gate"])+"""</p>
      <small>Classification: fictional signed QA documents; actual company revenue $0;
      26 historical findings still OPEN_UNVERIFIED; source receipt """+escape(proof["receipt_sha256"])+"""</small>
    </section>"""
    if html.count("</main>")!=1:
        raise ValueError("PHASE5D_HTML_STRUCTURE_CHANGED")
    return html.replace("</main>",section+"</main>")


def export(destination:Path)->dict:
    destination.mkdir(parents=True,exist_ok=True)
    data=phase5e_snapshot()
    (destination/"index.html").write_text(render_phase5e(data),encoding="utf8")
    (destination/"phase5e_executive.json").write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf8")
    return data


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    d=export(args.out)
    print(json.dumps({"admission_fix":d["phase5e"]["staged_backdated_revoked_signer_defect"],
                      "open_db_bypass":d["phase5e"]["direct_owner_sql_signature_bypass"],
                      "historical_closures":0,"actual_company_recovery":0},sort_keys=True))
