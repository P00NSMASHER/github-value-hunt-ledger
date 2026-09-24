import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG_DIR = ROOT / "supabase" / "migrations" / "ai_business_os"

BANNED_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".sqlite", ".sqlite3", ".db"}
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
STRIPE_ACCOUNT = re.compile(r"\bacct_[A-Za-z0-9]{8,}\b")
DATABASE_URL = re.compile(r"\bpostgres(?:ql)?://[^\s\"']+")


class PublicBoundaryTests(unittest.TestCase):
    def test_no_private_runtime_files_under_canonical_public_surfaces(self):
        roots = [ROOT / "ai_business_os", MIG_DIR]
        bad = []
        for base in roots:
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if path.is_file() and path.suffix.lower() in BANNED_SUFFIXES:
                    bad.append(path.relative_to(ROOT).as_posix())
        self.assertEqual([], bad)

    def test_public_migration_bootstrap_contains_no_live_identifiers(self):
        text = (MIG_DIR / "bootstrap.sql").read_text(encoding="utf-8")
        self.assertIsNone(STRIPE_ACCOUNT.search(text))
        self.assertIsNone(EMAIL.search(text))
        self.assertIsNone(DATABASE_URL.search(text))
        self.assertIn("__PRIVATE_STRIPE_ACCOUNT_ID_1__", text)

    def test_public_production_json_contains_no_obvious_live_identifiers(self):
        bad = []
        for path in (ROOT / "ai_business_os").glob("PRODUCTION_*.json"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if STRIPE_ACCOUNT.search(text) or EMAIL.search(text) or DATABASE_URL.search(text):
                bad.append(path.name)
        self.assertEqual([], bad)


if __name__ == "__main__":
    unittest.main()
