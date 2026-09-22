import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from ti_prepare_run import COUNTS, prepare_run, write_draft


class PrepareRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.intel = self.root / "intelligence"
        self.intel.mkdir()
        (self.intel / "schemas").mkdir()
        shutil.copyfile(Path(__file__).resolve().parents[1] / "intelligence/schemas/search_run.schema.json",
                        self.intel / "schemas/search_run.schema.json")
        self.rows("worker_profiles.jsonl", [{"worker_id": "HUNTER-01"}, {"worker_id": "HUNTER-02"}])
        self.rows("search_strategies.jsonl", [{"strategy_id": "STRAT:fixture-inspection"}])
        (self.intel / "search_objectives.json").write_text(json.dumps({
            "objectives": [{"search_objective_id": "OBJ:independent-evaluation"}]}))
        # Poison the old template: a helper that copies it will fail assertions.
        (self.intel / "SEARCH_RUN_TEMPLATE.json").write_text(json.dumps({
            "assignment_id": "ASSIGN:000000000000:slot-01", "candidate_count": 99,
            "candidate_dispositions": [{"repository": "owner/repo"}]}))
        self.args = dict(worker="HUNTER-01", strategy="STRAT:fixture-inspection",
                         query_family="independent executable evidence", objective="OBJ:independent-evaluation",
                         intel=self.intel)
        self.claim = {
            "event_type": "CLAIM", "event_id": "EXEC:123456789abc",
            "timestamp": "2026-09-21T01:00:00Z", "claim_id": "CLAIM:abcdef123456",
            "slot_id": "SLOT-01", "worker_id": "HUNTER-01",
            "assignment_id": "ASSIGN:123456789abc:slot-01", "allocator_generation_id": "ALLOCGEN:123456789abc",
            "portfolio_policy_generation_id": "PORTFOLIO:abc123def456", "work_item_id": "WORK:seed:abc123def456",
            "assignment_slot_role": "experiment", "assignment_work_kind": "capability_gap",
            "assignment_source_id": "SEED:gap:cap-002", "assignment_score": 0,
            "routing_mode": "generated", "routing_generation_id": "ROUTING:123456789abc",
            "worker_profile_generation_id": "WORKERS:123456789abc", "routing_score": 0,
            "dispatch_ticket_id": "DISPATCH:123456789abc", "dispatch_generation_id": "DISPATCHGEN:123456789abc",
            "routing_learning_generation_id": "ROUTELEARN:123456789abc", "dispatch_kind": "work_steal",
            "parent_dispatch_ticket_id": "DISPATCH:abc123def456", "presence_generation_id": "PRESENCEGEN:123456789abc",
            "presence_event_id": "PRESENCE:123456789abc", "activation_id": "ACTIVATE:123456789abc",
            "activation_generation_id": "ACTGEN:123456789abc", "claim_schema_version": 16,
        }

    def rows(self, name, rows):
        path = self.intel / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    def bound(self, **kwargs):
        args = dict(self.args, claim_id=self.claim["claim_id"])
        args.update(kwargs)
        return prepare_run(**args)

    def save_claim(self, *other_events):
        self.rows("execution_events/SLOT-01.jsonl", [self.claim, *other_events])

    def assignment(self, **overrides):
        row = {"assignment_id": self.claim["assignment_id"], "slot_id": "SLOT-01",
               "allocator_generation_id": self.claim["allocator_generation_id"],
               "portfolio_policy_generation_id": self.claim["portfolio_policy_generation_id"],
               "work_item_id": self.claim["work_item_id"], "slot_role": "experiment", "work_kind": "capability_gap",
               "source_id": self.claim["assignment_source_id"], "final_score": 0,
               "strategy_id": self.args["strategy"], "search_objective_id": self.args["objective"],
               "work_action": "execute_fixture"}
        row.update(overrides)
        self.rows("hunt_allocations.jsonl", [row])

    def test_unallocated_is_empty_honest_and_read_only(self):
        before = {path: path.read_bytes() for path in self.intel.rglob("*") if path.is_file()}
        started = datetime.now(timezone.utc)
        run = prepare_run(**self.args)
        self.assertGreaterEqual(datetime.fromisoformat(run["timestamp"].replace("Z", "+00:00")), started)
        self.assertEqual(run["allocation_mode"], "unallocated")
        self.assertEqual(run["routing_mode"], "unrouted")
        self.assertEqual(run["work_action"], "search")
        self.assertEqual(run["candidate_dispositions"], [])
        self.assertEqual(run["queries"], [])
        self.assertEqual(run["search_surfaces"], [])
        self.assertEqual(run["coordination_signal_ids"], [])
        self.assertEqual(run["consumed_coordination_signal_ids"], [])
        self.assertEqual(run["search_moves"], [])
        self.assertIsNone(run["recall_rescue_type"])
        self.assertIsNone(run["recall_rescue_found_qualifying_candidate"])
        self.assertIsNone(run["stop_reason_standard"])
        self.assertEqual(run["_draft"]["status"], "incomplete")
        for key in (*COUNTS, "assignment_id", "execution_claim_id", "dispatch_ticket_id", "activation_id"):
            self.assertIsNone(run[key], key)
        self.assertNotIn("000000000000", json.dumps(run))
        self.assertNotIn("owner/repo", json.dumps(run))
        self.assertNotEqual(run["search_run_id"], prepare_run(**self.args)["search_run_id"])
        after = {path: path.read_bytes() for path in self.intel.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_bound_run_copies_actual_provenance_including_zero_scores(self):
        self.save_claim()
        run = self.bound(worker=None)
        self.assertEqual(run["execution_claim_id"], self.claim["claim_id"])
        self.assertEqual(run["assignment_work_item_id"], self.claim["work_item_id"])
        self.assertEqual(run["assignment_score"], 0)
        self.assertEqual(run["routing_score"], 0)
        self.assertEqual(run["execution_worker_id"], "HUNTER-01")
        self.assertEqual(run["dispatch_parent_ticket_id"], self.claim["parent_dispatch_ticket_id"])
        self.assertEqual(run["parent_dispatch_ticket_id"], run["dispatch_parent_ticket_id"])
        self.assertEqual(run["activation_id"], self.claim["activation_id"])
        self.assertEqual(run["seed_ids"], [self.claim["assignment_source_id"]])
        self.assertIsNone(run["work_action"])
        self.assertIsNone(run["candidate_count"])
        self.assertEqual(run["candidate_dispositions"], [])

    def test_actual_assignment_action_is_copied_and_never_guessed(self):
        self.save_claim()
        self.assignment()
        run = self.bound(strategy=None, objective=None)
        self.assertEqual(run["strategy_id"], self.args["strategy"])
        self.assertEqual(run["work_action"], "execute_fixture")
        with self.assertRaisesRegex(ValueError, "work-action"):
            self.bound(work_action="search")
        self.assignment(assignment_id="ASSIGN:abcdef123456:slot-01")
        self.assertIsNone(self.bound()["work_action"])
        with self.assertRaisesRegex(ValueError, "provide --strategy"):
            self.bound(strategy=None)

    def test_claim_must_be_real_unique_and_owned_by_worker(self):
        self.rows("execution_claim_history.jsonl", [self.claim])
        self.rows("activation_claim_packets.jsonl", [self.claim])
        self.rows("shadow/execution_events/SLOT-01.jsonl", [self.claim])
        with self.assertRaisesRegex(ValueError, "exactly one stored CLAIM"):
            self.bound()
        self.save_claim()
        with self.assertRaisesRegex(ValueError, "worker"):
            self.bound(worker="HUNTER-02")
        self.save_claim(copy.deepcopy(self.claim))
        with self.assertRaisesRegex(ValueError, "exactly one stored CLAIM"):
            self.bound()

    def test_rejects_closed_claim_and_existing_canonical_telemetry(self):
        for terminal in ("COMPLETE", "FAIL", "RELEASE"):
            with self.subTest(terminal=terminal):
                self.save_claim(dict(self.claim, event_type=terminal))
                with self.assertRaisesRegex(ValueError, "already ended"):
                    self.bound()
        self.save_claim()
        self.rows("search_runs.jsonl", [{"execution_claim_id": self.claim["claim_id"]}])
        with self.assertRaisesRegex(ValueError, "already has canonical"):
            self.bound()

    def test_rejects_assignment_mismatch_and_template_provenance(self):
        self.save_claim()
        self.assignment(work_item_id="WORK:seed:other")
        with self.assertRaisesRegex(ValueError, "assignment disagrees"):
            self.bound()
        self.rows("hunt_allocations.jsonl", [])
        self.claim["activation_id"] = "ACTIVATE:000000000000"
        self.save_claim()
        with self.assertRaisesRegex(ValueError, "placeholder provenance"):
            self.bound()

    def test_shadow_benchmark_and_measurement_cannot_become_prospective(self):
        for extra in ({"shadow": True}, {"measurement_quality": "benchmark"},
                      {"measurement_quality": "shadow"}, {"benchmark_task_ids": ["01"]},
                      {"assignment_work_kind": "strategy_measurement"}):
            with self.subTest(extra=extra):
                event = dict(self.claim, **extra)
                self.rows("execution_events/SLOT-01.jsonl", [event])
                with self.assertRaises(ValueError):
                    self.bound()

    def test_adaptive_learning_measurement_is_prospective_but_frozen_measurement_stays_blocked(self):
        self.claim["assignment_slot_role"] = "measurement"
        self.claim["assignment_work_kind"] = "learning_measurement"
        self.claim["assignment_source_id"] = "SEED:learn:fixture-inspection"
        self.claim["work_item_id"] = "WORK:seed:learnfixture"
        self.save_claim()
        self.assignment(
            slot_role="measurement",
            work_kind="learning_measurement",
            source_id=self.claim["assignment_source_id"],
            work_item_id=self.claim["work_item_id"],
            work_action="search",
        )
        run = self.bound(strategy=None, objective=None)
        self.assertEqual(run["work_action"], "search")
        self.assertEqual(
            run["assignment_work_kind"],
            "learning_measurement",
        )
        self.assertEqual(
            run["allocation_mode"],
            "generated",
        )
        self.assertEqual(
            run["measurement_quality"],
            "prospective",
        )
        self.assertEqual(
            run["execution_claim_id"],
            self.claim["claim_id"],
        )

        self.claim["assignment_work_kind"] = "strategy_measurement"
        self.save_claim()
        self.assignment(
            slot_role="measurement",
            work_kind="strategy_measurement",
            source_id=self.claim["assignment_source_id"],
            work_item_id=self.claim["work_item_id"],
            work_action="search",
        )
        with self.assertRaisesRegex(
            ValueError,
            "separate benchmark workflow",
        ):
            self.bound()

    def test_schema_routing_enum_is_enforced(self):
        self.claim["routing_mode"] = "none"
        self.save_claim()
        with self.assertRaisesRegex(ValueError, "routing_mode"):
            self.bound()

    def test_manual_override_stays_out_of_generated_portfolio_learning(self):
        self.claim["routing_mode"] = "manual_override"
        self.claim["route_override_reason"] = "Operator assigned this worker to the existing slot."
        self.save_claim()
        run = self.bound()
        self.assertEqual(run["allocation_mode"], "manual_override")
        self.assertEqual(run["routing_mode"], "manual_override")
        self.assertEqual(run["route_override_reason"], self.claim["route_override_reason"])

    def test_qf_id_resolves_to_registered_label(self):
        self.rows("query_families.jsonl", [{"query_family_id": "QF:independent-executable-evidence",
                                           "label": "independent executable evidence"}])
        run = prepare_run(**dict(self.args, query_family="QF:independent-executable-evidence"))
        self.assertEqual(run["query_family"], self.args["query_family"])
        with self.assertRaisesRegex(ValueError, "registered label"):
            prepare_run(**dict(self.args, query_family="QF:replace-with-query"))

    def test_output_refuses_overwrite_and_all_canonical_paths(self):
        draft = prepare_run(**self.args)
        output = self.root / "run-draft.json"
        write_draft(draft, output, intel=self.intel)
        original = output.read_bytes()
        with self.assertRaises(FileExistsError):
            write_draft(draft, output, intel=self.intel)
        self.assertEqual(output.read_bytes(), original)
        for path in (self.intel / "search_runs.jsonl", self.intel / "search_run_spool/draft.json"):
            with self.assertRaisesRegex(ValueError, "outside intelligence"):
                write_draft(draft, path, intel=self.intel)
        link = self.root / "linked-intel"
        link.symlink_to(self.intel, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "outside intelligence"):
            write_draft(draft, link / "draft.json", intel=self.intel)


if __name__ == "__main__":
    unittest.main()
