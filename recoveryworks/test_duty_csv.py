from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.duty import audit_duty_entries
from recoveryworks.branches.duty_csv import (
    load_duty_assessments_csv,
    load_duty_entries_csv,
)


class DutyCsvTests(unittest.TestCase):
    def test_entry_and_reviewed_assessment_flow_to_validated_finding(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            entries = root / "entries.csv"
            assessments = root / "assessments.csv"
            entries.write_text(
                "Entry_Line_ID,Entry_ID,Importer_ID,Broker_ID,Import_Date,HTS_Code,"
                "Origin_Country,Actual_Duty_And_Fees\n"
                "EL-1,E-1,Importer-1,Broker-1,2026-08-01,6109.10.00,CN,300.00\n",
                encoding="utf-8",
            )
            assessments.write_text(
                "Assessment_ID,Entry_Line_ID,Import_Date,HTS_Code,Origin_Country,"
                "Expected_Base_Duty,Expected_Additional_Duty,Expected_MPF,Expected_HMF,"
                "Expected_Other,Schedule_Snapshot_Date,Professional_Reviewer_ID\n"
                "A-1,EL-1,2026-08-01,6109.10.00,CN,165.00,50.00,3.46,1.25,0,"
                "2026-07-31,broker-reviewer-1\n",
                encoding="utf-8",
            )
            batch = audit_duty_entries(
                client_id="Importer-1",
                entries=load_duty_entries_csv(entries, verified=True),
                assessments=load_duty_assessments_csv(
                    assessments,
                    verified=True,
                ),
            )
            self.assertEqual(batch.exceptions, ())
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.VALIDATED)
            self.assertEqual(finding.potential_recovery_cents, 8029)
            self.assertIn("#row=2", finding.evidence[0].locator)
            self.assertTrue(finding.rule.source_hash)

    def test_verified_assessment_csv_requires_reviewer_id(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "assessments.csv"
            path.write_text(
                "Assessment_ID,Entry_Line_ID,Import_Date,HTS_Code,Origin_Country,"
                "Expected_Base_Duty,Expected_Additional_Duty,Expected_MPF,Expected_HMF,"
                "Expected_Other,Schedule_Snapshot_Date,Professional_Reviewer_ID\n"
                "A-1,EL-1,2026-08-01,6109.10.00,CN,165.00,50.00,3.46,1.25,0,"
                "2026-07-31,\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_duty_assessments_csv(path, verified=True)

    def test_unverified_assessment_can_enter_review_without_reviewer(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            entries = root / "entries.csv"
            assessments = root / "assessments.csv"
            entries.write_text(
                "Entry_Line_ID,Entry_ID,Importer_ID,Broker_ID,Import_Date,HTS_Code,"
                "Origin_Country,Actual_Duty_And_Fees\n"
                "EL-1,E-1,Importer-1,Broker-1,2026-08-01,6109.10.00,CN,300.00\n",
                encoding="utf-8",
            )
            assessments.write_text(
                "Assessment_ID,Entry_Line_ID,Import_Date,HTS_Code,Origin_Country,"
                "Expected_Base_Duty,Expected_Additional_Duty,Expected_MPF,Expected_HMF,"
                "Expected_Other,Schedule_Snapshot_Date,Professional_Reviewer_ID\n"
                "A-1,EL-1,2026-08-01,6109.10.00,CN,165.00,50.00,3.46,1.25,0,"
                "2026-07-31,\n",
                encoding="utf-8",
            )
            batch = audit_duty_entries(
                client_id="Importer-1",
                entries=load_duty_entries_csv(entries),
                assessments=load_duty_assessments_csv(assessments),
            )
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.REVIEW)


if __name__ == "__main__":
    unittest.main()
