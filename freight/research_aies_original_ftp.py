"""RETALLY Lab 14 / Mission 19: authentic 2024 Census AIES original FTP proof.

Only original 2024 AIES00BASIC ZIP from Census can establish a source replay.
Its three NAICS employer-revenue observations are NOT customer-paid LTL
invoices, audit findings, potential recoveries, or 2026 business revenue.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from freight.research_cfs_archive_verifier import (
    _archive_members, _parse_tabular, _read_archive,
)
from freight.research_evidence_gate import canon_hash
from freight.research_ltl_revenue_bridge import RECORDS, build_revenue

SOURCE_URL = (
    "https://www2.census.gov/programs-surveys/aies/data/2024/AIES00BASIC.zip"
)
SOURCE_NAME = "AIES00BASIC.zip"
MEMBER_DAT = "AIES00BASIC.dat"
MEMBER_FIELDS = "AIES00BASIC_FIELDS.txt"
MEMBER_README = "AIES00BASIC_README.txt"
ZIP_SHA256 = "39c4235026672e7bffdbc36292ed976726df368f2ca435219aef1c84e8e4faa6"
ZIP_SIZE_BYTES = 340551
DATA_SIZE_BYTES = 1859064
DATA_ROW_COUNT = 8802
SCHEMA = (
    "#GEOTYPE|ST|GEO_ID|GEO_LABEL|GEO_ID_F|SECTOR|INDLEVEL|"
    "NAICS2017|NAICS2017_LABEL|NAICS2017_F|TYPOP|TYPOP_LABEL|"
    "TAXSTAT|TAXSTAT_LABEL|YEAR|RCPT_TOT_VAL|RCPT_TOT_VAL_F|"
    "PAY_ANN_VAL|PAY_ANN_VAL_F|PAY_QTR1_VAL|PAY_QTR1_VAL_F|"
    "EMP_MAR12_NUM|EMP_MAR12_NUM_F|EXPS_TOT_DVAL|EXPS_TOT_DVAL_F|"
    "RCPT_TOT_CV|RCPT_TOT_CV_F|PAY_ANN_CV|PAY_ANN_CV_F|"
    "PAY_QTR1_CV|PAY_QTR1_CV_F|EMP_MAR12_CV|EMP_MAR12_CV_F|"
    "EXPS_TOT_CV|EXPS_TOT_CV_F"
)
EXPECTED_LABEL_PHRASES = {
    "484": ("truck transportation",),
    "484121": ("long-distance", "truckload"),
    "484122": ("long-distance", "less than truckload"),
}
CENSUS_YEAR = "2024"
EARLIEST_OBSERVATION = date(2026, 10, 11)
SCOPE = "LAB14_2024_AIES_ORIGINAL_CENSUS_FTP_THREE_NAICS_REVENUE_ROWS"
BLOCKED = "BLOCKED_CENSUS_FTP_UNREACHABLE_NOT_VERIFIED"
VERIFIED = "ORIGINAL_CENSUS_2024_AIES_FTP_REVENUE_ROWS_REPRODUCED"
SOURCE_FIELDS = ("#GEOTYPE", "ST", "GEO_ID", "GEO_LABEL", "GEO_ID_F",
                 "SECTOR", "INDLEVEL", "NAICS2017", "NAICS2017_LABEL",
                 "NAICS2017_F", "TYPOP", "TYPOP_LABEL", "TAXSTAT",
                 "TAXSTAT_LABEL", "YEAR", "RCPT_TOT_VAL", "RCPT_TOT_VAL_F",
                 "RCPT_TOT_CV", "RCPT_TOT_CV_F")
MAX_DOWNLOAD_BYTES = 2_000_000
ALLOWED_MEMBER_NAMES = {MEMBER_DAT, MEMBER_FIELDS, MEMBER_README}


def _source_row(row: dict) -> bool:
    """Exactly national, all-employer population in 2024, not other scopes."""
    return (row.get("#GEOTYPE") == "01" and row.get("ST") == "00"
            and row.get("GEO_ID") == "0100000US"
            and row.get("GEO_LABEL") == "United States"
            and row.get("TYPOP") == "00"
            and row.get("TAXSTAT") == "00"
            and row.get("YEAR") == CENSUS_YEAR
            and row.get("NAICS2017") in RECORDS)


def selected_revenue(rows: list[dict], *, expected: dict[str, int]) -> list[dict]:
    """No archive proof is implied by passing preselected test rows here."""
    if (type(rows) is not list or type(expected) is not dict
        or set(expected) != set(RECORDS)
        or any(type(v) is not int or v <= 0 for v in expected.values())):
        raise ValueError("AIES_SOURCE_ROW_INPUT_OR_REVENUE_BASELINE_INVALID")
    selected = {}
    for row in rows:
        if type(row) is not dict or not set(SOURCE_FIELDS) <= set(row):
            raise ValueError("AIES_ROW_INVALID_SCHEMA")
        if not _source_row(row):
            continue
        code = row["NAICS2017"]
        if code in selected:
            raise ValueError("AIES_DUPLICATE_NATIONAL_NAICS_POPULATION:" + code)
        if (row["GEO_ID_F"] != "" or row["NAICS2017_F"] != ""
            or row["RCPT_TOT_VAL_F"] != "" or row["RCPT_TOT_CV_F"] != ""):
            raise ValueError("AIES_SOURCE_FLAGGED_ESTIMATE_NOT_DIRECT:" + code)
        if row["TYPOP_LABEL"].strip().lower() != "all establishments" or (
            row["TAXSTAT_LABEL"].strip().lower() != "all establishments"
        ):
            raise ValueError("AIES_NOT_ALL_ESTABLISHMENTS:" + code)
        if row["SECTOR"] != "48" or row["INDLEVEL"] != str(len(code)):
            raise ValueError("AIES_NAICS_HIERARCHY_OR_SECTOR_MISMATCH:" + code)
        label = row["NAICS2017_LABEL"].strip().lower()
        if not all(phrase in label for phrase in EXPECTED_LABEL_PHRASES[code]):
            raise ValueError("AIES_NAICS_LABEL_MISMATCH:" + code)
        val = row["RCPT_TOT_VAL"]
        if type(val) is not str or not re.fullmatch(r"[0-9]{1,14}", val):
            raise ValueError("AIES_REVENUE_SOURCE_VALUE_MALFORMED:" + code)
        revenue = int(val)
        if revenue != expected[code]:
            raise ValueError("AIES_ORIGINAL_FTP_DIFFERS_FROM_M18_FRED_SNAPSHOT:" + code)
        cv_raw = row["RCPT_TOT_CV"]
        if type(cv_raw) is not str or not re.fullmatch(r"(?:\d{1,3})?(?:\.\d{1,4})", cv_raw):
            raise ValueError("AIES_REVENUE_CV_MISSING_OR_INVALID:" + code)
        try:
            cv = Decimal(cv_raw)
        except InvalidOperation as ex:
            raise ValueError("AIES_SOURCE_CV_NOT_DECIMAL:" + code) from ex
        if not cv.is_finite() or not (0 <= cv <= 100):
            raise ValueError("AIES_SOURCE_CV_OUT_OF_RANGE:" + code)
        selected[code] = {
            "naics2017": code,
            "source_naics_label": row["NAICS2017_LABEL"],
            "revenue_thousand_usd": revenue,
            "published_source_cv_pct": str(cv),
            "published_flags_empty": True,
            "population": "US_2024_ALL_EMPLOYER_ESTABLISHMENTS",
            "metric": "CENSUS_RCPT_TOT_VAL_THOUSAND_USD",
        }
    if set(selected) != set(RECORDS):
        raise ValueError("AIES_MISSING_NATIONAL_SOURCE_NAICS:" +
                         ",".join(sorted(set(RECORDS) - set(selected))))
    return [selected[n] for n in ("484", "484121", "484122")]


def _base(*, as_of: date) -> tuple[dict, dict]:
    if type(as_of) is not date or as_of < EARLIEST_OBSERVATION:
        raise ValueError("M19_SOURCE_OBSERVATION_DATE_INVALID")
    reference = build_revenue(as_of=as_of)
    if (reference.get("ltl_2024_revenue_billion_usd") != "65.096" or
        reference.get("latest_observed_reference_year") != 2024 or
        reference.get("real_ltl_invoice_cases_observed") != 0 or
        reference.get("ltl_freight_audit_recoverable_tam_usd") is not None or
        reference.get("source", {}).get("full_census_origin_api_bytes_replayed") is not False):
        raise ValueError("M18_HISTORICAL_REVENUE_BASELINE_INVALID")
    expected = {
        row["year"]: row for row in reference["revenue_by_year"]
    }
    if 2024 not in expected:
        raise ValueError("M18_REFERENCE_YEAR_MISSING")
    values = {
        "484": expected[2024]["all_trucking_484_thousand_usd"],
        "484121": expected[2024]["tl_484121_thousand_usd"],
        "484122": expected[2024]["ltl_484122_thousand_usd"],
    }
    if values != {code: RECORDS[code]["values"][2] for code in RECORDS}:
        raise ValueError("M18_ORIGINAL_REVENUE_LINEAGE_CHANGED")
    return reference, values


def _report_shell(as_of: date, reference: dict) -> dict:
    return {
        "schema_version": 1,
        "scope": SCOPE,
        "lab": 14,
        "new_lab_created": False,
        "as_of": as_of.isoformat(),
        "reference_year_verified": None,
        "historical_2022_2023_original_ftp_replayed": False,
        "m18_research_receipt_sha256": reference["receipt_sha256"],
        "census_source_url": SOURCE_URL,
        "status": BLOCKED,
        "source_archive_sha256": None,
        "source_zip_bytes": None,
        "source_dat_sha256": None,
        "source_data_row_count": None,
        "source_data_field_count": None,
        "publisher_digitally_signed_archive_verified": False,
        "source_estimates": [],
        "matched_national_industry_source_rows": 0,
        "separate_fred_live_csv_replay_completed": False,
        "direct_original_census_ftp_replay_completed": False,
        "source_metric": "2024_CENSUS_EMPLOYER_INDUSTRY_REVENUE_THOUSAND_USD_NOT_LTL_INVOICES",
        "actual_paid_customer_ltl_invoices_observed": 0,
        "real_billing_errors_or_paid_recoveries_established": False,
        "actual_recovered_usd": None,
        "retally_audit_recoverable_tam_usd": None,
        "public_commercial_claims_authorized": False,
        "automated_carrier_or_customer_contact": False,
        "customer_or_carrier_records_processed": False,
        "pilot_18_independent_human_requirements_still_unverified": True,
        "caveat": (
            "2024 original Census AIES measures revenue of employer "
            "establishments, not LTL customer-paid invoice volume or recovery "
            "market. NAICS 484122 is long-distance general-freight LTL, not "
            "the entirety of all LTL services. Published source CV describes "
            "survey estimate variability, not invoice overcharge prevalence. "
            "The 2022 and 2023 FRED historical series were NOT authenticated "
            "from the original 2024 Census AIES ZIP. No buyer, refund, "
            "rate contract, commission, claim or earnings is verified."
        ),
    }


def verify_original_bytes(raw: bytes, *, as_of: date) -> dict:
    reference, expected = _base(as_of=as_of)
    if type(raw) is not bytes or len(raw) != ZIP_SIZE_BYTES:
        raise ValueError("AIES_ORIGINAL_ZIP_SIZE_MISMATCH")
    digest = sha256(raw).hexdigest()
    if digest != ZIP_SHA256:
        raise ValueError("AIES_ORIGINAL_ZIP_SHA256_MISMATCH")
    members, archive = _archive_members(raw)
    if {x["member"] for x in members} != ALLOWED_MEMBER_NAMES:
        raise ValueError("AIES_ORIGINAL_ZIP_MEMBER_SET_CHANGED")
    items = {x["member"]: x for x in members}
    if items[MEMBER_DAT]["uncompressed_bytes"] != DATA_SIZE_BYTES:
        raise ValueError("AIES_ORIGINAL_DAT_UNCOMPRESSED_SIZE_MISMATCH")
    header, rows = _parse_tabular(archive, MEMBER_DAT)
    if "|".join(header) != SCHEMA:
        raise ValueError("AIES_ORIGINAL_DATA_FIELD_SCHEMA_CHANGED")
    if len(rows) != DATA_ROW_COUNT:
        raise ValueError("AIES_ORIGINAL_DATA_ROW_CENSUS_CHANGED")
    source_rows = selected_revenue(rows, expected=expected)
    if sum(x["revenue_thousand_usd"] for x in source_rows[1:]) > source_rows[0]["revenue_thousand_usd"]:
        raise ValueError("AIES_CHILD_INDUSTRY_EXCEEDS_ALL_TRUCKING_REVENUE")
    original_data = archive.read(MEMBER_DAT)
    report = _report_shell(as_of, reference)
    report.update({
        "status": VERIFIED,
        "reference_year_verified": 2024,
        "source_archive_sha256": digest,
        "source_zip_bytes": len(raw),
        "source_dat_sha256": sha256(original_data).hexdigest(),
        "source_data_row_count": len(rows),
        "source_data_field_count": len(header),
        "source_estimates": source_rows,
        "matched_national_industry_source_rows": len(source_rows),
        "direct_original_census_ftp_replay_completed": True,
    })
    report["receipt_sha256"] = canon_hash(report)
    return report


def unavailable(*, as_of: date) -> dict:
    reference, _ = _base(as_of=as_of)
    result = _report_shell(as_of, reference)
    result["receipt_sha256"] = canon_hash(result)
    return result


def _download_original() -> bytes:
    """Exact publisher URL, bounded GET; no Census API credential required."""
    req = Request(SOURCE_URL, headers={
        "User-Agent": "RETALLY-Lab14-SourceVerification/1.0"
    })
    with urlopen(req, timeout=30) as response:
        if response.geturl() != SOURCE_URL:
            raise ValueError("AIES_OFFICIAL_SOURCE_REDIRECTED")
        data = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise ValueError("AIES_SOURCE_ARCHIVE_OVER_MAXIMUM_BOUND")
    return data


def render_html(report: dict) -> str:
    rows = "".join(
        "<tr><th>" + escape(x["naics2017"]) + "</th><td>" +
        escape(x["source_naics_label"]) + "</td><td>" +
        format(x["revenue_thousand_usd"], ",") + "</td><td>" +
        escape(x["published_source_cv_pct"]) + "%</td></tr>"
        for x in report["source_estimates"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY Lab 14 | Census original AIES verification</title>'
        '<style>body{background:#f6f9f7;color:#193528;font:16px/1.5 system-ui;'
        'margin:0}main{max-width:1050px;margin:40px auto;padding:18px}'
        'table{border-collapse:collapse;width:100%;background:white}'
        'td,th{text-align:left;padding:12px;border-bottom:1px solid #ddd}'
        'small{color:#566c62}</style></head><body><main>'
        '<small>RETALLY / RESEARCH LAB 14 / MISSION 19 / INTERNAL ONLY</small>'
        '<h1>Original Census AIES: publisher-source integrity</h1>'
        '<p>Verification: <strong>' + escape(report["status"]) +
        '</strong>. No real paid freight invoices or recoveries.</p>'
        '<p>Official publisher ZIP SHA-256: ' +
        escape(report["source_archive_sha256"] or "Not verified") + '</p>'
        '<table><thead><tr><th>2017 NAICS</th><th>Census industry label</th>'
        '<th>2024 revenue ($1,000)</th><th>Published revenue CV</th>'
        '</tr></thead><tbody>' + rows + '</tbody></table>'
        '<p>' + escape(report["caveat"]) + '</p>'
        '<p><a href="' + escape(report["census_source_url"]) +
        '">Original Census public AIES archive</a></p></main></body></html>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only original 2024 Census AIES verification"
    )
    parser.add_argument("--as-of-date", default=date.today().isoformat())
    parser.add_argument("--out", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fetch-official", action="store_true")
    mode.add_argument("--from-local", type=Path)
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of_date)
    if args.fetch_official:
        try:
            raw = _download_original()
        except (OSError, TimeoutError, HTTPError, URLError):
            result = unavailable(as_of=as_of)
        else:
            result = verify_original_bytes(raw, as_of=as_of)
    else:
        raw = _read_archive(args.from_local)
        result = verify_original_bytes(raw, as_of=as_of)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "aies_primary_source.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "aies_primary_source.html").write_text(
        render_html(result), encoding="utf-8"
    )
    print(json.dumps({
        "source_status": result["status"],
        "matched_source_naics": result["matched_national_industry_source_rows"],
        "source_archive_sha256": result["source_archive_sha256"],
        "source_dat_sha256": result["source_dat_sha256"],
        "actual_recoveries_established": False,
        "receipt_sha256": result["receipt_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
