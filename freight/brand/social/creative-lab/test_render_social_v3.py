"""RETALLY premium social studio v3 — six extra editorial layouts and browser QA."""
from __future__ import annotations

import base64
import json
import shutil
import struct
import tempfile
import unittest
from pathlib import Path

import render_social as base
import render_social_v3 as m

ROOT = Path(__file__).resolve().parents[4]
LOGO = ROOT / base.CANONICAL_WORDMARK
TINY = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/q6sAAAAASUVORK5CYII='
)


class FieldNotesV3Tests(unittest.TestCase):
    def test_six_nonoverlapping_topic_concepts(self):
        self.assertEqual(len(m.CONCEPTS),6)
        self.assertEqual(len(m.COPY),6)
        self.assertEqual(set(m.COPY),set(m.CONCEPTS))
        self.assertEqual(len(set(x["site_slug"] for x in m.COPY.values())),6)

    def test_no_external_source_or_borrowed_customer_claim(self):
        forbidden = ("guaranteed refund","our customer", "saved $", "recovered $",
                     "real customer", "carrier owes", "verified overcharge")
        for key in m.CONCEPTS:
            with self.subTest(key=key):
                c=m.COPY[key]
                rendered=m.template_html("data:image/png;base64,YWJj",
                                         "data:image/webp;base64,YWJj",
                                         key,preview=True)
                self.assertIn('DESIGN CONCEPT ONLY',rendered)
                self.assertIn('NOT APPROVED FOR PUBLICATION',rendered)
                self.assertIn('ILLUSTRATIVE ONLY',rendered)
                self.assertIn('NO CUSTOMER DATA',rendered)
                self.assertIn('ORIGINAL APPROVED RETALLY WORDMARK',rendered.upper())
                self.assertIn(c["caption_hook"],json.dumps(c))
                self.assertNotIn("<script",rendered.lower())
                self.assertNotIn("<form",rendered.lower())
                self.assertNotIn("https://",rendered.lower())
                self.assertNotIn("http://",rendered.lower())
                for fragment in forbidden:
                    self.assertNotIn(fragment,rendered.lower())

    def test_topic_specific_visual_direction_and_descriptive_alts(self):
        for key,c in m.COPY.items():
            with self.subTest(key=key):
                self.assertTrue(c["style"] in m.CSS_V3)
                self.assertTrue(c["alt"].startswith("RETALLY") or c["alt"].startswith("Clearly"))
                self.assertGreater(len(c["alt"]),60)
                self.assertIn("data" if key=="secure_intake" else "freight" if key=="scope_first" else "",
                              c["alt"].lower())
                self.assertGreaterEqual(len(c["cards"]),3)
                self.assertLess(c["focus"],len(c["cards"]))

    def test_scenario_math_no_cash_claim(self):
        txt=m.template_html("a","b","detention_clock")
        self.assertIn("08:30",txt)
        self.assertIn("11:00",txt)
        self.assertIn("120 MIN",txt)
        self.assertIn("30 min beyond",txt)
        self.assertIn("ILLUSTRATIVE",txt)
        self.assertNotIn("$",txt)

    def test_credit_reversal_not_recovered_without_confirmation(self):
        s=m.template_html("a","b","settlement_status")
        self.assertIn("APPROVED",s)
        self.assertIn("POSTED",s)
        self.assertIn("REVERSAL",s)
        self.assertIn("A posted credit can be reversed",s)
        self.assertNotIn("WE RECOVERED",s)

    def test_data_security_prohibits_dm_record_transfer(self):
        txt=m.template_html("a","b","secure_intake")
        self.assertIn("NO INVOICES",txt)
        self.assertIn("NEVER VIA DM",txt)
        self.assertIn("SECURE ROUTE",txt)
        self.assertNotIn("<form",txt)

    def test_unapproved_topic_denied(self):
        with self.assertRaisesRegex(ValueError,"Unknown new topic"):
            m.template_html("a","b","fake_recovery_results")
        with self.assertRaisesRegex(ValueError,"Unsupported field notes"):
            m.render(Path("/not/used"),"preview",LOGO,LOGO,concept="fake_recovery_results")

    def test_existing_templates_restored_after_v3(self):
        original=base.CONCEPTS,base.template_html
        with tempfile.TemporaryDirectory() as d:
            bad=Path(d)/"bad-logo.png"
            bad.write_bytes(b"broken")
            with self.assertRaisesRegex(ValueError,"Unapproved logo"):
                m.render(Path(d)/"output","preview",bad,bad)
            self.assertIs(base.CONCEPTS,original[0])
            self.assertIs(base.template_html,original[1])

    def test_invalid_mode_denied_without_side_effects(self):
        with tempfile.TemporaryDirectory() as d:
            o=Path(d)/"output"
            with self.assertRaisesRegex(ValueError,"Unsupported render mode"):
                m.render(o,"publish",LOGO,LOGO)
            self.assertFalse(o.exists())

    def test_canonical_master_never_mutated(self):
        if not LOGO.is_file(): self.skipTest("Approved logo unavailable")
        fingerprint=base.sha256(LOGO)
        self.assertEqual(fingerprint,base.APPROVED_WORDMARK_SHA256)
        m.template_html("x","y","scope_first")
        self.assertEqual(base.sha256(LOGO),fingerprint)

    def test_all_six_have_different_topic_specific_html(self):
        pages=[m.template_html("x","y",key) for key in m.CONCEPTS]
        self.assertEqual(len(pages),len(set(pages)))
        for s in pages:
            self.assertIn('<main class="artboard v3',s)
            self.assertEqual(s.count('class="document'),3)

    def test_six_real_fullsize_and_phone_pngs_with_no_external_network(self):
        if not LOGO.is_file(): self.skipTest("Canonical brand source missing")
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            photo=path/"source.png";photo.write_bytes(TINY)
            out=path/"rendered"
            try:
                result=m.render(out,"preview",LOGO,photo,
                    executable=shutil.which("chromium") or shutil.which("chromium-browser"))
            except Exception as exc:
                if "Executable doesn't exist" in str(exc):
                    self.skipTest("Playwright Chromium unavailable")
                raise
            self.assertEqual(len(result["assets"]),6)
            self.assertTrue(result["no_publication"])
            self.assertTrue(result["human_approval_required"])
            self.assertTrue(result["needs_owner_source_rights_and_content_review"])
            self.assertEqual(len(result["content_proposals"]),6)
            self.assertEqual(result["approved_wordmark_sha256"],base.APPROVED_WORDMARK_SHA256)
            for item in result["assets"]:
                with self.subTest(item=item["concept"]):
                    self.assertEqual(item["qa"]["escaped_elements"],[])
                    self.assertEqual(item["qa"]["logo"],[1619,257])
                    self.assertTrue(item["qa"]["preview_banner"])
                    self.assertTrue(item["preview_only"])
                    for key,dimension in (("image",(1080,1350)),("mobile_preview",(390,488))):
                        pixels=Path(item[key]).read_bytes()
                        self.assertTrue(pixels.startswith(b"\x89PNG\r\n\x1a\n"))
                        self.assertEqual(struct.unpack(">II",pixels[16:24]),dimension)
            saved=json.loads((out/"manifest.json").read_text())
            self.assertEqual(saved["creative_series"],result["creative_series"])
            self.assertFalse(any(x["approved_for_publication"] for x in saved["content_proposals"]))


if __name__=="__main__":
    unittest.main()
