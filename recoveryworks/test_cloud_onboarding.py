from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from recoveryworks.cloud_onboarding import (
    OnboardingItemState,
    validate_cloud_onboarding,
    write_onboarding_outputs,
)
from recoveryworks.private_io import private_permissions_verified


def H(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class CloudOnboardingTests(unittest.TestCase):
    def spec(self, root: Path) -> dict:
        inputs = root / "inputs"
        inputs.mkdir()
        (inputs / "focus.csv").write_text(
            "ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
            "BilledCost,BillingCurrency\n"
            "AWS,payer-1,EC2,2026-08-31,40.00,USD\n",
            encoding="utf-8",
        )
        (inputs / "meter.csv").write_text(
            "Meter_Record_ID,Usage_Units\nM-1,10\n",
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
            "onboarding_id": "onboard-1",
            "diagnostic_id": "diag-1",
            "client_id": "client-1",
            "provider": "aws",
            "billing_account_id": "payer-1",
            "currency": "USD",
            "period": {"start": "2026-08-01", "end": "2026-08-31"},
            "authorization": {
                "authorization_id": "auth-1",
                "customer_actor_id": "customer-owner",
                "authorized_at": "2026-09-24T12:00:00Z",
                "expires_at": "2026-10-01T12:00:00Z",
                "allowed_purposes": [
                    "BILLING_RECOVERY_DIAGNOSTIC",
                    "SAVINGS_ANALYSIS",
                ],
                "source_hash": H("auth"),
                "source_locator": "customer://auth-1",
            },
            "inputs": {
                "focus_csv": "inputs/focus.csv",
                "meter_csv": "inputs/meter.csv",
                "rates_csv": "inputs/rates.csv",
            },
            "verification": {
                "charge_source_verified": False,
                "meter_source_verified": False,
                "rate_source_verified": False,
            },
            "cletrics": {
                "release": "test",
                "commit": "a" * 40,
                "exported_at": "2026-09-24T13:00:00Z",
            },
            "outputs": {"private_root": "private/diag-1"},
        }

    def test_ready_onboarding_maps_directly_to_diagnostic_intake(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            readiness = validate_cloud_onboarding(self.spec(root), base_dir=root)
            self.assertTrue(readiness.diagnostic_ready)
            self.assertIsNotNone(readiness.diagnostic_intake)
            self.assertEqual(
                readiness.diagnostic_intake["billing_account_id"], "payer-1"
            )
            self.assertFalse(
                readiness.diagnostic_intake["verification"]["rate_source_verified"]
            )
            self.assertIn(
                "focus_csv", readiness.diagnostic_intake["onboarding"]["input_hashes"]
            )

    def test_missing_meter_blocks_diagnostic_without_claiming_verification(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = self.spec(root)
            (root / "inputs" / "meter.csv").unlink()
            readiness = validate_cloud_onboarding(spec, base_dir=root)
            self.assertFalse(readiness.diagnostic_ready)
            self.assertIsNone(readiness.diagnostic_intake)
            meter = next(item for item in readiness.checklist if item.item_id == "METER")
            self.assertIs(meter.state, OnboardingItemState.MISSING)

    def test_outputs_are_private(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            readiness = validate_cloud_onboarding(self.spec(root), base_dir=root)
            checklist = root / "private" / "checklist.json"
            intake = root / "private" / "diagnostic.json"
            write_onboarding_outputs(
                readiness,
                checklist_path=checklist,
                diagnostic_intake_path=intake,
            )
            self.assertTrue(private_permissions_verified(checklist))
            self.assertTrue(private_permissions_verified(intake))


if __name__ == "__main__":
    unittest.main()
