"""Material Scout evidence regressions executed by the existing release gate."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.public_repo_scout import (
    integrate, persist_snapshot, queued_pairs, worker_run,
)
from tools.retally_scout_pr_dedupe import (
    REPO, evidence_value, matching_open_proposal, semantic_fingerprint,
)


PATH = "intelligence/scout_queue/HUNTER-14.json"


def row(revision="a" * 40, *, license_id="MIT", score=35):
    return {
        "repository": "Example/Scout", "exact_revision": revision,
        "status": "PRE_VERIFICATION_CANDIDATE",
        "published_license_spdx": license_id,
        "triage_score": score, "stars": 12, "forks": 2,
        "size_kb": 123, "pushed_at": "2026-10-20T00:00:00Z",
    }


def snapshot(revision="a" * 40, *, license_id="MIT", score=35):
    return {
        "schema_version": 2, "worker_id": "HUNTER-14",
        "authority": "PRE_VERIFICATION_DISCOVERY_ONLY",
        "candidate_count": 1, "candidates": [
            row(revision, license_id=license_id, score=score)],
        "risk_review": [], "risk_review_count": 0,
        "generated_at": "2026-10-26T00:00:00Z",
        "api_metrics": {"api_requests": 4, "known_revision_skips": 0},
        "search_diagnostics": [{"query": "a", "returned": 1}],
    }


class ScoutMaterialEvidenceTests(unittest.TestCase):
    def test_timestamp_only_queue_is_byte_identical_after_second_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "HUNTER-14.json"
            original = snapshot()
            self.assertTrue(persist_snapshot(path, original))
            prior_bytes = path.read_bytes()
            rerun = snapshot()
            rerun["generated_at"] = "2026-10-27T00:00:00Z"
            rerun["api_metrics"] = {"api_requests": 888, "known_revision_skips": 42}
            rerun["search_diagnostics"] = [{"query": "a", "returned": 0}]
            rerun["candidates"][0]["size_kb"] = 999
            rerun["candidates"][0]["pushed_at"] = "2026-10-27T00:00:00Z"
            self.assertFalse(persist_snapshot(path, rerun))
            self.assertEqual(path.read_bytes(), prior_bytes)

    def test_new_exact_revision_must_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "HUNTER-14.json"
            persist_snapshot(path, snapshot())
            self.assertTrue(persist_snapshot(path, snapshot("b" * 40)))
            self.assertEqual(json.loads(path.read_text())["candidates"][0]
                             ["exact_revision"], "b" * 40)

    def test_meaningful_withdrawal_must_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "HUNTER-14.json"
            persist_snapshot(path, snapshot())
            removed = snapshot()
            removed["candidates"] = []
            removed["candidate_count"] = 0
            self.assertTrue(persist_snapshot(path, removed))

    def test_license_and_priority_changes_still_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "HUNTER-14.json"
            persist_snapshot(path, snapshot())
            self.assertTrue(persist_snapshot(path, snapshot(license_id="UNKNOWN")))
            self.assertTrue(persist_snapshot(path, snapshot(license_id="UNKNOWN", score=50)))

    def test_digest_clock_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / "HUNTER-14.json"
            queue.write_text(json.dumps(snapshot()))
            digest = root / "digest.md"
            self.assertEqual(integrate(root, digest), 1)
            first = digest.read_bytes()
            self.assertEqual(integrate(root, digest), 1)
            self.assertEqual(digest.read_bytes(), first)
            changed = snapshot("b" * 40)
            queue.write_text(json.dumps(changed))
            integrate(root, digest)
            self.assertNotEqual(digest.read_bytes(), first)
            self.assertIn("bbbbbbbbbbbb", digest.read_text())

    def test_own_pending_queue_does_not_suppress_its_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "HUNTER-14.json").write_text(json.dumps(snapshot()))
            self.assertIn(("example/scout", "a" * 40), queued_pairs(root))
            self.assertEqual(queued_pairs(root, exclude_worker="HUNTER-14"), set())

    def test_own_queued_revision_remains_discoverable(self):
        class GH:
            stats = {"api_requests": 0, "known_revision_skips": 0}
            def search(self, query, per_page):
                return [{"full_name": "Example/Scout", "default_branch": "main",
                         "name": "Scout", "description": "Substantive material",
                         "license": {"spdx_id": "MIT"}, "stargazers_count": 3,
                         "size": 123, "topics": []}]
            def revision(self, full, branch):
                return "a" * 40
            def root(self, full, branch):
                return ["src", "tests"]
        with patch("tools.public_repo_scout.time.sleep"):
            data = worker_run({"id": "HUNTER-14", "queries": ["test"]},
                              GH(), "", REPO, 8, 16, prior_pairs=set())
        self.assertEqual(data["candidate_count"], 1)
        self.assertEqual(data["candidates"][0]["exact_revision"], "a" * 40)

    def test_fingerprints_ignore_run_metrics_and_clocks(self):
        first = snapshot()
        second = snapshot()
        second["generated_at"] = "2030-01-01T00:00:00Z"
        second["api_metrics"] = {"api_requests": 900}
        second["candidates"][0]["stars"] = 900
        before = semantic_fingerprint({PATH: json.dumps(first)})
        after = semantic_fingerprint({PATH: json.dumps(second)})
        self.assertEqual(before, after)
        self.assertNotEqual(before,
                            semantic_fingerprint({PATH: json.dumps(snapshot("b"*40))}))

    def test_digest_fingerprint_ignores_only_generation_clock(self):
        a = "# Scout\nGenerated: 2026-10-21T00:00:00Z\nQueue snapshots read: 14\n"
        b = "# Scout\nGenerated: 2026-10-25T00:00:00Z\nQueue snapshots read: 14\n"
        c = b.replace("read: 14", "read: 13")
        self.assertEqual(evidence_value("automation/SCOUT_DIGEST.md", a),
                         evidence_value("automation/SCOUT_DIGEST.md", b))
        self.assertNotEqual(semantic_fingerprint({"automation/SCOUT_DIGEST.md": a}),
                            semantic_fingerprint({"automation/SCOUT_DIGEST.md": c}))

    def test_open_pr_reuse_requires_authorized_head_and_marker(self):
        sha = semantic_fingerprint({PATH: json.dumps(snapshot())})
        entry = {
            "state": "open", "base": {"ref": "main"},
            "head": {"ref": "automation/retally-scout-40223450239-1",
                     "repo": {"full_name": REPO}},
            "title": "Automated scout evidence refresh (GitHub run 40223450239)",
            "body": f"evidence\n<!-- scout-semantic-sha256:{sha} -->",
            "number": 799,
        }
        self.assertEqual(matching_open_proposal(sha, [entry]), 799)
        spoof = json.loads(json.dumps(entry))
        spoof["head"]["repo"]["full_name"] = "other/project"
        self.assertIsNone(matching_open_proposal(sha, [spoof]))
        spoof["head"]["repo"]["full_name"] = REPO
        spoof["base"]["ref"] = "production"
        self.assertIsNone(matching_open_proposal(sha, [spoof]))

    def test_unknown_field_is_material_and_unknown_path_is_blocked(self):
        d = snapshot()
        baseline = semantic_fingerprint({PATH: json.dumps(d)})
        d["future_evidence_assertion"] = "NOT_VERIFIED"
        self.assertNotEqual(baseline, semantic_fingerprint({PATH: json.dumps(d)}))
        with self.assertRaises(ValueError):
            semantic_fingerprint({"freight/research_lab/secret.json": "{}"})


if __name__ == "__main__":
    unittest.main()
