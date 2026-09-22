#!/usr/bin/env python3
"""Classify FMC crawl failures into safe retry / review queues.

This does not fetch anything. It converts durable crawl_errors into a deduplicated
plan so transient network failures can be retried without repeatedly hammering
authentication gates, stale 404s, or unresolved shared-publisher portals.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


TRANSIENT_ERROR_TYPES = {
    "ConnectionError",
    "ConnectTimeout",
    "ReadTimeout",
    "Timeout",
}
LOCAL_RETRY_TYPES = {"FileNotFoundError"}
TRANSIENT_HTTP = {408, 425, 429, 500, 502, 503, 504}
AUTH_HTTP = {401, 403}
STALE_HTTP = {404, 410}


def host_of(url: str) -> str:
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return "(invalid)"


def http_status_from_detail(detail: str) -> int | None:
    patterns = [
        r"\b(\d{3})\s+Client Error\b",
        r"\b(\d{3})\s+Server Error\b",
        r"\bstatus(?:_code)?[=: ]+(\d{3})\b",
        r"\bHTTP\s+(\d{3})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, detail or "", re.I)
        if match:
            value = int(match.group(1))
            if 100 <= value <= 599:
                return value
    return None


def classify(stage: str, error_type: str, detail: str) -> tuple[str, str]:
    if stage in {"publisher_access", "publisher_adapter"}:
        return "MANUAL_PUBLISHER_RESOLUTION", f"{stage}:{error_type}"

    if stage == "postvalidate":
        return "NO_RETRY_EVIDENCE_QUARANTINE", f"{stage}:{error_type}"

    if stage == "parse":
        return "OFFLINE_REPARSE", f"{stage}:{error_type}"

    if stage != "fetch":
        return "MANUAL_REVIEW", f"{stage}:{error_type}"

    if error_type in TRANSIENT_ERROR_TYPES:
        return "SAFE_NETWORK_RETRY", f"fetch:{error_type}"
    if error_type in LOCAL_RETRY_TYPES:
        return "SAFE_NETWORK_RETRY", "local_blob_write_race_or_missing_temp"

    if error_type == "SSLError":
        return "TLS_REVIEW", "fetch:SSLError"

    if error_type == "HTTPError":
        status = http_status_from_detail(detail)
        if status in TRANSIENT_HTTP:
            return "SAFE_NETWORK_RETRY", f"http:{status}"
        if status in AUTH_HTTP:
            return "ACCESS_REVIEW", f"http:{status}"
        if status in STALE_HTTP:
            return "STALE_LINK", f"http:{status}"
        if status is not None and 400 <= status < 500:
            return "CLIENT_ERROR_REVIEW", f"http:{status}"
        if status is not None and 500 <= status < 600:
            return "SAFE_NETWORK_RETRY", f"http:{status}"
        return "HTTP_STATUS_UNKNOWN", "fetch:HTTPError"

    return "MANUAL_REVIEW", f"fetch:{error_type}"


def build_plan(conn: sqlite3.Connection) -> dict[str, Any]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT
             ce.id,
             ce.tariff_location_id,
             ce.url,
             ce.stage,
             ce.error_type,
             ce.detail,
             tl.entity_id,
             e.entity_class,
             e.organization_no,
             e.legal_name,
             tl.canonical_url AS tariff_location
           FROM crawl_errors ce
           LEFT JOIN tariff_locations tl ON tl.id=ce.tariff_location_id
           LEFT JOIN entities e ON e.id=tl.entity_id"""
    ).fetchall()

    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    class_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()

    for row in rows:
        category, reason = classify(
            row["stage"],
            row["error_type"],
            row["detail"] or "",
        )
        class_counts[category] += 1
        reason_counts[f"{category}:{reason}"] += 1

        key = (category, row["url"])
        entry = grouped.setdefault(
            key,
            {
                "category": category,
                "url": row["url"],
                "host": host_of(row["url"]),
                "reasons": Counter(),
                "error_rows": 0,
                "fmc_entities": {},
                "tariff_locations": set(),
            },
        )
        entry["reasons"][reason] += 1
        entry["error_rows"] += 1
        if row["tariff_location"]:
            entry["tariff_locations"].add(row["tariff_location"])
        if row["organization_no"]:
            entry["fmc_entities"][row["organization_no"]] = {
                "entity_class": row["entity_class"],
                "organization_no": row["organization_no"],
                "legal_name": row["legal_name"],
            }

    queues: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in grouped.values():
        item = {
            "url": entry["url"],
            "host": entry["host"],
            "error_rows": entry["error_rows"],
            "reasons": dict(entry["reasons"].most_common()),
            "affected_fmc_entities": list(entry["fmc_entities"].values()),
            "affected_entity_count": len(entry["fmc_entities"]),
            "tariff_locations": sorted(entry["tariff_locations"]),
        }
        queues[entry["category"]].append(item)

    for category, items in queues.items():
        items.sort(
            key=lambda item: (
                -item["affected_entity_count"],
                -item["error_rows"],
                item["host"],
                item["url"],
            )
        )

    safe_retry = queues.get("SAFE_NETWORK_RETRY", [])
    return {
        "error_rows": len(rows),
        "classification_counts": dict(class_counts.most_common()),
        "reason_counts": dict(reason_counts.most_common()),
        "safe_network_retry": safe_retry,
        "safe_network_retry_unique_urls": len(safe_retry),
        "queues": dict(queues),
        "policy": {
            "authentication_not_auto_retried": True,
            "shared_publisher_resolution_not_auto_retried": True,
            "404_410_not_auto_retried": True,
            "parse_failures_use_offline_reparse": True,
            "429_5xx_timeouts_connections_are_retryable": True,
            "local_blob_write_race_is_retryable_after_thread_safe_fix": True,
        },
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--output")
    args = p.parse_args()

    conn = sqlite3.connect(args.db)
    plan = build_plan(conn)
    conn.close()
    payload = json.dumps(plan, indent=2, sort_keys=False) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
