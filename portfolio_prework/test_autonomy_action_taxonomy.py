import json
import unittest
from pathlib import Path


class AutonomyTaxonomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = Path("portfolio_prework/AUTONOMY_ACTION_TAXONOMY.json")
        cls.data = json.loads(cls.path.read_text(encoding="utf-8"))

    def test_exact_core_classes(self):
        classes = [item["autonomy_class"] for item in self.data["classes"]]
        self.assertEqual(classes, ["OBSERVE", "EXPERIMENT", "MODIFY", "ACT"])

    def test_default_deny_policy(self):
        self.assertEqual(self.data["default_policy"], "DENY_UNLESS_EXPLICITLY_ALLOWED")

    def test_act_is_not_autonomously_allowed(self):
        act = next(item for item in self.data["classes"] if item["autonomy_class"] == "ACT")
        self.assertFalse(act["default_allowed"])
        self.assertTrue(act["requires_human_authorization"])

    def test_live_trading_is_prohibited(self):
        gates = {item["action"]: item["policy"] for item in self.data["hard_gates"]}
        self.assertEqual(gates["live_market_trading_or_broker_order"], "PROHIBITED")

    def test_required_human_gates_present(self):
        gates = {item["action"]: item["policy"] for item in self.data["hard_gates"]}
        for action in [
            "production_deployment",
            "external_customer_communication",
            "money_movement_or_purchase",
            "destructive_or_irreversible_data_change",
            "consequential_child_facing_change_or_experiment",
        ]:
            self.assertEqual(gates[action], "HUMAN_APPROVAL_REQUIRED")


if __name__ == "__main__":
    unittest.main()
