import tempfile
import unittest
from pathlib import Path

from business_os.governance.control_plane import (
    GovernanceControlPlane,
    GovernanceError,
)


class RuntimeGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.g = GovernanceControlPlane(
            Path(self.tmp.name) / "governance.sqlite3"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def policy(self, agent="research", budget=10.0, cap=5.0):
        return self.g.set_policy(
            agent,
            allowed_tools=(
                "web.*",
                "github.read",
                "github.branch",
                "gmail.send",
            ),
            daily_budget_usd=budget,
            max_action_cost_usd=cap,
            now=100,
        )

    def test_unknown_agent_fails_closed(self):
        decision = self.g.request_action(
            "unknown", "web.search", "search", risk_level="READ", now=100
        )
        self.assertEqual("DENY", decision.state)
        self.assertIn("no policy", decision.reasons[0])

    def test_allowlisted_read_is_authorized(self):
        self.policy()
        decision = self.g.request_action(
            "research",
            "web.search",
            "search",
            risk_level="READ",
            estimated_cost_usd=1.25,
            now=101,
        )
        self.assertEqual("ALLOW", decision.state)
        self.assertIsNotNone(decision.receipt_id)
        self.assertAlmostEqual(
            1.25, self.g.budget_used("research", now=101)
        )

    def test_unlisted_tool_is_denied(self):
        self.policy()
        decision = self.g.request_action(
            "research",
            "stripe.refund",
            "refund",
            risk_level="FINANCIAL",
            now=101,
        )
        self.assertEqual("DENY", decision.state)
        self.assertIn("allowlisted", decision.reasons[0])

    def test_external_communication_requires_independent_approval(self):
        self.policy()
        decision = self.g.request_action(
            "research",
            "gmail.send",
            "send cold email",
            risk_level="EXTERNAL_COMMUNICATION",
            estimated_cost_usd=0.5,
            now=101,
        )
        self.assertEqual("REQUIRE_APPROVAL", decision.state)
        with self.assertRaises(PermissionError):
            self.g.approve(
                decision.request_id,
                approver_id="research",
                approver_role="HUMAN",
                reason="self approval",
                now=102,
            )
        receipt = self.g.approve(
            decision.request_id,
            approver_id="owner",
            approver_role="HUMAN",
            reason="reviewed message",
            now=103,
        )
        self.assertEqual("APPROVED", receipt.state)
        self.assertIsNotNone(receipt.authorization_receipt_id)

    def test_destructive_policy_cannot_be_overridden(self):
        self.policy()
        decision = self.g.request_action(
            "research",
            "github.branch",
            "delete repository",
            risk_level="DESTRUCTIVE",
            now=101,
        )
        self.assertEqual("DENY", decision.state)
        with self.assertRaises(GovernanceError):
            self.g.approve(
                decision.request_id,
                approver_id="owner",
                approver_role="ADMIN",
                reason="try override",
                now=102,
            )

    def test_budget_and_per_action_caps_fail_closed(self):
        self.policy(budget=3.0, cap=2.0)
        too_large = self.g.request_action(
            "research",
            "web.search",
            "expensive query",
            risk_level="READ",
            estimated_cost_usd=2.5,
            now=101,
        )
        self.assertEqual("DENY", too_large.state)
        first = self.g.request_action(
            "research",
            "web.search",
            "query",
            risk_level="READ",
            estimated_cost_usd=2.0,
            now=102,
        )
        self.assertEqual("ALLOW", first.state)
        second = self.g.request_action(
            "research",
            "web.search",
            "query 2",
            risk_level="READ",
            estimated_cost_usd=1.1,
            now=103,
        )
        self.assertEqual("DENY", second.state)
        self.assertIn("daily budget", second.reasons[0])

    def test_global_kill_switch_blocks_even_reads(self):
        self.policy()
        self.g.engage_kill_switch(
            reason="incident",
            actor_id="watchdog",
            actor_role="SYSTEM",
            now=101,
        )
        decision = self.g.request_action(
            "research",
            "web.search",
            "search",
            risk_level="READ",
            now=102,
        )
        self.assertEqual("DENY", decision.state)
        self.assertEqual(("kill switch engaged",), decision.reasons)
        with self.assertRaises(PermissionError):
            self.g.release_kill_switch(
                reason="unsafe release",
                actor_id="research",
                actor_role="HUMAN",
                now=103,
            )
        self.g.release_kill_switch(
            reason="incident cleared",
            actor_id="owner",
            actor_role="INTEGRATOR",
            now=104,
        )
        allowed = self.g.request_action(
            "research",
            "web.search",
            "search",
            risk_level="READ",
            now=105,
        )
        self.assertEqual("ALLOW", allowed.state)

    def test_agent_kill_switch_is_scoped(self):
        self.policy("a")
        self.policy("b")
        self.g.engage_kill_switch(
            scope="AGENT",
            scope_id="a",
            reason="bad state",
            actor_id="watchdog",
            actor_role="SYSTEM",
            now=101,
        )
        a = self.g.request_action(
            "a", "web.search", "q", risk_level="READ", now=102
        )
        b = self.g.request_action(
            "b", "web.search", "q", risk_level="READ", now=102
        )
        self.assertEqual("DENY", a.state)
        self.assertEqual("ALLOW", b.state)

    def test_approval_rechecks_kill_switch_and_does_not_charge(self):
        self.policy()
        pending = self.g.request_action(
            "research",
            "gmail.send",
            "send",
            risk_level="EXTERNAL_COMMUNICATION",
            estimated_cost_usd=1.0,
            now=101,
        )
        self.g.engage_kill_switch(
            scope="AGENT",
            scope_id="research",
            reason="pause",
            actor_id="watchdog",
            actor_role="SYSTEM",
            now=102,
        )
        receipt = self.g.approve(
            pending.request_id,
            approver_id="owner",
            approver_role="HUMAN",
            reason="message reviewed",
            now=103,
        )
        self.assertEqual("DENIED", receipt.state)
        self.assertEqual(
            0.0, self.g.budget_used("research", now=103)
        )

    def test_audit_log_is_append_only_and_records_control_events(self):
        self.policy()
        self.g.request_action(
            "research",
            "web.search",
            "search",
            risk_level="READ",
            now=101,
        )
        events = [row["event_type"] for row in self.g.audit_log()]
        self.assertEqual("POLICY_SET", events[0])
        self.assertIn("ACTION_REQUESTED", events)
        self.assertIn("ACTION_ALLOWED", events)
        seq = [row["sequence"] for row in self.g.audit_log()]
        self.assertEqual(sorted(seq), seq)
        self.assertEqual(len(seq), len(set(seq)))


if __name__ == "__main__":
    unittest.main()
