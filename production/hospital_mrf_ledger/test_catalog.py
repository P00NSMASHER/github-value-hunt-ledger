import json
import tempfile
import unittest
from pathlib import Path

import catalog


class HospitalMRFCatalogTests(unittest.TestCase):
    def test_cms_hpt_parser_keeps_public_locator_but_not_contacts(self):
        raw = b"""location-name: Example Hospital
source-page-url: /price-transparency
mrf-url: https://files.example.org/12_example_standardcharges.json
contact-name: Jane Doe
contact-email: jane@example.org

location-name: Second Campus
source-page-url: https://example.org/prices
mrf-url: /files/second.csv
"""
        rows = catalog.parse_cms_hpt_txt(raw, "https://example.org/")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["location_name"], "Example Hospital")
        self.assertEqual(
            rows[0]["source_page_url"],
            "https://example.org/price-transparency",
        )
        self.assertEqual(
            rows[0]["mrf_url"],
            "https://files.example.org/12_example_standardcharges.json",
        )
        self.assertEqual(rows[0]["contact_fields_present"], 1)
        self.assertNotIn("contact_name", rows[0])
        self.assertNotIn("contact_email", rows[0])
        self.assertEqual(
            rows[1]["mrf_url"],
            "https://example.org/files/second.csv",
        )

    def test_malformed_blocks_do_not_create_guessed_urls(self):
        raw = b"""location-name: Missing URL Hospital
source-page-url: https://example.org/prices

location-name: Complete Hospital
source-page-url: https://example.org/prices
mrf-url: https://example.org/complete.json
"""
        rows = catalog.parse_cms_hpt_txt(raw, "https://example.org/")
        self.assertEqual([r["location_name"] for r in rows], ["Complete Hospital"])

    def test_source_registry_loads_reviewed_roots(self):
        payload = {
            "seed_hospitals": [
                {
                    "hospital_name": "Example",
                    "homepage_url": "https://example.org/pricing",
                    "root_url": "https://example.org/",
                    "notes": "reviewed",
                }
            ]
        }
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sources.json"
            p.write_text(json.dumps(payload))
            seeds = catalog.load_sources(p)
        self.assertEqual(len(seeds), 1)
        self.assertEqual(seeds[0].hospital_name, "Example")
        self.assertEqual(seeds[0].root_url, "https://example.org/")
        self.assertEqual(seeds[0].source_key, "example.org")

    def test_content_addressed_storage_is_stable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a_digest, a_rel = catalog.store_bytes(root, b"same bytes")
            b_digest, b_rel = catalog.store_bytes(root, b"same bytes")
            self.assertEqual(a_digest, b_digest)
            self.assertEqual(a_rel, b_rel)
            self.assertTrue((root / a_rel).exists())


if __name__ == "__main__":
    unittest.main()
