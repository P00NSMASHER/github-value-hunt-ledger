import copy
import unittest

from production.learning_curriculum import (
    build_learning_curriculum,
    validate_learning_curriculum,
)


def strategy(sid):
    return {
        "strategy_id": sid,
        "name": sid.split(":", 1)[-1],
        "status": "active",
    }


def memory_row(
    sid,
    *,
    runs=0,
    deep=0,
    confirm_runs=0,
    confirm_deep=0,
    train_ready=False,
    confirm_ready=False,
    eligible=False,
    status="gathering_evidence",
    q=0.0,
):
    return {
        "key": sid,
        "kind": "STRATEGY",
        "q_value": q,
        "support": {
            "measured_runs": runs,
            "deep_inspections": deep,
            "mean_reward": 0.2 if runs else 0.0,
            "min_reward": 0.1 if runs else None,
            "positive_runs": runs,
        },
        "confirm_support": {
            "measured_runs": confirm_runs,
            "deep_inspections": confirm_deep,
            "mean_reward": 0.2 if confirm_runs else 0.0,
            "min_reward": 0.1 if confirm_runs else None,
            "positive_runs": confirm_runs,
        },
        "train_evidence_ready": train_ready,
        "confirm_evidence_ready": confirm_ready,
        "eligible_for_policy_consideration": eligible,
        "generalization_status": status,
    }


class LearningCurriculumTests(unittest.TestCase):
    def build(self, rows):
        strategies = [
            strategy("STRAT:near-a"),
            strategy("STRAT:near-b"),
            strategy("STRAT:zero-a"),
            strategy("STRAT:zero-b"),
            strategy("STRAT:suppressed"),
        ]
        state = {
            "policy_gate": {
                "minimum_measured_runs": 5,
                "minimum_deep_inspections": 20,
                "minimum_confirm_runs": 2,
                "minimum_confirm_deep_inspections": 6,
            },
            "memory": {"records": rows},
        }
        policy = {
            "strategy_allocation": [
                {"strategy_id": row["strategy_id"], "allocation": 0.2}
                for row in strategies
            ]
        }
        return build_learning_curriculum(
            state,
            strategies,
            policy,
        )

    def test_two_gate_closing_plus_one_zero_run_are_reserved(self):
        curriculum = self.build(
            [
                memory_row("STRAT:near-a", runs=4, deep=12),
                memory_row("STRAT:near-b", runs=3, deep=15),
                memory_row(
                    "STRAT:suppressed",
                    runs=5,
                    deep=20,
                    train_ready=True,
                    status="overfit_signal",
                ),
            ]
        )
        selected = [
            row["strategy_id"]
            for row in curriculum["recommended_measurements"]
        ]
        self.assertEqual(selected[:2], ["STRAT:near-a", "STRAT:near-b"])
        self.assertEqual(selected[2], "STRAT:zero-a")
        self.assertNotIn("STRAT:suppressed", selected)
        self.assertEqual(validate_learning_curriculum(curriculum), [])

    def test_confirm_measurement_outranks_train_measurement(self):
        curriculum = self.build(
            [
                memory_row(
                    "STRAT:near-a",
                    runs=5,
                    deep=20,
                    train_ready=True,
                ),
                memory_row("STRAT:near-b", runs=4, deep=19),
            ]
        )
        first = curriculum["recommended_measurements"][0]
        self.assertEqual(first["strategy_id"], "STRAT:near-a")
        self.assertEqual(first["phase"], "confirm_measurement")

    def test_q_value_does_not_change_measurement_selection(self):
        rows = [
            memory_row("STRAT:near-a", runs=4, deep=12, q=-1.0),
            memory_row("STRAT:near-b", runs=3, deep=15, q=1.0),
        ]
        first = self.build(rows)
        changed = copy.deepcopy(rows)
        changed[0]["q_value"] = 1.0
        changed[1]["q_value"] = -1.0
        second = self.build(changed)
        self.assertEqual(
            [
                row["strategy_id"]
                for row in first["recommended_measurements"]
            ],
            [
                row["strategy_id"]
                for row in second["recommended_measurements"]
            ],
        )
        self.assertFalse(first["uses_q_value_for_selection"])

    def test_blind_partition_rule_is_mandatory(self):
        curriculum = self.build(
            [memory_row("STRAT:near-a", runs=4, deep=12)]
        )
        rec = curriculum["recommended_measurements"][0]
        self.assertIn("Do not calculate", rec["blind_partition_rule"])
        tampered = copy.deepcopy(curriculum)
        tampered["recommended_measurements"][0]["blind_partition_rule"] = ""
        self.assertIn(
            "missing_blind_partition_rule:STRAT:near-a",
            validate_learning_curriculum(tampered),
        )

    def test_confirmed_strategy_is_not_remeasured_for_quota(self):
        curriculum = self.build(
            [
                memory_row(
                    "STRAT:near-a",
                    runs=5,
                    deep=20,
                    confirm_runs=2,
                    confirm_deep=6,
                    train_ready=True,
                    confirm_ready=True,
                    eligible=True,
                    status="confirmed",
                ),
                memory_row("STRAT:near-b", runs=4, deep=12),
            ]
        )
        selected = {
            row["strategy_id"]
            for row in curriculum["recommended_measurements"]
        }
        self.assertNotIn("STRAT:near-a", selected)


if __name__ == "__main__":
    unittest.main()
