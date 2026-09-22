#!/usr/bin/env python3
"""Catalog the CMS Transparency-in-Coverage MRF universe.

This stage catalogs payer/index/rate-file identities and provenance. It does not
blindly mirror every multi-GB/TB in-network rate file. Large rate files are
streamed only by the targeted extractor.

Sources include:
- historical GitHub-hosted SQLite URL catalogs;
- live payer blob/list APIs;
- payer metadata APIs;
- public HTML pages containing CMS index links;
- CMS table-of-contents/index JSON files discovered by those sources.

Every fetched manifest/catalog is SHA-256 hashed. Small/medium manifests are
stored in a content-addressed blob store; oversize index manifests are parsed
from a temp file and retain their hash/headers even if not copied into artifacts.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sqlite3
import tempfile
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

import ijson
import requests
from bs4 import BeautifulSoup


USER_AGENT = "RecoveryWorks-TiC-MRF-Ledger/1.0 (public price-transparency research)"


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def classify_file(url: str, hint: str | None = None) -> str:
    probe = f"{url} {hint or ''}".lower()
    if "allowed-amount" in probe or "allowed_amount" in probe:
        return "allowed_amounts"
    if "in-network" in probe or "innetwork" in probe or "in_network" in probe:
        return "in_network"
    if "index" in probe or "table-of-contents" in probe or "table_of_contents" in probe:
        return "index"
    if "provider-reference" in probe or "provider_reference" in probe:
        return "provider_reference"
    return "unknown"


def canonical_url(url: str, base: str | None = None) -> str:
    url = (url or "").strip()
    if base:
        url = urllib.parse.urljoin(base, url)
    p = urllib.parse.urlsplit(url)
    if not p.scheme:
        return url
    q = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
    q = [(k, v) for k, v in q if not k.lower().startswith("utm_")]
    return urllib.parse.urlunsplit(
        (p.scheme.lower(), p.netloc.lower(), p.path, urllib.parse.urlencode(q, doseq=True), "")
    )


def write_blob(root: Path, digest: str, raw: bytes) -> str:
    rel = Path("blobs") / "sha256" / digest[:2] / digest
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        tmp.write_bytes(raw)
        os.replace(tmp, path)
    return str(rel)


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(Path(__file__).with_name("schema.sql").read_text())
    conn.commit()
    return conn


@dataclass(frozen=True)
class Source:
    source_key: str
    payer_name: str
    adapter: str
    source_url: str
    historical: bool = False
    brand_code: str | None = None
    notes: str | None = None


def load_sources(path: Path) -> list[Source]:
    obj = json.loads(path.read_text())
    result: list[Source] = []
    for item in obj.get("historical_catalogs", []):
        result.append(Source(
            source_key=item["source_key"],
            payer_name=item["payer_name"],
            adapter=item["adapter"],
            source_url=item["source_url"],
            historical=True,
            brand_code=item.get("brand_code"),
            notes=item.get("notes"),
        ))
    for item in obj.get("live_sources", []):
        result.append(Source(
            source_key=item["source_key"],
            payer_name=item["payer_name"],
            adapter=item["adapter"],
            source_url=item["source_url"],
            historical=False,
            brand_code=item.get("brand_code"),
            notes=item.get("notes"),
        ))
    return result


def persist_source(conn: sqlite3.Connection, source: Source) -> int:
    conn.execute(
        """INSERT OR IGNORE INTO sources
           (source_key,payer_name,adapter,source_url,historical,notes)
           VALUES (?,?,?,?,?,?)""",
        (
            source.source_key, source.payer_name, source.adapter,
            source.source_url, int(source.historical), source.notes,
        ),
    )
    row = conn.execute("SELECT id FROM sources WHERE source_key=?", (source.source_key,)).fetchone()
    assert row
    return int(row[0])


def record_error(
    conn: sqlite3.Connection,
    source_key: str | None,
    url: str,
    stage: str,
    exc: Exception | str,
    error_type: str | None = None,
) -> None:
    if isinstance(exc, Exception):
        detail = str(exc)
        etype = type(exc).__name__
    else:
        detail = str(exc)
        etype = error_type or "Error"
    conn.execute(
        """INSERT INTO ingestion_errors(source_key,url,occurred_at,stage,error_type,detail)
           VALUES(?,?,?,?,?,?)""",
        (source_key, url, utcnow(), stage, etype, detail[:4000]),
    )


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
    return s


def fetch_bytes(url: str, *, timeout: int, max_bytes: int) -> tuple[bytes, requests.Response]:
    s = session()
    with s.get(url, stream=True, timeout=timeout, allow_redirects=True) as resp:
        resp.raise_for_status()
        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(1024 * 256):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(f"response exceeds max_bytes={max_bytes}")
            chunks.append(chunk)
        return b"".join(chunks), resp


def snapshot_bytes(
    conn: sqlite3.Connection,
    root: Path,
    source: Source,
    source_id: int,
    requested_url: str,
    raw: bytes,
    *,
    final_url: str | None,
    http_status: int | None,
    content_type: str | None,
    etag: str | None = None,
    last_modified: str | None = None,
    parser_status: str = "snapshotted",
    store_blob: bool = True,
) -> tuple[int, str]:
    digest = sha256_bytes(raw)
    rel = write_blob(root, digest, raw) if store_blob else None
    conn.execute(
        """INSERT OR IGNORE INTO source_snapshots
           (source_id,observed_at,requested_url,final_url,http_status,content_type,
            byte_count,sha256,blob_relpath,etag,last_modified,parser_status)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            source_id, utcnow(), requested_url, final_url, http_status, content_type,
            len(raw), digest, rel, etag, last_modified, parser_status,
        ),
    )
    row = conn.execute(
        """SELECT id FROM source_snapshots
           WHERE source_id=? AND requested_url=? AND sha256=?""",
        (source_id, requested_url, digest),
    ).fetchone()
    assert row
    return int(row[0]), digest


def insert_mrf_file(
    conn: sqlite3.Connection,
    source: Source,
    file_url: str,
    file_type: str,
    *,
    snapshot_id: int | None,
    manifest_sha: str | None,
    content_length: int | None = None,
    etag: str | None = None,
    last_modified: str | None = None,
    filename: str | None = None,
    reporting_entity_name: str | None = None,
    reporting_entity_type: str | None = None,
    schema_version: str | None = None,
    last_updated_on: str | None = None,
    parse_status: str = "catalogued",
) -> int:
    file_url = canonical_url(file_url)
    conn.execute(
        """INSERT OR IGNORE INTO mrf_files
           (payer_name,source_key,file_url,file_type,discovered_at,
            discovered_from_snapshot_id,source_manifest_sha256,historical,
            content_length,etag,last_modified,filename,reporting_entity_name,
            reporting_entity_type,schema_version,last_updated_on,parse_status)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            source.payer_name, source.source_key, file_url, file_type, utcnow(),
            snapshot_id, manifest_sha, int(source.historical), content_length,
            etag, last_modified, filename or Path(urllib.parse.urlsplit(file_url).path).name,
            reporting_entity_name, reporting_entity_type, schema_version,
            last_updated_on, parse_status,
        ),
    )
    row = conn.execute(
        """SELECT id FROM mrf_files
           WHERE source_key=? AND file_url=?
             AND COALESCE(source_manifest_sha256,'')=COALESCE(?,'')""",
        (source.source_key, file_url, manifest_sha),
    ).fetchone()
    assert row
    return int(row[0])


def import_historical_sqlite(
    conn: sqlite3.Connection,
    root: Path,
    source: Source,
    *,
    timeout: int,
    max_bytes: int,
) -> dict[str, int]:
    source_id = persist_source(conn, source)
    raw, resp = fetch_bytes(source.source_url, timeout=timeout, max_bytes=max_bytes)
    snap_id, digest = snapshot_bytes(
        conn, root, source, source_id, source.source_url, raw,
        final_url=resp.url, http_status=resp.status_code,
        content_type=resp.headers.get("content-type"),
        etag=resp.headers.get("etag"), last_modified=resp.headers.get("last-modified"),
        parser_status="parsed:sqlite_catalog",
    )

    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        tmp.write(raw)
        tmp.flush()
        h = sqlite3.connect(tmp.name)
        tables = {r[0] for r in h.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        inserted = 0
        for table, ftype in (("index_files", "index"), ("in_network_files", "in_network")):
            if table not in tables:
                continue
            cols = {r[1] for r in h.execute(f"PRAGMA table_info({table})")}
            if "url" not in cols:
                continue
            size_expr = "size" if "size" in cols else "NULL"
            for url, size in h.execute(f"SELECT url,{size_expr} FROM {table}"):
                if not url:
                    continue
                insert_mrf_file(
                    conn, source, str(url), ftype, snapshot_id=snap_id,
                    manifest_sha=digest,
                    content_length=int(size) if size not in (None, -1) else None,
                    parse_status="historical_catalog",
                )
                inserted += 1
        h.close()
    return {"files": inserted, "snapshots": 1}


def discover_blob_api(
    conn: sqlite3.Connection, root: Path, source: Source, *, timeout: int, max_bytes: int
) -> dict[str, int]:
    source_id = persist_source(conn, source)
    raw, resp = fetch_bytes(source.source_url, timeout=timeout, max_bytes=max_bytes)
    snap_id, digest = snapshot_bytes(
        conn, root, source, source_id, source.source_url, raw,
        final_url=resp.url, http_status=resp.status_code,
        content_type=resp.headers.get("content-type"),
        etag=resp.headers.get("etag"), last_modified=resp.headers.get("last-modified"),
        parser_status="parsed:blob_api",
    )
    data = json.loads(raw)
    rows = data.get("blobs", data if isinstance(data, list) else [])
    inserted = 0
    for item in rows:
        if not isinstance(item, dict):
            continue
        url = item.get("downloadUrl") or item.get("download_url") or item.get("url")
        if not url:
            continue
        size = item.get("size") or item.get("contentLength") or item.get("content_length")
        insert_mrf_file(
            conn, source, url, classify_file(url, json.dumps(item)),
            snapshot_id=snap_id, manifest_sha=digest,
            content_length=int(size) if str(size).isdigit() else None,
            filename=item.get("name") or item.get("fileName"),
        )
        inserted += 1
    return {"files": inserted, "snapshots": 1}


def discover_aetna_metadata(
    conn: sqlite3.Connection, root: Path, source: Source, *, timeout: int, max_bytes: int
) -> dict[str, int]:
    source_id = persist_source(conn, source)
    raw, resp = fetch_bytes(source.source_url, timeout=timeout, max_bytes=max_bytes)
    snap_id, digest = snapshot_bytes(
        conn, root, source, source_id, source.source_url, raw,
        final_url=resp.url, http_status=resp.status_code,
        content_type=resp.headers.get("content-type"),
        etag=resp.headers.get("etag"), last_modified=resp.headers.get("last-modified"),
        parser_status="parsed:aetna_metadata",
    )
    data = json.loads(raw)
    inserted = 0
    for item in data.get("files", []):
        if not isinstance(item, dict):
            continue
        schema = str(item.get("fileSchema", ""))
        filename = item.get("fileName") or item.get("name")
        direct = (
            item.get("downloadUrl") or item.get("downloadURL") or item.get("url")
            or item.get("fileUrl") or item.get("fileURL")
        )
        ftype = classify_file(filename or "", schema)
        if direct:
            url = direct
            status = "catalogued"
        elif filename:
            brand = source.brand_code or "unknown"
            url = f"mrf+unresolved://aetna/{brand}/{urllib.parse.quote(str(filename), safe='')}"
            status = "unresolved_path_from_metadata"
        else:
            continue
        size = item.get("size") or item.get("contentLength")
        insert_mrf_file(
            conn, source, url, ftype, snapshot_id=snap_id, manifest_sha=digest,
            content_length=int(size) if str(size).isdigit() else None,
            filename=str(filename) if filename else None,
            parse_status=status,
        )
        inserted += 1
    return {"files": inserted, "snapshots": 1}


def discover_humana(
    conn: sqlite3.Connection, root: Path, source: Source, *, timeout: int, max_bytes: int
) -> dict[str, int]:
    source_id = persist_source(conn, source)
    s = session()
    start = 0
    inserted = snapshots = 0
    while True:
        params = {
            "fileType": "innetwork",
            "iDisplayLength": "2000",
            "iDisplayStart": str(start),
        }
        resp = s.get(source.source_url, params=params, timeout=timeout)
        resp.raise_for_status()
        raw = resp.content
        snap_id, digest = snapshot_bytes(
            conn, root, source, source_id, str(resp.request.url), raw,
            final_url=resp.url, http_status=resp.status_code,
            content_type=resp.headers.get("content-type"),
            etag=resp.headers.get("etag"), last_modified=resp.headers.get("last-modified"),
            parser_status="parsed:humana_page",
        )
        snapshots += 1
        data = resp.json()
        rows = data.get("aaData", [])
        if not rows:
            break
        for item in rows:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            name = str(item["name"])
            url = (
                "https://developers.humana.com/Resource/DownloadPCTFile?"
                "fileType=innetwork&" + name
            )
            size = item.get("size")
            insert_mrf_file(
                conn, source, url, "in_network", snapshot_id=snap_id,
                manifest_sha=digest,
                content_length=int(size) if str(size).isdigit() else None,
                filename=name,
            )
            inserted += 1
        start += len(rows)
        total = data.get("iTotalRecords")
        if total is not None and start >= int(total):
            break
    return {"files": inserted, "snapshots": snapshots}


def discover_html_indexes(
    conn: sqlite3.Connection, root: Path, source: Source, *, timeout: int, max_bytes: int
) -> dict[str, int]:
    source_id = persist_source(conn, source)
    raw, resp = fetch_bytes(source.source_url, timeout=timeout, max_bytes=max_bytes)
    snap_id, digest = snapshot_bytes(
        conn, root, source, source_id, source.source_url, raw,
        final_url=resp.url, http_status=resp.status_code,
        content_type=resp.headers.get("content-type"),
        etag=resp.headers.get("etag"), last_modified=resp.headers.get("last-modified"),
        parser_status="parsed:html_index_links",
    )
    soup = BeautifulSoup(raw, "html.parser")
    inserted = 0
    for a in soup.find_all("a", href=True):
        url = canonical_url(a["href"], resp.url)
        label = a.get_text(" ", strip=True)
        if "index" not in f"{url} {label}".lower():
            continue
        if not url.startswith(("http://", "https://")):
            continue
        insert_mrf_file(
            conn, source, url, "index", snapshot_id=snap_id,
            manifest_sha=digest, parse_status="index_link_discovered",
        )
        inserted += 1
    return {"files": inserted, "snapshots": 1}


def open_json_stream(path: Path, url: str):
    if url.lower().endswith(".gz"):
        return gzip.open(path, "rb")
    return path.open("rb")


def fetch_to_temp(
    url: str,
    *,
    timeout: int,
    max_bytes: int,
) -> tuple[Path, dict[str, Any]]:
    s = session()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mrf")
    digest = hashlib.sha256()
    total = 0
    try:
        with s.get(url, stream=True, timeout=timeout, allow_redirects=True) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_content(1024 * 512):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError(f"index exceeds max_index_bytes={max_bytes}")
                digest.update(chunk)
                tmp.write(chunk)
            meta = {
                "final_url": resp.url,
                "http_status": resp.status_code,
                "content_type": resp.headers.get("content-type"),
                "etag": resp.headers.get("etag"),
                "last_modified": resp.headers.get("last-modified"),
                "content_length": total,
                "sha256": digest.hexdigest(),
            }
    except Exception:
        tmp.close()
        Path(tmp.name).unlink(missing_ok=True)
        raise
    tmp.close()
    return Path(tmp.name), meta


def persist_plan(conn: sqlite3.Connection, source: Source, p: dict[str, Any]) -> int:
    vals = (
        source.source_key,
        p.get("plan_name"),
        p.get("plan_id_type"),
        str(p.get("plan_id")) if p.get("plan_id") is not None else None,
        p.get("plan_market_type"),
    )
    conn.execute(
        """INSERT OR IGNORE INTO plans
           (source_key,plan_name,plan_id_type,plan_id,plan_market_type)
           VALUES(?,?,?,?,?)""", vals,
    )
    row = conn.execute(
        """SELECT id FROM plans WHERE source_key=?
           AND COALESCE(plan_name,'')=COALESCE(?,'')
           AND COALESCE(plan_id_type,'')=COALESCE(?,'')
           AND COALESCE(plan_id,'')=COALESCE(?,'')
           AND COALESCE(plan_market_type,'')=COALESCE(?,'')""",
        vals,
    ).fetchone()
    assert row
    return int(row[0])


def parse_index_file(
    conn: sqlite3.Connection,
    root: Path,
    source: Source,
    source_id: int,
    index_row: sqlite3.Row,
    *,
    timeout: int,
    max_index_bytes: int,
    snapshot_max_bytes: int,
) -> dict[str, int]:
    url = index_row["file_url"]
    if not url.startswith(("http://", "https://")):
        return {"files": 0, "plans": 0, "snapshots": 0}
    path, meta = fetch_to_temp(url, timeout=timeout, max_bytes=max_index_bytes)
    try:
        raw_for_snapshot = path.read_bytes() if meta["content_length"] <= snapshot_max_bytes else b""
        if raw_for_snapshot:
            snap_id, digest = snapshot_bytes(
                conn, root, source, source_id, url, raw_for_snapshot,
                final_url=meta["final_url"], http_status=meta["http_status"],
                content_type=meta["content_type"], etag=meta["etag"],
                last_modified=meta["last_modified"], parser_status="parsed:index",
            )
        else:
            # Preserve hash/headers even when intentionally not duplicating giant index bytes.
            conn.execute(
                """INSERT OR IGNORE INTO source_snapshots
                   (source_id,observed_at,requested_url,final_url,http_status,content_type,
                    byte_count,sha256,blob_relpath,etag,last_modified,parser_status)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    source_id, utcnow(), url, meta["final_url"], meta["http_status"],
                    meta["content_type"], meta["content_length"], meta["sha256"], None,
                    meta["etag"], meta["last_modified"], "parsed:index_hash_only",
                ),
            )
            row = conn.execute(
                "SELECT id FROM source_snapshots WHERE source_id=? AND requested_url=? AND sha256=?",
                (source_id, url, meta["sha256"]),
            ).fetchone()
            assert row
            snap_id, digest = int(row[0]), meta["sha256"]

        file_count = plan_count = 0
        with open_json_stream(path, url) as fh:
            for rs in ijson.items(fh, "reporting_structure.item"):
                if not isinstance(rs, dict):
                    continue
                plans = rs.get("reporting_plans") or []
                plan_ids = [persist_plan(conn, source, p) for p in plans if isinstance(p, dict)]
                plan_count += len(plan_ids)
                groups: list[tuple[str, list[dict[str, Any]]]] = []
                groups.append(("in_network", rs.get("in_network_files") or []))
                groups.append(("allowed_amounts", rs.get("allowed_amount_files") or []))
                for ftype, entries in groups:
                    for f in entries:
                        if not isinstance(f, dict):
                            continue
                        location = f.get("location")
                        if not location:
                            continue
                        mrf_id = insert_mrf_file(
                            conn, source, str(location), ftype,
                            snapshot_id=snap_id, manifest_sha=digest,
                            filename=f.get("description"),
                            parse_status="discovered_from_index",
                        )
                        for pid in plan_ids:
                            conn.execute(
                                """INSERT OR IGNORE INTO file_plan_links
                                   (mrf_file_id,plan_id,index_snapshot_id)
                                   VALUES(?,?,?)""",
                                (mrf_id, pid, snap_id),
                            )
                        file_count += 1
        conn.execute(
            "UPDATE mrf_files SET parse_status='index_parsed' WHERE id=?",
            (index_row["id"],),
        )
        return {"files": file_count, "plans": plan_count, "snapshots": 1}
    finally:
        path.unlink(missing_ok=True)


def run_catalog(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.out).resolve()
    root.mkdir(parents=True, exist_ok=True)
    db = Path(args.db)
    if not db.is_absolute():
        db = root / db
    conn = init_db(db)
    conn.row_factory = sqlite3.Row
    run_id = conn.execute(
        "INSERT INTO ingestion_runs(started_at,status) VALUES(?,?)",
        (utcnow(), "running"),
    ).lastrowid
    conn.commit()

    sources = load_sources(Path(args.sources))
    stats: dict[str, Any] = {
        "sources": len(sources),
        "source_successes": 0,
        "source_failures": 0,
        "files_discovered": 0,
        "source_snapshots": 0,
        "index_files_parsed": 0,
        "index_files_failed": 0,
        "plans_observed": 0,
    }

    adapters = {
        "github_sqlite": import_historical_sqlite,
        "blob_api": discover_blob_api,
        "aetna_metadata": discover_aetna_metadata,
        "humana_api": discover_humana,
        "html_index_links": discover_html_indexes,
    }

    for source in sources:
        if args.live_only and source.historical:
            continue
        if args.historical_only and not source.historical:
            continue
        persist_source(conn, source)
        try:
            delta = adapters[source.adapter](
                conn, root, source, timeout=args.timeout, max_bytes=args.max_manifest_bytes,
            )
            stats["files_discovered"] += delta.get("files", 0)
            stats["source_snapshots"] += delta.get("snapshots", 0)
            stats["source_successes"] += 1
            conn.commit()
        except Exception as exc:
            record_error(conn, source.source_key, source.source_url, "source_discovery", exc)
            stats["source_failures"] += 1
            conn.commit()

    if args.parse_indexes:
        rows = conn.execute(
            """SELECT * FROM mrf_files
               WHERE file_type='index'
                 AND historical=0
                 AND file_url LIKE 'http%'
               ORDER BY id"""
        ).fetchall()
        if args.max_indexes:
            rows = rows[: args.max_indexes]
        source_map = {s.source_key: s for s in sources}
        for row in rows:
            source = source_map.get(row["source_key"])
            if not source:
                continue
            source_id = persist_source(conn, source)
            try:
                delta = parse_index_file(
                    conn, root, source, source_id, row,
                    timeout=args.timeout,
                    max_index_bytes=args.max_index_bytes,
                    snapshot_max_bytes=args.snapshot_max_bytes,
                )
                stats["files_discovered"] += delta["files"]
                stats["plans_observed"] += delta["plans"]
                stats["source_snapshots"] += delta["snapshots"]
                stats["index_files_parsed"] += 1
                conn.commit()
            except Exception as exc:
                record_error(conn, source.source_key, row["file_url"], "index_parse", exc)
                stats["index_files_failed"] += 1
                conn.commit()

    stats["mrf_files_total"] = conn.execute("SELECT COUNT(*) FROM mrf_files").fetchone()[0]
    stats["mrf_files_unique_urls"] = conn.execute(
        "SELECT COUNT(DISTINCT file_url) FROM mrf_files"
    ).fetchone()[0]
    stats["in_network_unique_urls"] = conn.execute(
        "SELECT COUNT(DISTINCT file_url) FROM mrf_files WHERE file_type='in_network'"
    ).fetchone()[0]
    stats["index_unique_urls"] = conn.execute(
        "SELECT COUNT(DISTINCT file_url) FROM mrf_files WHERE file_type='index'"
    ).fetchone()[0]
    stats["historical_file_rows"] = conn.execute(
        "SELECT COUNT(*) FROM mrf_files WHERE historical=1"
    ).fetchone()[0]
    stats["unresolved_rows"] = conn.execute(
        "SELECT COUNT(*) FROM mrf_files WHERE parse_status LIKE 'unresolved%'"
    ).fetchone()[0]
    stats["errors"] = conn.execute("SELECT COUNT(*) FROM ingestion_errors").fetchone()[0]
    stats["finished_at"] = utcnow()

    conn.execute(
        "UPDATE ingestion_runs SET finished_at=?,status='complete',stats_json=? WHERE id=?",
        (stats["finished_at"], json.dumps(stats, sort_keys=True), run_id),
    )
    conn.commit()
    (root / "catalog_summary.json").write_text(json.dumps(stats, indent=2) + "\n")
    conn.close()
    return stats


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=".tic_mrf_ledger")
    p.add_argument("--db", default="tic_mrf.sqlite")
    p.add_argument("--sources", default=str(Path(__file__).with_name("sources.json")))
    p.add_argument("--timeout", type=int, default=45)
    p.add_argument("--max-manifest-bytes", type=int, default=100_000_000)
    p.add_argument("--max-index-bytes", type=int, default=2_000_000_000)
    p.add_argument("--snapshot-max-bytes", type=int, default=100_000_000)
    p.add_argument("--max-indexes", type=int, default=25)
    p.add_argument("--parse-indexes", action="store_true")
    p.add_argument("--live-only", action="store_true")
    p.add_argument("--historical-only", action="store_true")
    args = p.parse_args()
    if args.live_only and args.historical_only:
        p.error("--live-only and --historical-only are mutually exclusive")
    stats = run_catalog(args)
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
