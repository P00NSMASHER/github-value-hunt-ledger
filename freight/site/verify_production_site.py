"""Read-only RETALLY production release drift audit (never sends inquiries).

GitHub Actions runs this independently of Cloudflare's source build so a green
build cannot conceal a missing public asset or disabled HTTPS security header.
"""
from __future__ import annotations

import hashlib
import csv
from io import StringIO
from pathlib import Path
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from time import perf_counter, sleep
from urllib.parse import urlsplit

from freight.site.internal_links import validate_live_links

CANONICAL = "https://www.retallyrecovery.com/"
APEX = "https://retallyrecovery.com/"
MIN_HSTS_SECONDS = 86400
LTL_COMPARATOR_PAGE = CANONICAL + "ltl-reweigh-evidence-comparator"
LTL_COMPARATOR_SCRIPT = CANONICAL + "ltl-evidence-comparator.js"
EVIDENCE_LEDGER_RESOURCE = "freight-recovery-evidence-ledger.csv"
# Retries apply ONLY to transient public GET 504s. Other statuses (including
# intentionally disabled inquiry GET 503) and content/security mismatches
# remain fail-closed. This does not reinterpret Cloudflare internal cache logs.
TRANSIENT_504_RETRY_DELAYS_SECONDS = (0.25, 0.5)
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
    """GET-only public read; tolerate two brief 504s, but never a persistent one.

    A final 504 stays visible to the existing live-audit failure gates.
    No redirect following, non-GET requests, customer data, or unbounded loops.
    """
    opener = urllib.request.build_opener(_NoRedirect())
    req = urllib.request.Request(url, headers={
        "User-Agent": "RETALLY-Public-Release-Audit/1.0",
        "Cache-Control": "no-cache",
    }, method="GET")
    for attempt in range(len(TRANSIENT_504_RETRY_DELAYS_SECONDS) + 1):
        try:
            response = opener.open(req, timeout=18)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            status, headers, body = (
                response.status, response.headers, response.read(2_000_001)
            )
        if status != 504 or attempt == len(TRANSIENT_504_RETRY_DELAYS_SECONDS):
            return status, headers, body
        print(
            f"Transient public GET HTTP 504 for {urlsplit(url).path or '/'}; "
            f"retry {attempt + 1}/{len(TRANSIENT_504_RETRY_DELAYS_SECONDS)}",
            flush=True,
        )
        sleep(TRANSIENT_504_RETRY_DELAYS_SECONDS[attempt])
    raise AssertionError("Unreachable bounded public GET state")


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



def ensure_ltl_comparator(html: str, script: str) -> None:
    """Require the new free LTL comparison workflow, not just an old healthy site.

    Public GET text is untrusted evidence; this check does not run any JavaScript,
    accept user data or call the inquiry endpoint with POST.
    """
    for marker in (
        'id="ltlCompareForm"',
        'id="ltlCompareResults"',
        'src="ltl-evidence-comparator.js?',
        "No login",
    ):
        if marker not in html:
            raise LiveAuditError(f"Production LTL comparator missing page contract: {marker}")
    if "function compare(input)" not in script:
        raise LiveAuditError("Production LTL comparator JavaScript missing calculation")
    for prohibited in ("fetch(", "XMLHttpRequest", "localStorage", "sessionStorage", "sendBeacon"):
        if prohibited in script:
            raise LiveAuditError("Production LTL calculator contains forbidden data access")



def ensure_blank_evidence_ledger(published: bytes, source: bytes) -> None:
    """Compare to the exact checked-out blank ledger; no user files are read."""
    if published != source:
        raise LiveAuditError("Production blank evidence ledger differs from verified release")
    try:
        rows = list(csv.reader(StringIO(published.decode("utf-8"))))
    except (UnicodeDecodeError, csv.Error) as error:
        raise LiveAuditError("Production blank ledger is not valid UTF-8 CSV") from error
    if len(rows) != 2 or len(rows[0]) != 24 or len(set(rows[0])) != 24:
        raise LiveAuditError("Production ledger schema is incomplete")
    for name in (
        "Candidate_Difference_Not_Savings", "Previously_Applied_Credit_Or_Existing_Claim",
        "Evidence_Status", "Customer_Authorization", "Reversal_Or_Offset",
        "Net_Eligible_Realized_Value_Subject_To_Terms",
    ):
        if name not in rows[0]:
            raise LiveAuditError("Production ledger lost its recovery-integrity boundary")
    if rows[1] != [""] * len(rows[0]):
        raise LiveAuditError("Production ledger must not contain customer or sample data")


def inspect_live_site() -> dict[str, object]:
    status, headers, homepage = fetch(CANONICAL)
    if status != 200:
        raise LiveAuditError(f"Production homepage HTTP {status}")
    ensure_security_headers(headers)
    html = homepage.decode("utf-8")
    ensure_html(html, CANONICAL)
    link_pages = {CANONICAL: html}
    known_good = {CANONICAL}
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
    link_pages[CANONICAL + "recoveryos/"] = os_body.decode("utf-8")
    known_good.add(CANONICAL + "recoveryos/")

    map_status, _, body = fetch(CANONICAL + "sitemap.xml")
    if map_status != 200:
        raise LiveAuditError("Production sitemap missing")
    root = ET.fromstring(body)
    locs = [el.text for el in root.findall(".//{*}loc") if el.text]
    if len(locs) < 25 or len(locs) != len(set(locs)) or CANONICAL not in locs:
        raise LiveAuditError("Production sitemap incomplete or duplicates URLs")
    if any(not x.startswith(CANONICAL) for x in locs):
        raise LiveAuditError("Sitemap advertises a noncanonical hostname")
    if LTL_COMPARATOR_PAGE not in locs:
        raise LiveAuditError("New LTL buyer comparator is missing from live sitemap")
    html_get_timings_ms = []
    for url in locs:
        started = perf_counter()
        code, _, contents = fetch(url)
        html_get_timings_ms.append((round((perf_counter() - started) * 1000), url))
        if code != 200:
            raise LiveAuditError(f"Indexable public page failed: {url} (HTTP {code})")
        page = contents.decode("utf-8")
        ensure_html(page, url)
        link_pages[url] = page
        known_good.add(url)

    # Check all clickable first-party destinations, not only sitemap entries.
    # Reuse already verified responses and never send contact form requests.
    link_audit = validate_live_links(link_pages, fetch, known_good)

    # The old build can pass a general sitemap audit before Cloudflare finishes.
    # Verify both the actual new HTML and its working first-party calculation
    # script, without executing code, contacting customers, or sending inquiry data.
    script_status, _, script_body = fetch(LTL_COMPARATOR_SCRIPT)
    if script_status != 200:
        raise LiveAuditError(f"Production LTL comparator script HTTP {script_status}")
    ensure_ltl_comparator(
        link_pages[LTL_COMPARATOR_PAGE],
        script_body.decode("utf-8"),
    )

    # A healthy stale site can otherwise pass without publishing the new
    # buyer download. The GET-only receipt verifies byte-for-byte public CSV.
    ledger_status, _, ledger_body = fetch(CANONICAL + EVIDENCE_LEDGER_RESOURCE)
    if ledger_status != 200:
        raise LiveAuditError(f"Production blank evidence ledger HTTP {ledger_status}")
    expected_ledger = Path(__file__).with_name(EVIDENCE_LEDGER_RESOURCE).read_bytes()
    ensure_blank_evidence_ledger(ledger_body, expected_ledger)

    # Online intake is deliberately disabled pending separate mailbox QA.
    # A 503 is acceptable; never attempt a POST or assert delivery.
    intake_status, _, _ = fetch(CANONICAL + "api/inquiry")
    if intake_status not in (200, 503):
        raise LiveAuditError(f"Unexpected inquiry status: HTTP {intake_status}")

    return {
        "production": "verified",
        "ltl_buyer_comparator": "verified",
        "blank_evidence_ledger": "verified",
        "pages": len(locs),
        "internal_links_checked": link_audit["destinations"],
        # Observability only: do not fail releases on noisy single-run latency.
        # Timings measure GET of public HTML, not browser LCP or Ahrefs load time.
        "slowest_html_get_ms": [
            {"url": url, "ms": milliseconds}
            for milliseconds, url in sorted(html_get_timings_ms, reverse=True)[:3]
        ],
        "internal_link_redirects": link_audit["redirected_destinations"],
        "approved_logo_hashes": "verified",
        "tls_redirects": "verified",
        "hsts_nosniff_csp": "verified",
        "inquiry_status": "disabled" if intake_status == 503 else "online_not_delivery_verified",
    }


if __name__ == "__main__":
    print(inspect_live_site())
