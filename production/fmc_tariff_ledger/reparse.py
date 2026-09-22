#!/usr/bin/env python3
"""Offline reparse of harvested FMC tariff snapshots with the current parser.

The network crawl is intentionally decoupled from parsing evolution. This tool lets a
completed shard be upgraded from immutable raw blobs without refetching public sites.

Behavior:
- raw bytes stay unchanged;
- HTML/PDF/XLSX/text extraction is cached by content hash where safe;
- shared-publisher snapshots must be entity-scoped before terms are generated;
- successfully reparsed snapshots replace legacy normalized terms;
- effective dates/source versions are refreshed from current parsing logic;
- failed reparses retain legacy direct-source terms but are marked for review.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import urllib.parse
from pathlib import Path
from typing import Any

import crawler
import publisher_adapters as publishers
import run as production


PARSER_VERSION = "fmc-ledger-v3-reparse"


def _cache_key(row: sqlite3.Row) -> tuple[str, str, str]:
    source_url = row["source_url"] or ""
    suffix = Path(urllib.parse.urlsplit(source_url).path).suffix.lower()
    return (
        row["sha256"] or "",
        (row["content_type"] or "").lower(),
        suffix,
    )


def _insert_term(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    term: crawler.ExtractedTerm,
) -> None:
    conn.execute(
        """INSERT INTO terms(
             snapshot_id, entity_class, organization_no, legal_name, rule_type,
             term_kind, amount_value, currency, unit, quantity_value,
             effective_from, effective_to, source_version, evidence_locator,
             evidence_excerpt, confidence, parser_version, created_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            row["snapshot_id"],
            row["entity_class"],
            row["organization_no"],
            row["legal_name"],
            term.rule_type,
            term.term_kind,
            term.amount_value,
            term.currency,
            term.unit,
            term.quantity_value,
            term.effective_from,
            term.effective_to,
            term.source_version,
            term.evidence_locator,
            term.evidence_excerpt,
            term.confidence,
            PARSER_VERSION,
            crawler.utcnow(),
        ),
    )


def reparse(
    db_path: Path,
    artifact_root: Path,
    *,
    limit: int = 0,
    dry_run: bool = False,
) -> dict[str, Any]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
          s.id snapshot_id,
          s.sha256,
          s.blob_relpath,
          s.content_type,
          COALESCE(s.final_url, s.requested_url) source_url,
          s.parser_status,
          s.effective_from old_effective_from,
          s.effective_to old_effective_to,
          s.source_version old_source_version,
          e.entity_class,
          e.organization_no,
          e.legal_name,
          e.trade_name,
          tl.canonical_url tariff_location
        FROM snapshots s
        JOIN tariff_locations tl ON tl.id=s.tariff_location_id
        JOIN entities e ON e.id=tl.entity_id
        WHERE s.sha256 IS NOT NULL
          AND s.blob_relpath IS NOT NULL
        ORDER BY s.id
        """
    ).fetchall()
    if limit:
        rows = rows[:limit]

    stats = {
        "snapshots_examined": 0,
        "snapshots_reparsed": 0,
        "snapshots_skipped_shared_generic": 0,
        "snapshots_auth_skipped": 0,
        "missing_blobs": 0,
        "parse_failures": 0,
        "unique_blob_parses": 0,
        "terms_before": conn.execute("SELECT COUNT(*) FROM terms").fetchone()[0],
        "terms_deleted_for_reparse": 0,
        "terms_inserted": 0,
        "effective_dates_added": 0,
        "effective_dates_changed": 0,
        "source_versions_added": 0,
        "source_versions_changed": 0,
    }

    # Cache only extraction; effective/version detection may depend on the URL.
    text_cache: dict[tuple[str, str, str], tuple[str, str]] = {}

    for row in rows:
        stats["snapshots_examined"] += 1
        blob_rel = row["blob_relpath"]
        blob = artifact_root / blob_rel
        if not blob.exists():
            stats["missing_blobs"] += 1
            continue

        key = _cache_key(row)
        cached = text_cache.get(key)
        if cached is None:
            try:
                raw = blob.read_bytes()
                text, _, parse_kind, _ = crawler.extract_text_and_links(
                    raw,
                    row["content_type"] or "",
                    row["source_url"],
                )
            except Exception:
                stats["parse_failures"] += 1
                if not dry_run:
                    conn.execute(
                        """UPDATE snapshots
                           SET parser_status=parser_status || ':offline_reparse_failed'
                           WHERE id=?""",
                        (row["snapshot_id"],),
                    )
                continue
            text_cache[key] = (text, parse_kind)
            stats["unique_blob_parses"] += 1
        else:
            text, parse_kind = cached

        family = publishers.family_for(row["tariff_location"])
        if publishers.auth_or_login_page(text, row["source_url"]):
            stats["snapshots_auth_skipped"] += 1
            if not dry_run:
                old_count = conn.execute(
                    "SELECT COUNT(*) FROM terms WHERE snapshot_id=?",
                    (row["snapshot_id"],),
                ).fetchone()[0]
                if old_count:
                    conn.execute(
                        "DELETE FROM terms WHERE snapshot_id=?",
                        (row["snapshot_id"],),
                    )
                    stats["terms_deleted_for_reparse"] += old_count
                conn.execute(
                    """UPDATE snapshots
                       SET parser_status=parser_status || ':offline_auth_skipped'
                       WHERE id=?""",
                    (row["snapshot_id"],),
                )
            continue

        if family != "direct" and not publishers.entity_scoped_text(
            text,
            row["organization_no"],
            row["legal_name"],
            row["trade_name"] or "",
        ):
            stats["snapshots_skipped_shared_generic"] += 1
            if not dry_run:
                old_count = conn.execute(
                    "SELECT COUNT(*) FROM terms WHERE snapshot_id=?",
                    (row["snapshot_id"],),
                ).fetchone()[0]
                if old_count:
                    conn.execute(
                        "DELETE FROM terms WHERE snapshot_id=?",
                        (row["snapshot_id"],),
                    )
                    stats["terms_deleted_for_reparse"] += old_count
                conn.execute(
                    """UPDATE snapshots
                       SET parser_status=parser_status || ':offline_shared_generic'
                       WHERE id=?""",
                    (row["snapshot_id"],),
                )
            continue

        effective_from, effective_to = crawler.detect_effective_dates(text)
        source_version = crawler.detect_source_version(text, row["source_url"])
        terms = production.extract_terms_production(text, row["source_url"])

        if effective_from and not row["old_effective_from"]:
            stats["effective_dates_added"] += 1
        elif effective_from and effective_from != row["old_effective_from"]:
            stats["effective_dates_changed"] += 1

        if source_version and not row["old_source_version"]:
            stats["source_versions_added"] += 1
        elif source_version and source_version != row["old_source_version"]:
            stats["source_versions_changed"] += 1

        stats["snapshots_reparsed"] += 1
        if dry_run:
            stats["terms_inserted"] += len(terms)
            continue

        old_count = conn.execute(
            "SELECT COUNT(*) FROM terms WHERE snapshot_id=?",
            (row["snapshot_id"],),
        ).fetchone()[0]
        conn.execute("DELETE FROM terms WHERE snapshot_id=?", (row["snapshot_id"],))
        stats["terms_deleted_for_reparse"] += old_count

        conn.execute(
            """UPDATE snapshots
               SET effective_from=?, effective_to=?, source_version=?,
                   parser_status=?
               WHERE id=?""",
            (
                effective_from,
                effective_to,
                source_version,
                f"parsed:{parse_kind}:offline_reparse_v3",
                row["snapshot_id"],
            ),
        )
        before = conn.total_changes
        for term in terms:
            _insert_term(conn, row, term)
        stats["terms_inserted"] += conn.total_changes - before

        if stats["snapshots_reparsed"] % 1000 == 0:
            conn.commit()

    if dry_run:
        conn.rollback()
        stats["terms_after"] = stats["terms_before"]
    else:
        conn.commit()
        stats["terms_after"] = conn.execute("SELECT COUNT(*) FROM terms").fetchone()[0]

    conn.close()
    return stats


def main() -> int:
    p = argparse.ArgumentParser(description="Offline reparse FMC tariff shard")
    p.add_argument("--db", required=True)
    p.add_argument("--artifact-root", required=True)
    p.add_argument("--report")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    stats = reparse(
        Path(args.db),
        Path(args.artifact_root),
        limit=args.limit,
        dry_run=args.dry_run,
    )
    payload = json.dumps(stats, indent=2, sort_keys=True) + "\n"
    print(payload, end="")
    if args.report:
        Path(args.report).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
