"""Offline cryptographic acceptance plus real Workspace snapshot round-trip."""
from __future__ import annotations
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recoveryworks.offsite_archive import seal_bytes, unseal_bytes, seal_file, verify_file, restore_file
from recoveryworks.seven_branch_simulation import seed


@unittest.skipUnless(importlib.util.find_spec("cryptography"), "optional offsite crypto package absent")
class OffsiteArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Build one *immutable* original snapshot, avoiding repeated Windows
        ACL/PowerShell setup for the same seven-branch synthetic population.

        Each test still writes its own archive and restores to its own
        isolated directory. Real scrypt/AES-GCM operations are NOT mocked.
        """
        super().setUpClass()
        cls.fixture_temp = tempfile.TemporaryDirectory()
        try:
            fixture_root = Path(cls.fixture_temp.name)
            cls.workspace, cls.tokens = seed(fixture_root / "synthetic")
            cls.workspace.scan(cls.tokens["operator"])
            receipt = cls.workspace.backup(cls.tokens["operator"])
            cls.snapshot = cls.workspace.root / "backups" / (receipt["snapshot_id"] + ".json")
            cls.snapshot_sha256 = hashlib.sha256(cls.snapshot.read_bytes()).hexdigest()
        except BaseException:
            cls.fixture_temp.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            assert hashlib.sha256(cls.snapshot.read_bytes()).hexdigest() == cls.snapshot_sha256, (
                "shared original snapshot changed during encrypted-archive tests"
            )
        finally:
            cls.fixture_temp.cleanup()
            super().tearDownClass()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.assertEqual(hashlib.sha256(self.snapshot.read_bytes()).hexdigest(),
                         self.snapshot_sha256)
        self.password = "test-only-passphrase-with-at-least-twenty-characters"

    def tearDown(self):
        self.assertEqual(hashlib.sha256(self.snapshot.read_bytes()).hexdigest(),
                         self.snapshot_sha256, "archive test mutated the shared source")
        super().tearDown()

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

    def test_verify_hashes_the_same_ciphertext_that_was_authenticated(self):
        archive = self.root / "verify-once.rtbk"
        seal_file(self.snapshot, archive, self.password)
        original_read = Path.read_bytes
        archive_reads = 0

        def simulate_replacement_between_reads(path):
            nonlocal archive_reads
            if path == archive:
                archive_reads += 1
                if archive_reads > 1:
                    return b"replaced-after-authentication"
            return original_read(path)

        with patch.object(Path, "read_bytes", simulate_replacement_between_reads):
            verified = verify_file(archive, self.password)
        self.assertEqual(archive_reads, 1, "verification must not read the archive twice")
        self.assertEqual(verified["sealed_sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())
        self.assertTrue(verified["restore_verified"])
        self.assertFalse(verified["off_device_verified"])

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