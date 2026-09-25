import unittest

from ai_business_os.production_bridge import (
    ProductionBridgeError,
    ProductionReadBridge,
)


class FakeExecutor:
    def __init__(self):
        self.calls = []
        self.fingerprint = "a" * 64
        self.command_rows = [
            {
                "snapshot_key": "ceo-latest",
                "snapshot_hash": "b" * 64,
                "payload": '{"recommended_actions":[{"business":"freight"}]}',
                "generated_at": "2026-09-24T23:00:00Z",
            }
        ]

    def __call__(self, sql, params):
        self.calls.append((sql, params))
        normalized = " ".join(sql.split()).lower()
        if "schema_fingerprint_v1()" in normalized:
            return [{"schema_fingerprint": self.fingerprint}]
        if "from ai_business_os_prod.businesses" in normalized:
            return [
                {"id": "business-1", "slug": "freight", "name": "Freight"},
                {"id": "business-2", "slug": "starblox", "name": "StarBlox"},
            ]
        if "from ai_business_os_prod.command_center_snapshots" in normalized:
            return self.command_rows
        if "from ai_business_os_prod.approval_inbox" in normalized:
            return [
                {
                    "id": "approval-1",
                    "request_key": "approval-001",
                    "agent_id": "agent-growth",
                    "action_key": "github.pr.create",
                    "action_class": "EXTERNAL_WRITE",
                    "title": "Approve governed action",
                    "intent_hash": "c" * 64,
                    "predicted_risk": "MEDIUM_EXTERNAL_COMMITMENT",
                    "expected_money_cents": 0,
                    "status": "PENDING",
                    "created_at": "2026-09-24T23:01:00Z",
                    "expires_at": "2026-09-25T00:01:00Z",
                }
            ]
        raise AssertionError(f"unexpected query: {normalized}")


class ProductionReadBridgeTests(unittest.TestCase):
    def setUp(self):
        self.executor = FakeExecutor()
        self.bridge = ProductionReadBridge(self.executor)

    def test_portfolio_view_reads_authoritative_surfaces(self):
        view = self.bridge.portfolio_view(expected_schema_fingerprint="a" * 64)
        self.assertEqual("a" * 64, view["schema_fingerprint"])
        self.assertEqual(["freight", "starblox"], [row["slug"] for row in view["businesses"]])
        self.assertEqual("freight", view["command_center"]["payload"]["recommended_actions"][0]["business"])
        self.assertEqual("github.pr.create", view["pending_approvals"][0]["action_key"])
        self.assertEqual("approval-001", view["pending_approvals"][0]["request_key"])
        self.assertEqual("c" * 64, view["pending_approvals"][0]["intent_hash"])
        self.assertEqual(("PENDING",), self.executor.calls[-1][1])

    def test_every_bridge_query_is_a_single_select(self):
        self.bridge.portfolio_view()
        for sql, _ in self.executor.calls:
            normalized = " ".join(sql.strip().split()).lower()
            self.assertTrue(normalized.startswith("select "))
            self.assertNotIn(";", normalized)

    def test_schema_drift_fails_closed(self):
        with self.assertRaisesRegex(ProductionBridgeError, "production schema drift"):
            self.bridge.assert_schema_current("d" * 64)

    def test_mutating_sql_is_rejected_before_executor(self):
        with self.assertRaisesRegex(ProductionBridgeError, "SELECT statements only"):
            self.bridge._run("delete from ai_business_os_prod.businesses")
        self.assertEqual([], self.executor.calls)

    def test_invalid_command_center_payload_fails_closed(self):
        self.executor.command_rows[0]["payload"] = "not-json"
        with self.assertRaisesRegex(ProductionBridgeError, "invalid JSON"):
            self.bridge.latest_command_center_snapshot()

    def test_missing_command_center_snapshot_is_explicit(self):
        self.executor.command_rows = []
        self.assertIsNone(self.bridge.latest_command_center_snapshot())

    def test_pending_approval_requires_request_identity(self):
        original = self.executor.__call__

        def broken(sql, params):
            rows = original(sql, params)
            if "approval_inbox" in sql:
                rows[0]["intent_hash"] = ""
            return rows

        self.bridge = ProductionReadBridge(broken)
        with self.assertRaisesRegex(ProductionBridgeError, "immutable request identity"):
            self.bridge.pending_approvals()


if __name__ == "__main__":
    unittest.main()
