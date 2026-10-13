"""RETALLY Lab 14 / M35: no-publication research-to-commercial claim firebreak.

Read-only, source-bound classification. A first-party macroeconomic source
can support an internal properly qualified statistical statement but NEVER
establishes invoices, overcharge error rates, contingent fees, recoverable TAM,
real buyer approvals, human reviewer reliability or publication authority.
Even an internally factual claim does not gain external release approval.

This is not a website text scanner or an authorization process. It is a
closed register of known dangerous inferences, linked to the existing 18
independently unverified Mission 11 real-customer pilot controls.
"""
from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha1
from html import escape
import json
from pathlib import Path
import re

from freight.research_evidence_gate import canon_hash
from freight.research_economic_denominator_m34 import (
    report_shell as m34_report, OFFLINE as M34_OFFLINE,
)
from freight.research_bea_original_m33 import (
    report_shell as m33_report, OFFLINE as M33_OFFLINE,
)
from freight.research_bls_sectoral_output_m31 import (
    report_shell as m31_report, OFFLINE as M31_OFFLINE,
)
from freight.research_unified_blspci import (
    report_shell as m29_report, OFFLINE as M29_OFFLINE,
)
from freight.research_pilot_preflight import build_preflight, SCOPE as PILOT_BOOK_SCOPE

BOOK=Path(__file__).parent/"research/CLAIM_CLEARANCE_M35_20261012.json"
BOOK_SHA1="752ae34f4bc2b6e1baa329b8955efd35dd826f38"
SCOPE="LAB14_M35_TYPED_INTERNAL_SOURCE_CLAIM_CLEARANCE_NO_EXTERNAL_APPROVAL"
BOOK_SCOPE="RETALLY_LAB14_M35_RESEARCH_TO_COMMERCIAL_CLAIM_FIREBREAK_NO_PUBLICATION"
MIN_DATE=date(2026,10,12)
GATES=tuple(f"P11-{n:02d}" for n in range(1,19))
ALL_IDS=tuple(f"M35-{n:02d}" for n in range(1,17))
INTERNAL_IDS=ALL_IDS[:8]
BLOCKED_IDS=ALL_IDS[8:]
REFERENCES={
    "M34":"freight/research_economic_denominator_m34.py",
    "M33":"freight/research_bea_original_m33.py",
    "M31":"freight/research_bls_sectoral_output_m31.py",
    "M29":"freight/research_unified_blspci.py",
    "M11":"freight/research_pilot_preflight.py",
}
SOURCE_CLASSES={"ORIGINAL_GOVERNMENT","DESCRIPTIVE_ONLY",
                "MODEL_DESCRIPTIVE_ONLY"}
BLOCK_REASONS={
    "UNVERIFIED_RECOVERY_TAM","UNVERIFIED_INVOICE_ERROR_RATE",
    "SYNTHETIC_VERSUS_REAL","UNVERIFIED_CASH_AND_FEES",
    "UNVERIFIED_BUYER_AND_SECURITY_PERMISSION","UNVERIFIED_BUYER_DEMAND",
    "UNVERIFIED_CUSTOMER_OUTCOME","UNVERIFIED_HUMAN_APPROVAL",
}
DISPLAY_SOURCE={
    "BEA_2024_NOMINAL":"Original BEA gross output, $million",
    "CENSUS_2024_REVENUE":"Original Census employer revenue, $million",
    "DENOMINATOR_2024_GAP":"Arithmetic industry denominator difference, $million",
    "CENSUS_TO_BEA_RATIO":"Ratio of distinct nominal industry totals, %",
    "BEA_GROSS_OUTPUT_CHANGE":"BEA real gross output index change, %",
    "BLS_SECTORAL_CHANGE":"BLS real sectoral output index change, %",
    "CENSUS_PPI_PROXY":"Illustrative Census annual-PPI adjusted revenue, %",
    "PRICE_SCOPE_GAP":"BEA gross price less BLS net PPI change, percentage points",
}


def _blob(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _policy()->dict:
    raw=BOOK.read_bytes()
    if _blob(raw)!=BOOK_SHA1:
        raise ValueError("M35_CLAIM_POLICY_GIT_BLOB_CHANGED")
    return json.loads(raw.decode("utf-8"))


def _has_receipt(obj:object)->bool:
    return (type(obj) is dict
            and type(obj.get("receipt_sha256")) is str
            and re.fullmatch("[0-9a-f]{64}",obj["receipt_sha256"]) is not None
            and obj["receipt_sha256"]==canon_hash({
                k:v for k,v in obj.items() if k!="receipt_sha256"
            }))


def validate_policy(policy:object, *,as_of:date)->list[str]:
    """Closed source policy: no imported customer/PPI market claims tolerated."""
    try:
        if type(policy) is not dict or policy!=_policy():
            return ["M35_FROZEN_CLAIM_DECISION_POLICY_CHANGED"]
        errors=[]
        if type(as_of) is not date or as_of<MIN_DATE:
            errors.append("M35_FUTURE_SOURCE_OBSERVATION")
        if (policy.get("schema_version")!=1 or policy.get("scope")!=BOOK_SCOPE
            or policy.get("observed_on")!="2026-10-12"
            or policy.get("lab_number")!=14
            or policy.get("reference_reports")!=REFERENCES
            or policy.get("original_pilot_gate_catalog")!=
               "freight/research/PILOT_PREFLIGHT_20261011.json"
            or policy.get("required_pilot_gate_count")!=18
            or policy.get("required_pilot_stage_count")!=6):
            errors.append("M35_SOURCE_FAMILY_OR_PILOT_CATALOG_NOT_AUTHORITATIVE")
        for n,w in (
            ("independent_human_signoffs_observed",0),
            ("external_claims_approved",0),
            ("real_customer_invoices_observed",0),
            ("actual_cash_recovered_usd",None),
            ("recoverable_market_tam_usd",None),
        ):
            if type(policy.get(n)) is not type(w) or policy.get(n)!=w:
                errors.append("M35_PILOT_CUSTOMER_EVIDENCE_OR_CASH_FABRICATED:"+n)
        for n in (
            "no_external_marketing_or_outreach_authorized",
            "no_client_document_import_authorized",
            "no_pilot_signoff_from_research_ci",
            "no_recovery_tam_from_industry_denominator_gap",
            "no_statistical_confidence_from_synthetic_reviewer_agreement",
            "no_assumption_that_source_receipts_are_independent_human_approvals",
            "no_new_lab_created","no_new_schedule_created",
        ):
            if policy.get(n) is not True:
                errors.append("M35_EXTERNAL_PUBLICATION_OR_APPROVAL_VETO_REMOVED:"+n)
        claims=policy.get("claim_registry")
        if (type(claims) is not list or len(claims)!=16
            or policy.get("claim_count")!=16
            or policy.get("qualified_internal_claim_count")!=8
            or policy.get("blocked_inference_claim_count")!=8
            or [x.get("id") for x in claims if type(x) is dict]!=list(ALL_IDS)):
            return errors+["M35_16_CLAIMS_OR_FIXED_ORDER_NOT_PRESERVED"]
        all_gate_refs=set()
        for index,claim in enumerate(claims):
            if type(claim) is not dict:
                errors.append("M35_CLAIM_ROW_NOT_OBJECT")
                continue
            common={
                "id","name","metric_key","expected_value","evidence_class",
                "internal_result","external_result","required_pilot_gate_ids",
                "caveat","source_refs","approves_customer_money",
                "public_publication_authorized",
            }
            allowed=common if index<8 else common|{"block_reason_code"}
            if set(claim)!=allowed:
                errors.append("M35_CLAIM_EVIDENCE_FIELDS_CHANGED:"+str(index))
                continue
            if type(claim["name"]) is not str or len(claim["name"])<20 or (
                type(claim["caveat"]) is not str or len(claim["caveat"])<42
                or claim["approves_customer_money"] is not False
                or claim["public_publication_authorized"] is not False
            ):
                errors.append("M35_CLAIM_TEXT_MONEY_OR_PUBLICATION_INVALID:"+claim["id"])
            gates=claim["required_pilot_gate_ids"]
            if (type(gates) is not list or not gates
                or len(gates)!=len(set(gates))
                or any(g not in GATES for g in gates)
                or "P11-18" not in gates):
                errors.append("M35_UNREGISTERED_REQUIRED_HUMAN_APPROVAL:"+claim["id"])
            else:
                all_gate_refs.update(gates)
            if index<8:
                if (claim["metric_key"] not in DISPLAY_SOURCE
                    or type(claim["expected_value"]) is not str
                    or not re.fullmatch(r"-?[0-9]+\.[0-9]{2,3}",claim["expected_value"])
                    or claim["evidence_class"] not in SOURCE_CLASSES
                    or claim["internal_result"]!="INTERNAL_RESEARCH_WITH_SOURCE_CAVEATS"
                    or claim["external_result"]!="BLOCKED_NO_LAB_PUBLICATION_AUTHORITY"
                    or any(x not in REFERENCES for x in claim["source_refs"])):
                    errors.append("M35_MISLABELED_INTERNAL_SOURCE_QUALITY:"+claim["id"])
            else:
                if (claim["metric_key"] is not None
                    or claim["expected_value"] is not None
                    or claim["evidence_class"]!="CUSTOMER_EMPIRICAL_PROOF_NOT_OBSERVED"
                    or claim["internal_result"]!="BLOCKED_UNSUPPORTED_INFERENCE"
                    or claim["external_result"]!="BLOCKED_NO_INDEPENDENT_CUSTOMER_EVIDENCE"
                    or claim["block_reason_code"] not in BLOCK_REASONS
                    or claim["source_refs"]!=["M11"]):
                    errors.append("M35_FORGED_RECOVERY_OR_COMMERCIAL_CLAIM:"+claim["id"])
        if all_gate_refs!=set(GATES):
            errors.append("M35_NOT_ALL_18_INDEPENDENT_PILOT_GATES_REFERENCED")
        caveat=policy.get("source_caveat")
        if type(caveat) is not str or len(caveat)<800 or "eighteen" not in caveat:
            errors.append("M35_RESEARCH_AND_HUMAN_SOURCE_DISCLAIMER_ABSENT")
        return errors
    except (KeyError,TypeError,ValueError,AttributeError):
        return ["M35_INVALID_TYPED_CLAIM_POLICY"]


def _reports(*,as_of:date)->tuple[dict,dict,dict,dict,dict]:
    policy=_policy()
    problems=validate_policy(policy,as_of=as_of)
    if problems:
        raise ValueError("M35_RESEARCH_CLAIM_POLICY_INVALID: "+";".join(problems))
    m34=m34_report(as_of=as_of)
    m33=m33_report(as_of=as_of)
    m31=m31_report(as_of=as_of)
    m29=m29_report(as_of=as_of)
    pilot=build_preflight(as_of=as_of)
    named=(("M34",m34,M34_OFFLINE),("M33",m33,M33_OFFLINE),
           ("M31",m31,M31_OFFLINE),("M29",m29,M29_OFFLINE))
    for id_,report,status in named:
        if not _has_receipt(report):
            raise ValueError("M35_MACROECONOMIC_REPORT_RECEIPT_MISSING_OR_TAMPERED:"+id_)
        if report.get("as_of")!=as_of.isoformat() or (
            report.get("source_status",report.get("status"))!=status
        ):
            raise ValueError("M35_HISTORICAL_SOURCE_GRADE_PROMOTED_AS_FRESH:"+id_)
        if report.get("lab")!=14 or report.get("new_lab_created") is not False:
            raise ValueError("M35_NEW_SOURCE_LAB_OR_WRONG_EXISTING_SCOPE:"+id_)
    if (not _has_receipt(pilot)
        or pilot.get("scope")!="LAB14_PROSPECTIVE_PILOT_INTERNAL_READINESS_ONLY"
        or pilot.get("existing_lab_number")!=14
        or pilot.get("unmet_requirements")!=18
        or pilot.get("required_controls")!=18
        or pilot.get("workflow_stage_count")!=6
        or pilot.get("controls_with_independently_verified_external_evidence")!=0
        or pilot.get("real_invoices_received")!=0
        or pilot.get("real_net_recovery_cents")!=0
        or pilot.get("real_world_study_authorized") is not False
        or pilot.get("public_performance_claims_permitted") is not False):
        raise ValueError("M35_EXISTING_PILOT_SIGNOFFS_FALSIFIED_OR_NOT_PROVEN")
    queue=pilot.get("evidence_preparation_queue")
    if (type(queue) is not list or len(queue)!=18
        or [g.get("id") for g in queue]!=list(GATES)):
        raise ValueError("M35_INDEPENDENT_HUMAN_GATE_IDS_CHANGED")
    for g in queue:
        if (g.get("status")!="REQUIRED_INDEPENDENT_PROOF_NOT_RECEIVED"
            or g.get("real_world_evidence_observed") is not False
            or g.get("approval_and_storage_authorized") is not False
            or g.get("external_actions_permitted") is not False):
            raise ValueError("M35_INDEPENDENT_CUSTOMER_HUMAN_PROOF_FALSELY_ENTERED")
    mock=pilot.get("fictional_test_case_reviewer_concordance",{})
    if (mock.get("agreement_fraction")!="9/10"
        or mock.get("actual_independent_reviewer_reliability_established") is not False
        or pilot.get("actual_human_independent_reviewers")!=0):
        raise ValueError("M35_SYNTHETIC_VOTES_FALSELY_RELABELED_INDEPENDENT_HUMAN")
    if (m34["bea_minus_census_nominal_2024_million_usd"]!="142607.754"
        or m34["census_nominal_ratio_to_bea_is_actual_market_coverage"] is not False
        or m34["nominal_gap_is_missing_carrier_invoices_or_recoverable_overcharges"] is not False
        or m34["recoverable_audit_market_tam_usd"] is not None
        or m33["paid_customer_freight_invoice_rows"]!=0
        or m31["real_paid_customer_freight_invoices_observed"]!=0
        or m29["actual_paid_customer_freight_invoices_observed"]!=0):
        raise ValueError("M35_BEA_CENSUS_GAP_PROMOTED_TO_FAKE_CLIENT_OUTCOME")
    return m34,m33,m31,m29,pilot


def _metric_values(m34:dict,m33:dict,m31:dict,m29:dict)->dict[str,str]:
    final=m34["comparison_2017_to_2024"][-1]
    ppi=next(x for x in m29["industry_comparisons"] if x["naics"]=="484")
    return {
        "BEA_2024_NOMINAL":final["bea_nominal_gross_output_million_usd"],
        "CENSUS_2024_REVENUE":final["census_employer_industry_revenue_million_usd"],
        "DENOMINATOR_2024_GAP":m34["bea_minus_census_nominal_2024_million_usd"],
        "CENSUS_TO_BEA_RATIO":m34["nominal_census_to_bea_measure_ratio_2024_pct"],
        "BEA_GROSS_OUTPUT_CHANGE":m33["original_bea_gross_output_2017_to_2024_pct"],
        "BLS_SECTORAL_CHANGE":m31["aggregate_naics484_real_sectoral_output_2017_2024_pct"],
        "CENSUS_PPI_PROXY":ppi["2017_to_2024_illustrative_annual_mean_price_adjusted_revenue_pct"],
        "PRICE_SCOPE_GAP":m34["bea_minus_bls_producer_price_change_difference_pp"],
    }


def report_shell(*,as_of:date)->dict:
    m34,m33,m31,m29,pilot=_reports(as_of=as_of)
    policy=_policy()
    source_values=_metric_values(m34,m33,m31,m29)
    gates={g["id"]:g for g in pilot["evidence_preparation_queue"]}
    claims=[]
    for c in policy["claim_registry"]:
        metric=c["metric_key"]
        value=source_values[metric] if metric is not None else None
        if metric is not None and value!=c["expected_value"]:
            raise ValueError("M35_AUTHENTICATED_SOURCE_METRIC_OR_CLAIM_VALUE_CHANGED:"+c["id"])
        linked=[{
            "gate_id":gate_id,
            "owner_role":gates[gate_id]["owner_role"],
            "stage":gates[gate_id]["stage"],
            "name":gates[gate_id]["name"],
            "human_evidence_observed":False,
            "internal_preparation_only":gates[gate_id]["next_internal_preparation_step"],
        } for gate_id in c["required_pilot_gate_ids"]]
        if not linked:
            raise ValueError("M35_CLAIM_RELEASE_WITHOUT_HUMAN_APPROVAL_GATE")
        claims.append({
            "claim_id":c["id"],
            "claim_subject":c["name"],
            "metric_key":metric,
            "internal_value":value,
            "unit":DISPLAY_SOURCE[metric] if metric is not None else None,
            "source_grade":c["evidence_class"],
            "internal_decision":c["internal_result"],
            "external_publication_decision":c["external_result"],
            "source_refs":c["source_refs"],
            "required_unmet_human_signoffs":linked,
            "required_unmet_human_signoff_count":len(linked),
            "independent_customer_evidence_accepted":False,
            "external_claims_authorized":False,
            "carrier_or_customer_contacts_authorized":False,
            "claim_money_or_recovery_established":False,
            "reason":c["caveat"],
            "block_reason_code":c.get("block_reason_code"),
        })
    internal=[x for x in claims if x["internal_decision"]=="INTERNAL_RESEARCH_WITH_SOURCE_CAVEATS"]
    blocked=[x for x in claims if x["internal_decision"]=="BLOCKED_UNSUPPORTED_INFERENCE"]
    if (len(internal)!=8 or len(blocked)!=8 or
        any(x["external_claims_authorized"] for x in claims)
        or {r["claim_id"] for r in claims}!=set(ALL_IDS)):
        raise ValueError("M35_CLAIM_CLEARANCE_INTERNAL_EXTERNAL_CATEGORY_DRIFT")
    answer={
        "schema_version":1,"scope":SCOPE,"as_of":as_of.isoformat(),
        "lab":14,"new_lab_created":False,
        "source_status":"OFFLINE_VERIFIED_PRIOR_MACRO_SOURCE_CATALOGS_NOT_FRESH_SOURCE_REPLAY",
        "source_original_publisher_replay_completed_in_this_run":False,
        "separate_original_2017_2024_source_evidence_available_historically":True,
        "external_publication_and_marketing_authority":"NOT_ESTABLISHED",
        "research_audience":"INTERNAL_LAB14_ONLY",
        "claim_count":len(claims),
        "qualified_internal_source_statements":len(internal),
        "blocked_unsupported_customer_business_claims":len(blocked),
        "external_commercial_claims_authorized":0,
        "research_to_publication_autopromotion_permitted":False,
        "real_customer_invoices_observed":0,
        "real_carrier_overcharges_adjudicated":0,
        "retally_cash_recovered_usd":None,
        "retally_recoverable_tam_usd":None,
        "real_independent_reviewers_observed":0,
        "synthetic_only_reviewer_agreement":"9/10_NOT_REAL_HUMAN_ACCURACY",
        "independent_customer_pilot_human_approvals_required":18,
        "independent_customer_pilot_human_approvals_verified":0,
        "independent_customer_pilot_human_approvals_unmet":18,
        "original_six_stage_pilot_structure_preserved":True,
        "evidence_stage_progress":[{
            "stage":x["id"],
            "stage_name":x["name"],
            "required_evidence_records":x["required_evidence_records"],
            "real_independently_approved_records":0,
        } for x in pilot["stages"]],
        "source_provenance_receipts":{
            "M34_economic_denominator":m34["receipt_sha256"],
            "M33_BEA_original":m33["receipt_sha256"],
            "M31_BLS_sectoral":m31["receipt_sha256"],
            "M29_BLS_PPI":m29["receipt_sha256"],
            "M11_pilot_human_evidence":pilot["receipt_sha256"],
            "M35_claim_policy":canon_hash(policy),
        },
        "source_claim_registry":claims,
        "no_real_customer_document_or_carrier_research_data_imported":True,
        "no_client_outreach_or_external_production_change":True,
        "no_new_schedule_created_or_modified":True,
        "caveat":(
            "RETALLY may internally discuss attributed public trucking "
            "industry data and clearly qualified descriptive differences "
            "from original BEA, Census and BLS prior reports, but this "
            "does not approve external commercial marketing content. "
            "The $142607.754-million BEA/Census 2024 denominator gap "
            "is NOT recoverable freight bill errors. Original customer "
            "invoices, governing rates and tariff precedence, unbiased "
            "samples, two independent human adjudicators, legally "
            "authorized data rights, privacy/security control evidence "
            "and actual confirmed refund cash have not been provided. "
            "All eighteen independent real customer pilot signoffs remain "
            "unmet. Sources and synthetic tests cannot certify real "
            "customer demand, recoveries or marketing claims."
        ),
    }
    answer["receipt_sha256"]=canon_hash(answer)
    return answer


def lookup_claim(report:dict,claim_id:str)->dict:
    """Only controlled catalog IDs, never arbitrary claimed user text."""
    if type(claim_id) is not str or claim_id not in ALL_IDS:
        raise ValueError("M35_UNKNOWN_OR_UNCONTROLLED_CLAIM_IDENTIFIER")
    if not _has_receipt(report) or report.get("scope")!=SCOPE:
        raise ValueError("M35_UNTRUSTED_OR_FORGED_CLAIM_DECISION_REPORT")
    matching=[c for c in report.get("source_claim_registry",[])
              if c.get("claim_id")==claim_id]
    if len(matching)!=1:
        raise ValueError("M35_CLAIM_MISSING_OR_DUPLICATED_FROM_APPROVED_POLICY")
    return matching[0]


def render_html(report:dict)->str:
    allowed=[c for c in report["source_claim_registry"]
             if c["internal_decision"]=="INTERNAL_RESEARCH_WITH_SOURCE_CAVEATS"]
    blocked=[c for c in report["source_claim_registry"]
             if c["internal_decision"]=="BLOCKED_UNSUPPORTED_INFERENCE"]
    def cards(cases):
        out=[]
        for c in cases:
            numbered=", ".join(g["gate_id"] for g in c["required_unmet_human_signoffs"])
            value=(" <strong>"+escape(c["internal_value"])+"</strong>"
                   if c["internal_value"] is not None else "")
            out.append(
                '<article><small>'+escape(c["claim_id"])+' · '+
                escape(c["internal_decision"])+
                '</small><h3>'+escape(c["claim_subject"])+
                value+'</h3><p>'+escape(c["reason"])+
                '</p><p><strong>External status:</strong> '+
                escape(c["external_publication_decision"])+
                '</p><p><small>Unmet human approval gates: '+
                escape(numbered)+'</small></p></article>'
            )
        return "".join(out)
    stages="".join(
        "<li>"+escape(s["stage_name"])+": "+
        str(s["real_independently_approved_records"])+"/"+
        str(s["required_evidence_records"])+
        " human evidence records</li>"
        for s in report["evidence_stage_progress"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY Lab 14 | Research-to-claims decision gate</title>'
        '<style>body{font:15px/1.55 system-ui;background:#f6f9f7;color:#163a2a;margin:0}'
        'main{max-width:1160px;margin:32px auto;padding:18px}'
        '.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:14px}'
        'article{border:1px solid #d8e6db;border-radius:12px;background:white;padding:18px}'
        'article p{overflow-wrap:anywhere}h1{font-size:36px;letter-spacing:-.035em}'
        'h2{margin-top:32px}small{color:#547367;font-size:12px}</style></head><body><main>'
        '<small>RETALLY / EXISTING RESEARCH LAB 14 / M35 / INTERNAL ONLY</small>'
        '<h1>Source evidence ≠ commercial claim authority</h1>'
        '<p>Internal factual statements with caveats: <strong>'+
        str(report["qualified_internal_source_statements"])+
        '</strong>. Unsupported business inferences blocked: <strong>'+
        str(report["blocked_unsupported_customer_business_claims"])+
        '</strong>. External commercial claims authorized: <strong>0</strong>.</p>'
        '<p>The BEA–Census dollar gap is NOT recoverable customer freight bills.'
        ' Synthetic invoices and 9/10 mock reviewer agreement are NOT'
        ' independent buyer results.</p>'
        '<h2>Public data: internal research with mandatory qualification</h2>'
        '<div class="grid">'+cards(allowed)+'</div>'
        '<h2>Unsupported customer, invoice and market statements</h2>'
        '<div class="grid">'+cards(blocked)+'</div>'
        '<h2>Separate required human customer-pilot evidence</h2>'
        '<ul>'+stages+'</ul><p><strong>18/18 still unmet.</strong>'
        ' Passing tests and source receipts are not external'
        ' authorization or legal/privacy review.</p><p>'+
        escape(report["caveat"])+'</p></main></body></html>'
    )


def main()->None:
    ap=argparse.ArgumentParser(description="Internal source-to-commercial claims boundary only")
    ap.add_argument("--out",required=True,type=Path)
    ap.add_argument("--as-of-date",default=date.today().isoformat())
    args=ap.parse_args()
    report=report_shell(as_of=date.fromisoformat(args.as_of_date))
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"claim_clearance.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    (args.out/"claim_clearance.html").write_text(
        render_html(report),encoding="utf-8"
    )
    print(json.dumps({
        "internal_research_with_caveats":report["qualified_internal_source_statements"],
        "blocked_business_inferences":report["blocked_unsupported_customer_business_claims"],
        "external_marketing_claims_authorized":0,
        "independent_customer_pilot_controls_unmet":report["independent_customer_pilot_human_approvals_unmet"],
        "receipt_sha256":report["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
