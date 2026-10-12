#!/usr/bin/env python3
"""Read-only screenshot and layout regression evidence for RETALLY's public site.

Run against an independently built local public-only bundle. No inquiries are sent.
"""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

VIEWPORTS = ((1440, 900), (1024, 768), (390, 844), (375, 812), (320, 700))
PAGES = (
    ("home", "index.html"),
    ("pricing", "freight-audit-pricing.html"),
    ("sample-scenario", "freight-audit-example.html"),
    ("sample-report", "recovery-status-example.html"),
    ("about", "about.html"),
    ("trust", "trust.html"),
    ("privacy", "privacy.html"),
)
IMG_ISSUES = """() => [...document.images].filter(im => !im.complete || im.naturalWidth===0)
     .map(im => ({src:im.getAttribute('src'),alt:im.alt}))"""
MEASURE = """() => {
 const body=document.body, doc=document.documentElement;
 const extents=[...document.querySelectorAll('body *')]
   .filter(e=>{const r=e.getBoundingClientRect();return r.width && (r.right>innerWidth+1 || r.left<-1)})
   .slice(0,8).map(e=>({tag:e.tagName,className:String(e.className).slice(0,100),
         right:Math.round(e.getBoundingClientRect().right),
         left:Math.round(e.getBoundingClientRect().left)}));
 const date=document.querySelector('.report-population span:last-child');
 const footerBrand=document.querySelector('.home-simple .simple-footer > div:first-child > a.brand');
 const footerEmail=document.querySelector('.home-simple .simple-footer > div:first-child > a[data-contact-link]');
 let footerContact=null;
 if(footerBrand&&footerEmail){
   const b=footerBrand.getBoundingClientRect(),e=footerEmail.getBoundingClientRect();
   footerContact={
     gapPx:Math.round((e.top-b.bottom)*10)/10,
     touchHeightPx:Math.round(e.height*10)/10,
     withinViewport:e.left>=-1&&e.right<=innerWidth+1,
     nonOverlapping:e.top>=b.bottom+12,
     emailReadable:getComputedStyle(footerEmail).visibility==='visible'
   };
 }
 const buttonSurfaces=[...document.querySelectorAll('.button,.text-button,.menu-toggle,.retally-social__button,.retally-chat-launcher')]
   .filter(el=>{const st=getComputedStyle(el),r=el.getBoundingClientRect();
     return st.display!=='none'&&st.visibility!=='hidden'&&r.width>0&&r.height>0
       && !el.disabled && el.getAttribute('aria-disabled')!=='true';})
   .map(el=>{const st=getComputedStyle(el),r=el.getBoundingClientRect();
     return {tag:el.tagName,selector:String(el.className).slice(0,90),
       width:Math.round(r.width),height:Math.round(r.height),
       onScreen:r.left>=-1&&r.right<=innerWidth+1,
       hasDepth:st.boxShadow!=='none',hasFocusLabel:!!(el.textContent.trim()||el.getAttribute('aria-label'))};});
 return {innerWidth,documentWidth:doc.scrollWidth,bodyWidth:body.scrollWidth,
   overflow:Math.max(doc.scrollWidth,body.scrollWidth)-innerWidth,offenders:extents,
   buttonSurfaces,
   dateWidth:date?Math.round(date.getBoundingClientRect().width):null,
   dateUnbroken:date?getComputedStyle(date).whiteSpace==='nowrap':null,
   title:document.title,footerContact,
   requiredLabels:[...document.querySelectorAll('input[required],select[required]')]
     .filter(e=>!e.labels?.length && !e.getAttribute('aria-label')).map(e=>e.name||e.id)
  };
}"""



def verify_email_handoff(browser, base: str) -> list[dict]:
    """Exercise the actual mailto fallback without sending mail or a server POST.

    Synthetic values are confined to the isolated browser; the QA receipt saves
    only boolean assertions, not test addresses, references or request bodies.
    """
    from urllib.parse import parse_qs, urlparse

    campaign = ("utm_source=facebook&utm_medium=organic_social&"
                "utm_campaign=retally_oct2026_launch&"
                "utm_content=oct14_evidence")
    outcomes = []
    for width, height, via_guide in ((390, 844, True), (1440, 900, False)):
        context = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=1, is_mobile=width <= 390, has_touch=width <= 390,
            reduced_motion="reduce",
        )
        page = context.new_page()
        errors, api_posts = [], []
        page.on("pageerror", lambda err: errors.append(str(err)[:160]))
        page.on("request", lambda req: api_posts.append(True)
                if req.method == "POST" and "/api/inquiry" in req.url else None)
        state = {"viewport": f"{width}x{height}", "checks": {}, "errors": errors}
        outcomes.append(state)
        try:
            # The mobile journey starts at a tagged educational link; desktop
            # uses the tagged homepage. Both must preserve origin attribution.
            start = ("freight-audit-methodology.html" if via_guide else "index.html")
            page.goto(base + start + "?" + campaign,
                      wait_until="load", timeout=25000)
            if via_guide:
                page.locator('#next a[href*="start-audit"]').first.click()
                page.wait_for_url("**/*#start-audit", timeout=15000)
            check = state["checks"]
            check["utmRetained"] = all(
                page.url.find(piece) >= 0 for piece in
                ("utm_source=facebook", "utm_campaign=retally_oct2026_launch",
                 "utm_content=oct14_evidence")
            )
            check["startsInEmailMode"] = (
                "Open My Free Audit Request"
                in page.locator('#auditForm button[type="submit"]').inner_text()
            )

            # Capture *public event names only*; never persist visitor data.
            page.evaluate("""() => {
              window.__retallyQaEvents = [];
              window.addEventListener("freight:analytics", e => {
                if (["freight_audit_form_completed", "freight_audit_request_prepared"]
                      .includes(e.detail?.event)) window.__retallyQaEvents.push(e.detail.event);
              });
            }""")
            # Required fields must fail before any mailto draft is prepared.
            page.locator('#auditForm button[type="submit"]').click()
            check["emptyFormRejected"] = (
                bool(page.locator("#formError").inner_text().strip())
                and not page.locator("#auditReady").is_visible()
            )

            page.locator("#fullName").fill("Synthetic QA Person")
            page.locator("#workEmail").fill("qa-buyer@example.invalid")
            page.locator("#companyName").fill("SYNTHETIC QA ONLY")
            page.locator("#annualSpend").select_option(label="$250k–$1M")
            page.locator('input[name="modes"][value="LTL"]').check()

            # An intercepted clipboard is deterministic even in headless
            # Chromium. It neither sends mail nor grants OS clipboard access.
            page.evaluate("""() => {
              window.__retallyCopied = [];
              Object.defineProperty(navigator, "clipboard", {
                configurable: true,
                value: {writeText: async value => {
                  window.__retallyCopied.push(String(value));
                }}
              });
            }""")
            page.locator('#auditForm button[type="submit"]').click()
            page.locator("#auditReady").wait_for(state="visible", timeout=15000)

            recipient = page.locator(
                'meta[name="freight-contact-email"]').get_attribute("content")
            href = page.locator("#sendAuditRequest").get_attribute("href") or ""
            parsed = urlparse(href)
            parameters = parse_qs(parsed.query)
            body = parameters.get("body", [""])[0]
            ready_text = page.locator("#auditReady").inner_text()
            check["preparedStateVisible"] = (
                page.locator("#auditReady").is_visible()
                and not page.locator("#auditForm").is_visible()
            )
            # .inner_text() reflects CSS text-transform:uppercase on
            # .eyebrow; check the actual status-label source text instead.
            check["explicitlyNotReceived"] = (
                page.locator("#auditReady .eyebrow").text_content().strip()
                    == "Email prepared — not sent"
                and "Your request has not been sent yet." in
                    page.locator("#auditReady .audit-manual-fallback").text_content()
                and page.locator("#auditReady h3").inner_text().strip()
                    == "Review it, then press Send."
                and "RETALLY has received your request" not in ready_text
            )
            check["mailtoAddressCorrect"] = (
                bool(recipient) and parsed.scheme == "mailto"
                and parsed.path == recipient
                and page.locator("#auditRecipient").inner_text() == recipient
                and page.locator("#auditRecipient").is_visible()
            )
            check["mailtoIncludesSyntheticDetails"] = (
                "Synthetic QA Person" in body
                and "qa-buyer@example.invalid" in body
                and "SYNTHETIC QA ONLY" in body
                and "Free Recovery Audit Request" in parameters.get("subject", [""])[0]
            )
            check["mailtoIncludesCampaign"] = (
                "Acquisition source:" in body
                and "utm_source=facebook" in body
                and "utm_campaign=retally_oct2026_launch" in body
                and "utm_content=oct14_evidence" in body
            )
            page.locator("#copyAuditEmail").click()
            page.locator("#copyAuditSummary").click()
            copied = page.evaluate("window.__retallyCopied")
            check["copyRecipientWorks"] = (
                len(copied) == 2 and copied[0] == recipient
            )
            check["copySummaryWorks"] = (
                len(copied) == 2 and copied[1] == body
            )
            # A prepared email is an *attempt*, never a recorded customer lead.
            check["preparedDraftHasNoFalseConversion"] = page.evaluate("""() =>
              window.__retallyQaEvents.filter(n =>
                n === "freight_audit_form_completed").length === 0 &&
              window.__retallyQaEvents.filter(n =>
                n === "freight_audit_request_prepared").length === 1
            """)
            page.locator("#editAuditRequest").click()
            check["editRestoresPopulatedForm"] = (
                page.locator("#auditForm").is_visible()
                and not page.locator("#auditReady").is_visible()
                and page.locator("#companyName").input_value() == "SYNTHETIC QA ONLY"
                and page.locator("#sendAuditRequest").get_attribute("aria-disabled") == "true"
            )
            page.locator("#companyName").fill("SYNTHETIC QA REVISED")
            page.locator('#auditForm button[type="submit"]').click()
            page.locator("#auditReady").wait_for(state="visible", timeout=15000)
            amended = page.locator("#sendAuditRequest").get_attribute("href") or ""
            amended_params = parse_qs(urlparse(amended).query)
            amended_body = amended_params.get("body", [""])[0]
            check["editedDraftReplacesStaleDetails"] = (
                amended != href and "SYNTHETIC QA REVISED" in amended_body
                and "Company: SYNTHETIC QA ONLY" not in amended_body
                and "SYNTHETIC QA REVISED" in amended_params.get("subject", [""])[0]
            )
            check["editAndReprepareNeverSignalReceivedLead"] = page.evaluate("""() =>
              window.__retallyQaEvents.filter(n =>
                n === "freight_audit_form_completed").length === 0 &&
              window.__retallyQaEvents.filter(n =>
                n === "freight_audit_request_prepared").length === 2
            """)
            check["noOnlineInquiryPost"] = not api_posts
            check["noBrowserErrors"] = not errors
        except Exception as exc:
            # Persist only a bounded diagnostic in visual QA artifacts.
            state["errors"].append(type(exc).__name__ + ": " + str(exc)[:200])
        finally:
            context.close()
    return outcomes


def measure(bundle: Path, output: Path) -> dict:
    bundle = bundle.resolve()
    output.mkdir(parents=True, exist_ok=True)
    handler = partial(SimpleHTTPRequestHandler, directory=str(bundle))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}/"
    results = []
    handoff_checks = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            for width, height in VIEWPORTS:
                context = browser.new_context(viewport={"width": width, "height": height},
                    device_scale_factor=1, is_mobile=width<=390, has_touch=width<=390,
                    reduced_motion="reduce")
                for slug, path in PAGES:
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    response = page.goto(base + path, wait_until="load", timeout=25000)
                    page.evaluate("document.fonts.ready")
                    page.wait_for_timeout(75)
                    info = page.evaluate(MEASURE)
                    images = page.evaluate(IMG_ISSUES)
                    shot = output / f"{slug}-{width}x{height}.jpg"
                    page.screenshot(path=str(shot), type="jpeg", quality=72,
                        full_page=True, animations="disabled")
                    info.update(page=slug,viewport=f"{width}x{height}",
                        httpStatus=response.status if response else None,
                        missingImages=images,jsErrors=errors,screenshot=shot.name)
                    if slug=="home" and width<=390:
                        toggle = page.locator("#menuToggle")
                        if toggle.count():
                            toggle.click()
                            info["menuExpanded"]=toggle.get_attribute("aria-expanded")
                            info["menuVisible"]=page.locator("#mainNav").is_visible()
                            page.screenshot(path=str(output / f"home-menu-{width}x{height}.jpg"),
                                type="jpeg", quality=72, full_page=False)
                    results.append(info)
                    page.close()
                context.close()
            # Assert the real public site's click-to-open lifecycle with an
            # isolated fake widget. Never send a message to an actual chatbot.
            launcher_checks = []
            chat_context = browser.new_context(viewport={"width":390,"height":844},
                is_mobile=True,has_touch=True,reduced_motion="reduce")
            chat_context.route("**/*bubblav.com/**", lambda route: route.abort())
            chat_page = chat_context.new_page()
            chat_page.goto(base + "index.html",wait_until="load",timeout=25000)
            chat_btn = chat_page.locator("#retallyChatLauncher")
            if chat_btn.count():
                chat_page.evaluate("""() => {
                    const frame = document.createElement('iframe');
                    frame.id = 'bv-chat-frame';
                    document.body.appendChild(frame);
                    window.__retallyMockOpen = false;
                    window.BubblaV = {
                        open: () => { window.__retallyMockOpen = true; },
                        isOpen: () => window.__retallyMockOpen
                    };
                }""")
                chat_btn.click()
                chat_page.wait_for_timeout(650)
                opened = chat_page.evaluate("""() => ({
                    invoked: window.__retallyMockOpen === true,
                    classPresent: document.body.classList.contains('retally-chat-open'),
                    nativeVisible: getComputedStyle(document.getElementById('bv-chat-frame')).visibility === 'visible'
                })""")
                chat_page.evaluate("window.__retallyMockOpen = false")
                chat_page.wait_for_timeout(650)
                closed = chat_page.evaluate("""() => ({
                    buttonVisible: !document.getElementById('retallyChatLauncher').hidden,
                    nativeHidden: getComputedStyle(document.getElementById('bv-chat-frame')).visibility === 'hidden',
                    classRemoved: !document.body.classList.contains('retally-chat-open')
                })""")
                chat_page.evaluate("window.BubblaV = null")
                chat_btn.click()
                fallback = chat_page.evaluate("""() => ({
                    nativeRestored: document.body.classList.contains('retally-chat-fallback')
                        && getComputedStyle(document.getElementById('bv-chat-frame')).visibility === 'visible',
                    customHidden: document.getElementById('retallyChatLauncher').hidden
                })""")
                launcher_checks = [{"open":opened,"closed":closed,"fallback":fallback}]
            chat_context.close()
            handoff_checks = verify_email_handoff(browser, base)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    if launcher_checks:
        verified = launcher_checks[0]
        if not all(verified["open"].values()) or not all(verified["closed"].values()) or not all(verified["fallback"].values()):
            results.append({"page":"chat-launcher","viewport":"390x844","overflow":0,
                "missingImages":[],"jsErrors":["Launcher open/close/fallback contract failed"],
                "requiredLabels":[],"httpStatus":200,"screenshot":"n/a"})
    # Every visible first-party CTA must retain 44px tap height, non-clipped
    # geometry, a readable label and a dimensional rendered surface.
    for record in results:
        for button in record.get("buttonSurfaces", []):
            if button["height"] < 44 or not button["onScreen"] or not button["hasDepth"] or not button["hasFocusLabel"]:
                record["jsErrors"].append(
                    "3D button acceptance failure: " + button["selector"]
                )
                break
    # The footer has its own acceptance gate because contact links can collide
    # without causing overflow or a JavaScript error.
    for record in results:
        if record["page"] == "home":
            footer = record.get("footerContact")
            if not footer or footer["gapPx"] < 12 or footer["touchHeightPx"] < 44 \
                    or not footer["nonOverlapping"] or not footer["withinViewport"] \
                    or not footer["emailReadable"]:
                record["jsErrors"].append("Footer logo/contact spacing or touch-target failure")
    summary = {"screenshots":len(results),
      "screens":[r["screenshot"] for r in results],
      "issues":[r for r in results if r["overflow"]>1 or r["missingImages"]
                or r["jsErrors"] or r["requiredLabels"] or r["httpStatus"]!=200
                or ("menuExpanded" in r and
                    (r["menuExpanded"]!="true" or not r["menuVisible"]))],
      "results":results,"chatLauncher":launcher_checks}
    summary["emailFallback"] = handoff_checks
    for item in handoff_checks:
        broken = [name for name, passed in item["checks"].items() if not passed]
        if item["errors"] or broken:
            summary["issues"].append({
                "page": "email-fallback", "viewport": item["viewport"],
                "overflow": 0, "missingImages": [], "requiredLabels": [],
                "jsErrors": item["errors"] + ["Failed: " + ", ".join(broken)],
                "httpStatus": 200, "screenshot": "n/a",
            })
    if len(handoff_checks) != 2:
        summary["issues"].append({
            "page": "email-fallback", "viewport": "missing",
            "overflow": 0, "missingImages": [], "requiredLabels": [],
            "jsErrors": ["Expected both mobile and desktop journey checks"],
            "httpStatus": 200, "screenshot": "n/a",
        })
    (output / "manifest.json").write_text(json.dumps(summary,indent=2)+"\n")
    return summary


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--site",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--fail-on-issues",action="store_true")
    args=parser.parse_args()
    result=measure(args.site,args.out)
    print(json.dumps({"screenshots":result["screenshots"],
      "issuesCount":len(result["issues"]),
      "issues":[{"page":r["page"],"viewport":r["viewport"],
                 "overflow":r["overflow"],"missingImages":r["missingImages"],
                 "jsErrors":r["jsErrors"],"requiredLabels":r["requiredLabels"],
                 "menuExpanded":r.get("menuExpanded"),"footerContact":r.get("footerContact")} for r in result["issues"]]
    },indent=2))
    return int(args.fail_on_issues and bool(result["issues"]))


if __name__=="__main__":
    raise SystemExit(main())
