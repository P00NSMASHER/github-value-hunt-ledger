#!/usr/bin/env python3
"""Small read-only response-shape probe for authorized SHAQ rate ingestion.

Calls only read-only tools:
- list_ports (one call)
- search_freight_rates_batch (one call, three routes)
No bookings, alerts, or write tools.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession
from mcp.client.sse import sse_client


DEFAULT_URL = "https://search.shaq-logistics.com/sse"


def dump(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, list):
        return [dump(v) for v in value]
    if isinstance(value, dict):
        return {str(k): dump(v) for k, v in value.items()}
    return value


async def probe(url: str) -> dict:
    result = {
        "endpoint": url,
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "calls": [],
    }
    async with sse_client(url=url, timeout=30.0, sse_read_timeout=90.0) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()

            ports = await session.call_tool(
                "list_ports",
                {"query": "", "limit": 100},
            )
            result["calls"].append({
                "tool": "list_ports",
                "arguments": {"query": "", "limit": 100},
                "response": dump(ports),
            })

            queries = [
                "Shenzhen to Los Angeles 40HC",
                "Shanghai to Hamburg 40HC",
                "Ningbo to Long Beach 20GP",
            ]
            rates = await session.call_tool(
                "search_freight_rates_batch",
                {"queries": queries},
            )
            result["calls"].append({
                "tool": "search_freight_rates_batch",
                "arguments": {"queries": queries},
                "response": dump(rates),
            })
    return result


def main() -> int:
    url = os.environ.get("SHAQ_MCP_URL", DEFAULT_URL)
    output = Path(os.environ.get("SHAQ_SAMPLE_OUTPUT", "shaq_sample_probe.json"))
    payload = asyncio.run(probe(url))
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
