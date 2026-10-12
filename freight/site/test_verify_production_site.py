"""Pure fixture checks; network access belongs only to explicit live smoke runs."""
import unittest
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


if __name__ == "__main__":
    unittest.main()
