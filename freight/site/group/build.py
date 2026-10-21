"""Compose the RETALLY Group public pages on the existing allowlisted bundle."""
from html import escape
from pathlib import Path
import re
from urllib.parse import quote
import xml.etree.ElementTree as ET

from freight.site.group.catalog import BUSINESSES, DIVISIONS
from freight.site.rebase_public_urls import NEW_BASE

SOURCE = Path(__file__).parent
ROUTES = tuple(b["slug"] for b in BUSINESSES) + ("contact",)
# index replaces the freight homepage; all other additions are explicit.
ADDED_FILES = tuple(f"{slug}/index.html" for slug in ROUTES) + ("group.css", "group.js")


def mail(name):
    return "mailto:jay@retallyrecovery.com?subject=" + quote("RETALLY enquiry — " + name)


def link(label, href, cls=""):
    tag = f'<a class="{escape(cls)}" href="{escape(href, quote=True)}">{escape(label)}</a>'
    return "<!--email_off-->" + tag + "<!--/email_off-->" if href.startswith("mailto:") else tag


def header():
    choices = "".join(link(b["name"], "/" + b["slug"] + "/") for b in BUSINESSES)
    return f'''<a class="group-skip" href="#main">Skip to content</a>
<header class="group-header"><div class="group-wrap group-nav">
<a class="group-brand" href="/" aria-label="RETALLY Group home"><img src="/assets/brand/retally-wordmark-approved.png" width="1619" height="257" alt="RETALLY"><span>GROUP</span></a>
<nav aria-label="Main navigation"><details class="business-menu"><summary>Our businesses <span aria-hidden="true">⌄</span></summary><div class="business-menu-panel">{choices}</div></details><a class="group-about" href="/#approach">Our approach</a><a class="group-contact" href="/contact/">Get in touch <span aria-hidden="true">↗</span></a></nav>
</div></header>'''


def footer():
    cols = "".join(f'<div><h3>{escape(d[0])}</h3>' + "".join(link(b["name"], "/"+b["slug"]+"/") for b in BUSINESSES if b["division"] == d[0]) + '</div>' for d in DIVISIONS)
    return f'''<footer class="group-footer"><div class="group-wrap"><div class="group-footer-top"><div><p class="group-kicker">RETALLY GROUP</p><h2>Useful work.<br><em>Clear evidence.</em></h2></div><div><p>Start with a business problem.<br>We’ll help you find the right place to begin.</p>{link("Find your business contact →", "/contact/", "group-light-link")}</div></div><nav class="group-footer-links" aria-label="Business directory">{cols}</nav><div class="group-footer-bottom"><span>© 2026 RETALLY Group</span><span>Each offer has its own scope, availability and terms.</span>{link("jay@retallyrecovery.com", mail("General enquiry"))}</div></div></footer>'''


def document(title, description, route, body):
    canonical = NEW_BASE + route
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} | RETALLY Group</title><meta name="description" content="{escape(description, quote=True)}">
<meta name="theme-color" content="#06392f"><meta name="referrer" content="no-referrer">
<meta name="site-release" content="retally-group-20261021"><meta name="robots" content="index,follow">
<link rel="canonical" href="{canonical}"><meta property="og:type" content="website"><meta property="og:site_name" content="RETALLY Group"><meta property="og:title" content="{escape(title, quote=True)} | RETALLY Group"><meta property="og:description" content="{escape(description, quote=True)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{NEW_BASE}assets/brand/retally-wordmark-approved.png"><meta property="og:image:alt" content="RETALLY"><meta name="twitter:card" content="summary">
<link rel="icon" href="/assets/brand/retally-emblem-approved.png" type="image/png"><link rel="preload" href="/assets/fonts/hanken-grotesk-latin.woff2" as="font" type="font/woff2" crossorigin><link rel="stylesheet" href="/group.css"><script src="/group.js" defer></script>
</head><body class="group-site">{header()}<main id="main">{body}</main>{footer()}</body></html>'''


def home():
    directory = ""
    for n, (division, title, desc) in enumerate(DIVISIONS, 1):
        cards = ""
        for b in BUSINESSES:
            if b["division"] != division:
                continue
            cards += f'''<a class="business-card" href="/{b['slug']}/"><span class="group-status">{escape(b['status'])}</span><h3>{escape(b['name'])}</h3><p>{escape(b['summary'])}</p><span class="card-bottom">Explore {escape(b['name'])} <span aria-hidden="true">↗</span></span></a>'''
        directory += f'''<section class="division-section" id="division-{n}" aria-labelledby="division-title-{n}"><div class="division-intro"><p class="group-kicker">0{n} / {escape(division)}</p><h2 id="division-title-{n}">{title}</h2><p>{desc}</p></div><div class="business-grid">{cards}</div></section>'''
    body = f'''<section class="group-hero"><div class="group-wrap group-hero-grid"><div><p class="group-kicker">A FAMILY OF FOCUSED BUSINESSES</p><h1>Find the value.<br><em>Move forward.</em></h1><p class="group-lead">Recovery, research and practical tools.<br>Explore the businesses bringing clearer evidence to everyday decisions.</p><div class="group-actions">{link("Explore our businesses ↓", "#businesses", "group-button")}{link("Talk to RETALLY ↗", "/contact/", "group-text-link")}</div><p class="group-hero-note">One group. Each business with a purpose of its own.</p></div><aside class="group-map" aria-label="RETALLY business areas"><div class="group-map-head"><span>THE RETALLY GROUP</span><img src="/assets/brand/retally-emblem-approved.png" alt="" width="74" height="74"></div><p class="group-map-title">Good decisions<br>start with <em>clarity.</em></p><a href="#division-1"><span>01</span><strong>Recovery</strong><span>↗</span></a><a href="#division-2"><span>02</span><strong>Intelligence</strong><span>↗</span></a><a href="#division-3"><span>03</span><strong>Tools &amp; Data</strong><span>↗</span></a><a href="#division-4"><span>04</span><strong>Ventures</strong><span>↗</span></a></aside></div></section>
<div class="group-principles"><div class="group-wrap"><span>Evidence before claims</span><span>Human judgment where it matters</span><span>Clear scope from the start</span></div></div>
<div class="group-wrap" id="businesses"><div class="directory-heading"><p class="group-kicker">OUR BUSINESSES</p><p>Find the right fit.<br><span>Every business has its own page, scope and next step.</span></p></div>{directory}</div>
<section class="group-approach" id="approach"><div class="group-wrap group-two-col"><div><p class="group-kicker">HOW WE WORK</p><h2>Specific problems.<br><em>Thoughtful solutions.</em></h2></div><div class="approach-copy"><p>RETALLY brings together businesses with a common approach: understand the work, examine the evidence and make the next step clear.</p><p>Some offers are available today. Others are previews, demonstrations or research concepts. You can see the current stage on each business page before deciding whether to enquire.</p>{link("Find your starting point →", "/contact/", "group-text-link")}</div></div></section>'''
    return document("Recovery, intelligence & practical tools", "Explore RETALLY Group: recovery services, focused business research, spreadsheets, applications and public-data tools.", "", body)


def business_page(b):
    target = b.get("href", mail(b["name"]))
    features = "".join(f'<article><span class="feature-index">0{i}</span><h3>{escape(t)}</h3><p>{escape(d)}</p></article>' for i, (t, d) in enumerate(b["features"], 1))
    steps = "".join(f'<li><span>0{i}</span><p>{escape(s)}</p></li>' for i, s in enumerate(b["steps"], 1))
    resources = "".join(link(label + " ↗", href, "group-text-link") for label, href in b["links"])
    pricing = f'<p class="group-price">{b["price"]}<span>{b["unit"]}</span></p>' if "price" in b else '<p class="group-card-stage">' + escape(b["status"]) + '</p>'
    action_note = "Opens the existing product site for the full offer and next step." if "href" in b else "Opens an email draft. Nothing is sent automatically."
    body = f'''<section class="business-hero"><div class="group-wrap"><nav class="group-breadcrumb" aria-label="Breadcrumb"><a href="/">RETALLY Group</a><span aria-hidden="true">/</span><span>{escape(b['name'])}</span></nav><div class="business-hero-grid"><div><p class="group-kicker">{escape(b['division'])} / {escape(b['name'])}</p><h1>{escape(b['headline'])}</h1><p class="group-lead">{escape(b['summary'])}</p><p class="business-audience">For {escape(b['audience'][0].lower() + b['audience'][1:])}.</p></div><aside class="business-offer"><span class="group-status">{escape(b['status'])}</span><h2>{escape(b['name'])}</h2>{pricing}{link(b['cta'] + " ↗", target, "group-button")}<p class="group-small">{action_note}</p></aside></div></div></section>
<section class="group-section group-wrap"><div class="group-section-heading"><p class="group-kicker">THE FOCUS</p><h2>{escape(b['detail'])}</h2></div><div class="group-features">{features}</div></section>
<section class="group-how"><div class="group-wrap group-two-col"><div><p class="group-kicker">YOUR NEXT STEP</p><h2>A clear way<br><em>to begin.</em></h2></div><ol class="group-steps">{steps}</ol></div></section>
<section class="group-section group-wrap"><div class="group-two-col"><div><p class="group-kicker">SCOPE &amp; AVAILABILITY</p><h2>Know what to expect.</h2></div><div><p class="group-boundary">{escape(b['boundary'])}</p><div class="group-resource-links">{resources}</div><p class="group-small">Questions about {escape(b['name'])}? {link("Email RETALLY", mail(b['name']))}. Include the business name and a brief, non-sensitive description of what you need.</p></div></div></section>'''
    return document(b["name"], b["summary"], b["slug"] + "/", body)


def contact_page():
    contacts = "".join(f'<div class="contact-row"><div><h2>{escape(b["name"])}</h2><p>{escape(b["summary"])}</p></div>{link("Enquire →", mail(b["name"]), "group-text-link")}</div>' for b in BUSINESSES)
    body = f'''<section class="contact-hero group-wrap"><p class="group-kicker">GET IN TOUCH</p><h1>Start with<br><em>what you need.</em></h1><p class="group-lead">Choose a business below, or tell us about the problem you’re working on.</p>{link("Email RETALLY ↗", mail("General enquiry"), "group-button")}<p class="group-small">jay@retallyrecovery.com · Opens your email application. Nothing is sent automatically.</p><p class="contact-note">Keep your first message brief. Please do not include passwords, financial records, patient information, confidential proposals or customer files. We’ll agree on a suitable way to share documents if needed.</p></section><section class="group-wrap contact-directory" aria-label="Contact a business">{contacts}</section>'''
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
    sitemap = bundle / "sitemap.xml"
    tree = ET.parse(sitemap)
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    for route in ROUTES:
        url = ET.SubElement(tree.getroot(), "{" + ns + "}url")
        ET.SubElement(url, "{" + ns + "}loc").text = NEW_BASE + route + "/"
    tree.write(sitemap, encoding="utf-8", xml_declaration=True)

