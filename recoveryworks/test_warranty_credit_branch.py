from recoveryworks.test_support import source_hash as H
from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.warranty_credit import (
    WarrantyCreditEntitlement,
    WarrantyCreditSettlement,
    audit_warranty_credits,
)
from recoveryworks.branches.warranty_credit_csv import (
    load_warranty_credit_entitlements_csv,
    load_warranty_credit_settlements_csv,
)


def entitlement(*, verified=True, amount=10000):
    return WarrantyCreditEntitlement(
        entitlement_id="E-1",
        client_id="client-1",
        supplier_id="Supplier A",
        reference_id="RMA-77",
        credit_category="warranty",
        entitled_cents=amount,
        effective_date="2026-08-01",
        entitlement_basis="Approved warranty claim/RMA credit",
        source_hash=H("entitlement-hash"),
        source_locator="file://entitlements.csv#row=2",
        verified=verified,
        entitlement_reviewer_id="credit-reviewer-1" if verified else None,
    )


def settlement(*, verified=True, amount=3000, sid="S-1"):
    return WarrantyCreditSettlement(
        settlement_id=sid,
        entitlement_id="E-1",
        amount_received_cents=amount,
        settlement_date="2026-08-20",
        source_hash=H(f"settlement-{sid}"),
        source_locator=f"file://settlements.csv#{sid}",
        verified=verified,
        settlement_kind="CREDIT_MEMO",
    )


class WarrantyCreditRecoveryTests(unittest.TestCase):
    def test_verified_credit_shortfall_is_validated(self):
        batch = audit_warranty_credits(
            client_id="client-1",
            entitlements=(entitlement(),),
            settlements=(settlement(),),
        )
        self.assertEqual(batch.exceptions, ())
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.expected_cents, 10000)
        self.assertEqual(finding.actual_cents, 3000)
        self.assertEqual(finding.potential_recovery_cents, 7000)

    def test_missing_settlement_is_unknown_not_zero(self):
        batch = audit_warranty_credits(
            client_id="client-1",
            entitlements=(entitlement(),),
            settlements=(),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(
            batch.exceptions[0].code,
            "NO_CREDIT_SETTLEMENT_EVIDENCE",
        )

    def test_verified_entitlement_requires_reviewer(self):
        with self.assertRaises(ValueError):
            WarrantyCreditEntitlement(
                entitlement_id="E",
                client_id="client-1",
                supplier_id="S",
                reference_id="R",
                credit_category="return",
                entitled_cents=100,
                effective_date="2026-08-01",
                entitlement_basis="approved return",
                source_hash=H("h"),
                source_locator="file://x",
                verified=True,
                entitlement_reviewer_id=None,
            )

    def test_real_csvs_flow_to_validated_credit_shortfall(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "entitlements.csv").write_text(
                "Entitlement_ID,Client_ID,Supplier_ID,Reference_ID,Credit_Category,"
                "Entitled_Amount,Effective_Date,Entitlement_Basis,Entitlement_Reviewer_ID\n"
                "E-1,client-1,Supplier A,RMA-77,WARRANTY,100.00,2026-08-01,"
                "Approved warranty claim,reviewer-1\n",
                encoding="utf-8",
            )
            (root / "settlements.csv").write_text(
                "Settlement_ID,Entitlement_ID,Amount_Received,Settlement_Date,Settlement_Kind\n"
                "S-1,E-1,30.00,2026-08-20,CREDIT_MEMO\n",
                encoding="utf-8",
            )
            batch = audit_warranty_credits(
                client_id="client-1",
                entitlements=load_warranty_credit_entitlements_csv(
                    root / "entitlements.csv", verified=True
                ),
                settlements=load_warranty_credit_settlements_csv(
                    root / "settlements.csv", verified=True
                ),
            )
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertEqual(finding.potential_recovery_cents, 7000)
            self.assertIn("#row=2", finding.evidence[0].locator)


if __name__ == "__main__":
    unittest.main()
