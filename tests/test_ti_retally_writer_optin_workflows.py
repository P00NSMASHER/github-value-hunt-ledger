"""Ensure all four GitHub evidence writers publish only through guarded PRs."""
from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]

class WriterModeTests(unittest.TestCase):
    def test_four_lanes_are_pr_only_and_fail_closed_without_enabled_switch(self):
        lanes={"public-repo-hunter.yml":"scout","catalog-append.yml":"catalog",
               "integrator-sync.yml":"integrator",
               "technology-intelligence.yml":"technology"}
        switches={"public-repo-hunter.yml":"RETALLY_SCOUT_PR_ENABLED",
                  "catalog-append.yml":"RETALLY_CATALOG_PR_ENABLED",
                  "integrator-sync.yml":"RETALLY_INTEGRATOR_PR_ENABLED",
                  "technology-intelligence.yml":"RETALLY_TECHNOLOGY_PR_ENABLED"}
        for file,lane in lanes.items():
            s=(ROOT/".github"/"workflows"/file).read_text()
            with self.subTest(file=file):
                self.assertIn(switches[file],s)
                self.assertNotIn("RETALLY_AUTOMATED_PR_WRITERS_ENABLED",s)
                self.assertIn('if [ "$PR_MODE" = "true" ]; then',s)
                self.assertIn("  submit-pr:",s)
                self.assertIn("--lane "+lane,s)
                self.assertIn("proposal_ready == 'true'",s)
                self.assertIn("refs/heads/main",s)
                self.assertIn("pull-requests: write",s)
                self.assertIn("actions: write",s)
                self.assertIn("direct-main publishing is prohibited",s)
                self.assertIn("exit 2",s)
                self.assertNotIn("git push origin HEAD:main",s)
                self.assertNotIn("\n            git push\n",s)

    def test_legacy_job_schedules_and_payloads_remain_present(self):
        files={".github/workflows/public-repo-hunter.yml":'7 4,16 * * *',
               ".github/workflows/catalog-append.yml":"catalog_append_payload.json",
               ".github/workflows/integrator-sync.yml":"integrator_sync_payload.md",
               ".github/workflows/technology-intelligence.yml":"--clean-untracked-on-rebuild"}
        for name,marker in files.items():
            with self.subTest(name=name):
                self.assertIn(marker,(ROOT/name).read_text())

    def test_automatic_main_protection_is_not_enabled_during_migration(self):
        d=json.loads((ROOT/".github/retally-main-ruleset.json").read_text())
        self.assertEqual(d["enforcement"],"disabled")
        policy=(ROOT/"recoveryworks/CODE_RELEASE_POLICY.md").read_text()
        self.assertIn("production_release=HOLD",policy)

    def test_real_module_entry_points_refuse_untrusted_context(self):
        import os
        import subprocess
        import sys
        env = os.environ.copy()
        for key in ("GITHUB_REPOSITORY", "GH_TOKEN", "GITHUB_EVENT_NAME",
                    "GITHUB_ACTOR", "GITHUB_REF"):
            env.pop(key, None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        cases = [
            ([sys.executable, "-m", "tools.retally_automated_pr_merge"],
             "RETALLY GUARDED MERGE HOLD:"),
            ([sys.executable, "-m", "tools.retally_automated_pr_proposal",
              "--lane", "scout",
              "--branch", "automation/retally-scout-39603064849-1",
              "--base-sha", "a" * 40,
              "--head-sha", "b" * 40],
             "RETALLY PROPOSAL HOLD:"),
        ]
        for command, expected in cases:
            with self.subTest(command=command[2]):
                result = subprocess.run(
                    command, cwd=ROOT, env=env, capture_output=True, text=True,
                    timeout=15, check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn(expected, result.stderr)
                self.assertNotIn("ModuleNotFoundError", result.stderr)

    def test_generated_writer_jobs_use_module_entry_points(self):
        controller = (ROOT / ".github/workflows/retally-generated-pr-merge.yml").read_text()
        self.assertIn("python -m tools.retally_automated_pr_merge", controller)
        self.assertNotIn("python tools/retally_automated_pr_merge.py", controller)
        for name in ("public-repo-hunter.yml", "catalog-append.yml",
                     "integrator-sync.yml", "technology-intelligence.yml"):
            workflow = (ROOT / ".github/workflows" / name).read_text()
            with self.subTest(name=name):
                self.assertIn("python -m tools.retally_automated_pr_proposal", workflow)
                self.assertNotIn("python tools/retally_automated_pr_proposal.py", workflow)

if __name__=="__main__":
    unittest.main()
