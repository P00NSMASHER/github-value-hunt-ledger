import json
import unittest
from pathlib import Path


class AutonomyMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = json.loads(Path("portfolio_prework/AUTONOMY_MATRIX.json").read_text(encoding="utf-8"))
        cls.registry = json.loads(Path("portfolio_prework/PROJECT_ID_REGISTRY.json").read_text(encoding="utf-8"))
        cls.by_id = {item["project_id"]: item for item in cls.matrix["projects"]}

    def test_matrix_covers_registry_exactly(self):
        registry_ids = {item["project_id"] for item in self.registry["projects"]}
        matrix_ids = set(self.by_id)
        self.assertEqual(matrix_ids, registry_ids)

    def test_each_project_has_all_four_classes(self):
        for project in self.matrix["projects"]:
            self.assertEqual(set(project["permissions"]), {"OBSERVE", "EXPERIMENT", "MODIFY", "ACT"})

    def test_no_project_has_unbounded_act(self):
        for project in self.matrix["projects"]:
            self.assertNotIn(project["permissions"]["ACT"], {"ALLOW", "ALLOW_BOUNDED"})

    def test_modify_is_never_unbounded(self):
        for project in self.matrix["projects"]:
            self.assertIn(project["permissions"]["MODIFY"], {"ALLOW_BOUNDED", "HUMAN_APPROVAL", "PROHIBITED"})

    def test_trading_project_external_action_is_prohibited(self):
        project = self.by_id["PRJ-007"]
        self.assertEqual(project["permissions"]["ACT"], "PROHIBITED")
        overrides = project["action_overrides"]
        for key in [
            "live_market_trading_or_broker_order",
            "autonomous_investment_positioning",
            "trade_direction_or_position_sizing_output",
            "production_deployment_for_trade_execution",
        ]:
            self.assertEqual(overrides[key], "PROHIBITED")

    def test_child_facing_projects_are_human_gated(self):
        for project_id in ["PRJ-005", "PRJ-006"]:
            project = self.by_id[project_id]
            self.assertEqual(
                project["action_overrides"]["consequential_child_facing_change_or_experiment"],
                "HUMAN_APPROVAL",
            )

    def test_recovery_external_actions_are_human_gated(self):
        self.assertEqual(
            self.by_id["PRJ-001"]["action_overrides"]["external_customer_communication"],
            "HUMAN_APPROVAL",
        )
        self.assertEqual(
            self.by_id["PRJ-002"]["action_overrides"]["carrier_contact_or_claim_submission"],
            "HUMAN_APPROVAL",
        )

    def test_operational_state_and_evidence_protections(self):
        self.assertEqual(
            self.by_id["PRJ-003"]["action_overrides"]["publish_sensitive_operational_state"],
            "PROHIBITED",
        )
        self.assertEqual(
            self.by_id["PRJ-011"]["action_overrides"]["overwrite_immutable_evidence"],
            "PROHIBITED",
        )


if __name__ == "__main__":
    unittest.main()
