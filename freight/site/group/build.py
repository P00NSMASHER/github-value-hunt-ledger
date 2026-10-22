"""Restore the freight homepage and retain deliberate legacy-route handoffs.

The four companies publish separately. This step adds no group navigation,
marketing pages or design assets to the freight homepage.
"""
from hashlib import sha256
from html import escape, unescape
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from freight.site.rebase_public_urls import NEW_BASE

GROUP_BASE = "https://group.retallyrecovery.com/"
RECOVERYWORKS_BASE = "https://recoveryworks.retallyrecovery.com/"

# Compatibility and archive pages are not indexable sitemap destinations.
ROUTES = ()
SUCCESSORS = {
    "recovery": ("RETALLY Freight Recovery", NEW_BASE),
    "capturebrief": ("CaptureBrief", "https://capturebrief.retallyrecovery.com/"),
    "permitplate": ("PermitPlate", "https://permitplate.retallyrecovery.com/"),
    "contact": ("RETALLY Group contact", GROUP_BASE + "#contact"),
    "recoveryos": ("RETALLY RecoveryWorks", RECOVERYWORKS_BASE),
}
ARCHIVES = {
    "rehabsignal": "RehabSignal",
    "sheetharbor": "SheetHarbor",
    "app-factory": "App Factory",
    "data-services": "RETALLY Data Services",
    "scopesignal": "ScopeSignal",
    "contractor-quote-recovery": "Contractor Quote Recovery",
    "resonance": "Resonance",
    "market-surveillance": "Market Surveillance Research",
}
# RecoveryOS already belongs to the existing, independently allowlisted bundle.
LEGACY_ROUTES = tuple(route for route in SUCCESSORS if route != "recoveryos") + tuple(ARCHIVES)
ADDED_FILES = tuple(f"{route}/index.html" for route in LEGACY_ROUTES) + ("_redirects",)
DESIGN_ASSETS = ("foundry.css", "site.js")
GROUP_FOOTER_LINK = f'<a href="{GROUP_BASE}">Part of RETALLY Group</a>'
CONTACT_ANCHOR = '<div id="contact-pending"></div>'


def _restore_freight_home(html):
    """Keep the existing freight composition, including its verified intake."""
    if 'class="home-simple"' not in html or 'id="auditForm"' not in html:
        raise ValueError("Expected the original freight homepage before route migration")
    if 'id="contact-pending"' not in html:
        boundary = '<div class="wrap" id="contactStatus">'
        if html.count(boundary) != 1:
            raise ValueError("Unexpected freight contact-status boundary")
        html = html.replace(boundary, CONTACT_ANCHOR + boundary, 1)
    footer = re.compile(r'(<div class="wrap footer-bottom">)(.*?)(</div>)', re.S)
    if len(footer.findall(html)) != 1:
        raise ValueError("Unexpected freight footer boundary")
    if GROUP_FOOTER_LINK not in html:
        html = footer.sub(lambda match: match[1] + match[2] + GROUP_FOOTER_LINK + match[3], html, count=1)
    return html


def _freight_compatibility_page(html):
    """Keep old /recovery/#anchors usable in previews without HTTP redirects.

    Production uses the explicit redirect below. Canonical/structured URLs keep
    pointing to the restored root; the fallback receives no group decoration.
    """
    def root_attribute(match):
        key, value = match.groups()
        if value.startswith(("/", "#")) or urlsplit(value).scheme:
            return match.group(0)
        return f'{key}="/{value.removeprefix("./")}"'

    html = re.sub(r'\b(href|src)="([^"]+)"', root_attribute, html)
    for key in ("srcset", "imagesrcset"):
        html = re.sub(
            rf'{key}="([^"]+)"',
            lambda match: key + '="' + ", ".join(
                item.strip() if item.strip().startswith(("/", "https:", "http:", "data:"))
                else "/" + item.strip().removeprefix("./")
                for item in match[1].split(",")
            ) + '"',
            html,
        )
    return re.sub(r'(<meta name="robots" content=")[^"]+("\s*>)',
                  r'\g<1>noindex,follow\2', html, count=1)


def _notice_page(title, canonical, label, message, destination, link_text):
    """A local fallback or archive notice, never a replacement commercial offer."""
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} | RETALLY</title><meta name="robots" content="noindex,follow"><meta name="referrer" content="no-referrer">
<link rel="canonical" href="{escape(canonical, quote=True)}"><link rel="icon" href="/assets/brand/retally-emblem-approved.png" type="image/png">
<link rel="stylesheet" href="/site.css"><link rel="stylesheet" href="/foundry.css">
</head><body class="home-simple"><a class="skip" href="#main">Skip to content</a>
<main id="main" class="wrap"><section class="section"><p class="eyebrow">{escape(label)}</p><h1>{escape(title)}</h1>
<p>{escape(message)}</p><p><a class="button button-signal" href="{escape(destination, quote=True)}">{escape(link_text)}</a></p>
<p><a href="{NEW_BASE}">Freight recovery homepage</a></p></section></main></body></html>
'''


def _redirect_rules():
    # Exact routes only. Archived experiments must not acquire an artificial
    # commercial successor. A fragment-free Location for /recovery lets the
    # browser retain existing #start-audit, #pricing and other freight anchors.
    lines = ["# Established offers moved to their dedicated sites."]
    for route, (_, destination) in SUCCESSORS.items():
        for old_path in (f"/{route}", f"/{route}/", f"/{route}/index.html"):
            lines.append(f"{old_path} {destination} 301")
    return "\n".join(lines) + "\n"


def _point_links_at_successors(bundle):
    """Link directly to real successors while retaining queries and fragments."""
    for page in bundle.rglob("*.html"):
        source_url = NEW_BASE + page.relative_to(bundle).as_posix()

        def final_destination(match):
            reference = unescape(match[2])
            if reference.startswith("#"):
                return match.group(0)
            old = urlsplit(urljoin(source_url, reference))
            if old.scheme not in {"http", "https"} or old.netloc not in {
                "www.retallyrecovery.com", "retallyrecovery.com"
            }:
                return match.group(0)
            route = old.path.removesuffix("/index.html").strip("/")
            if route not in SUCCESSORS:
                return match.group(0)
            destination = urlsplit(SUCCESSORS[route][1])
            final = urlunsplit((destination.scheme, destination.netloc, destination.path,
                               old.query or destination.query, old.fragment or destination.fragment))
            return match[1] + escape(final, quote=True) + match[3]

        html = page.read_text(encoding="utf-8")
        html = re.sub(r'(<a\b[^>]*?\bhref=")([^"]+)(")', final_destination, html, flags=re.I)
        page.write_text(html, encoding="utf-8")


def build_group(bundle):
    """Preserve the freight root; write only compatibility routes and archives."""
    bundle = Path(bundle)
    for filename in ADDED_FILES:
        destination = bundle / filename
        if destination.exists() or (destination.parent != bundle and destination.parent.exists()):
            raise ValueError(f"Legacy route collides with existing public output: {filename}")
    recoveryos = bundle / "recoveryos" / "index.html"
    if not recoveryos.is_file():
        raise ValueError("Expected the existing allowlisted RecoveryOS information page")
    for name in DESIGN_ASSETS:
        if not (bundle / name).is_file():
            raise ValueError(f"Missing freight design asset: {name}")

    freight = _restore_freight_home((bundle / "index.html").read_text(encoding="utf-8"))
    (bundle / "index.html").write_text(freight, encoding="utf-8")
    for route in LEGACY_ROUTES:
        (bundle / route).mkdir()
    (bundle / "recovery" / "index.html").write_text(_freight_compatibility_page(freight), encoding="utf-8")
    for route, (name, destination) in SUCCESSORS.items():
        if route == "recovery":
            continue
        html = _notice_page(
            name, destination.split("#", 1)[0], "This page has moved",
            "Visit the dedicated website for this business's current scope, availability and terms.",
            destination, f"Continue to {name}",
        )
        (bundle / route / "index.html").write_text(html, encoding="utf-8")
    for route, name in ARCHIVES.items():
        html = _notice_page(
            name, NEW_BASE + route + "/", "Archived project",
            "This earlier project is outside RETALLY Group's current commercial portfolio. "
            "This archive does not offer a service or designate a replacement provider.",
            GROUP_BASE + "#businesses", "View RETALLY Group's current companies",
        )
        (bundle / route / "index.html").write_text(html, encoding="utf-8")
    (bundle / "_redirects").write_text(_redirect_rules(), encoding="utf-8")
    _point_links_at_successors(bundle)
    _version_design_assets(bundle)


def _version_design_assets(bundle):
    """Returning visitors receive current freight CSS and intake/chat behavior."""
    revisions = {name: sha256((bundle / name).read_bytes()).hexdigest()[:16]
                 for name in DESIGN_ASSETS}

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
