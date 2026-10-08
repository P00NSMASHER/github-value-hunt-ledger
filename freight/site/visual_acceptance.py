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
 return {innerWidth,documentWidth:doc.scrollWidth,bodyWidth:body.scrollWidth,
   overflow:Math.max(doc.scrollWidth,body.scrollWidth)-innerWidth,offenders:extents,
   dateWidth:date?Math.round(date.getBoundingClientRect().width):null,
   dateUnbroken:date?getComputedStyle(date).whiteSpace==='nowrap':null,
   title:document.title,footerContact,
   requiredLabels:[...document.querySelectorAll('input[required],select[required]')]
     .filter(e=>!e.labels?.length && !e.getAttribute('aria-label')).map(e=>e.name||e.id)
  };
}"""


def measure(bundle: Path, output: Path) -> dict:
    bundle = bundle.resolve()
    output.mkdir(parents=True, exist_ok=True)
    handler = partial(SimpleHTTPRequestHandler, directory=str(bundle))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}/"
    results = []
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
