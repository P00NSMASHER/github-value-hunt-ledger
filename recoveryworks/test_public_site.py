from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from recoveryworks.site.build import CONTACT_TOKEN, PUBLIC_FILES, build


class RecoveryOSSiteBuildTests(unittest.TestCase):
    def test_public_build_is_exact_and_contact_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "public"
            with patch.dict(
                "os.environ",
                {
                    "RECOVERYOS_CONTACT_EMAIL": "owner@recovery.test",
                    "RECOVERYOS_CONTACT_VERIFIED": "1",
                },
                clear=True,
            ):
                build(output)

            actual = {
                path.relative_to(output).as_posix()
                for path in output.rglob("*")
                if path.is_file()
            }
            self.assertEqual(set(PUBLIC_FILES), actual)
            index = (output / "index.html").read_text(encoding="utf-8")
            self.assertNotIn(CONTACT_TOKEN, index)
            self.assertIn("owner@recovery.test", index)
            self.assertIn("Nothing was uploaded", (output / "site.js").read_text(encoding="utf-8"))

    def test_build_requires_verified_contact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(
                "os.environ",
                {"RECOVERYOS_CONTACT_EMAIL": "owner@recovery.test"},
                clear=True,
            ):
                with self.assertRaisesRegex(RuntimeError, "RECOVERYOS_CONTACT_VERIFIED"):
                    build(Path(temporary) / "public")

    def test_build_rejects_placeholder_contact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(
                "os.environ",
                {
                    "RECOVERYOS_CONTACT_EMAIL": "sales@example.com",
                    "RECOVERYOS_CONTACT_VERIFIED": "1",
                },
                clear=True,
            ):
                with self.assertRaisesRegex(RuntimeError, "verified public business inbox"):
                    build(Path(temporary) / "public")

    def test_build_rejects_nonempty_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "public"
            output.mkdir()
            (output / "unexpected.txt").write_text("x", encoding="utf-8")
            with patch.dict(
                "os.environ",
                {
                    "RECOVERYOS_CONTACT_EMAIL": "owner@recovery.test",
                    "RECOVERYOS_CONTACT_VERIFIED": "1",
                },
                clear=True,
            ):
                with self.assertRaisesRegex(RuntimeError, "must be empty"):
                    build(output)


if __name__ == "__main__":
    unittest.main()
