"""RETALLY homepage organic-discovery acceptance: real worksheet, no intake posts.

Prevents an Instagram/social visitor from seeing only a high-friction intake
CTA. All actions are user-initiated navigation to an educational worksheet.
"""
from __future__ import annotations

import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from freight.site.build import build
from freight.site.rebase_public_urls import rebase, NEW_BASE

SOURCE=Path(__file__).with_name("index.html")
TARGET="freight-invoice-audit-checklist.html#worksheet"


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            self.links.append(dict(attrs))


class HomepageWorksheetTest(unittest.TestCase):
    def test_secondary_hero_promotes_educational_tool_without_changing_main_offer(self):
        html=SOURCE.read_text(encoding="utf-8")
        self.assertIn('class="button button-ghost" href="'+TARGET+'"',html)
        self.assertIn(">Free 15-Point Worksheet</a>",html)
        self.assertIn("free printable 15-point freight invoice audit worksheet",html)
        self.assertIn('class="button button-signal" href="#start-audit"',html)
        self.assertIn("Start Free Recovery Audit",html)
        self.assertIn('href="recovery-status-example.html"',html)
        self.assertIn('href="#audit-output"',html)

    def test_resource_list_promotes_same_worksheet_without_dead_links(self):
        html=SOURCE.read_text(encoding="utf-8")
        self.assertIn(f'<a href="{TARGET}">Free printable worksheet</a>',html)
        self.assertEqual(html.count(f'href="{TARGET}"'),2)
        self.assertEqual(html.count('id="resources"'),1)
        self.assertIn('href="freight-audit-example.html"',html)  # retains sample resource link if available?

    def test_live_public_bundle_keeps_real_worksheet_and_unchanged_contact_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            root=build(Path(temp)/"public","sales@freightfixture.com",True)
            index=(root/"index.html").read_text(encoding="utf-8")
            guide=(root/"freight-invoice-audit-checklist.html").read_text(encoding="utf-8")
            self.assertIn(f'href="{TARGET}"',index)
            self.assertIn('id="worksheet"',guide)
            self.assertIn('id="ws-share"',guide)
            self.assertIn("15 freight invoice audit checks",guide.lower())
            self.assertIn('id="auditForm"',index)
            self.assertNotIn('type="file"',guide)
            self.assertTrue((root/"freight-audit-example.html").exists())

    def test_production_rebase_preserves_anchor_and_removes_extension_redirect(self):
        with tempfile.TemporaryDirectory() as temp:
            root=build(Path(temp)/"public","sales@freightfixture.com",True)
            count=rebase(root)
            self.assertGreater(count,0)
            index=(root/"index.html").read_text(encoding="utf-8")
            self.assertEqual(index.count('href="freight-invoice-audit-checklist#worksheet"'),2)
            self.assertNotIn('href="'+TARGET+'"',index)
            self.assertTrue((root/"freight-invoice-audit-checklist.html").is_file())
            self.assertIn(f'<link rel="canonical" href="{NEW_BASE}">',index)

    def test_no_automatic_sharing_or_marketing_tracking_on_new_link(self):
        html=SOURCE.read_text(encoding="utf-8")
        anchors=Anchors();anchors.feed(html)
        targets=[p for p in anchors.links if p.get("href")==TARGET]
        self.assertEqual(len(targets),2)
        for item in targets:
            self.assertNotIn("data-track",item)
            self.assertNotIn("onclick",item)
            self.assertNotIn("target",item)
            self.assertNotIn("download",item)
        self.assertNotIn("/api/inquiry",TARGET)

if __name__=="__main__":
    unittest.main()
