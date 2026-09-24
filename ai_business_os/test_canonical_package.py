import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "business_os"
MANIFEST = LEGACY / "ARCHIVED_SOURCE_MANIFEST.json"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


class CanonicalPackageTests(unittest.TestCase):
    def test_legacy_python_tree_is_frozen(self):
        manifest = json.loads(MANIFEST.read_text())
        expected = {row["path"]: row["git_blob_sha"] for row in manifest["python_files"]}
        actual = sorted(path.relative_to(ROOT).as_posix() for path in LEGACY.rglob("*.py"))
        self.assertEqual(sorted(expected), actual)
        changed = [path for path, sha in expected.items() if git_blob_sha(ROOT / path) != sha]
        self.assertEqual([], changed)

    def test_no_external_python_imports_legacy_package(self):
        offenders = []
        pattern = re.compile(r"^\s*(?:from\s+business_os\b|import\s+business_os\b)", re.M)
        for path in ROOT.rglob("*.py"):
            rel = path.relative_to(ROOT)
            if rel.parts and rel.parts[0] == "business_os":
                continue
            if any(part in {".git", ".venv", "venv"} for part in rel.parts):
                continue
            if pattern.search(path.read_text(encoding="utf-8", errors="replace")):
                offenders.append(rel.as_posix())
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
