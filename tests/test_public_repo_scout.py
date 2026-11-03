import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.public_repo_scout import GH, candidate, integrate, known, persist_queue, queued_pairs, risk_flags, root_score, recency, triage

class ScoutTests(unittest.TestCase):
    def test_exact_revision_dedupe(self):
        c="example/project abcdef123456"
        self.assertTrue(known(c,"example/project","abcdef123456"))
        self.assertFalse(known(c,"example/project","deadbeef"))

    def test_risk_descriptor_gate(self):
        self.assertIn("credential stealer",risk_flags({"name":"x","description":"credential stealer proof of concept","topics":[]}))
        self.assertEqual([],risk_flags({"name":"x","description":"backup restore verifier","topics":["sre"]}))

    def test_root_signals(self):
        s,h=root_score(["src","tests","Dockerfile","pyproject.toml",".github"])
        self.assertGreaterEqual(s,10)
        self.assertIn("tests",h)

    def test_recency(self):
        self.assertGreaterEqual(recency("2026-09-01T00:00:00Z"),12)

    def test_triage_bounded(self):
        r={"stargazers_count":5000,"forks_count":800,"size":12000,"pushed_at":"2026-09-20T00:00:00Z","license":{"spdx_id":"MIT"},"description":"Production deterministic reconciliation engine","topics":["finance","ledger"],"archived":False}
        s,c,h=triage(r,["src","tests","Dockerfile","migrations",".github"])
        self.assertGreater(s,50)
        self.assertLessEqual(s,100)
        self.assertIn("root_code_signals",c)

    def test_known_revision_skips_root_fetch(self):
        class FakeGH:
            def __init__(self):
                self.root_calls=0
            def revision(self,full,branch):
                return "abcdef123456"
            def root(self,full,branch):
                self.root_calls+=1
                return ["src","tests"]
        gh=FakeGH()
        repo={"full_name":"example/project","default_branch":"main","name":"project","description":"useful engine","topics":[]}
        self.assertIsNone(candidate(gh,repo,"q","example/project abcdef123456","owner/repo"))
        self.assertEqual(0,gh.root_calls)

    def test_persisted_queue_pairs_are_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"HUNTER-01.json").write_text(json.dumps({"candidates":[{"repository":"Example/Project","exact_revision":"ABC123"}]}))
            self.assertIn(("example/project","abc123"),queued_pairs(root))

    def test_revision_and_root_cache(self):
        gh=GH("test-token")
        calls=[]
        def fake_get(path,q=None):
            calls.append((path,q))
            if "/commits/" in path:
                return {"sha":"abc123"}
            return [{"name":"src"},{"name":"tests"}]
        gh.get=fake_get
        self.assertEqual("abc123",gh.revision("example/project","main"))
        self.assertEqual("abc123",gh.revision("example/project","main"))
        self.assertEqual(["src","tests"],gh.root("example/project","main"))
        self.assertEqual(["src","tests"],gh.root("example/project","main"))
        self.assertEqual(2,len(calls))
        self.assertEqual(1,gh.stats["revision_cache_hits"])
        self.assertEqual(1,gh.stats["root_cache_hits"])

    def test_queue_run_metadata_does_not_generate_another_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"HUNTER-01.json"
            snapshot={"worker_id":"HUNTER-01", "schema_version":2,
                      "candidate_count":1, "candidates":[{"repository":"example/one",
                      "exact_revision":"a"*40}], "search_diagnostics":[{"returned":1}],
                      "generated_at":"2026-10-25T00:00:00+00:00",
                      "api_metrics":{"api_requests":8}}
            self.assertTrue(persist_queue(path,snapshot))
            original=path.read_bytes()
            telemetry_only={**snapshot, "generated_at":"2026-10-26T00:00:00+00:00",
                            "api_metrics":{"api_requests":99}}
            self.assertFalse(persist_queue(path,telemetry_only))
            self.assertEqual(path.read_bytes(),original)
            meaningful={**telemetry_only,
                        "candidates":[*snapshot["candidates"],
                                      {"repository":"example/two","exact_revision":"b"*40}],
                        "candidate_count":2}
            self.assertTrue(persist_queue(path,meaningful))
            self.assertNotEqual(path.read_bytes(),original)
            # Per-run provider diagnostics belong in job logs, not source
            # identity. A provider error blocks the writer before this call.
            self.assertFalse(persist_queue(path,{**meaningful,
                "search_diagnostics":[{"error":"GITHUB_RATE_LIMIT"}]}))

    def test_higher_ranked_unreviewed_candidate_cannot_silently_disappear(self):
        # Regression: 55-point MIT lead was silently displaced by 31-point
        # UNKNOWN lead in a generated ten-slot HUNTER-07 snapshot.
        top = {"repository": "example/strong-mit", "exact_revision": "a" * 40,
               "triage_score": 55, "status": "PRE_VERIFICATION_CANDIDATE",
               "published_license_spdx": "MIT"}
        low = {"repository": "example/weak", "exact_revision": "b" * 40,
               "triage_score": 29, "status": "PRE_VERIFICATION_CANDIDATE"}
        newcomer = {"repository": "example/new", "exact_revision": "c" * 40,
                    "triage_score": 31, "status": "PRE_VERIFICATION_CANDIDATE",
                    "published_license_spdx": "UNKNOWN"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "HUNTER-07.json"
            before = {"worker_id": "HUNTER-07", "candidate_count": 2,
                      "candidates": [top, low]}
            self.assertTrue(persist_queue(path, before))
            old_bytes = path.read_bytes()
            unsafe = {**before, "candidates": [newcomer, low]}
            with self.assertRaisesRegex(ValueError, "source-quality HOLD"):
                persist_queue(path, unsafe)
            self.assertEqual(path.read_bytes(), old_bytes)

            # Revised source head for the SAME repository is not a loss.
            refreshed = {**before, "candidates": [
                {**top, "exact_revision": "d" * 40}, low]}
            self.assertTrue(persist_queue(path, refreshed))

    def test_empty_queue_is_a_real_withdrawal_not_a_bad_replacement(self):
        top = {"repository": "example/strong", "exact_revision": "a" * 40,
               "triage_score": 55, "status": "PRE_VERIFICATION_CANDIDATE"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "HUNTER-07.json"
            prior = {"worker_id": "HUNTER-07", "candidate_count": 1,
                     "candidates": [top]}
            self.assertTrue(persist_queue(path, prior))
            self.assertTrue(persist_queue(
                path, {**prior, "candidate_count": 0, "candidates": []}))
            self.assertEqual(json.loads(path.read_text())["candidates"], [])

    def test_lower_ranked_candidate_can_rotate_out(self):
        top = {"repository": "example/top", "exact_revision": "a" * 40,
               "triage_score": 55, "status": "PRE_VERIFICATION_CANDIDATE"}
        low = {"repository": "example/low", "exact_revision": "b" * 40,
               "triage_score": 20, "status": "PRE_VERIFICATION_CANDIDATE"}
        fresh = {"repository": "example/fresh", "exact_revision": "c" * 40,
                 "triage_score": 35, "status": "PRE_VERIFICATION_CANDIDATE"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "HUNTER-07.json"
            before = {"worker_id": "HUNTER-07", "candidate_count": 2,
                      "candidates": [top, low]}
            self.assertTrue(persist_queue(path, before))
            self.assertTrue(persist_queue(
                path, {**before, "candidates": [top, fresh]}))
            data = json.loads(path.read_text())
            self.assertEqual([c["repository"] for c in data["candidates"]],
                             ["example/top", "example/fresh"])

    def test_digest_is_byte_stable_without_new_source_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            queue=root/"HUNTER-01.json"
            output=root/"SCOUT_DIGEST.md"
            candidate={"repository":"example/one", "exact_revision":"a"*40,
                       "triage_score":42, "stars":1, "url":"https://github.com/example/one",
                       "published_license_spdx":"MIT", "description":"Fixture"}
            queue.write_text(json.dumps({"worker_id":"HUNTER-01",
                "candidates":[candidate], "generated_at":"2026-10-25T00:00:00Z"}))
            with patch("tools.public_repo_scout.now",side_effect=AssertionError(
                    "Digest must not depend on current wall clock")):
                self.assertEqual(integrate(root,output),1)
                before=output.read_bytes()
                self.assertEqual(integrate(root,output),1)
                self.assertEqual(output.read_bytes(),before)
            queue.write_text(json.dumps({"worker_id":"HUNTER-01",
                "candidates":[{**candidate,"triage_score":43}],
                "generated_at":"2026-10-26T00:00:00Z"}))
            self.assertEqual(integrate(root,output),1)
            self.assertNotEqual(output.read_bytes(),before)


if __name__=="__main__":
    unittest.main()
