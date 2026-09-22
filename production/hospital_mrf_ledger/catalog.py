#!/usr/bin/env python3
"""Catalog CMS Hospital Price Transparency MRFs with immutable provenance."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import tempfile
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Iterable

import ijson
import requests


USER_AGENT = "RecoveryWorks-Hospital-MRF-Ledger/1.0 (public price-transparency research)"
CMS_REFERENCE = {
    "authority_key": "cms_hpt_v3",
    "repository": "CMSgov/hospital-price-transparency",
    "revision": "5333564a710f80d7740180b9ffab8dbdcba9b502",
    "schema_version": "3.0",
    "schema_path": "documentation/JSON/schemas/V3.0.0_Hospital_price_transparency_schema.json",
    "schema_blob_sha": "11043f073ab24e638c91bde1b8bcf73e4733b296",
}
TXT_KEYS = {"location-name", "source-page-url", "mrf-url", "contact-name", "contact-email"}


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_url(url: str, base: str | None = None) -> str:
    url = (url or "").strip()
    if base:
        url = urllib.parse.urljoin(base, url)
    p = urllib.parse.urlsplit(url)
    if not p.scheme:
        return url
    q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True)
         if not k.lower().startswith("utm_")]
    return urllib.parse.urlunsplit(
        (p.scheme.lower(), p.netloc.lower(), p.path, urllib.parse.urlencode(q, doseq=True), "")
    )


def root_url(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    if p.scheme not in {"http", "https"} or not p.netloc:
        raise ValueError(f"not an http(s) URL: {url}")
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower(), "/", "", ""))


def source_key(url: str) -> str:
    host = urllib.parse.urlsplit(root_url(url)).netloc.lower()
    return re.sub(r"[^a-z0-9._-]+", "-", host)


def blob_path(root: Path, digest: str) -> tuple[Path, str]:
    rel = Path("blobs") / "sha256" / digest[:2] / digest
    return root / rel, str(rel)


def store_bytes(root: Path, raw: bytes) -> tuple[str, str]:
    digest = hashlib.sha256(raw).hexdigest()
    path, rel = blob_path(root, digest)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        tmp.write_bytes(raw)
        os.replace(tmp, path)
    return digest, rel


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
    return s


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(Path(__file__).with_name("schema.sql").read_text())
    conn.commit()
    return conn


def persist_authority(conn: sqlite3.Connection) -> int:
    a = CMS_REFERENCE
    conn.execute(
        """INSERT OR IGNORE INTO authority_versions
           (authority_key,repository,revision,schema_version,schema_path,schema_blob_sha,observed_at)
           VALUES(?,?,?,?,?,?,?)""",
        (a["authority_key"], a["repository"], a["revision"], a["schema_version"],
         a["schema_path"], a["schema_blob_sha"], utcnow()),
    )
    row = conn.execute(
        "SELECT id FROM authority_versions WHERE authority_key=? AND revision=? AND schema_blob_sha=?",
        (a["authority_key"], a["revision"], a["schema_blob_sha"]),
    ).fetchone()
    assert row
    return int(row[0])


@dataclass(frozen=True)
class Seed:
    hospital_name: str | None
    homepage_url: str
    root_url: str
    notes: str | None = None

    @property
    def source_key(self) -> str:
        return source_key(self.root_url)


def load_sources(path: Path) -> list[Seed]:
    obj = json.loads(path.read_text())
    result: list[Seed] = []
    for item in obj.get("seed_hospitals", []):
        homepage = canonical_url(item["homepage_url"])
        root = canonical_url(item.get("root_url") or root_url(homepage))
        result.append(Seed(
            hospital_name=item.get("hospital_name"),
            homepage_url=homepage,
            root_url=root,
            notes=item.get("notes"),
        ))
    return result


def parse_source_arg(value: str) -> Seed:
    # hospital name is optional: "Hospital Name|https://example.org/"
    if "|" in value:
        name, url = value.split("|", 1)
        name = name.strip() or None
    else:
        name, url = None, value
    homepage = canonical_url(url)
    return Seed(name, homepage, root_url(homepage))


def persist_source(conn: sqlite3.Connection, seed: Seed) -> int:
    conn.execute(
        """INSERT OR IGNORE INTO source_domains
           (source_key,hospital_name,homepage_url,root_url,notes)
           VALUES(?,?,?,?,?)""",
        (seed.source_key, seed.hospital_name, seed.homepage_url, seed.root_url, seed.notes),
    )
    row = conn.execute("SELECT id FROM source_domains WHERE source_key=?", (seed.source_key,)).fetchone()
    assert row
    return int(row[0])


def fetch_small(url: str, *, timeout: int, max_bytes: int) -> tuple[bytes, requests.Response]:
    s = session()
    with s.get(url, timeout=timeout, allow_redirects=True, stream=True) as resp:
        resp.raise_for_status()
        raw = bytearray()
        for chunk in resp.iter_content(65536):
            if not chunk:
                continue
            raw.extend(chunk)
            if len(raw) > max_bytes:
                raise ValueError(f"response exceeds max_bytes={max_bytes}")
        return bytes(raw), resp


def parse_cms_hpt_txt(raw: bytes, base: str) -> list[dict[str, Any]]:
    text = raw.decode("utf-8-sig", errors="replace")
    blocks: list[dict[str, str]] = []
    current: dict[str, str] = {}

    def flush() -> None:
        nonlocal current
        if current:
            if all(current.get(k) for k in ("location-name", "source-page-url", "mrf-url")):
                blocks.append(current)
            current = {}

    for line in text.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key not in TXT_KEYS:
            continue
        if key == "location-name" and current.get("location-name"):
            flush()
        current[key] = value
    flush()

    out: list[dict[str, Any]] = []
    for b in blocks:
        source_page = canonical_url(b["source-page-url"], base)
        mrf = canonical_url(b["mrf-url"], base)
        if urllib.parse.urlsplit(mrf).scheme not in {"http", "https"}:
            continue
        out.append({
            "location_name": b["location-name"].strip(),
            "source_page_url": source_page,
            "mrf_url": mrf,
            "contact_fields_present": int(bool(b.get("contact-name") or b.get("contact-email"))),
        })
    return out


def snapshot_txt(
    conn: sqlite3.Connection,
    root: Path,
    source_id: int,
    url: str,
    *,
    timeout: int,
    max_bytes: int,
) -> tuple[int, list[dict[str, Any]]]:
    raw, resp = fetch_small(url, timeout=timeout, max_bytes=max_bytes)
    digest, rel = store_bytes(root, raw)
    entries = parse_cms_hpt_txt(raw, resp.url)
    parser_status = f"parsed:{len(entries)}" if entries else "parsed:0"
    conn.execute(
        """INSERT OR IGNORE INTO txt_snapshots
           (source_id,observed_at,requested_url,final_url,http_status,content_type,
            byte_count,sha256,blob_relpath,etag,last_modified,parser_status)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (source_id, utcnow(), url, resp.url, resp.status_code,
         resp.headers.get("content-type"), len(raw), digest, rel,
         resp.headers.get("etag"), resp.headers.get("last-modified"), parser_status),
    )
    row = conn.execute(
        "SELECT id FROM txt_snapshots WHERE source_id=? AND requested_url=? AND sha256=?",
        (source_id, url, digest),
    ).fetchone()
    assert row
    return int(row[0]), entries


def insert_entries(
    conn: sqlite3.Connection,
    source_id: int,
    snapshot_id: int,
    entries: Iterable[dict[str, Any]],
) -> int:
    n = 0
    for e in entries:
        conn.execute(
            """INSERT OR IGNORE INTO hpt_entries
               (source_id,txt_snapshot_id,location_name,source_page_url,mrf_url,
                contact_fields_present,discovered_at)
               VALUES(?,?,?,?,?,?,?)""",
            (source_id, snapshot_id, e["location_name"], e["source_page_url"],
             e["mrf_url"], e["contact_fields_present"], utcnow()),
        )
        n += 1
    return n


def download_to_blob(
    root: Path,
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
        with s.get(url, timeout=timeout, stream=True, allow_redirects=True) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_content(1024 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError(f"MRF exceeds max_bytes={max_bytes}")
                digest.update(chunk)
                tmp.write(chunk)
            meta = {
                "final_url": resp.url,
                "http_status": resp.status_code,
                "content_type": resp.headers.get("content-type"),
                "etag": resp.headers.get("etag"),
                "last_modified": resp.headers.get("last-modified"),
                "byte_count": total,
                "sha256": digest.hexdigest(),
            }
    except Exception:
        tmp.close()
        Path(tmp.name).unlink(missing_ok=True)
        raise
    tmp.close()
    target, rel = blob_path(root, meta["sha256"])
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        os.replace(tmp.name, target)
    else:
        Path(tmp.name).unlink(missing_ok=True)
    meta["blob_relpath"] = rel
    return target, meta


def open_decompressed(path: Path) -> BinaryIO:
    fh = path.open("rb")
    magic = fh.read(2)
    fh.seek(0)
    if magic == b"\x1f\x8b":
        return gzip.GzipFile(fileobj=fh, mode="rb")
    return fh


def detect_format(path: Path, url: str, content_type: str | None = None) -> tuple[str, str | None]:
    compression = "gzip" if url.lower().endswith(".gz") else None
    with open_decompressed(path) as fh:
        head = fh.read(4096).lstrip()
    if head.startswith((b"{", b"[")):
        return "json", compression
    if b"," in head or (content_type and "csv" in content_type.lower()):
        return "csv", compression
    return "unknown", compression


def json_header(path: Path) -> dict[str, Any]:
    wanted_scalar = {"hospital_name", "last_updated_on", "version"}
    out: dict[str, Any] = {"location_name": [], "hospital_address": [], "type_2_npi": []}
    with open_decompressed(path) as fh:
        for prefix, event, value in ijson.parse(fh):
            if prefix in wanted_scalar and event in {"string", "number", "boolean"}:
                out[prefix] = value
            elif prefix in {"location_name.item", "hospital_address.item", "type_2_npi.item"} and event == "string":
                out[prefix.split(".")[0]].append(value)
            elif prefix == "license_information.license_number" and event == "string":
                out["license_number"] = value
            elif prefix == "license_information.state" and event == "string":
                out["license_state"] = value
            elif prefix == "attestation.confirm_attestation" and event == "boolean":
                out["attestation_confirmed"] = bool(value)
            elif prefix == "standard_charge_information" and event == "start_array":
                break
    return out


def csv_header(path: Path) -> dict[str, Any]:
    with open_decompressed(path) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
        reader = csv.reader(text)
        rows = []
        for _ in range(3):
            try:
                rows.append(next(reader))
            except StopIteration:
                break
    if len(rows) < 3:
        raise ValueError("CSV missing required general/value/charge header rows")
    general_headers = [x.strip() for x in rows[0]]
    general_values = rows[1]
    general = {k: (general_values[i].strip() if i < len(general_values) else "")
               for i, k in enumerate(general_headers) if k}
    return {
        "hospital_name": general.get("hospital_name"),
        "last_updated_on": general.get("last_updated_on"),
        "version": general.get("version"),
        "location_name": [x.strip() for x in (general.get("location_name") or "").split("|") if x.strip()],
        "hospital_address": [x.strip() for x in (general.get("hospital_address") or "").split("|") if x.strip()],
        "type_2_npi": [re.sub(r"\D", "", x) for x in (general.get("type_2_npi") or "").split("|")
                       if len(re.sub(r"\D", "", x)) == 10],
        "license_number": general.get("license_number") or None,
        "license_state": general.get("state") or general.get("license_state") or None,
        "attestation_confirmed": str(general.get("confirm_attestation", "")).strip().lower() == "true",
        "charge_headers": rows[2],
    }


def persist_mrf_snapshot(
    conn: sqlite3.Connection,
    authority_id: int,
    mrf_url: str,
    meta: dict[str, Any],
    header: dict[str, Any],
    fmt: str,
    compression: str | None,
    parser_status: str,
) -> int:
    conn.execute(
        """INSERT OR IGNORE INTO mrf_snapshots
           (mrf_url,observed_at,requested_url,final_url,http_status,content_type,format,
            compression,byte_count,sha256,blob_relpath,etag,last_modified,schema_version,
            hospital_name,last_updated_on,attestation_confirmed,parser_status,authority_version_id)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (mrf_url, utcnow(), mrf_url, meta.get("final_url"), meta.get("http_status"),
         meta.get("content_type"), fmt, compression, meta.get("byte_count", 0),
         meta["sha256"], meta.get("blob_relpath"), meta.get("etag"), meta.get("last_modified"),
         str(header.get("version") or "") or None, header.get("hospital_name"),
         header.get("last_updated_on"),
         None if "attestation_confirmed" not in header else int(bool(header["attestation_confirmed"])),
         parser_status, authority_id),
    )
    row = conn.execute(
        "SELECT id FROM mrf_snapshots WHERE mrf_url=? AND sha256=?",
        (mrf_url, meta["sha256"]),
    ).fetchone()
    assert row
    sid = int(row[0])
    locations = header.get("location_name") or [None]
    addresses = header.get("hospital_address") or [None]
    npis = header.get("type_2_npi") or [None]
    for loc in locations:
        for address in addresses:
            for npi in npis:
                conn.execute(
                    """INSERT OR IGNORE INTO hospital_identities
                       (mrf_snapshot_id,location_name,hospital_address,license_number,license_state,type_2_npi)
                       VALUES(?,?,?,?,?,?)""",
                    (sid, loc, address, header.get("license_number"), header.get("license_state"), npi),
                )
    return sid


def record_error(conn: sqlite3.Connection, source: str | None, url: str | None,
                 stage: str, exc: Exception) -> None:
    conn.execute(
        """INSERT INTO ingestion_errors(source_key,url,occurred_at,stage,error_type,detail)
           VALUES(?,?,?,?,?,?)""",
        (source, url, utcnow(), stage, type(exc).__name__, str(exc)[:2000]),
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sources", default="sources.json")
    p.add_argument("--source", action="append", default=[],
                   help="Reviewed seed: URL or 'Hospital Name|URL'")
    p.add_argument("--out", default="output")
    p.add_argument("--db", default="hospital_mrf.sqlite")
    p.add_argument("--timeout", type=int, default=45)
    p.add_argument("--max-txt-bytes", type=int, default=2 * 1024 * 1024)
    p.add_argument("--fetch-mrfs", action="store_true")
    p.add_argument("--max-mrf-bytes", type=int, default=2 * 1024 * 1024 * 1024)
    p.add_argument("--max-mrfs", type=int, default=0,
                   help="0 means no count limit; byte ceiling still applies")
    args = p.parse_args()

    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)
    db_path = Path(args.db)
    if not db_path.is_absolute():
        db_path = root / db_path
    conn = init_db(db_path)
    authority_id = persist_authority(conn)
    seeds = load_sources(Path(args.sources)) if Path(args.sources).exists() else []
    seeds.extend(parse_source_arg(x) for x in args.source)

    run_id = conn.execute(
        "INSERT INTO ingestion_runs(started_at,status) VALUES(?,?)",
        (utcnow(), "RUNNING"),
    ).lastrowid
    stats = {"sources": 0, "txt_entries": 0, "mrf_snapshots": 0, "errors": 0}

    for seed in seeds:
        stats["sources"] += 1
        sid = persist_source(conn, seed)
        txt_url = canonical_url("cms-hpt.txt", seed.root_url)
        try:
            snap_id, entries = snapshot_txt(
                conn, root, sid, txt_url, timeout=args.timeout, max_bytes=args.max_txt_bytes
            )
            stats["txt_entries"] += insert_entries(conn, sid, snap_id, entries)
            conn.commit()
        except Exception as exc:
            record_error(conn, seed.source_key, txt_url, "cms_hpt_txt", exc)
            stats["errors"] += 1
            conn.commit()

    if args.fetch_mrfs:
        urls = [r[0] for r in conn.execute("SELECT DISTINCT mrf_url FROM hpt_entries ORDER BY mrf_url")]
        if args.max_mrfs:
            urls = urls[: args.max_mrfs]
        for url in urls:
            try:
                path, meta = download_to_blob(
                    root, url, timeout=args.timeout, max_bytes=args.max_mrf_bytes
                )
                fmt, compression = detect_format(path, url, meta.get("content_type"))
                if fmt == "json":
                    header = json_header(path)
                    status = "parsed:json_header"
                elif fmt == "csv":
                    header = csv_header(path)
                    status = "parsed:csv_header"
                else:
                    header = {}
                    status = "unsupported:format"
                persist_mrf_snapshot(
                    conn, authority_id, url, meta, header, fmt, compression, status
                )
                stats["mrf_snapshots"] += 1
                conn.commit()
            except Exception as exc:
                record_error(conn, None, url, "mrf_fetch_or_header", exc)
                stats["errors"] += 1
                conn.commit()

    conn.execute(
        "UPDATE ingestion_runs SET finished_at=?,status=?,stats_json=? WHERE id=?",
        (utcnow(), "COMPLETE", json.dumps(stats, sort_keys=True), run_id),
    )
    conn.commit()
    conn.close()
    print(json.dumps(stats, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
