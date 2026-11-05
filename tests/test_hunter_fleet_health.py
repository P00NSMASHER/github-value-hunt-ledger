import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest

from tools.hunter_fleet_health import WORKERS, evaluate, governed_runtime_truth, render


class HunterFleetHealthTests(unittest.TestCase):
    def fixture(self):
        now = dt.datetime(2026, 11, 4, 22, tzinfo=dt.timezone.utc)
        runs = [{"event": "schedule", "conclusion": "success",
                 "created_at": "2026-11-04T21:00:00Z"} for _ in range(15)]
        runs.append({"event": "repository_dispatch", "conclusion": "success",
                     "created_at": "2026-11-04T21:30:00Z"})
        queues = {w: {"scope_version": "active-projects-2026-11-v2"} for w in WORKERS}
        return now, runs, queues

    def test_all_gates_and_failure_injection(self):
        now, runs, queues = self.fixture()
        runs.append({"event": "schedule", "conclusion": "failure",
                     "created_at": "2026-11-04T05:00:00Z"})
        report = evaluate(runs, queues,
                          "Queue snapshots read: 14\nUnique exact-revision candidates: 81",
                          now, [], False)
        self.assertTrue(report["healthy"])
        injected = evaluate(runs, queues,
                            "Queue snapshots read: 14\nUnique exact-revision candidates: 81",
                            now, [], True)
        self.assertFalse(injected["healthy"])
        self.assertFalse(injected["checks"]["injected_failure_detected"])

    def test_failed_recovery_and_stale_queue_fail_closed(self):
        now, runs, queues = self.fixture()
        runs[-1]["conclusion"] = "failure"
        queues.pop("HUNTER-14")
        report = evaluate(runs, queues, "Queue snapshots read: 13", now, [], False)
        self.assertFalse(report["checks"]["recovery_demonstrated"])
        self.assertFalse(report["checks"]["queues_current"])
        self.assertFalse(report["checks"]["integrator_complete"])


    def test_adaptive_benchmark_is_not_a_scout_success_metric(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            results = root / "benchmark/results"
            results.mkdir(parents=True)
            for pair in range(1, 8):
                for arm in ("control", "experiment"):
                    (results / f"pair{pair}-{arm}.md").write_text(
                        "# Frozen source\n", encoding="utf-8"
                    )
            (results / "pair1-control.md").write_text(
                "TASK: 01 — Control case\nCONDITION: CONTROL\n", encoding="utf-8"
            )
            (results / "pair1-experiment.md").write_text(
                "TASK: 01 — First experiment\nCONDITION: EXPERIMENT\n"
                "TASK: 02 — New result not yet scored\nCONDITION: EXPERIMENT\n",
                encoding="utf-8",
            )
            (root / "benchmark/SCOREBOARD.md").write_text(
                "Matched tasks scored: **1**\n"
                "| 01 | CONTROL | 20 |\n"
                "| 01 | EXPERIMENT | 19 |\n",
                encoding="utf-8",
            )
            intelligence = root / "intelligence"
            intelligence.mkdir()
            (intelligence / "HUNTER_RESTART_READINESS.json").write_text(
                json.dumps({
                    "state": "BLOCKED",
                    "evidence": {"matched_benchmark_tasks": 1},
                    "blockers": [{"code": "frozen_benchmark_incomplete"}],
                }), encoding="utf-8",
            )
            (intelligence / "hunter_runtime_policy.json").write_text(
                json.dumps({"mode": "paused"}), encoding="utf-8",
            )
            (intelligence / "activation_metrics.json").write_text(
                json.dumps({
                    "runtime_activation_enabled": False,
                    "current_activations": 0,
                }), encoding="utf-8",
            )
            truth = governed_runtime_truth(root)
            self.assertEqual(truth["scored_matched_tasks"], 1)
            self.assertEqual(truth["required_matched_tasks"], 50)
            self.assertEqual(truth["raw_result_arms_unscored"], ["02/EXPERIMENT"])
            self.assertTrue(truth["benchmark_snapshot_consistent"])
            self.assertEqual(truth["readiness_state"], "BLOCKED")
            self.assertEqual(truth["adaptive_runtime_mode"], "paused")
            self.assertEqual(truth["current_generated_activations"], 0)
            self.assertEqual(truth["full_worker_runtime_verified"], "NOT_ESTABLISHED")
            now, runs, queues = self.fixture()
            monitor = evaluate(
                runs, queues,
                "Queue snapshots read: 14\nUnique exact-revision candidates: 81",
                now, [],
            )
            self.assertTrue(monitor["healthy"])  # scout-only gates pass
            monitor["governed_runtime"] = truth
            report = render(monitor)
            self.assertIn("Scouting operational gates: 100.0%", report)
            self.assertIn("Adaptive-worker readiness (separate", report)
            self.assertIn("02/EXPERIMENT", report)
            self.assertIn("NOT_OBSERVABLE from GitHub alone", report)

    def test_live_provenance_is_not_a_claim_of_full_autonomy(self):
        root = Path(__file__).resolve().parents[1]
        truth = governed_runtime_truth(root)
        self.assertTrue(0 <= truth["scored_matched_tasks"] <= 50)
        self.assertEqual(truth["required_matched_tasks"], 50)
        self.assertEqual(truth["full_worker_runtime_verified"], "NOT_ESTABLISHED")
        self.assertEqual(truth["chatgpt_task_health"], "NOT_OBSERVABLE_FROM_GITHUB")
        flow = (root / ".github/workflows/public-repo-hunter.yml").read_text()
        self.assertEqual(flow.count("- cron:"), 15)


if __name__ == "__main__":
    unittest.main()
