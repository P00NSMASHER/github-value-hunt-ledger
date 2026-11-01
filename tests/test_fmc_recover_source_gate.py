"""Run the actual embedded FMC recovery source-gate Python against synthetic API receipts.

No network, workflow dispatch, source artifact download, or repository mutation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/fmc-tariff-recover-merge.yml"
REPO = "P00NSMASHER/github-value-hunt-ledger"
SHA = "a" * 40


def gate_python() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    step = text.split("      - name: Verify source provenance, shard availability and duplicate success", 1)
    if len(step) != 2:
        raise AssertionError("FMC source gate step unavailable")
    body = step[1].split('          python3 - <<\'PY\' >> "$GITHUB_OUTPUT"\n', 1)
    if len(body) != 2 or "\n          PY" not in body[1]:
        raise AssertionError("FMC source gate Python block unavailable")
    embedded = body[1].split("\n          PY", 1)[0].splitlines()
    if not embedded or any(line and not line.startswith("          ") for line in embedded):
        raise AssertionError("Unexpected FMC source gate indentation")
    return "\n".join(line[10:] for line in embedded) + "\n"


class FmcSourceGateTests(unittest.TestCase):
    def run_case(
        self, *, duplicate=False, source_status="completed",
        source_branch="main", missing_shard=False, event="workflow_dispatch",
        automatic_sha=SHA,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = {
                "id": 123, "name": "FMC Tariff Rule Ledger",
                "repository": {"full_name": REPO}, "head_branch": source_branch,
                "head_sha": SHA, "status": source_status,
            }
            artifacts = [
                {"name": "fmc-shard-0", "expired": False},
                {"name": "fmc-shard-1", "expired": False},
            ]
            if missing_shard:
                artifacts.pop()
            recoveries = [{
                "id": 456, "display_title": "FMC recover source 123",
                "conclusion": "success" if duplicate else "failure",
            }]
            for name, value in (
                ("fmc-source-run.json", source),
                ("fmc-source-artifacts.json", {"artifacts": artifacts}),
                ("fmc-recovery-runs.json", {"workflow_runs": recoveries}),
            ):
                (root / name).write_text(json.dumps(value), encoding="utf-8")
            env = dict(os.environ)
            env.update({
                "RUNNER_TEMP": tmp, "SOURCE_RUN_ID": "123",
                "SOURCE_SHARD_COUNT": "2", "GITHUB_REPOSITORY": REPO,
                "EVENT_NAME": event, "AUTOMATIC_HEAD_SHA": automatic_sha,
                "MAIN_HEAD": SHA, "GITHUB_RUN_ID": "999",
            })
            return subprocess.run(
                [sys.executable, "-c", gate_python()],
                env=env, capture_output=True, text=True, check=False, timeout=10,
            )

    def test_completed_unique_source_proceeds(self):
        result = self.run_case()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("should_process=true", result.stdout)

    def test_completed_duplicate_is_skipped_without_name_error(self):
        result = self.run_case(duplicate=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("should_process=false", result.stdout)
        self.assertIn("already successfully recovered", result.stderr)

    def test_incomplete_source_rejected(self):
        result = self.run_case(source_status="in_progress")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Source run must have completed", result.stderr)

    def test_other_branch_source_rejected(self):
        result = self.run_case(source_branch="feature/untrusted")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("originate from this repository main", result.stderr)

    def test_missing_shard_rejected(self):
        result = self.run_case(missing_shard=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Source artifacts missing", result.stderr)

    def test_automatic_source_mismatch_rejected(self):
        result = self.run_case(event="workflow_run", automatic_sha="b" * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Event/source SHA mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
