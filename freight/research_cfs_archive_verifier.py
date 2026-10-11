"""Mission 13: offline source-byte inspection and row matching for CFS 2022.

Read-only, local-file processing. Does not fetch websites, obtain source rights,
authenticate the publisher, admit customer invoices or certify market/recovery
results. Synthetic test archives must never be presented as official Census data.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
from hashlib import sha256
from html import escape
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
from zipfile import BadZipFile, ZipFile

from freight.research_evidence_gate import canon_hash
from freight.research_market_audit import AUDIT, build_market_audit

OFFICIAL_URL = "https://www2.census.gov/programs-surveys/cfs/data/2022/CF2200A01.zip"
TABLE_ID = "CF2200A01"
LIMIT_ARCHIVE_BYTES = 2 * 1024 * 1024
LIMIT_MEMBER_BYTES = 24 * 1024 * 1024
LIMIT_TOTAL_UNCOMPRESSED = 40 * 1024 * 1024
LIMIT_CSV_ROWS = 120_000
LIMIT_MEMBERS = 24
LIMIT_FIELDS = 256
LIMIT_COMPRESSION_RATIO = 1000
MAPPING_SCOPE = "CFS_A01_LOCAL_COLUMN_MAP_REVIEW_NOT_SOURCE_AUTHENTICATION"
MAPPING_KEYS = {"schema_version", "scope", "source_url", "table_id", "member",
                "columns", "selectors", "claims_of_external_approval"}
COLUMN_KEYS = {"geography", "mode", "year", "value_million_usd",
               "weight_thousand_tons"}
SELECTOR_KEYS = {"row_id", "geography", "mode", "year"}


def digest_bytes(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _iso(value: object) -> date:
    if type(value) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("canonical ISO date required")
    return date.fromisoformat(value)


def _read_archive(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > LIMIT_ARCHIVE_BYTES:
        raise ValueError("LOCAL_ARCHIVE_MISSING_SYMLINK_OR_TOO_LARGE")
    raw = path.read_bytes()
    if not raw.startswith(b"PK\x03\x04"):
        raise ValueError("ARCHIVE_NOT_ZIP_LOCAL_HEADER")
    return raw


def _archive_members(raw: bytes) -> tuple[list[dict], ZipFile]:
    """Bound ZIP member names, compression, total decompression and encryption."""
    try:
        archive = ZipFile(io.BytesIO(raw))
        entries = archive.infolist()
    except (BadZipFile, OSError, ValueError) as exc:
        raise ValueError("INVALID_ARCHIVE_STRUCTURE") from exc
    if not entries or len(entries) > LIMIT_MEMBERS:
        raise ValueError("INVALID_ARCHIVE_MEMBER_COUNT")
    seen: set[str] = set()
    total = 0
    members = []
    for entry in entries:
        name = entry.filename
        normalized = PurePosixPath(name)
        if (not name or len(name) > 200 or
            name.startswith("/") or "\\" in name or ":" in name or
            normalized.is_absolute() or
            any(p in ("", ".", "..") for p in name.split("/")) or
            name in seen):
            raise ValueError("UNSAFE_OR_DUPLICATE_ARCHIVE_MEMBER")
        seen.add(name)
        if entry.is_dir():
            continue
        unix_mode = (entry.external_attr >> 16) & 0xFFFF
        if stat.S_IFMT(unix_mode) == stat.S_IFLNK:
            raise ValueError("SYMLINK_ARCHIVE_MEMBER_DENIED")
        if entry.flag_bits & 1:
            raise ValueError("ENCRYPTED_ARCHIVE_DENIED")
        if entry.file_size > LIMIT_MEMBER_BYTES:
            raise ValueError("DECOMPRESSION_SIZE_LIMIT")
        total += entry.file_size
        if total > LIMIT_TOTAL_UNCOMPRESSED:
            raise ValueError("TOTAL_UNCOMPRESSED_BYTES_LIMIT")
        if entry.compress_size == 0 and entry.file_size:
            raise ValueError("INVALID_COMPRESSION_RATIO")
        if entry.file_size and (entry.file_size / entry.compress_size) > LIMIT_COMPRESSION_RATIO:
            raise ValueError("ZIP_BOMB_SUSPECTED")
        members.append({
            "member": name,
            "compressed_bytes": entry.compress_size,
            "uncompressed_bytes": entry.file_size,
            "is_csv": name.lower().endswith(".csv"),
        })
    if not any(m["is_csv"] for m in members):
        raise ValueError("ORIGINAL_ARCHIVE_HAS_NO_CSV")
    return sorted(members, key=lambda x: x["member"]), archive


def _parse_csv(archive: ZipFile, member_name: str) -> tuple[list[str], list[dict]]:
    try:
        info = archive.getinfo(member_name)
    except KeyError as exc:
        raise ValueError("MAPPED_CSV_MEMBER_NOT_FOUND") from exc
    if info.is_dir() or not member_name.lower().endswith(".csv"):
        raise ValueError("MAPPED_MEMBER_MUST_BE_CSV")
    try:
        data = archive.read(member_name)
        text = data.decode("utf-8-sig")
    except (BadZipFile, RuntimeError, UnicodeError, OSError) as exc:
        raise ValueError("CSV_UNREADABLE_OR_CORRUPT") from exc
    if "\x00" in text:
        raise ValueError("BINARY_CONTENT_IN_CSV")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    header = reader.fieldnames
    if (not header or len(header) > LIMIT_FIELDS or
        any(not x or len(x) > 150 for x in header) or
        len(set(header)) != len(header)):
        raise ValueError("DUPLICATE_MISSING_OR_UNBOUNDED_HEADERS")
    rows = []
    for index, row in enumerate(reader, 1):
        if index > LIMIT_CSV_ROWS:
            raise ValueError("CSV_ROW_LIMIT")
        if None in row or any(type(v) is not str or len(v) > 800 for v in row.values()):
            raise ValueError("CSV_MALFORMED_ROW_OR_FIELD")
        rows.append(row)
    if not rows:
        raise ValueError("EMPTY_CFS_DATA_CSV")
    return header, rows


def _safe_description(s: object) -> bool:
    return type(s) is str and 1 <= len(s.strip()) <= 150 and not any(ord(c) < 32 for c in s)


def inspect_local_archive(raw: bytes, *, as_of: date) -> dict:
    members, archive = _archive_members(raw)
    result = {
        "schema_version": 1,
        "as_of": as_of.isoformat(),
        "scope": "CFS_ARCHIVE_LOCAL_BYTES_INSPECTION_NO_PUBLISHER_AUTHENTICATION",
        "source_url_intended_not_proven": OFFICIAL_URL,
        "local_archive_sha256": digest_bytes(raw),
        "archive_length_bytes": len(raw),
        "members": [],
        "official_source_identity_proven": False,
        "independent_full_cfs_dataset_replication": False,
        "actual_ltl_carrier_invoice_rows": 0,
        "external_actions_authorized": False,
    }
    for m in members:
        metadata = dict(m)
        if m["is_csv"]:
            header, rows = _parse_csv(archive, m["member"])
            metadata.update({"columns": header, "row_count": len(rows)})
        result["members"].append(metadata)
    result["receipt_sha256"] = canon_hash(result)
    return result


def _validate_mapping(mapping: dict, base: dict) -> dict:
    if type(mapping) is not dict or set(mapping) != MAPPING_KEYS or mapping.get("schema_version") != 1:
        raise ValueError("INVALID_LOCAL_MAPPING_SCHEMA")
    if (mapping.get("scope") != MAPPING_SCOPE or
        mapping.get("source_url") != OFFICIAL_URL or
        mapping.get("table_id") != TABLE_ID or
        mapping.get("claims_of_external_approval") is not False):
        raise ValueError("MAPPING_CANNOT_ASSERT_OFFICIAL_APPROVAL")
    member = mapping.get("member")
    if not _safe_description(member) or not member.lower().endswith(".csv"):
        raise ValueError("MAPPING_MEMBER_REQUIRED")
    cols = mapping.get("columns")
    if (type(cols) is not dict or set(cols) != COLUMN_KEYS or
        any(not _safe_description(v) for v in cols.values()) or
        len(set(cols.values())) != len(cols)):
        raise ValueError("INVALID_COLUMN_MAPPING")
    expected = {x["id"]: x for x in base["table_rows"]}
    selectors = mapping.get("selectors")
    if type(selectors) is not list or len(selectors) != len(expected):
        raise ValueError("ALL_SIX_PUBLIC_TABLE_ROWS_REQUIRED")
    seen = set()
    for selector in selectors:
        if type(selector) is not dict or set(selector) != SELECTOR_KEYS:
            raise ValueError("INVALID_SELECTOR_SHAPE")
        rid = selector.get("row_id")
        if type(rid) is not str or rid in seen or rid not in expected:
            raise ValueError("UNRECOGNIZED_OR_DUPLICATE_SOURCE_ROW")
        seen.add(rid)
        if (not _safe_description(selector.get("geography")) or
            selector.get("mode") != expected[rid]["mode_code"] or
            selector.get("year") != "2022"):
            raise ValueError("SOURCE_ROW_CODE_VINTAGE_OR_GEOGRAPHY_INVALID")
    if seen != set(expected):
        raise ValueError("SOURCE_ROW_COVERAGE_INCOMPLETE")
    return {row["row_id"]: row for row in selectors}


def _integer_cell(raw: str, *, role: str) -> int:
    # Census tables may use D, S, Z, dash, etc. These are not numeric zeros.
    normalized = raw.strip().replace(",", "")
    if not re.fullmatch(r"\d{1,15}", normalized):
        raise ValueError(f"SUPPRESSED_NON_NUMERIC_OR_MALFORMED_{role.upper()}")
    return int(normalized)


def match_original_excerpt(*, raw: bytes, mapping: dict, as_of: date,
                           simulated_test_bytes: bool = False) -> dict:
    """Check six rows against M12 frozen public excerpt; not publisher truth."""
    original = json.loads(AUDIT.read_text(encoding="utf-8"))
    selectors = _validate_mapping(mapping, original)
    members, archive = _archive_members(raw)
    names = {x["member"] for x in members if x["is_csv"]}
    if mapping["member"] not in names:
        raise ValueError("UNRECOGNIZED_MAPPED_SOURCE_MEMBER")
    columns, rows = _parse_csv(archive, mapping["member"])
    for key in mapping["columns"].values():
        if key not in columns:
            raise ValueError("MAPPING_COLUMN_NOT_IN_SOURCE")
    c = mapping["columns"]
    matches: dict[str, dict] = {}
    for row in rows:
        for rid, sel in selectors.items():
            if (row[c["geography"]].strip() == sel["geography"] and
                row[c["mode"]].strip() == sel["mode"] and
                row[c["year"]].strip() == sel["year"]):
                if rid in matches:
                    raise ValueError("DUPLICATE_CENSUS_SOURCE_ROW_AMBIGUITY")
                matches[rid] = row
    if set(matches) != set(selectors):
        raise ValueError("MISSING_CENSUS_SOURCE_ROWS")
    observed = []
    frozen = {x["id"]: x for x in original["table_rows"]}
    for rid in sorted(matches):
        row = matches[rid]
        value = _integer_cell(row[c["value_million_usd"]], role="value")
        weight = _integer_cell(row[c["weight_thousand_tons"]], role="weight")
        expected = frozen[rid]
        if (value != expected["value_million_usd"] or
            weight != expected["weight_thousand_tons"]):
            raise ValueError("SOURCE_FILE_DIFFERS_FROM_PREVIOUSLY_RECORDED_CFS_EXCERPT")
        observed.append({
            "row_id": rid, "value_million_usd": value,
            "weight_thousand_tons": weight,
            "matches_frozen_mission12_excerpt": True,
        })
    # Passing this parser doesn't say the supplied archive came from Census.
    result = {
        "schema_version": 1,
        "as_of": as_of.isoformat(),
        "scope": ("SYNTHETIC_ARCHIVE_PARSER_TEST_NO_ORIGINAL_SOURCE"
                  if simulated_test_bytes else
                  "LOCAL_ARCHIVE_MATCHES_RECORDED_EXCERPTS_PUBLISHER_UNAUTHENTICATED"),
        "source_url_declared_not_proven": OFFICIAL_URL,
        "original_zip_sha256_if_local_bytes": digest_bytes(raw),
        "member_name": mapping["member"],
        "member_count": len(members),
        "csv_row_count": len(rows),
        "six_excerpt_rows_matched": len(observed),
        "matched": observed,
        "mission12_press_discrepancy_auto_corrected": False,
        "no_source_independent_editorial_resolution": True,
        "original_publisher_authenticated": False,
        "real_invoice_spend_usd": None,
        "actual_ltl_invoice_error_rate": None,
        "market_tam_verified": False,
        "public_accuracy_claims_authorized": False,
        "new_lab_created": False,
        "existing_lab_number": 14,
        "boundary": (
            "Local archive bytes and declared column mapping can match six frozen "
            "published excerpt values; this cannot establish Census authorship, "
            "full dataset coverage, representative variance, LTL paid invoices, "
            "a resolved press correction or RETALLY business performance."
        ),
    }
    result["receipt_sha256"] = canon_hash(result)
    return result


def build_readiness(*, as_of: date) -> dict:
    """Default deterministic CI path; no file/network acquisition."""
    base = json.loads(AUDIT.read_text(encoding="utf-8"))
    report = {
        "schema_version": 1,
        "as_of": as_of.isoformat(),
        "scope": "CFS_A01_ORIGINAL_SOURCE_BYTE_REVIEW_NOT_YET_PERFORMED",
        "intended_original_census_zip_url": OFFICIAL_URL,
        "intended_source_table": TABLE_ID,
        "mission12_frozen_excerpt_digest": canon_hash(base),
        "expected_row_count": len(base["table_rows"]),
        "original_archive_bytes_inspected_in_this_run": False,
        "actual_official_zip_sha256": None,
        "local_column_mapping_approved": False,
        "publisher_signature_verified": False,
        "independent_original_rows_reproduced": 0,
        "south_press_discrepancy_cleared": False,
        "automatic_source_fetch_or_schedule": False,
        "real_invoice_records_ingested": 0,
        "any_ltl_recovery_market_claim_permitted": False,
        "next_local_operator_steps": (
            "Retrieve the exact public Census ZIP through a separately authorized "
            "read-only process; preserve original bytes outside this repository; "
            "run --inspect to record members/header and actual byte SHA-256; "
            "prepare a reviewed six-row column mapping; run --verify and manually "
            "compare source timestamps/terms. No CI source fetching."
        ),
        "new_lab_created": False,
        "existing_lab_number": 14,
    }
    report["receipt_sha256"] = canon_hash(report)
    return report


def render_html(report: dict) -> str:
    r = report
    title = ("CFS Original Source: Inspection Still Required"
             if r["scope"] == "CFS_A01_ORIGINAL_SOURCE_BYTE_REVIEW_NOT_YET_PERFORMED"
             else "Local CFS Source Bytes: Review Results")
    rows = []
    for x in r.get("matched", []):
        rows.append(
            "<tr><th>" + escape(x["row_id"]) + "</th><td>" +
            str(x["value_million_usd"]) + "</td><td>" +
            str(x["weight_thousand_tons"]) + "</td></tr>"
        )
    body = (
        "<p>Original Census ZIP has not been examined in this CI report. "
        "Manual byte-level verification is still necessary.</p>"
        if not rows else
        "<p>Local bytes matched six frozen excerpt values. This alone "
        "does not authenticate the original publisher or correct the "
        "South-region press discrepancy.</p>"
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | CFS Source Byte Verification</title><style>'
        '*{box-sizing:border-box}body{font:15px/1.55 system-ui,-apple-system,sans-serif;'
        'margin:0;background:#f6f9f7;color:#1e372b}main{max-width:980px;margin:auto;'
        'padding:32px 18px 64px}h1{font-size:clamp(30px,5vw,46px)}'
        'article{padding:24px;background:white;border:1px solid #dce7df;'
        'border-radius:14px}table{border-collapse:collapse;width:100%}'
        'td,th{padding:12px;border-bottom:1px solid #dce7df;text-align:left}'
        'small{color:#557263}</style></head><body><main><small>RETALLY / '
        'RESEARCH LAB 14 / MISSION 13</small><h1>' + escape(title) +
        '</h1><article>' + body + '<p><b>Status:</b> ' + escape(r["scope"]) +
        '</p><p>Publisher authenticated: no. Real invoice data: none. '
        'No LTL revenue or recovered fees established.</p></article>'
        '<table><thead><tr><th>CFS row</th><th>Goods $ million</th>'
        '<th>Weight 1,000 tons</th></tr></thead><tbody>' +
        "".join(rows) + '</tbody></table><footer><small>Receipt: ' +
        escape(r["receipt_sha256"]) +
        ' (local JSON consistency only)</small></footer></main></body></html>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--zip", type=Path)
    parser.add_argument("--mapping", type=Path)
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.inspect and args.verify:
        parser.error("choose --inspect or --verify, never both")
    if (args.inspect or args.verify) and not args.zip:
        parser.error("--zip required for inspection or verification")
    if args.mapping and not args.verify:
        parser.error("--mapping only allowed with --verify")
    if args.verify and not args.mapping:
        parser.error("--mapping required for --verify")
    if args.zip and not (args.inspect or args.verify):
        parser.error("choose --inspect or --verify for a local zip")
    if args.inspect:
        report = inspect_local_archive(_read_archive(args.zip), as_of=args.as_of_date)
    elif args.verify:
        map_doc = json.loads(args.mapping.read_text(encoding="utf-8"))
        report = match_original_excerpt(
            raw=_read_archive(args.zip), mapping=map_doc, as_of=args.as_of_date
        )
    else:
        report = build_readiness(as_of=args.as_of_date)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "cfs_source_bytes.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (args.out / "cfs_source_bytes.html").write_text(
        render_html(report), encoding="utf-8")
    print(json.dumps({
        "status": report["scope"], "receipt": report["receipt_sha256"]
    }, sort_keys=True))


if __name__ == "__main__":
    main()
