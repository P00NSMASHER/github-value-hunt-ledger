import tempfile
import unittest
from pathlib import Path

from ai_business_os.persistent_agents.runtime import AgentRuntime, InvalidTransition


class AgentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "runtime.sqlite3"
        self.runtime = AgentRuntime(self.db)

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def test_restart_persists_goal_and_state(self):
        agent = self.runtime.register_agent("research")
        goal = self.runtime.assign_goal(agent, "Find qualified prospects", state={"found": 0})
        self.runtime.transition_goal(goal, "ACTIVE")
        self.runtime.update_goal_state(goal, {"found": 7})
        self.runtime.close()

        self.runtime = AgentRuntime(self.db)
        restored = self.runtime.get_goal(goal)
        self.assertEqual(restored["status"], "ACTIVE")
        self.assertEqual(restored["state"]["found"], 7)

    def test_subagent_and_hash_chain(self):
        parent = self.runtime.register_agent("chief-of-staff")
        child = self.runtime.spawn_subagent(parent, "research")
        goal = self.runtime.assign_goal(child, "Research target market")
        self.runtime.transition_goal(goal, "ACTIVE")
        self.runtime.heartbeat(child)
        self.assertTrue(self.runtime.verify_event_chain(child))

    def test_snapshot_restores_state_without_deleting_history(self):
        agent = self.runtime.register_agent("engineering")
        goal = self.runtime.assign_goal(agent, "Improve product", state={"version": 1})
        self.runtime.transition_goal(goal, "ACTIVE")
        snap = self.runtime.snapshot_goal(goal)
        self.runtime.update_goal_state(goal, {"version": 2})
        restored = self.runtime.restore_snapshot(snap)
        self.assertEqual(restored["state"]["version"], 1)
        self.assertTrue(self.runtime.verify_event_chain(agent))

    def test_invalid_transition_fails_closed(self):
        agent = self.runtime.register_agent("sales")
        goal = self.runtime.assign_goal(agent, "Prepare outreach")
        with self.assertRaises(InvalidTransition):
            self.runtime.transition_goal(goal, "COMPLETE")

    def test_stale_reclaim_increments_generation(self):
        agent = self.runtime.register_agent("research")
        self.runtime.conn.execute(
            "UPDATE agents SET last_heartbeat = 0 WHERE id = ?",
            (agent,),
        )
        self.runtime.conn.commit()
        self.assertTrue(self.runtime.reclaim_if_stale(agent, 1))
        row = self.runtime._require_agent(agent)
        self.assertEqual(row["generation"], 2)


if __name__ == "__main__":
    unittest.main()
