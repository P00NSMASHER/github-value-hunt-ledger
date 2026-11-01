"""Enforce immutable historical source IDs and explicit, bounded compatibility deltas."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name("FIRST_CUSTOMER_ORIGINAL_SOURCES.json")
HOLD = Path(__file__).with_name("FIRST_CUSTOMER_REVIEW_HOLD.md")
COMPATIBILITY_PATHS = frozenset({
    "freight/commercial/test_zero_upfront_underwriting.py",
    "freight/test_engagement_resolution_integrity.py",
    "freight/test_fmcsa_public_carrier.py",
    "freight/commercial/remaining_gate_rehearsal.py",
    "freight/test_first_customer_rehearsal.py",
})


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + bytes([0]) + raw).hexdigest()


def test_source_equivalence_and_release_hold():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["source_pr"] == 329
    assert manifest["scope"] == "REVIEW_ONLY_UNRELEASED_CUSTOMER_EVIDENCE"
    assert len(manifest["files"]) == 45
    assert manifest["source_provenance"].startswith("40_ORIGINAL_GIT_BLOBS_PLUS_5_")
    for field in ("launch_approved", "customer_data_authorized", "payment_authorized", "external_actions_authorized"):
        assert manifest[field] is False
    seen = set()
    adapted = set()
    for row in manifest["files"]:
        path = row["path"]
        assert path.startswith("freight/") and path not in seen
        seen.add(path)
        assert len(row["git_blob_sha"]) == 40
        raw = (ROOT / path).read_bytes()
        actual = _git_blob_sha(raw)
        if "integrated_git_blob_sha" in row:
            assert path in COMPATIBILITY_PATHS
            assert row["integrated_git_blob_sha"] != row["git_blob_sha"]
            assert row["compatibility_note"]
            assert actual == row["integrated_git_blob_sha"], (path, actual)
            adapted.add(path)
        else:
            assert actual == row["git_blob_sha"], (path, actual)
    assert adapted == COMPATIBILITY_PATHS
    historical = manifest["supplemental_historical_module"]
    assert historical["source_pr"] == 329
    assert historical["status"] == "HISTORICAL_SYNTHETIC_TEST_ONLY"
    assert historical["original_path"] == "freight/synthetic_rehearsal.py"
    assert historical["path"] == "freight/commercial/historical_first_customer_rehearsal.py"
    assert _git_blob_sha((ROOT / historical["path"]).read_bytes()) == historical["git_blob_sha"]
    text = HOLD.read_text(encoding="utf-8")
    assert "NO-GO" in text and "not present-day certification" in text
    assert "40 **byte-exact**" in text
