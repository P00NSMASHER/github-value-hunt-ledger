import json
import unittest
from pathlib import Path


class ArchitectureEvidenceBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = json.loads(Path("portfolio_prework/ARCHITECTURE_EVIDENCE_BUNDLE.json").read_text(encoding="utf-8"))
        cls.state = json.loads(Path("portfolio_prework/PORTFOLIO_BUILD_STATE.json").read_text(encoding="utf-8"))

    def test_expected_source_artifacts_present(self):
        paths = {item["path"] for item in self.bundle["source_artifacts"]}
        expected = {
            "portfolio_prework/portfolio_inventory.json",
            "portfolio_prework/PROJECT_ID_REGISTRY.json",
            "portfolio_prework/repository_snapshot.json",
            "portfolio_prework/repository_delta.json",
            "portfolio_prework/AUTONOMY_ACTION_TAXONOMY.json",
            "portfolio_prework/AUTONOMY_MATRIX.json",
            "portfolio_prework/WORKFLOW_INVENTORY.json",
            "portfolio_prework/TEST_SUITE_INVENTORY.json",
            "portfolio_prework/DEPENDENCY_INVENTORY.json",
            "portfolio_prework/PORTFOLIO_BUILD_STATE.json",
        }
        self.assertEqual(paths, expected)

    def test_source_blob_shas_are_valid(self):
        for item in self.bundle["source_artifacts"]:
            self.assertEqual(len(item["blob_sha"]), 40)
            int(item["blob_sha"], 16)

    def test_core_counts_match_prework(self):
        facts = self.bundle["verified_facts"]
        self.assertEqual(facts["connected_repository_count"], 7)
        self.assertEqual(facts["canonical_project_count"], 12)
        self.assertEqual(facts["repository_snapshot"]["workflow_count"], 47)
        self.assertEqual(facts["repository_snapshot"]["test_path_count"], 367)
        self.assertEqual(facts["repository_snapshot"]["dependency_manifest_count"], 14)

    def test_no_unbounded_act(self):
        self.assertEqual(self.bundle["verified_facts"]["autonomy"]["unbounded_act_project_count"], 0)
        self.assertEqual(self.bundle["verified_facts"]["autonomy"]["live_trading_or_broker_execution"], "PROHIBITED")

    def test_prework_declared_ready_for_step_zero(self):
        self.assertTrue(self.bundle["readiness"]["parallel_prework_complete"])
        self.assertTrue(self.bundle["readiness"]["ready_for_architecture_step_0"])

    def test_handoff_does_not_claim_commercial_validation(self):
        text = " ".join(self.bundle["non_claims_and_scope_limits"]).lower()
        self.assertIn("does not prove commercial traction", text)


if __name__ == "__main__":
    unittest.main()
