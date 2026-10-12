#!/usr/bin/env python3
"""RETALLY experimental creative studio: local image export only; never publishes.

Production mode accepts only the SHA-256 pinned approved RETALLY wordmark from
freight/site/assets/brand. Preview mode accepts locally reviewed *noncanonical*
assets and visibly watermarks every output as NOT FOR PUBLICATION.
"""
import argparse
import base64
import hashlib
import json
import struct
from pathlib import Path

W, H = 1080, 1350
APPROVED_WORDMARK_SHA256 = '08421ccd7e8b1db752002f7ea177e76c83b6ee1cae40cf8b459368ade0c4eadd'
CANONICAL_WORDMARK = 'freight/site/assets/brand/retally-wordmark-approved.png'
CANONICAL_PHOTO = 'freight/site/assets/images/terminal-blue-hour.webp'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_resource(path, kind):
    data = Path(path).read_bytes()
    if kind == 'image/png' and not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Brand wordmark must be PNG')
    return f"data:{kind};base64,{base64.b64encode(data).decode('ascii')}"


def template_html(wordmark, photo, concept, preview=False):
    """Generate HTML with no network, links, tracking, scripts or editable input."""
    if concept not in ('rate_versions', 'accessorial_proof'):
        raise ValueError(f'Unknown concept: {concept}')
    # Both concepts share a deliberately constrained identity system.
    css = r'''
*{box-sizing:border-box} html,body{margin:0;background:#092020}
body{font-family:Arial,"Helvetica Neue",sans-serif;-webkit-font-smoothing:antialiased}
.artboard{width:1080px;height:1350px;position:relative;overflow:hidden;background:#f4f7f2;color:#11282a}
.hero{position:absolute;top:0;left:0;width:100%;height:710px;overflow:hidden;background:#071c1c;color:#fff}
.photo{position:absolute;inset:-20px;background-image:linear-gradient(90deg,rgba(4,22,22,.90),rgba(4,25,26,.55)),url('__PHOTO__');background-size:cover;background-position:center 45%;filter:saturate(.78) contrast(1.08)}
.hero::after{content:"";position:absolute;inset:0;background:linear-gradient(0deg,rgba(4,19,19,.96),rgba(5,26,27,.22) 60%),radial-gradient(circle at 75% 45%,transparent,rgba(2,14,14,.35));pointer-events:none}
.scan{position:absolute;inset:0;opacity:.14;background-image:linear-gradient(rgba(168,244,205,.24) 1px,transparent 1px),linear-gradient(90deg,rgba(168,244,205,.20) 1px,transparent 1px);background-size:44px 44px;transform:perspective(520px) rotateX(23deg) scale(1.25);transform-origin:center top;mask-image:linear-gradient(90deg,transparent 20%,black)}
.top{position:absolute;top:61px;left:74px;right:76px;height:95px;display:flex;justify-content:space-between;align-items:center;z-index:5}
.brand{background:#fcfcf8;box-shadow:0 3px 20px rgba(0,0,0,.22);border-radius:16px;padding:16px 22px;width:342px;height:84px;display:flex;align-items:center}
.brand img{display:block;width:100%;height:auto;object-fit:contain}
.issue{font-weight:800;color:#d2f9e9;font-size:20px;letter-spacing:2.5px;text-align:right;line-height:1.45}
.issue small{color:#8bcfac;font-size:16px;letter-spacing:2.1px;display:block}
.hero-body{position:absolute;left:77px;right:74px;top:230px;z-index:5}
.kicker{font-size:20px;color:#a2ebc9;font-weight:800;letter-spacing:3.4px;text-transform:uppercase;display:flex;align-items:center;gap:17px}
.kicker:before{content:"";height:2px;width:44px;background:#40cf92}
.hero-title{font-weight:900;letter-spacing:-5.5px;font-size:95px;line-height:.99;margin:29px 0 25px;max-width:916px;text-shadow:0 4px 15px rgba(0,0,0,.12)}
.hero-title .accent{color:#aaf1d0}
.hero-sub{font-size:30px;color:#e5f5ed;line-height:1.28;letter-spacing:-.5px;max-width:800px;margin-top:24px}
.upper-pill{display:inline-block;background:rgba(11,77,62,.48);border:1px solid rgba(154,238,201,.36);border-radius:999px;padding:11px 18px;font-size:17px;letter-spacing:2px;font-weight:800;color:#ceffe5;margin-top:30px}
.paper{position:absolute;top:687px;left:0;width:1080px;height:663px;background:#f4f7f2;border-radius:35px 35px 0 0;z-index:7;box-shadow:0 -30px 70px rgba(1,23,20,.18)}
.paper:before{content:"";position:absolute;right:-100px;top:-45px;width:380px;height:380px;border:1px solid rgba(18,132,93,.10);border-radius:50%}
.section-top{position:absolute;top:55px;left:75px;right:75px;display:flex;align-items:end;justify-content:space-between;z-index:2}
.eyebrow{font-weight:900;letter-spacing:2.9px;color:#087d59;font-size:19px}
.section-title{font-weight:900;font-size:37px;line-height:1.04;letter-spacing:-1.2px;margin:12px 0 0;color:#10272a}
.sample{font-size:19px;letter-spacing:1.4px;color:#53766d;font-weight:800;text-align:right;line-height:1.6}
.sample b{color:#146d58}
.divider{position:absolute;left:75px;right:75px;top:175px;height:2px;background:#d4e1d8}
.documents{position:absolute;top:220px;left:73px;width:934px;height:300px;z-index:4;display:flex;gap:22px}
.document{position:relative;flex:1;border:1px solid #d7e7de;background:#fff;border-radius:21px;padding:27px 28px;box-shadow:0 17px 36px rgba(15,44,36,.12);overflow:hidden}
.document:after{content:"";position:absolute;right:-30px;top:-35px;width:140px;height:140px;border:2px solid rgba(10,128,89,.065);border-radius:50%}
.doc-top{display:flex;align-items:center;justify-content:space-between;color:#5d7770;font-size:22px;font-weight:900;letter-spacing:1px}
.doc-type{font-size:30px;font-weight:900;letter-spacing:-.8px;margin:23px 0 14px;color:#143835}
.doc-rule{height:2px;background:#e3ece6;margin-bottom:24px}
.doc-label{font-size:20px;color:#77948a;letter-spacing:1.6px;font-weight:900;margin-bottom:10px}
.doc-value{border:2px solid #d5e4dc;border-radius:12px;height:54px;padding:14px 18px;color:#194137;font-size:22px;font-weight:800;background:#fbfdfa}
.document.verified{background:#f7fffa;border:2px solid #15916b;transform:translateY(-9px);box-shadow:0 19px 40px rgba(10,109,74,.16)}
.document.verified .doc-value{border-color:#21b486;background:#e6f9ed}
.doc-status{position:absolute;bottom:24px;right:24px;background:#d5fbe6;color:#087e55;border:1px solid #95e2bd;border-radius:999px;padding:8px 13px;font-size:14px;font-weight:900;letter-spacing:1.1px}
.connector{position:absolute;top:235px;left:524px;width:39px;height:4px;background:#0e9d72;z-index:10}
.connector:after{content:"";position:absolute;right:-1px;top:-6px;border-left:16px solid #0e9d72;border-top:8px solid transparent;border-bottom:8px solid transparent}
.keypoint{position:absolute;top:544px;left:76px;right:76px;border-top:2px solid #d0e0d5;display:flex;align-items:center;justify-content:space-between;padding-top:23px;z-index:3}
.keypoint strong{font-size:21px;letter-spacing:-.3px;color:#12352d;display:block;max-width:680px}
.keypoint em{font-size:17px;font-weight:900;font-style:normal;letter-spacing:1.4px;color:#087f59}
.footer-note{position:absolute;bottom:37px;left:77px;right:77px;display:flex;align-items:center;justify-content:space-between;font-size:21px;color:#5e7770;letter-spacing:1.1px;font-weight:800;z-index:4}
.footer-line{width:30px;height:3px;background:#0ba878;display:inline-block;margin-right:12px;vertical-align:middle}
/* Accessorial / second art direction */
.access .hero{height:800px;background:#edf5ef;color:#14342f}
.access .photo{filter:grayscale(.13) contrast(1.03) saturate(.85);background-image:linear-gradient(90deg,rgba(4,26,24,.85) 10%,rgba(4,29,26,.30) 70%),url('__PHOTO__');background-position:50% 45%}
.access .hero-title{font-size:91px;line-height:1.02;color:#fff}
.access .hero-sub{max-width:740px}
.access .paper{top:680px;height:670px}
.access .documents{height:322px;top:212px}
.access .document{padding:26px 28px}
.access .document .doc-type{font-size:28px}
.access .document.verified .doc-value{background:#f0fdf3}
.access .connector{top:245px}
.access .section-title{font-size:36px}
/* Preview-only mark never appears in production composition. */
.preview{position:absolute;bottom:0;left:0;width:100%;height:27px;background:#fff1cb;border-top:2px solid #ce8a19;z-index:100;color:#5b3804;font:900 15px Arial;text-align:center;padding-top:4px;letter-spacing:1.3px}
'''
    if concept == 'rate_versions':
        extra = '''
<section class="hero"><div class="photo"></div><div class="scan"></div>
<header class="top"><div class="brand"><img src="__LOGO__" alt="RETALLY approved wordmark" /></div><div class="issue">FIELD NOTES <small>01 / 02 · RATE CONTROL</small></div></header>
<div class="hero-body"><div class="kicker">Freight invoice intelligence</div>
<h1 class="hero-title">ONE LOAD.<br><span class="accent">TWO RATE</span><br>SHEETS.</h1>
<div class="hero-sub">The invoice may be correct.<br>The governing rate may not be.</div>
<div class="upper-pill">THE DATE CHANGES THE ANSWER</div></div></section>
<section class="paper"><div class="section-top"><div><div class="eyebrow">THE DOCUMENT TEST</div><h2 class="section-title">Which version applied?</h2></div><div class="sample">ILLUSTRATIVE<br><b>NO CUSTOMER DATA</b></div></div><div class="divider"></div>
<div class="documents">
<div class="document"><div class="doc-top"><span>DOCUMENT 01</span><span>ARCHIVED</span></div><div class="doc-type">RATE SHEET A</div><div class="doc-rule"></div><div class="doc-label">APPLICABLE DATE</div><div class="doc-value">Requires verification</div></div>
<div class="document verified"><div class="doc-top"><span>DOCUMENT 02</span><span>REVISED</span></div><div class="doc-type">RATE SHEET B</div><div class="doc-rule"></div><div class="doc-label">EFFECTIVE DATE</div><div class="doc-value">Requires verification</div><div class="doc-status">CHECK AUTHORITY</div></div></div>
<div class="connector"></div>
<div class="keypoint"><strong>Compare effective dates, amendments and governing terms.</strong><em>VERIFY →</em></div>
<div class="footer-note"><span><i class="footer-line"></i>FIND IT. PROVE IT. RECOVER IT.</span><span>RETALLYRECOVERY.COM</span></div></section>'''
        cl = 'artboard'
    else:
        extra = '''
<section class="hero"><div class="photo"></div><div class="scan"></div>
<header class="top"><div class="brand"><img src="__LOGO__" alt="RETALLY approved wordmark" /></div><div class="issue">FIELD NOTES <small>02 / 02 · SERVICE EVIDENCE</small></div></header>
<div class="hero-body"><div class="kicker">Freight accessorial controls</div>
<h1 class="hero-title">CHARGE<br><span class="accent">≠ PROOF.</span></h1>
<div class="hero-sub">A liftgate fee appears on a bill.<br>What shows the service happened?</div>
<div class="upper-pill">A FLAG IS NOT A FINDING</div></div></section>
<section class="paper"><div class="section-top"><div><div class="eyebrow">THE EVIDENCE CHAIN</div><h2 class="section-title">Reconcile the records.</h2></div><div class="sample">ILLUSTRATIVE<br><b>NO CUSTOMER DATA</b></div></div><div class="divider"></div>
<div class="documents">
<div class="document"><div class="doc-top"><span>INVOICE</span><span>LINE ITEM</span></div><div class="doc-type">LIFTGATE FEE</div><div class="doc-rule"></div><div class="doc-label">BILLED CHARGE</div><div class="doc-value">Fee present on bill</div></div>
<div class="document verified"><div class="doc-top"><span>SERVICE</span><span>RECORD</span></div><div class="doc-type">PROOF OF SERVICE</div><div class="doc-rule"></div><div class="doc-label">EVIDENCE REQUIRED</div><div class="doc-value">Verify documentation</div><div class="doc-status">DO NOT ASSUME</div></div></div>
<div class="connector"></div>
<div class="keypoint"><strong>Check the contract trigger, service proof and prior credits.</strong><em>SAVE THIS →</em></div>
<div class="footer-note"><span><i class="footer-line"></i>FIND IT. PROVE IT. RECOVER IT.</span><span>RETALLYRECOVERY.COM</span></div></section>'''
        cl = 'artboard access'
    doc = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=1080,initial-scale=1"><title>RETALLY graphic concept</title><style>{css}</style></head><body><main class="{cl}">{extra}'
    if preview:
        doc += '<div class="preview">DESIGN CONCEPT ONLY • NOT APPROVED FOR PUBLICATION</div>'
    doc += '</main></body></html>'
    return doc.replace('__LOGO__', wordmark).replace('__PHOTO__', photo)


def run(output, mode, concept, logo, photo, executable=None):
    output = Path(output);output.mkdir(parents=True,exist_ok=True)
    if mode == 'production':
        if sha256(logo) != APPROVED_WORDMARK_SHA256:
            raise ValueError('Unapproved logo checksum: refuse export')
        png = Path(logo).read_bytes()
        if struct.unpack('>II',png[16:24]) != (1619,257):
            raise ValueError('Approved logo geometry mismatch')
    wordmark = read_resource(str(logo),'image/png')
    photo = read_resource(str(photo),'image/webp' if str(photo).lower().endswith('.webp') else 'image/png')
    concepts = ['rate_versions','accessorial_proof'] if concept == 'both' else [concept]
    images = []
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        opts={'headless':True}
        if executable:opts['executable_path']=executable
        browser = pw.chromium.launch(**opts)
        try:
            for name in concepts:
                page=browser.new_page(viewport={'width':W,'height':H},device_scale_factor=1)
                page.set_content(template_html(wordmark,photo,name,preview=(mode=='preview')),wait_until='load')
                page.evaluate('document.fonts.ready')
                check=page.evaluate('''() => {const b=document.querySelector('.artboard');const r=b.getBoundingClientRect();return {w:r.width,h:r.height, scrollW:b.scrollWidth,scrollH:b.scrollHeight,logo:document.images[0]?.naturalWidth,photoLoaded:document.images[0]?.complete}}''')
                if (check['w'],check['h']) != (W,H) or check['logo'] < 400 or not check['photoLoaded']:
                    raise RuntimeError(f'Geometry/approved image load failed: {check}')
                path=output/(f'concept-{name}-{mode}.png')
                page.screenshot(path=str(path),type='png',animations='disabled')
                blob=path.read_bytes()
                if not blob.startswith(b'\x89PNG\r\n\x1a\n') or struct.unpack('>II',blob[16:24])!=(W,H):
                    raise RuntimeError('Rendered image has wrong size or MIME')
                images.append({'concept':name,'file':str(path),'sha256':sha256(path),'width':W,'height':H,'preview_only':mode=='preview','requires_human_visual_approval':True})
                page.close()
        finally:
            browser.close()
    manifest={'brand':'RETALLY','intent':'local graphics QA only','network_calls':False,'social_publication':False,'mode':mode,'assets':images}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--mode',choices=['production','preview'],default='production')
    a.add_argument('--concept',choices=['rate_versions','accessorial_proof','both'],default='both')
    a.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parent)
    a.add_argument('--logo',type=Path,help='Preview mode only: local reviewed wordmark image')
    a.add_argument('--photo',type=Path,help='Preview mode only: locally licensed freight photo PNG/WebP')
    a.add_argument('--chromium',help='Optional local Chromium binary path')
    a.add_argument('--output-dir',type=Path,default=Path('dist/retally-social-review'))
    args=a.parse_args()
    if args.mode=='production':
        if args.logo or args.photo: a.error('Production assets are fixed to approved repo paths; overrides forbidden')
        logo=args.repo_root/CANONICAL_WORDMARK
        photo=args.repo_root/CANONICAL_PHOTO
    else:
        if not args.logo or not args.photo: a.error('Preview needs explicit local reviewed assets')
        logo,photo=args.logo,args.photo
    report=run(args.output_dir,args.mode,args.concept,logo,photo,args.chromium)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()