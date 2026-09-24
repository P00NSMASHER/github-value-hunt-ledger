"""Publication-boundary checks. Fixture contacts are never deployed."""

import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from freight.synthetic_pilot_bundle import verify_synthetic_pilot_bundle

spec = importlib.util.spec_from_file_location(
    "marketing_build", Path(__file__).with_name("build.py")
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def build(output, email="sales@freightfixture.com", contact_verified=True, rate="0.30"):
    return builder.build(output, email, contact_verified, rate)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.links = []
        self.ids = []
        self.forms = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "img":
            self.images.append(attributes)
        if tag == "a":
            self.links.append(attributes.get("href", ""))
        if "id" in attributes:
            self.ids.append(attributes["id"])
        if tag == "form":
            self.forms.append(attributes)


class PublicBuildTests(unittest.TestCase):
    def test_contact_must_be_present_and_verified(self):
        for email, verified in [
            ("", True),
            ("sales@freightfixture.com", False),
            ("sales@example.com", True),
            ("not-an-email", True),
        ]:
            with self.subTest(email=email, verified=verified):
                with tempfile.TemporaryDirectory() as temporary, self.assertRaises(ValueError):
                    build(Path(temporary) / "public", email=email, contact_verified=verified)

    def test_contingency_rate_is_validated_and_configurable(self):
        for invalid in ("", "0", "1", "-0.1", "nan"):
            with self.subTest(rate=invalid):
                with tempfile.TemporaryDirectory() as temporary, self.assertRaises(ValueError):
                    build(Path(temporary) / "public", rate=invalid)
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public", rate="0.325")
            config = (output / "commercial-config.js").read_text()
            self.assertIn('contingencyRecoveryRate: "0.325"', config)
            self.assertIn('contingencyRecoveryRateLabel: "32.5%"', config)

    def test_private_repository_cannot_be_the_output(self):
        for output in (
            builder.REPOSITORY,
            builder.REPOSITORY / "dist",
            builder.REPOSITORY.parent,
        ):
            with self.subTest(output=output), self.assertRaises(ValueError):
                build(output)

    def test_output_contains_only_allowlisted_public_assets(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            files = {
                path.relative_to(output).as_posix()
                for path in output.rglob("*")
                if path.is_file()
            }
            self.assertEqual(set(builder.PUBLIC_FILES), files)
            for name in builder.BINARY_SOURCE_FILES:
                self.assertEqual((builder.SOURCE / name).read_bytes(), (output / name).read_bytes())

    def test_public_pages_express_the_free_audit_contingency_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            page = (output / "index.html").read_text()
            config = (output / "commercial-config.js").read_text()

            self.assertIn("Find freight money you may be owed", page)
            self.assertIn("Start Free Recovery Audit", page)
            self.assertIn("<strong>$0</strong> upfront audit fee", page)
            self.assertIn("no recovery fee", page.lower())
            self.assertIn('id="auditForm"', page)
            self.assertIn('data-form-step="1"', page)
            self.assertIn('data-form-step="2"', page)
            self.assertIn('data-form-step="3"', page)
            self.assertIn("approved secure intake route", page)
            self.assertIn("Fixed-Fee Forensic Audit", page)
            self.assertIn("Available", page)
            self.assertIn("Potential recovery", page)
            self.assertIn("Approved claim value", page)
            self.assertIn("Actual recovered funds", page)
            self.assertIn("Rate confirmed before engagement", page)
            self.assertIn('contingencyRecoveryRate: "0.3"', config)
            self.assertIn('contingencyRecoveryRateLabel: "30%"', config)
            self.assertIn('itemscope itemtype="https://schema.org/WebPage"', page)
            self.assertIn('itemprop="mainEntity" itemscope itemtype="https://schema.org/Service"', page)
            self.assertIn('itemprop="offers" itemscope itemtype="https://schema.org/Offer"', page)
            self.assertIn('itemprop="priceCurrency" content="USD"', page)
            self.assertIn('itemprop="price" content="0"', page)
            self.assertIn('name="twitter:title"', page)
            self.assertIn('name="twitter:description"', page)
            self.assertIn('name="twitter:image"', page)
            self.assertIn('id="actualRecoveredDisplay">$100,000</dd>', page)
            self.assertIn('content="free-audit-contingency-v3"', page)

            forbidden = (
                "$5,000",
                "$15,000",
                "Start checkout",
                "See prices & checkout",
                "Secure checkout is open",
                "buy.stripe.com",
                "Customer keeps 80%",
                "our recovery fee 20%",
            )
            public_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in output.rglob("*")
                if path.is_file() and path.suffix.lower() in {".html", ".js", ".css", ".txt", ".xml"}
            )
            for phrase in forbidden:
                with self.subTest(phrase=phrase):
                    self.assertNotIn(phrase, public_text)

    def test_contact_is_injected_without_enabling_file_submission(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            index = (output / "index.html").read_text()
            privacy = (output / "privacy.html").read_text()
            engagement = (output / "engagement-framework.html").read_text()
            for page in (index, privacy, engagement):
                self.assertIn('content="sales@freightfixture.com"', page)
                self.assertNotIn(builder.CONTACT_META, page)
            self.assertIn('href="mailto:sales@freightfixture.com', index)
            self.assertIn('href="mailto:sales@freightfixture.com', privacy)
            self.assertNotIn('type="file"', index.lower())
            self.assertIn("form-action 'none'", index)
            self.assertIn("connect-src 'none'", index)

    def test_pages_have_unique_ids_and_resolvable_local_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            for name in ("index.html", "privacy.html", "engagement-framework.html", "404.html"):
                parser = PageParser()
                parser.feed((output / name).read_text())
                self.assertEqual(len(parser.ids), len(set(parser.ids)), name)
                self.assertTrue(all("alt" in image for image in parser.images), name)
                anchors = set(parser.ids)
                for href in parser.links:
                    if not href or href.startswith(("mailto:", "https://")):
                        continue
                    if href == "#contact-pending":
                        continue
                    clean = href.split("?", 1)[0]
                    if clean.startswith("#"):
                        self.assertIn(clean[1:], anchors, f"{name}: {href}")
                    else:
                        file_part, _, fragment = clean.partition("#")
                        target = (output / file_part).resolve() if file_part else (output / name).resolve()
                        self.assertTrue(target.exists(), f"{name}: {href}")
                        if fragment and target.suffix == ".html":
                            target_parser = PageParser()
                            target_parser.feed(target.read_text())
                            self.assertIn(fragment, target_parser.ids, f"{name}: {href}")

    def test_form_and_analytics_scripts_are_local_and_truthful(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            script = (output / "site.js").read_text()
            page = (output / "index.html").read_text()
            self.assertIn('site.css?v=free-audit-contingency-v2', page)
            self.assertIn('commercial-config.js?v=free-audit-contingency-v2', page)
            self.assertIn('site.js?v=free-audit-contingency-v2', page)
            self.assertIn('id="actualRecovery" type="number" min="0" max="1000000000" step="1000" value="100000"', page)
            self.assertIn('<dd id="actualRecoveredDisplay">$100,000</dd>', page)
            self.assertNotIn('value="50000"', page)
            self.assertIn("freight_audit_form_started", script)
            self.assertIn("freight_audit_form_completed", script)
            self.assertIn("freight_data_submitted", script)
            self.assertIn("freight_qualified_lead", script)
            self.assertIn("freight_audit_completed", script)
            self.assertIn("freight_recovery_engagement_accepted", script)
            self.assertIn("freight_actual_recovery_recorded", script)
            self.assertIn("actual * contingencyRate", script)
            self.assertIn("sendLink.href = `mailto:${contactEmail}", script)
            self.assertIn("Nothing has been sent yet", page)
            stylesheet = (output / "site.css").read_text()
            self.assertIn(".output-copy{min-width:0}", stylesheet)
            self.assertIn(".security-layout>*{min-width:0}", stylesheet)
            self.assertIn(".security-image{width:100%;margin:0;position:relative}", stylesheet)
            self.assertIn("overflow-wrap:anywhere", stylesheet)
            self.assertIn(".navlinks{position:absolute;left:0;right:0;top:100%", stylesheet)
            for network_or_storage_api in (
                "fetch(",
                "XMLHttpRequest",
                "sendBeacon",
                "WebSocket",
                "localStorage",
                "sessionStorage",
            ):
                self.assertNotIn(network_or_storage_api, script)

    def test_controlled_demo_is_current_and_clearly_synthetic(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            page = (output / "index.html").read_text()
            self.assertNotIn(builder.DEMO_MARKER, page)
            self.assertIn('href="synthetic-pilot-demo.zip"', page)
            self.assertIn("Fictional data only", page)
            demo = output / builder.DEMO_FILE
            receipt = verify_synthetic_pilot_bundle(demo)
            self.assertEqual(11, receipt["entry_count"])
            self.assertEqual(
                hashlib.sha256(demo.read_bytes()).hexdigest(), receipt["bundle_sha256"]
            )
            self.assertIn(receipt["bundle_sha256"], page)

    def test_fonts_and_images_retain_integrity(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            stylesheet = (output / "site.css").read_text()
            self.assertIn("@font-face", stylesheet)
            self.assertNotIn("https://", stylesheet)
            for name in builder.BINARY_SOURCE_FILES:
                payload = (output / name).read_bytes()
                if name.endswith(".webp"):
                    self.assertEqual(b"RIFF", payload[:4])
                    self.assertEqual(b"WEBP", payload[8:12])
                elif name.endswith(".woff2"):
                    self.assertEqual(b"wOF2", payload[:4])
            attribution = json.loads((output / "assets/fonts/ATTRIBUTION.json").read_text())
            copied_fonts = {
                Path(name).name for name in builder.BINARY_SOURCE_FILES if name.endswith(".woff2")
            }
            for item in attribution["assets"]:
                if item["file"] not in copied_fonts:
                    continue
                font = output / "assets/fonts" / item["file"]
                self.assertEqual(item["sha256"], hashlib.sha256(font.read_bytes()).hexdigest())
                self.assertEqual("SIL Open Font License 1.1", item["license"])

    def test_existing_files_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            marker = output / "keep.txt"
            marker.write_text("unchanged")
            with self.assertRaises(ValueError):
                build(output)
            self.assertEqual(marker.read_text(), "unchanged")
            self.assertEqual(["keep.txt"], [file.name for file in output.iterdir()])


if __name__ == "__main__":
    unittest.main()
