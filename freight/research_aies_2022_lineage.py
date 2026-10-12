"""Mission 21: verify original Census 2024 AIES historical 2022 carrier-revenue rows.

This is the publisher's linked HISTORICAL series; it is not a separately
fielded 2022 AIES survey, current LTL invoice spending, a customer audit, or
evidence of billing errors or recoverable cash.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
from hashlib import sha1, sha256
from html import escape
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

from freight.research_cfs_archive_verifier import _archive_members, _parse_tabular, _read_archive
from freight.research_evidence_gate import canon_hash
from freight.research_ltl_revenue_bridge import RECORDS, build_revenue
from freight.research_aies_historical_lineage import report_shell as prior_historical

ROOT = Path(__file__).resolve().parent
BOOK = ROOT / "research/AIES_2022_LEGACY_LINEAGE_20261011.json"
BOOK_GIT_BLOB_SHA1 = "d4c5d7b23151d08fbb42f03480dd63be6eeee815"
SCOPE = "LAB14_CENSUS_AIES_2022_HISTORICAL_SOURCE_REPLAY_NOT_A_2022_DIRECT_SURVEY"
SOURCE_URL = "https://www2.census.gov/programs-surveys/aies/data/2024/API_Datasets/AIESTIMESERIES.zip"
ZIP_SHA256 = "1487da6e619f2e9701635a7f6ad2ab282302d75921e33797060866142c0d94a4"
ZIP_BYTES = 771290
DAT_MEMBER = "AIESTIMESERIES.dat"
DAT_SHA256 = "a8053af22913f1872a10a5d386a602d7a3bbecfdd4441727b8a70ecde4235648"
DAT_BYTES = 6800762
DAT_ROWS = 23448
DAT_FIELDS = 89
MEMBER_NAMES = {DAT_MEMBER, "AIESTIMESERIES_FIELDS.txt", "AIESTIMESERIES_README.txt"}
MIN_DATE = date(2026, 10, 11)
YEARS = (2022, 2023, 2024)
NAICS = ("484", "484121", "484122")
EXPECTED_LABELS = {
    "484": "Truck transportation",
    "484121": "General freight trucking, long-distance, truckload",
    "484122": "General freight trucking, long-distance, less than truckload",
}
EXPECTED_VALUES = {
    (year, naics): value
    for naics, info in RECORDS.items()
    for year, value in zip(YEARS, info["values"])
}
EXPECTED_CV = {
    (2022, code): "0" for code in NAICS
} | {
    (2023, "484"): ".6", (2023, "484121"): "1.1", (2023, "484122"): ".9",
    (2024, "484"): ".6", (2024, "484121"): "1.1", (2024, "484122"): ".9",
}
SELECTOR_FIELDS = {
    "#GEOTYPE", "ST", "GEO_ID", "GEO_LABEL", "GEO_ID_F",
    "NAICS", "NAICS_LABEL", "NAICS_F", "TYPOP", "TYPOP_LABEL",
    "TAXSTAT", "TAXSTAT_LABEL", "YEAR", "RCPT_TOT_VAL",
    "RCPT_TOT_VAL_F", "RCPT_TOT_CV", "RCPT_TOT_CV_F",
}
BOOLEAN_HOLDS = (
    "raw_2022_aies_standalone_survey_collected",
    "historical_2022_source_archive_aies_original_year_file_found",
    "original_2022_sas_benchmark_source_rows_verified",
    "legacy_2022_sas_interchangeable_with_2024_aies_timeseries",
    "is_2022_published_cv_zero_proof_of_exact_population",
    "calculated_sample_linking_factor_disclosed",
    "cross_series_growth_or_2022_to_2024_cagr_certified",
    "linked_2022_2024_change_is_invoice_error_rate",
    "actual_recoveries_proven", "commercial_marketing_allowed",
    "real_customer_data_or_carrier_records_present",
    "lab_count_modified", "pilot_18_real_data_gates_satisfied",
)
REQUIRED_BOOK_KEYS = {
    "schema_version","scope","observed_on","source_url",
    "original_archive_size_bytes","original_archive_sha256",
    "original_data_member","original_data_member_bytes",
    "original_data_member_sha256","original_data_field_count",
    "original_data_row_count","archive_members","publication_date",
    "census_reference_years","source_methodology",
    "source_historical_api_documentation","sample_linkage",
    "naics_source","geographic_scope","population","revenue_metric",
    "same_source_family","observations","legacy_sas_2022_series",
    "legacy_sas_2022_revenue_million_usd",
    "legacy_sas_series_url","benchmark_sas_2022_release_url",
    "benchmark_sas_2022_release_date","reconciliation_status",
    "customer_paid_invoices_observed","recovery_tam_usd",*BOOLEAN_HOLDS,
}
VERIFIED = "VERIFIED_CENSUS_2024_HISTORICAL_ZIP_2022_REVENUE_LEGACY_LINKED"
BLOCKED = "BLOCKED_CENSUS_HISTORICAL_ZIP_UNAVAILABLE_NO_NEW_REPLAY"
OFFLINE = "OFFLINE_HISTORICAL_METADATA_ONLY_NO_SOURCE_REPLAY"
MAX_FETCH = 2_000_000


def _blob_id(raw: bytes) -> str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _read_manifest() -> dict:
    raw = BOOK.read_bytes()
    if _blob_id(raw) != BOOK_GIT_BLOB_SHA1:
        raise ValueError("M21_FROZEN_HISTORICAL_MANIFEST_DRIFT")
    return json.loads(raw.decode("utf-8"))


def validate_manifest(book: object, *, as_of: date) -> list[str]:
    try:
        if type(book) is not dict or set(book) != REQUIRED_BOOK_KEYS or book.get("schema_version") != 1:
            return ["M21_MANIFEST_SCHEMA_OR_EXTRA_SENSITIVE_FIELDS"]
        problems = []
        exact = {
            "scope":"LAB14_CENSUS_AIES_2022_HISTORICAL_PUBLISHER_ARCHIVE_NOT_A_NEW_2022_SURVEY",
            "observed_on":"2026-10-11", "source_url":SOURCE_URL,
            "original_archive_size_bytes":ZIP_BYTES,"original_archive_sha256":ZIP_SHA256,
            "original_data_member":DAT_MEMBER,"original_data_member_bytes":DAT_BYTES,
            "original_data_member_sha256":DAT_SHA256,
            "original_data_field_count":DAT_FIELDS,"original_data_row_count":DAT_ROWS,
            "archive_members":sorted(MEMBER_NAMES),
            "publication_date":"2026-09-10", "census_reference_years":[2022,2023,2024],
            "source_methodology":"https://www2.census.gov/programs-surveys/aies/technical-documentation/methodology/2023-aies-methodology.pdf",
            "source_historical_api_documentation":"https://www.census.gov/data/developers/data-sets/aiestimeseries.html",
            "sample_linkage":"2022 is a backcast/linked historical observation with legacy survey benchmark, not an independently collected original 2022 AIES survey.",
            "naics_source":"2017_NAICS","geographic_scope":"0100000US",
            "population":"NATIONAL_US_ALL_ESTABLISHMENTS_TYPOP00_TAXSTAT00",
            "revenue_metric":"RCPT_TOT_VAL_IN_THOUSANDS_OF_NOMINAL_US_DOLLARS",
            "same_source_family":"SINGLE_2024_AIES_HISTORICAL_CENSUS_TIME_SERIES_NOT_THREE_INDEPENDENT_SURVEYS",
            "legacy_sas_2022_series":"REVEF484122ALLEST",
            "legacy_sas_2022_revenue_million_usd":68411,
            "legacy_sas_series_url":"https://fred.stlouisfed.org/data/REVEF484122ALLEST",
            "benchmark_sas_2022_release_url":"https://www.census.gov/data/tables/2022/econ/services/sas-naics.html",
            "benchmark_sas_2022_release_date":"2026-08-31",
            "reconciliation_status":"PUBLISHED_AIES_HISTORICAL_2022_SOURCE_VERIFIED_BUT_LEGACY_SAS_VINTAGE_DIFFERENCE_NOT_FULLY_ADJUDICATED",
            "customer_paid_invoices_observed":0,"recovery_tam_usd":None,
        }
        if type(as_of) is not date or as_of < MIN_DATE:
            problems.append("M21_SOURCE_TIME_TRAVEL_FORBIDDEN")
        for key, value in exact.items():
            if type(book.get(key)) != type(value) or book.get(key) != value:
                problems.append("M21_SOURCE_SCHEMA_OR_PROVENANCE_CHANGED:"+key)
        for key in BOOLEAN_HOLDS:
            if book.get(key) is not False:
                problems.append("M21_UNSUPPORTED_HISTORICAL_OR_COMMERCIAL_PROMOTION:"+key)
        rows=book.get("observations")
        if type(rows) is not list or len(rows)!=9:
            return problems+["M21_EXACTLY_NINE_HISTORIC_NAICS_SOURCE_CELLS_REQUIRED"]
        seen=set()
        for row in rows:
            if type(row) is not dict or set(row)!={"year","naics","revenue_thousand_usd","published_cv_raw"}:
                problems.append("M21_OBSERVATION_EXTRA_FIELDS_OR_MISSING_COLUMNS")
                continue
            key=(row.get("year"),row.get("naics"))
            if key not in EXPECTED_VALUES or key in seen:
                problems.append("M21_DUPLICATED_OR_UNEXPECTED_YEAR_NAICS_KEY")
                continue
            seen.add(key)
            if (type(row["year"]) is not int
                or type(row["revenue_thousand_usd"]) is not int
                or row["revenue_thousand_usd"] != EXPECTED_VALUES[key]
                or row["published_cv_raw"] != EXPECTED_CV[key]):
                problems.append("M21_PUBLISHED_SOURCE_REVENUE_OR_CV_CHANGED:"+str(key))
        if seen != set(EXPECTED_VALUES):
            problems.append("M21_NINE_YEAR_NAICS_KEYS_NOT_COMPLETE")
        return problems
    except (AttributeError,KeyError,ValueError,TypeError):
        return ["M21_SOURCE_MANIFEST_CORRUPT"]


def _prior(as_of: date, book: dict | None = None) -> tuple[dict,dict,dict]:
    if book is None:
        book = _read_manifest()
    issues=validate_manifest(book,as_of=as_of)
    if issues:
        raise ValueError("M21_MANIFEST_INVALID: "+"; ".join(issues))
    m18=build_revenue(as_of=as_of)
    m20=prior_historical(as_of=as_of)
    if (m18.get("real_ltl_invoice_cases_observed")!=0 or
        m18.get("ltl_freight_audit_recoverable_tam_usd") is not None or
        m20.get("actual_paid_ltl_invoices_observed")!=0 or
        not m20.get("year_2022_status","").startswith("HOLD_")):
        raise ValueError("M21_PRIOR_RESEARCH_GOVERNANCE_REGRESSION")
    previous={row["year"]:row for row in m18["revenue_by_year"]}
    if len(previous)!=3:
        raise ValueError("M21_M18_HISTORIC_POPULATION_MISSING")
    for (year, naics), val in EXPECTED_VALUES.items():
        field={"484":"all_trucking_484_thousand_usd",
               "484121":"tl_484121_thousand_usd",
               "484122":"ltl_484122_thousand_usd"}[naics]
        if previous[year][field] != val:
            raise ValueError("M21_HISTORIC_REVENUE_M18_NOT_SAME_AS_CENSUS")
    return m18,m20,book


def selected_cells(rows: list[dict]) -> list[dict]:
    """This comparison alone cannot authenticate a ZIP's origin."""
    if type(rows) is not list or not rows:
        raise ValueError("M21_ORIGINAL_SOURCE_ROWS_REQUIRED")
    selected={}
    for row in rows:
        if type(row) is not dict or not SELECTOR_FIELDS <= set(row):
            raise ValueError("M21_DAT_SOURCE_COLUMNS_INCOMPLETE")
        if not (row.get("#GEOTYPE")=="01" and row.get("ST")=="00"
                and row.get("GEO_ID")=="0100000US" and row.get("GEO_LABEL")=="United States"
                and row.get("TYPOP")=="00" and row.get("TAXSTAT")=="00"
                and row.get("YEAR") in ("2022","2023","2024")
                and row.get("NAICS") in NAICS):
            continue
        key=(int(row["YEAR"]),row["NAICS"])
        if key in selected:
            raise ValueError("M21_DUPLICATE_2022_2024_NATIONAL_SOURCE_ROW:"+str(key))
        if (row["GEO_ID_F"]!="" or row["NAICS_F"]!=""
            or row["RCPT_TOT_VAL_F"]!="" or row["RCPT_TOT_CV_F"]!=""):
            raise ValueError("M21_CENSUS_SOURCE_SUPPRESSION_OR_QUALITY_FLAG:"+str(key))
        if (row["TYPOP_LABEL"].casefold()!="all establishments"
            or row["TAXSTAT_LABEL"].casefold()!="all establishments"):
            raise ValueError("M21_NOT_ALL_EMPLOYER_ESTABLISHMENTS:"+str(key))
        if row["NAICS_LABEL"].casefold()!=EXPECTED_LABELS[key[1]].casefold():
            raise ValueError("M21_NAICS2017_SOURCE_POPULATION_MISMATCH:"+str(key))
        if type(row["RCPT_TOT_VAL"]) is not str or not re.fullmatch(r"\d{1,14}",row["RCPT_TOT_VAL"]):
            raise ValueError("M21_HISTORICAL_REVENUE_NON_INTEGER_OR_SUPPRESSED:"+str(key))
        value=int(row["RCPT_TOT_VAL"])
        if value != EXPECTED_VALUES[key]:
            raise ValueError("M21_CENSUS_PRIMARY_HISTORIC_VS_FRED_DISAGREEMENT:"+str(key))
        cv=row["RCPT_TOT_CV"]
        if cv != EXPECTED_CV[key]:
            raise ValueError("M21_HISTORICAL_CV_SOURCE_CELL_MISMATCH:"+str(key))
        selected[key] = {
            "year":key[0],"naics":key[1],
            "revenue_thousand_usd":value,
            "published_cv_raw":cv,
            "source_year_direct_2022_aies_survey_collected":False if key[0]==2022 else True,
            "cv_is_not_an_invoice_error_rate":True,
            "historical_2022_cv_zero_does_not_establish_zero_uncertainty":key[0]==2022,
        }
    if set(selected)!=set(EXPECTED_VALUES):
        raise ValueError("M21_CENSUS_HISTORIC_NINE_KEYS_MISSING:"+str(sorted(set(EXPECTED_VALUES)-set(selected))))
    return [selected[(year,naics)] for year in YEARS for naics in NAICS]


def _shell(as_of: date) -> dict:
    m18,m20,book=_prior(as_of)
    result={
        "schema_version":1,"scope":SCOPE,"as_of":as_of.isoformat(),
        "status":OFFLINE,"lab":14,"new_lab_created":False,
        "official_census_source_url":SOURCE_URL,
        "verified_source_zip_sha256":None,"verified_source_dat_sha256":None,
        "source_zip_bytes":None,"source_dat_bytes":None,
        "source_dat_rows":None,"source_dat_fields":None,
        "matched_national_year_naics_source_cells":0,"selected_source_cells":[],
        "published_2022_historical_ltl_revenue_thousand_usd":65688461,
        "published_2023_ltl_revenue_thousand_usd":64651167,
        "published_2024_ltl_revenue_thousand_usd":65096292,
        "2022_historical_source_status":"PUBLISHED_HISTORICAL_REVENUE_UNREPLAYED_OFFLINE",
        "2022_collected_under_standalone_original_aies_survey":False,
        "2022_cv_zero_means_exact_no_uncertainty":False,
        "legacy_sas_2022_revenue_million_usd":68411,
        "legacy_sas_gap_million_usd":str(
            Decimal("68411")-Decimal("65688461")/Decimal("1000")
        ),
        "legacy_sas_gap_assigned_causal_mechanism":None,
        "latest_2022_sas_benchmark_original_rows_replayed":False,
        "legacy_sas_2022_vintage_mismatch_still_unadjudicated":True,
        "historical_2022_to_2024_growth_significance_proven":False,
        "separate_2022_2023_2024_independent_survey_count":None,
        "source_family_is_not_independent_samples":True,
        "m18_source_snapshot_receipt_sha256":m18["receipt_sha256"],
        "m20_offline_source_receipt_sha256":m20["receipt_sha256"],
        "frozen_source_manifest_receipt_sha256":canon_hash(book),
        "actual_customer_invoice_rows_processed":0,
        "actual_issued_refunds_or_recoveries_proven":False,
        "invoice_error_prevalence_pct":None,
        "ltl_recoverable_market_tam_usd":None,
        "buyer_demand_established":False,
        "external_contact_or_commercial_claims_authorized":False,
        "human_pilot_18_controls_still_unverified":True,
        "automatic_source_refresh_or_schedule_created":False,
        "caveat":(
            "The source is an original Census publisher historical time-series "
            "ZIP, but its 2022 observations are linked to earlier surveys via "
            "Census carry-forward/benchmark methodology, not an independently "
            "fielded original 2022 AIES survey. A published 2022 CV of 0 is "
            "not proof of perfect population measurement or a 0 percent invoice "
            "error rate. Older legacy SAS 2022 figures may reflect different "
            "benchmark/vintage; without comparable SAS original row-level "
            "verification no exact cause of the gap is certified. All observed "
            "goods and carrier revenue measures remain separate from invoices, "
            "contractual overcharges, recoveries or market opportunity."
        ),
    }
    result["receipt_sha256"]=canon_hash(result)
    return result


def verify_archive(raw: bytes, *, as_of: date) -> dict:
    if type(raw) is not bytes or len(raw)!=ZIP_BYTES:
        raise ValueError("M21_ORIGINAL_CENSUS_ZIP_SIZE_MISMATCH")
    if sha256(raw).hexdigest()!=ZIP_SHA256:
        raise ValueError("M21_ORIGINAL_CENSUS_ZIP_SHA256_DRIFT")
    members,z=_archive_members(raw)
    if {x["member"] for x in members} != MEMBER_NAMES:
        raise ValueError("M21_UNEXPECTED_ORIGINAL_ARCHIVE_MEMBER")
    header,rows=_parse_tabular(z,DAT_MEMBER)
    if len(header)!=DAT_FIELDS or not SELECTOR_FIELDS <= set(header):
        raise ValueError("M21_HISTORICAL_SOURCE_HEADER_SCHEMA_CHANGED")
    if len(rows)!=DAT_ROWS:
        raise ValueError("M21_HISTORICAL_SOURCE_ROW_COUNT_CHANGED")
    dat=z.read(DAT_MEMBER)
    if len(dat)!=DAT_BYTES or sha256(dat).hexdigest()!=DAT_SHA256:
        raise ValueError("M21_ORIGINAL_CENSUS_DAT_INTEGRITY_DRIFT")
    chosen=selected_cells(rows)
    result=_shell(as_of)
    result.update({
        "status":VERIFIED,
        "verified_source_zip_sha256":sha256(raw).hexdigest(),
        "verified_source_dat_sha256":sha256(dat).hexdigest(),
        "source_zip_bytes":len(raw),"source_dat_bytes":len(dat),
        "source_dat_rows":len(rows),"source_dat_fields":len(header),
        "matched_national_year_naics_source_cells":len(chosen),
        "selected_source_cells":chosen,
        "2022_historical_source_status":"ORIGINAL_CENSUS_PUBLISHER_HISTORICAL_DATA_REPLAYED_LEGACY_LINKED_NOT_DIRECT_2022_AIES_SURVEY",
    })
    result["receipt_sha256"]=canon_hash({k:v for k,v in result.items() if k!="receipt_sha256"})
    return result


def blocked(*, as_of: date) -> dict:
    result=_shell(as_of)
    result["status"]=BLOCKED
    result["receipt_sha256"]=canon_hash({k:v for k,v in result.items() if k!="receipt_sha256"})
    return result


def _fetch_census_original() -> bytes:
    req=Request(SOURCE_URL,headers={"User-Agent":"RETALLY-Lab14-AIES-Historic-SourceCheck/1.0"})
    with urlopen(req,timeout=30) as resp:
        if resp.geturl()!=SOURCE_URL:
            raise ValueError("M21_OFFICIAL_HTTPS_SOURCE_REDIRECTED")
        data=resp.read(MAX_FETCH+1)
    if len(data)>MAX_FETCH:
        raise ValueError("M21_ARCHIVE_EXCEEDS_SOURCE_BYTE_LIMIT")
    return data


def render_html(result: dict) -> str:
    body="".join(
        "<tr><td>"+str(x["year"])+"</td><td>"+escape(x["naics"])+
        "</td><td>"+format(x["revenue_thousand_usd"],",")+
        "</td><td>"+escape(x["published_cv_raw"])+
        "</td><td>"+("Legacy linked, no independent 2022 AIES"
                      if x["year"]==2022 else "Direct year within historical product")+
        "</td></tr>"
        for x in result["selected_source_cells"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | Historical Census Source Integrity</title></head>'
        '<body style="font:16px/1.6 system-ui;background:#f6f9f7;color:#1b392e">'
        '<main style="max-width:1100px;margin:35px auto;padding:20px">'
        '<small>RESEARCH ONLY / LAB 14 / MISSION 21</small>'
        '<h1>2022 Census historical figure: publisher verified, legacy linked</h1>'
        '<p>Status: <strong>'+escape(result["status"])+'</strong></p>'
        '<p>2022 LTL published Census historical revenue: $65.688461B '
        '(not 2022 direct AIES fielding). Prior legacy SAS vintage: '
        '$68.411B; difference: $'+escape(result["legacy_sas_gap_million_usd'])+
        ' million. The original SAS benchmark comparison is still unadjudicated.</p>'
        '<table style="border-collapse:collapse;background:white"><thead><tr>'
        '<th>Year</th><th>2017 NAICS</th><th>Revenue ($1,000)</th>'
        '<th>Census CV raw</th><th>Interpretation</th></tr></thead><tbody>'+
        body+'</tbody></table><p>'+escape(result["caveat"])+
        '</p><p><a href="'+escape(result["official_census_source_url"])+
        '">Original Census historical ZIP</a></p>'
        '</main></body></html>'
    )


def main() -> None:
    parser=argparse.ArgumentParser(description="Lab14 2022 publisher historic evidence")
    parser.add_argument("--as-of-date",default=date.today().isoformat())
    parser.add_argument("--out",type=Path,required=True)
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline",action="store_true")
    modes.add_argument("--fetch-original",action="store_true")
    modes.add_argument("--from-local",type=Path)
    args=parser.parse_args()
    as_of=date.fromisoformat(args.as_of_date)
    if args.fetch_original:
        try:
            raw=_fetch_census_original()
        except (OSError,TimeoutError):
            report=blocked(as_of=as_of)
        else:
            report=verify_archive(raw,as_of=as_of)
    elif args.from_local:
        report=verify_archive(_read_archive(args.from_local),as_of=as_of)
    else:
        report=_shell(as_of)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"aies_2022_lineage.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    (args.out/"aies_2022_lineage.html").write_text(
        render_html(report),encoding="utf-8"
    )
    print(json.dumps({
        "source_status":report["status"],
        "selected_source_cells":report["matched_national_year_naics_source_cells"],
        "2022_direct_aies_survey_collected":False,
        "2022_historical_source_verified":report["status"]==VERIFIED,
        "real_customer_recoveries_or_pilot_approvals":False,
        "receipt_sha256":report["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
