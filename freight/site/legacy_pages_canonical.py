"""Point RETALLY's GitHub Pages *generated fallback* at the official SEO canonicals.

This runs only on the already isolated GitHub Pages artifact, after the usual
publishable-file build. It never touches the source or the Cloudflare bundle.
The legacy copy remains usable, including original .html navigation, but
search engines see the primary www.retallyrecovery.com URLs in the canonical,
Open Graph, JSON-LD, sitemap and robots signals.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from freight.site.build import PUBLIC_CONTACT_PAGES
from freight.site.rebase_public_urls import OLD_BASE, NEW_BASE

_CANONICAL = re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"', re.I)
_SITEMAP_LOC = "{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
_EXTRA_CANONICAL = ("recovery-status-example.html",)


def primary_url(legacy: str) -> str:
    """Turn one *known* legacy absolute marketing URL into the live pretty URL."""
    if not legacy.startswith(OLD_BASE):
        raise ValueError("A non-legacy URL cannot be canonicalized")
    path = legacy[len(OLD_BASE):]
    if not path:
        return NEW_BASE
    if "/" in path or not path.endswith(".html"):
        raise ValueError("Expected a root-level public HTML page")
    stem = path[:-5]
    if not re.fullmatch(r"[a-z0-9-]+", stem):
        raise ValueError("Unexpected page name")
    return NEW_BASE + stem


def consolidate_generated_legacy(directory: Path, names: tuple[str, ...] = PUBLIC_CONTACT_PAGES) -> dict[str, int]:
    root = directory.resolve()
    if not root.is_dir():
        raise ValueError("Expected an existing isolated public bundle")
    required = set(names)
    if "index.html" not in required or len(required) != len(names):
        raise ValueError("Expected registered, unique public marketing pages with home")
    if any(path.is_symlink() for path in root.rglob("*")):
        raise ValueError("Refusing a symlink in generated public output")

    # The extra sample report is also indexable with a legacy canonical,
    # although it is deliberately excluded from the public sitemap.
    page_names = sorted(required | set(_EXTRA_CANONICAL))
    staged: dict[Path, str] = {}
    for name in page_names:
        if "/" in name or not name.endswith(".html"):
            raise ValueError("Unexpected published page name")
        path = root / name
        if not path.is_file():
            raise ValueError(f"Generated fallback is missing public page: {name}")
        content = path.read_text(encoding="utf-8")
        expected = OLD_BASE + ("" if name == "index.html" else name)
        if _CANONICAL.findall(content) != [expected]:
            raise ValueError(f"Unexpected legacy canonical before retargeting: {name}")
        rewritten = content.replace(OLD_BASE, NEW_BASE)
        # Make *absolute* links, OG/JSON-LD identities and schema point to
        # Cloudflare's existing 200 route, not its .html redirect.
        for other in page_names:
            if other != "index.html":
                rewritten = rewritten.replace(
                    NEW_BASE + other,
                    NEW_BASE + other.removesuffix(".html"),
                )
        if _CANONICAL.findall(rewritten) != [primary_url(expected)]:
            raise ValueError(f"Canonical consolidation failed for {name}")
        if OLD_BASE in rewritten:
            raise ValueError(f"Unexpected legacy absolute identity left in {name}")
        staged[path] = rewritten

    sitemap = root / "sitemap.xml"
    xml = sitemap.read_text(encoding="utf-8")
    document = ET.fromstring(xml)
    actual = [el.text for el in document.iter(_SITEMAP_LOC)]
    expected_sitemap = {
        OLD_BASE + ("" if name == "index.html" else name)
        for name in required
    }
    if len(actual) != len(required) or set(actual) != expected_sitemap:
        raise ValueError("Legacy sitemap changed unexpectedly; do not write SEO signals")
    for page in sorted(required):
        old_url = OLD_BASE + ("" if page == "index.html" else page)
        xml = xml.replace("<loc>" + old_url + "</loc>",
                          "<loc>" + primary_url(old_url) + "</loc>")
    if OLD_BASE in xml:
        raise ValueError("Legacy sitemap is not fully consolidated")
    staged[sitemap] = xml

    robots = root / "robots.txt"
    robots_text = robots.read_text(encoding="utf-8")
    expected_robots = "Sitemap: " + OLD_BASE + "sitemap.xml"
    if robots_text.count(expected_robots) != 1:
        raise ValueError("Unexpected legacy robots sitemap")
    staged[robots] = robots_text.replace(
        expected_robots, "Sitemap: " + NEW_BASE + "sitemap.xml"
    )

    # Publish consistent AI-readable references without touching any source
    # or confidential/restricted content. Only the allowlisted text is edited.
    llms = root / "llms.txt"
    if llms.is_file():
        content = llms.read_text(encoding="utf-8").replace(OLD_BASE, NEW_BASE)
        for page in page_names:
            if page != "index.html":
                content = content.replace(NEW_BASE + page, NEW_BASE + page[:-5])
        if OLD_BASE in content:
            raise ValueError("Legacy AI-readable links were not consolidated")
        staged[llms] = content

    # Fail-closed reads above prevent partial results on a bad source schema.
    for path, content in staged.items():
        path.write_text(content, encoding="utf-8")
    return {"html_pages": len(page_names), "sitemap_urls": len(required),
            "text_assets_updated": len(staged)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    options = parser.parse_args()
    print(consolidate_generated_legacy(options.directory))


if __name__ == "__main__":
    main()
