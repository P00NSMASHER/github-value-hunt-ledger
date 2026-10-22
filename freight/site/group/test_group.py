"""Release checks for migrated pages, links, metadata and freight continuity."""
from html.parser import HTMLParser
from hashlib import sha256
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import re
import shutil
import xml.etree.ElementTree as ET

import pytest

from freight.site import cloudflare_build
from freight.site.asset_integrity import AssetIntegrityError, webp_dimensions
from freight.site.group import build as group_build
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
        self.elements = []
        self.texts = []
        self.parents = []
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        self.elements.append((tag, attrs, tuple(self.parents)))
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.parents.append((tag, attrs))
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

    def handle_endtag(self, tag):
        for i in range(len(self.parents) - 1, -1, -1):
            if self.parents[i][0] == tag:
                del self.parents[i:]
                break

    def handle_data(self, text):
        self.texts.append((text, tuple(self.parents)))


def within(parents, *, tag=None, element_id=None, css_class=None):
    return any((tag is None or name == tag)
               and (element_id is None or attrs.get("id") == element_id)
               and (css_class is None or css_class in attrs.get("class", "").split())
               for name, attrs in parents)


# This reviewed contract is deliberately independent of the production allowlist.
REVIEWED_IMAGES = {
    "hero-768.webp": (768, 512),
    "hero-1536.webp": (1536, 1024),
    "digital-768.webp": (768, 512),
    "digital-1536.webp": (1536, 1024),
    "research-768.webp": (768, 512),
    "research-1536.webp": (1536, 1024),
    "restaurant-768.webp": (768, 512),
    "restaurant-1536.webp": (1536, 1024),
    "tools-768.webp": (768, 512),
    "tools-1536.webp": (1536, 1024),
}


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
            assert 'href="/contact/?business=' + b["slug"] + '"' in html
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


def test_group_photography_matches_reviewed_assets_and_page_budget(bundle):
    source = group_build.SOURCE / "assets"
    published = bundle / "assets/group"
    assert set(group_build.IMAGE_NAMES) == set(REVIEWED_IMAGES)
    assert {p.name for p in source.iterdir()} == set(REVIEWED_IMAGES)
    assert {p.name for p in published.iterdir()} == set(REVIEWED_IMAGES)
    assert {f.removeprefix("assets/group/") for f in ADDED_FILES
            if f.startswith("assets/group/")} == set(REVIEWED_IMAGES)
    for filename, geometry in REVIEWED_IMAGES.items():
        original = source / filename
        assert original.is_file() and not original.is_symlink()
        data = (published / filename).read_bytes()
        assert data == original.read_bytes()
        assert 25_000 <= len(data) <= 450_000, filename
        assert webp_dimensions(data) == geometry, filename

    used = set()
    for html in bundle.rglob("*.html"):
        page = Page(html.read_text())
        for _, ref in page.refs:
            if ref.startswith("/assets/group/"):
                filename = ref.removeprefix("/assets/group/")
                assert filename in REVIEWED_IMAGES, (html, ref)
                used.add(filename)
        for tag, attrs, parents in page.elements:
            if tag == "img" and attrs.get("src", "").startswith("/assets/group/"):
                assert (int(attrs["width"]), int(attrs["height"])) == (1536, 1024)
                assert "alt" in attrs
                assert attrs["alt"].strip() or any(a.get("aria-hidden") == "true" for _, a in parents)
                assert attrs.get("loading") in {"eager", "lazy"}
                assert attrs.get("sizes")
                name = Path(attrs["src"]).name.removesuffix("-1536.webp")
                variants = {part.strip() for part in attrs.get("srcset", "").split(",")}
                assert variants == {f"/assets/group/{name}-768.webp 768w",
                                    f"/assets/group/{name}-1536.webp 1536w"}
    assert used == set(REVIEWED_IMAGES)


@pytest.mark.parametrize("fault", ["unreviewed", "symlink", "geometry", "oversize", "malformed"])
def test_group_build_rejects_unreviewed_or_invalid_photography(tmp_path, monkeypatch, fault):
    source = tmp_path / "source"
    shutil.copytree(group_build.SOURCE, source)
    image = source / "assets/research-1536.webp"
    if fault == "unreviewed":
        (source / "assets/unreviewed.png").write_bytes(b"not approved")
    elif fault == "symlink":
        image.unlink()
        image.symlink_to(group_build.SOURCE / "assets/research-1536.webp")
    elif fault == "geometry":
        image.write_bytes((source / "assets/research-768.webp").read_bytes())
    elif fault == "oversize":
        image.write_bytes(b"x" * 450_001)
    else:
        data = image.read_bytes()
        image.write_bytes(b"FAIL" + data[4:])
    monkeypatch.setattr(group_build, "SOURCE", source)
    output = tmp_path / "public"
    (output / "assets").mkdir(parents=True)
    (output / "index.html").write_text("<html><head></head><body></body></html>")
    with pytest.raises(AssetIntegrityError):
        group_build.build_group(output)


def test_contact_form_is_labelled_private_and_requires_a_saved_receipt(bundle):
    page = Page((bundle / "contact/index.html").read_text())
    forms = [attrs for tag, attrs, _ in page.elements if tag == "form"]
    assert len(forms) == 1
    assert forms[0]["id"] == "group-enquiry"
    assert not forms[0].get("action")
    assert "hidden" in forms[0]  # Direct email remains available without JavaScript.
    controls = [(tag, attrs) for tag, attrs, parents in page.elements
                if tag in {"input", "select", "textarea"}
                and within(parents, element_id="group-enquiry")]
    assert {tag for tag, _ in controls} >= {"select", "textarea"}
    for _, attrs in controls:
        assert attrs.get("type") != "file"
        assert attrs.get("id")
        assert attrs.get("aria-label") or any(text.strip() and any(tag == "label" and label.get("for") == attrs["id"]
                   for tag, label in parents) for text, parents in page.texts), attrs
    composer_copy = " ".join(text for text, parents in page.texts
                             if within(parents, element_id="group-enquiry")).lower()
    assert "draft" in composer_copy
    assert re.search(r"nothing\s+(?:is|has been)\s+sent", composer_copy)
    assert any(tag == "p" and attrs.get("role") == "status"
               for tag, attrs, parents in page.elements
               if within(parents, element_id="group-enquiry"))
    draft = next(attrs for tag, attrs, _ in page.elements
                 if tag == "a" and attrs.get("id") == "enquiry-draft")
    assert urlsplit(draft["href"]).scheme == "mailto"
    assert urlsplit(draft["href"]).path == "jay@retallyrecovery.com"
    assert ("a", "/recovery/#start-audit") in page.refs
    assert "auditForm" not in page.ids
    assert {urlsplit(ref).path for tag, ref in page.refs if tag == "script"} == {"/group.js"}
    script = (bundle / "group.js").read_text()
    assert "/api/group-inquiry" in script
    assert 'action: "retally_group"' in script
    assert 'response.status !== 202' in script
    assert 'receipt.received !== true' in script
    assert not re.search(r"\b(?:localStorage|sessionStorage|sendBeacon|WebSocket)\b", script)
    by_id = {attrs["id"]: attrs for _, attrs in controls}
    assert by_id["enquiry-message"]["maxlength"] == "800"
    assert by_id["enquiry-email"]["type"] == "email"
    assert "required" in by_id["enquiry-consent"]
    assert by_id["enquiry-consent"]["type"] == "checkbox"
    assert "checked" not in by_id["enquiry-consent"]
    assert "not confirm email delivery" in composer_copy
    assert "privately store" in composer_copy
    assert all(b["slug"] in (bundle / "contact/index.html").read_text() for b in BUSINESSES)


@pytest.mark.parametrize("slug", ["capturebrief", "permitplate"])
def test_sample_link_is_available_beside_the_product_offer(bundle, slug):
    business = next(b for b in BUSINESSES if b["slug"] == slug)
    page = Page((bundle / slug / "index.html").read_text())
    offer_links = {attrs["href"] for tag, attrs, parents in page.elements
                   if tag == "a" and within(parents, tag="aside", css_class="business-offer")}
    assert business["href"] in offer_links
    assert business["links"][0][1] in offer_links
    assert business["href"] != business["links"][0][1]


def test_homepage_features_only_the_three_available_offers(bundle):
    page = Page((bundle / "index.html").read_text())
    featured = [attrs["href"] for tag, attrs, parents in page.elements
                if tag == "a" and within(parents, element_id="businesses")]
    assert sorted(featured) == ["/capturebrief/", "/permitplate/", "/recovery/"]


def test_homepage_offer_heading_preserves_word_separation_without_layout_breaks(bundle):
    page = Page((bundle / "index.html").read_text())
    headings = [(tag, attrs, parents) for tag, attrs, parents in page.elements
                if tag == "h2" and within(parents, css_class="hero-console")]
    assert len(headings) == 1
    # Join actual text nodes without inserting spaces: otherwise this test would
    # conceal the original `you<br>like` regression when CSS hides the break.
    text = "".join(text for text, parents in page.texts
                   if within(parents, css_class="hero-console") and within(parents, tag="h2"))
    assert " ".join(text.split()) == "What would you like to move forward?"


def test_returning_visitors_receive_current_design_assets(bundle, tmp_path):
    names = {"group.css", "group.js", "foundry.css", "site.js"}
    seen = set()
    for source in bundle.rglob("*.html"):
        for tag, reference in Page(source.read_text()).refs:
            url = urlsplit(reference)
            name = url.path.removeprefix("/")
            if not url.netloc and name in names:
                expected = sha256((bundle / name).read_bytes()).hexdigest()[:16]
                assert url.query == "v=" + expected, (source, reference)
                seen.add(name)
    assert seen == names
    # A later stylesheet edit must change its URL without a manual release tag.
    for name in names:
        shutil.copyfile(bundle / name, tmp_path / name)
    shutil.copyfile(bundle / "index.html", tmp_path / "index.html")
    before = (tmp_path / "index.html").read_text()
    with (tmp_path / "group.css").open("a") as changed:
        changed.write("\n/* subsequent design revision */\n")
    group_build._version_design_assets(tmp_path)
    after = (tmp_path / "index.html").read_text()
    css_ref = lambda html: next(ref for _, ref in Page(html).refs if urlsplit(ref).path == "/group.css")
    assert css_ref(before) != css_ref(after)
    assert {ref for tag, ref in Page(before).refs if tag == "script"} == {ref for tag, ref in Page(after).refs if tag == "script"}

