#!/usr/bin/env python3
"""Rebase absolute public-site URLs in a generated, public-only RETALLY bundle.

Only the generated deployment directory is modified; repository sources remain unchanged.
"""
from __future__ import annotations

import argparse
from pathlib import Path

OLD_BASE = "https://p00nsmasher.github.io/github-value-hunt-ledger/"
NEW_BASE = "https://www.retallyrecovery.com/"
TEXT_SUFFIXES = {".html", ".xml", ".txt", ".json", ".js", ".css", ".svg"}


def rebase(directory: Path) -> int:
    if not directory.is_dir():
        raise ValueError("Public bundle directory does not exist")
    replacements = 0
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Public bundle contains a symlink: {path}")
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        source = path.read_text(encoding="utf-8")
        count = source.count(OLD_BASE)
        if count:
            path.write_text(source.replace(OLD_BASE, NEW_BASE), encoding="utf-8")
            replacements += count
    if replacements < 1:
        raise ValueError("No previous absolute site URLs found; check the public site source")
    for path in directory.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            if OLD_BASE in path.read_text(encoding="utf-8"):
                raise ValueError(f"Unconverted absolute site URL: {path}")
    return replacements


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    arguments = parser.parse_args()
    print(f"Rebased {rebase(arguments.directory)} absolute public URLs to {NEW_BASE}")
