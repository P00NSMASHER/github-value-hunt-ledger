import tempfile
import unittest
from pathlib import Path

from business_os.agents.persistent_runtime import PersistentAgentRuntime


class PersistentAgentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "runtime.sqlite3"
        self.rt = PersistentAgentRuntime(self.db)
        self.rt.register_agent("research-1", "RESEARCH", now=100.0)

    def tearDown(self):
        self.tmp.cleanup()

    def test_goal_persists_and_claims(self):
        goal = self.rt.enqueue_goal(
            "Find three qualified prospects",
            {"business": "freight-recovery"},
            priority=7,
            now=101.0,
        )
        claimed = self.rt.claim_next_goal(
            "research-1", lease_seconds=30, now=102.0
        )
        self.assertEqual(goal.id, claimed.id)
        self.assertEqual("RUNNING", claimed.state)
        self.assertEqual("research-1", claimed.claimed_by)
        self.assertEqual(1, claimed.lease_generation)

        reopened = PersistentAgentRuntime(self.db)
        persisted = reopened.get_goal(goal.id)
        self.assertEqual("RUNNING", persisted.state)
        self.assertEqual(1, persisted.lease_generation)

    def test_priority_queue(self):
        self.rt.enqueue_goal("low", priority=1, now=101)
        high = self.rt.enqueue_goal("high", priority=99, now=102)
        claimed = self.rt.claim_next_goal("research-1", now=103)
        self.assertEqual(high.id, claimed.id)

    def test_heartbeat_extends_lease(self):
        goal = self.rt.enqueue_goal("work", now=101)
        claimed = self.rt.claim_next_goal(
            "research-1", lease_seconds=10, now=102
        )
        beat = self.rt.heartbeat(
            "research-1",
            goal.id,
            claimed.lease_generation,
            extend_seconds=50,
            now=105,
        )
        self.assertEqual(155.0, beat.lease_expires_at)

    def test_expired_goal_is_requeued_and_stale_worker_cannot_complete(self):
        goal = self.rt.enqueue_goal("work", now=101)
        claimed = self.rt.claim_next_goal(
            "research-1", lease_seconds=10, now=102
        )
        count = self.rt.requeue_expired(now=113)
        self.assertEqual(1, count)
        self.assertEqual("PENDING", self.rt.get_goal(goal.id).state)

        with self.assertRaises(RuntimeError):
            self.rt.complete_goal(
                "research-1",
                goal.id,
                claimed.lease_generation,
                {"bad": "stale success"},
                now=114,
            )

    def test_reclaimed_goal_increments_generation(self):
        goal = self.rt.enqueue_goal("work", now=101)
        first = self.rt.claim_next_goal("research-1", lease_seconds=10, now=102)
        self.rt.requeue_expired(now=113)
        second = self.rt.claim_next_goal("research-1", lease_seconds=10, now=114)
        self.assertEqual(goal.id, second.id)
        self.assertEqual(first.lease_generation + 1, second.lease_generation)

    def test_wrong_agent_cannot_commit(self):
        goal = self.rt.enqueue_goal("work", now=101)
        claimed = self.rt.claim_next_goal("research-1", now=102)
        self.rt.register_agent("engineering-1", "ENGINEERING", now=103)

        with self.assertRaises(PermissionError):
            self.rt.complete_goal(
                "engineering-1",
                goal.id,
                claimed.lease_generation,
                {"status": "pretend"},
                now=104,
            )

    def test_complete_goal_is_terminal(self):
        goal = self.rt.enqueue_goal("work", now=101)
        claimed = self.rt.claim_next_goal("research-1", now=102)
        completed = self.rt.complete_goal(
            "research-1",
            goal.id,
            claimed.lease_generation,
            {"artifact": "report.json"},
            now=103,
        )
        self.assertEqual("COMPLETED", completed.state)
        self.assertIsNone(completed.lease_expires_at)
        self.assertIsNone(self.rt.claim_next_goal("research-1", now=104))

    def test_failed_goal_can_be_requeued(self):
        goal = self.rt.enqueue_goal("work", now=101)
        claimed = self.rt.claim_next_goal("research-1", now=102)
        failed = self.rt.fail_goal(
            "research-1",
            goal.id,
            claimed.lease_generation,
            "temporary provider failure",
            requeue=True,
            now=103,
        )
        self.assertEqual("PENDING", failed.state)
        again = self.rt.claim_next_goal("research-1", now=104)
        self.assertEqual(goal.id, again.id)
        self.assertEqual(2, again.lease_generation)

    def test_dashboard(self):
        self.rt.enqueue_goal("a", now=101)
        self.rt.enqueue_goal("b", now=102)
        self.rt.claim_next_goal("research-1", now=103)
        d = self.rt.dashboard()
        self.assertEqual(1, d["agents"])
        self.assertEqual(1, d["goals"]["PENDING"])
        self.assertEqual(1, d["goals"]["RUNNING"])
        self.assertEqual(1, d["open_runs"])


if __name__ == "__main__":
    unittest.main()
