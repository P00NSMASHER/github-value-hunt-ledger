#!/usr/bin/env python3
"""Build an actionable gap report from an FMC tariff ledger."""

from __future__ import annotations

import argparse
import json
import sqlite3
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path


def host_of(url: str | None) -> str:
    if not url:
        return "(none)"
    try:
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
    except ValueError:
        return "(invalid)"
    return host.removeprefix("www.") or "(none)"


def build_report(db_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    domains: dict[str, dict] = {}

    def get_domain(host: str) -> dict:
        if host not in domains:
            domains[host] = {
                "host": host,
                "entity_ids": set(),
                "tariff_location_ids": set(),
                "snapshot_ids": set(),
                "snapshot_hashes": set(),
                "term_count": 0,
                "effective_dated_term_count": 0,
                "errors": Counter(),
                "unresolved_entity_ids": set(),
                "auth_entity_ids": set(),
            }
        return domains[host]

    loc_rows = conn.execute(
        """SELECT tl.id tariff_location_id, tl.entity_id, tl.canonical_url
           FROM tariff_locations tl"""
    ).fetchall()
    loc_host: dict[int, str] = {}
    for row in loc_rows:
        host = host_of(row["canonical_url"])
        loc_host[int(row["tariff_location_id"])] = host
        d = get_domain(host)
        d["entity_ids"].add(int(row["entity_id"]))
        d["tariff_location_ids"].add(int(row["tariff_location_id"]))

    snapshot_rows = conn.execute(
        """SELECT id, tariff_location_id, sha256 FROM snapshots"""
    ).fetchall()
    snap_host: dict[int, str] = {}
    for row in snapshot_rows:
        host = loc_host.get(int(row["tariff_location_id"]), "(unknown)")
        snap_host[int(row["id"])] = host
        d = get_domain(host)
        d["snapshot_ids"].add(int(row["id"]))
        if row["sha256"]:
            d["snapshot_hashes"].add(row["sha256"])

    for row in conn.execute(
        """SELECT t.snapshot_id,
                  CASE WHEN COALESCE(t.effective_from, s.effective_from) IS NOT NULL
                       THEN 1 ELSE 0 END AS effective_dated
           FROM terms t
           JOIN snapshots s ON s.id=t.snapshot_id"""
    ):
        host = snap_host.get(int(row["snapshot_id"]), "(unknown)")
        d = get_domain(host)
        d["term_count"] += 1
        d["effective_dated_term_count"] += int(row["effective_dated"])

    for row in conn.execute(
        """SELECT ce.tariff_location_id, ce.url, ce.stage, ce.error_type,
                  tl.entity_id
           FROM crawl_errors ce
           LEFT JOIN tariff_locations tl ON tl.id=ce.tariff_location_id"""
    ):
        if row["tariff_location_id"] is not None:
            host = loc_host.get(int(row["tariff_location_id"]), host_of(row["url"]))
        else:
            host = host_of(row["url"])
        d = get_domain(host)
        reason = f"{row['stage']}:{row['error_type']}"
        d["errors"][reason] += 1
        if row["entity_id"] is not None:
            entity_id = int(row["entity_id"])
            if row["stage"] == "publisher_adapter" and row["error_type"] == "EntityTariffNotResolved":
                d["unresolved_entity_ids"].add(entity_id)
            if row["stage"] == "publisher_access" and row["error_type"] == "AuthenticationRequired":
                d["auth_entity_ids"].add(entity_id)

    domain_rows = []
    for host, d in domains.items():
        entities = len(d["entity_ids"])
        terms = d["term_count"]
        effective = d["effective_dated_term_count"]
        row = {
            "host": host,
            "entities": entities,
            "tariff_locations": len(d["tariff_location_ids"]),
            "snapshots": len(d["snapshot_ids"]),
            "unique_snapshot_hashes": len(d["snapshot_hashes"]),
            "terms": terms,
            "effective_dated_terms": effective,
            "effective_date_coverage_pct": round((100.0 * effective / terms), 2) if terms else 0.0,
            "unresolved_entities": len(d["unresolved_entity_ids"]),
            "authentication_required_entities": len(d["auth_entity_ids"]),
            "http_errors": d["errors"].get("fetch:HTTPError", 0),
            "ssl_errors": d["errors"].get("fetch:SSLError", 0),
            "connection_errors": (
                d["errors"].get("fetch:ConnectionError", 0)
                + d["errors"].get("fetch:ConnectTimeout", 0)
                + d["errors"].get("fetch:ReadTimeout", 0)
            ),
            "parse_errors": sum(v for k, v in d["errors"].items() if k.startswith("parse:")),
            "errors": dict(d["errors"].most_common()),
        }
        domain_rows.append(row)

    priority = sorted(
        [
            r for r in domain_rows
            if r["unresolved_entities"]
            or r["authentication_required_entities"]
            or r["http_errors"]
            or r["parse_errors"]
        ],
        key=lambda r: (
            -r["unresolved_entities"],
            -r["authentication_required_entities"],
            -r["http_errors"],
            -r["entities"],
            r["host"],
        ),
    )

    rules = []
    for row in conn.execute(
        """SELECT t.rule_type,
                  COUNT(*) terms,
                  SUM(CASE WHEN COALESCE(t.effective_from, s.effective_from) IS NOT NULL
                           THEN 1 ELSE 0 END) effective_dated
           FROM terms t
           JOIN snapshots s ON s.id=t.snapshot_id
           GROUP BY t.rule_type
           ORDER BY terms DESC, t.rule_type"""
    ):
        count = int(row["terms"])
        effective = int(row["effective_dated"] or 0)
        rules.append({
            "rule_type": row["rule_type"],
            "terms": count,
            "effective_dated_terms": effective,
            "effective_date_coverage_pct": round(100.0 * effective / count, 2) if count else 0.0,
        })

    date_basis = []
    try:
        for row in conn.execute(
            """SELECT date_basis, COUNT(*) c
               FROM carrier_rule_effective_ledger
               GROUP BY date_basis ORDER BY c DESC"""
        ):
            date_basis.append([row["date_basis"], int(row["c"])])
    except sqlite3.OperationalError:
        pass

    overall = {
        "entities": conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
        "tariff_locations": conn.execute("SELECT COUNT(*) FROM tariff_locations").fetchone()[0],
        "snapshots": conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0],
        "unique_snapshot_hashes": conn.execute(
            "SELECT COUNT(DISTINCT sha256) FROM snapshots WHERE sha256 IS NOT NULL"
        ).fetchone()[0],
        "terms": conn.execute("SELECT COUNT(*) FROM terms").fetchone()[0],
        "errors": conn.execute("SELECT COUNT(*) FROM crawl_errors").fetchone()[0],
    }

    conn.close()
    return {
        "overall": overall,
        "priority_basis": [
            "unresolved_entities DESC",
            "authentication_required_entities DESC",
            "http_errors DESC",
            "entities DESC",
            "host ASC",
        ],
        "publisher_priority_queue": priority[:100],
        "all_domains": sorted(domain_rows, key=lambda r: (-r["entities"], r["host"])),
        "rule_coverage": rules,
        "date_basis": date_basis,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--output")
    args = p.parse_args()
    report = build_report(Path(args.db))
    payload = json.dumps(report, indent=2, sort_keys=False) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
