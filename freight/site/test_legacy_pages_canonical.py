"""RETALLY legacy alias: SEO consolidation without breaking the fallback."""
from pathlib import Path
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET

import pytest

from freight.site.build import PUBLIC_CONTACT_PAGES, build
from freight.site.legacy_pages_canonical import (
    OLD_BASE, NEW_BASE, consolidate_generated_legacy, primary_url,
)


def make_fixture(root: Path):
    files = ("index.html", "about.html")
    for name in files:
        old = OLD_BASE + ("" if name == "index.html" else name)
        (root / name).write_text(
            '<!doctype html><head><link rel="canonical" href="' + old
            + '"><meta property="og:url" content="' + old + '"></head>'
            '<body><a href="about.html">Internal fallback navigation</a></body>',
            encoding="utf-8",
        )
    (root / "recovery-status-example.html").write_text(
        '<link rel="canonical" href="' + OLD_BASE
        + 'recovery-status-example.html">',
        encoding="utf-8",
    )
    (root / "404.html").write_text('<meta name="robots" content="noindex">')
    (root / "google1234567890.html").write_text("verification-token\n")
    (root / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?><urlset '
        'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        '<url><loc>' + OLD_BASE + '</loc></url>'
        '<url><loc>' + OLD_BASE + 'about.html</loc></url>'
        '<url><loc>' + OLD_BASE + 'recovery-status-example.html</loc></url>'
        '</urlset>',
        encoding="utf-8",
    )
    (root / "robots.txt").write_text(
        'User-agent: *\nAllow: /\n\nSitemap: ' + OLD_BASE + 'sitemap.xml\n',
        encoding="utf-8",
    )
    (root / "llms.txt").write_text(OLD_BASE + 'about.html\n')
    return files


def test_only_generated_fallback_canoncial_and_source_links(tmp_path):
    names = make_fixture(tmp_path)
    original_404 = (tmp_path / "404.html").read_bytes()
    result = consolidate_generated_legacy(tmp_path, names)
    assert result == {"html_pages": 3, "sitemap_urls": 3, "text_assets_updated": 6}
    for name in ("index.html", "about.html", "recovery-status-example.html"):
        content = (tmp_path / name).read_text(encoding="utf-8")
        old = OLD_BASE + ("" if name == "index.html" else name)
        assert f'href="{primary_url(old)}"' in content
        assert OLD_BASE not in content
    assert '<a href="about.html">' in (tmp_path / "index.html").read_text()
    assert (tmp_path / "404.html").read_bytes() == original_404
    assert (tmp_path / "google1234567890.html").read_text() == "verification-token\n"
    assert (tmp_path / "llms.txt").read_text() == NEW_BASE + "about\n"
    xml = (tmp_path / "sitemap.xml").read_text()
    assert "<loc>" + NEW_BASE + "about</loc>" in xml
    assert OLD_BASE not in xml
    assert "Sitemap: " + NEW_BASE + "sitemap.xml" in (tmp_path / "robots.txt").read_text()


def test_fails_before_mutation_on_bad_sitemap(tmp_path):
    names = make_fixture(tmp_path)
    sitemap = tmp_path / "sitemap.xml"
    sitemap.write_text(sitemap.read_text().replace(
        OLD_BASE + "about.html", "https://example.invalid/replaced"
    ))
    before = (tmp_path / "index.html").read_text()
    with pytest.raises(ValueError, match="sitemap"):
        consolidate_generated_legacy(tmp_path, names)
    assert (tmp_path / "index.html").read_text() == before


def test_does_not_change_checked_in_source_or_cloudflare_build(tmp_path):
    output = tmp_path / "public"
    build(output, "sales@freightfixture.com", True)
    original = (output / "index.html").read_text()
    original_asset = (output / "assets/brand/retally-emblem-approved.png").read_bytes()
    original_js = (output / "site.js").read_bytes()
    assert OLD_BASE in original
    result = consolidate_generated_legacy(output)
    assert result["sitemap_urls"] == len(PUBLIC_CONTACT_PAGES) + 1
    assert result["html_pages"] == len(PUBLIC_CONTACT_PAGES) + 1
    assert OLD_BASE not in (output / "index.html").read_text()
    assert (output / "index.html").read_text().count(
        '<link rel="canonical" href="' + NEW_BASE + '"'
    ) == 1
    assert (output / "site.js").read_bytes() == original_js
    assert (output / "assets/brand/retally-emblem-approved.png").read_bytes() == original_asset
    sitemap = ET.fromstring((output / "sitemap.xml").read_text())
    indexed = [x.text for x in sitemap.findall(".//{*}loc")]
    assert len(indexed) == len(PUBLIC_CONTACT_PAGES) + 1
    assert all(u and u.startswith(NEW_BASE) and not u.endswith(".html") for u in indexed)
    assert (output / "robots.txt").read_text().count(
        "Sitemap: " + NEW_BASE + "sitemap.xml"
    ) == 1


def test_reject_unsupported_legacy_urls():
    assert primary_url(OLD_BASE) == NEW_BASE
    assert primary_url(OLD_BASE + "carrier-rate-audit.html") == NEW_BASE + "carrier-rate-audit"
    for bad in ("https://other.example/target", OLD_BASE + "a/b.html",
                OLD_BASE + "about", OLD_BASE + "a?query=.html"):
        with pytest.raises(ValueError):
            primary_url(bad)
