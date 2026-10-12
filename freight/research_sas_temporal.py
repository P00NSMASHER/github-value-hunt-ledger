"""RETALLY Lab 14 Mission 24: Census 2017–22 SAS source-vintage revision audit.

Read-only original Census source comparison. The same employer-industry survey
was revised; this work does NOT measure shipping rates, customer freight
invoices, errors, cash recoveries, or a serviceable audit market.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha1, sha256
from html import escape
from io import BytesIO
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from freight.research_evidence_gate import canon_hash
from freight.research_sas_benchmark import REVISED, LEGACY, SOURCES as M22_SOURCES
from freight.research_sas_peer_benchmark import (
    IDS, NAICS, EXPECTED as M23_2022, NS,
    _strings, _cells_from_row, _source_million,
    inspect_source, report_shell as m23_report_shell,
)
from freight.research_sas_xlsx_probe import get_source

BOOK = Path(__file__).parent / "research/SAS_TEMPORAL_2017_2022_20261011.json"
BOOK_BLOB_SHA1 = "386a6c07f2e2cd18ed89a08859ff52b6019c0c88"
SCOPE = "LAB14_SAS_2017_2022_CENSUS_VINTAGE_REVISION_SURFACE_NOT_AUDIT_SPEND"
MANIFEST_SCOPE = "LAB14_SAS_2017_2022_TRUCKING_VINTAGE_TEMPORAL_REVISIONS_NOT_INVOICE_ERRORS"
OFFLINE = "OFFLINE_PINNED_SOURCE_SNAPSHOT_ORIGINALS_NOT_REPLAYED_THIS_RUN"
VERIFIED = "CENSUS_SAS_2017_2022_ORIGINAL_XLSX_72_SOURCE_CELLS_VERIFIED"
BLOCKED = "BLOCKED_CENSUS_SAS_SOURCE_NETWORK_NO_NEW_BYTE_VERIFICATION"
MIN_DATE = date(2026,10,11)
YEARS = tuple(range(2017, 2023))
COLUMNS = {2017:"K",2018:"J",2019:"I",2020:"H",2021:"G",2022:"F"}
SOURCE_KEYS = {"source_url","source_xlsx_sha256","source_xlsx_bytes",
               "source_sheet_member","source_sheet_row_count",
               "original_source_title","industries"}
INDUSTRY_KEYS = {"naics","official_label","all_establishments_row",
                 "income_tax_establishments_row","raw_2022_cv_pct",
                 "yearly_revenue_million_usd"}
BOOK_KEYS = {
    "schema_version","scope","observed_on","publisher","population","source_family",
    "year_range","source_measure","year_column_order","release_method_url",
    "release_page_url","original_source_vintages",
    "parent_and_child_categories_cannot_be_added_as_distinct_markets",
    "both_tax_status_rows_are_not_two_independent_observations",
    "publisher_2017_anchor_equality_expected",
    "published_2018_to_2022_revisions_can_be_called_invoice_errors",
    "growth_estimates_are_inflation_adjusted",
    "benchmarking_years_are_separate_survey_panels",
    "automated_original_workbook_download_in_offline_report",
    "all_source_vintages_are_independent_samples",
    "revised_2022_raw_cv_zero_proves_exact_precision",
    "recoverable_freight_audit_tam_usd","verified_paid_customer_invoices",
    "actual_retally_recovered_cash_usd","buyer_demand_proven",
    "external_marketing_or_outreach_authorized","private_or_customer_data_ingested",
    "new_lab_created","scheduled_refresh_created",
    "pilot_18_independent_approvals_still_unverified","source_caveat",
}
FALSE_GUARDS = {
    "published_2018_to_2022_revisions_can_be_called_invoice_errors",
    "growth_estimates_are_inflation_adjusted",
    "benchmarking_years_are_separate_survey_panels",
    "automated_original_workbook_download_in_offline_report",
    "all_source_vintages_are_independent_samples",
    "revised_2022_raw_cv_zero_proves_exact_precision",
    "buyer_demand_proven","external_marketing_or_outreach_authorized",
    "private_or_customer_data_ingested","new_lab_created","scheduled_refresh_created",
}
EXPECTED_ANNUAL = {
 REVISED:{
 "484":(290532,310688,314044,308131,361243,423271),
 "484121":(112441,122875,121331,121752,145249,172717),
 "484122":(46192,49584,51037,49186,58035,65688)},
 LEGACY:{
 "484":(290532,313809,320817,318602,376903,445509),
 "484121":(112441,124337,124566,126768,152753,183482),
 "484122":(46192,49982,51897,50515,60003,68411)},
}


def _blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _read_manifest() -> dict:
    raw=BOOK.read_bytes()
    if _blob(raw)!=BOOK_BLOB_SHA1:
        raise ValueError("M24_FROZEN_SOURCE_MANIFEST_GIT_BLOB_CHANGED")
    return json.loads(raw.decode("utf-8"))


def validate_manifest(book: object, *, as_of: date) -> list[str]:
    try:
        if type(book) is not dict or set(book)!=BOOK_KEYS or book.get("schema_version")!=1:
            return ["M24_SOURCE_BOOK_INVALID_SCHEMA_OR_PRIVATE_FIELDS"]
        errors=[]
        if type(as_of) is not date or as_of<MIN_DATE:
            errors.append("M24_INVALID_OBSERVATION_DATE")
        literal={
            "scope":MANIFEST_SCOPE,"observed_on":"2026-10-11",
            "publisher":"U.S. Census Bureau",
            "population":"2017_NAICS_US_EMPLOYER_FIRMS_ALL_ESTABLISHMENTS_2022_SAS",
            "source_family":"SAME_2022_SERVICES_ANNUAL_SURVEY_LEGACY_AND_AUGUST_2026_BENCHMARKED_RELEASES",
            "year_range":list(YEARS),
            "source_measure":"ESTIMATED_REVENUE_MILLIONS_OF_NOMINAL_USD",
            "year_column_order":{str(y):COLUMNS[y] for y in YEARS},
            "release_method_url":"https://www.census.gov/programs-surveys/sas/technical-documentation/methodology/benchmarkprocess22.html",
            "release_page_url":"https://www.census.gov/data/tables/2022/econ/services/sas-naics.html",
            "recoverable_freight_audit_tam_usd":None,
            "verified_paid_customer_invoices":0,
            "actual_retally_recovered_cash_usd":None,
        }
        for field,value in literal.items():
            if type(book.get(field))!=type(value) or book.get(field)!=value:
                errors.append("M24_SOURCE_BOOK_IDENTITY_UNIT_OR_YEAR_DRIFT:"+field)
        if book.get("pilot_18_independent_approvals_still_unverified") is not True:
            errors.append("M24_UNAUTHORIZED_CUSTOMER_PILOT_APPROVAL")
        for field in FALSE_GUARDS:
            if book.get(field) is not False:
                errors.append("M24_UNAUTHORIZED_SOURCE_OR_COMMERCIAL_PROMOTION:"+field)
        for field in ("parent_and_child_categories_cannot_be_added_as_distinct_markets",
                      "both_tax_status_rows_are_not_two_independent_observations",
                      "publisher_2017_anchor_equality_expected"):
            if book.get(field) is not True:
                errors.append("M24_REQUIRED_NAICS_OVERLAP_OR_BENCHMARK_GUARD_MISSING:"+field)
        caveat=book.get("source_caveat")
        if (type(caveat) is not str or len(caveat)<350 or
            "not" not in caveat.lower() or "2022" not in caveat or
            "2017" not in caveat or "independent" not in caveat.lower()):
            errors.append("M24_MISSING_EXPLICIT_COMMERCIAL_EVIDENCE_LIMIT")
        releases=book.get("original_source_vintages")
        if type(releases) is not dict or set(releases)!=set(IDS):
            return errors+["M24_REQUIRE_EXACTLY_TWO_CENSUS_PUBLICATION_VINTAGES"]
        for ident in IDS:
            raw=releases[ident]
            if type(raw) is not dict or set(raw)!=SOURCE_KEYS:
                errors.append("M24_WORKBOOK_METADATA_SCHEMA_CHANGED:"+ident)
                continue
            ancestor=M22_SOURCES[ident]
            fixed={
                "source_url":ancestor["url"],
                "source_xlsx_sha256":ancestor["sha256"],
                "source_xlsx_bytes":ancestor["bytes"],
                "source_sheet_member":ancestor["sheet_member"],
                "source_sheet_row_count":839,
                "original_source_title":"Table 2.  Estimated Revenue by Tax Status for Employer Firms: 2013 Through 2022",
            }
            for key,value in fixed.items():
                if type(raw.get(key))!=type(value) or raw.get(key)!=value:
                    errors.append("M24_PUBLISHER_XLSX_FINGERPRINT_OR_TABLE_DRIFT:"+ident+":"+key)
            industry=raw["industries"]
            if type(industry) is not dict or set(industry)!=set(NAICS):
                errors.append("M24_EXACT_PARENT_AND_CHILD_NAICS_REQUIRED:"+ident)
                continue
            for code in NAICS:
                row=industry[code]
                if type(row) is not dict or set(row)!=INDUSTRY_KEYS:
                    errors.append("M24_NAICS_ROW_FIELDS_NOT_CLOSED:"+ident+":"+code)
                    continue
                label,positions,year2022,cv=M23_2022[ident][code]
                exact={
                    "naics":code,"official_label":label,
                    "all_establishments_row":positions[0],
                    "income_tax_establishments_row":positions[1],
                    "raw_2022_cv_pct":cv,
                    "yearly_revenue_million_usd":{
                        str(y):EXPECTED_ANNUAL[ident][code][i]
                        for i,y in enumerate(YEARS)
                    },
                }
                if row!=exact:
                    errors.append("M24_NAICS_YEAR_VALUE_CV_OR_SOURCE_ROW_CHANGED:"+ident+":"+code)
        return errors
    except (TypeError,ValueError,KeyError,AttributeError,OverflowError):
        return ["M24_SOURCE_BOOK_INVALID_CONTENT"]


def _pct(numer: int,denom: int) -> str:
    if type(numer) is not int or type(denom) is not int or denom<=0:
        raise ValueError("M24_INVALID_DENOMINATOR")
    return str((Decimal(numer)*100/Decimal(denom)).quantize(
        Decimal("0.01"),rounding=ROUND_HALF_UP))


def _baseline(*,as_of:date) -> tuple[dict,dict]:
    manifest=_read_manifest()
    errors=validate_manifest(manifest,as_of=as_of)
    if errors:
        raise ValueError("M24_SOURCE_MANIFEST_REJECTED: "+"; ".join(errors))
    prior=m23_report_shell(as_of=as_of)
    if (prior["source_status"]!="OFFLINE_SAS_PEER_MANIFEST_NOT_ORIGINAL_REPLAY"
        or prior["naics_industries_compared"]!=3
        or prior["actual_independently_adjudicated_freight_invoices"]!=0
        or prior["freight_recovery_tam_usd"] is not None
        or prior["pilot_18_external_requirements_unmet"] is not True):
        raise ValueError("M24_PRIOR_LAB14_GOVERNED_PEER_REPORT_NOT_TRUSTED")
    for ident in IDS:
        for code in NAICS:
            if EXPECTED_ANNUAL[ident][code][-1] != M23_2022[ident][code][2]:
                raise ValueError("M24_ORIGINAL_2022_PEER_REVENUE_LINEAGE_INCONSISTENT")
    return manifest,prior


def audit_rows(rows: list[tuple[int,dict]], *,ident:str) -> list[dict]:
    """Pure source-grain check. Input rows alone are not publisher-source proof."""
    if ident not in IDS or type(rows) is not list:
        raise ValueError("M24_UNKNOWN_PUBLIC_CENSUS_SOURCE_OR_ROWS")
    found={}
    for rowno,cells in rows:
        if type(rowno) is not int or type(cells) is not dict:
            raise ValueError("M24_MALFORMED_EXTRACTED_SOURCE_ROW")
        code=cells.get("A")
        if code not in NAICS or cells.get("C")!="Revenue" or cells.get("E")!="Employer Firms":
            continue
        label,positions,expected_2022,cv=M23_2022[ident][code]
        if rowno not in positions:
            raise ValueError("M24_UNEXPECTED_SAS_NAICS_SOURCE_ROW_ADDRESS:"+ident+":"+code)
        if rowno in found:
            raise ValueError("M24_DUPLICATE_SOURCE_ROW:"+ident+":"+str(rowno))
        tax=("All Establishments" if rowno==positions[0] else
             "Establishments subject to federal income tax")
        if (cells.get("B")!=label or cells.get("D")!=tax or
            cells.get("E")!="Employer Firms"):
            raise ValueError("M24_INCORRECT_SAS_NAICS_OR_TAX_POPULATION:"+ident+":"+code)
        if cells.get("P")!=cv:
            raise ValueError("M24_PUBLISHED_2022_CV_CHANGED:"+ident+":"+code)
        yearvalues={}
        for i,year in enumerate(YEARS):
            raw=cells.get(COLUMNS[year])
            value=_source_million(raw)
            if value!=EXPECTED_ANNUAL[ident][code][i]:
                raise ValueError("M24_CENSUS_ANNUAL_VALUE_MISMATCH:"+ident+":"+code+":"+str(year))
            yearvalues[str(year)]=value
        found[rowno]={
            "source_row_number":rowno,"naics":code,
            "tax_population":tax,"annual_revenue_million_usd":yearvalues,
            "source_2022_revenue_cv_raw":cv,
            "independent_customer_invoice_count":0,
        }
    expected={p for code in NAICS for p in M23_2022[ident][code][1]}
    if set(found)!=expected:
        raise ValueError("M24_SOURCE_YEAR_NAICS_TAX_ROWS_INCOMPLETE:"+ident)
    return [found[row] for row in sorted(found)]


def inspect_workbook(raw:bytes, *,ident:str) -> dict:
    if ident not in IDS or type(raw) is not bytes:
        raise ValueError("M24_UNAUTHORIZED_CENSUS_SOURCE")
    source=M22_SOURCES[ident]
    if len(raw)!=source["bytes"]:
        raise ValueError("M24_ORIGINAL_WORKBOOK_BYTE_LENGTH_MISMATCH:"+ident)
    if sha256(raw).hexdigest()!=source["sha256"]:
        raise ValueError("M24_ORIGINAL_WORKBOOK_SHA256_CHANGED:"+ident)
    # Original M23 verifies 2022, tax status, peer NAICS and 839 source rows.
    parent=inspect_source(raw,ident=ident)
    with ZipFile(BytesIO(raw)) as archive:
        shared=_strings(archive)
        root=ET.fromstring(archive.read(source["sheet_member"]))
        actual=root.findall(".//"+NS+"sheetData/"+NS+"row")
        if len(actual)!=839:
            raise ValueError("M24_OFFICIAL_SAS_TABLE_ROW_COUNT_DRIFT")
        rows=[]
        for line in actual:
            index=int(line.get("r","0"))
            if index<=0:
                raise ValueError("M24_INVALID_SAS_EXCEL_ROW_INDEX")
            cells=_cells_from_row(line,shared)
            rows.append((index,cells))
        header=dict(rows).get(5,{})
        if header.get("F")!="2022 Estimate" or header.get("K")!="2017 Estimate":
            raise ValueError("M24_SOURCE_YEAR_HEADERS_WRONG")
        for year,col in COLUMNS.items():
            if header.get(col)!=str(year)+" Estimate":
                raise ValueError("M24_SAS_YEAR_COLUMN_MISMATCH:"+str(year))
        observed=audit_rows(rows,ident=ident)
    if len(observed)!=6 or parent["selected_row_count"]!=6:
        raise ValueError("M24_PARENT_SOURCE_INVARIANT_BROKEN")
    return {
        "publication_vintage":ident,
        "publisher_source_url":source["url"],
        "original_source_sha256":sha256(raw).hexdigest(),
        "original_source_bytes":len(raw),
        "original_table_rows":839,
        "distinct_source_naics":3,
        "source_rows_replayed":len(observed),
        "annual_source_values_replayed":len(observed)*len(YEARS),
        "all_2017_2022_headers_reproduced":True,
        "revenue_units":"MILLIONS_NOMINAL_USD",
        "source_rows":observed,
        "source_is_digitally_signed_by_census":False,
    }


def report_shell(*,as_of:date) -> dict:
    book,prior=_baseline(as_of=as_of)
    peer=[]
    total_changed=0
    unchanged_anchor=0
    each_year_down=0
    for code in NAICS:
        old=EXPECTED_ANNUAL[LEGACY][code]
        new=EXPECTED_ANNUAL[REVISED][code]
        yearly=[]
        for i,year in enumerate(YEARS):
            revision=new[i]-old[i]
            if revision!=0: total_changed+=1
            if year==2017 and revision==0:unchanged_anchor+=1
            if year>2017 and revision<0:each_year_down+=1
            yearly.append({
                "year":year,
                "earlier_sas_revenue_million_usd":old[i],
                "revised_sas_revenue_million_usd":new[i],
                "signed_vintage_revision_million_usd":revision,
                "revision_pct_of_earlier_vintage":_pct(revision,old[i]),
                "this_is_not_a_freight_invoice_error":True,
            })
        if old[0]!=new[0]:
            raise ValueError("M24_CENSUS_ORIGINAL_2017_ANCHOR_NOT_EQUAL")
        if any(new[i]>=old[i] for i in range(1,len(YEARS))):
            raise ValueError("M24_BENCHMARK_REVISIONS_NOT_DOWNWARD_2018_2022")
        if any(old[i]-new[i]<=old[i-1]-new[i-1] for i in range(1,len(YEARS))):
            raise ValueError("M24_BENCHMARK_ABSOLUTE_REVISION_NOT_MONOTONIC")
        oldgrowth=_pct(old[-1]-old[0],old[0])
        newgrowth=_pct(new[-1]-new[0],new[0])
        peer.append({
            "naics":code,"industry":M23_2022[REVISED][code][0],
            "annual_comparisons":yearly,
            "same_published_2017_anchor":True,
            "first_year_revision_detected":2018,
            "2018_to_2022_every_year_downward_revised":True,
            "absolute_benchmark_revision_increases_each_year":True,
            "2017_to_2022_older_vintage_nominal_cumulative_growth_pct":oldgrowth,
            "2017_to_2022_benchmarked_nominal_cumulative_growth_pct":newgrowth,
            "revised_minus_old_cumulative_growth_pp":str(
                (Decimal(newgrowth)-Decimal(oldgrowth)).quantize(Decimal("0.01"))
            ),
            "nominal_growth_is_not_inflation_adjusted_or_causally_identified":True,
        })
    report={
        "schema_version":1,"scope":SCOPE,
        "as_of":as_of.isoformat(),"lab":14,"new_lab_created":False,
        "source_status":OFFLINE,"publication_snapshot_on":"2026-10-11",
        "source_family":"ONE_CENSUS_2022_SAS_SAMPLE_TWO_RELEASE_VINTAGES",
        "source_revenue_unit":"MILLIONS_OF_NOMINAL_USD",
        "frozen_source_manifest_sha256":canon_hash(book),
        "prior_m23_source_receipt_sha256":prior["receipt_sha256"],
        "census_original_workbooks_replayed_this_run":False,
        "original_census_workbook_receipts":[],
        "naics_categories":list(NAICS),
        "publication_years":list(YEARS),
        "unique_naics_year_vintage_comparisons":len(IDS)*len(NAICS)*len(YEARS),
        "original_excel_tax_population_year_cells_required":len(IDS)*len(NAICS)*2*len(YEARS),
        "source_year_cells_changed":total_changed,
        "2017_unchanged_anchor_categories":unchanged_anchor,
        "2018_2022_downward_revised_categories_years":each_year_down,
        "original_publisher_parent_contains_both_children":True,
        "revisions_and_nominal_growth_are_not_customer_freight_audit_data":True,
        "industry_comparisons":peer,
        "freight_invoice_error_rate_pct":None,
        "actual_paid_customer_freight_invoice_sample_size":0,
        "recoverable_overpayment_market_usd":None,
        "actual_retally_recovered_cash_usd":None,
        "buyer_demand_study_completed":False,
        "permitted_commercial_publication_or_outreach":False,
        "source_year_2022_cv_zero_proves_perfect_precision":False,
        "historical_growth_changes_are_statistically_significant":False,
        "actual_customer_data_ingested":False,
        "pilot_18_independent_external_controls_still_unmet":True,
        "scheduled_tasks_created_or_modified":False,
        "caveat":(
            "The earlier and revised 2017–2022 Census SAS releases represent "
            "revised estimates from a related Census survey family; an unchanged "
            "2017 anchor and revisions in 2018–2022 are not direct observations "
            "of freight bills, contractually incorrect charges, or refunds. "
            "NAICS 484 parent includes NAICS 484121 and 484122 children, so the "
            "series cannot be added as separate markets. The nominal cumulative "
            "revenue changes are not inflation-adjusted, tested for statistical "
            "significance, or proof of rising freight recoveries or buyer demand. "
            "No independently cleared real customer invoice evidence exists."
        ),
    }
    report["receipt_sha256"]=canon_hash(report)
    return report


def verify_originals(*,as_of:date,archives:dict[str,bytes]) -> dict:
    result=report_shell(as_of=as_of)
    if type(archives) is not dict or set(archives)!=set(IDS):
        raise ValueError("M24_TWO_SOURCE_VINTAGES_REQUIRED_FOR_ORIGINAL_REPLAY")
    receipts=[inspect_workbook(archives[ident],ident=ident) for ident in IDS]
    if sum(r["annual_source_values_replayed"] for r in receipts)!=72:
        raise ValueError("M24_MISSING_ORIGINAL_CENSUS_TAX_YEAR_CELLS")
    result["census_original_workbooks_replayed_this_run"]=True
    result["source_status"]=VERIFIED
    result["original_census_workbook_receipts"]=receipts
    result["receipt_sha256"]=canon_hash({k:v for k,v in result.items() if k!="receipt_sha256"})
    return result


def blocked(*,as_of:date) -> dict:
    report=report_shell(as_of=as_of)
    report["source_status"]=BLOCKED
    report["receipt_sha256"]=canon_hash({k:v for k,v in report.items() if k!="receipt_sha256"})
    return report


def render_html(report:dict) -> str:
    rows=[]
    for industry in report["industry_comparisons"]:
        for year in industry["annual_comparisons"]:
            rows.append(
                "<tr><th>"+escape(industry["naics"])+"</th><td>"+
                str(year["year"])+"</td><td>"+
                format(year["earlier_sas_revenue_million_usd"],",")+"</td><td>"+
                format(year["revised_sas_revenue_million_usd"],",")+"</td><td>"+
                format(year["signed_vintage_revision_million_usd"],",")+"</td><td>"+
                escape(year["revision_pct_of_earlier_vintage"])+"%</td></tr>"
            )
    summary="".join(
        "<li>"+escape(x["industry"])+": earlier 2017–22 cumulative nominal revenue "
        "change "+escape(x["2017_to_2022_older_vintage_nominal_cumulative_growth_pct"])+
        "%, benchmarked "+escape(x["2017_to_2022_benchmarked_nominal_cumulative_growth_pct"])+
        "% (difference "+escape(x["revised_minus_old_cumulative_growth_pp"])+" percentage points).</li>"
        for x in report["industry_comparisons"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | 2017–2022 Census SAS source-vintage revision</title>'
        '<style>body{font:15px/1.5 system-ui;background:#f7f9f6;color:#18392d;margin:0}'
        'main{max-width:1080px;margin:28px auto;padding:16px}table{border-collapse:collapse;'
        'background:#fff;width:100%}th,td{border-bottom:1px solid #dbe4dc;'
        'padding:10px;text-align:left}section{background:white;padding:18px;'
        'border-radius:12px;border:1px solid #dae8de;margin:15px 0}'
        'small{color:#607368}code{font-size:12px}</style></head><body><main>'
        '<small>RETALLY / LAB 14 / MISSION 24 / INTERNAL RESEARCH ONLY</small>'
        '<h1>How Census benchmark revisions changed trucking revenue history</h1>'
        '<p>Source status: <strong>'+escape(report["source_status"])+'</strong>.</p>'
        '<section><h2>2017 original anchor unchanged; 2018–2022 revised downward</h2>'
        '<p>All three related industries share this temporal source pattern. '
        'Employer-industry revenues are not paid customer freight invoices, '
        'billing errors or recoverable overpayments.</p><ul>'+summary+'</ul></section>'
        '<section style="overflow-x:auto"><table><thead><tr><th>2017 NAICS</th>'
        '<th>Year</th><th>Prior SAS ($million)</th><th>Revised SAS ($million)</th>'
        '<th>Signed revision ($million)</th><th>Revision vs old</th>'
        '</tr></thead><tbody>'+''.join(rows)+'</tbody></table></section>'
        '<section><h2>Evidence and limitations</h2><p>'+
        escape(report["caveat"])+'</p></section>'
        '<p><a href="https://www.census.gov/data/tables/2022/econ/services/sas-naics.html">'
        'U.S. Census Bureau revised Services Annual Survey</a></p>'
        '</main></body></html>'
    )


def main() -> None:
    parser=argparse.ArgumentParser(description="Census SAS six-year publisher source comparison")
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--as-of-date",default=date.today().isoformat())
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline",action="store_true")
    mode.add_argument("--fetch-originals",action="store_true")
    args=parser.parse_args()
    as_of=date.fromisoformat(args.as_of_date)
    if args.fetch_originals:
        try:
            downloads={
                REVISED:get_source("revised_table2"),
                LEGACY:get_source("original_2017_2022"),
            }
        except (OSError,TimeoutError):
            result=blocked(as_of=as_of)
        else:
            result=verify_originals(as_of=as_of,archives=downloads)
    else:
        result=report_shell(as_of=as_of)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"sas_temporal_revisions.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (args.out/"sas_temporal_revisions.html").write_text(
        render_html(result),encoding="utf-8")
    print(json.dumps({
        "source_status":result["source_status"],
        "census_publisher_original_workbooks_replayed":result["census_original_workbooks_replayed_this_run"],
        "unique_source_year_cells":result["unique_naics_year_vintage_comparisons"],
        "actual_customer_invoices":0,
        "receipt_sha256":result["receipt_sha256"],
    },sort_keys=True))


if __name__ == "__main__":
    main()
