import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from ai_business_os.hunter_bridge import compile_hunter_seeds
from ti_assignment_projection import project_ti_assignment


class BusinessOsHunterIntegrationTests(unittest.TestCase):
    def _seed(self):
        plan = {
            "plan_hash": "a" * 64,
            "hunter_queue": [
                {
                    "work_id": "portfolio-plan:technical-gap",
                    "initiative_id": "initiative-1",
                    "initiative_key": "starblox",
                    "initiative_name": "StarBlox",
                    "metric_key": "runtime_auth_adapter",
                    "gap_type": "MISSING",
                    "priority": 92,
                    "hunter_eligible": True,
                    "required_source_type": "PUBLIC_GITHUB",
                    "acceptance_target": "Find a tested public implementation with exact revision evidence.",
                    "planning_only": True,
                    "external_write_allowed": False,
                    "human_approval_required_for_external_write": True,
                }
            ],
        }
        return compile_hunter_seeds(plan)[0]

    def test_business_os_provenance_survives_assignment_projection(self):
        seed = self._seed()
        candidate = {
            "work_item_id": "WORK:bos:test",
            "work_revision_sha256": None,
            "work_identity_payload": None,
            "work_kind": "business_os_gap",
            "work_action": "search",
            "query_recipe_id": None,
            "query_anchors": seed["query_anchors"],
            "required_signatures": [],
            "exclude_domains": [],
            "source_id": seed["source_id"],
            "title": seed["title"],
            "measurement_contract_version": None,
            "authorization_basis": "ai_business_os_portfolio_gap",
            "final_score": 92,
            "score_components": {"business_os_priority": 92},
            "strategy_id": None,
            "search_objective_id": None,
            "capability_ids": [],
            "experiment_ids": [],
            "coverage_gap_ids": [],
            "adjacency_root": None,
            "instructions": seed["instructions"],
            "business_os_plan_hash": seed["business_os_plan_hash"],
            "business_os_work_id": seed["business_os_work_id"],
            "business_os_seed_hash": seed["business_os_seed_hash"],
            "business_os_initiative_key": seed["initiative_key"],
            "business_os_metric_key": seed["metric_key"],
            "business_os_gap_type": seed["gap_type"],
            "business_os_required_source_type": seed["required_source_type"],
        }
        assignment = project_ti_assignment(
            candidate,
            {
                "assignment_id": "ASSIGN:test:slot-09",
                "allocator_generation_id": "ALLOCGEN:test",
                "portfolio_policy_generation_id": "PORTFOLIO:test",
                "slot_id": "SLOT-09",
                "slot_role": "coverage",
                "slot_label": "Blind-spot / transfer exploration",
            },
        )
        for key in (
            "business_os_plan_hash",
            "business_os_work_id",
            "business_os_seed_hash",
            "business_os_initiative_key",
            "business_os_metric_key",
            "business_os_gap_type",
            "business_os_required_source_type",
        ):
            self.assertEqual(candidate[key], assignment[key])

    def test_only_slot_09_accepts_business_os_gap(self):
        policy = json.loads(
            (ROOT / "intelligence" / "allocator_policy.json").read_text(encoding="utf-8")
        )
        accepted = [
            slot["slot_id"]
            for slot in policy["slots"]
            if "business_os_gap" in slot.get("accepts", [])
        ]
        self.assertEqual(["SLOT-09"], accepted)
        for slot_id in ("SLOT-07", "SLOT-08"):
            slot = next(slot for slot in policy["slots"] if slot["slot_id"] == slot_id)
            self.assertNotIn("business_os_gap", slot["accepts"])


if __name__ == "__main__":
    unittest.main()
