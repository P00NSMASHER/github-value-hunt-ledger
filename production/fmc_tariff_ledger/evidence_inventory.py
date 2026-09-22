#!/usr/bin/env python3
"""Build a compact inventory of raw FMC evidence across shard artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Any


SHARD_RE = re.compile(r"fmc-metadata-shard-(\d+)")


def shard_id_for(path: Path) -> int | None:
    for part in path.parts:
        match = SHARD_RE.fullmatch(part)
        if match:
            return int(match.group(1))
    return None


def build_inventory(root: Path, source_run_id: str | None = None) -> dict[str, Any]:
    by_hash: dict[str, dict[str, Any]] = {}
    shard_blob_bytes_sum = 0
    shard_count = 0

    for db_path in sorted(root.rglob("ledger.sqlite")):
        shard = shard_id_for(db_path)
        if shard is None:
            continue
        shard_count += 1
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT
                 sha256,
                 MIN(blob_relpath) blob_relpath,
                 MAX(byte_count) byte_count,
                 GROUP_CONCAT(DISTINCT content_type) content_types,
                 COUNT(*) reference_count,
                 MIN(fetched_at) first_observed_at,
                 MAX(fetched_at) last_observed_at,
                 MIN(requested_url) example_url
               FROM snapshots
               WHERE sha256 IS NOT NULL
               GROUP BY sha256"""
        ).fetchall()
        conn.close()

        shard_blob_bytes_sum += sum(int(row["byte_count"] or 0) for row in rows)
        for row in rows:
            digest = row["sha256"]
            entry = by_hash.setdefault(
                digest,
                {
                    "sha256": digest,
                    "byte_count": int(row["byte_count"] or 0),
                    "content_types": set(),
                    "reference_count": 0,
                    "source_shards": set(),
                    "source_artifacts": set(),
                    "blob_relpaths": set(),
                    "first_observed_at": row["first_observed_at"],
                    "last_observed_at": row["last_observed_at"],
                    "example_urls": [],
                },
            )
            entry["byte_count"] = max(
                entry["byte_count"],
                int(row["byte_count"] or 0),
            )
            entry["reference_count"] += int(row["reference_count"] or 0)
            entry["source_shards"].add(shard)
            entry["source_artifacts"].add(f"fmc-shard-{shard}")
            if row["blob_relpath"]:
                entry["blob_relpaths"].add(row["blob_relpath"])
            for content_type in (row["content_types"] or "").split(","):
                content_type = content_type.strip()
                if content_type:
                    entry["content_types"].add(content_type)
            first = row["first_observed_at"]
            last = row["last_observed_at"]
            if first and (
                not entry["first_observed_at"]
                or first < entry["first_observed_at"]
            ):
                entry["first_observed_at"] = first
            if last and (
                not entry["last_observed_at"]
                or last > entry["last_observed_at"]
            ):
                entry["last_observed_at"] = last
            url = row["example_url"]
            if url and url not in entry["example_urls"] and len(entry["example_urls"]) < 3:
                entry["example_urls"].append(url)

    blobs = []
    for digest, entry in sorted(by_hash.items()):
        blobs.append({
            "sha256": digest,
            "byte_count": entry["byte_count"],
            "content_types": sorted(entry["content_types"]),
            "reference_count": entry["reference_count"],
            "source_shards": sorted(entry["source_shards"]),
            "source_artifacts": sorted(entry["source_artifacts"]),
            "blob_relpaths": sorted(entry["blob_relpaths"]),
            "first_observed_at": entry["first_observed_at"],
            "last_observed_at": entry["last_observed_at"],
            "example_urls": entry["example_urls"],
        })

    unique_blob_bytes = sum(item["byte_count"] for item in blobs)
    cross_shard_duplicate_bytes = max(
        0,
        shard_blob_bytes_sum - unique_blob_bytes,
    )
    return {
        "source_workflow_run_id": source_run_id,
        "metadata_shards_found": shard_count,
        "unique_blob_count": len(blobs),
        "unique_blob_bytes": unique_blob_bytes,
        "shard_unique_blob_bytes_sum": shard_blob_bytes_sum,
        "cross_shard_duplicate_bytes": cross_shard_duplicate_bytes,
        "cross_shard_duplicate_pct": round(
            100.0 * cross_shard_duplicate_bytes / shard_blob_bytes_sum,
            2,
        ) if shard_blob_bytes_sum else 0.0,
        "raw_artifact_name_pattern": "fmc-shard-{shard}",
        "raw_bytes_embedded_here": False,
        "blobs": blobs,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input-root", required=True)
    p.add_argument("--source-run-id")
    p.add_argument("--output")
    args = p.parse_args()

    result = build_inventory(
        Path(args.input_root),
        source_run_id=args.source_run_id,
    )
    payload = json.dumps(result, indent=2, sort_keys=False) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
