from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import requests

USER_AGENT = "CMS-TiC-Ledger/1.0 (public machine-readable price transparency research)"
PARSER_VERSION = "cms-tic-ledger-v1"
_thread_local = threading.local()


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def stable_key(*parts: object, length: int = 32) -> str:
    raw = "|".join("" if p is None else str(p) for p in parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:length]


def session() -> requests.Session:
    value = getattr(_thread_local, "session", None)
    if value is None:
        value = requests.Session()
        value.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
        _thread_local.session = value
    return value


def canonicalize_url(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw or raw.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    if raw.startswith("//"):
        raw = "https:" + raw
    if not re.match(r"^https?://", raw, re.I):
        return None
    try:
        p = urlsplit(raw)
    except ValueError:
        return None
    if not p.hostname:
        return None
    query = [
        (k, v)
        for k, v in parse_qsl(p.query, keep_blank_values=True)
        if k.lower() not in {"utm_source", "utm_medium", "utm_campaign", "gclid", "fbclid"}
    ]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or "/", urlencode(query), ""))


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.commit()
    return conn


def write_blob(output_root: Path, digest: str, raw: bytes) -> str:
    rel = Path("blobs") / "sha256" / digest[:2] / digest
    path = output_root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return str(rel)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        tmp.write_bytes(raw)
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
    return str(rel)


def fetch_small(url: str, *, timeout: int = 30, max_bytes: int = 50_000_000):
    with session().get(url, timeout=timeout, allow_redirects=True, stream=True) as resp:
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


def head_metadata(url: str, *, timeout: int = 20) -> dict:
    try:
        resp = session().head(url, timeout=timeout, allow_redirects=True)
        if resp.status_code >= 400 or "content-length" not in resp.headers:
            raise requests.HTTPError(f"HEAD {resp.status_code}")
    except Exception:
        # A bounded range request often works on storage/CDN endpoints where HEAD is blocked.
        resp = session().get(
            url,
            timeout=timeout,
            allow_redirects=True,
            stream=True,
            headers={"Range": "bytes=0-0"},
        )
    length = resp.headers.get("content-range") or resp.headers.get("content-length")
    size = None
    if length:
        m = re.search(r"/(\d+)$", length)
        if m:
            size = int(m.group(1))
        elif str(length).isdigit():
            size = int(length)
    result = {
        "status": resp.status_code,
        "final_url": str(resp.url),
        "content_type": resp.headers.get("content-type", "").split(";")[0].strip().lower(),
        "content_length": size,
        "etag": resp.headers.get("etag"),
        "last_modified": resp.headers.get("last-modified"),
    }
    resp.close()
    return result
