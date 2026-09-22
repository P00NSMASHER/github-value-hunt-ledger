"""Parsers for SHAQ MCP read-only responses.

Current MCP v1.29 returns result strings rather than typed rate rows. These parsers
preserve raw evidence and label current batch-search output as SPOT_MARKET because
the server itself says those results are spot-market prices.

They do not assign FMC carrier identity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any


PORT_RE = re.compile(
    r"^\s*(?P<name>.+?)\s+\((?P<code>[A-Z0-9]{5})\)\s+"
    r"\[(?P<country>[^\]]+)\]"
    r"(?:\s+-\s+aka:\s*(?P<aliases>.*))?$"
)

SECTION_RE = re.compile(
    r"(?ms)^\[(?P<index>\d+)\]\s+(?P<query>[^\n]+)\n"
    r"(?P<body>.*?)(?=^\[\d+\]\s+|\nNote:|\Z)"
)

PARSED_RE = re.compile(
    r"Parsed:\s*(?P<origin>.+?)\s*->\s*(?P<destination>.+?)\s*\|\s*(?P<container>[^\n]+)"
)

FOUND_RE = re.compile(
    r"Found\s+(?P<count>\d+)\s+valid rate\(s\);\s*container types:\s*(?P<types>[^\n]+)",
    re.I,
)

RATE_RE = re.compile(
    r"^\s*(?P<container>[A-Z0-9'\-]+)\s+"
    r"(?P<amount>\d+(?:\.\d+)?)\s+"
    r"(?P<currency>[A-Z]{3})\s+"
    r"\(valid\s+(?P<valid_from>\d{4}-\d{2}-\d{2})\s+to\s+"
    r"(?P<valid_to>\d{4}-\d{2}-\d{2})\)\s*$",
    re.I | re.M,
)


@dataclass(frozen=True)
class PortRecord:
    raw_name: str
    normalized_name: str
    port_code: str | None
    country: str | None
    aliases: list[str]
    raw_line: str


@dataclass(frozen=True)
class RateRecord:
    query: str
    origin_raw: str
    destination_raw: str
    container_type: str
    amount_value: str
    currency: str
    valid_from: str
    valid_to: str
    rate_kind: str
    source_label: str
    carrier_raw: str | None
    evidence_excerpt: str
    parser_confidence: float


def normalize_port(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip())
    return value.upper()


def extract_result_text(response: Any) -> str:
    """Read result text from MCP SDK dump or direct structured response."""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        structured = response.get("structured_content") or response.get("structuredContent")
        if isinstance(structured, dict) and isinstance(structured.get("result"), str):
            return structured["result"]
        if isinstance(response.get("result"), str):
            return response["result"]
        for item in response.get("content") or []:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                return item["text"]
    raise ValueError("MCP response does not contain result text")


def parse_ports(text: str) -> tuple[int | None, list[PortRecord]]:
    header = re.search(r"Found\s+(\d+)\s+port\(s\):", text, re.I)
    total = int(header.group(1)) if header else None
    records: list[PortRecord] = []

    for line in text.splitlines():
        match = PORT_RE.match(line)
        if not match:
            continue
        name = match.group("name").strip()
        code = match.group("code").strip()
        country = match.group("country").strip()
        aliases_raw = (match.group("aliases") or "").strip()
        aliases = [
            alias.strip()
            for alias in aliases_raw.split(",")
            if alias.strip()
        ]
        records.append(
            PortRecord(
                raw_name=name,
                normalized_name=normalize_port(name),
                port_code=None if code == "XXXXX" else code,
                country=None if country.lower() == "unknown" else country,
                aliases=aliases,
                raw_line=line.strip(),
            )
        )
    return total, records


def parse_batch_rates(text: str) -> dict[str, Any]:
    output: list[RateRecord] = []
    routes = []
    server_labels_spot = "spot market prices" in text.lower()

    for section in SECTION_RE.finditer(text):
        query = section.group("query").strip()
        body = section.group("body").strip()
        parsed = PARSED_RE.search(body)
        if not parsed:
            routes.append({
                "query": query,
                "status": "UNPARSED",
                "evidence_excerpt": body[:2000],
            })
            continue

        origin = parsed.group("origin").strip()
        destination = parsed.group("destination").strip()
        container = parsed.group("container").strip()

        if "No currently-valid rates" in body:
            routes.append({
                "query": query,
                "origin": origin,
                "destination": destination,
                "container_type": container,
                "status": "NO_CURRENT_RATES",
                "evidence_excerpt": body[:2000],
            })
            continue

        found = FOUND_RE.search(body)
        advertised_count = int(found.group("count")) if found else None
        parsed_rates = []
        for match in RATE_RE.finditer(body):
            record = RateRecord(
                query=query,
                origin_raw=origin,
                destination_raw=destination,
                container_type=match.group("container").upper(),
                amount_value=match.group("amount"),
                currency=match.group("currency").upper(),
                valid_from=match.group("valid_from"),
                valid_to=match.group("valid_to"),
                rate_kind="SPOT_MARKET" if server_labels_spot else "UNKNOWN",
                source_label="SHAQ_MCP_BATCH",
                carrier_raw=None,
                evidence_excerpt=match.group(0).strip(),
                parser_confidence=0.99 if server_labels_spot else 0.90,
            )
            output.append(record)
            parsed_rates.append(asdict(record))

        routes.append({
            "query": query,
            "origin": origin,
            "destination": destination,
            "container_type": container,
            "status": "RATES_FOUND" if parsed_rates else "RATE_COUNT_WITHOUT_VISIBLE_ROWS",
            "advertised_rate_count": advertised_count,
            "parsed_visible_rate_count": len(parsed_rates),
            "visible_rates": parsed_rates,
            "evidence_excerpt": body[:3000],
        })

    return {
        "rate_kind": "SPOT_MARKET" if server_labels_spot else "UNKNOWN",
        "routes": routes,
        "rates": [asdict(record) for record in output],
    }
