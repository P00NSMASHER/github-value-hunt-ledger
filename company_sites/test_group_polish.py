"""RETALLY Group visual regression checks; no enquiry contract changes."""
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from company_sites.build import build


class BusinessCards(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.cards = []
        self.visuals = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        if tag == "article" and "company-card" in classes:
            self.current = next((name for name in (
                "freight", "recoveryworks", "permitplate", "capturebrief"
            ) if name in classes), None)
            self.cards.append(self.current)
        if self.current and tag == "div" and "card-visual" in classes:
            self.visuals.append(self.current)
        if self.current and tag == "img":
            self.images[self.current] = attrs

    def handle_endtag(self, tag):
        if tag == "article":
            self.current = None

    images = None


class GroupPolishTests(unittest.TestCase):
    def test_four_businesses_use_approved_logo_artwork(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = build("group", Path(tmp) / "group")
            html = (output / "index.html").read_text(encoding="utf-8")
            cards = BusinessCards()
            cards.images = {}
            cards.feed(html)
            self.assertEqual(
                ["freight", "recoveryworks", "permitplate", "capturebrief"],
                cards.cards
            )
            self.assertEqual(cards.cards, cards.visuals)
            expected = {
                "freight": "freightrecovery-emblem.webp",
                "recoveryworks": "recoveryos-emblem.webp",
                "permitplate": "permitplate-emblem.webp",
                "capturebrief": "capturebrief-emblem.webp",
            }
            for company, filename in expected.items():
                img = cards.images[company]
                self.assertEqual("/assets/brand/" + filename, img["src"])
                self.assertIn("native-company-emblem", img["class"])
                self.assertTrue(img["alt"].strip())
                self.assertTrue((output / img["src"].lstrip("/")).is_file())
            self.assertNotIn('src="/assets/recoveryworks.webp"', html)
            self.assertIn("Shared recovery software", html)
            self.assertIn("group-enquiry", html)
            self.assertIn('aria-label="RETALLY Group home"', html)
            self.assertIn("↗︎", html)

    def test_polished_style_keeps_reduced_motion_and_touch_accessibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = build("group", Path(tmp) / "group")
            css = (output / "site.css").read_text(encoding="utf-8")
            for marker in (
                ".card-visual", ".company-card:hover", ".approved-brand-software",
                ".contact-panel.enquiry-card", "prefers-reduced-motion:reduce",
                "focus-visible", "object-fit:contain", "background-clip:text"
            ):
                self.assertIn(marker, css)
            self.assertNotIn("@import", css)


if __name__ == "__main__":
    unittest.main()
