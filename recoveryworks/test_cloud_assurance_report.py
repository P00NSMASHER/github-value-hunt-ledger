from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recoveryworks.cloud_assurance_report import (
    build_cloud_assurance_report,
    write_cloud_assurance_report,
)
from recoveryworks.pilot_runner import run_local_pilot
from recoveryworks.private_io import private_permissions_verified
from recoveryworks.store import LocalBundleStore


def build_spec(root: Path) -> dict:
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
        "deployment_id": "pilot-report-test",
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


class CloudAssuranceReportTests(unittest.TestCase):
    def test_validated_recovery_has_full_rule_and_evidence_packet(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = build_spec(root)
            pilot = run_local_pilot(spec, base_dir=root)
            ledger = LocalBundleStore(root / spec["recoveryos"]["ledger_path"]).load()
            report = build_cloud_assurance_report(
                result=pilot.continuous_result,
                ledger=ledger,
            )
            self.assertEqual(len(report.validated_recovery_packets), 1)
            packet = report.validated_recovery_packets[0]
            self.assertEqual(packet["calculation"]["potential_recovery_cents"], 1000)
            self.assertTrue(packet["rule"]["verified_controlling"])
            self.assertEqual(len(packet["rule"]["source_hash"]), 64)
            self.assertTrue(packet["evidence"])
            self.assertTrue(all(item["verified"] for item in packet["evidence"]))
            self.assertEqual(
                report.savings_summary["estimated_savings_opportunity_cents"],
                2500,
            )
            self.assertEqual(report.diagnostics["estimated_anomaly_exposure_cents"], 0)
            self.assertFalse(report.controls["cloud_mutation_authorized_by_report"])

    def test_report_outputs_are_private_and_markdown_keeps_surfaces_separate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = build_spec(root)
            pilot = run_local_pilot(spec, base_dir=root)
            ledger = LocalBundleStore(root / spec["recoveryos"]["ledger_path"]).load()
            report = build_cloud_assurance_report(
                result=pilot.continuous_result,
                ledger=ledger,
            )
            json_path, markdown_path = write_cloud_assurance_report(
                report,
                json_path=root / "private" / "assurance.json",
                markdown_path=root / "private" / "assurance.md",
            )
            self.assertTrue(private_permissions_verified(json_path))
            self.assertTrue(private_permissions_verified(markdown_path))
            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn("## Recoverable cash", markdown)
            self.assertIn("## Prospective and realized savings", markdown)
            self.assertIn("## Diagnostics", markdown)
            self.assertIn("## Validated recovery evidence packets", markdown)


if __name__ == "__main__":
    unittest.main()
