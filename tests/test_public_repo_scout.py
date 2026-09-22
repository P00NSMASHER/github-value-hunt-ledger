import unittest
from tools.public_repo_scout import known, risk_flags, root_score, recency, triage

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

if __name__=="__main__":
    unittest.main()
