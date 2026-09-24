from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from recoveryworks.multicloud_executive import (
    build_multicloud_executive_rollup,
    write_multicloud_executive_rollup,
)
from recoveryworks.multicloud_orchestration import run_multicloud_orchestration
from recoveryworks.private_io import private_permissions_verified
from recoveryworks.test_multicloud_execution import executable_job


class MultiCloudExecutiveRollupTests(unittest.TestCase):
    def execution(self, root: Path):
        return run_multicloud_orchestration(
            {
                "schema": 1,
                "client_id": "client-multi-exec",
                "currency": "USD",
                "jobs": [
                    executable_job(root, "aws", 1000),
                    executable_job(root, "azure", 2000),
                    executable_job(root, "gcp", 3000),
                ],
            },
            base_dir=root,
        )

    def test_rollup_aggregates_only_allowlisted_same_semantic_categories(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rollup = build_multicloud_executive_rollup(self.execution(root))
            self.assertEqual(rollup.comparable_totals["validated_cents"], 3000)
            self.assertEqual(
                rollup.comparable_totals[
                    "estimated_savings_opportunity_cents"
                ],
                6000,
            )
            self.assertFalse(rollup.provider_authority_merged)
            self.assertFalse(rollup.provider_evidence_merged)
            self.assertFalse(rollup.provider_findings_merged)
            self.assertIn("individual findings", rollup.excluded_from_rollup)
            self.assertNotIn("cases", rollup.comparable_totals)

    def test_rollup_rejects_tampered_provider_report(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            execution = self.execution(root)
            report = Path(execution.provider_runs[0].assurance_report_path)
            payload = json.loads(report.read_text(encoding="utf-8"))
            payload["currency"] = "EUR"
            report.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no longer matches|proof hash"):
                build_multicloud_executive_rollup(execution)

    def test_rollup_outputs_are_private(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rollup = build_multicloud_executive_rollup(self.execution(root))
            json_path = root / "private" / "executive.json"
            md_path = root / "private" / "executive.md"
            write_multicloud_executive_rollup(
                rollup,
                json_path=json_path,
                markdown_path=md_path,
            )
            self.assertTrue(private_permissions_verified(json_path))
            self.assertTrue(private_permissions_verified(md_path))


if __name__ == "__main__":
    unittest.main()
