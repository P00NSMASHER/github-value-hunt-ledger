#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Iterator

import ijson
import pyarrow as pa
import pyarrow.parquet as pq

from common import (
    PARSER_VERSION,
    canonicalize_url,
    head_metadata,
    init_db,
    session,
    stable_key,
    utcnow,
)

SCHEMAS = {
    "provider_references": pa.schema([
        ("source_file_id", pa.string()),
        ("source_sha256", pa.string()),
        ("provider_group_id", pa.string()),
        ("network_names", pa.list_(pa.string())),
        ("provider_location", pa.string()),
    ]),
    "provider_groups": pa.schema([
        ("source_file_id", pa.string()),
        ("source_sha256", pa.string()),
        ("provider_group_id", pa.string()),
        ("group_ordinal", pa.int32()),
        ("tin_type", pa.string()),
        ("tin_value", pa.string()),
        ("business_name", pa.string()),
    ]),
    "provider_npis": pa.schema([
        ("source_file_id", pa.string()),
        ("source_sha256", pa.string()),
        ("provider_group_id", pa.string()),
        ("group_ordinal", pa.int32()),
        ("npi", pa.string()),
    ]),
    "items": pa.schema([
        ("source_file_id", pa.string()),
        ("source_sha256", pa.string()),
        ("item_id", pa.string()),
        ("item_ordinal", pa.int64()),
        ("negotiation_arrangement", pa.string()),
        ("name", pa.string()),
        ("billing_code_type", pa.string()),
        ("billing_code_type_version", pa.string()),
        ("billing_code", pa.string()),
        ("description", pa.string()),
        ("severity_of_illness", pa.string()),
        ("bundled_codes_json", pa.string()),
        ("covered_services_json", pa.string()),
    ]),
    "rates": pa.schema([
        ("source_file_id", pa.string()),
        ("source_sha256", pa.string()),
        ("rate_id", pa.string()),
        ("item_id", pa.string()),
        ("rate_ordinal", pa.int32()),
    ]),
    "rate_provider_refs": pa.schema([
        ("source_file_id", pa.string()),
        ("source_sha256", pa.string()),
        ("rate_id", pa.string()),
        ("provider_group_id", pa.string()),
    ]),
    "prices": pa.schema([
        ("source_file_id", pa.string()),
        ("source_sha256", pa.string()),
        ("price_id", pa.string()),
        ("rate_id", pa.string()),
        ("price_ordinal", pa.int32()),
        ("negotiated_type", pa.string()),
        ("negotiated_rate", pa.string()),
        ("expiration_date", pa.string()),
        ("billing_class", pa.string()),
        ("setting", pa.string()),
        ("service_codes", pa.list_(pa.string())),
        ("billing_code_modifiers", pa.list_(pa.string())),
        ("additional_information", pa.string()),
    ]),
}


def scalar(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def str_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if v is not None]


class RollingWriter:
    def __init__(self, root: Path, name: str, rows_per_part: int = 1_000_000, batch_size: int = 25_000):
        self.root = root / name
        self.root.mkdir(parents=True, exist_ok=True)
        self.name = name
        self.schema = SCHEMAS[name]
        self.rows_per_part = rows_per_part
        self.batch_size = batch_size
        self.buffer: list[dict] = []
        self.writer: pq.ParquetWriter | None = None
        self.part = 0
        self.part_rows = 0
        self.total_rows = 0
        self.parts: list[str] = []

    def _open(self):
        path = self.root / f"part-{self.part:05d}.parquet"
        self.writer = pq.ParquetWriter(path, self.schema, compression="zstd")
        self.parts.append(str(path))

    def add(self, row: dict):
        self.buffer.append(row)
        if len(self.buffer) >= self.batch_size:
            self.flush()

    def flush(self):
        if not self.buffer:
            return
        if self.writer is None:
            self._open()
        table = pa.Table.from_pylist(self.buffer, schema=self.schema)
        self.writer.write_table(table)
        count = len(self.buffer)
        self.total_rows += count
        self.part_rows += count
        self.buffer.clear()
        if self.part_rows >= self.rows_per_part:
            self.writer.close()
            self.writer = None
            self.part += 1
            self.part_rows = 0

    def close(self):
        self.flush()
        if self.writer is not None:
            self.writer.close()
            self.writer = None


@contextmanager
def json_stream(path: Path):
    with path.open("rb") as base:
        magic = base.read(4)
    if magic[:2] == b"\x1f\x8b":
        with gzip.open(path, "rb") as fh:
            yield fh
        return
    if magic[:4] == b"PK\x03\x04":
        with zipfile.ZipFile(path) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith((".json", ".jsonl"))]
            if len(names) != 1:
                raise ValueError(f"ZIP must contain exactly one JSON payload, got {len(names)}")
            with zf.open(names[0], "r") as fh:
                yield fh
        return
    with path.open("rb") as fh:
        yield fh


def source_preview(path: Path, limit: int = 2_000_000) -> str:
    with json_stream(path) as fh:
        return fh.read(limit).decode("utf-8", errors="replace")


def metadata_from_preview(text: str) -> dict:
    result = {}
    for key in (
        "reporting_entity_name",
        "reporting_entity_type",
        "issuer_name",
        "plan_name",
        "plan_id_type",
        "plan_id",
        "plan_market_type",
        "last_updated_on",
        "version",
    ):
        m = re.search(rf'"{re.escape(key)}"\s*:\s*"([^"]*)"', text)
        if m:
            result[key] = m.group(1)
    return result


def stream_download(url: str, out_root: Path, max_gb: float) -> tuple[Path, str, int, dict]:
    meta = head_metadata(url, timeout=30)
    max_bytes = int(max_gb * 1024**3)
    if meta.get("content_length") and meta["content_length"] > max_bytes:
        raise ValueError(
            f"source content_length={meta['content_length']} exceeds max_gb={max_gb}"
        )

    tmp_dir = out_root / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="tic-", suffix=".download", dir=tmp_dir)
    os.close(fd)
    tmp = Path(tmp_name)
    digest = hashlib.sha256()
    total = 0
    try:
        with session().get(url, stream=True, allow_redirects=True, timeout=(30, 300)) as resp:
            resp.raise_for_status()
            meta.update({
                "status": resp.status_code,
                "final_url": str(resp.url),
                "content_type": resp.headers.get("content-type", "").split(";")[0].lower(),
                "etag": resp.headers.get("etag") or meta.get("etag"),
                "last_modified": resp.headers.get("last-modified") or meta.get("last_modified"),
            })
            with tmp.open("wb") as fh:
                for chunk in resp.iter_content(1024 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError(f"download exceeded max_gb={max_gb}")
                    digest.update(chunk)
                    fh.write(chunk)
        hexdigest = digest.hexdigest()
        final = out_root / "blobs" / "sha256" / hexdigest[:2] / hexdigest
        final.parent.mkdir(parents=True, exist_ok=True)
        if final.exists():
            tmp.unlink()
        else:
            os.replace(tmp, final)
        return final, hexdigest, total, meta
    except Exception:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise


def parse_providers(
    path: Path,
    *,
    source_file_id: str,
    source_sha: str,
    writers: dict[str, RollingWriter],
    npi_filter: set[str],
    tin_filter: set[str],
) -> tuple[set[str], dict]:
    matching_groups: set[str] = set()
    stats = {"provider_references": 0, "provider_groups": 0, "provider_npis": 0, "external_provider_locations": 0}
    with json_stream(path) as fh:
        for ref in ijson.items(fh, "provider_references.item"):
            group_id = scalar(ref.get("provider_group_id")) or ""
            location = scalar(ref.get("location"))
            writers["provider_references"].add({
                "source_file_id": source_file_id,
                "source_sha256": source_sha,
                "provider_group_id": group_id,
                "network_names": str_list(ref.get("network_name")),
                "provider_location": location,
            })
            stats["provider_references"] += 1
            if location:
                stats["external_provider_locations"] += 1

            for ordinal, group in enumerate(ref.get("provider_groups") or []):
                tin = group.get("tin") or {}
                tin_type = scalar(tin.get("type"))
                tin_value = scalar(tin.get("value"))
                business_name = scalar(tin.get("business_name"))
                writers["provider_groups"].add({
                    "source_file_id": source_file_id,
                    "source_sha256": source_sha,
                    "provider_group_id": group_id,
                    "group_ordinal": ordinal,
                    "tin_type": tin_type,
                    "tin_value": tin_value,
                    "business_name": business_name,
                })
                stats["provider_groups"] += 1
                npis = str_list(group.get("npi"))
                matched = bool(tin_filter and tin_value in tin_filter)
                for npi in npis:
                    writers["provider_npis"].add({
                        "source_file_id": source_file_id,
                        "source_sha256": source_sha,
                        "provider_group_id": group_id,
                        "group_ordinal": ordinal,
                        "npi": npi,
                    })
                    stats["provider_npis"] += 1
                    if npi_filter and npi in npi_filter:
                        matched = True
                if matched:
                    matching_groups.add(group_id)
    return matching_groups, stats


def parse_rates(
    path: Path,
    *,
    source_file_id: str,
    source_sha: str,
    writers: dict[str, RollingWriter],
    billing_codes: set[str],
    provider_filter_active: bool,
    matching_groups: set[str],
    max_items: int,
) -> dict:
    stats = {
        "items_seen": 0,
        "items_written": 0,
        "rates_written": 0,
        "provider_refs_written": 0,
        "prices_written": 0,
    }
    with json_stream(path) as fh:
        for item_ordinal, item in enumerate(ijson.items(fh, "in_network.item")):
            stats["items_seen"] += 1
            if max_items and stats["items_seen"] > max_items:
                break
            billing_code = scalar(item.get("billing_code")) or ""
            if billing_codes and billing_code not in billing_codes:
                continue

            accepted_rates = []
            for rate_ordinal, rate in enumerate(item.get("negotiated_rates") or []):
                refs = [scalar(x) or "" for x in rate.get("provider_references") or []]
                if provider_filter_active and not (set(refs) & matching_groups):
                    continue
                accepted_rates.append((rate_ordinal, rate, refs))
            if not accepted_rates:
                continue

            item_id = stable_key(source_sha, "item", item_ordinal)
            writers["items"].add({
                "source_file_id": source_file_id,
                "source_sha256": source_sha,
                "item_id": item_id,
                "item_ordinal": item_ordinal,
                "negotiation_arrangement": scalar(item.get("negotiation_arrangement")),
                "name": scalar(item.get("name")),
                "billing_code_type": scalar(item.get("billing_code_type")),
                "billing_code_type_version": scalar(item.get("billing_code_type_version")),
                "billing_code": billing_code,
                "description": scalar(item.get("description")),
                "severity_of_illness": scalar(item.get("severity_of_illness")),
                "bundled_codes_json": json.dumps(item.get("bundled_codes") or [], default=str),
                "covered_services_json": json.dumps(item.get("covered_services") or [], default=str),
            })
            stats["items_written"] += 1

            for rate_ordinal, rate, refs in accepted_rates:
                rate_id = stable_key(item_id, "rate", rate_ordinal)
                writers["rates"].add({
                    "source_file_id": source_file_id,
                    "source_sha256": source_sha,
                    "rate_id": rate_id,
                    "item_id": item_id,
                    "rate_ordinal": rate_ordinal,
                })
                stats["rates_written"] += 1
                for ref in refs:
                    writers["rate_provider_refs"].add({
                        "source_file_id": source_file_id,
                        "source_sha256": source_sha,
                        "rate_id": rate_id,
                        "provider_group_id": ref,
                    })
                    stats["provider_refs_written"] += 1
                for price_ordinal, price in enumerate(rate.get("negotiated_prices") or []):
                    writers["prices"].add({
                        "source_file_id": source_file_id,
                        "source_sha256": source_sha,
                        "price_id": stable_key(rate_id, "price", price_ordinal),
                        "rate_id": rate_id,
                        "price_ordinal": price_ordinal,
                        "negotiated_type": scalar(price.get("negotiated_type")),
                        "negotiated_rate": scalar(price.get("negotiated_rate")),
                        "expiration_date": scalar(price.get("expiration_date")),
                        "billing_class": scalar(price.get("billing_class")),
                        "setting": scalar(price.get("setting")),
                        "service_codes": str_list(price.get("service_code")),
                        "billing_code_modifiers": str_list(price.get("billing_code_modifier")),
                        "additional_information": scalar(price.get("additional_information")),
                    })
                    stats["prices_written"] += 1
    return stats


def resolve_source_url(conn: sqlite3.Connection, file_key: str | None, url: str | None):
    if url:
        canon = canonicalize_url(url)
        if not canon:
            raise ValueError("invalid --url")
        row = conn.execute("SELECT file_key FROM files WHERE url=?", (canon,)).fetchone()
        return (row[0] if row else stable_key(canon)), canon
    if not file_key:
        raise ValueError("provide --file-key or --url")
    row = conn.execute("SELECT url FROM files WHERE file_key=?", (file_key,)).fetchone()
    if not row:
        raise ValueError(f"file key not found in catalog: {file_key}")
    return file_key, row[0]


def command_ingest(args) -> int:
    out_root = Path(args.out).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    catalog = Path(args.catalog).resolve()
    conn = init_db(catalog)
    file_key, url = resolve_source_url(conn, args.file_key, args.url)
    source_file_id = stable_key(url)

    filters = {
        "billing_codes": sorted(set(args.billing_code or [])),
        "npis": sorted(set(args.npi or [])),
        "tins": sorted(set(args.tin or [])),
        "max_items": args.max_items,
    }
    cur = conn.execute(
        """INSERT INTO ingest_runs
           (file_key,source_url,started_at,parser_version,filters_json,status)
           VALUES (?,?,?,?,?,'running')""",
        (
            file_key if conn.execute("SELECT 1 FROM files WHERE file_key=?", (file_key,)).fetchone() else None,
            url,
            utcnow(),
            PARSER_VERSION,
            json.dumps(filters, sort_keys=True),
        ),
    )
    run_id = int(cur.lastrowid)
    conn.commit()

    try:
        blob, source_sha, compressed_bytes, http_meta = stream_download(url, out_root, args.max_gb)
        preview = metadata_from_preview(source_preview(blob))
        data_root = out_root / "normalized" / source_file_id / source_sha
        writers = {
            name: RollingWriter(data_root, name, rows_per_part=args.rows_per_part, batch_size=args.batch_size)
            for name in SCHEMAS
        }
        matching_groups, provider_stats = parse_providers(
            blob,
            source_file_id=source_file_id,
            source_sha=source_sha,
            writers=writers,
            npi_filter=set(args.npi or []),
            tin_filter=set(args.tin or []),
        )
        rate_stats = parse_rates(
            blob,
            source_file_id=source_file_id,
            source_sha=source_sha,
            writers=writers,
            billing_codes=set(args.billing_code or []),
            provider_filter_active=bool(args.npi or args.tin),
            matching_groups=matching_groups,
            max_items=args.max_items,
        )
        for writer in writers.values():
            writer.close()

        manifest = {
            "source_file_id": source_file_id,
            "source_url": url,
            "source_sha256": source_sha,
            "compressed_bytes": compressed_bytes,
            "http": http_meta,
            "metadata_preview": preview,
            "filters": filters,
            "matching_provider_group_count": len(matching_groups),
            "provider_stats": provider_stats,
            "rate_stats": rate_stats,
            "tables": {
                name: {"rows": writer.total_rows, "parts": [str(Path(x).relative_to(out_root)) for x in writer.parts]}
                for name, writer in writers.items()
            },
            "date_semantics": {
                "last_updated_on": preview.get("last_updated_on"),
                "expiration_date_is_rate_end_evidence": True,
                "effective_start_present_in_cms_schema": False,
                "historical_service_date_before_first_snapshot_must_fail_closed": True,
            },
            "parser_version": PARSER_VERSION,
            "finished_at": utcnow(),
        }
        manifest_path = data_root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

        conn.execute(
            """UPDATE ingest_runs SET finished_at=?,source_sha256=?,raw_blob_relpath=?,
                 compressed_bytes=?,output_manifest=?,status='complete',stats_json=?
               WHERE id=?""",
            (
                utcnow(),
                source_sha,
                str(blob.relative_to(out_root)),
                compressed_bytes,
                str(manifest_path.relative_to(out_root)),
                json.dumps({"providers": provider_stats, "rates": rate_stats}, sort_keys=True),
                run_id,
            ),
        )
        conn.commit()
        print(json.dumps(manifest, indent=2))
        return 0
    except Exception as exc:
        conn.execute(
            "UPDATE ingest_runs SET finished_at=?,status='failed',stats_json=? WHERE id=?",
            (utcnow(), json.dumps({"error": type(exc).__name__, "detail": str(exc)}), run_id),
        )
        conn.commit()
        raise
    finally:
        conn.close()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--file-key")
    p.add_argument("--url")
    p.add_argument("--billing-code", action="append")
    p.add_argument("--npi", action="append")
    p.add_argument("--tin", action="append")
    p.add_argument("--max-gb", type=float, default=2.0)
    p.add_argument("--max-items", type=int, default=0)
    p.add_argument("--rows-per-part", type=int, default=1_000_000)
    p.add_argument("--batch-size", type=int, default=25_000)
    args = p.parse_args()
    return command_ingest(args)


if __name__ == "__main__":
    raise SystemExit(main())
