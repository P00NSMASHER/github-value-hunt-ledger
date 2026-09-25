import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"ai_business_os"/"EXTERNAL_OUTCOME_LEARNING_V1.json"
COMPLETE=ROOT/"REPOSITORY_PLAN_COMPLETE_V1.json"
MIGRATIONS=ROOT/"supabase"/"migrations"/"ai_business_os"/"manifest.json"


class ExternalOutcomeLearningContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(CONTRACT.read_text())
        cls.complete=json.loads(COMPLETE.read_text())
        cls.migrations=json.loads(MIGRATIONS.read_text())

    def test_only_independently_verified_outcomes_drive_learning(self):
        self.assertEqual(["AUDITOR_REDTEAM","FINANCE_ANALYTICS"],self.data["verifier_roles"])
        self.assertIn("creator and verifier must be different active agents",self.data["hard_invariants"])
        self.assertIn("repository activity is never an external outcome",self.data["hard_invariants"])

    def test_negative_outcomes_are_first_class_learning(self):
        policy=self.data["reward_policy"]
        self.assertLess(policy["BUYER_NEGATIVE_REPLY"],0)
        self.assertLess(policy["EXPLICIT_NO_VALUE"],0)
        self.assertGreater(policy["COLLECTED_REVENUE"],0)

    def test_canary_proved_outcome_to_allocator_to_memory_path(self):
        c=self.data["canary"]
        self.assertTrue(c["self_verification_rejected"])
        self.assertTrue(c["pre_attribution_memory_rejected"])
        self.assertTrue(c["verified_positive_outcomes_made_capturebrief_allocation_eligible"])
        self.assertTrue(c["collected_revenue_flowed_to_allocator"])
        self.assertTrue(c["fully_attributed_collected_revenue_became_verified_positive_memory"])
        self.assertEqual(0,c["persistent_synthetic_outcomes"])
        self.assertEqual(0,c["persistent_synthetic_memory_observations"])

    def test_real_state_is_still_fail_closed(self):
        state=self.data["current_real_state"]
        self.assertEqual(0,state["verified_external_outcomes"])
        self.assertEqual(0,state["learned_external_outcomes"])
        for key,value in state.items():
            if key.endswith("_allocation_eligible"):
                self.assertFalse(value)

    def test_all_step10_production_migrations_are_archived(self):
        names={x["name"] for x in self.migrations["migrations"]}
        expected={
            "create_ai_business_os_verified_external_outcomes_v1",
            "wire_ai_business_os_outcomes_to_allocator_memory_v1",
            "add_ai_business_os_opportunity_first_contact_v1",
            "fix_ai_business_os_external_outcome_snapshot_ordering_v1",
            "integrate_ai_business_os_external_outcomes_command_center_v1",
            "add_ai_business_os_external_outcomes_to_ceo_snapshot_v1",
        }
        self.assertTrue(expected <= names)
        self.assertEqual(
            self.data["live_schema_fingerprint_sha256"],
            self.migrations["live_schema_fingerprint_sha256"],
        )

    def test_repository_plan_is_ten_of_ten_without_claiming_commercial_success(self):
        self.assertEqual("COMPLETE_10_OF_10",self.complete["status"])
        self.assertEqual(0,self.complete["operating_truth"]["real_verified_external_outcomes"])
        self.assertIn("commercial evidence must now be earned",self.complete["operating_truth"]["statement"])


if __name__=="__main__":
    unittest.main()
