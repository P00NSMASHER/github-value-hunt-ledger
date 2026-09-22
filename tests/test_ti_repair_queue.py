import copy
import unittest

from production.repair_queue import (
    build_repair_queue,
    validate_repair_queue,
)


def good_failure(**overrides):
    row = {
        "schema_version": 1,
        "failure_id": "FAIL:test:1",
        "run_id": "RUN:test:1",
        "hunter_id": "HUNTER-01",
        "target_type": "search_skill",
        "target_id": "STRAT:test",
        "failure_class": "false_positive",
        "observation": "The strategy retained a README-only candidate as load-bearing.",
        "reproduction_steps": [
            "Run the frozen query family",
            "Inspect source tree before retaining candidate",
        ],
        "evidence_refs": [
            "hunters/19.md#readme-only-candidate",
        ],
        "proposed_regression_test": (
            "Reject a candidate whose central capability is supported only by README prose."
        ),
        "sensitive_material_involved": False,
        "benchmark_contaminated": False,
    }
    row.update(overrides)
    return row


def alert_state(alert_type="confirm_regression_signal", key="STRAT:test"):
    return {
        "schema_version": 1,
        "policy_effect": "none",
        "learning_alerts": [
            {
                "type": alert_type,
                "memory_key": key,
                "train_mean_reward": 0.4,
                "confirm_mean_reward": 0.1,
                "confirm_min_reward": -0.3,
                "confirm_positive_runs": 1,
                "confirm_runs": 2,
                "confirm_deep_inspections": 6,
            }
        ],
    }


def training_environment(
    *,
    key="STRAT:test",
    objective=None,
):
    state = {
        "search_objective_id": objective,
    }
    action = {
        "strategy_id": key if key.startswith("STRAT:") else None,
        "query_family_id": key if key.startswith("QF:") else None,
        "search_move_ids": [key] if key.startswith("MOVE:") else [],
        "search_moves": [],
    }
    return {
        "schema_version": 1,
        "episodes": [
            {
                "run_id": "RUN:confirm:bad",
                "split": "confirm",
                "state": state,
                "action": action,
                "reward": {
                    "training_reward": -0.3,
                    "reward_stage": "technical_proxy",
                },
                "provenance": {
                    "durable_evidence_path": "hunters/19-confirm.md",
                },
                "episode_sha256": "a" * 64,
            }
        ],
    }


class RepairQueueTests(unittest.TestCase):
    def test_reproducible_failure_is_ready_for_bounded_repair(self):
        queue = build_repair_queue(
            {"learning_alerts": []},
            [good_failure()],
            {},
        )
        self.assertEqual(queue["summary"]["ready_for_repair"], 1)
        task = queue["tasks"][0]
        self.assertEqual(task["state"], "READY_FOR_REPAIR")
        self.assertEqual(task["source"]["kind"], "failure_packet")
        self.assertFalse(task["mutation_scope"]["automatic_write_allowed"])
        self.assertFalse(task["mutation_scope"]["global_promotion_allowed"])
        self.assertTrue(task["regression_test_requirement"])
        self.assertEqual(validate_repair_queue(queue), [])

    def test_sensitive_failure_is_blocked_not_repairable(self):
        queue = build_repair_queue(
            {"learning_alerts": []},
            [good_failure(sensitive_material_involved=True)],
            {},
        )
        self.assertEqual(queue["tasks"], [])
        self.assertEqual(queue["summary"]["blocked_sources"], 1)
        self.assertIn(
            "sensitive_material_blocked",
            queue["blocked_sources"][0]["reasons"],
        )
        self.assertEqual(validate_repair_queue(queue), [])

    def test_benchmark_contaminated_failure_is_blocked(self):
        queue = build_repair_queue(
            {"learning_alerts": []},
            [good_failure(benchmark_contaminated=True)],
            {},
        )
        self.assertEqual(queue["summary"]["ready_for_repair"], 0)
        self.assertEqual(queue["summary"]["blocked_sources"], 1)
        self.assertIn(
            "benchmark_contamination_blocked",
            queue["blocked_sources"][0]["reasons"],
        )

    def test_statistical_alert_needs_reproduction_before_mutation(self):
        queue = build_repair_queue(
            alert_state(),
            [],
            training_environment(),
        )
        self.assertEqual(queue["summary"]["needs_reproduction"], 1)
        task = queue["tasks"][0]
        self.assertEqual(task["state"], "NEEDS_REPRODUCTION")
        self.assertEqual(task["source"]["kind"], "learning_alert")
        self.assertIsNone(task["regression_test_requirement"])
        self.assertEqual(
            task["confirm_failure_refs"][0]["run_id"],
            "RUN:confirm:bad",
        )
        self.assertEqual(
            task["evidence_refs"],
            ["hunters/19-confirm.md"],
        )
        self.assertEqual(validate_repair_queue(queue), [])

    def test_contextual_alert_only_matches_same_objective(self):
        key = "CTX:OBJ:alpha::STRAT:test"
        env = training_environment(
            key="STRAT:test",
            objective="OBJ:alpha",
        )
        queue = build_repair_queue(
            alert_state(key=key),
            [],
            env,
        )
        task = queue["tasks"][0]
        self.assertEqual(len(task["confirm_failure_refs"]), 1)

        env["episodes"][0]["state"]["search_objective_id"] = "OBJ:beta"
        queue = build_repair_queue(
            alert_state(key=key),
            [],
            env,
        )
        self.assertEqual(
            queue["tasks"][0]["confirm_failure_refs"],
            [],
        )

    def test_explicit_failure_outranks_matching_statistical_alert(self):
        queue = build_repair_queue(
            alert_state(key="STRAT:test"),
            [good_failure(target_id="STRAT:test")],
            training_environment(),
        )
        states = [task["state"] for task in queue["tasks"]]
        self.assertEqual(states, ["READY_FOR_REPAIR"])

    def test_duplicate_failure_packets_collapse_by_signature(self):
        duplicate = good_failure(
            failure_id="FAIL:test:2",
        )
        queue = build_repair_queue(
            {"learning_alerts": []},
            [good_failure(), duplicate],
            {},
        )
        self.assertEqual(queue["summary"]["tasks"], 1)
        self.assertEqual(queue["summary"]["ready_for_repair"], 1)

    def test_tampered_hash_fails_validation(self):
        queue = build_repair_queue(
            {"learning_alerts": []},
            [good_failure()],
            {},
        )
        tampered = copy.deepcopy(queue)
        tampered["tasks"][0]["priority_score"] = 1
        errors = validate_repair_queue(tampered)
        self.assertTrue(
            any(error.startswith("task_hash_mismatch:") for error in errors)
        )

    def test_broadened_mutation_scope_fails_validation(self):
        queue = build_repair_queue(
            {"learning_alerts": []},
            [good_failure()],
            {},
        )
        unsafe = copy.deepcopy(queue)
        unsafe["tasks"][0]["mutation_scope"]["automatic_write_allowed"] = True
        errors = validate_repair_queue(unsafe)
        self.assertTrue(
            any(error.startswith("automatic_write_enabled:") for error in errors)
        )

    def test_queue_is_deterministic(self):
        first = build_repair_queue(
            alert_state(),
            [good_failure()],
            training_environment(),
        )
        second = build_repair_queue(
            alert_state(),
            [good_failure()],
            training_environment(),
        )
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
