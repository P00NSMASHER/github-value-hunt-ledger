"""Translate a Freight pilot launch decision into an actionable remediation brief."""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

PRIORITY_ORDER={"P0":0,"P1":1,"P2":2}

@dataclass(frozen=True)
class Action:
    priority:str
    owner:str
    category:str
    code:str
    title:str
    evidence_required:tuple[str,...]
    unlocks:str

@dataclass(frozen=True)
class Brief:
    status:str
    route:str
    summary:str
    actions:tuple[Action,...]
    warnings:tuple[str,...]
    brief_hash:str

ACTIONS={
    "buyer_authorization_missing": Action("P0","BUYER / COMMERCIAL","BUYER_READINESS","buyer_authorization_missing","Document buyer authorization for the selected pilot population.",("buyer authorization reference","buyer/business-unit scope","approved source/date range"),"Data Readiness can advance."),
    "controlling_authority_not_reconstructable": Action("P0","BUYER PROCUREMENT / FREIGHT OPS","AUTHORITY","controlling_authority_not_reconstructable","Supply controlling contract/rate/addendum/tariff authority.",("base agreement/rate source","all effective amendments/addenda","incorporated tariff/accessorial references"),"Expected charges can be validated."),
    "deployment_team_mfa_not_enforced": Action("P0","ACCOUNT OWNER","DEPLOYMENT_SECURITY","deployment_team_mfa_not_enforced","Enforce MFA on the hosting team before confidential buyer data.",("provider configuration showing MFA enforcement enabled",),"One confidential-data access blocker is removed."),
    "customer_data_plane_not_discovered": Action("P0","FREIGHT RECOVERY ENGINEERING","DEPLOYMENT_SECURITY","customer_data_plane_not_discovered","Identify the production customer data plane before using the deployed route.",("database/object-store/API provider and project IDs","authorization model","source-to-storage data-flow map"),"Deployment-specific tenant controls can be tested."),
    "cross_tenant_isolation_not_proven": Action("P0","FREIGHT RECOVERY SECURITY","DEPLOYMENT_SECURITY","cross_tenant_isolation_not_proven","Run real A-vs-B tenant-isolation tests.",("identified production data plane","at least two tenant identities","passed negative cross-tenant read/write tests","preserved evidence references"),"Multi-tenant confidential-data use can be considered."),
    "parser_sandbox_not_proven": Action("P0","FREIGHT RECOVERY ENGINEERING / SECURITY","PARSER_SECURITY","parser_sandbox_not_proven","Prove the production parser sandbox.",("runtime provider/project","CPU limit evidence","memory limit evidence","execution-time limit evidence","network-egress isolation evidence","credential-isolation evidence"),"Production parser use can be considered."),
    "deployment_evidence_missing": Action("P0","FREIGHT RECOVERY SECURITY","DEPLOYMENT_SECURITY","deployment_evidence_missing","Collect a deployment-security evidence snapshot.",("provider/project identity","access-control evidence","collection timestamp"),"Current-deployment route can be evaluated."),
    "deployment_evidence_expired": Action("P0","FREIGHT RECOVERY SECURITY","DEPLOYMENT_SECURITY","deployment_evidence_expired","Recollect deployment-security evidence.",("fresh provider/project snapshot within the evidence-validity window",),"Current-deployment route can be reevaluated."),
    "separate_environment_evidence_manifest_missing": Action("P0","FREIGHT RECOVERY SECURITY / OPS","SEPARATE_ENVIRONMENT","separate_environment_evidence_manifest_missing","Complete the separate controlled-environment evidence manifest.",("completed SEPARATE_ENVIRONMENT_EVIDENCE_TEMPLATE.json","environment identifier/provider","configuration fingerprint","control evidence references and SHA-256"),"Separate route can move to evidence review."),
    "separate_environment_evidence_not_verified": Action("P0","SECURITY REVIEWER","SEPARATE_ENVIRONMENT","separate_environment_evidence_not_verified","Verify the separate controlled environment with source evidence.",("VERIFIED status","verifier role/date","control evidence references and SHA-256"),"Controlled manual pilot may become READY."),
    "separate_environment_evidence_expired": Action("P0","SECURITY REVIEWER","SEPARATE_ENVIRONMENT","separate_environment_evidence_expired","Reverify the separate controlled environment.",("fresh verification date","validity window <=90 days","updated evidence hashes"),"Separate route can be reevaluated."),
    "invoice_source_coverage_below_95pct": Action("P1","BUYER DATA","DATA_COVERAGE","invoice_source_coverage_below_95pct","Increase invoice-source coverage or narrow scope.",("invoice coverage >=95% or documented narrowed scope",),"Pilot can advance from diagnostic toward acceptance testing."),
    "authority_source_coverage_below_90pct": Action("P1","BUYER PROCUREMENT","DATA_COVERAGE","authority_source_coverage_below_90pct","Increase controlling-authority coverage or narrow scope.",("authority coverage >=90% or documented narrowed scope",),"Pilot can advance from diagnostic toward acceptance testing."),
    "shipment_evidence_coverage_below_80pct": Action("P1","BUYER FREIGHT OPS","DATA_COVERAGE","shipment_evidence_coverage_below_80pct","Increase shipment/supporting-evidence coverage or narrow scope.",("shipment evidence >=80% or documented narrowed scope",),"Pilot can advance from diagnostic toward acceptance testing."),
}

def _fallback(code:str, condition:bool=False)->Action:
    return Action("P1" if condition else "P0","PRODUCT / SECURITY REVIEW","UNMAPPED_REVIEW",code,"Resolve this launch-gate item with source evidence before overriding the gate.",("root-cause description","source evidence/configuration reference","reviewer sign-off if interpretation is required"),"Launch gate can be reevaluated.")

def _lookup(code:str, condition:bool=False)->Action:
    if code.startswith("deployment_evidence_invalid:"):
        return Action("P0","FREIGHT RECOVERY SECURITY","DEPLOYMENT_SECURITY",code,"Correct the invalid deployment-security evidence record.",("corrected evidence record","deployment evidence validator passes"),"Current-deployment route can be reevaluated.")
    if code.startswith("separate_environment_evidence_invalid:"):
        return Action("P0","SECURITY REVIEWER","SEPARATE_ENVIRONMENT",code,"Correct the invalid separate-environment evidence record.",("corrected evidence manifest","separate-environment validator passes"),"Separate route can be reevaluated.")
    return ACTIONS.get(code,_fallback(code,condition))

def _hash(value:object)->str:
    payload=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def build_brief(decision:dict)->Brief:
    by_code={}
    for code in decision.get("blockers",[]):
        by_code[code]=_lookup(code,False)
    for code in decision.get("conditions",[]):
        by_code.setdefault(code,_lookup(code,True))
    actions=tuple(sorted(by_code.values(),key=lambda a:(PRIORITY_ORDER.get(a.priority,99),a.category,a.code)))
    status=decision.get("status","UNKNOWN")
    route=decision.get("route","UNKNOWN")
    if status=="READY":
        summary="Pilot launch gate is READY for the selected route."
    elif status=="CONDITIONAL":
        summary="Pilot launch is CONDITIONAL. Close the listed evidence conditions before accepting confidential customer data."
    else:
        summary="Pilot launch is BLOCKED. Close P0 actions before the selected customer-data route can launch."
    warnings=tuple(decision.get("warnings",[]))
    body={"status":status,"route":route,"summary":summary,"actions":[asdict(a) for a in actions],"warnings":list(warnings)}
    return Brief(status,route,summary,actions,warnings,_hash(body))

def render_markdown(brief:Brief)->str:
    lines=["# Freight Recovery — Pilot Launch Brief","",f"**Status:** {brief.status}",f"**Current route:** {brief.route}",f"**Brief hash:** `{brief.brief_hash}`","",brief.summary,"","## Required actions",""]
    if not brief.actions:
        lines.append("No remediation actions are required by the current launch gate.")
    for i,a in enumerate(brief.actions,1):
        lines.extend([f"### {i}. [{a.priority}] {a.title}",f"- Owner: **{a.owner}**",f"- Category: `{a.category}`",f"- Gate code: `{a.code}`","- Evidence required:"])
        lines.extend(f"  - {item}" for item in a.evidence_required)
        lines.extend([f"- Unlocks: {a.unlocks}",""])
    lines.extend(["## Warnings",""])
    lines.extend([f"- {w}" for w in brief.warnings] or ["- None."])
    lines.extend(["","## Operating rule","","This brief cannot override the launch gate. An item closes only when the underlying evidence changes and the launch gate is rerun.",""])
    return "\n".join(lines)

def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("decision_json")
    parser.add_argument("--format",choices=("json","markdown"),default="markdown")
    args=parser.parse_args()
    decision=json.loads(Path(args.decision_json).read_text(encoding="utf-8"))
    brief=build_brief(decision)
    if args.format=="json":
        print(json.dumps(asdict(brief),indent=2))
    else:
        print(render_markdown(brief))

if __name__=="__main__":
    main()