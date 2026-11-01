"""No real logo bytes are used here: fail-closed importer unit tests."""
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "source"))
from import_approved_masters import import_approved, ALLOWED


class ApprovedAssetImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name) / "project"
        (self.project / "source").mkdir(parents=True)
        self.original = {name: (b"controlled-test-data:" + name.encode("ascii")) for name in ALLOWED}
        hashes = {("wordmark" if "wordmark" in name else "emblem") + "_sha256":
                  hashlib.sha256(value).hexdigest() for name, value in self.original.items()}
        (self.project / "source" / "commercial_truth.json").write_text(json.dumps({"approved_brand": hashes}))
        self.archive = Path(self.tmp.name) / "assets.zip"
        with zipfile.ZipFile(self.archive, "w") as z:
            for name, payload in self.original.items():
                z.writestr("freight/brand/mission2b/assets/" + name, payload)

    def test_import_and_check_only(self):
        self.assertEqual(len(import_approved(self.archive, self.project, True)), 2)
        self.assertFalse((self.project / "assets").exists())
        self.assertEqual(len(import_approved(self.archive, self.project)), 2)
        for name, payload in self.original.items():
            self.assertEqual((self.project / "assets" / name).read_bytes(), payload)

    def test_tampered_bytes_preserve_existing(self):
        import_approved(self.archive, self.project)
        tampered = Path(self.tmp.name) / "tampered.zip"
        with zipfile.ZipFile(tampered, "w") as z:
            for name, payload in self.original.items():
                z.writestr("x/assets/" + name, payload + b"!" if "emblem" in name else payload)
        with self.assertRaisesRegex(ValueError, "unapproved binary"):
            import_approved(tampered, self.project)
        for name, payload in self.original.items():
            self.assertEqual((self.project / "assets" / name).read_bytes(), payload)

    def test_reject_duplicate_named_entries(self):
        duplicate = Path(self.tmp.name) / "duplicate.zip"
        with zipfile.ZipFile(duplicate, "w") as z:
            for name, payload in self.original.items():
                z.writestr("one/assets/" + name, payload)
                if "wordmark" in name:
                    z.writestr("two/assets/" + name, payload)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            import_approved(duplicate, self.project)
        self.assertFalse((self.project / "assets").exists())


if __name__ == "__main__":
    unittest.main()
