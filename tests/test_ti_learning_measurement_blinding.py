import unittest

from production.learning_measurement_blinding import (
    PHASE_BLIND_CONTRACT_VERSION,
    REQUIRED_BLINDING_STOP,
    worker_measurement_blinding_errors,
)


def seed(**overrides):
    row = {
        "seed_id": "SEED:learn:test",
        "seed_type": "learning_measurement",
        "measurement_contract_version": PHASE_BLIND_CONTRACT_VERSION,
        "authorization_basis": "adaptive_learning_curriculum",
        "strategy_id": "STRAT:test",
        "priority": 75,
        "why_now": (
            "STRAT:test is a scheduler-selected adaptive-learning measurement "
            "target. Pair it with one bounded transfer task. Scheduler-only "
            "state is intentionally withheld from the worker."
        ),
        "stop_conditions": [
            "A no-find result is valid evidence.",
            REQUIRED_BLINDING_STOP,
        ],
    }
    row.update(overrides)
    return row


class LearningMeasurementBlindingTests(unittest.TestCase):
    def test_phase_blind_seed_is_valid(self):
        self.assertEqual(
            worker_measurement_blinding_errors(seed()),
            [],
        )

    def test_planner_only_fields_are_rejected(self):
        errors = worker_measurement_blinding_errors(
            seed(
                learning_phase="confirm_measurement",
                learning_curriculum_rank=1,
                learning_selection_reason="confirm debt",
            )
        )
        self.assertIn(
            "planner_only_field_exposed:learning_phase",
            errors,
        )
        self.assertIn(
            "planner_only_field_exposed:learning_curriculum_rank",
            errors,
        )
        self.assertIn(
            "planner_only_field_exposed:learning_selection_reason",
            errors,
        )

    def test_phase_bearing_text_is_rejected(self):
        errors = worker_measurement_blinding_errors(
            seed(
                why_now=(
                    "STRAT:test is a scheduler-selected adaptive-learning "
                    "measurement target. Train evidence: 5 runs. "
                    "confirm_measurement is next."
                )
            )
        )
        self.assertTrue(
            any(
                error.startswith("planner_only_text_exposed:")
                for error in errors
            )
        )

    def test_blinding_stop_is_required(self):
        errors = worker_measurement_blinding_errors(
            seed(stop_conditions=["Bounded search only."])
        )
        self.assertIn(
            "planner_state_blinding_stop_required",
            errors,
        )

    def test_contract_version_is_required(self):
        errors = worker_measurement_blinding_errors(
            seed(measurement_contract_version="legacy")
        )
        self.assertIn(
            "phase_blind_contract_required",
            errors,
        )

    def test_neutral_reason_is_required(self):
        errors = worker_measurement_blinding_errors(
            seed(why_now="Run a useful search.")
        )
        self.assertIn(
            "phase_blind_measurement_reason_not_neutral",
            errors,
        )

    def test_non_learning_seed_is_ignored(self):
        self.assertEqual(
            worker_measurement_blinding_errors(
                {
                    "seed_type": "capability_gap",
                    "learning_phase": "confirm_measurement",
                }
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
