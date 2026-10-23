"""Conservative Article JSON-LD for genuine public freight learning resources.

Only source-registered editorial guides receive Article. Service pages, private
reports, calculators, noindex routes, and the commercial homepage do not.
No publication dates, customer outcomes, ratings or legal status are invented.
"""
from __future__ import annotations

import html
import json
import re

LEGACY_BASE = "https://p00nsmasher.github.io/github-value-hunt-ledger/"
EDITORIAL_GUIDES = frozenset({
    "accessorial-charge-audit.html",
    "carrier-rate-audit.html",
    "duplicate-freight-charges.html",
    "freight-audit-and-payment.html",
    "freight-audit-companies.html",
    "freight-audit-example.html",
    "freight-audit-methodology.html",
    "freight-audit-pricing.html",
    "freight-credit-rebill-audit.html",
    "freight-invoice-audit-checklist.html",
    "freight-overcharge-dispute-process.html",
    "freight-recovery-evidence-standard.html",
    "ltl-freight-audit.html",
    "ltl-reweigh-reclass-checklist.html",
    "parcel-audit.html",
})
TITLE = re.compile(r"<title>([^<]+)</title>", re.I)
DESCRIPTION = re.compile(r'<meta\s+name="description"\s+content="([^"]+)"', re.I)
CANONICAL = re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"', re.I)
SOCIAL_IMAGE = re.compile(r'<meta\s+property="og:image"\s+content="([^"]+)"', re.I)


def _unique(pattern: re.Pattern, source: str, field: str) -> str:
    matches = pattern.findall(source)
    if len(matches) != 1:
        raise ValueError(f"Article requires exactly one {field}")
    value = html.unescape(matches[0]).strip()
    if not value or len(value) > 500 or any(char in value for char in "<>\r\n"):
        raise ValueError(f"Unsafe {field} in public Article metadata")
    return value


def embed_article_schema(source: str, page: str) -> str:
    """Insert non-executable Article metadata without changing visual markup."""
    if page not in EDITORIAL_GUIDES:
        return source
    if source.count("</head>") != 1:
        raise ValueError(f"{page}: expected one HTML head")
    if re.search(r'"@type"\s*:\s*"Article"', source):
        raise ValueError(f"{page}: duplicate Article JSON-LD")

    canonical = _unique(CANONICAL, source, "canonical")
    expected = LEGACY_BASE + page
    if canonical != expected:
        raise ValueError(f"{page}: unexpected source canonical for Article")
    image = _unique(SOCIAL_IMAGE, source, "social image")
    if not image.startswith(LEGACY_BASE + "assets/"):
        raise ValueError(f"{page}: Article image is outside the approved site")
    article = {
        "@context": "https://schema.org",
        "@type": "Article",
        "@id": canonical + "#article",
        "headline": _unique(TITLE, source, "title"),
        "description": _unique(DESCRIPTION, source, "description"),
        "inLanguage": "en-US",
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "image": image,
        "author": {"@type": "Organization", "name": "RETALLY"},
        "publisher": {"@type": "Organization", "name": "RETALLY", "url": LEGACY_BASE},
    }
    # Escape script terminators if editorial content changes in the future.
    payload = json.dumps(article, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return source.replace("</head>", '<script type="application/ld+json">' + payload + "</script>\n</head>", 1)
