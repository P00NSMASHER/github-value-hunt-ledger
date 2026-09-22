import copy
import unittest

from production.learning_curriculum import (
    build_learning_curriculum,
    validate_learning_curriculum,
)


def strategy(sid, status="active"):
    return {
        "strategy_id": sid,
        "name": sid.split(":", 1)[-1],
        "status": status,
    }


def memory_row(
    sid,
    *,
    runs=0,
    deep=0,
    train_mean=0.2,
    confirm_runs=0,
    confirm_deep=0,
    confirm_mean=0.2,
    confirm_min=0.1,
    confirm_positive=None,
    train_ready=False,
    confirm_ready=False,
    eligible=False,
    status="gathering_evidence",
    q=0.0,
):
    if confirm_positive is None:
        confirm_positive = confirm_runs
    return {
        "key": sid,
        "kind": "STRATEGY",
        "q_value": q,
        "support": {
            "measured_runs": runs,
            "deep_inspections": deep,
            "mean_reward": train_mean if runs else 0.0,
            "min_reward": (
                train_mean if runs else None
            ),
            "positive_runs": (
                runs if train_mean > 0 else 0
            ),
        },
        "confirm_support": {
            "measured_runs": confirm_runs,
            "deep_inspections": confirm_deep,
            "mean_reward": (
                confirm_mean if confirm_runs else 0.0
            ),
            "min_reward": (
                confirm_min if confirm_runs else None
            ),
            "positive_runs": confirm_positive,
        },
        "train_evidence_ready": train_ready,
        "confirm_evidence_ready": confirm_ready,
        "eligible_for_policy_consideration": eligible,
        "generalization_status": status,
    }


class LearningCurriculumTests(unittest.TestCase):
    def build(self, rows, allocations=None):
        strategies = [
            strategy("STRAT:near-a"),
            strategy("STRAT:near-b"),
            strategy("STRAT:zero-a"),
            strategy("STRAT:zero-b"),
            strategy("STRAT:suppressed"),
            strategy("STRAT:ready"),
            strategy("STRAT:inactive", status="retired"),
        ]
        state = {
            "policy_gate": {
                "minimum_measured_runs": 5,
                "minimum_deep_inspections": 20,
                "minimum_confirm_runs": 2,
                "minimum_confirm_deep_inspections": 6,
                "minimum_confirm_mean_reward": 0.0,
                "minimum_confirm_min_reward": 0.0,
                "minimum_confirm_positive_runs": 1,
            },
            "memory": {"records": rows},
        }
        allocations = allocations or {
            row["strategy_id"]: 0.2
            for row in strategies
        }
        policy = {
            "strategy_allocation": [
                {
                    "strategy_id": sid,
                    "allocation": allocation,
                }
                for sid, allocation in allocations.items()
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
                memory_row(
                    "STRAT:near-a",
                    runs=4,
                    deep=12,
                ),
                memory_row(
                    "STRAT:near-b",
                    runs=3,
                    deep=15,
                ),
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
            for row in curriculum[
                "recommended_measurements"
            ]
        ]
        self.assertEqual(
            selected[:2],
            ["STRAT:near-a", "STRAT:near-b"],
        )
        self.assertEqual(
            selected[2],
            "STRAT:zero-a",
        )
        self.assertNotIn(
            "STRAT:suppressed",
            selected,
        )
        self.assertEqual(
            validate_learning_curriculum(
                curriculum
            ),
            [],
        )

    def test_confirm_measurement_outranks_train_measurement(self):
        curriculum = self.build(
            [
                memory_row(
                    "STRAT:near-a",
                    runs=5,
                    deep=20,
                    train_ready=True,
                ),
                memory_row(
                    "STRAT:near-b",
                    runs=4,
                    deep=19,
                ),
            ]
        )
        first = curriculum[
            "recommended_measurements"
        ][0]
        self.assertEqual(
            first["strategy_id"],
            "STRAT:near-a",
        )
        self.assertEqual(
            first["phase"],
            "confirm_measurement",
        )
        self.assertTrue(
            first["requires_generated_claim"]
        )

    def test_value_reward_and_policy_allocation_do_not_change_selection(self):
        rows = [
            memory_row(
                "STRAT:near-a",
                runs=4,
                deep=12,
                train_mean=-0.9,
                q=-1.0,
            ),
            memory_row(
                "STRAT:near-b",
                runs=3,
                deep=15,
                train_mean=0.9,
                q=1.0,
            ),
        ]
        first = self.build(
            rows,
            {
                "STRAT:near-a": 0.001,
                "STRAT:near-b": 0.999,
            },
        )

        changed = copy.deepcopy(rows)
        changed[0]["q_value"] = 1.0
        changed[0]["support"][
            "mean_reward"
        ] = 1.0
        changed[1]["q_value"] = -1.0
        changed[1]["support"][
            "mean_reward"
        ] = -1.0
        second = self.build(
            changed,
            {
                "STRAT:near-a": 0.999,
                "STRAT:near-b": 0.001,
            },
        )

        first_ids = [
            row["strategy_id"]
            for row in first[
                "recommended_measurements"
            ]
        ]
        second_ids = [
            row["strategy_id"]
            for row in second[
                "recommended_measurements"
            ]
        ]
        self.assertEqual(first_ids, second_ids)
        self.assertFalse(
            first["uses_q_value_for_selection"]
        )
        self.assertFalse(
            first["uses_reward_for_selection"]
        )
        self.assertFalse(
            first[
                "uses_policy_allocation_for_selection"
            ]
        )

    def test_suppressed_and_confirmed_strategies_are_not_recommended(self):
        curriculum = self.build(
            [
                memory_row(
                    "STRAT:suppressed",
                    runs=5,
                    deep=20,
                    confirm_runs=2,
                    confirm_deep=8,
                    train_ready=True,
                    status="confirm_regression_signal",
                ),
                memory_row(
                    "STRAT:ready",
                    runs=5,
                    deep=20,
                    confirm_runs=2,
                    confirm_deep=8,
                    train_ready=True,
                    confirm_ready=True,
                    eligible=True,
                    status="confirmed",
                ),
                memory_row(
                    "STRAT:near-a",
                    runs=4,
                    deep=12,
                ),
            ]
        )
        selected = {
            row["strategy_id"]
            for row in curriculum[
                "recommended_measurements"
            ]
        }
        self.assertNotIn(
            "STRAT:suppressed",
            selected,
        )
        self.assertNotIn(
            "STRAT:ready",
            selected,
        )

    def test_blind_partition_and_retry_rules_are_mandatory(self):
        curriculum = self.build(
            [
                memory_row(
                    "STRAT:near-a",
                    runs=4,
                    deep=12,
                )
            ]
        )
        rec = curriculum[
            "recommended_measurements"
        ][0]
        self.assertIn(
            "Do not calculate",
            rec["blind_partition_rule"],
        )
        self.assertIn(
            "never to seek",
            rec["retry_rule"],
        )

        tampered = copy.deepcopy(curriculum)
        tampered[
            "recommended_measurements"
        ][0]["blind_partition_rule"] = ""
        tampered[
            "recommended_measurements"
        ][0]["requires_generated_claim"] = False
        errors = validate_learning_curriculum(
            tampered
        )
        self.assertIn(
            "missing_blind_partition_rule:STRAT:near-a",
            errors,
        )
        self.assertIn(
            "generated_claim_required:STRAT:near-a",
            errors,
        )

    def test_current_confirm_floor_is_copied_into_measurement_contract(self):
        curriculum = self.build(
            [
                memory_row(
                    "STRAT:near-a",
                    runs=5,
                    deep=20,
                    train_ready=True,
                    confirm_runs=1,
                    confirm_deep=4,
                    confirm_mean=0.3,
                    confirm_min=-0.2,
                    confirm_positive=1,
                )
            ]
        )
        rec = curriculum[
            "recommended_measurements"
        ][0]
        self.assertEqual(
            rec["confirm"][
                "minimum_reward_floor"
            ],
            0.0,
        )
        self.assertEqual(
            rec["confirm"][
                "positive_runs_needed"
            ],
            0,
        )
        self.assertFalse(
            curriculum[
                "partition_selection_allowed"
            ]
        )
        self.assertFalse(
            curriculum[
                "manual_work_can_satisfy_confirm"
            ]
        )


if __name__ == "__main__":
    unittest.main()
