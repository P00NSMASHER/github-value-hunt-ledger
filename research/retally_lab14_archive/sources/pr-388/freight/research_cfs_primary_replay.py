"""Lab 14 Mission 17: independently replay selected CFS rows from original ZIP bytes.

This is a bounded forensic source verification operation, NOT a freight invoice
audit, an LTL market-sizing model, publisher signature validation or production
data ingestion. Never use successful ZIP matching to promote commercial claims.
"""
from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

from freight.research_cfs_archive_verifier import (
    _archive_members, _parse_tabular, _read_archive,
)
from freight.research_cfs_industry_quality import OFFICIAL_PROFILES
from freight.research_cfs_mode_hierarchy import (
    BOOK, EXPECTED_BOOK_BLOB_SHA1, TABLES, _git_blob_sha1, validate_catalog,
)
from freight.research_evidence_gate import canon_hash

SCOPE = "LAB14_CFS_OFFICIAL_BYTES_60_ROW_REPLAY_NOT_LTL_BILLING"
MAX_DOWNLOAD_BYTES = 256_000
SELECTED_FIELDS = (
    ("VAL", "goods_value_million_usd"),
    ("VAL_F", "goods_value_flag"),
    ("TON", "tonnage_thousand_tons"),
    ("TON_F", "tonnage_flag"),
    ("VAL_S", "goods_value_cv_pct"),
    ("VAL_S_F", "goods_value_cv_flag"),
    ("TON_S", "tonnage_cv_pct"),
    ("TON_S_F", "tonnage_cv_flag"),
)
COMMON_NATIONAL = {
    "#GEOTYPE": "01", "ST": "00", "GEO_ID": "0100000US",
    "GEO_LABEL": "United States", "YEAR": "2022", "DMODE": "111",
}
TABLE_AXIS = {"CF2200A18": "SHIPDIST", "CF2200A19": "SHIPWT"}


def _frozen_book(as_of: date) -> dict:
    raw = BOOK.read_bytes()
    if _git_blob_sha1(raw) != EXPECTED_BOOK_BLOB_SHA1:
        raise ValueError("MIRROR_BOOK_GIT_BLOB_DRIFT")
    book = json.loads(raw.decode("utf-8"))
    problems = validate_catalog(book, as_of=as_of)
    if problems:
        raise ValueError("INVALID_FROZEN_SOURCE_BOOK: " + "; ".join(problems))
    return book


def _selected_rows(table: str, rows: list[dict], frozen: dict) -> dict:
    """Check all source values, flags, CVs and labels at exact Census grain.

    Caller must independently authenticate the *entire* original source ZIP.
    This function cannot on its own establish origin or archive integrity.
    """
    if table not in TABLE_AXIS or type(rows) is not list or not rows:
        raise ValueError("INVALID_SOURCE_TABLE_OR_ROWS")
    axis = TABLE_AXIS[table]
    target = {
        (x["naics2017"], x["stratum_code"]): x
        for x in frozen["selected_source_rows"] if x["table_id"] == table
    }
    if len(target) != 30:
        raise ValueError("INCOMPLETE_FROZEN_SELECTED_ROW_SET")
    found = set()
    failures = []
    for raw in rows:
        if type(raw) is not dict:
            raise ValueError("CORRUPTED_OFFICIAL_SOURCE_ROW")
        if any(raw.get(k) != v for k, v in COMMON_NATIONAL.items()):
            continue
        key = (raw.get("NAICS2017"), raw.get(axis))
        if key not in target:
            continue
        if key in found:
            failures.append("DUPLICATE_SOURCE_KEY:" + "/".join(key))
            continue
        found.add(key)
        expected = target[key]
        if raw.get("GEO_ID_F") != "" or raw.get("DMODE_F") != "":
            failures.append("SOURCE_GEOGRAPHY_OR_MODE_FLAGGED:" + "/".join(key))
        if raw.get(axis + "_LABEL") != expected["stratum_label"]:
            failures.append("SOURCE_BUCKET_LABEL_DIFFERS:" + "/".join(key))
        if "for-hire" not in str(raw.get("DMODE_LABEL", "")).lower():
            failures.append("SOURCE_MODE_LABEL_NOT_FOR_HIRE:" + "/".join(key))
        for source_field, frozen_field in SELECTED_FIELDS:
            actual = raw.get(source_field)
            recorded = expected[frozen_field]
            if actual != (str(recorded) if type(recorded) is int else recorded):
                failures.append("SOURCE_CELL_DIFFERS:" + "/".join(key) + ":" + source_field)
    missing = sorted(set(target) - found)
    if missing:
        failures.append("MISSING_SOURCE_KEYS:" + ",".join("/".join(k) for k in missing))
    if failures:
        raise ValueError("ORIGINAL_VS_MIRROR_DISAGREEMENT: " + "; ".join(failures[:20]))
    return {"table_id": table, "selected_rows_matched": len(found),
            "unmatched_selected_rows": 0, "mismatched_cells": 0,
            "suppressed_cells_preserved": True}


def _verify_archive(table: str, raw: bytes, frozen: dict) -> dict:
    if table not in TABLES or type(raw) is not bytes:
        raise ValueError("INVALID_CFS_ARCHIVE_ARGUMENTS")
    spec = TABLES[table]
    if len(raw) != spec["original_zip_size_bytes"]:
        raise ValueError("ORIGINAL_ZIP_SIZE_MISMATCH:" + table)
    digest = sha256(raw).hexdigest()
    if digest != spec["original_zip_sha256"]:
        raise ValueError("ORIGINAL_ZIP_SHA256_MISMATCH:" + table)
    members, archive = _archive_members(raw)
    names = [x["member"] for x in members if x["is_dat"]]
    if names != [table + ".dat"]:
        raise ValueError("OFFICIAL_ZIP_WRONG_DAT_MEMBER:" + table)
    header, records = _parse_tabular(archive, table + ".dat")
    profile = OFFICIAL_PROFILES[table]
    if "|".join(header) != profile["header"]:
        raise ValueError("OFFICIAL_DAT_HEADER_DRIFT:" + table)
    if len(records) != spec["mirror_file_row_count"]:
        raise ValueError("OFFICIAL_DAT_ROW_COUNT_DIFFERS:" + table)
    raw_dat = archive.read(table + ".dat")
    if len(raw_dat) != spec["mirror_file_bytes"]:
        raise ValueError("OFFICIAL_DAT_BYTE_LENGTH_DIFFERS:" + table)
    official_dat_git_blob_sha1 = _git_blob_sha1(raw_dat)
    if official_dat_git_blob_sha1 != spec["mirror_git_blob_sha1"]:
        raise ValueError("FULL_ORIGINAL_DAT_DIFFERS_FROM_PINNED_GITHUB_MIRROR:" + table)
    matched = _selected_rows(table, records, frozen)
    return {
        **matched,
        "publisher_table": table,
        "official_archive_sha256": digest,
        "official_archive_bytes": len(raw),
        "official_member": table + ".dat",
        "official_member_sha256": sha256(raw_dat).hexdigest(),
        "official_member_git_blob_sha1": official_dat_git_blob_sha1,
        "official_member_bytes": len(raw_dat),
        "official_member_rows": len(records),
        "whole_dat_file_identical_to_git_mirror_proven": True,
    }


def _official_download(table: str) -> bytes:
    if table not in TABLES:
        raise ValueError("UNAUTHORIZED_DOWNLOAD_TABLE")
    # Exactly two public government ZIPs; no arbitrary URLs or credentials.
    url = "https://www2.census.gov/programs-surveys/cfs/data/2022/" + table + ".zip"
    req = Request(url, headers={"User-Agent": "RETALLY-Lab14-SourceValidation/1.0"})
    with urlopen(req, timeout=25) as response:
        if response.geturl() != url:
            raise ValueError("OFFICIAL_SOURCE_REDIRECTED")
        raw = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(raw) > MAX_DOWNLOAD_BYTES:
        raise ValueError("CFS_OFFICIAL_DOWNLOAD_OVER_SIZE_LIMIT")
    return raw


def replay(*, as_of: date, zip_bytes: dict[str, bytes],
           acquisition: str = "OFFLINE_USER_SUPPLIED_LOCAL_ARCHIVES") -> dict:
    frozen = _frozen_book(as_of)
    if set(zip_bytes) != set(TABLES) or acquisition not in {
        "OFFLINE_USER_SUPPLIED_LOCAL_ARCHIVES",
        "DIRECT_CENSUS_HTTPS_GET_IN_THIS_CI_RUN",
    }:
        raise ValueError("EXACTLY_TWO_ARCHIVES_AND_KNOWN_ACQUISITION_REQUIRED")
    results = [_verify_archive(t, zip_bytes[t], frozen) for t in TABLES]
    if sum(t["selected_rows_matched"] for t in results) != 60:
        raise ValueError("ORIGINAL_REPLAY_NOT_ALL_SIXTY")
    result = {
        "schema_version": 1, "scope": SCOPE, "as_of": as_of.isoformat(),
        "status": "SOURCE_BYTES_MATCH_OBSERVED_HASHES_AND_60_CELLS",
        "acquisition": acquisition,
        "source_2022_five_year_cfs_goods_survey_not_freight_invoices": True,
        "frozen_m16_mirror_git_blob_sha1": EXPECTED_BOOK_BLOB_SHA1,
        "source_archive_sha256_previously_observed_in_browser": True,
        "tables": results, "selected_rows_matched": 60,
        "source_bytes_replayed_this_run": True,
        "github_mirror_other_tables_or_other_repo_files_proven": False,
        "a18_a19_full_mirror_dat_files_match_official_original_dat_bytes": True,
        "publisher_digitally_signed_archive_verified": False,
        "official_host_https_used_this_run": acquisition.startswith("DIRECT_"),
        "same_survey_two_tables_not_independent_research_samples": True,
        "actual_paid_ltl_invoices_observed": 0,
        "ltl_only_freight_spend_usd": None,
        "ltl_recovery_market_tam_usd": None,
        "recoveries_proven": False, "buyer_demand_proven": False,
        "joint_distance_by_weight_distribution_established": False,
        "commercial_public_claims_authorized": False,
        "customer_or_carrier_records_processed": False,
        "new_lab_created": False, "lab": 14,
        "caveat": (
            "Official archived ZIP SHA-256s match previously observed government "
            "values; both extracted full A18/A19 DAT members also match the "
            "pinned GitHub mirror's content-addressed Git blob IDs, and all "
            "sixty selected Census source cells were independently compared. "
            "This does not establish a publisher digital signature, LTL-only "
            "invoice spend, annual carrier charges, market demand, recoveries, "
            "other third-party repo files, or joint distance/weight distributions. "
            "CFS NAICS 4931 includes NAICS 484; censored S cells are not zeros."
        ),
    }
    result["receipt_sha256"] = canon_hash(result)
    return result


def render_html(result: dict) -> str:
    rows = "".join("<tr><td>" + escape(x["table_id"]) + "</td><td>" +
                   str(x["selected_rows_matched"]) + "</td><td><code>" +
                   escape(x["official_archive_sha256"]) + "</code></td></tr>"
                   for x in result["tables"])
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>RETALLY CFS Primary-Source Evidence</title></head>'
        '<body><main><h1>RETALLY Lab 14 — original Census ZIP replay</h1>'
        '<p>Research evidence only, not freight bills, LTL TAM or recoveries.</p>'
        '<p>Result: ' + escape(result["status"]) +
        ' · 60 of 60 selected rows</p><table><tr><th>Table</th>'
        '<th>Matched source rows</th><th>Original ZIP SHA-256</th></tr>' +
        rows + '</table><p>' + escape(result["caveat"]) +
        '</p><p>Source method: ' + escape(result["acquisition"]) +
        '</p></main></body></html>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Lab 14 Census source byte replay")
    parser.add_argument("--as-of-date", default=date.today().isoformat())
    parser.add_argument("--out", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fetch-official", action="store_true")
    mode.add_argument("--from-local", action="store_true")
    parser.add_argument("--zip-a18", type=Path)
    parser.add_argument("--zip-a19", type=Path)
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of_date)
    if args.fetch_official:
        if args.zip_a18 or args.zip_a19:
            parser.error("no local paths with --fetch-official")
        data = {t: _official_download(t) for t in TABLES}
        method = "DIRECT_CENSUS_HTTPS_GET_IN_THIS_CI_RUN"
    else:
        if not args.zip_a18 or not args.zip_a19:
            parser.error("--from-local requires both ZIP paths")
        data = {
            "CF2200A18": _read_archive(args.zip_a18),
            "CF2200A19": _read_archive(args.zip_a19),
        }
        method = "OFFLINE_USER_SUPPLIED_LOCAL_ARCHIVES"
    report = replay(as_of=as_of, zip_bytes=data, acquisition=method)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "cfs_primary_replay.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.out / "cfs_primary_replay.html").write_text(
        render_html(report), encoding="utf-8"
    )
    print(json.dumps({
        "status": report["status"], "matched_rows": report["selected_rows_matched"],
        "receipt_sha256": report["receipt_sha256"],
        "publisher_signature_validated": False,
        "freight_recovery_market_validated": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
