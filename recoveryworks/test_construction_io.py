from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.construction import (
    audit_construction_recovery,
    calculate_cpm,
)
from recoveryworks.branches.construction_io import (
    load_causation_reviews_csv,
    load_construction_entitlements_csv,
    load_construction_events_csv,
    load_construction_settlements_csv,
    load_event_activity_mappings_csv,
    load_schedule_versions_json,
)


def write_sources(root: Path, *, claimant="client-1", accepted_days=3):
    (root / "entitlements.csv").write_text(
        "Entitlement_ID,Claimant_ID,Project_ID,Counterparty_ID,Change_ID,Event_ID,"
        "Entitled_Amount,Effective_Date,Entitlement_Basis,Entitlement_Reviewer_ID\n"
        f"ENT-1,{claimant},PRJ-1,Owner-1,CO-7,EV-1,100000.00,2026-08-10,"
        "Reviewed clause 7.4 and priced change,contract-reviewer-1\n",
        encoding="utf-8",
    )
    (root / "events.csv").write_text(
        "Event_ID,Project_ID,Event_Date,Description\n"
        "EV-1,PRJ-1,2026-08-05,Owner-directed access restriction\n",
        encoding="utf-8",
    )
    (root / "mappings.csv").write_text(
        "Mapping_ID,Event_ID,Baseline_Activity_ID,Update_Activity_ID,Mapping_Basis\n"
        "MAP-1,EV-1,B,B,RFI and daily report link event to activity B\n",
        encoding="utf-8",
    )
    (root / "schedules.json").write_text(
        """{
          "versions": [
            {
              "version_id": "BASE",
              "project_id": "PRJ-1",
              "data_date": "2026-08-01",
              "label": "Approved baseline",
              "activities": [
                {"activity_id": "A", "name": "Start work", "duration_days": 5},
                {"activity_id": "B", "name": "Affected work", "duration_days": 5}
              ],
              "relationships": [
                {"predecessor_id": "A", "successor_id": "B", "relationship_type": "FS"}
              ]
            },
            {
              "version_id": "UPD",
              "project_id": "PRJ-1",
              "data_date": "2026-09-01",
              "label": "September update",
              "activities": [
                {"activity_id": "A", "name": "Start work", "duration_days": 5},
                {"activity_id": "B", "name": "Affected work", "duration_days": 8}
              ],
              "relationships": [
                {"predecessor_id": "A", "successor_id": "B", "relationship_type": "FS"}
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


class ConstructionIoTests(unittest.TestCase):
    def test_real_files_produce_versioned_validated_construction_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root)
            entitlements = load_construction_entitlements_csv(
                root / "entitlements.csv", verified=True
            )
            events = load_construction_events_csv(root / "events.csv", verified=True)
            mappings = load_event_activity_mappings_csv(
                root / "mappings.csv", verified=True
            )
            schedules = load_schedule_versions_json(
                root / "schedules.json", verified=True
            )
            reviews = load_causation_reviews_csv(
                root / "causation.csv", verified=True
            )
            settlements = load_construction_settlements_csv(
                root / "settlements.csv", verified=True
            )

            self.assertEqual(schedules[0].version_id, "BASE")
            self.assertEqual(schedules[1].version_id, "UPD")
            self.assertEqual(schedules[0].source_hash, schedules[1].source_hash)
            self.assertNotEqual(
                schedules[0].source_locator,
                schedules[1].source_locator,
            )
            self.assertIn("#versions[0]", schedules[0].source_locator)
            self.assertEqual(calculate_cpm(schedules[0]).project_duration_days, 10)
            self.assertEqual(calculate_cpm(schedules[1]).project_duration_days, 13)

            batch = audit_construction_recovery(
                client_id="client-1",
                entitlements=entitlements,
                events=events,
                mappings=mappings,
                schedules=schedules,
                causation_reviews=reviews,
                settlements=settlements,
            )
            self.assertEqual(batch.exceptions, ())
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.VALIDATED)
            self.assertEqual(finding.potential_recovery_cents, 8_000_000)
            self.assertEqual(
                finding.metadata["baseline_source_hash"],
                schedules[0].source_hash,
            )
            self.assertEqual(
                finding.metadata["update_source_hash"],
                schedules[1].source_hash,
            )
            self.assertIn("#row=2", finding.rule.source_locator)

    def test_verified_entitlement_file_requires_entitlement_reviewer(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root)
            text = (root / "entitlements.csv").read_text()
            text = text.replace(",contract-reviewer-1\n", ",\n")
            (root / "entitlements.csv").write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError):
                load_construction_entitlements_csv(
                    root / "entitlements.csv", verified=True
                )

    def test_verified_causation_file_requires_qualified_reviewer(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root)
            text = (root / "causation.csv").read_text()
            text = text.replace(",scheduler-1\n", ",\n")
            (root / "causation.csv").write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError):
                load_causation_reviews_csv(
                    root / "causation.csv", verified=True
                )

    def test_unsupported_schedule_relationship_type_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root)
            text = (root / "schedules.json").read_text().replace(
                '"relationship_type": "FS"',
                '"relationship_type": "SS"',
                1,
            )
            (root / "schedules.json").write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError):
                load_schedule_versions_json(root / "schedules.json")

    def test_causation_review_cannot_precede_update_schedule(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_sources(root)
            text = (root / "causation.csv").read_text().replace(
                "2026-09-15,scheduler-1",
                "2026-08-15,scheduler-1",
            )
            (root / "causation.csv").write_text(text, encoding="utf-8")
            batch = audit_construction_recovery(
                client_id="client-1",
                entitlements=load_construction_entitlements_csv(
                    root / "entitlements.csv", verified=True
                ),
                events=load_construction_events_csv(
                    root / "events.csv", verified=True
                ),
                mappings=load_event_activity_mappings_csv(
                    root / "mappings.csv", verified=True
                ),
                schedules=load_schedule_versions_json(
                    root / "schedules.json", verified=True
                ),
                causation_reviews=load_causation_reviews_csv(
                    root / "causation.csv", verified=True
                ),
                settlements=load_construction_settlements_csv(
                    root / "settlements.csv", verified=True
                ),
            )
            self.assertEqual(batch.observations, ())
            self.assertEqual(
                batch.exceptions[0].code,
                "CAUSATION_REVIEW_PRECEDES_UPDATE",
            )


if __name__ == "__main__":
    unittest.main()
