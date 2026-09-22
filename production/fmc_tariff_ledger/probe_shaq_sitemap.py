#!/usr/bin/env python3
"""Read-only SHAQ public sitemap/robots discovery.

Fetches only a handful of standard public discovery URLs. Does not submit forms,
log in, or call booking/alert APIs.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree


URLS = [
    "https://shaq-log.com/robots.txt",
    "https://www.shaq-log.com/robots.txt",
    "https://shaq-log.com/sitemap.xml",
    "https://www.shaq-log.com/sitemap.xml",
    "https://shaq-log.com/sitemap_index.xml",
    "https://www.shaq-log.com/sitemap_index.xml",
]


def fetch(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "GitHub-Research-SHAQ-Public-Discovery/1.0",
            "Accept": "text/plain, application/xml, text/xml, */*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read(25_000_000)
            final_url = response.geturl()
            status = response.status
            ctype = response.headers.get("content-type", "")
    except urllib.error.HTTPError as exc:
        return {
            "url": url,
            "status": exc.code,
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "url": url,
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

    text = raw.decode("utf-8", errors="replace")
    record = {
        "url": url,
        "final_url": final_url,
        "status": status,
        "content_type": ctype,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "preview": text[:12000],
    }

    if "xml" in ctype.lower() or text.lstrip().startswith("<?xml"):
        try:
            root = ElementTree.fromstring(raw)
            locations = [
                elem.text.strip()
                for elem in root.iter()
                if elem.tag.rsplit("}", 1)[-1] == "loc" and elem.text
            ]
            record["xml_location_count"] = len(locations)
            record["xml_locations_first_100"] = locations[:100]
            record["route_page_count"] = sum("/q/" in x for x in locations)
        except Exception as exc:
            record["xml_parse_error"] = f"{type(exc).__name__}: {exc}"
    return record


def main() -> int:
    payload = {
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "results": [fetch(url) for url in URLS],
    }
    out = Path("shaq_sitemap_probe.json")
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
