#!/usr/bin/env python3
"""Retry only measured transient FMC crawl failures.

This stage is intentionally narrow. It retries URLs whose durable crawl_errors
classify as SAFE_NETWORK_RETRY (timeouts, connection errors, retryable HTTP
statuses, and the now-fixed local blob-write race). It never auto-retries
authentication gates, unresolved shared publishers, stale 404/410 links, TLS
policy failures, or parse failures.

Successful retry bytes are stored in the same content-addressed evidence store
and normalized with the current production parser. Original error rows remain
as historical observations; retry outcomes are additive evidence.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

import crawler as base
import crawler_v2 as v2
import publisher_adapters as publishers
import retry_plan
import run as production


PARSER_VERSION = "fmc-ledger-v3-retry"


def collect_targets(
    conn: sqlite3.Connection,
    *,
    limit: int = 0,
) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT
             ce.id error_id,
             ce.tariff_location_id,
             ce.url,
             ce.stage,
             ce.error_type,
             ce.detail,
             tl.canonical_url,
             tl.directory_url,
             tl.directory_snapshot_sha256,
             e.entity_class,
             e.organization_no,
             e.legal_name,
             e.trade_name,
             e.active
           FROM crawl_errors ce
           JOIN tariff_locations tl ON tl.id=ce.tariff_location_id
           JOIN entities e ON e.id=tl.entity_id
           ORDER BY ce.id"""
    ).fetchall()

    targets: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        category, reason = retry_plan.classify(
            row["stage"],
            row["error_type"],
            row["detail"] or "",
        )
        if category != "SAFE_NETWORK_RETRY":
            continue

        # If the same location+URL already has successful bytes, the historic
        # failure is resolved and does not need another request.
        existing = conn.execute(
            """SELECT 1 FROM snapshots
               WHERE tariff_location_id=?
                 AND requested_url=?
                 AND sha256 IS NOT NULL
                 AND http_status BETWEEN 200 AND 299
               LIMIT 1""",
            (row["tariff_location_id"], row["url"]),
        ).fetchone()
        if existing:
            continue

        key = (int(row["tariff_location_id"]), row["url"])
        target = targets.setdefault(
            key,
            {
                "tariff_location_id": int(row["tariff_location_id"]),
                "url": row["url"],
                "reasons": set(),
                "error_ids": [],
                "source": base.EntitySource(
                    entity_class=row["entity_class"],
                    organization_no=row["organization_no"],
                    legal_name=row["legal_name"],
                    trade_name=row["trade_name"] or "",
                    active=bool(row["active"]),
                    tariff_url=row["canonical_url"],
                    directory_url=row["directory_url"],
                    directory_sha256=row["directory_snapshot_sha256"] or "",
                ),
            },
        )
        target["reasons"].add(reason)
        target["error_ids"].append(int(row["error_id"]))

    result = list(targets.values())
    result.sort(
        key=lambda x: (
            x["source"].entity_class,
            x["source"].organization_no,
            x["url"],
        )
    )
    if limit > 0:
        result = result[:limit]
    return result


def retry_one(
    target: dict[str, Any],
    artifact_root: Path,
    *,
    timeout: int,
    max_bytes: int,
) -> dict[str, Any]:
    src: base.EntitySource = target["source"]
    requested_url = base.canonicalize_url(target["url"]) or target["url"]
    now = base.utcnow()
    errors: list[dict[str, str]] = []

    try:
        raw, resp = v2.fetch_bytes_cached(requested_url, timeout, max_bytes)
    except Exception as exc:
        return {
            "source": src,
            "snapshots": [],
            "terms": [],
            "errors": [{
                "url": requested_url,
                "stage": "retry_fetch",
                "error_type": type(exc).__name__,
                "detail": (
                    f"bounded retry failed; prior reasons="
                    f"{sorted(target['reasons'])}; {str(exc)[:1600]}"
                ),
            }],
            "retry_status": "FAILED",
            "parser_version": PARSER_VERSION,
        }

    final_url = base.canonicalize_url(resp.url) or resp.url
    digest = base.sha256_bytes(raw)
    ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    text = ""
    title = None
    parse_kind = "binary"
    parser_status = "retry:snapshotted"

    try:
        text, _, parse_kind, title = base.extract_text_and_links(
            raw,
            ctype,
            final_url,
        )
        parser_status = f"retry:parsed:{parse_kind}"
    except Exception as exc:
        errors.append({
            "url": final_url,
            "stage": "retry_parse",
            "error_type": type(exc).__name__,
            "detail": str(exc)[:2000],
        })
        parser_status = f"retry:snapshot_only:{type(exc).__name__}"

    family = publishers.family_for(src.tariff_url)
    auth_page = bool(text) and publishers.auth_or_login_page(text, final_url)
    if auth_page:
        errors.append({
            "url": final_url,
            "stage": "publisher_access",
            "error_type": "AuthenticationRequired",
            "detail": "Transient retry reached an authentication page; no terms parsed.",
        })

    should_parse = bool(text) and publishers.should_parse_entity_terms(
        family=family,
        explicit_parse_flag=True,
        text=text,
        url=final_url,
        organization_no=src.organization_no,
        legal_name=src.legal_name,
        trade_name=src.trade_name,
    )
    if should_parse:
        parser_status += ":entity_scoped"
    elif family != "direct":
        parser_status += ":publisher_retry_unresolved"

    doc_start, doc_end = (
        base.detect_effective_dates(text) if text else (None, None)
    )
    version = base.detect_source_version(text, final_url) if text else None
    blob_relpath = base.write_blob(artifact_root / "blobs", digest, raw)

    snapshot = {
        "requested_url": requested_url,
        "final_url": final_url,
        "fetched_at": now,
        "http_status": resp.status_code,
        "content_type": ctype,
        "byte_count": len(raw),
        "sha256": digest,
        "blob_relpath": blob_relpath,
        "parser_status": parser_status,
        "title": title,
        "source_version": version,
        "effective_from": doc_start,
        "effective_to": doc_end,
    }

    terms = []
    if should_parse and not auth_page:
        for term in production.extract_terms_production(text, final_url):
            terms.append((0, term))

    return {
        "source": src,
        "snapshots": [snapshot],
        "terms": terms,
        "errors": errors,
        "retry_status": "RECOVERED",
        "parser_version": PARSER_VERSION,
    }


def execute(
    db_path: Path,
    artifact_root: Path,
    *,
    timeout: int = 45,
    max_bytes: int = 50_000_000,
    limit: int = 0,
) -> dict[str, Any]:
    conn = base.init_db(db_path)
    targets = collect_targets(conn, limit=limit)
    stats = {
        "targets": len(targets),
        "recovered": 0,
        "failed": 0,
        "snapshots_added_or_reobserved": 0,
        "terms_generated": 0,
        "retry_errors_recorded": 0,
        "reason_counts": {},
    }

    for target in targets:
        for reason in target["reasons"]:
            stats["reason_counts"][reason] = (
                stats["reason_counts"].get(reason, 0) + 1
            )

        result = retry_one(
            target,
            artifact_root,
            timeout=timeout,
            max_bytes=max_bytes,
        )
        base.persist_crawl_result(conn, result, artifact_root)
        if result["retry_status"] == "RECOVERED":
            stats["recovered"] += 1
            stats["snapshots_added_or_reobserved"] += len(result["snapshots"])
            stats["terms_generated"] += len(result["terms"])
        else:
            stats["failed"] += 1
        stats["retry_errors_recorded"] += len(result["errors"])

    conn.close()
    return stats


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--artifact-root", required=True)
    p.add_argument("--timeout", type=int, default=45)
    p.add_argument("--max-bytes", type=int, default=50_000_000)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--report")
    args = p.parse_args()

    stats = execute(
        Path(args.db),
        Path(args.artifact_root),
        timeout=args.timeout,
        max_bytes=args.max_bytes,
        limit=args.limit,
    )
    payload = json.dumps(stats, indent=2, sort_keys=True) + "\n"
    print(payload, end="")
    if args.report:
        Path(args.report).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
