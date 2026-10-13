"""RETALLY v4 mobile-first legibility, logo provenance, publication-hold QA."""
from __future__ import annotations

import base64
import html
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest

import render_social as legacy
import render_social_v3 as v3
import render_social_v4 as v4

ROOT=Path(__file__).resolve().parents[4]
LOGO=ROOT / legacy.CANONICAL_WORDMARK
TINY=base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/q6sAAAAASUVORK5CYII="
)


class V4VisualAcceptanceTests(unittest.TestCase):
    def test_v4_preserves_all_six_topics_and_copy(self):
        self.assertEqual(len(v3.CONCEPTS),6)
        for concept in v3.CONCEPTS:
            full=v4.template_html("data:image/png;base64,YWJj",
                                  "data:image/png;base64,YWJj",concept,preview=True)
            original=v3.template_html("data:image/png;base64,YWJj",
                                      "data:image/png;base64,YWJj",concept,preview=True)
            self.assertIn(html.escape(v3.COPY[concept]["title"],quote=True),full)
            self.assertIn(html.escape(v3.COPY[concept]["section"]),full)
            self.assertIn(html.escape(v3.COPY[concept]["note"],quote=True),full)
            self.assertIn('<main class="artboard v3 v4 ',full)
            self.assertEqual(full.count('class="document"') + full.count('class="document focus"'),3)
            self.assertNotEqual(full,original)

    def test_true_full_width_stacked_rows_and_legibility_type(self):
        self.assertIn("grid-template-columns:minmax(0,1fr)",v4.CSS_V4)
        self.assertIn("grid-template-rows:repeat(3,92px)",v4.CSS_V4)
        self.assertIn("font-size:42px",v4.CSS_V4)
        self.assertIn("font-size:29px",v4.CSS_V4)
        self.assertIn("font-size:23px",v4.CSS_V4)
        self.assertIn("width:940px",v4.CSS_V4)

    def test_no_script_or_remote_assets(self):
        for key in v3.CONCEPTS:
            s=v4.template_html("data:image/png;base64,ZmFrZQ==",
                               "data:image/webp;base64,ZmFrZQ==",key,preview=True)
            self.assertNotIn("https://",s)
            self.assertNotIn("http://",s)
            self.assertNotIn("<script",s)
            self.assertNotIn("<iframe",s)
            self.assertNotIn("<form",s)

    def test_draft_disclosures_not_removed(self):
        for key in v3.CONCEPTS:
            html=v4.template_html("x","y",key,preview=True)
            self.assertIn("ILLUSTRATIVE ONLY",html)
            self.assertIn("NO CUSTOMER DATA",html)
            self.assertIn("DESIGN CONCEPT ONLY",html)
            self.assertIn("NOT APPROVED FOR PUBLICATION",html)

    def test_original_v3_not_mutated_by_static_v4_template(self):
        before=v3.template_html("x","y","claim_evidence")
        v4.template_html("x","y","claim_evidence")
        self.assertEqual(v3.template_html("x","y","claim_evidence"),before)

    def test_unsafe_concept_denied(self):
        with self.assertRaisesRegex(ValueError,"Unknown new topic"):
            v4.template_html("x","y","claim_we_recovered_cash")

    def test_fake_logo_rejected_before_folder_creation(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            bad=path/"logo.png"
            bad.write_bytes(b"fake source")
            out=path/"export"
            with self.assertRaisesRegex(ValueError,"Unapproved logo"):
                v4.render(out,"preview",bad,bad,concept="scope_first")
            self.assertFalse(out.exists())

    def test_unapproved_mode_rejected(self):
        with self.assertRaisesRegex(ValueError,"Unsupported render mode"):
            v4.render(Path("/tmp/should-not-exist"),"publish",LOGO,LOGO)

    def test_v4_static_text_not_fake_recovery(self):
        forbidden=("our customers saved","we recovered $","guaranteed refund",
                   "verified paid refund","client case study")
        for key in v3.CONCEPTS:
            source=v4.template_html("x","y",key).lower()
            for text in forbidden:
                self.assertNotIn(text,source)

    def test_v3_renderer_callbacks_restored_after_v4_failure(self):
        original_v3=v3.template_html
        original_dom=legacy._dom_qa
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            bad=path/"bad-logo.png";bad.write_bytes(b"corrupt")
            with self.assertRaises(ValueError):
                v4.render(path/"render","preview",bad,bad)
        self.assertIs(v3.template_html,original_v3)
        self.assertIs(legacy._dom_qa,original_dom)

    def test_illustrative_detention_math_retained(self):
        s=v4.template_html("x","y","detention_clock")
        self.assertIn("08:30",s)
        self.assertIn("11:00",s)
        self.assertIn("120 MIN",s)
        self.assertIn("30 min beyond",s)
        self.assertIn("ILLUSTRATIVE",s)

    def test_one_preview_render_has_stacked_readable_cards(self):
        if not LOGO.exists():
            self.skipTest("Exact brand master not available")
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            photo=root/"generated-test.png"
            photo.write_bytes(TINY)
            out=root/"output"
            try:
                result=v4.render(out,"preview",LOGO,photo,concept="claim_evidence",
                    executable=shutil.which("chromium") or shutil.which("chromium-browser"))
            except Exception as exc:
                if "Executable doesn't exist" in str(exc):
                    self.skipTest("Chromium is unavailable")
                raise
            self.assertEqual(len(result["assets"]),1)
            art=result["assets"][0]
            self.assertEqual(art["concept"],"claim_evidence")
            self.assertEqual(art["qa"]["escaped_elements"],[])
            q=art["qa"]["v4_phone_readability"]
            self.assertEqual(q["columns"],3)
            self.assertTrue(q["stacked"])
            self.assertTrue(q["all_card_text_visible"])
            self.assertTrue(q["headline_not_clipped"])
            self.assertGreaterEqual(min(q["card_title_sizes_px"]),40)
            self.assertGreaterEqual(min(q["card_value_sizes_px"]),28)
            self.assertTrue(result["no_publication"])
            self.assertTrue(result["human_approval_required"])
            self.assertTrue(result["needs_owner_source_rights_and_content_review"])
            self.assertTrue(result["existing_published_and_scheduled_posts_untouched"])
            self.assertFalse(result["content_proposals"][0]["approved_for_publication"])
            for key,dims in (("image",(1080,1350)),("mobile_preview",(390,488))):
                raw=Path(art[key]).read_bytes()
                self.assertEqual(struct.unpack(">II",raw[16:24]),dims)
            reread=json.loads((out/"manifest.json").read_text())
            self.assertEqual(reread["creative_series"],result["creative_series"])


if __name__=="__main__":
    unittest.main()
