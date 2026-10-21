"""Offline contract for zero-review main protection. Never mutates GitHub."""
from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".github" / "retally-main-ruleset.json"
GATE = ROOT / ".github" / "workflows" / "repository-release-gate.yml"


class MainBranchRulesetTests(unittest.TestCase):
    def setUp(self):
        self.ruleset = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.rules = {r["type"]: r for r in self.ruleset["rules"]}

    def test_scope_and_zero_bypass_exact_default_branch(self):
        self.assertEqual(self.ruleset["target"], "branch")
        self.assertEqual(self.ruleset["enforcement"], "disabled")
        self.assertEqual(self.ruleset["bypass_actors"], [])
        self.assertEqual(self.ruleset["conditions"]["ref_name"], {
            "include": ["~DEFAULT_BRANCH"], "exclude": [],
        })
        self.assertEqual(set(self.rules), {
            "deletion", "non_fast_forward", "pull_request", "required_status_checks",
        })

    def test_pull_requests_are_required_but_no_human_reviews(self):
        params = self.rules["pull_request"]["parameters"]
        self.assertEqual(params["required_approving_review_count"], 0)
        for field in ("dismiss_stale_reviews_on_push", "require_code_owner_review",
                      "require_last_push_approval", "required_review_thread_resolution"):
            self.assertIs(params[field], False)
        self.assertEqual(set(params["allowed_merge_methods"]), {"merge", "squash", "rebase"})

    def test_required_status_is_unique_aggregate_from_github_actions(self):
        params = self.rules["required_status_checks"]["parameters"]
        self.assertIs(params["strict_required_status_checks_policy"], True)
        self.assertEqual(params["required_status_checks"], [
            {"context": "release-gate", "integration_id": 15368},
        ])
        # Path-filtered RecoveryWorks and Portfolio CI jobs cannot be globally
        # required: they are absent on unrelated pull requests.
        workflows = ROOT / ".github" / "workflows"
        matching = []
        for path in list(workflows.glob("*.yml")) + list(workflows.glob("*.yaml")):
            body = path.read_text(encoding="utf-8")
            if re.search(r"(?m)^  release-gate:\s*$", body):
                matching.append(path.name)
        self.assertEqual(matching, ["repository-release-gate.yml"])

    def test_release_gate_aggregates_four_nonoptional_ci_lanes(self):
        body = GATE.read_text(encoding="utf-8")
        self.assertRegex(body, r"(?m)^  pull_request:\s*$")
        self.assertRegex(body, r"(?m)^  push:\s*$")
        # The release gate must not have a global path filter.
        trigger = body.split("permissions:", 1)[0]
        self.assertNotIn("paths:", trigger)
        self.assertRegex(body, r"(?m)^  release-gate:\s*$")
        self.assertIn("    if: always()", body)
        for name in ("ai-business-os", "freight", "recoveryworks",
                     "technology-intelligence"):
            self.assertIn("      - " + name, body)
        for var in ("AI_BUSINESS_OS_RESULT", "FREIGHT_RESULT",
                    "RECOVERYWORKS_RESULT", "TECHNOLOGY_INTELLIGENCE_RESULT"):
            self.assertIn('test "$' + var + '" = "success"', body)

    def test_activation_is_blocked_by_existing_direct_main_writers(self):
        # A PR-only ruleset would strand scheduled writers still pushing into
        # main. Keep the template disabled until every writer is migrated.
        direct = []
        writer_files = {
            "catalog-append.yml": "git push",
            "integrator-sync.yml": "git push",
            "public-repo-hunter.yml": "git push origin HEAD:main",
        }
        for name, marker in writer_files.items():
            body = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
            if marker in body:
                direct.append(name)
        ti = (ROOT / "tools" / "ti_persist_generated.py").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "technology-intelligence.yml").read_text(
            encoding="utf-8"
        )
        if '"HEAD:main"' in ti and "ti_persist_generated.py" in workflow:
            direct.append("technology-intelligence.yml")
        if self.ruleset["enforcement"] == "active":
            self.assertEqual(direct, [], "Direct-main writers must migrate before protection")
        # Deliberately do not assert that any writer must remain; migrating
        # them is a prerequisite for switching the manifest to active.

    def test_customer_release_remains_a_separate_hold(self):
        policy = (ROOT / "recoveryworks" / "CODE_RELEASE_POLICY.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("production_release=HOLD", policy)
        self.assertIn("customer authorization", policy.lower())
        self.assertIn("without a required separate human", policy.lower())


if __name__ == "__main__":
    unittest.main()
