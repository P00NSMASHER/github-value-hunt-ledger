"""Isolated acceptance for freight and independently built company sites; no live traffic."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit, urlunsplit

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
from freight.site.group.build import LEGACY_ROUTES


VIEWPORTS = ((1440, 900), (768, 1024), (390, 844), (375, 812), (320, 700))
PUBLIC_URLS = {
    "freight": "https://www.retallyrecovery.com/",
    "group": "https://group.retallyrecovery.com/",
    "recoveryworks": "https://recoveryworks.retallyrecovery.com/",
    "permitplate": "https://permitplate.retallyrecovery.com/",
    "capturebrief": "https://capturebrief.retallyrecovery.com/",
}
COMPANY_CARDS = {
    "RETALLY Freight Recovery": PUBLIC_URLS["freight"],
    "RETALLY RecoveryWorks": PUBLIC_URLS["recoveryworks"],
    "PermitPlate": PUBLIC_URLS["permitplate"],
    "CaptureBrief": PUBLIC_URLS["capturebrief"],
}
HEADINGS = {
    "group": "Focused businesses. Clear purpose.",
    "recoveryworks": "Find the gap. Keep the proof.",
}
NAVIGATION = {
    "group": ("/#businesses", "/#about", "/#contact"),
    "recoveryworks": ("/#services", "/#process", "/#example", "/engagement/", "/#contact"),
}
GROUP_INQUIRY_URL = PUBLIC_URLS["freight"] + "api/group-inquiry"


def install_group_security_fixture(context, base):
    """Show a compact widget without loading or solving a real challenge."""
    context.add_init_script("""(() => {
      if (location.origin !== """ + json.dumps(base) + """) return;
      const state = window.__retallyGroupQA = {widgets: []};
      window.turnstile = {
        render(selector, options) {
          const holder = document.querySelector(selector);
          const fixture = document.createElement('div');
          fixture.dataset.qaTurnstile = 'compact';
          fixture.setAttribute('role', 'img');
          fixture.setAttribute('aria-label', 'Isolated security verification fixture');
          fixture.style.cssText = 'width:150px;height:140px;background:#fff;color:#111;border:1px solid #888;display:grid;place-items:center;text-align:center;font:14px sans-serif';
          fixture.textContent = 'Security verification fixture';
          holder.appendChild(fixture);
          state.widgets.push({selector, action: options.action, size: options.size});
          state.verify = () => options.callback('isolated-qa-token-never-sent');
          state.expire = () => options['expired-callback']();
          return 0;
        },
        reset() { state.expire(); }
      };
    })();""")


def check_group_widget(page, width):
    page.wait_for_function("window.__retallyGroupQA?.widgets.length === 1")
    assert page.evaluate("window.__retallyGroupQA.widgets") == [
        {"selector": "#enquiry-turnstile", "action": "retally_group", "size": "compact"}]
    holder = page.locator("#enquiry-turnstile")
    assert holder.get_attribute("role") == "group"
    assert holder.get_attribute("aria-label") == "Security verification"
    geometry = holder.evaluate("""element => {
      const holder = element.getBoundingClientRect();
      const widget = element.querySelector('[data-qa-turnstile]').getBoundingClientRect();
      return {holderLeft: holder.left, holderRight: holder.right, widgetLeft: widget.left,
              widgetRight: widget.right, widgetWidth: widget.width,
              overflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - innerWidth};
    }""")
    assert geometry["widgetWidth"] == 150 and geometry["overflow"] <= 1, geometry
    assert geometry["widgetLeft"] >= geometry["holderLeft"] - 1, geometry
    assert geometry["widgetRight"] <= geometry["holderRight"] + 1, geometry
    return {"width": width, "compact_widget": True, "geometry": geometry, "provider_loaded": False}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def check_company_canvas(page, company, slug, output, width):
    """Check each company's own canvas and intentionally static navigation."""
    if company == "group":
        expected = {"body": "rgb(245, 242, 233)", ".site-header": "rgb(6, 44, 37)",
                    ".site-footer": "rgb(6, 44, 37)"}
        if not slug:
            expected.update({"#businesses": "rgb(245, 242, 233)",
                             "#about": "rgb(7, 62, 50)", "#contact": "rgb(245, 242, 233)"})
    else:
        expected = {"body": "rgb(244, 241, 235)", ".site-header": "rgb(18, 26, 53)",
                    ".site-footer": "rgb(12, 18, 41)"}
        if not slug:
            expected.update({"#services": "rgb(244, 241, 235)",
                             "#process": "rgb(33, 43, 76)", "#contact": "rgb(18, 26, 53)"})
    surfaces = page.evaluate("""selectors => {
      const background = element => {
        while (element) {
          const color = getComputedStyle(element).backgroundColor;
          if (color !== 'rgba(0, 0, 0, 0)' && color !== 'transparent') return color;
          element = element.parentElement;
        }
        return 'transparent';
      };
      return selectors.map(selector => {
        const element = document.querySelector(selector);
        return {selector, present: !!element, background: element ? background(element) : null};
      });
    }""", list(expected))
    assert all(item["present"] and item["background"] == expected[item["selector"]]
               for item in surfaces), {"site": company, "route": slug, "width": width, "surfaces": surfaces}
    header = page.locator(".site-header")
    state = """element => {
      const rect = element.getBoundingClientRect(), style = getComputedStyle(element);
      return {top: rect.top, background: style.backgroundColor, color: style.color,
              position: style.position, scrollY: window.scrollY};
    }"""
    before = header.evaluate(state)
    page.locator(".site-footer" if slug else "#businesses" if company == "group" else "#services").scroll_into_view_if_needed()
    after = header.evaluate(state)
    assert before["background"] == after["background"] == expected[".site-header"], (before, after)
    assert before["color"] == after["color"] and before["color"] != before["background"], (before, after)
    assert before["position"] == after["position"] == "static", (before, after)
    assert abs(before["top"]) <= 1 and after["top"] < 0 and after["scrollY"] > 0, (before, after)
    if not slug:
        page.screenshot(path=str(output / f"{company}-{width}-beyond-hero.png"), full_page=False)
    page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
    return {"site": company, "route": slug or "home", "width": width, "surfaces": surfaces,
            "header_before": before, "header_after": after}


def check_heading_breakpoints(page, bases, output):
    """Retain the 501–800px wrapping guard on both independent company heroes."""
    results = []
    for company, expected in HEADINGS.items():
        for width in (500, 501, 768, 800, 801):
            page.set_viewport_size({"width": width, "height": 1024})
            page.goto(bases[company] + "/", wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            heading = page.locator(".hero h1")
            assert heading.is_visible()
            text = " ".join(heading.inner_text().split())
            assert text == expected, {"site": company, "width": width, "visible_heading": text}
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            if width in (501, 800):
                page.screenshot(path=str(output / f"{company}-heading-{width}.png"), full_page=False)
            results.append({"site": company, "width": width, "visible_heading": text, "passed": True})
    return results


def check_card_heading_contrast(page, company):
    """Axe may leave gradient backgrounds untested; check each actual stop."""
    selector, panel, expected = (
        (".company-card h3", ".company-card", 4) if company == "group" else
        (".service-cards article h3, .pilot-card h2", ".service-cards article, .pilot-card", 3))
    results = page.evaluate(r"""({selector, panel}) => {
      const channels = value => value.match(/[\d.]+/g).slice(0, 3).map(Number);
      const luminance = rgb => rgb.map(v => v / 255)
        .map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4)
        .reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
      return [...document.querySelectorAll(selector)].map(heading => {
        const style = getComputedStyle(heading.closest(panel));
        const colors = style.backgroundImage.match(/rgba?\([^)]+\)/g) || [style.backgroundColor];
        const foreground = luminance(channels(getComputedStyle(heading).color));
        const contrast = Math.min(...colors.map(color => {
          const background = luminance(channels(color));
          return (Math.max(foreground, background) + .05) / (Math.min(foreground, background) + .05);
        }));
        return {text: heading.innerText, contrast};
      });
    }""", {"selector": selector, "panel": panel})
    assert len(results) == expected and all(item["contrast"] >= 4.5 for item in results), results
    return results


def load_page_images(page):
    """Exercise native lazy loading before judging images or taking screenshots."""
    page.evaluate("""async () => {
      await document.fonts.ready;
      const nextPaint = () => new Promise(resolve =>
        requestAnimationFrame(() => requestAnimationFrame(resolve)));
      for (const image of document.querySelectorAll('img[loading="lazy"]')) {
        image.scrollIntoView({block: 'center', behavior: 'instant'});
        await nextPaint();
        // A completed network response can still be undecoded when a full-page
        // capture moves the image off screen. Paint it while it is in view.
        try { await image.decode(); } catch (_) { /* recorded below */ }
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


def check_keyboard_target(link):
    assert link.is_visible()
    link.focus()
    assert link.evaluate("element => element === document.activeElement")
    assert link.evaluate("element => element.getBoundingClientRect().height >= 44"), link.inner_text()


def check_company_cards(page, bases):
    """Assert all four real destinations; exercise locally available successors."""
    page.goto(bases["group"] + "/", wait_until="networkidle")
    cards = page.locator(".company-card")
    assert cards.count() == len(COMPANY_CARDS) == 4
    found = {}
    for card in cards.all():
        title = " ".join(card.locator("h3").inner_text().split())
        link = card.locator(".card-end a")
        assert link.count() == 1
        check_keyboard_target(link)
        found[title] = link.get_attribute("href")
    assert found == COMPANY_CARDS, found
    for company, title in (("freight", "RETALLY Freight Recovery"),
                           ("recoveryworks", "RETALLY RecoveryWorks")):
        page.goto(bases["group"] + "/", wait_until="networkidle")
        link = page.locator(".company-card").filter(has=page.get_by_role("heading", name=title, exact=True)).locator(".card-end a")
        check_keyboard_target(link)
        page.keyboard.press("Enter")
        page.wait_for_url(bases[company] + "/")
        if company == "freight":
            assert page.locator("#auditForm").count() == 1
        else:
            assert " ".join(page.locator(".hero h1").inner_text().split()) == HEADINGS[company]
    # PermitPlate/CaptureBrief are independently tested in their own repositories.
    # Their real hrefs and keyboard focus are checked above; no live request is sent.
    return {"destinations": found, "local_keyboard_navigation": ["freight", "recoveryworks"],
            "permitplate_capturebrief": "destination and keyboard focus checked; no live navigation"}


def check_company_navigation(page, base, company):
    for href in NAVIGATION[company]:
        page.goto(base + "/", wait_until="networkidle")
        nav = page.get_by_role("navigation", name="Primary navigation", exact=True)
        assert nav.locator("a").count() == len(NAVIGATION[company])
        link = nav.locator(f'a[href="{href}"]')
        assert link.count() == 1
        check_keyboard_target(link)
        page.keyboard.press("Enter")
        page.wait_for_url(base + href)
        target = urlsplit(href)
        if target.fragment:
            assert page.locator(f"#{target.fragment}").is_visible()
        else:
            assert page.locator("main#main h1").is_visible()
    return {"keyboard_destinations": list(NAVIGATION[company])}


def check_secure_group_contact(page, base, output, width, axe_source, report):
    page.goto(base + "/?business=CaptureBrief#contact", wait_until="networkidle")
    form = page.locator("#group-enquiry")
    assert form.is_visible()
    fields = {name: form.locator("#enquiry-" + name)
              for name in ("business", "name", "email", "company", "message", "consent")}
    for control in fields.values():
        assert control.evaluate("element => [...element.labels].some(label => label.textContent.trim())"), "Enquiry field needs a visible label"
    business, name, email, company, message, consent = (fields[key] for key in fields)
    assert business.locator("option").evaluate_all("elements => elements.map(element => element.value)") == [
        "general", "recovery", "recoveryworks", "permitplate", "capturebrief"]
    assert business.input_value() == "capturebrief"
    assert message.get_attribute("maxlength") == "800"
    assert email.get_attribute("type") == "email"
    assert consent.get_attribute("required") is not None and not consent.is_checked()
    assert form.locator('input[type="file"]').count() == 0
    submit = form.locator("#send-enquiry")
    assert submit.get_attribute("type") == "submit" and submit.is_disabled()
    status = form.locator("#enquiry-status")
    assert status.get_attribute("role") == "status" and status.get_attribute("aria-live") == "polite"
    report["group_widget"].append(check_group_widget(page, width))

    sample = "QA preview only. Please do not send this draft."
    name.fill("Example Person")
    email.fill("person@example.test")
    company.fill("Acceptance fixture")
    message.fill(sample)
    draft = form.locator("#enquiry-draft")
    check_keyboard_target(draft)
    for value, label in (("capturebrief", "CaptureBrief"), ("permitplate", "PermitPlate")):
        business.select_option(value=value)
        url = urlsplit(draft.get_attribute("href"))
        parts = parse_qs(url.query)
        assert url.scheme == "mailto" and url.path == "jay@retallyrecovery.com"
        assert label in parts.get("subject", [""])[0]
        assert all(detail in parts.get("body", [""])[0]
                   for detail in (sample, "Example Person", "person@example.test", "Acceptance fixture"))
    consent.check()
    assert form.evaluate("element => element.checkValidity()")
    assert submit.is_disabled()  # Consent alone cannot bypass security verification.
    page.evaluate("window.__retallyGroupQA.verify()")
    assert submit.is_enabled()
    assert "Nothing has been sent yet" in status.inner_text()
    record_accessibility(page, axe_source, report, "group", "home#contact-ready", width)
    submit.scroll_into_view_if_needed()
    page.screenshot(path=str(output / f"group-contact-ready-{width}.png"), full_page=False)
    page.evaluate("window.__retallyGroupQA.expire()")
    assert submit.is_disabled() and "expired" in status.inner_text()

    # The route fixture changes only this isolated GET response. No request
    # reaches the API, and the real client must expose its honest fallback.
    page.goto(base + "/?qa_intake=offline#contact", wait_until="networkidle")
    assert page.locator("#group-enquiry").is_visible()
    assert page.locator("#send-enquiry").is_disabled()
    offline = page.locator("#enquiry-status").inner_text()
    assert "unavailable" in offline and "not been sent" in offline
    assert page.evaluate("window.__retallyGroupQA.widgets.length") == 0
    draft = page.locator("#enquiry-draft")
    check_keyboard_target(draft)
    assert urlsplit(draft.get_attribute("href")).path == "jay@retallyrecovery.com"
    assert page.locator("#copy-enquiry").is_visible()
    page.locator("#contact").scroll_into_view_if_needed()
    page.screenshot(path=str(output / f"group-contact-offline-{width}.png"), full_page=False)
    return {"labelled_fields": True, "explicit_consent": True, "no_upload": True,
            "compact_widget": True, "verification_required": True, "expiry_disables_send": True,
            "email_draft_updates": True, "offline_intake_fallback": True,
            "submit_clicked": False, "mailto_navigation": False}


def check_company_contact(page, base, company):
    """RecoveryWorks retains its explicit email-only enquiry path."""
    assert company == "recoveryworks"
    page.goto(base + "/#contact", wait_until="networkidle")
    panel = page.locator(".contact-card")
    link = panel.locator("a.button")
    assert link.count() == 1
    check_keyboard_target(link)
    draft = urlsplit(link.get_attribute("href"))
    fields = parse_qs(draft.query)
    expected = "RETALLY RecoveryWorks"
    assert draft.scheme == "mailto" and draft.path == "jay@retallyrecovery.com"
    assert expected in fields.get("subject", [""])[0]
    assert "Opens your email app." in panel.inner_text()
    assert page.locator("form, input[type=file]").count() == 0
    # Inspect the deliberate email handoff without opening a draft or sending it.
    return {"recipient": draft.path, "subject": fields["subject"][0],
            "email_handoff_disclosed": True, "mailto_navigation": False}


def check_freight_navigation(page, base):
    page.goto(base + "/", wait_until="networkidle")
    assert page.locator("body.home-simple").count() == 1
    assert page.locator(".group-header, .group-home, .company-grid").count() == 0
    assert page.locator(f'.footer-bottom a[href="{PUBLIC_URLS["group"]}"]').count() == 1
    toggle = page.locator("#menuToggle")
    nav = page.locator("#mainNav")
    assert nav.locator("a").count() == 5
    if toggle.is_visible():
        toggle.focus()
        page.keyboard.press("Enter")
        assert toggle.get_attribute("aria-expanded") == "true"
        assert all(link.is_visible() for link in nav.locator("a").all())
        page.keyboard.press("Enter")
        assert toggle.get_attribute("aria-expanded") == "false"
        assert toggle.evaluate("element => element === document.activeElement")
    # The original root owns freight anchors. The /recovery/ HTML is also checked
    # as a static-preview fallback; HTTP 301 behavior is verified separately.
    for path in ("/", "/recovery/"):
        page.goto(base + path + "?utm_source=acceptance#start-audit", wait_until="networkidle")
        location = urlsplit(page.url)
        assert location.path == path and location.fragment == "start-audit"
        assert parse_qs(location.query) == {"utm_source": ["acceptance"]}
        assert page.locator("#auditForm").is_visible()
        assert page.locator('link[rel="canonical"]').get_attribute("href") == PUBLIC_URLS["freight"]
    return {"root_freight_home": True, "navigation_keyboard": True,
            "root_and_legacy_fallback_anchors": True, "production_redirect_tested": False}


def check_chat_clearance(page, base, output, width, height):
    page.goto(base + "/#start-audit", wait_until="networkidle")
    launcher = page.locator("#retallyChatLauncher")
    assert launcher.count() == 1
    submit = page.locator('#auditForm button[type="submit"]')
    submit.scroll_into_view_if_needed()
    assert submit.is_visible()
    assert submit.evaluate("element => {const r = element.getBoundingClientRect(); return r.top < innerHeight && r.bottom > 0;}")
    launcher.wait_for(state="hidden")
    page.screenshot(path=str(output / f"freight-intake-clear-{width}.png"), full_page=False)
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


def record_accessibility(page, axe_source, report, company, slug, width):
    if not axe_source:
        return
    result = {"site": company, "route": slug or "home", "width": width,
              **check_accessibility(page, axe_source)}
    report["accessibility"]["checks"].append(result)
    blocking = [item for item in result["violations"] if item["impact"] in ("serious", "critical")]
    if blocking:
        report["accessibility"]["blocking_failures"].append({
            "site": company, "route": slug or "home", "width": width, "violations": blocking})
        report["accessibility"]["status"] = "failed"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True, help="Restored freight Cloudflare bundle")
    parser.add_argument("--group-site", type=Path, required=True, help="Independent Group bundle")
    parser.add_argument("--recoveryworks-site", type=Path, required=True, help="Independent RecoveryWorks bundle")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--axe-js", type=Path, help="Local axe-core script; never fetched by the QA browser")
    args = parser.parse_args()
    roots = {"freight": args.site, "group": args.group_site, "recoveryworks": args.recoveryworks_site}
    if any(not (root / "index.html").is_file() for root in roots.values()):
        parser.error("Each --site argument must point to its own existing built site")
    if len({root.resolve() for root in roots.values()}) != 3:
        parser.error("Freight, Group and RecoveryWorks must be independently built directories")
    if args.axe_js and not args.axe_js.is_file():
        parser.error("--axe-js must point to an existing local axe-core script")
    axe_source = args.axe_js.read_text() if args.axe_js else None
    args.out.mkdir(parents=True, exist_ok=True)
    routes = {"freight": ("",) + LEGACY_ROUTES + ("recoveryos",),
              "group": ("", "privacy"), "recoveryworks": ("", "engagement", "privacy")}
    assert len(routes["freight"]) == 14, "Legacy route coverage changed; review the screenshot contract"
    servers, bases = [], {}
    report = {"pages": [], "interactions": [], "chat_clearance": [], "non_get_requests": [],
              "company_canvas": [], "heading_breakpoints": [], "card_heading_contrast": [],
              "group_widget": [], "group_config_mocks": [],
              "local_company_handoffs": [], "external_requests_blocked": 0, "passed": False,
              "accessibility": {"status": "pending" if axe_source else "skipped",
                                "reason": None if axe_source else "No local axe-core script supplied with --axe-js",
                                "checks": [], "blocking_failures": []}}
    try:
        for company, root in roots.items():
            server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(root.resolve())))
            servers.append(server)
            Thread(target=server.serve_forever, daemon=True).start()
            bases[company] = f"http://127.0.0.1:{server.server_port}"
        local_hosts = {urlsplit(base).netloc for base in bases.values()}
        public_to_local = {urlsplit(PUBLIC_URLS[company]).netloc: base for company, base in bases.items()}

        def route(request_route):
            request = request_route.request
            parsed = urlsplit(request.url)
            if request.method != "GET":
                report["non_get_requests"].append(request.method)
                request_route.abort()
            elif (request.url == GROUP_INQUIRY_URL and not request.is_navigation_request()
                  and urlsplit(request.frame.url).netloc == urlsplit(bases["group"]).netloc):
                online = parse_qs(urlsplit(request.frame.url).query).get("qa_intake") != ["offline"]
                report["group_config_mocks"].append({"online": online, "method": "GET"})
                request_route.fulfill(status=200, headers={
                    "Content-Type": "application/json", "Cache-Control": "no-store",
                    "Access-Control-Allow-Origin": bases["group"], "Vary": "Origin"},
                    body=json.dumps({"online": online, "siteKey": "isolated-public-fixture" if online else ""}))
            elif parsed.netloc in local_hosts:
                request_route.continue_()
            elif request.is_navigation_request() and parsed.netloc in public_to_local:
                # Keep production hrefs intact, but exercise their destination
                # using another independently built local server. No live traffic.
                local = public_to_local[parsed.netloc]
                destination = local + urlunsplit(("", "", parsed.path, parsed.query, parsed.fragment))
                report["local_company_handoffs"].append({"public": request.url, "local": destination})
                request_route.fulfill(status=302, headers={"Location": destination}, body="")
            else:
                report["external_requests_blocked"] += 1
                request_route.abort()

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            for width, height in VIEWPORTS:
                context = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce",
                                              is_mobile=width <= 390, has_touch=width <= 390,
                                              bypass_csp=bool(axe_source))
                context.route("**/*", route)
                install_group_security_fixture(context, bases["group"])
                page = context.new_page()
                for company, slugs in routes.items():
                    for slug in slugs:
                        response = page.goto(bases[company] + "/" + (slug + "/" if slug else ""), wait_until="networkidle")
                        load_page_images(page)
                        result = page.evaluate("""() => ({
                          overflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - innerWidth,
                          h1Count: document.querySelectorAll('h1').length,
                          brokenImages: [...document.images].filter(im => !im.complete || !im.naturalWidth).map(im => im.getAttribute('src')),
                          title: document.title,
                          mainPresent: !!document.querySelector('main#main')
                        })""")
                        result.update({"site": company, "route": slug or "home", "width": width, "status": response.status})
                        report["pages"].append(result)
                        assert result["status"] == 200 and result["overflow"] <= 1 and result["h1Count"] == 1 and result["mainPresent"] and not result["brokenImages"], result
                        record_accessibility(page, axe_source, report, company, slug, width)
                        # Keep evidence from every route, including accessibility
                        # failures, so one defect cannot hide the remaining pages.
                        name = f'{company}-{slug or "home"}-{width}'
                        page.screenshot(path=str(args.out / f"{name}.png"), full_page=True)
                        if not slug:
                            page.screenshot(path=str(args.out / f"{name}-viewport.png"), full_page=False)
                        if company != "freight":
                            report["company_canvas"].append(check_company_canvas(page, company, slug, args.out, width))
                            if not slug:
                                report["card_heading_contrast"].append({
                                    "site": company, "width": width, "headings": check_card_heading_contrast(page, company)})
                interaction = {"width": width, "company_cards": check_company_cards(page, bases),
                               "freight": check_freight_navigation(page, bases["freight"])}
                for company in HEADINGS:
                    interaction[company] = {
                        "navigation": check_company_navigation(page, bases[company], company),
                        "contact": (check_secure_group_contact(page, bases[company], args.out, width, axe_source, report)
                                    if company == "group" else check_company_contact(page, bases[company], company))}
                report["interactions"].append(interaction)
                report["chat_clearance"].append(check_chat_clearance(page, bases["freight"], args.out, width, height))
                context.close()
            # Preserve the extra geometry where the original launcher obscured submit.
            context = browser.new_context(viewport={"width": 1363, "height": 936}, reduced_motion="reduce",
                                          bypass_csp=bool(axe_source))
            context.route("**/*", route)
            install_group_security_fixture(context, bases["group"])
            page = context.new_page()
            report["chat_clearance"].append(check_chat_clearance(page, bases["freight"], args.out, 1363, 936))
            report["group_desktop_contact"] = check_secure_group_contact(
                page, bases["group"], args.out, 1363, axe_source, report)
            report["heading_breakpoints"] = check_heading_breakpoints(page, bases, args.out)
            context.close()
            browser.close()
        assert len(report["pages"]) == sum(map(len, routes.values())) * len(VIEWPORTS) == 95
        assert len(report["group_widget"]) == 6
        assert report["group_config_mocks"] and all(item["method"] == "GET" for item in report["group_config_mocks"])
        assert not report["non_get_requests"]
        if axe_source:
            failures = report["accessibility"]["blocking_failures"]
            assert not failures, f"Serious/critical accessibility failures in {len(failures)} route/viewport checks; see {args.out / 'report.json'}"
            report["accessibility"]["status"] = "passed"
        report["passed"] = True
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
        (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"RETALLY separate sites: {len(report['pages'])} responsive page checks, four direct company destinations, "
          f"keyboard navigation, secure Group controls, disclosed email handoffs, freight anchors and {len(report['chat_clearance'])} chat-clearance checks passed; "
          f"{len(report['company_canvas'])} company canvas/header checks and "
          f"{len(report['heading_breakpoints'])} heading-breakpoint checks passed; "
          f"{len(report['group_widget'])} compact security-widget checks passed; "
          f"no POSTs sent. Accessibility: {report['accessibility']['status']}.")


if __name__ == "__main__":
    main()

