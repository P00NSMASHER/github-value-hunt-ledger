#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from common import (
    canonicalize_url,
    fetch_small,
    head_metadata,
    init_db,
    sha256_bytes,
    stable_key,
    utcnow,
    write_blob,
)
from source_registry import SourceRoot, load_registry, stable_source_bucket

TIC_RE = re.compile(
    r"(transparency|machine[-_ ]?readable|in[-_ ]?network|allowed[-_ ]?amount|"
    r"table[-_ ]?of[-_ ]?contents?|\bindex\b|\btoc\b)",
    re.I,
)
IN_NETWORK_RE = re.compile(r"in[-_ ]?network(?:[-_ ]?rates?)?", re.I)
ALLOWED_RE = re.compile(r"allowed[-_ ]?amount", re.I)
TOC_RE = re.compile(r"table[-_ ]?of[-_ ]?contents?|(?:^|[/_-])index(?:[._/-]|$)|\btoc\b", re.I)

UHC_LISTING = "https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/"


def file_kind(url: str, description: str = "") -> str:
    probe = f"{url} {description}"
    if IN_NETWORK_RE.search(probe):
        return "in_network"
    if ALLOWED_RE.search(probe):
        return "allowed_amounts"
    if TOC_RE.search(probe):
        return "table_of_contents"
    return "unknown"


def insert_error(conn, source_id: int | None, url: str, stage: str, exc: Exception | str):
    conn.execute(
        """INSERT INTO errors(source_root_id,url,occurred_at,stage,error_type,detail)
           VALUES (?,?,?,?,?,?)""",
        (
            source_id,
            url,
            utcnow(),
            stage,
            type(exc).__name__ if isinstance(exc, Exception) else stage,
            str(exc)[:4000],
        ),
    )
    conn.commit()


def source_id_for(conn: sqlite3.Connection, root: SourceRoot) -> int:
    row = conn.execute(
        "SELECT id FROM source_roots WHERE payer_name=? AND root_url=?",
        (root.payer_name, root.root_url),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"source root not persisted: {root}")
    return int(row[0])


def observe(
    conn,
    *,
    source_id: int,
    url: str,
    parent_url: str | None,
    kind: str,
    discovery_method: str,
    meta: dict,
    status: str,
    note: str = "",
    sha256: str | None = None,
    blob_relpath: str | None = None,
):
    conn.execute(
        """INSERT INTO observations
           (source_root_id,url,parent_url,observed_at,kind,discovery_method,
            http_status,content_type,content_length,etag,last_modified,sha256,
            blob_relpath,status,note)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            source_id,
            url,
            parent_url,
            utcnow(),
            kind,
            discovery_method,
            meta.get("status"),
            meta.get("content_type"),
            meta.get("content_length"),
            meta.get("etag"),
            meta.get("last_modified"),
            sha256,
            blob_relpath,
            status,
            note,
        ),
    )


def upsert_file(
    conn,
    *,
    source_id: int,
    url: str,
    kind: str,
    description: str = "",
    source_index_url: str | None = None,
    source_index_sha256: str | None = None,
    meta: dict | None = None,
    last_updated_on: str | None = None,
    schema_version: str | None = None,
) -> str:
    meta = meta or {}
    now = utcnow()
    key = stable_key(url)
    conn.execute(
        """INSERT OR IGNORE INTO files
           (file_key,source_root_id,url,kind,description,first_seen_at,last_seen_at,
            last_updated_on,schema_version,content_length,etag,last_modified,
            source_index_url,source_index_sha256,status)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            key,
            source_id,
            url,
            kind,
            description,
            now,
            now,
            last_updated_on,
            schema_version,
            meta.get("content_length"),
            meta.get("etag"),
            meta.get("last_modified"),
            source_index_url,
            source_index_sha256,
            "discovered",
        ),
    )
    conn.execute(
        """UPDATE files SET last_seen_at=?,
             kind=CASE WHEN kind='unknown' AND ?!='unknown' THEN ? ELSE kind END,
             description=CASE WHEN description='' THEN ? ELSE description END,
             content_length=COALESCE(?,content_length),
             etag=COALESCE(?,etag), last_modified=COALESCE(?,last_modified),
             last_updated_on=COALESCE(?,last_updated_on),
             schema_version=COALESCE(?,schema_version),
             source_index_url=COALESCE(?,source_index_url),
             source_index_sha256=COALESCE(?,source_index_sha256)
           WHERE file_key=?""",
        (
            now,
            kind,
            kind,
            description,
            meta.get("content_length"),
            meta.get("etag"),
            meta.get("last_modified"),
            last_updated_on,
            schema_version,
            source_index_url,
            source_index_sha256,
            key,
        ),
    )
    return key


def parse_toc(
    conn: sqlite3.Connection,
    *,
    source_id: int,
    index_url: str,
    index_sha: str,
    payload: dict,
) -> dict:
    structures = payload.get("reporting_structure")
    if not isinstance(structures, list):
        return {"is_toc": False, "plans": 0, "files": 0}

    entity_name = str(payload.get("reporting_entity_name") or "")
    entity_type = str(payload.get("reporting_entity_type") or "")
    last_updated = payload.get("last_updated_on")
    version = payload.get("version")
    cur = conn.execute(
        """INSERT OR IGNORE INTO reporting_entities
           (source_root_id,index_url,index_sha256,reporting_entity_name,
            reporting_entity_type,last_updated_on,schema_version)
           VALUES (?,?,?,?,?,?,?)""",
        (source_id, index_url, index_sha, entity_name, entity_type, last_updated, version),
    )
    row = conn.execute(
        "SELECT id FROM reporting_entities WHERE index_url=? AND index_sha256=?",
        (index_url, index_sha),
    ).fetchone()
    assert row
    entity_id = int(row[0])

    plan_count = 0
    file_count = 0
    for sidx, structure in enumerate(structures):
        if not isinstance(structure, dict):
            continue
        plan_keys: list[str] = []
        for pidx, plan in enumerate(structure.get("reporting_plans") or []):
            if not isinstance(plan, dict):
                continue
            plan_key = stable_key(
                index_sha,
                plan.get("plan_id_type"),
                plan.get("plan_id"),
                plan.get("plan_name"),
                plan.get("issuer_name"),
                pidx,
            )
            conn.execute(
                """INSERT OR IGNORE INTO plans
                   (plan_key,reporting_entity_id,plan_name,issuer_name,plan_id_type,
                    plan_id,plan_sponsor_name,plan_market_type)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    plan_key,
                    entity_id,
                    str(plan.get("plan_name") or ""),
                    str(plan.get("issuer_name") or ""),
                    str(plan.get("plan_id_type") or ""),
                    str(plan.get("plan_id") or ""),
                    str(plan.get("plan_sponsor_name") or ""),
                    str(plan.get("plan_market_type") or ""),
                ),
            )
            plan_keys.append(plan_key)
            plan_count += 1

        refs: list[tuple[str, str, str]] = []
        for ref in structure.get("in_network_files") or []:
            if isinstance(ref, dict) and ref.get("location"):
                refs.append(("in_network", str(ref.get("location")), str(ref.get("description") or "")))
        allowed = structure.get("allowed_amount_file")
        if isinstance(allowed, dict) and allowed.get("location"):
            refs.append(("allowed_amounts", str(allowed.get("location")), str(allowed.get("description") or "")))

        for kind, raw_url, description in refs:
            url = canonicalize_url(raw_url)
            if not url:
                continue
            file_key = upsert_file(
                conn,
                source_id=source_id,
                url=url,
                kind=kind,
                description=description,
                source_index_url=index_url,
                source_index_sha256=index_sha,
                last_updated_on=last_updated,
                schema_version=version,
            )
            for plan_key in plan_keys:
                conn.execute(
                    "INSERT OR IGNORE INTO file_plans(file_key,plan_key) VALUES (?,?)",
                    (file_key, plan_key),
                )
            file_count += 1
    conn.commit()
    return {"is_toc": True, "plans": plan_count, "files": file_count}


def all_urls(value) -> list[str]:
    out: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            out.extend(all_urls(item))
    elif isinstance(value, list):
        for item in value:
            out.extend(all_urls(item))
    elif isinstance(value, str):
        if value.startswith(("http://", "https://")):
            url = canonicalize_url(value)
            if url:
                out.append(url)
    return out


def html_links(raw: bytes, base_url: str) -> list[str]:
    soup = BeautifulSoup(raw, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        href = canonicalize_url(urljoin(base_url, a["href"]))
        if href and TIC_RE.search(f"{href} {a.get_text(' ', strip=True)}"):
            out.append(href)
    return list(dict.fromkeys(out))


def discover_uhc(conn, source_id: int, output_root: Path, max_index_bytes: int) -> dict:
    raw, resp = fetch_small(UHC_LISTING, timeout=60, max_bytes=max_index_bytes)
    digest = sha256_bytes(raw)
    rel = write_blob(output_root, digest, raw)
    payload = json.loads(raw)
    blobs = payload.get("blobs") if isinstance(payload, dict) else payload
    count = 0
    if isinstance(blobs, list):
        for item in blobs:
            if not isinstance(item, dict):
                continue
            url = canonicalize_url(str(item.get("downloadUrl") or item.get("url") or ""))
            if not url:
                continue
            kind = file_kind(url, str(item.get("name") or ""))
            if kind == "unknown":
                continue
            size = item.get("size") or item.get("contentLength") or item.get("content_length")
            meta = {"content_length": int(size) if str(size).isdigit() else None}
            upsert_file(
                conn,
                source_id=source_id,
                url=url,
                kind=kind,
                description=str(item.get("name") or ""),
                source_index_url=UHC_LISTING,
                source_index_sha256=digest,
                meta=meta,
            )
            count += 1
    observe(
        conn,
        source_id=source_id,
        url=UHC_LISTING,
        parent_url=None,
        kind="listing_api",
        discovery_method="uhc_api",
        meta={
            "status": resp.status_code,
            "content_type": resp.headers.get("content-type", ""),
            "content_length": len(raw),
        },
        status="parsed",
        sha256=digest,
        blob_relpath=rel,
        note=f"listed_files={count}",
    )
    conn.commit()
    return {"files": count, "snapshots": 1}


def discover_root(
    conn,
    root: SourceRoot,
    output_root: Path,
    *,
    max_depth: int,
    max_pages: int,
    max_index_bytes: int,
    head_files: int,
) -> dict:
    source_id = source_id_for(conn, root)
    if "transparency-in-coverage.uhc.com" in root.root_url:
        try:
            return discover_uhc(conn, source_id, output_root, max_index_bytes)
        except Exception as exc:
            insert_error(conn, source_id, root.root_url, "uhc_adapter", exc)
            return {"files": 0, "snapshots": 0, "errors": 1}

    q = deque([(root.root_url, None, 0, "source_root")])
    seen: set[str] = set()
    stats = {"files": 0, "snapshots": 0, "errors": 0, "pages": 0}
    file_heads = 0

    while q and stats["pages"] < max_pages:
        url, parent, depth, method = q.popleft()
        url = canonicalize_url(url) or url
        if url in seen:
            continue
        seen.add(url)
        kind = file_kind(url)

        # Rate bodies are inventoried, not downloaded, during discovery.
        if kind in {"in_network", "allowed_amounts"}:
            meta = {}
            if file_heads < head_files:
                try:
                    meta = head_metadata(url)
                    file_heads += 1
                except Exception as exc:
                    insert_error(conn, source_id, url, "head_rate_file", exc)
            upsert_file(conn, source_id=source_id, url=url, kind=kind, meta=meta)
            stats["files"] += 1
            continue

        try:
            raw, resp = fetch_small(url, timeout=45, max_bytes=max_index_bytes)
            stats["pages"] += 1
            digest = sha256_bytes(raw)
            rel = write_blob(output_root, digest, raw)
            ctype = resp.headers.get("content-type", "").split(";")[0].lower()
            meta = {
                "status": resp.status_code,
                "content_type": ctype,
                "content_length": len(raw),
                "etag": resp.headers.get("etag"),
                "last_modified": resp.headers.get("last-modified"),
            }
            obs_kind = "page"
            links: list[str] = []

            text = raw.decode("utf-8", errors="replace")
            payload = None
            if "json" in ctype or urlsplit(url).path.lower().endswith(".json"):
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    payload = None

            if isinstance(payload, dict):
                toc = parse_toc(
                    conn,
                    source_id=source_id,
                    index_url=url,
                    index_sha=digest,
                    payload=payload,
                )
                if toc["is_toc"]:
                    obs_kind = "table_of_contents"
                    stats["files"] += toc["files"]
                links = all_urls(payload)
            elif isinstance(payload, list):
                links = all_urls(payload)
            elif "html" in ctype or "<html" in text[:500].lower():
                links = html_links(raw, str(resp.url))
            else:
                links = [
                    canonicalize_url(x)
                    for x in re.findall(r"https?://[^\s\"'<>]+", text)
                ]
                links = [x for x in links if x and TIC_RE.search(x)]

            observe(
                conn,
                source_id=source_id,
                url=url,
                parent_url=parent,
                kind=obs_kind,
                discovery_method=method,
                meta=meta,
                status="parsed",
                sha256=digest,
                blob_relpath=rel,
                note=f"links={len(links)}",
            )
            stats["snapshots"] += 1
            conn.commit()

            if depth < max_depth:
                for link in links:
                    link = canonicalize_url(link)
                    if not link or link in seen:
                        continue
                    if TIC_RE.search(link) or file_kind(link) != "unknown":
                        q.append((link, url, depth + 1, "discovered_link"))
        except Exception as exc:
            stats["errors"] += 1
            insert_error(conn, source_id, url, "discover", exc)

    return stats


def command_inventory(args) -> int:
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    db = Path(args.db)
    if not db.is_absolute():
        db = out / db
    conn = init_db(db)
    roots = load_registry(conn, out, timeout=args.timeout)
    roots = [
        root for root in roots
        if stable_source_bucket(root, args.shard_count) == args.shard_index
    ]
    if args.max_sources:
        roots = roots[: args.max_sources]

    run = conn.execute(
        """INSERT INTO discovery_runs(started_at,shard_index,shard_count,status)
           VALUES (?,?,?,'running')""",
        (utcnow(), args.shard_index, args.shard_count),
    )
    run_id = int(run.lastrowid)
    conn.commit()

    totals = {
        "sources": len(roots),
        "files": 0,
        "snapshots": 0,
        "errors": 0,
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
    }
    for idx, root in enumerate(roots, start=1):
        delta = discover_root(
            conn,
            root,
            out,
            max_depth=args.max_depth,
            max_pages=args.max_pages_per_source,
            max_index_bytes=args.max_index_mb * 1024 * 1024,
            head_files=args.head_files_per_source,
        )
        for key in ("files", "snapshots", "errors"):
            totals[key] += delta.get(key, 0)
        if idx % 10 == 0 or idx == len(roots):
            print(f"progress {idx}/{len(roots)} files={totals['files']} snapshots={totals['snapshots']} errors={totals['errors']}")

    totals["unique_files"] = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    totals["plans"] = conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
    totals["reporting_entities"] = conn.execute(
        "SELECT COUNT(*) FROM reporting_entities"
    ).fetchone()[0]
    totals["finished_at"] = utcnow()
    conn.execute(
        """UPDATE discovery_runs SET finished_at=?,status='complete',stats_json=?
           WHERE id=?""",
        (totals["finished_at"], json.dumps(totals, sort_keys=True), run_id),
    )
    conn.commit()
    (out / "summary.json").write_text(json.dumps(totals, indent=2) + "\n")
    print(json.dumps(totals, indent=2))
    conn.close()
    return 0


def command_summary(args) -> int:
    conn = sqlite3.connect(args.db)
    result = {
        "source_roots": conn.execute("SELECT COUNT(*) FROM source_roots").fetchone()[0],
        "observations": conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
        "reporting_entities": conn.execute("SELECT COUNT(*) FROM reporting_entities").fetchone()[0],
        "plans": conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0],
        "files": conn.execute("SELECT COUNT(*) FROM files").fetchone()[0],
        "in_network_files": conn.execute("SELECT COUNT(*) FROM files WHERE kind='in_network'").fetchone()[0],
        "allowed_amount_files": conn.execute("SELECT COUNT(*) FROM files WHERE kind='allowed_amounts'").fetchone()[0],
        "files_with_size": conn.execute("SELECT COUNT(*) FROM files WHERE content_length IS NOT NULL").fetchone()[0],
        "errors": conn.execute("SELECT COUNT(*) FROM errors").fetchone()[0],
        "top_sources": conn.execute(
            """SELECT sr.payer_name, COUNT(f.file_key) c
               FROM source_roots sr LEFT JOIN files f ON f.source_root_id=sr.id
               GROUP BY sr.id ORDER BY c DESC LIMIT 25"""
        ).fetchall(),
        "error_types": conn.execute(
            """SELECT stage||':'||error_type, COUNT(*) c
               FROM errors GROUP BY 1 ORDER BY c DESC LIMIT 25"""
        ).fetchall(),
    }
    print(json.dumps(result, indent=2))
    conn.close()
    return 0


def build_parser():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    i = sub.add_parser("inventory")
    i.add_argument("--out", default=".cms_tic_ledger")
    i.add_argument("--db", default="catalog.sqlite")
    i.add_argument("--timeout", type=int, default=30)
    i.add_argument("--max-depth", type=int, default=2)
    i.add_argument("--max-pages-per-source", type=int, default=100)
    i.add_argument("--max-index-mb", type=int, default=300)
    i.add_argument("--head-files-per-source", type=int, default=25)
    i.add_argument("--max-sources", type=int, default=0)
    i.add_argument("--shard-index", type=int, default=0)
    i.add_argument("--shard-count", type=int, default=1)
    i.set_defaults(func=command_inventory)

    s = sub.add_parser("summary")
    s.add_argument("--db", required=True)
    s.set_defaults(func=command_summary)
    return p


def main() -> int:
    p = build_parser()
    args = p.parse_args()
    if getattr(args, "shard_count", 1) < 1:
        p.error("--shard-count must be >=1")
    if getattr(args, "shard_index", 0) < 0 or getattr(args, "shard_index", 0) >= getattr(args, "shard_count", 1):
        p.error("--shard-index must be in [0, shard-count)")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
