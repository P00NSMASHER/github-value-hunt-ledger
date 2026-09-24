import json
import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG_DIR = ROOT / "supabase" / "migrations" / "ai_business_os"
MANIFEST = MIG_DIR / "manifest.json"


class ProductionMigrationArchiveTests(unittest.TestCase):
    def test_manifest_is_ordered_and_hash_bound_to_live_history(self):
        manifest = json.loads(MANIFEST.read_text())
        rows = manifest["migrations"]
        versions = [row["version"] for row in rows]
        self.assertEqual(sorted(versions), versions)
        self.assertEqual(len(versions), len(set(versions)))
        self.assertEqual(manifest["migration_count"], len(rows))
        self.assertEqual(manifest["latest_version"], versions[-1])
        for row in rows:
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")

    def test_sanitized_bootstrap_preserves_exact_migration_order(self):
        manifest = json.loads(MANIFEST.read_text())
        text = (MIG_DIR / "bootstrap.sql").read_text()
        positions = []
        for row in manifest["migrations"]:
            marker = f"-- MIGRATION {row['version']} {row['name']}"
            self.assertEqual(1, text.count(marker), marker)
            positions.append(text.index(marker))
        self.assertEqual(sorted(positions), positions)
        self.assertTrue(manifest["public_bootstrap_sanitized"])
        for placeholder in manifest["private_seed_placeholders"]:
            self.assertIn(placeholder, text)

    def test_live_schema_fingerprint_shape(self):
        manifest = json.loads(MANIFEST.read_text())
        self.assertRegex(manifest["live_schema_fingerprint_sha256"], r"^[0-9a-f]{64}$")

    def test_optional_private_live_drift_check(self):
        supplied = os.environ.get("AI_BUSINESS_OS_LIVE_SCHEMA_FINGERPRINT")
        if supplied:
            manifest = json.loads(MANIFEST.read_text())
            self.assertEqual(manifest["live_schema_fingerprint_sha256"], supplied)


if __name__ == "__main__":
    unittest.main()
