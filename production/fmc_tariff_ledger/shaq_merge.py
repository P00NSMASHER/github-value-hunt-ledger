#!/usr/bin/env python3
"""Merge compact SHAQ route-crawl shard databases without raw blobs."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import shaq_route_crawl


def merge_one(dst: sqlite3.Connection, src_path: Path) -> dict:
    src = sqlite3.connect(src_path)
    src.row_factory = sqlite3.Row
    run_map: dict[int, int] = {}
    page_map: dict[int, int] = {}
    stats = {"runs": 0, "pages": 0, "rates": 0}

    for row in src.execute("SELECT * FROM shaq_runs ORDER BY id"):
        cur = dst.execute(
            """INSERT INTO shaq_runs(
                 started_at, finished_at, endpoint, server_name, server_version,
                 parser_version, status, stats_json
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row["started_at"], row["finished_at"], row["endpoint"],
                row["server_name"], row["server_version"], row["parser_version"],
                row["status"], row["stats_json"],
            ),
        )
        run_map[row["id"]] = int(cur.lastrowid)
        stats["runs"] += 1

    for row in src.execute("SELECT * FROM shaq_route_pages ORDER BY id"):
        new_run = run_map.get(row["run_id"])
        dst.execute(
            """INSERT OR IGNORE INTO shaq_route_pages(
                 run_id, url, fetched_at, http_status, content_type, byte_count,
                 sha256, blob_relpath, page_title, page_heading, parser_status, lastmod
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                new_run, row["url"], row["fetched_at"], row["http_status"],
                row["content_type"], row["byte_count"], row["sha256"],
                row["blob_relpath"], row["page_title"], row["page_heading"],
                row["parser_status"], row["lastmod"],
            ),
        )
        found = dst.execute(
            "SELECT id FROM shaq_route_pages WHERE url=? AND sha256=?",
            (row["url"], row["sha256"]),
        ).fetchone()
        assert found
        page_map[row["id"]] = int(found[0])
        stats["pages"] += 1

    # Identity maps/classifications/authorizations are usually empty in crawl shards,
    # but merge them without granting new authority.
    for row in src.execute("SELECT * FROM carrier_identity_map ORDER BY id"):
        dst.execute(
            """INSERT OR IGNORE INTO carrier_identity_map(
                 carrier_raw_pattern, carrier_normalized, fmc_organization_no,
                 mapping_method, confidence, reviewed, evidence, created_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            tuple(row[k] for k in (
                "carrier_raw_pattern", "carrier_normalized", "fmc_organization_no",
                "mapping_method", "confidence", "reviewed", "evidence", "created_at",
            )),
        )

    for row in src.execute("SELECT * FROM dataset_authorizations ORDER BY id"):
        dst.execute(
            """INSERT OR IGNORE INTO dataset_authorizations(
                 dataset_key, authorization_scope, asserted_by, asserted_at, evidence_note
               ) VALUES (?, ?, ?, ?, ?)""",
            tuple(row[k] for k in (
                "dataset_key", "authorization_scope", "asserted_by",
                "asserted_at", "evidence_note",
            )),
        )

    for row in src.execute("SELECT * FROM shaq_source_classification ORDER BY id"):
        dst.execute(
            """INSERT OR IGNORE INTO shaq_source_classification(
                 dataset_key, match_field, source_pattern, rate_kind,
                 classification_method, reviewed, evidence, created_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            tuple(row[k] for k in (
                "dataset_key", "match_field", "source_pattern", "rate_kind",
                "classification_method", "reviewed", "evidence", "created_at",
            )),
        )

    rate_cols = [
        "origin_query", "destination_query", "origin_raw", "destination_raw",
        "carrier_raw", "carrier_normalized", "fmc_organization_no",
        "fmc_identity_status", "service_type", "container_type", "amount_value",
        "currency", "valid_from", "valid_to", "rate_basis", "transit_time",
        "source_url", "rate_kind", "source_label", "source_contract_reference",
        "evidence_excerpt", "raw_record_json", "parser_confidence",
        "parser_version", "created_at",
    ]
    placeholders = ",".join("?" for _ in range(2 + len(rate_cols)))
    columns = "query_id,route_page_id," + ",".join(rate_cols)
    for row in src.execute("SELECT * FROM shaq_rates ORDER BY id"):
        page_id = page_map.get(row["route_page_id"]) if row["route_page_id"] else None
        before = dst.total_changes
        dst.execute(
            f"INSERT OR IGNORE INTO shaq_rates({columns}) VALUES ({placeholders})",
            (None, page_id, *(row[col] for col in rate_cols)),
        )
        stats["rates"] += dst.total_changes - before

    dst.commit()
    src.close()
    return stats


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input-root", required=True)
    p.add_argument("--db", required=True)
    p.add_argument("--summary")
    args = p.parse_args()

    inputs = sorted(Path(args.input_root).rglob("shaq_routes.sqlite"))
    if not inputs:
        raise SystemExit("no shaq_routes.sqlite shard databases found")

    dst = shaq_route_crawl.init_db(Path(args.db))
    total = {"shards": len(inputs), "runs": 0, "pages": 0, "rates": 0}
    for path in inputs:
        delta = merge_one(dst, path)
        for key in ("runs", "pages", "rates"):
            total[key] += delta[key]

    total.update({
        "merged_route_pages": dst.execute(
            "SELECT COUNT(*) FROM shaq_route_pages"
        ).fetchone()[0],
        "merged_rates": dst.execute("SELECT COUNT(*) FROM shaq_rates").fetchone()[0],
        "distinct_lanes": dst.execute(
            """SELECT COUNT(DISTINCT origin_raw || '->' || destination_raw)
               FROM shaq_rates"""
        ).fetchone()[0],
        "distinct_carriers": dst.execute(
            "SELECT COUNT(DISTINCT carrier_raw) FROM shaq_rates"
        ).fetchone()[0],
        "validity_covered_rates": dst.execute(
            "SELECT COUNT(*) FROM shaq_rates WHERE valid_from IS NOT NULL OR valid_to IS NOT NULL"
        ).fetchone()[0],
        "authority_ready": dst.execute(
            """SELECT COUNT(*) FROM shaq_rate_authority_view
               WHERE authority_readiness='AUTHORITY_READY'"""
        ).fetchone()[0],
        "benchmark_only": dst.execute(
            """SELECT COUNT(*) FROM shaq_rate_authority_view
               WHERE authority_readiness='BENCHMARK_ONLY'"""
        ).fetchone()[0],
    })
    dst.close()

    payload = json.dumps(total, indent=2, sort_keys=True) + "\n"
    print(payload, end="")
    if args.summary:
        Path(args.summary).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
