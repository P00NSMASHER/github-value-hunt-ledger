import json
import unittest

from ai_business_os.runtime_service import (
    GatewayError,
    GatewayProductionBridge,
    GatewayReadExecutor,
    GatewayWriteExecutor,
)


class FakeGateway:
    def __init__(self):
        self.calls = []

    def call(self, action, payload=None):
        self.calls.append((action, payload or {}))
        if action == "health":
            return {"schema_fingerprint": "a" * 64}
        if action == "portfolio_view":
            return {
                "schema_fingerprint": "a" * 64,
                "businesses": [{"id": "b1", "slug": "starblox", "name": "StarBlox"}],
                "command_center": None,
                "pending_approvals": [],
            }
        if action == "planning_inputs":
            return {"agents": [], "initiatives": [], "data_gaps": [], "open_goals": []}
        if action == "worker_status":
            return {"heartbeats": [], "leases": [], "recent_runs": []}
        if action == "approval_lookup":
            return {
                "approval": {
                    "request_key": payload["request_key"],
                    "intent_hash": "c" * 64,
                    "status": "PENDING",
                }
            }
        if action == "activate_goal":
            return {
                "goal": {
                    "id": "g1",
                    "agent_id": payload["target_agent_id"],
                    "goal_type": payload["goal_type"],
                    "title": payload["objective"],
                    "status": "PENDING",
                    "priority": payload["priority"],
                    "constraints": payload["constraints"],
                    "evidence_requirements": payload["evidence_requirements"],
                }
            }
        if action in {"worker_claim", "worker_heartbeat", "worker_submit", "worker_fail"}:
            return {"claim": None} if action == "worker_claim" else {"ok": True}
        if action == "decide_approval":
            return {
                "receipt": {
                    "request_key": payload["request_key"],
                    "status": "APPROVED" if payload["decision"] == "APPROVE" else "REJECTED",
                    "decision_receipt_hash": "d" * 64,
                }
            }
        raise AssertionError(action)


class RuntimeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.gateway = FakeGateway()

    def test_bridge_checks_exact_schema_fingerprint(self):
        bridge = GatewayProductionBridge(self.gateway)
        self.assertEqual("a" * 64, bridge.assert_schema_current("a" * 64))
        with self.assertRaisesRegex(GatewayError, "schema drift"):
            bridge.assert_schema_current("b" * 64)

    def test_bridge_reads_only_named_gateway_operations(self):
        bridge = GatewayProductionBridge(self.gateway)
        view = bridge.portfolio_view(expected_schema_fingerprint="a" * 64)
        self.assertEqual("starblox", view["businesses"][0]["slug"])
        inputs = bridge.planning_inputs()
        self.assertEqual([], inputs["data_gaps"])
        self.assertEqual(["portfolio_view", "planning_inputs"], [x[0] for x in self.gateway.calls])

    def test_read_executor_only_supports_approval_lookup_contract(self):
        executor = GatewayReadExecutor(self.gateway)
        rows = executor(
            "select request_key from ai_business_os_prod.approval_inbox where request_key = %s",
            ("approval-001",),
        )
        self.assertEqual("approval-001", rows[0]["request_key"])
        with self.assertRaisesRegex(GatewayError, "unrecognized SQL"):
            executor("select * from ai_business_os_prod.businesses", ())

    def test_write_executor_maps_goal_activation_without_arbitrary_sql(self):
        executor = GatewayWriteExecutor(self.gateway)
        rows = executor(
            "insert into ai_business_os_prod.agent_goals(...) values (...)",
            (
                "agent-research",
                "RESEARCH",
                "Research StarBlox retention",
                80,
                json.dumps({"objective_hash": "x"}),
                json.dumps(["evidence required"]),
            ),
        )
        self.assertEqual("PENDING", rows[0]["status"])
        self.assertEqual("activate_goal", self.gateway.calls[-1][0])
        with self.assertRaisesRegex(GatewayError, "unrecognized SQL"):
            executor("delete from ai_business_os_prod.agent_goals", ())

    def test_write_executor_maps_approval_decision_but_not_consumption(self):
        executor = GatewayWriteExecutor(self.gateway)
        rows = executor(
            "select * from ai_business_os_prod.approval_decide(%s,%s,%s,%s)",
            ("approval-001", "APPROVE", "owner", "Reviewed"),
        )
        self.assertEqual("APPROVED", rows[0]["status"])
        self.assertEqual("decide_approval", self.gateway.calls[-1][0])
        with self.assertRaisesRegex(GatewayError, "unrecognized SQL"):
            executor(
                "select * from ai_business_os_prod.approval_consume(%s,%s,%s,%s)",
                ("approval-001", "hash", "receipt", "owner"),
            )


if __name__ == "__main__":
    unittest.main()
