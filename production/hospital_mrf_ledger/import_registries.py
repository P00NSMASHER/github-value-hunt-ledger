#!/usr/bin/env python3
"""Import pinned GitHub hospital-price-transparency registries.

This stage is intentionally separate from direct cms-hpt.txt crawling:
- direct hospital pointer snapshots remain first-party observations;
- the 2026 tracker is a secondary current discovery/compliance registry;
- the TPAFS file is a historical 2022 discovery registry.

No contact names, contact emails, or phone values are persisted by this importer.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sqlite3
from pathlib import Path
from typing import Any

import requests

import catalog


TRACKER_REPO = "anthonyisnotadev/cms-hpt-tracker"
TRACKER_REVISION = "27c08db25896d765845f9ff6827da7f96ee66b04"
TRACKER_COMPLIANCE_PATH = "data/hpt-audit/compliance.csv"
TRACKER_ROSTER_PATH = "cms_data/hpt/roster.json"

TPAFS_REPO = "TPAFS/transparency-data"
TPAFS_REVISION = "8baae985b3d08380305c93091ad815e4cf57b83f"
TPAFS_PATH = "price_transparency/hospitals/machine_readable_links.csv"

USER_AGENT = (
    "RecoveryWorks-Hospital-MRF-Registry/1.0 "
    "(public GitHub hospital price-transparency research)"
)


def raw_github_url(repository: str, revision: str, source_path: str) -> str:
    return f"https://raw.githubusercontent.com/{repository}/{revision}/{source_path}"


def fetch_bytes(repository: str, revision: str, source_path: str, timeout: int = 60) -> bytes:
    url = raw_github_url(repository, revision, source_path)
    resp = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
    )
    resp.raise_for_status()
    return resp.content


def persist_registry_source(
    conn: sqlite3.Connection,
    root: Path,
    *,
    source_key: str,
    repository: str,
    revision: str,
    source_path: str,
    raw: bytes,
    upstream_license: str,
    evidence_class: str,
) -> int:
    digest, rel = catalog.store_bytes(root, raw)
    conn.execute(
        """INSERT OR IGNORE INTO registry_sources(
             source_key,repository,revision,source_path,observed_at,sha256,
             byte_count,blob_relpath,upstream_license,evidence_class
           ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (
            source_key,
            repository,
            revision,
            source_path,
            catalog.utcnow(),
            digest,
            len(raw),
            rel,
            upstream_license,
            evidence_class,
        ),
    )
    row = conn.execute(
        """SELECT id FROM registry_sources
           WHERE repository=? AND revision=? AND source_path=? AND sha256=?""",
        (repository, revision, source_path, digest),
    ).fetchone()
    assert row
    return int(row[0])


def parse_csv(raw: bytes) -> list[dict[str, str]]:
    text = raw.decode("utf-8-sig", errors="replace")
    return [dict(row) for row in csv.DictReader(io.StringIO(text))]


def parse_roster(raw: bytes) -> dict[str, dict[str, Any]]:
    rows = json.loads(raw.decode("utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        ccn = str(row.get("ccn") or "").strip()
        if not ccn:
            continue
        # Deliberately omit phone; it is unnecessary for pricing/entity resolution.
        out[ccn] = {
            "ccn": ccn,
            "name": row.get("name"),
            "address": row.get("address"),
            "city": row.get("city"),
            "state": row.get("state"),
            "zip": row.get("zip"),
            "type": row.get("type"),
        }
    return out


def as_bool(value: str | None) -> int | None:
    if value is None:
        return None
    value = value.strip().lower()
    if value in {"yes", "true", "1"}:
        return 1
    if value in {"no", "false", "0"}:
        return 0
    return None


def import_tracker(
    conn: sqlite3.Connection,
    root: Path,
    *,
    timeout: int,
) -> dict[str, Any]:
    compliance_raw = fetch_bytes(
        TRACKER_REPO, TRACKER_REVISION, TRACKER_COMPLIANCE_PATH, timeout
    )
    roster_raw = fetch_bytes(
        TRACKER_REPO, TRACKER_REVISION, TRACKER_ROSTER_PATH, timeout
    )
    compliance_source_id = persist_registry_source(
        conn,
        root,
        source_key="cms-hpt-tracker-compliance",
        repository=TRACKER_REPO,
        revision=TRACKER_REVISION,
        source_path=TRACKER_COMPLIANCE_PATH,
        raw=compliance_raw,
        upstream_license=(
            "Repository LICENSE is AGPL-3.0; underlying CMS roster and hospital "
            "disclosure facts retain their own public-source provenance."
        ),
        evidence_class="national_2026_tracker",
    )
    roster_source_id = persist_registry_source(
        conn,
        root,
        source_key="cms-hpt-tracker-roster",
        repository=TRACKER_REPO,
        revision=TRACKER_REVISION,
        source_path=TRACKER_ROSTER_PATH,
        raw=roster_raw,
        upstream_license=(
            "Repository LICENSE is AGPL-3.0; roster derives from CMS Hospital "
            "General Information public data."
        ),
        evidence_class="national_2026_roster",
    )

    compliance = parse_csv(compliance_raw)
    roster = parse_roster(roster_raw)
    conn.execute(
        "DELETE FROM national_hospital_registry WHERE registry_source_id=?",
        (compliance_source_id,),
    )

    inserted = 0
    mrf_rows = 0
    pointer_rows = 0
    current_2026 = 0
    findings: dict[str, int] = {}
    versions: dict[str, int] = {}

    for row in compliance:
        ccn = (row.get("ccn") or "").strip()
        if not ccn:
            continue
        r = roster.get(ccn, {})
        hospital_name = (
            (row.get("hospital_name") or "").strip()
            or str(r.get("name") or "").strip()
            or "(unknown)"
        )
        mrf_url = (row.get("mrf_url") or "").strip() or None
        pointer_url = (row.get("pointer_url") or "").strip() or None
        updated = (row.get("mrf_last_updated") or "").strip() or None
        version = (row.get("cms_template_version") or "").strip() or None
        finding = (row.get("finding") or "").strip() or None

        conn.execute(
            """INSERT INTO national_hospital_registry(
                 registry_source_id,roster_source_id,ccn,hospital_name,address,city,
                 state,zip,hospital_type,domain,pointer_url,mrf_url,mrf_last_updated,
                 cms_template_version,finding,assessable,checked_at,evidence
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                compliance_source_id,
                roster_source_id,
                ccn,
                hospital_name,
                r.get("address"),
                (row.get("city") or "").strip() or r.get("city"),
                (row.get("state") or "").strip() or r.get("state"),
                r.get("zip"),
                (row.get("type") or "").strip() or r.get("type"),
                (row.get("domain") or "").strip() or None,
                pointer_url,
                mrf_url,
                updated,
                version,
                finding,
                as_bool(row.get("assessable")),
                (row.get("checked_at") or "").strip() or None,
                (row.get("evidence") or "").strip() or None,
            ),
        )
        inserted += 1
        mrf_rows += int(bool(mrf_url))
        pointer_rows += int(bool(pointer_url))
        current_2026 += int(bool(updated and updated.startswith("2026-")))
        if finding:
            findings[finding] = findings.get(finding, 0) + 1
        if version:
            versions[version] = versions.get(version, 0) + 1

    return {
        "rows": inserted,
        "roster_rows": len(roster),
        "rows_with_pointer": pointer_rows,
        "rows_with_mrf": mrf_rows,
        "mrf_last_updated_2026": current_2026,
        "findings": dict(sorted(findings.items(), key=lambda x: (-x[1], x[0]))),
        "template_versions": dict(sorted(versions.items(), key=lambda x: (-x[1], x[0]))),
        "revision": TRACKER_REVISION,
        "compliance_source_id": compliance_source_id,
        "roster_source_id": roster_source_id,
    }


def import_tpafs(
    conn: sqlite3.Connection,
    root: Path,
    *,
    timeout: int,
) -> dict[str, Any]:
    raw = fetch_bytes(TPAFS_REPO, TPAFS_REVISION, TPAFS_PATH, timeout)
    source_id = persist_registry_source(
        conn,
        root,
        source_key="tpafs-hospital-mrf-links",
        repository=TPAFS_REPO,
        revision=TPAFS_REVISION,
        source_path=TPAFS_PATH,
        raw=raw,
        upstream_license="CC BY-SA 4.0 data; Apache-2.0 original code.",
        evidence_class="historical_2022_registry",
    )
    rows = parse_csv(raw)
    conn.execute(
        "DELETE FROM historical_hospital_mrf_registry WHERE registry_source_id=?",
        (source_id,),
    )

    inserted = 0
    urls: set[str] = set()
    ccns: set[str] = set()
    formats: dict[str, int] = {}
    states: dict[str, int] = {}

    columns = (
        "ccn",
        "reporting_entity_name_legal",
        "reporting_entity_name_common",
        "reporting_entity_type",
        "machine_readable_url",
        "machine_readable_url_status",
        "machine_readable_page",
        "supplemental_url",
        "file_name",
        "file_format",
        "file_size",
        "meets_standard",
        "standard_issue",
        "state_or_region",
        "last_updated_date",
        "entry_date",
        "notes",
    )
    placeholders = ",".join("?" for _ in range(len(columns) + 1))
    sql = (
        "INSERT INTO historical_hospital_mrf_registry("
        "registry_source_id," + ",".join(columns) + f") VALUES({placeholders})"
    )

    for row in rows:
        values = [source_id] + [(row.get(c) or "").strip() or None for c in columns]
        conn.execute(sql, values)
        inserted += 1
        if row.get("machine_readable_url"):
            urls.add(row["machine_readable_url"].strip())
        if row.get("ccn"):
            ccns.add(row["ccn"].strip())
        fmt = (row.get("file_format") or "").strip() or "(blank)"
        formats[fmt] = formats.get(fmt, 0) + 1
        state = (row.get("state_or_region") or "").strip() or "(blank)"
        states[state] = states.get(state, 0) + 1

    return {
        "rows": inserted,
        "unique_mrf_urls": len(urls),
        "unique_ccns": len(ccns),
        "formats": dict(sorted(formats.items(), key=lambda x: (-x[1], x[0]))),
        "states": dict(sorted(states.items(), key=lambda x: (-x[1], x[0]))),
        "revision": TPAFS_REVISION,
        "source_id": source_id,
    }


def summarize(conn: sqlite3.Connection) -> dict[str, Any]:
    return {
        "registry_sources": conn.execute(
            "SELECT COUNT(*) FROM registry_sources"
        ).fetchone()[0],
        "national_hospitals": conn.execute(
            "SELECT COUNT(*) FROM national_hospital_registry"
        ).fetchone()[0],
        "national_unique_mrf_urls": conn.execute(
            """SELECT COUNT(DISTINCT mrf_url) FROM national_hospital_registry
               WHERE mrf_url IS NOT NULL AND mrf_url<>''"""
        ).fetchone()[0],
        "national_unique_pointer_urls": conn.execute(
            """SELECT COUNT(DISTINCT pointer_url) FROM national_hospital_registry
               WHERE pointer_url IS NOT NULL AND pointer_url<>''"""
        ).fetchone()[0],
        "historical_rows": conn.execute(
            "SELECT COUNT(*) FROM historical_hospital_mrf_registry"
        ).fetchone()[0],
        "historical_unique_mrf_urls": conn.execute(
            """SELECT COUNT(DISTINCT machine_readable_url)
               FROM historical_hospital_mrf_registry
               WHERE machine_readable_url IS NOT NULL
                 AND machine_readable_url<>''"""
        ).fetchone()[0],
        "combined_discovery_rows": conn.execute(
            "SELECT COUNT(*) FROM hospital_discovery_evidence"
        ).fetchone()[0],
    }


def resolve_db_path(root: Path, value: str) -> Path:
    """Match catalog.py semantics without double-prefixing an explicit out/... path."""
    db = Path(value)
    if db.is_absolute():
        return db
    if db.parts and db.parts[0] == root.name:
        return db
    return root / db


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--timeout", type=int, default=90)
    p.add_argument("--report")
    args = p.parse_args()

    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)
    db = resolve_db_path(root, args.db)
    conn = catalog.init_db(db)

    tracker = import_tracker(conn, root, timeout=args.timeout)
    tpafs = import_tpafs(conn, root, timeout=args.timeout)
    conn.commit()
    summary = summarize(conn)
    conn.close()

    result = {
        "tracker_2026": tracker,
        "tpafs_2022": tpafs,
        "ledger": summary,
        "privacy": {
            "contact_names_stored": False,
            "contact_emails_stored": False,
            "phone_values_stored": False,
        },
    }
    payload = json.dumps(result, indent=2, sort_keys=False) + "\n"
    print(payload, end="")
    if args.report:
        Path(args.report).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
