"""Build the public RecoveryOS site from an exact allowlist."""

from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path


SITE_DIR = Path(__file__).resolve().parent
TEXT_FILES = ("index.html", "site.css", "site.js", "_headers", "favicon.svg")
ASSET_FILES = (
    "analyst-review.webp",
    "construction-project.webp",
    "healthcare-operations.webp",
    "hero-industrial.webp",
    "proof-stack.webp",
    "familjen-grotesk-latin-wght-normal.woff2",
    "newsreader-latin-wght-italic.woff2",
    "newsreader-latin-wght-normal.woff2",
    "LICENSE-Familjen-Grotesk.txt",
    "LICENSE-Newsreader.txt",
)
PUBLIC_FILES = TEXT_FILES + tuple(f"assets/{name}" for name in ASSET_FILES)
CONTACT_TOKEN = "{{CONTACT_EMAIL}}"
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _safe_source(relative_path: str) -> Path:
    source = SITE_DIR / relative_path
    if source.is_symlink() or not source.is_file():
        raise RuntimeError(f"Required public source is missing or unsafe: {relative_path}")
    return source


def _verified_contact() -> str:
    email = os.environ.get("RECOVERYOS_CONTACT_EMAIL", "").strip()
    verified = os.environ.get("RECOVERYOS_CONTACT_VERIFIED", "").strip()
    if verified != "1":
        raise RuntimeError("RECOVERYOS_CONTACT_VERIFIED must be 1 before publication")
    if not EMAIL_PATTERN.fullmatch(email) or "example." in email.lower():
        raise RuntimeError("RECOVERYOS_CONTACT_EMAIL must be a verified public business inbox")
    return email


def build(output: Path) -> None:
    contact = _verified_contact()
    output = output.resolve()
    if output == SITE_DIR or SITE_DIR in output.parents:
        raise RuntimeError("Output must be outside the RecoveryOS site source directory")
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("Output directory must be empty")
    output.mkdir(parents=True, exist_ok=True)

    for relative_path in TEXT_FILES:
        source = _safe_source(relative_path)
        text = source.read_text(encoding="utf-8")
        if relative_path == "index.html":
            if CONTACT_TOKEN not in text:
                raise RuntimeError("Contact placeholder is missing from index.html")
            text = text.replace(CONTACT_TOKEN, contact)
        destination = output / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8", newline="\n")

    for name in ASSET_FILES:
        source = _safe_source(f"assets/{name}")
        destination = output / "assets" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    actual = tuple(
        path.relative_to(output).as_posix()
        for path in sorted(output.rglob("*"))
        if path.is_file()
    )
    if set(actual) != set(PUBLIC_FILES):
        raise RuntimeError(f"Unexpected publication boundary: {actual!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.output)


if __name__ == "__main__":
    main()
