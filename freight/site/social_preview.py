"""RETALLY social share metadata: source-backed, no-input, no-network.

Populate Open Graph and Twitter summary cards for public informational pages
that previously provided no link preview. Homepage has a separately approved
identity and is not changed here. All images already belong to the existing
public binary allowlist; no remote content or unapproved customer imagery.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

LEGACY_ROOT = "https://p00nsmasher.github.io/github-value-hunt-ledger/"
IMAGE_BY_TOPIC = {
    "assets/images/terminal-blue-hour.webp": frozenset({
        "freight-audit-services.html", "freight-overcharge-recovery.html",
        "ltl-freight-audit.html", "parcel-audit.html",
        "freight-audit-companies.html", "founding-program.html",
        "post-payment-freight-audit.html",
    }),
    "assets/images/freight-network.webp": frozenset({
        "about.html", "trust.html", "privacy.html", "referral-partners.html",
        "engagement-framework.html", "freight-audit-pricing.html",
        "freight-audit-and-payment.html",
    }),
    "assets/images/invoice-evidence.webp": frozenset({
        "freight-invoice-audit.html", "accessorial-charge-audit.html",
        "duplicate-freight-charges.html", "carrier-rate-audit.html",
        "freight-invoice-audit-checklist.html",
        "freight-overcharge-dispute-process.html", "freight-audit-methodology.html",
        "freight-audit-example.html", "second-look-freight-audit.html",
        "freight-recovery-evidence-standard.html",
    }),
}
ALT = {
    "assets/images/terminal-blue-hour.webp": "Freight transport and distribution terminal at blue hour",
    "assets/images/freight-network.webp": "Freight transport network and logistics operations",
    "assets/images/invoice-evidence.webp": "Freight invoices and records for evidence-based review",
}
WORKSHEET = "freight-invoice-audit-checklist.html"
WORKSHEET_TITLE = "RETALLY | Free Printable Freight Invoice Audit Worksheet"
WORKSHEET_DESCRIPTION = (
    "Print a 15-point freight audit checklist and compare sample or "
    "anonymized invoice amounts privately in your browser. "
    "Educational only; no refund or recovery is promised."
)
TAG_RE = {
    "title": re.compile(r"<title>([^<]+)</title>", re.IGNORECASE),
    "description": re.compile(r'<meta\s+name="description"\s+content="([^"]+)"\s*/?>',re.IGNORECASE),
    "canonical": re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"\s*/?>',re.IGNORECASE),
}

def _plain_markup(value: str) -> str:
    value=html.unescape(value).strip()
    if not value or len(value)>240 or any(x in value for x in ("\n","\r","<",">")):
        raise ValueError("Missing or unsafe SEO source metadata")
    return value

def _one(pattern: re.Pattern, content: str, key: str) -> str:
    matches=pattern.findall(content)
    if len(matches)!=1:
        raise ValueError("Expected exactly one "+key)
    return _plain_markup(matches[0])

def preview_images() -> dict[str,str]:
    images={}
    for image,names in IMAGE_BY_TOPIC.items():
        for name in names:
            if name in images:
                raise ValueError(f"Multiple topic images for {name}")
            images[name]=image
    return images

def embed(content: str, page: str, *, available_images: set[str]) -> str:
    """Strictly add static link preview tags to one published content page.

    Site build and Cloudflare canonical-rebase remain separate. The stored
    source uses the existing legacy canonical; Cloudflare transparently
    upgrades this page, og:url and image URL to its final extensionless host.
    """
    if page == "index.html":
        # Existing owner-approved homepage OG/Twitter creative is preserved.
        return content
    images=preview_images()
    if page not in images:
        raise ValueError(f"No registered social media topic preview for {page}")
    image=images[page]
    if image not in available_images:
        raise ValueError(f"Social image is missing from public source allowlist: {image}")
    if content.count("</head>")!=1:
        raise ValueError(f"{page}: unexpected <head> structure")
    title=WORKSHEET_TITLE if page==WORKSHEET else _one(TAG_RE["title"],content,"title")
    description=(WORKSHEET_DESCRIPTION if page==WORKSHEET
                 else _one(TAG_RE["description"],content,"description"))
    if "RETALLY" not in title.upper():
        title += " | RETALLY"
    canonical=_one(TAG_RE["canonical"],content,"canonical")
    expected=LEGACY_ROOT+page
    if canonical!=expected:
        raise ValueError(f"{page}: canonical URL does not match registered page")
    if len(title)>95 or len(description)>240:
        raise ValueError(f"{page}: social text should fit the source contract")
    if any(token in content for token in ('property="og:title"','name="twitter:card"',
                                          'property="og:image"')):
        raise ValueError(f"{page}: existing share card must be reviewed instead of overwritten")
    encode=lambda value:html.escape(value,quote=True)
    remote_image=LEGACY_ROOT+image
    tags=[
        '<!-- RETALLY static public share card: no analytics, amounts, or lead tracking -->',
        '<meta property="og:type" content="website">',
        '<meta property="og:locale" content="en_US">',
        '<meta property="og:site_name" content="RETALLY">',
        f'<meta property="og:title" content="{encode(title)}">',
        f'<meta property="og:description" content="{encode(description)}">',
        f'<meta property="og:url" content="{encode(canonical)}">',
        f'<meta property="og:image" content="{encode(remote_image)}">',
        '<meta property="og:image:type" content="image/webp">',
        f'<meta property="og:image:alt" content="{encode(ALT[image])}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{encode(title)}">',
        f'<meta name="twitter:description" content="{encode(description)}">',
        f'<meta name="twitter:image" content="{encode(remote_image)}">',
        f'<meta name="twitter:image:alt" content="{encode(ALT[image])}">',
        '<!-- /RETALLY static public share card -->',
    ]
    return content.replace("</head>","\n  " + "\n  ".join(tags)+"\n</head>",1)
