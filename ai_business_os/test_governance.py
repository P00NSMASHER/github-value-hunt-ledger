import tempfile
import unittest
from pathlib import Path

from ai_business_os.governance import GovernanceControlPlane, GovernanceError
from ai_business_os.persistent_agents.runtime import AgentRuntime


class GovernanceControlPlaneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = AgentRuntime(Path(self.tmp.name) / "runtime.sqlite3")
        self.gov = GovernanceControlPlane(self.runtime)
        self.agent = self.runtime.register_agent("worker")

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def policy(
        self,
        allowed=("READ", "INTERNAL_WRITE", "EXTERNAL_WRITE", "MONEY_MOVEMENT"),
        approval=("EXTERNAL_WRITE", "MONEY_MOVEMENT"),
        **kwargs,
    ):
        return self.gov.set_agent_policy(
            self.agent,
            allowed_classes=allowed,
            human_approval_classes=approval,
            updated_by_principal="owner",
            principal_kind="HUMAN",
            evidence={"ticket": "POL-1"},
            **kwargs,
        )

    def test_missing_policy_fails_closed(self):
        with self.assertRaises(GovernanceError):
            self.gov.request_action(
                self.agent,
                action_key="drive.read",
                action_class="READ",
                parameters={"file": "x"},
            )

    def test_nonhuman_cannot_change_policy(self):
        with self.assertRaises(GovernanceError):
            self.gov.set_agent_policy(
                self.agent,
                allowed_classes=["READ"],
                human_approval_classes=[],
                updated_by_principal="agent-self",
                principal_kind="AGENT",
                evidence={"attempt": "self-escalation"},
            )

    def test_highest_risk_classes_cannot_bypass_human_approval(self):
        with self.assertRaises(GovernanceError):
            self.gov.set_agent_policy(
                self.agent,
                allowed_classes=["READ", "MONEY_MOVEMENT"],
                human_approval_classes=[],
                updated_by_principal="owner",
                principal_kind="HUMAN",
                evidence={"attempt": "unsafe-autonomy"},
            )

    def test_read_action_can_be_authorized_without_approval(self):
        self.policy()
        decision = self.gov.request_action(
            self.agent,
            action_key="drive.read",
            action_class="READ",
            parameters={"file": "report.pdf"},
        )
        self.assertEqual(decision["decision"], "ALLOW")
        self.assertEqual(len(decision["receipt_hash"]), 64)

    def test_external_write_requires_human_approval(self):
        self.policy()
        first = self.gov.request_action(
            self.agent,
            action_key="gmail.send",
            action_class="EXTERNAL_WRITE",
            parameters={"to": "customer@example.com", "draft_hash": "abc"},
        )
        self.assertEqual(first["decision"], "REQUIRE_APPROVAL")
        approval = self.gov.approve_request(
            first["request_id"],
            approver_principal="owner",
            approver_kind="HUMAN",
            evidence={"reviewed": True},
        )
        allowed = self.gov.evaluate_request(
            first["request_id"],
            approval_id=approval["id"],
        )
        self.assertEqual(allowed["decision"], "ALLOW")
        self.assertEqual(allowed["approval_id"], approval["id"])

    def test_agent_cannot_approve_high_consequence_action(self):
        self.policy()
        req = self.gov.request_action(
            self.agent,
            action_key="gmail.send",
            action_class="EXTERNAL_WRITE",
            parameters={"to": "customer@example.com"},
        )
        with self.assertRaises(GovernanceError):
            self.gov.approve_request(
                req["request_id"],
                approver_principal="another-agent",
                approver_kind="AGENT",
                evidence={"claimed": "approved"},
            )

    def test_approval_is_bound_to_exact_request(self):
        self.policy()
        a = self.gov.request_action(
            self.agent,
            action_key="gmail.send",
            action_class="EXTERNAL_WRITE",
            parameters={"to": "a@example.com", "body": "A"},
        )
        b = self.gov.request_action(
            self.agent,
            action_key="gmail.send",
            action_class="EXTERNAL_WRITE",
            parameters={"to": "b@example.com", "body": "B"},
        )
        approval = self.gov.approve_request(
            a["request_id"],
            approver_principal="owner",
            approver_kind="HUMAN",
            evidence={"reviewed": "A"},
        )
        with self.assertRaises(GovernanceError):
            self.gov.evaluate_request(b["request_id"], approval_id=approval["id"])

    def test_approval_and_request_are_single_use(self):
        self.policy()
        req = self.gov.request_action(
            self.agent,
            action_key="gmail.send",
            action_class="EXTERNAL_WRITE",
            parameters={"to": "a@example.com"},
        )
        approval = self.gov.approve_request(
            req["request_id"],
            approver_principal="owner",
            approver_kind="HUMAN",
            evidence={"reviewed": True},
        )
        self.gov.evaluate_request(req["request_id"], approval_id=approval["id"])
        with self.assertRaises(GovernanceError):
            self.gov.evaluate_request(req["request_id"], approval_id=approval["id"])

    def test_explicit_denylist_overrides_allowed_class(self):
        self.policy(denied_action_keys=["drive.delete"])
        decision = self.gov.request_action(
            self.agent,
            action_key="drive.delete",
            action_class="INTERNAL_WRITE",
            parameters={"file": "important"},
        )
        self.assertEqual(decision["decision"], "DENY")

    def test_allowlist_blocks_unknown_action_keys(self):
        self.policy(allowed_action_keys=["drive.read"])
        allowed = self.gov.request_action(
            self.agent,
            action_key="drive.read",
            action_class="READ",
            parameters={"file": "ok"},
        )
        self.assertEqual(allowed["decision"], "ALLOW")
        denied = self.gov.request_action(
            self.agent,
            action_key="github.read",
            action_class="READ",
            parameters={"repo": "x"},
        )
        self.assertEqual(denied["decision"], "DENY")

    def test_action_count_budget_is_enforced(self):
        self.policy(max_actions_per_window=1)
        first = self.gov.request_action(
            self.agent,
            action_key="drive.read",
            action_class="READ",
            parameters={"file": "1"},
        )
        second = self.gov.request_action(
            self.agent,
            action_key="drive.read",
            action_class="READ",
            parameters={"file": "2"},
        )
        self.assertEqual(first["decision"], "ALLOW")
        self.assertEqual(second["decision"], "DENY")
        self.assertIn("action-count", second["reason"])

    def test_cost_budget_is_enforced(self):
        self.policy(max_cost_units_per_window=5.0)
        first = self.gov.request_action(
            self.agent,
            action_key="analysis.run",
            action_class="INTERNAL_WRITE",
            parameters={"job": "1"},
            cost_units=4.0,
        )
        second = self.gov.request_action(
            self.agent,
            action_key="analysis.run",
            action_class="INTERNAL_WRITE",
            parameters={"job": "2"},
            cost_units=2.0,
        )
        self.assertEqual(first["decision"], "ALLOW")
        self.assertEqual(second["decision"], "DENY")
        self.assertIn("cost-unit", second["reason"])

    def test_money_movement_needs_approval_and_budget(self):
        self.policy(max_money_cents_per_window=10000)
        req = self.gov.request_action(
            self.agent,
            action_key="stripe.refund",
            action_class="MONEY_MOVEMENT",
            parameters={"payment_id": "p1"},
            amount_cents=7000,
        )
        self.assertEqual(req["decision"], "REQUIRE_APPROVAL")
        approval = self.gov.approve_request(
            req["request_id"],
            approver_principal="owner",
            approver_kind="HUMAN",
            evidence={"refund_review": "approved"},
        )
        allowed = self.gov.evaluate_request(req["request_id"], approval_id=approval["id"])
        self.assertEqual(allowed["decision"], "ALLOW")

        over = self.gov.request_action(
            self.agent,
            action_key="stripe.refund",
            action_class="MONEY_MOVEMENT",
            parameters={"payment_id": "p2"},
            amount_cents=4000,
        )
        self.assertEqual(over["decision"], "DENY")
        self.assertIn("money-movement", over["reason"])

    def test_global_kill_switch_denies_even_read(self):
        self.policy()
        self.gov.set_global_kill_switch(
            enabled=True,
            principal="owner",
            principal_kind="HUMAN",
            reason="incident",
            evidence={"incident": "INC-1"},
        )
        decision = self.gov.request_action(
            self.agent,
            action_key="drive.read",
            action_class="READ",
            parameters={"file": "x"},
        )
        self.assertEqual(decision["decision"], "DENY")
        self.assertIn("global kill switch", decision["reason"])

    def test_agent_kill_switch_is_scoped(self):
        self.policy()
        other = self.runtime.register_agent("other-worker")
        self.gov.set_agent_policy(
            other,
            allowed_classes=["READ"],
            human_approval_classes=[],
            updated_by_principal="owner",
            principal_kind="HUMAN",
            evidence={"ticket": "POL-2"},
        )
        self.gov.set_agent_kill_switch(
            self.agent,
            enabled=True,
            principal="owner",
            principal_kind="HUMAN",
            reason="agent anomaly",
            evidence={"incident": "INC-2"},
        )
        denied = self.gov.request_action(
            self.agent,
            action_key="drive.read",
            action_class="READ",
            parameters={"file": "x"},
        )
        allowed = self.gov.request_action(
            other,
            action_key="drive.read",
            action_class="READ",
            parameters={"file": "y"},
        )
        self.assertEqual(denied["decision"], "DENY")
        self.assertEqual(allowed["decision"], "ALLOW")

    def test_nonhuman_cannot_toggle_kill_switch(self):
        with self.assertRaises(GovernanceError):
            self.gov.set_global_kill_switch(
                enabled=True,
                principal="worker",
                principal_kind="AGENT",
                reason="self-issued",
                evidence={"bad": True},
            )

    def test_policy_version_changes_and_hashes(self):
        p1 = self.policy()
        p2 = self.policy(max_actions_per_window=5)
        self.assertEqual(p1["version"], 1)
        self.assertEqual(p2["version"], 2)
        self.assertNotEqual(p1["policy_hash"], p2["policy_hash"])


if __name__ == "__main__":
    unittest.main()
