import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import render_social as m

class CreativePrototypeTests(unittest.TestCase):
    def test_exact_dimensions_and_canonical_logo(self):
        self.assertEqual((m.W,m.H),(1080,1350))
        self.assertTrue(m.CANONICAL_WORDMARK.endswith('retally-wordmark-approved.png'))
        self.assertEqual(len(m.APPROVED_WORDMARK_SHA256),64)

    def test_never_upload_or_send_or_claim_customer_result(self):
        for name in ('rate_versions','accessorial_proof'):
            src=m.template_html('data:image/png;base64,Zm9v','data:image/webp;base64,YmFy',name,True)
            self.assertIn('NOT APPROVED FOR PUBLICATION',src)
            self.assertIn('ILLUSTRATIVE',src)
            self.assertIn('NO CUSTOMER DATA',src)
            self.assertNotIn('fetch(',src)
            self.assertNotIn('<script',src)
            self.assertNotIn('http://',src)
            self.assertNotIn('https://',src)

    def test_reject_unknown_concepts(self):
        with self.assertRaises(ValueError):
            m.template_html('x','y','unexpected',False)

    def test_logo_source_hash_mismatch_rejected(self):
        with TemporaryDirectory() as td:
            p=Path(td)/'unauthorized.png';p.write_bytes(b'\x89PNG\r\n\x1a\n'+b'\0'*40)
            q=Path(td)/'pic.webp';q.write_bytes(b'12345')
            with self.assertRaisesRegex(ValueError,'Unapproved logo checksum'):
                m.run(Path(td)/'out','production','rate_versions',p,q)

if __name__ == '__main__':unittest.main()