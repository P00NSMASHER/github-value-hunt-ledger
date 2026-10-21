"""Compose the RETALLY Group public pages on the existing allowlisted bundle."""
from html import escape
from pathlib import Path
import re
from urllib.parse import quote
import xml.etree.ElementTree as ET

from freight.site.group.catalog import BUSINESSES, DIVISIONS
from freight.site.rebase_public_urls import NEW_BASE
from freight.site.asset_integrity import assert_webp, AssetIntegrityError

SOURCE = Path(__file__).parent
ROUTES = tuple(b["slug"] for b in BUSINESSES) + ("contact",)
# index replaces the freight homepage; all other additions are explicit.
IMAGE_NAMES = tuple(f"{name}-{width}.webp" for name in ("research", "restaurant", "tools") for width in (768, 1536))
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
<meta name="site-release" content="retally-group-20261021"><meta name="design-release" content="retally-design-20261021"><meta name="robots" content="index,follow">
<link rel="canonical" href="{canonical}"><meta property="og:type" content="website"><meta property="og:site_name" content="RETALLY Group"><meta property="og:title" content="{escape(title, quote=True)} | RETALLY Group"><meta property="og:description" content="{escape(description, quote=True)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{NEW_BASE}assets/brand/retally-wordmark-approved.png"><meta property="og:image:alt" content="RETALLY"><meta name="twitter:card" content="summary">
<link rel="icon" href="/assets/brand/retally-emblem-approved.png" type="image/png"><link rel="preload" href="/assets/fonts/hanken-grotesk-latin.woff2" as="font" type="font/woff2" crossorigin><link rel="stylesheet" href="/group.css"><script src="/group.js" defer></script>
</head><body class="group-site">{header()}<main id="main">{body}</main>{footer()}</body></html>'''


def home():
    featured = ""
    photos = {
        "capturebrief": photograph("research", "Sunlit research desk with notebooks and a green folio"),
        "permitplate": photograph("restaurant", "Illustrative New York corner restaurant with green window frames"),
        "recovery": '<img class="editorial-photo" src="/assets/images/terminal-blue-hour-800.webp" width="800" height="500" alt="Freight terminal at blue hour" loading="lazy" decoding="async">',
    }
    captions = {"recovery": ("Freight audit & recovery", "Start with a free audit"), "capturebrief": ("Federal opportunity research", "$149 / one review"), "permitplate": ("NYC restaurant intelligence", "$79 / month")}
    for b in BUSINESSES[:3]:
        category, price = captions[b["slug"]]
        featured += f'''<a class="business-card featured-card" href="/{b['slug']}/"><div class="card-image">{photos[b['slug']]}</div><div class="card-copy"><p class="group-kicker">{category}</p><h3>{escape(b['name'])}</h3><p>{escape(b['summary'])}</p><div class="card-bottom"><span>{price}</span><span aria-hidden="true">↗</span></div></div></a>'''
    studio = ""
    for n, (division, title, desc) in enumerate(DIVISIONS[1:], 2):
        rows = ""
        for b in BUSINESSES[3:]:
            if b["division"] == division:
                rows += f'''<a class="portfolio-item" href="/{b['slug']}/"><span class="group-status">{escape(b['status'])}</span><h3>{escape(b['name'])}<span aria-hidden="true">↗</span></h3><p>{escape(b['summary'])}</p></a>'''
        studio += f'<section id="division-{n}" class="studio-column"><p class="group-kicker">{escape(division)}</p>{rows}</section>'
    body = f'''<section class="group-hero"><div class="group-wrap group-hero-grid"><div class="hero-intro"><p class="group-kicker">RECOVERY · RESEARCH · PRACTICAL TOOLS</p><h1>Find the value.<br><em>Move forward.</em></h1><p class="group-lead">Recover freight overcharges. Research your next opportunity. Put clearer evidence behind your business decisions.</p><div class="group-actions">{link("Find your service ↓", "#businesses", "group-button")}{link("Talk to RETALLY ↗", "/contact/", "group-text-link")}</div><p class="group-hero-note">Focused businesses. A clear place to start.</p></div><figure class="hero-photograph">{photograph("research", "A sunlit workspace with research notebooks, a green folio and a laptop", True)}<figcaption><span>THE RETALLY APPROACH</span><strong>Good work starts<br>with a closer look.</strong></figcaption></figure></div></section>
<div class="group-principles"><div class="group-wrap"><span>Evidence before claims</span><span>Human judgment where it matters</span><span>Clear scope from the start</span></div></div>
<section class="group-section group-wrap" id="businesses"><div class="section-title-row"><div><p class="group-kicker">AVAILABLE TODAY</p><h2>A useful next step.</h2></div><p>Three focused offers.<br>Choose the problem you need to solve.</p></div><div class="featured-grid" id="division-1">{featured}</div></section>
<section class="studio-section"><div class="group-wrap"><div class="section-title-row"><div><p class="group-kicker">MORE FROM RETALLY</p><h2>In the studio.</h2></div><p>Tools, previews and ideas taking shape.<br>Each page shows its current stage.</p></div><div class="studio-grid">{studio}</div></div></section>
<section class="group-approach" id="approach"><div class="group-wrap approach-layout"><figure class="approach-photo">{photograph("tools", "Ceramics, a candle and measuring tools on an oak maker’s workbench")}</figure><div><p class="group-kicker">HOW WE WORK</p><h2>Specific problems.<br><em>Thoughtful solutions.</em></h2><p>Understand the work. Examine the evidence. Make the next step clear.</p><p>That approach connects every RETALLY business, from freight recovery to focused research and practical tools. We explain the scope, the limits and what happens next before you commit.</p>{link("Find your starting point →", "/contact/", "group-text-link")}</div></div></section>'''
    return document("Recovery, intelligence & practical tools", "Explore RETALLY Group: recovery services, focused business research, spreadsheets, applications and public-data tools.", "", body)


def business_page(b):
    target = b.get("href", mail(b["name"]))
    features = "".join(f'<article><span class="feature-index">0{i}</span><h3>{escape(t)}</h3><p>{escape(d)}</p></article>' for i, (t, d) in enumerate(b["features"], 1))
    steps = "".join(f'<li><span>0{i}</span><p>{escape(s)}</p></li>' for i, s in enumerate(b["steps"], 1))
    resources = "".join(link(label + " ↗", href, "group-text-link") for label, href in b["links"])
    photo_names = {"capturebrief": ("research", "Research notebooks and a laptop in a sunlit workspace"), "permitplate": ("restaurant", "Illustrative New York corner restaurant"), "sheetharbor": ("tools", "Maker’s workbench with ceramics, a candle and measuring tools")}
    offer_photo = photograph(*photo_names[b["slug"]], eager=True) if b["slug"] in photo_names else ""
    sample = link(b["links"][0][0] + " ↗", b["links"][0][1], "group-text-link sample-link") if b["slug"] in {"capturebrief", "permitplate"} else ""
    pricing = f'<p class="group-price">{b["price"]}<span>{b["unit"]}</span></p>' if "price" in b else '<p class="group-card-stage">' + escape(b["status"]) + '</p>'
    action_note = "Opens the existing product site for the full offer and next step." if "href" in b else "Opens an email draft. Nothing is sent automatically."
    body = f'''<section class="business-hero"><div class="group-wrap"><nav class="group-breadcrumb" aria-label="Breadcrumb"><a href="/">RETALLY Group</a><span aria-hidden="true">/</span><span>{escape(b['name'])}</span></nav><div class="business-hero-grid"><div><p class="group-kicker">{escape(b['division'])} / {escape(b['name'])}</p><h1>{escape(b['headline'])}</h1><p class="group-lead">{escape(b['summary'])}</p><p class="business-audience">For {escape(b['audience'][0].lower() + b['audience'][1:])}.</p></div><aside class="business-offer">{offer_photo}<div class="offer-content"><span class="group-status">{escape(b['status'])}</span><h2>{escape(b['name'])}</h2>{pricing}{link(b['cta'] + " ↗", target, "group-button")}{sample}<p class="group-small">{action_note}</p></div></aside></div></div></section>
<section class="group-section group-wrap"><div class="group-section-heading"><p class="group-kicker">THE FOCUS</p><h2>Built around your decision.</h2><p>{escape(b['detail'])}</p></div><div class="group-features">{features}</div></section>
<section class="group-how"><div class="group-wrap group-two-col"><div><p class="group-kicker">YOUR NEXT STEP</p><h2>A clear way<br><em>to begin.</em></h2></div><ol class="group-steps">{steps}</ol></div></section>
<section class="group-section group-wrap"><div class="group-two-col"><div><p class="group-kicker">SCOPE &amp; AVAILABILITY</p><h2>Know what to expect.</h2></div><div><p class="group-boundary">{escape(b['boundary'])}</p><div class="group-resource-links">{resources}</div><p class="group-small">Questions about {escape(b['name'])}? {link("Email RETALLY", mail(b['name']))}. Include the business name and a brief, non-sensitive description of what you need.</p></div></div></section>'''
    return document(b["name"], b["summary"], b["slug"] + "/", body)


def contact_page():
    options = '<option value="General enquiry">Help me find the right business</option>' + "".join(f'<option value="{escape(b["name"], quote=True)}">{escape(b["name"])}</option>' for b in BUSINESSES)
    draft = link("Email RETALLY ↗", mail("General enquiry"), "group-text-link").replace('<a ', '<a id="enquiry-draft" ', 1)
    body = f'''<section class="contact-hero group-wrap"><div class="contact-layout"><div><p class="group-kicker">GET IN TOUCH</p><h1>Start with<br><em>what you need.</em></h1><p class="group-lead">Tell us what you’re working on. We’ll help you find the right RETALLY business.</p><div class="contact-direct"><p class="group-kicker">PREFER A DIRECT CONVERSATION?</p>{link("jay@retallyrecovery.com", mail("General enquiry"), "group-text-link")}<p>For freight invoices, use the dedicated audit request.</p>{link("Start a free freight audit →", "/recovery/#start-audit", "group-text-link")}</div><p class="contact-note">A brief, non-sensitive description is enough to begin. We’ll agree on a suitable way to share documents if needed.</p></div><div class="enquiry-card"><p class="group-kicker">LET’S FIND YOUR STARTING POINT</p><h2>A little context helps.</h2><form id="group-enquiry" hidden><label for="enquiry-business">Which business interests you?</label><select id="enquiry-business" name="business">{options}</select><label for="enquiry-message">What would you like help with?</label><textarea id="enquiry-message" name="message" rows="5" maxlength="1800" placeholder="A sentence or two about your business and what you need." aria-describedby="enquiry-hint"></textarea><p id="enquiry-hint" class="group-small">Please leave out passwords, confidential documents and personal customer information.</p><button class="group-button" type="submit">Open email draft <span aria-hidden="true">↗</span></button><button class="copy-draft group-text-link" type="button" id="copy-enquiry">Copy message</button><p id="enquiry-status" role="status" class="group-small">This prepares a draft in your email app. Nothing is sent from this page.</p></form><div class="enquiry-fallback">{draft}<noscript><p>Include the business name and a short description of what you need.</p></noscript></div></div></div></section>'''
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

