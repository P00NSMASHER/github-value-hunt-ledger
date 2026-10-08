#!/usr/bin/env python3
"""Read-only, production-representative hosted acceptance for RETALLY.

This test runs solely against a *.retally-web.pages.dev preview and cannot send
a real inquiry. It checks visible behavior and captures evidence at five widths.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

SIZES = [(1440, 900), (1024, 768), (390, 844), (375, 812), (320, 700)]
PAGES = ["", "freight-audit-pricing", "freight-audit-example",
         "recovery-status-example", "about", "trust", "privacy"]
CHECK_DOM = """() => ({
  overflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - innerWidth,
  images: [...document.images].filter(x => !x.complete || !x.naturalWidth).map(x => x.src),
  unlabeled: [...document.querySelectorAll('input[required],select[required]')]
    .filter(x => !x.labels?.length && !x.getAttribute('aria-label')).map(x => x.name),
  h1count: document.querySelectorAll('h1').length,
  font: getComputedStyle(document.body).fontFamily,
  date: (()=>{const e=document.querySelector('.report-population span:last-child');if(!e)return null;
    const r=e.getBoundingClientRect();return {text:e.textContent, nowrap:getComputedStyle(e).whiteSpace,
    left:r.left,right:r.right,width:r.width};})()
})"""


def run(base: str, output: Path, axe_path: Path | None) -> dict:
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".retally-web.pages.dev"):
        raise ValueError("Tests must use a Cloudflare Pages preview, never live production")
    base = base.rstrip("/") + "/"
    output.mkdir(parents=True, exist_ok=True)
    records, defects, axe_violations = [], [], []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for width, height in SIZES:
            context = browser.new_context(viewport={"width": width, "height": height},
                is_mobile=width <= 390, has_touch=width <= 390,
                reduced_motion="reduce")
            for slug in PAGES:
                page = context.new_page()
                js_errors = []
                page.on("pageerror", lambda err: js_errors.append(str(err)))
                name = slug or "homepage"
                response = page.goto(base + slug, wait_until="load", timeout=35000)
                page.evaluate("document.fonts.ready")
                data = page.evaluate(CHECK_DOM)
                status = response.status if response else None
                item = {"page": name, "width": width, "height": height,
                    "status": status, "url": page.url, **data, "errors": js_errors}
                if slug == "":
                    item["cta"] = page.get_by_role("link", name="Start Free Recovery Audit").first.get_attribute("href")
                    if width <= 390:
                        toggle = page.locator("#menuToggle")
                        toggle.click()
                        item["menu"] = {"expanded":toggle.get_attribute("aria-expanded"),
                            "visible":page.locator("#mainNav").is_visible()}
                page.screenshot(path=str(output / f"{name}-{width}.jpg"),
                    type="jpeg", quality=65, full_page=True, animations="disabled")
                records.append(item)
                if status != 200 or data["overflow"] > 1 or data["images"] or data["unlabeled"] or js_errors or data["h1count"] != 1:
                    defects.append({"page": name, "width":width,"failure":"document","data":item})
                if "Hanken" not in data["font"]:
                    defects.append({"page":name,"width":width,"failure":"brand_font", "font":data["font"]})
                if slug == "recovery-status-example":
                    date = data["date"]
                    if not date or not date["nowrap"] == "nowrap" or date["right"] > width + 1 or date["left"] < -1:
                        defects.append({"page":name,"width":width,"failure":"report_date","date":date})
                    if "$13,450.00" not in page.locator("body").inner_text():
                        defects.append({"page":name,"width":width,"failure":"sample_amount"})
                if slug == "" and width <= 390 and (
                    item.get("menu",{}).get("expanded") != "true" or not item.get("menu",{}).get("visible")):
                    defects.append({"page":name,"width":width,"failure":"mobile_menu"})
                if axe_path and axe_path.exists() and width in (1440, 390) and slug in ("","trust","recovery-status-example"):
                    page.add_script_tag(content=axe_path.read_text())
                    violations = page.evaluate("""async () => {
                      const r=await axe.run(document,{runOnly:{type:'tag',
                        values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}});
                      return r.violations.map(v=>({id:v.id,impact:v.impact,
                        description:v.description,nodes:v.nodes.length,
                        sample:v.nodes.slice(0,3).map(n=>n.target)}));}""")
                    if violations:
                        axe_violations.append({"page":name,"width":width,"violations":violations})
                    if any(v["impact"] in ("critical","serious") for v in violations):
                        defects.append({"page":name,"width":width,"failure":"axe_serious_critical","violations":violations})
                page.close()
            context.close()

        # On the preview hostname the form ONLY prepares a mailto draft,
        # it cannot connect to the live intake API; do not submit real data.
        context = browser.new_context(viewport={"width": 390,"height":844},is_mobile=True,has_touch=True)
        page=context.new_page()
        page.goto(base,wait_until="load",timeout=35000)
        page.locator("#auditForm button[type=submit]").click()
        invalid_feedback=page.locator("#formError").inner_text()
        if not invalid_feedback.strip():
            defects.append({"page":"form","failure":"empty_form_was_accepted"})
        page.locator("#fullName").fill("RETALLY Preview QA")
        page.locator("#workEmail").fill("retally-qa@example.invalid")
        page.locator("#companyName").fill("PREVIEW TEST - DO NOT CONTACT")
        page.locator("#annualSpend").select_option(label="$250k–$1M")
        page.locator('input[name="modes"][value="LTL"]').check()
        page.locator("#auditForm button[type=submit]").click()
        page.wait_for_timeout(300)
        ready_visible=page.locator("#auditReady").is_visible()
        href=page.locator("#sendAuditRequest").get_attribute("href")
        form_qa={"invalidFeedback":invalid_feedback[:500],"readyVisible":ready_visible,
            "preparedEmail":bool(href and href.startswith("mailto:")),
            "testDataPresent":bool(href and "example.invalid" in href)}
        if not ready_visible or not form_qa["preparedEmail"] or not form_qa["testDataPresent"]:
            defects.append({"page":"form","failure":"email_draft_path","result":form_qa})
        page.screenshot(path=str(output/"form-prepared-390.jpg"),full_page=False,type="jpeg",quality=70)
        context.close()
        browser.close()
    report={"base":base,"totalScreens":len(records)+1,"pages":len(PAGES),
            "viewports":SIZES,"defects":defects,"axeViolations":axe_violations,
            "form":form_qa,"results":records}
    (output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--base-url",required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--axe-js",type=Path)
    args=ap.parse_args()
    result=run(args.base_url,args.out,args.axe_js)
    print(json.dumps({"screens":result["totalScreens"],"defects":result["defects"],
        "axe":result["axeViolations"],"form":result["form"]},indent=2))
    raise SystemExit(1 if result["defects"] else 0)
