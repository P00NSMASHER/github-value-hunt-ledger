"""Release checks for the restored freight homepage and old portfolio links."""
from hashlib import sha256
from html.parser import HTMLParser
import re
import shutil
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET

import pytest

from freight.site import cloudflare_build
from freight.site.group import build as group_build
from freight.site.group.build import ADDED_FILES, ARCHIVES, LEGACY_ROUTES, ROUTES
from freight.site.rebase_public_urls import NEW_BASE, validate_cloudflare_seo


@pytest.fixture(scope="module")
def release(tmp_path_factory):
    root = tmp_path_factory.mktemp("freight-home-restoration")
    original = {}

    def capture_and_restore(bundle):
        # Capture the production freight builder output, including its CSP,
        # contact, commercial terms and chat, before the migration step runs.
        original["home"] = (bundle / "index.html").read_text()
        original["sitemap"] = (bundle / "sitemap.xml").read_bytes()
        original["styles"] = {name: (bundle / name).read_bytes()
                              for name in ("site.css", "foundry.css", "site.js", "commercial-config.js")}
        group_build.build_group(bundle)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(cloudflare_build, "REPO", root)
        patch.setattr(cloudflare_build, "build_group", capture_and_restore)
        patch.setenv("FREIGHT_CONTACT_EMAIL", "jay@retallyrecovery.com")
        patch.setenv("FREIGHT_CONTACT_VERIFIED", "1")
        original["bundle"] = cloudflare_build.build(root / "public")
    return original


@pytest.fixture(scope="module")
def bundle(release):
    return release["bundle"]


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.refs = []
        self.ids = set()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        self.elements.append((tag, attrs))
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag in {"a", "img", "script", "link"}:
            reference = attrs.get("href") if tag in {"a", "link"} else attrs.get("src")
            if reference:
                self.refs.append((tag, reference))
        for key in ("srcset", "imagesrcset"):
            for candidate in attrs.get(key, "").split(","):
                if candidate.strip():
                    self.refs.append(("image", candidate.strip().split()[0]))


def _without_design_versions(html):
    return re.sub(r'((?:href|src)="/?(?:foundry\.css|site\.js))\?[^"#]*', r'\1', html)


def test_original_freight_home_structure_and_assets_survive(release):
    bundle = release["bundle"]
    restored = (bundle / "index.html").read_text()
    # The only composition changes are the explicitly requested group footer
    # link and a missing fallback anchor. No captured/duplicated HTML fixture.
    without_additions = restored.replace(group_build.GROUP_FOOTER_LINK, "").replace(group_build.CONTACT_ANCHOR, "")
    assert _without_design_versions(without_additions) == _without_design_versions(release["home"])
    for name, original in release["styles"].items():
        assert (bundle / name).read_bytes() == original
    assert 'class="home-simple"' in restored
    assert '<span class="hero-phrase">Find it.</span>' in restored
    assert 'class="portfolio-bar"' not in restored
    assert "group.css" not in restored and "group.js" not in restored
    assert restored.count(group_build.GROUP_FOOTER_LINK) == 1


def test_secure_freight_intake_and_anchors_remain_at_root(bundle):
    home = (bundle / "index.html").read_text()
    page = Page(home)
    assert {"start-audit", "auditForm", "pricing", "contact-pending", "contactStatus"} <= page.ids
    assert 'href="' + NEW_BASE + '"' in home
    assert 'https://challenges.cloudflare.com' in home
    assert "connect-src 'self'" in home
    assert "freight-contact-email" in home and "jay@retallyrecovery.com" in home
    assert "<!--email_off-->" in home
    assert any(tag == "script" and urlsplit(ref).path == "site.js" for tag, ref in page.refs)
    assert any(tag == "script" and urlsplit(ref).path == "commercial-config.js" for tag, ref in page.refs)
    assert {attrs["id"] for tag, attrs in page.elements if tag == "form"} == {"auditForm"}


def test_legacy_recovery_fallback_preserves_freight_hashes_and_canonical(bundle):
    home = Page((bundle / "index.html").read_text())
    html = (bundle / "recovery/index.html").read_text()
    legacy = Page(html)
    assert home.ids == legacy.ids
    assert f'<link rel="canonical" href="{NEW_BASE}">' in html
    assert '<meta name="robots" content="noindex,follow">' in html
    assert "group.css" not in html and "group.js" not in html
    assert 'src="/assets/images/' in html and 'srcset="/assets/images/' in html
    for tag, reference in legacy.refs:
        if not urlsplit(reference).scheme:
            assert reference.startswith(("/", "#")), (tag, reference)


def test_only_established_successors_receive_redirects(bundle):
    expected = {
        "recovery": NEW_BASE,
        "capturebrief": "https://capturebrief.retallyrecovery.com/",
        "permitplate": "https://permitplate.retallyrecovery.com/",
        "contact": "https://group.retallyrecovery.com/#contact",
        "recoveryos": "https://recoveryworks.retallyrecovery.com/",
    }
    rules = [line.split() for line in (bundle / "_redirects").read_text().splitlines()
             if line and not line.startswith("#")]
    assert {(path, target, code) for path, target, code in rules} == {
        (path, target, "301") for route, target in expected.items()
        for path in (f"/{route}", f"/{route}/", f"/{route}/index.html")
    }
    # A Location without a fragment preserves old incoming freight anchors.
    assert all(not urlsplit(target).fragment for path, target, _ in rules if path.startswith("/recovery/") or path == "/recovery")
    for route, target in expected.items():
        if route != "recovery":
            html = (bundle / route / "index.html").read_text()
            assert f'href="{target}"' in html
            assert "noindex,follow" in html
            assert "<form" not in html and "buy.stripe.com" not in html


def test_retired_experiments_are_archived_without_a_successor_claim(bundle):
    redirects = (bundle / "_redirects").read_text()
    assert set(ARCHIVES) == {"rehabsignal", "sheetharbor", "app-factory", "data-services", "scopesignal", "contractor-quote-recovery", "resonance", "market-surveillance"}
    for route, name in ARCHIVES.items():
        html = (bundle / route / "index.html").read_text()
        assert f"<h1>{name}</h1>" in html
        assert "Archived project" in html and "noindex,follow" in html
        assert "does not offer a service or designate a replacement provider" in html
        assert 'href="https://group.retallyrecovery.com/#businesses"' in html
        assert f'<link rel="canonical" href="{NEW_BASE}{route}/">' in html
        assert f"/{route} " not in redirects and f"/{route}/ " not in redirects
        assert "<form" not in html and "<script" not in html
        assert "mailto:" not in html and "buy.stripe.com" not in html


def test_successor_links_resolve_directly_without_changing_unrelated_urls(tmp_path):
    page = tmp_path / "index.html"
    page.write_text('''<a href="/recovery/#start-audit">Freight</a>
<a href="capturebrief/?source=old&amp;campaign=launch#sample">Sample</a>
<a href="https://www.retallyrecovery.com/permitplate/index.html#nyc">NYC</a>
<a href="/recoveryos/">Other recovery</a><a href="/contact/">Contact</a>
<a href="/rehabsignal/">Archive</a><a href="/recoveryos/guide.pdf">Guide</a>
<a href="#pricing">Pricing</a><a href="mailto:jay@retallyrecovery.com">Email</a>
<link rel="canonical" href="https://www.retallyrecovery.com/">''')
    group_build._point_links_at_successors(tmp_path)
    html = page.read_text()
    assert f'href="{NEW_BASE}#start-audit"' in html
    assert 'href="https://capturebrief.retallyrecovery.com/?source=old&amp;campaign=launch#sample"' in html
    assert 'href="https://permitplate.retallyrecovery.com/#nyc"' in html
    assert 'href="https://recoveryworks.retallyrecovery.com/"' in html
    assert 'href="https://group.retallyrecovery.com/#contact"' in html
    for unchanged in ("/rehabsignal/", "/recoveryos/guide.pdf", "#pricing", "mailto:jay@retallyrecovery.com"):
        assert f'href="{unchanged}"' in html
    assert f'<link rel="canonical" href="{NEW_BASE}">' in html


def test_compatibility_files_are_explicit_and_absent_from_sitemap(release):
    bundle = release["bundle"]
    assert ROUTES == ()
    assert len(LEGACY_ROUTES) == 12 and len(ADDED_FILES) == 13
    assert all((bundle / file).is_file() for file in ADDED_FILES)
    assert not (bundle / "group.css").exists()
    assert not (bundle / "group.js").exists()
    assert not (bundle / "assets/group").exists()
    assert len([path for path in bundle.rglob("*") if path.is_file()]) == cloudflare_build.EXPECTED_FILES
    assert (bundle / "sitemap.xml").read_bytes() == release["sitemap"]
    assert validate_cloudflare_seo(bundle, ROUTES) > 0
    urls = {element.text for element in ET.fromstring((bundle / "sitemap.xml").read_text()).iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")}
    assert not urls.intersection(NEW_BASE + route + "/" for route in LEGACY_ROUTES + ("recoveryos",))


def test_restored_and_legacy_local_assets_and_fragments_resolve(bundle):
    for route in ("",) + tuple(route + "/" for route in LEGACY_ROUTES) + ("recoveryos/",):
        source = bundle / route / "index.html"
        page = Page(source.read_text())
        for tag, reference in page.refs:
            url = urlsplit(urljoin(NEW_BASE + route, reference))
            if url.scheme != "https" or url.netloc != "www.retallyrecovery.com":
                continue
            target = bundle / url.path.lstrip("/")
            if url.path.endswith("/"):
                target = target / "index.html"
            elif not target.suffix:
                target = target.with_suffix(".html")
            assert target.is_file(), (source, reference, target)
            if url.fragment and tag == "a" and target.suffix == ".html":
                assert url.fragment in Page(target.read_text()).ids, (route, reference)


def test_returning_visitors_receive_current_freight_assets(bundle, tmp_path):
    seen = set()
    for source in bundle.rglob("*.html"):
        for _, reference in Page(source.read_text()).refs:
            url = urlsplit(reference)
            name = url.path.removeprefix("/")
            if not url.netloc and name in {"foundry.css", "site.js"}:
                assert url.query == "v=" + sha256((bundle / name).read_bytes()).hexdigest()[:16]
                seen.add(name)
    assert seen == {"foundry.css", "site.js"}
    for name in ("foundry.css", "site.js", "index.html"):
        shutil.copyfile(bundle / name, tmp_path / name)
    before = (tmp_path / "index.html").read_text()
    with (tmp_path / "foundry.css").open("a") as changed:
        changed.write("\n/* later freight design revision */\n")
    group_build._version_design_assets(tmp_path)
    after = (tmp_path / "index.html").read_text()
    css_ref = lambda html: next(ref for _, ref in Page(html).refs if urlsplit(ref).path == "foundry.css")
    assert css_ref(before) != css_ref(after)
    assert {ref for tag, ref in Page(before).refs if tag == "script"} == {ref for tag, ref in Page(after).refs if tag == "script"}
