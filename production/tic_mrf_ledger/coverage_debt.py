#!/usr/bin/env python3
"""Measure TiC universe coverage debt without conflating discovery with authority."""

from __future__ import annotations

import argparse
import json
import sqlite3
import urllib.parse
from pathlib import Path
from typing import Any


def host_of(url: str | None) -> str:
    if not url:
        return "(none)"
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return "(invalid)"


def build_report(conn: sqlite3.Connection) -> dict[str, Any]:
    conn.row_factory = sqlite3.Row

    source_rows = conn.execute(
        """SELECT s.source_key,s.payer_name,s.adapter,s.source_url,s.historical,
                  COUNT(DISTINCT mf.id) file_rows,
                  COUNT(DISTINCT mf.file_url) unique_files
           FROM sources s
           LEFT JOIN mrf_files mf ON mf.source_key=s.source_key
           GROUP BY s.source_key,s.payer_name,s.adapter,s.source_url,s.historical"""
    ).fetchall()

    error_by_source: dict[str, dict[str, int]] = {}
    for row in conn.execute(
        """SELECT COALESCE(source_key,'(none)') source_key,
                  stage || ':' || error_type reason,
                  COUNT(*) c
           FROM ingestion_errors
           GROUP BY source_key,reason"""
    ):
        error_by_source.setdefault(row["source_key"], {})[row["reason"]] = int(row["c"])

    no_file = []
    by_adapter: dict[str, dict[str, Any]] = {}
    host_debt: dict[str, dict[str, Any]] = {}

    for row in source_rows:
        adapter = row["adapter"]
        a = by_adapter.setdefault(adapter, {
            "sources": 0, "sources_with_files": 0, "sources_without_files": 0,
            "unique_files": 0, "error_rows": 0,
        })
        a["sources"] += 1
        a["unique_files"] += int(row["unique_files"] or 0)
        errs = error_by_source.get(row["source_key"], {})
        a["error_rows"] += sum(errs.values())

        if row["unique_files"]:
            a["sources_with_files"] += 1
            continue

        a["sources_without_files"] += 1
        host = host_of(row["source_url"])
        h = host_debt.setdefault(host, {
            "host": host, "sources_without_files": 0, "payers": set(),
            "adapters": set(), "error_rows": 0,
        })
        h["sources_without_files"] += 1
        h["payers"].add(row["payer_name"])
        h["adapters"].add(adapter)
        h["error_rows"] += sum(errs.values())
        no_file.append({
            "source_key": row["source_key"],
            "payer_name": row["payer_name"],
            "adapter": adapter,
            "source_url": row["source_url"],
            "historical": bool(row["historical"]),
            "errors": errs,
        })

    hosts = []
    for h in host_debt.values():
        hosts.append({
            **{k: v for k, v in h.items() if k not in {"payers", "adapters"}},
            "payer_count": len(h["payers"]),
            "payers": sorted(h["payers"]),
            "adapters": sorted(h["adapters"]),
        })
    hosts.sort(key=lambda x: (-x["sources_without_files"], -x["payer_count"], x["host"]))

    file_stats = {
        "rows": conn.execute("SELECT COUNT(*) FROM mrf_files").fetchone()[0],
        "unique_urls": conn.execute(
            "SELECT COUNT(DISTINCT file_url) FROM mrf_files"
        ).fetchone()[0],
        "in_network_unique_urls": conn.execute(
            "SELECT COUNT(DISTINCT file_url) FROM mrf_files WHERE file_type='in_network'"
        ).fetchone()[0],
        "allowed_amount_unique_urls": conn.execute(
            "SELECT COUNT(DISTINCT file_url) FROM mrf_files WHERE file_type='allowed_amounts'"
        ).fetchone()[0],
        "index_unique_urls": conn.execute(
            "SELECT COUNT(DISTINCT file_url) FROM mrf_files WHERE file_type='index'"
        ).fetchone()[0],
        "unresolved_rows": conn.execute(
            "SELECT COUNT(*) FROM mrf_files WHERE parse_status LIKE 'unresolved%'"
        ).fetchone()[0],
        "known_content_bytes": conn.execute(
            "SELECT COALESCE(SUM(content_length),0) FROM mrf_files"
        ).fetchone()[0],
    }

    source_total = len(source_rows)
    sources_with_files = sum(1 for row in source_rows if row["unique_files"])
    current_rows = [row for row in source_rows if not row["historical"]]
    current_with_files = sum(1 for row in current_rows if row["unique_files"])

    return {
        "sources": {
            "total": source_total,
            "with_files": sources_with_files,
            "without_files": source_total - sources_with_files,
            "coverage_pct": round(100.0 * sources_with_files / source_total, 2)
            if source_total else 0.0,
            "current_total": len(current_rows),
            "current_with_files": current_with_files,
            "current_coverage_pct": round(
                100.0 * current_with_files / len(current_rows), 2
            ) if current_rows else 0.0,
        },
        "files": file_stats,
        "by_adapter": [
            {"adapter": k, **v}
            for k, v in sorted(
                by_adapter.items(),
                key=lambda kv: (-kv[1]["sources_without_files"], kv[0]),
            )
        ],
        "unresolved_host_priority": hosts[:100],
        "sources_without_files": sorted(
            no_file,
            key=lambda x: (
                -sum(x["errors"].values()),
                x["adapter"],
                x["payer_name"],
            ),
        ),
        "errors": {
            "rows": conn.execute("SELECT COUNT(*) FROM ingestion_errors").fetchone()[0],
            "by_type": [
                {"stage": row[0], "error_type": row[1], "count": row[2]}
                for row in conn.execute(
                    """SELECT stage,error_type,COUNT(*)
                       FROM ingestion_errors
                       GROUP BY stage,error_type
                       ORDER BY COUNT(*) DESC"""
                )
            ],
        },
        "authority_boundary": {
            "universe_catalog_ready": True,
            "targeted_public_rate_extraction_ready": True,
            "public_tic_is_controlling_provider_contract": False,
            "validated_recovery_requires_contract_authority": True,
        },
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--output")
    args = p.parse_args()

    conn = sqlite3.connect(args.db)
    report = build_report(conn)
    conn.close()
    payload = json.dumps(report, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
