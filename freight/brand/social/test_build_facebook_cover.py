"""Offline unit gates for Facebook cover geometry and asset identity."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('build_facebook_cover', HERE / 'build_facebook_cover.py')
cover = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cover)


class FacebookCoverTests(unittest.TestCase):
    def test_cover_dimensions_rgb_and_safe_area(self):
        # Synthetic QA wordmark only; never published as real brand art.
        demo = Image.new('RGBA',(1619,257),'white')
        draw = ImageDraw.Draw(demo)
        draw.rectangle((160,65,1459,192), fill=(32,47,43,255))
        image = cover.render(demo)
        self.assertEqual(image.size,(1640,624))
        self.assertEqual(image.mode,'RGB')
        for coordinate in [(380,180),(1260,180),(380,500),(1260,500)]:
            self.assertTrue(all(c >= 220 for c in image.getpixel(coordinate)))

    def test_wrong_logo_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            test_logo=Path(t)/'retally-wordmark-approved.png'
            test_logo.write_bytes(b'not approved')
            self.assertFalse(cover._master_is_verified(test_logo))
            bad_name=Path(t)/'retally-wordmark.webp'
            bad_name.write_bytes(b'not approved')
            self.assertFalse(cover._master_is_verified(bad_name))


if __name__ == '__main__':
    unittest.main()
