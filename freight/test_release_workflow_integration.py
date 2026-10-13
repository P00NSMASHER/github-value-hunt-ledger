"""Keep commercial proof tests inside the existing repository release decision.

The shell probes execute only the release aggregator, with synthetic job results.
They neither run a customer workflow nor establish deployment or financial authority.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
RELEASE = WORKFLOWS / "repository-release-gate.yml"
COMMERCIAL = WORKFLOWS / "freight-contracts.yml"
RESULTS = {
    "ai-business-os": "AI_BUSINESS_OS_RESULT",
    "freight": "FREIGHT_RESULT",
    "freight-commercial": "FREIGHT_COMMERCIAL_RESULT",
    "recoveryworks": "RECOVERYWORKS_RESULT",
    "technology-intelligence": "TECHNOLOGY_INTELLIGENCE_RESULT",
}


def job_block(source: str, job: str) -> str:
    """Extract one repository-style, two-space-indented job, not a YAML parser."""
    match = re.search(
        rf"(?ms)^  {re.escape(job)}:[ \t]*\n.*?(?=^  [^ \n]|\Z)", source
    )
    if match is None:
        raise AssertionError(f"Required workflow job missing: {job}")
    return match.group(0)


def aggregator_script(source: str) -> str:
    block = job_block(source, "release-gate")
    match = re.search(r"(?m)^        run: \|\n((?:          .*\n)+)", block)
    if match is None:
        raise AssertionError("Release aggregator shell block missing")
    return textwrap.dedent(match.group(1))


class ReleaseWorkflowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = RELEASE.read_text(encoding="utf-8")
        cls.commercial = COMMERCIAL.read_text(encoding="utf-8")

    def test_commercial_workflow_accepts_same_revision_calls(self):
        triggers = self.commercial.split("\npermissions:", 1)[0]
        self.assertIn("\n  workflow_call:\n", triggers)
        self.assertIn("\n  push:\n", triggers)
        self.assertIn("\n  pull_request:\n", triggers)

    def test_commercial_lane_reuses_local_workflow_without_ref_override(self):
        lane = job_block(self.release, "freight-commercial")
        self.assertIn("uses: ./.github/workflows/freight-contracts.yml\n", lane)
        for forbidden in ("@main", "@", "if:", "continue-on-error:", "steps:", "secrets:"):
            self.assertNotIn(forbidden, lane)
        # Default checkout inside the called workflow uses the caller context.
        self.assertNotRegex(self.commercial, r"(?m)^\s+ref:")

    def test_release_gate_waits_for_commercial_and_all_original_lanes(self):
        gate = job_block(self.release, "release-gate")
        needs = re.findall(r"(?m)^      - ([a-z-]+)$", gate)
        self.assertCountEqual(needs, RESULTS)

    def test_release_gate_binds_every_result_to_its_dependency(self):
        gate = job_block(self.release, "release-gate")
        for job, variable in RESULTS.items():
            with self.subTest(job=job):
                self.assertIn(f"{variable}: ${{{{ needs.{job}.result }}}}", gate)

    def test_release_gate_still_runs_after_upstream_failure(self):
        gate = job_block(self.release, "release-gate")
        self.assertIn("\n    if: always()\n", gate)
        self.assertNotIn("continue-on-error:", gate)
        self.assertIn("\n        shell: bash\n", gate)
        self.assertIn("set -euo pipefail", aggregator_script(self.release))

    def run_gate(self, results):
        bash = shutil.which("bash")
        self.assertIsNotNone(bash, "Bash is required to verify the actual release shell")
        # Do not inherit job-result values, shell startup files, or credentials.
        env = {"PATH": os.defpath, **results}
        return subprocess.run(
            [bash, "--noprofile", "--norc", "-c", aggregator_script(self.release)],
            env=env, capture_output=True, text=True, timeout=5, check=False,
        )

    def test_release_gate_accepts_all_five_successes(self):
        result = self.run_gate(dict.fromkeys(RESULTS.values(), "success"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Repository release gate passed.", result.stdout)

    def test_release_gate_rejects_every_non_success_for_every_lane(self):
        for variable in RESULTS.values():
            for status in ("failure", "cancelled", "skipped", "", "neutral", "timed_out", "queued", "success "):
                with self.subTest(variable=variable, status=status):
                    results = dict.fromkeys(RESULTS.values(), "success")
                    results[variable] = status
                    self.assertNotEqual(self.run_gate(results).returncode, 0)

    def test_release_gate_rejects_missing_results(self):
        for variable in RESULTS.values():
            with self.subTest(variable=variable):
                results = dict.fromkeys(RESULTS.values(), "success")
                del results[variable]
                self.assertNotEqual(self.run_gate(results).returncode, 0)

    def test_reuse_stays_read_only_without_secret_inheritance(self):
        lane = job_block(self.release, "freight-commercial")
        self.assertIn("\n    permissions:\n      contents: read\n", lane)
        for source in (self.release, self.commercial):
            self.assertIn("\npermissions:\n  contents: read\n", source)
            self.assertNotIn("secrets: inherit", source)
            self.assertNotIn("contents: write", source)
            self.assertNotIn("pull_request_target:", source)

    def test_existing_commercial_proofs_and_customer_holds_are_preserved(self):
        for required in (
            "python -m pytest -q freight/test_contracts.py",
            "freight/test_recovery_evidence_pack.py",
            "freight/test_first_customer_rehearsal.py",
            "python -m freight.synthetic_rehearsal --first-customer",
            'assert p["release_policy"]=="REVIEW_ONLY_NO_CUSTOMER_DATA"',
            'assert not p["all_customer_pilot_gates_ready"]',
            "python freight/rights_evidence.py --stage pilot --expect CLEAR",
            "timeout-minutes: 10",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.commercial)

    def test_regressions_are_discovered_by_the_required_freight_lane(self):
        lane = job_block(self.release, "freight")
        self.assertIn('python -m unittest discover -s freight -p "test_*.py" -v', lane)
        self.assertNotIn("continue-on-error:", lane)


if __name__ == "__main__":
    unittest.main()
