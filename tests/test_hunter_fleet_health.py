import datetime as dt
import unittest

from tools.hunter_fleet_health import WORKERS, evaluate


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


if __name__ == "__main__":
    unittest.main()
