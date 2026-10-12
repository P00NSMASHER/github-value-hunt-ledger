"""RETALLY Research Lab 14 — Mission 23: audited 2022 trucking SAS peer revisions.

Compares the same source family's two Census 2022 Services Annual Survey
publication vintages. 2017 NAICS 484 includes 484121 and 484122.
These employer-revenue survey cells are NOT freight invoices, carrier
billing errors, recoveries, buyer demand, or independent surveys.
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
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from freight.research_evidence_gate import canon_hash
from freight.research_sas_benchmark import (
    LEGACY, REVISED, SOURCES as M22_SOURCES,
    TITLE, report_shell as m22_report_shell,
    selected_sas_source as m22_replay_ltl,
)
from freight.research_sas_xlsx_probe import get_source, scan_xlsx
from freight.research_ltl_revenue_bridge import RECORDS

BOOK = Path(__file__).parent / "research/SAS_TRUCKING_PEER_BENCHMARK_20261011.json"
EXPECTED_BOOK_BLOB_SHA1 = "e7e22e510cecae95e10f4bb1c35cf523b64bb1a4"
MANIFEST_SCOPE = "LAB14_CENSUS_SAS_2022_TRUCKING_PEER_BENCHMARK_NOT_CUSTOMER_FREIGHT_AUDITS"
REPORT_SCOPE = "LAB14_SAS_2022_TRUCKING_PEER_REVISIONS_NOT_FREIGHT_AUDIT_ERRORS"
OFFLINE = "OFFLINE_SAS_PEER_MANIFEST_NOT_ORIGINAL_REPLAY"
VERIFIED = "CENSUS_SAS_THREE_TRUCKING_PEER_REVISIONS_PUBLISHER_XLSX_VERIFIED"
BLOCKED = "BLOCKED_CENSUS_PEER_WORKBOOKS_UNAVAILABLE_NOT_REPLAYED"
MIN_DATE = date(2026, 10, 11)
NAICS = ("484", "484121", "484122")
UNITS = "MILLIONS_OF_NOMINAL_US_DOLLARS"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
IDS = (REVISED, LEGACY)
EXPECTED = {
    REVISED: {
        "484": ("Truck Transportation", (42, 43), 423271, "0"),
        "484121": ("General Freight Trucking, Long-Distance, Truckload", (46, 47), 172717, "0"),
        "484122": ("General Freight Trucking, Long-Distance, Less Than Truckload", (48, 49), 65688, "0"),
    },
    LEGACY: {
        "484": ("Truck Transportation", (44, 45), 445509, "1.3"),
        "484121": ("General Freight Trucking, Long-Distance, Truckload", (48, 49), 183482, "2.7"),
        "484122": ("General Freight Trucking, Long-Distance, Less Than Truckload", (50, 51), 68411, "1.6"),
    },
}
MANIFEST_KEYS = {
    "schema_version", "scope", "observed_on", "census_origin",
    "census_release_context", "census_release_page", "census_methodology_page",
    "source_family", "naics_vintage", "source_grain", "units",
    "report_population", "publisher_workbooks",
    "aies_historical_2022_thousand_usd", "aies_original_census_publisher_zip_sha256",
    "old_and_new_tax_status_rows_are_independent_samples",
    "three_trucking_naics_subsets_are_additive_independent_markets",
    "residual_between_parent_and_two_children_is_separately_surveyed_naics",
    "revised_2022_cv_zero_proves_zero_statistical_uncertainty",
    "survey_revisions_are_carrier_billing_overcharges",
    "quantitative_causal_benchmark_factor_independently_proven",
    "historical_series_fielded_as_standalone_aies_2022_sample",
    "consumer_invoice_data_ingested", "customer_billing_error_frequency_established",
    "recovered_freight_cash_usd", "serviceable_recovery_market_usd",
    "buyer_demand_established", "marketing_public_claims_or_outreach_allowed",
    "approved_real_customer_studies", "pilot_18_requirements_remain_unverified",
    "lab_count_changed", "new_scheduler_created", "caveat",
}
FALSE_GUARDS = {
    "old_and_new_tax_status_rows_are_independent_samples",
    "three_trucking_naics_subsets_are_additive_independent_markets",
    "residual_between_parent_and_two_children_is_separately_surveyed_naics",
    "revised_2022_cv_zero_proves_zero_statistical_uncertainty",
    "survey_revisions_are_carrier_billing_overcharges",
    "quantitative_causal_benchmark_factor_independently_proven",
    "historical_series_fielded_as_standalone_aies_2022_sample",
    "consumer_invoice_data_ingested", "customer_billing_error_frequency_established",
    "buyer_demand_established", "marketing_public_claims_or_outreach_allowed",
    "lab_count_changed", "new_scheduler_created",
}
WORKBOOK_KEYS = {
    "id","source_url","archive_sha256","archive_bytes","tab",
    "sheet_row_count","title","records",
}
RECORD_KEYS = {"naics","label","row_numbers","revenue_million_usd","raw_2022_cv"}


def _blob(raw: bytes) -> str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def load_manifest() -> dict:
    raw=BOOK.read_bytes()
    if _blob(raw)!=EXPECTED_BOOK_BLOB_SHA1:
        raise ValueError("M23_SOURCE_MANIFEST_GIT_BLOB_CHANGED")
    return json.loads(raw.decode("utf-8"))


def validate_manifest(book: object, *, as_of: date) -> list[str]:
    """Prevent stale-year or forged Census source/value/claim promotion."""
    try:
        if type(book) is not dict or set(book)!=MANIFEST_KEYS or book.get("schema_version")!=1:
            return ["M23_INVALID_CLOSED_SCHEMA_OR_PRIVATE_FIELDS"]
        issues=[]
        if type(as_of) is not date or as_of<MIN_DATE:
            issues.append("M23_SOURCE_DATE_BEFORE_OBSERVATION")
        literal={
            "scope":MANIFEST_SCOPE,"observed_on":"2026-10-11",
            "census_origin":"U.S. Census Bureau",
            "census_release_context":"2022 Services Annual Survey revised August 31 2026 using 2022 Economic Census benchmarking",
            "census_release_page":"https://www.census.gov/data/tables/2022/econ/services/sas-naics.html",
            "census_methodology_page":"https://www.census.gov/programs-surveys/sas/technical-documentation/methodology/benchmarkprocess22.html",
            "source_family":"SAME_CENSUS_2022_SAS_INDUSTRY_SURVEY_TWO_PUBLICATION_VINTAGES_NOT_TWO_INDEPENDENT_SAMPLES",
            "naics_vintage":"2017_NAICS",
            "source_grain":"2022_US_EMPLOYER_FIRMS_ALL_TAX_STATUSES_REVENUE",
            "units":UNITS,
            "report_population":"NAICS484_PARENT_INCLUDES_NAICS484121_AND_484122_OTHER_SUBINDUSTRIES_NOT_SEPARATELY_IDENTIFIED",
            "aies_original_census_publisher_zip_sha256":"1487da6e619f2e9701635a7f6ad282302d75921e33797060866142c0d94a4",
            "approved_real_customer_studies":0,
            "recovered_freight_cash_usd":None,
            "serviceable_recovery_market_usd":None,
        }
        for key,value in literal.items():
            if type(book.get(key))!=type(value) or book.get(key)!=value:
                issues.append("M23_SOURCE_IDENTITY_OR_POPULATION_DRIFT:"+key)
        if book.get("pilot_18_requirements_remain_unverified") is not True:
            issues.append("M23_FALSE_PILOT_APPROVAL")
        for field in FALSE_GUARDS:
            if book.get(field) is not False:
                issues.append("M23_FORGED_SOURCE_OR_CUSTOMER_RECOVERY_EVIDENCE:"+field)
        note=book.get("caveat")
        if type(note) is not str or len(note)<350 or "not" not in note.lower() or "2022" not in note:
            issues.append("M23_MISSING_EVIDENCE_CAVEAT")
        crosswalk=book.get("aies_historical_2022_thousand_usd")
        expected_aies={key:RECORDS[key]["values"][0] for key in NAICS}
        if type(crosswalk) is not dict or crosswalk !=expected_aies or any(
            type(crosswalk.get(key)) is not int for key in NAICS
        ):
            issues.append("M23_AIES_HISTORICAL_RECONCILIATION_CHANGED")
        sources=book.get("publisher_workbooks")
        if type(sources) is not list or len(sources)!=2:
            return issues+["M23_REQUIRE_BOTH_CENSUS_WORKBOOK_VINTAGES"]
        seen=set()
        for source in sources:
            if type(source) is not dict or set(source)!=WORKBOOK_KEYS:
                issues.append("M23_WORKBOOK_METADATA_SCHEMA_DRIFT")
                continue
            ident=source.get("id")
            if ident not in IDS or ident in seen:
                issues.append("M23_DUPLICATED_OR_UNKNOWN_PUBLISHER_SOURCE")
                continue
            seen.add(ident)
            ancestor=M22_SOURCES[ident]
            expected_fields={
                "source_url":ancestor["url"],
                "archive_sha256":ancestor["sha256"],
                "archive_bytes":ancestor["bytes"],
                "tab":ancestor["sheet_member"],
                "sheet_row_count":839,
                "title":TITLE,
            }
            for key,value in expected_fields.items():
                if type(source.get(key))!=type(value) or source.get(key)!=value:
                    issues.append("M23_CENSUS_ARCHIVE_OR_WORKBOOK_IDENTITY_CHANGED:"+ident+":"+key)
            rows=source.get("records")
            if type(rows) is not list or len(rows)!=3:
                issues.append("M23_WORKBOOK_THREE_NAICS_REVENUE_ROWS_REQUIRED:"+ident)
                continue
            observed=set()
            for row in rows:
                if type(row) is not dict or set(row)!=RECORD_KEYS:
                    issues.append("M23_NAICS_RECORD_SCHEMA_DRIFT:"+ident)
                    continue
                code=row.get("naics")
                if code not in NAICS or code in observed:
                    issues.append("M23_MISSING_OR_DUPLICATE_NAICS:"+ident)
                    continue
                observed.add(code)
                label, numbers, value, cv=EXPECTED[ident][code]
                if row!={"naics":code,"label":label,
                         "row_numbers":list(numbers),"revenue_million_usd":value,
                         "raw_2022_cv":cv}:
                    issues.append("M23_NAICS_REVENUE_ROW_ADDRESS_OR_CV_CHANGED:"+ident+":"+code)
            if observed!=set(NAICS):
                issues.append("M23_SOURCE_NAICS_SET_INCOMPLETE:"+ident)
        if seen!=set(IDS):
            issues.append("M23_SAS_PUBLICATION_VINTAGE_MISSING")
        return issues
    except (TypeError, KeyError, ValueError, AttributeError, OverflowError):
        return ["M23_SOURCE_BOOK_CORRUPT"]


def _pct(numerator: int, denominator: int) -> str:
    if type(numerator) is not int or type(denominator) is not int or denominator<=0:
        raise ValueError("M23_INVALID_SOURCE_PERCENT_DENOMINATOR")
    return str((Decimal(numerator)*100/Decimal(denominator)).quantize(
        Decimal("0.01"),rounding=ROUND_HALF_UP))


def _baseline(as_of: date) -> tuple[dict,dict]:
    book=load_manifest()
    failures=validate_manifest(book,as_of=as_of)
    if failures:
        raise ValueError("M23_INVALID_FROZEN_SOURCE_BOOK: "+"; ".join(failures))
    prior=m22_report_shell(as_of=as_of)
    if (prior["status"]!="OFFLINE_SAS_SOURCE_VINTAGE_MANIFEST_ONLY_NOT_FRESH_ZIP_REPLAY"
        or prior["vintage_2024_original_sas_million_usd"]!=68411
        or prior["vintage_2026_benchmarked_sas_million_usd"]!=65688
        or prior["actual_customer_paid_invoices_observed"]!=0
        or prior["recoverable_freight_audit_tam_usd"] is not None):
        raise ValueError("M23_PRIOR_LTL_ONLY_BENCHMARK_LINEAGE_INVALID")
    return book,prior


def _strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root=ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(x.text or "" for x in item.iter(NS+"t"))
        for item in root.findall(NS+"si")
    ]


def _cells_from_row(row: ET.Element, shared: list[str]) -> dict[str,str]:
    cells={}
    for el in row.findall(NS+"c"):
        ref=el.get("r","")
        if not re.fullmatch(r"[A-Z]{1,3}[0-9]{1,5}",ref):
            raise ValueError("M23_MALFORMED_PUBLISHER_WORKBOOK_CELL_ADDRESS")
        col=re.match("[A-Z]+",ref).group()
        if col in cells:
            raise ValueError("M23_DUPLICATE_SOURCE_COLUMN:"+col)
        celltype=el.get("t","")
        v=el.find(NS+"v")
        if celltype=="inlineStr":
            inline=el.find(NS+"is")
            text="".join(x.text or "" for x in inline.iter(NS+"t")) if inline is not None else ""
        elif v is None:
            text=""
        elif celltype=="s":
            try: index=int(v.text or "-1")
            except ValueError as exc:raise ValueError("M23_BAD_SHARED_STRING_INDEX") from exc
            if not 0<=index<len(shared):
                raise ValueError("M23_SHARED_STRING_OUT_OF_RANGE")
            text=shared[index]
        else:
            text=v.text or ""
        if len(text)>1000:
            raise ValueError("M23_UNBOUNDED_SOURCE_TEXT_CELL")
        cells[col]=text
    return cells


def _source_million(text: str) -> int:
    if type(text) is not str or not re.fullmatch(r"(?:[0-9]{1,9}|[0-9]{1,3}(?:,[0-9]{3}){1,3})",text):
        raise ValueError("M23_SAS_REVENUE_NON_INTEGER_OR_WRONG_UNITS")
    return int(text.replace(",",""))


def selected_peers_from_rows(rows: list[tuple[int,dict]], *, ident: str) -> list[dict]:
    """Compare parsed XLSX row contents; not an original-archive provenance claim."""
    if ident not in IDS or type(rows) is not list:
        raise ValueError("M23_UNKNOWN_CENSUS_SOURCE")
    expected=EXPECTED[ident]
    hits={}
    for rownum, cells in rows:
        if type(rownum) is not int or type(cells) is not dict:
            raise ValueError("M23_INVALID_OR_UNTRUSTED_ROW_SHAPE")
        code=cells.get("A")
        if code not in NAICS or cells.get("C")!="Revenue" or cells.get("E")!="Employer Firms":
            continue
        if rownum in hits:
            raise ValueError("M23_DUPLICATE_SAS_SOURCE_RECORD:"+str(rownum))
        label,numbers,value,cv=expected[code]
        if rownum not in numbers:
            raise ValueError("M23_UNEXPECTED_NAICS_SOURCE_ROW:"+code+":"+str(rownum))
        tax="All Establishments" if rownum==numbers[0] else "Establishments subject to federal income tax"
        if cells.get("B")!=label or cells.get("D")!=tax or cells.get("E")!="Employer Firms":
            raise ValueError("M23_SAS_NAICS_OR_TAX_COHORT_CHANGED:"+code)
        if _source_million(cells.get("F"))!=value:
            raise ValueError("M23_SAS_PUBLISHER_REVENUE_DISAGREEMENT:"+code)
        if cells.get("P")!=cv:
            raise ValueError("M23_SAS_PUBLISHED_CV_CHANGED:"+code)
        hits[rownum]={
            "source_row":rownum, "naics":code,
            "tax_status":tax, "revenue_million_usd":value,
            "raw_cv_pct":cv,
            "customer_invoice_sample":False,
        }
    expected_rows={n for code in NAICS for n in expected[code][1]}
    if set(hits)!=expected_rows:
        raise ValueError("M23_MISSING_REQUIRED_SAS_PEER_SOURCE_ROWS:"+ident+":"+str(sorted(expected_rows-set(hits))))
    return [hits[n] for n in sorted(hits)]


def inspect_source(raw: bytes, *, ident: str) -> dict:
    """Read exactly one SHA-pinned Census original XLSX (no formulas executed)."""
    if ident not in IDS or type(raw) is not bytes:
        raise ValueError("M23_UNAPPROVED_CENSUS_ORIGINAL_SOURCE")
    spec=M22_SOURCES[ident]
    if len(raw)!=spec["bytes"]:
        raise ValueError("M23_ORIGINAL_SAS_XLSX_SIZE_MISMATCH:"+ident)
    if sha256(raw).hexdigest()!=spec["sha256"]:
        raise ValueError("M23_ORIGINAL_SAS_XLSX_SHA256_MISMATCH:"+ident)
    key="revised_table2" if ident==REVISED else "original_2017_2022"
    # Existing M22 safety and original LTL cell proof must also pass.
    m22proof=m22_replay_ltl(scan_xlsx(raw,key=key),ident=ident)
    with ZipFile(BytesIO(raw)) as archive:
        shared=_strings(archive)
        root=ET.fromstring(archive.read(spec["sheet_member"]))
        all_rows=root.findall(".//"+NS+"sheetData/"+NS+"row")
        if len(all_rows)!=839:
            raise ValueError("M23_ORIGINAL_SAS_SHEET_ROW_COUNT_DRIFT:"+ident)
        selection=[]
        for row in all_rows:
            rownum=int(row.get("r","0"))
            if rownum in (1,5) or (40<=rownum<=52):
                cells=_cells_from_row(row,shared)
                selection.append((rownum,cells))
        headings=dict(selection)
        if (headings.get(1,{}).get("A")!=TITLE
            or headings.get(5,{}).get("A")!="NAICS"
            or headings.get(5,{}).get("B")!="NAICS Description"
            or headings.get(5,{}).get("C")!="Item"
            or headings.get(5,{}).get("D")!="Tax Status"
            or headings.get(5,{}).get("E")!="Employer Status"
            or headings.get(5,{}).get("F")!="2022 Estimate"):
            raise ValueError("M23_SAS_PUBLISHER_TITLE_OR_YEAR_UNITS_DRIFT:"+ident)
        # Examine all 839 source records, not only the expected row positions.
        applicable=[]
        for row in all_rows:
            rownum=int(row.get("r","0"))
            if rownum<=5:continue
            cells=_cells_from_row(row,shared)
            applicable.append((rownum,cells))
        cells=selected_peers_from_rows(applicable,ident=ident)
        ltl=[x for x in cells if x["naics"]=="484122"]
        if [x["revenue_million_usd"] for x in ltl]!=[m22proof["revenue_million_usd"]]*2:
            raise ValueError("M23_PRIOR_LTL_REVENUE_PROOF_DISAGREES")
    return {
        "id":ident,
        "publisher_url":spec["url"],
        "official_xlsx_sha256":sha256(raw).hexdigest(),
        "official_xlsx_bytes":len(raw),
        "published_census_rows":839,
        "selected_source_rows":cells,
        "selected_row_count":len(cells),
        "revenue_unit":UNITS,
        "same_survey_two_tax_rows_not_independent_samples":True,
        "publisher_digitally_signed_archive_proven":False,
    }


def report_shell(*,as_of:date) -> dict:
    book, prior=_baseline(as_of)
    current=EXPECTED[REVISED]
    previous=EXPECTED[LEGACY]
    peers=[]
    for code in NAICS:
        name=previous[code][0]
        old=previous[code][2]
        new=current[code][2]
        aies=RECORDS[code]["values"][0]
        diff=Decimal(aies)/Decimal(1000)-Decimal(new)
        if diff.copy_abs()>Decimal("0.5") or (
            (Decimal(aies)/Decimal(1000)).quantize(Decimal("1"),rounding=ROUND_HALF_UP)!=new
        ):
            raise ValueError("M23_AIES_HISTORICAL_VS_REVISED_SAS_UNITS_INCONSISTENT:"+code)
        peers.append({
            "naics":code, "industry":name,
            "old_sas_revenue_million_usd":old,
            "revised_sas_revenue_million_usd":new,
            "signed_revision_million_usd":new-old,
            "signed_revision_pct_of_old":_pct(new-old,old),
            "revision_is_an_invoice_error":False,
            "aies_2022_historical_revenue_million_usd":str(Decimal(aies)/1000),
            "aies_minus_revised_sas_million_usd":str(diff),
            "aies_agrees_at_sas_nearest_million_precision":True,
            "revised_raw_cv":current[code][3],
            "prior_raw_cv":previous[code][3],
        })
    old_parent, new_parent=previous["484"][2],current["484"][2]
    other_old=old_parent-previous["484121"][2]-previous["484122"][2]
    other_new=new_parent-current["484121"][2]-current["484122"][2]
    if other_old<=0 or other_new<=0:
        raise ValueError("M23_PARENT_AND_CHILD_HIERARCHY_BROKEN")
    parent_delta=new_parent-old_parent
    if parent_delta!=sum(x["signed_revision_million_usd"] for x in peers[1:])+(other_new-other_old):
        raise ValueError("M23_PARENT_REVISION_DECOMPOSITION_INCONSISTENT")
    report={
        "schema_version":1,"scope":REPORT_SCOPE,
        "lab":14,"new_lab_created":False,"as_of":as_of.isoformat(),
        "source_status":OFFLINE,
        "publisher":"U.S. Census Bureau",
        "source_release_vintages":"ORIGINAL_2022_SAS_VS_AUGUST_2026_ECONOMIC_CENSUS_BENCHMARKED_SAS",
        "source_grain":"2022_NATIONAL_EMPLOYER_ESTABLISHMENT_2017_NAICS",
        "units":UNITS,
        "manifest_receipt_sha256":canon_hash(book),
        "m22_reconciliation_receipt_sha256":prior["receipt_sha256"],
        "frozen_source_manifest_git_blob_sha1":EXPECTED_BOOK_BLOB_SHA1,
        "original_workbooks_replayed_this_run":False,
        "original_workbook_evidence":[],
        "naics_peer_revisions":peers,
        "naics_industries_compared":len(peers),
        "all_three_industries_downward_revised":all(r["signed_revision_million_usd"]<0 for r in peers),
        "ltl_revised_down_more_than_parent_or_tl_in_percentage_terms":False,
        "ltl_original_parent_share_pct":_pct(previous["484122"][2],old_parent),
        "ltl_revised_parent_share_pct":_pct(current["484122"][2],new_parent),
        "ltl_absolute_revision_share_of_parent_revision_pct":_pct(
            previous["484122"][2]-current["484122"][2],old_parent-new_parent
        ),
        "other_trucking_residual_old_million_usd":other_old,
        "other_trucking_residual_revised_million_usd":other_new,
        "other_trucking_residual_revision_million_usd":other_new-other_old,
        "other_trucking_residual_is_a_separate_surveyed_naics":False,
        "census_same_survey_vintages_are_independent_market_estimates":False,
        "survey_2022_cv_zero_means_no_uncertainty":False,
        "original_sas_2022_surveys_are_customer_paid_freight_invoices":False,
        "survey_revision_is_verified_carrier_overcharge_or_refund":False,
        "ltl_invoice_error_rate_pct":None,
        "customer_paid_ltl_invoice_volume_usd":None,
        "freight_recovery_tam_usd":None,
        "verified_retally_customer_recoveries_usd":None,
        "actual_independently_adjudicated_freight_invoices":0,
        "actual_buyer_demand_verified":False,
        "customer_or_carrier_data_processed":False,
        "marketing_or_prospect_contact_authorized":False,
        "pilots_approved":0,
        "pilot_18_external_requirements_unmet":True,
        "automated_background_refresh_or_schedule_created":False,
        "publisher_digital_signatures_verified":False,
        "industry_specific_sas_sample_adjustment_factors_calculated":False,
        "caveat":(
            "The 2022 Census SAS originals and August 2026 benchmark use the same "
            "Census survey lineage, not independent field samples. NAICS 484 "
            "total trucking contains both long-distance truckload 484121 and "
            "long-distance LTL 484122; these revenue amounts must not be added "
            "as separate markets. The parent-minus-two-children figure is an "
            "arithmetic residual, NOT a directly surveyed other-trucking NAICS. "
            "The magnitude of the benchmark revision differs across industries "
            "but provides no LTL bill error rate, recoverable overcharges, "
            "client freight spend, or validated marketing TAM. Published zero "
            "CV in a benchmarked historical year does not establish error-free "
            "source estimates or freight-billing quality."
        ),
    }
    report["receipt_sha256"]=canon_hash(report)
    return report


def verify_sources(*,as_of:date,downloaded:dict[str,bytes]) -> dict:
    report=report_shell(as_of=as_of)
    if type(downloaded) is not dict or set(downloaded)!=set(IDS):
        raise ValueError("M23_BOTH_CENSUS_ORIGINAL_SAS_VINTAGES_REQUIRED")
    proofs=[inspect_source(downloaded[ident],ident=ident) for ident in IDS]
    for proof in proofs:
        ident=proof["id"]
        observed={code:[] for code in NAICS}
        for x in proof["selected_source_rows"]:
            observed[x["naics"]].append(x["revenue_million_usd"])
        for code in NAICS:
            if observed[code] != [EXPECTED[ident][code][2]]*2:
                raise ValueError("M23_CENSUS_PEER_SOURCE_REVENUE_REPLAY_DISAGREES:"+ident+":"+code)
    report.update({
        "source_status":VERIFIED,
        "original_workbooks_replayed_this_run":True,
        "original_workbook_evidence":proofs,
    })
    report["receipt_sha256"]=canon_hash({k:v for k,v in report.items() if k!="receipt_sha256"})
    return report


def blocked(*,as_of:date) -> dict:
    result=report_shell(as_of=as_of)
    result["source_status"]=BLOCKED
    result["receipt_sha256"]=canon_hash({k:v for k,v in result.items() if k!="receipt_sha256"})
    return result


def render_html(report: dict) -> str:
    rows="".join(
        "<tr><th>"+escape(row["naics"])+"</th><td>"+escape(row["industry"])+
        "</td><td>"+format(row["old_sas_revenue_million_usd"],",")+
        "</td><td>"+format(row["revised_sas_revenue_million_usd"],",")+
        "</td><td>"+format(row["signed_revision_million_usd"],",")+
        "</td><td>"+escape(row["signed_revision_pct_of_old"])+
        "%</td></tr>" for row in report["naics_peer_revisions"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | Census 2022 trucking peer benchmark</title>'
        '<style>body{font:16px/1.5 system-ui;color:#1b382d;background:#f6f8f6;'
        'margin:0}main{max-width:1080px;margin:32px auto;padding:20px}'
        'table{border-collapse:collapse;width:100%;background:white}'
        'th,td{border-bottom:1px solid #d5ddd6;padding:12px;text-align:left}'
        'small{color:#557165}</style></head><body><main>'
        '<small>RETALLY / RESEARCH LAB 14 / MISSION 23 / NOT FOR MARKETING</small>'
        '<h1>2022 trucking peer industries: Census benchmark revisions</h1>'
        '<p>Direct publisher source status: <strong>'+
        escape(report["source_status"])+
        '</strong>. All revenues are millions of nominal USD for 2022 '
        'U.S. employer-industry estimates. The parent contains both children.</p>'
        '<table><thead><tr><th>NAICS</th><th>Employer industry</th>'
        '<th>Earlier SAS ($m)</th><th>Revised SAS ($m)</th>'
        '<th>Revised minus old ($m)</th><th>Nominal source revision (%)</th>'
        '</tr></thead><tbody>'+rows+'</tbody></table>'
        '<p>LTL original parent share '+escape(report["ltl_original_parent_share_pct"])+
        '%; revised share '+escape(report["ltl_revised_parent_share_pct"])+
        '%. Residual of parent minus long-distance TL and LTL is NOT '
        'independently observed.</p><p>'+escape(report["caveat"])+
        '</p><p><a href="https://www.census.gov/data/tables/2022/econ/services/sas-naics.html">'
        'Census 2022 benchmark release</a></p></main></body></html>'
    )


def main() -> None:
    parser=argparse.ArgumentParser(description="Bounded Census SAS trucking peer benchmark")
    parser.add_argument("--as-of-date",default=date.today().isoformat())
    parser.add_argument("--out",required=True,type=Path)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--offline",action="store_true")
    group.add_argument("--fetch-publisher-workbooks",action="store_true")
    args=parser.parse_args()
    as_of=date.fromisoformat(args.as_of_date)
    if args.fetch_publisher_workbooks:
        try:
            sources={
                REVISED:get_source("revised_table2"),
                LEGACY:get_source("original_2017_2022"),
            }
        except (OSError,TimeoutError):
            report=blocked(as_of=as_of)
        else:
            report=verify_sources(as_of=as_of,downloaded=sources)
    else:
        report=report_shell(as_of=as_of)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"sas_peer_benchmark.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    (args.out/"sas_peer_benchmark.html").write_text(
        render_html(report),encoding="utf-8"
    )
    print(json.dumps({
        "source_status":report["source_status"],
        "workbooks_replayed":report["original_workbooks_replayed_this_run"],
        "peer_industries_compared":len(report["naics_peer_revisions"]),
        "industry_revision_is_a_customer_invoice_error":False,
        "receipt_sha256":report["receipt_sha256"],
    },sort_keys=True))


if __name__ == "__main__":
    main()
