#!/usr/bin/env python3
"""Read-only RETALLY public media and landing-page preflight.

Offline manifest generation by default. Optional HTTPS GET inspection only
for exact allowlisted public hostnames; never touches social account APIs,
publication settings, customer records, or the audit submission form.

This complements queue_preflight.py (planner drift), social_review.py
(independently verified publication), and verify_production_site.py (site
release/security), without duplicating their responsibilities.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from social_review import read_json

CDN = "static.metricool.com"
SITE = "www.retallyrecovery.com"
MAX_IMAGE = 6_000_000
MAX_PAGE = 1_000_000
MAX_URL = 1600
TIMEOUT_SECONDS = 15
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
IMAGE_MIMES = ("image/jpeg", "image/png", "image/webp")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _allowed(url: str, kind: str) -> bool:
    """Exact hostname allowlist protects on-demand GETs from SSRF."""
    if not isinstance(url, str) or len(url) > MAX_URL:
        return False
    try:
        p = urlsplit(url)
        if p.scheme != "https" or p.username or p.password:
            return False
        if p.port not in (None, 443) or p.fragment and kind == "image":
            return False
        if any(v in p.path.lower() for v in ("%2e", "%2f", "%5c", "..", "\\")):
            return False
        if kind == "image":
            return (p.hostname == CDN and p.path.startswith("/planner/")
                    and p.path.lower().endswith(IMAGE_EXTENSIONS)
                    and not p.query)
        if kind == "landing":
            qs = parse_qs(p.query, keep_blank_values=True, strict_parsing=False)
            return (p.hostname == SITE and
                    qs.get("utm_source") == ["facebook"] and
                    qs.get("utm_medium") == ["organic_social"] and
                    len(qs.get("utm_campaign", [])) == 1 and
                    len(qs["utm_campaign"][0]) > 0 and
                    len(qs.get("utm_content", [])) == 1 and
                    len(qs["utm_content"][0]) > 0)
        return False
    except (ValueError, TypeError, KeyError):
        return False


def _fb_url(caption: str) -> str | None:
    urls = re.findall(r"https://[^\s<>()]+", caption)
    accepted = [url.rstrip(".,;]") for url in urls
                if _allowed(url.rstrip(".,;]"), "landing")]
    return accepted[0] if len(set(accepted)) == 1 else None


def targets(snapshot: dict, *, include_drafts: bool = False) -> list[dict]:
    """Create unique URL targets from exact immutable planner snapshot."""
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("data"), list):
        raise ValueError("Expected a Metricool snapshot containing data array")
    merged: dict[tuple[str, str], dict] = {}
    uuids = set()
    for post in snapshot["data"]:
        if not isinstance(post, dict):
            raise ValueError("Post must be an object")
        providers = post.get("providers") or []
        if len(providers) != 1 or providers[0].get("network") not in ("facebook", "instagram"):
            continue
        uid = post.get("uuid")
        if not isinstance(uid, str) or not uid or uid in uuids:
            raise ValueError("Missing or duplicate Facebook/Instagram stable UUID")
        uuids.add(uid)
        if post.get("draft") is not False and not include_drafts:
            continue
        network = providers[0]["network"]
        media = post.get("media")
        if not isinstance(media, list) or not media:
            raise ValueError(f"{uid}: no scheduled media")
        alts = post.get("mediaAltText")
        if not isinstance(alts, list) or len(media) != len(alts) or any(
                not isinstance(x, str) or not x.strip() for x in alts):
            raise ValueError(f"{uid}: missing or mismatched media alt text")
        def insert(kind: str, url: str):
            if not _allowed(url, kind):
                raise ValueError(f"{uid}: URL blocked by public-{kind} allowlist")
            key = (kind, url)
            if key not in merged:
                merged[key] = {"kind": kind, "url": url, "uuids": [], "networks": []}
            merged[key]["uuids"].append(uid)
            if network not in merged[key]["networks"]:
                merged[key]["networks"].append(network)
        for url in media:
            insert("image", url)
        if network == "facebook" and not post.get("draft"):
            landing = _fb_url(post.get("text") or "")
            if not landing:
                raise ValueError(f"{uid}: missing unique tracked Facebook destination")
            insert("landing", landing)
    return sorted(merged.values(), key=lambda item: (item["kind"], item["url"]))


def _dimensions(blob: bytes) -> tuple[int, int] | None:
    """Read PNG/JPEG image dimensions with the Python standard library."""
    if blob.startswith(b"\x89PNG\r\n\x1a\n") and len(blob) >= 24:
        width, height = struct.unpack(">II", blob[16:24])
        return (width, height) if width and height else None
    if blob.startswith(b"\xff\xd8"):
        pos = 2
        while pos + 4 < len(blob):
            if blob[pos] != 0xFF:
                pos += 1
                continue
            marker = blob[pos + 1]
            pos += 2
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                continue
            if pos + 2 > len(blob):
                break
            length = int.from_bytes(blob[pos:pos+2], "big")
            if length < 2 or pos + length > len(blob):
                break
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                          0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF) and length >= 7:
                height = int.from_bytes(blob[pos + 3:pos + 5], "big")
                width = int.from_bytes(blob[pos + 5:pos + 7], "big")
                return (width, height) if width and height else None
            pos += length
    return None


def fetch(url: str, kind: str) -> tuple[int, dict[str, str], bytes]:
    """One bounded GET; redirect explicitly refused, no cookies or credentials."""
    if not _allowed(url, kind):
        raise ValueError("URL denied by allowlist")
    opener = urllib.request.build_opener(_NoRedirect())
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "RETALLY-Organic-Public-Preflight/1.0",
                 "Cache-Control": "no-cache", "Accept": "image/*,text/html"},
        method="GET")
    try:
        response = opener.open(req, timeout=TIMEOUT_SECONDS)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        limit = MAX_IMAGE if kind == "image" else MAX_PAGE
        body = response.read(limit + 1)
        if len(body) > limit:
            raise ValueError("Public response exceeds bounded size cap")
        return response.status, dict(response.headers.items()), body


def inspect(item: dict, *, fetcher=fetch) -> dict:
    """Report what this network vantage point observed, never global guarantees."""
    result = dict(item)
    try:
        status, headers, blob = fetcher(item["url"], item["kind"])
        mime = next((v for k, v in headers.items()
                     if k.lower() == "content-type"), "").lower().split(";")[0].strip()
        result["http_status"] = status
        if status in (404, 410):
            result.update(state="FAIL", reason=f"Public endpoint returned HTTP {status}")
        elif status != 200:
            result.update(state="RECHECK", reason=f"Public endpoint returned HTTP {status}; verify provider-side")
        elif item["kind"] == "image":
            if mime not in IMAGE_MIMES:
                result.update(state="FAIL", reason="Public media served non-image content type")
            else:
                dimensions = _dimensions(blob)
                if not dimensions:
                    result.update(state="FAIL", reason="Media image magic/dimensions could not be validated")
                else:
                    width, height = dimensions
                    result["dimensions"] = [width, height]
                    if width < 640 or height < 640:
                        result.update(state="RECHECK", reason="Image appears below feed-quality size")
                    elif height < width:
                        result.update(state="RECHECK", reason="Landscape asset may crop in mobile feed")
                    else:
                        result.update(state="PASS", reason="Reachable image with valid dimensions")
        else:
            if mime not in ("text/html", "application/xhtml+xml"):
                result.update(state="FAIL", reason="Campaign destination not served as HTML")
            elif b"<html" not in blob.lower() or b"retally" not in blob.lower():
                result.update(state="RECHECK", reason="Landing page lacks expected HTML/RETALLY marker")
            else:
                result.update(state="PASS", reason="Canonical tagged landing page responds with RETALLY HTML")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        # Do not mislabel CDN geo-blocks, intermittent outages or DNS failures
        # as globally broken. Avoid exposing secrets or exception URLs.
        result.update(state="RECHECK", reason=f"Unverified from this network: {type(error).__name__}")
    return result


def run(snapshot: dict, *, live: bool = False, include_drafts: bool = False,
        fetcher=fetch) -> dict:
    manifest = targets(snapshot, include_drafts=include_drafts)
    inspected = [inspect(item, fetcher=fetcher) if live
                 else {**item, "state": "NOT_CHECKED", "reason": "Network inspection not requested"}
                 for item in manifest]
    counts = {k: sum(x["state"] == k for x in inspected)
              for k in ("PASS", "FAIL", "RECHECK", "NOT_CHECKED")}
    return {
        "mode": "public_https_get" if live else "offline_manifest",
        "publication_verified": False,
        "live_social_provider_checked": False,
        "counts": counts,
        "targets": inspected,
        "limitations": [
            "A public CDN image is not proof that Meta published a post.",
            "HTTP checks are from one vantage point; timeouts and 403s require provider review.",
            "Tracking tags in the requested URL do not prove page visits or actual inquiries.",
            "The RETALLY audit form is NOT submitted or accessed by this tool.",
        ],
    }


def markdown(result: dict) -> str:
    lines = [
        "# RETALLY — public media and landing-page preflight",
        f"Mode: {result['mode']}. Social publication: **NOT VERIFIED**.",
        "",
        " | ".join(f"{key}: **{value}**" for key, value in result["counts"].items()),
        "",
        "| Type | Public URL | Status | Observation |",
        "| --- | --- | --- | --- |",
    ]
    for entry in result["targets"]:
        url = entry["url"].replace("|", "%7C")
        reason = entry["reason"].replace("|", " ")
        lines.append(f"| {entry['kind']} | {url} | {entry['state']} | {reason} |")
    lines.append("")
    lines.extend(f"- {caveat}" for caveat in result["limitations"])
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--schedule", required=True, help="Saved Metricool planner JSON")
    ap.add_argument("--live", action="store_true",
                    help="Opt-in public allowlisted HTTPS GET checks; no social API access")
    ap.add_argument("--include-drafts", action="store_true",
                    help="Also verify unpublished draft media; never publish them")
    ap.add_argument("--output", help="Optional Markdown destination")
    ap.add_argument("--json-output", help="Optional JSON destination")
    ap.add_argument("--fail-on-hard-errors", action="store_true",
                    help="Exit code 2 for an observed FAIL; RECHECK remains explicitly uncertain")
    args = ap.parse_args()
    result = run(read_json(args.schedule), live=args.live,
                 include_drafts=args.include_drafts)
    if args.output:
        Path(args.output).write_text(markdown(result), encoding="utf-8")
    else:
        print(markdown(result))
    if args.json_output:
        Path(args.json_output).write_text(json.dumps(result, indent=2) + "\n",
                                         encoding="utf-8")
    if args.fail_on_hard_errors and result["counts"]["FAIL"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
