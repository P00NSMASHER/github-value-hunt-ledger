"""RETALLY Lab 14, Mission 22: verify Census 2022 SAS benchmark vintages.

Exact publisher workbook SHA-256 and source-row checks distinguish the older
2022 SAS revenue estimate from the Aug. 2026 2022 Economic Census benchmark.
SAS industry revenue is not an LTL customer's paid freight bills, error
prevalence, prospective buyer demand or recoverable cash.
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
from freight.research_sas_xlsx_probe import ALLOWED, get_source, scan_xlsx
from freight.research_aies_2022_lineage import _shell as build_m21_offline

BOOK = Path(__file__).resolve().parent / "research/SAS_BENCHMARK_2022_EVIDENCE_20261011.json"
BOOK_SHA1 = "c4bc01fc38d4b204b300b5ed0390b320f2245fe8"
SCOPE = "LAB14_SAS_AUG2026_2022_REVISION_RECONCILIATION_NO_FREIGHT_RECOVERY"
BOOK_SCOPE = "LAB14_CENSUS_2022_SAS_VINTAGE_RECONCILIATION_NO_FREIGHT_RECOVERY_CLAIMS"
REVISED = "revised_2026_sas"
LEGACY = "legacy_2024_sas"
METADATA = "OFFLINE_SAS_SOURCE_VINTAGE_MANIFEST_ONLY_NOT_FRESH_ZIP_REPLAY"
VERIFIED = "CENSUS_2022_SAS_VINTAGE_REVISION_VERIFIED_AIES_ROUNDING_MATCH"
BLOCKED = "BLOCKED_CENSUS_SAS_WORKBOOK_DOWNLOAD_NOT_VERIFIED"
DATE_PIN = date(2026, 10, 11)
SOURCES = {
    REVISED: {
        "url": ALLOWED["revised_table2"],
        "sha256": "cdfaaec9375064517da18e81623308fe4d62ae3ad102a232413ec2a6299310ac",
        "bytes": 128635, "sheet_member": "xl/worksheets/sheet1.xml",
        "sheet_rows": 839, "selected_naics_rows": [48, 49],
        "revenue_2022_million_usd": 65688, "revenue_2022_cv_raw": "0",
        "cohort": "BENCHMARKED_TO_2022_ECONOMIC_CENSUS_2017_NAICS_PUBLISHED_AUGUST_2026",
        "census_release_version": "BENCHMARK_RELEASE_AUGUST_31_2026",
    },
    LEGACY: {
        "url": ALLOWED["original_2017_2022"],
        "sha256": "4aa1efe9533fb3b16f32806af4f0b1bd5c72e92f2db024e559f891e03f0bc33a",
        "bytes": 515901, "sheet_member": "xl/worksheets/sheet2.xml",
        "sheet_rows": 839, "selected_naics_rows": [50, 51],
        "revenue_2022_million_usd": 68411, "revenue_2022_cv_raw": "1.6",
        "cohort": "LEGACY_2022_SAS_2017_NAICS_BEFORE_AUGUST_2026_BENCHMARK",
        "census_release_version": "OLDER_2022_SAS_2017_NAICS",
    },
}
TITLE = "Table 2.  Estimated Revenue by Tax Status for Employer Firms: 2013 Through 2022"
SOURCE_FIELDS = {
    "id", "url", "sha256", "bytes", "sheet_member", "sheet_rows",
    "header_row", "selected_naics_rows", "table_title", "cohort",
    "revenue_2022_million_usd", "revenue_2022_cv_raw", "census_release_version",
}
MANIFEST_FIELDS = {
    "schema_version", "scope", "observed_on", "research_date", "publisher",
    "revised_benchmark_release_date", "original_series_naics_restatement_date",
    "source_discovery", "census_sas_release_url", "census_benchmark_methods_url",
    "census_aies_linking_url", "source_family", "source_population",
    "source_metric", "sources", "linked_aies_2022_thousand_usd",
    "linked_aies_2022_original_census_zip_sha256", "old_sas_fred_series_id",
    "old_sas_fred_revenue_million_usd", "revised_sas_minus_old_million_usd",
    "linked_aies_minus_revised_sas_million_usd",
    "publication_rounding_tolerance_million_usd", "notes",
    "customer_paid_invoices_observed", "verified_recovery_market_usd",
    "industry_specific_benchmark_ratio_from_unmodified_sample_calculated",
    "pre_benchmark_modified_survey_row_retrieved",
    "exact_census_industry_specific_carryforward_factor_reproduced",
    "revision_attributed_to_survey_vintage_and_benchmarking",
    "all_residual_causes_and_underlying_method_coefficients_proven",
    "revised_sas_source_is_independent_economic_sample_from_old_sas",
    "aies_historical_2022_is_new_standalone_aies_sample",
    "revised_sas_cv_zero_means_exact_no_statistical_error",
    "legacy_sas_cv_is_billing_error_rate", "cfs_shipped_goods_value_equals_carrier_revenue",
    "cash_recoveries_proven", "buyer_demand_proven",
    "external_public_marketing_or_financial_claims_authorized",
    "customer_or_carrier_data_processed", "new_lab_created",
    "pilot_18_independent_approvals_satisfied",
}
FALSE_FLAGS = (
    "industry_specific_benchmark_ratio_from_unmodified_sample_calculated",
    "pre_benchmark_modified_survey_row_retrieved",
    "exact_census_industry_specific_carryforward_factor_reproduced",
    "all_residual_causes_and_underlying_method_coefficients_proven",
    "revised_sas_source_is_independent_economic_sample_from_old_sas",
    "aies_historical_2022_is_new_standalone_aies_sample",
    "revised_sas_cv_zero_means_exact_no_statistical_error",
    "legacy_sas_cv_is_billing_error_rate", "cfs_shipped_goods_value_equals_carrier_revenue",
    "cash_recoveries_proven", "buyer_demand_proven",
    "external_public_marketing_or_financial_claims_authorized",
    "customer_or_carrier_data_processed", "new_lab_created",
    "pilot_18_independent_approvals_satisfied",
)

def _git_blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def load_source_book() -> dict:
    raw=BOOK.read_bytes()
    if _git_blob(raw)!=BOOK_SHA1:
        raise ValueError("FROZEN_SAS_BENCHMARK_MANIFEST_BLOB_CHANGED")
    return json.loads(raw.decode("utf-8"))


def validate_book(book: object, *, as_of: date) -> list[str]:
    """Fail closed on unsupported promotion or altered observed Census source."""
    try:
        errors=[]
        if type(book) is not dict or set(book)!=MANIFEST_FIELDS or book.get("schema_version")!=1:
            return ["SAS_CLOSED_BOOK_SCHEMA_CHANGED_OR_PRIVATE_CUSTOMER_FIELDS"]
        fixed={
            "scope": BOOK_SCOPE,
            "observed_on":"2026-10-11", "research_date":"2026-10-11",
            "publisher":"U.S. Census Bureau",
            "revised_benchmark_release_date":"2026-08-31",
            "original_series_naics_restatement_date":"2024-09-25",
            "source_discovery":"READ_ONLY_CENSUS_PUBLISHER_EXACT_XLSX_OFFLINE_ADVERSARIAL_VERIFY_REQUIRED",
            "census_sas_release_url":"https://www.census.gov/data/tables/2022/econ/services/sas-naics.html",
            "census_benchmark_methods_url":"https://www.census.gov/programs-surveys/sas/technical-documentation/methodology/benchmarkprocess22.html",
            "census_aies_linking_url":"https://www2.census.gov/programs-surveys/aies/technical-documentation/methodology/2023-aies-methodology.pdf",
            "source_family":"SAME_CENSUS_2022_SAS_SURVEY_DIFFERENT_RELEASE_VINTAGES_NOT_TWO_INDEPENDENT_SAMPLES",
            "source_population":"2017_NAICS_484122_US_EMPLOYER_FIRMS_ALL_TAX_STATUSES",
            "source_metric":"2022_REVENUE_MILLIONS_NOMINAL_USD_NOT_FREIGHT_INVOICES",
            "linked_aies_2022_thousand_usd":65688461,
            "linked_aies_2022_original_census_zip_sha256":"1487da6e619f2e9701635a7f6ad2ab282302d75921e33797060866142c0d94a4",
            "old_sas_fred_series_id":"REVEF484122ALLEST",
            "old_sas_fred_revenue_million_usd":68411,
            "revised_sas_minus_old_million_usd":-2723,
            "linked_aies_minus_revised_sas_million_usd":"0.461",
            "publication_rounding_tolerance_million_usd":"0.5",
            "customer_paid_invoices_observed":0,"verified_recovery_market_usd":None,
            "revision_attributed_to_survey_vintage_and_benchmarking":True,
        }
        if type(as_of) is not date or as_of<DATE_PIN:
            errors.append("SAS_EVIDENCE_TIME_TRAVEL")
        for key,value in fixed.items():
            if type(book.get(key)) != type(value) or book.get(key)!=value:
                errors.append("SAS_PUBLISHER_SOURCE_IDENTITY_OR_UNITS_CHANGED:"+key)
        if type(book.get("notes")) is not str or len(book["notes"])<350 or (
            "not proof" not in book["notes"].lower() or "not independent" not in book["notes"].lower()
        ):
            errors.append("SAS_EVIDENCE_NOTES_MISSING_CRITICAL_CAVEATS")
        for flag in FALSE_FLAGS:
            if book.get(flag) is not False:
                errors.append("SAS_UNAUTHORIZED_PUBLISHER_OR_RECOVERY_PROMOTION:"+flag)
        source=book.get("sources")
        if type(source) is not list or len(source)!=2:
            return errors+["SAS_BOTH_PUBLICATION_VINTAGES_REQUIRED"]
        seen=set()
        for obj in source:
            if type(obj) is not dict or set(obj)!=SOURCE_FIELDS:
                errors.append("SAS_ARCHIVE_SOURCE_FIELDS_MISSING_OR_ADDED")
                continue
            ident=obj.get("id")
            if ident not in SOURCES or ident in seen:
                errors.append("SAS_UNKNOWN_OR_DUPLICATE_RELEASE_ID")
                continue
            seen.add(ident)
            expected={"id":ident,**SOURCES[ident],"header_row":5,"table_title":TITLE}
            if obj!=expected:
                errors.append("SAS_FROZEN_PUBLISHER_ARCHIVE_CHANGED:"+ident)
        if seen!=set(SOURCES):
            errors.append("SAS_MISSING_PUBLISHED_VINTAGE")
        return errors
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError):
        return ["SAS_INVALID_MANIFEST_CONTENT"]


def _million_display(value: int) -> str:
    return format(value,",")


def selected_sas_source(probe: dict, *, ident: str) -> dict:
    """Inspect two publication table rows without claiming underlying ZIP origin."""
    if ident not in SOURCES or type(probe) is not dict:
        raise ValueError("SAS_SOURCE_ID_NOT_APPROVED")
    spec=SOURCES[ident]
    if (probe.get("source_id") != ("revised_table2" if ident==REVISED else "original_2017_2022") or
        probe.get("source_url")!=spec["url"] or probe.get("raw_xlsx_bytes")!=spec["bytes"] or
        probe.get("raw_xlsx_sha256")!=spec["sha256"]):
        raise ValueError("SAS_XLSX_URL_SIZE_OR_SHA256_INCORRECT:"+ident)
    sheets=probe.get("sheets")
    if type(sheets) is not list:
        raise ValueError("SAS_SOURCE_SHEET_LIST_MISSING")
    found=[sheet for sheet in sheets if sheet.get("sheet_member")==spec["sheet_member"]]
    if len(found)!=1 or found[0].get("rows")!=spec["sheet_rows"]:
        raise ValueError("SAS_PUBLISHER_SHEET_ROW_COUNT_OR_ID_CHANGED:"+ident)
    sheet=found[0]
    headings=sheet.get("headings")
    if type(headings) is not list:
        raise ValueError("SAS_PUBLISHER_TABLE_HEADERS_MISSING")
    def heading(number: str):
        rows=[x["cells"] for x in headings if x.get("row")==number]
        return rows[0] if len(rows)==1 else {}
    if heading("1").get("A1")!=TITLE or (
        heading("5").get("A5")!="NAICS" or
        heading("5").get("C5")!="Item" or
        heading("5").get("D5")!="Tax Status" or
        heading("5").get("E5")!="Employer Status" or
        heading("5").get("F5")!="2022 Estimate"
    ):
        raise ValueError("SAS_PUBLISHER_WORKBOOK_HEADER_OR_COLUMN_DRIFT:"+ident)
    hits=sheet.get("naics_484122_hits")
    if (type(hits) is not list or len(hits)!=2 or
        sheet.get("total_matching_rows")!=2):
        raise ValueError("SAS_ALL_TWO_TAX_STATUS_ROWS_REQUIRED:"+ident)
    byrow={x.get("row"):x.get("cells") for x in hits if type(x) is dict}
    if set(byrow)!={str(x) for x in spec["selected_naics_rows"]}:
        raise ValueError("SAS_SELECTORS_OR_PUBLISHER_ROW_ADDRESSES_CHANGED:"+ident)
    observed=[]
    for rownum in spec["selected_naics_rows"]:
        fields=byrow[str(rownum)]
        expect_tax=("All Establishments" if rownum==spec["selected_naics_rows"][0] else
                    "Establishments subject to federal income tax")
        expected={
            "A":"484122",
            "B":"General Freight Trucking, Long-Distance, Less Than Truckload",
            "C":"Revenue","D":expect_tax,"E":"Employer Firms",
            "F":_million_display(spec["revenue_2022_million_usd"]),
            "P":spec["revenue_2022_cv_raw"],
        }
        for col,val in expected.items():
            if fields.get(col+str(rownum)) != val and not (
                col=="F" and fields.get(col+str(rownum))==str(spec["revenue_2022_million_usd"])
            ):
                raise ValueError("SAS_NAICS_REVENUE_TAX_STATUS_CV_FIELD_DIFFERS:"+ident+":"+col+str(rownum))
        observed.append({
            "xlsx_row":rownum, "naics":"484122",
            "tax_status":expect_tax,
            "2022_employer_revenue_million_usd":spec["revenue_2022_million_usd"],
            "2022_published_cv_raw":spec["revenue_2022_cv_raw"],
            "census_quality_risk":"ZERO_CV_NOT_PROOF_OF_ERROR_FREE_INVOICES",
        })
    return {
        "source_id":ident, "source_url":spec["url"],
        "source_xlsx_sha256":spec["sha256"], "source_xlsx_bytes":spec["bytes"],
        "sheet_member":spec["sheet_member"],"sheet_rows":spec["sheet_rows"],
        "published_vintage":spec["census_release_version"],
        "source_naics":"484122", "source_year":2022,
        "source_unit":"MILLIONS_NOMINAL_USD",
        "revenue_million_usd":spec["revenue_2022_million_usd"],
        "published_revenue_cv_raw":spec["revenue_2022_cv_raw"],
        "two_tax_status_rows_same_survey_not_independent":True,
        "selected_source_rows":observed,
        "number_of_independent_freight_audits":0,
    }


def _baseline(as_of:date) -> tuple[dict,dict]:
    if type(as_of) is not date or as_of<DATE_PIN:
        raise ValueError("SAS_AS_OF_DATE_BEFORE_SOURCE_OBSERVATION")
    book=load_source_book()
    errors=validate_book(book,as_of=as_of)
    if errors:
        raise ValueError("SAS_BOOK_NOT_VALID: "+"; ".join(errors))
    earlier=build_m21_offline(as_of)
    if (earlier.get("published_2022_historical_ltl_revenue_thousand_usd")!=65688461 or
        earlier.get("legacy_sas_2022_revenue_million_usd")!=68411 or
        earlier.get("legacy_sas_gap_assigned_causal_mechanism") is not None or
        earlier.get("actual_customer_invoice_rows_processed")!=0 or
        earlier.get("ltl_recoverable_market_tam_usd") is not None):
        raise ValueError("SAS_PRIOR_M21_PUBLISHER_HISTORY_UNTRUSTED")
    return book,earlier


def report_shell(*,as_of:date) -> dict:
    book,m21=_baseline(as_of)
    old=Decimal(SOURCES[LEGACY]["revenue_2022_million_usd"])
    revised=Decimal(SOURCES[REVISED]["revenue_2022_million_usd"])
    history=Decimal(book["linked_aies_2022_thousand_usd"])/1000
    gap=(old-revised)
    if not (-gap == Decimal(book["revised_sas_minus_old_million_usd"]) and
            (history-revised)==Decimal(book["linked_aies_minus_revised_sas_million_usd"]) and
            (history-revised).copy_abs()<=Decimal(book["publication_rounding_tolerance_million_usd"]) and
            history.quantize(Decimal("1"),rounding=ROUND_HALF_UP)==revised):
        raise ValueError("SAS_BENCHMARK_VINTAGE_ROUNDING_RECONCILIATION_INCONSISTENT")
    pct=((revised-old)*100/old).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
    result={
        "schema_version":1,"scope":SCOPE,"as_of":as_of.isoformat(),
        "status":METADATA,"lab":14,"new_lab_created":False,
        "original_source_workbooks_replayed_this_run":False,
        "source_vintages_replayed_this_run":[],
        "frozen_source_manifest_receipt_sha256":canon_hash(book),
        "prior_m21_historical_source_receipt_sha256":m21["receipt_sha256"],
        "publisher":"U.S. Census Bureau",
        "vintage_2024_original_sas_million_usd":int(old),
        "vintage_2026_benchmarked_sas_million_usd":int(revised),
        "revised_minus_old_sas_million_usd":int(revised-old),
        "revised_vs_old_sas_pct_change":str(pct),
        "original_aies_2022_historical_million_usd":str(history),
        "aies_minus_revised_sas_million_usd":str(history-revised),
        "aies_reconciles_to_published_benchmarked_sas_nearest_million":True,
        "revenue_measure":"CENSUS_2022_US_EMPLOYER_NAICS484122_INDUSTRY_REVENUE_MILLION_USD",
        "same_underlying_sas_survey_different_publication_vintages":True,
        "latest_census_benchmark_uses_2022_economic_census":True,
        "exact_modified_sas_sample_and_carryforward_factor_verified":False,
        "revision_explained_as_updated_census_benchmark_publication_vintage":True,
        "revision_peculiar_to_freight_auditing_or_billing_errors":False,
        "revised_cv_raw_not_invoice_error_rate":"0",
        "older_cv_raw_not_invoice_error_rate":"1.6",
        "both_cvs_not_statistically_reconciled_or_independent_samples":True,
        "actual_customer_paid_invoices_observed":0,
        "real_customer_recovery_error_rate_pct":None,
        "actual_cash_recoveries_usd":None,
        "recoverable_freight_audit_tam_usd":None,
        "commercial_claims_and_carrier_contact_authorized":False,
        "customer_or_carrier_records_processed":False,
        "human_pilot_18_approval_requirements_unmet":True,
        "source_caveat":(
            "The older 2022 Services Annual Survey Table 2 published $68,411 "
            "million for 2017 NAICS 484122, while the August 31 2026 Census "
            "benchmarked replacement reports $65,688 million. The 2024 AIES "
            "historical file reports $65,688.461 million, consistent with "
            "rounding to the nearest million. This difference is attributable "
            "to publication vintage and the documented 2022 Economic Census "
            "benchmark process, not observed freight billing errors. The "
            "industry-specific latent adjustment factor and independent "
            "sampling precision comparison have not been demonstrated. "
            "Revenue of carrier employers is not customer-paid LTL invoice "
            "spend, recoverable refunds or RETALLY market demand."
        ),
    }
    result["receipt_sha256"]=canon_hash(result)
    return result


def verify_source_bytes(*,as_of:date,archives:dict[str,bytes]) -> dict:
    base=report_shell(as_of=as_of)
    if type(archives) is not dict or set(archives)!=set(SOURCES):
        raise ValueError("SAS_EXACTLY_TWO_PUBLISHER_WORKBOOKS_REQUIRED")
    proofs=[]
    for ident in (REVISED,LEGACY):
        raw=archives[ident]
        if type(raw) is not bytes or len(raw)!=SOURCES[ident]["bytes"]:
            raise ValueError("SAS_ORIGINAL_XLSX_BYTE_LENGTH_MISMATCH:"+ident)
        if sha256(raw).hexdigest()!=SOURCES[ident]["sha256"]:
            raise ValueError("SAS_ORIGINAL_XLSX_SHA256_MISMATCH:"+ident)
        key="revised_table2" if ident==REVISED else "original_2017_2022"
        proof=selected_sas_source(scan_xlsx(raw,key=key),ident=ident)
        proofs.append(proof)
    if proofs[0]["revenue_million_usd"]!=65688 or proofs[1]["revenue_million_usd"]!=68411:
        raise ValueError("SAS_ORIGINAL_SOURCE_VINTAGE_REVENUES_NOT_AS_PUBLISHED")
    result=base
    result["status"]=VERIFIED
    result["original_source_workbooks_replayed_this_run"]=True
    result["source_vintages_replayed_this_run"]=proofs
    result["receipt_sha256"]=canon_hash({k:v for k,v in result.items() if k!="receipt_sha256"})
    return result


def blocked(*,as_of:date) -> dict:
    r=report_shell(as_of=as_of)
    r["status"]=BLOCKED
    r["receipt_sha256"]=canon_hash({k:v for k,v in r.items() if k!="receipt_sha256"})
    return r


def render_html(report:dict) -> str:
    rows="".join("<tr><th>"+escape(x["source_id"])+"</th><td>$"+
                 format(x["revenue_million_usd"],",")+
                 "m</td><td>"+escape(x["published_revenue_cv_raw"])+
                 "%</td></tr>" for x in report["source_vintages_replayed_this_run"])
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | 2022 SAS benchmark reconciliation</title>'
        '<style>body{font:16px/1.5 system-ui,sans-serif;background:#f6f9f7;'
        'color:#17392b;margin:0}main{max-width:900px;margin:32px auto;padding:20px}'
        'th,td{border-bottom:1px solid #ddd;padding:12px;text-align:left}</style>'
        '</head><body><main><small>RETALLY / LAB 14 / MISSION 22 / INTERNAL ONLY</small>'
        '<h1>2022 trucking revenue: Census publication-vintage reconciliation</h1>'
        '<p><strong>'+escape(report["status"])+
        '</strong>. This report is not a customer freight invoice analysis.</p>'
        '<p>Older SAS: $'+format(report["vintage_2024_original_sas_million_usd"],",")+
        'm · August 2026 benchmark: $'+format(report["vintage_2026_benchmarked_sas_million_usd"],",")+
        'm · AIES historical: $'+escape(report["original_aies_2022_historical_million_usd"])+
        'm (difference after published SAS rounding $'+
        escape(report["aies_minus_revised_sas_million_usd"])+
        'm).</p><p>Two source workbooks downloaded and authenticated in this execution: '+
        ('yes' if report["original_source_workbooks_replayed_this_run"] else 'no')+
        '</p><table><thead><tr><th>Census workbook vintage</th><th>2022 revenue</th>'
        '<th>Published CV</th></tr></thead><tbody>'+rows+'</tbody></table>'
        '<p>'+escape(report["source_caveat"])+
        '</p><p><a href="https://www.census.gov/data/tables/2022/econ/services/sas-naics.html">'
        'Official Census 2022 SAS benchmark release</a></p></main></body></html>'
    )


def main() -> None:
    parser=argparse.ArgumentParser(description="Bounded 2022 Census SAS source-vintage reconciliation")
    parser.add_argument("--as-of-date",default=date.today().isoformat())
    parser.add_argument("--out",required=True,type=Path)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline",action="store_true")
    mode.add_argument("--fetch-publisher-workbooks",action="store_true")
    args=parser.parse_args()
    as_of=date.fromisoformat(args.as_of_date)
    if args.fetch_publisher_workbooks:
        try:
            data={
                REVISED:get_source("revised_table2"),
                LEGACY:get_source("original_2017_2022"),
            }
        except (OSError,TimeoutError):
            result=blocked(as_of=as_of)
        else:
            result=verify_source_bytes(as_of=as_of,archives=data)
    else:
        result=report_shell(as_of=as_of)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"sas_2022_reconciliation.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    (args.out/"sas_2022_reconciliation.html").write_text(
        render_html(result),encoding="utf-8"
    )
    print(json.dumps({
        "status":result["status"],
        "source_workbooks_verified":result["original_source_workbooks_replayed_this_run"],
        "aies_historical_matches_revised_sas_to_nearest_million":result["aies_reconciles_to_published_benchmarked_sas_nearest_million"],
        "recovery_or_billing_error_data_proven":False,
        "receipt_sha256":result["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
