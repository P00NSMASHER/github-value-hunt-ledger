"""CI contract: all four RETALLY scheduled writers use guarded PRs only."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
LANES = {
    "public-repo-hunter.yml": "scout",
    "catalog-append.yml": "catalog",
    "integrator-sync.yml": "integrator",
    "technology-intelligence.yml": "technology",
}

class WriterModeTests(unittest.TestCase):
    def test_all_four_lanes_are_pr_only_not_variable_dependent(self):
        for filename, lane in LANES.items():
            workflow = (ROOT / ".github" / "workflows" / filename).read_text()
            with self.subTest(filename=filename):
                self.assertIn("  submit-pr:", workflow)
                self.assertIn("--lane " + lane, workflow)
                self.assertIn("proposal_ready == 'true'", workflow)
                self.assertIn("pull-requests: write", workflow)
                self.assertIn("actions: write", workflow)
                self.assertIn("persist-credentials: false", workflow)
                self.assertIn("refs/heads/main", workflow)
                self.assertNotIn("PR_MODE", workflow)
                self.assertNotIn("_PR_ENABLED", workflow)
                self.assertNotIn("git push origin HEAD:main", workflow)
                self.assertNotRegex(workflow, r"(?m)^\s+git push\s*$")
                self.assertNotIn("git push --force", workflow)
                if lane == "technology":
                    self.assertIn("--proposal-branch", workflow)
                else:
                    self.assertIn('git push origin "HEAD:refs/heads/$BRANCH"', workflow)

    def test_original_event_triggers_and_work_remain(self):
        checks = {
            ".github/workflows/public-repo-hunter.yml": "7 4,16 * * *",
            ".github/workflows/catalog-append.yml": "catalog_append_payload.json",
            ".github/workflows/integrator-sync.yml": "integrator_sync_payload.md",
            ".github/workflows/technology-intelligence.yml": "--clean-untracked-on-rebuild",
        }
        for path, marker in checks.items():
            with self.subTest(path=path):
                self.assertIn(marker, (ROOT / path).read_text())
        technology=(ROOT/".github/workflows/technology-intelligence.yml").read_text()
        self.assertIn("github.actor != 'github-actions[bot]'", technology)

    def test_actions_cli_without_proposal_cannot_write_main(self):
        env = dict(os.environ)
        env["GITHUB_ACTIONS"] = "true"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [sys.executable, "tools/ti_persist_generated.py", "--max-attempts", "1"],
            cwd=ROOT, env=env, capture_output=True, text=True,
            timeout=15, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("GitHub Actions refuses direct-main persistence", result.stderr)

    def test_ruleset_activation_remains_separate_from_code_update(self):
        manifest = json.loads((ROOT / ".github/retally-main-ruleset.json").read_text())
        self.assertEqual(manifest["enforcement"], "disabled")
        checks = manifest["rules"][-1]["parameters"]["required_status_checks"]
        self.assertEqual(checks, [{"context": "release-gate", "integration_id": 15368}])
        policy = (ROOT / "recoveryworks/CODE_RELEASE_POLICY.md").read_text()
        self.assertIn("production_release=HOLD", policy)

if __name__ == "__main__":
    unittest.main()
