#!/usr/bin/env python3
"""Read-only MCP discovery probe for the authorized SHAQ freight-rate surface."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession
from mcp.client.sse import sse_client


DEFAULT_URL = "https://search.shaq-logistics.com/sse"


def dump_model(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, list):
        return [dump_model(v) for v in value]
    if isinstance(value, dict):
        return {str(k): dump_model(v) for k, v in value.items()}
    return value


async def probe(url: str) -> dict:
    result = {
        "endpoint": url,
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "actions_performed": ["initialize", "tools/list", "prompts/list", "resources/list"],
        "tool_calls_performed": [],
    }

    async with sse_client(url=url, timeout=30.0, sse_read_timeout=60.0) as streams:
        async with ClientSession(*streams) as session:
            init = await session.initialize()
            result["initialize"] = dump_model(init)

            tools = await session.list_tools()
            result["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": dump_model(tool.inputSchema),
                    "outputSchema": dump_model(getattr(tool, "outputSchema", None)),
                    "annotations": dump_model(getattr(tool, "annotations", None)),
                }
                for tool in tools.tools
            ]

            try:
                prompts = await session.list_prompts()
                result["prompts"] = [
                    {
                        "name": p.name,
                        "description": p.description,
                        "arguments": dump_model(p.arguments),
                    }
                    for p in prompts.prompts
                ]
            except Exception as exc:
                result["prompts_error"] = f"{type(exc).__name__}: {exc}"

            try:
                resources = await session.list_resources()
                result["resources"] = [
                    {
                        "uri": str(r.uri),
                        "name": r.name,
                        "description": r.description,
                        "mimeType": r.mimeType,
                    }
                    for r in resources.resources
                ]
            except Exception as exc:
                result["resources_error"] = f"{type(exc).__name__}: {exc}"

    return result


def main() -> int:
    url = os.environ.get("SHAQ_MCP_URL", DEFAULT_URL)
    output = Path(os.environ.get("SHAQ_PROBE_OUTPUT", "shaq_mcp_schema.json"))
    payload = asyncio.run(probe(url))
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
