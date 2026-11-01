"""Source-wide privacy regression checks for RETALLY's *public GitHub repository*.

The site-build checks protect only deployed artifacts; documents and code in
the public repository are separately readable. Do not embed actual residential
addresses, old personal mailbox addresses, or matched values in test logs.
"""
from pathlib import Path
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
SKIP_SUFFIXES = frozenset({
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".ico",
    ".pdf", ".doc", ".docx", ".xlsx", ".xls", ".pptx", ".ppt",
    ".zip", ".gz", ".7z", ".tar", ".woff", ".woff2", ".ttf",
    ".otf", ".mp4", ".mov", ".mp3", ".wav", ".sqlite", ".db",
})
# The checks deliberately retain only the street *name* and legacy mailbox
# prefix, never the full residential address or complete personal email.
PRIVATE_STREET = re.compile(
    r"\b\d{1,5}\s+Yorktowne\s+(?:Road|Rd\.?)(?![a-z])", re.IGNORECASE
)
LEGACY_EMAIL = re.compile(
    r"\bjayp19386@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", re.IGNORECASE
)


def flags(content: str) -> list[str]:
    """Return finding categories, never the matched confidential values."""
    issues = []
    if PRIVATE_STREET.search(content):
        issues.append("residential_street")
    if LEGACY_EMAIL.search(content):
        issues.append("legacy_personal_inbox")
    return issues


def tracked_text_files() -> list[Path]:
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT, capture_output=True, check=True
    ).stdout
    paths = []
    for raw in tracked.split(b"\0"):
        if not raw:
            continue
        relative = Path(raw.decode("utf-8", errors="surrogateescape"))
        file = ROOT / relative
        if file.is_file() and file.suffix.lower() not in SKIP_SUFFIXES:
            paths.append(file)
    return paths


class PublicSourcePrivacyTests(unittest.TestCase):
    def test_detection_fixtures_fail_closed(self):
        self.assertEqual(flags("General freight marketing copy"), [])
        # Use a *synthetic* street number, assembled from fragments so the
        # test source does not itself expose the address under protection.
        self.assertIn("residential_street", flags("500 " + "Yorktowne" + " Road"))
        self.assertIn(
            "legacy_personal_inbox", flags("jayp19386@" + "example.invalid")
        )

    def test_all_git_tracked_public_text_rejects_private_contact_identifiers(self):
        files = tracked_text_files()
        self.assertGreater(len(files), 100)
        violations = []
        for file in files:
            data = file.read_bytes()
            if b"\0" in data[:4096]:
                continue
            content = data.decode("utf-8", errors="replace")
            for issue in flags(content):
                violations.append(f"{file.relative_to(ROOT)}: {issue}")
        self.assertEqual(
            violations, [],
            "Private contact material in tracked public source (values suppressed): "
            + "; ".join(violations[:30])
        )


if __name__ == "__main__":
    unittest.main()
