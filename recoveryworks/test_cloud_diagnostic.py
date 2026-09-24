from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from recoveryworks.cloud_diagnostic import (
    build_customer_diagnostic_authorization,
    build_diagnostic_evidence_review,
    run_authorized_cloud_diagnostic,
)
from recoveryworks.private_io import private_permissions_verified


def H(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class AuthorizedCloudDiagnosticTests(unittest.TestCase):
    def inputs(self, root: Path):
        inputs = root / "inputs"
        inputs.mkdir()
        values = {
            "focus_csv": (
                "ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
                "BilledCost,BillingCurrency,ResourceId\n"
                "AWS,payer-123,EC2,2026-08-31T00:00:00Z,40.00,USD,i-1\n"
            ),
            "meter_csv": (
                "Meter_Record_ID,Usage_Units,ResourceId,ServiceName,UsageDate\n"
                "M-1,10,i-1,EC2,2026-08-31\n"
            ),
            "rates_csv": (
                "Counterparty,Service_ID,Effective_From,Effective_To,Fixed_Fee,"
                "Included_Units,Unit_Rate\n"
                "AWS,EC2,2026-01-01,,10.00,0,2.00\n"
            ),
            "savings_csv": (
                "Signal_ID,Detected_At,Provider,Account_ID,Service_ID,Resource_ID,"
                "Region,Savings_Category,Estimated_Savings,Confidence,Recommendation,"
                "Remediation_Action\n"
                "S-1,2026-09-01T00:00:00Z,aws,payer-123,EC2,i-1,us-east-1,"
                "rightsize,25.00,0.8,Review and downsize,resize_instance\n"
            ),
        }
        paths = {}
        for role, value in values.items():
            path = inputs / role
            path.write_text(value, encoding="utf-8")
            paths[role] = path
        hashes = {role: H(path.read_bytes()) for role, path in paths.items()}
        return paths, hashes

    def authorization(self, hashes, *, verified=True):
        return build_customer_diagnostic_authorization(
            client_id="client-1",
            billing_account_id="payer-123",
            customer_actor_id="customer-finops-owner",
            period_start="2026-08-01",
            period_end="2026-08-31",
            authorized_at="2026-09-24T12:00:00Z",
            expires_at="2026-09-30T12:00:00Z",
            authorized_input_hashes=hashes,
            source_hash=H(b"customer-authorization"),
            source_locator="customer://authorization/diag-001",
            verified=verified,
        )

    def review(self, hashes, *, rate_verified=True):
        return build_diagnostic_evidence_review(
            reviewer_id="evidence-reviewer",
            reviewed_at="2026-09-24T12:05:00Z",
            money_source_hashes={
                role: hashes[role]
                for role in ("focus_csv", "meter_csv", "rates_csv")
            },
            charge_source_verified=True,
            meter_source_verified=True,
            rate_source_verified=rate_verified,
        )

    def test_exact_authorized_bytes_run_to_private_assurance_report(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            paths, hashes = self.inputs(root)
            run = run_authorized_cloud_diagnostic(
                diagnostic_id="diag-001",
                authorization=self.authorization(hashes),
                evidence_review=self.review(hashes),
                input_paths={role: str(path) for role, path in paths.items()},
                cletrics_release="customer-export",
                cletrics_commit="a" * 40,
                exported_at="2026-09-24T13:00:00Z",
                private_root=root / "private" / "diag-001",
                run_at="2026-09-24T14:00:00Z",
            )
            self.assertEqual(
                run.pilot.continuous_result.scan.report.totals["validated_cents"],
                1000,
            )
            self.assertEqual(
                run.pilot.continuous_result.savings_report.
                estimated_savings_opportunity_cents,
                2500,
            )
            self.assertTrue(
                private_permissions_verified(Path(run.intake_receipt_path))
            )
            for value in run.intake_receipt.private_snapshot_paths.values():
                self.assertTrue(private_permissions_verified(Path(value)))

    def test_customer_permission_does_not_promote_unverified_rate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            paths, hashes = self.inputs(root)
            run = run_authorized_cloud_diagnostic(
                diagnostic_id="diag-001",
                authorization=self.authorization(hashes),
                evidence_review=self.review(hashes, rate_verified=False),
                input_paths={role: str(path) for role, path in paths.items()},
                cletrics_release="customer-export",
                cletrics_commit="a" * 40,
                exported_at="2026-09-24T13:00:00Z",
                private_root=root / "private" / "diag-001",
                run_at="2026-09-24T14:00:00Z",
            )
            self.assertEqual(
                run.pilot.continuous_result.scan.report.totals["validated_cents"],
                0,
            )
            self.assertEqual(
                run.pilot.continuous_result.scan.report.totals["review_cents"],
                1000,
            )

    def test_changed_bytes_after_authorization_fail_before_private_state(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            paths, hashes = self.inputs(root)
            auth = self.authorization(hashes)
            paths["rates_csv"].write_text("changed\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "do not match customer authorization"):
                run_authorized_cloud_diagnostic(
                    diagnostic_id="diag-001",
                    authorization=auth,
                    evidence_review=self.review(hashes),
                    input_paths={role: str(path) for role, path in paths.items()},
                    cletrics_release="customer-export",
                    cletrics_commit="a" * 40,
                    exported_at="2026-09-24T13:00:00Z",
                    private_root=root / "private" / "diag-001",
                    run_at="2026-09-24T14:00:00Z",
                )
            self.assertFalse((root / "private" / "diag-001").exists())

    def test_unverified_customer_authorization_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            paths, hashes = self.inputs(root)
            with self.assertRaisesRegex(ValueError, "must be verified"):
                run_authorized_cloud_diagnostic(
                    diagnostic_id="diag-001",
                    authorization=self.authorization(hashes, verified=False),
                    evidence_review=self.review(hashes),
                    input_paths={role: str(path) for role, path in paths.items()},
                    cletrics_release="customer-export",
                    cletrics_commit="a" * 40,
                    exported_at="2026-09-24T13:00:00Z",
                    private_root=root / "private" / "diag-001",
                    run_at="2026-09-24T14:00:00Z",
                )


if __name__ == "__main__":
    unittest.main()
