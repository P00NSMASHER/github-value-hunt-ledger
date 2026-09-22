#!/usr/bin/env python3
"""Post-crawl evidence revalidation for shared FMC tariff publishers.

This is designed both for current-run cleanup and future defense in depth.
For any tariff location now known to be a shared publisher, normalized terms are
retained only when the exact snapshot contains entity-specific evidence (FMC org
number or sufficiently distinctive legal/trade-name tokens). Raw bytes are never
deleted.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import crawler
import publisher_adapters as publishers


BOGUS_RULE_IDS = {"rule:no", "rule:number", "rule:nos"}


def revalidate(db_path: Path, artifact_root: Path, dry_run: bool = False) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    stats = {
        "shared_snapshots_examined": 0,
        "shared_snapshots_validated_entity_scoped": 0,
        "shared_snapshots_terms_quarantined": 0,
        "terms_quarantined_shared_generic": 0,
        "bogus_rule_terms_removed": 0,
        "missing_blobs": 0,
        "parse_failures": 0,
    }

    bogus_count = conn.execute(
        "SELECT COUNT(*) FROM terms WHERE lower(rule_type) IN ('rule:no','rule:number','rule:nos')"
    ).fetchone()[0]
    stats["bogus_rule_terms_removed"] = bogus_count
    if not dry_run:
        conn.execute(
            "DELETE FROM terms WHERE lower(rule_type) IN ('rule:no','rule:number','rule:nos')"
        )

    rows = conn.execute(
        """
        SELECT DISTINCT
          s.id snapshot_id,
          s.blob_relpath,
          s.content_type,
          COALESCE(s.final_url, s.requested_url) source_url,
          s.parser_status,
          e.organization_no,
          e.legal_name,
          e.trade_name,
          tl.canonical_url tariff_location
        FROM snapshots s
        JOIN tariff_locations tl ON tl.id = s.tariff_location_id
        JOIN entities e ON e.id = tl.entity_id
        WHERE EXISTS (SELECT 1 FROM terms t WHERE t.snapshot_id = s.id)
        """
    ).fetchall()

    for row in rows:
        family = publishers.family_for(row["tariff_location"])
        if family == "direct":
            continue

        stats["shared_snapshots_examined"] += 1
        rel = row["blob_relpath"]
        if not rel:
            stats["missing_blobs"] += 1
            continue
        blob = artifact_root / rel
        if not blob.exists():
            stats["missing_blobs"] += 1
            continue

        try:
            raw = blob.read_bytes()
            text, _, _, _ = crawler.extract_text_and_links(
                raw,
                row["content_type"] or "",
                row["source_url"],
            )
        except Exception:
            stats["parse_failures"] += 1
            continue

        entity_scoped = (
            not publishers.auth_or_login_page(text, row["source_url"])
            and publishers.entity_scoped_text(
                text,
                row["organization_no"],
                row["legal_name"],
                row["trade_name"] or "",
            )
        )
        if entity_scoped:
            stats["shared_snapshots_validated_entity_scoped"] += 1
            continue

        term_count = conn.execute(
            "SELECT COUNT(*) FROM terms WHERE snapshot_id=?", (row["snapshot_id"],)
        ).fetchone()[0]
        if term_count == 0:
            continue

        stats["shared_snapshots_terms_quarantined"] += 1
        stats["terms_quarantined_shared_generic"] += term_count
        if not dry_run:
            conn.execute("DELETE FROM terms WHERE snapshot_id=?", (row["snapshot_id"],))
            conn.execute(
                """
                UPDATE snapshots
                SET parser_status = parser_status || ':postvalidated_publisher_generic'
                WHERE id=?
                """,
                (row["snapshot_id"],),
            )
            conn.execute(
                """
                INSERT INTO crawl_errors
                  (tariff_location_id, url, occurred_at, stage, error_type, detail)
                SELECT tariff_location_id, ?, ?, 'postvalidate',
                       'GenericSharedPublisherEvidence',
                       'Normalized terms quarantined because snapshot did not contain entity-specific FMC organization/name evidence.'
                FROM snapshots WHERE id=?
                """,
                (row["source_url"], crawler.utcnow(), row["snapshot_id"]),
            )

    if dry_run:
        conn.rollback()
    else:
        conn.commit()

    stats["remaining_terms"] = conn.execute("SELECT COUNT(*) FROM terms").fetchone()[0]
    conn.close()
    return stats


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--artifact-root", required=True)
    p.add_argument("--report")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    stats = revalidate(
        Path(args.db),
        Path(args.artifact_root),
        dry_run=args.dry_run,
    )
    payload = json.dumps(stats, indent=2, sort_keys=True) + "\n"
    print(payload, end="")
    if args.report:
        Path(args.report).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
