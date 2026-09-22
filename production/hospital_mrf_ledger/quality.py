#!/usr/bin/env python3
"""Quality and coverage report for the Hospital Price Transparency ledger."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def scalar(conn: sqlite3.Connection, sql: str, params=()) -> int:
    return int(conn.execute(sql, params).fetchone()[0])


def build_report(conn: sqlite3.Connection) -> dict:
    formats = {
        row[0] or "unknown": int(row[1])
        for row in conn.execute(
            "SELECT format,COUNT(*) FROM mrf_snapshots GROUP BY format ORDER BY format"
        )
    }
    versions = {
        row[0] or "missing": int(row[1])
        for row in conn.execute(
            "SELECT schema_version,COUNT(*) FROM mrf_snapshots GROUP BY schema_version ORDER BY schema_version"
        )
    }
    parser_status = {
        row[0]: int(row[1])
        for row in conn.execute(
            "SELECT parser_status,COUNT(*) FROM mrf_snapshots GROUP BY parser_status ORDER BY parser_status"
        )
    }
    return {
        "source_domains": scalar(conn, "SELECT COUNT(*) FROM source_domains"),
        "txt_snapshots": scalar(conn, "SELECT COUNT(*) FROM txt_snapshots"),
        "txt_domains_without_entries": scalar(
            conn,
            """SELECT COUNT(*) FROM source_domains s
               WHERE NOT EXISTS (SELECT 1 FROM hpt_entries e WHERE e.source_id=s.id)"""
        ),
        "unique_mrf_urls": scalar(conn, "SELECT COUNT(DISTINCT mrf_url) FROM hpt_entries"),
        "mrf_snapshots": scalar(conn, "SELECT COUNT(*) FROM mrf_snapshots"),
        "formats": formats,
        "schema_versions": versions,
        "parser_status": parser_status,
        "v3_snapshots": scalar(
            conn,
            """SELECT COUNT(*) FROM mrf_snapshots
               WHERE schema_version LIKE '3.%' OR schema_version='3.0'"""
        ),
        "confirmed_attestation_false_or_missing": scalar(
            conn,
            "SELECT COUNT(*) FROM mrf_snapshots WHERE attestation_confirmed IS NOT 1"
        ),
        "snapshots_without_type2_npi": scalar(
            conn,
            """SELECT COUNT(*) FROM mrf_snapshots m
               WHERE NOT EXISTS (
                 SELECT 1 FROM hospital_identities h
                 WHERE h.mrf_snapshot_id=m.id AND h.type_2_npi IS NOT NULL
               )"""
        ),
        "targeted_charge_rows": scalar(conn, "SELECT COUNT(*) FROM charge_rows"),
        "ingestion_errors": scalar(conn, "SELECT COUNT(*) FROM ingestion_errors"),
        "boundary": {
            "public_rates_are_benchmark_only": True,
            "verified_controlling_rate": False,
            "verified_claim_applicability": False,
        },
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    conn = sqlite3.connect(Path(args.db))
    report = build_report(conn)
    conn.close()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for key, value in report.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
