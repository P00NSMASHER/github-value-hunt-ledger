"""Publication-boundary checks. The fixture mailbox is never deployed."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

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
            self.assertIn("Freight Recovery", page)
            self.assertIn("Blind Freight Audit Acceptance Test", page)
            self.assertIn("$15k–$25k", page)
            self.assertIn("Data Readiness / Authority Diagnostic", page)
            self.assertIn("$5k–$7.5k", page)
            self.assertIn("Invoice disposition register", page)
            self.assertIn("Synthetic example", page)
            self.assertIn("Realized recovery", page)
            self.assertIn("Nothing is submitted, uploaded, or saved by this page.", page)
            self.assertNotIn('id="name"', page)
            self.assertNotIn('id="notes"', page)

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


class PublicOfferBoundaryTests(unittest.TestCase):
    def test_source_preview_keeps_contact_unconfigured_and_no_document_upload(self):
        page = (builder.SOURCE / "index.html").read_text()
        self.assertEqual(page.count(builder.CONTACT_META), 1)
        self.assertIn("Contact channel pending.", page)
        self.assertNotIn('type="file"', page)
        self.assertNotIn("<form", page)
        self.assertIn("Do not send freight documents here.", page)

    def test_current_offer_copy_separates_discrepancy_from_recovery(self):
        page = (builder.SOURCE / "index.html").read_text()
        self.assertIn("Supported discrepancy", page)
        self.assertIn("Realized recovery", page)
        self.assertIn("$0", page)
        self.assertIn("not a promise of savings or recovery", page)
        self.assertIn("No guaranteed recovery", page)

    def test_inquiry_is_three_fact_fit_check(self):
        page = (builder.SOURCE / "index.html").read_text()
        for field in ('id="company"', 'id="email"', 'id="volume"'):
            self.assertIn(field, page)
        self.assertEqual(page.count("<input"), 2)
        self.assertEqual(page.count("<select"), 1)
        self.assertNotIn("<textarea id="notes"", page)
