#!/usr/bin/env python3
"""Build the public RETALLY freight bundle; never publish the private repo."""

from __future__ import annotations

import argparse
import hashlib
import html
import os
from pathlib import Path
import re
import sys
import tempfile

SOURCE = Path(__file__).resolve().parent
REPOSITORY = SOURCE.parent.parent
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from freight.commercial_terms import (
    DEFAULT_CONTINGENCY_RECOVERY_RATE,
    contingency_rate_label,
    normalize_contingency_rate,
)
from freight.synthetic_pilot_bundle import build_synthetic_pilot_bundle
from freight.site.asset_integrity import validate_freight_media

PUBLIC_CONTACT_PAGES = (
    "index.html",
    "privacy.html",
    "engagement-framework.html",
    "freight-audit-services.html",
    "freight-invoice-audit.html",
    "freight-overcharge-recovery.html",
    "accessorial-charge-audit.html",
    "freight-audit-and-payment.html",
    "duplicate-freight-charges.html",
    "carrier-rate-audit.html",
    "ltl-freight-audit.html",
    "parcel-audit.html",
    "freight-invoice-audit-checklist.html",
    "about.html",
    "freight-overcharge-dispute-process.html",
    "freight-audit-methodology.html",
    "freight-audit-example.html",
    "freight-audit-pricing.html",
    "second-look-freight-audit.html",
    "trust.html",
    "founding-program.html",
    "referral-partners.html",
    "freight-recovery-evidence-standard.html",
    "post-payment-freight-audit.html",
    "freight-audit-companies.html",
)
TEXT_SOURCE_FILES = (
    "index.html",
    "privacy.html",
    "engagement-framework.html",
    "freight-audit-services.html",
    "freight-invoice-audit.html",
    "freight-overcharge-recovery.html",
    "accessorial-charge-audit.html",
    "freight-audit-and-payment.html",
    "duplicate-freight-charges.html",
    "carrier-rate-audit.html",
    "ltl-freight-audit.html",
    "parcel-audit.html",
    "freight-invoice-audit-checklist.html",
    "about.html",
    "freight-overcharge-dispute-process.html",
    "freight-audit-methodology.html",
    "freight-audit-example.html",
    "freight-audit-pricing.html",
    "second-look-freight-audit.html",
    "trust.html",
    "founding-program.html",
    "referral-partners.html",
    "recovery-status-example.html",
    "post-payment-freight-audit.html",
    "freight-recovery-evidence-standard.html",
    "freight-audit-companies.html",
    "404.html",
    "site.css",
    "foundry.css",
    "site.js",
    "commercial-config.js",
    "robots.txt",
    "sitemap.xml",
    "site.webmanifest",
    "llms.txt",
    "_headers",
    "google738a4fc9a0997cd0.html",
    "freight-audit-provider-scorecard.csv",
    "assets/fonts/ATTRIBUTION.json",
    "assets/fonts/LICENSE-HANKEN-GROTESK.txt",
    "assets/fonts/LICENSE-INSTRUMENT-SERIF.txt",
)
BINARY_SOURCE_FILES = (
    "assets/fonts/hanken-grotesk-latin.woff2",
    "assets/fonts/instrument-serif-italic-latin.woff2",
    "assets/fonts/instrument-serif-latin.woff2",
    "assets/images/freight-network-800.webp",
    "assets/images/freight-network.webp",
    "assets/images/invoice-evidence-800.webp",
    "assets/images/invoice-evidence.webp",
    "assets/images/terminal-blue-hour-800.webp",
    "assets/images/terminal-blue-hour.webp",
    "assets/brand/retally-wordmark.webp",
    "assets/brand/retally-wordmark-approved.png",
    "assets/brand/retally-emblem-approved.png",
)
SOURCE_FILES = TEXT_SOURCE_FILES + BINARY_SOURCE_FILES
DEMO_FILE = "synthetic-pilot-demo.zip"
PUBLIC_FILES = SOURCE_FILES + (DEMO_FILE,)

CONTACT_META = '<meta name="freight-contact-email" content="">'
CONTACT_LINK = 'data-contact-link href="#contact-pending"'
STATUS_PATTERN = re.compile(r'(<div class="wrap" id="contactStatus">).*?(</div>)')
DEMO_MARKER = '<!-- CONTROLLED_SYNTHETIC_DEMO_DOWNLOAD -->'
RATE_TOKEN = "__CONTINGENCY_RECOVERY_RATE__"
RATE_LABEL_TOKEN = "__CONTINGENCY_RECOVERY_RATE_LABEL__"


# Officially recognizable scalable social brand marks, pinned to vetted
# Simple Icons SVG blobs (CC0 icon collection). Full-color logos are rendered
# with brand-colored surfaces while gloss is confined to the enclosing card.
# Icons: Facebook f66767e46165f562134ca2c2e3d4bea8f37fb1ac; Instagram c0e86b0bfc7b902c485699953dee878f290f575b;
# YouTube 0492366a2be42c6f0372a64b8c6f4f6b2cb660f7. Not a partnership or endorsement.
SOCIAL_CHANNELS = (
    ("facebook", "Facebook", "https://www.facebook.com/p/Retally-61595467040747/",
     "Visit our page", "M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z"),
    ("instagram", "Instagram", "https://www.instagram.com/retallyrecovery/",
     "@retallyrecovery", "M7.0301.084c-1.2768.0602-2.1487.264-2.911.5634-.7888.3075-1.4575.72-2.1228 1.3877-.6652.6677-1.075 1.3368-1.3802 2.127-.2954.7638-.4956 1.6365-.552 2.914-.0564 1.2775-.0689 1.6882-.0626 4.947.0062 3.2586.0206 3.6671.0825 4.9473.061 1.2765.264 2.1482.5635 2.9107.308.7889.72 1.4573 1.388 2.1228.6679.6655 1.3365 1.0743 2.1285 1.38.7632.295 1.6361.4961 2.9134.552 1.2773.056 1.6884.069 4.9462.0627 3.2578-.0062 3.668-.0207 4.9478-.0814 1.28-.0607 2.147-.2652 2.9098-.5633.7889-.3086 1.4578-.72 2.1228-1.3881.665-.6682 1.0745-1.3378 1.3795-2.1284.2957-.7632.4966-1.636.552-2.9124.056-1.2809.0692-1.6898.063-4.948-.0063-3.2583-.021-3.6668-.0817-4.9465-.0607-1.2797-.264-2.1487-.5633-2.9117-.3084-.7889-.72-1.4568-1.3876-2.1228C21.2982 1.33 20.628.9208 19.8378.6165 19.074.321 18.2017.1197 16.9244.0645 15.6471.0093 15.236-.005 11.977.0014 8.718.0076 8.31.0215 7.0301.0839m.1402 21.6932c-1.17-.0509-1.8053-.2453-2.2287-.408-.5606-.216-.96-.4771-1.3819-.895-.422-.4178-.6811-.8186-.9-1.378-.1644-.4234-.3624-1.058-.4171-2.228-.0595-1.2645-.072-1.6442-.079-4.848-.007-3.2037.0053-3.583.0607-4.848.05-1.169.2456-1.805.408-2.2282.216-.5613.4762-.96.895-1.3816.4188-.4217.8184-.6814 1.3783-.9003.423-.1651 1.0575-.3614 2.227-.4171 1.2655-.06 1.6447-.072 4.848-.079 3.2033-.007 3.5835.005 4.8495.0608 1.169.0508 1.8053.2445 2.228.408.5608.216.96.4754 1.3816.895.4217.4194.6816.8176.9005 1.3787.1653.4217.3617 1.056.4169 2.2263.0602 1.2655.0739 1.645.0796 4.848.0058 3.203-.0055 3.5834-.061 4.848-.051 1.17-.245 1.8055-.408 2.2294-.216.5604-.4763.96-.8954 1.3814-.419.4215-.8181.6811-1.3783.9-.4224.1649-1.0577.3617-2.2262.4174-1.2656.0595-1.6448.072-4.8493.079-3.2045.007-3.5825-.006-4.848-.0608M16.953 5.5864A1.44 1.44 0 1 0 18.39 4.144a1.44 1.44 0 0 0-1.437 1.4424M5.8385 12.012c.0067 3.4032 2.7706 6.1557 6.173 6.1493 3.4026-.0065 6.157-2.7701 6.1506-6.1733-.0065-3.4032-2.771-6.1565-6.174-6.1498-3.403.0067-6.156 2.771-6.1496 6.1738M8 12.0077a4 4 0 1 1 4.008 3.9921A3.9996 3.9996 0 0 1 8 12.0077"),
    ("youtube", "YouTube", "https://www.youtube.com/channel/UCnS99gTJFScnA2gy4wKU_JQ",
     "Watch our channel", "M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"),
) 

def _social_nav() -> str:
    links = "".join(
        f'<a class="retally-social__button retally-social__button--{slug}" '
        f'href="{url}" target="_blank" rel="noopener noreferrer" '
        f'aria-label="RETALLY on {name} (opens in a new tab)">'
        f'<span class="retally-social__brandmark retally-social__brandmark--{slug}" aria-hidden="true">'
        f'<svg viewBox="0 0 24 24" width="26" height="26" role="presentation" '
        f'aria-hidden="true" focusable="false"><path d="{icon_path}"/></svg></span>'
        f'<span class="retally-social__copy"><strong>{name}</strong>'
        f'<span class="retally-social__detail">{detail}</span></span>'
        '<span class="retally-social__arrow" aria-hidden="true">&#8599;</span>'
        '</a>'
        for slug, name, url, detail, icon_path in SOCIAL_CHANNELS
    )
    return (
        '<nav class="wrap retally-social" aria-label="RETALLY social media">'
        '<span class="retally-social__title">Follow RETALLY</span>'
        '<div class="retally-social__links">' + links + '</div></nav>'
    )


def _embed_social_nav(page: str, asset: str) -> str:
    footer_bottom = '<div class="wrap footer-bottom">'
    if (page.count(footer_bottom) != 1 or page.count("</footer>") != 1
            or 'class="wrap retally-social"' in page
            or page.index("<footer") >= page.index(footer_bottom)):
        raise ValueError(f"Unexpected social footer boundary: {asset}")
    page = page.replace(footer_bottom, _social_nav() + "\n  " + footer_bottom, 1)
    return page



# Public site identifier, not an API credential. The widget reads public
# marketing knowledge only, never customer files or RecoveryOS information.
BUBBLAV_ID = "b0e3b0a1-8f64-4dcd-ac82-507366428147"
BUBBLAV_SNIPPET = (
    '<script src="https://www.bubblav.com/widget.js" '
    f'data-site-id="{BUBBLAV_ID}" defer></script>'
)

# The custom button is part of the public marketing artifact, not the vendor iframe.
# Its click handler uses BubblaV's published window.BubblaV.open() API.
BUBBLAV_LAUNCHER = (
    '<button id="retallyChatLauncher" class="retally-chat-launcher" type="button" '
    'aria-label="Open RETALLY AI chat assistant" aria-haspopup="dialog">'
    '<span class="retally-chat-orb" aria-hidden="true">'
    '<svg viewBox="0 0 32 32" fill="none" aria-hidden="true" focusable="false">'
    '<path d="M7 9.8C7 7.15 9.15 5 11.8 5h9.4C23.85 5 26 7.15 26 9.8v9.4'
    'c0 2.65-2.15 4.8-4.8 4.8h-6.7l-5.25 3.5v-4.17C7.9 22.49 7 21.07 7 19.2V9.8Z" '
    'stroke="currentColor" stroke-width="2.15" stroke-linejoin="round"/>'
    '<path d="M12 14.5h9M12 18.5h6" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round"/>'
    '</svg><span class="retally-chat-spark"></span></span>'
    '<span class="retally-chat-copy"><strong>Ask RETALLY</strong>'
    '<span>Freight recovery help</span></span></button>'
)
BUBBLAV_CONNECT_POLICY = (
    "https://www.bubblav.com https://bubblav.com https://*.bubblav.com"
)
BUBBLAV_POLICY_REPLACEMENTS = (
    ("script-src 'self';", "script-src 'self' https://www.bubblav.com;"),
    ("style-src 'self';", "style-src 'self' 'unsafe-inline';"),
    ("img-src 'self' data:;", "img-src 'self' data: https://www.bubblav.com https://*.bubblav.com;"),
    (
        "connect-src 'none';",
        f"connect-src {BUBBLAV_CONNECT_POLICY}; frame-src {BUBBLAV_CONNECT_POLICY};",
    ),
)


def _allow_bubblav(content: str, asset: str) -> str:
    """Allow only the vendor hosts needed by the public chat loader."""
    for old, new in BUBBLAV_POLICY_REPLACEMENTS:
        if content.count(old) != 1:
            raise ValueError(f"Cannot safely update widget CSP: {asset}: {old}")
        content = content.replace(old, new)
    # Existing content pages intentionally differ: some allow data: fonts.
    # Keep that original allowance and add only BubblaV's font origin.
    font_pattern = r"font-src 'self'( data:)?;"
    if len(re.findall(font_pattern, content)) != 1:
        raise ValueError(f"Unexpected font policy: {asset}")
    content = re.sub(
        font_pattern,
        lambda match: f"font-src 'self'{match.group(1) or ''} https://www.bubblav.com;",
        content,
    )
    return content


def _embed_bubblav(page: str, asset: str) -> str:
    if page.count("</body>") != 1 or page.count(BUBBLAV_SNIPPET) != 0:
        raise ValueError(f"Unexpected widget insertion boundary: {asset}")
    return _allow_bubblav(page, asset).replace("</body>", BUBBLAV_LAUNCHER + "\n" + BUBBLAV_SNIPPET + "\n</body>")



def _public_source(name: str) -> Path:
    path = SOURCE
    for part in Path(name).parts:
        path /= part
        if path.is_symlink():
            raise ValueError(f"Symlink is not allowed in public asset path: {name}")
    if not path.is_file():
        raise ValueError(f"Missing or non-regular public asset: {name}")
    return path


def validate_contact(value: str, verified: bool) -> str:
    if not verified:
        raise ValueError("Verify the business inbox, then set FREIGHT_CONTACT_VERIFIED=1.")
    email = value.strip()
    if len(email) > 254 or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._+\-]{0,63}@"
        r"(?:[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?\.)+"
        r"[A-Za-z]{2,63}",
        email,
    ):
        raise ValueError("Set FREIGHT_CONTACT_EMAIL to a valid business email address.")
    local, domain = email.rsplit("@", 1)
    if ".." in local or local.endswith("."):
        raise ValueError("The contact mailbox is malformed.")
    domain = domain.lower()
    if domain in {"example.com", "example.net", "example.org"} or domain.endswith(
        (".example", ".test", ".invalid", ".localhost")
    ):
        raise ValueError("A placeholder email cannot be used for a public launch.")
    return f"{local}@{domain}"


def build(
    output: Path,
    contact_email: str,
    contact_verified: bool,
    contingency_recovery_rate=DEFAULT_CONTINGENCY_RECOVERY_RATE,
) -> Path:
    contact = validate_contact(contact_email, contact_verified)
    rate = normalize_contingency_rate(contingency_recovery_rate)
    rate_label = contingency_rate_label(rate)
    destination = output.expanduser().resolve()
    if destination == REPOSITORY or REPOSITORY in destination.parents or destination in REPOSITORY.parents:
        raise ValueError("Public output must be outside the private repository and its parent directories.")
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError("Choose a new or empty output directory; existing files will not be overwritten.")

    text_bundle = {name: _public_source(name).read_text(encoding="utf-8") for name in TEXT_SOURCE_FILES}
    binary_bundle = {name: _public_source(name).read_bytes() for name in BINARY_SOURCE_FILES}
    validate_freight_media(SOURCE)

    safe_contact = html.escape(contact, quote=True)
    for name in PUBLIC_CONTACT_PAGES:
        page = text_bundle[name]
        if page.count(CONTACT_META) != 1:
            raise ValueError(f"{name} must contain exactly one empty contact configuration.")
        text_bundle[name] = page.replace(CONTACT_META, f'<meta name="freight-contact-email" content="{safe_contact}">')

    marker_count = sum(page.count(CONTACT_LINK) for page in text_bundle.values())
    if marker_count < 1:
        raise ValueError("The public bundle must contain at least one contact-link marker.")
    for name, page in tuple(text_bundle.items()):
        text_bundle[name] = page.replace(
            CONTACT_LINK,
            'data-contact-link href="mailto:' + safe_contact + '?subject=RETALLY%20question"',
        )

    page, count = STATUS_PATTERN.subn(
        lambda match: match.group(1)
        + "<strong>Free audit requests are open.</strong> "
        + match.group(2),
        text_bundle["index.html"],
    )
    if count != 1:
        raise ValueError("The source must contain exactly one contact status banner.")
    text_bundle["index.html"] = page

    config = text_bundle["commercial-config.js"]
    if config.count(RATE_TOKEN) != 1 or config.count(RATE_LABEL_TOKEN) != 1:
        raise ValueError("Commercial configuration must contain one rate and label token.")
    text_bundle["commercial-config.js"] = config.replace(RATE_TOKEN, format(rate, "f")).replace(RATE_LABEL_TOKEN, rate_label)

    if text_bundle["index.html"].count(DEMO_MARKER) != 1:
        raise ValueError("The source must contain exactly one controlled-demo marker.")
    with tempfile.TemporaryDirectory() as temporary:
        demo_path = Path(temporary) / DEMO_FILE
        receipt = build_synthetic_pilot_bundle(demo_path)
        demo_bytes = demo_path.read_bytes()
    if hashlib.sha256(demo_bytes).hexdigest() != receipt["bundle_sha256"]:
        raise ValueError("Controlled-demo digest changed during the public build.")
    demo_link = (
        '<a class="text-link text-link-light" href="synthetic-pilot-demo.zip" '
        'download data-track="controlled_demo_downloaded">'
        'Download a sample audit walkthrough <span aria-hidden="true">&#8599;</span></a>'
        '<p class="microcopy">Sample data only. This walkthrough is not a customer result or recovery claim.</p>'
    )
    text_bundle["index.html"] = text_bundle["index.html"].replace(DEMO_MARKER, demo_link)

    # Social profiles are informational, read-only outbound links. Inject the
    # same accessible component on every public marketing page at build time.
    for name in PUBLIC_CONTACT_PAGES:
        text_bundle[name] = _embed_social_nav(text_bundle[name], name)

    # All HTML pages—including standalone reports and the 404 page—must
    # request the new shared button stylesheet. Never re-publish a stale
    # cached visual system merely because a page lacks the social footer.
    button_css = "foundry.css?v=retally-all-buttons-3d-20261010"
    for name in TEXT_SOURCE_FILES:
        if not name.endswith(".html") or "foundry.css?v=" not in text_bundle[name]:
            continue
        updated, count = re.subn(
            r'foundry\.css\?v=[\w-]+', button_css, text_bundle[name]
        )
        if count != 1:
            raise ValueError(f"Unexpected button stylesheet reference: {name}")
        text_bundle[name] = updated

    # The marketing chatbot belongs on customer-facing content pages, not
    # RecoveryOS, the sample accounting report, or the error page. Keep the
    # original strict policy on all unpublished/private content.
    for name in PUBLIC_CONTACT_PAGES:
        text_bundle[name] = _embed_bubblav(text_bundle[name], name)
    text_bundle["_headers"] = _allow_bubblav(text_bundle["_headers"], "_headers")

    # Fail closed before publishing any source text containing the removed private contact.
    # Log only the filename, never the discovered private value.
    for name, page in text_bundle.items():
        if any(token in page.lower() for token in ("yorktowne", "17901", "jayp19386@")):
            raise ValueError(f"Nonbusiness contact information in public asset: {name}")

    destination.mkdir(parents=True, exist_ok=True)
    for name, content in text_bundle.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    for name, content in binary_bundle.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    (destination / DEMO_FILE).write_bytes(demo_bytes)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="New or empty public directory outside the private repository",
    )
    args = parser.parse_args()
    try:
        output = build(
            args.output,
            os.environ.get("FREIGHT_CONTACT_EMAIL", ""),
            os.environ.get("FREIGHT_CONTACT_VERIFIED") == "1",
            os.environ.get("FREIGHT_CONTINGENCY_RECOVERY_RATE", str(DEFAULT_CONTINGENCY_RECOVERY_RATE)),
        )
    except ValueError as error:
        parser.error(str(error))
    print(f"Public bundle prepared: {output}")
    print("Files: " + ", ".join(PUBLIC_FILES))
    print("No deployment performed. Deploy only this output directory.")


if __name__ == "__main__":
    main()
