from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recoveryworks.multicloud_orchestration import (
    build_multicloud_orchestration_plan,
    write_multicloud_orchestration_plan,
)
from recoveryworks.private_io import private_permissions_verified


def provider_job(root: Path, provider: str) -> dict:
    inputs = root / f"inputs-{provider}"
    inputs.mkdir(exist_ok=True)
    for name in ("focus.csv", "meter.csv", "rates.csv"):
        (inputs / name).write_text("header\n", encoding="utf-8")
    private = root / "private" / provider
    return {
        "schema": 1,
        "deployment_id": f"{provider}-pilot",
        "client_id": "client-multi",
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
            "release": "test",
            "commit": "a" * 40,
        },
        "recoveryos": {
            "rates_csv": str(inputs / "rates.csv"),
            "bundle_path": str(private / "bundle.zip"),
            "ledger_path": str(private / "ledger.json"),
            "receipt_registry_path": str(private / "receipts.json"),
            "report_path": str(private / "assurance.json"),
        },
    }


class MultiCloudOrchestrationPlanTests(unittest.TestCase):
    def test_three_provider_plan_preserves_isolation_and_does_not_execute(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan = build_multicloud_orchestration_plan(
                {
                    "schema": 1,
                    "client_id": "client-multi",
                    "currency": "USD",
                    "jobs": [
                        provider_job(root, "aws"),
                        provider_job(root, "azure"),
                        provider_job(root, "gcp"),
                    ],
                },
                base_dir=root,
            )
            self.assertEqual(plan.providers, ("aws", "azure", "gcp"))
            self.assertFalse(plan.execution_enabled)
            self.assertFalse(plan.shared_ledger_allowed)
            self.assertFalse(plan.shared_receipt_registry_allowed)
            self.assertFalse(plan.shared_financial_rollup_enabled)
            self.assertFalse(plan.cross_provider_authority_reuse_allowed)
            self.assertEqual(
                len({item.ledger_path for item in plan.provider_plans}), 3
            )

    def test_duplicate_provider_job_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaisesRegex(ValueError, "duplicate provider"):
                build_multicloud_orchestration_plan(
                    {
                        "schema": 1,
                        "client_id": "client-multi",
                        "currency": "USD",
                        "jobs": [
                            provider_job(root, "aws"),
                            provider_job(root, "aws"),
                        ],
                    },
                    base_dir=root,
                )

    def test_shared_ledger_path_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            aws = provider_job(root, "aws")
            azure = provider_job(root, "azure")
            azure["recoveryos"]["ledger_path"] = aws["recoveryos"]["ledger_path"]
            with self.assertRaisesRegex(ValueError, "cannot share state/output"):
                build_multicloud_orchestration_plan(
                    {
                        "schema": 1,
                        "client_id": "client-multi",
                        "currency": "USD",
                        "jobs": [aws, azure],
                    },
                    base_dir=root,
                )

    def test_mixed_client_or_currency_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            aws = provider_job(root, "aws")
            gcp = provider_job(root, "gcp")
            gcp["client_id"] = "other-client"
            with self.assertRaisesRegex(ValueError, "same client_id"):
                build_multicloud_orchestration_plan(
                    {
                        "schema": 1,
                        "client_id": "client-multi",
                        "currency": "USD",
                        "jobs": [aws, gcp],
                    },
                    base_dir=root,
                )

    def test_plan_outputs_are_private(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan = build_multicloud_orchestration_plan(
                {
                    "schema": 1,
                    "client_id": "client-multi",
                    "currency": "USD",
                    "jobs": [
                        provider_job(root, "azure"),
                        provider_job(root, "gcp"),
                    ],
                },
                base_dir=root,
            )
            json_path = root / "private" / "multicloud-plan.json"
            md_path = root / "private" / "multicloud-plan.md"
            write_multicloud_orchestration_plan(
                plan,
                json_path=json_path,
                markdown_path=md_path,
            )
            self.assertTrue(private_permissions_verified(json_path))
            self.assertTrue(private_permissions_verified(md_path))


if __name__ == "__main__":
    unittest.main()
