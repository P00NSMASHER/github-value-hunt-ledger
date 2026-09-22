#!/usr/bin/env python3
"""Targeted streaming extraction from TiC in-network MRFs.

Designed for recovery work where the provider and billing codes are already known.
The extractor:
1. streams the requested rate file to disk while hashing it;
2. scans only requested billing codes, skipping unrelated in_network items early;
3. records referenced provider_group_ids for those rates;
4. scans provider_references and keeps only groups containing requested NPIs;
5. deletes rate candidates not tied to the requested NPIs.

Public TiC rates remain benchmark/context evidence. They are not treated as the
provider's controlling contract rate by this subsystem.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import ijson
import requests

import catalog


USER_AGENT = "RecoveryWorks-TiC-TargetedExtractor/1.0"
SCALAR_EVENTS = {"string", "number", "boolean", "null"}


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
    return s


def download_rate_file(
    url: str,
    *,
    timeout: int,
    max_bytes: int,
) -> tuple[Path, dict[str, Any]]:
    s = session()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mrf")
    digest = hashlib.sha256()
    total = 0
    try:
        with s.get(url, stream=True, timeout=timeout, allow_redirects=True) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_content(1024 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError(f"rate file exceeds max_bytes={max_bytes}")
                digest.update(chunk)
                tmp.write(chunk)
            meta = {
                "final_url": resp.url,
                "http_status": resp.status_code,
                "content_type": resp.headers.get("content-type"),
                "content_length": total,
                "etag": resp.headers.get("etag"),
                "last_modified": resp.headers.get("last-modified"),
                "sha256": digest.hexdigest(),
            }
    except Exception:
        tmp.close()
        Path(tmp.name).unlink(missing_ok=True)
        raise
    tmp.close()
    return Path(tmp.name), meta


def read_rate_header(path: Path, url: str) -> dict[str, str]:
    wanted = {
        "reporting_entity_name",
        "reporting_entity_type",
        "plan_name",
        "issuer_name",
        "plan_sponsor_name",
        "plan_id_type",
        "plan_id",
        "plan_market_type",
        "last_updated_on",
        "version",
    }
    out: dict[str, str] = {}
    with catalog.open_json_stream(path, url) as fh:
        for prefix, event, value in ijson.parse(fh):
            if prefix in wanted and event in SCALAR_EVENTS and value is not None:
                out[prefix] = str(value)
            if prefix in {"provider_references", "in_network"} and event == "start_array":
                break
    return out


def skip_to_item_end(parser: Iterator[tuple[str, str, Any]], base_prefix: str) -> None:
    for prefix, event, _ in parser:
        if prefix == base_prefix and event == "end_map":
            return


def iter_target_in_network_items(
    path: Path,
    url: str,
    billing_codes: set[str],
) -> Iterator[dict[str, Any]]:
    """Build only in_network objects whose billing_code is requested."""
    with catalog.open_json_stream(path, url) as fh:
        parser = ijson.parse(fh, use_float=True)
        builder: ijson.ObjectBuilder | None = None
        current_code: str | None = None

        for prefix, event, value in parser:
            if prefix == "in_network.item" and event == "start_map":
                builder = ijson.ObjectBuilder()
                builder.event(event, value)
                current_code = None
                continue

            if builder is None:
                continue

            builder.event(event, value)

            if prefix == "in_network.item.billing_code" and event in SCALAR_EVENTS:
                current_code = str(value).strip().upper()
                if current_code not in billing_codes:
                    skip_to_item_end(parser, "in_network.item")
                    builder = None
                    current_code = None
                    continue

            if prefix == "in_network.item" and event == "end_map":
                if current_code in billing_codes:
                    yield builder.value
                builder = None
                current_code = None


def iter_target_provider_references(
    path: Path,
    url: str,
    provider_group_ids: set[int],
) -> Iterator[dict[str, Any]]:
    """Build only provider_reference objects used by targeted rate rows."""
    with catalog.open_json_stream(path, url) as fh:
        parser = ijson.parse(fh, use_float=True)
        builder: ijson.ObjectBuilder | None = None
        current_id: int | None = None

        for prefix, event, value in parser:
            if prefix == "provider_references.item" and event == "start_map":
                builder = ijson.ObjectBuilder()
                builder.event(event, value)
                current_id = None
                continue

            if builder is None:
                continue

            builder.event(event, value)

            if prefix == "provider_references.item.provider_group_id" and event in SCALAR_EVENTS:
                try:
                    current_id = int(value)
                except (TypeError, ValueError):
                    current_id = None
                if current_id not in provider_group_ids:
                    skip_to_item_end(parser, "provider_references.item")
                    builder = None
                    current_id = None
                    continue

            if prefix == "provider_references.item" and event == "end_map":
                if current_id in provider_group_ids:
                    yield builder.value
                builder = None
                current_id = None


def normalized_npi(value: Any) -> str | None:
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits if len(digits) == 10 else None


def insert_candidate_rates(
    conn: sqlite3.Connection,
    item: dict[str, Any],
    *,
    header: dict[str, str],
    rate_url: str,
    rate_sha: str,
    extraction_run_id: str,
) -> tuple[int, set[int]]:
    inserted = 0
    refs_seen: set[int] = set()
    code = str(item.get("billing_code") or "").strip().upper()
    if not code:
        return 0, refs_seen

    for rate_idx, rate in enumerate(item.get("negotiated_rates") or []):
        if not isinstance(rate, dict):
            continue
        refs = []
        for ref in rate.get("provider_references") or []:
            try:
                refs.append(int(ref))
            except (TypeError, ValueError):
                continue
        refs_seen.update(refs)

        for price_idx, price in enumerate(rate.get("negotiated_prices") or []):
            if not isinstance(price, dict) or price.get("negotiated_rate") is None:
                continue
            service_codes = price.get("service_code")
            modifiers = price.get("billing_code_modifier")
            for ref in refs:
                conn.execute(
                    """INSERT INTO rate_rows(
                         rate_file_url,rate_file_sha256,reporting_entity_name,
                         billing_code_type,billing_code_type_version,billing_code,
                         name,description,negotiation_arrangement,provider_group_id,
                         negotiated_rate,negotiated_type,setting,expiration_date,
                         billing_class,service_code_json,billing_code_modifier_json,
                         additional_information,source_locator,observed_at,extraction_run_id
                       ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        rate_url,
                        rate_sha,
                        header.get("reporting_entity_name"),
                        item.get("billing_code_type"),
                        item.get("billing_code_type_version"),
                        code,
                        item.get("name"),
                        item.get("description"),
                        item.get("negotiation_arrangement"),
                        ref,
                        str(price.get("negotiated_rate")),
                        price.get("negotiated_type"),
                        price.get("setting"),
                        price.get("expiration_date"),
                        price.get("billing_class"),
                        json.dumps(service_codes, sort_keys=True) if service_codes is not None else None,
                        json.dumps(modifiers, sort_keys=True) if modifiers is not None else None,
                        price.get("additional_information"),
                        (
                            f"{rate_url}#billing_code={urllib_quote(code)}"
                            f"&rate={rate_idx}&price={price_idx}&provider_group_id={ref}"
                        ),
                        utcnow(),
                        extraction_run_id,
                    ),
                )
                inserted += 1
    return inserted, refs_seen


def urllib_quote(value: str) -> str:
    import urllib.parse
    return urllib.parse.quote(value, safe="")


def insert_matching_provider_groups(
    conn: sqlite3.Connection,
    ref: dict[str, Any],
    *,
    target_npis: set[str],
    rate_url: str,
    rate_sha: str,
) -> tuple[int, bool]:
    try:
        group_id = int(ref.get("provider_group_id"))
    except (TypeError, ValueError):
        return 0, False

    inserted = 0
    matched = False
    groups = ref.get("provider_groups") or []
    if not groups and ref.get("location"):
        # Current CMS schema requires inline provider_groups. Preserve an explicit
        # unresolved observation instead of fetching an unbounded extension here.
        return 0, False

    for group_idx, group in enumerate(groups):
        if not isinstance(group, dict):
            continue
        npis = {n for n in (normalized_npi(x) for x in group.get("npi") or []) if n}
        wanted = sorted(npis & target_npis)
        if not wanted:
            continue
        matched = True
        tin = group.get("tin") or {}
        tin_type = str(tin.get("type") or "") or None
        tin_value = str(tin.get("value") or "") or None
        business_name = str(tin.get("business_name") or "") or None
        for npi in wanted:
            conn.execute(
                """INSERT OR IGNORE INTO provider_groups(
                     rate_file_url,rate_file_sha256,provider_group_id,
                     tin_type,tin_value,business_name,npi,source_locator
                   ) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    rate_url, rate_sha, group_id, tin_type, tin_value,
                    business_name, npi,
                    f"{rate_url}#provider_group_id={group_id}&group={group_idx}&npi={npi}",
                ),
            )
            inserted += 1
    return inserted, matched


def extract_one(
    conn: sqlite3.Connection,
    *,
    rate_url: str,
    billing_codes: set[str],
    target_npis: set[str],
    timeout: int,
    max_bytes: int,
) -> dict[str, Any]:
    path, meta = download_rate_file(rate_url, timeout=timeout, max_bytes=max_bytes)
    extraction_run_id = f"{utcnow()}:{meta['sha256'][:16]}"
    stats = {
        "rate_url": rate_url,
        "rate_file_sha256": meta["sha256"],
        "byte_count": meta["content_length"],
        "target_items": 0,
        "candidate_rate_rows": 0,
        "provider_group_ids_referenced": 0,
        "provider_rows": 0,
        "matched_provider_group_ids": 0,
        "kept_rate_rows": 0,
        "extraction_run_id": extraction_run_id,
    }
    try:
        header = read_rate_header(path, rate_url)
        candidate_groups: set[int] = set()

        for item in iter_target_in_network_items(path, rate_url, billing_codes):
            stats["target_items"] += 1
            count, refs = insert_candidate_rates(
                conn, item,
                header=header,
                rate_url=rate_url,
                rate_sha=meta["sha256"],
                extraction_run_id=extraction_run_id,
            )
            stats["candidate_rate_rows"] += count
            candidate_groups.update(refs)

        stats["provider_group_ids_referenced"] = len(candidate_groups)
        matched_groups: set[int] = set()
        for ref in iter_target_provider_references(path, rate_url, candidate_groups):
            count, matched = insert_matching_provider_groups(
                conn, ref,
                target_npis=target_npis,
                rate_url=rate_url,
                rate_sha=meta["sha256"],
            )
            stats["provider_rows"] += count
            if matched:
                try:
                    matched_groups.add(int(ref["provider_group_id"]))
                except (TypeError, ValueError, KeyError):
                    pass

        stats["matched_provider_group_ids"] = len(matched_groups)
        if matched_groups:
            marks = ",".join("?" for _ in matched_groups)
            conn.execute(
                f"""DELETE FROM rate_rows
                    WHERE extraction_run_id=?
                      AND provider_group_id NOT IN ({marks})""",
                (extraction_run_id, *sorted(matched_groups)),
            )
        else:
            conn.execute(
                "DELETE FROM rate_rows WHERE extraction_run_id=?",
                (extraction_run_id,),
            )

        stats["kept_rate_rows"] = conn.execute(
            "SELECT COUNT(*) FROM rate_rows WHERE extraction_run_id=?",
            (extraction_run_id,),
        ).fetchone()[0]

        conn.execute(
            """UPDATE mrf_files
               SET content_length=COALESCE(content_length,?),
                   etag=COALESCE(etag,?),
                   last_modified=COALESCE(last_modified,?),
                   reporting_entity_name=COALESCE(reporting_entity_name,?),
                   reporting_entity_type=COALESCE(reporting_entity_type,?),
                   schema_version=COALESCE(schema_version,?),
                   last_updated_on=COALESCE(last_updated_on,?),
                   parse_status='target_extracted'
               WHERE file_url=?""",
            (
                meta["content_length"], meta["etag"], meta["last_modified"],
                header.get("reporting_entity_name"),
                header.get("reporting_entity_type"),
                header.get("version"),
                header.get("last_updated_on"),
                rate_url,
            ),
        )
        conn.commit()
        return stats
    finally:
        path.unlink(missing_ok=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--url", action="append", default=[])
    p.add_argument("--billing-code", action="append", required=True)
    p.add_argument("--npi", action="append", required=True)
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--max-bytes", type=int, default=100_000_000_000)
    p.add_argument("--output")
    args = p.parse_args()

    billing_codes = {str(x).strip().upper() for x in args.billing_code if str(x).strip()}
    target_npis = {n for n in (normalized_npi(x) for x in args.npi) if n}
    if not billing_codes:
        p.error("at least one --billing-code is required")
    if not target_npis:
        p.error("at least one valid 10-digit --npi is required")

    conn = catalog.init_db(Path(args.db))
    results = []
    urls = list(dict.fromkeys(args.url))
    if not urls:
        raise SystemExit("at least one --url is required for targeted extraction")

    for url in urls:
        try:
            results.append(extract_one(
                conn,
                rate_url=catalog.canonical_url(url),
                billing_codes=billing_codes,
                target_npis=target_npis,
                timeout=args.timeout,
                max_bytes=args.max_bytes,
            ))
        except Exception as exc:
            catalog.record_error(conn, None, url, "target_extract", exc)
            conn.commit()
            results.append({
                "rate_url": url,
                "status": "error",
                "error_type": type(exc).__name__,
                "detail": str(exc),
            })

    conn.close()
    payload = {
        "billing_codes": sorted(billing_codes),
        "npis": sorted(target_npis),
        "files": results,
    }
    text = json.dumps(payload, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
