#!/usr/bin/env python3
"""Verify every byte-exact historical source without importing or executing it."""
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "research" / "retally_first_customer_archive"
PREFIX = "research/retally_first_customer_archive/sources/pr-329/"
SOURCE_HEAD = "a77ecc03b45425a15e2cd3f1a49b14e229ad4f78"


def main():
    m = json.loads((FOLDER / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    assert m["authority"] == "HISTORICAL_SOURCE_ONLY_NOT_PRODUCTION_OR_CUSTOMER_APPROVAL"
    assert m["source_head"] == SOURCE_HEAD and m["source_pr"] == 329
    assert m["archive_review_only"] is True and m["no_live_customer_or_cash_authority"] is True
    assert len(m["records"]) == m["original_pr_file_count"] == 86
    assert sum(r["status"] == "modified" for r in m["records"]) == 41
    assert sum(r["status"] == "added" for r in m["records"]) == 45
    assert len({r["original_path"] for r in m["records"]}) == 86
    assert len({r["archived_path"] for r in m["records"]}) == 86
    for r in m["records"]:
        assert r["pr"] == 329 and r["pr_head"] == SOURCE_HEAD
        assert r["status"] in ("added", "modified")
        assert re.fullmatch(r"[0-9a-f]{40}", r["blob_sha"])
        assert r["archived_path"] == PREFIX + r["original_path"]
        assert r["original_path"].startswith(("freight/", ".github/"))
        assert all(part not in ("", ".", "..") for part in Path(r["archived_path"]).parts)
        file = ROOT / r["archived_path"]
        assert file.is_file(), r["archived_path"]
        result = subprocess.run(["git", "hash-object", "--", str(file)],
                                check=True, capture_output=True, text=True, cwd=ROOT)
        assert result.stdout.strip() == r["blob_sha"], r["archived_path"]
    assert not (ROOT / "freight" / "commercial" / "historical_first_customer_rehearsal.py").exists(), "Do not install historical code directly"
    print("PASS: 86 historical Git blobs verified; all 45 added and 41 modified originals preserved as review-only inert sources.")


if __name__ == "__main__":
    main()
