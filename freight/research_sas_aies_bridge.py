"""RETALLY Lab 14 / Mission 25: source-bound 2017–2024 Census carrier revenue.

An evidence-safe historical publication bridge. Revised 2022 SAS supplies
2017–2021, AIES historical supplies 2022–2024, 2022 SAS is a rounding
cross-check and 2024 AIES Basic is a matching Census distribution.
These employer-industry receipts are not customer freight bills, overcharges,
recoverable TAM, buyer interest, or actual RETALLY income.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha1, sha256
from html import escape
import json
from pathlib import Path

from freight.research_evidence_gate import canon_hash
from freight.research_sas_temporal import (
    REVISED, NAICS, EXPECTED_ANNUAL, inspect_workbook,
    report_shell as sas_temporal_report,
)
from freight.research_aies_2022_lineage import (
    EXPECTED_VALUES as AIES_HISTORICAL_CELLS,
    SOURCE_URL as AIES_HISTORY_URL,
    ZIP_SHA256 as AIES_HISTORY_SHA256,
    ZIP_BYTES as AIES_HISTORY_BYTES,
    verify_archive as verify_history_bytes,
    _shell as aies_history_report,
    _fetch_census_original as download_aies_history,
)
from freight.research_aies_original_ftp import (
    SOURCE_URL as AIES_2024_URL,
    ZIP_SHA256 as AIES_2024_SHA256,
    ZIP_SIZE_BYTES as AIES_2024_BYTES,
    verify_original_bytes as verify_basic_2024,
    _download_original as download_aies_basic,
)
from freight.research_ltl_revenue_bridge import RECORDS
from freight.research_sas_xlsx_probe import get_source

BOOK = Path(__file__).parent / "research/SAS_AIES_CARRIER_BRIDGE_2017_2024_20261012.json"
BOOK_BLOB_SHA1 = "0df081d41cb519b142c1ccfcbaf9d14bd82af3d0"
SCOPE = "LAB14_CENSUS_2017_2024_SOURCE_VERSIONED_EMPLOYER_REVENUE_NOT_LTL_RECOVERY"
BOOK_SCOPE = "LAB14_CENSUS_2017_2024_SOURCE_VERSIONED_CARRIER_REVENUE_CONTINUITY_NOT_LTL_RECOVERY_TAM"
OFFLINE = "OFFLINE_CENSUS_BRIDGE_PRIOR_VERIFIED_SNAPSHOTS_NO_NEW_SOURCE_REPLAY"
VERIFIED = "THREE_ORIGINAL_CENSUS_ARCHIVES_2017_2024_SOURCE_BRIDGE_REPRODUCED"
BLOCKED = "BLOCKED_CENSUS_SOURCE_NOT_REACHABLE_NO_NEW_REPLAY"
OBSERVED_ON = date(2026, 10, 12)
SAS_YEARS = (2017,2018,2019,2020,2021,2022)
HISTORY_YEARS = (2022,2023,2024)
ALL_YEARS = tuple(range(2017,2025))
SAS_ID = "revised_sas_2017_2022"
HISTORY_ID = "linked_aies_2022_2024"
BASIC_ID = "aies_basic_2024"
SOURCE_IDS = (SAS_ID, HISTORY_ID, BASIC_ID)
SOURCE_KEYS = {
    "id","source_url","original_sha256","original_bytes","source_years",
    "unit","naics_revenue","survey_role",
}
BOOK_KEYS = {
    "schema_version","scope","observed_on","publisher","measurement_definition",
    "naics_basis","geography","national_naics","selected_years",
    "aies_historical_release_date","benchmark_sas_release_date","sources",
    "source_year_2017_2021","source_year_2022","source_year_2023_2024",
    "source_family_continuity_described_by_census",
    "year_2022_aies_was_standalone_original_aies_survey",
    "different_source_distributions_are_statistically_independent_samples",
    "summing_parent_484_and_children_484121_484122_allowed",
    "legacy_prebenchmark_2022_sas_can_substitute_for_revised_sas",
    "suppress_or_wrong_naics_data_can_be_accepted",
    "source_vintage_crosswalk_gap_greater_than_half_million_allowed",
    "historical_2022_raw_cv_zero_means_perfect_accuracy",
    "adjusted_inflation_growth_in_this_report",
    "statistical_significance_or_causal_growth_proven",
    "transportation_services_revenue_equals_2022_cfs_shipped_goods_value",
    "all_ltl_spending_is_measured_by_484122",
    "real_paid_customer_invoices_verified",
    "invoice_error_rate_established","recoverable_market_tam_usd",
    "actual_retally_cash_recovered_usd","buyers_interviewed_or_demand_verified",
    "commercial_claim_or_carrier_contact_authorized",
    "customer_or_carrier_private_records_used",
    "real_customer_pilot_18_requirements_satisfied",
    "new_lab_created","scheduled_tasks_modified","source_caveat",
}
FALSE_GUARDS = {
    "year_2022_aies_was_standalone_original_aies_survey",
    "different_source_distributions_are_statistically_independent_samples",
    "summing_parent_484_and_children_484121_484122_allowed",
    "legacy_prebenchmark_2022_sas_can_substitute_for_revised_sas",
    "suppress_or_wrong_naics_data_can_be_accepted",
    "source_vintage_crosswalk_gap_greater_than_half_million_allowed",
    "historical_2022_raw_cv_zero_means_perfect_accuracy",
    "adjusted_inflation_growth_in_this_report",
    "statistical_significance_or_causal_growth_proven",
    "transportation_services_revenue_equals_2022_cfs_shipped_goods_value",
    "all_ltl_spending_is_measured_by_484122",
    "invoice_error_rate_established",
    "commercial_claim_or_carrier_contact_authorized",
    "customer_or_carrier_private_records_used",
    "real_customer_pilot_18_requirements_satisfied",
    "new_lab_created","scheduled_tasks_modified",
}
SOURCE_IDENTITY = {
    SAS_ID: (
        "https://www2.census.gov/programs-surveys/sas/tables/time-series/sas-latest/Table2.xlsx",
        "cdfaaec9375064517da18e81623308fe4d62ae3ad102a232413ec2a6299310ac",
        128635,SAS_YEARS,"MILLION_NOMINAL_USD",
        "BENCHMARKED_2022_SAS_PREDECESSOR_HISTORY_REVISED_VINTAGE",
    ),
    HISTORY_ID: (
        AIES_HISTORY_URL,AIES_HISTORY_SHA256,AIES_HISTORY_BYTES,
        HISTORY_YEARS,"THOUSAND_NOMINAL_USD",
        "AIES_2024_HISTORICAL_LINKED_TO_LEGACY_SURVEYS_NOT_3_INDEPENDENT_AIES_SURVEYS",
    ),
    BASIC_ID: (
        AIES_2024_URL,AIES_2024_SHA256,AIES_2024_BYTES,
        (2024,),"THOUSAND_NOMINAL_USD",
        "DIRECT_2024_AIES_BASIC_SAME_CENSUS_SOURCE_POPULATION_NOT_INDEPENDENT_MARKET_STUDY",
    ),
}


def _git_blob(raw: bytes) -> str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _frozen_catalog() -> dict:
    raw=BOOK.read_bytes()
    if _git_blob(raw)!=BOOK_BLOB_SHA1:
        raise ValueError("M25_CENSUS_BRIDGE_MANIFEST_GIT_BLOB_CHANGED")
    return json.loads(raw.decode("utf-8"))


def _expected_values(ident: str, code: str) -> list[int]:
    if ident == SAS_ID:
        return list(EXPECTED_ANNUAL[REVISED][code])
    if ident == HISTORY_ID:
        return [AIES_HISTORICAL_CELLS[(y,code)] for y in HISTORY_YEARS]
    if ident == BASIC_ID:
        return [RECORDS[code]["values"][2]]
    raise ValueError("M25_NONALLOWLISTED_REVENUE_SOURCE")


def validate_catalog(book: object, *, as_of: date) -> list[str]:
    try:
        if type(book) is not dict or set(book)!=BOOK_KEYS or book.get("schema_version")!=1:
            return ["M25_CLOSED_SOURCE_CATALOG_FIELDS_INVALID"]
        problems=[]
        if type(as_of) is not date or as_of<OBSERVED_ON:
            problems.append("M25_SOURCE_RECORD_USED_BEFORE_OBSERVATION")
        exact={
            "scope":BOOK_SCOPE,"observed_on":"2026-10-12",
            "publisher":"U.S. Census Bureau",
            "measurement_definition":"US_EMPLOYER_INDUSTRY_ESTABLISHMENT_REVENUE_NOMINAL_USD_NOT_PAID_CUSTOMER_LTL_INVOICES",
            "naics_basis":"2017_NAICS",
            "geography":"US_0100000US_ALL_ESTABLISHMENTS",
            "national_naics":list(NAICS),
            "selected_years":list(ALL_YEARS),
            "aies_historical_release_date":"2026-09-10",
            "benchmark_sas_release_date":"2026-08-31",
            "source_year_2017_2021":"AUGUST_2026_BENCHMARKED_SAS_PUBLICATION",
            "source_year_2022":"AIES_2024_LEGACY_LINKED_HISTORICAL_OBSERVATION_SAS_2022_ROUNDING_CROSSCHECK",
            "source_year_2023_2024":"AIES_HISTORICAL_SERIES_WITH_INDEPENDENT_2024_BASIC_DISTRIBUTION_CROSSCHECK",
            "real_paid_customer_invoices_verified":0,
            "buyers_interviewed_or_demand_verified":0,
            "recoverable_market_tam_usd":None,
            "actual_retally_cash_recovered_usd":None,
        }
        for key,val in exact.items():
            if type(book.get(key))!=type(val) or book.get(key)!=val:
                problems.append("M25_SOURCE_SCOPE_YEAR_OR_UNITS_CHANGED:"+key)
        if book.get("source_family_continuity_described_by_census") is not True:
            problems.append("M25_MISSING_CENSUS_HISTORICAL_METHOD_CAVEAT")
        for flag in FALSE_GUARDS:
            if book.get(flag) is not False:
                problems.append("M25_FALSE_CENSUS_OR_CUSTOMER_EVIDENCE_PROMOTION:"+flag)
        caveat=book.get("source_caveat")
        if (type(caveat) is not str or len(caveat)<500 or "2022" not in caveat
            or "NOT" not in caveat or "invoice" not in caveat.lower()):
            problems.append("M25_MISSING_NONCOMMERCIAL_VINTAGE_LIMITATIONS")
        sources=book.get("sources")
        if type(sources) is not list or len(sources)!=3:
            return problems+["M25_REQUIRE_EXACTLY_THREE_ORIGINAL_CENSUS_SOURCES"]
        ids=set()
        for source in sources:
            if type(source) is not dict or set(source)!=SOURCE_KEYS:
                problems.append("M25_ARCHIVE_LINEAGE_SCHEMA_DRIFT")
                continue
            sid=source.get("id")
            if sid not in SOURCE_IDS or sid in ids:
                problems.append("M25_DUPLICATE_OR_UNKNOWN_ORIGINAL_ARCHIVE")
                continue
            ids.add(sid)
            url,sha,size,years,unit,role=SOURCE_IDENTITY[sid]
            exact_source={
                "id":sid,"source_url":url,"original_sha256":sha,
                "original_bytes":size,"source_years":list(years),
                "unit":unit,"survey_role":role,
                "naics_revenue":{code:_expected_values(sid,code) for code in NAICS},
            }
            if source!=exact_source:
                problems.append("M25_CENSUS_ARCHIVE_VALUE_NAICS_OR_PROVENANCE_CHANGED:"+sid)
        if ids!=set(SOURCE_IDS):
            problems.append("M25_ORIGINAL_CENSUS_SOURCE_COVERAGE_INCOMPLETE")
        return problems
    except (TypeError,ValueError,AttributeError,KeyError):
        return ["M25_SOURCE_CATALOG_MALFORMED"]


def _pct(after: int, before: int) -> str:
    if type(after) is not int or type(before) is not int or before<=0:
        raise ValueError("M25_NOMINAL_RATIO_INVALID")
    return str(((Decimal(after)-Decimal(before))*100/Decimal(before)).quantize(
        Decimal("0.01"),rounding=ROUND_HALF_UP
    ))


def _millions(thousand_usd: int) -> str:
    return str((Decimal(thousand_usd)/Decimal(1000)).quantize(Decimal("0.001")))


def stitch_values(*,sas:dict,aies:dict,basic:dict) -> dict:
    """Enforce year/industry/units before assembling 24 historical cells.

    The inputs represent parsed source values, not an origin attestation.
    Direct-Census authenticity is only set after all 3 source ZIPs are checked.
    """
    if (type(sas) is not dict or type(aies) is not dict or type(basic) is not dict
        or set(sas)!=set(NAICS) or set(aies)!=set(NAICS)
        or set(basic)!=set(NAICS)):
        raise ValueError("M25_REJECT_MISSING_OR_ADDED_NAICS_CLASSIFICATION")
    records=[]
    overlap=[]
    for code in NAICS:
        s,h,b=sas[code],aies[code],basic[code]
        if (type(s) is not list or type(h) is not list or type(b) is not list
            or len(s)!=6 or len(h)!=3 or len(b)!=1
            or any(type(x) is not int or x<=0 for x in s+h+b)):
            raise ValueError("M25_REJECT_WRONG_YEAR_GRAIN_UNIT_OR_UNPUBLISHED_VALUE:"+code)
        overlap_gap=Decimal(h[0])/1000-Decimal(s[5])
        if (overlap_gap.copy_abs()>Decimal("0.5")
            or (Decimal(h[0])/1000).quantize(
                Decimal("1"),rounding=ROUND_HALF_UP)!=Decimal(s[5])):
            raise ValueError("M25_SAS_AIES_2022_HANDOFF_DOES_NOT_ROUND_TO_SAME_MILLION:"+code)
        if h[2]!=b[0]:
            raise ValueError("M25_2024_AIES_BASIC_DISAGREES_WITH_HISTORICAL_SERIES:"+code)
        if (s!=_expected_values(SAS_ID,code)
            or h!=_expected_values(HISTORY_ID,code)
            or b!=_expected_values(BASIC_ID,code)):
            raise ValueError("M25_SOURCE_VINTAGE_OR_INDUSTRY_REVENUE_CHANGED:"+code)
        annual=[]
        for i,year in enumerate(ALL_YEARS):
            if year<=2021:
                value=s[i]*1000
                source=SAS_ID
                linked=False
                as_reported_unit="MILLION_NOMINAL_USD"
            else:
                value=h[year-2022]
                source=HISTORY_ID
                linked=year==2022
                as_reported_unit="THOUSAND_NOMINAL_USD"
            annual.append({
                "year":year,
                "revenue_thousand_usd":value,
                "revenue_million_usd":_millions(value),
                "source_id":source,
                "source_unit":as_reported_unit,
                "year_is_linked_legacy_not_standalone_aies_survey":linked,
                "is_customer_freight_invoice_or_recovered_cash":False,
            })
        records.append({
            "naics":code,"industry":RECORDS[code]["title"],
            "annual_revenue":annual,
            "2017_to_2024_nominal_cumulative_change_pct":_pct(h[2],s[0]*1000),
            "2022_to_2023_aies_nominal_change_pct":_pct(h[1],h[0]),
            "2023_to_2024_aies_nominal_change_pct":_pct(h[2],h[1]),
            "2017_to_2024_change_is_statistically_significant":False,
        })
        overlap.append({
            "naics":code,
            "revised_2022_sas_million_usd":s[5],
            "aies_2022_linked_historical_million_usd":_millions(h[0]),
            "aies_minus_sas_million_usd":str(overlap_gap),
            "agrees_at_original_sas_nearest_million":True,
            "is_2022_independently_fielded_aies_survey":False,
        })
    return {"industry_series":records,"overlap_2022":overlap}


def report_shell(*,as_of:date) -> dict:
    book=_frozen_catalog()
    issues=validate_catalog(book,as_of=as_of)
    if issues:
        raise ValueError("M25_CLOSED_CENSUS_SOURCE_BOOK_INVALID: "+"; ".join(issues))
    earlier=sas_temporal_report(as_of=as_of)
    history=aies_history_report(as_of)
    if (earlier["source_status"]!="OFFLINE_PINNED_SOURCE_SNAPSHOT_ORIGINALS_NOT_REPLAYED_THIS_RUN"
        or earlier["actual_paid_customer_freight_invoice_sample_size"]!=0
        or earlier["recoverable_overpayment_market_usd"] is not None
        or history["status"]!="OFFLINE_HISTORICAL_METADATA_ONLY_NO_SOURCE_REPLAY"
        or history["actual_customer_invoice_rows_processed"]!=0
        or not history["human_pilot_18_controls_still_unverified"]):
        raise ValueError("M25_PRIOR_SOURCE_PROVENANCE_OR_CUSTOMER_GUARD_REGRESSION")
    joined=stitch_values(
        sas={code:_expected_values(SAS_ID,code) for code in NAICS},
        aies={code:_expected_values(HISTORY_ID,code) for code in NAICS},
        basic={code:_expected_values(BASIC_ID,code) for code in NAICS},
    )
    report={
        "schema_version":1,"scope":SCOPE,"lab":14,"new_lab_created":False,
        "as_of":as_of.isoformat(),
        "source_status":OFFLINE,
        "census_original_replay_completed_in_this_run":False,
        "source_original_archive_receipts":[],
        "original_source_archives_required":3,
        "distinct_industry_year_values":len(NAICS)*len(ALL_YEARS),
        "benchmark_sas_revenue_years":list(range(2017,2022)),
        "aies_historical_revenue_years":list(HISTORY_YEARS),
        "source_crosschecks":"SAS_2022_ROUND_TO_AIES_2022_AND_AIES_HISTORICAL_2024_MATCH_BASIC",
        "source_family_not_independent_surveys":True,
        "sas_aies_same_2022_population_to_published_precision":True,
        "2022_aies_was_not_a_separately_fielded_2022_survey":True,
        "naics_484_contains_484121_and_484122":True,
        "same_parent_child_revenue_cannot_be_added_as_independent_markets":True,
        "released_census_aies_2024_from_same_publisher_not_independent_market_study":True,
        "frozen_census_source_manifest_receipt_sha256":canon_hash(book),
        "m24_sas_temporal_offline_receipt_sha256":earlier["receipt_sha256"],
        "m21_aies_historical_offline_receipt_sha256":history["receipt_sha256"],
        "industry_series":joined["industry_series"],
        "overlap_2022":joined["overlap_2022"],
        "historical_revenue_is_paid_invoice_volume":False,
        "nominal_growth_is_inflation_adjusted":False,
        "nominal_growth_statistical_significance_established":False,
        "ltl_shipping_market_spending_covered_entirely":False,
        "real_ltl_freight_invoice_cases_observed":0,
        "customer_billing_error_rate_pct":None,
        "contractually_eligible_refund_volume_usd":None,
        "actual_retally_collected_recovery_cash_usd":None,
        "recoverable_freight_audit_market_usd":None,
        "buyer_demand_established":False,
        "carrier_or_customer_contact_authorized":False,
        "customer_or_carrier_private_documents_accessed":False,
        "human_pilot_18_independent_requirements_unmet":True,
        "automated_tasks_or_schedules_modified":False,
        "caveat":(
            "The eight-year 2017–2024 revenue description uses benchmarked 2022 "
            "Census SAS historical estimates for 2017–2021 and Census AIES "
            "historical publication estimates for 2022–2024. The 2022 "
            "source handoff is a million-dollar published rounding comparison, "
            "not two statistically independent samples. AIES 2022 is linked "
            "historical data, not a separately collected 2022 AIES survey. "
            "Nominal cumulative comparisons are descriptive, not inflation "
            "adjusted, not statistically significant growth findings and not "
            "commercial opportunities. NAICS 484 includes its trucking "
            "subindustries; do not add parent and children. Actual paid freight "
            "invoices, governing customer rates, audit errors, collectible "
            "refunds and buyer demand remain unmeasured."
        ),
    }
    report["receipt_sha256"]=canon_hash(report)
    return report


def verify_origins(*,as_of:date,archives:dict[str,bytes]) -> dict:
    report=report_shell(as_of=as_of)
    if type(archives) is not dict or set(archives)!=set(SOURCE_IDS):
        raise ValueError("M25_THREE_CENSUS_ORIGINAL_ARCHIVES_REQUIRED_FOR_REPLAY")
    sasproof=inspect_workbook(archives[SAS_ID],ident=REVISED)
    histproof=verify_history_bytes(archives[HISTORY_ID],as_of=as_of)
    basicproof=verify_basic_2024(archives[BASIC_ID],as_of=as_of)
    sas={code:None for code in NAICS}
    for row in sasproof["source_rows"]:
        if row["tax_population"]=="All Establishments":
            code=row["naics"]
            if sas[code] is not None:
                raise ValueError("M25_DUPLICATE_SOURCE_SAS_ALL_ESTABLISHMENT_NAICS")
            sas[code]=[row["annual_revenue_million_usd"][str(y)] for y in SAS_YEARS]
    hist={code:[] for code in NAICS}
    for year in HISTORY_YEARS:
        for code in NAICS:
            found=[x for x in histproof["selected_source_cells"] if x["year"]==year and x["naics"]==code]
            if len(found)!=1:
                raise ValueError("M25_HISTORICAL_AIES_YEAR_NAICS_MISSING_OR_DUPLICATE")
            hist[code].append(found[0]["revenue_thousand_usd"])
    basic={code:[] for code in NAICS}
    for value in basicproof["source_estimates"]:
        code=value["naics2017"]
        basic[code].append(value["revenue_thousand_usd"])
    observed=stitch_values(sas=sas,aies=hist,basic=basic)
    if observed["industry_series"]!=report["industry_series"] or observed["overlap_2022"]!=report["overlap_2022"]:
        raise ValueError("M25_THREE_PUBLISHER_SOURCES_INCONSISTENT_WITH_REPORT")
    if (sasproof["annual_source_values_replayed"]!=36
        or histproof["matched_national_year_naics_source_cells"]!=9
        or basicproof["matched_national_industry_source_rows"]!=3):
        raise ValueError("M25_ORIGINAL_SOURCE_COVERAGE_INCOMPLETE")
    if not (basicproof["direct_original_census_ftp_replay_completed"]
            and histproof["status"]=="VERIFIED_CENSUS_2024_HISTORICAL_ZIP_2022_REVENUE_LEGACY_LINKED"):
        raise ValueError("M25_ORIGINAL_CENSUS_AIES_REPLAY_NOT_SUCCESSFUL")
    report.update({
        "source_status":VERIFIED,
        "census_original_replay_completed_in_this_run":True,
        "source_original_archive_receipts":[
            {"id":SAS_ID,"sha256":sasproof["original_source_sha256"],
             "original_bytes":sasproof["original_source_bytes"],
             "source_tax_year_cells":36,
             "original_source_is_independent_audit":False},
            {"id":HISTORY_ID,"sha256":histproof["verified_source_zip_sha256"],
             "original_bytes":histproof["source_zip_bytes"],"source_data_rows":histproof["source_dat_rows"],
             "national_industry_year_cells":9,
             "origin_receipt_sha256":histproof["receipt_sha256"],
             "original_source_is_independent_audit":False},
            {"id":BASIC_ID,"sha256":basicproof["source_archive_sha256"],
             "original_bytes":basicproof["source_zip_bytes"],"source_data_rows":basicproof["source_data_row_count"],
             "national_industry_year_cells":3,
             "origin_receipt_sha256":basicproof["receipt_sha256"],
             "original_source_is_independent_audit":False},
        ],
    })
    report["receipt_sha256"]=canon_hash({k:v for k,v in report.items() if k!="receipt_sha256"})
    return report


def blocked(*,as_of:date) -> dict:
    r=report_shell(as_of=as_of)
    r["source_status"]=BLOCKED
    r["receipt_sha256"]=canon_hash({k:v for k,v in r.items() if k!="receipt_sha256"})
    return r


def render_html(r:dict) -> str:
    heading="".join(
        "<th>"+str(y)+"</th>" for y in ALL_YEARS
    )
    rows=""
    for industry in r["industry_series"]:
        cells="".join(
            "<td>"+escape(x["revenue_million_usd"])+
            ("*" if x["year"]==2022 else "")+"</td>"
            for x in industry["annual_revenue"]
        )
        rows+=("<tr><th>"+escape(industry["naics"])+"</th>"+
               cells+"<td><strong>"+
               escape(industry["2017_to_2024_nominal_cumulative_change_pct"])+
               "%</strong></td></tr>")
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY Research Lab 14 | 2017–2024 source-graded Census revenue</title>'
        '<style>body{font:15px/1.5 system-ui;color:#18382a;background:#f5f8f5;margin:0}'
        'main{max-width:1200px;margin:36px auto;padding:20px}'
        'section{background:white;padding:18px;border-radius:10px;margin:16px 0}'
        '.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:900px}'
        'th,td{padding:10px;border-bottom:1px solid #d7e2da;text-align:right}'
        'th:first-child{text-align:left}small{color:#597267}</style>'
        '</head><body><main><small>RETALLY / EXISTING LAB 14 / MISSION 25 / INTERNAL RESEARCH ONLY</small>'
        '<h1>Eight years of Census trucking industry revenue — with source lineage</h1>'
        '<p>Original Census source replay: <strong>'+
        escape(r["source_status"])+'</strong>.</p>'
        '<section class="scroll"><table><thead><tr><th>2017 NAICS</th>'+
        heading+'<th>2017–24 nominal change</th></tr></thead><tbody>'+
        rows+'</tbody></table></section>'
        '<section><p>Values are <strong>millions of nominal U.S. dollars</strong>. '
        'Years 2017–2021: revised SAS. Years 2022–2024: Census AIES historical; '
        'an asterisk marks 2022 legacy-linked data, not a separately fielded 2022 AIES sample. '
        'The original benchmarked SAS 2022 and AIES historical 2022 must reconcile '
        'at published nearest-million precision. 2024 matches the separate original AIES Basic distribution.</p></section>'
        '<section><h2>Measurement and commercial limitations</h2><p>'+
        escape(r["caveat"])+
        '</p><p>Actual customer-paid invoices: 0 verified; '
        'recoverable refunds and RETALLY audit TAM: not established. '
        'All 18 independent customer pilot approvals remain unverified.</p></section>'
        '<p><a href="https://www.census.gov/newsroom/press-releases/2026/aies-time-series-data.html">'
        'Census AIES historical release (September 10, 2026)</a></p>'
        '</main></body></html>'
    )


def main() -> None:
    ap=argparse.ArgumentParser(description="Lab14 bounded source-bound Census revenue history")
    ap.add_argument("--out",required=True,type=Path)
    ap.add_argument("--as-of-date",default=date.today().isoformat())
    choices=ap.add_mutually_exclusive_group(required=True)
    choices.add_argument("--offline",action="store_true")
    choices.add_argument("--fetch-originals",action="store_true")
    args=ap.parse_args()
    as_of=date.fromisoformat(args.as_of_date)
    if args.fetch_originals:
        try:
            sources={
                SAS_ID:get_source("revised_table2"),
                HISTORY_ID:download_aies_history(),
                BASIC_ID:download_aies_basic(),
            }
        except (OSError,TimeoutError):
            report=blocked(as_of=as_of)
        else:
            report=verify_origins(as_of=as_of,archives=sources)
    else:
        report=report_shell(as_of=as_of)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"sas_aies_revenue_bridge.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    (args.out/"sas_aies_revenue_bridge.html").write_text(
        render_html(report),encoding="utf-8")
    print(json.dumps({
        "source_status":report["source_status"],
        "publisher_archives_replayed":report["census_original_replay_completed_in_this_run"],
        "distinct_naics_year_series_cells":report["distinct_industry_year_values"],
        "2022_crosswalk_source_consistent":report["sas_aies_same_2022_population_to_published_precision"],
        "actual_customer_recoveries":None,
        "evidence_receipt_sha256":report["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
