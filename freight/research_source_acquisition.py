"""Bounded, manually triggered capture of preapproved public research pages.

CRITICAL: Capture is a CANDIDATE, never a verified research claim.
No credentials, POST, scheduled requests, client data, source discovery, HTML
script execution, raw full-page persistence, or production side effects.
CI exercises only mocked transports; optional live fetch requires --execute.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from ipaddress import ip_address
import json
from pathlib import Path
import socket
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler, Request, build_opener,
)

MAX_SOURCES = 12
MAX_BYTES = 256_000
MAX_EXCERPT_CHARS = 950
TIMEOUT_SECONDS = 8
ALLOWED_HOSTS = frozenset({
    "www.bts.gov", "www.cassinfo.com", "www.estes-express.com",
    "nmfta.org", "help.nmfta.org", "www.ecfr.gov", "www.govinfo.gov",
    "usc-cdn.house.gov", "x12.org", "www.sec.gov",
    "www.retallyrecovery.com", "recover-audit.com",
    "www.tarerecovery.com", "www.loop.com",
})
SAFE_MIME = frozenset({"text/html", "text/plain", "application/xhtml+xml"})
SCHEMA_VERSION = 1


class CaptureError(ValueError):
    pass


def sha_hex(data: bytes) -> str:
    return sha256(data).hexdigest()


def canonical_sha(data: object) -> str:
    return sha_hex(json.dumps(data, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False).encode("utf-8"))


def validate_url(url: object) -> str:
    if not isinstance(url, str) or len(url) > 2048 or any(c.isspace() for c in url):
        raise CaptureError("URL_UNSAFE")
    try:
        parts = urlsplit(url)
        if (parts.scheme != "https" or not parts.hostname or parts.port not in (None, 443)
                or parts.username or parts.password or parts.fragment):
            raise CaptureError("URL_UNSAFE")
    except ValueError as exc:
        raise CaptureError("URL_UNSAFE") from exc
    if parts.hostname.lower() not in ALLOWED_HOSTS:
        raise CaptureError("HOST_NOT_PREAPPROVED")
    if not parts.path.startswith("/") or parts.path.startswith("//"):
        raise CaptureError("URL_PATH_UNSAFE")
    return url


def validate_manifest(manifest: object) -> None:
    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA_VERSION:
        raise CaptureError("INVALID_MANIFEST_SCHEMA")
    entries = manifest.get("sources")
    if not isinstance(entries, list) or not entries or len(entries) > MAX_SOURCES:
        raise CaptureError("INVALID_MANIFEST_SIZE")
    ids = set()
    urls = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise CaptureError("INVALID_ENTRY")
        ident = entry.get("id")
        if not isinstance(ident, str) or not ident or len(ident) > 96:
            raise CaptureError("INVALID_SOURCE_ID")
        if ident in ids:
            raise CaptureError("DUPLICATE_SOURCE_ID")
        ids.add(ident)
        url = validate_url(entry.get("url"))
        if url in urls:
            raise CaptureError("DUPLICATE_URL")
        urls.add(url)
        if entry.get("lane") not in {
            "market", "competitive", "opposition", "buyers",
            "carrier_regulatory", "technology", "economics", "strategy",
        }:
            raise CaptureError("UNKNOWN_RESEARCH_LANE")
        if not isinstance(entry.get("publisher"), str) or not entry["publisher"].strip():
            raise CaptureError("MISSING_PUBLISHER")


def resolve_public_host(host: str) -> None:
    """DNS guard in addition to fixed-host allowlist; not a network firewall."""
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise CaptureError("DNS_FAILURE") from exc
    if not addresses:
        raise CaptureError("DNS_NO_ANSWERS")
    for record in addresses:
        try:
            ip = ip_address(record[4][0])
        except (ValueError, IndexError, TypeError) as exc:
            raise CaptureError("DNS_INVALID_ADDRESS") from exc
        if not ip.is_global:
            raise CaptureError("DNS_NONPUBLIC_ADDRESS")


class DenyRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise CaptureError("REDIRECT_REJECTED")


class BoundedHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data):
        if not self.hidden_depth:
            self.items.append(data)


def text_excerpt(blob: bytes, mime: str) -> str:
    decoded = blob.decode("utf-8", errors="replace")
    if mime in {"text/html", "application/xhtml+xml"}:
        parser = BoundedHTML()
        parser.feed(decoded)
        decoded = " ".join(parser.items)
    normalized = " ".join(decoded.split())
    return normalized[:MAX_EXCERPT_CHARS]


def http_read(url: str) -> tuple[int, str, str, bytes]:
    """Never follow redirects. Resolve fixed public DNS just before TLS request.

    This is a defense-in-depth measure, not absolute protection against DNS
    rebinding; use only the preapproved named publisher hosts.
    """
    parts = urlsplit(validate_url(url))
    resolve_public_host(parts.hostname)
    opener = build_opener(DenyRedirects)
    req = Request(url, headers={
        "User-Agent": "RETALLY-Research-Source-Review/1.0",
        "Accept": "text/html,text/plain,application/xhtml+xml",
        "Accept-Encoding": "identity",
    }, method="GET")
    try:
        with opener.open(req, timeout=TIMEOUT_SECONDS) as response:
            code = response.getcode()
            mime = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            final = response.geturl()
            raw = response.read(MAX_BYTES + 1)
    except CaptureError:
        raise
    except Exception as exc:
        raise CaptureError("HTTP_REQUEST_FAILED") from exc
    return code, final, mime, raw


def capture(manifest: dict, *, selected: list[str] | None = None,
            network_enabled: bool = False, transport=None,
            now: datetime | None = None) -> dict:
    """Collect candidates only. Live network needs explicit opt-in."""
    validate_manifest(manifest)
    if not network_enabled:
        raise CaptureError("NETWORK_DISABLED_EXPLICIT_CONSENT_REQUIRED")
    entries = {s["id"]: s for s in manifest["sources"]}
    ids = selected if selected is not None else list(entries)
    if not ids or len(ids) > MAX_SOURCES or len(set(ids)) != len(ids):
        raise CaptureError("INVALID_SELECTION")
    if any(item not in entries for item in ids):
        raise CaptureError("UNKNOWN_SOURCE_SELECTION")
    observed_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    fetch = transport if transport is not None else http_read
    receipts = []
    for ident in ids:
        source = entries[ident]
        url = validate_url(source["url"])
        base = {
            "id": ident, "publisher": source["publisher"], "lane": source["lane"],
            "url": url, "captured_at_utc": observed_at,
            "publisher_content_truth_verified": False,
            "claim_import_authorized": False,
        }
        try:
            code, final, mime, raw = fetch(url)
            if code != 200:
                raise CaptureError("HTTP_STATUS_NOT_200")
            if final != url:
                raise CaptureError("FINAL_URL_DIFFERENT")
            if mime not in SAFE_MIME:
                raise CaptureError("CONTENT_TYPE_UNSUPPORTED")
            if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BYTES:
                raise CaptureError("BODY_EMPTY_OR_TOO_LARGE")
            excerpt = text_excerpt(raw, mime)
            if not excerpt:
                raise CaptureError("TEXT_EXTRACTION_EMPTY")
            receipts.append({
                **base, "status": "CANDIDATE_UNREVIEWED", "http_status": code,
                "content_type": mime, "body_size_bytes": len(raw),
                "raw_body_sha256": sha_hex(raw),
                "preview_excerpt": excerpt,
                "preview_excerpt_sha256": sha_hex(excerpt.encode("utf-8")),
                "full_body_saved": False,
            })
        except CaptureError as exc:
            receipts.append({**base, "status": "FETCH_FAILED_OR_REJECTED",
                             "reason": str(exc), "claim_import_authorized": False})
    out = {
        "schema_version": SCHEMA_VERSION,
        "status": "CANDIDATES_NEED_HUMAN_SOURCE_REVIEW",
        "network_execution": True,
        "no_claim_verification": True,
        "captures": receipts,
        "fetch_error_count": sum(r["status"] != "CANDIDATE_UNREVIEWED" for r in receipts),
    }
    out["receipt_sha256"] = canonical_sha(out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Manual, bounded public-page candidate fetch")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-id", action="append")
    parser.add_argument("--execute", action="store_true",
                        help="Required confirmation before any live public GET request")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not args.execute:
        raise SystemExit("NETWORK_DISABLED: pass --execute for an explicit one-time public fetch")
    result = capture(data, selected=args.source_id, network_enabled=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "sources": len(result["captures"]),
        "not_reviewed": sum(x["status"] == "CANDIDATE_UNREVIEWED" for x in result["captures"]),
        "rejected_or_failed": result["fetch_error_count"],
        "receipt_sha256": result["receipt_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
