#!/usr/bin/env python3
"""Hash and parse SHAQ's public /q/ route pages from its published sitemap.

Design goals:
- discover routes only from the public sitemap, never brute-force port pairs;
- respect the site's published robots policy and keep concurrency intentionally low;
- preserve exact page bytes + SHA-256;
- parse carrier/container/amount/validity as PUBLISHER_CARRIER_RATE;
- never bind an FMC organization or promote contract authority automatically.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup

import shaq_identity


SITEMAP_URL = "https://shaq-log.com/sitemap.xml"
ROBOTS_URL = "https://shaq-log.com/robots.txt"
USER_AGENT = "GitHub-Research-SHAQ-Public-Route-Archive/1.0"
PARSER_VERSION = "shaq-route-v1"
DEFAULT_RATE_KIND = "PUBLISHER_CARRIER_RATE"

_thread_local = threading.local()
_host_lock = threading.Lock()
_host_last_request: dict[str, float] = {}


@dataclass(frozen=True)
class RouteRate:
    origin: str
    destination: str
    container_type: str
    amount_value: str
    currency: str
    carrier: str
    transit_time: str | None
    valid_to: str | None
    evidence_excerpt: str
    confidence: float = 0.99


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_session() -> requests.Session:
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml,text/plain,*/*",
            }
        )
        _thread_local.session = session
    return session


def polite_get(
    url: str,
    *,
    timeout: int = 30,
    max_bytes: int = 15_000_000,
    min_host_interval: float = 0.50,
) -> tuple[bytes, requests.Response]:
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    with _host_lock:
        last = _host_last_request.get(host, 0.0)
        delay = min_host_interval - (time.monotonic() - last)
        if delay > 0:
            time.sleep(delay)
        _host_last_request[host] = time.monotonic()

    with get_session().get(url, timeout=timeout, allow_redirects=True, stream=True) as resp:
        resp.raise_for_status()
        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(128 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(f"response exceeds max_bytes={max_bytes}")
            chunks.append(chunk)
        return b"".join(chunks), resp


def write_blob(root: Path, digest: str, raw: bytes) -> str:
    rel = Path("blobs") / "sha256" / digest[:2] / digest
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return str(rel)

    # Multiple crawl workers frequently encounter the same shared-publisher
    # bytes. Use a per-process/per-thread temp name so concurrent identical
    # content can safely race to the same content-addressed final path.
    tmp = path.with_name(
        f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    try:
        tmp.write_bytes(raw)
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
    return str(rel)


def fetch_discovery_snapshot(
    url: str,
    out_root: Path,
    *,
    timeout: int,
    max_bytes: int,
) -> dict:
    raw, resp = polite_get(
        url,
        timeout=timeout,
        max_bytes=max_bytes,
        min_host_interval=0.25,
    )
    digest = hashlib.sha256(raw).hexdigest()
    rel = write_blob(out_root, digest, raw)
    return {
        "url": url,
        "final_url": resp.url,
        "fetched_at": utcnow(),
        "http_status": resp.status_code,
        "content_type": resp.headers.get("content-type", ""),
        "byte_count": len(raw),
        "sha256": digest,
        "blob_relpath": rel,
        "raw": raw,
    }


def parse_sitemap(raw: bytes) -> list[tuple[str, str | None]]:
    root = ET.fromstring(raw)
    urls: list[tuple[str, str | None]] = []
    for url_elem in root.iter():
        if url_elem.tag.rsplit("}", 1)[-1] != "url":
            continue
        loc = lastmod = None
        for child in url_elem:
            name = child.tag.rsplit("}", 1)[-1]
            if name == "loc" and child.text:
                loc = child.text.strip()
            elif name == "lastmod" and child.text:
                lastmod = child.text.strip()
        if loc and "/q/" in urllib.parse.urlsplit(loc).path:
            urls.append((loc, lastmod))
    return urls


def stable_shard(url: str, count: int) -> int:
    digest = hashlib.sha256(url.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % count


def normalize_container(value: str) -> str:
    value = value.upper().replace(" CONTAINER", "").strip()
    aliases = {
        "40HC": "40HQ",
        "40 HIGH CUBE": "40HQ",
        "20 DRY": "20GP",
        "40 DRY": "40GP",
    }
    return aliases.get(value, value)


def parse_money(value: str) -> tuple[str | None, str | None]:
    value = value.strip()
    match = re.search(
        r"(?:(?P<currency>USD|EUR|GBP|CAD|AUD|CNY|RMB)\s*)?"
        r"(?P<symbol>[$€£])?\s*"
        r"(?P<amount>\d+(?:,\d{3})*(?:\.\d+)?)",
        value,
        re.I,
    )
    if not match:
        return None, None
    currency = (match.group("currency") or "").upper()
    symbol = match.group("symbol")
    if not currency:
        currency = {"$": "USD", "€": "EUR", "£": "GBP"}.get(symbol or "", "")
    return match.group("amount").replace(",", ""), currency or None


def split_lane_heading(text: str) -> tuple[str, str] | None:
    text = re.sub(r"\s+", " ", text.strip())
    # Route pages use headings like "Shanghai to Hamburg".
    match = re.match(r"^(.+?)\s+to\s+(.+)$", text, re.I)
    if not match:
        return None
    return match.group(1).strip(), match.group(2).strip()


def _table_headers(table) -> list[str]:
    first = table.find("tr")
    if not first:
        return []
    return [
        re.sub(r"\s+", " ", cell.get_text(" ", strip=True)).strip().lower()
        for cell in first.find_all(["th", "td"])
    ]


def parse_route_page(raw: bytes, url: str) -> tuple[dict, list[RouteRate]]:
    soup = BeautifulSoup(raw, "html.parser")
    title = soup.title.get_text(" ", strip=True)[:500] if soup.title else None
    h1 = soup.find("h1")
    heading = h1.get_text(" ", strip=True)[:500] if h1 else None
    rows: list[RouteRate] = []

    # Preferred parser: lane H2 followed by a table.
    for h2 in soup.find_all("h2"):
        lane = split_lane_heading(h2.get_text(" ", strip=True))
        if not lane:
            continue
        origin, destination = lane

        table = h2.find_next("table")
        if table is None:
            continue

        # Do not accidentally attach a later section's table.
        next_h2 = h2.find_next("h2")
        if next_h2 is not None and next_h2.sourceline and table.sourceline:
            if table.sourceline > next_h2.sourceline:
                continue

        headers = _table_headers(table)
        if not headers:
            continue
        header_map = {name: idx for idx, name in enumerate(headers)}

        def col(*names: str) -> int | None:
            for name in names:
                for header, idx in header_map.items():
                    if name in header:
                        return idx
            return None

        i_container = col("container type", "container")
        i_rate = col("rate", "price")
        i_carrier = col("carrier")
        i_transit = col("transit")
        i_valid = col("valid until", "valid")

        if None in (i_container, i_rate, i_carrier):
            continue

        for tr in table.find_all("tr")[1:]:
            cells = [
                re.sub(r"\s+", " ", td.get_text(" ", strip=True)).strip()
                for td in tr.find_all(["td", "th"])
            ]
            if not cells or max(i_container, i_rate, i_carrier) >= len(cells):
                continue
            amount, currency = parse_money(cells[i_rate])
            if not amount or not currency:
                continue
            carrier = cells[i_carrier].strip()
            container = normalize_container(cells[i_container])
            transit = (
                cells[i_transit].strip()
                if i_transit is not None and i_transit < len(cells)
                else None
            )
            valid_to = (
                cells[i_valid].strip()
                if i_valid is not None and i_valid < len(cells)
                else None
            )
            if valid_to and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", valid_to):
                match = re.search(r"\d{4}-\d{2}-\d{2}", valid_to)
                valid_to = match.group(0) if match else None

            excerpt = " | ".join(cells)[:2000]
            rows.append(
                RouteRate(
                    origin=origin,
                    destination=destination,
                    container_type=container,
                    amount_value=amount,
                    currency=currency,
                    carrier=carrier,
                    transit_time=transit,
                    valid_to=valid_to,
                    evidence_excerpt=excerpt,
                )
            )

    # Fallback parser for cards/plain text when tables are absent.
    if not rows:
        text = soup.get_text("\n", strip=True)
        lane = None
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            maybe_lane = split_lane_heading(line)
            if maybe_lane:
                lane = maybe_lane
                continue
            if not lane:
                continue
            if not re.fullmatch(r"(?:20|40|45)(?:GP|HQ|HC|RQ|RF) Container", line, re.I):
                continue
            block = lines[idx : idx + 8]
            amount_line = next((x for x in block[1:] if "$" in x or re.search(r"\bUSD\b", x)), None)
            carrier = next((x for x in block[1:] if re.search(r"\bCOSCO\b|\bMSC\b|\bMAERSK\b|\bCMA\b|\bONE\b|\bHAPAG\b", x, re.I)), None)
            valid = next((x for x in block[1:] if "valid" in x.lower()), None)
            if not amount_line or not carrier:
                continue
            amount, currency = parse_money(amount_line)
            if not amount or not currency:
                continue
            valid_match = re.search(r"\d{4}-\d{2}-\d{2}", valid or "")
            rows.append(
                RouteRate(
                    origin=lane[0],
                    destination=lane[1],
                    container_type=normalize_container(line),
                    amount_value=amount,
                    currency=currency,
                    carrier=carrier,
                    transit_time=None,
                    valid_to=valid_match.group(0) if valid_match else None,
                    evidence_excerpt=" | ".join(block)[:2000],
                    confidence=0.90,
                )
            )

    # De-duplicate exact visible table/card rows but preserve distinct amounts.
    seen = set()
    unique: list[RouteRate] = []
    for row in rows:
        key = (
            row.origin,
            row.destination,
            row.container_type,
            row.amount_value,
            row.currency,
            row.carrier,
            row.transit_time,
            row.valid_to,
        )
        if key not in seen:
            seen.add(key)
            unique.append(row)

    return {
        "title": title,
        "heading": heading,
        "rate_count": len(unique),
        "url": url,
    }, unique


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    schema = Path(__file__).with_name("shaq_schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.commit()
    return conn


def crawl_page(
    url: str,
    lastmod: str | None,
    out_root: Path,
    *,
    timeout: int,
    max_bytes: int,
    min_interval: float,
) -> dict:
    try:
        raw, resp = polite_get(
            url,
            timeout=timeout,
            max_bytes=max_bytes,
            min_host_interval=min_interval,
        )
        digest = hashlib.sha256(raw).hexdigest()
        rel = write_blob(out_root, digest, raw)
        meta, rates = parse_route_page(raw, resp.url)
        return {
            "ok": True,
            "url": url,
            "final_url": resp.url,
            "lastmod": lastmod,
            "fetched_at": utcnow(),
            "status": resp.status_code,
            "content_type": resp.headers.get("content-type", ""),
            "byte_count": len(raw),
            "sha256": digest,
            "blob_relpath": rel,
            "meta": meta,
            "rates": rates,
        }
    except Exception as exc:
        return {
            "ok": False,
            "url": url,
            "lastmod": lastmod,
            "error_type": type(exc).__name__,
            "error": str(exc)[:2000],
        }


def persist_result(conn: sqlite3.Connection, run_id: int, result: dict) -> tuple[int, int]:
    if not result["ok"]:
        return 0, 0

    conn.execute(
        """INSERT OR IGNORE INTO shaq_route_pages(
             run_id, url, fetched_at, http_status, content_type, byte_count,
             sha256, blob_relpath, page_title, page_heading, parser_status, lastmod
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run_id,
            result["url"],
            result["fetched_at"],
            result["status"],
            result["content_type"],
            result["byte_count"],
            result["sha256"],
            result["blob_relpath"],
            result["meta"]["title"],
            result["meta"]["heading"],
            "parsed" if result["meta"]["rate_count"] else "parsed:no_rates",
            result["lastmod"],
        ),
    )
    row = conn.execute(
        "SELECT id FROM shaq_route_pages WHERE url=? AND sha256=?",
        (result["url"], result["sha256"]),
    ).fetchone()
    assert row
    page_id = int(row[0])

    inserted = 0
    for rate in result["rates"]:
        identity = shaq_identity.resolve_identity(conn, rate.carrier)
        before = conn.total_changes
        conn.execute(
            """INSERT OR IGNORE INTO shaq_rates(
                 route_page_id, origin_raw, destination_raw,
                 carrier_raw, carrier_normalized, fmc_organization_no,
                 fmc_identity_status, container_type, amount_value, currency,
                 valid_to, rate_basis, transit_time, source_url, rate_kind,
                 source_label, evidence_excerpt, parser_confidence,
                 parser_version, created_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'per container',
                         ?, ?, ?, 'SHAQ_PUBLIC_ROUTE_PAGE', ?, ?, ?, ?)""",
            (
                page_id,
                rate.origin,
                rate.destination,
                rate.carrier,
                identity.carrier_normalized,
                identity.fmc_organization_no,
                identity.status,
                rate.container_type,
                rate.amount_value,
                rate.currency,
                rate.valid_to,
                rate.transit_time,
                result["url"],
                DEFAULT_RATE_KIND,
                rate.evidence_excerpt,
                rate.confidence,
                PARSER_VERSION,
                utcnow(),
            ),
        )
        inserted += conn.total_changes - before
    conn.commit()
    return 1, inserted


def main() -> int:
    p = argparse.ArgumentParser(description="Archive SHAQ public route-rate pages")
    p.add_argument("--out", default=".shaq_routes")
    p.add_argument("--db", default="shaq_routes.sqlite")
    p.add_argument("--shard-count", type=int, default=1)
    p.add_argument("--shard-index", type=int, default=0)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--max-bytes", type=int, default=15_000_000)
    p.add_argument("--min-host-interval", type=float, default=0.50)
    p.add_argument("--max-pages", type=int, default=0)
    args = p.parse_args()

    if args.shard_count < 1 or not (0 <= args.shard_index < args.shard_count):
        raise SystemExit("invalid shard configuration")
    if not (1 <= args.workers <= 4):
        raise SystemExit("workers must be 1..4")
    if args.min_host_interval < 0.25:
        raise SystemExit("min-host-interval must be >= 0.25 seconds")

    out_root = Path(args.out).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    db_path = Path(args.db)
    if not db_path.is_absolute():
        db_path = out_root / db_path

    robots = fetch_discovery_snapshot(
        ROBOTS_URL,
        out_root,
        timeout=args.timeout,
        max_bytes=args.max_bytes,
    )
    sitemap = fetch_discovery_snapshot(
        SITEMAP_URL,
        out_root,
        timeout=args.timeout,
        max_bytes=args.max_bytes,
    )
    robots_text = robots["raw"].decode("utf-8", errors="replace")
    if "User-agent: *" not in robots_text or "Allow: /" not in robots_text:
        raise SystemExit("robots snapshot does not explicitly allow public crawl")

    all_routes = parse_sitemap(sitemap["raw"])
    routes = [
        item
        for item in all_routes
        if stable_shard(item[0], args.shard_count) == args.shard_index
    ]
    if args.max_pages:
        routes = routes[: args.max_pages]

    conn = init_db(db_path)
    cur = conn.execute(
        """INSERT INTO shaq_runs(
             started_at, endpoint, parser_version, status, stats_json
           ) VALUES (?, ?, ?, 'running', ?)""",
        (
            utcnow(),
            SITEMAP_URL,
            PARSER_VERSION,
            json.dumps(
                {
                    "sitemap_sha256": sitemap["sha256"],
                    "robots_sha256": robots["sha256"],
                    "all_route_pages": len(all_routes),
                    "selected_route_pages": len(routes),
                    "shard_index": args.shard_index,
                    "shard_count": args.shard_count,
                },
                sort_keys=True,
            ),
        ),
    )
    run_id = int(cur.lastrowid)
    conn.commit()

    stats = {
        "sitemap_route_pages": len(all_routes),
        "selected_pages": len(routes),
        "pages_ok": 0,
        "pages_failed": 0,
        "rates_inserted": 0,
        "pages_without_rates": 0,
        "errors": [],
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(
                crawl_page,
                url,
                lastmod,
                out_root,
                timeout=args.timeout,
                max_bytes=args.max_bytes,
                min_interval=args.min_host_interval,
            )
            for url, lastmod in routes
        ]
        for idx, fut in enumerate(concurrent.futures.as_completed(futures), 1):
            result = fut.result()
            if result["ok"]:
                pages, inserted = persist_result(conn, run_id, result)
                stats["pages_ok"] += pages
                stats["rates_inserted"] += inserted
                if result["meta"]["rate_count"] == 0:
                    stats["pages_without_rates"] += 1
            else:
                stats["pages_failed"] += 1
                if len(stats["errors"]) < 200:
                    stats["errors"].append(
                        {
                            "url": result["url"],
                            "error_type": result["error_type"],
                            "error": result["error"],
                        }
                    )
            if idx % 100 == 0 or idx == len(futures):
                print(
                    f"progress {idx}/{len(futures)} pages_ok={stats['pages_ok']} "
                    f"rates={stats['rates_inserted']} failed={stats['pages_failed']}"
                )

    conn.execute(
        "UPDATE shaq_runs SET finished_at=?, status='complete', stats_json=? WHERE id=?",
        (utcnow(), json.dumps(stats, sort_keys=True), run_id),
    )
    conn.commit()
    conn.close()

    summary_path = out_root / "summary.json"
    summary_path.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n")
    discovery = {
        "robots": {k: v for k, v in robots.items() if k != "raw"},
        "sitemap": {k: v for k, v in sitemap.items() if k != "raw"},
    }
    (out_root / "discovery.json").write_text(
        json.dumps(discovery, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(stats, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
