"""Isolated CI acceptance for the consolidated marketing site; no live traffic."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
from freight.site.group.build import ROUTES


def load_page_images(page):
    """Exercise native lazy loading before judging images or taking screenshots."""
    page.evaluate("""async () => {
      await document.fonts.ready;
      const nextPaint = () => new Promise(resolve =>
        requestAnimationFrame(() => requestAnimationFrame(resolve)));
      for (const image of document.querySelectorAll('img[loading="lazy"]')) {
        image.scrollIntoView({block: 'center', behavior: 'instant'});
        await nextPaint();
      }
      window.scrollTo({top: 0, behavior: 'instant'});
      await nextPaint();
    }""")
    try:
        page.wait_for_function("[...document.images].every(image => image.complete)", timeout=10000)
    except PlaywrightTimeoutError:
        # The document check below records the actual unfinished image URLs.
        # A broken image is never treated as a successful lazy-load check.
        pass


def check_contact_composer(page, base):
    page.goto(base + "/contact/", wait_until="networkidle")
    form = page.locator("#group-enquiry")
    assert form.is_visible()
    business = form.locator("#enquiry-business")
    message = form.locator("#enquiry-message")
    for control in (business, message):
        assert control.evaluate("element => [...element.labels].some(label => label.textContent.trim())"), "Enquiry field needs a visible label"
    submit = form.get_by_role("button", name="Open email draft", exact=True)
    assert submit.get_attribute("type") == "submit" and submit.is_visible()
    assert page.locator("#enquiry-status").evaluate("element => element.getAttribute('role') === 'status' || ['polite', 'assertive'].includes(element.getAttribute('aria-live'))")
    sample = "QA preview only. Please do not send this draft."
    business.select_option(label="CaptureBrief")
    message.fill(sample)
    page.wait_for_function("document.querySelector('#enquiry-draft')?.getAttribute('href')?.startsWith('mailto:')")
    draft = urlsplit(page.locator("#enquiry-draft").get_attribute("href"))
    fields = parse_qs(draft.query)
    assert draft.scheme == "mailto" and draft.path == "jay@retallyrecovery.com"
    assert "CaptureBrief" in fields.get("subject", [""])[0]
    assert sample in fields.get("body", [""])[0]
    assert page.locator("#enquiry-status").inner_text().strip()
    business.select_option(label="PermitPlate NYC")
    updated = parse_qs(urlsplit(page.locator("#enquiry-draft").get_attribute("href")).query)
    assert "PermitPlate NYC" in updated.get("subject", [""])[0]
    assert sample in updated.get("body", [""])[0]
    assert urlsplit(page.url).path == "/contact/"
    # Deliberately do not click the submit button or the mailto anchor.
    return {"email_draft_updates": True, "labelled_fields": True,
            "live_status": True, "submit_clicked": False, "mailto_navigation": False}


def check_chat_clearance(page, base, output, width, height):
    page.goto(base + "/recovery/#start-audit", wait_until="networkidle")
    launcher = page.locator("#retallyChatLauncher")
    assert launcher.count() == 1
    submit = page.locator('#auditForm button[type="submit"]')
    submit.scroll_into_view_if_needed()
    assert submit.is_visible()
    assert submit.evaluate("element => {const r = element.getBoundingClientRect(); return r.top < innerHeight && r.bottom > 0;}")
    launcher.wait_for(state="hidden")
    page.screenshot(path=str(output / f"recovery-intake-clear-{width}.png"), full_page=False)
    page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
    launcher.wait_for(state="visible")
    assert page.locator("#auditForm").evaluate("element => {const r = element.getBoundingClientRect(); return r.top >= innerHeight || r.bottom <= 0;}")
    return {"width": width, "height": height, "launcher_hidden_at_intake": True,
            "launcher_restored_at_hero": True, "form_submitted": False}


def check_accessibility(page, axe_source):
    # Only the isolated QA browser receives this script; deployed CSP is unchanged.
    page.add_script_tag(content=axe_source)
    return page.evaluate("""async () => {
      const result = await axe.run(document, {runOnly: {type: 'tag',
        values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']}});
      return {version: axe.version, violations: result.violations.map(violation => ({
        id: violation.id, impact: violation.impact, description: violation.description,
        nodes: violation.nodes.length, sample: violation.nodes.slice(0, 3).map(node => node.target),
        details: violation.nodes.map(node => ({target: node.target, failureSummary: node.failureSummary}))
      }))};
    }""")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--axe-js", type=Path, help="Local axe-core script; never fetched by the QA browser")
    args = parser.parse_args()
    if args.axe_js and not args.axe_js.is_file():
        parser.error("--axe-js must point to an existing local axe-core script")
    axe_source = args.axe_js.read_text() if args.axe_js else None
    args.out.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(args.site.resolve())))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    report = {"pages": [], "interactions": [], "chat_clearance": [], "non_get_requests": [],
              "external_requests_blocked": 0, "passed": False,
              "accessibility": {"status": "pending" if axe_source else "skipped",
                                "reason": None if axe_source else "No local axe-core script supplied with --axe-js",
                                "checks": [], "blocking_failures": []}}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            for width, height in ((1440, 900), (768, 1024), (390, 844), (375, 812), (320, 700)):
                context = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce",
                                              is_mobile=width <= 390, has_touch=width <= 390,
                                              bypass_csp=bool(axe_source))
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
                    load_page_images(page)
                    result = page.evaluate("""() => ({
                      overflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - innerWidth,
                      h1Count: document.querySelectorAll('h1').length,
                      brokenImages: [...document.images].filter(im => !im.complete || !im.naturalWidth).map(im => im.getAttribute('src')),
                      title: document.title,
                      mainPresent: !!document.querySelector('main#main')
                    })""")
                    result.update({"route": slug or "home", "width": width, "status": response.status})
                    report["pages"].append(result)
                    assert result["status"] == 200 and result["overflow"] <= 1 and result["h1Count"] == 1 and result["mainPresent"] and not result["brokenImages"], result
                    if axe_source:
                        accessibility = {"route": slug or "home", "width": width, **check_accessibility(page, axe_source)}
                        report["accessibility"]["checks"].append(accessibility)
                        blocking = [v for v in accessibility["violations"] if v["impact"] in ("serious", "critical")]
                        if blocking:
                            report["accessibility"]["blocking_failures"].append({
                                "route": slug or "home", "width": width, "violations": blocking})
                            report["accessibility"]["status"] = "failed"
                    # Capture every route/viewport, including failed accessibility checks,
                    # so one defect cannot hide the remaining release evidence.
                    page.screenshot(path=str(args.out / f'{slug or "home"}-{width}.png'), full_page=True)
                    if slug in ("", "capturebrief", "contact"):
                        page.screenshot(path=str(args.out / f'{slug or "home"}-{width}-viewport.png'), full_page=False)
                page.goto(base + "/")
                menu = page.locator(".business-menu summary")
                menu.focus()
                page.keyboard.press("Enter")
                assert page.locator(".business-menu").get_attribute("open") is not None
                assert page.locator(".business-menu-panel a").count() == 11
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                page.keyboard.press("Escape")
                assert page.locator(".business-menu").get_attribute("open") is None
                assert menu.evaluate("element => element === document.activeElement")
                page.locator('.business-card[href="/capturebrief/"]').first.click()
                page.wait_for_url("**/capturebrief/")
                assert page.get_by_role("heading", name="Know what your bid decision rests on.").is_visible()
                page.goto(base + "/?utm_source=acceptance#start-audit")
                page.wait_for_url("**/recovery/?utm_source=acceptance#start-audit")
                assert page.locator("#auditForm").is_visible()
                contact = check_contact_composer(page, base)
                report["interactions"].append({"width": width, "menu_keyboard": True, "business_navigation": True,
                                               "legacy_freight_anchor": True, "contact_composer": contact})
                report["chat_clearance"].append(check_chat_clearance(page, base, args.out, width, height))
                context.close()
            # Reproduce the desktop geometry where the original launcher obscured submit.
            context = browser.new_context(viewport={"width": 1363, "height": 936}, reduced_motion="reduce")
            context.route("**/*", route)
            page = context.new_page()
            report["chat_clearance"].append(check_chat_clearance(page, base, args.out, 1363, 936))
            context.close()
            browser.close()
        assert not report["non_get_requests"]
        if axe_source:
            failures = report["accessibility"]["blocking_failures"]
            assert not failures, f"Serious/critical accessibility failures in {len(failures)} route/viewport checks; see {args.out / 'report.json'}"
            report["accessibility"]["status"] = "passed"
        report["passed"] = True
    finally:
        server.shutdown()
        (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"RETALLY Group: {len(report['pages'])} responsive page checks, keyboard menus, business navigation, "
          f"email-draft controls, legacy freight anchors and {len(report['chat_clearance'])} chat-clearance checks passed; "
          f"no POSTs sent. Accessibility: {report['accessibility']['status']}.")


if __name__ == "__main__":
    main()
