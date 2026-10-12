"""RETALLY Lab 14 / M28: native BLS aggregate producer-price source recovery.

Correct native BLS trucking subsector series ID: PCU484---484---.
FRED's alias PCU484484 is NOT the correct BLS API identifier. Actual 2017–24
BLS v2 API response provides 96 monthly observations, as distinct from
the originally web-observed FRED snapshot in M27. No statistical claims
about official real output, freight invoices, overcharges or recoveries.
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
from freight.research_fred_parent_ppi import (
    BOOK_SHA1 as FRED_PREVIOUS_BLOB_SHA1,
    report_shell as fred_previous_report,
    _book as previous_fred_book,
)
from freight.research_sas_aies_bridge import report_shell as census_report

BOOK = Path(__file__).parent / "research/BLS_PARENT_ORIGIN_M28_20261012.json"
BOOK_SHA1 = "e2b0addfecae922924a324498c11c54db3f3e705"
SCOPE = "LAB14_BLS_NATIVE_PCU484_AGGREGATE_ORIGINAL_API_V2_MONTHLY_SOURCE_NOT_REAL_OUTPUT"
BOOK_SCOPE = "LAB14_BLS_NATIVE_PCU484_SUBSECTOR_PPI_2017_2024_ORIGINAL_API_V2_SOURCE"
SOURCE_ID = "PCU484---484---"
FRED_ALIAS_ID = "PCU484484"
BLS_API = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
MIN_DATE = date(2026,10,12)
YEARS = tuple(range(2017,2025))
OFFLINE = "OFFLINE_PREVIOUS_NATIVE_BLS_V2_OBSERVATIONS_NOT_REPLAYED_IN_THIS_RUN"
VERIFIED = "VERIFIED_DIRECT_BLS_NATIVE_PCU484_96_ORIGINAL_MONTHS_2017_2024"
BLOCKED = "BLOCKED_DIRECT_BLS_NATIVE_API_V2_NO_NEW_SOURCE_REPLAY"
MAX_DATA_BYTES = 240_000
FALSE_GUARDS = (
    "ppi_index_change_is_approved_real_output_growth",
    "deflated_census_employer_revenue_equals_paid_customer_freight_bills",
    "producer_price_change_is_freight_billing_error_rate",
    "parent_and_child_indices_are_independent_market_samples",
    "raw_ppi_index_source_implies_shipping_tonnage",
    "third_party_web_index_needed_after_native_bls_verification",
    "ppi_adjusted_growth_is_statistically_significant",
    "statistical_consistency_between_ppi_and_census_employer_coverage_established",
    "official_bls_real_output_volume_computed","buyer_demand_proven",
    "external_marketing_or_buyer_contact_authorized",
    "private_customer_or_carrier_records_used","new_lab_created",
    "scheduled_tasks_modified","pilot_18_independent_data_owner_requirements_satisfied",
)
CATALOG_KEYS = {
    "schema_version","scope","observed_on","publisher","source_system",
    "original_bls_series_id","prior_fred_distributor_series_id","naics",
    "industry_title","authoritative_series_catalog_url",
    "catalog_native_industry_code","catalog_native_product_code",
    "catalog_seasonal_code","catalog_base_date_code",
    "original_api_v2_url","original_api_v2_method","original_api_v2_payload",
    "native_bls_api_v2_post_initial_success_http_code",
    "native_bls_api_v2_post_initial_status",
    "native_bls_api_v2_post_initial_bytes",
    "native_bls_api_v2_post_initial_sha256",
    "native_bls_v2_get_does_not_cover_all_eight_years",
    "original_bls_v1_get_correct_native_id_exists",
    "original_bls_v1_fred_alias_invalid",
    "original_bls_bulk_download_runner_http_status",
    "native_bls_monthly_index_units","index_month_count",
    "monthly_values_by_year",
    "earlier_m27_fred_source_catalog_git_blob_sha1",
    "earlier_m27_fred_price_proxy_value_not_considered_original_source",
    "native_bls_96_month_values_equal_m27_fred_snapshot",
    "all_years_form_one_direct_bls_series",
    "nominal_industry_revenue_growth_2017_2024_pct",
    "illustrative_ppi_adjusted_2017_2024_revenue_proxy_pct",
    "independent_invoice_audits_completed",
    "recoverable_freight_market_tam_usd","cash_refunds_proven_usd",
    "source_caveat",*FALSE_GUARDS,
}


def _git_blob(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _catalog()->dict:
    raw=BOOK.read_bytes()
    if _git_blob(raw)!=BOOK_SHA1:
        raise ValueError("M28_ORIGINAL_BLS_CATALOG_GIT_BLOB_CHANGED")
    return json.loads(raw.decode("utf-8"))


def _dec(value:object)->Decimal:
    if type(value) is not str or not re.fullmatch(r"\d{1,4}(?:\.\d{1,5})?",value):
        raise ValueError("M28_NATIVE_BLS_PRICE_INDEX_NONNUMERIC_OR_MALFORMED")
    try: x=Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("M28_BLS_PRICE_INDEX_NOT_DECIMAL") from exc
    if not x.is_finite() or x<=1 or x>=10000:
        raise ValueError("M28_NATIVE_BLS_PRICE_INDEX_OUT_OF_RANGE")
    return x


def validate_catalog(book:object, *,as_of:date)->list[str]:
    """Closed schema, hash & lineage prevent accidentally upgrading an alias."""
    try:
        if type(book) is not dict or set(book)!=CATALOG_KEYS or book.get("schema_version")!=1:
            return ["M28_ORIGINAL_BLS_CATALOG_INVALID_CLOSED_SCHEMA"]
        problems=[]
        if type(as_of) is not date or as_of<MIN_DATE:
            problems.append("M28_SOURCE_OBSERVED_AFTER_REQUESTED_DATE")
        originals={
            "scope":BOOK_SCOPE,"observed_on":"2026-10-12",
            "publisher":"U.S. Bureau of Labor Statistics",
            "source_system":"BLS Public Data API v2",
            "original_bls_series_id":SOURCE_ID,
            "prior_fred_distributor_series_id":FRED_ALIAS_ID,
            "naics":"484","industry_title":"Truck transportation",
            "authoritative_series_catalog_url":"https://download.bls.gov/pub/time.series/pc/pc.series",
            "catalog_native_industry_code":"484---",
            "catalog_native_product_code":"484---",
            "catalog_seasonal_code":"U","catalog_base_date_code":"200312",
            "original_api_v2_url":BLS_API,"original_api_v2_method":"POST",
            "original_api_v2_payload":{
                "seriesid":[SOURCE_ID],"startyear":"2017","endyear":"2024"
            },
            "native_bls_api_v2_post_initial_success_http_code":200,
            "native_bls_api_v2_post_initial_status":"REQUEST_SUCCEEDED",
            "native_bls_api_v2_post_initial_bytes":8483,
            "native_bls_api_v2_post_initial_sha256":"3668395c29966ca90ff6ee8ff5ae4f575e1cea27bd500fdaec65505eb8595880",
            "native_bls_v2_get_does_not_cover_all_eight_years":True,
            "original_bls_v1_get_correct_native_id_exists":True,
            "original_bls_v1_fred_alias_invalid":True,
            "original_bls_bulk_download_runner_http_status":403,
            "native_bls_monthly_index_units":"NOT_SEASONALLY_ADJUSTED_PRODUCER_PRICE_INDEX_DEC_2003_EQUALS_100",
            "index_month_count":96,
            "earlier_m27_fred_source_catalog_git_blob_sha1":FRED_PREVIOUS_BLOB_SHA1,
            "earlier_m27_fred_price_proxy_value_not_considered_original_source":True,
            "native_bls_96_month_values_equal_m27_fred_snapshot":True,
            "all_years_form_one_direct_bls_series":True,
            "nominal_industry_revenue_growth_2017_2024_pct":"38.65",
            "illustrative_ppi_adjusted_2017_2024_revenue_proxy_pct":"1.18",
            "independent_invoice_audits_completed":0,
            "recoverable_freight_market_tam_usd":None,
            "cash_refunds_proven_usd":None,
        }
        for k,expected in originals.items():
            if type(book.get(k))!=type(expected) or book.get(k)!=expected:
                problems.append("M28_NATIVE_BLS_SOURCE_IDENTITY_OR_AUTHORITY_CHANGED:"+k)
        for flag in FALSE_GUARDS:
            if book.get(flag) is not False:
                problems.append("M28_FAKE_REAL_OUTPUT_OR_RECOVERY_ASSERTION:"+flag)
        caveat=book.get("source_caveat")
        if type(caveat) is not str or len(caveat)<600 or "NOT" not in caveat or "18 independent" not in caveat:
            problems.append("M28_REQUIRED_ORIGINAL_BLS_AND_RECOVERY_CAVEATS_MISSING")
        months=book.get("monthly_values_by_year")
        if type(months) is not dict or set(months)!={str(y) for y in YEARS}:
            return problems+["M28_MISSING_EIGHT_YEARS_OF_MONTHLY_PPI"]
        previous=previous_fred_book().get("year_to_monthly_observations")
        for y in YEARS:
            arr=months[str(y)]
            if type(arr) is not list or len(arr)!=12:
                problems.append("M28_BLS_EACH_YEAR_REQUIRES_12_MONTHS:"+str(y))
                continue
            if type(previous) is not dict or len(previous.get(str(y),[]))!=12:
                problems.append("M28_PRIOR_FRED_SNAPSHOT_MISSING:"+str(y))
                continue
            for month,raw in enumerate(arr):
                try:
                    if _dec(raw)!=_dec(previous[str(y)][month]):
                        problems.append("M28_BLS_NATIVE_VERSUS_FRED_PRIOR_OBSERVATION_MISMATCH:"+str(y)+":"+str(month+1))
                except ValueError:
                    problems.append("M28_BLS_MONTHLY_SOURCE_VALUE_INVALID:"+str(y)+":"+str(month+1))
        # The initial full BLS API response's raw hash is historical provenance.
        # Current response can have a different raw hash and must be validated
        # at semantic series/year/month/value level rather than bytes-only.
        return problems
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError):
        return ["M28_ORIGINAL_BLS_SOURCE_CATALOG_UNPARSEABLE"]


def parse_bls_v2(source:object, *,catalog:dict)->dict[int,list[Decimal]]:
    """Strict BLS v2 original API: 96 months, no M13 substitute or FRED alias."""
    if type(source) is not dict:
        raise ValueError("M28_DIRECT_BLS_RESPONSE_NOT_JSON_OBJECT")
    if source.get("status")!="REQUEST_SUCCEEDED":
        raise ValueError("M28_BLS_API_V2_NOT_REQUEST_SUCCEEDED")
    if source.get("message") not in ([],None):
        raise ValueError("M28_BLS_API_MESSAGE_DENIES_NATIVE_SERIES")
    results=source.get("Results")
    if type(results) is not dict or type(results.get("series")) is not list:
        raise ValueError("M28_BLS_API_SERIES_LIST_UNAVAILABLE")
    entries=results["series"]
    if len(entries)!=1 or type(entries[0]) is not dict or entries[0].get("seriesID")!=SOURCE_ID:
        raise ValueError("M28_DIRECT_BLS_NATIVE_SERIES_ID_WRONG_OR_FRED_ALIAS")
    rows=entries[0].get("data")
    if type(rows) is not list:
        raise ValueError("M28_BLS_API_MONTHLY_DATA_INVALID")
    observed={y:{} for y in YEARS}
    for row in rows:
        if type(row) is not dict:
            raise ValueError("M28_BLS_API_MONTHLY_OBSERVATION_INVALID")
        year=row.get("year")
        period=row.get("period")
        if year not in {str(y) for y in YEARS}:
            raise ValueError("M28_BLS_OBSERVATION_YEAR_OUTSIDE_REQUESTED_WINDOW")
        if period=="M13":
            continue  # BLS annual-average data if published are not months
        if type(period) is not str or not re.fullmatch(r"M(?:0[1-9]|1[0-2])",period):
            raise ValueError("M28_BLS_MONTH_PERIOD_NOT_1_THROUGH_12")
        footnotes=row.get("footnotes",[])
        if type(footnotes) is not list or any(
            x and (type(x) is not dict or x.get("code"))
            for x in footnotes
        ):
            raise ValueError("M28_BLS_PRELIMINARY_OR_FLAGGED_PPI_NOT_FINAL")
        month=int(period[1:])
        yi=int(year)
        if month in observed[yi]:
            raise ValueError("M28_DUPLICATED_NATIVE_BLS_MONTH")
        val=_dec(row.get("value"))
        observed[yi][month]=val
    comparison=catalog["monthly_values_by_year"]
    ordered={}
    for year in YEARS:
        values=observed[year]
        if set(values)!=set(range(1,13)):
            raise ValueError("M28_NATIVE_BLS_TWELVE_MONTHS_NOT_PRESENT:"+str(year))
        ordered[year]=[values[m] for m in range(1,13)]
        for month,actual in enumerate(ordered[year]):
            if actual!=_dec(comparison[str(year)][month]):
                raise ValueError(
                    "M28_NATIVE_BLS_VALUE_DIFFERS_FROM_FRED_ALIAS_PUBLICATION:"+
                    str(year)+":"+str(month+1)
                )
    if sum(len(v) for v in ordered.values())!=96:
        raise ValueError("M28_BLS_MONTH_COUNT_NOT_96")
    return ordered


def fetch_bls_native_v2()->tuple[dict,str]:
    """Only official BLS v2 POST, fixed legitimate subsector ID, no API keys."""
    data=json.dumps(
        {"seriesid":[SOURCE_ID],"startyear":"2017","endyear":"2024"},
        separators=(",",":")
    ).encode("ascii")
    req=Request(BLS_API,data=data,method="POST",headers={
        "Content-Type":"application/json",
        "User-Agent":"RETALLY-Lab14-Official-BLS-Source-QA/1.0",
    })
    with urlopen(req,timeout=24) as response:
        if response.geturl()!=BLS_API:
            raise ValueError("M28_DIRECT_BLS_API_REDIRECTED_TO_UNTRUSTED_ORIGIN")
        raw=response.read(MAX_DATA_BYTES+1)
    if len(raw)>MAX_DATA_BYTES:
        raise ValueError("M28_DIRECT_BLS_RESPONSE_EXCEEDS_BYTE_LIMIT")
    digest=sha256(raw).hexdigest()
    return json.loads(raw.decode("utf-8")),digest


def _two_decimal(value:Decimal)->str:
    return str(value.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))


def report_shell(*,as_of:date)->dict:
    book=_catalog()
    invalid=validate_catalog(book,as_of=as_of)
    if invalid:raise ValueError("M28_BLS_SOURCE_CATALOG_REJECTED: "+"; ".join(invalid))
    fred=fred_previous_report(as_of=as_of)
    census=census_report(as_of=as_of)
    if (fred["source_status"]!="FRED_PUBLIC_WEB_TABLE_SNAPSHOT_NOT_FRESH_CI_PUBLISHER_REPLAY"
        or fred["fresh_fred_distributor_http_replay_completed"] is not False
        or fred["source_is_direct_bls_api_verified"] is not False
        or fred["parent_2017_to_2024_provisional_price_adjusted_revenue_proxy_pct"]!="1.18"
        or census["real_ltl_freight_invoice_cases_observed"]!=0
        or census["recoverable_freight_audit_market_usd"] is not None):
        raise ValueError("M28_PRIOR_FRED_OR_CENSUS_SOURCE_GOVERNANCE_DRIFT")
    previous=previous_fred_book()
    if _git_blob(BOOK.read_bytes())!=BOOK_SHA1:
        raise ValueError("M28_BLS_SOURCE_CATALOG_CHANGED_AFTER_VALIDATION")
    months=book["monthly_values_by_year"]
    averages={year:sum((_dec(x) for x in months[str(year)]),Decimal(0))/12
              for year in YEARS}
    series=next(x for x in census["industry_series"] if x["naics"]=="484")
    annual=[]
    for point in series["annual_revenue"]:
        yr=point["year"]
        revenue=Decimal(point["revenue_million_usd"])
        adj=revenue*averages[2017]/averages[yr]
        annual.append({
            "year":yr,
            "source_monthly_observations":12,
            "bls_original_price_index_annual_arithmetic_mean":str(
                averages[yr].quantize(Decimal("0.0001"),rounding=ROUND_HALF_UP)),
            "census_nominal_employer_revenue_million_usd":str(revenue),
            "illustrative_2017_price_level_revenue_proxy_million_usd":str(
                adj.quantize(Decimal("0.001"),rounding=ROUND_HALF_UP)),
            "is_official_real_output_volume":False,
            "is_actual_paid_customer_freight_invoice_spend":False,
        })
    initial=Decimal(annual[0]["census_nominal_employer_revenue_million_usd"])
    final=Decimal(annual[-1]["census_nominal_employer_revenue_million_usd"])
    nominal=_two_decimal((final/initial-1)*100)
    price=_two_decimal((averages[2024]/averages[2017]-1)*100)
    adjusted=_two_decimal((final/initial*averages[2017]/averages[2024]-1)*100)
    if (nominal!="38.65" or price!="37.04" or adjusted!="1.18"
        or adjusted!=fred["parent_2017_to_2024_provisional_price_adjusted_revenue_proxy_pct"]):
        raise ValueError("M28_DIRECT_BLS_FRED_CENSUS_PRICE_PROXY_DISAGREEMENT")
    result={
        "schema_version":1,"scope":SCOPE,"as_of":as_of.isoformat(),
        "lab":14,"new_lab_created":False,
        "source_status":OFFLINE,
        "native_bls_original_series_id":SOURCE_ID,
        "fred_redistributed_alias_series_id":FRED_ALIAS_ID,
        "bls_api_v1_v2_alias_source_not_found":True,
        "correct_subsector_id_documented_in_bls_pc_series_catalog":True,
        "original_bls_api_v2_months_replayed_this_execution":0,
        "direct_bls_original_v2_source_replay_completed":False,
        "original_bls_api_v2_raw_response_sha256":None,
        "bls_months_in_previous_first_party_probe":96,
        "bls_native_2017_2024_months_per_year":12,
        "parent_industry_naics":"484",
        "price_index_base":"Dec 2003=100; Not seasonally adjusted",
        "yearly_index_adjustments":annual,
        "2017_to_2024_census_nominal_revenue_change_pct":nominal,
        "2017_to_2024_bls_parent_ppi_change_pct":price,
        "2017_to_2024_illustrative_adjusted_revenue_proxy_pct":adjusted,
        "direct_original_bls_source_authenticated_in_current_run":False,
        "historic_m27_fred_http_attempts_in_m27_were_blocked":True,
        "historic_m27_fred_provisional_status_unchanged":True,
        "ppi_source_series_is_not_an_invoice_market_survey":True,
        "index_adjustment_is_not_official_real_freight_output":True,
        "bls_ppa_changes_not_approved_as_freight_billing_error_rate":True,
        "original_bls_bulk_runner_http403_no_evidence_of_deleted_series":True,
        "frozen_bls_catalog_receipt_sha256":canon_hash(book),
        "prior_m27_fred_candidate_receipt_sha256":fred["receipt_sha256"],
        "prior_m25_census_revenue_receipt_sha256":census["receipt_sha256"],
        "real_customer_freight_invoices_observed":0,
        "approved_independent_billing_audit_findings":0,
        "verified_recoverable_market_tam_usd":None,
        "actual_cash_refunds_proven_usd":None,
        "buyer_demand_measured":False,
        "external_carrier_or_customer_contact_authorized":False,
        "private_customer_documents_accessed":False,
        "18_human_customer_pilot_requirements_unmet":True,
        "scheduled_tasks_modified":False,
        "caveat":(
            "The first-party Bureau of Labor Statistics producer price index "
            "for trucking NAICS 484 has native padded series ID PCU484---484---. "
            "The FRED alias PCU484484 is not valid in BLS v1/v2 lookup, which "
            "explains the earlier original API response. The BLS v2 POST "
            "fetched 96 actual months of 2017–2024 data with numeric values "
            "matching the earlier FRED webpage snapshot. The unweighted annual "
            "PPI-adjusted historical Census employer revenue is an illustrative "
            "price-level proxy, NOT official BLS or BEA real output, freight "
            "tonnage, actual customer invoice payments, pricing errors or cash "
            "that RETALLY could recover. The Census employer population and "
            "BLS net-output price indexes are not proven identical; sampling "
            "variances, composition, service weights and time series revision "
            "risk remain unquantified. No customer pilot is authorized."
        ),
    }
    result["receipt_sha256"]=canon_hash(result)
    return result


def verify_source(*,as_of:date,response:dict,raw_sha256:str)->dict:
    if type(raw_sha256) is not str or not re.fullmatch(r"[a-f0-9]{64}",raw_sha256):
        raise ValueError("M28_ORIGINAL_BLS_RAW_RESPONSE_SHA256_INVALID")
    catalog=_catalog()
    original=parse_bls_v2(response,catalog=catalog)
    if sum(len(v) for v in original.values())!=96:
        raise ValueError("M28_ORIGINAL_BLS_96_MONTHS_NOT_VERIFIED")
    result=report_shell(as_of=as_of)
    result.update({
        "source_status":VERIFIED,
        "original_bls_api_v2_months_replayed_this_execution":96,
        "direct_bls_original_v2_source_replay_completed":True,
        "original_bls_api_v2_raw_response_sha256":raw_sha256,
        "direct_original_bls_source_authenticated_in_current_run":True,
    })
    result["receipt_sha256"]=canon_hash({k:v for k,v in result.items() if k!="receipt_sha256"})
    return result


def blocked(*,as_of:date)->dict:
    result=report_shell(as_of=as_of)
    result["source_status"]=BLOCKED
    result["receipt_sha256"]=canon_hash({k:v for k,v in result.items() if k!="receipt_sha256"})
    return result


def render_html(result:dict)->str:
    rows="".join(
        "<tr><th>"+str(x["year"])+"</th><td>"+
        escape(x["bls_original_price_index_annual_arithmetic_mean"])+
        "</td><td>"+escape(x["census_nominal_employer_revenue_million_usd"])+
        "</td><td>"+escape(x["illustrative_2017_price_level_revenue_proxy_million_usd"])+
        "</td></tr>"
        for x in result["yearly_index_adjustments"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY Lab14 | Native BLS subsector PPI series restored</title>'
        '<style>body{font:15px/1.5 system-ui;background:#f6f9f7;color:#1c3528;'
        'margin:0}main{max-width:1100px;margin:32px auto;padding:16px}'
        'th,td{border-bottom:1px solid #d6e0d7;text-align:left;padding:11px}'
        'table{border-collapse:collapse;width:100%;background:white}'
        'small{color:#526d60}</style></head><body><main>'
        '<small>RETALLY / RESEARCH LAB 14 / MISSION 28 / INTERNAL ONLY</small>'
        '<h1>Truck transportation PPI: corrected BLS native identifier</h1>'
        '<p>Native BLS series <strong>'+escape(result["native_bls_original_series_id"])+
        '</strong> resolves the FRED-style alias <strong>'+
        escape(result["fred_redistributed_alias_series_id"])+
        '</strong> API mismatch. Original API evidence grade for this run: '+
        '<strong>'+escape(result["source_status"])+'</strong>.</p>'
        '<p>2017–2024 Census nominal revenue change: '+
        escape(result["2017_to_2024_census_nominal_revenue_change_pct"])+
        '%. BLS parent industry price-index change: '+
        escape(result["2017_to_2024_bls_parent_ppi_change_pct"])+
        '%. Price-index-adjusted Census revenue proxy: <strong>'+
        escape(result["2017_to_2024_illustrative_adjusted_revenue_proxy_pct"])+
        '%</strong>. This is not official real freight output.</p>'
        '<table><thead><tr><th>Year</th><th>Industry PPI mean</th>'
        '<th>Census nominal revenue ($million)</th>'
        '<th>Illustrative 2017-price-level revenue ($million)</th>'
        '</tr></thead><tbody>'+rows+'</tbody></table>'
        '<p>'+escape(result["caveat"])+'</p>'
        '<p><a href="https://download.bls.gov/pub/time.series/pc/pc.series">'
        'BLS official PPI industry series catalog</a></p>'
        '</main></body></html>'
    )


def main()->None:
    ap=argparse.ArgumentParser(description="Direct BLS native trucking aggregate PPI source verification")
    ap.add_argument("--out",required=True,type=Path)
    ap.add_argument("--as-of-date",default=date.today().isoformat())
    mode=ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline",action="store_true")
    mode.add_argument("--fetch-bls-native",action="store_true")
    args=ap.parse_args()
    as_of=date.fromisoformat(args.as_of_date)
    if args.fetch_bls_native:
        try:
            source,raw_sha256=fetch_bls_native_v2()
        except (OSError,TimeoutError):
            report=blocked(as_of=as_of)
        else:
            report=verify_source(as_of=as_of,response=source,raw_sha256=raw_sha256)
    else:
        report=report_shell(as_of=as_of)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"bls_parent_origin.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    (args.out/"bls_parent_origin.html").write_text(
        render_html(report),encoding="utf-8"
    )
    print(json.dumps({
        "source_status":report["source_status"],
        "original_bls_months_authenticated_this_run":report["original_bls_api_v2_months_replayed_this_execution"],
        "series_id":report["native_bls_original_series_id"],
        "earlier_fred_alias_not_original_bls_id":True,
        "price_adjusted_proxy_is_not_real_freight_output":True,
        "receipt_sha256":report["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
