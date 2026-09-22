from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.tax import audit_tax_lines
from recoveryworks.branches.tax_csv import (
    load_tax_assessments_csv,
    load_tax_lines_csv,
)


class TaxCsvTests(unittest.TestCase):
    def test_files_flow_to_validated_tax_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lines = root / "tax_lines.csv"
            assessments = root / "assessments.csv"

            lines.write_text(
                "Tax_Line_ID,Invoice_ID,Purchaser_ID,Vendor_ID,Transaction_Date,"
                "Jurisdiction,Tax_Category,Taxable_Basis,Actual_Tax\n"
                "TL-1,INV-1,client,Vendor-1,2026-08-01,US-PA,Software,1000.00,100.00\n",
                encoding="utf-8",
            )
            assessments.write_text(
                "Assessment_ID,Tax_Line_ID,Transaction_Date,Jurisdiction,Tax_Category,"
                "Expected_Tax,Taxability_Basis,Rule_Snapshot_Date,Professional_Reviewer_ID\n"
                "A-1,TL-1,2026-08-01,US-PA,Software,60.00,"
                "Reviewed software taxability,2026-07-31,tax-reviewer-1\n",
                encoding="utf-8",
            )

            batch = audit_tax_lines(
                client_id="client",
                lines=load_tax_lines_csv(lines, verified=True),
                assessments=load_tax_assessments_csv(assessments, verified=True),
            )
            self.assertEqual(batch.exceptions, ())
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.VALIDATED)
            self.assertEqual(finding.potential_recovery_cents, 4000)
            self.assertIn("#row=2", finding.evidence[0].locator)
            self.assertIn("#row=2", finding.rule.source_locator)
            self.assertTrue(finding.rule.source_hash)

    def test_verified_assessment_csv_requires_professional_reviewer(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "assessments.csv"
            path.write_text(
                "Assessment_ID,Tax_Line_ID,Transaction_Date,Jurisdiction,Tax_Category,"
                "Expected_Tax,Taxability_Basis,Rule_Snapshot_Date,Professional_Reviewer_ID\n"
                "A-1,TL-1,2026-08-01,US-PA,Software,60.00,"
                "Reviewed software taxability,2026-07-31,\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_tax_assessments_csv(path, verified=True)

    def test_verified_assessment_csv_requires_rule_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "assessments.csv"
            path.write_text(
                "Assessment_ID,Tax_Line_ID,Transaction_Date,Jurisdiction,Tax_Category,"
                "Expected_Tax,Taxability_Basis,Rule_Snapshot_Date,Professional_Reviewer_ID\n"
                "A-1,TL-1,2026-08-01,US-PA,Software,60.00,"
                "Reviewed software taxability,,tax-reviewer-1\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_tax_assessments_csv(path, verified=True)


if __name__ == "__main__":
    unittest.main()
