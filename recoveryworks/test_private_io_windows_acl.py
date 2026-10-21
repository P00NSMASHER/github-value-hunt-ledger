"""Security contract for private Windows files (no weakening to pass CI)."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from recoveryworks.private_io import _restrict_private_permissions, private_permissions_verified


@unittest.skipUnless(os.name == "nt", "Windows-only ACL assurance")
class WindowsAclTests(unittest.TestCase):
    def test_extra_world_read_ace_is_rejected_and_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic-acl-test.txt"
            path.write_text("synthetic, noncustomer data", encoding="utf-8")
            _restrict_private_permissions(path)
            self.assertTrue(private_permissions_verified(path))

            added = subprocess.run(
                ["icacls.exe", str(path), "/grant", "*S-1-1-0:(R)", "/Q"],
                capture_output=True, text=True, check=False, timeout=10,
            )
            self.assertEqual(added.returncode, 0, added.stderr)
            self.assertFalse(private_permissions_verified(path),
                             "private ACL verifier must reject unexpected explicit Everyone ACE")
            _restrict_private_permissions(path)
            self.assertTrue(private_permissions_verified(path))

    def test_inherited_ace_is_rejected_until_hardened(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic-inherit-test.txt"
            path.write_text("synthetic only", encoding="utf-8")
            self.assertFalse(private_permissions_verified(path))
            _restrict_private_permissions(path)
            self.assertTrue(private_permissions_verified(path))


if __name__ == "__main__":
    unittest.main()
