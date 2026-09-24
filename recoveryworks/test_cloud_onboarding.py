from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from recoveryworks.cloud_diagnostic import run_authorized_cloud_diagnostic
from recoveryworks.cloud_onboarding import (
    OnboardingItemState,
    materialize_cloud_diagnostic_call,
    validate_cloud_onboarding,
    write_onboarding_outputs,
)
from recoveryworks.private_io import private_permissions_verified


def H(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def build_spec(root: Path) -> dict:
    inputs = root / "inputs"
    inputs.mkdir()
    (inputs / "focus.csv").write_text(
        "ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
        "BilledCost,BillingCurrency,ResourceId\n"
        "AWS,payer-1,EC2,2026-08-31,40.00,USD,i-1\n",
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
        "schema": 2,
        "onboarding_id": "onboard-1",
        "diagnostic_id": "diag-1",
        "client_id": "client-1",
        "provider": "aws",
        "billing_account_id": "payer-1",
        "currency": "USD",
        "period": {"start": "2026-08-01", "end": "2026-08-31"},
        "authorization": {
            "customer_actor_id": "customer-owner",
            "authorized_at": "2026-09-24T12:00:00Z",
            "expires_at": "2026-10-01T12:00:00Z",
            "source_hash": H("auth"),
            "source_locator": "customer://auth-1",
            "verified": True,
        },
        "evidence_review": {
            "reviewer_id": "reviewer-1",
            "reviewed_at": "2026-09-24T12:05:00Z",
            "charge_source_verified": True,
            "meter_source_verified": True,
            "rate_source_verified": False,
        },
        "inputs": {
            "focus_csv": "inputs/focus.csv",
            "meter_csv": "inputs/meter.csv",
            "rates_csv": "inputs/rates.csv",
        },
        "cletrics": {
            "release": "test",
            "commit": "a" * 40,
            "exported_at": "2026-09-24T13:00:00Z",
        },
        "outputs": {"private_root": "private/diag-1"},
    }


class CloudOnboardingTests(unittest.TestCase):
    def test_ready_onboarding_materializes_current_diagnostic_api(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            readiness = validate_cloud_onboarding(build_spec(root), base_dir=root)
            self.assertTrue(readiness.diagnostic_ready)
            kwargs = materialize_cloud_diagnostic_call(readiness)
            self.assertEqual(kwargs["authorization"].billing_account_id, "payer-1")
            self.assertTrue(kwargs["authorization"].verified)
            self.assertFalse(kwargs["evidence_review"].rate_source_verified)
            result = run_authorized_cloud_diagnostic(
                **kwargs,
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

    def test_unverified_processing_authorization_blocks_readiness(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = build_spec(root)
            spec["authorization"]["verified"] = False
            readiness = validate_cloud_onboarding(spec, base_dir=root)
            self.assertFalse(readiness.diagnostic_ready)
            auth = next(
                item for item in readiness.checklist
                if item.item_id == "AUTHORIZATION"
            )
            self.assertIs(auth.state, OnboardingItemState.INVALID)

    def test_outputs_are_private(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            readiness = validate_cloud_onboarding(build_spec(root), base_dir=root)
            checklist = root / "private" / "checklist.json"
            request = root / "private" / "diagnostic-request.json"
            write_onboarding_outputs(
                readiness,
                checklist_path=checklist,
                diagnostic_request_path=request,
            )
            self.assertTrue(private_permissions_verified(checklist))
            self.assertTrue(private_permissions_verified(request))


if __name__ == "__main__":
    unittest.main()
