import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "repository-release-gate.yml"


class RepositoryReleaseGateContractTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_runs_on_all_pull_requests_and_main_pushes_without_path_filters(self):
        self.assertIn("pull_request:", self.text)
        self.assertIn("push:", self.text)
        self.assertIn("branches: [main]", self.text)
        self.assertNotIn("paths:", self.text)
        self.assertNotIn("paths-ignore:", self.text)

    def test_release_gate_is_read_only_and_has_no_secret_dependency(self):
        self.assertIn("permissions:\n  contents: read", self.text)
        self.assertNotIn("contents: write", self.text)
        self.assertNotIn("secrets.", self.text)
        self.assertNotIn("pages: write", self.text)
        self.assertNotIn("id-token: write", self.text)

    def test_all_external_actions_are_immutably_pinned(self):
        refs = re.findall(r"\buses:\s*([^\s#]+)", self.text)
        self.assertTrue(refs)
        floating = [
            ref for ref in refs
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}", ref)
        ]
        self.assertEqual([], floating)

    def test_all_four_release_lanes_are_required_by_final_gate(self):
        for job in (
            "ai-business-os",
            "freight",
            "recoveryworks",
            "technology-intelligence",
        ):
            self.assertRegex(self.text, rf"(?m)^\s{{6}}- {re.escape(job)}$")
        self.assertIn("if: always()", self.text)
        self.assertIn('test "$AI_BUSINESS_OS_RESULT" = "success"', self.text)
        self.assertIn('test "$FREIGHT_RESULT" = "success"', self.text)
        self.assertIn('test "$RECOVERYWORKS_RESULT" = "success"', self.text)
        self.assertIn('test "$TECHNOLOGY_INTELLIGENCE_RESULT" = "success"', self.text)


if __name__ == "__main__":
    unittest.main()
