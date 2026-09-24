from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from recoveryworks.branches.cloud_remediation import (
    approve_cloud_remediation_plan,
    build_cloud_remediation_plan,
    prepare_cloud_remediation_envelopes,
)
from recoveryworks.branches.cloud_savings import build_cloud_savings_report
from recoveryworks.integrations.cletrics import CLETRICS_BUNDLE_TYPE, load_cletrics_bundle
from recoveryworks.integrations.cletrics_continuous import run_continuous_cletrics_scan
from recoveryworks.integrations.cletrics_registry import CletricsReceiptRegistry
from recoveryworks.runner import run_scan360_config


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def manifest_entry(role: str, path: str, raw: bytes, kind: str) -> dict:
    return {
        "role": role,
        "path": path,
        "sha256": sha(raw),
        "size_bytes": len(raw),
        "transformation_id": f"test-{role}-v1",
        "source": {
            "kind": kind,
            "locator": f"source://{role}",
            "sha256": sha((kind + "-raw").encode()),
            "acquired_at": "2026-09-23T22:00:00Z",
        },
    }


def make_bundle(path: Path) -> Path:
    charges = (
        b"Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,Actual_Amount\n"
        b"C-1,AWS,acct-1,compute,2026-08-31,40.00\n"
    )
    meter = b"Charge_ID,Meter_Record_ID,Usage_Units\nC-1,M-1,10\n"
    anomaly = (
        b"Signal_ID,Detected_At,Provider,Account_ID,Service_ID,Resource_ID,Region,"
        b"Severity,Detection_Method,Metric_Name,Z_Score,Baseline_Value,Actual_Value,"
        b"Estimated_Cost_Impact,Confidence\n"
        b"A-1,2026-09-23T20:00:00Z,aws,acct-1,compute,i-1,us-east-1,"
        b"P1,zscore,cost_estimate,4.0,10,100,5000.00,0.90\n"
    )
    savings = (
        b"Signal_ID,Detected_At,Provider,Account_ID,Service_ID,Resource_ID,Region,"
        b"Savings_Category,Estimated_Savings,Confidence,Recommendation,Remediation_Action\n"
        b"S-1,2026-09-23T20:05:00Z,aws,acct-1,compute,i-1,us-east-1,"
        b"rightsize,250.00,0.80,Reduce instance size after utilization review,resize_instance\n"
    )
    entries = [
        manifest_entry("invoice_charges", "billing/charges.csv", charges, "billing"),
        manifest_entry("meter_usage", "usage/meter.csv", meter, "meter"),
        manifest_entry("anomaly_signals", "signals/anomaly.csv", anomaly, "anomaly"),
        manifest_entry("savings_signals", "signals/savings.csv", savings, "savings"),
    ]
    manifest = {
        "schema": 1,
        "bundle_type": CLETRICS_BUNDLE_TYPE,
        "client_id": "client-1",
        "provider": "aws",
        "billing_account_id": "acct-1",
        "currency": "USD",
        "period_start": "2026-08-01",
        "period_end": "2026-08-31",
        "exported_at": "2026-09-23T22:10:00Z",
        "cletrics": {"release": "test", "commit": "a" * 40, "image_digest": None},
        "entries": entries,
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(manifest, sort_keys=True, separators=(",", ":")),
        )
        archive.writestr("billing/charges.csv", charges)
        archive.writestr("usage/meter.csv", meter)
        archive.writestr("signals/anomaly.csv", anomaly)
        archive.writestr("signals/savings.csv", savings)
    return path


def write_rates(path: Path, unit_rate: str = "2.00") -> None:
    path.write_text(
        "Counterparty,Service_ID,Effective_From,Effective_To,"
        "Fixed_Fee,Included_Units,Unit_Rate\n"
        f"AWS,compute,2026-01-01,,10.00,0,{unit_rate}\n",
        encoding="utf-8",
    )


class SavingsSurfaceTests(unittest.TestCase):
    def test_only_explicit_savings_signals_roll_up_as_savings(self):
        with tempfile.TemporaryDirectory() as d:
            bundle = load_cletrics_bundle(make_bundle(Path(d) / "bundle.zip"))
            report = build_cloud_savings_report(bundle.signals)
            self.assertEqual(report.signal_count, 2)
            self.assertEqual(report.savings_opportunity_count, 1)
            self.assertEqual(report.estimated_savings_opportunity_cents, 25_000)
            self.assertEqual(report.anomaly_count, 1)
            self.assertEqual(report.estimated_anomaly_exposure_cents, 500_000)
            self.assertEqual(report.reconciliation_drift_cents, 0)
            self.assertEqual(report.as_dict()["realized_savings_cents"], 0)

    def test_scan360_exposes_separate_recovery_and_savings_surfaces(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_bundle(root / "bundle.zip")
            write_rates(root / "rates.csv")
            result = run_scan360_config(
                {
                    "client_id": "client-1",
                    "currency": "USD",
                    "cloud": {
                        "cletrics_bundle": "bundle.zip",
                        "rates_csv": "rates.csv",
                        "charge_source_verified": True,
                        "meter_source_verified": True,
                        "rate_source_verified": True,
                    },
                },
                state_path=root / "ledger.json",
                base_dir=root,
            )
            payload = result.as_dict()
            self.assertEqual(
                payload["financial_surfaces"]["recovery"]["totals"]["validated_cents"],
                1000,
            )
            self.assertEqual(
                payload["financial_surfaces"]["savings"][
                    "estimated_savings_opportunity_cents"
                ],
                25_000,
            )
            self.assertEqual(
                payload["financial_surfaces"]["savings"][
                    "estimated_anomaly_exposure_cents"
                ],
                500_000,
            )


class RemediationWorkflowTests(unittest.TestCase):
    def test_plan_approval_and_envelopes_never_execute(self):
        with tempfile.TemporaryDirectory() as d:
            bundle = load_cletrics_bundle(make_bundle(Path(d) / "bundle.zip"))
            plan = build_cloud_remediation_plan(bundle.signals)
            self.assertEqual(len(plan.actions), 1)
            self.assertFalse(hasattr(plan, "execute"))
            approval = approve_cloud_remediation_plan(
                plan,
                reviewer_id="reviewer-1",
                customer_authorization_id="customer-auth-1",
            )
            envelopes = prepare_cloud_remediation_envelopes(plan, approval)
            self.assertEqual(len(envelopes), 1)
            self.assertEqual(envelopes[0].execution_status, "NOT_EXECUTED")
            self.assertFalse(hasattr(envelopes[0], "execute"))

    def test_approval_must_bind_exact_plan_and_known_action(self):
        with tempfile.TemporaryDirectory() as d:
            bundle = load_cletrics_bundle(make_bundle(Path(d) / "bundle.zip"))
            plan = build_cloud_remediation_plan(bundle.signals)
            with self.assertRaisesRegex(ValueError, "unknown"):
                approve_cloud_remediation_plan(
                    plan,
                    reviewer_id="reviewer",
                    customer_authorization_id="auth",
                    approved_action_ids=("not-an-action",),
                )
            approval = approve_cloud_remediation_plan(
                plan,
                reviewer_id="reviewer",
                customer_authorization_id="auth",
            )
            altered = plan.__class__(
                plan_id=plan.plan_id + "-altered",
                actions=plan.actions,
            )
            with self.assertRaisesRegex(ValueError, "exact plan"):
                prepare_cloud_remediation_envelopes(altered, approval)

    def test_runner_rejects_execution_request(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_bundle(root / "bundle.zip")
            write_rates(root / "rates.csv")
            with self.assertRaisesRegex(ValueError, "plan-only"):
                run_scan360_config(
                    {
                        "client_id": "client-1",
                        "currency": "USD",
                        "cloud": {
                            "cletrics_bundle": "bundle.zip",
                            "rates_csv": "rates.csv",
                        },
                        "cloud_remediation": {"enabled": True, "execute": True},
                    },
                    state_path=root / "ledger.json",
                    base_dir=root,
                )
            self.assertFalse((root / "ledger.json").exists())


class ContinuousIngestionTests(unittest.TestCase):
    def test_exact_repeat_is_skipped_and_registry_is_durable(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_bundle(root / "bundle.zip")
            write_rates(root / "rates.csv")
            config = {
                "client_id": "client-1",
                "currency": "USD",
                "cloud": {
                    "cletrics_bundle": "bundle.zip",
                    "rates_csv": "rates.csv",
                    "charge_source_verified": True,
                    "meter_source_verified": True,
                    "rate_source_verified": True,
                },
                "cloud_remediation": {"enabled": True},
            }
            first = run_continuous_cletrics_scan(
                config,
                state_path=root / "ledger.json",
                registry_path=root / "receipts.json",
                base_dir=root,
            )
            self.assertEqual(len(first.new_job_fingerprints), 1)
            self.assertEqual(first.duplicate_job_fingerprints, ())
            self.assertEqual(first.scan.report.totals["validated_cents"], 1000)
            self.assertEqual(
                first.savings_report.estimated_savings_opportunity_cents, 25_000
            )
            self.assertIsNotNone(first.remediation_plan)
            self.assertEqual(len(first.remediation_plan.actions), 1)

            second = run_continuous_cletrics_scan(
                config,
                state_path=root / "ledger.json",
                registry_path=root / "receipts.json",
                base_dir=root,
            )
            self.assertEqual(second.new_job_fingerprints, ())
            self.assertEqual(len(second.duplicate_job_fingerprints), 1)
            self.assertEqual(second.scan.added_finding_ids, ())
            self.assertEqual(second.scan.report.as_dict(), first.scan.report.as_dict())
            self.assertEqual(
                second.savings_report.as_dict(),
                first.savings_report.as_dict(),
            )
            registry = CletricsReceiptRegistry(root / "receipts.json")
            self.assertEqual(len(registry.receipts()), 1)
            self.assertEqual(registry.state_hash(), second.registry_hash)

    def test_authority_change_changes_fingerprint_and_reprocesses(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_bundle(root / "bundle.zip")
            write_rates(root / "rates.csv", "2.00")
            config = {
                "client_id": "client-1",
                "currency": "USD",
                "cloud": {
                    "cletrics_bundle": "bundle.zip",
                    "rates_csv": "rates.csv",
                    "charge_source_verified": True,
                    "meter_source_verified": True,
                    "rate_source_verified": True,
                },
            }
            first = run_continuous_cletrics_scan(
                config,
                state_path=root / "ledger.json",
                registry_path=root / "receipts.json",
                base_dir=root,
            )
            write_rates(root / "rates.csv", "1.80")
            second = run_continuous_cletrics_scan(
                config,
                state_path=root / "ledger.json",
                registry_path=root / "receipts.json",
                base_dir=root,
            )
            self.assertEqual(len(second.new_job_fingerprints), 1)
            self.assertNotEqual(
                first.new_job_fingerprints[0],
                second.new_job_fingerprints[0],
            )
            self.assertEqual(len(CletricsReceiptRegistry(root / "receipts.json").receipts()), 2)

    def test_registry_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_bundle(root / "bundle.zip")
            write_rates(root / "rates.csv")
            config = {
                "client_id": "client-1",
                "cloud": {
                    "cletrics_bundle": "bundle.zip",
                    "rates_csv": "rates.csv",
                },
            }
            run_continuous_cletrics_scan(
                config,
                state_path=root / "ledger.json",
                registry_path=root / "receipts.json",
                base_dir=root,
            )
            payload = json.loads((root / "receipts.json").read_text())
            payload["payload"]["receipts"][0]["provider"] = "tampered"
            (root / "receipts.json").write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                CletricsReceiptRegistry(root / "receipts.json").receipts()


if __name__ == "__main__":
    unittest.main()
