"""RETALLY Lab 14: exact, offline-verifiable public government freight evidence.

BTS FAF6 (2022 model estimates) and EIA (2026 weekly diesel observations)
are NOT customer invoices, contracted rates, overcharges or savings proof.

No network access, secrets, filesystem mutation or customer action at import.
The archive verifier accepts a separately obtained exact BTS ZIP by filename;
it never downloads URLs, silently promotes revised data, or trusts caller claims.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "fixtures/public_faf6_eia_manifest_20261017.json"
FAF_FIELDS = ("dms_origst", "dms_destst", "dms_mode", "trade_type",
              "sctg2", "tons_2022", "value_2022")
EIA_FIELDS = ("week_ending_monday", "area", "usd_per_gallon")
SOURCE_FAF_FIELDS = ("fr_orig","dms_origst","dms_destst","fr_dest",
                     "fr_inmode","dms_mode","fr_outmode","sctg2",
                     "trade_type","tons_2022","value_2022")
ALLOWED_PAIRS = (("24","42"),("42","24"))
ALLOWED_EIA_AREAS = ("US","PADD1","PADD1B")
NUMERIC_SIX = re.compile(r"^[0-9]+\.[0-9]{6}$")
NUMERIC_THREE = re.compile(r"^[0-9]+\.[0-9]{3}$")


def _fail(reason: str) -> None:
    raise ValueError("PUBLIC_BENCHMARK_" + reason)


def _load_manifest() -> dict:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (type(m) is not dict or m.get("schema_version") != 1
        or m.get("intent") != "source_bound_public_freight_market_context_only"
        or m.get("faf6",{}).get("frozen_rows") != 78
        or m.get("eia",{}).get("frozen_rows") != 18):
        _fail("INVALID_MANIFEST")
    return m


def _read_public_csv(path: Path, header: tuple[str, ...], max_bytes: int) -> list[dict]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > max_bytes:
        _fail("UNEXPECTED_FIXTURE_SOURCE")
    try:
        contents = path.read_bytes().decode("utf-8-sig")
        if "\x00" in contents:
            _fail("NUL_IN_SOURCE")
        reader = csv.DictReader(io.StringIO(contents, newline=""))
        if tuple(reader.fieldnames or ()) != header:
            _fail("UNEXPECTED_COLUMNS")
        records = list(reader)
        if not records or any(
            set(record) != set(header)
            or any(not isinstance(v,str) for v in record.values())
            for record in records
        ):
            _fail("MALFORMED_ROW")
        return records
    except (UnicodeError, csv.Error) as exc:
        raise ValueError("PUBLIC_BENCHMARK_MALFORMED_CSV") from exc


def _decimal(token: str, pattern: re.Pattern[str]) -> Decimal:
    if type(token) is not str or not pattern.fullmatch(token):
        _fail("INVALID_NUMERIC_PRECISION")
    try:
        value = Decimal(token)
    except InvalidOperation as exc:
        raise ValueError("PUBLIC_BENCHMARK_INVALID_NUMBER") from exc
    if not value.is_finite() or value < 0:
        _fail("INVALID_NONNEGATIVE_VALUE")
    return value


def read_faf6_rows() -> list[dict]:
    m = _load_manifest()["faf6"]
    path = ROOT / "fixtures" / Path(m["fixture"]).name
    rows = _read_public_csv(path,FAF_FIELDS,24_000)
    if len(rows) != m["frozen_rows"]:
        _fail("FAF6_ROW_COUNT_MISMATCH")
    seen: set[tuple[str,str,str]] = set()
    totals = {(a,b): [0, Decimal("0"), Decimal("0")] for a,b in ALLOWED_PAIRS}
    for row in rows:
        pair = (row["dms_origst"],row["dms_destst"])
        key = (pair[0],pair[1],row["sctg2"])
        if (pair not in ALLOWED_PAIRS
            or row["dms_mode"] != "1" or row["trade_type"] != "1"
            or not re.fullmatch(r"[0-9]{2}",row["sctg2"])
            or key in seen):
            _fail("FAF6_SCOPE_OR_DUPLICATE")
        seen.add(key)
        totals[pair][0] += 1
        totals[pair][1] += _decimal(row["tons_2022"],NUMERIC_SIX)
        totals[pair][2] += _decimal(row["value_2022"],NUMERIC_SIX)
    for pair,label in [(("24","42"),"md_to_pa"),(("42","24"),"pa_to_md")]:
        expected = m[label]
        count,tons,value = totals[pair]
        if (count != expected["rows"]
            or str(tons) != expected["tons_2022"]
            or str(value) != expected["value_2022"]):
            _fail("FAF6_TOTAL_OR_COMMODITY_MISMATCH")
    if len(seen) != 78:
        _fail("FAF6_CENSUS_INCOMPLETE")
    return rows


def read_eia_rows() -> list[dict]:
    m = _load_manifest()["eia"]
    path = ROOT / "fixtures" / Path(m["fixture"]).name
    rows = _read_public_csv(path,EIA_FIELDS,4_000)
    if len(rows) != m["frozen_rows"]:
        _fail("EIA_ROW_COUNT_MISMATCH")
    seen: set[tuple[str,str]] = set()
    weeks = {str(date(2026,9,7)+timedelta(days=7*i)) for i in range(6)}
    for row in rows:
        week,area,price = (row[x] for x in EIA_FIELDS)
        key = (week,area)
        if area not in ALLOWED_EIA_AREAS or week not in weeks or key in seen:
            _fail("EIA_SCOPE_OR_DUPLICATE")
        seen.add(key)
        _decimal(price,NUMERIC_THREE)
    if seen != {(w,a) for w in weeks for a in ALLOWED_EIA_AREAS}:
        _fail("EIA_MISSING_OBSERVATION")
    for area,expected in m["latest_prices"].items():
        record = next((r for r in rows
                       if r["area"] == area
                       and r["week_ending_monday"] == "2026-10-12"),None)
        if record is None or record["usd_per_gallon"] != expected:
            _fail("EIA_PUBLISHER_BENCHMARK_MISMATCH")
    return rows


def verify_official_faf6_zip(archive: Path) -> dict:
    """Independently replay the derived 78 rows from pinned BTS full-source bytes.

    This function NEVER reaches the internet and refuses unknown/revised ZIPs.
    """
    m = _load_manifest()["faf6"]
    if (archive.is_symlink() or not archive.is_file()
        or archive.stat().st_size != m["archive_bytes"]):
        _fail("OFFICIAL_ARCHIVE_SIZE_MISMATCH")
    raw = archive.read_bytes()
    if sha256(raw).hexdigest() != m["source_archive_sha256"]:
        _fail("OFFICIAL_ARCHIVE_SHA_MISMATCH")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if set(z.namelist()) != {"FAF6.0_State.csv","FAF6_Metadata.xlsx"}:
            _fail("OFFICIAL_ARCHIVE_LAYOUT_MISMATCH")
        item = z.getinfo(m["internal_csv"])
        if item.file_size != m["internal_csv_bytes"] or z.testzip() is not None:
            _fail("OFFICIAL_ARCHIVE_CRC_OR_SIZE_MISMATCH")
        original = z.read(m["internal_csv"])
    if sha256(original).hexdigest() != m["internal_csv_sha256"]:
        _fail("OFFICIAL_EXTRACTED_CSV_SHA_MISMATCH")
    full = csv.DictReader(io.StringIO(original.decode("utf-8-sig")))
    if tuple(full.fieldnames or ()) != SOURCE_FAF_FIELDS:
        _fail("OFFICIAL_SCHEMA_CHANGED")
    projection: list[dict] = []
    rows_read = 0
    for r in full:
        rows_read += 1
        if (r["dms_mode"] == "1" and r["trade_type"] == "1"
            and (r["dms_origst"],r["dms_destst"]) in ALLOWED_PAIRS):
            projection.append({k:r[k] for k in FAF_FIELDS})
    if rows_read != m["source_rows"] or len(projection) != m["frozen_rows"]:
        _fail("OFFICIAL_ROWS_CHANGED")
    projection.sort(key=lambda r:(r["dms_origst"],r["dms_destst"],r["sctg2"]))
    if projection != read_faf6_rows():
        _fail("OFFICIAL_ROW_COMPARISON_FAILED")
    return {"archive_verified":True,"source_rows":rows_read,
            "replayed_exact_rows":len(projection),
            "source_archive_sha256":m["source_archive_sha256"],
            "actual_customer_invoices_verified":False}


def public_context_report() -> dict:
    """Descriptive-only. No verified overcharges or contractual audit result."""
    a,b = read_faf6_rows(),read_eia_rows()
    m = _load_manifest()
    return {
        "scope":"RETALLY_EXISTING_LAB14_PUBLIC_SOURCE_BENCHMARK_ONLY",
        "faf6_model_year":2022,
        "faf6_source_rows_in_snapshot":len(a),
        "faf6_state_pairs":{k:m["faf6"][k] for k in ("md_to_pa","pa_to_md")},
        "eia_weeks":m["eia"]["snapshot_weeks"],
        "eia_observations":len(b),
        "eia_latest_week":"2026-10-12",
        "eia_diesel_usd_per_gallon":m["eia"]["latest_prices"],
        "original_government_data":True,
        "modeled_commodity_value_is_not_freight_spend":True,
        "diesel_retail_price_is_not_customer_surcharge_authority":True,
        "real_invoices_or_tariffs_examined":False,
        "verified_overcharge_cents":None,
        "validated_customer_recovery_cents":0,
        "automated_customer_contact_authorized":False,
        "commercial_claim_clearance":"NOT_ESTABLISHED",
        "all_26_historical_findings_still_open":True,
        "human_pilot_approvals_met":False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline first-party freight research verification")
    parser.add_argument("--official-zip",type=Path,help="Verify a separately downloaded pinned BTS FAF6.0 State ZIP, offline")
    args = parser.parse_args()
    result = public_context_report()
    if args.official_zip:
        result["official_replay"] = verify_official_faf6_zip(args.official_zip)
    print(json.dumps(result,sort_keys=True,indent=2))


if __name__ == "__main__":
    main()
