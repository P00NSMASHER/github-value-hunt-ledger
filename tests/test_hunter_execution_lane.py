"""Regression and adversarial coverage for the separate read-only Hunter execution lane."""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.hunter_source_inspection import (
    SCOPE, SourceError, candidates, choose, execute, inspected_blob, roster)
from tools.hunter_completion_evidence import (
    AcceptanceError, validate_shape, verify_live)

SHA = "a" * 40
TARGET_SHA = "b" * 40
SOURCE_SHA = "c" * 40

def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

class FakeAPI:
    def __init__(self):
        self.requests = []
        self.src = b"def verified_function():\n    # The source must have enough bytes to qualify for inspection.\n    return 1\n"
        self.test = b"def test_verified_function():\n    # This deterministic test has an observable assertion.\n    assert True\n"
        self.license = b"MIT License\nCopyright 2026 Test Team\n"
        self.blobs = {
            blob(self.src): self.src, blob(self.test): self.test,
            blob(self.license): self.license,
        }

    def get(self, path):
        self.requests.append(path)
        if path.startswith("/repos/external/tool/git/trees/"):
            return {"truncated": False, "tree": [
                {"type": "blob", "path": "src/main.py", "size": len(self.src), "sha": blob(self.src)},
                {"type": "blob", "path": "tests/test_main.py", "size": len(self.test), "sha": blob(self.test)},
                {"type": "blob", "path": "LICENSE", "size": len(self.license), "sha": blob(self.license)}]}
        if "/git/blobs/" in path:
            key = path.split("/")[-1]
            if key not in self.blobs:
                raise ValueError("unknown blob")
            return {"sha": key, "encoding": "base64",
                    "content": base64.b64encode(self.blobs[key]).decode()}
        raise ValueError("unexpected request: " + path)

def manifest():
    return {"scope_version": SCOPE, "workers": [
        {"id": f"HUNTER-{i:02d}", "project": "trading" if i == 1 else "misc",
         "target_repository": "P00NSMASHER/github-value-hunt-ledger",
         "mission": "safe source inspection", "evidence_gate": "no unverified outcomes"}
        for i in range(1, 15)
    ]}

def queue(worker, with_candidate=True):
    cs = [{"repository": "external/tool", "exact_revision": SHA,
           "published_license_spdx": "MIT", "triage_score": 70,
           "status": "PRE_VERIFICATION_CANDIDATE"}] if with_candidate else []
    return {**worker, "worker_id": worker["id"], "scope_version": SCOPE,
            "generated_at": "2026-11-05T00:00:00Z",
            "candidates": cs, "candidate_count": len(cs), "search_diagnostics": []}

def completed():
    return {"schema_version": 1, "status": "COMPLETE", "worker_id": "HUNTER-05",
            "source_repository": "external/tool", "source_exact_revision": SOURCE_SHA,
            "target_repository": "P00NSMASHER/github-value-hunt-ledger",
            "target_commit_sha": TARGET_SHA, "merged_pr_number": 5,
            "test_run_id": 101, "verifier_run_id": 102,
            "required_test_steps": ["Unit acceptance tests"],
            "external_outcome": "UNKNOWN"}

class AcceptanceAPI:
    def get(self, path):
        if path == f"/repos/external/tool/git/commits/{SOURCE_SHA}":
            return {"sha": SOURCE_SHA}
        if path == "/repos/P00NSMASHER/github-value-hunt-ledger/pulls/5":
            return {"merged": True, "state": "closed", "merge_commit_sha": TARGET_SHA}
        if path.endswith("/actions/runs/101"):
            return {"head_sha": TARGET_SHA, "conclusion": "success",
                    "status": "completed", "workflow_id": 1001,
                    "repository": {"full_name": "P00NSMASHER/github-value-hunt-ledger"}}
        if path.endswith("/actions/runs/102"):
            return {"head_sha": TARGET_SHA, "conclusion": "success",
                    "status": "completed", "workflow_id": 1002,
                    "repository": {"full_name": "P00NSMASHER/github-value-hunt-ledger"}}
        if path.endswith("/actions/runs/101/jobs?per_page=100"):
            return {"jobs": [{"conclusion": "success", "steps":
                              [{"name": "Unit acceptance tests", "conclusion": "success"}]}]}
        if path.endswith("/actions/runs/102/jobs?per_page=100"):
            return {"jobs": [{"conclusion": "success", "steps":
                              [{"name": "Independent validation", "conclusion": "success"}]}]}
        raise ValueError("unexpected request " + path)

class ReadOnlyWorkerTests(unittest.TestCase):
    def test_immutable_roster_and_queue_binding(self):
        m = manifest()
        self.assertEqual(14, len(roster(m)))
        m["workers"][1]["id"] = "HUNTER-01"
        with self.assertRaises(SourceError):
            roster(m)

    def test_bounded_actual_blob_reads_cannot_be_called_complete(self):
        m = manifest()
        with tempfile.TemporaryDirectory() as temp:
            for w in m["workers"]:
                Path(temp, w["id"] + ".json").write_text(json.dumps(queue(w, w["id"] == "HUNTER-01")))
            api = FakeAPI()
            r = execute(m, Path(temp), "AUTO", 0, api)
        self.assertEqual("HUNTER-01", r["worker_id"])
        self.assertTrue(r["source_inspected"])
        self.assertEqual("NOT_ACCEPTED", r["completion_status"])
        self.assertFalse(r["claim_issued"])
        self.assertFalse(r["external_writes"])
        self.assertEqual("UNKNOWN", r["measured_outcome"])
        files = r["attempts"][0]["inspected_files"]
        self.assertEqual(3, len(files))  # source, test, and exact pinned license
        self.assertTrue(all(x["verified_git_blob"] for x in files))
        self.assertEqual(len(files), len([x for x in api.requests if "/git/blobs/" in x]))
        self.assertTrue(all(x.startswith("/repos/") for x in api.requests))

    def test_unknown_rights_cannot_enter_execution_candidates(self):
        q = queue(manifest()["workers"][0])
        q["candidates"][0]["published_license_spdx"] = "NOASSERTION"
        self.assertEqual([], candidates(q))

    def test_forged_source_sha_rejected(self):
        fake = FakeAPI()
        with self.assertRaises(SourceError):
            inspected_blob(fake, "external/tool", ("src/main.py", SHA))

    def test_schedule_count_unmodified_and_no_new_schedule(self):
        old = Path(".github/workflows/public-repo-hunter.yml").read_text()
        new = Path(".github/workflows/hunter-source-inspection.yml").read_text()
        self.assertEqual(old.count("- cron:"), 15)
        self.assertNotIn("- cron:", new)
        self.assertIn("workflow_run:", new)
        self.assertIn("contents: read", new)
        self.assertNotIn("contents: write", new)

class CompletionEvidenceTests(unittest.TestCase):
    def test_live_exact_head_and_distinct_verifier_admitted(self):
        output = verify_live(completed(), AcceptanceAPI())
        self.assertEqual("VERIFIED_CODE_INTEGRATION", output["status"])
        self.assertEqual("UNKNOWN", output["real_world_outcomes"])
        self.assertEqual(2, len(output["live_evidence"]))

    def test_missing_real_tests_not_complete(self):
        entry = completed()
        entry["required_test_steps"] = []
        with self.assertRaises(AcceptanceError):
            validate_shape(entry)

    def test_source_inspection_not_complete(self):
        entry = completed()
        entry["status"] = "SOURCE_INSPECTED"
        with self.assertRaises(AcceptanceError):
            validate_shape(entry)

    def test_no_synthetic_dollars_or_novelty(self):
        for key, val in (("revenue_usd", 1.0), ("trading_profit_usd", 100),
                         ("engineering_hours_saved", 8), ("scientific_novelty", True)):
            entry = completed()
            entry[key] = val
            with self.assertRaises(AcceptanceError):
                validate_shape(entry)

    def test_separate_run_cannot_share_identity(self):
        entry = completed()
        entry["verifier_run_id"] = entry["test_run_id"]
        with self.assertRaises(AcceptanceError):
            validate_shape(entry)

    def test_exact_merge_commit_required(self):
        class BadPR(AcceptanceAPI):
            def get(self, path):
                result = super().get(path)
                if "/pulls/" in path:
                    result["merge_commit_sha"] = "f" * 40
                return result
        with self.assertRaises(AcceptanceError):
            verify_live(completed(), BadPR())

    def test_real_test_step_must_pass(self):
        class NoTest(AcceptanceAPI):
            def get(self, path):
                result = super().get(path)
                if "/runs/101/jobs" in path:
                    result["jobs"][0]["steps"][0]["conclusion"] = "failure"
                return result
        with self.assertRaises(AcceptanceError):
            verify_live(completed(), NoTest())

if __name__ == "__main__":
    unittest.main()
