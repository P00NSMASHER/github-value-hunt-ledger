"""Read-only, no-dependency Git-blob archival integrity check; no source execution."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = Path(__file__).resolve().parent


def main() -> None:
    data = json.loads((ARCHIVE / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["kind"] == "TEST_ONLY_HISTORICAL_SOURCE_ARCHIVE"
    assert data["authority"] == "REVIEW_ONLY_NOT_PRODUCTION_OR_VERIFIED_CUSTOMER_DATA"
    records = data["records"]
    assert len(records) == data["record_count"] == 11
    assert {r["origin_pr"] for r in records} == {646, 653, 656}
    seen = set()
    for item in records:
        dest = item["archived_path"]
        assert dest.startswith("research/retally-redteam-archive/pr")
        assert ".." not in Path(dest).parts and dest not in seen
        seen.add(dest)
        target = ROOT / dest
        assert target.is_file() and not target.is_symlink(), dest
        original = item["original_path"]
        assert dest == f"research/retally-redteam-archive/pr{item['origin_pr']}/{original}"
        expected = item["original_blob_sha"]
        assert len(expected) == 40 and all(c in "0123456789abcdef" for c in expected)
        actual = subprocess.run(["git", "hash-object", "--", str(target)],
                                capture_output=True, text=True, check=True).stdout.strip()
        assert actual == expected, dest
        if original.endswith(".py"):
            ast.parse(target.read_text(encoding="utf-8"), filename=dest)
    assert len(seen) == 11
    print("PASS: 11/11 historical Git blobs exact, Python syntax parsed, no execution/deploy")


if __name__ == "__main__":
    main()
