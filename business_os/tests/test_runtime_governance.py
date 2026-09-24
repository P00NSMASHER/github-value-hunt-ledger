import tempfile
import unittest
from pathlib import Path

from business_os.governance.policy import ActionRequest, GovernanceEngine


class GovernanceEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "governance.sqlite3"
        self.g = GovernanceEngine(self.db)
        self.g.grant("RESEARCH", "web", "search", max_risk="READ")
        self.g.grant("ENGINEERING", "github", "create_pr", max_risk="WRITE_LOW")
        self.g.grant(
            "ENGINEERING", "github", "merge_production", max_risk="CONSEQUENTIAL"
        )
        self.g.grant(
            "OPS", "database", "delete_production_data", max_risk="DESTRUCTIVE"
        )
        self.g.grant("GROWTH", "ads", "spend", max_risk="CONSEQUENTIAL")
        self.g.set_budget("growth", 100.0, now=100)

    def tearDown(self):
        self.tmp.cleanup()

    def test_explicit_read_grant_allows(self):
        request = ActionRequest(
            "research-1", "RESEARCH", "web", "search", "READ"
        )
        self.assertEqual("ALLOW", self.g.authorize(request, now=110).decision)

    def test_unknown_action_is_default_deny(self):
        request = ActionRequest(
            "research-1", "RESEARCH", "web", "delete_everything", "READ"
        )
        decision = self.g.authorize(request, now=110)
        self.assertEqual("DENY", decision.decision)
        self.assertIn("no explicit grant", decision.reason)

    def test_risk_cannot_exceed_grant(self):
        request = ActionRequest(
            "engineering-1",
            "ENGINEERING",
            "github",
            "create_pr",
            "CONSEQUENTIAL",
        )
        decision = self.g.authorize(request, now=110)
        self.assertEqual("DENY", decision.decision)
        self.assertIn("exceeds grant", decision.reason)

    def test_consequential_action_requires_exact_approval(self):
        request = ActionRequest(
            "engineering-1",
            "ENGINEERING",
            "github",
            "merge_production",
            "CONSEQUENTIAL",
        )
        self.assertEqual(
            "REQUIRE_APPROVAL", self.g.authorize(request, now=110).decision
        )
        self.g.approve(request, approver_id="human-1", now=111)
        allowed = self.g.authorize(request, now=112)
        self.assertEqual("ALLOW", allowed.decision)
        self.assertIsNotNone(allowed.approval_id)
        self.assertEqual(
            "REQUIRE_APPROVAL", self.g.authorize(request, now=113).decision
        )

    def test_approval_cannot_be_replayed_for_modified_request(self):
        original = ActionRequest(
            "engineering-1",
            "ENGINEERING",
            "github",
            "merge_production",
            "CONSEQUENTIAL",
            metadata={"branch": "release-a"},
            request_id="req-fixed",
        )
        self.g.approve(original, approver_id="human-1", now=110)
        modified = ActionRequest(
            "engineering-1",
            "ENGINEERING",
            "github",
            "merge_production",
            "CONSEQUENTIAL",
            metadata={"branch": "release-b"},
            request_id="req-fixed",
        )
        self.assertEqual(
            "REQUIRE_APPROVAL", self.g.authorize(modified, now=111).decision
        )

    def test_destructive_action_is_never_auto_allowed(self):
        request = ActionRequest(
            "ops-1",
            "OPS",
            "database",
            "delete_production_data",
            "DESTRUCTIVE",
        )
        self.assertEqual(
            "REQUIRE_APPROVAL", self.g.authorize(request, now=110).decision
        )
        self.g.approve(request, approver_id="human-owner", now=111)
        self.assertEqual("ALLOW", self.g.authorize(request, now=112).decision)

    def test_paid_action_without_budget_is_denied(self):
        self.g.grant("AI", "provider", "call", max_risk="WRITE_LOW")
        request = ActionRequest(
            "ai-1", "AI", "provider", "call", "WRITE_LOW",
            estimated_cost_usd=1.0, budget_key="missing"
        )
        decision = self.g.authorize(request, now=110)
        self.assertEqual("DENY", decision.decision)
        self.assertIn("no configured budget", decision.reason)

    def test_budget_estimate_and_actual_spend_are_enforced(self):
        request = ActionRequest(
            "growth-1", "GROWTH", "ads", "spend", "CONSEQUENTIAL",
            estimated_cost_usd=70.0, budget_key="growth"
        )
        self.g.approve(request, approver_id="human-1", now=110)
        self.assertEqual("ALLOW", self.g.authorize(request, now=111).decision)
        self.g.record_spend(request, 70.0, receipt_ref="receipt-1", now=112)
        self.assertEqual(30.0, self.g.budget_status("growth")["remaining_usd"])

        next_request = ActionRequest(
            "growth-1", "GROWTH", "ads", "spend", "CONSEQUENTIAL",
            estimated_cost_usd=40.0, budget_key="growth"
        )
        self.assertEqual("DENY", self.g.authorize(next_request, now=113).decision)
        with self.assertRaises(PermissionError):
            self.g.record_spend(
                next_request, 40.0, receipt_ref="receipt-2", now=114
            )

    def test_kill_switch_overrides_even_read_grant(self):
        request = ActionRequest(
            "research-1", "RESEARCH", "web", "search", "READ"
        )
        self.g.set_kill_switch(True, actor_id="human-owner", now=110)
        decision = self.g.authorize(request, now=111)
        self.assertEqual("DENY", decision.decision)
        self.assertIn("kill switch", decision.reason)
        self.g.set_kill_switch(False, actor_id="human-owner", now=112)
        self.assertEqual("ALLOW", self.g.authorize(request, now=113).decision)

    def test_every_authorization_attempt_is_audited(self):
        request = ActionRequest(
            "research-1", "RESEARCH", "web", "search", "READ"
        )
        decision = self.g.authorize(request, now=110)
        rows = self.g.audit_rows(request.request_id)
        self.assertEqual(1, len(rows))
        self.assertEqual(decision.audit_id, rows[0]["audit_id"])
        self.assertEqual(request.sha256, rows[0]["request_sha256"])


if __name__ == "__main__":
    unittest.main()
