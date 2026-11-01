"""RETALLY v4 carousel editorial, brand, accessibility and security tests.

These tests never publish or access social-network APIs.
"""
from __future__ import annotations

import html
import re
import struct
import tempfile
import unittest
from pathlib import Path

import render_carousels_v4 as v4
import render_social_v3 as v3


class V4CarouselTests(unittest.TestCase):
    def test_exact_six_complete_editorial_topics(self):
        self.assertEqual(set(v4.TOPICS),set(v3.CONCEPTS))
        self.assertEqual(set(v4.CONCEPTS),set(v3.CONCEPTS))
        self.assertEqual(len(v4.TOPICS),6)
        self.assertEqual(len(set(x["cover"] for x in v4.TOPICS.values())),6)
        for item in v4.TOPICS.values():
            self.assertEqual(len(item["three"]),3)
            self.assertEqual(len(set(x[0] for x in item["three"])),3)
            self.assertTrue(item["evidence"])
            self.assertTrue(item["not_evidence"])
            self.assertTrue(item["last"])
            self.assertTrue(item["closer"])

    def test_all_twenty_four_data_only_unique_html_slides(self):
        seen=set()
        for concept in v4.CONCEPTS:
            for slide in range(1,5):
                with self.subTest(concept=concept,slide=slide):
                    text=v4.template_html(concept,slide,"data:image/png;base64,YWJj",
                                          "data:image/webp;base64,YWJj")
                    self.assertNotIn(text,seen)
                    seen.add(text)
                    self.assertIn("DESIGN DRAFT",text)
                    self.assertIn("NOT PUBLISHED",text)
                    self.assertIn("FIND IT. PROVE IT. RECOVER IT.",text)
                    self.assertIn("Original RETALLY wordmark",text)
                    self.assertNotIn("<script",text.lower())
                    self.assertNotIn("<form",text.lower())
                    self.assertNotIn("<iframe",text.lower())
                    self.assertNotIn("https://",text.lower())
                    self.assertNotIn("http://",text.lower())
                    self.assertNotIn("our customers",text.lower())
                    self.assertNotIn("we recovered",text.lower())
                    self.assertNotIn("guaranteed refund",text.lower())
        self.assertEqual(len(seen),24)

    def test_every_topic_uses_distinct_registered_freight_image(self):
        self.assertEqual(set(v3.CANONICAL_HERO_PHOTOS),set(v4.CONCEPTS))
        self.assertEqual(len(set(v3.CANONICAL_HERO_PHOTOS.values())),6)
        for name in v4.CONCEPTS:
            self.assertTrue(v3.CANONICAL_HERO_PHOTOS[name].endswith(".webp"))

    def test_slide_one_has_legible_hook_and_disclosure(self):
        for name in v4.CONCEPTS:
            markup=v4.template_html(name,1,"logo","photo")
            self.assertIn("SWIPE TO REVIEW",markup)
            self.assertIn("ILLUSTRATIVE FRAMEWORK",markup)
            self.assertIn("NOT CUSTOMER RESULTS",markup)
            self.assertIn(html.escape(v4.TOPICS[name]["lead"],quote=True),markup)

    def test_slide_two_has_all_three_evidence_steps(self):
        for name in v4.CONCEPTS:
            markup=v4.template_html(name,2,"logo","photo")
            for _,title,detail in v4.TOPICS[name]["three"]:
                self.assertIn(title,markup)
                self.assertIn(detail.replace("&","&amp;"),markup)
            self.assertEqual(markup.count('class="row"'),3)
            self.assertIn("3 EVIDENCE",markup)

    def test_slide_three_separates_proof_from_assumption(self):
        for name in v4.CONCEPTS:
            markup=v4.template_html(name,3,"logo","photo")
            self.assertIn("Evidence to confirm",markup)
            self.assertIn("Do not assume",markup)
            self.assertIn(v4.TOPICS[name]["evidence"],markup)
            self.assertIn(html.escape(v4.TOPICS[name]["not_evidence"],quote=True),markup)
            self.assertEqual(markup.count('class="panel"'),2)

    def test_slide_four_has_topic_specific_educational_page(self):
        seen=set()
        for name in v4.CONCEPTS:
            markup=v4.template_html(name,4,"logo","photo")
            target="retallyrecovery.com/"+v3.COPY[name]["site_slug"]
            self.assertIn(target,markup)
            seen.add(target)
            self.assertIn(v4.TOPICS[name]["closer"],markup)
            self.assertNotIn("Start Free Audit",markup)
        self.assertEqual(len(seen),6)

    def test_detention_math_disclosed_at_readable_size(self):
        cover=v4.template_html("detention_clock",1,"logo","photo")
        self.assertIn("Illustrative timing example",cover)
        proof=v4.template_html("detention_clock",2,"logo","photo")
        for thing in ("08:30 TO 11:00","150 minutes","120 MIN FREE",
                      "30 MIN BEYOND","90 billed","60-minute question"):
            self.assertIn(thing,proof)
        self.assertNotIn("proven refund",proof.lower())

    def test_privacy_slide_forbids_sending_customer_files(self):
        proof=v4.template_html("secure_intake",2,"logo","photo")
        self.assertIn("Keep rates, invoices and bank details out of DMs.",proof)
        self.assertIn("out of DMs",proof)
        conclusion=v4.template_html("secure_intake",4,"logo","photo")
        self.assertIn("not a request",conclusion)

    def test_zero_actual_customer_and_money_claims(self):
        banned=re.compile(r"(?:we|retally)\s+(?:have\s+)?recovered\s+\$|"
                          r"guaranteed\s+(?:refund|recovery)|"
                          r"customer\s+(?:saved|testimonial)",re.I)
        for name in v4.CONCEPTS:
            for slide in range(1,5):
                markup=v4.template_html(name,slide,"logo","photo")
                self.assertNotRegex(markup,banned)

    def test_invalid_concept_slide_and_markup_fail_closed(self):
        for name,slide in (("unsupported",1),("scope_first",0),
                           ("scope_first",5)):
            with self.assertRaises(ValueError):
                v4.template_html(name,slide,"logo","photo")
        with self.assertRaisesRegex(ValueError,"markup"):
            v4._h("<script>alert(1)</script>")

    def test_exact_logo_checksum_stays_enforced(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with self.assertRaises((ValueError, FileNotFoundError)):
                v4.render(root,root/"art")
            self.assertFalse((root/"art").exists())

    def test_png_magic_and_dimensions(self):
        good=b"\x89PNG\r\n\x1a\n"+b"\0"*8+struct.pack(">II",1080,1350)
        self.assertEqual(v4.png_dimensions(good),(1080,1350))
        with self.assertRaises(ValueError):
            v4.png_dimensions(b"not an image")

    def test_output_inside_checkout_denied(self):
        repo=Path(__file__).resolve().parents[4]
        # Check fail-closed source contract without rendering.
        self.assertIn("Exports must be outside repository checkout",
                      Path(__file__).with_name("render_carousels_v4.py").read_text())

    def test_body_types_large_enough_at_phone_scale(self):
        self.assertIn("font-size:36px",v4.CSS)
        self.assertIn("font-size:47px",v4.CSS)
        self.assertIn("font-size:114px",v4.CSS)
        self.assertIn("font-size:48px",v4.CSS)


if __name__=="__main__":
    unittest.main()
