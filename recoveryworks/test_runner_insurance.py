from pathlib import Path
import tempfile
import unittest

from recoveryworks.runner import run_scan360_config


def write_sources(root: Path, *, claimant="client-1"):
    (root / "claims.csv").write_text(
        "Claim_Line_ID,Claimant_ID,Insurer_ID,Policy_ID,Loss_Date,"
        "Coverage_Category,Claimed_Amount\n"
        f"CL-1,{claimant},Insurer-1,POL-1,2026-08-01,Property,100000.00\n",
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


class InsuranceRunnerTests(unittest.TestCase):
    def test_insurance_recovery_runs_into_durable_scan360(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root)
            config = {
                "client_id": "client-1",
                "currency": "USD",
                "insurance": {
                    "claim_lines_csv": "claims.csv",
                    "assessments_csv": "assessments.csv",
                    "settlements_csv": "settlements.csv",
                    "claim_source_verified": True,
                    "assessment_source_verified": True,
                    "settlement_source_verified": True,
                },
            }
            state = root / "private" / "ledger.json"
            first = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(first.exceptions, ())
            self.assertEqual(len(first.added_finding_ids), 1)
            self.assertEqual(
                first.report.branches["insurance"]["validated_cents"],
                3_000_000,
            )

            second = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(second.added_finding_ids, ())
            self.assertEqual(second.state_head_hash, first.state_head_hash)
            self.assertEqual(second.report.as_dict(), first.report.as_dict())

    def test_claimant_scope_mismatch_is_hard_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root, claimant="other-client")
            with self.assertRaises(ValueError):
                run_scan360_config(
                    {
                        "client_id": "client-1",
                        "insurance": {
                            "claim_lines_csv": "claims.csv",
                            "assessments_csv": "assessments.csv",
                            "settlements_csv": "settlements.csv",
                            "claim_source_verified": True,
                            "assessment_source_verified": True,
                            "settlement_source_verified": True,
                        },
                    },
                    state_path=root / "ledger.json",
                    base_dir=root,
                )

    def test_unverified_sources_stay_review(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root)
            result = run_scan360_config(
                {
                    "client_id": "client-1",
                    "insurance": {
                        "claim_lines_csv": "claims.csv",
                        "assessments_csv": "assessments.csv",
                        "settlements_csv": "settlements.csv",
                        "claim_source_verified": False,
                        "assessment_source_verified": False,
                        "settlement_source_verified": False,
                    },
                },
                state_path=root / "ledger.json",
                base_dir=root,
            )
            self.assertEqual(result.report.totals["validated_cents"], 0)
            self.assertEqual(result.report.totals["review_cents"], 3_000_000)


if __name__ == "__main__":
    unittest.main()
