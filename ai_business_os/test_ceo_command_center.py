import unittest

from ai_business_os.ceo_command_center import (
    ACTIVATE_GOAL_SQL,
    APPROVAL_DECIDE_SQL,
    CommandCenterError,
    CommandCenterOperator,
)
from ai_business_os.production_bridge import ProductionReadBridge


class FakeProduction:
    def __init__(self):
        self.fingerprint = "a" * 64
        self.writes = []
        self.approval = {
            "request_key": "approval-001",
            "agent_id": "agent-growth",
            "action_key": "gmail.send",
            "action_class": "EXTERNAL_WRITE",
            "intent_hash": "c" * 64,
            "status": "PENDING",
            "expires_at": "2026-10-01T00:00:00Z",
        }

    def read(self, sql, params):
        normalized = " ".join(sql.split()).lower()
        if "schema_fingerprint_v1()" in normalized:
            return [{"schema_fingerprint": self.fingerprint}]
        if "from ai_business_os_prod.businesses" in normalized:
            return [
                {"id": "b1", "slug": "starblox", "name": "StarBlox"},
                {"id": "b2", "slug": "capturebrief", "name": "CaptureBrief"},
            ]
        if "command_center_snapshots" in normalized:
            return [{
                "snapshot_key": "ceo",
                "snapshot_hash": "b" * 64,
                "payload": {"system": {"pending_approvals": 1}},
                "generated_at": "2026-09-24T23:00:00Z",
            }]
        if "approval_inbox" in normalized and "where status = %s" in normalized:
            return [{
                "id": "ap1",
                "request_key": self.approval["request_key"],
                "agent_id": self.approval["agent_id"],
                "action_key": self.approval["action_key"],
                "action_class": self.approval["action_class"],
                "title": "Send reply",
                "intent_hash": self.approval["intent_hash"],
                "predicted_risk": "MEDIUM_EXTERNAL_COMMITMENT",
                "expected_money_cents": 0,
                "status": self.approval["status"],
                "created_at": "2026-09-24T23:01:00Z",
                "expires_at": self.approval["expires_at"],
            }]
        if "approval_inbox" in normalized and "where request_key = %s" in normalized:
            return [dict(self.approval)]
        if "from ai_business_os_prod.agents" in normalized:
            roles = [
                ("agent-chief", "CHIEF_OF_STAFF"),
                ("agent-engineering", "ENGINEERING"),
                ("agent-finance", "FINANCE_ANALYTICS"),
                ("agent-growth", "GROWTH_SALES"),
                ("agent-product", "PRODUCT"),
                ("agent-research", "RESEARCH"),
            ]
            return [
                {"agent_id": agent, "role_key": role, "display_name": role, "mode": "LOW_RISK_AUTONOMY", "status": "ACTIVE"}
                for agent, role in roles
            ]
        if "portfolio_initiatives" in normalized:
            return [{
                "id": "i1",
                "initiative_key": "starblox",
                "name": "StarBlox",
                "business_id": "b1",
                "product_id": "p1",
                "owner_agent_id": "agent-chief",
                "status": "ACTIVE",
            }]
        if "portfolio_data_gaps" in normalized:
            return [{
                "id": "g1",
                "initiative_id": "i1",
                "metric_key": "remaining_effort_hours",
                "gap_type": "MISSING",
                "priority": 80,
                "recommended_source_type": "ANALYTICS/MANUAL_RECORD",
                "rationale": "Need remaining effort.",
                "resolved_at": None,
                "created_at": "2026-09-24T23:02:00Z",
            }]
        if "agent_goals" in normalized:
            return []
        raise AssertionError(f"unexpected read query: {normalized}")

    def write(self, sql, params):
        self.writes.append((sql, params))
        normalized = " ".join(sql.split()).lower()
        if "insert into ai_business_os_prod.agent_goals" in normalized:
            return [{
                "id": "goal-1",
                "agent_id": params[0],
                "goal_type": params[1],
                "title": params[2],
                "status": "PENDING",
                "priority": params[3],
                "constraints": params[4],
                "evidence_requirements": params[5],
            }]
        if "approval_decide" in normalized:
            status = "APPROVED" if params[1] == "APPROVE" else "REJECTED"
            self.approval["status"] = status
            return [{
                "request_key": params[0],
                "status": status,
                "decision_receipt_hash": "d" * 64,
            }]
        raise AssertionError(f"unexpected write query: {normalized}")


class CommandCenterOperatorTests(unittest.TestCase):
    def setUp(self):
        self.prod = FakeProduction()
        self.bridge = ProductionReadBridge(self.prod.read)
        self.operator = CommandCenterOperator(
            self.bridge,
            expected_schema_fingerprint="a" * 64,
        )

    def test_dashboard_combines_live_status_and_planning(self):
        view = self.operator.dashboard()
        self.assertEqual("a" * 64, view["schema_fingerprint"])
        self.assertEqual(1, view["command_center"]["payload"]["system"]["pending_approvals"])
        self.assertEqual(1, view["planning"]["summary"]["build_items"])

    def test_natural_language_build_objective_routes_to_engineering(self):
        proposal = self.operator.propose_objective(
            "Fix the StarBlox login bug and prepare the code change",
            requested_by="owner",
        )
        self.assertEqual("ENGINEERING", proposal["target_role"])
        self.assertEqual("BUILD", proposal["goal_type"])
        self.assertEqual(["starblox"], proposal["business_refs"])
        self.assertEqual("INTERNAL_WRITE", proposal["possible_action_class"])
        self.assertEqual("PROPOSED", proposal["status"])

    def test_consequential_objective_is_flagged_but_not_executed(self):
        proposal = self.operator.propose_objective(
            "Deploy the StarBlox update to production",
            requested_by="owner",
        )
        self.assertEqual("PRODUCTION_CHANGE", proposal["possible_action_class"])
        self.assertTrue(proposal["requires_human_approval_for_possible_action"])
        self.assertEqual([], self.prod.writes)

    def test_production_evidence_phrase_does_not_imply_production_change(self):
        proposal = self.operator.propose_objective(
            "Research current production evidence and identify the highest-priority verification task",
            requested_by="owner",
        )
        self.assertEqual("RESEARCH", proposal["target_role"])
        self.assertEqual("INTERNAL_WRITE", proposal["possible_action_class"])
        self.assertFalse(proposal["requires_human_approval_for_possible_action"])
        self.assertEqual([], self.prod.writes)

    def test_ambiguous_objective_routes_to_chief_of_staff(self):
        proposal = self.operator.propose_objective(
            "Figure out what I should focus on next",
            requested_by="owner",
        )
        self.assertEqual("CHIEF_OF_STAFF", proposal["target_role"])
        self.assertEqual("TRIAGE", proposal["goal_type"])

    def test_activation_creates_only_pending_internal_goal(self):
        proposal = self.operator.propose_objective(
            "Research StarBlox retention evidence",
            requested_by="owner",
        )
        activated = self.operator.activate_objective(
            proposal,
            human_principal="owner",
            write_execute=self.prod.write,
        )
        self.assertEqual("PENDING", activated["goal"]["status"])
        self.assertEqual(1, len(self.prod.writes))
        self.assertIn("insert into ai_business_os_prod.agent_goals", " ".join(self.prod.writes[0][0].split()).lower())

    def test_tampered_proposal_is_rejected_before_write(self):
        proposal = self.operator.propose_objective(
            "Research StarBlox retention evidence",
            requested_by="owner",
        )
        proposal["priority"] = 100
        with self.assertRaisesRegex(CommandCenterError, "hash mismatch"):
            self.operator.activate_objective(
                proposal,
                human_principal="owner",
                write_execute=self.prod.write,
            )
        self.assertEqual([], self.prod.writes)

    def test_activation_requires_same_human_principal(self):
        proposal = self.operator.propose_objective(
            "Research StarBlox retention evidence",
            requested_by="owner",
        )
        with self.assertRaisesRegex(CommandCenterError, "match the requesting human"):
            self.operator.activate_objective(
                proposal,
                human_principal="other-person",
                write_execute=self.prod.write,
            )

    def test_approval_decision_is_bound_to_exact_intent_hash(self):
        with self.assertRaisesRegex(CommandCenterError, "intent hash mismatch"):
            self.operator.decide_approval(
                request_key="approval-001",
                intent_hash="e" * 64,
                decision="APPROVE",
                human_principal="owner",
                reason="Reviewed exact request",
                read_execute=self.prod.read,
                write_execute=self.prod.write,
            )
        self.assertEqual([], self.prod.writes)

    def test_human_can_decide_exact_pending_approval(self):
        result = self.operator.decide_approval(
            request_key="approval-001",
            intent_hash="c" * 64,
            decision="APPROVE",
            human_principal="owner",
            reason="Reviewed exact request and intent",
            read_execute=self.prod.read,
            write_execute=self.prod.write,
        )
        self.assertEqual("APPROVED", result["receipt"]["status"])
        self.assertEqual(1, len(self.prod.writes))
        self.assertIn("approval_decide", self.prod.writes[0][0])

    def test_command_center_never_consumes_or_executes_approval(self):
        result = self.operator.decide_approval(
            request_key="approval-001",
            intent_hash="c" * 64,
            decision="REJECT",
            human_principal="owner",
            reason="Do not proceed",
            read_execute=self.prod.read,
            write_execute=self.prod.write,
        )
        self.assertEqual("REJECTED", result["receipt"]["status"])
        self.assertTrue(all("approval_consume" not in sql for sql, _ in self.prod.writes))


if __name__ == "__main__":
    unittest.main()
