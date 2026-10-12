"""Read-only RETALLY production release drift audit (never sends inquiries).

GitHub Actions runs this independently of Cloudflare's source build so a green
build cannot conceal a missing public asset or disabled HTTPS security header.
"""
from __future__ import annotations

import hashlib
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

CANONICAL = "https://www.retallyrecovery.com/"
APEX = "https://retallyrecovery.com/"
MIN_HSTS_SECONDS = 86400
APPROVED_MEDIA = {
    "assets/brand/retally-wordmark-approved.png":
        "08421ccd7e8b1db752002f7ea177e76c83b6ee1cae40cf8b459368ade0c4eadd",
    "assets/brand/retally-emblem-approved.png":
        "bb02ab4a468762f597c241199baeff61b485dd793f8fb746140ad33670b68043",
}


class LiveAuditError(AssertionError):
    """Production returned an unexpected published state."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def fetch(url: str) -> tuple[int, object, bytes]:
    """A GET-only bounded public request, without cookies or credentials."""
    opener = urllib.request.build_opener(_NoRedirect())
    req = urllib.request.Request(url, headers={
        "User-Agent": "RETALLY-Public-Release-Audit/1.0",
        "Cache-Control": "no-cache",
    }, method="GET")
    try:
        response = opener.open(req, timeout=18)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, response.headers, response.read(2_000_001)


def ensure_security_headers(headers) -> None:
    hsts = headers.get("Strict-Transport-Security", "")
    duration = re.search(r"(?:^|;)\s*max-age=(\d+)(?:;|$)", hsts, re.I)
    if not duration or int(duration.group(1)) < MIN_HSTS_SECONDS:
        raise LiveAuditError("Production HSTS policy missing or below staged minimum")
    if headers.get("X-Content-Type-Options", "").lower() != "nosniff":
        raise LiveAuditError("Production X-Content-Type-Options missing nosniff")
    csp = headers.get("Content-Security-Policy", "")
    if "frame-ancestors 'none'" not in csp or "object-src 'none'" not in csp:
        raise LiveAuditError("Production Content Security Policy lost key isolation controls")


def ensure_logo(data: bytes, path: str) -> None:
    expected = APPROVED_MEDIA[path]
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise LiveAuditError(f"Published logo is not an intact PNG: {path}")
    if hashlib.sha256(data).hexdigest() != expected:
        raise LiveAuditError(f"Published brand master SHA-256 mismatch: {path}")


def ensure_html(html: str, url: str) -> None:
    if '<link rel="canonical" href="' + url + '"' not in html:
        raise LiveAuditError(f"Missing exact canonical link on {url}")
    if ("assets/brand/retally-emblem.webp" in html or
            "assets/brand/retally-wordmark.webp" in html):
        raise LiveAuditError(f"Retired bitmap logo is referenced on {url}")
    if ("yorktowne" in html.lower() or "jayp19386@" in html.lower()):
        raise LiveAuditError(f"Private contact identifier exposed on {url}")


def inspect_live_site() -> dict[str, object]:
    status, headers, homepage = fetch(CANONICAL)
    if status != 200:
        raise LiveAuditError(f"Production homepage HTTP {status}")
    ensure_security_headers(headers)
    html = homepage.decode("utf-8")
    ensure_html(html, CANONICAL)
    for path in APPROVED_MEDIA:
        if path not in html:
            raise LiveAuditError(f"Approved artwork is missing from home HTML: {path}")
        asset_status, asset_headers, blob = fetch(CANONICAL + path)
        if asset_status != 200 or "image/png" not in asset_headers.get("Content-Type", ""):
            raise LiveAuditError(f"Approved logo not served as PNG: {path}")
        ensure_logo(blob, path)

    for url in ("http://retallyrecovery.com/", "http://www.retallyrecovery.com/", APEX):
        code, response_headers, _ = fetch(url)
        if code not in (301, 302, 307, 308) or response_headers.get("Location") != CANONICAL:
            raise LiveAuditError(f"HTTP/hostname redirect not canonical: {url}")

    os_status, os_headers, os_body = fetch(CANONICAL + "recoveryos/")
    if os_status != 200 or b"<html" not in os_body.lower():
        raise LiveAuditError("RecoveryOS public information page missing")
    ensure_security_headers(os_headers)

    map_status, _, body = fetch(CANONICAL + "sitemap.xml")
    if map_status != 200:
        raise LiveAuditError("Production sitemap missing")
    root = ET.fromstring(body)
    locs = [el.text for el in root.findall(".//{*}loc") if el.text]
    if len(locs) < 25 or len(locs) != len(set(locs)) or CANONICAL not in locs:
        raise LiveAuditError("Production sitemap incomplete or duplicates URLs")
    if any(not x.startswith(CANONICAL) for x in locs):
        raise LiveAuditError("Sitemap advertises a noncanonical hostname")
    for url in locs:
        code, _, contents = fetch(url)
        if code != 200:
            raise LiveAuditError(f"Indexable public page failed: {url} (HTTP {code})")
        ensure_html(contents.decode("utf-8"), url)

    # Online intake is deliberately disabled pending separate mailbox QA.
    # A 503 is acceptable; never attempt a POST or assert delivery.
    intake_status, _, _ = fetch(CANONICAL + "api/inquiry")
    if intake_status not in (200, 503):
        raise LiveAuditError(f"Unexpected inquiry status: HTTP {intake_status}")

    return {
        "production": "verified",
        "pages": len(locs),
        "approved_logo_hashes": "verified",
        "tls_redirects": "verified",
        "hsts_nosniff_csp": "verified",
        "inquiry_status": "disabled" if intake_status == 503 else "online_not_delivery_verified",
    }


if __name__ == "__main__":
    print(inspect_live_site())
