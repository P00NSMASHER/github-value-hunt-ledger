"""Offline correctness and visual geometry checks for RETALLY creative assets."""
import base64
import importlib.util
import json
import shutil
import struct
import tempfile
import unittest
from pathlib import Path

import render_social as m

ROOT = Path(__file__).resolve().parents[4]
APPROVED = ROOT / m.CANONICAL_WORDMARK
# Tiny local data-only PNG; rendering with this intentionally is NOT a visual sign-off.
TINY_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/q6sAAAAASUVORK5CYII='
)


class BrandAndCopyTests(unittest.TestCase):
    def test_expected_geometry_and_original_asset_paths(self):
        self.assertEqual((m.W,m.H),(1080,1350))
        self.assertEqual((m.PHONE_W,m.PHONE_H),(390,488))
        self.assertEqual(len(m.APPROVED_WORDMARK_SHA256),64)
        self.assertEqual(len(m.APPROVED_EMBLEM_SHA256),64)
        self.assertEqual(len(m.CONCEPTS),3)
        self.assertTrue(str(m.CANONICAL_WORDMARK).endswith('retally-wordmark-approved.png'))

    def test_verified_exact_original_assets(self):
        # Uploaded master bytes are already tracked in this repository; no repair or redraw.
        if APPROVED.is_file():
            m.validate_logo(APPROVED)
            self.assertEqual(m.sha256(APPROVED),m.APPROVED_WORDMARK_SHA256)
        else:
            self.skipTest('Full approved master not in standalone partial checkout')

    def test_unapproved_wordmark_rejected_before_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'logo.png'
            file.write_bytes(b'\x89PNG\r\n\x1a\n'+b'\0'*64)
            with self.assertRaisesRegex(ValueError,'Unapproved logo checksum'):
                m.validate_logo(file)
            with self.assertRaisesRegex(ValueError,'Unapproved logo checksum'):
                m.run(Path(tmp)/'export','preview','rate_versions',file,file)
            self.assertFalse((Path(tmp)/'export').exists())

    def test_invalid_photo_magic_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'stock.webp'
            file.write_bytes(b'unknown')
            with self.assertRaisesRegex(ValueError,'Unsupported image'):
                m.read_image(file)

    def test_unknown_template_is_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'Unknown concept'):
            m.template_html('x','y','invoice_savings_guaranteed')

    def test_all_templates_are_no_network_no_fake_savings_and_correct_logo(self):
        for key in m.CONCEPTS:
            with self.subTest(key=key):
                html=m.template_html('data:image/png;base64,YWJj', 'data:image/png;base64,YWJj', key,preview=True)
                self.assertIn('ORIGINAL APPROVED RETALLY WORDMARK',html.upper())
                self.assertIn('DESIGN CONCEPT ONLY',html)
                self.assertIn('NOT APPROVED FOR PUBLICATION',html)
                self.assertIn('ILLUSTRATIVE ONLY',html)
                self.assertIn('NO CUSTOMER DATA',html)
                self.assertNotIn('<script',html.lower())
                self.assertNotIn('<form',html.lower())
                self.assertNotIn('http://',html.lower())
                self.assertNotIn('https://',html.lower())
                self.assertNotIn('guaranteed savings',html.lower())
                self.assertNotIn('recovered $',html.lower())

    def test_claim_control_is_explicit(self):
        cc = m.template_html('a','b','credit_chain')
        self.assertIn('A second invoice is not automatically a second payment.',cc)
        self.assertIn('CREDIT MEMO',cc)
        ap = m.template_html('a','b','accessorial_proof')
        self.assertIn('First confirm the service',ap)
        rv = m.template_html('a','b','rate_versions')
        self.assertIn('Confirm governing terms',rv)


class RenderSmokeTests(unittest.TestCase):
    def test_three_actual_png_exports_mobile_qa_and_publication_hold(self):
        if not APPROVED.is_file():
            self.skipTest('Approved source logo not present in partial checkout')
        with tempfile.TemporaryDirectory() as d:
            photo=Path(d)/'synthetic-test-image.png'
            photo.write_bytes(TINY_PNG)
            outputs=Path(d)/'outputs'
            try:
                manifest=m.run(outputs,'preview','all',APPROVED,photo,executable=shutil.which('chromium') or shutil.which('chromium-browser'))
            except Exception as exc:
                if 'Executable doesn\'t exist' in str(exc):
                    self.skipTest('Chromium not installed in this environment')
                raise
            self.assertEqual(len(manifest['assets']),3)
            self.assertTrue(manifest['no_publication'])
            self.assertTrue(manifest['human_approval_required'])
            self.assertEqual(manifest['approved_wordmark_sha256'],m.APPROVED_WORDMARK_SHA256)
            self.assertEqual(manifest['photo_sha256'],m.sha256(photo))
            recorded=json.loads((outputs/'manifest.json').read_text())
            self.assertEqual(recorded['mode'],'preview')
            for row in manifest['assets']:
                with self.subTest(row=row['concept']):
                    self.assertEqual(row['qa']['escaped_elements'],[])
                    self.assertEqual(row['qa']['logo'],[1619,257])
                    self.assertTrue(row['qa']['preview_banner'])
                    self.assertTrue(row['preview_only'])
                    for filename,dims in [('image',(1080,1350)),('mobile_preview',(390,488))]:
                        data=Path(row[filename]).read_bytes()
                        self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))
                        self.assertEqual(struct.unpack('>II',data[16:24]),dims)


if __name__=='__main__':
    unittest.main()
