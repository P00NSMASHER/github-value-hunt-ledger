from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from recoveryworks.cloud_diagnostic import run_authorized_cloud_diagnostic
from recoveryworks.private_io import private_permissions_verified


def H(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class AuthorizedCloudDiagnosticTests(unittest.TestCase):
    def intake(self, root: Path) -> dict:
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
            "diagnostic_id": "diag-001",
            "client_id": "client-1",
            "provider": "aws",
            "billing_account_id": "payer-123",
            "currency": "USD",
            "period": {"start": "2026-08-01", "end": "2026-08-31"},
            "authorization": {
                "authorization_id": "cust-auth-diag-1",
                "customer_actor_id": "customer-finops-owner",
                "authorized_at": "2026-09-24T12:00:00Z",
                "expires_at": "2026-09-30T12:00:00Z",
                "allowed_purposes": [
                    "BILLING_RECOVERY_DIAGNOSTIC",
                    "SAVINGS_ANALYSIS",
                ],
                "source_hash": H("customer-authorization"),
                "source_locator": "customer://authorization/diag-001",
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
                "release": "customer-export",
                "commit": "a" * 40,
                "exported_at": "2026-09-24T13:00:00Z",
            },
            "outputs": {"private_root": "private/diag-001"},
        }

    def test_authorized_real_account_path_produces_private_diagnostic(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = run_authorized_cloud_diagnostic(
                self.intake(root),
                base_dir=root,
                run_at="2026-09-24T14:00:00Z",
            )
            self.assertEqual(
                result.pilot.continuous_result.scan.report.totals["validated_cents"],
                1000,
            )
            self.assertEqual(
                result.intake_receipt.billing_account_id,
                "payer-123",
            )
            self.assertTrue(
                private_permissions_verified(Path(result.intake_receipt_path))
            )

    def test_wrong_focus_account_fails_before_state_creation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            intake = self.intake(root)
            focus = root / "inputs" / "focus.csv"
            focus.write_text(
                "ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
                "BilledCost,BillingCurrency,ResourceId\n"
                "AWS,other-payer,EC2,2026-08-31T00:00:00Z,40.00,USD,i-1\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "outside authorization"):
                run_authorized_cloud_diagnostic(
                    intake,
                    base_dir=root,
                    run_at="2026-09-24T14:00:00Z",
                )
            self.assertFalse((root / "private" / "diag-001").exists())

    def test_expired_authorization_fails_before_state_creation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            intake = self.intake(root)
            with self.assertRaisesRegex(ValueError, "has expired"):
                run_authorized_cloud_diagnostic(
                    intake,
                    base_dir=root,
                    run_at="2026-10-01T14:00:00Z",
                )
            self.assertFalse((root / "private" / "diag-001").exists())

    def test_authorization_never_promotes_unverified_rates(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            intake = self.intake(root)
            intake["verification"]["rate_source_verified"] = False
            result = run_authorized_cloud_diagnostic(
                intake,
                base_dir=root,
                run_at="2026-09-24T14:00:00Z",
            )
            self.assertEqual(
                result.pilot.continuous_result.scan.report.totals["validated_cents"],
                0,
            )
            self.assertEqual(
                result.pilot.continuous_result.scan.report.totals["review_cents"],
                1000,
            )


if __name__ == "__main__":
    unittest.main()
