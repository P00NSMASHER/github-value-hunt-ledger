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
from recoveryworks.test_pilot_runner import LocalPilotRunnerTests


class CloudAssuranceReportTests(unittest.TestCase):
    def test_validated_recovery_has_full_rule_and_evidence_packet(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = LocalPilotRunnerTests().build_spec(root)
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
            spec = LocalPilotRunnerTests().build_spec(root)
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
