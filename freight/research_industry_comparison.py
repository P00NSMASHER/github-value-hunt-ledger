"""Mission 15 — quantified, evidence-bounded CFS sector comparison (Lab 14).

Only direct CFS 2022 NAICS *all-mode* national totals are eligible. This is
commodity goods shipped, not shipping invoices, recovery spend, carrier mode
mix by sector, LTL bills, sales leads, cash recovered or a market TAM.

M12/M14 share the SAME survey family. No claim of independent replication
in GitHub CI; the source ZIP fingerprints were observed in a read-only browser.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from html import escape
import json
from pathlib import Path
import re

from freight.research_evidence_gate import canon_hash
from freight.research_market_audit import build_market_audit
from freight.research_cfs_industry_quality import (
    BOOK as ORIGINAL_INDUSTRY_BOOK, validate_manifest as validate_original,
)
from freight.research_validation_protocols import build_protocol_report

ROOT = Path(__file__).resolve().parent
PLAN = ROOT / "research/CFS_INDUSTRY_COMPARISON_PLAN_20261011.json"
SCOPE = "RETALLY_LAB14_INDUSTRY_COMPARISON_SURVEY_GOODS_ONLY"
SOURCE_LINEAGE = "SAME_CFS_2022_SURVEY_SHARED_EVIDENCE_NOT_THREE_INDEPENDENT_MARKETS"
EXPECTED_SOURCE_LIST = ["CF2200A18", "CF2200A19", "CF2200A01"]
EXPECTED_CODES = (
    ("manufacturing", "31-33", "Manufacturing establishments", 1),
    ("wholesale", "42", "Wholesale trade establishments", 2),
    ("warehousing", "4931", "Warehousing and storage establishments", 3),
)
GATE_KEYS = ("source_consistency","mode_segmentation","distance_weight","customer_reality")
PRIOR_GATES = {
    "source_consistency":"M12_AND_M14_PUBLIC_SOURCE",
    "mode_segmentation":"A18_A19_INDUSTRY_FORHIRE_DIRECT_ROWS_NOT_YET_REPRODUCED",
    "distance_weight":"ORIGINAL_BUCKET_LEVEL_ROWS_AND_NONCOMPARABLE_FLAGS",
    "customer_reality":"MISSION11_18_UNMET_BUYER_PILOT_CONTROLS",
}
BLOCK_FALSE = (
    "privacy_or_customer_source_data_used",
    "local_original_archives_replayed_in_ci",
    "source_subpopulation_coverage_complete",
    "industry_forhire_rows_verified_for_each_segment",
    "paid_ltl_invoice_total_known",
    "actual_audit_revenue_tam_known",
    "customer_demand_established",
    "real_external_claims_or_actions_authorized",
    "public_marketing_accuracy_claims_authorized",
    "new_lab_created",
)
EXPECTED_UNITS = {
    "value":"MILLIONS_USD_OF_GOODS_SHIPPED",
    "weight":"THOUSAND_TONS_OF_SHIPPED_GOODS",
}
EXPECTED_PROHIBITED = {
    "ANNUAL_LTL_PAID_BILLS","LTL_ONLY_FOR_HIRE_SHARE_BY_NAICS",
    "OVERCHARGE_FREQUENCY","RECOVERABLE_CASH","FEES_COLLECTED",
    "BUYER_PROPENSITY","MARKET_TAM_OR_SHARE","COMPETITOR_SUPERIORITY",
}
PLAN_TOP_FIELDS = {
    "schema_version","scope","observed_on","survey_year","data_sources",
    "source_lineage","units","method","analysis_profiles",
    "independent_evidence_gaps","prohibited_measures",
    "recommended_source_action", *BLOCK_FALSE,
}
PROFILE_FIELDS = {
    "id","naics","source_label","question","counterargument","disproof",
    "sector_research_order_not_market_rank","source_status",
}
GATE_FIELDS = {"id","description","required_evidence","dependency","approved"}


def _date(value: object) -> date:
    if type(value) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",value):
        raise ValueError("ISO date required")
    d=date.fromisoformat(value)
    if d.isoformat()!=value:
        raise ValueError("canonical date required")
    return d


def _text(value: object, minimum=30, maximum=1000) -> bool:
    return type(value) is str and minimum<=len(value.strip())<=maximum


def _exact_int(value: object) -> bool:
    return type(value) is int and value>=0


def _percent(num: int, den: int) -> str:
    if not _exact_int(num) or not _exact_int(den) or den<=0 or num>den:
        raise ValueError("INCOMPATIBLE_CENSUS_DENOMINATOR")
    return str((Decimal(num)*Decimal(100)/Decimal(den)).quantize(
        Decimal("0.01"),rounding=ROUND_HALF_UP
    ))


def _dollars_per_ton(value_million: int, weight_thousand: int) -> str:
    # millions of USD / thousands of tons => USD-per-ton x 1,000
    if not _exact_int(value_million) or not _exact_int(weight_thousand) or weight_thousand<=0:
        raise ValueError("INCOMPATIBLE_CENSUS_GOODS_VALUE_PER_TON")
    return str((Decimal(value_million)*Decimal(1000)/Decimal(weight_thousand))
               .quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))


def _validate_plan_inner(plan: dict, source_book: dict, *, as_of: date) -> list[str]:
    errors=[]
    if type(plan) is not dict or plan.get("schema_version") != 1:
        return ["M15 plan must be schema-1 object"]
    if set(plan) != PLAN_TOP_FIELDS or plan.get("scope") != SCOPE:
        errors.append("M15 scope or schema changed")
    try:
        observed=_date(plan.get("observed_on"))
        if observed!=date(2026,10,11):
            errors.append("M15 source review date cannot be backdated or shifted")
        if observed>as_of:
            errors.append("M15 public observation date in future")
    except ValueError:
        errors.append("invalid M15 observation date")
    if plan.get("survey_year") != 2022 or type(plan.get("survey_year")) is not int:
        errors.append("wrong CFS study vintage")
    if plan.get("source_lineage") != SOURCE_LINEAGE or plan.get("data_sources") != EXPECTED_SOURCE_LIST:
        errors.append("original CFS shared survey lineage or source set changed")
    if plan.get("units") != EXPECTED_UNITS:
        errors.append("Census goods/weight units relabeled as freight spend")
    for flag in BLOCK_FALSE:
        if plan.get(flag) is not False:
            errors.append(f"unverified market/customer approval attempted: {flag}")
    if not _text(plan.get("method"),100) or not _text(plan.get("recommended_source_action"),80):
        errors.append("direct-source methodology/future extraction step missing")
    if (type(plan.get("prohibited_measures")) is not list or
        set(plan["prohibited_measures"])!=EXPECTED_PROHIBITED or
        len(plan["prohibited_measures"])!=len(EXPECTED_PROHIBITED)):
        errors.append("prohibited LTL market/financial measures changed")
    rows=plan.get("analysis_profiles")
    if type(rows) is not list or len(rows)!=len(EXPECTED_CODES):
        return errors + ["three sourced, unranked industry research cohorts required"]
    for index,(row,(name,naics,label,order)) in enumerate(zip(rows,EXPECTED_CODES)):
        if type(row) is not dict or set(row)!=PROFILE_FIELDS:
            errors.append(f"cohort {index}: missing/extra fields")
            continue
        if (row.get("id")!=name or row.get("naics")!=naics or
            row.get("source_label")!=label or
            row.get("sector_research_order_not_market_rank")!=order or
            type(row.get("sector_research_order_not_market_rank")) is not int or
            row.get("source_status")!="CFS2022_ALL_MODE_DIRECT_TOTAL_ONLY"):
            errors.append(f"cohort {index}: source code/label or priority falsified")
        for field in ("question","counterargument","disproof"):
            if not _text(row.get(field),90):
                errors.append(f"cohort {index}: {field} must be falsifiable")
    gates=plan.get("independent_evidence_gaps")
    if type(gates) is not list or len(gates)!=len(GATE_KEYS):
        return errors+["four independent evidence gaps must remain visible"]
    for index,gate in enumerate(gates):
        if type(gate) is not dict or set(gate)!=GATE_FIELDS:
            errors.append(f"gate {index}: invalid schema")
            continue
        key=GATE_KEYS[index]
        if (gate.get("id")!=key or gate.get("dependency")!=PRIOR_GATES[key] or
            gate.get("approved") is not False):
            errors.append(f"{key}: fabricated provenance or signoff")
        if (not _text(gate.get("description"),35) or
            not _text(gate.get("required_evidence"),70)):
            errors.append(f"{key}: missing evidence requirement")
    errors.extend(validate_original(source_book,as_of=as_of))
    return errors


def validate_plan(plan: dict, source_book: dict, *, as_of: date) -> list[str]:
    try:
        return _validate_plan_inner(plan,source_book,as_of=as_of)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return ["malformed, unknown or untrusted CFS research metadata"]


def build_comparison(*, as_of: date, plan: dict|None=None,
                     source_book: dict|None=None,
                     market_report: dict|None=None) -> dict:
    if plan is None:
        plan=json.loads(PLAN.read_text(encoding="utf-8"))
    if source_book is None:
        source_book=json.loads(ORIGINAL_INDUSTRY_BOOK.read_text(encoding="utf-8"))
    problems=validate_plan(plan,source_book,as_of=as_of)
    if problems:
        raise ValueError("INVALID_CFS_INDUSTRY_COMPARISON: "+"; ".join(problems))
    if market_report is None:
        market_report=build_market_audit(as_of=as_of)
    receipt=market_report.get("receipt_sha256")
    if (type(receipt) is not str or receipt!=canon_hash({
        k:v for k,v in market_report.items() if k!="receipt_sha256"
    }) or market_report.get("scope")!="LAB14_SOURCE_LINKED_CFS_MARKET_AUDIT_RESEARCH_ONLY" or
        market_report.get("market_ranking_or_recovery_tam_established") is not False or
        market_report.get("buyer_demand_confirmed") is not False or
        market_report.get("existing_lab_number")!=14):
        raise ValueError("M12_ORIGINAL_DENOMINATOR_AUDIT_UNTRUSTED")
    benchmark=market_report["published_estimate_measurements"]
    rows=source_book["actual_industry_source_records"]
    observed={(x["naics"],x["mode"]):x for x in rows}
    # This small exact set is present in M14's real browser-observed national
    # source archive receipts, not estimated from vendor survey or own customers.
    expected_keys={("00","00"),("00","111"),("31-33","00"),("42","00"),("4931","00")}
    if set(observed)!=expected_keys or len(rows)!=5:
        raise ValueError("M14_SOURCE_ROW_INVENTORY_OR_NAICS_GRAIN_DRIFT")
    national=observed[("00","00")]
    for field,source_key in (
        ("value_million_usd","total_value_million_usd"),
        ("weight_thousand_tons","total_weight_thousand_tons"),
    ):
        if national.get(field)!=benchmark[source_key] or type(national.get(field)) is not int:
            raise ValueError("NATIONAL_CFS_DENOMINATOR_DISAGREES_WITH_M12")
    forhire=observed[("00","111")]
    if (forhire["value_million_usd"]!=benchmark["for_hire_truck_value_million_usd"]
        or forhire["weight_thousand_tons"]!=benchmark["for_hire_truck_weight_thousand_tons"]):
        raise ValueError("NATIONAL_FORHIRE_TRUCK_GRAIN_INCONSISTENT")
    comparison=[]
    for entry in plan["analysis_profiles"]:
        k=entry["naics"]
        source=observed[(k,"00")]
        value,weight=source["value_million_usd"],source["weight_thousand_tons"]
        if (source["value_flag"]!="" or source["ton_flag"]!="" or
            source["cross_archive_direct_totals_match"] is not True):
            raise ValueError("CFS_INDUSTRY_TOTAL_HAS_UNRESOLVED_QUALITY_FLAG")
        comparison.append({
            "id":entry["id"],"naics2017":k,
            "label":("CFS 4931/484 combined category (captive warehousing plus truck transportation)"
                     if k=="4931" else entry["source_label"]),
            "source_4931_484_tabulation_group_not_pure_warehouse":k=="4931",
            "survey_year":2022,
            "source_mode_code":"00",
            "source_mode_definition":"ALL_MODES_IN_SURVEY_NOT_LTL_ONLY",
            "source_location":"A18 SHIPDIST 001 / A19 SHIPWT 01",
            "value_million_usd_goods_shipped":value,
            "weight_thousand_tons_goods_shipped":weight,
            "source_value_share_of_survey_covered_us_pct":_percent(
                value,national["value_million_usd"]
            ),
            "source_weight_share_of_survey_covered_us_pct":_percent(
                weight,national["weight_thousand_tons"]
            ),
            "shipped_goods_value_density_usd_per_ton_not_carrier_rate":_dollars_per_ton(value,weight),
            "for_hire_truck_value_in_this_industry_million_usd":None,
            "within_industry_for_hire_shipment_value_share_pct":None,
            "distance_under_250mi_forhire_share_pct":None,
            "shipment_weight_500_to_9999lbs_forhire_share_pct":None,
            "actual_paid_ltl_invoice_count":None,
            "actual_ltl_invoice_spend_usd":None,
            "independently_verified_invoice_overcharges":None,
            "buyer_demand_verified":False,
            "source_all_mode_value_and_weight_flags":"UNFLAGGED_PUBLISHED_DIRECT_TOTALS",
            "source_industry_specific_cv_review_complete":False,
            "consumer_revenue_or_market_rank_authorized":False,
            "research_question":entry["question"],
            "disconfirming_explanation":entry["counterargument"],
            "proposed_falsification":entry["disproof"],
            "research_order_not_commercial_rank":entry["sector_research_order_not_market_rank"],
        })
    risk=[]
    for archive in source_book["official_archives"]:
        n=archive["published_table_row_count"]
        flag_totals={}
        for metric,f in (("goods_value",archive["value_flag_counts"]),
                         ("weight",archive["weight_flag_counts"])):
            if set(f)!={"blank","S","Z"} or sum(f.values())!=n:
                raise ValueError("ORIGINAL_PUBLISHER_FLAG_DENOMINATOR_DRIFT")
            flag_totals[metric]={
                "n_table_rows":n,
                "flag_S_rows":f["S"],
                "flag_Z_rows":f["Z"],
                "flag_S_pct_of_table_rows":_percent(f["S"],n),
                "flag_Z_pct_of_table_rows":_percent(f["Z"],n),
                "flagged_S_or_Z_pct_of_table_rows":_percent(f["S"]+f["Z"],n),
                "industry_specific_flag_incidence_unmeasured":True,
                "not_freight_market_or_customer_prevalence":True,
            }
        risk.append({
            "table_id":archive["table_id"],
            "original_zip_sha256_browser_observed":archive["original_zip_sha256"],
            "original_bytes_replayed_in_ci":False,
            "all_table_cell_quality_not_proof_of_sector_precision":True,
            "metrics":flag_totals,
        })
    stale=(as_of-_date(plan["observed_on"])).days>=90
    report={
        "schema_version":1,"scope":"LAB14_DIRECT_CFS_INDUSTRY_COMPARISON_RESEARCH_ONLY",
        "as_of":as_of.isoformat(),"survey_year":2022,
        "same_survey_not_independent_sources":True,
        "quantitative_data_basis":"FIVE_DIRECT_NATIONAL_A18_A19_CFS2022_TOTALS",
        "source_receipts":{
            "M14_industry_original_browser_report":canon_hash(source_book),
            "M12_national_comparison":receipt,
            "M15_hypothesis_plan":canon_hash(plan),
        },
        "n_industries":len(comparison),
        "market_or_customer_rankings_created":0,
        "national_shipment_value_million_usd_goods":national["value_million_usd"],
        "national_forhire_truck_goods_value_million_usd_not_ltl_spend":forhire["value_million_usd"],
        "national_forhire_truck_goods_value_share_of_us_pct":_percent(
            forhire["value_million_usd"],national["value_million_usd"]
        ),
        "industry_comparisons":comparison,
        "global_table_quality_flags":risk,
        "quality_statistical_caveat":"Table-wide S/Z proportions describe cross-tabular cells, not freight-billing error rates among manufacturers, wholesalers, or CFS combined 4931/484 establishments. Unflagged rows have not had individual coefficients of variation reviewed here.",
        "source_4931_484_tabulation_note":"Official 2022 CFS methodology groups NAICS 484 truck transportation with reported 4931, includes captive warehouse auxiliaries only, and excludes warehouses serving the public; reported 4931 cannot be treated as pure warehouse market.",
        "research_gates":[{
            "id":g["id"],"required_evidence":g["required_evidence"],
            "status":"HUMAN_REVIEW_OR_NEW_DIRECT_SOURCE_REQUIRED",
            "evidence_independently_observed":False,
            "external_action_authorized":False,
        } for g in plan["independent_evidence_gaps"]],
        "independent_source_verification_due_for_recheck":stale,
        "real_buyer_records":0,
        "actual_invoice_bills_counted":0,
        "actual_recovered_cash_usd":None,
        "ltl_market_tam_usd":None,
        "paid_ltl_spend_by_industry_usd":None,
        "no_future_effective_rate_or_legal_applied":True,
        "no_public_buyer_claims_authorized":True,
        "automated_source_fetch_or_schedule":False,
        "new_lab_created":False,"existing_lab_number":14,
        "limits":"CFS 2022 goods value density is not freight rate. Direct NAICS totals within one CFS survey family are not invoices or buyers; modes, parent-child NAICS and industry distribution channels overlap. Source CI did not fetch raw ZIPs; there is no industry-specific for-hire table row and no LTL-only paid freight or recovery estimate.",
    }
    report["receipt_sha256"]=canon_hash(report)
    return report


def render_html(report: dict) -> str:
    rows=[]
    for r in report["industry_comparisons"]:
        rows.append(
            "<tr><th>"+escape(r["label"])+"</th><td>"+
            format(r["value_million_usd_goods_shipped"],",")+"</td><td>"+
            escape(r["source_value_share_of_survey_covered_us_pct"])+"%</td><td>"+
            escape(r["shipped_goods_value_density_usd_per_ton_not_carrier_rate"]) +
            "</td><td>Unknown</td></tr>"
        )
    quality=[]
    for table in report["global_table_quality_flags"]:
        metrics=table["metrics"]
        quality.append(
            "<tr><th>"+escape(table["table_id"])+"</th><td>"+
            escape(metrics["goods_value"]["flagged_S_or_Z_pct_of_table_rows"])+"%</td><td>"+
            escape(metrics["weight"]["flagged_S_or_Z_pct_of_table_rows"])+"%</td></tr>"
        )
    hypotheses=[]
    for r in report["industry_comparisons"]:
        hypotheses.append(
            '<article><small>UNRANKED RESEARCH QUESTION · NAICS '+
            escape(r["naics2017"])+"</small><h3>"+escape(r["label"])+
            "</h3><p>"+escape(r["research_question"])+
            "</p><p><b>Alternative explanation:</b> "+
            escape(r["disconfirming_explanation"])+
            "</p><p><b>Falsification:</b> "+escape(r["proposed_falsification"])+
            "</p></article>"
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | CFS Industry Comparison</title><style>'
        '*{box-sizing:border-box}body{margin:0;background:#f5f8f6;color:#20382c;'
        'font:15px/1.6 system-ui,-apple-system,sans-serif}'
        'main{max-width:1120px;margin:auto;padding:32px 18px 70px}'
        'h1{font-size:clamp(30px,5vw,46px);line-height:1.12;letter-spacing:-.04em}'
        'article{background:white;border:1px solid #d9e7df;'
        'border-radius:14px;padding:22px;margin:16px 0}'
        'table{width:100%;border-collapse:collapse;margin:15px 0}'
        'th,td{text-align:left;padding:11px;border-bottom:1px solid #dce8df}'
        'small{font-size:12px;color:#5b7065}td{font-variant-numeric:tabular-nums}'
        'b{color:#126b46}p{overflow-wrap:anywhere}'
        '</style></head><body><main><small>RETALLY / RESEARCH LAB 14 / '
        'MISSION 15 / SOURCE-GROUNDED</small>'
        '<h1>Compare observed freight goods, not imaginary audit revenue.</h1>'
        '<p>These are direct national, all-mode 2022 Commodity Flow Survey '
        'shipped-goods values by establishment NAICS. They are not paid LTL '
        'bills, shipping rates, market share, service demand or recoveries. '
        'Sources share one Census survey; figures are not additive across '
        'supply-chain stages.</p>'
        '<h2>Three distinct research cohorts</h2><table><thead><tr>'
        '<th>Origin establishment</th><th>Goods value ($m)</th>'
        '<th>Share of CFS-covered U.S. goods value</th>'
        '<th>Goods value ($/ton), NOT a freight rate</th>'
        '<th>Industry LTL spend</th></tr></thead><tbody>'+
        "".join(rows)+'</tbody></table>'
        '<h2>Quality flags across all published table cells</h2>'
        '<table><thead><tr><th>CFS table</th><th>Goods cells flagged S or Z</th>'
        '<th>Weight cells flagged S or Z</th></tr></thead><tbody>'+
        "".join(quality)+'</tbody></table>'
        '<p>This is table-wide flagged-row frequency, NOT the error rate, '
        'representativeness or precision of any one industry.</p>'
        '<h2>Questions that would falsify the opportunity hypothesis</h2>'+
        "".join(hypotheses)+
        '<footer><p><b>Blocked:</b> in-sector for-hire shares, shipment weight '
        'band mix, distance band mix, buyer LTL spend, market TAM, customer '
        'claims and any net recoveries until stronger evidence arrives.</p>'
        '<small>Local integrity receipt '+escape(report["receipt_sha256"])+
        ' — not a publisher signature or independent customer outcome.'
        '</small></footer></main></body></html>'
    )


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--as-of-date",type=date.fromisoformat,default=date.today())
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    report=build_comparison(as_of=args.as_of_date)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"cfs_industry_comparison.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (args.out/"cfs_industry_comparison.html").write_text(
        render_html(report),encoding="utf-8")
    print(json.dumps({
        "scope":report["scope"],"industries":report["n_industries"],
        "market_rankings":report["market_or_customer_rankings_created"],
        "receipt":report["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
