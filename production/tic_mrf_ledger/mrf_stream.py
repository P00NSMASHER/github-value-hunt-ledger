#!/usr/bin/env python3
"""Selective streaming extraction from CMS Transparency-in-Coverage in-network MRFs.

The universe catalog and rate extraction are intentionally separated. This tool
requires an explicit billing-code filter, and by default an NPI filter too, so
it cannot accidentally materialize trillions of public rate rows.

Public TiC rates are stored as corroborating evidence. They are not marked as a
verified controlling provider contract merely because they appear in an MRF.
"""

from __future__ import annotations

import argparse
import contextlib
import gzip
import hashlib
import io
import json
import sqlite3
from pathlib import Path
from typing import Any, BinaryIO, Iterator

import ijson
import requests

import catalog


PARSER_VERSION = "tic-mrf-stream-v1"
USER_AGENT = "Hunter-TiC-MRF-Stream/1.0"


def load_code_filter(path: Path) -> set[tuple[str | None, str]]:
    result: set[tuple[str | None, str]] = set()
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        parts = [x.strip() for x in text.split(",")]
        if len(parts) == 1:
            result.add((None, parts[0].upper()))
        else:
            result.add((parts[0].upper() or None, parts[1].upper()))
    if not result:
        raise ValueError("code filter is empty")
    return result


def load_npi_filter(path: Path | None) -> set[str]:
    if path is None:
        return set()
    result = {
        line.strip()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    bad = [x for x in result if not x.isdigit()]
    if bad:
        raise ValueError(f"NPI filter contains non-digits: {bad[:3]}")
    return result


def filter_hash(values: set[Any]) -> str:
    payload = json.dumps(sorted(values), separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


def code_matches(
    code_type: str | None,
    code: str | None,
    wanted: set[tuple[str | None, str]],
) -> bool:
    if code is None:
        return False
    code_norm = str(code).upper()
    type_norm = str(code_type).upper() if code_type is not None else None
    return (type_norm, code_norm) in wanted or (None, code_norm) in wanted


@contextlib.contextmanager
def remote_json_stream(
    session: requests.Session,
    url: str,
    *,
    timeout: int,
) -> Iterator[tuple[BinaryIO, requests.Response]]:
    resp = session.get(url, stream=True, timeout=timeout, allow_redirects=True)
    try:
        resp.raise_for_status()
        resp.raw.decode_content = False
        raw: BinaryIO = resp.raw
        content_encoding = (resp.headers.get("content-encoding") or "").lower()
        ctype = (resp.headers.get("content-type") or "").lower()
        if (
            url.lower().split("?", 1)[0].endswith(".gz")
            or "gzip" in content_encoding
            or "gzip" in ctype
        ):
            raw = gzip.GzipFile(fileobj=resp.raw)
        yield raw, resp
    finally:
        resp.close()


@contextlib.contextmanager
def local_json_stream(path: Path) -> Iterator[BinaryIO]:
    raw = path.open("rb")
    try:
        if path.suffix.lower() == ".gz":
            gz = gzip.GzipFile(fileobj=raw)
            try:
                yield gz
            finally:
                gz.close()
        else:
            yield raw
    finally:
        raw.close()


def provider_groups_pass(
    open_stream,
    *,
    npi_filter: set[str],
    allow_all_providers: bool,
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, Any],
]:
    selected: dict[str, list[dict[str, Any]]] = {}
    stats = {
        "provider_references_examined": 0,
        "provider_references_selected": 0,
        "provider_groups_selected": 0,
        "npis_selected": 0,
    }

    with open_stream() as stream:
        for ref in ijson.items(stream, "provider_references.item"):
            if not isinstance(ref, dict):
                continue
            stats["provider_references_examined"] += 1
            group_id = ref.get("provider_group_id")
            if group_id is None:
                continue
            groups = [
                g for g in (ref.get("provider_groups") or [])
                if isinstance(g, dict)
            ]
            keep_groups: list[dict[str, Any]] = []
            for group in groups:
                npis = {
                    str(npi)
                    for npi in (group.get("npi") or [])
                    if str(npi) not in {"", "0", "None"}
                }
                if allow_all_providers or not npi_filter or (npis & npi_filter):
                    keep_groups.append(group)
                    stats["npis_selected"] += len(npis & npi_filter) if npi_filter else len(npis)
            if keep_groups:
                selected[str(group_id)] = keep_groups
                stats["provider_references_selected"] += 1
                stats["provider_groups_selected"] += len(keep_groups)
    return selected, stats


def ensure_extract_run(
    conn: sqlite3.Connection,
    *,
    mrf_file_id: int,
    code_filter_sha: str,
    npi_filter_sha: str | None,
    source_sha256: str | None,
    source_etag: str | None,
    source_last_modified: str | None,
) -> int:
    run_id = conn.execute(
        """INSERT INTO rate_extract_runs(
             mrf_file_id, started_at, parser_version, code_filter_sha256,
             npi_filter_sha256, source_sha256, source_etag,
             source_last_modified, status
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running')""",
        (
            mrf_file_id, catalog.utcnow(), PARSER_VERSION,
            code_filter_sha, npi_filter_sha, source_sha256,
            source_etag, source_last_modified,
        ),
    ).lastrowid
    conn.commit()
    return int(run_id)


def persist_provider_groups(
    conn: sqlite3.Connection,
    run_id: int,
    selected: dict[str, list[dict[str, Any]]],
) -> dict[str, set[str]]:
    group_npis: dict[str, set[str]] = {}
    for group_id, groups in selected.items():
        group_npis.setdefault(group_id, set())
        for group in groups:
            tin = group.get("tin") if isinstance(group.get("tin"), dict) else {}
            tin_type = str(tin.get("type")) if tin.get("type") is not None else None
            tin_value = str(tin.get("value")) if tin.get("value") is not None else None
            conn.execute(
                """INSERT OR IGNORE INTO provider_groups(
                     rate_extract_run_id, provider_group_id, tin_type, tin_value
                   ) VALUES (?, ?, ?, ?)""",
                (run_id, group_id, tin_type, tin_value),
            )
            row_id = conn.execute(
                """SELECT id FROM provider_groups
                   WHERE rate_extract_run_id=? AND provider_group_id=?
                     AND COALESCE(tin_type,'')=COALESCE(?, '')
                     AND COALESCE(tin_value,'')=COALESCE(?, '')""",
                (run_id, group_id, tin_type, tin_value),
            ).fetchone()[0]
            for npi in group.get("npi") or []:
                npi_s = str(npi)
                if npi_s in {"0", "", "None"}:
                    continue
                group_npis[group_id].add(npi_s)
                conn.execute(
                    """INSERT OR IGNORE INTO provider_group_npis(
                         provider_group_row_id, npi
                       ) VALUES (?, ?)""",
                    (row_id, npi_s),
                )
    conn.commit()
    return group_npis


def evidence_fingerprint(row: dict[str, Any]) -> str:
    payload = json.dumps(
        row, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def rates_pass(
    open_stream,
    *,
    conn: sqlite3.Connection,
    run_id: int,
    code_filter: set[tuple[str | None, str]],
    selected_group_ids: set[str],
    row_limit: int,
) -> dict[str, int]:
    stats = {
        "in_network_items_examined": 0,
        "billing_code_items_matched": 0,
        "rate_rows_generated": 0,
        "provider_reference_rows_skipped": 0,
    }

    with open_stream() as stream:
        for item in ijson.items(stream, "in_network.item"):
            if not isinstance(item, dict):
                continue
            stats["in_network_items_examined"] += 1
            if not code_matches(
                item.get("billing_code_type"),
                item.get("billing_code"),
                code_filter,
            ):
                continue
            stats["billing_code_items_matched"] += 1

            for negotiated_rate in item.get("negotiated_rates") or []:
                if not isinstance(negotiated_rate, dict):
                    continue
                refs = [
                    str(x)
                    for x in (negotiated_rate.get("provider_references") or [])
                ]
                refs = [x for x in refs if x in selected_group_ids]
                if not refs:
                    stats["provider_reference_rows_skipped"] += 1
                    continue

                for price in negotiated_rate.get("negotiated_prices") or []:
                    if not isinstance(price, dict):
                        continue
                    negotiated_rate_value = price.get("negotiated_rate")
                    if negotiated_rate_value is None:
                        continue

                    for group_id in refs:
                        normalized = {
                            "billing_code_type": str(item.get("billing_code_type") or "").upper(),
                            "billing_code_type_version": (
                                str(item.get("billing_code_type_version"))
                                if item.get("billing_code_type_version") is not None
                                else None
                            ),
                            "billing_code": str(item.get("billing_code") or "").upper(),
                            "description": item.get("description"),
                            "name": item.get("name"),
                            "billing_class": price.get("billing_class"),
                            "setting": price.get("setting"),
                            "negotiation_arrangement": item.get("negotiation_arrangement"),
                            "negotiated_type": price.get("negotiated_type"),
                            "negotiated_rate": str(negotiated_rate_value),
                            "expiration_date": price.get("expiration_date"),
                            "provider_group_id": group_id,
                            "service_codes_json": json.dumps(
                                price.get("service_code") or [],
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                            "billing_code_modifiers_json": json.dumps(
                                price.get("billing_code_modifier") or [],
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                            "additional_information": price.get("additional_information"),
                        }
                        fingerprint = evidence_fingerprint(normalized)
                        conn.execute(
                            """INSERT OR IGNORE INTO rates(
                                 rate_extract_run_id, billing_code_type,
                                 billing_code_type_version, billing_code,
                                 description, name, billing_class, setting,
                                 negotiation_arrangement, negotiated_type,
                                 negotiated_rate, expiration_date,
                                 provider_group_id, service_codes_json,
                                 billing_code_modifiers_json,
                                 additional_information, evidence_fingerprint
                               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                run_id,
                                normalized["billing_code_type"],
                                normalized["billing_code_type_version"],
                                normalized["billing_code"],
                                normalized["description"],
                                normalized["name"],
                                normalized["billing_class"],
                                normalized["setting"],
                                normalized["negotiation_arrangement"],
                                normalized["negotiated_type"],
                                normalized["negotiated_rate"],
                                normalized["expiration_date"],
                                normalized["provider_group_id"],
                                normalized["service_codes_json"],
                                normalized["billing_code_modifiers_json"],
                                normalized["additional_information"],
                                fingerprint,
                            ),
                        )
                        stats["rate_rows_generated"] += 1
                        if row_limit and stats["rate_rows_generated"] >= row_limit:
                            conn.commit()
                            return stats

            if stats["rate_rows_generated"] and stats["rate_rows_generated"] % 5000 == 0:
                conn.commit()

    conn.commit()
    return stats


def get_mrf_row(conn: sqlite3.Connection, mrf_file_id: int) -> sqlite3.Row:
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """SELECT f.*, s.payer_key, s.display_name
           FROM mrf_files f
           JOIN sources s ON s.id=f.source_id
           WHERE f.id=?""",
        (mrf_file_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"mrf_file_id {mrf_file_id} not found")
    if row["file_type"] != "IN_NETWORK":
        raise ValueError("selective rate extraction requires file_type=IN_NETWORK")
    return row


def command_extract(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    conn = catalog.init_db(db_path)
    mrf = get_mrf_row(conn, args.mrf_file_id)

    codes = load_code_filter(Path(args.code_file))
    npis = load_npi_filter(Path(args.npi_file) if args.npi_file else None)
    if not npis and not args.allow_all_providers:
        raise SystemExit(
            "NPI filter is required by default. Pass --allow-all-providers only "
            "for an intentionally broad code-only extraction."
        )

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})

    source_sha256 = None
    source_etag = None
    source_last_modified = None

    local_path = Path(args.local_file) if args.local_file else None
    if local_path:
        raw = local_path.read_bytes()
        source_sha256 = hashlib.sha256(raw).hexdigest()

        def open_stream():
            return local_json_stream(local_path)
    else:
        url = str(mrf["url"])

        # A lightweight HEAD is best-effort only; many payer CDNs do not support it.
        try:
            head = session.head(url, timeout=args.timeout, allow_redirects=True)
            if head.ok:
                source_etag = head.headers.get("etag")
                source_last_modified = head.headers.get("last-modified")
        except requests.RequestException:
            pass

        def open_stream():
            return remote_json_stream(session, url, timeout=args.timeout)

    run_id = ensure_extract_run(
        conn,
        mrf_file_id=args.mrf_file_id,
        code_filter_sha=filter_hash(codes),
        npi_filter_sha=filter_hash(npis) if npis else None,
        source_sha256=source_sha256,
        source_etag=source_etag,
        source_last_modified=source_last_modified,
    )

    try:
        selected, provider_stats = provider_groups_pass(
            open_stream,
            npi_filter=npis,
            allow_all_providers=args.allow_all_providers,
        )
        group_npis = persist_provider_groups(conn, run_id, selected)
        rate_stats = rates_pass(
            open_stream,
            conn=conn,
            run_id=run_id,
            code_filter=codes,
            selected_group_ids=set(group_npis),
            row_limit=args.row_limit,
        )
        stats = {
            **provider_stats,
            **rate_stats,
            "selected_provider_group_ids": len(group_npis),
            "distinct_selected_npis": len(
                {npi for values in group_npis.values() for npi in values}
            ),
        }
        conn.execute(
            """UPDATE rate_extract_runs
               SET finished_at=?, status='complete', stats_json=?
               WHERE id=?""",
            (catalog.utcnow(), json.dumps(stats, sort_keys=True), run_id),
        )
        conn.execute(
            """UPDATE mrf_files SET access_status='RATE_EXTRACTED',
                   etag=COALESCE(?, etag),
                   last_modified=COALESCE(?, last_modified)
               WHERE id=?""",
            (source_etag, source_last_modified, args.mrf_file_id),
        )
        conn.commit()
        print(json.dumps({"rate_extract_run_id": run_id, **stats}, indent=2))
        return 0
    except Exception as exc:
        conn.execute(
            """UPDATE rate_extract_runs
               SET finished_at=?, status='failed', stats_json=?
               WHERE id=?""",
            (
                catalog.utcnow(),
                json.dumps({"error_type": type(exc).__name__, "detail": str(exc)[:4000]}),
                run_id,
            ),
        )
        catalog.record_error(
            conn,
            int(mrf["source_id"]),
            str(mrf["url"]),
            "rate_extract",
            exc,
        )
        conn.commit()
        raise
    finally:
        conn.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Selective TiC in-network MRF extractor")
    sub = p.add_subparsers(dest="command", required=True)

    e = sub.add_parser("extract")
    e.add_argument("--db", required=True)
    e.add_argument("--mrf-file-id", type=int, required=True)
    e.add_argument("--code-file", required=True)
    e.add_argument("--npi-file")
    e.add_argument("--local-file")
    e.add_argument("--allow-all-providers", action="store_true")
    e.add_argument("--row-limit", type=int, default=0)
    e.add_argument("--timeout", type=int, default=60)
    e.set_defaults(func=command_extract)
    return p


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
