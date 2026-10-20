#!/usr/bin/env python3
"""RETALLY Field Notes v4: six four-slide, review-only freight-finance carousels.

Builds 24 original 1080x1350 PNGs plus phone-sized previews with exactly
approved RETALLY source wordmark and registered topic-specific photo sources.
Offline only: no customer material, social posting, external requests or claims.
Human visual and source-asset rights sign-off are separate release blockers.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import struct

import render_social as base
import render_social_v3 as v3

WIDTH, HEIGHT = 1080, 1350
PHONE_WIDTH, PHONE_HEIGHT = 390, 488
CONCEPTS = v3.CONCEPTS
TOPICS = {
    "scope_first": {
        "cover": "FIRST DEFINE<br>THE <em>SCOPE.</em>",
        "lead": "A reliable audit begins with a fixed set of freight invoices.",
        "three": [
            ("01", "WHICH SHIPMENTS?", "Identify carriers, modes, entities and invoice periods."),
            ("02", "WHAT IS EXCLUDED?", "Record exclusions, currencies and the cutoff dates."),
            ("03", "WHAT WAS FIXED?", "Reconcile existing disputes, corrections and credits."),
        ],
        "test_title": "THE QUESTION ISN'T<br>HOW BIG.",
        "evidence": "Can another reviewer reproduce the exact invoice population?",
        "not_evidence": "Counting a previously issued credit as a fresh recovery.",
        "last": "FREEZE THE<br><em>POPULATION.</em>",
        "closer": "Source the invoice set, then compare each charge against the governing record.",
    },
    "fuel_authority": {
        "cover": "FUEL CHARGE?<br><em>CHECK THE RULE.</em>",
        "lead": "The index on today's website may not govern yesterday's shipment.",
        "three": [
            ("01", "RATE AUTHORITY", "Find the signed agreement and incorporated fuel terms."),
            ("02", "INDEX PERIOD", "Verify lookback dates and effective surcharge table."),
            ("03", "CHARGE BASIS", "Recalculate the eligible base and rounding method."),
        ],
        "test_title": "THE LOWER RATE<br>ISN'T THE PROOF.",
        "evidence": "The controlling contract version and applicable index window.",
        "not_evidence": "A convenient current rate downloaded after shipment.",
        "last": "THE AGREEMENT<br><em>CONTROLS.</em>",
        "closer": "Missing authority means review is needed, not that an overcharge is proven.",
    },
    "detention_clock": {
        "cover": "90 MIN BILLED.<br><em>30 PAST FREE?</em>",
        "lead": "Illustrative timing example, never a real customer result.",
        "three": [
            ("01", "08:30 TO 11:00", "Gate log: 150 minutes onsite in this sample."),
            ("02", "120 MIN FREE", "Hypothetical signed terms start free time at arrival."),
            ("03", "30 MIN BEYOND", "90 billed suggests a 60-minute question for review."),
        ],
        "test_title": "A QUESTION.<br>NOT A REFUND.",
        "evidence": "Contract trigger, appointment rule, actual timestamp and adjustments.",
        "not_evidence": "Assuming onsite time alone makes the carrier's fee invalid.",
        "last": "THE TERMS<br><em>DECIDE.</em>",
        "closer": "Verify exceptions, corrections and previous credits before disputing.",
    },
    "claim_evidence": {
        "cover": "A FLAG<br><em>ISN'T PROOF.</em>",
        "lead": "A defensible dispute comes with the documents and calculation.",
        "three": [
            ("01", "IDENTIFY THE LOAD", "Connect the freight invoice to the shipment record."),
            ("02", "IDENTIFY THE RULE", "Show the rate authority in force at shipment time."),
            ("03", "REPRODUCE THE GAP", "Recalculate and reconcile corrections and credits."),
        ],
        "test_title": "CAN SOMEONE ELSE<br>VERIFY IT?",
        "evidence": "Invoice, bill of lading, controlling terms and reproducible amount.",
        "not_evidence": "A dashboard flag described as an approved recovery.",
        "last": "PROOF<br><em>BEFORE CLAIM.</em>",
        "closer": "External recovery action still requires separate customer authorization.",
    },
    "settlement_status": {
        "cover": "APPROVED<br><em>ISN'T PAID.</em>",
        "lead": "An authorized claim, credit memo and actual recovery are different.",
        "three": [
            ("01", "VALIDATED FINDING", "Evidence supports the billing discrepancy."),
            ("02", "CLAIM DECISION", "Approval or denial is a separate milestone."),
            ("03", "USABLE RECOVERY", "Confirm posted credits, refunds and reversals."),
        ],
        "test_title": "COUNT WHAT<br>WAS REALIZED.",
        "evidence": "Eligible net received funds or usable credits under signed terms.",
        "not_evidence": "An estimate, approval email or reversed credit.",
        "last": "NET VALUE.<br><em>NOT PROMISES.</em>",
        "closer": "A reported recovery must survive reconciliation and later reversals.",
    },
    "secure_intake": {
        "cover": "NO INVOICES<br><em>IN DMS.</em>",
        "lead": "Public social channels are not secure freight-file transfer routes.",
        "three": [
            ("01", "START WITH SCOPE", "Discuss freight mode, carriers and billing periods."),
            ("02", "AGREE THE ROUTE", "Confirm permissions and a suitable secure transfer."),
            ("03", "PROTECT RECORDS", "Keep rates, invoices and bank details out of DMs."),
        ],
        "test_title": "GENERAL QUESTIONS.<br>PRIVATE RECORDS.",
        "evidence": "A bounded request and an authorized secure data route.",
        "not_evidence": "Sharing a customer invoice, password or account details in chat.",
        "last": "SCOPE FIRST.<br><em>DATA SECOND.</em>",
        "closer": "An opened email draft is not a request that the business received.",
    },
}

CSS = r'''
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#0a1b1c;color:#f4fff7;font-family:Arial,Helvetica,sans-serif;-webkit-font-smoothing:antialiased}
.art{width:1080px;height:1350px;overflow:hidden;position:relative;isolation:isolate;background:#0b2523}
.bg{position:absolute;inset:0;background-image:linear-gradient(99deg,#04191ee8 2%,#0a2524c2 57%,#12272777 100%),url("__PHOTO__");background-size:cover;background-position:50% 50%;filter:saturate(.91) contrast(1.05)}
.art:before{position:absolute;inset:0;content:"";z-index:1;background:linear-gradient(0deg,#001913f2,transparent 48%),radial-gradient(circle at 84% 56%,#1ad99d29,transparent 43%);pointer-events:none}
.inner{position:relative;z-index:3;height:100%;padding:73px 78px}
.top{display:flex;align-items:center;justify-content:space-between;min-height:72px}
.brand{width:313px;padding:15px 19px;background:#fafffc;border-radius:13px;box-shadow:0 16px 33px #00170f6b}
.brand img{display:block;width:100%;height:auto}
.series{text-transform:uppercase;font-size:26px;letter-spacing:2px;color:#beffe0;text-align:right;font-weight:800;line-height:1.25}
.series b{display:block;font-size:19px;letter-spacing:1px;color:#e3fff4;margin-top:7px}
.line{height:3px;width:65px;background:#34e4a6;margin:52px 0 27px}
.label{font-size:26px;font-weight:900;letter-spacing:3.4px;color:#acffd6;text-transform:uppercase}
h1{font-weight:900;letter-spacing:-5.1px;line-height:1.06;font-size:114px;margin:30px 0 27px;color:white}
h1 em{font-style:normal;color:#a2ffd1}
.intro{font-size:49px;line-height:1.25;letter-spacing:-1.1px;font-weight:500;max-width:900px}
.cover .content{position:absolute;left:78px;right:80px;top:325px}
.cover .intro{margin-top:24px}
.bottom{position:absolute;left:78px;right:78px;bottom:95px;display:flex;align-items:end;justify-content:space-between;gap:30px}
.swipe{font-size:35px;font-weight:900;background:#16af7e;color:#fff;border-radius:60px;padding:25px 34px;white-space:nowrap}
.smallnote{font-size:24px;line-height:1.3;text-align:right;font-weight:700;color:#dafdeb}
.footer{position:absolute;left:78px;right:78px;bottom:31px;font-size:21px;font-weight:800;letter-spacing:1px;color:#b8d9ca;display:flex;justify-content:space-between;align-items:center}
.steps{background:linear-gradient(165deg,#f7fff8,#dceee6);color:#113c31}
.steps .inner{z-index:3}
.steps .bg{display:none}
.steps:before{background:radial-gradient(circle at 100% 0%,#30c48827,transparent 45%)}
.steps .series{color:#177755}.steps .series b{color:#427668}
.steps h1{font-size:88px;letter-spacing:-3.6px;color:#07372b;line-height:1.04;margin:55px 0 18px}
.steps .intro{font-size:37px;color:#47675b;margin:0}
.steps .stack{position:absolute;left:76px;right:77px;top:415px;display:grid;gap:23px}
.row{height:221px;border:2px solid #c7dfd3;background:#fffefa;border-radius:28px;display:flex;gap:34px;align-items:center;padding:32px 35px;box-shadow:0 17px 30px #143b2d13}
.row:nth-child(2){border-color:#33b887;background:linear-gradient(115deg,#f5fff9,#ddf8e9)}
.number{height:112px;min-width:112px;border-radius:26px;background:#0b614b;color:#effff6;font-size:48px;font-weight:900;display:grid;place-items:center}
.row h2{font-size:47px;line-height:1.05;margin:0 0 13px;letter-spacing:-1.8px;color:#083b2b}
.row p{font-size:36px;line-height:1.19;margin:0;color:#385949;max-width:650px}
.steps .footer{color:#205f4b}
.compare{background:linear-gradient(145deg,#063a33,#081c21)}
.compare .bg{opacity:.19;filter:grayscale(.6)}
.compare .inner h1{font-size:94px;margin:47px 0 18px;max-width:900px}
.compare .intro{font-size:36px;color:#c5e5d7;margin:0 0 27px}
.panels{position:absolute;left:75px;right:77px;top:536px;display:grid;gap:26px}
.panel{padding:29px 41px;background:#eefff5;color:#0a3428;border-radius:28px;min-height:266px;box-shadow:0 15px 29px #001a1770}
.panel:nth-child(2){background:#fff5e9;color:#443323}
.panel h2{font-size:37px;text-transform:uppercase;letter-spacing:1.6px;margin:0 0 14px;color:#087557}
.panel:nth-child(2) h2{color:#96602e}
.panel p{font-size:48px;line-height:1.14;font-weight:800;letter-spacing:-1.3px;margin:0}
.closer .bg{background-image:linear-gradient(93deg,#061917ee,#051e20e1 44%,#082926a8 100%),url("__PHOTO__");background-position:center 40%}
.closer .content{position:absolute;left:78px;right:77px;top:343px}
.closer h1{font-size:109px}
.closer .intro{font-size:47px;max-width:910px;margin-top:28px}
.cta{position:absolute;left:75px;right:75px;bottom:145px;border-radius:28px;padding:29px 35px;background:#eafff3;color:#07392e}
.cta strong{display:block;font-size:35px;font-weight:900;color:#087957;letter-spacing:1px}
.cta span{display:block;margin-top:11px;font-size:37px;font-weight:700;line-height:1.18;overflow-wrap:anywhere}
.art.scope .bg{background-position:50% 55%}
.art.fuel .bg{background-position:43% 52%}
.art.detention .bg{background-position:68% 55%}
.art.evidence .bg{background-position:60% 50%}
.art.settlement .bg{background-position:67% 52%}
.art.security .bg{background-position:43% 52%}
.art.detention.cover h1{font-size:105px}
.art.detention.compare h1{font-size:102px}
.art.security.compare h1{font-size:91px}
'''


def _e(value: str) -> str:
    return html.escape(value, quote=True)


def _h(value: str) -> str:
    """Allow only two trusted, fixed formatting tags from the static copy."""
    # All copy is repository-owned; forbid future remotely influenced markup.
    if re.search(r"<(?!/?(?:em|br)\b)", value, re.I):
        raise ValueError("Unexpected markup in editorial source")
    return value


def template_html(concept: str, slide: int, logo_uri: str, photo_uri: str) -> str:
    if concept not in CONCEPTS or slide not in (1,2,3,4):
        raise ValueError("Unrecognized concept or slide")
    item=TOPICS[concept]
    if len(item["three"]) != 3:
        raise ValueError("Every carousel requires three evidence checks")
    klass=v3.COPY[concept]["style"]
    parts=[
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>RETALLY | illustrative internal carousel draft</title>',
        '<style>',CSS,'</style></head><body>',
        '<main class="art ',klass,' ',('cover' if slide==1 else 'steps' if slide==2 else 'compare' if slide==3 else 'closer'),'">',
        '<div class="bg"></div><div class="inner"><div class="top">',
        '<div class="brand" data-qa="logo"><img src="__LOGO__" alt="Original RETALLY wordmark"></div>',
        '<div class="series">FIELD NOTES <b>',str(slide),' / 4</b></div></div>',
    ]
    if slide==1:
        parts.extend([
            '<div class="content" data-qa="content"><div class="label">',_e(v3.COPY[concept]["subissue"]),'</div>',
            '<h1 data-qa="headline">',_h(item["cover"]),'</h1>',
            '<p class="intro" data-qa="description">',_e(item["lead"]),'</p></div>',
            '<div class="bottom" data-qa="cta"><div class="swipe">SWIPE TO REVIEW →</div>',
            '<div class="smallnote">ILLUSTRATIVE FRAMEWORK<br>NOT CUSTOMER RESULTS</div></div>'
        ])
    elif slide==2:
        parts.extend([
            '<h1 data-qa="headline">3 EVIDENCE<br>CHECKS.</h1>',
            '<p class="intro" data-qa="description">Each question needs the controlling record.</p>',
            '<div class="stack">'
        ])
        for number,title,description in item["three"]:
            parts.extend([
                '<div class="row" data-qa="evidence"><div class="number">',_e(number),'</div>',
                '<div class="words"><h2>',_e(title),'</h2><p>',_e(description),'</p></div></div>'
            ])
        parts.append('</div>')
    elif slide==3:
        parts.extend([
            '<h1 data-qa="headline">',_h(item["test_title"]),'</h1>',
            '<p class="intro" data-qa="description">Separate the supported fact from the assumption.</p>',
            '<div class="panels"><div class="panel" data-qa="supported"><h2>Evidence to confirm</h2>',
            '<p>',_e(item["evidence"]),'</p></div>',
            '<div class="panel" data-qa="unsupported"><h2>Do not assume</h2>',
            '<p>',_e(item["not_evidence"]),'</p></div></div>'
        ])
    else:
        parts.extend([
            '<div class="content" data-qa="content"><div class="label">WHAT TO REMEMBER</div>',
            '<h1 data-qa="headline">',_h(item["last"]),'</h1>',
            '<p class="intro" data-qa="description">',_e(item["closer"]),'</p></div>',
            '<div class="cta" data-qa="cta"><strong>READ THE EVIDENCE GUIDE</strong>',
            '<span>retallyrecovery.com/',_e(v3.COPY[concept]["site_slug"]),'</span></div>'
        ])
    parts.extend([
        '<div class="footer" data-qa="footer"><span>FIND IT. PROVE IT. RECOVER IT.</span>',
        '<span>DESIGN DRAFT · NOT PUBLISHED</span></div>',
        '</div></main></body></html>'
    ])
    markup=''.join(parts).replace("__LOGO__",logo_uri).replace("__PHOTO__",photo_uri)
    if re.search(r"<script|<iframe|<form|https?://",markup,re.I):
        raise ValueError("Offline carousel attempted active or external content")
    return markup


QA_SCRIPT = r'''() => {
 const art=document.querySelector('.art'),logo=document.querySelector('.brand img');
 const bad=[], selectors=['[data-qa]'];
 for(const node of document.querySelectorAll(selectors.join(','))){
   const r=node.getBoundingClientRect(),cl=node.clientWidth,sc=node.scrollWidth;
   if(r.left < -2 || r.right > 1082 || r.top < -2 || r.bottom > 1352) bad.push(node.getAttribute('data-qa')+':canvas');
   if(sc>cl+3) bad.push(node.getAttribute('data-qa')+':overflow');
 }
 for(const node of document.querySelectorAll('.row h2,.row p,.panel p,.panel h2,.cta span,.intro,.series,.footer')){
   const rect=node.getBoundingClientRect(), parent=node.parentElement.getBoundingClientRect();
   if(rect.right > parent.right+3 || rect.bottom > parent.bottom+3) bad.push(node.className+':clipped');
 }
 return {
  art:[art.clientWidth,art.clientHeight],
  brand:[logo.naturalWidth,logo.naturalHeight],
  evidence_cards:document.querySelectorAll('.row').length,
  panels:document.querySelectorAll('.panel').length,
  escaped_elements:bad,
  scripts:document.scripts.length,
  has_draft_label:document.body.innerText.includes('NOT PUBLISHED')
 };
}'''


def slide_alt(concept: str, number: int) -> str:
    """Per-slide accessibility text, never a fabricated customer description."""
    if concept not in CONCEPTS or number not in (1,2,3,4):
        raise ValueError("Unrecognized concept or slide")
    item=TOPICS[concept]
    if number==1:
        detail="Topic opener: "+re.sub(r"<[^>]+>"," ",item["cover"]).strip()+". "+item["lead"]
    elif number==2:
        detail="Three evidence checks: "+ "; ".join(
            f"{title}: {description}" for _,title,description in item["three"])
    elif number==3:
        detail=("Separate proof from assumption. Evidence to confirm: "+
                item["evidence"]+" Do not assume: "+item["not_evidence"])
    else:
        detail=("Summary: "+re.sub(r"<[^>]+>"," ",item["last"]).strip()+". "+
                item["closer"]+" Read the educational guide.")
    return "RETALLY Field Notes, slide "+str(number)+" of 4. "+detail+" Illustrative framework; not an actual customer outcome."


def png_dimensions(blob: bytes) -> tuple[int,int]:
    if not blob.startswith(b"\x89PNG\r\n\x1a\n") or len(blob)<24:
        raise ValueError("Screenshot is not PNG")
    return struct.unpack(">II",blob[16:24])


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(repo: Path, output: Path, *, concept: str="all",
           chromium: str|None=None, preview_photo: Path|None=None) -> dict:
    if concept not in (*CONCEPTS,"all"):
        raise ValueError("Unknown concept")
    repo=repo.resolve()
    output=output.resolve()
    logo=repo/base.CANONICAL_WORDMARK
    base.validate_logo(logo)
    if output==repo or repo in output.parents:
        raise ValueError("Exports must be outside repository checkout")
    names=CONCEPTS if concept=="all" else (concept,)
    photos={}
    for name in names:
        file=(preview_photo if preview_photo is not None else
              repo/"freight/site/assets/images"/v3.CANONICAL_HERO_PHOTOS[name])
        if file.is_symlink() or not file.is_file():
            raise ValueError("Unreviewed or missing photo source")
        photos[name]={"file":file,"data":base.read_image(file),"sha256":digest(file)}
    logo_uri=base.read_image(logo)
    output.mkdir(parents=True,exist_ok=True)
    from playwright.sync_api import sync_playwright
    slides=[]
    with sync_playwright() as p:
        config={"headless":True}
        if chromium: config["executable_path"]=chromium
        browser=p.chromium.launch(**config)
        try:
            for name in names:
                for number in range(1,5):
                    page=browser.new_page(viewport={"width":WIDTH,"height":HEIGHT})
                    external=[]
                    page.on("request",lambda q:external.append(q.url) if q.url.startswith(("http:","https:")) else None)
                    page.set_content(template_html(name,number,logo_uri,photos[name]["data"]),wait_until="load")
                    page.evaluate("document.fonts.ready")
                    qa=page.evaluate(QA_SCRIPT)
                    if (qa["art"] != [WIDTH,HEIGHT] or
                        qa["brand"]!=[1619,257] or qa["escaped_elements"] or
                        qa["scripts"] or external or not qa["has_draft_label"]):
                        raise RuntimeError(f"Carousel QA failed: {name} #{number} {qa} external={external}")
                    full=output/f"retally-{name}-v4-slide{number}-1080x1350.png"
                    phone=output/f"retally-{name}-v4-slide{number}-390px.png"
                    page.screenshot(path=str(full),type="png",animations="disabled")
                    scaled=browser.new_page(viewport={"width":PHONE_WIDTH,"height":PHONE_HEIGHT})
                    scaled.set_content(template_html(name,number,logo_uri,photos[name]["data"]),wait_until="load")
                    scaled.add_style_tag(content=(
                        f"html,body{{width:{PHONE_WIDTH}px;height:{PHONE_HEIGHT}px;overflow:hidden}}"
                        f".art{{transform:scale({PHONE_WIDTH/WIDTH});transform-origin:top left}}"))
                    scaled.screenshot(path=str(phone),type="png",animations="disabled")
                    if png_dimensions(full.read_bytes()) != (WIDTH,HEIGHT):
                        raise RuntimeError("Invalid full-size output")
                    if png_dimensions(phone.read_bytes()) != (PHONE_WIDTH,PHONE_HEIGHT):
                        raise RuntimeError("Invalid phone output")
                    slides.append({
                        "concept":name,"slide":number,"image":str(full),
                        "phone_preview":str(phone),"sha256":digest(full),
                        "phone_sha256":digest(phone),"qa":qa,
                        "publication_approved":False,
                        "human_visual_review_required":True,
                        "proposed_alt_text":slide_alt(name,number),
                        "educational_page":"/"+v3.COPY[name]["site_slug"]
                    })
                    page.close();scaled.close()
        finally:
            browser.close()
    report={
        "brand":"RETALLY","series":"Field Notes v4 4-slide carousels",
        "status":"INTERNAL_DRAFT_ONLY_NOT_APPROVED_FOR_PUBLICATION",
        "no_publication":True,"no_network_requests":True,
        "logo_sha256":digest(logo),
        "logo_preserved_original":True,
        "source_photo_rights_review_required":True,
        "sources":{k:{"filename":v["file"].name,"sha256":v["sha256"],
                      "rights_verified_for_social":False} for k,v in photos.items()},
        "slides":slides,
        "slide_count":len(slides),
        "phone_preview_count":len(slides),
    }
    # Offline publication-hold handoff: all 12 existing topic-specific captions
    # become review-only carousels with four local image files. No API calls or
    # externally hosted URLs are invented for these unreleased images.
    source=Path(__file__).with_name("v3_draft_captions.json")
    proposal=json.loads(source.read_text(encoding="utf-8"))
    by_concept={row["concept"]:row for row in proposal["content"]}
    if set(by_concept)!=set(CONCEPTS):
        raise ValueError("Source caption pack does not match the six carousel topics")
    review_posts=[]
    for name in names:
        group=sorted([row for row in slides if row["concept"]==name],key=lambda row:row["slide"])
        if [row["slide"] for row in group]!=[1,2,3,4]:
            raise ValueError("Carousel must include exactly four ordered slides")
        for network in ("facebook","instagram"):
            original=by_concept[name][network]
            if original.get("autoPublish") is not False or original.get("type")!="POST":
                raise ValueError("Source caption cannot auto-publish")
            review_posts.append({
                "network":network,"concept":name,"draft":True,
                "autoPublish":False,"ready_to_publish":False,
                "status":"UNAPPROVED_LOCAL_ONLY",
                "caption":original["caption"],
                "carousel_images":[Path(row["image"]).name for row in group],
                "mediaAltText":[row["proposed_alt_text"] for row in group],
                "educational_page":"/"+v3.COPY[name]["site_slug"],
                "source_rights_review_required":True,
                "human_visual_approval_required":True,
            })
    postings={
        "brand":"RETALLY","kind":"internal-only-carousel-draft-handoff",
        "social_provider_mutations":False,
        "no_external_images_uploaded":True,
        "posts":review_posts,
    }
    (output/"v4-review-only-post-pack.json").write_text(
        json.dumps(postings,indent=2)+"\n",encoding="utf8")
    report["draft_post_pack"]="v4-review-only-post-pack.json"
    # Self-contained, dependency-free offline visual comparison page.
    gallery=[
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>RETALLY carousel phone preview | review only</title>',
        '<style>body{font:16px Arial;background:#091e1a;color:#eafff3;margin:0;padding:18px}',
        'h1{font-size:26px}h2{font-size:21px;color:#a2f8ca}',
        '.hint{background:#164c3b;padding:14px;border-radius:10px;max-width:860px}',
        '.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));',
        'gap:18px;max-width:1700px;margin:18px 0 35px}',
        'figure{margin:0}img{width:100%;height:auto;border-radius:8px;border:1px solid #557b6b}',
        'figcaption{padding-top:8px;font-weight:700}</style></head><body>',
        '<h1>RETALLY Field Notes v4 — six swipe carousels</h1>',
        '<p class="hint">Internal visual review only. Not licensed, approved,',
        ' scheduled or published. Check readability on a real phone and',
        ' original image rights before any future posting.</p>',
    ]
    for name in names:
        gallery.append('<section><h2>'+_e(name.replace("_"," ").title())+'</h2><div class="grid">')
        for row in sorted((x for x in slides if x["concept"]==name),
                          key=lambda x:x["slide"]):
            gallery.extend([
                '<figure><img loading="lazy" src="',
                _e(Path(row["phone_preview"]).name),
                '" alt="',_e(row["proposed_alt_text"]),'">',
                '<figcaption>Slide ',str(row["slide"]),'/4</figcaption></figure>'
            ])
        gallery.append('</div></section>')
    gallery.append('</body></html>')
    (output/"review-gallery.html").write_text("".join(gallery),encoding="utf8")
    report["offline_review_gallery"]="review-gallery.html"
    (output/"manifest-v4.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    return report


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",type=Path,default=Path(__file__).resolve().parents[4])
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--concept",choices=(*CONCEPTS,"all"),default="all")
    p.add_argument("--chromium",default=None)
    args=p.parse_args()
    outcome=render(args.repo_root,args.output_dir,concept=args.concept,chromium=args.chromium)
    print(json.dumps({"slide_count":outcome["slide_count"],"no_publication":outcome["no_publication"],
                      "source_concepts":sorted(outcome["sources"])},indent=2))


if __name__=="__main__":
    main()
