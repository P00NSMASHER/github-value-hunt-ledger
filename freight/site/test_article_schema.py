"""Build-level Article JSON-LD, canonical and source-boundary regressions."""
from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from freight.site import build as builder
from freight.site.article_schema import EDITORIAL_GUIDES, LEGACY_BASE, embed_article_schema
from freight.site.rebase_public_urls import NEW_BASE, rebase


def article_nodes(source: str) -> list[dict]:
    scripts = re.findall(r'<script\s+type="application/ld\+json">([\s\S]*?)</script>', source)
    return [data for script in scripts for data in [json.loads(script)]
            if data.get("@type") == "Article"]


class ArticleSchemaTests(unittest.TestCase):
    def test_exact_guide_registry_and_exclusions(self):
        self.assertEqual(len(EDITORIAL_GUIDES), 15)
        self.assertTrue(EDITORIAL_GUIDES <= set(builder.PUBLIC_CONTACT_PAGES))
        self.assertNotIn("index.html", EDITORIAL_GUIDES)
        self.assertNotIn("freight-audit-services.html", EDITORIAL_GUIDES)
        self.assertNotIn("recovery-status-example.html", EDITORIAL_GUIDES)

    def test_real_build_has_one_truthful_article_on_guides_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = builder.build(Path(temporary) / "site", "sales@freightfixture.com", True)
            for page in (*builder.PUBLIC_CONTACT_PAGES, "recovery-status-example.html"):
                content = (output / page).read_text(encoding="utf-8")
                nodes = article_nodes(content)
                if page not in EDITORIAL_GUIDES:
                    self.assertEqual(nodes, [], page)
                    continue
                self.assertEqual(len(nodes), 1, page)
                article = nodes[0]
                canonical = LEGACY_BASE + page
                self.assertEqual(article["@id"], canonical + "#article")
                self.assertEqual(article["mainEntityOfPage"]["@id"], canonical)
                self.assertEqual(article["publisher"]["name"], "RETALLY")
                self.assertEqual(article["author"]["name"], "RETALLY")
                self.assertIn(canonical, content)
                self.assertNotIn("datePublished", article)
                self.assertNotIn("aggregateRating", article)
                self.assertNotIn("offers", article)

    def test_cloudflare_bundle_rebase_corrects_article_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = builder.build(Path(temporary) / "site", "sales@freightfixture.com", True)
            rebase(output)
            for page in EDITORIAL_GUIDES:
                content = (output / page).read_text(encoding="utf-8")
                article, = article_nodes(content)
                url = NEW_BASE + page.removesuffix(".html")
                self.assertEqual(article["@id"], url + "#article", page)
                self.assertEqual(article["mainEntityOfPage"]["@id"], url, page)
                self.assertTrue(article["image"].startswith(NEW_BASE + "assets/"), page)
                self.assertEqual(article["publisher"]["url"], NEW_BASE)

    def test_unexpected_canonical_and_duplicate_article_fail_closed(self):
        page = "freight-audit-methodology.html"
        source = (
            '<head><title>Freight Audit | RETALLY</title>'
            '<meta name="description" content="A verifiable sample process.">'
            f'<link rel="canonical" href="{LEGACY_BASE}{page}">'
            f'<meta property="og:image" content="{LEGACY_BASE}assets/photo.webp">'
            '</head><body>Original body</body>'
        )
        self.assertIn('"@type":"Article"', embed_article_schema(source, page))
        with self.assertRaisesRegex(ValueError, "canonical"):
            embed_article_schema(source.replace(LEGACY_BASE + page, "https://wrong.example/"), page)
        with self.assertRaisesRegex(ValueError, "duplicate Article"):
            embed_article_schema(embed_article_schema(source, page), page)
        self.assertEqual(embed_article_schema(source, "index.html"), source)


if __name__ == "__main__":
    unittest.main()
