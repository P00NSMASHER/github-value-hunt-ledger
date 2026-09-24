#!/usr/bin/env python3
"""Build the public Freight Recovery bundle; never publish the private repo."""

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


PUBLIC_CONTACT_PAGES = (
    "index.html",
    "privacy.html",
    "engagement-framework.html",
)
TEXT_SOURCE_FILES = (
    "index.html",
    "privacy.html",
    "engagement-framework.html",
    "404.html",
    "site.css",
    "site.js",
    "commercial-config.js",
    "favicon.svg",
    "robots.txt",
    "sitemap.xml",
    "site.webmanifest",
    "_headers",
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


def _public_source(name: str) -> Path:
    """Resolve one explicitly allowed file without traversing a source symlink."""
    path = SOURCE
    for part in Path(name).parts:
        path /= part
        if path.is_symlink():
            raise ValueError(f"Symlink is not allowed in public asset path: {name}")
    if not path.is_file():
        raise ValueError(f"Missing or non-regular public asset: {name}")
    return path


def validate_contact(value: str, verified: bool) -> str:
    """Require a sensible public mailbox plus explicit operator verification."""
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
    if (
        destination == REPOSITORY
        or REPOSITORY in destination.parents
        or destination in REPOSITORY.parents
    ):
        raise ValueError(
            "Public output must be outside the private repository and its parent directories."
        )
    if destination.exists() and (
        not destination.is_dir() or any(destination.iterdir())
    ):
        raise ValueError(
            "Choose a new or empty output directory; existing files will not be overwritten."
        )

    text_bundle = {
        name: _public_source(name).read_text(encoding="utf-8")
        for name in TEXT_SOURCE_FILES
    }
    binary_bundle = {
        name: _public_source(name).read_bytes()
        for name in BINARY_SOURCE_FILES
    }

    safe_contact = html.escape(contact, quote=True)
    for name in PUBLIC_CONTACT_PAGES:
        page = text_bundle[name]
        if page.count(CONTACT_META) != 1:
            raise ValueError(f"{name} must contain exactly one empty contact configuration.")
        text_bundle[name] = page.replace(
            CONTACT_META,
            f'<meta name="freight-contact-email" content="{safe_contact}">',
        )

    contact_marker_count = sum(page.count(CONTACT_LINK) for page in text_bundle.values())
    if contact_marker_count < 1:
        raise ValueError("The public bundle must contain at least one contact-link marker.")
    for name, page in tuple(text_bundle.items()):
        text_bundle[name] = page.replace(
            CONTACT_LINK,
            'data-contact-link href="mailto:'
            + safe_contact
            + '?subject=Freight%20Recovery%20question"',
        )

    page, count = STATUS_PATTERN.subn(
        lambda match: match.group(1)
        + "<strong>Free audit requests are open.</strong> "
        + "Start with non-sensitive business details. "
        + "Freight records move only through an approved secure route."
        + match.group(2),
        text_bundle["index.html"],
    )
    if count != 1:
        raise ValueError("The source must contain exactly one contact status banner.")
    text_bundle["index.html"] = page

    config = text_bundle["commercial-config.js"]
    if config.count(RATE_TOKEN) != 1 or config.count(RATE_LABEL_TOKEN) != 1:
        raise ValueError("Commercial configuration must contain one rate and label token.")
    text_bundle["commercial-config.js"] = config.replace(
        RATE_TOKEN, format(rate, "f")
    ).replace(RATE_LABEL_TOKEN, rate_label)

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
        'Download a fictional audit example <span aria-hidden="true">&#8599;</span></a>'
        '<p class="microcopy">Fictional data only. This walkthrough is not a customer '
        'result or recovery claim.</p>'
    )
    text_bundle["index.html"] = text_bundle["index.html"].replace(
        DEMO_MARKER, demo_link
    )

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
            os.environ.get(
                "FREIGHT_CONTINGENCY_RECOVERY_RATE",
                str(DEFAULT_CONTINGENCY_RECOVERY_RATE),
            ),
        )
    except ValueError as error:
        parser.error(str(error))
    print(f"Public bundle prepared: {output}")
    print("Files: " + ", ".join(PUBLIC_FILES))
    print("No deployment performed. Deploy only this output directory.")


if __name__ == "__main__":
    main()
