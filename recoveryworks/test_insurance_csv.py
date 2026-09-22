from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.insurance import audit_insurance_claims
from recoveryworks.branches.insurance_csv import (
    load_insurance_assessments_csv,
    load_insurance_claim_lines_csv,
    load_insurance_settlements_csv,
)


class InsuranceCsvTests(unittest.TestCase):
    def test_files_flow_to_validated_insurance_underpayment(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "claims.csv").write_text(
                "Claim_Line_ID,Claimant_ID,Insurer_ID,Policy_ID,Loss_Date,"
                "Coverage_Category,Claimed_Amount\n"
                "CL-1,client-1,Insurer-1,POL-1,2026-08-01,Property,100000.00\n",
                encoding="utf-8",
            )
            (root / "assessments.csv").write_text(
                "Assessment_ID,Claim_Line_ID,Policy_ID,Loss_Date,Coverage_Category,"
                "Expected_Net_Payment,Coverage_Basis,Policy_Effective_From,"
                "Policy_Effective_To,Policy_Snapshot_Date,Qualified_Reviewer_ID,"
                "Qualification_Basis\n"
                "A-1,CL-1,POL-1,2026-08-01,Property,80000.00,"
                "Reviewed policy limits deductible and covered loss,2026-01-01,"
                "2026-12-31,2026-07-31,adjuster-1,licensed claims reviewer\n",
                encoding="utf-8",
            )
            (root / "settlements.csv").write_text(
                "Settlement_ID,Claim_Line_ID,Amount_Paid,Payment_Date\n"
                "S-1,CL-1,50000.00,2026-09-01\n",
                encoding="utf-8",
            )

            batch = audit_insurance_claims(
                client_id="client-1",
                claim_lines=load_insurance_claim_lines_csv(
                    root / "claims.csv", verified=True
                ),
                assessments=load_insurance_assessments_csv(
                    root / "assessments.csv", verified=True
                ),
                settlements=load_insurance_settlements_csv(
                    root / "settlements.csv", verified=True
                ),
            )
            self.assertEqual(batch.exceptions, ())
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.VALIDATED)
            self.assertEqual(finding.potential_recovery_cents, 3_000_000)
            self.assertIn("#row=2", finding.evidence[0].locator)
            self.assertIn("#row=2", finding.rule.source_locator)
            self.assertTrue(finding.rule.source_hash)

    def test_verified_assessment_file_requires_reviewer(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "assessments.csv"
            path.write_text(
                "Assessment_ID,Claim_Line_ID,Policy_ID,Loss_Date,Coverage_Category,"
                "Expected_Net_Payment,Coverage_Basis,Policy_Effective_From,"
                "Policy_Effective_To,Policy_Snapshot_Date,Qualified_Reviewer_ID,"
                "Qualification_Basis\n"
                "A-1,CL-1,POL-1,2026-08-01,Property,80000.00,"
                "Reviewed policy,2026-01-01,2026-12-31,2026-07-31,,licensed reviewer\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_insurance_assessments_csv(path, verified=True)

    def test_zero_settlement_amount_is_valid_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settlements.csv"
            path.write_text(
                "Settlement_ID,Claim_Line_ID,Amount_Paid,Payment_Date\n"
                "DENIAL-1,CL-1,0.00,2026-09-01\n",
                encoding="utf-8",
            )
            rows = load_insurance_settlements_csv(path, verified=True)
            self.assertEqual(rows[0].amount_paid_cents, 0)
            self.assertTrue(rows[0].source_hash)


if __name__ == "__main__":
    unittest.main()
