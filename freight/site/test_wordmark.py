"""Approved wordmark display and first-party publication boundaries."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from freight.site.wordmark import embed_approved_wordmark
from company_sites.build import build as build_company

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "freight/site/assets/brand/retally-wordmark-approved.png"
MASTER_DIGEST = "08421ccd7e8b1db752002f7ea177e76c83b6ee1cae40cf8b459368ade0c4eadd"


class WordmarkTests(unittest.TestCase):
    def test_approved_master_is_unchanged(self):
        self.assertEqual(hashlib.sha256(MASTER.read_bytes()).hexdigest(), MASTER_DIGEST)

    def test_inserts_in_visual_text_only(self):
        markup = (
            '<!doctype html><html><head><title>RETALLY</title>'
            '<meta name="description" content="RETALLY"></head><body>'
            '<nav><a href="/RETALLY">RETALLY Group</a></nav>'
            '<p>Operated by RETALLY</p>'
            '<p>RETALLY ' + "offers straightforward services. " * 8 + '</p>'
            '<label for="agreed">RETALLY consent</label>'
            '<select><option value="RETALLY">RETALLY Group</option></select>'
            '<script>const title="RETALLY";</script>'
            '<footer>© 2026 RETALLY</footer>'
            '</body></html>'
        )
        result = embed_approved_wordmark(markup, "/assets/brand/retally-wordmark-approved.png")
        self.assertEqual(2, result.count('class="retally-wordmark"'))
        self.assertIn('<title>RETALLY</title>', result)
        self.assertIn('href="/RETALLY"', result)
        self.assertIn('value="RETALLY">RETALLY Group</option>', result)
        self.assertIn('RETALLY consent</label>', result)
        self.assertIn('const title="RETALLY"', result)
        self.assertIn('© 2026 RETALLY', result)
        self.assertEqual(result, embed_approved_wordmark(result, "/assets/brand/retally-wordmark-approved.png"))

    def test_group_and_recoveryworks_include_exact_master(self):
        with tempfile.TemporaryDirectory() as tmp:
            for company in ("group", "recoveryworks"):
                with self.subTest(company=company):
                    output = build_company(company, Path(tmp) / company)
                    wordmark = output / "assets/brand/retally-wordmark-approved.png"
                    self.assertEqual(wordmark.read_bytes(), MASTER.read_bytes())
                    for file in output.rglob("*.html"):
                        html = file.read_text(encoding="utf-8")
                        self.assertIn('class="retally-wordmark"', html)
                        self.assertIn('alt="RETALLY"', html)
                        self.assertIn('<title>', html)
                        self.assertIn('RETALLY', html)  # Metadata and machine names remain text.


if __name__ == "__main__":
    unittest.main()
