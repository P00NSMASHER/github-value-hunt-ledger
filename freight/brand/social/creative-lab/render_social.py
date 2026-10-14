#!/usr/bin/env python3
"""RETALLY creative studio: approved-brand, offline, draft-only social graphics.

Renders three freight-billing education compositions to 1080x1350 PNG and
390px feed-size QA previews. It NEVER publishes, uploads, or sends messages.
The exact approved PNG brand source is enforced in preview and production.
Preview mode accepts art-directed locally owned sample imagery, watermarks the
finished graphics and records their provenance as unapproved production art.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import struct
from pathlib import Path

W, H = 1080, 1350
PHONE_W, PHONE_H = 390, 488
CONCEPTS = ('rate_versions', 'accessorial_proof', 'credit_chain')
APPROVED_WORDMARK_SHA256 = '08421ccd7e8b1db752002f7ea177e76c83b6ee1cae40cf8b459368ade0c4eadd'
APPROVED_EMBLEM_SHA256 = 'bb02ab4a468762f597c241199baeff61b485dd793f8fb746140ad33670b68043'
CANONICAL_WORDMARK = 'freight/site/assets/brand/retally-wordmark-approved.png'
CANONICAL_EMBLEM = 'freight/site/assets/brand/retally-emblem-approved.png'
CANONICAL_PHOTOS = {
    'rate_versions': 'freight/site/assets/images/terminal-blue-hour.webp',
    'accessorial_proof': 'freight/site/assets/images/terminal-blue-hour.webp',
    'credit_chain': 'freight/site/assets/images/terminal-blue-hour.webp',
}


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_logo(path: Path) -> None:
    """Do not accept approximated, retired, reconstructed or generated logos."""
    data = Path(path).read_bytes()
    if sha256(path) != APPROVED_WORDMARK_SHA256:
        raise ValueError('Unapproved logo checksum: refuse export')
    if not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data) < 24:
        raise ValueError('Approved wordmark must be a PNG')
    if struct.unpack('>II', data[16:24]) != (1619, 257):
        raise ValueError('Approved logo geometry mismatch')


def read_image(path: Path) -> str:
    path = Path(path)
    data = path.read_bytes()
    if data.startswith(b'\x89PNG\r\n\x1a\n') and len(data) >= 24:
        mime = 'image/png'
        if not all(0 < dim <= 10000 for dim in struct.unpack('>II', data[16:24])):
            raise ValueError(f'Implausible PNG dimensions in {path}')
    elif data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        mime = 'image/webp'
    elif data.startswith(b'\xff\xd8\xff'):
        mime = 'image/jpeg'
    else:
        raise ValueError(f'Unsupported image bytes: {path}')
    return f'data:{mime};base64,{base64.b64encode(data).decode("ascii")}'


CSS = r'''
*{box-sizing:border-box}
html,body{margin:0;background:#071916}
body{font-family:Cabin,Arimo,"Arial",sans-serif;-webkit-font-smoothing:antialiased}
.artboard{position:relative;isolation:isolate;width:1080px;height:1350px;overflow:hidden;color:#112d27;background:#ecf4ee}
.hero{position:absolute;inset:0 0 auto;height:758px;background:#071d1b;color:white;overflow:hidden}
.photo{position:absolute;inset:-13px;background-image:linear-gradient(90deg,rgba(2,15,16,.93) 3%,rgba(2,22,25,.75) 47%,rgba(4,18,20,.12) 100%),url('__PHOTO__');background-size:cover;background-position:center 50%;filter:saturate(1.11) contrast(1.09)}
.hero:before{content:"";position:absolute;inset:0;z-index:1;background:radial-gradient(circle at 83% 42%,rgba(18,232,145,.24),transparent 30%),linear-gradient(0deg,rgba(3,20,19,.89),transparent 52%);pointer-events:none}
.hero:after{content:"";position:absolute;inset:0;z-index:2;opacity:.30;background:linear-gradient(112deg,transparent 45%,rgba(134,255,221,.16) 45.2%,transparent 47%),repeating-linear-gradient(90deg,rgba(140,255,212,.05) 0 1px,transparent 1px 62px);pointer-events:none}
.top{position:absolute;top:56px;left:76px;right:75px;display:flex;align-items:center;justify-content:space-between;z-index:5}
.brand{width:337px;height:81px;display:flex;align-items:center;justify-content:center;background:linear-gradient(140deg,#fff,#e9f3eb);border:2px solid #fff;border-radius:14px;padding:14px 19px;box-shadow:inset 0 2px 3px rgba(255,255,255,.92),0 15px 30px rgba(0,0,0,.24)}
.brand img{display:block;width:100%;height:auto;max-height:53px;object-fit:contain}
.issue{font-weight:800;color:#f1fff6;font-size:20px;letter-spacing:2.4px;text-align:right;line-height:1.5;text-shadow:0 2px 6px #001}
.issue small{display:block;color:#a1e9cc;font-size:17px;letter-spacing:2px}
.hero-body{position:absolute;top:232px;left:77px;right:76px;z-index:5}
.kicker{display:flex;align-items:center;gap:16px;font-size:21px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#b0ffdd}
.kicker:before{content:"";width:43px;height:3px;background:#3aea9f;box-shadow:0 0 14px #1fc889}
.hero-title{font-size:91px;line-height:1.008;letter-spacing:-4.9px;font-weight:900;color:#fff;margin:27px 0 22px;text-shadow:0 5px 22px rgba(0,0,0,.29);max-width:926px}
.hero-title .accent{color:#abf8d4;text-shadow:0 0 26px rgba(36,240,155,.13)}
.hero-sub{font-size:29px;line-height:1.27;letter-spacing:-.35px;font-weight:500;max-width:850px;color:#f0fff7;text-shadow:0 2px 13px rgba(0,0,0,.38)}
.upper-pill{display:inline-block;margin-top:26px;border:1px solid rgba(161,250,204,.47);border-radius:40px;background:linear-gradient(120deg,rgba(6,101,72,.8),rgba(12,51,51,.57));padding:11px 19px;box-shadow:inset 0 1px 0 rgba(255,255,255,.25),0 9px 25px rgba(0,0,0,.17);font-size:18px;font-weight:800;letter-spacing:1.25px;color:#d5ffea}
.paper{position:absolute;top:697px;left:0;width:1080px;height:653px;z-index:10;border-radius:34px 34px 0 0;background:linear-gradient(162deg,#fbfffa 0%,#f0f7f2 57%,#eaf2ed 100%);box-shadow:0 -30px 64px rgba(0,16,12,.30),inset 0 1px 0 #fff;overflow:hidden}
.paper:before{content:"";position:absolute;top:-120px;left:55%;width:780px;height:550px;background:radial-gradient(circle,rgba(76,229,148,.13),transparent 64%);pointer-events:none}
.section-top{position:absolute;top:49px;left:77px;right:75px;display:flex;justify-content:space-between;align-items:center}
.eyebrow{font-size:19px;letter-spacing:2px;font-weight:900;color:#07875e}
.section-title{font-size:37px;line-height:1.06;letter-spacing:-1.1px;margin:8px 0 0;color:#0c352c;font-weight:900}
.sample{color:#5d746a;font-size:18px;letter-spacing:1px;font-weight:800;line-height:1.5;text-align:right}
.sample b{color:#066c51}
.divider{position:absolute;top:157px;left:76px;right:75px;height:2px;background:linear-gradient(90deg,#23bd81,#d8e5dc 54%)}
.documents{position:absolute;top:205px;left:70px;width:940px;height:300px;display:flex;gap:20px;perspective:1300px}
.document{position:relative;flex:1;min-width:0;overflow:hidden;border:2px solid #e3efe8;border-top-color:#fff;border-radius:24px;padding:27px 27px;background:linear-gradient(145deg,#fff 0%,#f7faf7 88%);box-shadow:inset 0 2px 0 rgba(255,255,255,.98),inset 0 -4px 15px rgba(14,50,30,.04),0 6px 0 #dae8df,0 22px 29px rgba(22,63,49,.16);transform:rotateX(1.7deg)}
.document:before{z-index:0;content:"";position:absolute;left:-50px;top:-42px;height:115px;width:110%;background:linear-gradient(150deg,rgba(255,255,255,.78),rgba(255,255,255,0));transform:rotate(-8deg);pointer-events:none}
.document > :not(.doc-status){position:relative;z-index:1}
.document .doc-status{z-index:2}
.document.focus{border-color:#24a779;background:linear-gradient(135deg,#fafffd,#def8e8);transform:translateY(-10px) rotateX(1.7deg);box-shadow:inset 0 2px 0 #fff,0 7px 0 #9fdbc0,0 23px 32px rgba(14,104,67,.25)}
.doc-top{display:flex;align-items:center;justify-content:space-between;color:#54776c;font-size:19px;font-weight:900;letter-spacing:1.1px;gap:6px}
.doc-type{font-size:30px;line-height:1.04;font-weight:900;letter-spacing:-.85px;color:#12352e;margin:28px 0 17px}
.doc-rule{height:2px;background:linear-gradient(90deg,#48c99b,#dbeae0)}
.doc-label{font-size:19px;color:#678c7c;font-weight:900;letter-spacing:1.15px;margin:17px 0 10px}
.doc-value{font-size:22px;line-height:1.25;color:#123c31;font-weight:800;border:2px solid #d4e7db;border-radius:12px;padding:14px;background:rgba(255,255,255,.86)}
.doc-status{position:absolute;bottom:20px;right:23px;font-size:16px;font-weight:900;letter-spacing:.7px;color:#086a50;background:#c8f6dd;border:1px solid #a0e6c5;padding:8px 13px;border-radius:24px}
.connector{position:absolute;left:457px;top:133px;width:37px;height:4px;background:#179a70;z-index:20;box-shadow:0 0 13px #82eec1}
.connector:after{content:"";position:absolute;right:-1px;top:-8px;border-left:16px solid #179a70;border-top:10px solid transparent;border-bottom:10px solid transparent}
.keypoint{position:absolute;left:76px;right:76px;top:528px;border-top:2px solid #d0dfd5;padding-top:20px;display:flex;justify-content:space-between;align-items:center;gap:17px}
.keypoint strong{font-size:21px;line-height:1.12;color:#153d30;max-width:735px}
.keypoint em{font-size:17px;font-style:normal;font-weight:900;letter-spacing:.5px;color:#067c54;white-space:nowrap}
.footer-note{position:absolute;left:77px;right:75px;bottom:30px;display:flex;align-items:center;justify-content:space-between;color:#466e60;font-size:19px;font-weight:900;letter-spacing:.65px}
.footer-line{display:inline-block;vertical-align:middle;width:28px;height:3px;background:#17b57b;margin-right:10px}
/* Subtle but consequential art-direction differences. */
.rate .photo{background-position:center 56%}
.rate .hero-body{top:210px}
.rate .hero-title{font-size:87px;margin:22px 0 17px}
.rate .upper-pill{margin-top:16px}
.access .photo{background-image:linear-gradient(91deg,rgba(3,18,19,.9),rgba(3,18,19,.55) 54%,rgba(2,23,24,.18)),url('__PHOTO__');background-position:center 43%}
.access .hero-title{font-size:102px;line-height:.98}
/* Accessorial uses a high-contrast deep-emerald lower panel rather than the
   light editorial paper used by the rate and credit layouts. */
.access .paper{background:linear-gradient(145deg,#0b3f34 0%,#052522 66%,#041c1e 100%);box-shadow:0 -26px 65px rgba(0,15,12,.38),inset 0 2px rgba(176,255,207,.24)}
.access .paper:before{background:radial-gradient(circle,rgba(37,225,153,.17),transparent 62%)}
.access .section-title{font-size:37px;color:#effff5}
.access .eyebrow{color:#a4ffcf}
.access .sample{color:#c7e6d8}
.access .sample b{color:#83e4b2}
.access .divider{background:linear-gradient(90deg,#28de9d,rgba(160,220,194,.18))}
.access .keypoint{border-top-color:rgba(145,209,174,.35)}
.access .keypoint strong{color:#f0fff7}
.access .keypoint em{color:#a8fed2}
.access .footer-note{color:#d7f5e7}
.credit .hero{height:758px}
.credit .photo{background-image:linear-gradient(90deg,rgba(1,13,16,.94) 0%,rgba(5,22,27,.63) 55%,rgba(6,40,38,.12) 100%),url('__PHOTO__');background-position:54% 54%;filter:saturate(1.24) contrast(1.06)}
.credit .hero-body{top:212px}
.credit .hero-title{font-size:85px;margin:20px 0 15px}
.credit .upper-pill{margin-top:18px}
.credit .documents{gap:18px}
.credit .document{padding:22px 21px}
.credit .document .doc-top{font-size:18px}
.credit .document .doc-type{font-size:26px;letter-spacing:-.5px;margin:28px 0 19px}
.credit .document .doc-label{font-size:17px}
.credit .document .doc-value{font-size:19px;padding:11px}
.credit .document > :not(.doc-status){position:relative;z-index:1}
.document .doc-status{z-index:2}
.document.focus{border-color:#24a779}
.credit .keypoint{top:530px}
.credit .documents{height:301px}
.credit .doc-status{bottom:22px;font-size:13px;padding:7px 11px}
.credit .connector{display:none}
/* Non-production art remains visibly marked and cannot be mistaken for approved creative. */
.preview{position:absolute;z-index:40;left:0;bottom:0;width:1080px;height:28px;background:#fff0cb;border-top:2px solid #bc8b27;text-align:center;color:#5b3901;font-size:16px;line-height:25px;font-weight:900;letter-spacing:1.1px}
'''


def _common_top(section: str, issue: str, subissue: str, headline: str,
                tagline: str, pill: str) -> str:
    return f'''<section class="hero"><div class="photo"></div>
<header class="top"><div class="brand"><img src="__LOGO__" alt="Original approved RETALLY wordmark" /></div>
<div class="issue">FIELD NOTES<small>{issue} · {subissue}</small></div></header>
<div class="hero-body"><div class="kicker">{section}</div>
<h1 class="hero-title">{headline}</h1><div class="hero-sub">{tagline}</div>
<div class="upper-pill">{pill}</div></div></section>'''


def _paper_start(eyebrow: str, title: str) -> str:
    return f'''<section class="paper"><div class="section-top"><div><div class="eyebrow">{eyebrow}</div>
<h2 class="section-title">{title}</h2></div><div class="sample">ILLUSTRATIVE ONLY<br><b>NO CUSTOMER DATA</b></div></div>
<div class="divider"></div><div class="documents">'''


def _card(prefix: str, status: str, title: str, label: str, value: str,
          highlight: bool = False, badge: str | None = None) -> str:
    klass = 'document focus' if highlight else 'document'
    extra = f'<div class="doc-status">{badge}</div>' if badge else ''
    return f'''<div class="{klass}"><div class="doc-top"><span>{prefix}</span><span>{status}</span></div>
<div class="doc-type">{title}</div><div class="doc-rule"></div><div class="doc-label">{label}</div>
<div class="doc-value">{value}</div>{extra}</div>'''


def _paper_end(note: str, action: str) -> str:
    return f'''</div><div class="keypoint"><strong>{note}</strong><em>{action}</em></div>
<div class="footer-note"><span><i class="footer-line"></i>FIND IT. PROVE IT. RECOVER IT.</span>
<span>RETALLYRECOVERY.COM</span></div></section>'''


def template_html(wordmark: str, photo: str, concept: str, preview: bool = False) -> str:
    """Return offline, data-URI-only HTML for one content-reviewed concept."""
    if concept not in CONCEPTS:
        raise ValueError(f'Unknown concept: {concept}')
    if concept == 'rate_versions':
        body = _common_top(
            'Freight billing intelligence', '01 / 03', 'RATE CONTROL',
            'ONE LOAD.<br><span class="accent">TWO RATE</span><br>SHEETS.',
            'The invoice can add up.<br>The wrong rate can still apply.',
            'THE CONTRACT DECIDES — NOT THE INVOICE')
        body += _paper_start('THE RATE AUTHORITY TEST', 'Which version governs?')
        body += _card('DOCUMENT 01', 'VERSION A', 'RATE SHEET A', 'EFFECTIVE PERIOD', 'Confirm dates')
        body += _card('DOCUMENT 02', 'VERSION B', 'RATE SHEET B', 'APPLICABILITY', 'Confirm governing terms', True, 'NOT VERIFIED')
        body += '<div class="connector"></div>'
        body += _paper_end('Check effective dates, amendments and prior credits.', 'SAVE THIS →')
        klass = 'rate'
    elif concept == 'accessorial_proof':
        body = _common_top(
            'Accessorial fee control', '02 / 03', 'SERVICE EVIDENCE',
            'A CHARGE<br>IS NOT <span class="accent">PROOF.</span>',
            'Billed for a liftgate?<br>First confirm the service and terms.',
            'EVIDENCE FIRST. RECOVERY SECOND.')
        body += _paper_start('THE SERVICE TEST', 'Match the charge to proof.')
        body += _card('INVOICE', 'LINE ITEM', 'LIFTGATE FEE', 'INVOICE STATUS', 'Charge appears')
        body += _card('SERVICE', 'SOURCE RECORD', 'PROOF OF SERVICE', 'DOCUMENTATION', 'Verify the service', True, 'EVIDENCE PENDING')
        body += '<div class="connector"></div>'
        body += _paper_end('Review the fee trigger, service record and credits.', 'CHECK IT →')
        klass = 'access'
    else:
        body = _common_top(
            'Duplicate charge investigation', '03 / 03', 'CREDIT CONTROL',
            'TWO BILLS.<br><span class="accent">ONE LOAD.</span><br>WHAT CHANGED?',
            'A correction can look like a duplicate.<br>Trace the complete billing chain.',
            'CHECK CREDITS BEFORE CALLING IT DOUBLE-PAID')
        body += _paper_start('THE BILLING CHAIN', 'Three records. One reconciliation.')
        body += _card('STEP 01', 'ISSUED', 'ORIGINAL BILL', 'MATCH THE LOAD', 'Find original')
        body += _card('STEP 02', 'CHECK', 'CREDIT MEMO', 'POSTED OR OPEN?', 'Confirm credit', True, 'RECONCILE')
        body += _card('STEP 03', 'REVISED', 'REPLACEMENT', 'PAYMENT STATUS', 'Verify payment')
        body += _paper_end('A second invoice is not automatically a second payment.', 'TRACE IT →')
        klass = 'credit'
    markup = f'''<!doctype html><html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>RETALLY illustrative freight-billing graphic</title><style>{CSS}</style></head>
<body><main class="artboard {klass}">{body}'''
    if preview:
        markup += '<div class="preview">DESIGN CONCEPT ONLY · NOT APPROVED FOR PUBLICATION</div>'
    markup += '</main></body></html>'
    markup = markup.replace('__LOGO__', wordmark).replace('__PHOTO__', photo)
    # Invariant: no remotely loaded CSS, fonts, scripts, tracking, or social APIs.
    if re.search(r'<script|https?://|<iframe|<form', markup, re.IGNORECASE):
        raise ValueError('External content or active HTML unexpectedly present')
    return markup


def _dom_qa(page) -> dict:
    """Check visible layout; reject clipped document text and missing approved logo."""
    return page.evaluate('''() => {
      const board=document.querySelector('.artboard'),b=board.getBoundingClientRect();
      const logo=document.querySelector('.brand img');
      const unsafe=[];
      for(const selector of ['.top','.hero-title','.hero-sub','.upper-pill','.section-top','.documents','.keypoint','.footer-note']) {
        const e=document.querySelector(selector),r=e.getBoundingClientRect();
        if(r.left<-2||r.right>1082||r.top<-2||r.bottom>1352) unsafe.push(selector+':outside-canvas');
      }
      for(const e of document.querySelectorAll('.document .doc-type,.document .doc-value,.document .doc-top,.keypoint strong')) {
        if(e.scrollWidth>e.clientWidth+3) unsafe.push(e.className+':horizontal-overflow');
      }
      const pill=document.querySelector('.upper-pill').getBoundingClientRect();
      const paper=document.querySelector('.paper').getBoundingClientRect();
      if(pill.bottom>paper.top-12) unsafe.push('.upper-pill:hidden-by-paper');
      const title=document.querySelector('.hero-title');
      return {canvas:[Math.round(b.width),Math.round(b.height)],logo:[logo.naturalWidth,logo.naturalHeight],
        document_cards:document.querySelectorAll('.document').length,
        title_font_px:parseFloat(getComputedStyle(title).fontSize),
        escaped_elements:unsafe,
        external_scripts:document.scripts.length,
        preview_banner:Boolean(document.querySelector('.preview'))};
    }''')


def run(output: Path, mode: str, concept: str, logo: Path, photo: Path,
        executable: str | None = None) -> dict:
    if mode not in ('production', 'preview'):
        raise ValueError('Unsupported mode')
    concepts = list(CONCEPTS) if concept in ('all', 'both') else [concept]
    if any(x not in CONCEPTS for x in concepts):
        raise ValueError('Unsupported concept')
    validate_logo(logo)  # Both modes MUST use authentic approved brand asset.
    wordmark_uri = read_image(logo)
    photo_uri = read_image(photo)
    from playwright.sync_api import sync_playwright
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as play:
        opts = {'headless': True}
        if executable:
            opts['executable_path'] = executable
        browser = play.chromium.launch(**opts)
        try:
            for name in concepts:
                page = browser.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
                requests = []
                page.on('request', lambda r: requests.append(r.url) if r.url.startswith(('https:', 'http:')) else None)
                page.set_content(template_html(wordmark_uri, photo_uri, name, mode == 'preview'), wait_until='load')
                page.evaluate('document.fonts.ready')
                qa = _dom_qa(page)
                if qa['canvas'] != [W,H] or qa['logo'] != [1619,257] or qa['escaped_elements'] or requests or qa['external_scripts']:
                    raise RuntimeError(f'Graphics QA failed: {name}: {qa} network={requests}')
                png = output / f'retally-{name}-{mode}-1080x1350.png'
                page.screenshot(path=str(png), animations='disabled', type='png')
                phone = browser.new_page(viewport={'width': PHONE_W, 'height': PHONE_H}, device_scale_factor=1)
                phone.set_content(template_html(wordmark_uri, photo_uri, name, mode=='preview'),wait_until='load')
                phone.add_style_tag(content=f'''html,body{{height:{PHONE_H}px;width:{PHONE_W}px;overflow:hidden}}
                .artboard{{transform:scale({PHONE_W/W});transform-origin:top left;}}''')
                small = output / f'retally-{name}-{mode}-390px.png'
                phone.screenshot(path=str(small), type='png', animations='disabled')
                for path, dims in [(png,(W,H)), (small,(PHONE_W,PHONE_H))]:
                    data = path.read_bytes()
                    if not data.startswith(b'\x89PNG\r\n\x1a\n') or struct.unpack('>II',data[16:24])!=dims:
                        raise RuntimeError(f'Wrong exported PNG geometry: {path}')
                results.append({
                    'concept':name,'image':str(png),'mobile_preview':str(small),
                    'image_sha256':sha256(png),'mobile_sha256':sha256(small),
                    'dimensions':[W,H],'mobile_dimensions':[PHONE_W,PHONE_H],
                    'qa':qa, 'preview_only':mode=='preview','human_approval_required':True,
                })
                page.close();phone.close()
        finally:
            browser.close()
    manifest = {
        'brand':'RETALLY','purpose':'offline draft-only graphics review',
        'mode':mode,'no_publication':True,'network_calls':False,'human_approval_required':True,
        'approved_wordmark_sha256':sha256(logo),
        'photo_sha256':sha256(photo),'photo_source':str(photo),
        'production_photo_rights_review_required':True,
        'assets':results,
    }
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    return manifest


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('production','preview'),default='production')
    p.add_argument('--concept',choices=CONCEPTS+('all','both'),default='all')
    p.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[4])
    p.add_argument('--logo',type=Path,help='Preview-only approved original wordmark, exact SHA must match')
    p.add_argument('--photo',type=Path,help='Preview-only local photo (nonproduction)',default=None)
    p.add_argument('--chromium',type=str,default=None)
    p.add_argument('--output-dir',type=Path,default=Path('/tmp/retally-creative-review'))
    args=p.parse_args()
    if args.mode=='production' and (args.logo or args.photo):
        p.error('Production forbids asset overrides')
    logo=args.logo if args.logo else args.repo_root/CANONICAL_WORDMARK
    photo=args.photo if args.photo else args.repo_root/CANONICAL_PHOTOS[CONCEPTS[0]]
    if args.mode=='preview' and not args.photo:
        p.error('Preview requires explicitly supplied locally reviewed photo')
    manifest=run(args.output_dir,args.mode,args.concept,logo,photo,args.chromium)
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    main()
