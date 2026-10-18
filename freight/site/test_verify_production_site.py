"""Pure fixture checks; network access belongs only to explicit live smoke runs."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from freight.site.internal_links import (
    CANONICAL, InternalLinkError, internal_destinations,
    validate_bundle_links, validate_live_links,
)
from email.message import Message

from freight.site.verify_production_site import (
    APPROVED_MEDIA, LiveAuditError, ensure_html, ensure_logo,
    ensure_security_headers,
)


class ProductionSmokeInvariantTests(unittest.TestCase):
    def headers(self, *, hsts="max-age=86400", nosniff="nosniff", csp=True):
        h = Message()
        h["Strict-Transport-Security"] = hsts
        h["X-Content-Type-Options"] = nosniff
        h["Content-Security-Policy"] = (
            "default-src 'self'; object-src 'none'; frame-ancestors 'none'"
            if csp else "default-src 'self'"
        )
        return h

    def test_expected_staged_security_policy(self):
        ensure_security_headers(self.headers())
        for args in (
            {"hsts": ""},
            {"hsts": "max-age=3600"},
            {"nosniff": ""},
            {"csp": False},
        ):
            with self.subTest(args=args), self.assertRaises(LiveAuditError):
                ensure_security_headers(self.headers(**args))

    def test_corrupted_published_logo_is_detected(self):
        for path in APPROVED_MEDIA:
            with self.subTest(path=path), self.assertRaises(LiveAuditError):
                ensure_logo(b"\x89PNG\r\n\x1a\n" + b"not-the-approved-art", path)

    def test_canonical_and_legacy_identity_gate(self):
        url = "https://www.retallyrecovery.com/freight-audit-services"
        good = '<link rel="canonical" href="' + url + '">'
        ensure_html(good, url)
        for bad in (
            good.replace(url, "https://p00nsmasher.github.io/"),
            good + '<img src="assets/brand/retally-emblem.webp">',
        ):
            with self.assertRaises(LiveAuditError):
                ensure_html(bad, url)


class InternalHyperlinkAuditTests(unittest.TestCase):
    def test_resolve_internal_links_without_visiting_outbound_urls(self):
        markup = (
            '<a href="/">Home</a><a href="#section">Section</a>'
            '<a href="/about?utm_source=test#overview">About</a>'
            '<a href="mailto:team@example.com">Email</a>'
            '<a href="https://other.example.com/">Off-site</a>'
        )
        self.assertEqual(
            internal_destinations(markup, CANONICAL + "trust"),
            {
                CANONICAL,
                CANONICAL + "trust",
                CANONICAL + "about?utm_source=test",
            },
        )

    def test_bundle_passes_real_pretty_urls_and_downloads(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text(
                '<a href="/about">About</a><a href="#main">Main</a>'
            )
            (root / "about.html").write_text(
                '<a href="/">Home</a><a href="/guide.pdf?download=1">Guide</a>'
            )
            (root / "guide.pdf").write_bytes(b"test download fixture")
            stats = validate_bundle_links(root)
            self.assertEqual(stats["pages"], 2)
            self.assertEqual(stats["destinations"], 3)

    def test_bundle_rejects_missing_destinations_and_host_aliases(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = root / "index.html"
            index.write_text('<a href="/missing">Missing page</a>')
            with self.assertRaisesRegex(InternalLinkError, "Missing published internal link"):
                validate_bundle_links(root)
            index.write_text('<a href="http://retallyrecovery.com/">Old alias</a>')
            with self.assertRaisesRegex(InternalLinkError, "Noncanonical internal link"):
                validate_bundle_links(root)

    def test_bundle_rejects_business_mailto_without_cloudflare_exemption(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            html = '<a href="mailto:jay@retallyrecovery.com">Business contact</a>'
            (root / "index.html").write_text(html)
            with self.assertRaisesRegex(InternalLinkError, "Cloudflare 404"):
                validate_bundle_links(root)
            (root / "index.html").write_text(
                "<!--email_off-->" + html + "<!--/email_off-->"
            )
            self.assertEqual(validate_bundle_links(root)["pages"], 1)

    def test_recipientless_share_draft_requires_narrow_cloudflare_exemption(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "index.html"
            draft = '<a href="mailto:?subject=Free%20Guide&amp;body=Hello">Prepare email draft</a>'
            page.write_text(draft, encoding="utf-8")
            with self.assertRaisesRegex(InternalLinkError, "recipientless share draft creates Cloudflare 404"):
                validate_bundle_links(root)
            page.write_text("<!--email_off-->" + draft + "<!--/email_off-->", encoding="utf-8")
            self.assertEqual(validate_bundle_links(root)["pages"], 1)

    def test_live_links_reuse_sitemap_checks_and_fetch_unique_destinations(self):
        calls = []
        about = CANONICAL + "about"

        def fake_fetch(url):
            calls.append(url)
            self.assertEqual(url, about)
            return 200, {}, b""

        stats = validate_live_links(
            {
                CANONICAL: '<a href="/about">About</a><a href="/#main">Home</a>',
                CANONICAL + "trust": '<a href="/about#team">About again</a>',
            },
            fake_fetch, known_good={CANONICAL},
        )
        self.assertEqual(calls, [about])
        self.assertEqual(stats, {"destinations": 2, "redirected_destinations": 0})

    def test_live_links_reject_404_with_source_context(self):
        def fake_fetch(url):
            return 404, {}, b"Not found"

        with self.assertRaisesRegex(InternalLinkError, "Broken internal link.*HTTP 404"):
            validate_live_links(
                {CANONICAL: '<a href="/unpublished">Broken</a>'},
                fake_fetch, known_good={CANONICAL},
            )

    def test_live_links_follow_bounded_local_redirects(self):
        def fake_fetch(url):
            if url == CANONICAL + "old":
                return 308, {"Location": "/new"}, b""
            if url == CANONICAL + "new":
                return 200, {}, b""
            self.fail(f"Unexpected request: {url}")

        stats = validate_live_links(
            {CANONICAL: '<a href="/old">Old public route</a>'},
            fake_fetch, known_good={CANONICAL},
        )
        self.assertEqual(stats["redirected_destinations"], 1)

    def test_live_links_never_follow_external_redirects(self):
        def fake_fetch(url):
            return 302, {"Location": "https://example.com/elsewhere"}, b""

        with self.assertRaisesRegex(InternalLinkError, "Unsafe internal redirect"):
            validate_live_links(
                {CANONICAL: '<a href="/old">Redirect</a>'},
                fake_fetch, known_good={CANONICAL},
            )


if __name__ == "__main__":
    unittest.main()
