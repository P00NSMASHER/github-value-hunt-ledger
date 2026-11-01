"""Enforce exact immutable source identity of historical PR #329 first-customer materials."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name("FIRST_CUSTOMER_ORIGINAL_SOURCES.json")
HOLD = Path(__file__).with_name("FIRST_CUSTOMER_REVIEW_HOLD.md")


def test_source_equivalence_and_release_hold():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["source_pr"] == 329
    assert manifest["scope"] == "REVIEW_ONLY_UNRELEASED_CUSTOMER_EVIDENCE"
    assert len(manifest["files"]) == 45
    for field in ("launch_approved", "customer_data_authorized", "payment_authorized", "external_actions_authorized"):
        assert manifest[field] is False
    seen = set()
    for row in manifest["files"]:
        path = row["path"]
        assert path.startswith("freight/") and path not in seen
        seen.add(path)
        raw = (ROOT / path).read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + bytes([0]) + raw).hexdigest()
        assert actual == row["git_blob_sha"], (path, actual, row["git_blob_sha"])
    text = HOLD.read_text(encoding="utf-8")
    assert "NO-GO" in text and "not present-day certification" in text
