"""SEO/identity tests for RETALLY Group and RecoveryWorks. No invented registration claims."""
import json
import tempfile
import unittest
from pathlib import Path
from html.parser import HTMLParser
from company_sites.build import build

ROOT = Path(__file__).resolve().parent

class ScriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self._attrs = None
        self._data = ""
    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self._attrs = dict(attrs)
            self._data = ""
    def handle_data(self, data):
        if self._attrs is not None:
            self._data += data
    def handle_endtag(self, tag):
        if tag == "script" and self._attrs is not None:
            self.scripts.append((self._attrs, self._data))
            self._attrs = None

class PublicIdentityTests(unittest.TestCase):
    def test_group_and_recoveryworks_have_truthful_indexable_jsonld(self):
        expected = {
            "group": {"Organization", "WebSite"},
            "recoveryworks": {"Service", "WebSite", "Organization"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            for company, types in expected.items():
                with self.subTest(company=company):
                    out = build(company, Path(tmp) / company)
                    html = (out / "index.html").read_text(encoding="utf-8")
                    parser = ScriptParser()
                    parser.feed(html)
                    ld = [json.loads(data) for attrs, data in parser.scripts
                          if attrs.get("type") == "application/ld+json"]
                    self.assertEqual(len(ld), 1)
                    nodes = ld[0].get("@graph", [ld[0]])
                    self.assertEqual({n["@type"] for n in nodes}, types)
                    self.assertEqual(ld[0]["@context"], "https://schema.org")
                    canonical = "https://group.retallyrecovery.com/" if company == "group" else "https://recoveryworks.retallyrecovery.com/"
                    self.assertTrue(all(n.get("url", canonical).startswith(canonical) for n in nodes))
                    for n in nodes:
                        self.assertNotIn("legalName", n, "Do not invent a registered legal entity")
                        self.assertNotIn("aggregateRating", n, "Do not invent reviews")
                    if company == "group":
                        organization = next(n for n in nodes if n["@type"] == "Organization")
                        self.assertEqual(organization["name"], "RETALLY Group")
                        self.assertEqual(organization["logo"], canonical + "assets/brand/retally-emblem-approved.png")
                        self.assertTrue((out / "assets/brand/retally-emblem-approved.png").is_file())
                        self.assertIn('href="/assets/brand/retally-emblem-approved.png"', html)
                    else:
                        service = next(n for n in nodes if n["@type"] == "Service")
                        self.assertEqual(service["name"], "RETALLY RecoveryWorks")
                        self.assertIn("vendor overpayment", service["description"].lower())
                        self.assertIn("missing supplier credits", service["description"].lower())
                        self.assertNotIn("price", service)
                        self.assertNotIn("offers", service)
    def test_no_executable_inline_script_in_recoveryworks(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = build("recoveryworks", Path(tmp) / "recoveryworks")
            for html_file in out.rglob("*.html"):
                parser = ScriptParser()
                parser.feed(html_file.read_text(encoding="utf-8"))
                self.assertTrue(all(a.get("type") == "application/ld+json" and "src" not in a
                                    for a, _ in parser.scripts))
if __name__ == "__main__":
    unittest.main()
