"""Compose the RETALLY Group public pages on the existing allowlisted bundle."""
from html import escape
from hashlib import sha256
from pathlib import Path
import re
from urllib.parse import quote
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

from freight.site.group.catalog import BUSINESSES, DIVISIONS
from freight.site.group.home_page import render_home
from freight.site.group.business_pages import render_business
from freight.site.rebase_public_urls import NEW_BASE
from freight.site.asset_integrity import assert_webp, AssetIntegrityError

SOURCE = Path(__file__).parent
ROUTES = tuple(b["slug"] for b in BUSINESSES) + ("contact",)
# index replaces the freight homepage; all other additions are explicit.
IMAGE_NAMES = tuple(f"{name}-{width}.webp" for name in ("research", "restaurant", "tools", "hero", "digital") for width in (768, 1536))
ADDED_FILES = tuple(f"{slug}/index.html" for slug in ROUTES) + ("group.css", "group.js") + tuple("assets/group/" + name for name in IMAGE_NAMES)


def photograph(name, alt, eager=False):
    return f'<img class="editorial-photo" src="/assets/group/{name}-1536.webp" srcset="/assets/group/{name}-768.webp 768w, /assets/group/{name}-1536.webp 1536w" sizes="(max-width: 760px) calc(100vw - 40px), 600px" width="1536" height="1024" alt="{escape(alt, quote=True)}" loading="{"eager" if eager else "lazy"}" decoding="async"{chr(32) + "fetchpriority=high" if eager else ""}>'


def mail(name):
    return "mailto:jay@retallyrecovery.com?subject=" + quote("RETALLY enquiry — " + name)


def link(label, href, cls=""):
    tag = f'<a class="{escape(cls)}" href="{escape(href, quote=True)}">{escape(label)}</a>'
    return "<!--email_off-->" + tag + "<!--/email_off-->" if href.startswith("mailto:") else tag


def header():
    choices = "".join('<div class="menu-division"><p>' + escape(division) + '</p>' + "".join(link(b["name"], "/" + b["slug"] + "/") for b in BUSINESSES if b["division"] == division) + '</div>' for division, _, _ in DIVISIONS)
    return f'''<a class="group-skip" href="#main">Skip to content</a>
<header class="group-header"><div class="group-wrap group-nav">
<a class="group-brand" href="/" aria-label="RETALLY Group home"><img src="/assets/brand/retally-wordmark-approved.png" width="1619" height="257" alt="RETALLY"><span>GROUP</span></a>
<nav aria-label="Main navigation"><details class="business-menu"><summary>Our businesses <span aria-hidden="true">⌄</span></summary><div class="business-menu-panel">{choices}</div></details><a class="group-about" href="/#approach">Our approach</a><a class="group-contact" href="/contact/">Get in touch <span aria-hidden="true">↗</span></a></nav>
</div></header>'''


def footer():
    cols = "".join(f'<div><h3>{escape(d[0])}</h3>' + "".join(link(b["name"], "/"+b["slug"]+"/") for b in BUSINESSES if b["division"] == d[0]) + '</div>' for d in DIVISIONS)
    return f'''<footer class="group-footer"><div class="group-wrap"><div class="group-footer-top"><div><p class="group-kicker">RETALLY GROUP</p><h2>Useful work.<br><em>Clear evidence.</em></h2></div><div><p>Start with a business problem.<br>We’ll help you find the right place to begin.</p>{link("Find your business contact →", "/contact/", "group-light-link")}</div></div><nav class="group-footer-links" aria-label="Business directory">{cols}</nav><nav class="group-trust-links" aria-label="Company information"><a href="/#approach">Our approach</a><a href="/about.html">About Recovery</a><a href="/trust.html">Recovery Trust Center</a><a href="/privacy.html">Privacy</a><span>Editorial images are illustrative.</span></nav><div class="group-footer-bottom"><span>© 2026 RETALLY Group</span><span>Each offer has its own scope, availability and terms.</span>{link("jay@retallyrecovery.com", mail("General enquiry"))}</div></div></footer>'''


def document(title, description, route, body):
    canonical = NEW_BASE + route
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} | RETALLY Group</title><meta name="description" content="{escape(description, quote=True)}">
<meta name="theme-color" content="#06392f"><meta name="referrer" content="no-referrer">
<meta name="site-release" content="retally-group-20261021"><meta name="design-release" content="retally-freight-benchmark-20261021"><meta name="robots" content="index,follow">
<link rel="canonical" href="{canonical}"><meta property="og:type" content="website"><meta property="og:site_name" content="RETALLY Group"><meta property="og:title" content="{escape(title, quote=True)} | RETALLY Group"><meta property="og:description" content="{escape(description, quote=True)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{NEW_BASE}assets/brand/retally-wordmark-approved.png"><meta property="og:image:alt" content="RETALLY"><meta name="twitter:card" content="summary">
<link rel="icon" href="/assets/brand/retally-emblem-approved.png" type="image/png"><link rel="preload" href="/assets/fonts/hanken-grotesk-latin.woff2" as="font" type="font/woff2" crossorigin><link rel="stylesheet" href="/group.css"><script src="/group.js" defer></script>
</head><body class="group-site">{header()}<main id="main">{body}</main>{footer()}</body></html>'''


def home():
    return document("Recovery, intelligence & practical tools", "Explore RETALLY Group: recovery services, focused business research, spreadsheets, applications and public-data tools.", "", render_home(BUSINESSES, photograph, link))


def business_page(b):
    return document(b["name"], b["summary"], b["slug"] + "/", render_business(b, photograph, link, mail))


def contact_page():
    options = '<option value="general">Help me find the right business</option>' + "".join(f'<option value="{escape(b["slug"], quote=True)}">{escape(b["name"])}</option>' for b in BUSINESSES)
    draft = link("Open an email draft ↗", mail("General enquiry"), "group-text-link").replace('<a ', '<a id="enquiry-draft" ', 1)
    body = f'''<section class="contact-hero group-wrap"><div class="contact-layout"><div><p class="group-kicker">GET IN TOUCH</p><h1>Start with<br><em>what you need.</em></h1><p class="group-lead">Tell us what you’re working on. We’ll help you find the right RETALLY business.</p><div class="contact-direct"><p class="group-kicker">PREFER A DIRECT CONVERSATION?</p>{link("jay@retallyrecovery.com", mail("General enquiry"), "group-text-link")}<p>For freight invoices, use the dedicated audit request.</p>{link("Start a free freight audit →", "/recovery/#start-audit", "group-text-link")}</div><p class="contact-note">A brief, non-sensitive description is enough to begin. Do not send documents, passwords, payment details, patient information or confidential customer records. We’ll agree on a suitable way to share documents if needed.</p></div><div class="enquiry-card"><p class="group-kicker">LET’S FIND YOUR STARTING POINT</p><h2>A little context helps.</h2><form id="group-enquiry" hidden>
<fieldset id="enquiry-fields"><label for="enquiry-business">Which business interests you?</label><select id="enquiry-business" name="business">{options}</select>
<label for="enquiry-name">Your name</label><input id="enquiry-name" name="fullName" autocomplete="name" maxlength="100" required>
<label for="enquiry-email">Work email</label><input id="enquiry-email" name="workEmail" type="email" autocomplete="email" maxlength="160" required>
<label for="enquiry-company">Company <span class="enquiry-optional">(optional)</span></label><input id="enquiry-company" name="companyName" autocomplete="organization" maxlength="140">
<label for="enquiry-message">What would you like help with?</label><textarea id="enquiry-message" name="message" rows="5" maxlength="800" required placeholder="A sentence or two about your business and what you need." aria-describedby="enquiry-hint"></textarea><p id="enquiry-hint" class="group-small">Up to 800 characters. Please leave out sensitive information and credentials. This form does not accept documents.</p>
<div class="enquiry-honeypot" hidden><label for="enquiry-website">Leave this field empty</label><input id="enquiry-website" name="website" tabindex="-1" autocomplete="off"></div>
<label class="enquiry-consent" for="enquiry-consent"><input id="enquiry-consent" name="consent" type="checkbox" required><span>I agree that RETALLY may privately store these details and contact me about this enquiry.</span></label>
<div id="enquiry-turnstile" aria-label="Security verification"></div><button id="send-enquiry" class="group-button" type="submit" disabled>Send enquiry <span aria-hidden="true">↗</span></button></fieldset>
<p id="enquiry-status" role="status" aria-live="polite" class="group-small">Checking secure intake availability. Nothing has been sent.</p><p class="group-small">A reference confirms that your enquiry was saved. It does not confirm email delivery, a purchase, accepted work or a response time.</p>
<div class="enquiry-alternatives"><p class="group-small">You can also review and send a draft in your email app.</p>{draft}<button class="copy-draft group-text-link" type="button" id="copy-enquiry">Copy enquiry</button><p id="enquiry-copy-status" role="status" class="group-small"></p><textarea id="enquiry-copy-text" rows="7" readonly hidden aria-label="Enquiry text to copy"></textarea></div></form><noscript><p>The secure form needs JavaScript. {link("Email RETALLY ↗", mail("General enquiry"), "group-text-link")} with the business name and a short, non-sensitive description of what you need.</p></noscript></div></div></section>'''
    return document("Contact", "Find the right RETALLY business and start a conversation about your needs.", "contact/", body)


def _move_freight_home(bundle):
    html = (bundle / "index.html").read_text(encoding="utf-8")
    # The existing form, scripts and CSP remain intact. Resolve only relative
    # URLs against their original root; fragment-only links remain on this page.
    def root_attribute(match):
        key, value = match.groups()
        if value.startswith(("/", "#", "https:", "http:", "mailto:", "data:")):
            return match.group(0)
        return f'{key}="/{value.removeprefix("./")}"'
    html = re.sub(r'\b(href|src)="([^"]+)"', root_attribute, html)
    for key in ("srcset", "imagesrcset"):
        html = re.sub(rf'{key}="([^"]+)"', lambda m: key + '="' + ", ".join("/" + item.strip() if not item.strip().startswith(("/", "http")) else item.strip() for item in m[1].split(",")) + '"', html)
    html = html.replace(f'<link rel="canonical" href="{NEW_BASE}">', f'<link rel="canonical" href="{NEW_BASE}recovery/">')
    html = html.replace(f'<meta property="og:url" content="{NEW_BASE}">', f'<meta property="og:url" content="{NEW_BASE}recovery/">')
    html = html.replace(f'<meta itemprop="url" content="{NEW_BASE}">', f'<meta itemprop="url" content="{NEW_BASE}recovery/">')
    html = html.replace('</head>', '<link rel="stylesheet" href="/group.css"></head>')
    html = html.replace('class="home-simple"', 'class="home-simple group-recovery"', 1)
    html = html.replace('<div class="wrap" id="contactStatus">', '<div id="contact-pending"></div><div class="wrap" id="contactStatus">', 1)
    html = html.replace('<header class="site-header">', '<div class="portfolio-bar"><a href="/">← RETALLY Group</a><span>RETALLY Recovery</span><a href="/contact/">Other business enquiries →</a></div><header class="site-header">', 1)
    (bundle / "recovery" / "index.html").write_text(html, encoding="utf-8")


def build_group(bundle):
    for route in ROUTES:
        path = bundle / route
        if path.exists():
            raise ValueError(f"Group route collides with existing public output: {route}")
        path.mkdir()
    _move_freight_home(bundle)
    (bundle / "index.html").write_text(home(), encoding="utf-8")
    for b in BUSINESSES:
        if b["slug"] != "recovery":
            (bundle / b["slug"] / "index.html").write_text(business_page(b), encoding="utf-8")
    (bundle / "contact" / "index.html").write_text(contact_page(), encoding="utf-8")
    for filename in ("group.css", "group.js"):
        (bundle / filename).write_bytes((SOURCE / filename).read_bytes())
    assets = bundle / "assets" / "group"
    assets.mkdir()
    found = {p.name for p in (SOURCE / "assets").iterdir()}
    if found != set(IMAGE_NAMES):
        raise AssetIntegrityError("Group imagery differs from the reviewed allowlist")
    for filename in IMAGE_NAMES:
        source = SOURCE / "assets" / filename
        if source.is_symlink() or not source.is_file():
            raise AssetIntegrityError("Unsafe group image")
        data = source.read_bytes()
        width = int(filename.rsplit("-", 1)[1].split(".")[0])
        if len(data) > 450_000 or assert_webp(data, filename, width, width * 2 // 3) != (width, width * 2 // 3):
            raise AssetIntegrityError("Group image exceeds its size or geometry budget")
        (assets / filename).write_bytes(data)
    sitemap = bundle / "sitemap.xml"
    tree = ET.parse(sitemap)
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    for route in ROUTES:
        url = ET.SubElement(tree.getroot(), "{" + ns + "}url")
        ET.SubElement(url, "{" + ns + "}loc").text = NEW_BASE + route + "/"
    tree.write(sitemap, encoding="utf-8", xml_declaration=True)
    _version_design_assets(bundle)


def _version_design_assets(bundle):
    """Returning visitors must receive the assets matching the current HTML."""
    revisions = {
        name: sha256((bundle / name).read_bytes()).hexdigest()[:16]
        for name in ("group.css", "group.js", "foundry.css", "site.js")
    }

    def version(match):
        key, reference = match.groups()
        url = urlsplit(reference)
        name = url.path.removeprefix("/")
        if url.scheme or url.netloc or name not in revisions:
            return match.group(0)
        return f'{key}="{url.path}?v={revisions[name]}"'

    for page in bundle.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        page.write_text(re.sub(r'\b(href|src)="([^"]+)"', version, html), encoding="utf-8")


