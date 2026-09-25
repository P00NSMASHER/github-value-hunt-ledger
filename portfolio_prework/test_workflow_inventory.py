import json
import unittest
from pathlib import Path


class WorkflowInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = json.loads(Path("portfolio_prework/WORKFLOW_INVENTORY.json").read_text(encoding="utf-8"))
        cls.snapshot = json.loads(Path("portfolio_prework/repository_snapshot.json").read_text(encoding="utf-8"))

    def test_workflow_count_matches_snapshot(self):
        expected = sum(len(repo.get("workflow_paths", [])) for repo in self.snapshot["repositories"])
        self.assertEqual(len(self.inventory["workflows"]), expected)
        self.assertEqual(expected, 47)

    def test_every_snapshot_workflow_is_present_exactly_once(self):
        expected = {
            (repo["repo_id"], path)
            for repo in self.snapshot["repositories"]
            for path in repo.get("workflow_paths", [])
        }
        actual = {(item["repo_id"], item["path"]) for item in self.inventory["workflows"]}
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), len(self.inventory["workflows"]))

    def test_every_workflow_has_trigger_and_permissions_record(self):
        for item in self.inventory["workflows"]:
            self.assertTrue(item["triggers"], item["path"])
            self.assertTrue(item["permissions"], item["path"])

    def test_no_pull_request_target_detected(self):
        self.assertEqual(self.inventory["summary"]["pull_request_target_count"], 0)

    def test_write_or_deploy_workflows_are_flagged(self):
        flagged = [
            item for item in self.inventory["workflows"]
            if "write_permission" in item["risk_markers"] or "deployment_or_pages" in item["risk_markers"]
        ]
        self.assertEqual(len(flagged), self.inventory["summary"]["write_capable_or_deploy_workflows"])
        self.assertGreater(len(flagged), 0)

    def test_state_repo_has_no_workflows(self):
        self.assertEqual(self.inventory["summary"]["workflows_by_repository"]["REPO-006"], 0)


if __name__ == "__main__":
    unittest.main()
