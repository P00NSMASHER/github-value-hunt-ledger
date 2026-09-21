"""Telemetry integrity tests: no lost history, invented fields, or silent conflicts."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import ti_ingest_runs as intake


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.intel = self.root / "intelligence"
        for directory in ("schemas", "search_run_spool", "search_runs"):
            (self.intel / directory).mkdir(parents=True, exist_ok=True)
        source = Path(__file__).resolve().parents[1] / "intelligence/schemas/search_run.schema.json"
        shutil.copyfile(source, self.intel / "schemas/search_run.schema.json")
        self.jsonl("search_strategies.jsonl", [{"strategy_id": "STRAT:example"}])
        self.jsonl("capabilities.jsonl", [{"capability_id": "CAP-001"}])
        self.json("search_objectives.json", {"objectives": [{"search_objective_id": "OBJ:example"}]})
        self.json("reason_codes.json", {"positive": ["strong_component"]})
        self.json("query_family_aliases.json", {})
        self.json("strategy_evaluation_sets.json", {"sets": [{"evaluation_set_id": "EVAL:example", "strategy_ids": ["STRAT:example"], "task_ids": ["01"]}]})
        self.ledger = self.intel / "search_runs.jsonl"
        self.ledger.write_bytes(b"")

    def json(self, name, value):
        (self.intel / name).write_text(json.dumps(value), encoding="utf-8")

    def jsonl(self, name, rows):
        (self.intel / name).write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def run_record(self, rid="RUN:test"):
        return {"schema_version": 4, "search_run_id": rid, "strategy_id": "STRAT:example",
                "query_family": "test query", "query_family_id": "QF:test-query",
                "search_objective_id": "OBJ:example", "measurement_quality": "prospective",
                "candidate_count": 3, "deep_inspected": 2, "retained_count": 1, "master_promoted_count": 0}

    def submit(self, row, name="submission", folder="search_run_spool"):
        path = self.intel / folder / f"{name}.json"
        path.write_text(json.dumps(row, indent=2), encoding="utf-8")
        return path

    def assert_blocked(self):
        before = self.ledger.read_bytes()
        report = intake.ingest(self.root, write=True)
        self.assertTrue(report["errors"])
        self.assertEqual(report["appended_runs"], 0)
        self.assertEqual(before, self.ledger.read_bytes())
        return report

    def test_deterministic_idempotent_append_preserves_existing_bytes(self):
        old = {"search_run_id": "RUN:historical", "unknown": None}
        original = json.dumps(old, indent=None).encode("utf-8")  # No final newline.
        self.ledger.write_bytes(original)
        self.submit(self.run_record("RUN:z"), "aaa")
        self.submit(self.run_record("RUN:a"), "zzz", "search_runs")
        self.submit(self.run_record("RUN:a"), "replay")
        report = intake.ingest(self.root, write=True)
        self.assertEqual(report["appended_runs"], 2)
        self.assertEqual(report["duplicate_submission_files"], 1)
        content = self.ledger.read_bytes()
        self.assertTrue(content.startswith(original + b"\n"))
        rows = intake.read_rows(self.ledger)
        self.assertEqual([r["search_run_id"] for r in rows], ["RUN:historical", "RUN:a", "RUN:z"])
        second = intake.ingest(self.root, write=True)
        self.assertEqual(second["appended_runs"], 0)
        self.assertEqual(second["replayed_files"], 3)
        self.assertEqual(self.ledger.read_bytes(), content)
        self.assertEqual(len(list((self.intel / "search_run_spool").glob("*.json"))), 2)

    def test_read_only_check_reports_pending_without_writing(self):
        self.submit(self.run_record())
        report = intake.ingest(self.root)
        self.assertEqual(report["pending_runs"], 1)
        self.assertEqual(self.ledger.read_bytes(), b"")
        self.assertFalse((self.intel / ".search_runs.ingest.lock").exists())

    def test_conflict_with_ledger_rejects_entire_batch(self):
        self.jsonl("search_runs.jsonl", [self.run_record()])
        conflict = self.run_record()
        conflict["candidate_count"] = 99
        self.submit(conflict)
        self.submit(self.run_record("RUN:new"), "new")
        self.assertIn("conflicting search_run_id", self.assert_blocked()["errors"][0])

    def test_conflict_between_submissions_rejects_entire_batch(self):
        self.submit(self.run_record())
        conflict = self.run_record()
        conflict["notes"] = "different immutable submission"
        self.submit(conflict, "other", "search_runs")
        self.assertIn("conflicting submissions", self.assert_blocked()["errors"][0])

    def test_invalid_shapes_counts_and_references_are_rejected(self):
        cases = [{"candidate_count": True}, {"deep_inspected": 4}, {"candidate_count": -1},
                 {"strategy_id": "STRAT:unknown"}, {"search_objective_id": "OBJ:unknown"},
                 {"query_family_id": "QF:wrong"}, {"new_capability_ids": ["CAP-999"]},
                 {"candidate_dispositions": [{"repository": "owner/repo", "status": "watch"}]},
                 {"measurement_quality": "made-up"}, {"candidate_dispositions": [None]},
                 {"elapsed_minutes": -1}, {"candidate_count": "3"}]
        for changes in cases:
            with self.subTest(changes=changes):
                row = self.run_record()
                row.update(changes)
                self.submit(row)
                self.assert_blocked()

    def test_required_version_fields_and_benchmark_metadata_rejected(self):
        row = self.run_record()
        del row["search_objective_id"]
        self.submit(row)
        self.assert_blocked()
        row = self.run_record()
        row.update(measurement_quality="benchmark", benchmark_task_ids=["02"],
                   comparison_group_id="CMP:test", evaluation_set_id="EVAL:example")
        self.submit(row)
        self.assertIn("outside evaluation set", self.assert_blocked()["errors"][0])

    def test_invalid_json_duplicate_keys_and_nonfinite_numbers_rejected(self):
        for raw in ('{"search_run_id":"RUN:a","search_run_id":"RUN:b"}', '{"x":NaN}',
                    '{"x":1e999}', '{', '[]'):
            with self.subTest(raw=raw):
                (self.intel / "search_run_spool/bad.json").write_text(raw)
                self.assert_blocked()

    def test_old_exact_replay_is_not_reinterpreted_or_upgraded(self):
        row = {"search_run_id": "RUN:legacy", "schema_version": 11, "candidate_count": None}
        self.jsonl("search_runs.jsonl", [row])
        self.submit(row)
        before = self.ledger.read_bytes()
        report = intake.ingest(self.root, write=True)
        self.assertEqual(report["replayed_files"], 1)
        self.assertEqual(report["errors"], [])
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_draft_marker_blocks_new_submissions_even_if_false_or_null(self):
        for marker in ({"review_required": True}, False, None):
            with self.subTest(marker=marker):
                row = self.run_record()
                row["_draft"] = marker
                self.submit(row)
                self.assertIn("record actual observations and complete review", self.assert_blocked()["errors"][0])

    def test_historical_exact_replay_with_draft_marker_is_preserved(self):
        row = self.run_record()
        row["_draft"] = {"historical": True}
        self.jsonl("search_runs.jsonl", [row])
        self.submit(row)
        before = self.ledger.read_bytes()
        report = intake.ingest(self.root, write=True)
        self.assertEqual(report["replayed_files"], 1)
        self.assertEqual(report["errors"], [])
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_missing_historical_fields_and_nulls_are_preserved(self):
        row = self.run_record()
        del row["schema_version"]
        del row["query_family_id"]
        del row["search_objective_id"]
        row["candidate_count"] = None
        row["extra_observation"] = {"unavailable": None}
        self.submit(row)
        self.assertEqual(intake.ingest(self.root, write=True)["appended_runs"], 1)
        self.assertEqual(intake.read_rows(self.ledger), [row])

    def test_duplicate_canonical_ids_are_not_silently_deduplicated(self):
        self.jsonl("search_runs.jsonl", [self.run_record(), self.run_record()])
        with self.assertRaisesRegex(intake.IntakeError, "duplicate search_run_id"):
            intake.ingest(self.root, write=True)

    def test_lock_prevents_second_integrator(self):
        lock = self.intel / ".search_runs.ingest.lock"
        lock.mkdir()
        self.submit(self.run_record())
        with self.assertRaisesRegex(intake.IntakeError, "lock exists"):
            intake.ingest(self.root, write=True)
        self.assertTrue(lock.exists())
        self.assertEqual(self.ledger.read_bytes(), b"")

    def test_unsupported_schema_change_fails_closed(self):
        path = self.intel / "schemas/search_run.schema.json"
        schema = json.loads(path.read_text())
        schema["anyOf"] = []
        path.write_text(json.dumps(schema))
        with self.assertRaisesRegex(intake.IntakeError, "unsupported schema keywords"):
            intake.ingest(self.root, write=True)

    def test_changed_ledger_is_not_overwritten(self):
        self.submit(self.run_record())
        real_build_plan = intake.build_plan
        foreign = b'{"search_run_id":"RUN:foreign"}\n'
        def concurrent_append(root):
            plan = real_build_plan(root)
            with self.ledger.open("ab") as stream:
                stream.write(foreign)
            return plan
        with patch.object(intake, "build_plan", concurrent_append):
            with self.assertRaisesRegex(intake.IntakeError, "ledger changed"):
                intake.ingest(self.root, write=True)
        self.assertEqual(self.ledger.read_bytes(), foreign)

    def test_changed_submission_is_not_appended(self):
        path = self.submit(self.run_record())
        real_build_plan = intake.build_plan
        def concurrent_mutation(root):
            plan = real_build_plan(root)
            path.write_text("{}")
            return plan
        with patch.object(intake, "build_plan", concurrent_mutation):
            with self.assertRaisesRegex(intake.IntakeError, "submission changed"):
                intake.ingest(self.root, write=True)
        self.assertEqual(self.ledger.read_bytes(), b"")


if __name__ == "__main__":
    unittest.main()
