"""RETALLY Lab 14 / Mission 31: independent first-party BLS sectoral-output publication.

BEA real GROSS OUTPUT quantity (industry 484) remains unverified in Mission 30.
BLS Industry Productivity's REAL SECTORAL OUTPUT is a different original
government measure: removes intra-industry shipments, uses source overlaps,
and must never be reported as BEA gross output or an independently drawn
customer survey. BLS original annual A01 indices measure quantities, not
billing errors, cash refunds or a recoverable freight market.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha1, sha256
from html import escape
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

from freight.research_evidence_gate import canon_hash
from freight.research_unified_blspci import (
    report_shell as m29_report,
    OFFLINE as M29_OFFLINE,
)
from freight.research_bea_measurement_gate import (
    report_shell as m30_report,
    OFFLINE as M30_OFFLINE,
)

BOOK = Path(__file__).parent / "research/BLS_SECTORAL_OUTPUT_M31_20261012.json"
BOOK_SHA1 = "63031e5795efe37eedb7c8f69aeb789c7f9885cb"
API = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
CODES = ("484", "4841", "48412")
IDS = ("IPUIN484___T010000000","IPUIN4841__T010000000",
       "IPUIN48412_T010000000")
YEARS = tuple(range(2017,2025))
MIN_DATE = date(2026,10,12)
SCOPE = "LAB14_M31_FIRST_PARTY_BLS_SECTORAL_OUTPUT_OUTPUT_MEASUREMENT_NOT_BEA_GROSS_OUTPUT"
BOOK_SCOPE = "LAB14_ORIGINAL_BLS_REAL_SECTORAL_OUTPUT_2017_2024_NOT_BEA_GROSS_OUTPUT"
OFFLINE = "M31_OFFLINE_PRIOR_BLS_IP_SOURCE_OBSERVATION_NOT_FRESH_REPLAY"
VERIFIED = "M31_VERIFIED_DIRECT_BLS_IP_THREE_INDUSTRY_24_A01_ANNUAL_RECORDS"
BLOCKED = "M31_BLS_PUBLIC_IP_API_UNREACHABLE_0_NEW_VERIFIED_ANNUAL_VALUES"
MAX_BYTES=120_000
FALSE_GUARDS = (
    "bls_original_sectoral_output_equals_official_bea_real_gross_output",
    "bls_original_sectoral_output_equals_bea_gdp_value_added",
    "bls_real_sectoral_output_and_census_ppi_proxy_are_independent_survey_samples",
    "difference_can_be_claimed_statistical_model_error",
    "gross_output_original_bea_quantity_index_naics484_verified",
    "bea_api_key_acquired",
    "fred_style_ipu_aliases_valid_original_bls_api_ids",
    "direct_bea_real_output_competitor_validation_completed",
    "official_real_output_can_be_promoted_from_ppi_proxy",
    "external_public_marketing_claims_allowed",
    "private_customer_records_imported",
    "pilot_18_independent_authorizations_satisfied",
    "scheduled_tasks_modified",
    "new_lab_created",
)
EXPECTED_ROWS = {
    "484": ("IPUIN484___T010000000",
      ("100.000","102.374","101.979","103.475","109.162",
       "107.218","102.502","104.019")),
    "4841": ("IPUIN4841__T010000000",
      ("100.000","102.964","102.079","105.327","111.081",
       "108.932","104.238","105.912")),
    "48412": ("IPUIN48412_T010000000",
      ("100.000","103.007","101.809","104.963","108.995",
       "105.299","100.840","102.984")),
}
DISPLAY = {
    "484":"Truck transportation",
    "4841":"General freight trucking",
    "48412":"General freight trucking, long-distance",
}


def _blob_id(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _catalog()->dict:
    raw=BOOK.read_bytes()
    if _blob_id(raw)!=BOOK_SHA1:
        raise ValueError("M31_FROZEN_ORIGINAL_BLS_SECTORAL_OUTPUT_BOOK_CHANGED")
    return json.loads(raw.decode("utf-8"))


def _source_decimal(raw:object)->Decimal:
    if type(raw) is not str or not re.fullmatch(r"\d{1,5}(?:\.\d{1,5})?",raw):
        raise ValueError("M31_BLS_REAL_SECTORAL_OUTPUT_BAD_NUMERIC_RECORD")
    try:dec=Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("M31_INVALID_DECIMAL_OUTPUT_INDEX") from exc
    if not dec.is_finite() or dec<=0 or dec>=10000:
        raise ValueError("M31_BLS_OUTPUT_INDEX_NONPOSITIVE_OR_OUT_OF_RANGE")
    return dec


def validate_catalog(book:object, *,as_of:date)->list[str]:
    try:
        if type(book) is not dict or book!=_catalog():
            return ["M31_ORIGINAL_BLS_SOURCE_CATALOG_FIELDS_OR_VALUES_CHANGED"]
        problems=[]
        if type(as_of) is not date or as_of<MIN_DATE:
            problems.append("M31_BLS_SOURCE_OBSERVATION_IN_FUTURE")
        if (book.get("schema_version")!=1 or book.get("scope")!=BOOK_SCOPE or
            book.get("publisher")!="U.S. Bureau of Labor Statistics" or
            book.get("source_api_url")!=API or
            book.get("source_grain")!="ANNUAL_A01_NOT_SEASONALLY_ADJUSTED_2017_EQUALS_100" or
            book.get("source_api_request")!={
                "seriesid":["IPUIN484___T010000000","IPUIN4841__T010000000",
                            "IPUIN48412_T010000000"],
                "startyear":"2017","endyear":"2024",
            }):
            problems.append("M31_BLS_ORIGIN_SERIES_ID_PERIOD_OR_SOURCE_WRONG")
        rows=book.get("series")
        if type(rows) is not list or len(rows)!=3:
            return problems+["M31_EXACT_THREE_BLS_REAL_SECTORAL_INDUSTRIES_REQUIRED"]
        if [x.get("naics") for x in rows]!=list(CODES):
            problems.append("M31_NAICS_HIERARCHY_OR_ORDER_MISLABELED")
        for row in rows:
            code=row.get("naics")
            if code not in CODES:continue
            sid,expected=EXPECTED_ROWS[code]
            actual=row.get("values_by_year")
            if (row.get("native_bls_id")!=sid or
                row.get("industry")!=DISPLAY[code] or
                type(actual) is not dict or
                set(actual)!={str(y) for y in YEARS}):
                problems.append("M31_NATIVE_BLS_2017_2024_IND_DATE_MAP_INCORRECT:"+code)
                continue
            for year,want in zip(YEARS,expected):
                if _source_decimal(actual[str(year)])!=Decimal(want):
                    problems.append("M31_SOURCE_ANNUAL_VALUE_DRIFT:"+code+":"+str(year))
        for field in FALSE_GUARDS:
            if book.get(field) is not False:
                problems.append("M31_UNSUPPORTED_BEA_OUTPUT_OR_RECOVERY_CLAIM:"+field)
        for key,value in (
            ("recoverable_market_tam_usd",None),
            ("actual_cash_refunds_received_usd",None),
            ("real_customer_paid_ltl_invoices_observed",0),
            ("original_customer_rate_contracts_audited",0),
            ("independently_adjudicated_ltl_billing_errors",0),
            ("buyers_with_verified_interest",0),
        ):
            if type(book.get(key))!=type(value) or book.get(key)!=value:
                problems.append("M31_FAKE_REAL_CUSTOMER_EVIDENCE:"+key)
        if (book.get("bls_minus_m29_parent_percentage_points")!="2.84" or
            book.get("bls2017_2024_parent_real_sectoral_output_change_pct")!="4.02" or
            book.get("m29_2017_2024_parent_illustrative_ppi_deflated_census_revenue_change_pct")!="1.18"):
            problems.append("M31_BLS_VS_M29_PUBLISHED_COMPARISON_NOT_REPRODUCIBLE")
        if (type(book.get("source_caveat")) is not str or
            len(book["source_caveat"])<700 or
            "BEA" not in book["source_caveat"] or
            "18 genuine" not in book["source_caveat"]):
            problems.append("M31_CRITICAL_MEASUREMENT_AND_PILOT_HOLDS_MISSING")
        return problems
    except (ValueError,KeyError,TypeError,AttributeError):
        return ["M31_SOURCE_CATALOG_INVALID"]


def validate_original_bls_response(source:object, *,catalog:dict)->dict[str,dict[int,str]]:
    """Require exactly three native, final annual A01 index observations/years."""
    if type(source) is not dict or source.get("status")!="REQUEST_SUCCEEDED":
        raise ValueError("M31_BLS_IP_API_NOT_REQUEST_SUCCEEDED")
    if source.get("message") not in ([],None):
        raise ValueError("M31_BLS_IP_API_ERROR_DIAGNOSTIC_OR_WRONG_ALIAS")
    results=source.get("Results")
    if type(results) is not dict or type(results.get("series")) is not list:
        raise ValueError("M31_BLS_IP_RESULTS_SERIES_MISSING")
    groups=results["series"]
    if len(groups)!=3:
        raise ValueError("M31_EXACTLY_THREE_INDUSTRY_SOURCE_SERIES_REQUIRED")
    correct={item["native_bls_id"]:item for item in catalog["series"]}
    records={}
    for group in groups:
        if type(group) is not dict:
            raise ValueError("M31_BLS_ANNUAL_SERIES_NOT_OBJECT")
        sid=group.get("seriesID")
        if sid not in IDS or sid in records:
            raise ValueError("M31_WRONG_NATIVE_BLS_ID_FRED_ALIAS_OR_DUPLICATE")
        data=group.get("data")
        if type(data) is not list:
            raise ValueError("M31_MISSING_BLS_ANNUAL_SOURCE_RECORDS")
        peryear={}
        for r in data:
            if type(r) is not dict or r.get("period")!="A01":
                raise ValueError("M31_BLS_REAL_SECTORAL_OUTPUT_NOT_ANNUAL_A01")
            y=r.get("year")
            if y not in {str(z) for z in YEARS}:
                raise ValueError("M31_BLS_OUTPUT_YEAR_OUT_OF_RANGE")
            yi=int(y)
            if yi in peryear:
                raise ValueError("M31_DUPLICATED_BLS_SECTORAL_OUTPUT_YEAR")
            footnotes=r.get("footnotes",[])
            if type(footnotes) is not list or any(
                x and (type(x) is not dict or x.get("code"))
                for x in footnotes
            ):
                raise ValueError("M31_PRELIMINARY_SUPPRESSED_OR_FLAGGED_SOURCE_VALUE")
            dec=_source_decimal(r.get("value"))
            exp=_source_decimal(correct[sid]["values_by_year"][y])
            if dec!=exp:
                raise ValueError("M31_BLS_OFFICIAL_SOURCE_VALUE_CHANGED_REQUIRES_REVIEW:"+sid+":"+y)
            peryear[yi]=str(dec)
        if set(peryear)!=set(YEARS):
            raise ValueError("M31_EIGHT_SOURCE_ANNUAL_VALUES_REQUIRED:"+sid)
        records[sid]=peryear
    if set(records)!=set(IDS) or sum(len(x) for x in records.values())!=24:
        raise ValueError("M31_BLS_24_ORIGINAL_SOURCE_YEARS_NOT_COMPLETE")
    return records


def _pct(value:Decimal)->str:
    return str(value.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))


def _baseline(*,as_of:date)->tuple[dict,dict,dict]:
    b=_catalog()
    errs=validate_catalog(b,as_of=as_of)
    if errs:
        raise ValueError("M31_FROZEN_SOURCE_CATALOG_VALIDATION_FAILED:"+";".join(errs))
    m29=m29_report(as_of=as_of)
    m30=m30_report(as_of=as_of)
    if (m29["status"]!=M29_OFFLINE or m29["source_series_ids"]!=[
            "PCU484---484---","PCU484121484121","PCU484122484122"] or
        m29["actual_paid_customer_freight_invoices_observed"]!=0 or
        m29["freight_recovery_market_tam_usd"] is not None or
        m30["bea_gross_output_original_source_status"]!=
            "HOLD_PRIMARY_BEA_QUANTITY_INDEX_NOT_RETRIEVED" or
        m30["bea_484_real_gross_output_2017_2024_available_for_validation"] is not False or
        m30["all_18_real_customer_pilot_requirements_unmet"] is not True):
        raise ValueError("M31_M29_M30_SOURCE_OR_GROSS_OUTPUT_GUARD_REGRESSION")
    return b,m29,m30


def report_shell(*,as_of:date)->dict:
    book,m29,m30=_baseline(as_of=as_of)
    source={x["naics"]:x for x in book["series"]}
    output=[]
    for code in CODES:
        src=source[code]
        values=[_source_decimal(src["values_by_year"][str(y)]) for y in YEARS]
        change=_pct((values[-1]/values[0]-1)*100)
        output.append({
            "naics":code,"name":src["industry"],"native_bls_id":src["native_bls_id"],
            "years":list(YEARS),
            "annual_index_values":[str(x.quantize(Decimal("0.001"))) for x in values],
            "2017_index":str(values[0].quantize(Decimal("0.001"))),
            "2024_index":str(values[-1].quantize(Decimal("0.001"))),
            "2017_2024_real_sectoral_output_change_pct":change,
            "sectoral_output_excludes_intra_industry_shipments":True,
            "index_is_official_bea_real_gross_output":False,
            "source_is_customer_freight_billing_record":False,
        })
    bycode={x["naics"]:x for x in output}
    if [bycode[c]["2017_2024_real_sectoral_output_change_pct"] for c in CODES]!=[
        "4.02","5.91","2.98"]:
        raise ValueError("M31_OFFICIAL_BLS_SECTORAL_OUTPUT_GROWTH_CALCULATION_DRIFT")
    proxy=next(x for x in m29["industry_comparisons"] if x["naics"]=="484")[
        "2017_to_2024_illustrative_annual_mean_price_adjusted_revenue_pct"
    ]
    gap=_pct(Decimal(bycode["484"]["2017_2024_real_sectoral_output_change_pct"])-Decimal(proxy))
    if proxy!="1.18" or gap!="2.84":
        raise ValueError("M31_INCOMPATIBLE_PROXY_GAP_MISCOMPUTED")
    result={
        "schema_version":1,"scope":SCOPE,"as_of":as_of.isoformat(),
        "lab":14,"new_lab_created":False,
        "status":OFFLINE,"source_program":"BLS_INDUSTRY_PRODUCTIVITY",
        "original_bls_api_v2_url":API,
        "original_bls_api_v2_native_ids":list(IDS),
        "historically_observed_original_bls_source_annual_cells":24,
        "fresh_original_bls_output_source_replayed_this_run":False,
        "fresh_original_bls_source_year_cells_authenticated":0,
        "fresh_api_response_sha256":None,
        "current_source_has_been_directly_downloaded_in_this_report":False,
        "original_bls_sectoral_output_industry_series":output,
        "aggregate_naics484_real_sectoral_output_2017_2024_pct":"4.02",
        "m29_aggregate_illustrative_census_ppi_revenue_proxy_2017_2024_pct":proxy,
        "bls_minus_ppi_proxy_descriptive_gap_percentage_points":gap,
        "comparison_verdict":"DESCRIPTIVE_DIFFERENCE_NOT_VALIDATED_MODEL_ERROR_OR_OFFICIAL_BEA_REAL_OUTPUT",
        "bls_real_sectoral_output_is_not_bea_gross_output":True,
        "bls_real_sectoral_output_is_not_bea_gdp_value_added":True,
        "bls_sectoral_output_and_m29_revenue_proxy_can_share_input_sources":True,
        "bls48412_is_combined_long_distance_not_ltl_484122_or_tl_484121":True,
        "naics484_contains_4841_contains_48412_not_independent":True,
        "gross_output_original_bea_naics484_source_still_unverified":True,
        "be_a_real_output_484_2017_2024_available":False,
        "bea_api_no_key_original_probe_blocker":"API_ERROR_4_USER_ID_NOT_ACTIVE",
        "source_edition_variability_possible":True,
        "frozen_original_bls_catalog_receipt_sha256":canon_hash(book),
        "m29_census_bls_price_proxy_receipt_sha256":m29["receipt_sha256"],
        "m30_bea_measurement_compatibility_receipt_sha256":m30["receipt_sha256"],
        "real_paid_customer_freight_invoices_observed":0,
        "independently_adjudicated_overcharges_observed":0,
        "refund_cash_proven_usd":None,
        "recoverable_freight_audit_tam_usd":None,
        "buyer_demand_verified":False,
        "external_marketing_or_contact_authorized":False,
        "private_customer_or_carrier_documents_imported":False,
        "original_18_real_customer_pilot_requirements_unmet":True,
        "scheduled_tasks_created_or_modified":False,
        "caveat":(
            "Official BLS real sectoral output index for NAICS 484 measures "
            "real industry production after removing intra-industry and "
            "intra-sector shipments, based in part on sales and price "
            "source statistics. It is NOT BEA real gross output or "
            "GDP/value added, and it is not independently sampled from "
            "all Census and BLS PPI inputs used in the simpler M29 proxy. "
            "The 4.02% 2017–2024 BLS real sectoral-output change and 1.18% "
            "M29 illustrative adjusted-revenue proxy are different "
            "estimands; their 2.84 percentage point gap is not a validation "
            "error or statistically meaningful model-rejection threshold. "
            "Broad NAICS 48412 long-distance general freight contains "
            "both NAICS 484121 truckload and NAICS 484122 LTL, and cannot "
            "be substituted for either 6-digit series or summed with its "
            "parent. Direct national BEA original gross-output quantity "
            "observations were not fetched, and BEA API requires an active "
            "user ID. No real carrier invoice overcharges, paid customer "
            "spend, buyer demand, actual refunds, or recoverable market "
            "amounts are established by these government output indexes."
        ),
    }
    result["receipt_sha256"]=canon_hash(result)
    return result


def verify_origins(*,as_of:date,response:dict,raw_sha256:str)->dict:
    if type(raw_sha256) is not str or not re.fullmatch(r"[a-f0-9]{64}",raw_sha256):
        raise ValueError("M31_ORIGINAL_BLS_RESPONSE_SHA256_INVALID")
    book,_,_=_baseline(as_of=as_of)
    values=validate_original_bls_response(response,catalog=book)
    result=report_shell(as_of=as_of)
    result.update({
        "status":VERIFIED,
        "fresh_original_bls_output_source_replayed_this_run":True,
        "fresh_original_bls_source_year_cells_authenticated":24,
        "fresh_api_response_sha256":raw_sha256,
        "current_source_has_been_directly_downloaded_in_this_report":True,
        "fresh_semantic_values_receipt_sha256":canon_hash({
            "official_bls_source":API,"native_ids":list(IDS),
            "yearly_source_cells":values,
        }),
    })
    result["receipt_sha256"]=canon_hash({
        k:v for k,v in result.items() if k!="receipt_sha256"
    })
    return result


def blocked(*,as_of:date)->dict:
    r=report_shell(as_of=as_of)
    r["status"]=BLOCKED
    r["receipt_sha256"]=canon_hash({k:v for k,v in r.items() if k!="receipt_sha256"})
    return r


def fetch_original_bls()->tuple[dict,str]:
    payload={"seriesid":list(IDS),"startyear":"2017","endyear":"2024"}
    req=Request(API,
                data=json.dumps(payload,separators=(",",":")).encode("ascii"),
                headers={"Content-Type":"application/json",
                         "User-Agent":"RETALLY-Lab14-Real-Sectoral-Output-Original/1.0"},
                method="POST")
    with urlopen(req,timeout=30) as resp:
        if resp.geturl()!=API:
            raise ValueError("M31_ORIGINAL_BLS_REQUEST_REDIRECTED")
        raw=resp.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:
        raise ValueError("M31_BLS_OUTPUT_SOURCE_BYTES_OVER_LIMIT")
    return json.loads(raw.decode("utf-8")),sha256(raw).hexdigest()


def render_html(report:dict)->str:
    rows="".join(
        "<tr><th>"+escape(x["naics"])+"</th><td>"+escape(x["name"])+
        "</td><td>"+escape(x["2017_index"])+
        "</td><td>"+escape(x["2024_index"])+
        "</td><td>"+escape(x["2017_2024_real_sectoral_output_change_pct"])+
        "%</td></tr>" for x in report["original_bls_sectoral_output_industry_series"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | Real sectoral output and real gross output source gate</title>'
        '<style>body{font:15px/1.5 system-ui;color:#143b2b;background:#f7f9f6;'
        'margin:0}main{max-width:1120px;margin:35px auto;padding:20px}'
        'table{width:100%;border-collapse:collapse;background:white}'
        'th,td{border-bottom:1px solid #d4e0d7;text-align:left;padding:11px}'
        'small{color:#536b61}</style></head><body><main>'
        '<small>RETALLY / RESEARCH LAB 14 / M31 / INTERNAL ONLY</small>'
        '<h1>Original BLS real sectoral output: separate from BEA real gross output</h1>'
        '<p>Direct BLS API v2 annual-source grade in this run: <strong>'+
        escape(report["status"])+'</strong>. Source years authenticated in this '
        'execution: '+str(report["fresh_original_bls_source_year_cells_authenticated"])+
        ' of 24.</p><table><thead><tr><th>NAICS</th><th>BLS industry</th>'
        '<th>2017 output index</th><th>2024 output index</th><th>Change</th>'
        '</tr></thead><tbody>'+rows+'</tbody></table>'
        '<p>Parent NAICS 484 BLS real sectoral output +4.02%; Mission 29 Census'
        '/BLS-PPI illustrative adjusted revenue +'+escape(
            report["m29_aggregate_illustrative_census_ppi_revenue_proxy_2017_2024_pct"]
        )+'%. These differ by '+escape(
            report["bls_minus_ppi_proxy_descriptive_gap_percentage_points"]
        )+' percentage points. This is a <strong>measurement and source-coverage'
        ' distinction, NOT proof of a model error, official BEA real gross output'
        ' or freight invoice overcharges</strong>.</p>'
        '<p>'+escape(report["caveat"])+'</p>'
        '<p>Direct original BEA real gross output: <strong>NOT AUTHENTICATED</strong>.'
        ' An active BEA API user ID was not available; no key was created.</p>'
        '<p><a href="https://www.bls.gov/opub/hom/opt/calculation.htm">'
        'BLS sectoral output methodology</a></p></main></body></html>'
    )


def main()->None:
    p=argparse.ArgumentParser(description="Official BLS sectoral-output source, BEA gap held")
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--as-of-date",default=date.today().isoformat())
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline",action="store_true")
    mode.add_argument("--fetch-original",action="store_true")
    args=p.parse_args()
    as_of=date.fromisoformat(args.as_of_date)
    if args.fetch_original:
        try:
            source,digest=fetch_original_bls()
        except (OSError,TimeoutError):
            report=blocked(as_of=as_of)
        else:
            report=verify_origins(as_of=as_of,response=source,raw_sha256=digest)
    else:
        report=report_shell(as_of=as_of)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"bls_sectoral_output.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    (args.out/"bls_sectoral_output.html").write_text(
        render_html(report),encoding="utf-8"
    )
    print(json.dumps({
        "source_status":report["status"],
        "direct_bls_source_year_cells_verified":report[
            "fresh_original_bls_source_year_cells_authenticated"],
        "bea_original_real_gross_output_source_status":"NOT_AUTHENTICATED",
        "genuine_customer_invoices_verified":0,
        "receipt_sha256":report["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
