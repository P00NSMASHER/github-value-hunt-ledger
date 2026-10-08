#!/usr/bin/env python3
"""Rebase the generated RETALLY Pages bundle without touching the legacy site.

Cloudflare Pages serves `page.html` at `/page` and redirects the former URL.
Its sitemap, canonical tags, and internal page links must name the final 200
route, not the redirecting `.html` address. GitHub Pages keeps its original
source, sitemap and URL structure while migration evidence is collected.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
import xml.etree.ElementTree as ET

OLD_BASE = "https://p00nsmasher.github.io/github-value-hunt-ledger/"
NEW_BASE = "https://www.retallyrecovery.com/"
TEXT_SUFFIXES = {".html", ".xml", ".txt", ".json", ".js", ".css", ".svg"}
CANONICAL_PATTERN = re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"', re.I)
SITEMAP_LOC = "{http://www.sitemaps.org/schemas/sitemap/0.9}loc"


def _page_stems(directory: Path) -> list[str]:
    """Root-level indexable pages, excluding HTML error and verification files."""
    return sorted(
        p.stem
        for p in directory.glob("*.html")
        if p.name not in {"index.html", "404.html"} and not p.name.startswith("google")
    )


def _pretty_urls(content: str, page_stems: list[str], is_root_html: bool) -> str:
    """Use Cloudflare's final public URLs; preserve real filenames on disk."""
    for stem in page_stems:
        # Canonicals, sitemap locs, Open Graph, JSON-LD and absolute content URLs.
        content = content.replace(f"{NEW_BASE}{stem}.html", f"{NEW_BASE}{stem}")
        if is_root_html:
            # Root-level navigation should not need a 308 redirect per click.
            for prefix in ('href="', 'href="./', 'href="/'):
                content = content.replace(
                    f'{prefix}{stem}.html', f'{prefix}{stem}'
                )
    if is_root_html:
        content = content.replace('href="index.html"', 'href="./"')
        content = content.replace('href="./index.html"', 'href="./"')
        content = content.replace('href="/index.html"', 'href="/"')
    return content


def rebase(directory: Path) -> int:
    """Rewrite only a generated directory; never alter repository source files."""
    if not directory.is_dir():
        raise ValueError("Public bundle directory does not exist")
    page_stems = _page_stems(directory)
    replacements = 0
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Public bundle contains a symlink: {path}")
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        source = path.read_text(encoding="utf-8")
        count = source.count(OLD_BASE)
        rebased = _pretty_urls(
            source.replace(OLD_BASE, NEW_BASE),
            page_stems,
            is_root_html=path.parent == directory and path.suffix.lower() == ".html",
        )
        if rebased != source:
            path.write_text(rebased, encoding="utf-8")
        replacements += count
    if replacements < 1:
        raise ValueError("No previous absolute site URLs found; check the public site source")
    for path in directory.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            if OLD_BASE in path.read_text(encoding="utf-8"):
                raise ValueError(f"Unconverted absolute site URL: {path}")
    return replacements


def validate_cloudflare_seo(directory: Path) -> int:
    """Fail the Pages build if its advertised URLs would redirect or disagree."""
    if not directory.is_dir():
        raise ValueError("Public bundle directory does not exist")
    page_stems = _page_stems(directory)
    expected = {NEW_BASE} | {NEW_BASE + stem for stem in page_stems}
    sitemap = directory / "sitemap.xml"
    root = ET.fromstring(sitemap.read_text(encoding="utf-8"))
    actual = [element.text for element in root.iter(SITEMAP_LOC)]
    if len(actual) != len(expected) or set(actual) != expected:
        missing = sorted(expected.difference(actual))
        unexpected = sorted(set(actual).difference(expected))
        raise ValueError(
            f"Cloudflare sitemap must list each final indexable URL once: "
            f"missing={missing}, unexpected={unexpected}, listed={len(actual)}"
        )
    for stem, file in [("", directory / "index.html")] + [
        (stem, directory / f"{stem}.html") for stem in page_stems
    ]:
        canonical = CANONICAL_PATTERN.findall(file.read_text(encoding="utf-8"))
        correct = NEW_BASE + stem
        if canonical != [correct]:
            raise ValueError(
                f"{file.name}: expected one self-referencing canonical {correct}, "
                f"found {canonical}"
            )
    robots = (directory / "robots.txt").read_text(encoding="utf-8")
    if f"Sitemap: {NEW_BASE}sitemap.xml" not in robots:
        raise ValueError("Cloudflare robots.txt must advertise the production sitemap")
    return len(actual)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    arguments = parser.parse_args()
    print(f"Rebased {rebase(arguments.directory)} absolute public URLs to {NEW_BASE}")
    print(f"Validated {validate_cloudflare_seo(arguments.directory)} canonical sitemap URLs")
