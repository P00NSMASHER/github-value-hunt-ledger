"""Lab 14 M26: original BLS trucking PPI and Census price-adjusted revenue proxy.

Monthly BLS PPI is a producer output PRICE index. The derived statistic
is an ILLUSTRATIVE 2017-index-level adjusted Census revenue proxy,
not official real freight output, paid invoices, shipping tonnage,
carrier billing errors, recoveries, or RETALLY TAM.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from hashlib import sha1, sha256
from html import escape
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

from freight.research_evidence_gate import canon_hash
from freight.research_sas_aies_bridge import (
    report_shell as census_2017_2024,
    OFFLINE as CENSUS_SOURCE_OFFLINE,
)

BOOK = Path(__file__).parent / "research/BLS_PPI_TRUCKING_2017_2024_20261012.json"
BOOK_SHA1 = "e507d9adf49244527e59e0a4eaa141fa6192a3ad"
SCOPE = "LAB14_BLS_PPI_2017_2024_PRICE_ADJUSTED_REVENUE_PROXY_NOT_REAL_FREIGHT_OUTPUT"
BOOK_SCOPE = "LAB14_BLS_PPI_2017_2024_INDUSTRY_PRICE_ADJUSTED_CENSUS_REVENUE_PROXY_NOT_OFFICIAL_OUTPUT"
OFFLINE = "OFFLINE_BLS_PPI_SNAPSHOT_NOT_REPLAYED_IN_THIS_RUN"
VERIFIED = "BLS_PUBLIC_API_ORIGINAL_192_MONTHLY_PPI_LEVELS_REPRODUCED"
BLOCKED = "BLOCKED_BLS_PUBLIC_API_UNREACHABLE_NO_NEW_SOURCE_REPLAY"
MIN_DATE = date(2026,10,12)
YEARS = tuple(range(2017,2025))
CODES = ("484121","484122")
SERIES = ("PCU484121484121","PCU484122484122")
API = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
MAX_REPLY = 500_000
FALSE_GUARDS = (
    "ppi_is_measured_customer_freight_invoice_error_rate",
    "price_adjusted_revenue_proxy_is_official_real_output_measure",
    "ppi_coverage_identical_to_census_industry_revenue_proven",
    "nominal_revenue_is_industry_freight_bill_payment_spend",
    "all_trucking_price_index_available_from_original_api",
    "price_adjustment_proves_caused_volume_shift",
    "statistical_significance_or_precision_proven",
    "buyer_demand_proven","external_marketing_or_outreach_authorized",
    "customer_or_carrier_data_imported",
    "real_customer_pilot_18_requirements_satisfied",
    "new_lab_created","scheduled_tasks_modified",
)
CATALOG_KEYS = {
    "schema_version","scope","observed_on","publisher","api_url",
    "method","payload","source_monthly_grain","annual_aggregation",
    "annual_revenue_source","revenue_source_scope","deflation_method",
    "index_base","industries",
    "all_trucking_484_source_probe_series_id",
    "all_trucking_484_original_bls_api_source_status",
    "all_trucking_484_ppi_adjusted_growth_pct",
    "original_bls_api_probe_receipt_sha256","year_range",
    "only_two_industry_codes_authorized_for_adjustment","source_caveat",
    "freight_recoverable_tam_usd","real_customer_invoices_verified",
    "actual_cash_recovered_usd",*FALSE_GUARDS,
}
CATALOG_SERIES_KEYS = {"naics","series_id","label","months_by_year"}
EXPECTED_LABELS={
    "484121":"General freight trucking, long-distance truckload",
    "484122":"General freight trucking, long-distance less-than-truckload",
}


def _blob(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _catalog()->dict:
    raw=BOOK.read_bytes()
    if _blob(raw)!=BOOK_SHA1:
        raise ValueError("M26_BLS_SOURCE_CATALOG_GIT_BLOB_CHANGED")
    return json.loads(raw.decode("utf-8"))


def _read_decimal(value:object)->Decimal:
    if type(value) is not str or not re.fullmatch(r"\d{1,5}(?:\.\d{1,5})?",value):
        raise ValueError("M26_BLS_PPI_MONTHLY_VALUE_NOT_FINITE_NUMERIC_STRING")
    try:
        x=Decimal(value)
    except InvalidOperation as err:
        raise ValueError("M26_BLS_NONDECIMAL_PRICE_INDEX") from err
    if not Decimal("1")<x<Decimal("10000") or not x.is_finite():
        raise ValueError("M26_BLS_PRICE_INDEX_OUTSIDE_ALLOWED_BOUNDS")
    return x


def _expected_months(book:dict)->dict[str,dict[int,list[str]]]:
    return {
        x["series_id"]:{int(year):values
                        for year,values in x["months_by_year"].items()}
        for x in book["industries"]
    }


def validate_catalog(book:object, *, as_of:date)->list[str]:
    try:
        if type(book) is not dict or set(book)!=CATALOG_KEYS or book.get("schema_version")!=1:
            return ["M26_PRIVATE_OR_UNEXPECTED_SOURCE_BOOK_SCHEMA"]
        problems=[]
        if type(as_of) is not date or as_of<MIN_DATE:
            problems.append("M26_SOURCE_BOOK_BEFORE_BLS_OBSERVATION_DATE")
        fixed={
            "scope":BOOK_SCOPE,"observed_on":"2026-10-12",
            "publisher":"U.S. Bureau of Labor Statistics",
            "api_url":API,"method":"POST",
            "payload":{"seriesid":list(SERIES),"startyear":"2017","endyear":"2024"},
            "source_monthly_grain":"NOT_SEASONALLY_ADJUSTED_INDUSTRY_NET_OUTPUT_PRODUCER_PRICE_INDEX",
            "annual_aggregation":"ARITHMETIC_MEAN_OF_EXACTLY_12_NONPRELIMINARY_MONTHLY_INDEX_LEVELS",
            "annual_revenue_source":"M25_REVISED_CENSUS_SAS_2017_TO_2021_AIES_LINKED_2022_TO_2024",
            "revenue_source_scope":"NAICS2017_US_EMPLOYER_INDUSTRY_NOMINAL_REVENUE",
            "deflation_method":"ILLUSTRATIVE_ANNUAL_INDUSTRY_PPI_OUTPUT_PRICE_ADJUSTMENT_ANCHORED_TO_2017_NOT_OFFICIAL_BLS_OR_CENSUS_REAL_OUTPUT",
            "index_base":"DECEMBER_2003_EQUALS_100_NOT_SEASONALLY_ADJUSTED_FOR_BOTH_ACCEPTED_SERIES",
            "all_trucking_484_source_probe_series_id":"PCU484484",
            "all_trucking_484_original_bls_api_source_status":"REJECTED_SERIES_DOES_NOT_EXIST_IN_BLS_V1_RESPONSE_THIS_PROBE",
            "all_trucking_484_ppi_adjusted_growth_pct":None,
            "original_bls_api_probe_receipt_sha256":"8a8a1e6d2eb3cf2fc8c86eb9268312ded3e51af78984a57d1ee481205b627153",
            "year_range":list(YEARS),
            "freight_recoverable_tam_usd":None,
            "real_customer_invoices_verified":0,
            "actual_cash_recovered_usd":None,
        }
        for k,val in fixed.items():
            if type(book.get(k))!=type(val) or book.get(k)!=val:
                problems.append("M26_BLS_IDENTITY_UNITS_OR_WINDOW_CHANGED:"+k)
        if book.get("only_two_industry_codes_authorized_for_adjustment") is not True:
            problems.append("M26_BLS_WRONG_INDUSTRY_COVERAGE")
        for flag in FALSE_GUARDS:
            if book.get(flag) is not False:
                problems.append("M26_FORGED_PRICE_OR_FREIGHT_AUDIT_EVIDENCE:"+flag)
        caveat=book.get("source_caveat")
        if type(caveat) is not str or len(caveat)<450 or "not" not in caveat.lower() or "2017" not in caveat:
            problems.append("M26_SOURCE_METHOD_CAVEATS_MISSING")
        items=book.get("industries")
        if type(items) is not list or len(items)!=2:
            return problems+["M26_EXACTLY_TWO_BLS_SOURCE_SERIES_REQUIRED"]
        seen=set()
        for item in items:
            if type(item) is not dict or set(item)!=CATALOG_SERIES_KEYS:
                problems.append("M26_PRICE_SERIES_SCHEMA_INVALID")
                continue
            code=item.get("naics")
            if code not in CODES or code in seen:
                problems.append("M26_UNKNOWN_OR_DUPLICATE_NAICS_PPI_SOURCE")
                continue
            seen.add(code)
            if (item.get("series_id")!="PCU"+code+code or
                item.get("label")!=EXPECTED_LABELS[code]):
                problems.append("M26_BLS_SERIES_ID_OR_LABEL_MISMATCH:"+code)
            dates=item.get("months_by_year")
            if type(dates) is not dict or set(dates)!={str(y) for y in YEARS}:
                problems.append("M26_MONTHLY_YEAR_COVERAGE_INCOMPLETE:"+code)
                continue
            for year in YEARS:
                monthly=dates[str(year)]
                if type(monthly) is not list or len(monthly)!=12:
                    problems.append("M26_PPI_TWELVE_MONTHS_REQUIRED:"+code+":"+str(year))
                    continue
                try:
                    for value in monthly:_read_decimal(value)
                except ValueError:
                    problems.append("M26_INVALID_PPI_SOURCE_VALUE:"+code+":"+str(year))
        if seen!=set(CODES):
            problems.append("M26_MISSING_PPI_INDUSTRY")
        return problems
    except (TypeError, KeyError, AttributeError, ValueError, OverflowError):
        return ["M26_CATALOG_MALFORMED"]


def validate_bls_source_response(source:dict, *, book:dict)->dict[str,dict[int,list[str]]]:
    """Validate all BLS original month/year rows, missing months, IDs & revisions."""
    if type(source) is not dict or source.get("status")!="REQUEST_SUCCEEDED":
        raise ValueError("M26_BLS_SOURCE_RESPONSE_NOT_REQUEST_SUCCEEDED")
    if source.get("message") not in ([],None):
        raise ValueError("M26_BLS_SOURCE_HAS_ERROR_OR_UNRESOLVED_MESSAGE")
    series=source.get("Results",{}).get("series")
    if type(series) is not list or len(series)!=2:
        raise ValueError("M26_BLS_PPI_TWO_VALID_SERIES_REQUIRED_NO_PARENT_SUBSTITUTION")
    result={}
    expected=_expected_months(book)
    for item in series:
        if type(item) is not dict:
            raise ValueError("M26_BLS_SOURCE_SERIES_SCHEMA_INVALID")
        sid=item.get("seriesID")
        if sid not in SERIES or sid in result:
            raise ValueError("M26_BLS_SOURCE_ID_MISSING_DUPLICATED_OR_UNKNOWN")
        rows=item.get("data")
        if type(rows) is not list:
            raise ValueError("M26_BLS_SOURCE_MONTHLY_RECORDS_MISSING")
        current={year:{} for year in YEARS}
        for row in rows:
            if type(row) is not dict:
                raise ValueError("M26_BLS_MONTHLY_OBSERVATION_SHAPE_INVALID")
            year=row.get("year")
            period=row.get("period")
            if year not in {str(y) for y in YEARS}:
                raise ValueError("M26_BLS_OUT_OF_SCOPE_YEAR")
            if period=="M13":
                continue  # A separately reported annual observation is not a month
            if type(period) is not str or not re.fullmatch(r"M(?:0[1-9]|1[0-2])",period):
                raise ValueError("M26_BLS_PPI_NOT_MONTHLY_OBSERVATION")
            month=int(period[1:])
            yr=int(year)
            if month in current[yr]:
                raise ValueError("M26_BLS_DUPLICATED_MONTH:"+sid+":"+year+period)
            notes=row.get("footnotes",[])
            if type(notes) is not list or any(
                x and (type(x) is not dict or x.get("code"))
                for x in notes
            ):
                raise ValueError("M26_BLS_PRELIMINARY_FLAG_OR_BAD_FOOTNOTE")
            value=row.get("value")
            _read_decimal(value)
            current[yr][month]=value
        ordered={}
        for yr,months in current.items():
            if set(months)!=set(range(1,13)):
                raise ValueError("M26_BLS_TWELVE_DISTINCT_MONTHS_MISSING:"+sid+":"+str(yr))
            observed=[months[n] for n in range(1,13)]
            if observed!=expected[sid][yr]:
                raise ValueError("M26_BLS_ORIGINAL_MONTHLY_INDEX_DRIFT_REQUIRES_HUMAN_REVIEW:"+sid+":"+str(yr))
            ordered[yr]=observed
        result[sid]=ordered
    if set(result)!=set(SERIES):
        raise ValueError("M26_BLS_SERIES_COVERAGE_INCOMPLETE")
    return result


def fetch_bls()->dict:
    book=_catalog()
    # Only original BLS v1 endpoint, two validated existing industry series;
    # no API key, access token, private data, or unapproved URL.
    payload=json.dumps(book["payload"],separators=(",",":")).encode("ascii")
    request=Request(API,data=payload,headers={
        "Content-Type":"application/json",
        "User-Agent":"RETALLY-Lab14-Public-PPI-Research/1.0",
    },method="POST")
    with urlopen(request,timeout=30) as response:
        if response.geturl()!=API:
            raise ValueError("M26_BLS_ORIGINAL_API_REDIRECTED")
        raw=response.read(MAX_REPLY+1)
    if len(raw)>MAX_REPLY:
        raise ValueError("M26_BLS_API_RESPONSE_OVER_LIMIT")
    return json.loads(raw)


def _dec_pct(value:Decimal)->str:
    return str(value.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))


def _source_snapshot(*,as_of:date)->tuple[dict,dict,dict]:
    book=_catalog()
    failures=validate_catalog(book,as_of=as_of)
    if failures:
        raise ValueError("M26_BLS_PINNED_SOURCE_INVALID: "+"; ".join(failures))
    census=census_2017_2024(as_of=as_of)
    if (census["source_status"]!=CENSUS_SOURCE_OFFLINE
        or census["real_ltl_freight_invoice_cases_observed"]!=0
        or census["recoverable_freight_audit_market_usd"] is not None
        or not census["human_pilot_18_independent_requirements_unmet"]):
        raise ValueError("M26_CENSUS_SOURCE_GOVERNANCE_REGRESSION")
    return book,census,_expected_months(book)


def report_shell(*,as_of:date)->dict:
    book,census,prices=_source_snapshot(as_of=as_of)
    source_values={x["naics"]:x for x in census["industry_series"]}
    comparisons=[]
    for code,sid in zip(CODES,SERIES):
        src=source_values[code]
        monthly=prices[sid]
        avg={year:sum((_read_decimal(v) for v in months),Decimal(0))/12
             for year,months in monthly.items()}
        anchor=avg[2017]
        annual=[]
        for row in src["annual_revenue"]:
            year=row["year"]
            nom=Decimal(row["revenue_million_usd"])
            index=avg[year]
            estimated=nom*anchor/index
            annual.append({
                "year":year,
                "census_nominal_revenue_million_usd":str(nom),
                "bls_months":12,
                "annual_average_ppi_index":str(index.quantize(Decimal("0.0001"),rounding=ROUND_HALF_UP)),
                "2017_price_level_adjusted_revenue_proxy_million_usd":str(
                    estimated.quantize(Decimal("0.001"),rounding=ROUND_HALF_UP)),
                "is_official_real_output_or_freight_tonnage":False,
                "is_recoverable_carrier_cash":False,
            })
        old=Decimal(src["annual_revenue"][0]["revenue_million_usd"])
        now=Decimal(src["annual_revenue"][-1]["revenue_million_usd"])
        nominal=(now/old-1)*100
        price=(avg[2024]/anchor-1)*100
        proxy=(now/old*anchor/avg[2024]-1)*100
        comparisons.append({
            "naics":code,"bls_series_id":sid,"industry":src["industry"],
            "annual_observations":annual,
            "2017_to_2024_nominal_census_revenue_change_pct":_dec_pct(nominal),
            "2017_to_2024_producer_output_price_index_change_pct":_dec_pct(price),
            "2017_to_2024_illustrative_price_adjusted_revenue_proxy_change_pct":_dec_pct(proxy),
            "difference_not_ltl_invoice_error_rate_or_refund":True,
            "price_adjusted_growth_is_not_official_output_growth":True,
        })
    result={
        "schema_version":1,"scope":SCOPE,"as_of":as_of.isoformat(),
        "lab":14,"new_lab_created":False,"source_status":OFFLINE,
        "original_bls_public_api_replayed_this_run":False,
        "source_monthly_observations_authenticated_in_this_run":0,
        "original_bls_source_receipt_sha256":None,
        "frozen_price_index_monthly_observations":192,
        "ppi_months_per_industry":96,
        "industry_price_adjustments":comparisons,
        "parent_trucking_naics484_price_adjusted_proxy_pct":None,
        "parent_484_source_rejected_by_bls_v1_api_in_original_probe":True,
        "original_monthly_ppi_source_unweighted_annual_mean":True,
        "price_deflation_proxies_use_2017_ppi_level_as_anchor":True,
        "census_data_revenue_measure_not_exactly_same_as_bls_ppi_coverage_proven":True,
        "single_source_family_bls_ppi_not_independent_market_survey":True,
        "frozen_bls_source_catalog_receipt_sha256":canon_hash(book),
        "m25_census_nominal_revenue_evidence_receipt_sha256":census["receipt_sha256"],
        "ppi_is_producer_price_not_customer_invoice_error_rate":True,
        "ppi_adjusted_revenue_proxy_not_official_bls_real_output_measure":True,
        "real_customer_freight_invoices_observed":0,
        "actual_adjudicated_customer_overcharges":0,
        "eligible_recovery_market_tam_usd":None,
        "actual_retally_cash_recovered_usd":None,
        "buyer_demand_established":False,
        "externally_publish_or_contact_customers_carriers":False,
        "customer_or_carrier_private_data_used":False,
        "human_pilot_18_requirements_unmet":True,
        "scheduled_tasks_modified":False,
        "caveat":(
            "These are illustrative, historical BLS industry Producer Price "
            "Index-adjusted Census employer revenue proxies. Producer prices "
            "received by industry sellers differ from customer paid freight "
            "invoice rates and fees. Simple annual means from 12 unadjusted "
            "monthly PPI levels do not fully account for composition, non-price "
            "changes, variations in Census/PPI population coverage, service "
            "quality, aggregation weights, measurement errors or source "
            "revisions. No official real gross output volume, tonnage or "
            "inflation-adjusted customer demand is calculated. The original "
            "BLS public API rejected the parent trucking NAICS 484 series, "
            "so no all-trucking price-adjusted estimate is invented. No "
            "bill overcharge frequency, recoverable funds, customers or "
            "cash recovery has been observed."
        ),
    }
    result["receipt_sha256"]=canon_hash(result)
    return result


def verify_source(*,as_of:date, response:dict)->dict:
    book,_,_= _source_snapshot(as_of=as_of)
    observations=validate_bls_source_response(response,book=book)
    if sum(len(months) for years in observations.values() for months in years.values())!=192:
        raise ValueError("M26_BLS_SOURCE_192_MONTHS_NOT_FULLY_VERIFIED")
    result=report_shell(as_of=as_of)
    result["source_status"]=VERIFIED
    result["original_bls_public_api_replayed_this_run"]=True
    result["source_monthly_observations_authenticated_in_this_run"]=192
    result["original_bls_source_receipt_sha256"]=canon_hash({
        "api_endpoint":API,
        "request_payload":book["payload"],
        "month_records":observations,
    })
    result["receipt_sha256"]=canon_hash({k:v for k,v in result.items() if k!="receipt_sha256"})
    return result


def blocked(*,as_of:date)->dict:
    result=report_shell(as_of=as_of)
    result["source_status"]=BLOCKED
    result["receipt_sha256"]=canon_hash({k:v for k,v in result.items() if k!="receipt_sha256"})
    return result


def render_html(r:dict)->str:
    rows="".join(
        "<tr><th>"+escape(item["naics"])+"</th><td>"+
        escape(item["industry"])+"</td><td>"+
        escape(item["2017_to_2024_nominal_census_revenue_change_pct"])+
        "%</td><td>"+escape(item["2017_to_2024_producer_output_price_index_change_pct"])+
        "%</td><td>"+escape(item["2017_to_2024_illustrative_price_adjusted_revenue_proxy_change_pct"])+
        "%</td></tr>"
        for item in r["industry_price_adjustments"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY Lab 14 | BLS PPI illustrative industry revenue adjustments</title>'
        '<style>body{font:16px/1.5 system-ui;background:#f5f8f6;color:#173829;'
        'margin:0}main{max-width:1050px;margin:35px auto;padding:18px}'
        'th,td{padding:12px;border-bottom:1px solid #d5dfd6;text-align:left}'
        'table{width:100%;background:white;border-collapse:collapse}'
        'small{color:#5b7262}</style></head><body><main>'
        '<small>RETALLY / EXISTING RESEARCH LAB 14 / M26 / INTERNAL ONLY</small>'
        '<h1>Nominal Census revenue versus BLS industry producer-price adjustment</h1>'
        '<p><strong>'+escape(r["source_status"])+'</strong>. '
        'Comparison does NOT represent official real output, customer freight '
        'billing-error rates, refunds, tonnage or recoverable market size.</p>'
        '<table><thead><tr><th>NAICS</th><th>Industry</th>'
        '<th>2017–2024 nominal revenue</th><th>BLS output price index</th>'
        '<th>Illustrative price-adjusted proxy</th></tr></thead>'
        '<tbody>'+rows+'</tbody></table>'
        '<p>All trucking (NAICS 484): not verified from the original BLS API '
        'and intentionally excluded.</p><p>'+escape(r["caveat"])+
        '</p><p><a href="https://www.bls.gov/ppi/overview.htm">'
        'Bureau of Labor Statistics Producer Price Index methods</a></p>'
        '</main></body></html>'
    )


def main()->None:
    p=argparse.ArgumentParser(description="Original BLS public PPI price index research, not recovery claims")
    p.add_argument("--as-of-date",default=date.today().isoformat())
    p.add_argument("--out",required=True,type=Path)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline",action="store_true")
    mode.add_argument("--fetch-original",action="store_true")
    args=p.parse_args()
    as_of=date.fromisoformat(args.as_of_date)
    if args.fetch_original:
        try:
            response=fetch_bls()
        except (OSError,TimeoutError):
            report=blocked(as_of=as_of)
        else:
            report=verify_source(as_of=as_of,response=response)
    else:
        report=report_shell(as_of=as_of)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"bls_ppi_adjustment.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    (args.out/"bls_ppi_adjustment.html").write_text(
        render_html(report),encoding="utf-8")
    print(json.dumps({
        "source_status":report["source_status"],
        "authenticated_monthly_observations":report["source_monthly_observations_authenticated_in_this_run"],
        "industries_adjusted":len(report["industry_price_adjustments"]),
        "parent_trucking_proxy_status":"BLOCKED_UNVERIFIED",
        "real_customer_recoveries_established":False,
        "receipt_sha256":report["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
