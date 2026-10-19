"""Offline cryptographic acceptance plus real Workspace snapshot round-trip."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from recoveryworks.offsite_archive import seal_bytes, unseal_bytes, seal_file, verify_file, restore_file
from recoveryworks.seven_branch_simulation import seed


@unittest.skipUnless(importlib.util.find_spec("cryptography"), "optional offsite crypto package absent")
class OffsiteArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace, self.tokens = seed(self.root / "synthetic")
        self.workspace.scan(self.tokens["operator"])
        receipt = self.workspace.backup(self.tokens["operator"])
        self.snapshot = self.workspace.root / "backups" / (receipt["snapshot_id"] + ".json")
        self.password = "test-only-passphrase-with-at-least-twenty-characters"

    def test_encryption_stores_no_plaintext_and_restores_credentials_revoked(self):
        archive = self.root / "sealed.rtbk"
        result = seal_file(self.snapshot, archive, self.password)
        self.assertTrue(result["verified_locally"])
        self.assertFalse(result["off_device_verified"])
        self.assertNotIn(b"SIMULATED-CUSTOMER-ONLY", archive.read_bytes())
        self.assertEqual(verify_file(archive, self.password)["restore_verified"], True)
        dest = self.root / "recovered"
        restored = restore_file(archive, dest, self.password)
        self.assertTrue(restored["all_credentials_revoked"])
        for token in self.tokens.values():
            with self.assertRaises(PermissionError):
                from recoveryworks.workbench import Workspace
                Workspace(dest).principal(token)

    def test_wrong_password_header_mutation_tag_mutation_and_truncation_fail(self):
        raw = self.snapshot.read_bytes()
        sealed = seal_bytes(raw, self.password)
        with self.assertRaises(ValueError):
            unseal_bytes(sealed, "this-is-a-wrong-password-that-is-long-enough")
        for changed in [sealed[:-1], sealed[:-28] + bytes([sealed[-28] ^ 1]) + sealed[-27:],
                        sealed[:36] + bytes([sealed[36] ^ 1]) + sealed[37:]]:
            with self.subTest(size=len(changed)), self.assertRaises(ValueError):
                unseal_bytes(changed, self.password)

    def test_no_overwrite_and_no_restored_key_resurrection(self):
        dest = self.root / "sealed.rtbk"
        seal_file(self.snapshot, dest, self.password)
        with self.assertRaises(ValueError):
            seal_file(self.snapshot, dest, self.password)
        restored = self.root / "restored"
        restore_file(dest, restored, self.password)
        with self.assertRaises(ValueError):
            restore_file(dest, restored, self.password)


if __name__ == "__main__":
    unittest.main()