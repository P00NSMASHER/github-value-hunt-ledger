"""Fail-closed import of RETALLY's exact approved logo master PNGs.

Usage:
  python source/import_approved_masters.py /path/to/RETALLY_Mission2D_Approved_Master_Transfer.zip
  python source/import_approved_masters.py /path/to/zip --check-only

Only the two approved sources are extracted. No network, GitHub write, or deployment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
ALLOWED = ("retally-wordmark-approved.png", "retally-emblem-approved.png")


def import_approved(zip_path: Path, project: Path = PROJECT, check_only: bool = False) -> dict[str, str]:
    truth = json.loads((project / "source" / "commercial_truth.json").read_text(encoding="utf-8"))
    approved = truth["approved_brand"]
    data: dict[str, bytes] = {}
    hashes: dict[str, str] = {}
    with zipfile.ZipFile(zip_path) as archive:
        for filename in ALLOWED:
            matches = [entry for entry in archive.infolist()
                       if not entry.is_dir() and entry.filename.replace(chr(92), "/").endswith("/assets/" + filename)]
            if len(matches) != 1:
                raise ValueError(f"expected exactly one approved {filename}; found {len(matches)}")
            entry = matches[0]
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(f"symbolic link prohibited: {entry.filename}")
            payload = archive.read(entry)
            digest = hashlib.sha256(payload).hexdigest()
            kind = "wordmark" if "wordmark" in filename else "emblem"
            if digest != approved[f"{kind}_sha256"]:
                raise ValueError(f"unapproved binary for {filename}: hash mismatch")
            data[filename], hashes[filename] = payload, digest
    if not check_only:
        output = project / "assets"
        output.mkdir(parents=True, exist_ok=True)
        for name, payload in data.items():
            descriptor, temp_path = tempfile.mkstemp(prefix=".retally-approved-", dir=str(output))
            try:
                with os.fdopen(descriptor, "wb") as output_file:
                    output_file.write(payload)
                os.replace(temp_path, output / name)
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
    return hashes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    for name, sha in import_approved(args.zip_path, check_only=args.check_only).items():
        print(f"{'VERIFIED' if args.check_only else 'IMPORTED'} {name} SHA256={sha}")
