import unittest

from ai_business_os.persistent_workers import (
    PersistentGoalWorker,
    WorkerResult,
    system_health_executor,
)


class FakeGateway:
    def __init__(self, claim=None):
        self.claim = claim
        self.calls = []

    def call(self, action, payload=None):
        payload = dict(payload or {})
        self.calls.append((action, payload))
        if action == "planning_inputs":
            return {
                "agents": [{"agent_id": "agent-chief", "status": "ACTIVE"}],
                "data_gaps": [],
                "open_goals": [],
            }
        if action == "worker_claim":
            return {"claim": self.claim}
        if action in {"worker_submit", "worker_fail", "worker_heartbeat"}:
            return {"ok": True}
        if action == "health":
            return {"schema_fingerprint": "a" * 64}
        raise AssertionError(action)


class PersistentGoalWorkerTests(unittest.TestCase):
    def test_no_supported_goal_is_noop(self):
        gateway = FakeGateway()
        worker = PersistentGoalWorker(
            gateway,
            worker_instance_id="worker-1",
            executors={"SYSTEM_HEALTH_CHECK": lambda goal: WorkerResult("ok", [])},
            poll_seconds=1,
        )
        self.assertEqual(0, worker.run_once())
        self.assertEqual("worker_claim", gateway.calls[-1][0])
        self.assertEqual(["SYSTEM_HEALTH_CHECK"], gateway.calls[-1][1]["goal_types"])

    def test_claim_executes_only_registered_type_and_submits_for_verification(self):
        gateway = FakeGateway(
            {
                "goal": {
                    "id": "goal-1",
                    "agent_id": "agent-chief",
                    "goal_type": "SYSTEM_HEALTH_CHECK",
                    "title": "Check system",
                },
                "run_id": "run-1",
                "lease_generation": 4,
            }
        )
        worker = PersistentGoalWorker(
            gateway,
            worker_instance_id="worker-1",
            executors={"SYSTEM_HEALTH_CHECK": lambda goal: WorkerResult("healthy", [{"kind": "test"}])},
            heartbeat_seconds=5,
            lease_seconds=30,
            poll_seconds=1,
        )
        self.assertEqual(1, worker.run_once())
        submit = next(payload for action, payload in gateway.calls if action == "worker_submit")
        self.assertEqual("goal-1", submit["goal_id"])
        self.assertEqual(4, submit["lease_generation"])
        self.assertEqual(64, len(submit["output_hash"]))
        self.assertFalse(any(action == "complete_goal" for action, _ in gateway.calls))

    def test_executor_failure_blocks_instead_of_retry_loop(self):
        gateway = FakeGateway(
            {
                "goal": {
                    "id": "goal-1",
                    "agent_id": "agent-chief",
                    "goal_type": "SYSTEM_HEALTH_CHECK",
                    "title": "Check system",
                },
                "run_id": "run-1",
                "lease_generation": 1,
            }
        )
        def fail(_goal):
            raise RuntimeError("boom")
        worker = PersistentGoalWorker(
            gateway,
            worker_instance_id="worker-1",
            executors={"SYSTEM_HEALTH_CHECK": fail},
            heartbeat_seconds=5,
            lease_seconds=30,
            poll_seconds=1,
        )
        self.assertEqual(1, worker.run_once())
        failure = next(payload for action, payload in gateway.calls if action == "worker_fail")
        self.assertFalse(failure["requeue"])

    def test_system_health_executor_is_read_only(self):
        gateway = FakeGateway()
        executor = system_health_executor(gateway)
        result = executor({"id": "goal-health"})
        self.assertEqual(64, len(result.output_hash()))
        self.assertEqual(["health", "planning_inputs"], [a for a, _ in gateway.calls])


if __name__ == "__main__":
    unittest.main()
