"""Publication-boundary checks. The fixture mailbox is never deployed."""

import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from freight.synthetic_pilot_bundle import verify_synthetic_pilot_bundle

spec = importlib.util.spec_from_file_location("marketing_build", Path(__file__).with_name("build.py"))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class ImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.images.append(dict(attrs))


class PublicBuildTests(unittest.TestCase):
    def test_contact_must_be_present_and_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "public"
            for email, verified in [("", True), ("sales@freightfixture.com", False),
                                    ("sales@example.com", True), ("not-an-email", True)]:
                with self.subTest(email=email, verified=verified), self.assertRaises(ValueError):
                    builder.build(output, email, verified)
                self.assertFalse(output.exists())

    def test_private_repository_cannot_be_the_output(self):
        for output in [builder.REPOSITORY, builder.REPOSITORY / "dist", builder.REPOSITORY.parent]:
            with self.subTest(output=output), self.assertRaises(ValueError):
                builder.build(output, "sales@freightfixture.com", True)

    def test_output_contains_only_public_assets_with_configured_contact(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = builder.build(Path(temporary) / "public", "sales@freightfixture.com", True)
            files = {
                path.relative_to(output).as_posix()
                for path in output.rglob("*")
                if path.is_file()
            }
            self.assertEqual(set(builder.PUBLIC_FILES), files)
            page = (output / "index.html").read_text()
            self.assertIn('content="sales@freightfixture.com"', page)
            self.assertIn('href="mailto:sales@freightfixture.com"', page)
            self.assertNotIn("This is a source preview.", page)
            self.assertIn("Synthetic records", page)
            self.assertIn("Freight Recovery", page)
            self.assertNotIn("FreightLeak", page)
            self.assertNotIn(builder.DEMO_MARKER, page)
            self.assertIn('href="synthetic-pilot-demo.zip"', page)
            self.assertIn("Content-Security-Policy", page)
            self.assertIn("form-action 'none'", page)
            self.assertIn('<meta name="referrer" content="no-referrer">', page)
            self.assertIn("$5,000&ndash;$7,500", page)
            self.assertIn("$15,000&ndash;$25,000", page)
            self.assertNotIn("<form", page.lower())

            parser = ImageParser()
            parser.feed(page)
            self.assertEqual(11, len(parser.images))
            self.assertTrue(all("alt" in image for image in parser.images))
            self.assertTrue(all(image["src"].startswith("assets/images/")
                                for image in parser.images))
            self.assertTrue(all("srcset" in image for image in parser.images))
            self.assertTrue(all("width" in image and "height" in image
                                for image in parser.images))

            stylesheet = (output / "site.css").read_text()
            self.assertIn('@font-face', stylesheet)
            self.assertNotIn("https://", stylesheet)
            for name in builder.BINARY_SOURCE_FILES:
                asset = output / name
                source = builder.SOURCE / name
                self.assertEqual(source.read_bytes(), asset.read_bytes())
                if name.endswith(".webp"):
                    payload = asset.read_bytes()
                    self.assertEqual(b"RIFF", payload[:4])
                    self.assertEqual(b"WEBP", payload[8:12])
                elif name.endswith(".woff2"):
                    self.assertEqual(b"wOF2", asset.read_bytes()[:4])

            attribution = json.loads(
                (output / "assets/fonts/ATTRIBUTION.json").read_text()
            )
            for item in attribution["assets"]:
                font = output / "assets/fonts" / item["file"]
                self.assertEqual(item["sha256"], hashlib.sha256(font.read_bytes()).hexdigest())
                self.assertEqual("SIL Open Font License 1.1", item["license"])

            script = (output / "site.js").read_text()
            for network_or_storage_api in (
                "fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket",
                "localStorage", "sessionStorage",
            ):
                self.assertNotIn(network_or_storage_api, script)

            demo = output / builder.DEMO_FILE
            receipt = verify_synthetic_pilot_bundle(demo)
            self.assertEqual(11, receipt["entry_count"])
            self.assertEqual(hashlib.sha256(demo.read_bytes()).hexdigest(),
                             receipt["bundle_sha256"])
            self.assertIn(receipt["bundle_sha256"], page)

    def test_existing_files_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            marker = output / "keep.txt"
            marker.write_text("unchanged")
            with self.assertRaises(ValueError):
                builder.build(output, "sales@freightfixture.com", True)
            self.assertEqual(marker.read_text(), "unchanged")
            self.assertEqual(["keep.txt"], [file.name for file in output.iterdir()])


if __name__ == "__main__":
    unittest.main()
