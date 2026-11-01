"""Lab 14 Mission 27: FRED redistributor's BLS truck-transportation PPI.

FRED hosts BLS-origin PCU484484 while the original BLS API v1 returned
"Series does not exist" in Mission 26. This module deliberately separates
a web-indexed FRED observation SNAPSHOT from a successful fresh FRED HTTP
replay, and neither establishes direct BLS API authenticity. PPI-adjusted
Census employer revenues are only illustrative proxies, never freight
tonnage, actual freight bills, overcharge rates, recoveries or TAM.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from hashlib import sha1, sha256
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

from freight.research_evidence_gate import canon_hash
from freight.research_sas_aies_bridge import report_shell as census_revenue
from freight.research_bls_ppi_bridge import report_shell as child_ppi_report

BOOK = Path(__file__).parent / "research/FRED_PARENT_484_PPI_2017_2024_20261012.json"
BOOK_SHA1 = "fe9219597bd0fd19cca688825a66aca8c6972dcb"
FRED_URL = "https://fred.stlouisfed.org/data/PCU484484"
SERIES = "PCU484484"
YEARS = tuple(range(2017,2025))
MIN_DATE = date(2026,10,12)
SCOPE = "LAB14_FRED_BLS_PARENT_TRUCKING_PPI_PROVENANCE_NOT_OFFICIAL_REAL_OUTPUT"
BOOK_SCOPE = "LAB14_FRED_DISTRIBUTED_BLS_PARENT_PPI_2017_2024_CANDIDATE_NOT_DIRECT_BLS_API_REPLAY"
OFFLINE = "FRED_PUBLIC_WEB_TABLE_SNAPSHOT_NOT_FRESH_CI_PUBLISHER_REPLAY"
BLOCKED = "BLOCKED_FRED_DISTRIBUTOR_HTTP_NO_ORIGINAL_SOURCE_REPLAY"
VERIFIED_FRED = "FRED_DISTRIBUTOR_HTTP_96_MONTHS_REPLAYED_NOT_DIRECT_BLS_API"
MAX_HTML_BYTES = 600_000
REVENUE_BASE_2017_MILLION = Decimal("290532.000")
REVENUE_2024_MILLION = Decimal("402827.246")
MINIMAL_IDENTITY = {
    "schema_version":1,
    "scope":BOOK_SCOPE,
    "observed_date":"2026-10-12",
    "public_issuer":"U.S. Bureau of Labor Statistics",
    "public_distributor":"Federal Reserve Bank of St. Louis FRED",
    "series_id":SERIES,
    "industry_naics":"484",
    "industry_title":"Producer Price Index by Industry: Truck Transportation",
    "known_fred_table_url":FRED_URL,
    "known_fred_series_url":"https://fred.stlouisfed.org/series/PCU484484",
    "known_fred_graph_csv_url":"https://fred.stlouisfed.org/graph/fredgraph.csv?id=PCU484484",
    "fred_display_last_updated":"2026-09-10 11:53 AM CDT",
    "measure":"NOT_SEASONALLY_ADJUSTED_INDUSTRY_PRODUCER_NET_OUTPUT_PRICE_INDEX",
    "index_base":"DECEMBER_2003_EQUALS_100",
    "report_years":list(YEARS),
    "observation_source_state":"PUBLIC_FRED_TABLE_OBSERVED_VIA_WEB_SOURCE_NOT_AUTHENTICATED_IN_GITHUB_RUNNER",
    "original_bls_api_v1_series_lookup":"SERIES_DOES_NOT_EXIST_FOR_PCU484484_IN_M26_PROBE",
    "original_bls_api_month_values_replayed":False,
    "original_fred_publisher_bytes_replayed_in_ci":False,
    "original_fred_binary_checksum":None,
    "distributor_fred_not_independent_bls_survey":True,
    "original_bls_api_rejection_remains_unresolved":True,
    "parent_index_is_simple_average_of_child_series":False,
    "direct_bls_authenticated_parent_index_available":False,
    "parent_price_adjusted_revenue_official_real_output":False,
    "price_adjustment_is_illustrative_from_public_table_only":True,
    "source_observations_should_be_marked_fresh_verified_without_direct_fetch":False,
    "census_revenue_survey_same_scope_as_bls_price_index_established":False,
    "all_parent_freight_spending_or_invoice_market_is_measured":False,
    "public_commercial_price_volume_claims_authorized":False,
    "paid_customer_invoice_rows_observed":0,
    "carrier_billing_errors_established":False,
    "real_refund_volume_usd":None,
    "recoverable_revenue_tam_usd":None,
    "customer_demand_established":False,
    "scheduled_checks_created":False,
    "changes_to_original_14_labs":False,
    "pilot_18_independent_human_controls_unmet":True,
}
BLOCKED_ENDPOINTS = {
    FRED_URL:"TIMEOUT_NOT_AUTHENTICATED",
    "https://fred.stlouisfed.org/graph/fredgraph.csv?id=PCU484484":"TIMEOUT_NOT_AUTHENTICATED",
}


def _git_blob(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _book()->dict:
    raw=BOOK.read_bytes()
    if _git_blob(raw)!=BOOK_SHA1:
        raise ValueError("M27_FRED_SOURCE_CATALOG_GIT_BLOB_CHANGED")
    return json.loads(raw.decode("utf-8"))


def _index_num(value:object)->Decimal:
    if type(value) is not str or not re.fullmatch(r"[0-9]{1,4}\.[0-9]{3}",value):
        raise ValueError("M27_FRED_PPI_MONTHLY_NUMERIC_VALUE_INVALID")
    try:dec=Decimal(value)
    except InvalidOperation as ex:raise ValueError("M27_PPI_NONDECIMAL") from ex
    if not Decimal(1)<dec<Decimal(10000) or not dec.is_finite():
        raise ValueError("M27_PPI_MONTHLY_INDEX_OUT_OF_BOUNDS")
    return dec


def validate_catalog(book:object, *,as_of:date)->list[str]:
    """Reject catalog edits and any retrospective source/claim promotion.

    Source values are pinned by this module's original Git-blob hash, even
    though FRED was NOT freshly reachable in the Github source runner.
    """
    try:
        if type(book) is not dict:
            return ["M27_INVALID_FRED_SOURCE_BOOK"]
        if type(as_of) is not date or as_of<MIN_DATE:
            return ["M27_FRED_SOURCE_OBSERVED_LATER_THAN_REQUESTED_DATE"]
        original=_book()
        errors=[]
        if set(book)!=set(original) or book!=original:
            errors.append("M27_PINNED_FRED_WEB_INDEXED_PUBLICATION_SNAPSHOT_CHANGED")
        for key,val in MINIMAL_IDENTITY.items():
            if type(book.get(key))!=type(val) or book.get(key)!=val:
                errors.append("M27_PROVENANCE_OR_EVIDENCE_GUARD_CHANGED:"+key)
        if book.get("original_fred_http_results_in_latest_ci")!=BLOCKED_ENDPOINTS:
            errors.append("M27_UNAUTHENTICATED_FRED_HTTP_REPLAY_PROMOTED")
        values=book.get("year_to_monthly_observations")
        if type(values) is not dict or set(values)!={str(y) for y in YEARS}:
            errors.append("M27_EIGHT_SOURCE_YEARS_REQUIRED")
        else:
            for year in YEARS:
                sample=values[str(year)]
                if type(sample) is not list or len(sample)!=12:
                    errors.append("M27_TWELVE_MONTHLY_INDICES_REQUIRED:"+str(year))
                    continue
                for v in sample:
                    try:_index_num(v)
                    except ValueError:
                        errors.append("M27_MALFORMED_SOURCE_MONTHLY_VALUE:"+str(year))
                        break
        if (type(book.get("caveat")) is not str
            or len(book["caveat"])<500
            or "not freshly" not in book["caveat"].lower()
            or "18 real-customer" not in book["caveat"]):
            errors.append("M27_FRED_SOURCE_AUTHORITY_OR_COMMERCIAL_LIMITATIONS_MISSING")
        return errors
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError):
        return ["M27_FRED_CATALOG_INVALID"]


class _FREDTable(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows=[]
        self._row=None
        self._cell=None
        self._all=[]
    def handle_starttag(self,tag,attrs):
        if tag=="tr":self._row=[]
        elif tag in ("th","td") and self._row is not None:
            self._cell=[]
    def handle_data(self,data):
        self._all.append(data)
        if self._cell is not None:self._cell.append(data)
    def handle_endtag(self,tag):
        if tag in ("th","td") and self._cell is not None and self._row is not None:
            self._row.append(" ".join(" ".join(self._cell).split()))
            self._cell=None
        if tag=="tr" and self._row is not None:
            self.rows.append(self._row)
            self._row=None


def parse_fred_html(raw:bytes, *,book:dict)->dict[int,list[str]]:
    """Parse only FRED distributor's public HTML table, never BLS originals."""
    if type(raw) is not bytes or len(raw)>MAX_HTML_BYTES or not raw:
        raise ValueError("M27_FRED_HTML_MISSING_OR_OVER_BOUNDED_SIZE")
    text=raw.decode("utf-8")
    if "<html" not in text.lower() or "PCU484484" not in text:
        raise ValueError("M27_NOT_THE_FRED_DISTRIBUTOR_484_TABLE")
    parser=_FREDTable()
    parser.feed(text)
    meta=" ".join(parser._all)
    for phrase in (
        "Producer Price Index by Industry: Truck Transportation",
        "Bureau of Labor Statistics","Not Seasonally Adjusted",
        "Dec 2003=100",
    ):
        if phrase not in meta:
            raise ValueError("M27_FRED_BLS_SERIES_METADATA_MISSING:"+phrase)
    observed={y:{} for y in YEARS}
    for cells in parser.rows:
        if len(cells)<2:continue
        day,value=cells[:2]
        if not re.fullmatch(r"(?:19|20)\d{2}-\d{2}-01",day):
            continue
        year=int(day[:4])
        if year not in observed:continue
        month=int(day[5:7])
        if not 1<=month<=12:
            raise ValueError("M27_FRED_SOURCE_BAD_MONTH")
        if month in observed[year]:
            raise ValueError("M27_FRED_DUPLICATE_MONTH_OBSERVATION")
        _index_num(value)
        observed[year][month]=value
    original=book["year_to_monthly_observations"]
    ordered={}
    for year in YEARS:
        values=observed[year]
        if set(values)!=set(range(1,13)):
            raise ValueError("M27_FRED_ORIGINAL_96_MONTHLY_VALUES_INCOMPLETE:"+str(year))
        arr=[values[month] for month in range(1,13)]
        if arr!=original[str(year)]:
            raise ValueError("M27_FRED_DISTRIBUTOR_MONTHLY_VALUE_CHANGED_REVIEW_REQUIRED:"+str(year))
        ordered[year]=arr
    return ordered


def _fetch_fred_page()->bytes:
    """Only the fixed public FRED table; no keys, client data or redirects."""
    req=Request(FRED_URL,headers={"User-Agent":"Mozilla/5.0 (RETALLY research source probe)"})
    with urlopen(req,timeout=12) as response:
        if response.geturl()!=FRED_URL:
            raise ValueError("M27_FRED_SOURCE_REDIRECTED_OR_NOT_ALLOWLISTED")
        raw=response.read(MAX_HTML_BYTES+1)
    if len(raw)>MAX_HTML_BYTES:
        raise ValueError("M27_FRED_SOURCE_EXCEEDS_BOUND")
    return raw


def _pct(x:Decimal)->str:
    return str(x.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))


def report_shell(*,as_of:date)->dict:
    book=_book()
    faults=validate_catalog(book,as_of=as_of)
    if faults:raise ValueError("M27_PPI_SOURCE_GUARDS_FAILED: "+"; ".join(faults))
    census=census_revenue(as_of=as_of)
    children=child_ppi_report(as_of=as_of)
    if (census["real_ltl_freight_invoice_cases_observed"]!=0 or
        census["recoverable_freight_audit_market_usd"] is not None or
        not census["human_pilot_18_independent_requirements_unmet"] or
        children["original_bls_public_api_replayed_this_run"] is not False or
        children["parent_trucking_naics484_price_adjusted_proxy_pct"] is not None or
        children["frozen_price_index_monthly_observations"]!=192):
        raise ValueError("M27_CENSUS_OR_PRIOR_BLS_PRICE_GOVERNANCE_DRIFT")
    parent=next(x for x in census["industry_series"] if x["naics"]=="484")
    ppi=book["year_to_monthly_observations"]
    means={year:sum((_index_num(v) for v in ppi[str(year)]),Decimal(0))/12
           for year in YEARS}
    annual=[]
    for row in parent["annual_revenue"]:
        yr=row["year"]
        value=Decimal(row["revenue_million_usd"])
        equivalent=value*means[2017]/means[yr]
        annual.append({
            "year":yr,
            "public_fred_snapshot_months":12,
            "public_fred_snapshot_mean_ppi":str(means[yr].quantize(Decimal("0.0001"),rounding=ROUND_HALF_UP)),
            "census_employer_revenue_million_usd":str(value),
            "provisional_2017_ppi_level_revenue_proxy_million_usd":str(
                equivalent.quantize(Decimal("0.001"),rounding=ROUND_HALF_UP)),
            "source_id":"FRED_DISTRIBUTOR_BLS_ORIGIN_PCU484484",
            "verified_direct_bls_api_this_run":False,
            "verified_fred_publisher_http_this_run":False,
            "is_official_real_freight_output":False,
        })
    first=Decimal(parent["annual_revenue"][0]["revenue_million_usd"])
    last=Decimal(parent["annual_revenue"][-1]["revenue_million_usd"])
    nominal=_pct((last/first-1)*100)
    price=_pct((means[2024]/means[2017]-1)*100)
    adj=_pct((last/first*means[2017]/means[2024]-1)*100)
    compare=[{
        "naics":x["naics"],
        "series_id":x["bls_series_id"],
        "nominal_census_revenue_growth_pct":x["2017_to_2024_nominal_census_revenue_change_pct"],
        "2017_index_level_adjusted_proxy_growth_pct":x[
            "2017_to_2024_illustrative_price_adjusted_revenue_proxy_change_pct"],
        "source_provenance":"PREVIOUS_M26_BLS_ORIGINAL_API_VERIFIED_OFFLINE_SNAPSHOT",
        "bls_api_replayed_in_this_job":False,
    } for x in children["industry_price_adjustments"]]
    result={
        "schema_version":1,
        "scope":SCOPE,"lab":14,"new_lab_created":False,
        "as_of":as_of.isoformat(),
        "source_status":OFFLINE,
        "parent_484_price_index_provenance_grade":"PUBLIC_WEB_INDEXED_FRED_NOT_FRESH_HTTP_AUTHENTICATED",
        "source_url":FRED_URL,"source_series_id":SERIES,
        "source_months_2017_2024_in_web_observed_snapshot":96,
        "fresh_monthly_observations_verified_against_fred_http_this_run":0,
        "fresh_fred_distributor_http_replay_completed":False,
        "fresh_fred_http_sha256":None,
        "source_is_bls_origin_but_fred_distributed":True,
        "source_is_direct_bls_api_verified":False,
        "m26_bls_original_api_parent_source_rejection_preserved":True,
        "m26_child_original_bls_series_months":192,
        "m26_child_ppi_comparison":compare,
        "parent_source_snapshot_reference_updated":"2026-09-10 11:53 AM CDT",
        "frozen_catalog_receipt_sha256":canon_hash(book),
        "m25_census_nominal_revenue_receipt_sha256":census["receipt_sha256"],
        "m26_child_bls_ppi_receipt_sha256":children["receipt_sha256"],
        "parent_price_proxy_annual_observations":annual,
        "parent_2017_to_2024_nominal_census_growth_pct":nominal,
        "parent_2017_to_2024_fred_displayed_price_index_change_pct":price,
        "parent_2017_to_2024_provisional_price_adjusted_revenue_proxy_pct":adj,
        "parent_index_adjusted_estimate_can_be_marked_source_authenticated":False,
        "all_trucking_ppi_is_not_mean_of_child_tl_ltl_indices":True,
        "adjusted_revenue_proxy_is_not_official_real_gross_output":True,
        "client_paid_ltl_invoice_rows_observed":0,
        "actual_carrier_bill_overcharge_count_verified":0,
        "actual_refunds_or_cash_recoveries_usd":None,
        "freight_recoverable_market_tam_usd":None,
        "independent_buyer_demand_established":False,
        "public_performance_claims_or_external_contacts_authorized":False,
        "customer_or_carrier_private_records_processed":False,
        "human_customer_pilot_18_independent_requirements_still_unmet":True,
        "scheduled_tasks_created_or_modified":False,
        "caveat":(
            "The Federal Reserve Bank of St. Louis FRED publicly displays "
            "the BLS-origin PCU484484 truck transportation PPI. In the current "
            "GitHub research environment, FRED publisher HTTP timed out, "
            "and original BLS API v1 rejected the series identifier. "
            "These ninety-six monthly observations are a frozen public table "
            "SNAPSHOT, not independently re-downloaded source bytes in this "
            "execution. Their provisional index-adjusted Census employer "
            "revenue ratio is not official real output, paid invoices, "
            "freight tonnage, bill errors, recoverable cash or market TAM. "
            "The two M26 child-industry BLS-v1 series have stronger historical "
            "source replay evidence, but child and parent indices cannot be "
            "combined as independently sampled or additive markets. "
            "The source must remain quarantined from external commercial "
            "claims until a fresh authorized FRED/BLS verification succeeds."
        ),
    }
    result["receipt_sha256"]=canon_hash(result)
    return result


def verify_fred_html_source(*,as_of:date,raw:bytes)->dict:
    book=_book()
    observations=parse_fred_html(raw,book=book)
    if sum(len(x) for x in observations.values())!=96:
        raise ValueError("M27_FRED_96_OBSERVATIONS_NOT_FULLY_MATCHED")
    result=report_shell(as_of=as_of)
    result["source_status"]=VERIFIED_FRED
    result["parent_484_price_index_provenance_grade"]="DIRECT_FRED_DISTRIBUTOR_HTTP_NOT_DIRECT_BLS"
    result["fresh_monthly_observations_verified_against_fred_http_this_run"]=96
    result["fresh_fred_distributor_http_replay_completed"]=True
    result["fresh_fred_http_sha256"]=sha256(raw).hexdigest()
    result["parent_index_adjusted_estimate_can_be_marked_source_authenticated"]=True
    for row in result["parent_price_proxy_annual_observations"]:
        row["verified_fred_publisher_http_this_run"]=True
    result["receipt_sha256"]=canon_hash({k:v for k,v in result.items() if k!="receipt_sha256"})
    return result


def blocked(*,as_of:date)->dict:
    result=report_shell(as_of=as_of)
    result["source_status"]=BLOCKED
    result["receipt_sha256"]=canon_hash({k:v for k,v in result.items() if k!="receipt_sha256"})
    return result


def render_html(r:dict)->str:
    child_rows="".join(
        "<tr><th>"+escape(x["naics"])+"</th><td>"+
        escape(x["nominal_census_revenue_growth_pct"])+"%</td><td>"+
        escape(x["2017_index_level_adjusted_proxy_growth_pct"])+"%</td><td>"+
        escape(x["source_provenance"])+"</td></tr>"
        for x in r["m26_child_ppi_comparison"]
    )
    parent_row=(
        "<tr><th>484 (all trucking)</th><td>"+
        escape(r["parent_2017_to_2024_nominal_census_growth_pct"])+"%</td><td>"+
        escape(r["parent_2017_to_2024_provisional_price_adjusted_revenue_proxy_pct"])+"%</td><td>"+
        escape(r["parent_484_price_index_provenance_grade"])+"</td></tr>"
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY Lab 14 | FRED BLS aggregate PPI provenance</title>'
        '<style>body{font:15px/1.5 system-ui;color:#183829;background:#f7f9f6;'
        'margin:0}main{max-width:1100px;margin:35px auto;padding:20px}'
        'table{border-collapse:collapse;width:100%;background:white}'
        'td,th{border-bottom:1px solid #dee5df;padding:12px;text-align:left}'
        'small{color:#60776b}code{overflow-wrap:anywhere}</style></head>'
        '<body><main><small>RETALLY / LAB 14 / MISSION 27 / INTERNAL SOURCE REVIEW</small>'
        '<h1>All-trucking producer price index: distributor versus origin</h1>'
        '<p>Current publisher-fetch status: <strong>'+
        escape(r["source_status"])+'</strong>. '
        'The all-trucking adjusted proxy below is a provisional FRED webpage '
        'snapshot, not freshly authenticated from original BLS API.</p>'
        '<table><thead><tr><th>Industry NAICS</th><th>Nominal Census revenue change</th>'
        '<th>Illustrative 2017-index adjusted proxy</th><th>Evidence grade</th>'
        '</tr></thead><tbody>'+parent_row+child_rows+'</tbody></table>'
        '<p><strong>No official real-output, freight-volume, customer billing-error '
        'or recoverable-market inference is authorized.</strong></p>'
        '<p>'+escape(r["caveat"])+'</p>'
        '<p><a href="'+escape(r["source_url"])+'">FRED public PCU484484 table</a></p>'
        '</main></body></html>'
    )


def main()->None:
    p=argparse.ArgumentParser(description="FRED distributor parent PPI source provenance hold")
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--as-of-date",default=date.today().isoformat())
    kind=p.add_mutually_exclusive_group(required=True)
    kind.add_argument("--offline",action="store_true")
    kind.add_argument("--fetch-fred",action="store_true")
    args=p.parse_args()
    as_of=date.fromisoformat(args.as_of_date)
    if args.fetch_fred:
        try:
            data=_fetch_fred_page()
        except (OSError,TimeoutError):
            report=blocked(as_of=as_of)
        else:
            report=verify_fred_html_source(as_of=as_of,raw=data)
    else:
        report=report_shell(as_of=as_of)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"fred_parent_ppi_provenance.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    (args.out/"fred_parent_ppi_provenance.html").write_text(
        render_html(report),encoding="utf-8"
    )
    print(json.dumps({
        "source_status":report["source_status"],
        "fresh_fred_months_replayed":report["fresh_monthly_observations_verified_against_fred_http_this_run"],
        "direct_bls_api_source_authenticated":False,
        "provisional_parent_ppi_adjusted_revenue_growth_pct":report["parent_2017_to_2024_provisional_price_adjusted_revenue_proxy_pct"],
        "real_paid_invoice_or_recovery_claim":False,
        "receipt_sha256":report["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
