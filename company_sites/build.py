"""Build either independent, static RETALLY company site from an explicit allowlist.

Run from the repository root or from company_sites. No freight Functions,
private workspaces, operational data, or research catalog files are published.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from html import escape
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from xml.etree import ElementTree as ET

SOURCE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SOURCE_ROOT.parent
import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from freight.site.wordmark import embed_approved_wordmark
CONTACT_EMAIL = "jay@retallyrecovery.com"  # Existing published business inbox.

DEFAULT_URLS = {
    "GROUP_URL": "https://group.retallyrecovery.com/",
    "FREIGHT_URL": "https://www.retallyrecovery.com/",
    "RECOVERYWORKS_URL": "https://recoveryworks.retallyrecovery.com/",
    "PERMITPLATE_URL": "https://permitplate.retallyrecovery.com/",
    "CAPTUREBRIEF_URL": "https://capturebrief.retallyrecovery.com/",
}
PROFILES = {
    "group": {
        "url_key": "GROUP_URL",
        "pages": ("index.html", "privacy/index.html"),
        "files": ("index.html", "privacy/index.html", "site.css", "enquiry.js", "_headers"),
        "assets": {
            "assets/brand/retally-emblem-approved.png": "freight/site/assets/brand/retally-emblem-approved.png",
            "assets/brand/retally-wordmark-approved.png": "freight/site/assets/brand/retally-wordmark-approved.png",
            "assets/brand/freightrecovery-emblem.webp": "freight/site/assets/brand/freightrecovery-emblem.webp",
            "assets/brand/recoveryos-emblem.webp": "freight/site/assets/brand/recoveryos-emblem.webp",
            "assets/brand/permitplate-emblem.webp": "freight/site/assets/brand/permitplate-emblem.webp",
            "assets/brand/capturebrief-emblem.webp": "freight/site/assets/brand/capturebrief-emblem.webp",
            "assets/brand/freightrecovery-600-20261022.webp": "freight/site/assets/brand/freightrecovery-600-20261022.webp",
            "assets/brand/freightrecovery-1200-20261022.webp": "freight/site/assets/brand/freightrecovery-1200-20261022.webp",
            "assets/brand/recoveryos-600-20261022.webp": "freight/site/assets/brand/recoveryos-600-20261022.webp",
            "assets/brand/recoveryos-1200-20261022.webp": "freight/site/assets/brand/recoveryos-1200-20261022.webp",
            "assets/brand/permitplate-600-20261022.webp": "freight/site/assets/brand/permitplate-600-20261022.webp",
            "assets/brand/permitplate-1200-20261022.webp": "freight/site/assets/brand/permitplate-1200-20261022.webp",
            "assets/brand/capturebrief-600-20261022.webp": "freight/site/assets/brand/capturebrief-600-20261022.webp",
            "assets/brand/capturebrief-1200-20261022.webp": "freight/site/assets/brand/capturebrief-1200-20261022.webp",
            "assets/hero.webp": "freight/site/group/assets/hero-1536.webp",
            "assets/freight.webp": "freight/site/assets/images/terminal-blue-hour-800.webp",
            "assets/permitplate.webp": "freight/site/group/assets/restaurant-768.webp",
            "assets/capturebrief.webp": "freight/site/group/assets/research-768.webp",
            "assets/hanken.woff2": "freight/site/assets/fonts/hanken-grotesk-latin.woff2",
            "assets/instrument.woff2": "freight/site/assets/fonts/instrument-serif-latin.woff2",
            "assets/instrument-italic.woff2": "freight/site/assets/fonts/instrument-serif-italic-latin.woff2",
            "assets/LICENSE-HANKEN-GROTESK.txt": "freight/site/assets/fonts/LICENSE-HANKEN-GROTESK.txt",
            "assets/LICENSE-INSTRUMENT-SERIF.txt": "freight/site/assets/fonts/LICENSE-INSTRUMENT-SERIF.txt",
            "assets/favicon.svg": "recoveryworks/site/favicon.svg",
        },
    },
    "recoveryworks": {
        "url_key": "RECOVERYWORKS_URL",
        "pages": ("index.html", "engagement/index.html", "privacy/index.html"),
        "files": ("index.html", "engagement/index.html", "privacy/index.html", "site.css", "_headers"),
        "assets": {
            "assets/brand/retally-wordmark-approved.png": "freight/site/assets/brand/retally-wordmark-approved.png",
            "assets/brand/recoveryos-emblem.webp": "freight/site/assets/brand/recoveryos-emblem.webp",
            "assets/brand/recoveryos-600-20261022.webp": "freight/site/assets/brand/recoveryos-600-20261022.webp",
            "assets/brand/recoveryos-1200-20261022.webp": "freight/site/assets/brand/recoveryos-1200-20261022.webp",
            "assets/hero-industrial.webp": "recoveryworks/site/assets/hero-industrial.webp",
            "assets/analyst-review.webp": "recoveryworks/site/assets/analyst-review.webp",
            "assets/proof-stack.webp": "recoveryworks/site/assets/proof-stack.webp",
            "assets/familjen.woff2": "recoveryworks/site/assets/familjen-grotesk-latin-wght-normal.woff2",
            "assets/newsreader.woff2": "recoveryworks/site/assets/newsreader-latin-wght-normal.woff2",
            "assets/newsreader-italic.woff2": "recoveryworks/site/assets/newsreader-latin-wght-italic.woff2",
            "assets/LICENSE-Familjen-Grotesk.txt": "recoveryworks/site/assets/LICENSE-Familjen-Grotesk.txt",
            "assets/LICENSE-Newsreader.txt": "recoveryworks/site/assets/LICENSE-Newsreader.txt",
            "assets/favicon.svg": "recoveryworks/site/favicon.svg",
        },
    },
}
GENERATED_FILES = ("404.html", "robots.txt", "sitemap.xml", "build-info.json")


def _public_url(value: str) -> str:
    url = urlsplit(value.strip())
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.query or url.fragment or url.port not in (None, 443)
            or any(char.isspace() for char in value)):
        raise ValueError("Public destinations must be HTTPS URLs without credentials, query or fragment")
    return urlunsplit(("https", url.netloc, url.path.rstrip("/") + "/", "", ""))


def _source(path: Path) -> Path:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(REPO_ROOT):
        raise ValueError(f"Missing or unsafe allowlisted source: {path.relative_to(REPO_ROOT)}")
    for parent in path.parents:
        if parent == REPO_ROOT:
            break
        if parent.is_symlink():
            raise ValueError("A public source directory must not be a symlink")
    return path


def _source_commit() -> str:
    value = os.environ.get("CF_PAGES_COMMIT_SHA") or os.environ.get("GITHUB_SHA") or "local"
    if value != "local" and not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError("Build source revision must be a full lowercase Git SHA or the explicit value local")
    return value


def build(company: str, output: Path, public_url: str | None = None) -> Path:
    if company not in PROFILES:
        raise ValueError("Unknown company target")
    profile = PROFILES[company]
    source_dir = SOURCE_ROOT / company
    output = Path(output).resolve()
    for name in PROFILES:
        protected = SOURCE_ROOT / name
        if output == protected or protected in output.parents:
            raise ValueError("Output must be outside company source directories")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Output directory must be empty")

    urls = {
        key: _public_url(os.environ.get("RETALLY_" + key, default))
        for key, default in DEFAULT_URLS.items()
    }
    if public_url is not None:
        urls[profile["url_key"]] = _public_url(public_url)
    canonical = urls[profile["url_key"]]
    tokens = {
        **urls,
        "SITE_URL": canonical,
        "CONTACT_EMAIL": CONTACT_EMAIL,
        "FREIGHT_PRIVACY_URL": urls["FREIGHT_URL"] + "privacy",
        "RECOVERYWORKS_PRIVACY_URL": urls["RECOVERYWORKS_URL"] + "privacy/",
        "PERMITPLATE_PRIVACY_URL": urls["PERMITPLATE_URL"] + "privacy.html",
        "CAPTUREBRIEF_PRIVACY_URL": urls["CAPTUREBRIEF_URL"] + "privacy.html",
    }
    # Validate all input bytes before creating any output.
    text_sources = {
        name: _source(source_dir / name).read_text(encoding="utf-8")
        for name in profile["files"]
    }
    asset_sources = {name: _source(REPO_ROOT / origin) for name, origin in profile["assets"].items()}
    commit = _source_commit()
    css_revision = hashlib.sha256(text_sources["site.css"].encode()).hexdigest()[:16]
    script_revisions = {
        name: hashlib.sha256(content.encode()).hexdigest()[:16]
        for name, content in text_sources.items() if name.endswith(".js")
    }
    output.mkdir(parents=True, exist_ok=True)

    for name, content in text_sources.items():
        for key, value in tokens.items():
            content = content.replace("{{" + key + "}}", escape(value, quote=True))
        if re.search(r"\{\{[^}]+\}\}", content):
            raise ValueError(f"Unresolved publication token in {name}")
        if name.endswith(".html"):
            content = embed_approved_wordmark(content, "/assets/brand/retally-wordmark-approved.png")
            content = content.replace('href="/site.css"', f'href="/site.css?v={css_revision}"')
            for script, revision in script_revisions.items():
                content = content.replace(f'src="/{script}"', f'src="/{script}?v={revision}"')
            # Cloudflare must not rewrite the public inbox into an injected
            # email-obfuscation script outside the explicit script allowlist.
            content = re.sub(r"(<body(?:\s[^>]*)?>)", r"\1<!--email_off-->", content, count=1)
            content = content.replace("</body>", "<!--/email_off--></body>")
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")

    for name, source in asset_sources.items():
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    sitemap_ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", sitemap_ns)
    sitemap = ET.Element("{" + sitemap_ns + "}urlset")
    for page in profile["pages"]:
        route = page.removesuffix("index.html")
        item = ET.SubElement(sitemap, "{" + sitemap_ns + "}url")
        ET.SubElement(item, "{" + sitemap_ns + "}loc").text = canonical + route
    ET.ElementTree(sitemap).write(output / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    (output / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {canonical}sitemap.xml\n", encoding="utf-8")
    (output / "build-info.json").write_text(json.dumps({
        "company": company,
        "canonical_url": canonical,
        "source_commit": commit,
        "source_commit_kind": "local_unattributed" if commit == "local" else "git_commit",
        "release": "retally-four-businesses-20261021",
    }, indent=2) + "\n", encoding="utf-8")
    title = "RETALLY Group" if company == "group" else "RETALLY RecoveryWorks"
    not_found = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex"><title>Page not found | {title}</title><link rel="stylesheet" href="/site.css?v={css_revision}"></head><body><main class="document wrap"><p class="eyebrow">{title}</p><h1>That page isn't here.</h1><p>Use the homepage to find the current service and contact details.</p><a href="/">Return to {title}</a></main></body></html>"""
    (output / "404.html").write_text(embed_approved_wordmark(not_found, "/assets/brand/retally-wordmark-approved.png") + "\n", encoding="utf-8")
    expected = set(profile["files"]) | set(profile["assets"]) | set(GENERATED_FILES)
    actual = {file.relative_to(output).as_posix() for file in output.rglob("*") if file.is_file()}
    if actual != expected:
        raise ValueError("Output differs from the company publication allowlist")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("company", choices=tuple(PROFILES))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--public-url", help="Override this company's canonical HTTPS base URL")
    args = parser.parse_args()
    output = build(args.company, args.output, args.public_url)
    print(f"Built {args.company}: {output}")


if __name__ == "__main__":
    main()

