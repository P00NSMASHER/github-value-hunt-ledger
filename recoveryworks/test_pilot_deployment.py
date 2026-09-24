from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from recoveryworks.pilot_deployment import build_pilot_deployment_plan


class PilotDeploymentDryRunTests(unittest.TestCase):
    def setup_spec(self, root: Path) -> dict:
        inputs = root / "inputs"
        inputs.mkdir()
        for name in (
            "focus.csv",
            "meter.csv",
            "anomaly.csv",
            "reconciliation.csv",
            "savings.csv",
            "reviewed-rates.csv",
        ):
            (inputs / name).write_text("header\n", encoding="utf-8")
        return {
            "schema": 1,
            "deployment_id": "aws-pilot-001",
            "client_id": "client-1",
            "provider": "aws",
            "security": {
                "cloud_access_mode": "READ_ONLY",
                "recoveryos_provider_write_credentials": False,
                "remediation_execution_enabled": False,
                "external_actions_enabled": False,
                "private_state_required": True,
            },
            "period": {
                "start": "2026-08-01",
                "end": "2026-08-31",
                "exported_at": "2026-09-01T12:00:00Z",
            },
            "cletrics": {
                "focus_csv": "inputs/focus.csv",
                "meter_csv": "inputs/meter.csv",
                "anomaly_csv": "inputs/anomaly.csv",
                "reconciliation_csv": "inputs/reconciliation.csv",
                "savings_csv": "inputs/savings.csv",
                "release": "1.3.13",
                "commit": "a" * 40,
            },
            "recoveryos": {
                "rates_csv": "inputs/reviewed-rates.csv",
                "bundle_path": "private/cletrics-bundle.zip",
                "ledger_path": "private/recovery-ledger.json",
                "receipt_registry_path": "private/cletrics-receipts.json",
                "report_path": "private/cloud-recovery-report.json",
            },
        }

    def test_valid_read_only_aws_spec_produces_dry_run_plan(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = self.setup_spec(root)
            plan = build_pilot_deployment_plan(spec, base_dir=root)
            self.assertEqual(plan.provider, "aws")
            self.assertFalse(plan.provisioning_allowed)
            self.assertEqual(len(plan.commands), 2)
            self.assertIn("--focus", plan.commands[0].argv)
            self.assertIn("--dry-run-contract-only", plan.commands[1].argv)
            self.assertEqual(len(plan.proof_hash), 64)

    def test_write_credentials_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = self.setup_spec(root)
            spec["security"]["recoveryos_provider_write_credentials"] = True
            with self.assertRaisesRegex(ValueError, "must not receive provider write"):
                build_pilot_deployment_plan(spec, base_dir=root)

    def test_remediation_execution_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = self.setup_spec(root)
            spec["security"]["remediation_execution_enabled"] = True
            with self.assertRaisesRegex(ValueError, "must remain disabled"):
                build_pilot_deployment_plan(spec, base_dir=root)

    def test_missing_input_file_fails_before_any_plan(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = self.setup_spec(root)
            (root / "inputs" / "focus.csv").unlink()
            with self.assertRaisesRegex(ValueError, "does not exist"):
                build_pilot_deployment_plan(spec, base_dir=root)


if __name__ == "__main__":
    unittest.main()
