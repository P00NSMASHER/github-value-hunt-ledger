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
WORKSHEET_TITLE = "RETALLY | Free Printable Freight Audit Worksheet"
WORKSHEET_DESCRIPTION = (
    "Print 15 freight invoice checks and compare sample totals privately in "
    "your browser. Educational only; no refund or recovery is promised."
)

# Human-authored, topic-specific captions designed for a small social
# preview. They never convert an estimate into a customer result or imply
# that confidential records can be uploaded on the public site.
EDITORIAL_SHARE_META = {
    "privacy.html": (
        "RETALLY | Freight Data Privacy and Handling",
        "See how audit scope can be discussed without sharing private invoices in messages. Confidential files require a separately approved transfer route.",
    ),
    "engagement-framework.html": (
        "RETALLY | Freight Recovery Engagement Framework",
        "Understand how review scope, customer authorization, evidence and eligible realized value are defined before recovery work.",
    ),
    "freight-audit-services.html": (
        "RETALLY | Freight Invoice Audit Services",
        "Evidence-first freight invoice review across rates, fees and prior credits. A flagged billing difference is not an approved or recovered claim.",
    ),
    "freight-invoice-audit.html": (
        "RETALLY | How to Review a Freight Invoice",
        "Match shipments, governing rates, fuel, accessorials and prior credits before treating billed differences as supported findings.",
    ),
    "freight-overcharge-recovery.html": (
        "RETALLY | Freight Overcharge Recovery Process",
        "From a documented invoice difference to an authorized dispute, carrier response and eligible funds or credits actually received.",
    ),
    "accessorial-charge-audit.html": (
        "RETALLY | Freight Accessorial Charge Audit",
        "Check detention, liftgate and other carrier fees against contracts, actual service records and credits before disputing a charge.",
    ),
    "freight-audit-and-payment.html": (
        "RETALLY | Freight Audit and Payment Controls",
        "Use contract checks, billing reconciliation and independent calculations to review freight AP charges before payment.",
    ),
    "duplicate-freight-charges.html": (
        "RETALLY | Duplicate Freight Charge Checklist",
        "Two invoices may reflect a rebill, correction or separate service. Follow shipment identity, payment and credit history first.",
    ),
    "carrier-rate-audit.html": (
        "RETALLY | Carrier Rate Audit Checklist",
        "Verify the controlling agreement, effective date, surcharge schedule and exceptions before claiming a rate mismatch.",
    ),
    "ltl-freight-audit.html": (
        "RETALLY | LTL Freight Audit Guide",
        "Review LTL freight class, billed weight, accessorials, minimums, fuel and tariff terms against shipment evidence.",
    ),
    "parcel-audit.html": (
        "RETALLY | Parcel Invoice Audit Guide",
        "Review package dimensions, service tiers, surcharges and credits using the governing carrier terms and shipment details.",
    ),
    WORKSHEET: (WORKSHEET_TITLE, WORKSHEET_DESCRIPTION),
    "about.html": (
        "About RETALLY | Freight Billing Review",
        "Learn RETALLY's evidence-first approach to freight billing reviews and why documented findings matter more than estimates.",
    ),
    "freight-overcharge-dispute-process.html": (
        "RETALLY | Freight Overcharge Dispute Guide",
        "Build an evidence-backed dispute using the governing rate, shipment records, reproducible math and existing corrections.",
    ),
    "freight-audit-methodology.html": (
        "RETALLY | Freight Audit Evidence Method",
        "Explore a conservative review method covering shipment identity, rate authority, calculation, authorization and settlement.",
    ),
    "freight-audit-example.html": (
        "RETALLY | Worked Freight Audit Example",
        "A clearly labelled sample invoice walkthrough, from expected-charge calculation through supported findings and credit reconciliation.",
    ),
    "freight-audit-pricing.html": (
        "RETALLY | Freight Audit Pricing Explained",
        "$0 upfront for agreed eligible initial audit scope. Separate recovery fees apply only to eligible value actually recovered under written terms.",
    ),
    "second-look-freight-audit.html": (
        "RETALLY | Independent Second-Look Freight Audit",
        "An independent review starts by excluding issues, disputes and credits already identified by existing controls or auditors.",
    ),
    "trust.html": (
        "RETALLY | Security, Review and Trust Center",
        "Learn how freight information is handled, where human review matters and why confidential files stay off the public website.",
    ),
    "founding-program.html": (
        "RETALLY | Freight Buyer Founding Program",
        "Explore the founding program approach and the separate qualification, authorization and written engagement boundaries.",
    ),
    "referral-partners.html": (
        "RETALLY | Freight Audit Referral Partners",
        "Review the referral partner approach and evidence and authorization boundaries for business introductions.",
    ),
    "freight-recovery-evidence-standard.html": (
        "RETALLY | Freight Recovery Evidence Standard",
        "Separate candidate differences, supported findings, authorized claims, and eligible credits or refunds actually realized.",
    ),
    "post-payment-freight-audit.html": (
        "RETALLY | Post-Payment Freight Audit Guide",
        "Review historical paid freight invoices against governing rates, corrections and credit history to identify documented questions.",
    ),
    "freight-audit-companies.html": (
        "RETALLY | Comparing Freight Audit Companies",
        "Compare freight audit approaches by their scope, evidence rules, prior-credit treatment, recovery fees and authorization.",
    ),
}
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
    # Source title/description must exist even when the shorter social
    # editorial text intentionally differs from SEO snippets.
    _one(TAG_RE["title"],content,"title")
    _one(TAG_RE["description"],content,"description")
    if set(EDITORIAL_SHARE_META) != set(images):
        raise ValueError("Social editorial copy must cover every registered public page")
    title,description=EDITORIAL_SHARE_META[page]
    if "RETALLY" not in title.upper():
        raise ValueError(f"{page}: a share card must identify the real brand")
    canonical=_one(TAG_RE["canonical"],content,"canonical")
    expected=LEGACY_ROOT+page
    if canonical!=expected:
        raise ValueError(f"{page}: canonical URL does not match registered page")
    if len(title)>70 or len(description)>175:
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
