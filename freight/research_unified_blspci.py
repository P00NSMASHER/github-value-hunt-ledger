"""RETALLY Lab 14 / Mission 29: one current-source BLS trucking PPI report.

A single first-party BLS API v2 request authenticates 288 monthly producer
price observations across parent NAICS 484 and nested 484121/484122 children.
The Census 2017–2024 employer revenue inputs were previously verified in M25,
not refetched here. All index-adjusted revenue figures are ILLUSTRATIVE,
not official real output, tonnage, invoice errors, recoveries or TAM.
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
from freight.research_bls_parent_origin import (
    _catalog as original_parent,
    validate_catalog as validate_parent_catalog,
    SOURCE_ID as PARENT_BLS_ID,
    report_shell as earlier_parent,
)
from freight.research_bls_ppi_bridge import (
    _catalog as original_children,
    validate_catalog as validate_child_catalog,
    CODES as CHILD_CODES,
    SERIES as CHILD_BLS_IDS,
    report_shell as earlier_children,
)
from freight.research_sas_aies_bridge import (
    report_shell as original_census,
    OFFLINE as CENSUS_OFFLINE,
)

BOOK = Path(__file__).parent / "research/BLS_TRUCKING_UNIFIED_SOURCE_POLICY_M29_20261012.json"
BOOK_SHA1 = "885d48630dc912bbb959fbdd1180b1a9c81299b3"
BLS_API = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
MIN_DATE = date(2026, 10, 12)
YEARS = tuple(range(2017, 2025))
NAICS = ("484", "484121", "484122")
PPI_SERIES = (PARENT_BLS_ID, *CHILD_BLS_IDS)
PPI_MAP = dict(zip(NAICS, PPI_SERIES))
SCOPE = "LAB14_M29_UNIFIED_DIRECT_BLS_TRUCKING_PPI_CONTEXT_NOT_REAL_FREIGHT_OUTPUT"
POLICY_SCOPE = "LAB14_M29_CURRENT_SOURCE_UNIFIED_ORIGINAL_BLS_THREE_TRUCKING_INDUSTRY_SERIES_NOT_REAL_OUTPUT"
OFFLINE = "M29_OFFLINE_PRIOR_BLS_SOURCE_OBSERVATIONS_NO_FRESH_THREE_SERIES_REPLAY"
VERIFIED = "M29_DIRECT_BLS_V2_288_MONTHS_ALL_THREE_INDUSTRIES_AUTHENTICATED"
BLOCKED = "M29_BLS_V2_UNAVAILABLE_NO_FRESH_THREE_INDUSTRY_SOURCE_PROOF"
MAX_RESPONSE = 500_000


def _blob_id(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _policy() -> dict:
    raw = BOOK.read_bytes()
    if _blob_id(raw) != BOOK_SHA1:
        raise ValueError("M29_FROZEN_BLS_SOURCE_POLICY_GIT_BLOB_CHANGED")
    return json.loads(raw.decode("utf-8"))


def validate_policy(data: object, *, as_of: date) -> list[str]:
    """Require exact original policy plus trust and noncommercial invariants."""
    try:
        if type(data) is not dict:
            return ["M29_INVALID_BLS_SOURCE_POLICY"]
        errors = []
        if type(as_of) is not date or as_of < MIN_DATE:
            errors.append("M29_BEFORE_BLS_SOURCE_OBSERVATION_DATE")
        if data != _policy():
            errors.append("M29_SOURCE_POLICY_OR_PROHIBITED_EVIDENCE_CLAIM_CHANGED")
        if (data.get("schema_version") != 1
            or data.get("scope") != POLICY_SCOPE
            or data.get("publisher") != "U.S. Bureau of Labor Statistics"
            or data.get("live_api_url") != BLS_API
            or data.get("live_api_method") != "POST"):
            errors.append("M29_SOURCE_PUBLISHER_SCOPE_INVALID")
        if data.get("source_api_payload") != {
            "seriesid": list(PPI_SERIES),
            "startyear": "2017", "endyear": "2024",
        }:
            errors.append("M29_SOURCE_SERIES_ID_YEAR_WINDOW_INVALID")
        if data.get("required_monthly_observations_total") != 288 or (
            data.get("required_monthly_observations_per_series") != 96
            or data.get("required_months_per_year") != 12
            or data.get("required_years") != list(YEARS)
        ):
            errors.append("M29_MONTHLY_GRANULARITY_OR_YEAR_COVERAGE_INVALID")
        if ([x.get("naics") for x in data.get("series", [])] != list(NAICS)
            or [x.get("id") for x in data.get("series", [])] != list(PPI_SERIES)):
            errors.append("M29_NATIVE_BLS_CORRECT_SERIES_MAPPING_REQUIRED")
        if data.get("first_full_three_series_source_probe_run_id") != 38274002011:
            errors.append("M29_ORIGINAL_THREE_SERIES_PROBE_ID_CHANGED")
        if data.get("historical_m26_parent_missing_status_preserved_as_historical") is not True or (
            data.get("historical_m27_fred_timeout_preserved_as_historical") is not True
        ):
            errors.append("M29_HISTORICAL_M26_M27_EVIDENCE_NOT_PRESERVED")
        for false_key in (
            "adjusted_revenue_is_official_bea_or_bls_real_output",
            "consumer_invoice_payments_implied_by_census_employer_revenue",
            "price_index_is_customer_rate_overcharge_percentage",
            "aggregate_trucking_is_sum_of_children",
            "december_endpoint_is_annual_average",
            "real_freight_shipping_volume_measured",
            "real_cargo_tonnage_measured",
            "ppi_yearly_series_stacking_creates_independent_survey_samples",
            "producer_price_changes_prove_real_customer_demand",
            "confidence_intervals_calculated",
            "external_recovery_market_claims_allowed",
            "pilot_18_real_customer_authorizations_satisfied",
            "new_lab_created","scheduled_tasks_modified",
            "customer_or_carrier_private_data_ingested",
        ):
            if data.get(false_key) is not False:
                errors.append("M29_UNSUPPORTED_SOURCE_OR_RECOVERY_CLAIM:"+false_key)
        for key,value in (
            ("actual_retally_refunds_usd",None),
            ("recoverable_ltl_market_tam_usd",None),
            ("real_customer_paid_freight_invoices_count",0),
        ):
            if type(data.get(key)) != type(value) or data.get(key) != value:
                errors.append("M29_FALSE_CLIENT_INVOICES_OR_RECOVERY_MARKET:"+key)
        return errors
    except (ValueError,KeyError,AttributeError,TypeError):
        return ["M29_SOURCE_POLICY_UNREADABLE"]


def _price_grid(*, as_of: date) -> tuple[dict, dict, dict]:
    policy = _policy()
    mistakes = validate_policy(policy, as_of=as_of)
    if mistakes:
        raise ValueError("M29_POLICY_INVALID:" + "; ".join(mistakes))
    parent = original_parent()
    children = original_children()
    parent_errors = validate_parent_catalog(parent, as_of=as_of)
    child_errors = validate_child_catalog(children, as_of=as_of)
    if parent_errors or child_errors:
        raise ValueError("M29_PRIOR_BLS_NATIVE_SOURCE_CATALOG_CHANGED:" +
                         ";".join(parent_errors+child_errors))
    mapped = {
        PARENT_BLS_ID: {
            year: [Decimal(x) for x in parent["monthly_values_by_year"][str(year)]]
            for year in YEARS
        },
    }
    for item in children["industries"]:
        if item["series_id"] not in CHILD_BLS_IDS:
            raise ValueError("M29_UNAUTHORIZED_CHILD_BLS_SERIES")
        mapped[item["series_id"]] = {
            year: [Decimal(x) for x in item["months_by_year"][str(year)]]
            for year in YEARS
        }
    if set(mapped) != set(PPI_SERIES) or any(
        set(years) != set(YEARS) or any(len(months) != 12 for months in years.values())
        for years in mapped.values()
    ):
        raise ValueError("M29_PRIOR_BLS_288_MONTHLY_SOURCE_VALUES_INCOMPLETE")
    return policy, mapped, {"parent":parent,"children":children}


def _source_number(value: object) -> Decimal:
    if type(value) is not str or not re.fullmatch(r"\d{1,5}(?:\.\d{1,5})?",value):
        raise ValueError("M29_BLS_PPI_MONTHLY_PRICE_NONDECIMAL_OR_MISSING")
    try:
        dec=Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("M29_BAD_BLS_PPI_DECIMAL") from exc
    if not dec.is_finite() or not 1 < dec < 10000:
        raise ValueError("M29_BLS_PPI_MONTHLY_PRICE_OUT_OF_RANGE")
    return dec


def validate_first_party_response(source: object, *, expected: dict) -> dict:
    """Only a complete one-request 3-series v2 response authenticates new data."""
    if type(source) is not dict or source.get("status") != "REQUEST_SUCCEEDED":
        raise ValueError("M29_BLS_PUBLIC_API_NOT_REQUEST_SUCCEEDED")
    if source.get("message") not in ([],None):
        raise ValueError("M29_BLS_API_SERIES_ERROR_MESSAGE_PRESENT")
    body=source.get("Results")
    if type(body) is not dict or type(body.get("series")) is not list:
        raise ValueError("M29_BLS_API_SERIES_CONTAINER_INVALID")
    series=body["series"]
    if len(series)!=3:
        raise ValueError("M29_REQUIRE_EXACTLY_THREE_INDUSTRY_SERIES")
    output={}
    for item in series:
        if type(item) is not dict:
            raise ValueError("M29_BLS_SERIES_RECORD_INVALID")
        sid=item.get("seriesID")
        if sid not in PPI_SERIES or sid in output:
            raise ValueError("M29_DUPLICATE_UNKNOWN_OR_FRED_ALIAS_BLS_SERIES")
        rows=item.get("data")
        if type(rows) is not list:
            raise ValueError("M29_BLS_MONTHLY_SOURCE_ROWS_INVALID")
        byyear={y:{} for y in YEARS}
        for row in rows:
            if type(row) is not dict:
                raise ValueError("M29_BLS_RECORD_NOT_OBJECT")
            year=row.get("year")
            period=row.get("period")
            if year not in {str(y) for y in YEARS}:
                raise ValueError("M29_BLS_OUT_OF_WINDOW_YEAR")
            if period=="M13":
                continue  # Annual-average period is never a thirteenth month
            if type(period) is not str or not re.fullmatch(r"M(?:0[1-9]|1[0-2])",period):
                raise ValueError("M29_BLS_SOURCE_NOT_CALENDAR_MONTH")
            flags=row.get("footnotes",[])
            if type(flags) is not list or any(
                flag and (type(flag) is not dict or flag.get("code"))
                for flag in flags
            ):
                raise ValueError("M29_BLS_FLAGGED_OR_PRELIMINARY_PPI")
            value=_source_number(row.get("value"))
            yi=int(year)
            month=int(period[1:])
            if month in byyear[yi]:
                raise ValueError("M29_DUPLICATE_BLS_MONTH")
            byyear[yi][month]=value
        year_grid={}
        for year in YEARS:
            row=byyear[year]
            if set(row)!=set(range(1,13)):
                raise ValueError("M29_INCOMPLETE_TWELVE_MONTH_YEAR:"+sid+":"+str(year))
            actual=[row[m] for m in range(1,13)]
            if actual!=expected[sid][year]:
                raise ValueError("M29_BLS_NATIVE_MONTH_VALUE_REVISED_HUMAN_REVIEW_REQUIRED:"+sid+":"+str(year))
            year_grid[year]=[str(x) for x in actual]
        output[sid]=year_grid
    if set(output)!=set(PPI_SERIES) or sum(
        len(row) for series in output.values() for row in series.values()
    )!=288:
        raise ValueError("M29_ALL_288_BLS_SOURCE_MONTHS_NOT_REPRODUCED")
    return output


def _pct(x: Decimal) -> str:
    return str(x.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))


def report_shell(*, as_of: date) -> dict:
    policy,price,book=_price_grid(as_of=as_of)
    census=original_census(as_of=as_of)
    old_parent=earlier_parent(as_of=as_of)
    old_children=earlier_children(as_of=as_of)
    if (census["source_status"]!=CENSUS_OFFLINE
        or census["real_ltl_freight_invoice_cases_observed"]!=0
        or census["recoverable_freight_audit_market_usd"] is not None
        or census["human_pilot_18_independent_requirements_unmet"] is not True
        or old_parent["source_status"]!=
            "OFFLINE_PREVIOUS_NATIVE_BLS_V2_OBSERVATIONS_NOT_REPLAYED_IN_THIS_RUN"
        or old_parent["native_bls_original_series_id"]!=PARENT_BLS_ID
        or old_children["source_status"]!=
            "OFFLINE_BLS_PPI_SNAPSHOT_NOT_REPLAYED_IN_THIS_RUN"
        or old_children["parent_trucking_naics484_price_adjusted_proxy_pct"] is not None):
        raise ValueError("M29_EXISTING_CENSUS_BLS_LINEAGE_OR_GOVERNANCE_INCONSISTENT")
    census_code={r["naics"]:r for r in census["industry_series"]}
    industry_rows=[]
    for code in NAICS:
        sid=PPI_MAP[code]
        annual_source=census_code[code]["annual_revenue"]
        means={year:sum(price[sid][year],Decimal(0))/12 for year in YEARS}
        decs={year:price[sid][year][11] for year in YEARS}
        start=Decimal(annual_source[0]["revenue_million_usd"])
        end=Decimal(annual_source[-1]["revenue_million_usd"])
        if start<=0 or end<=0:
            raise ValueError("M29_CENSUS_SOURCE_REVENUE_WRONG_POPULATION_OR_ZERO")
        nominal=(end/start-1)*100
        meanindex=(means[2024]/means[2017]-1)*100
        annual_adjusted=(end/start*means[2017]/means[2024]-1)*100
        december_index=(decs[2024]/decs[2017]-1)*100
        december_adjusted=(end/start*decs[2017]/decs[2024]-1)*100
        observed_years=[]
        for row in annual_source:
            year=row["year"]
            amount=Decimal(row["revenue_million_usd"])
            corrected=amount*means[2017]/means[year]
            observed_years.append({
                "year":year,
                "original_census_nominal_revenue_million_usd":str(amount),
                "original_bls_annual_month_count":12,
                "original_bls_annual_mean_index":str(
                    means[year].quantize(Decimal("0.0001"),rounding=ROUND_HALF_UP)),
                "illustrative_2017_index_level_revenue_proxy_million_usd":str(
                    corrected.quantize(Decimal("0.001"),rounding=ROUND_HALF_UP)),
                "official_real_output":False,
            })
        industry_rows.append({
            "naics":code,
            "industry":census_code[code]["industry"],
            "bls_native_series_id":sid,
            "original_bls_months_in_prior_catalog":96,
            "annual_observations":observed_years,
            "2017_to_2024_census_nominal_revenue_change_pct":_pct(nominal),
            "2017_to_2024_bls_annual_mean_output_price_change_pct":_pct(meanindex),
            "2017_to_2024_illustrative_annual_mean_price_adjusted_revenue_pct":_pct(annual_adjusted),
            "2017_to_2024_december_endpoint_price_change_pct":_pct(december_index),
            "2017_to_2024_december_endpoint_price_adjusted_revenue_pct":_pct(december_adjusted),
            "december_minus_annual_mean_adjusted_change_percentage_points":_pct(
                december_adjusted-annual_adjusted),
            "year_end_sensitivity_is_not_a_comparable_annual_revenue_deflator":True,
            "is_official_bls_real_output_volume_or_freight_spend":False,
            "producer_price_is_a_freight_billing_error_rate":False,
        })
    bycode={r["naics"]:r for r in industry_rows}
    if [bycode[c]["2017_to_2024_illustrative_annual_mean_price_adjusted_revenue_pct"]
        for c in NAICS] != ["1.18","2.82","-1.89"]:
        raise ValueError("M29_DIRECT_BLS_PRIOR_PRICE_PROXY_VALUES_CHANGED")
    if [bycode[c]["2017_to_2024_census_nominal_revenue_change_pct"]
        for c in NAICS] != ["38.65","43.48","40.93"]:
        raise ValueError("M29_CENSUS_NOMINAL_REVENUE_PREVIOUS_M25_CHANGED")
    if (bycode["484122"]["2017_to_2024_december_endpoint_price_adjusted_revenue_pct"]!="1.60"
        or bycode["484122"]["december_minus_annual_mean_adjusted_change_percentage_points"]!="3.49"):
        raise ValueError("M29_LTL_ENDPOINT_METHODOLOGY_SENSITIVITY_MISSING")
    result={
        "schema_version":1,"scope":SCOPE,"lab":14,"new_lab_created":False,
        "as_of":as_of.isoformat(),
        "status":OFFLINE,
        "current_evidence_priority":"M29_UNIFIED_NATIVE_BLS_PRODUCER_PRICE_INDEX_SOURCE",
        "source_type":"DIRECT_FIRST_PARTY_BLS_API_V2",
        "source_api":BLS_API,
        "source_series_ids":list(PPI_SERIES),
        "current_original_bls_source_replayed_this_run":False,
        "current_source_authenticated_month_count":0,
        "original_bls_response_sha256":None,
        "historical_original_bls_months_in_pinned_catalogs":288,
        "historical_m26_missing_parent_was_wrong_alias_not_deleted_bls_series":True,
        "historical_m27_fred_source_timeout_remains_true":True,
        "m28_native_parent_id_supersedes_invalid_fred_alias_for_current_reports":True,
        "legacy_source_reports_kept_as_historical_evidence":True,
        "naics484_is_parent_of_484121_and_484122_non_additive":True,
        "revenue_source_years":"2017_2021_SAS_REVISED_2022_2024_AIES_LINKED_HISTORICAL",
        "independent_customer_invoice_and_recovery_evidence_established":False,
        "industry_comparisons":industry_rows,
        "industry_counts":3,
        "source_policy_receipt_sha256":canon_hash(policy),
        "prior_original_bls_parent_source_receipt_sha256":old_parent["receipt_sha256"],
        "prior_original_bls_child_source_receipt_sha256":old_children["receipt_sha256"],
        "prior_census_eight_year_source_receipt_sha256":census["receipt_sha256"],
        "adjustments_measure_official_real_freight_output":False,
        "comparisons_are_not_inflation_adjusted_client_freight_billing_spend":True,
        "december_endpoint_sensitivity_is_not_a_statistical_confidence_interval":True,
        "producer_price_indices_are_not_paid_invoice_error_rates":True,
        "actual_paid_customer_freight_invoices_observed":0,
        "independently_adjudicated_carrier_overcharges":0,
        "actual_retally_cash_recovered_usd":None,
        "freight_recovery_market_tam_usd":None,
        "customer_buyers_with_verified_demand":0,
        "commercial_recovery_claims_or_external_contact_authorized":False,
        "private_customer_or_carrier_records_ingested":False,
        "original_18_independent_pilot_requirements_still_unmet":True,
        "scheduled_tasks_created_or_modified":False,
        "caveat":(
            "One original BLS public data API v2 request can verify eight "
            "years of parent and child trucking producer net-output price "
            "index levels (288 months). Parent NAICS 484 includes 484121 "
            "and 484122, so their indexed series and revenue populations "
            "are overlapping, not additive markets. Nominal Census employer "
            "industry revenue and BLS industry price coverage differ "
            "potentially in composition, establishment coverage and weights. "
            "The annual-mean industry PPI-adjusted revenue series is only an "
            "ILLUSTRATIVE sensitivity proxy, not official BLS/BEA real output, "
            "physical freight tonnage, actual customer-paid invoices or "
            "recoverable refunds. Using December endpoint ratios instead "
            "of annual-mean price ratios can flip the LTL proxy's sign; "
            "December endpoint changes are not equivalent to annual "
            "revenue-compatible deflation and cannot establish a second "
            "independent volume estimate. Neither method is statistically "
            "validated against real invoices. All 18 independently "
            "permissioned customer pilot approvals remain unmet."
        ),
    }
    result["receipt_sha256"]=canon_hash(result)
    return result


def verify_original_bls(*, as_of: date, response: dict, raw_sha256: str) -> dict:
    if type(raw_sha256) is not str or not re.fullmatch(r"[0-9a-f]{64}",raw_sha256):
        raise ValueError("M29_BLS_PUBLISHER_RAW_RESPONSE_SHA256_INVALID")
    _, expected, _=_price_grid(as_of=as_of)
    verified=validate_first_party_response(response,expected=expected)
    result=report_shell(as_of=as_of)
    result.update({
        "status":VERIFIED,
        "current_original_bls_source_replayed_this_run":True,
        "current_source_authenticated_month_count":288,
        "original_bls_response_sha256":raw_sha256,
        "current_evidence_priority":"M29_FRESH_DIRECT_BLS_API_V2_SOURCE_288_MONTHS",
    })
    result["fresh_source_semantic_receipt_sha256"]=canon_hash({
        "bls_publisher_url":BLS_API,
        "native_series_ids":list(PPI_SERIES),
        "monthly_observations":verified,
    })
    result["receipt_sha256"]=canon_hash({
        k:v for k,v in result.items() if k!="receipt_sha256"
    })
    return result


def blocked(*,as_of:date) -> dict:
    result=report_shell(as_of=as_of)
    result["status"]=BLOCKED
    result["receipt_sha256"]=canon_hash({
        k:v for k,v in result.items() if k!="receipt_sha256"
    })
    return result


def fetch_original_bls() -> tuple[dict,str]:
    request_payload={
        "seriesid":list(PPI_SERIES),
        "startyear":"2017","endyear":"2024",
    }
    req=Request(BLS_API,
                data=json.dumps(request_payload,separators=(",",":")).encode("ascii"),
                headers={"Content-Type":"application/json",
                         "User-Agent":"RETALLY-Lab14-Public-BLS-Unified-Source-Replay/1.0"},
                method="POST")
    with urlopen(req,timeout=30) as response:
        if response.geturl()!=BLS_API:
            raise ValueError("M29_BLS_API_REDIRECTED_NOT_ORIGINAL_PUBLISHER")
        raw=response.read(MAX_RESPONSE+1)
    if len(raw)>MAX_RESPONSE:
        raise ValueError("M29_BLS_API_RESPONSE_OVER_BYTE_LIMIT")
    return json.loads(raw.decode("utf-8")),sha256(raw).hexdigest()


def render_html(report: dict) -> str:
    rows="".join(
        "<tr><th>"+escape(item["naics"])+"</th><td>"+
        escape(item["bls_native_series_id"])+"</td><td>"+
        escape(item["2017_to_2024_census_nominal_revenue_change_pct"])+
        "%</td><td>"+
        escape(item["2017_to_2024_bls_annual_mean_output_price_change_pct"])+
        "%</td><td>"+
        escape(item["2017_to_2024_illustrative_annual_mean_price_adjusted_revenue_pct"])+
        "%</td><td>"+
        escape(item["2017_to_2024_december_endpoint_price_adjusted_revenue_pct"])+
        "%</td></tr>"
        for item in report["industry_comparisons"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | Current original BLS trucking PPI evidence</title>'
        '<style>body{font:15px/1.5 system-ui;background:#f6f9f7;color:#18372c;'
        'margin:0}main{max-width:1200px;margin:32px auto;padding:20px}'
        'table{border-collapse:collapse;background:white;width:100%}'
        'td,th{border-bottom:1px solid #d6e0d7;padding:11px;text-align:left}'
        'small{color:#556a5d}strong{font-weight:700}</style></head><body><main>'
        '<small>RETALLY / RESEARCH LAB 14 / MISSION 29 / INTERNAL ONLY</small>'
        '<h1>Current BLS producer-price evidence — all three trucking industries</h1>'
        '<p>Fresh original-source state: <strong>'+
        escape(report["status"])+'</strong>; authenticated monthly records '
        'in this execution: '+str(report["current_source_authenticated_month_count"])+
        ' of 288. Historical reports remain available and are not rewritten.</p>'
        '<table><thead><tr><th>2017 NAICS</th><th>Original BLS native series</th>'
        '<th>Census nominal revenue, 2017–2024</th>'
        '<th>BLS annual-average producer price</th>'
        '<th>Illustrative annual-average adjusted revenue</th>'
        '<th>Dec-endpoint sensitivity only</th></tr></thead><tbody>'+
        rows+'</tbody></table>'
        '<p><strong>Warning:</strong> An end-December index ratio is '
        'not equivalent to the annual-average index for yearly revenues. '
        'For LTL, the annual-average proxy is negative while the December '
        'endpoint proxy is positive; neither is official real output or a '
        'confidence interval. No customer freight invoice or refund sample.</p>'
        '<p>'+escape(report["caveat"])+'</p>'
        '<p><a href="https://www.bls.gov/ppi/overview.htm">'
        'Original BLS PPI measurement context</a></p>'
        '</main></body></html>'
    )


def main() -> None:
    p=argparse.ArgumentParser(description="Unified original BLS trucking PPI source, research only")
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--as-of-date",default=date.today().isoformat())
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline",action="store_true")
    mode.add_argument("--fetch-original",action="store_true")
    args=p.parse_args()
    as_of=date.fromisoformat(args.as_of_date)
    if args.fetch_original:
        try:
            response,digest=fetch_original_bls()
        except (OSError,TimeoutError):
            result=blocked(as_of=as_of)
        else:
            result=verify_original_bls(as_of=as_of,response=response,raw_sha256=digest)
    else:
        result=report_shell(as_of=as_of)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"unified_bls_evidence.json").write_text(
        json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    (args.out/"unified_bls_evidence.html").write_text(
        render_html(result),encoding="utf-8"
    )
    print(json.dumps({
        "source_status":result["status"],
        "fresh_direct_original_bls_months":result["current_source_authenticated_month_count"],
        "industry_count":result["industry_counts"],
        "december_ltl_sensitivity_is_not_official_real_output":True,
        "customer_refunds_or_freight_invoices_observed":0,
        "receipt_sha256":result["receipt_sha256"],
    },sort_keys=True))


if __name__ == "__main__":
    main()
