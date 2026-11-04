import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.public_repo_scout import GH, candidate, integrate, known, persist_queue, queued_pairs, retain_unreviewed_candidates, risk_flags, root_score, recency, triage, validate_manifest

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


    def test_active_manifest_is_complete_and_excludes_retired_research(self):
        manifest = json.loads((Path(__file__).resolve().parents[1] /
                               "automation/hunter_schedule.json").read_text())
        self.assertEqual(validate_manifest(manifest), "active-projects-2026-11-v2")
        self.assertEqual(len(manifest["workers"]), 14)
        self.assertEqual(len(set(manifest["active_repositories"])), 5)
        self.assertEqual([w["project"] for w in manifest["workers"][:5]],
                         ["trading", "revenue-hunt", "retally-social-media",
                          "novel-discovery", "engineering-acceleration"])
        self.assertNotIn("P00NSMASHER/project-genesis",
                         manifest["active_repositories"])
        self.assertFalse(any(w["project"] == "genesis"
                             for w in manifest["workers"]))
        self.assertTrue(all(
            worker["target_repository"] in manifest["active_repositories"]
            for worker in manifest["workers"]))
        bad = json.loads(json.dumps(manifest))
        bad["workers"][0]["queries"][0] = "Roblox retired research"
        with self.assertRaisesRegex(ValueError, "Retired-project"):
            validate_manifest(bad)
        bad = json.loads(json.dumps(manifest))
        bad["workers"][0]["project"] = "genesis"
        with self.assertRaisesRegex(ValueError, "Removed Genesis"):
            validate_manifest(bad)
        bad = json.loads(json.dumps(manifest))
        bad["workers"][2].pop("evidence_gate")
        with self.assertRaisesRegex(ValueError, "Research evidence gate"):
            validate_manifest(bad)
        bad = json.loads(json.dumps(manifest))
        bad["workers"][0]["project"] = "engineering-acceleration"
        with self.assertRaisesRegex(ValueError, "assignment drift"):
            validate_manifest(bad)

    def test_integrator_ignores_historical_queues_but_keeps_current_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prior = {"worker_id": "HUNTER-01",
                     "scope_version": "active-projects-2026-11-v1",
                     "project": "genesis",
                     "candidates": [{"repository": "example/legacy",
                                     "exact_revision": "a" * 40,
                                     "triage_score": 99,
                                     "url": "https://github.com/example/legacy"}]}
            current = {"worker_id": "HUNTER-02",
                       "scope_version": "active-projects-2026-11-v2",
                       "project": "trading",
                       "candidates": [{"repository": "example/active",
                                       "exact_revision": "b" * 40,
                                       "triage_score": 42,
                                       "url": "https://github.com/example/active"}]}
            (root / "HUNTER-01.json").write_text(json.dumps(prior))
            (root / "HUNTER-02.json").write_text(json.dumps(current))
            output = root / "digest.md"
            self.assertEqual(integrate(root, output,
                                       scope_version="active-projects-2026-11-v2"), 1)
            digest = output.read_text()
            self.assertIn("example/active", digest)
            self.assertIn("| trading |", digest)
            self.assertNotIn("example/legacy", digest)
            self.assertIn("Queue snapshots read: 1", digest)
            self.assertEqual(integrate(root, output,
                                       scope_version="active-projects-2026-11-v2"), 1)

    def test_legacy_snapshots_do_not_consume_current_discovery_pairs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "HUNTER-01.json").write_text(json.dumps({
                "scope_version": "active-projects-2026-11-v1",
                "candidates": [{"repository": "example/historical",
                                "exact_revision": "a" * 40}]}))
            (root / "HUNTER-02.json").write_text(json.dumps({
                "scope_version": "active-projects-2026-11-v2",
                "candidates": [{"repository": "example/current",
                                "exact_revision": "b" * 40}]}))
            pairs = queued_pairs(root, scope_version="active-projects-2026-11-v2")
            self.assertNotIn(("example/historical", "a" * 40), pairs)
            self.assertIn(("example/current", "b" * 40), pairs)

    def test_scope_migration_does_not_trigger_same_scope_rank_loss_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "HUNTER-01.json"
            previous = {"worker_id": "HUNTER-01",
                        "scope_version": "active-projects-2026-11-v1",
                        "candidates": [
                {"repository": "example/old", "exact_revision": "a" * 40,
                 "triage_score": 99, "status": "PRE_VERIFICATION_CANDIDATE"}]}
            current = {"worker_id": "HUNTER-01",
                       "scope_version": "active-projects-2026-11-v2",
                       "candidates": [{"repository": "example/new",
                                       "exact_revision": "b" * 40,
                                       "triage_score": 25,
                                       "status": "PRE_VERIFICATION_CANDIDATE"}]}
            self.assertTrue(persist_queue(path, previous))
            self.assertTrue(persist_queue(path, current))
            self.assertEqual(json.loads(path.read_text())["scope_version"],
                             "active-projects-2026-11-v2")
            replacement = {**current, "candidates": [
                {"repository": "example/worse", "exact_revision": "c" * 40,
                 "triage_score": 10, "status": "PRE_VERIFICATION_CANDIDATE"}]}
            with self.assertRaisesRegex(ValueError, "source-quality HOLD"):
                persist_queue(path, replacement)
            self.assertEqual(json.loads(path.read_text())["candidates"],
                             current["candidates"])

    def test_updated_research_objectives_have_verifiable_acceptance_gates(self):
        manifest = json.loads((Path(__file__).resolve().parents[1] /
                               "automation/hunter_schedule.json").read_text())
        goals = manifest["workers"][:5]
        self.assertTrue(all(len(w["queries"]) == 4 for w in goals))
        self.assertTrue(all(w["evidence_gate"] for w in goals))
        self.assertIn("out-of-sample", goals[0]["evidence_gate"])
        self.assertIn("actual collected payment", goals[1]["evidence_gate"])
        self.assertIn("publishing requires separate authorization",
                      goals[2]["evidence_gate"])
        self.assertIn("UNKNOWN", goals[3]["evidence_gate"])
        self.assertIn("baseline-versus-after", goals[4]["evidence_gate"])

    def test_retired_repository_is_never_accepted_as_new_source(self):
        class NoNetwork:
            def revision(self, *_args):
                raise AssertionError("retired project must not be fetched")
        self.assertIsNone(candidate(
            NoNetwork(), {"full_name": "P00NSMASHER/StarBlox"}, "query",
            "", "P00NSMASHER/github-value-hunt-ledger"))


    def test_same_scope_genesis_queue_cannot_enter_production_digest(self):
        manifest = json.loads((Path(__file__).resolve().parents[1] /
                               "automation/hunter_schedule.json").read_text())
        worker = manifest["workers"][2]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bogus = {"worker_id": worker["id"],
                     "scope_version": manifest["scope_version"],
                     "project": "genesis",
                     "target_repository": "P00NSMASHER/project-genesis",
                     "mission": "Genesis",
                     "evidence_gate": worker["evidence_gate"],
                     "candidates": [{"repository": "example/poison",
                                     "exact_revision": "a" * 40,
                                     "triage_score": 100}]}
            (root / "HUNTER-03.json").write_text(json.dumps(bogus))
            output = root / "digest.md"
            with self.assertRaisesRegex(ValueError, "Invalid current-scope scout assignment"):
                integrate(root, output, scope_version=manifest["scope_version"],
                          worker_index={w["id"]: w for w in manifest["workers"]})
            self.assertFalse(output.exists())

    def test_genesis_topic_drift_fails_first_five_manifest_validation(self):
        manifest = json.loads((Path(__file__).resolve().parents[1] /
                               "automation/hunter_schedule.json").read_text())
        manifest["workers"][3]["queries"][0] = "Genesis simulator"
        with self.assertRaisesRegex(ValueError, "Removed Genesis research topic"):
            validate_manifest(manifest)


    def test_query_refresh_retains_higher_ranked_unreviewed_evidence(self):
        keys = {"scope_version": "active-projects-2026-11-v2",
                "worker_id": "HUNTER-01", "project": "trading",
                "target_repository": "P00NSMASHER/github-value-hunt-ledger",
                "mission": "Trading research", "evidence_gate": "verify"}
        prior = {**keys, "candidate_count": 2,
                 "candidates": [
                     {"repository": "example/strong", "exact_revision": "a"*40,
                      "triage_score": 46, "stars": 1,
                      "status": "PRE_VERIFICATION_CANDIDATE"},
                     {"repository": "example/weak", "exact_revision": "b"*40,
                      "triage_score": 10, "stars": 1,
                      "status": "PRE_VERIFICATION_CANDIDATE"}]}
        fresh = {**keys, "search_queries": ["tradier"],
                 "risk_review_count": 0, "risk_review": [], "candidate_count": 1,
                 "candidates": [{"repository": "example/new", "exact_revision": "c"*40,
                                 "triage_score": 35, "stars": 1,
                                 "status": "PRE_VERIFICATION_CANDIDATE"}]}
        combined = retain_unreviewed_candidates(prior, fresh, limit=2)
        self.assertEqual([c["repository"] for c in combined["candidates"]],
                         ["example/strong", "example/new"])
        self.assertTrue(combined["candidates"][0]["retained_unreviewed"])
        self.assertNotIn("retained_unreviewed", combined["candidates"][1])
        self.assertEqual(combined["candidate_count"], 2)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "HUNTER-01.json"
            self.assertTrue(persist_queue(p, prior))
            self.assertTrue(persist_queue(p, combined))
            self.assertEqual(json.loads(p.read_text())["candidates"], combined["candidates"])

    def test_continuity_does_not_revive_legacy_genesis_or_risky_leads(self):
        keys = {"scope_version": "active-projects-2026-11-v2",
                "worker_id": "HUNTER-01", "project": "trading",
                "target_repository": "P00NSMASHER/github-value-hunt-ledger",
                "mission": "Trading", "evidence_gate": "proof"}
        old = {**keys, "candidates": [
            {"repository": "example/unsafe", "exact_revision": "a"*40,
             "triage_score": 42, "status": "PRE_VERIFICATION_CANDIDATE"}]}
        fresh = {**keys, "candidates": [], "risk_review": [],
                 "risk_review_count": 0}
        legacy = {**old, "scope_version": "active-projects-2026-11-v1",
                  "project": "genesis"}
        self.assertEqual(retain_unreviewed_candidates(legacy, dict(fresh), 16)["candidates"], [])
        flagged = {**fresh, "risk_review": [{"repository": "example/unsafe"}],
                   "risk_review_count": 1}
        with self.assertRaisesRegex(ValueError, "risk-review HOLD"):
            retain_unreviewed_candidates(old, flagged, 16)
        retained = retain_unreviewed_candidates(old, dict(fresh), 16)
        self.assertEqual(retained["candidate_count"], 1)
        self.assertTrue(retained["candidates"][0]["retained_unreviewed"])

if __name__=="__main__":
    unittest.main()
