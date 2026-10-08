from pathlib import Path

import pytest

from freight.site.rebase_public_urls import OLD_BASE, NEW_BASE, rebase


def test_rebase_changes_only_generated_public_text(tmp_path: Path):
    (tmp_path / "index.html").write_text(
        f'<link rel="canonical" href="{OLD_BASE}"><a href="about.html">About</a>',
        encoding="utf-8",
    )
    (tmp_path / "sitemap.xml").write_text(OLD_BASE + "about.html", encoding="utf-8")
    binary = b"\\x00" + OLD_BASE.encode() + b"\\xff"
    (tmp_path / "image.webp").write_bytes(binary)
    assert rebase(tmp_path) == 2
    assert NEW_BASE in (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "href=\"about.html\"" in (tmp_path / "index.html").read_text(encoding="utf-8")
    assert (tmp_path / "image.webp").read_bytes() == binary


def test_rebase_refuses_missing_original_url(tmp_path: Path):
    (tmp_path / "index.html").write_text("no original site URL", encoding="utf-8")
    with pytest.raises(ValueError, match="No previous absolute site URLs"):
        rebase(tmp_path)
