#!/usr/bin/env python3
"""Catalog-first ingestion for CMS Transparency-in-Coverage machine-readable files.

This stage deliberately does NOT download giant in-network rate files. It snapshots
payer landing/index/table-of-contents pages, hashes the exact bytes, extracts MRF
URLs and plan metadata, and records unresolved dynamic portals explicitly.

Full/selective in-network rate extraction is handled by mrf_stream.py.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

import ijson
import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Hunter-TiC-MRF-Ledger/1.0 "
    "(public CMS Transparency-in-Coverage catalog research)"
)

URL_RE = re.compile(r"https?://[^\s\"'<>\\]+", re.I)
INDEX_HINT_RE = re.compile(
    r"(?:_index\.(?:json|json\.gz)|(?:^|[/_-])index\.(?:json|json\.gz)|"
    r"table[-_ ]?of[-_ ]?contents|toc\.(?:json|json\.gz))",
    re.I,
)
IN_NETWORK_RE = re.compile(r"in[-_ ]?network[-_ ]?rates", re.I)
ALLOWED_RE = re.compile(r"allowed[-_ ]?amounts", re.I)


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonicalize_url(raw: str, base: str | None = None) -> str | None:
    raw = (raw or "").strip().strip(".,);]")
    if not raw or raw.startswith(("mailto:", "javascript:", "tel:", "#")):
        return None
    if base:
        raw = urllib.parse.urljoin(base, raw)
    if raw.startswith("//"):
        raw = "https:" + raw
    try:
        parsed = urllib.parse.urlsplit(raw)
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return None
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower()
    port = parsed.port
    netloc = host
    if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        netloc = f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query = [
        (k, v) for k, v in query
        if k.lower() not in {
            "utm_source", "utm_medium", "utm_campaign", "utm_term",
            "utm_content", "fbclid", "gclid",
        }
    ]
    return urllib.parse.urlunsplit(
        (scheme, netloc, path, urllib.parse.urlencode(query, doseq=True), "")
    )


def classify_url(url: str) -> str:
    probe = urllib.parse.unquote(url).lower()
    if IN_NETWORK_RE.search(probe):
        return "IN_NETWORK"
    if ALLOWED_RE.search(probe):
        return "ALLOWED_AMOUNTS"
    if INDEX_HINT_RE.search(probe):
        return "INDEX"
    return "UNKNOWN"


def write_blob(out_dir: Path, digest: str, raw: bytes) -> str:
    rel = Path("blobs") / "sha256" / digest[:2] / digest
    path = out_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        tmp.write_bytes(raw)
        try:
            os.replace(tmp, path)
        finally:
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass
    return str(rel)


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.commit()
    return conn


def load_source_config(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("sources")
    if not isinstance(rows, list):
        raise ValueError("sources.json must contain a sources array")
    return rows


def persist_source(conn: sqlite3.Connection, row: dict[str, Any]) -> int:
    now = utcnow()
    payer_key = str(row["payer_key"]).strip()
    conn.execute(
        """INSERT INTO sources(
             payer_key, display_name, landing_url, source_kind, active,
             first_seen_at, last_seen_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(payer_key) DO UPDATE SET
             display_name=excluded.display_name,
             landing_url=excluded.landing_url,
             source_kind=excluded.source_kind,
             active=excluded.active,
             last_seen_at=excluded.last_seen_at""",
        (
            payer_key,
            str(row["display_name"]).strip(),
            str(row["landing_url"]).strip(),
            str(row.get("source_kind") or "payer_landing").strip(),
            int(bool(row.get("active", True))),
            now,
            now,
        ),
    )
    source_id = conn.execute(
        "SELECT id FROM sources WHERE payer_key=?", (payer_key,)
    ).fetchone()[0]
    conn.commit()
    return int(source_id)


def fetch_bytes(
    session: requests.Session,
    url: str,
    *,
    timeout: int,
    max_bytes: int,
) -> tuple[bytes, requests.Response]:
    with session.get(url, stream=True, timeout=timeout, allow_redirects=True) as resp:
        resp.raise_for_status()
        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(1024 * 256):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(
                    f"catalog source exceeds max_bytes={max_bytes}; "
                    "use a targeted adapter or raise the explicit cap"
                )
            chunks.append(chunk)
        return b"".join(chunks), resp


def persist_snapshot(
    conn: sqlite3.Connection,
    out_dir: Path,
    source_id: int,
    requested_url: str,
    raw: bytes,
    resp: requests.Response,
    parser_status: str,
) -> int:
    digest = sha256_bytes(raw)
    blob_rel = write_blob(out_dir, digest, raw)
    fetched = utcnow()
    final_url = canonicalize_url(resp.url) or resp.url
    ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    etag = resp.headers.get("etag")
    last_modified = resp.headers.get("last-modified")
    conn.execute(
        """INSERT OR IGNORE INTO snapshots(
             source_id, requested_url, final_url, fetched_at, http_status,
             content_type, byte_count, sha256, etag, last_modified,
             blob_relpath, parser_status
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            source_id, requested_url, final_url, fetched, resp.status_code,
            ctype, len(raw), digest, etag, last_modified, blob_rel, parser_status,
        ),
    )
    snapshot_id = conn.execute(
        """SELECT id FROM snapshots
           WHERE source_id=? AND requested_url=? AND sha256=?""",
        (source_id, requested_url, digest),
    ).fetchone()[0]
    conn.execute(
        """INSERT OR IGNORE INTO snapshot_observations(
             snapshot_id, observed_at, http_status, final_url, etag, last_modified
           ) VALUES (?, ?, ?, ?, ?, ?)""",
        (snapshot_id, fetched, resp.status_code, final_url, etag, last_modified),
    )
    conn.commit()
    return int(snapshot_id)


def record_error(
    conn: sqlite3.Connection,
    source_id: int | None,
    url: str,
    stage: str,
    exc: Exception | str,
    error_type: str | None = None,
) -> None:
    if isinstance(exc, Exception):
        detail = str(exc)[:4000]
        kind = error_type or type(exc).__name__
    else:
        detail = str(exc)[:4000]
        kind = error_type or "Error"
    conn.execute(
        """INSERT INTO crawl_errors(
             source_id, url, occurred_at, stage, error_type, detail
           ) VALUES (?, ?, ?, ?, ?, ?)""",
        (source_id, url, utcnow(), stage, kind, detail),
    )
    conn.commit()


def iter_json_strings(raw: bytes) -> Iterator[str]:
    try:
        for _prefix, event, value in ijson.parse(io.BytesIO(raw)):
            if event == "string" and isinstance(value, str):
                yield value
    except Exception:
        return


def candidate_urls(raw: bytes, content_type: str, base_url: str) -> list[str]:
    out: set[str] = set()
    text = raw.decode("utf-8", errors="replace")

    if "html" in content_type or "<html" in text[:2000].lower():
        soup = BeautifulSoup(text, "html.parser")
        for tag in soup.find_all(["a", "link", "script"], src=True):
            url = canonicalize_url(tag.get("src"), base_url)
            if url:
                out.add(url)
        for tag in soup.find_all(["a", "link"], href=True):
            url = canonicalize_url(tag.get("href"), base_url)
            if url:
                out.add(url)

    for match in URL_RE.findall(text):
        url = canonicalize_url(match, base_url)
        if url:
            out.add(url)

    if "json" in content_type or text.lstrip().startswith(("{", "[")):
        for value in iter_json_strings(raw):
            if value.startswith(("http://", "https://", "//")):
                url = canonicalize_url(value, base_url)
                if url:
                    out.add(url)

    return sorted(out)


def top_level_scalar(raw: bytes, key: str) -> str | None:
    try:
        for value in ijson.items(io.BytesIO(raw), key):
            if isinstance(value, (str, int, float)):
                return str(value)
            break
    except Exception:
        pass
    return None


def iter_reporting_structures(raw: bytes) -> Iterator[dict[str, Any]]:
    try:
        for item in ijson.items(io.BytesIO(raw), "reporting_structure.item"):
            if isinstance(item, dict):
                yield item
    except Exception:
        return


def extract_file_locations(structure: dict[str, Any]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for entry in structure.get("in_network_files") or []:
        if isinstance(entry, dict):
            loc = entry.get("location")
            if isinstance(loc, str):
                result.append((loc, "IN_NETWORK"))

    allowed = structure.get("allowed_amount_file")
    if isinstance(allowed, dict) and isinstance(allowed.get("location"), str):
        result.append((allowed["location"], "ALLOWED_AMOUNTS"))
    elif isinstance(allowed, list):
        for entry in allowed:
            if isinstance(entry, dict) and isinstance(entry.get("location"), str):
                result.append((entry["location"], "ALLOWED_AMOUNTS"))

    return result


def normalize_plan(
    plan: dict[str, Any],
) -> tuple[
    str | None, str | None, str | None,
    str | None, str | None, str | None,
]:
    return (
        str(plan.get("plan_name")) if plan.get("plan_name") is not None else None,
        str(plan.get("issuer_name")) if plan.get("issuer_name") is not None else None,
        str(plan.get("plan_sponsor_name")) if plan.get("plan_sponsor_name") is not None else None,
        str(plan.get("plan_id_type")) if plan.get("plan_id_type") is not None else None,
        str(plan.get("plan_id")) if plan.get("plan_id") is not None else None,
        str(plan.get("plan_market_type")) if plan.get("plan_market_type") is not None else None,
    )


def upsert_mrf_file(
    conn: sqlite3.Connection,
    *,
    source_id: int,
    snapshot_id: int | None,
    url: str,
    file_type: str,
    reporting_entity_name: str | None,
    reporting_entity_type: str | None,
    last_updated_on: str | None,
    schema_version: str | None,
) -> int:
    now = utcnow()
    conn.execute(
        """INSERT INTO mrf_files(
             source_id, discovered_from_snapshot_id, url, file_type,
             reporting_entity_name, reporting_entity_type, last_updated_on,
             schema_version, first_seen_at, last_seen_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(source_id, url) DO UPDATE SET
             discovered_from_snapshot_id=COALESCE(excluded.discovered_from_snapshot_id, mrf_files.discovered_from_snapshot_id),
             file_type=CASE WHEN excluded.file_type!='UNKNOWN' THEN excluded.file_type ELSE mrf_files.file_type END,
             reporting_entity_name=COALESCE(excluded.reporting_entity_name, mrf_files.reporting_entity_name),
             reporting_entity_type=COALESCE(excluded.reporting_entity_type, mrf_files.reporting_entity_type),
             last_updated_on=COALESCE(excluded.last_updated_on, mrf_files.last_updated_on),
             schema_version=COALESCE(excluded.schema_version, mrf_files.schema_version),
             last_seen_at=excluded.last_seen_at""",
        (
            source_id, snapshot_id, url, file_type, reporting_entity_name,
            reporting_entity_type, last_updated_on, schema_version, now, now,
        ),
    )
    row = conn.execute(
        "SELECT id FROM mrf_files WHERE source_id=? AND url=?",
        (source_id, url),
    ).fetchone()
    conn.commit()
    return int(row[0])


def persist_plan(conn: sqlite3.Connection, mrf_file_id: int, plan: dict[str, Any]) -> None:
    name, issuer_name, sponsor_name, id_type, plan_id, market = normalize_plan(plan)
    conn.execute(
        """INSERT OR IGNORE INTO plans(
             mrf_file_id, plan_name, issuer_name, plan_sponsor_name,
             plan_id_type, plan_id, plan_market_type
           ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            mrf_file_id, name, issuer_name, sponsor_name,
            id_type, plan_id, market,
        ),
    )


def parse_index_snapshot(
    conn: sqlite3.Connection,
    *,
    source_id: int,
    snapshot_id: int,
    raw: bytes,
    base_url: str,
) -> dict[str, int]:
    entity_name = top_level_scalar(raw, "reporting_entity_name")
    entity_type = top_level_scalar(raw, "reporting_entity_type")
    last_updated = top_level_scalar(raw, "last_updated_on")
    schema_version = top_level_scalar(raw, "version")

    files = 0
    plans = 0
    structures = 0

    for structure in iter_reporting_structures(raw):
        structures += 1
        reporting_plans = [
            p for p in (structure.get("reporting_plans") or [])
            if isinstance(p, dict)
        ]
        for raw_url, forced_type in extract_file_locations(structure):
            url = canonicalize_url(raw_url, base_url)
            if not url:
                continue
            mrf_id = upsert_mrf_file(
                conn,
                source_id=source_id,
                snapshot_id=snapshot_id,
                url=url,
                file_type=forced_type,
                reporting_entity_name=entity_name,
                reporting_entity_type=entity_type,
                last_updated_on=last_updated,
                schema_version=schema_version,
            )
            files += 1
            for plan in reporting_plans:
                persist_plan(conn, mrf_id, plan)
                plans += 1

    conn.commit()
    return {"structures": structures, "files": files, "plans": plans}


def looks_like_json(raw: bytes, content_type: str) -> bool:
    if "json" in content_type:
        return True
    head = raw[:4096].lstrip()
    return head.startswith((b"{", b"["))


def crawl_source(
    conn: sqlite3.Connection,
    out_dir: Path,
    source: dict[str, Any],
    *,
    timeout: int,
    max_bytes: int,
    max_indexes: int,
    max_depth: int,
) -> dict[str, int]:
    source_id = persist_source(conn, source)
    landing = canonicalize_url(str(source["landing_url"]))
    if not landing:
        raise ValueError(f"invalid landing URL for {source['payer_key']}")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})

    queue: list[tuple[str, int]] = [(landing, 0)]
    seen: set[str] = set()
    stats = {
        "pages_fetched": 0,
        "snapshots": 0,
        "index_documents": 0,
        "mrf_files_discovered": 0,
        "plans_discovered": 0,
        "errors": 0,
    }

    while queue and stats["index_documents"] < max_indexes:
        url, depth = queue.pop(0)
        url = canonicalize_url(url) or url
        if url in seen:
            continue
        seen.add(url)

        try:
            raw, resp = fetch_bytes(session, url, timeout=timeout, max_bytes=max_bytes)
            stats["pages_fetched"] += 1
            ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
            final_url = canonicalize_url(resp.url) or resp.url
            url_type = classify_url(final_url)
            parser_status = "catalog_snapshot"
            if url_type == "INDEX" or looks_like_json(raw, ctype):
                parser_status += ":json_candidate"

            snapshot_id = persist_snapshot(
                conn, out_dir, source_id, url, raw, resp, parser_status
            )
            stats["snapshots"] += 1

            parsed_index = False
            if looks_like_json(raw, ctype):
                parsed = parse_index_snapshot(
                    conn,
                    source_id=source_id,
                    snapshot_id=snapshot_id,
                    raw=raw,
                    base_url=final_url,
                )
                if parsed["structures"] or parsed["files"]:
                    parsed_index = True
                    stats["index_documents"] += 1
                    stats["mrf_files_discovered"] += parsed["files"]
                    stats["plans_discovered"] += parsed["plans"]
                    upsert_mrf_file(
                        conn,
                        source_id=source_id,
                        snapshot_id=snapshot_id,
                        url=final_url,
                        file_type="INDEX",
                        reporting_entity_name=top_level_scalar(raw, "reporting_entity_name"),
                        reporting_entity_type=top_level_scalar(raw, "reporting_entity_type"),
                        last_updated_on=top_level_scalar(raw, "last_updated_on"),
                        schema_version=top_level_scalar(raw, "version"),
                    )

            candidates = candidate_urls(raw, ctype, final_url)
            useful = 0
            for candidate in candidates:
                ftype = classify_url(candidate)
                if ftype in {"IN_NETWORK", "ALLOWED_AMOUNTS"}:
                    upsert_mrf_file(
                        conn,
                        source_id=source_id,
                        snapshot_id=snapshot_id,
                        url=candidate,
                        file_type=ftype,
                        reporting_entity_name=None,
                        reporting_entity_type=None,
                        last_updated_on=None,
                        schema_version=None,
                    )
                    stats["mrf_files_discovered"] += 1
                    useful += 1
                    continue

                if depth < max_depth and ftype == "INDEX":
                    queue.append((candidate, depth + 1))
                    useful += 1

                # Many payer portals link to a JS/HTML search app whose source
                # then contains the actual public index endpoints.
                if (
                    depth < max_depth
                    and ftype == "UNKNOWN"
                    and urllib.parse.urlsplit(candidate).hostname
                    == urllib.parse.urlsplit(final_url).hostname
                    and candidate.rsplit(".", 1)[-1].lower() in {"html", "htm", "js", "json"}
                ):
                    queue.append((candidate, depth + 1))

            if depth == 0 and not parsed_index and useful == 0:
                record_error(
                    conn,
                    source_id,
                    final_url,
                    "discovery",
                    "Landing page exposed no static index/MRF links; payer-specific dynamic adapter required.",
                    "DynamicPortalUnresolved",
                )
                stats["errors"] += 1

        except Exception as exc:
            record_error(conn, source_id, url, "fetch", exc)
            stats["errors"] += 1

    return stats


def command_crawl(args: argparse.Namespace) -> int:
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = Path(args.db)
    if not db_path.is_absolute():
        db_path = out_dir / db_path
    conn = init_db(db_path)

    run_id = conn.execute(
        "INSERT INTO crawl_runs(started_at, mode, status) VALUES (?, ?, ?)",
        (utcnow(), "catalog", "running"),
    ).lastrowid
    conn.commit()

    all_stats: dict[str, Any] = {"sources": {}, "totals": {}}
    rows = load_source_config(Path(args.sources))
    if args.payer_key:
        rows = [x for x in rows if x.get("payer_key") == args.payer_key]
        if not rows:
            raise SystemExit(f"unknown payer_key={args.payer_key}")

    for source in rows:
        if not source.get("active", True):
            continue
        key = str(source["payer_key"])
        print(f"cataloging {key}", file=sys.stderr)
        try:
            stats = crawl_source(
                conn,
                out_dir,
                source,
                timeout=args.timeout,
                max_bytes=args.max_bytes,
                max_indexes=args.max_indexes_per_source,
                max_depth=args.max_depth,
            )
        except Exception as exc:
            stats = {"errors": 1}
            record_error(
                conn, None, str(source.get("landing_url")), "source", exc
            )
        all_stats["sources"][key] = stats

    total_keys = {
        key for stats in all_stats["sources"].values()
        for key, value in stats.items()
        if isinstance(value, int)
    }
    all_stats["totals"] = {
        key: sum(int(stats.get(key, 0)) for stats in all_stats["sources"].values())
        for key in sorted(total_keys)
    }
    all_stats["catalog_mrf_files"] = conn.execute(
        "SELECT COUNT(*) FROM mrf_files"
    ).fetchone()[0]
    all_stats["catalog_plans"] = conn.execute(
        "SELECT COUNT(*) FROM plans"
    ).fetchone()[0]
    all_stats["index_files"] = conn.execute(
        "SELECT COUNT(*) FROM mrf_files WHERE file_type='INDEX'"
    ).fetchone()[0]
    all_stats["in_network_files"] = conn.execute(
        "SELECT COUNT(*) FROM mrf_files WHERE file_type='IN_NETWORK'"
    ).fetchone()[0]
    all_stats["allowed_amount_files"] = conn.execute(
        "SELECT COUNT(*) FROM mrf_files WHERE file_type='ALLOWED_AMOUNTS'"
    ).fetchone()[0]
    all_stats["errors"] = conn.execute(
        "SELECT COUNT(*) FROM crawl_errors"
    ).fetchone()[0]

    finished = utcnow()
    conn.execute(
        """UPDATE crawl_runs
           SET finished_at=?, status='complete', stats_json=?
           WHERE id=?""",
        (finished, json.dumps(all_stats, sort_keys=True), run_id),
    )
    conn.commit()
    (out_dir / "catalog_summary.json").write_text(
        json.dumps(all_stats, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(all_stats, indent=2, sort_keys=True))
    conn.close()
    return 0


def command_summary(args: argparse.Namespace) -> int:
    conn = sqlite3.connect(args.db)
    summary = {
        "sources": conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
        "snapshots": conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0],
        "unique_snapshot_hashes": conn.execute(
            "SELECT COUNT(DISTINCT sha256) FROM snapshots WHERE sha256 IS NOT NULL"
        ).fetchone()[0],
        "mrf_files": conn.execute("SELECT COUNT(*) FROM mrf_files").fetchone()[0],
        "plans": conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0],
        "rates": conn.execute("SELECT COUNT(*) FROM rates").fetchone()[0],
        "errors": conn.execute("SELECT COUNT(*) FROM crawl_errors").fetchone()[0],
        "file_types": conn.execute(
            "SELECT file_type, COUNT(*) FROM mrf_files GROUP BY file_type ORDER BY 2 DESC"
        ).fetchall(),
        "source_coverage": conn.execute(
            """SELECT s.payer_key, s.display_name,
                      COUNT(DISTINCT f.id) mrf_files,
                      SUM(CASE WHEN f.file_type='IN_NETWORK' THEN 1 ELSE 0 END) in_network,
                      SUM(CASE WHEN f.file_type='INDEX' THEN 1 ELSE 0 END) indexes,
                      COUNT(DISTINCT p.id) plans
               FROM sources s
               LEFT JOIN mrf_files f ON f.source_id=s.id
               LEFT JOIN plans p ON p.mrf_file_id=f.id
               GROUP BY s.id ORDER BY mrf_files DESC"""
        ).fetchall(),
        "errors_by_type": conn.execute(
            """SELECT stage || ':' || error_type, COUNT(*)
               FROM crawl_errors GROUP BY 1 ORDER BY 2 DESC"""
        ).fetchall(),
    }
    print(json.dumps(summary, indent=2))
    conn.close()
    return 0



def command_probe(args: argparse.Namespace) -> int:
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    params: list[Any] = []
    where = ["1=1"]
    if args.file_type:
        where.append("f.file_type=?")
        params.append(args.file_type.upper())
    if args.payer_key:
        where.append("s.payer_key=?")
        params.append(args.payer_key)

    sql = f"""SELECT f.id, f.url, f.source_id, f.file_type, s.payer_key
              FROM mrf_files f
              JOIN sources s ON s.id=f.source_id
              WHERE {' AND '.join(where)}
              ORDER BY f.id"""
    if args.limit:
        sql += " LIMIT ?"
        params.append(args.limit)
    rows = conn.execute(sql, params).fetchall()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
    stats = {"targets": len(rows), "head_ok": 0, "head_failed": 0}

    for row in rows:
        try:
            resp = session.head(
                row["url"],
                timeout=args.timeout,
                allow_redirects=True,
            )
            status = resp.status_code
            if 200 <= status < 400:
                length = resp.headers.get("content-length")
                conn.execute(
                    """UPDATE mrf_files
                       SET etag=COALESCE(?, etag),
                           last_modified=COALESCE(?, last_modified),
                           content_length=COALESCE(?, content_length),
                           access_status='HEAD_OK',
                           last_seen_at=?
                       WHERE id=?""",
                    (
                        resp.headers.get("etag"),
                        resp.headers.get("last-modified"),
                        int(length) if length and length.isdigit() else None,
                        utcnow(),
                        row["id"],
                    ),
                )
                stats["head_ok"] += 1
            else:
                conn.execute(
                    """UPDATE mrf_files SET access_status=? WHERE id=?""",
                    (f"HEAD_HTTP_{status}", row["id"]),
                )
                record_error(
                    conn,
                    int(row["source_id"]),
                    row["url"],
                    "head_probe",
                    f"HEAD returned HTTP {status}",
                    "HTTPStatus",
                )
                stats["head_failed"] += 1
        except Exception as exc:
            record_error(
                conn,
                int(row["source_id"]),
                row["url"],
                "head_probe",
                exc,
            )
            stats["head_failed"] += 1
        conn.commit()

    totals = conn.execute(
        """SELECT COUNT(*), COALESCE(SUM(content_length), 0)
           FROM mrf_files WHERE content_length IS NOT NULL"""
    ).fetchone()
    stats["files_with_content_length"] = int(totals[0])
    stats["known_content_bytes"] = int(totals[1])
    print(json.dumps(stats, indent=2))
    conn.close()
    return 0



def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="CMS TiC public MRF catalog")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("crawl")
    c.add_argument("--sources", default=str(Path(__file__).with_name("sources.json")))
    c.add_argument("--out", default=".tic_mrf_ledger")
    c.add_argument("--db", default="ledger.sqlite")
    c.add_argument("--payer-key")
    c.add_argument("--timeout", type=int, default=30)
    c.add_argument("--max-bytes", type=int, default=250_000_000)
    c.add_argument("--max-indexes-per-source", type=int, default=25)
    c.add_argument("--max-depth", type=int, default=2)
    c.set_defaults(func=command_crawl)

    probe = sub.add_parser("probe")
    probe.add_argument("--db", required=True)
    probe.add_argument("--payer-key")
    probe.add_argument(
        "--file-type",
        choices=["INDEX", "IN_NETWORK", "ALLOWED_AMOUNTS", "UNKNOWN"],
        default="IN_NETWORK",
    )
    probe.add_argument("--limit", type=int, default=0)
    probe.add_argument("--timeout", type=int, default=20)
    probe.set_defaults(func=command_probe)

    s = sub.add_parser("summary")
    s.add_argument("--db", required=True)
    s.set_defaults(func=command_summary)
    return p


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
