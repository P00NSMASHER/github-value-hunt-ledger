from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recoveryworks.multicloud_orchestration import run_multicloud_orchestration


_PROVIDER = {
    "aws": ("Amazon Web Services", "EC2", "aws-acct", "i-aws"),
    "azure": ("Microsoft Azure", "VirtualMachines", "azure-acct", "vm-azure"),
    "gcp": ("Google Cloud Platform", "ComputeEngine", "gcp-acct", "vm-gcp"),
}


def executable_job(root: Path, provider: str, savings: int) -> dict:
    display, service, account, resource = _PROVIDER[provider]
    inputs = root / f"exec-inputs-{provider}"
    inputs.mkdir()
    (inputs / "focus.csv").write_text(
        "ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
        "BilledCost,BillingCurrency,ResourceId\n"
        f"{display},{account},{service},2026-08-31T00:00:00Z,40.00,USD,{resource}\n",
        encoding="utf-8",
    )
    (inputs / "meter.csv").write_text(
        "Meter_Record_ID,Usage_Units,ResourceId,ServiceName,UsageDate\n"
        f"M-1,10,{resource},{service},2026-08-31\n",
        encoding="utf-8",
    )
    (inputs / "rates.csv").write_text(
        "Counterparty,Service_ID,Effective_From,Effective_To,Fixed_Fee,"
        "Included_Units,Unit_Rate\n"
        f"{display},{service},2026-01-01,,10.00,0,2.00\n",
        encoding="utf-8",
    )
    (inputs / "savings.csv").write_text(
        "Signal_ID,Detected_At,Provider,Account_ID,Service_ID,Resource_ID,"
        "Region,Savings_Category,Estimated_Savings,Confidence,Recommendation,"
        "Remediation_Action\n"
        f"{provider.upper()}-S-1,2026-09-01T00:00:00Z,{provider},{account},"
        f"{service},{resource},region-1,rightsize,{savings / 100:.2f},0.9,"
        "Review and resize,resize_instance\n",
        encoding="utf-8",
    )
    private = root / "private" / provider
    return {
        "schema": 1,
        "deployment_id": f"{provider}-exec",
        "client_id": "client-multi-exec",
        "currency": "USD",
        "provider": provider,
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
            "focus_csv": str(inputs / "focus.csv"),
            "meter_csv": str(inputs / "meter.csv"),
            "savings_csv": str(inputs / "savings.csv"),
            "release": "multi-exec-test",
            "commit": "a" * 40,
        },
        "recoveryos": {
            "rates_csv": str(inputs / "rates.csv"),
            "verification": {
                "charge_source_verified": True,
                "meter_source_verified": True,
                "rate_source_verified": True,
            },
            "bundle_path": str(private / "bundle.zip"),
            "ledger_path": str(private / "ledger.json"),
            "receipt_registry_path": str(private / "receipts.json"),
            "report_path": str(private / "assurance.json"),
        },
    }


class MultiCloudExecutionTests(unittest.TestCase):
    def test_three_provider_jobs_execute_with_separate_truth_planes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = {
                "schema": 1,
                "client_id": "client-multi-exec",
                "currency": "USD",
                "jobs": [
                    executable_job(root, "aws", 1000),
                    executable_job(root, "azure", 2000),
                    executable_job(root, "gcp", 3000),
                ],
            }
            result = run_multicloud_orchestration(spec, base_dir=root)
            self.assertEqual(
                tuple(run.provider for run in result.provider_runs),
                ("aws", "azure", "gcp"),
            )
            self.assertFalse(result.combined_financial_rollup_enabled)
            self.assertFalse(result.cross_provider_authority_reuse_allowed)
            self.assertFalse(result.cloud_mutation_performed)
            self.assertFalse(result.external_actions_performed)
            self.assertEqual(
                [
                    run.pilot.continuous_result.scan.report.totals["validated_cents"]
                    for run in result.provider_runs
                ],
                [1000, 1000, 1000],
            )
            self.assertEqual(
                [
                    run.pilot.continuous_result.savings_report.
                    estimated_savings_opportunity_cents
                    for run in result.provider_runs
                ],
                [1000, 2000, 3000],
            )
            self.assertEqual(
                len({run.assurance_report_proof_hash for run in result.provider_runs}),
                3,
            )
            payload = result.as_dict()
            self.assertNotIn("totals", payload)
            self.assertNotIn("validated_cents", payload)


if __name__ == "__main__":
    unittest.main()
