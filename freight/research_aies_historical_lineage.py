"""RETALLY Research Lab 14 Mission 20: source-bound AIES historical lineage.

Validate two original 2023 Census ZIPs and the separately pinned 2024
original ZIP, keeping 2022 historical Census/FRED legacy observations on HOLD.
Carrier industry revenue is not customer-paid LTL invoices or recoveries.
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

from freight.research_cfs_archive_verifier import (
    _archive_members, _parse_tabular, _read_archive,
)
from freight.research_aies_original_ftp import (
    SOURCE_URL as CENSUS_2024_URL,
    verify_original_bytes as verify_m19_original_2024,
)
from freight.research_ltl_revenue_bridge import RECORDS, build_revenue
from freight.research_evidence_gate import canon_hash

ROOT = Path(__file__).parent
BOOK = ROOT / "research/AIES_HISTORICAL_LINEAGE_20261011.json"
EXPECTED_BOOK_BLOB_SHA1 = "28c42b6f17e300bac28b1bd11c828aa233bc901b"
SCOPE = "LAB14_AIES_2023_ORIGINAL_HISTORICAL_LINEAGE_NOT_LTL_BILLINGS"
CATALOG_SCOPE = "LAB14_CENSUS_AIES_2023_PRIMARY_ARCHIVES_NOT_2022_LEGACY_PROOF"
VERIFIED = "VERIFIED_2023_AND_2024_CENSUS_ORIGINALS_2022_ON_HOLD"
OFFLINE = "OFFLINE_SOURCE_METADATA_ONLY_NO_FRESH_CENSUS_REPLAY"
BLOCKED = "BLOCKED_ORIGINAL_CENSUS_ARCHIVE_FETCH_NOT_VERIFIED"
MIN_DATE = date(2026, 10, 11)
URLS = {
    "2023_published": "https://www2.census.gov/programs-surveys/aies/data/2023/API_Datasets/AIESBASIC2023.zip",
    "2023_timeseries": "https://www2.census.gov/programs-surveys/aies/data/2023/API_Datasets/AIESBASICTIMESERIES.zip",
    "2024_published": CENSUS_2024_URL,
}
PINNED = {
    "2023_published": ("7da68855e995342d9039c3c2f146eee72f079eabcd9a9620e34c3596d2e4ce9e",
                       819756, "AIESBASIC2023.dat", 5987194, 13512, "NAICS2017"),
    "2023_timeseries": ("5e69e6a025ec25398321242b170c384b57e45bce522cdadd843ec39e13dffb69",
                        846487, "AIESBASICTIMESERIES.dat", 6936210, 13512, "NAICS"),
}
EXPECTED_2023 = {
    "484": ("Truck transportation", 406651010, "0.6"),
    "484121": ("General freight trucking, long-distance, truckload", 163025116, "1.1"),
    "484122": ("General freight trucking, long-distance, less than truckload", 64651167, "0.9"),
}
SOURCE_REQUIRED = {
    "#GEOTYPE", "ST", "GEO_ID", "GEO_LABEL", "GEO_ID_F", "NAICS_F",
    "TYPOP", "TYPOP_LABEL", "TAXSTAT", "TAXSTAT_LABEL", "YEAR",
    "RCPT_TOT_VAL", "RCPT_TOT_VAL_F", "RCPT_TOT_CV", "RCPT_TOT_CV_F",
}
GUARD_FIELDS = {
    "schema_version", "scope", "observed_on", "publisher",
    "data_reference_year", "source_families_are_not_independent",
    "historical_2022_2023_methodology", "source_year_2022_original_reproduced",
    "census_historical_2024_url_probe",
    "census_historical_2024_url_probe_http_status",
    "source_2024_primary_verification", "sources", "selected_industries",
    "referenced_m18_2022_historical_ltl_thousand_usd",
    "referenced_m18_2024_ltl_thousand_usd", "historical_2022_census_original_replay",
    "original_2024_census_replay_in_this_manifest",
    "verified_real_customer_ltl_invoices", "industry_revenue_equals_customer_spend",
    "ltl_recovery_tam_usd", "real_overcharges_or_cash_recovery_proven",
    "buyer_demand_proven", "human_pilot_18_gates_completed",
    "publication_or_marketing_allowed", "customer_or_carrier_data_used",
    "new_lab_created", "source_caveat",
}
SOURCE_KEYS = {
    "id", "url", "sha256", "archive_bytes", "member", "dat_bytes",
    "dat_rows", "naics_field", "data_grain",
}
MAX_ZIP_BYTES = 2_000_000


def _git_blob_sha1(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _read_book() -> dict:
    raw = BOOK.read_bytes()
    if _git_blob_sha1(raw) != EXPECTED_BOOK_BLOB_SHA1:
        raise ValueError("M20_SOURCE_MANIFEST_GIT_BLOB_CHANGED")
    return json.loads(raw.decode("utf-8"))


def validate_manifest(book: object, *, as_of: date) -> list[str]:
    try:
        err = []
        if type(book) is not dict or set(book) != GUARD_FIELDS or book.get("schema_version") != 1:
            return ["M20_MANIFEST_SCHEMA_OR_PRIVATE_FIELDS_INVALID"]
        if as_of < MIN_DATE or book.get("observed_on") != MIN_DATE.isoformat():
            err.append("M20_MANIFEST_SOURCE_DATE_INVALID")
        literals = {
            "scope": CATALOG_SCOPE, "publisher": "U.S. Census Bureau",
            "data_reference_year": 2023,
            "source_families_are_not_independent": "TWO_2023_CENSUS_DISTRIBUTIONS_OF_SAME_AIES_POPULATION",
            "historical_2022_2023_methodology": "AIES_STARTED_WITH_2023_REFERENCE_PERIOD_AND_INCORPORATED_LEGACY_SURVEYS_IN_HISTORICAL_SERIES",
            "census_historical_2024_url_probe": "2024/API_Datasets/AIESBASICTIMESERIES.zip",
            "census_historical_2024_url_probe_http_status": 404,
            "source_2024_primary_verification": "M19_2024_AIES00BASIC_ZIP_REPLAYED_IN_SEPARATE_JOB_OR_BRANCH",
            "referenced_m18_2022_historical_ltl_thousand_usd": 65688461,
            "referenced_m18_2024_ltl_thousand_usd": 65096292,
            "ltl_recovery_tam_usd": None,
            "verified_real_customer_ltl_invoices": 0,
        }
        for key, value in literals.items():
            if type(book.get(key)) != type(value) or book.get(key) != value:
                err.append("M20_SOURCE_VERSION_SCOPE_OR_MEASURE_CHANGED:" + key)
        for flag in (
            "source_year_2022_original_reproduced", "historical_2022_census_original_replay",
            "original_2024_census_replay_in_this_manifest", "industry_revenue_equals_customer_spend",
            "real_overcharges_or_cash_recovery_proven", "buyer_demand_proven",
            "human_pilot_18_gates_completed", "publication_or_marketing_allowed",
            "customer_or_carrier_data_used", "new_lab_created",
        ):
            if book.get(flag) is not False:
                err.append("M20_UNSUPPORTED_COMMERCIAL_OR_SOURCE_PROMOTION:" + flag)
        caveat = book.get("source_caveat")
        if (type(caveat) is not str or len(caveat) < 350
            or "2022" not in caveat or "not independent" not in caveat.lower()
            or "not invoice" not in caveat.lower()):
            err.append("M20_MISSING_REQUIRED_2022_SOURCE_CAVEAT")
        sources = book.get("sources")
        if type(sources) is not list or len(sources) != 2:
            return err + ["M20_TWO_ORIGINAL_2023_SOURCE_ARCHIVES_REQUIRED"]
        seen = set()
        for item in sources:
            if type(item) is not dict or set(item) != SOURCE_KEYS:
                err.append("M20_SOURCE_ARCHIVE_METADATA_INVALID")
                continue
            ident = item.get("id")
            if ident not in PINNED or ident in seen:
                err.append("M20_UNKNOWN_OR_DUPLICATE_SOURCE_ARCHIVE")
                continue
            seen.add(ident)
            fingerprint, size, member, dat_bytes, rows, naics = PINNED[ident]
            expected = {
                "id": ident, "url": URLS[ident], "sha256": fingerprint,
                "archive_bytes": size, "member": member,
                "dat_bytes": dat_bytes, "dat_rows": rows, "naics_field": naics,
                "data_grain": (
                    "2023_CENSUS_AIES_ALL_ESTABLISHMENTS_NATIONAL_INDUSTRY"
                    if ident=="2023_published" else
                    "2023_CENSUS_AIES_HISTORICAL_DISTRIBUTION_NATIONAL_INDUSTRY"
                ),
            }
            if item != expected:
                err.append("M20_SOURCE_ARCHIVE_IDENTITY_OR_FINGERPRINT_CHANGED:" + ident)
        if seen != set(PINNED):
            err.append("M20_MISSING_ORIGINAL_PUBLISHER_ARCHIVE")
        values = book.get("selected_industries")
        if type(values) is not list or len(values) != 3:
            return err + ["M20_THREE_EXACT_NAICS_REVENUES_REQUIRED"]
        check = set()
        for item in values:
            if type(item) is not dict or set(item) != {
                "naics", "label", "revenue_thousand_usd", "revenue_cv_pct",
            }:
                err.append("M20_NAICS_RECORD_SCHEMA_INVALID")
                continue
            code = item.get("naics")
            if code not in EXPECTED_2023 or code in check:
                err.append("M20_NAICS_NOT_UNIQUE_OR_UNKNOWN")
                continue
            check.add(code)
            label, val, cv = EXPECTED_2023[code]
            if item != {"naics":code,"label":label,"revenue_thousand_usd":val,"revenue_cv_pct":cv}:
                err.append("M20_NAICS_REVENUE_OR_CV_TAMPER:" + code)
        if check != set(EXPECTED_2023):
            err.append("M20_THREE_NAICS_COVERAGE_INCOMPLETE")
        return err
    except (TypeError, KeyError, ValueError, AttributeError):
        return ["M20_MALFORMED_MANIFEST"]


def _baseline(as_of: date, book: dict | None = None) -> tuple[dict, dict]:
    if type(as_of) is not date or as_of < MIN_DATE:
        raise ValueError("M20_DATE_BEFORE_SOURCE_OBSERVATION")
    if book is None:
        book = _read_book()
    bad = validate_manifest(book, as_of=as_of)
    if bad:
        raise ValueError("M20_SOURCE_PROVENANCE_INVALID: "+"; ".join(bad))
    prior = build_revenue(as_of=as_of)
    years = {x["year"]: x for x in prior["revenue_by_year"]}
    if set(years) != {2022,2023,2024} or prior["ltl_freight_audit_recoverable_tam_usd"] is not None:
        raise ValueError("M20_M18_PRIOR_LINEAGE_INVALID")
    if (years[2022]["ltl_484122_thousand_usd"] != 65688461 or
        years[2023]["ltl_484122_thousand_usd"] != 64651167 or
        years[2024]["ltl_484122_thousand_usd"] != 65096292 or
        prior["real_ltl_invoice_cases_observed"] != 0):
        raise ValueError("M20_M18_HISTORICAL_SERIES_CHANGED")
    return prior, book


def _pct_change(after: int, before: int) -> str:
    return str(((Decimal(after)-Decimal(before))*100/Decimal(before)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP))


def select_national_2023(rows: list[dict], *, naics_field: str) -> list[dict]:
    """Exact national all-establishment 2023 industry grain; no source origin proof."""
    if naics_field not in ("NAICS2017","NAICS") or type(rows) is not list:
        raise ValueError("M20_WRONG_NAICS_COLUMN_OR_ROWS")
    required = SOURCE_REQUIRED | {naics_field, naics_field+"_LABEL"}
    observed = {}
    for row in rows:
        if type(row) is not dict or not required <= set(row):
            raise ValueError("M20_MALFORMED_OFFICIAL_DATA_ROW")
        if not (row["#GEOTYPE"] == "01" and row["ST"] == "00"
                and row["GEO_ID"] == "0100000US"
                and row["GEO_LABEL"] == "United States"
                and row["TYPOP"] == "00" and row["TAXSTAT"] == "00"
                and row["YEAR"] == "2023" and row[naics_field] in EXPECTED_2023):
            continue
        code = row[naics_field]
        if code in observed:
            raise ValueError("M20_DUPLICATE_NATIONAL_INDUSTRY_SOURCE_ROW:"+code)
        label, val, cv = EXPECTED_2023[code]
        if row[naics_field+"_LABEL"].casefold() != label.casefold():
            raise ValueError("M20_SOURCE_NAICS_LABEL_INCORRECT:"+code)
        for f in ("GEO_ID_F","NAICS_F","RCPT_TOT_VAL_F","RCPT_TOT_CV_F"):
            if row[f] != "":
                raise ValueError("M20_CENSUS_ESTIMATE_SUPPRESSED_OR_FLAGGED:"+code+":"+f)
        if (row["TYPOP_LABEL"].casefold() != "all establishments"
            or row["TAXSTAT_LABEL"].casefold() != "all establishments"):
            raise ValueError("M20_NOT_ALL_EMPLOYER_ESTABLISHMENTS:"+code)
        if type(row["RCPT_TOT_VAL"]) is not str or not re.fullmatch(r"\d{1,14}",row["RCPT_TOT_VAL"]):
            raise ValueError("M20_SOURCE_REVENUE_NOT_PUBLISHED_INTEGER:"+code)
        value = int(row["RCPT_TOT_VAL"])
        if value != val:
            raise ValueError("M20_FRED_CENSUS_REVENUE_DISAGREEMENT:"+code)
        source_cv = row["RCPT_TOT_CV"]
        if type(source_cv) is not str or not re.fullmatch(r"(?:\d{1,3})?(?:\.\d{1,4})",source_cv):
            raise ValueError("M20_SOURCE_CV_INVALID:"+code)
        try:
            dcv=Decimal(source_cv)
        except InvalidOperation as exc:
            raise ValueError("M20_SOURCE_CV_NONNUMERIC:"+code) from exc
        if not dcv.is_finite() or dcv<0 or dcv>100 or dcv!=Decimal(cv):
            raise ValueError("M20_SOURCE_CV_DIFFERS_FROM_PINNED_CENSUS:"+code)
        observed[code] = {
            "naics": code, "label":row[naics_field+"_LABEL"],
            "year":2023, "revenue_thousand_usd":value,
            "published_cv_pct":str(dcv), "all_quality_flags_unset":True,
        }
    if set(observed) != set(EXPECTED_2023):
        raise ValueError("M20_CENSUS_2023_NAICS_INCOMPLETE:"+str(sorted(set(EXPECTED_2023)-set(observed))))
    return [observed[code] for code in ("484","484121","484122")]


def inspect_2023_zip(raw: bytes, *, source: dict) -> dict:
    ident = source["id"]
    if ident not in PINNED or source["url"]!=URLS[ident] or type(raw) is not bytes:
        raise ValueError("M20_UNRECOGNIZED_ARCHIVE")
    expected_sha, expected_size, member, dat_size, count, naics = PINNED[ident]
    if len(raw)!=expected_size:
        raise ValueError("M20_OFFICIAL_ZIP_BYTE_LENGTH_MISMATCH:"+ident)
    digest=sha256(raw).hexdigest()
    if digest!=expected_sha:
        raise ValueError("M20_OFFICIAL_ZIP_SHA256_CHANGED:"+ident)
    members,archive=_archive_members(raw)
    expected_names={member,member.replace(".dat","_FIELDS.txt"),member.replace(".dat","_README.txt")}
    if {x["member"] for x in members}!=expected_names:
        raise ValueError("M20_CENSUS_ZIP_MEMBER_CENSUS_CHANGED:"+ident)
    header,rows=_parse_tabular(archive,member)
    if (naics not in header or naics+"_LABEL" not in header or
        not SOURCE_REQUIRED <= set(header)):
        raise ValueError("M20_CENSUS_SOURCE_FIELD_SCHEMA_CHANGED:"+ident)
    if len(rows)!=count:
        raise ValueError("M20_CENSUS_SOURCE_ROW_COUNT_CHANGED:"+ident)
    original=archive.read(member)
    if len(original)!=dat_size:
        raise ValueError("M20_CENSUS_DAT_ORIGINAL_LENGTH_CHANGED:"+ident)
    results=select_national_2023(rows,naics_field=naics)
    return {
        "source_id":ident,"source_url":source["url"],
        "zip_sha256":digest, "zip_bytes":len(raw),
        "data_member":member,
        "data_member_sha256":sha256(original).hexdigest(),
        "data_member_bytes":len(original),
        "source_rows_total":len(rows),
        "source_field_count":len(header),
        "source_2023_naics_rows":results,
        "source_selects_2023_only":True,
        "government_publisher_digitally_signed_bytes":False,
    }


def report_shell(*, as_of: date, book: dict | None = None) -> dict:
    prior, catalog = _baseline(as_of,book)
    rev2023=EXPECTED_2023["484122"][1]
    rev2024=RECORDS["484122"]["values"][2]
    report={
        "schema_version":1,"scope":SCOPE,"lab":14,"new_lab_created":False,
        "as_of":as_of.isoformat(),
        "status":OFFLINE,
        "manifest_source_receipt_sha256":canon_hash(catalog),
        "m18_revenue_receipt_sha256":prior["receipt_sha256"],
        "source_family_is_independent_crosscheck":False,
        "original_2023_archive_replays":[],
        "original_2024_m19_replay":None,
        "original_2023_and_2024_replayed_this_run":False,
        "year_2022_status":"HOLD_FRED_HISTORICAL_LEGACY_CONSTRUCTION_NOT_PRIMARY_ORIGINAL_ARCHIVE_REPLAY",
        "year_2023_status":"METADATA_SNAPSHOT_NOT_NEW_PRIMARY_BYTE_REPLAY",
        "year_2024_status":"M19_ORIGINAL_REPLAY_SEPARATE_PRIOR_JOB_NOT_NEW_PRIMARY_BYTE_REPLAY",
        "latest_revenue_reference_year":2024,
        "2022_m18_historical_ltl_thousand_usd_unverified_primary":65688461,
        "2023_national_ltl_thousand_usd":rev2023,
        "2024_national_ltl_thousand_usd":rev2024,
        "2023_to_2024_nominal_change_pct":_pct_change(rev2024,rev2023),
        "2022_to_2024_cagr_or_2022_to_2023_growth_promotion_allowed":False,
        "2023_to_2024_change_statistical_significance_established":False,
        "2022_legacy_sas_comparison_not_interchangeable":True,
        "actual_paid_ltl_invoices_observed":0,
        "customer_billing_error_rate_pct":None,
        "actual_cash_recovered_usd":None,
        "recoverable_freight_audit_tam_usd":None,
        "buyer_demand_verified":False,
        "customer_or_carrier_data_ingested":False,
        "marketing_contact_or_external_claims_authorized":False,
        "18_pilot_approval_requirements_unmet":True,
        "caveat":(
            "2023 AIES published and 2023 historical datasets are two "
            "distributions of the same Census source, not independent surveys. "
            "AIES current direct reference periods began with 2023; 2022 "
            "historic values incorporate earlier legacy surveys and have not "
            "been reproduced as directly observed 2022 AIES primary archive "
            "bytes here. A 2023/2024 nominal revenue difference is not "
            "statistical significance or inflation-adjusted market growth. "
            "Industry receipts are not paid customer invoices, audit errors, "
            "recoverable freight payments, or proven buyer demand."
        ),
    }
    report["receipt_sha256"]=canon_hash(report)
    return report


def verify_originals(*,as_of:date,archives:dict[str,bytes]) -> dict:
    prior,book=_baseline(as_of)
    if type(archives) is not dict or set(archives)!=set(URLS):
        raise ValueError("M20_ALL_2023_AND_2024_CENSUS_ARCHIVES_REQUIRED")
    inputs={s["id"]:s for s in book["sources"]}
    proofs=[
        inspect_2023_zip(archives[ident],source=inputs[ident])
        for ident in ("2023_published","2023_timeseries")
    ]
    lhs,rhs=proofs[0]["source_2023_naics_rows"],proofs[1]["source_2023_naics_rows"]
    if lhs!=rhs:
        raise ValueError("M20_2023_CENSUS_RELEASES_DISAGREE_WITH_EACH_OTHER")
    official2024=verify_m19_original_2024(archives["2024_published"],as_of=as_of)
    m19_2024=next(x for x in official2024["source_estimates"] if x["naics2017"]=="484122")
    if m19_2024["revenue_thousand_usd"]!=RECORDS["484122"]["values"][2]:
        raise ValueError("M20_2024_CENSUS_REVENUE_DOES_NOT_MATCH_M18")
    if not (official2024["direct_original_census_ftp_replay_completed"] and
            official2024["matched_national_industry_source_rows"]==3):
        raise ValueError("M20_M19_2024_PRIMARY_ARCHIVE_REPLAY_NOT_VERIFIED")
    report=report_shell(as_of=as_of,book=book)
    report.update({
        "status":VERIFIED,
        "original_2023_archive_replays":proofs,
        "original_2024_m19_replay":{
            "source_zip_sha256":official2024["source_archive_sha256"],
            "source_data_sha256":official2024["source_dat_sha256"],
            "source_2024_national_naics_count":3,
            "source_2024_ltl_revenue_thousand_usd":m19_2024["revenue_thousand_usd"],
            "original_source_receipt_sha256":official2024["receipt_sha256"],
        },
        "original_2023_and_2024_replayed_this_run":True,
        "year_2023_status":"2023_CENSUS_BASIC_AND_HISTORICAL_ARCHIVES_ORIGINAL_BYTES_MATCH",
        "year_2024_status":"M19_2024_CENSUS_BASIC_ORIGINAL_BYTES_MATCH_THIS_RUN",
    })
    report["receipt_sha256"]=canon_hash({k:v for k,v in report.items() if k!="receipt_sha256"})
    return report


def blocked(*,as_of:date) -> dict:
    r=report_shell(as_of=as_of)
    r["status"]=BLOCKED
    r["receipt_sha256"]=canon_hash({k:v for k,v in r.items() if k!="receipt_sha256"})
    return r


def _download_exact(ident: str) -> bytes:
    if ident not in URLS:
        raise ValueError("M20_UNAUTHORIZED_REMOTE_SOURCE_ID")
    url=URLS[ident]
    request=Request(url,headers={"User-Agent":"RETALLY-Lab14-Original-Source-Replay/1.0"})
    with urlopen(request,timeout=28) as response:
        if response.geturl()!=url:
            raise ValueError("M20_OFFICIAL_SOURCE_REDIRECTED")
        raw=response.read(MAX_ZIP_BYTES+1)
    if len(raw)>MAX_ZIP_BYTES:
        raise ValueError("M20_OFFICIAL_ARCHIVE_EXCEEDS_BOUNDED_SIZE")
    return raw


def render_html(result: dict) -> str:
    rows="".join(
        "<tr><th>"+escape(str(year))+"</th><td>"+escape(status)+"</td><td>"+
        escape(amt)+"</td></tr>"
        for year,status,amt in (
            (2022,result["year_2022_status"],"65,688,461 (prior FRED/legacy; not primary replayed)"),
            (2023,result["year_2023_status"],format(result["2023_national_ltl_thousand_usd"],",")),
            (2024,result["year_2024_status"],format(result["2024_national_ltl_thousand_usd"],",")),
        )
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY Lab 14 | Census Historical Provenance</title>'
        '<style>body{font:15px/1.6 system-ui;color:#193628;background:#f6f9f7;'
        'margin:0}main{max-width:1030px;margin:32px auto;padding:18px}'
        'table{border-collapse:collapse;width:100%;background:white}'
        'td,th{border-bottom:1px solid #ddd;text-align:left;padding:12px}'
        'small{color:#537162}</style></head><body><main>'
        '<small>RETALLY / LAB 14 / MISSION 20 / RESEARCH ONLY</small>'
        '<h1>Historical AIES provenance: verify 2023 and 2024, hold 2022</h1>'
        '<p><strong>'+escape(result["status"])+'</strong>.</p>'
        '<p>Revenue values are thousands of nominal U.S. dollars. '
        'Comparisons never establish invoice volume, error prevalence or refunds.</p>'
        '<table><thead><tr><th>Year</th><th>Primary-source status</th>'
        '<th>NAICS 484122 employer revenue ($1,000)</th></tr></thead><tbody>'+
        rows+'</tbody></table>'
        '<p>2023 to 2024 descriptive nominal change: '+
        escape(result["2023_to_2024_nominal_change_pct"])+'%. '
        'Not a statistical-significance test or projected opportunity.</p>'
        '<p>'+escape(result["caveat"])+'</p></main></body></html>'
    )


def main() -> None:
    parser=argparse.ArgumentParser(description="Bounded original Census AIES historical replay")
    parser.add_argument("--as-of-date",default=date.today().isoformat())
    parser.add_argument("--out",required=True,type=Path)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fetch-originals",action="store_true")
    mode.add_argument("--offline",action="store_true")
    mode.add_argument("--from-local",nargs=3,type=Path,metavar=("AIES2023","HISTORY2023","AIES2024"))
    args=parser.parse_args()
    as_of=date.fromisoformat(args.as_of_date)
    if args.fetch_originals:
        try:
            archive_bytes={name:_download_exact(name) for name in URLS}
        except (OSError,TimeoutError):
            result=blocked(as_of=as_of)
        else:
            result=verify_originals(as_of=as_of,archives=archive_bytes)
    elif args.from_local:
        archive_bytes={ident:_read_archive(file)
                       for ident,file in zip(URLS,args.from_local)}
        result=verify_originals(as_of=as_of,archives=archive_bytes)
    else:
        result=report_shell(as_of=as_of)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"aies_historical_lineage.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    (args.out/"aies_historical_lineage.html").write_text(
        render_html(result),encoding="utf-8"
    )
    print(json.dumps({
        "source_status":result["status"],
        "2023_2024_direct_census_zip_replay":result["original_2023_and_2024_replayed_this_run"],
        "2022_original_replay":False,
        "ltl_recoveries_or_error_rates_established":False,
        "evidence_receipt_sha256":result["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
