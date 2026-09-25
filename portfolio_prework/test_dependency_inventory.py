import json
import unittest
from pathlib import Path


class DependencyInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = json.loads(Path("portfolio_prework/DEPENDENCY_INVENTORY.json").read_text(encoding="utf-8"))
        cls.snapshot = json.loads(Path("portfolio_prework/repository_snapshot.json").read_text(encoding="utf-8"))

    def test_exact_manifest_coverage(self):
        expected = {
            (repo["repo_id"], path)
            for repo in self.snapshot["repositories"]
            for path in repo.get("dependency_manifest_paths", [])
        }
        actual = {
            (repo["repo_id"], manifest["path"])
            for repo in self.inventory["repositories"]
            for manifest in repo.get("manifests", [])
        }
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 14)

    def test_per_repository_manifest_counts_match(self):
        expected = {
            repo["repo_id"]: len(repo.get("dependency_manifest_paths", []))
            for repo in self.snapshot["repositories"]
        }
        self.assertEqual(self.inventory["summary"]["manifest_count_by_repository"], expected)

    def test_manifest_blob_shas_are_recorded(self):
        for repo in self.inventory["repositories"]:
            for manifest in repo.get("manifests", []):
                sha = manifest.get("blob_sha", "")
                self.assertEqual(len(sha), 40)
                int(sha, 16)

    def test_abvm_floating_latest_is_explicit(self):
        repo = next(r for r in self.inventory["repositories"] if r["repo_id"] == "REPO-003")
        deps = repo["manifests"][0]["dependencies"]
        self.assertEqual({d["constraint"] for d in deps}, {"latest"})
        self.assertFalse(repo["lockfile_discovered"])

    def test_trading_lockfiles_present(self):
        repo = next(r for r in self.inventory["repositories"] if r["repo_id"] == "REPO-004")
        self.assertTrue(repo["lockfile_discovered"])
        kinds = {m["kind"] for m in repo["manifests"]}
        self.assertIn("pip-lock", kinds)
        self.assertEqual(repo["unique_locked_packages"], 19)

    def test_no_manifest_is_not_claimed_dependency_free(self):
        for repo_id in ["REPO-005", "REPO-006", "REPO-007"]:
            repo = next(r for r in self.inventory["repositories"] if r["repo_id"] == repo_id)
            self.assertEqual(repo["manifests"], [])
            joined = " ".join(repo["observations"])
            self.assertIn("No dependency manifest", joined)


if __name__ == "__main__":
    unittest.main()
