"""Hunter outcome-truth and activation regression tests (no network)."""
import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from tools.hunter_effectiveness import collect, describe_worker, render
from tools.retally_writer_proposal_policy import allowed_path
from tools.retally_scout_pr_dedupe import evidence_value, semantic_fingerprint


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "automation" / "hunter_schedule.json"
WORKFLOW = ROOT / ".github" / "workflows" / "public-repo-hunter.yml"
EXPECTED_CRONS = (
    "7 2,14 * * *", "15 2,14 * * *", "23 2,14 * * *",
    "31 2,14 * * *", "39 2,14 * * *", "47 2,14 * * *",
    "55 2,14 * * *", "3 3,15 * * *", "11 3,15 * * *",
    "19 3,15 * * *", "27 3,15 * * *", "35 3,15 * * *",
    "43 3,15 * * *", "51 3,15 * * *", "7 4,16 * * *",
)


class HunterOutcomeTruthTests(unittest.TestCase):
    def manifest(self):
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_empty_new_scope_is_unknown_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = collect(self.manifest(), Path(tmp))
        self.assertEqual(len(report["workers"]), 14)
        self.assertEqual(report["current_scope_queue_count"], 0)
        self.assertEqual(report["unreviewed_candidate_count"], 0)
        self.assertTrue(all(r["verified_integration"] == "UNKNOWN"
                            and r["measured_result"] == "UNKNOWN"
                            and r["status"] == "NOT_OBSERVED_IN_SCOPE"
                            for r in report["workers"]))
        rendered = render(report)
        self.assertIn("not proof of scheduled execution", rendered)
        self.assertIn("**UNKNOWN**", rendered)

    def test_prior_starblox_and_genesis_queues_are_not_current(self):
        manifest = self.manifest()
        with tempfile.TemporaryDirectory() as tmp:
            q = Path(tmp)
            legacy = {"scope_version": "active-projects-2026-11-v1",
                      "worker_id": "HUNTER-01", "project": "genesis",
                      "candidate_count": 1, "generated_at": "2026-11-03T00:00:00+00:00",
                      "search_diagnostics": [], "candidates": [
                          {"repository": "example/stale", "exact_revision": "a" * 40,
                           "status": "PRE_VERIFICATION_CANDIDATE"}]}
            (q / "HUNTER-01.json").write_text(json.dumps(legacy))
            report = collect(manifest, q)
        self.assertEqual(report["current_scope_queue_count"], 0)
        self.assertEqual(report["workers"][0]["status"], "NOT_OBSERVED_IN_SCOPE")

    def test_valid_current_candidate_remains_unverified(self):
        manifest = self.manifest()
        worker = manifest["workers"][0]
        with tempfile.TemporaryDirectory() as tmp:
            q = Path(tmp)
            current = {"scope_version": manifest["scope_version"],
                       "worker_id": worker["id"], "project": worker["project"],
                       "target_repository": worker["target_repository"],
                       "mission": worker["mission"],
                       "evidence_gate": worker.get("evidence_gate"),
                       "candidate_count": 1,
                       "generated_at": "2026-11-04T01:00:00+00:00",
                       "search_diagnostics": [{"query": "test", "returned": 1}],
                       "candidates": [{"repository": "example/source",
                                       "exact_revision": "b" * 40,
                                       "status": "PRE_VERIFICATION_CANDIDATE"}]}
            (q / "HUNTER-01.json").write_text(json.dumps(current))
            report = collect(manifest, q)
        self.assertEqual(report["current_scope_queue_count"], 1)
        self.assertEqual(report["unreviewed_candidate_count"], 1)
        self.assertEqual(report["workers"][0]["status"], "UNREVIEWED_CANDIDATES")
        self.assertEqual(report["workers"][0]["verified_integration"], "UNKNOWN")
        self.assertEqual(report["workers"][0]["measured_result"], "UNKNOWN")
        self.assertIn("example", json.dumps(current))

    def test_bad_queue_never_counts_as_usable_discovery(self):
        manifest = self.manifest()
        worker = manifest["workers"][0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / "HUNTER-01.json"
            base = {"scope_version": manifest["scope_version"],
                    "worker_id": worker["id"], "project": worker["project"],
                    "target_repository": worker["target_repository"],
                    "mission": worker["mission"],
                    "evidence_gate": worker.get("evidence_gate"),
                    "candidate_count": 1,
                    "generated_at": "2026-11-04T01:00:00+00:00",
                    "search_diagnostics": [],
                    "candidates": []}
            p.write_text(json.dumps(base))
            self.assertEqual(describe_worker(worker, root, manifest["scope_version"])["status"],
                             "INVALID_QUEUE")
            p.write_text(json.dumps({**base, "candidate_count": 0,
                                     "search_diagnostics": [{"error": "rate limit"}]}))
            self.assertEqual(describe_worker(worker, root, manifest["scope_version"])["status"],
                             "SOURCE_ERROR")
            p.write_text("{bad json")
            self.assertEqual(describe_worker(worker, root, manifest["scope_version"])["status"],
                             "INVALID_QUEUE")
            p.write_text(json.dumps({**base, "candidate_count": 0,
                                     "search_diagnostics": [{"query": "a", "returned": 0}],
                                     "candidates": []}))
            self.assertEqual(describe_worker(worker, root, manifest["scope_version"])["status"],
                             "NO_SEARCH_MATCHES")
            p.write_text(json.dumps({**base, "candidate_count": 0,
                                     "search_diagnostics": [{"query": "a", "returned": 1}],
                                     "target_repository": "P00NSMASHER/project-genesis",
                                     "candidates": []}))
            self.assertEqual(describe_worker(worker, root, manifest["scope_version"])["status"],
                             "INVALID_QUEUE")

    def test_report_is_deterministic_without_clocks_or_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = collect(self.manifest(), Path(tmp))
            before = render(report)
            after = render(collect(self.manifest(), Path(tmp)))
        self.assertEqual(before, after)
        self.assertNotIn("INTEGRATED_OK", before)
        self.assertNotIn("VERIFIED_PROFIT", before)

    def test_only_the_new_evidence_report_is_added_to_proposal_allowlist(self):
        path = "automation/HUNTER_EFFECTIVENESS.md"
        self.assertTrue(allowed_path("scout", path, ti_paths=frozenset()))
        self.assertFalse(allowed_path("scout", "automation/secret.md",
                                      ti_paths=frozenset()))
        report = "# Hunter effectiveness\n\nVerified integration: UNKNOWN\n"
        self.assertEqual(evidence_value(path, report), report)
        self.assertNotEqual(semantic_fingerprint({path: report}),
                            semantic_fingerprint({path: report + "review needed\\n"}))
        with self.assertRaises(ValueError):
            evidence_value("automation/arbitrary.md", "fake")

    def test_existing_schedule_is_preserved_and_smoke_is_one_worker(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        got = tuple(re.findall(r'^\s*-\s*cron:\s*"([^"]+)"', source, re.M))
        self.assertEqual(got, EXPECTED_CRONS)
        for i, cron in enumerate(EXPECTED_CRONS[:5], 1):
            self.assertIn(f'"{cron}") worker="HUNTER-{i:02d}";;', source)
        self.assertIn('if [ "$EVENT_NAME" = "schedule" ]; then worker=""; fi', source)
        self.assertIn("Unrecognized scheduled hunter route", source)
        for w in self.manifest()["workers"][:5]:
            self.assertTrue(all(1 <= len(q.split()) <= 4 for q in w["queries"]), w["id"])
        self.assertIn("branches: [main]", source)
        self.assertIn('if [ "$EVENT_NAME" = "push" ]; then worker="HUNTER-01"; fi', source)
        self.assertIn('EVENT_NAME: ${{ github.event_name }}', source)
        self.assertIn("python -m tools.hunter_effectiveness", source)
        self.assertIn("automation/HUNTER_EFFECTIVENESS.md", source)
        self.assertNotIn("cancel-in-progress: true", source)


    def test_scoped_evidence_is_uploaded_before_branch_persistence(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        upload = "Preserve worker evidence independently of PR publication"
        self.assertIn(upload, source)
        self.assertLess(source.index(upload), source.index("Commit queue refresh"))
        self.assertIn("hunter-evidence-${{ steps.route.outputs.worker }}-", source)
        self.assertIn("intelligence/scout_queue/${{ steps.route.outputs.worker }}.json", source)
        self.assertIn("automation/HUNTER_EFFECTIVENESS.md", source)
        self.assertIn("if-no-files-found: error", source)
        self.assertIn("steps.route.outputs.worker != 'INTEGRATOR'", source)
        self.assertIn("steps.route.outputs.worker != 'ALL'", source)



if __name__ == "__main__":
    unittest.main()
