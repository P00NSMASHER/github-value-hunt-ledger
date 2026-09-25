import json
import tempfile
import unittest
from pathlib import Path
from tools.public_repo_scout import GH, candidate, known, queued_pairs, risk_flags, root_score, recency, triage

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

if __name__=="__main__":
    unittest.main()
