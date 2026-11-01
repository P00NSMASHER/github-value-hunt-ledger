"""Regression checks for parallel Cloudflare and legacy GitHub Pages URLs."""

from pathlib import Path

import pytest

from freight.site.rebase_public_urls import (
    OLD_BASE,
    NEW_BASE,
    rebase,
    validate_cloudflare_seo,
)


def make_public_site(tmp_path: Path) -> Path:
    (tmp_path / "index.html").write_text(
        f'<link rel="canonical" href="{OLD_BASE}">'
        '<a href="about.html">About</a>'
        '<a href="external.html">Unpublished page</a>',
        encoding="utf-8",
    )
    (tmp_path / "about.html").write_text(
        f'<link rel="canonical" href="{OLD_BASE}about.html">'
        f'<meta property="og:url" content="{OLD_BASE}about.html">'
        '<a href="./index.html">Home</a>',
        encoding="utf-8",
    )
    (tmp_path / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f'<url><loc>{OLD_BASE}</loc></url>'
        f'<url><loc>{OLD_BASE}about.html</loc></url>'
        '</urlset>',
        encoding="utf-8",
    )
    (tmp_path / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {OLD_BASE}sitemap.xml\n",
        encoding="utf-8",
    )
    return tmp_path


def test_rebase_emits_final_cloudflare_routes_and_preserves_assets(tmp_path: Path):
    site = make_public_site(tmp_path)
    verification = site / "google738a4fc9a0997cd0.html"
    verification.write_text(
        "google-site-verification: google738a4fc9a0997cd0.html\n",
        encoding="utf-8",
    )
    binary = b"\x00" + OLD_BASE.encode() + b"\xff"
    (site / "image.webp").write_bytes(binary)

    assert rebase(site) == 6
    assert validate_cloudflare_seo(site) == 2

    home = (site / "index.html").read_text()
    about = (site / "about.html").read_text()
    sitemap = (site / "sitemap.xml").read_text()
    assert f'<link rel="canonical" href="{NEW_BASE}">' in home
    assert 'href="about"' in home
    assert 'href="external.html"' in home  # Unknown assets cannot be rewritten.
    assert f'<link rel="canonical" href="{NEW_BASE}about">' in about
    assert f'<meta property="og:url" content="{NEW_BASE}about">' in about
    assert 'href="./"' in about
    assert f"<loc>{NEW_BASE}about</loc>" in sitemap
    assert f"<loc>{NEW_BASE}about.html</loc>" not in sitemap
    assert f"Sitemap: {NEW_BASE}sitemap.xml" in (site / "robots.txt").read_text()
    assert verification.read_text() == "google-site-verification: google738a4fc9a0997cd0.html\n"
    assert (site / "image.webp").read_bytes() == binary
    assert OLD_BASE not in home + about + sitemap


def test_rebase_does_not_rewrite_relative_links_in_subdirectories(tmp_path: Path):
    site = make_public_site(tmp_path)
    subdir = site / "recoveryos"
    subdir.mkdir()
    (subdir / "index.html").write_text(
        f'<a href="about.html">Sibling</a><a href="{OLD_BASE}about.html">RETALLY</a>',
        encoding="utf-8",
    )
    rebase(site)
    result = (subdir / "index.html").read_text()
    assert 'href="about.html"' in result
    assert f'href="{NEW_BASE}about"' in result


def test_rebase_refuses_missing_original_url(tmp_path: Path):
    (tmp_path / "index.html").write_text("no original site URL", encoding="utf-8")
    with pytest.raises(ValueError, match="No previous absolute site URLs"):
        rebase(tmp_path)


def test_sitemap_must_list_final_nonredirecting_urls(tmp_path: Path):
    site = make_public_site(tmp_path)
    rebase(site)
    sitemap = site / "sitemap.xml"
    sitemap.write_text(sitemap.read_text().replace(
        f"<loc>{NEW_BASE}about</loc>", f"<loc>{NEW_BASE}about.html</loc>"
    ))
    with pytest.raises(ValueError, match="final indexable URL"):
        validate_cloudflare_seo(site)


def test_each_html_canonical_must_match_sitemap_destination(tmp_path: Path):
    site = make_public_site(tmp_path)
    rebase(site)
    about = site / "about.html"
    about.write_text(about.read_text().replace(
        f'href="{NEW_BASE}about"', f'href="{NEW_BASE}about.html"'
    ))
    with pytest.raises(ValueError, match="self-referencing canonical"):
        validate_cloudflare_seo(site)


def test_build_rejects_duplicate_sitemap_entries(tmp_path: Path):
    site = make_public_site(tmp_path)
    rebase(site)
    sitemap = site / "sitemap.xml"
    sitemap.write_text(sitemap.read_text().replace(
        "</urlset>", f"<url><loc>{NEW_BASE}about</loc></url></urlset>"
    ))
    with pytest.raises(ValueError, match="final indexable URL"):
        validate_cloudflare_seo(site)


def test_rebase_refuses_symlinks(tmp_path: Path):
    site = make_public_site(tmp_path)
    (site / "linked.xml").symlink_to(site / "sitemap.xml")
    with pytest.raises(ValueError, match="symlink"):
        rebase(site)
