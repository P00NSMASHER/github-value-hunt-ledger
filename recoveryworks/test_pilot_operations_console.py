from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from recoveryworks.cloud_diagnostic import run_authorized_cloud_diagnostic
from recoveryworks.pilot_operations_console import (
    build_pilot_operations_snapshot,
    write_pilot_operations_snapshot,
)
from recoveryworks.private_io import private_permissions_verified


def H(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def build_intake(root: Path) -> dict:
    inputs = root / "inputs"
    inputs.mkdir()
    (inputs / "focus.csv").write_text(
        "ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
        "BilledCost,BillingCurrency,ResourceId\n"
        "AWS,payer-123,EC2,2026-08-31T00:00:00Z,40.00,USD,i-1\n",
        encoding="utf-8",
    )
    (inputs / "meter.csv").write_text(
        "Meter_Record_ID,Usage_Units,ResourceId,ServiceName,UsageDate\n"
        "M-1,10,i-1,EC2,2026-08-31\n",
        encoding="utf-8",
    )
    (inputs / "rates.csv").write_text(
        "Counterparty,Service_ID,Effective_From,Effective_To,Fixed_Fee,"
        "Included_Units,Unit_Rate\n"
        "AWS,EC2,2026-01-01,,10.00,0,2.00\n",
        encoding="utf-8",
    )
    return {
        "schema": 1,
        "diagnostic_id": "diag-console",
        "client_id": "client-1",
        "provider": "aws",
        "billing_account_id": "payer-123",
        "currency": "USD",
        "period": {"start": "2026-08-01", "end": "2026-08-31"},
        "authorization": {
            "authorization_id": "auth-console",
            "customer_actor_id": "customer-owner",
            "authorized_at": "2026-09-24T12:00:00Z",
            "expires_at": "2026-09-30T12:00:00Z",
            "allowed_purposes": [
                "BILLING_RECOVERY_DIAGNOSTIC",
                "SAVINGS_ANALYSIS",
            ],
            "source_hash": H("auth-console"),
            "source_locator": "customer://auth-console",
            "credentials_embedded": False,
            "external_actions_allowed": False,
            "remediation_allowed": False,
        },
        "inputs": {
            "focus_csv": "inputs/focus.csv",
            "meter_csv": "inputs/meter.csv",
            "rates_csv": "inputs/rates.csv",
        },
        "verification": {
            "charge_source_verified": True,
            "meter_source_verified": True,
            "rate_source_verified": True,
        },
        "cletrics": {
            "release": "test",
            "commit": "a" * 40,
            "exported_at": "2026-09-24T13:00:00Z",
        },
        "outputs": {"private_root": "private/diag-console"},
    }


class PilotOperationsConsoleTests(unittest.TestCase):
    def test_read_only_snapshot_shows_readiness_totals_and_no_actions(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = run_authorized_cloud_diagnostic(
                build_intake(root),
                base_dir=root,
                run_at="2026-09-24T14:00:00Z",
            )
            snapshot = build_pilot_operations_snapshot(result)
            self.assertEqual(snapshot.diagnostic_status, "COMPLETED_READ_ONLY")
            self.assertEqual(snapshot.evidence_readiness["validated_cases"], 1)
            self.assertEqual(snapshot.recovery_totals["validated_cents"], 1000)
            self.assertTrue(snapshot.controls["read_only"])
            self.assertFalse(snapshot.controls["case_approval_available"])
            self.assertFalse(snapshot.controls["cloud_mutation_available"])

    def test_unverified_case_appears_in_evidence_review_count(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            intake = build_intake(root)
            intake["verification"]["rate_source_verified"] = False
            result = run_authorized_cloud_diagnostic(
                intake,
                base_dir=root,
                run_at="2026-09-24T14:00:00Z",
            )
            snapshot = build_pilot_operations_snapshot(result)
            self.assertEqual(snapshot.evidence_readiness["review_cases"], 1)
            self.assertEqual(snapshot.evidence_readiness["needs_review_cases"], 1)
            self.assertEqual(snapshot.recovery_totals["validated_cents"], 0)

    def test_snapshot_outputs_are_private(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = run_authorized_cloud_diagnostic(
                build_intake(root),
                base_dir=root,
                run_at="2026-09-24T14:00:00Z",
            )
            snapshot = build_pilot_operations_snapshot(result)
            json_path = root / "private" / "ops.json"
            markdown_path = root / "private" / "ops.md"
            write_pilot_operations_snapshot(
                snapshot,
                json_path=json_path,
                markdown_path=markdown_path,
            )
            self.assertTrue(private_permissions_verified(json_path))
            self.assertTrue(private_permissions_verified(markdown_path))
            text = markdown_path.read_text(encoding="utf-8")
            self.assertIn("Pilot Operations Console — Read Only", text)
            self.assertIn("Execution available from console: False", text)


if __name__ == "__main__":
    unittest.main()
