#!/usr/bin/env python3
"""CMS Transparency-in-Coverage payer MRF universe ingestion.

Two-stage design:
1) catalog public payer/index/file URLs with immutable source evidence;
2) selectively download and normalize chosen MRFs into provider/rate tables.

The catalog stage is intentionally cheap enough to run broadly. Full MRF download
is always explicit because the national TiC universe is enormous.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import hashlib
import io
import json
import os
import re
import sqlite3
import tempfile
import threading
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

import ijson
import requests
from bs4 import BeautifulSoup


PARSER_VERSION = "tic-payer-mrf-v1"
USER_AGENT = "GitHub-Value-Hunt-TiC-Catalog/1.0"
_thread_local = threading.local()

MRF_HINT_RE = re.compile(
    r"(?:in[-_ ]?network|allowed[-_ ]?amount|out[-_ ]?of[-_ ]?network|"
    r"machine[-_ ]?readable|table[-_ ]?of[-_ ]?contents?|\bindex\b)",
    re.I,
)


@dataclass(frozen=True)
class BlobResult:
    requested_url: str
    final_url: str
    fetched_at: str
    status: int
    content_type: str
    byte_count: int
    sha256: str
    blob_relpath: str
    etag: str | None
    last_modified: str | None


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def session() -> requests.Session:
    s = getattr(_thread_local, "session", None)
    if s is None:
        s = requests.Session()
        s.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
        _thread_local.session = s
    return s


def canonicalize_url(raw: str, base: str | None = None) -> str | None:
    raw = (raw or "").strip()
    if not raw or raw.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    if base:
        raw = urllib.parse.urljoin(base, raw)
    if raw.startswith("//"):
        raw = "https:" + raw
    if not re.match(r"^https?://", raw, re.I):
        return None
    try:
        p = urllib.parse.urlsplit(raw)
    except ValueError:
        return None
    if not p.hostname:
        return None
    scheme = p.scheme.lower()
    host = p.hostname.lower()
    port = f":{p.port}" if p.port and not (
        (scheme == "https" and p.port == 443)
        or (scheme == "http" and p.port == 80)
    ) else ""
    path = re.sub(r"/{2,}", "/", p.path or "/")
    query = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
    query = [
        (k, v)
        for k, v in query
        if k.lower()
        not in {
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "fbclid",
            "gclid",
        }
    ]
    return urllib.parse.urlunsplit(
        (scheme, host + port, path, urllib.parse.urlencode(query, doseq=True), "")
    )


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(Path(__file__).with_name("schema.sql").read_text())
    conn.commit()
    return conn


def load_sources(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("sources", []))


def blob_path(root: Path, digest: str) -> tuple[Path, str]:
    rel = Path("blobs") / "sha256" / digest[:2] / digest
    return root / rel, str(rel)


def _atomic_move_to_hash(root: Path, temp_path: Path, digest: str) -> str:
    dest, rel = blob_path(root, digest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        temp_path.unlink(missing_ok=True)
        return rel
    try:
        os.replace(temp_path, dest)
    except FileExistsError:
        temp_path.unlink(missing_ok=True)
    return rel


def fetch_to_blob(
    url: str,
    root: Path,
    *,
    timeout: int = 45,
    max_bytes: int = 0,
) -> BlobResult:
    root.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="tic-", suffix=".partial", dir=root)
    os.close(fd)
    tmp = Path(tmp_name)
    digest = hashlib.sha256()
    total = 0
    try:
        with session().get(url, timeout=timeout, allow_redirects=True, stream=True) as resp:
            resp.raise_for_status()
            with tmp.open("wb") as fh:
                for chunk in resp.iter_content(1024 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if max_bytes and total > max_bytes:
                        raise ValueError(f"response exceeds max_bytes={max_bytes}")
                    digest.update(chunk)
                    fh.write(chunk)
            sha = digest.hexdigest()
            rel = _atomic_move_to_hash(root, tmp, sha)
            return BlobResult(
                requested_url=url,
                final_url=canonicalize_url(resp.url) or resp.url,
                fetched_at=utcnow(),
                status=resp.status_code,
                content_type=(resp.headers.get("content-type") or "").split(";")[0],
                byte_count=total,
                sha256=sha,
                blob_relpath=rel,
                etag=resp.headers.get("etag"),
                last_modified=resp.headers.get("last-modified"),
            )
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def open_blob(root: Path, relpath: str, source_url: str = ""):
    path = root / relpath
    raw = path.open("rb")
    magic = raw.read(2)
    raw.seek(0)
    if magic == b"\x1f\x8b" or source_url.lower().endswith(".gz"):
        return gzip.GzipFile(fileobj=raw, mode="rb")
    return raw


def infer_kind(url: str, description: str = "") -> str:
    text = f"{url} {description}".lower()
    if "allowed-amount" in text or "allowed_amount" in text or "out-of-network" in text:
        return "allowed-amounts"
    if "in-network" in text or "in_network" in text:
        return "in-network-rates"
    if "index" in text or "table-of-contents" in text or "table_of_contents" in text:
        return "index"
    return "unknown"


def record_error(
    conn: sqlite3.Connection,
    *,
    stage: str,
    error_type: str,
    detail: str,
    source_id: str | None = None,
    url: str | None = None,
) -> None:
    conn.execute(
        """INSERT INTO errors(occurred_at, stage, source_id, url, error_type, detail)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (utcnow(), stage, source_id, url, error_type, detail[:4000]),
    )
    conn.commit()


def upsert_source(conn: sqlite3.Connection, cfg: dict[str, Any]) -> int:
    now = utcnow()
    conn.execute(
        """INSERT OR IGNORE INTO sources(
             source_id,payer_family,resolver,seed_url,config_json,first_seen_at,last_seen_at
           ) VALUES (?,?,?,?,?,?,?)""",
        (
            cfg["source_id"],
            cfg["payer_family"],
            cfg["resolver"],
            cfg["url"],
            json.dumps(cfg, sort_keys=True),
            now,
            now,
        ),
    )
    conn.execute(
        """UPDATE sources SET payer_family=?,resolver=?,seed_url=?,config_json=?,last_seen_at=?
           WHERE source_id=?""",
        (
            cfg["payer_family"],
            cfg["resolver"],
            cfg["url"],
            json.dumps(cfg, sort_keys=True),
            now,
            cfg["source_id"],
        ),
    )
    row = conn.execute(
        "SELECT id FROM sources WHERE source_id=?", (cfg["source_id"],)
    ).fetchone()
    conn.commit()
    return int(row[0])


def persist_observation(
    conn: sqlite3.Connection,
    source_db_id: int,
    result: BlobResult,
    *,
    parser_status: str,
    meta: dict[str, str | None] | None = None,
) -> int:
    meta = meta or {}
    conn.execute(
        """INSERT OR IGNORE INTO source_observations(
             source_id,requested_url,final_url,fetched_at,http_status,content_type,
             byte_count,sha256,blob_relpath,etag,last_modified,parser_status,
             reporting_entity_name,reporting_entity_type,last_updated_on,schema_version
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            source_db_id,
            result.requested_url,
            result.final_url,
            result.fetched_at,
            result.status,
            result.content_type,
            result.byte_count,
            result.sha256,
            result.blob_relpath,
            result.etag,
            result.last_modified,
            parser_status,
            meta.get("reporting_entity_name"),
            meta.get("reporting_entity_type"),
            meta.get("last_updated_on"),
            meta.get("version"),
        ),
    )
    row = conn.execute(
        """SELECT id FROM source_observations
           WHERE source_id=? AND requested_url=? AND sha256=?""",
        (source_db_id, result.requested_url, result.sha256),
    ).fetchone()
    conn.commit()
    return int(row[0])


def plan_key(plan: dict[str, Any]) -> str:
    identity = {
        "plan_name": plan.get("plan_name"),
        "plan_sponsor_name": plan.get("plan_sponsor_name"),
        "issuer_name": plan.get("issuer_name"),
        "plan_id_type": plan.get("plan_id_type"),
        "plan_id": plan.get("plan_id"),
        "plan_market_type": plan.get("plan_market_type"),
    }
    raw = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def upsert_plan(conn: sqlite3.Connection, plan: dict[str, Any]) -> int:
    key = plan_key(plan)
    conn.execute(
        """INSERT OR IGNORE INTO plans(
             plan_key,plan_name,plan_sponsor_name,issuer_name,plan_id_type,plan_id,
             plan_market_type
           ) VALUES (?,?,?,?,?,?,?)""",
        (
            key,
            plan.get("plan_name"),
            plan.get("plan_sponsor_name"),
            plan.get("issuer_name"),
            plan.get("plan_id_type"),
            plan.get("plan_id"),
            plan.get("plan_market_type"),
        ),
    )
    row = conn.execute("SELECT id FROM plans WHERE plan_key=?", (key,)).fetchone()
    return int(row[0])


def upsert_catalog_file(
    conn: sqlite3.Connection,
    *,
    url: str,
    kind: str,
    description: str | None,
    observation_id: int | None,
    payer_family: str | None,
    reporting_entity_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> int:
    now = utcnow()
    metadata = metadata or {}
    conn.execute(
        """INSERT OR IGNORE INTO catalog_files(
             file_url,file_kind,description,discovered_at,last_seen_at,
             source_observation_id,payer_family,reporting_entity_name,
             content_length,content_type,etag,last_modified,http_status,metadata_status
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            url,
            kind,
            description,
            now,
            now,
            observation_id,
            payer_family,
            reporting_entity_name,
            metadata.get("content_length"),
            metadata.get("content_type"),
            metadata.get("etag"),
            metadata.get("last_modified"),
            metadata.get("http_status"),
            metadata.get("metadata_status", "unprobed"),
        ),
    )
    conn.execute(
        """UPDATE catalog_files SET
             file_kind=CASE WHEN file_kind='unknown' THEN ? ELSE file_kind END,
             description=COALESCE(description,?),
             last_seen_at=?,
             source_observation_id=COALESCE(?,source_observation_id),
             payer_family=COALESCE(?,payer_family),
             reporting_entity_name=COALESCE(?,reporting_entity_name),
             content_length=COALESCE(?,content_length),
             content_type=COALESCE(?,content_type),
             etag=COALESCE(?,etag),
             last_modified=COALESCE(?,last_modified),
             http_status=COALESCE(?,http_status),
             metadata_status=CASE WHEN ?!='unprobed' THEN ? ELSE metadata_status END
           WHERE file_url=?""",
        (
            kind,
            description,
            now,
            observation_id,
            payer_family,
            reporting_entity_name,
            metadata.get("content_length"),
            metadata.get("content_type"),
            metadata.get("etag"),
            metadata.get("last_modified"),
            metadata.get("http_status"),
            metadata.get("metadata_status", "unprobed"),
            metadata.get("metadata_status", "unprobed"),
            url,
        ),
    )
    row = conn.execute(
        "SELECT id FROM catalog_files WHERE file_url=?", (url,)
    ).fetchone()
    conn.commit()
    return int(row[0])


def parse_toc_catalog(
    conn: sqlite3.Connection,
    *,
    root: Path,
    observation_id: int,
    result: BlobResult,
    payer_family: str,
) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    counts = {"structures": 0, "plans": 0, "files": 0, "links": 0}

    with open_blob(root, result.blob_relpath, result.final_url) as fh:
        for prefix, event, value in ijson.parse(fh):
            if event in {"string", "number", "boolean", "null"} and prefix in {
                "reporting_entity_name",
                "reporting_entity_type",
                "last_updated_on",
                "version",
            }:
                meta[prefix] = None if value is None else str(value)
            if prefix == "reporting_structure" and event == "start_array":
                break

    with open_blob(root, result.blob_relpath, result.final_url) as fh:
        for struct in ijson.items(fh, "reporting_structure.item"):
            counts["structures"] += 1
            plan_ids: list[int] = []
            for plan in struct.get("reporting_plans") or []:
                plan_ids.append(upsert_plan(conn, plan))
                counts["plans"] += 1

            refs: list[tuple[str, dict[str, Any]]] = []
            for item in struct.get("in_network_files") or []:
                refs.append(("in-network-rates", item))
            if struct.get("allowed_amount_file"):
                refs.append(("allowed-amounts", struct["allowed_amount_file"]))

            for kind, item in refs:
                url = canonicalize_url(str(item.get("location") or ""))
                if not url:
                    continue
                file_id = upsert_catalog_file(
                    conn,
                    url=url,
                    kind=kind,
                    description=item.get("description"),
                    observation_id=observation_id,
                    payer_family=payer_family,
                    reporting_entity_name=meta.get("reporting_entity_name"),
                )
                counts["files"] += 1
                for pid in plan_ids:
                    conn.execute(
                        """INSERT OR IGNORE INTO file_plan_links(
                             catalog_file_id,plan_id,source_observation_id
                           ) VALUES (?,?,?)""",
                        (file_id, pid, observation_id),
                    )
                    counts["links"] += 1
            if counts["structures"] % 500 == 0:
                conn.commit()
    conn.commit()
    return {**meta, **counts}


def html_candidates(root: Path, result: BlobResult, cfg: dict[str, Any]) -> list[tuple[str, str]]:
    path = root / result.blob_relpath
    if path.stat().st_size > 50_000_000:
        raise ValueError("HTML landing page exceeds 50MB safety limit")
    text = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(text, "html.parser")
    pattern = re.compile(cfg.get("link_filter") or MRF_HINT_RE.pattern, re.I)
    found: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        label = a.get_text(" ", strip=True)
        url = canonicalize_url(a["href"], result.final_url)
        if not url:
            continue
        if pattern.search(f"{label} {url}"):
            found.append((url, label))
    # Some TiC pages embed URLs in script/config JSON rather than anchors.
    for raw in re.findall(r"https://[^\s\"'<>]+", text):
        url = canonicalize_url(raw.rstrip("\\,);"))
        if url and pattern.search(url):
            found.append((url, "embedded URL"))
    dedup: dict[str, str] = {}
    for url, label in found:
        dedup.setdefault(url, label)
    return sorted(dedup.items())


def metadata_json_candidates(
    root: Path, result: BlobResult, cfg: dict[str, Any]
) -> list[tuple[str, str, dict[str, Any]]]:
    path = root / result.blob_relpath
    payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    base = cfg.get("base_url") or result.final_url
    files = payload.get("files") if isinstance(payload, dict) else None
    if not isinstance(files, list):
        raise ValueError("metadata JSON has no files[] list")
    out = []
    for item in files:
        if not isinstance(item, dict):
            continue
        candidate = (
            item.get("url")
            or item.get("location")
            or item.get("downloadUrl")
            or item.get("filePath")
        )
        url = canonicalize_url(str(candidate or ""), base)
        if not url:
            continue
        description = str(
            item.get("description")
            or item.get("fileName")
            or item.get("name")
            or item.get("filePath")
            or ""
        )
        md = {
            "content_length": item.get("fileSize") or item.get("size"),
            "etag": item.get("etag"),
            "last_modified": item.get("lastModified") or item.get("last_modified"),
            "metadata_status": "metadata_json",
        }
        out.append((url, description, md))
    return out


def azure_month_prefix(template: str) -> str:
    now = datetime.now(timezone.utc)
    return template.replace("{YYYY-MM}", now.strftime("%Y-%m"))


def azure_list(
    cfg: dict[str, Any],
    root: Path,
    conn: sqlite3.Connection,
    source_db_id: int,
    *,
    max_pages: int,
    timeout: int,
) -> tuple[int, int]:
    base = cfg["url"].rstrip("/")
    prefix = azure_month_prefix(cfg.get("monthly_prefix") or "")
    marker = ""
    pages = files = 0

    while pages < max_pages:
        params = {
            "restype": "container",
            "comp": "list",
            "prefix": prefix,
            "maxresults": "5000",
        }
        if marker:
            params["marker"] = marker
        listing_url = base + "?" + urllib.parse.urlencode(params)
        result = fetch_to_blob(listing_url, root, timeout=timeout, max_bytes=100_000_000)
        obs_id = persist_observation(
            conn, source_db_id, result, parser_status="parsed:azure_blob_list"
        )
        xml_path = root / result.blob_relpath
        tree = ET.parse(xml_path)
        root_xml = tree.getroot()
        for blob in root_xml.findall(".//Blob"):
            name = blob.findtext("Name") or ""
            if not name:
                continue
            url = canonicalize_url(base + "/" + urllib.parse.quote(name, safe="/:._-"))
            if not url:
                continue
            props = blob.find("Properties")
            md: dict[str, Any] = {"metadata_status": "azure_listing"}
            if props is not None:
                length = props.findtext("Content-Length")
                md["content_length"] = int(length) if length and length.isdigit() else None
                md["content_type"] = props.findtext("Content-Type")
                md["etag"] = props.findtext("Etag")
                md["last_modified"] = props.findtext("Last-Modified")
                md["http_status"] = 200
            upsert_catalog_file(
                conn,
                url=url,
                kind=infer_kind(url, name),
                description=name,
                observation_id=obs_id,
                payer_family=cfg["payer_family"],
                metadata=md,
            )
            files += 1
        marker = root_xml.findtext("NextMarker") or ""
        pages += 1
        if not marker:
            break
    return pages, files


def catalog_source(
    conn: sqlite3.Connection,
    root: Path,
    cfg: dict[str, Any],
    *,
    timeout: int,
    max_list_pages: int,
) -> dict[str, Any]:
    source_db_id = upsert_source(conn, cfg)
    resolver = cfg["resolver"]
    stats = {"source_id": cfg["source_id"], "observations": 0, "files": 0, "plans": 0}

    if resolver == "azure_blob_container":
        pages, files = azure_list(
            cfg, root, conn, source_db_id, max_pages=max_list_pages, timeout=timeout
        )
        stats.update({"observations": pages, "files": files})
        return stats

    result = fetch_to_blob(cfg["url"], root, timeout=timeout, max_bytes=500_000_000)
    obs_id = persist_observation(
        conn, source_db_id, result, parser_status=f"fetched:{resolver}"
    )
    stats["observations"] = 1

    if resolver == "html_links":
        candidates = html_candidates(root, result, cfg)
        for url, desc in candidates:
            kind = infer_kind(url, desc)
            upsert_catalog_file(
                conn,
                url=url,
                kind=kind,
                description=desc,
                observation_id=obs_id,
                payer_family=cfg["payer_family"],
            )
            stats["files"] += 1
        if not candidates:
            record_error(
                conn,
                stage="catalog",
                source_id=cfg["source_id"],
                url=cfg["url"],
                error_type="NoMRFLinksResolved",
                detail="Landing page fetched but no public MRF/index links were discovered.",
            )
        return stats

    if resolver == "metadata_json":
        candidates = metadata_json_candidates(root, result, cfg)
        for url, desc, md in candidates:
            upsert_catalog_file(
                conn,
                url=url,
                kind=infer_kind(url, desc),
                description=desc,
                observation_id=obs_id,
                payer_family=cfg["payer_family"],
                metadata=md,
            )
            stats["files"] += 1
        return stats

    if resolver == "direct_index":
        meta = parse_toc_catalog(
            conn,
            root=root,
            observation_id=obs_id,
            result=result,
            payer_family=cfg["payer_family"],
        )
        persist_observation(
            conn,
            source_db_id,
            result,
            parser_status="parsed:cms_toc",
            meta=meta,
        )
        stats["files"] = int(meta.get("files") or 0)
        stats["plans"] = int(meta.get("plans") or 0)
        return stats

    raise ValueError(f"unsupported resolver: {resolver}")


def probe_one(url: str, timeout: int) -> dict[str, Any]:
    try:
        resp = session().head(url, allow_redirects=True, timeout=timeout)
        if resp.status_code >= 400 or not resp.headers.get("content-length"):
            resp.close()
            resp = session().get(
                url,
                allow_redirects=True,
                timeout=timeout,
                headers={"Range": "bytes=0-0"},
                stream=True,
            )
        length = resp.headers.get("content-length")
        result = {
            "http_status": resp.status_code,
            "content_length": int(length) if length and length.isdigit() else None,
            "content_type": (resp.headers.get("content-type") or "").split(";")[0],
            "etag": resp.headers.get("etag"),
            "last_modified": resp.headers.get("last-modified"),
            "metadata_status": "probed",
        }
        resp.close()
        return result
    except Exception as exc:
        return {
            "metadata_status": "probe_error",
            "error_type": type(exc).__name__,
            "detail": str(exc),
        }


def probe_catalog(
    conn: sqlite3.Connection,
    *,
    workers: int,
    timeout: int,
    limit: int,
) -> dict[str, int]:
    rows = conn.execute(
        """SELECT id,file_url FROM catalog_files
           WHERE metadata_status IN ('unprobed','probe_error')
           ORDER BY id"""
    ).fetchall()
    if limit:
        rows = rows[:limit]
    stats = {"targets": len(rows), "probed": 0, "errors": 0}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(probe_one, url, timeout): (fid, url) for fid, url in rows}
        for fut in concurrent.futures.as_completed(futs):
            fid, url = futs[fut]
            md = fut.result()
            if md["metadata_status"] == "probe_error":
                stats["errors"] += 1
                record_error(
                    conn,
                    stage="probe",
                    url=url,
                    error_type=md["error_type"],
                    detail=md["detail"],
                )
                conn.execute(
                    "UPDATE catalog_files SET metadata_status='probe_error' WHERE id=?",
                    (fid,),
                )
            else:
                stats["probed"] += 1
                conn.execute(
                    """UPDATE catalog_files SET
                         content_length=?,content_type=?,etag=?,last_modified=?,
                         http_status=?,metadata_status='probed'
                       WHERE id=?""",
                    (
                        md["content_length"],
                        md["content_type"],
                        md["etag"],
                        md["last_modified"],
                        md["http_status"],
                        fid,
                    ),
                )
            conn.commit()
    return stats


def _read_head_metadata(root: Path, relpath: str, source_url: str) -> dict[str, str | None]:
    """Best-effort top-level scalar extraction from an initial decompressed window."""
    meta = {
        "reporting_entity_name": None,
        "reporting_entity_type": None,
        "last_updated_on": None,
        "version": None,
        "plan_name": None,
        "issuer_name": None,
        "plan_sponsor_name": None,
        "plan_id_type": None,
        "plan_id": None,
        "plan_market_type": None,
    }
    with open_blob(root, relpath, source_url) as fh:
        prefix = fh.read(4_000_000).decode("utf-8", errors="replace")
    for key in meta:
        match = re.search(
            rf'"{re.escape(key)}"\s*:\s*"([^"]*)"', prefix, re.I
        )
        if match:
            meta[key] = match.group(1)
    return meta


def _download_or_import(
    source: str,
    root: Path,
    *,
    timeout: int,
    max_bytes: int,
) -> tuple[BlobResult, str | None]:
    if re.match(r"^https?://", source, re.I):
        return fetch_to_blob(source, root, timeout=timeout, max_bytes=max_bytes), source
    src = Path(source)
    digest = hashlib.sha256()
    fd, tmp_name = tempfile.mkstemp(prefix="tic-local-", suffix=".partial", dir=root)
    os.close(fd)
    tmp = Path(tmp_name)
    total = 0
    with src.open("rb") as inp, tmp.open("wb") as out:
        for chunk in iter(lambda: inp.read(1024 * 1024), b""):
            total += len(chunk)
            if max_bytes and total > max_bytes:
                tmp.unlink(missing_ok=True)
                raise ValueError(f"file exceeds max_bytes={max_bytes}")
            digest.update(chunk)
            out.write(chunk)
    sha = digest.hexdigest()
    rel = _atomic_move_to_hash(root, tmp, sha)
    return (
        BlobResult(
            requested_url=f"file://{src.name}",
            final_url=f"file://{src.name}",
            fetched_at=utcnow(),
            status=200,
            content_type="application/gzip" if src.suffix == ".gz" else "application/json",
            byte_count=total,
            sha256=sha,
            blob_relpath=rel,
            etag=None,
            last_modified=None,
        ),
        None,
    )


def create_snapshot(
    conn: sqlite3.Connection,
    *,
    result: BlobResult,
    source_url: str | None,
    kind: str,
    meta: dict[str, Any],
) -> int:
    catalog_id = None
    if source_url:
        row = conn.execute(
            "SELECT id FROM catalog_files WHERE file_url=?", (source_url,)
        ).fetchone()
        if row:
            catalog_id = int(row[0])
    conn.execute(
        """INSERT OR IGNORE INTO mrf_snapshots(
             catalog_file_id,requested_url,source_file_name,fetched_at,sha256,blob_relpath,
             byte_count,content_type,reporting_entity_name,reporting_entity_type,
             last_updated_on,schema_version,plan_name,issuer_name,plan_sponsor_name,
             plan_id_type,plan_id,plan_market_type,mrf_kind,parser_version
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            catalog_id,
            source_url or result.requested_url,
            Path(urllib.parse.urlsplit(result.final_url).path).name,
            result.fetched_at,
            result.sha256,
            result.blob_relpath,
            result.byte_count,
            result.content_type,
            meta.get("reporting_entity_name"),
            meta.get("reporting_entity_type"),
            meta.get("last_updated_on"),
            meta.get("version"),
            meta.get("plan_name"),
            meta.get("issuer_name"),
            meta.get("plan_sponsor_name"),
            meta.get("plan_id_type"),
            meta.get("plan_id"),
            meta.get("plan_market_type"),
            kind,
            PARSER_VERSION,
        ),
    )
    row = conn.execute(
        "SELECT id FROM mrf_snapshots WHERE sha256=? AND mrf_kind=? AND parser_version=?",
        (result.sha256, kind, PARSER_VERSION),
    ).fetchone()
    conn.commit()
    return int(row[0])


def parse_provider_groups(
    conn: sqlite3.Connection,
    *,
    root: Path,
    snapshot_id: int,
    relpath: str,
    source_url: str,
) -> dict[str, int]:
    stats = {"provider_groups": 0, "provider_entities": 0}
    with open_blob(root, relpath, source_url) as fh:
        for idx, item in enumerate(ijson.items(fh, "provider_references.item")):
            pgid = item.get("provider_group_id")
            if pgid is None:
                continue
            conn.execute(
                """INSERT OR IGNORE INTO provider_groups(
                     snapshot_id,provider_group_id,network_names_json,evidence_locator
                   ) VALUES (?,?,?,?)""",
                (
                    snapshot_id,
                    int(pgid),
                    json.dumps(item.get("network_name") or [], separators=(",", ":")),
                    f"provider_references[{idx}]",
                ),
            )
            row = conn.execute(
                """SELECT id FROM provider_groups
                   WHERE snapshot_id=? AND provider_group_id=?""",
                (snapshot_id, int(pgid)),
            ).fetchone()
            pgrow = int(row[0])
            stats["provider_groups"] += 1
            for group in item.get("provider_groups") or []:
                tin = group.get("tin") or {}
                npis = group.get("npi") or [None]
                for npi in npis:
                    conn.execute(
                        """INSERT OR IGNORE INTO provider_entities(
                             provider_group_row_id,tin_type,tin_value,business_name,npi
                           ) VALUES (?,?,?,?,?)""",
                        (
                            pgrow,
                            tin.get("type"),
                            tin.get("value"),
                            tin.get("business_name"),
                            str(npi) if npi is not None else None,
                        ),
                    )
                    stats["provider_entities"] += 1
            if idx and idx % 5000 == 0:
                conn.commit()
    conn.commit()
    return stats


def normalize_in_network(
    conn: sqlite3.Connection,
    *,
    root: Path,
    snapshot_id: int,
    relpath: str,
    source_url: str,
    code_filter: set[str] | None,
) -> dict[str, int]:
    stats = {"billing_items": 0, "rate_rows": 0}
    with open_blob(root, relpath, source_url) as fh:
        for idx, item in enumerate(ijson.items(fh, "in_network.item")):
            code = str(item.get("billing_code") or "")
            if not code or (code_filter and code.upper() not in code_filter):
                continue
            stats["billing_items"] += 1
            for nr_idx, nr in enumerate(item.get("negotiated_rates") or []):
                refs = nr.get("provider_references") or [None]
                prices = nr.get("negotiated_prices") or []
                for pr_idx, price in enumerate(prices):
                    rate = price.get("negotiated_rate")
                    if rate is None:
                        continue
                    for ref in refs:
                        conn.execute(
                            """INSERT INTO negotiated_rates(
                                 snapshot_id,billing_code_type,billing_code_type_version,
                                 billing_code,description,negotiation_arrangement,
                                 provider_group_id,negotiated_type,negotiated_rate,
                                 expiration_date,billing_class,setting,service_codes_json,
                                 modifiers_json,additional_information,evidence_locator
                               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (
                                snapshot_id,
                                item.get("billing_code_type"),
                                item.get("billing_code_type_version"),
                                code,
                                item.get("description"),
                                item.get("negotiation_arrangement"),
                                int(ref) if ref is not None else None,
                                price.get("negotiated_type"),
                                str(rate),
                                price.get("expiration_date"),
                                price.get("billing_class"),
                                price.get("setting"),
                                json.dumps(price.get("service_code") or [], separators=(",", ":")),
                                json.dumps(price.get("billing_code_modifier") or [], separators=(",", ":")),
                                price.get("additional_information"),
                                f"in_network[{idx}].negotiated_rates[{nr_idx}].negotiated_prices[{pr_idx}]",
                            ),
                        )
                        stats["rate_rows"] += 1
            if idx and idx % 1000 == 0:
                conn.commit()
    conn.commit()
    return stats


def normalize_allowed(
    conn: sqlite3.Connection,
    *,
    root: Path,
    snapshot_id: int,
    relpath: str,
    source_url: str,
    code_filter: set[str] | None,
) -> dict[str, int]:
    stats = {"billing_items": 0, "allowed_rows": 0}
    with open_blob(root, relpath, source_url) as fh:
        for idx, item in enumerate(ijson.items(fh, "out_of_network.item")):
            code = str(item.get("billing_code") or "")
            if not code or (code_filter and code.upper() not in code_filter):
                continue
            stats["billing_items"] += 1
            for aa_idx, aa in enumerate(item.get("allowed_amounts") or []):
                tin = aa.get("tin") or {}
                for pay_idx, payment in enumerate(aa.get("payments") or []):
                    amount = payment.get("allowed_amount")
                    if amount is None:
                        continue
                    providers = payment.get("providers") or [{}]
                    for provider in providers:
                        npis = provider.get("npi") or [None]
                        for npi in npis:
                            conn.execute(
                                """INSERT INTO allowed_amounts(
                                     snapshot_id,billing_code_type,billing_code_type_version,
                                     billing_code,description,tin_type,tin_value,billing_class,
                                     service_codes_json,modifiers_json,allowed_amount,billed_charge,
                                     npi,evidence_locator
                                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                (
                                    snapshot_id,
                                    item.get("billing_code_type"),
                                    item.get("billing_code_type_version"),
                                    code,
                                    item.get("description"),
                                    tin.get("type"),
                                    tin.get("value"),
                                    aa.get("billing_class"),
                                    json.dumps(aa.get("service_code") or [], separators=(",", ":")),
                                    json.dumps(payment.get("billing_code_modifier") or [], separators=(",", ":")),
                                    str(amount),
                                    str(provider.get("billed_charge")) if provider.get("billed_charge") is not None else None,
                                    str(npi) if npi is not None else None,
                                    f"out_of_network[{idx}].allowed_amounts[{aa_idx}].payments[{pay_idx}]",
                                ),
                            )
                            stats["allowed_rows"] += 1
            if idx and idx % 1000 == 0:
                conn.commit()
    conn.commit()
    return stats


def command_catalog(args: argparse.Namespace) -> int:
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    db = Path(args.db)
    if not db.is_absolute():
        db = out / db
    conn = init_db(db)
    run = conn.execute(
        "INSERT INTO runs(started_at,mode,status) VALUES (?,?,?)",
        (utcnow(), "catalog", "running"),
    )
    run_id = int(run.lastrowid)
    conn.commit()

    stats = {"sources": 0, "source_errors": 0, "files": 0, "plans": 0}
    for cfg in load_sources(Path(args.sources)):
        try:
            result = catalog_source(
                conn,
                out,
                cfg,
                timeout=args.timeout,
                max_list_pages=args.max_list_pages,
            )
            stats["sources"] += 1
            stats["files"] += int(result.get("files") or 0)
            stats["plans"] += int(result.get("plans") or 0)
            print(json.dumps(result), flush=True)
        except Exception as exc:
            stats["source_errors"] += 1
            record_error(
                conn,
                stage="catalog_source",
                source_id=cfg.get("source_id"),
                url=cfg.get("url"),
                error_type=type(exc).__name__,
                detail=str(exc),
            )
            print(
                json.dumps(
                    {
                        "source_id": cfg.get("source_id"),
                        "error": type(exc).__name__,
                        "detail": str(exc),
                    }
                ),
                flush=True,
            )

    if args.probe:
        stats["probe"] = probe_catalog(
            conn, workers=args.workers, timeout=args.timeout, limit=args.probe_limit
        )

    stats["catalog_file_rows"] = conn.execute(
        "SELECT COUNT(*) FROM catalog_files"
    ).fetchone()[0]
    stats["plan_rows"] = conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
    stats["unique_source_hashes"] = conn.execute(
        "SELECT COUNT(DISTINCT sha256) FROM source_observations WHERE sha256 IS NOT NULL"
    ).fetchone()[0]
    conn.execute(
        "UPDATE runs SET finished_at=?,status='complete',stats_json=? WHERE id=?",
        (utcnow(), json.dumps(stats, sort_keys=True), run_id),
    )
    conn.commit()
    (out / "catalog_summary.json").write_text(
        json.dumps(stats, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(stats, indent=2, sort_keys=True))
    return 0


def command_normalize(args: argparse.Namespace) -> int:
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    db = Path(args.db)
    if not db.is_absolute():
        db = out / db
    conn = init_db(db)

    result, source_url = _download_or_import(
        args.source, out, timeout=args.timeout, max_bytes=args.max_bytes
    )
    kind = args.kind or infer_kind(args.source)
    if kind not in {"in-network-rates", "allowed-amounts"}:
        raise SystemExit("--kind must be supplied when file type cannot be inferred")
    meta = _read_head_metadata(out, result.blob_relpath, result.final_url)
    snapshot_id = create_snapshot(
        conn,
        result=result,
        source_url=source_url,
        kind=kind,
        meta=meta,
    )
    code_filter = (
        {x.strip().upper() for x in args.codes.split(",") if x.strip()}
        if args.codes
        else None
    )
    stats: dict[str, Any] = {
        "snapshot_id": snapshot_id,
        "sha256": result.sha256,
        "byte_count": result.byte_count,
        "kind": kind,
        "meta": meta,
    }
    if kind == "in-network-rates":
        if not args.skip_providers:
            stats.update(
                parse_provider_groups(
                    conn,
                    root=out,
                    snapshot_id=snapshot_id,
                    relpath=result.blob_relpath,
                    source_url=result.final_url,
                )
            )
        stats.update(
            normalize_in_network(
                conn,
                root=out,
                snapshot_id=snapshot_id,
                relpath=result.blob_relpath,
                source_url=result.final_url,
                code_filter=code_filter,
            )
        )
    else:
        stats.update(
            normalize_allowed(
                conn,
                root=out,
                snapshot_id=snapshot_id,
                relpath=result.blob_relpath,
                source_url=result.final_url,
                code_filter=code_filter,
            )
        )
    report = out / f"normalize_{result.sha256[:16]}.json"
    report.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n")
    print(json.dumps(stats, indent=2, sort_keys=True))
    return 0


def command_summary(args: argparse.Namespace) -> int:
    conn = sqlite3.connect(args.db)
    payload = {
        "sources": conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
        "source_observations": conn.execute(
            "SELECT COUNT(*) FROM source_observations"
        ).fetchone()[0],
        "unique_source_hashes": conn.execute(
            "SELECT COUNT(DISTINCT sha256) FROM source_observations WHERE sha256 IS NOT NULL"
        ).fetchone()[0],
        "catalog_files": conn.execute("SELECT COUNT(*) FROM catalog_files").fetchone()[0],
        "in_network_files": conn.execute(
            "SELECT COUNT(*) FROM catalog_files WHERE file_kind='in-network-rates'"
        ).fetchone()[0],
        "allowed_amount_files": conn.execute(
            "SELECT COUNT(*) FROM catalog_files WHERE file_kind='allowed-amounts'"
        ).fetchone()[0],
        "plans": conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0],
        "mrf_snapshots": conn.execute("SELECT COUNT(*) FROM mrf_snapshots").fetchone()[0],
        "provider_groups": conn.execute("SELECT COUNT(*) FROM provider_groups").fetchone()[0],
        "provider_entities": conn.execute("SELECT COUNT(*) FROM provider_entities").fetchone()[0],
        "negotiated_rates": conn.execute("SELECT COUNT(*) FROM negotiated_rates").fetchone()[0],
        "allowed_amount_rows": conn.execute("SELECT COUNT(*) FROM allowed_amounts").fetchone()[0],
        "errors": conn.execute("SELECT COUNT(*) FROM errors").fetchone()[0],
        "files_by_payer": conn.execute(
            """SELECT COALESCE(payer_family,'(unknown)'),COUNT(*)
               FROM catalog_files GROUP BY 1 ORDER BY 2 DESC LIMIT 30"""
        ).fetchall(),
        "files_by_kind": conn.execute(
            "SELECT file_kind,COUNT(*) FROM catalog_files GROUP BY 1 ORDER BY 2 DESC"
        ).fetchall(),
        "error_types": conn.execute(
            """SELECT stage||':'||error_type,COUNT(*) FROM errors
               GROUP BY 1 ORDER BY 2 DESC LIMIT 30"""
        ).fetchall(),
    }
    print(json.dumps(payload, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="TiC payer MRF universe ingestion")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("catalog")
    c.add_argument("--sources", default=str(Path(__file__).with_name("sources.json")))
    c.add_argument("--out", default=".tic_payer_mrf")
    c.add_argument("--db", default="ledger.sqlite")
    c.add_argument("--timeout", type=int, default=45)
    c.add_argument("--max-list-pages", type=int, default=50)
    c.add_argument("--probe", action="store_true")
    c.add_argument("--probe-limit", type=int, default=0)
    c.add_argument("--workers", type=int, default=8)
    c.set_defaults(func=command_catalog)

    n = sub.add_parser("normalize")
    n.add_argument("source", help="MRF URL or local .json/.json.gz")
    n.add_argument("--kind", choices=["in-network-rates", "allowed-amounts"])
    n.add_argument("--codes", help="comma-separated CPT/HCPCS/etc codes to retain")
    n.add_argument("--skip-providers", action="store_true")
    n.add_argument("--out", default=".tic_payer_mrf")
    n.add_argument("--db", default="ledger.sqlite")
    n.add_argument("--timeout", type=int, default=90)
    n.add_argument("--max-bytes", type=int, default=0)
    n.set_defaults(func=command_normalize)

    s = sub.add_parser("summary")
    s.add_argument("--db", required=True)
    s.set_defaults(func=command_summary)
    return p


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
