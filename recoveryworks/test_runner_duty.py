from pathlib import Path
import tempfile
import unittest

from recoveryworks.runner import run_scan360_config


def write_sources(root: Path, *, importer="Importer-1"):
    (root / "entries.csv").write_text(
        "Entry_Line_ID,Entry_ID,Importer_ID,Broker_ID,Import_Date,HTS_Code,"
        "Origin_Country,Actual_Duty_And_Fees\n"
        f"EL-1,E-1,{importer},Broker-1,2026-08-01,6109.10.00,CN,300.00\n",
        encoding="utf-8",
    )
    (root / "assessments.csv").write_text(
        "Assessment_ID,Entry_Line_ID,Import_Date,HTS_Code,Origin_Country,"
        "Expected_Base_Duty,Expected_Additional_Duty,Expected_MPF,Expected_HMF,"
        "Expected_Other,Schedule_Snapshot_Date,Professional_Reviewer_ID\n"
        "A-1,EL-1,2026-08-01,6109.10.00,CN,165.00,50.00,3.46,1.25,0,"
        "2026-07-31,broker-reviewer-1\n",
        encoding="utf-8",
    )


class DutyRunnerTests(unittest.TestCase):
    def test_duty_recovery_flows_into_scan360(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root)
            config = {
                "client_id": "Importer-1",
                "currency": "USD",
                "duty": {
                    "entries_csv": "entries.csv",
                    "assessments_csv": "assessments.csv",
                    "entry_source_verified": True,
                    "assessment_source_verified": True,
                },
            }
            state = root / "private" / "ledger.json"
            first = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(first.exceptions, ())
            self.assertEqual(len(first.added_finding_ids), 1)
            self.assertEqual(first.report.branches["duty"]["validated_cents"], 8029)

            second = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(second.added_finding_ids, ())
            self.assertEqual(second.state_head_hash, first.state_head_hash)

    def test_importer_scope_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root, importer="Other-Importer")
            with self.assertRaises(ValueError):
                run_scan360_config(
                    {
                        "client_id": "Importer-1",
                        "duty": {
                            "entries_csv": "entries.csv",
                            "assessments_csv": "assessments.csv",
                            "entry_source_verified": True,
                            "assessment_source_verified": True,
                        },
                    },
                    state_path=root / "ledger.json",
                    base_dir=root,
                )


if __name__ == "__main__":
    unittest.main()
