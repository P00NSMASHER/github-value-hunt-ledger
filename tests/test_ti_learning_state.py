import tempfile
import unittest
from pathlib import Path

from production.training_environment import split_for_run
from tools.ti_learning_state import compile_state


class LearningStateIntegrationTests(unittest.TestCase):
    def search_run(self, index, *, deep=4, retained=1):
        return {
            "schema_version": 16,
            "search_run_id": f"RUN:test:{index}",
            "timestamp": f"2026-09-{10 + index:02d}T00:00:00Z",
            "work_action": "search",
            "measurement_quality": "prospective",
            "strategy_id": "STRAT:integration-test",
            "query_family_id": "QF:integration-test",
            "candidate_count": max(1, deep),
            "deep_inspected": deep,
            "retained_count": retained,
            "master_promoted_count": 0,
            "new_capability_ids": [],
            "search_moves": [],
        }

    def train_runs(self, count):
        rows = []
        index = 1
        while len(rows) < count:
            row = self.search_run(index)
            if split_for_run(row) == "train":
                rows.append(row)
            index += 1
        return rows

    def confirm_run(self):
        index = 1
        while True:
            row = self.search_run(index)
            if split_for_run(row) == "confirm":
                return row
            index += 1

    def test_policy_support_requires_same_runs_that_can_train_reward(self):
        runs = self.train_runs(5)
        runs.append(
            {
                "schema_version": 10,
                "search_run_id": "RUN:legacy:execution-only",
                "date": "2026-09-20",
                "work_action": None,
                "measurement_quality": "prospective",
                "strategy_id": "STRAT:integration-test",
                "query_family_id": "QF:integration-test",
                "candidate_count": 0,
                "deep_inspected": 0,
                "retained_count": 0,
                "master_promoted_count": 0,
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            state = compile_state(runs, [], Path(tmp))

        records = {
            row["key"]: row
            for row in state["memory"]["records"]
        }
        strategy = records["STRAT:integration-test"]
        self.assertEqual(strategy["visits"], 5)
        self.assertEqual(strategy["support"]["measured_runs"], 5)
        self.assertEqual(strategy["support"]["deep_inspections"], 20)
        self.assertTrue(strategy["eligible_for_policy_consideration"])

    def test_four_valid_runs_do_not_unlock_policy_prior(self):
        runs = self.train_runs(4)
        with tempfile.TemporaryDirectory() as tmp:
            state = compile_state(runs, [], Path(tmp))

        strategy = next(
            row
            for row in state["memory"]["records"]
            if row["key"] == "STRAT:integration-test"
        )
        self.assertEqual(strategy["support"]["measured_runs"], 4)
        self.assertEqual(strategy["support"]["deep_inspections"], 16)
        self.assertFalse(strategy["eligible_for_policy_consideration"])

    def test_confirm_episode_does_not_update_memory_or_support(self):
        train = self.train_runs(1)[0]
        confirm = self.confirm_run()
        with tempfile.TemporaryDirectory() as tmp:
            state = compile_state(
                [train, confirm],
                [],
                Path(tmp),
            )

        strategy = next(
            row
            for row in state["memory"]["records"]
            if row["key"] == "STRAT:integration-test"
        )
        self.assertEqual(strategy["visits"], 1)
        self.assertEqual(
            strategy["support"]["measured_runs"],
            1,
        )
        self.assertEqual(
            state["training_environment"][
                "split_counts"
            ].get("confirm"),
            1,
        )

    def test_generated_state_is_deterministic_for_identical_sources(self):
        runs = [self.search_run(1)]
        with tempfile.TemporaryDirectory() as tmp:
            first = compile_state(runs, [], Path(tmp))
            second = compile_state(runs, [], Path(tmp))

        self.assertEqual(
            first["source_snapshot_sha256"],
            second["source_snapshot_sha256"],
        )
        self.assertEqual(first["source_through"], second["source_through"])
        self.assertNotIn("generated_at", first)


if __name__ == "__main__":
    unittest.main()
