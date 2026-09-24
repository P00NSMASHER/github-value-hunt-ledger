from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recoveryworks.commercial_pilot import (
    build_commercial_pilot_package,
    write_commercial_pilot_package,
)
from recoveryworks.private_io import private_permissions_verified


class CommercialPilotPackageTests(unittest.TestCase):
    def spec(self) -> dict:
        return {
            "schema": 1,
            "offer_name": "Cloud Recovery & Savings Assurance Pilot",
            "buyer_profile": (
                "AWS-heavy SaaS or mid-market company with negotiated rates "
                "and meaningful monthly cloud spend"
            ),
            "scope": {
                "provider": "aws",
                "lookback_months": 12,
                "max_billing_accounts": 1,
                "recovery_modes": [
                    "CONTRACT_RATE_MISMATCH",
                    "CONTRACT_DISCOUNT_OMISSION",
                    "COMMITMENT_BENEFIT_OMISSION",
                ],
                "include_prospective_savings": True,
                "include_diagnostics": True,
                "include_remediation_plan": True,
                "cloud_mutation_in_scope": False,
                "external_recovery_actions_in_scope": False,
            },
            "pricing": {
                "currency": "USD",
                "diagnostic_fee_cents": 1000000,
                "recovered_cash_success_fee_bps": 2000,
                "monthly_assurance_fee_cents": 300000,
                "savings_implementation_fee_cents": 500000,
                "pricing_is_hypothesis": True,
            },
            "deliverables": [
                "Private Cloud Recovery & Savings Assurance report",
                "Evidence packet for every active validated recovery",
                "Separate prospective savings and diagnostic surfaces",
                "Read-only remediation plan where applicable",
            ],
            "acceptance_criteria": [
                {
                    "criterion_id": "AC-1",
                    "description": "All customer inputs stay within authorized read-only scope.",
                    "required_evidence": "Diagnostic authorization and intake receipt",
                },
                {
                    "criterion_id": "AC-2",
                    "description": "No unverified candidate is represented as validated recovery.",
                    "required_evidence": "RecoveryOS report plus finding evidence packets",
                },
                {
                    "criterion_id": "AC-3",
                    "description": "Validated recoveries have reproducible contract-backed calculations.",
                    "required_evidence": "Rule/evidence hashes and expected-vs-actual calculation",
                },
                {
                    "criterion_id": "AC-4",
                    "description": "Savings estimates remain separate from recoverable cash.",
                    "required_evidence": "Separated report financial surfaces",
                },
            ],
            "exclusions": [
                "Cloud resource mutation",
                "Provider dispute submission",
                "Counterparty contact",
                "Guarantee of recovery or savings",
            ],
            "assumptions": [
                "Customer supplies authorized billing, meter, and reviewed commercial authority data.",
                "Any pricing shown is a commercial hypothesis to test, not observed market traction.",
            ],
        }

    def test_package_keeps_recovery_fee_on_recovered_cash_only(self):
        package = build_commercial_pilot_package(self.spec())
        self.assertTrue(package.pricing.pricing_is_hypothesis)
        self.assertEqual(
            package.pricing.success_fee_for_recovered_cash(5000000),
            1000000,
        )
        self.assertFalse(package.scope.cloud_mutation_in_scope)
        self.assertFalse(package.outreach_allowed)
        self.assertFalse(package.external_commitment_created)

    def test_mutation_in_scope_is_rejected(self):
        spec = self.spec()
        spec["scope"]["cloud_mutation_in_scope"] = True
        with self.assertRaisesRegex(ValueError, "cloud mutation out of scope"):
            build_commercial_pilot_package(spec)

    def test_outputs_are_private_internal_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            package = build_commercial_pilot_package(self.spec())
            json_path = root / "commercial.json"
            markdown_path = root / "commercial.md"
            write_commercial_pilot_package(
                package,
                json_path=json_path,
                markdown_path=markdown_path,
            )
            self.assertTrue(private_permissions_verified(json_path))
            self.assertTrue(private_permissions_verified(markdown_path))
            text = markdown_path.read_text(encoding="utf-8")
            self.assertIn("Pricing configuration (hypothesis to test)", text)
            self.assertIn("Customer acceptance criteria", text)
            self.assertIn("not a contract", text)


if __name__ == "__main__":
    unittest.main()
