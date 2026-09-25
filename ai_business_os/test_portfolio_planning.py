import unittest

from ai_business_os.portfolio_planning import (
    PortfolioPlanningError,
    build_portfolio_plan,
)


class PortfolioPlanningTests(unittest.TestCase):
    def inputs(self):
        return {
            "agents": [
                {"agent_id": "agent-finance", "role_key": "FINANCE_ANALYTICS", "status": "ACTIVE"},
                {"agent_id": "agent-growth", "role_key": "GROWTH_SALES", "status": "ACTIVE"},
                {"agent_id": "agent-engineering", "role_key": "ENGINEERING", "status": "ACTIVE"},
                {"agent_id": "agent-research", "role_key": "RESEARCH", "status": "ACTIVE"},
            ],
            "initiatives": [
                {"id": "i1", "initiative_key": "capturebrief", "name": "CaptureBrief"},
                {"id": "i2", "initiative_key": "starblox", "name": "StarBlox"},
            ],
            "data_gaps": [
                {"id": "g1", "initiative_id": "i1", "metric_key": "cash_collected_30d", "gap_type": "PARTIAL_SCOPE", "priority": 100, "recommended_source_type": "BANK/GENERAL_LEDGER", "rationale": "Need complete cash scope."},
                {"id": "g2", "initiative_id": "i2", "metric_key": "remaining_effort_hours", "gap_type": "MISSING", "priority": 80, "recommended_source_type": "ANALYTICS/MANUAL_RECORD", "rationale": "Need remaining effort."},
                {"id": "g3", "initiative_id": "i2", "metric_key": "technical_capability_gap", "gap_type": "MISSING", "priority": 70, "recommended_source_type": "PUBLIC_GITHUB", "rationale": "Need a reusable implementation."},
            ],
            "open_goals": [
                {"id": "goal-finance", "agent_id": "agent-finance", "goal_type": "OUTCOME_VERIFICATION", "title": "Verify revenue-loop cash outcomes", "constraints": {}, "evidence_requirements": ["authoritative financial record"]},
            ],
        }

    def test_routes_financial_gap_to_finance_verification(self):
        plan = build_portfolio_plan(
            schema_fingerprint="a" * 64,
            command_center_snapshot_hash="b" * 64,
            planning_inputs=self.inputs(),
        )
        item = next(x for x in plan["work_items"] if x["metric_key"] == "cash_collected_30d")
        self.assertEqual("VERIFY", item["work_kind"])
        self.assertEqual("FINANCE_ANALYTICS", item["owner_role"])
        self.assertEqual("agent-finance", item["owner_agent_id"])
        self.assertFalse(item["hunter_eligible"])
        self.assertIn("goal-finance", item["overlap_goal_ids"])

    def test_build_gap_is_planning_only_and_has_no_write_authority(self):
        plan = build_portfolio_plan(
            schema_fingerprint="a" * 64,
            command_center_snapshot_hash=None,
            planning_inputs=self.inputs(),
        )
        item = next(x for x in plan["work_items"] if x["metric_key"] == "remaining_effort_hours")
        self.assertEqual("BUILD", item["work_kind"])
        self.assertEqual("agent-engineering", item["owner_agent_id"])
        self.assertTrue(item["planning_only"])
        self.assertFalse(item["external_write_allowed"])

    def test_hunters_receive_only_explicit_public_technical_sources(self):
        plan = build_portfolio_plan(
            schema_fingerprint="a" * 64,
            command_center_snapshot_hash=None,
            planning_inputs=self.inputs(),
        )
        self.assertEqual(1, len(plan["hunter_queue"]))
        self.assertEqual("technical_capability_gap", plan["hunter_queue"][0]["metric_key"])
        self.assertEqual("PUBLIC_GITHUB", plan["hunter_queue"][0]["required_source_type"])

    def test_finance_crm_and_manual_gaps_do_not_enter_hunter_queue(self):
        plan = build_portfolio_plan(
            schema_fingerprint="a" * 64,
            command_center_snapshot_hash=None,
            planning_inputs=self.inputs(),
        )
        nontechnical = [x for x in plan["work_items"] if x["metric_key"] != "technical_capability_gap"]
        self.assertTrue(all(not x["hunter_eligible"] for x in nontechnical))

    def test_plan_is_deterministic(self):
        kwargs = {
            "schema_fingerprint": "a" * 64,
            "command_center_snapshot_hash": "b" * 64,
            "planning_inputs": self.inputs(),
        }
        self.assertEqual(build_portfolio_plan(**kwargs)["plan_hash"], build_portfolio_plan(**kwargs)["plan_hash"])

    def test_unknown_initiative_fails_closed(self):
        data = self.inputs()
        data["data_gaps"][0]["initiative_id"] = "missing"
        with self.assertRaisesRegex(PortfolioPlanningError, "unknown initiative"):
            build_portfolio_plan(
                schema_fingerprint="a" * 64,
                command_center_snapshot_hash=None,
                planning_inputs=data,
            )

    def test_missing_required_agent_role_fails_closed(self):
        data = self.inputs()
        data["agents"] = [x for x in data["agents"] if x["role_key"] != "FINANCE_ANALYTICS"]
        with self.assertRaisesRegex(PortfolioPlanningError, "no active agent"):
            build_portfolio_plan(
                schema_fingerprint="a" * 64,
                command_center_snapshot_hash=None,
                planning_inputs=data,
            )


if __name__ == "__main__":
    unittest.main()
