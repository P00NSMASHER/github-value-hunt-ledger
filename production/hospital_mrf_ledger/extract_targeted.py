#!/usr/bin/env python3
"""Targeted extraction from CMS Hospital Price Transparency MRFs.

Public hospital MRF prices remain benchmark/context evidence. This module does
not assert claim-level applicability or a controlling contract rate.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Iterable

import ijson

import catalog


def norm_text(value: Any) -> str:
    return str(value or "").strip()


def norm_code(value: Any) -> str:
    return re.sub(r"\s+", "", norm_text(value)).upper()


def matches_filter(value: Any, wanted: set[str]) -> bool:
    if not wanted:
        return True
    return norm_text(value).casefold() in wanted


def latest_snapshot(conn: sqlite3.Connection, url: str) -> sqlite3.Row | None:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        """SELECT * FROM mrf_snapshots
           WHERE mrf_url=? ORDER BY id DESC LIMIT 1""",
        (catalog.canonical_url(url),),
    ).fetchone()


def ensure_snapshot(
    conn: sqlite3.Connection,
    db_path: Path,
    mrf_url: str,
    *,
    timeout: int,
    max_bytes: int,
) -> tuple[sqlite3.Row, Path]:
    mrf_url = catalog.canonical_url(mrf_url)
    row = latest_snapshot(conn, mrf_url)
    if row and row["blob_relpath"]:
        p = db_path.parent / row["blob_relpath"]
        if p.exists():
            return row, p

    authority_id = catalog.persist_authority(conn)
    path, meta = catalog.download_to_blob(
        db_path.parent, mrf_url, timeout=timeout, max_bytes=max_bytes
    )
    fmt, compression = catalog.detect_format(path, mrf_url, meta.get("content_type"))
    if fmt == "json":
        header = catalog.json_header(path)
        status = "parsed:json_header"
    elif fmt == "csv":
        header = catalog.csv_header(path)
        status = "parsed:csv_header"
    else:
        header = {}
        status = "unsupported:format"
    catalog.persist_mrf_snapshot(
        conn, authority_id, mrf_url, meta, header, fmt, compression, status
    )
    conn.commit()
    row = latest_snapshot(conn, mrf_url)
    assert row
    return row, path


def matching_code_pairs(item: dict[str, Any], targets: set[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for obj in item.get("code_information") or []:
        if not isinstance(obj, dict):
            continue
        code = norm_code(obj.get("code"))
        typ = norm_text(obj.get("type")).upper()
        if code and (not targets or code in targets):
            pairs.append((typ, code))
    return pairs


def insert_row(
    conn: sqlite3.Connection,
    *,
    snapshot_id: int,
    extraction_id: str,
    description: Any,
    code_type: str,
    code: str,
    charge: dict[str, Any],
    payer: dict[str, Any] | None,
    source_locator: str,
) -> None:
    payer = payer or {}
    conn.execute(
        """INSERT INTO charge_rows(
             mrf_snapshot_id,extraction_run_id,description,code_type,code,setting,
             modifier_json,gross_charge,discounted_cash,minimum_negotiated,maximum_negotiated,
             payer_name,plan_name,methodology,standard_charge_dollar,
             standard_charge_percentage,standard_charge_algorithm,median_amount,
             percentile_10,percentile_90,allowed_amount_count,additional_payer_notes,
             additional_generic_notes,source_locator,observed_at
           ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            snapshot_id,
            extraction_id,
            norm_text(description) or None,
            code_type,
            code,
            charge.get("setting"),
            json.dumps(charge.get("modifier_code"), sort_keys=True)
            if charge.get("modifier_code") is not None else None,
            None if charge.get("gross_charge") is None else str(charge.get("gross_charge")),
            None if charge.get("discounted_cash") is None else str(charge.get("discounted_cash")),
            None if charge.get("minimum") is None else str(charge.get("minimum")),
            None if charge.get("maximum") is None else str(charge.get("maximum")),
            payer.get("payer_name"),
            payer.get("plan_name"),
            payer.get("methodology"),
            None if payer.get("standard_charge_dollar") is None else str(payer.get("standard_charge_dollar")),
            None if payer.get("standard_charge_percentage") is None else str(payer.get("standard_charge_percentage")),
            payer.get("standard_charge_algorithm"),
            None if payer.get("median_amount") is None else str(payer.get("median_amount")),
            None if payer.get("10th_percentile") is None else str(payer.get("10th_percentile")),
            None if payer.get("90th_percentile") is None else str(payer.get("90th_percentile")),
            None if payer.get("count") is None else str(payer.get("count")),
            payer.get("additional_payer_notes"),
            charge.get("additional_generic_notes"),
            source_locator,
            catalog.utcnow(),
        ),
    )


def extract_json(
    conn: sqlite3.Connection,
    path: Path,
    *,
    snapshot_id: int,
    targets: set[str],
    payers: set[str],
    plans: set[str],
    extraction_id: str,
    url: str,
) -> int:
    inserted = 0
    with catalog.open_decompressed(path) as fh:
        for item_idx, item in enumerate(
            ijson.items(fh, "standard_charge_information.item", use_float=True)
        ):
            if not isinstance(item, dict):
                continue
            pairs = matching_code_pairs(item, targets)
            if not pairs:
                continue
            for charge_idx, charge in enumerate(item.get("standard_charges") or []):
                if not isinstance(charge, dict):
                    continue
                payer_rows = charge.get("payers_information") or []
                # Gross/cash-only rows remain useful benchmark evidence when no payer filter exists.
                if not payer_rows and not payers and not plans:
                    for typ, code in pairs:
                        insert_row(
                            conn,
                            snapshot_id=snapshot_id,
                            extraction_id=extraction_id,
                            description=item.get("description"),
                            code_type=typ,
                            code=code,
                            charge=charge,
                            payer=None,
                            source_locator=f"{url}#standard_charge_information={item_idx}&charge={charge_idx}",
                        )
                        inserted += 1
                    continue

                for payer_idx, payer in enumerate(payer_rows):
                    if not isinstance(payer, dict):
                        continue
                    if not matches_filter(payer.get("payer_name"), payers):
                        continue
                    if not matches_filter(payer.get("plan_name"), plans):
                        continue
                    for typ, code in pairs:
                        insert_row(
                            conn,
                            snapshot_id=snapshot_id,
                            extraction_id=extraction_id,
                            description=item.get("description"),
                            code_type=typ,
                            code=code,
                            charge=charge,
                            payer=payer,
                            source_locator=(
                                f"{url}#standard_charge_information={item_idx}"
                                f"&charge={charge_idx}&payer={payer_idx}"
                            ),
                        )
                        inserted += 1
    return inserted


def canon_header(value: str) -> str:
    return re.sub(r"\s*\|\s*", "|", value.strip()).lower()


def csv_general_and_reader(path: Path) -> tuple[dict[str, str], csv.DictReader]:
    raw = catalog.open_decompressed(path)
    text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
    reader = csv.reader(text)
    try:
        general_headers = next(reader)
        general_values = next(reader)
        charge_headers = next(reader)
    except StopIteration as exc:
        text.close()
        raise ValueError("CSV missing the required three header rows") from exc

    general = {
        canon_header(k): (general_values[i].strip() if i < len(general_values) else "")
        for i, k in enumerate(general_headers) if k.strip()
    }
    dict_reader = csv.DictReader(text, fieldnames=[canon_header(x) for x in charge_headers])
    # Keep TextIOWrapper reachable through reader.line_num / underlying reader lifetime.
    setattr(dict_reader, "_hpt_text_wrapper", text)
    return general, dict_reader


def row_code_pairs(row: dict[str, str], targets: set[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for key, value in row.items():
        m = re.fullmatch(r"code\|(\d+)", key or "")
        if not m:
            continue
        code = norm_code(value)
        typ = norm_text(row.get(f"code|{m.group(1)}|type")).upper()
        if code and typ and (not targets or code in targets):
            pairs.append((typ, code))
    return pairs


def extract_csv_tall(
    conn: sqlite3.Connection,
    path: Path,
    *,
    snapshot_id: int,
    targets: set[str],
    payers: set[str],
    plans: set[str],
    extraction_id: str,
    url: str,
) -> int:
    _, reader = csv_general_and_reader(path)
    inserted = 0
    try:
        fieldset = set(reader.fieldnames or [])
        required = {"description", "setting", "payer_name", "plan_name"}
        if not required.issubset(fieldset):
            raise ValueError("CSV is not recognized as CMS tall layout")

        for row_idx, row in enumerate(reader, start=4):
            pairs = row_code_pairs(row, targets)
            if not pairs:
                continue
            if not matches_filter(row.get("payer_name"), payers):
                continue
            if not matches_filter(row.get("plan_name"), plans):
                continue
            charge = {
                "setting": row.get("setting") or None,
                "modifier_code": [x.strip() for x in (row.get("modifiers") or "").split("|") if x.strip()] or None,
                "gross_charge": row.get("standard_charge|gross") or None,
                "discounted_cash": row.get("standard_charge|discounted_cash") or None,
                "minimum": row.get("standard_charge|min") or None,
                "maximum": row.get("standard_charge|max") or None,
                "additional_generic_notes": row.get("additional_generic_notes") or None,
            }
            payer = {
                "payer_name": row.get("payer_name") or None,
                "plan_name": row.get("plan_name") or None,
                "methodology": row.get("standard_charge|methodology") or None,
                "standard_charge_dollar": row.get("standard_charge|negotiated_dollar") or None,
                "standard_charge_percentage": row.get("standard_charge|negotiated_percentage") or None,
                "standard_charge_algorithm": row.get("standard_charge|negotiated_algorithm") or None,
                "median_amount": row.get("median_amount") or None,
                "10th_percentile": row.get("10th_percentile") or None,
                "90th_percentile": row.get("90th_percentile") or None,
                "count": row.get("count") or None,
                "additional_payer_notes": (
                    row.get("additional_payer_notes")
                    or row.get("additional_payer_specific_notes")
                    or None
                ),
            }
            for typ, code in pairs:
                insert_row(
                    conn,
                    snapshot_id=snapshot_id,
                    extraction_id=extraction_id,
                    description=row.get("description"),
                    code_type=typ,
                    code=code,
                    charge=charge,
                    payer=payer,
                    source_locator=f"{url}#csv_row={row_idx}",
                )
                inserted += 1
    finally:
        wrapper = getattr(reader, "_hpt_text_wrapper", None)
        if wrapper:
            wrapper.close()
    return inserted


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--mrf-url", required=True)
    p.add_argument("--billing-code", action="append", default=[])
    p.add_argument("--payer", action="append", default=[])
    p.add_argument("--plan", action="append", default=[])
    p.add_argument("--output")
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--max-bytes", type=int, default=2 * 1024 * 1024 * 1024)
    args = p.parse_args()

    db_path = Path(args.db)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    targets = {norm_code(x) for x in args.billing_code if norm_code(x)}
    payers = {x.strip().casefold() for x in args.payer if x.strip()}
    plans = {x.strip().casefold() for x in args.plan if x.strip()}
    extraction_id = f"HPT:{uuid.uuid4().hex}"

    snap, path = ensure_snapshot(
        conn, db_path, args.mrf_url, timeout=args.timeout, max_bytes=args.max_bytes
    )
    fmt = snap["format"]
    if fmt == "json":
        inserted = extract_json(
            conn, path, snapshot_id=int(snap["id"]), targets=targets, payers=payers,
            plans=plans, extraction_id=extraction_id, url=snap["mrf_url"],
        )
    elif fmt == "csv":
        inserted = extract_csv_tall(
            conn, path, snapshot_id=int(snap["id"]), targets=targets, payers=payers,
            plans=plans, extraction_id=extraction_id, url=snap["mrf_url"],
        )
    else:
        raise SystemExit(f"unsupported MRF format: {fmt}")

    conn.commit()
    rows = conn.execute(
        """SELECT * FROM hospital_rate_benchmark_ledger
           WHERE extraction_run_id=? ORDER BY code_type,code,payer_name,plan_name""",
        (extraction_id,),
    ).fetchall()
    columns = [d[0] for d in conn.execute(
        "SELECT * FROM hospital_rate_benchmark_ledger LIMIT 0"
    ).description]
    payload = [dict(zip(columns, row)) for row in rows]
    if args.output:
        Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps({"extraction_run_id": extraction_id, "rows": inserted}, sort_keys=True))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
