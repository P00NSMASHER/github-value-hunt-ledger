#!/usr/bin/env python3
"""Read-only detailed SHAQ lane + OpenAPI probe.

Business tool calls:
- search_freight_rates: one lane
- rate_trends: same lane
No booking, alerts, tracking, analyst chat, or write operations.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession
from mcp.client.sse import sse_client


MCP_URL = "https://search.shaq-logistics.com/sse"
OPENAPI_URL = "https://search.shaq-logistics.com/openapi.json"


def dump(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, list):
        return [dump(v) for v in value]
    if isinstance(value, dict):
        return {str(k): dump(v) for k, v in value.items()}
    return value


def fetch_openapi() -> dict:
    req = urllib.request.Request(
        OPENAPI_URL,
        headers={"User-Agent": "GitHub-Research-SHAQ-ReadOnly-Probe/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read(10_000_000)
    except Exception as exc:
        return {
            "url": OPENAPI_URL,
            "status": "unavailable",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

    digest = hashlib.sha256(raw).hexdigest()
    parsed = json.loads(raw)
    paths = {}
    for path, operations in (parsed.get("paths") or {}).items():
        paths[path] = {
            method: {
                "summary": spec.get("summary"),
                "operationId": spec.get("operationId"),
                "parameters": spec.get("parameters"),
                "requestBody": spec.get("requestBody"),
                "responses": spec.get("responses"),
            }
            for method, spec in operations.items()
            if isinstance(spec, dict)
        }
    return {
        "url": OPENAPI_URL,
        "status": "available",
        "sha256": digest,
        "title": (parsed.get("info") or {}).get("title"),
        "version": (parsed.get("info") or {}).get("version"),
        "servers": parsed.get("servers"),
        "paths": paths,
    }


async def probe_mcp() -> list[dict]:
    calls = []
    async with sse_client(url=MCP_URL, timeout=30.0, sse_read_timeout=90.0) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            args = {
                "origin": "Shanghai",
                "destination": "Hamburg",
                "container_type": "40HQ",
            }
            detailed = await session.call_tool("search_freight_rates", args)
            calls.append({
                "tool": "search_freight_rates",
                "arguments": args,
                "response": dump(detailed),
            })
            trend_args = {**args, "weeks": 4}
            trends = await session.call_tool("rate_trends", trend_args)
            calls.append({
                "tool": "rate_trends",
                "arguments": trend_args,
                "response": dump(trends),
            })
    return calls


def main() -> int:
    output = Path(os.environ.get("SHAQ_DETAIL_OUTPUT", "shaq_detail_probe.json"))
    payload = {
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "openapi": fetch_openapi(),
        "mcp_calls": asyncio.run(probe_mcp()),
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
