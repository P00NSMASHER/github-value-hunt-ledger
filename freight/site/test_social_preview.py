"""RETALLY editorial social previews: static-source, canonical/brand safety.

These are website sharing previews, NOT claims of externally verified Meta
publication, user conversion or customer invoices.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import tempfile
import unittest

from freight.site import build as builder
from freight.site.rebase_public_urls import OLD_BASE, NEW_BASE, rebase
from freight.site.social_preview import (
    ALT, IMAGE_BY_TOPIC, WORKSHEET, WORKSHEET_DESCRIPTION,
    WORKSHEET_TITLE, embed, preview_images,
)

class HeadTags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta=[]
    def handle_starttag(self,tag,attrs):
        if tag == "meta":
            self.meta.append(dict(attrs))
    def property(self,field):
        return [x["content"] for x in self.meta if x.get("property")==field]
    def name(self,field):
        return [x["content"] for x in self.meta if x.get("name")==field]


class ShareCardTest(unittest.TestCase):
    def example(self,page="freight-invoice-audit-checklist.html"):
        content=(
            '<!doctype html><html lang="en"><head>\n'
            '<title>Freight Invoice Audit Checklist | RETALLY</title>\n'
            '<meta name="description" content="A printable evidence checklist.">\n'
            f'<link rel="canonical" href="{OLD_BASE}{page}">\n'
            '</head><body><main>Educational only</main></body></html>'
        )
        return content

    def test_exact_registry_matches_all_current_public_information_pages(self):
        topics=preview_images()
        self.assertEqual(set(topics),set(builder.PUBLIC_CONTACT_PAGES)-{"index.html"})
        self.assertEqual(len(topics),24)
        self.assertEqual(len(set(topics)),24)
        self.assertEqual(len(IMAGE_BY_TOPIC),3)
        self.assertEqual(set(ALT),set(IMAGE_BY_TOPIC))

    def test_reuse_only_allowlisted_original_public_art(self):
        topics=preview_images()
        for page,image in topics.items():
            with self.subTest(page=page):
                self.assertIn(image,builder.BINARY_SOURCE_FILES)
                self.assertTrue((builder.SOURCE/image).is_file())
                self.assertTrue(image.endswith(".webp"))
                self.assertTrue(ALT[image].strip())

    def test_worksheet_title_is_concise_and_not_a_fake_refund(self):
        self.assertEqual(WORKSHEET_TITLE,
            "RETALLY | Free Printable Freight Invoice Audit Worksheet")
        self.assertIn("anonymized",WORKSHEET_DESCRIPTION)
        self.assertIn("no refund",WORKSHEET_DESCRIPTION.lower())
        self.assertNotIn("real customer",WORKSHEET_DESCRIPTION.lower())
        self.assertNotIn("guaranteed savings",WORKSHEET_DESCRIPTION.lower())

    def test_homepage_owner_approved_meta_is_untouched(self):
        html='<head><meta property="og:title" content="Original RETALLY"></head>'
        self.assertEqual(embed(html,"index.html",available_images=set()),html)

    def test_exact_metadata_both_platforms_and_factual_alt(self):
        html=embed(self.example(),WORKSHEET,available_images=set(builder.BINARY_SOURCE_FILES))
        p=HeadTags();p.feed(html)
        for prop in ("og:title","og:description","og:site_name","og:image",
                     "og:image:alt","og:url","og:type","og:locale"):
            self.assertEqual(len(p.property(prop)),1,prop)
        for prop in ("twitter:card","twitter:title","twitter:description",
                     "twitter:image","twitter:image:alt"):
            self.assertEqual(len(p.name(prop)),1,prop)
        self.assertEqual(p.property("og:url"),[OLD_BASE+WORKSHEET])
        self.assertEqual(p.property("og:image"),p.name("twitter:image"))
        self.assertEqual(p.name("twitter:card"),["summary_large_image"])
        self.assertEqual(p.property("og:site_name"),["RETALLY"])
        self.assertEqual(p.name("twitter:title"),p.property("og:title"))
        self.assertEqual(p.name("twitter:description"),p.property("og:description"))
        self.assertEqual(p.property("og:title"),[WORKSHEET_TITLE])
        self.assertEqual(p.property("og:description"),[WORKSHEET_DESCRIPTION])
        self.assertTrue(p.property("og:image")[0].startswith(OLD_BASE+"assets/images/"))
        self.assertIn(p.property("og:image:alt")[0],ALT.values())
        self.assertNotIn("example.invalid",html)

    def test_no_silent_duplicate_share_metadata(self):
        input_html=self.example().replace("</head>",
            '<meta property="og:title" content="Already configured"></head>')
        with self.assertRaisesRegex(ValueError,"existing share card"):
            embed(input_html,WORKSHEET,available_images=set(builder.BINARY_SOURCE_FILES))

    def test_unallowlisted_image_is_blocked(self):
        with self.assertRaisesRegex(ValueError,"public source allowlist"):
            embed(self.example(),WORKSHEET,available_images=set())

    def test_unknown_page_is_rejected_not_mislabeled_as_another_page(self):
        with self.assertRaisesRegex(ValueError,"registered social"):
            embed(self.example("secret-customer-report.html"),
                  "secret-customer-report.html",
                  available_images=set(builder.BINARY_SOURCE_FILES))

    def test_broken_or_duplicate_canonical_rejected(self):
        html=self.example().replace(OLD_BASE,"https://phishing.example.net/")
        with self.assertRaisesRegex(ValueError,"canonical URL"):
            embed(html,WORKSHEET,available_images=set(builder.BINARY_SOURCE_FILES))
        html=self.example().replace("</head>",
            '<link rel="canonical" href="https://fake.example.net/"></head>')
        with self.assertRaisesRegex(ValueError,"one canonical"):
            embed(html,WORKSHEET,available_images=set(builder.BINARY_SOURCE_FILES))

    def test_html_source_is_not_edited_by_embed(self):
        src=self.example()
        modified=embed(src,WORKSHEET,available_images=set(builder.BINARY_SOURCE_FILES))
        self.assertNotEqual(modified,src)
        self.assertIn("<main>Educational only</main>",modified)
        self.assertEqual(src,self.example())

    def test_exact_public_build_injects_all_marketing_pages_not_private_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=builder.build(Path(tmp)/"site","sales@freightfixture.com",True)
            for file in builder.PUBLIC_CONTACT_PAGES:
                document=(output/file).read_text(encoding="utf-8")
                if file=="index.html":
                    self.assertEqual(document.count('property="og:title"'),1)
                    continue
                for field in ("og:title","og:description","og:image","og:url"):
                    self.assertEqual(document.count(f'property="{field}"'),1,file)
                self.assertEqual(document.count('name="twitter:card"'),1,file)
                self.assertEqual(document.count('name="twitter:image"'),1,file)
            self.assertNotIn('property="og:description"',
                (output/"404.html").read_text(encoding="utf-8"))
            self.assertNotIn('property="og:description"',
                (output/"recovery-status-example.html").read_text(encoding="utf-8"))

    def test_cloudflare_rebase_keeps_absolute_asset_and_exact_pretty_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=builder.build(Path(tmp)/"site","sales@freightfixture.com",True)
            rebase(output)
            for file in builder.PUBLIC_CONTACT_PAGES:
                if file=="index.html": continue
                document=(output/file).read_text(encoding="utf-8")
                tags=HeadTags();tags.feed(document)
                canonical=NEW_BASE+file.removesuffix(".html")
                self.assertEqual(tags.property("og:url"),[canonical],file)
                self.assertIn(f'<link rel="canonical" href="{canonical}">',document)
                assert tags.property("og:image")[0].startswith(NEW_BASE)
                path=tags.property("og:image")[0].removeprefix(NEW_BASE)
                self.assertTrue((output/path).is_file(),path)
                self.assertNotIn(OLD_BASE,document)

    def test_all_social_cards_require_no_analytics_or_customer_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=builder.build(Path(tmp)/"site","sales@freightfixture.com",True)
            for name in builder.PUBLIC_CONTACT_PAGES:
                if name=="index.html":continue
                document=(output/name).read_text(encoding="utf-8")
                start=document.index("<!-- RETALLY static public share card:")
                end=document.index("<!-- /RETALLY static public share card -->")
                card=document[start:end]
                for bad in ("freight:analytics","gtag","api/inquiry","real customer",
                            "<script","dataLayer","recovering $","jay@","sales@"):
                    self.assertNotIn(bad,card,name)


if __name__=="__main__":
    unittest.main()
