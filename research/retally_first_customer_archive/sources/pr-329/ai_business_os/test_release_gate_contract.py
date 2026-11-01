import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "repository-release-gate.yml"
COMMERCIAL_WORKFLOW = ROOT / ".github" / "workflows" / "freight-contracts.yml"
LOCAL_COMMERCIAL = "./.github/workflows/freight-contracts.yml"
PINNED_ACTION = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}")


def floating_references(text, *, allow_commercial=False):
    # This one same-repository call is bound to the caller commit by GitHub.
    # Never exempt arbitrary local paths or branch/tag-qualified references.
    refs = re.findall(r"\buses:\s*([^\s#]+)", text)
    return [ref for ref in refs if not (
        PINNED_ACTION.fullmatch(ref)
        or (allow_commercial and ref == LOCAL_COMMERCIAL)
    )]


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
        self.assertEqual([], floating_references(self.text, allow_commercial=True))
        # Inspect the called workflow too; its external actions stay SHA-pinned.
        called = COMMERCIAL_WORKFLOW.read_text(encoding="utf-8")
        self.assertTrue(re.findall(r"\buses:\s*([^\s#]+)", called))
        self.assertEqual([], floating_references(called))

    def test_only_the_exact_same_commit_commercial_call_is_allowed(self):
        source = f"    uses: {LOCAL_COMMERCIAL}\n"
        self.assertEqual([], floating_references(source, allow_commercial=True))
        self.assertEqual([LOCAL_COMMERCIAL], floating_references(source))
        for ref in (
            LOCAL_COMMERCIAL + "@main",
            LOCAL_COMMERCIAL + "@" + "a" * 40,
            "./.github/workflows/other.yml",
            "./.github/workflows/../freight-contracts.yml",
            "../.github/workflows/freight-contracts.yml",
        ):
            with self.subTest(ref=ref):
                self.assertEqual([ref], floating_references(
                    f"    uses: {ref}\n", allow_commercial=True
                ))

    def test_external_actions_still_require_complete_immutable_sha(self):
        pinned = "actions/checkout@" + "a" * 40
        self.assertEqual([], floating_references(f"uses: {pinned}\n"))
        for ref in (
            "actions/checkout@main", "actions/checkout@v4",
            "actions/checkout@" + "a" * 39, "actions/checkout",
            "docker://unreviewed:latest",
        ):
            with self.subTest(ref=ref):
                self.assertEqual([ref], floating_references(
                    f"uses: {ref}\n", allow_commercial=True
                ))

    def test_called_workflow_cannot_hide_a_floating_or_recursive_reference(self):
        called = COMMERCIAL_WORKFLOW.read_text(encoding="utf-8")
        for ref in ("actions/checkout@main", LOCAL_COMMERCIAL):
            with self.subTest(ref=ref):
                mutated = called + f"\n      - uses: {ref}\n"
                self.assertEqual([ref], floating_references(mutated))

    def test_all_five_release_lanes_are_required_by_final_gate(self):
        for job in (
            "ai-business-os",
            "freight",
            "freight-commercial",
            "recoveryworks",
            "technology-intelligence",
        ):
            self.assertRegex(self.text, rf"(?m)^\s{{6}}- {re.escape(job)}$")
        self.assertIn("if: always()", self.text)
        self.assertIn('test "$AI_BUSINESS_OS_RESULT" = "success"', self.text)
        self.assertIn('test "$FREIGHT_RESULT" = "success"', self.text)
        self.assertIn('test "$FREIGHT_COMMERCIAL_RESULT" = "success"', self.text)
        self.assertIn('test "$RECOVERYWORKS_RESULT" = "success"', self.text)
        self.assertIn('test "$TECHNOLOGY_INTELLIGENCE_RESULT" = "success"', self.text)


if __name__ == "__main__":
    unittest.main()
