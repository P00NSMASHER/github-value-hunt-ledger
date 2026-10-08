#!/usr/bin/env python3
"""Build RETALLY's allowlisted public-only Cloudflare Pages artifact.

Never publish the repository checkout or any directory outside the exact bundle.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
import shutil
import tempfile

from freight.site.build import PUBLIC_FILES as FREIGHT_PUBLIC_FILES, build as build_freight
from freight.site.rebase_public_urls import OLD_BASE, rebase
from recoveryworks.site.build import PUBLIC_FILES as RECOVERY_PUBLIC_FILES, build as build_recoveryos

REPO = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO / "cf-retally-public"
EXPECTED_FILES = len(FREIGHT_PUBLIC_FILES) + len(RECOVERY_PUBLIC_FILES)


def build(output: Path = OUTPUT_DIR) -> Path:
    contact = os.environ.get("FREIGHT_CONTACT_EMAIL", "").strip().lower()
    verified = os.environ.get("FREIGHT_CONTACT_VERIFIED") == "1"
    if not verified or contact != "jay@retallyrecovery.com":
        raise ValueError("Only the verified RETALLY business mailbox may be published")
    output = output.resolve()
    if output == REPO or REPO not in output.parents:
        raise ValueError("Cloudflare build output must be a child of the checkout")
    if output.exists():
        raise ValueError("Refusing to overwrite existing deployment output")

    with tempfile.TemporaryDirectory(prefix="retally-pages-") as workspace:
        root = Path(workspace)
        bundle = root / "public"
        build_freight(bundle, contact, True)
        os.environ["RECOVERYOS_CONTACT_EMAIL"] = contact
        os.environ["RECOVERYOS_CONTACT_VERIFIED"] = "1"
        build_recoveryos(root / "recoveryos")
        shutil.copytree(root / "recoveryos", bundle / "recoveryos")
        rewrites = rebase(bundle)
        published = [path for path in bundle.rglob("*") if path.is_file()]
        if any(path.is_symlink() for path in bundle.rglob("*")):
            raise RuntimeError("Symlinks are forbidden in the public bundle")
        if len(published) != EXPECTED_FILES:
            raise RuntimeError(f"Unexpected public file count: {len(published)} != {EXPECTED_FILES}")
        if OLD_BASE in (bundle / "index.html").read_text(encoding="utf-8"):
            raise RuntimeError("Old site canonical remains")
        if rewrites < 1:
            raise RuntimeError("Public URL rewrite did not occur")
        # Audit every generated public text asset, including RecoveryOS and URL rewrites.
        # Never log the private value if a check fails.
        for path in published:
            if path.suffix.lower() not in {".html", ".txt", ".xml", ".json", ".js", ".css", ".svg", ".csv"}:
                continue
            content = path.read_text(encoding="utf-8").lower()
            if re.search(r"yorktowne|\\b17901\\b|jayp19386\\s*@", content):
                raise RuntimeError(f"Private contact data in public bundle: {path.relative_to(bundle)}")
        shutil.copytree(bundle, output)
    return output


if __name__ == "__main__":
    path = build()
    print(f"Cloudflare RETALLY public bundle ready: {path} ({EXPECTED_FILES} files)")
