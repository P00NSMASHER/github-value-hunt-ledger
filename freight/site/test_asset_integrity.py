"""The release must reject undersized/corrupt images before publication."""
from pathlib import Path
import unittest

from freight.site.asset_integrity import (
    APPROVED_LOGOS, AssetIntegrityError, assert_approved_logo, assert_webp,
    validate_freight_media, validate_recoveryos_media, webp_dimensions,
)
from freight.site.build import BINARY_SOURCE_FILES, SOURCE
from recoveryworks.site.build import SITE_DIR as RECOVERY_SITE


class PublicAssetIntegrityTests(unittest.TestCase):
    def test_every_registered_freight_and_recoveryos_image(self):
        validate_freight_media(SOURCE)
        validate_recoveryos_media(RECOVERY_SITE)

    def test_exact_approved_logos_are_the_only_published_primary_artwork(self):
        for name in APPROVED_LOGOS:
            with self.subTest(name=name):
                data = (SOURCE / "assets" / "brand" / name).read_bytes()
                assert_approved_logo(data, name)
        self.assertNotIn("assets/brand/retally-emblem.webp", BINARY_SOURCE_FILES)
        self.assertNotIn("assets/brand/retally-wordmark.svg", BINARY_SOURCE_FILES)
        self.assertNotIn("assets/brand/retally-emblem.svg", BINARY_SOURCE_FILES)

    def test_corrupt_original_logo_is_rejected_not_upscaled(self):
        # The original failed image was 110x106, far below the content threshold.
        original = bytearray((SOURCE / "assets/images/terminal-blue-hour-800.webp").read_bytes())
        self.assertEqual(webp_dimensions(original)[0], 800)
        original[26:28] = (110).to_bytes(2, "little")
        original[28:30] = (106).to_bytes(2, "little")
        with self.assertRaisesRegex(AssetIntegrityError, "Undersized"):
            assert_webp(bytes(original), "defective-legacy-emblem.webp", 800, 450)

    def test_truncated_webp_fails_closed(self):
        original = (SOURCE / "assets/images/terminal-blue-hour-800.webp").read_bytes()
        with self.assertRaisesRegex(AssetIntegrityError, "Malformed or truncated"):
            webp_dimensions(original[:-15])

    def test_altered_approved_logo_fails_closed(self):
        name = "retally-emblem-approved.png"
        original = bytearray((SOURCE / "assets/brand" / name).read_bytes())
        original[-20] ^= 0x01
        with self.assertRaisesRegex(AssetIntegrityError, "Approved original"):
            assert_approved_logo(bytes(original), name)


if __name__ == "__main__":
    unittest.main()
