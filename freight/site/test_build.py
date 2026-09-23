"""Publication-boundary checks. The fixture mailbox is never deployed."""

import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

from freight.synthetic_pilot_bundle import verify_synthetic_pilot_bundle

spec = importlib.util.spec_from_file_location("marketing_build", Path(__file__).with_name("build.py"))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


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
            self.assertEqual(set(builder.PUBLIC_FILES), {file.name for file in output.iterdir()})
            page = (output / "index.html").read_text()
            self.assertIn('content="sales@freightfixture.com"', page)
            self.assertIn('href="mailto:sales@freightfixture.com"', page)
            self.assertNotIn("This is a source preview.", page)
            self.assertIn("Synthetic data", page)
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
