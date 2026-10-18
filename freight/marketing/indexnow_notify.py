"""RETALLY IndexNow changed-page notification, not an indexing guarantee.

Runs only after a successful first-party live publication audit on a main push.
Read-only checks on our public site, then at most one outbound IndexNow POST.
No customer, advertising-account, or private operational records are read.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = "https://www.retallyrecovery.com/"
HOST = "www.retallyrecovery.com"
KEY = "1a17119c023bc3e3c0abe34188f4eeb4"
KEY_PATH = KEY + ".txt"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
IGNORED_HTML = frozenset({"404.html", "recovery-status-example.html"})
USER_AGENT = "RETALLY-Public-IndexNow/1.0"


def changed_public_urls(paths: list[str]) -> list[str]:
    """Translate only actual first-party changed HTML source into canonical URLs."""
    output = set()
    for path in paths:
        if not path.startswith("freight/site/"):
            continue
        stem = path.removeprefix("freight/site/")
        if "/" in stem or not stem.endswith(".html") or stem in IGNORED_HTML:
            continue
        if stem.startswith("google"):
            continue
        slug = stem[:-5]
        if not slug or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in slug):
            continue
        output.add(ROOT if slug == "index" else ROOT + slug)
    return sorted(output)


def changed_git_paths(commit: str) -> list[str]:
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("Expected exact 40-character Git commit SHA")
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=AMR", commit + "^1", commit,
         "--", "freight/site"],
        check=True, capture_output=True, text=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _get(url: str) -> tuple[str, str]:
    if not url.startswith(ROOT):
        raise ValueError("Only RETALLY public HTTPS URLs may be checked")
    request = urllib.request.Request(
        url, method="GET", headers={"User-Agent": USER_AGENT, "Cache-Control": "no-cache"}
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.status != 200 or response.geturl() != url:
            raise RuntimeError("Public URL is not an exact 200 canonical destination")
        return response.read(2_000_001).decode("utf-8"), response.headers.get("Content-Type", "")


def verify_published(urls: list[str]) -> None:
    """Prove the public key and every notified page are live before submission."""
    keybody, _ = _get(ROOT + KEY_PATH)
    if keybody.strip() != KEY:
        raise RuntimeError("IndexNow ownership key file not yet publicly verified")
    xml, _ = _get(ROOT + "sitemap.xml")
    root = ET.fromstring(xml)
    visible = {
        el.text for el in root.findall(".//{*}loc") if el.text and el.text.startswith(ROOT)
    }
    for url in urls:
        if url not in visible:
            raise RuntimeError("Changed URL not yet listed in the live canonical sitemap")
        markup, _ = _get(url)
        if f'<link rel="canonical" href="{url}">' not in markup:
            raise RuntimeError("Changed URL canonical not yet present in production")


def make_payload(urls: list[str]) -> bytes:
    if not urls or len(urls) > 100:
        raise ValueError("Expect 1-100 genuinely changed pages in one release")
    if len(set(urls)) != len(urls) or any(not url.startswith(ROOT) for url in urls):
        raise ValueError("URL list contains duplicate or noncanonical destination")
    return json.dumps({
        "host": HOST, "key": KEY, "keyLocation": ROOT + KEY_PATH, "urlList": urls,
    }, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def submit_once(urls: list[str]) -> int:
    """Send exactly one bounded update to IndexNow; never retry ambiguous POSTs."""
    request = urllib.request.Request(
        INDEXNOW_ENDPOINT, data=make_payload(urls), method="POST",
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            code = int(response.status)
    except urllib.error.HTTPError as error:
        code = error.code
    if code not in (200, 202):
        raise RuntimeError(f"IndexNow declined submission (HTTP {code}); no automatic retry")
    return code


def notify(commit: str, attempts: int = 15, delay: int = 20) -> dict[str, object]:
    urls = changed_public_urls(changed_git_paths(commit))
    if not urls:
        return {"state": "skipped", "reason": "No first-party HTML pages changed"}
    for attempt in range(1, attempts + 1):
        try:
            verify_published(urls)
            break
        except (OSError, ET.ParseError, RuntimeError, UnicodeDecodeError) as error:
            if attempt == attempts:
                raise RuntimeError(
                    f"Public pages/key not verified after {attempts} bounded attempts"
                ) from error
            print(f"Production readiness unavailable on check {attempt}/{attempts}; retrying verification.")
            time.sleep(delay)
    response = submit_once(urls)
    return {
        "state": "received", "changed_urls": urls, "http_status": response,
        "note": "IndexNow acknowledged receipt; crawl, ranking and indexing are not guaranteed.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--attempts", type=int, default=15)
    parser.add_argument("--delay", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.attempts <= 20 or not 0 <= args.delay <= 60:
        parser.error("Invalid bounded verification retry settings")
    print(json.dumps(notify(args.sha, args.attempts, args.delay), indent=2))
