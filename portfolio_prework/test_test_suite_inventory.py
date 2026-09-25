import json
import unittest
from pathlib import Path


class TestSuiteInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = json.loads(Path("portfolio_prework/TEST_SUITE_INVENTORY.json").read_text(encoding="utf-8"))
        cls.snapshot = json.loads(Path("portfolio_prework/repository_snapshot.json").read_text(encoding="utf-8"))

    def test_exact_test_path_coverage(self):
        expected = {
            (repo["repo_id"], path)
            for repo in self.snapshot["repositories"]
            for path in repo.get("test_paths", [])
        }
        actual = {
            (repo["repo_id"], path)
            for repo in self.inventory["repositories"]
            for path in repo.get("test_paths", [])
        }
        self.assertEqual(actual, expected)

    def test_total_count(self):
        expected = sum(len(repo.get("test_paths", [])) for repo in self.snapshot["repositories"])
        self.assertEqual(expected, 367)
        self.assertEqual(self.inventory["summary"]["total_test_paths"], expected)

    def test_per_repository_counts_match(self):
        expected = {
            repo["repo_id"]: len(repo.get("test_paths", []))
            for repo in self.snapshot["repositories"]
        }
        self.assertEqual(self.inventory["summary"]["test_paths_by_repository"], expected)

    def test_state_repo_has_no_tests(self):
        repo = next(r for r in self.inventory["repositories"] if r["repo_id"] == "REPO-006")
        self.assertEqual(repo["test_path_count"], 0)
        self.assertEqual(repo["test_paths"], [])

    def test_framework_metadata_present_for_tested_repos(self):
        for repo in self.inventory["repositories"]:
            if repo["test_path_count"]:
                self.assertTrue(repo["frameworks"], repo["repo_id"])
                self.assertTrue(repo["ci_entrypoints"], repo["repo_id"])


if __name__ == "__main__":
    unittest.main()
