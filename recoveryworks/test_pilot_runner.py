from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recoveryworks.pilot_runner import run_local_pilot
from recoveryworks.private_io import private_permissions_verified


class LocalPilotRunnerTests(unittest.TestCase):
    def build_spec(self, root: Path) -> dict:
        inputs = root / "inputs"
        inputs.mkdir()
        (inputs / "focus.csv").write_text(
            "ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
            "BilledCost,BillingCurrency,ResourceId\n"
            "AWS,acct-1,compute,2026-08-31T00:00:00Z,40.00,USD,i-1\n",
            encoding="utf-8",
        )
        (inputs / "meter.csv").write_text(
            "Meter_Record_ID,Usage_Units,ResourceId,ServiceName,UsageDate\n"
            "M-1,10,i-1,compute,2026-08-31\n",
            encoding="utf-8",
        )
        (inputs / "savings.csv").write_text(
            "Signal_ID,Detected_At,Provider,Account_ID,Service_ID,Resource_ID,"
            "Region,Savings_Category,Estimated_Savings,Confidence,Recommendation,"
            "Remediation_Action\n"
            "S-1,2026-09-01T00:00:00Z,aws,acct-1,compute,i-1,us-east-1,"
            "rightsize,25.00,0.8,Review and downsize,resize_instance\n",
            encoding="utf-8",
        )
        (inputs / "rates.csv").write_text(
            "Counterparty,Service_ID,Effective_From,Effective_To,Fixed_Fee,"
            "Included_Units,Unit_Rate\n"
            "AWS,compute,2026-01-01,,10.00,0,2.00\n",
            encoding="utf-8",
        )
        return {
            "schema": 1,
            "deployment_id": "pilot-test",
            "client_id": "client-1",
            "currency": "USD",
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
                "exported_at": "2026-09-01T01:00:00Z",
            },
            "cletrics": {
                "focus_csv": "inputs/focus.csv",
                "meter_csv": "inputs/meter.csv",
                "savings_csv": "inputs/savings.csv",
                "release": "test",
                "commit": "a" * 40,
            },
            "recoveryos": {
                "rates_csv": "inputs/rates.csv",
                "verification": {
                    "charge_source_verified": True,
                    "meter_source_verified": True,
                    "rate_source_verified": True,
                },
                "bundle_path": "private/bundle.zip",
                "ledger_path": "private/ledger.json",
                "receipt_registry_path": "private/receipts.json",
                "report_path": "private/pilot-report.json",
            },
        }

    def test_one_command_pipeline_writes_private_bundle_ledger_registry_report(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = run_local_pilot(self.build_spec(root), base_dir=root)
            self.assertEqual(
                result.continuous_result.scan.report.totals["validated_cents"],
                1000,
            )
            self.assertEqual(
                result.continuous_result.savings_report.estimated_savings_opportunity_cents,
                2500,
            )
            for value in result.private_paths:
                path = Path(value)
                self.assertTrue(path.is_file())
                self.assertTrue(private_permissions_verified(path))

    def test_unverified_pilot_stays_review(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = self.build_spec(root)
            spec["recoveryos"]["verification"]["rate_source_verified"] = False
            result = run_local_pilot(spec, base_dir=root)
            self.assertEqual(
                result.continuous_result.scan.report.totals["validated_cents"],
                0,
            )
            self.assertEqual(
                result.continuous_result.scan.report.totals["review_cents"],
                1000,
            )


if __name__ == "__main__":
    unittest.main()
