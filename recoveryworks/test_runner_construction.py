from pathlib import Path
import tempfile
import unittest

from recoveryworks.runner import run_scan360_config


def write_sources(root: Path, *, claimant="client-1", accepted_days=3):
    (root / "entitlements.csv").write_text(
        "Entitlement_ID,Claimant_ID,Project_ID,Counterparty_ID,Change_ID,Event_ID,"
        "Entitled_Amount,Effective_Date,Entitlement_Basis,Entitlement_Reviewer_ID\n"
        f"ENT-1,{claimant},PRJ-1,Owner-1,CO-7,EV-1,100000.00,2026-08-10,"
        "Reviewed clause and priced change,contract-reviewer-1\n",
        encoding="utf-8",
    )
    (root / "events.csv").write_text(
        "Event_ID,Project_ID,Event_Date,Description\n"
        "EV-1,PRJ-1,2026-08-05,Owner-directed access restriction\n",
        encoding="utf-8",
    )
    (root / "mappings.csv").write_text(
        "Mapping_ID,Event_ID,Baseline_Activity_ID,Update_Activity_ID,Mapping_Basis\n"
        "MAP-1,EV-1,B,B,RFI and daily report map event to activity B\n",
        encoding="utf-8",
    )
    (root / "schedules.json").write_text(
        """{
          "versions": [
            {
              "version_id":"BASE",
              "project_id":"PRJ-1",
              "data_date":"2026-08-01",
              "activities":[
                {"activity_id":"A","name":"A","duration_days":5},
                {"activity_id":"B","name":"B","duration_days":5}
              ],
              "relationships":[
                {"predecessor_id":"A","successor_id":"B","relationship_type":"FS"}
              ]
            },
            {
              "version_id":"UPD",
              "project_id":"PRJ-1",
              "data_date":"2026-09-01",
              "activities":[
                {"activity_id":"A","name":"A","duration_days":5},
                {"activity_id":"B","name":"B","duration_days":8}
              ],
              "relationships":[
                {"predecessor_id":"A","successor_id":"B","relationship_type":"FS"}
              ]
            }
          ]
        }""",
        encoding="utf-8",
    )
    (root / "causation.csv").write_text(
        "Review_ID,Entitlement_ID,Event_ID,Baseline_Version_ID,Update_Version_ID,"
        "Accepted_Causation,Accepted_Delay_Days,Review_Date,Qualified_Reviewer_ID\n"
        f"REV-1,ENT-1,EV-1,BASE,UPD,true,{accepted_days},2026-09-15,scheduler-1\n",
        encoding="utf-8",
    )
    (root / "settlements.csv").write_text(
        "Settlement_ID,Entitlement_ID,Amount_Received,Settlement_Date\n"
        "PAY-1,ENT-1,20000.00,2026-09-20\n",
        encoding="utf-8",
    )


def config(*, verified=True):
    return {
        "client_id": "client-1",
        "currency": "USD",
        "construction": {
            "entitlements_csv": "entitlements.csv",
            "events_csv": "events.csv",
            "mappings_csv": "mappings.csv",
            "schedules_json": "schedules.json",
            "causation_reviews_csv": "causation.csv",
            "settlements_csv": "settlements.csv",
            "entitlement_source_verified": verified,
            "event_source_verified": verified,
            "mapping_source_verified": verified,
            "schedule_source_verified": verified,
            "causation_source_verified": verified,
            "settlement_source_verified": verified,
        },
    }


class ConstructionRunnerTests(unittest.TestCase):
    def test_construction_recovery_runs_into_durable_scan360(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root)
            state = root / "private" / "ledger.json"

            first = run_scan360_config(config(), state_path=state, base_dir=root)
            self.assertEqual(first.exceptions, ())
            self.assertEqual(len(first.added_finding_ids), 1)
            self.assertEqual(first.report.totals["validated_cents"], 8_000_000)
            self.assertEqual(
                first.report.branches["construction"]["validated_cents"],
                8_000_000,
            )
            self.assertTrue(state.exists())

            second = run_scan360_config(config(), state_path=state, base_dir=root)
            self.assertEqual(second.added_finding_ids, ())
            self.assertEqual(second.state_head_hash, first.state_head_hash)
            self.assertEqual(second.report.as_dict(), first.report.as_dict())

    def test_unverified_construction_sources_stay_review(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root)
            result = run_scan360_config(
                config(verified=False),
                state_path=root / "ledger.json",
                base_dir=root,
            )
            self.assertEqual(result.report.totals["validated_cents"], 0)
            self.assertEqual(result.report.totals["review_cents"], 8_000_000)
            self.assertEqual(
                result.report.review_backlog[0]["branch"],
                "construction",
            )

    def test_claimant_scope_mismatch_is_hard_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root, claimant="other-client")
            with self.assertRaises(ValueError):
                run_scan360_config(
                    config(),
                    state_path=root / "ledger.json",
                    base_dir=root,
                )

    def test_excess_causation_days_are_exception_not_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root, accepted_days=4)
            result = run_scan360_config(
                config(),
                state_path=root / "ledger.json",
                base_dir=root,
            )
            self.assertEqual(result.added_finding_ids, ())
            self.assertEqual(result.exceptions[0]["branch"], "construction")
            self.assertEqual(
                result.exceptions[0]["code"],
                "ACCEPTED_DELAY_EXCEEDS_CPM_IMPACT",
            )
            self.assertNotIn("construction", result.report.branches)


if __name__ == "__main__":
    unittest.main()
