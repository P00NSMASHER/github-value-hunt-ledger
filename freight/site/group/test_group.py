"""Release checks for migrated pages, links, metadata and freight continuity."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET

import pytest

from freight.site import cloudflare_build
from freight.site.group.build import ROUTES, ADDED_FILES
from freight.site.group.catalog import BUSINESSES
from freight.site.rebase_public_urls import NEW_BASE, validate_cloudflare_seo


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    root = tmp_path_factory.mktemp("group-release")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(cloudflare_build, "REPO", root)
        patch.setenv("FREIGHT_CONTACT_EMAIL", "jay@retallyrecovery.com")
        patch.setenv("FREIGHT_CONTACT_VERIFIED", "1")
        yield cloudflare_build.build(root / "public")


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.refs = []
        self.ids = set()
        self.h1_count = 0
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "h1":
            self.h1_count += 1
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag in {"a", "img", "script", "link"}:
            ref = attrs.get("href") if tag in {"a", "link"} else attrs.get("src")
            if ref:
                self.refs.append((tag, ref))
        for key in ("srcset", "imagesrcset"):
            for candidate in attrs.get(key, "").split(","):
                if candidate.strip():
                    self.refs.append(("image", candidate.strip().split()[0]))


def target_file(root, path):
    target = root / path.lstrip("/")
    if path.endswith("/"):
        return target / "index.html"
    return target if target.suffix else target.with_suffix(".html")


def test_every_business_has_a_unique_discoverable_page(bundle):
    assert len(BUSINESSES) == len({b["slug"] for b in BUSINESSES}) == 11
    home = (bundle / "index.html").read_text()
    for b in BUSINESSES:
        assert f'href="/{b["slug"]}/"' in home
        assert (bundle / b["slug"] / "index.html").is_file()
    assert all((bundle / f).is_file() for f in ADDED_FILES)
    assert len([p for p in bundle.rglob("*") if p.is_file()]) == cloudflare_build.EXPECTED_FILES


def test_metadata_sitemap_and_asset_paths_match_actual_output(bundle):
    assert validate_cloudflare_seo(bundle, ROUTES) >= 40
    for route in ("",) + tuple(r + "/" for r in ROUTES):
        source = bundle / route / "index.html"
        page = Page(source.read_text())
        assert page.h1_count == 1
        for tag, ref in page.refs:
            url = urlsplit(urljoin(NEW_BASE + route, ref))
            if url.scheme != "https" or url.netloc != "www.retallyrecovery.com":
                continue
            target = target_file(bundle, url.path)
            assert target.is_file(), (source, ref, target)
            if url.fragment and tag == "a" and target.suffix == ".html":
                assert url.fragment in Page(target.read_text()).ids, (route, ref)


def test_freight_intake_is_preserved_on_its_own_route(bundle):
    freight = (bundle / "recovery/index.html").read_text()
    for marker in ('id="start-audit"', 'id="auditForm"', '/commercial-config.js', '/site.js',
                   'https://challenges.cloudflare.com', 'freight-contact-email',
                   'jay@retallyrecovery.com', '<!--email_off-->'):
        assert marker in freight, marker
    assert 'href="' + NEW_BASE + 'recovery/"' in freight
    assert 'src="/assets/images/' in freight
    assert 'srcset="/assets/images/' in freight


def test_unavailable_products_do_not_gain_purchase_or_upload_flows(bundle):
    for b in BUSINESSES:
        if b["status"] in {"Research", "Research prototype", "In development", "Private evaluation", "Preview available"}:
            html = (bundle / b["slug"] / "index.html").read_text()
            assert b["status"] in html
            assert "mailto:jay@retallyrecovery.com?subject=" in html
            assert "buy.stripe.com" not in html
            assert "<form" not in html
            assert 'type="file"' not in html
    for path in bundle.rglob("*.html"):
        assert "jayp19386@" not in path.read_text().lower()


def test_nested_canonical_regression_is_rejected(bundle, tmp_path):
    # A wrong nested canonical must fail even if the root pages still look good.
    import shutil
    copy = tmp_path / "copy"
    shutil.copytree(bundle, copy)
    page = copy / "capturebrief/index.html"
    page.write_text(page.read_text().replace(NEW_BASE + "capturebrief/", NEW_BASE))
    with pytest.raises(ValueError, match="self-referencing canonical"):
        validate_cloudflare_seo(copy, ROUTES)


def test_group_business_email_cannot_be_rewritten_to_cloudflare_404(bundle):
    # Cloudflare rewrites bare email text as well as mailto anchors. The zone
    # keeps obfuscation enabled; approved business addresses use its opt-out.
    import re
    for route in ("",) + tuple(r + "/" for r in ROUTES if r != "recovery"):
        html = (bundle / route / "index.html").read_text()
        outside_opt_out = re.sub(r"<!--email_off-->.*?<!--/email_off-->", "", html, flags=re.S)
        assert "jay@retallyrecovery.com" not in outside_opt_out, route
