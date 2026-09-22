from pathlib import Path
import tempfile
import unittest

from recoveryworks.runner import run_scan360_config


def write_sources(root: Path, *, purchaser="client-1"):
    (root / "tax_lines.csv").write_text(
        "Tax_Line_ID,Invoice_ID,Purchaser_ID,Vendor_ID,Transaction_Date,"
        "Jurisdiction,Tax_Category,Taxable_Basis,Actual_Tax\n"
        f"TL-1,INV-1,{purchaser},Vendor-1,2026-08-01,US-PA,Software,1000.00,100.00\n",
        encoding="utf-8",
    )
    (root / "assessments.csv").write_text(
        "Assessment_ID,Tax_Line_ID,Transaction_Date,Jurisdiction,Tax_Category,"
        "Expected_Tax,Taxability_Basis,Rule_Snapshot_Date,Professional_Reviewer_ID\n"
        "A-1,TL-1,2026-08-01,US-PA,Software,60.00,"
        "Reviewed software taxability,2026-07-31,tax-reviewer-1\n",
        encoding="utf-8",
    )


class TaxRunnerTests(unittest.TestCase):
    def test_tax_recovery_runs_into_durable_scan360(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root)
            config = {
                "client_id": "client-1",
                "currency": "USD",
                "tax": {
                    "lines_csv": "tax_lines.csv",
                    "assessments_csv": "assessments.csv",
                    "line_source_verified": True,
                    "assessment_source_verified": True,
                },
            }
            state = root / "private" / "ledger.json"
            first = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(first.exceptions, ())
            self.assertEqual(len(first.added_finding_ids), 1)
            self.assertEqual(first.report.branches["tax"]["validated_cents"], 4000)

            second = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(second.added_finding_ids, ())
            self.assertEqual(second.state_head_hash, first.state_head_hash)
            self.assertEqual(second.report.as_dict(), first.report.as_dict())

    def test_tax_purchaser_scope_mismatch_is_hard_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root, purchaser="other-client")
            with self.assertRaises(ValueError):
                run_scan360_config(
                    {
                        "client_id": "client-1",
                        "tax": {
                            "lines_csv": "tax_lines.csv",
                            "assessments_csv": "assessments.csv",
                            "line_source_verified": True,
                            "assessment_source_verified": True,
                        },
                    },
                    state_path=root / "ledger.json",
                    base_dir=root,
                )

    def test_unverified_tax_sources_stay_review(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root)
            # The assessment itself must be structurally valid, but source verification
            # flags may remain false and must keep dollars in REVIEW.
            result = run_scan360_config(
                {
                    "client_id": "client-1",
                    "tax": {
                        "lines_csv": "tax_lines.csv",
                        "assessments_csv": "assessments.csv",
                        "line_source_verified": False,
                        "assessment_source_verified": False,
                    },
                },
                state_path=root / "ledger.json",
                base_dir=root,
            )
            self.assertEqual(result.report.totals["validated_cents"], 0)
            self.assertEqual(result.report.totals["review_cents"], 4000)


if __name__ == "__main__":
    unittest.main()
