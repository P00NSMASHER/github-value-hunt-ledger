#!/usr/bin/env python3
"""Exercise RETALLY's dormant online-receipt UI using isolated synthetic browser traffic.

This does not contact Cloudflare, send mail, or change production inquiry flags.
Every request is fulfilled from the built site or an in-memory API fixture.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlparse

from playwright.sync_api import sync_playwright

HOST = "www.retallyrecovery.com"
REFERENCE = "RA-20261009-CAFEBABE"


def verify(site: Path, out: Path) -> dict:
    site = site.resolve()
    if not (site / "index.html").is_file() or not (site / "site.js").is_file():
        raise ValueError("Expected a complete, locally built RETALLY site")
    out.mkdir(parents=True, exist_ok=True)
    posts = []

    def intercept(route):
        request = route.request
        url = urlparse(request.url)
        if url.hostname == HOST and url.path == "/api/inquiry":
            if request.method == "GET":
                return route.fulfill(status=200, content_type="application/json",
                    body=json.dumps({"online": True, "siteKey": "syntheticSiteKey123"}))
            if request.method == "POST":
                posts.append(json.loads(request.post_data or "{}"))
                return route.fulfill(status=202, content_type="application/json",
                    body=json.dumps({"received": True, "reference": REFERENCE}))
            return route.abort()
        if url.hostname == HOST:
            path = unquote(url.path.lstrip("/")) or "index.html"
            candidate = (site / path).resolve()
            if site not in candidate.parents or not candidate.is_file():
                return route.fulfill(status=404, body="Not found")
            mime = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
            return route.fulfill(status=200, path=str(candidate), content_type=mime)
        if url.hostname == "challenges.cloudflare.com" and url.path.endswith("/api.js"):
            # Script loads successfully without contacting the live Turnstile service.
            return route.fulfill(status=200, content_type="application/javascript",
                body="window.turnstile = { reset() {} };")
        return route.abort()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        # The public-only build deliberately embeds connect-src 'none' for
        # GitHub Pages. Bypass it ONLY in this isolated intercepted browser:
        # Cloudflare's production-specific CSP is untouched, and all outside
        # requests are blocked by intercept().
        context = browser.new_context(viewport={"width": 390, "height": 844},
            is_mobile=True, has_touch=True, reduced_motion="reduce", bypass_csp=True)
        context.route("**/*", intercept)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = page.goto(f"https://{HOST}/index.html", wait_until="load", timeout=30000)
        if response is None or response.status != 200:
            raise AssertionError("Synthetic site did not load")
        page.wait_for_function("""() => document.querySelector(
            '#auditForm button[type="submit"]')?.textContent.includes('Submit My Free Audit Request')""")
        page.locator("#fullName").fill("Synthetic Buyer")
        page.locator("#workEmail").fill("buyer@example.invalid")
        page.locator("#companyName").fill("TEST ONLY - NO CONTACT")
        page.locator("#annualSpend").select_option(label="$250k–$1M")
        page.locator('input[name="modes"][value="LTL"]').check()
        page.evaluate("""() => {
            const token = document.createElement('input');
            token.name = 'cf-turnstile-response';
            token.value = 'synthetic-token-not-verified';
            document.querySelector('#auditForm').append(token);
        }""")
        page.locator("#auditForm button[type=submit]").click()
        page.locator("#auditReady").wait_for(state="visible", timeout=15000)
        ready = page.locator("#auditReady")
        report = {
            "method": "isolated fixture; no network, email, or customer data",
            "source": str(site),
            "postCount": len(posts),
            "sampleEmailOnly": len(posts) == 1 and
                posts[0].get("workEmail") == "buyer@example.invalid",
            "durableHeading": ready.locator("h3").inner_text(),
            "referenceShown": REFERENCE in ready.inner_text(),
            "formHidden": not page.locator("#auditForm").is_visible(),
            "mailOnlyControlsHidden": {
                selector: not page.locator(selector).is_visible()
                for selector in (
                    "#sendAuditRequest", "#copyAuditSummary", "#copyAuditEmail",
                    "#copyStatus", ".audit-manual-fallback"
                )
            },
            "noResendInstruction": (
                "Your request has not been sent yet" not in ready.inner_text()
                and "If no email draft opens" not in ready.inner_text()
            ),
            "pageErrors": errors,
        }
        page.screenshot(path=str(out / "durable-receipt-390x844.jpg"),
            type="jpeg", quality=72, full_page=False)
        context.close()
        browser.close()

    (out / "durable-receipt-acceptance.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    if (report["postCount"] != 1 or not report["sampleEmailOnly"]
            or report["durableHeading"] != "RETALLY has received your request."
            or not report["referenceShown"] or not report["formHidden"]
            or not all(report["mailOnlyControlsHidden"].values())
            or not report["noResendInstruction"] or report["pageErrors"]):
        raise AssertionError("Durable receipt browser acceptance failed: " + json.dumps(report))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.site, args.out), indent=2))
