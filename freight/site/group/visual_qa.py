"""Isolated CI acceptance for the consolidated marketing site; no live traffic."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright
from freight.site.group.build import ROUTES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(args.site.resolve())))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    report = {"pages": [], "interactions": [], "non_get_requests": [], "external_requests_blocked": 0}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            for width, height in ((1440, 900), (768, 1024), (390, 844), (320, 700)):
                context = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce")
                def route(request_route):
                    request = request_route.request
                    if request.method != "GET":
                        report["non_get_requests"].append(request.method)
                        request_route.abort()
                    elif urlsplit(request.url).netloc != urlsplit(base).netloc:
                        report["external_requests_blocked"] += 1
                        request_route.abort()
                    else:
                        request_route.continue_()
                context.route("**/*", route)
                page = context.new_page()
                for slug in ("",) + ROUTES:
                    response = page.goto(base + "/" + (slug + "/" if slug else ""), wait_until="networkidle")
                    page.evaluate("document.fonts.ready")
                    result = page.evaluate("""() => ({
                      overflow: document.documentElement.scrollWidth - innerWidth,
                      h1Count: document.querySelectorAll('h1').length,
                      brokenImages: [...document.images].filter(im => !im.complete || !im.naturalWidth).map(im => im.getAttribute('src')),
                      title: document.title,
                      mainPresent: !!document.querySelector('main#main')
                    })""")
                    result.update({"route": slug or "home", "width": width, "status": response.status})
                    report["pages"].append(result)
                    assert result["status"] == 200 and result["overflow"] <= 1 and result["h1Count"] == 1 and result["mainPresent"] and not result["brokenImages"], result
                    if (width == 390 or (width == 1440 and slug in ("", "capturebrief", "recovery"))):
                        page.screenshot(path=str(args.out / f'{slug or "home"}-{width}.png'), full_page=True)
                page.goto(base + "/")
                menu = page.locator(".business-menu summary")
                menu.focus()
                page.keyboard.press("Enter")
                assert page.locator(".business-menu").get_attribute("open") is not None
                assert page.locator(".business-menu-panel a").count() == 11
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                page.keyboard.press("Escape")
                assert page.locator(".business-menu").get_attribute("open") is None
                page.locator('.business-card[href="/capturebrief/"]').click()
                page.wait_for_url("**/capturebrief/")
                assert page.get_by_role("heading", name="Know what your bid decision rests on.").is_visible()
                page.goto(base + "/?utm_source=acceptance#start-audit")
                page.wait_for_url("**/recovery/?utm_source=acceptance#start-audit")
                assert page.locator("#auditForm").is_visible()
                report["interactions"].append({"width": width, "menu_keyboard": True, "business_navigation": True, "legacy_freight_anchor": True})
                context.close()
            browser.close()
        assert not report["non_get_requests"]
        report["passed"] = True
    finally:
        server.shutdown()
        (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("RETALLY Group: 52 responsive page checks, keyboard menus, business navigation and legacy freight anchors passed; no POSTs sent.")


if __name__ == "__main__":
    main()
