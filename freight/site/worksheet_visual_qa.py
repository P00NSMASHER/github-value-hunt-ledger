#!/usr/bin/env python3
"""Read-only mobile and print visual QA for RETALLY's anonymous social worksheet.

Uses a temporary loopback static server and headless Chromium. No external
network, customer data, form submission, cookies or browser storage.
"""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

SIZES = ((320,700),(390,844),(768,1000),(1440,900))
PAGE = "freight-invoice-audit-checklist.html"
QUERY = "?utm_source=facebook&utm_medium=organic_social&utm_campaign=retally_social_worksheet_qa&utm_content=synthetic_test#worksheet"


def verify(bundle: Path, destination: Path) -> dict:
    destination.mkdir(parents=True,exist_ok=True)
    bundle=bundle.resolve()
    if not (bundle/PAGE).is_file() or not (bundle/"worksheet.js").is_file():
        raise ValueError("A built, public-only freight worksheet bundle is required")
    http=ThreadingHTTPServer(("127.0.0.1",0),
                             partial(SimpleHTTPRequestHandler,directory=str(bundle)))
    Thread(target=http.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{http.server_port}/"
    records=[]
    print_info={}
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
            try:
                for width,height in SIZES:
                    ctx=browser.new_context(viewport={"width":width,"height":height},
                        device_scale_factor=1,reduced_motion="reduce",
                        is_mobile=width<=390,has_touch=width<=390)
                    external=[]
                    posts=[]
                    errors=[]
                    def route_request(route):
                        if route.request.url.startswith(base):
                            if route.request.method != "GET":
                                posts.append(route.request.method)
                                return route.abort()
                            return route.continue_()
                        external.append(route.request.url.split("?")[0][:150])
                        return route.abort()
                    ctx.route("**/*",route_request)
                    page=ctx.new_page()
                    page.on("pageerror",lambda exc:errors.append(str(exc)[:140]))
                    response=page.goto(base+PAGE+QUERY,wait_until="load",timeout=30000)
                    page.wait_for_selector('#invoiceWorksheet[data-initialized="true"]',timeout=15000)
                    sample=page.locator("#ws-sample")
                    sample.click()
                    got=page.locator("#ws-unresolved").inner_text().strip()
                    billed=page.locator("#ws-billed").input_value()
                    policy=page.locator("#invoiceWorksheet").get_attribute("data-data-policy")
                    page.screenshot(path=str(destination/f"worksheet-{width}.png"),
                                    full_page=True,animations="disabled")
                    geom=page.evaluate("""() => {
                       const el=document.getElementById('worksheet');
                       const ids=['ws-billed','ws-expected','ws-credits','ws-sample',
                                   'ws-clear','ws-print','ws-copy'];
                       const buttons=ids.map(id=>document.getElementById(id).getBoundingClientRect());
                       const outside=buttons.filter(r=>r.left < -1 || r.right > innerWidth+1);
                       const cards=[...document.querySelectorAll('.worksheet-stat')].map(x=>{
                         const r=x.getBoundingClientRect();return [r.width,r.left,r.right]});
                       const title=document.getElementById('ws-title');
                       const style=getComputedStyle(title);
                       return {width:innerWidth,documentWidth:document.documentElement.scrollWidth,
                         bodyWidth:document.body.scrollWidth,
                         offenderCount:outside.length,cardBounds:cards,
                         headingSize:parseFloat(style.fontSize),
                         printButtonHeight:document.getElementById('ws-print').getBoundingClientRect().height,
                         headerVisible:getComputedStyle(document.querySelector('.document-hero')).display!=='none'};
                    }""")
                    success=(response.status==200 and got=="$125.00"
                             and billed=="1167.60"
                             and policy=="local-only-no-storage-or-upload"
                             and geom["documentWidth"]<=width+1
                             and geom["bodyWidth"]<=width+1
                             and geom["offenderCount"]==0
                             and geom["printButtonHeight"]>=44
                             and not posts and not errors)
                    records.append({"viewport":f"{width}x{height}","http":response.status,
                        "candidate":got,"inputLocalOnly":policy=="local-only-no-storage-or-upload",
                        "withinViewport":geom["documentWidth"]<=width+1 and geom["bodyWidth"]<=width+1,
                        "controlOverflow":geom["offenderCount"],"minTapTarget":geom["printButtonHeight"],
                        "externalAttemptsBlocked":len(external),
                        "externalRequestSent":False,
                        "posts":len(posts),"errors":errors,"status":"PASS" if success else "RECHECK"})
                    if width==390:
                        # Tests actual recalculation without claiming money was received.
                        page.locator("#ws-credits").fill("50.00")
                        updated=page.locator("#ws-unresolved").inner_text().strip()
                        page.locator("#ws-clear").click()
                        cleared=page.locator("#ws-unresolved").inner_text().strip()
                        print_info["localRecalculation"]=(updated=="$75.00" and cleared=="—")
                        page.emulate_media(media="print")
                        page.set_viewport_size({"width":816,"height":1056})
                        page.evaluate("document.body.classList.add('worksheet-print-mode')")
                        # Print must reproduce checkboxes beside the text, not
                        # browser-native controls on a second line.
                        page.evaluate("document.querySelector('.worksheet-checklist input').checked = true")
                        print_info["checkedPrintState"] = page.evaluate("""() => {
                          const label=document.querySelector('.worksheet-checklist label');
                          const before=getComputedStyle(label,'::before');
                          return before.content.includes('✓') &&
                                 getComputedStyle(label.querySelector('input')).display==='none';
                        }""")
                        page.evaluate("document.querySelector('.worksheet-checklist input').checked = false")
                        printed=page.evaluate("""() => ({
                          checkboxIconVisible:(() => {
                            const label=document.querySelector('.worksheet-checklist label');
                            const style=getComputedStyle(label,'::before');
                            return style.display==='block' && parseFloat(style.width)>=10 &&
                              getComputedStyle(label.querySelector('input')).display==='none';
                          })(),
                          headerHidden:getComputedStyle(document.querySelector('.site-header')).display==='none',
                          skipHidden:getComputedStyle(document.querySelector('.skip')).display==='none',
                          boldBlack:getComputedStyle(document.querySelector('.worksheet-head strong')).color==='rgb(17, 17, 17)',
                          navHidden:getComputedStyle(document.querySelector('.document-nav')).display==='none',
                          worksheetVisible:getComputedStyle(document.querySelector('.worksheet-builder')).display!=='none',
                          checklistCount:document.querySelectorAll('.worksheet-checklist input[type=checkbox]').length,
                          printActionsHidden:getComputedStyle(document.querySelector('.worksheet-sharing')).display==='none'
                        })""")
                        page.screenshot(path=str(destination/"worksheet-print-mode-letter.png"),
                                        full_page=True,animations="disabled")
                        print_info["printCss"]=printed
                        print_info["printReadiness"]=all([
                            printed["headerHidden"],printed["navHidden"],
                            printed["skipHidden"],printed["boldBlack"],
                            printed["checkboxIconVisible"], print_info["checkedPrintState"],
                            printed["worksheetVisible"],printed["checklistCount"]==15,
                            printed["printActionsHidden"]])
                    ctx.close()
            finally:
                browser.close()
    finally:
        http.shutdown()
        http.server_close()
    report={
        "scope":"LOOPBACK_READ_ONLY_SYNTHETIC_FIGURES_NO_REAL_INVOICE",
        "buyerLeadVerified":False,"fundsRecovered":False,
        "screenshots":[f"worksheet-{w}.png" for w,_ in SIZES]+["worksheet-print-mode-letter.png"],
        "records":records,"print":print_info,
        "passed":len(records)==len(SIZES) and all(x["status"]=="PASS" for x in records)
                 and print_info.get("printReadiness") is True
                 and print_info.get("localRecalculation") is True,
    }
    (destination/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--site",required=True,type=Path)
    ap.add_argument("--out",required=True,type=Path)
    ap.add_argument("--fail-on-issues",action="store_true")
    args=ap.parse_args()
    result=verify(args.site,args.out)
    print(json.dumps({"passed":result["passed"],"viewports":result["records"],
                      "print":result["print"]},indent=2))
    return int(args.fail_on_issues and not result["passed"])


if __name__=="__main__":
    raise SystemExit(main())
