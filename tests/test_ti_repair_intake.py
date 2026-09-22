import copy
import unittest

from production.repair_intake import (
    build_repair_candidate_intake,
    validate_repair_candidate_intake,
)
from production.repair_queue import build_repair_queue


def failure_packet():
    return {
        "schema_version": 1,
        "failure_id": "FAIL:intake:1",
        "run_id": "RUN:intake:1",
        "hunter_id": "HUNTER-01",
        "target_type": "search_skill",
        "target_id": "STRAT:test",
        "failure_class": "false_positive",
        "observation": "The search strategy retained a README-only implementation.",
        "reproduction_steps": [
            "Run the frozen search case",
            "Inspect substantive source before retaining",
        ],
        "evidence_refs": ["hunters/19.md#candidate"],
        "proposed_regression_test": (
            "Reject candidates whose central implementation is README-only."
        ),
        "sensitive_material_involved": False,
        "benchmark_contaminated": False,
    }


def ready_queue():
    return build_repair_queue(
        {"learning_alerts": []},
        [failure_packet()],
        {},
    )


def reproduction_queue():
    return build_repair_queue(
        {
            "learning_alerts": [
                {
                    "type": "confirm_regression_signal",
                    "memory_key": "STRAT:test",
                }
            ]
        },
        [],
        {
            "episodes": [
                {
                    "run_id": "RUN:confirm:repair-intake",
                    "split": "confirm",
                    "state": {
                        "search_objective_id": None,
                    },
                    "action": {
                        "strategy_id": "STRAT:test",
                        "query_family_id": None,
                        "search_move_ids": [],
                        "search_moves": [],
                    },
                    "reward": {
                        "training_reward": -0.3,
                        "reward_stage": "technical_proxy",
                    },
                    "provenance": {
                        "durable_evidence_path": (
                            "hunters/19-confirm-repair-intake.md"
                        ),
                    },
                    "episode_sha256": "f" * 64,
                }
            ]
        },
    )


def candidate_packet(queue=None, **overrides):
    queue = queue or ready_queue()
    task = queue["tasks"][0]
    row = {
        "schema_version": 1,
        "repair_candidate_id": "RCAND:test:1",
        "repair_task_id": task["repair_task_id"],
        "repair_task_sha256": task["task_sha256"],
        "target_type": task["target"]["type"],
        "target_id": task["target"]["id"],
        "artifact_id": "SKILL:test",
        "baseline_version": "v1",
        "candidate_version": "v2",
        "baseline_artifact_ref": "artifacts/baseline.json",
        "baseline_artifact_sha256": "1" * 64,
        "candidate_artifact_ref": "artifacts/candidate.json",
        "candidate_artifact_sha256": "2" * 64,
        "diff_hash": "a" * 64,
        "changed_logical_targets": [task["target"]["id"]],
        "regression_test_requirement": task["regression_test_requirement"],
        "regression_tests_total": 2,
        "regression_tests_passed": 2,
        "regression_test_evidence_refs": [
            "tests/test_skill.py::test_readme_only",
        ],
        "regression_test_evidence_sha256": "3" * 64,
        "decision_history_ref": "production/history/RCAND-test-1.json",
        "decision_history_sha256": "4" * 64,
        "unrelated_files_changed": False,
        "sensitive_material_involved": False,
        "benchmark_contaminated": False,
    }
    row.update(overrides)
    return row


class RepairCandidateIntakeTests(unittest.TestCase):
    def test_passing_repair_becomes_ready_for_skill_eval_only(self):
        queue = ready_queue()
        state = build_repair_candidate_intake(
            queue,
            [candidate_packet(queue)],
        )
        self.assertEqual(state["summary"]["ready_for_skill_eval"], 1)
        self.assertEqual(
            state["candidates"][0]["state"],
            "READY_FOR_SKILL_EVAL",
        )
        self.assertEqual(len(state["skill_eval_queue"]), 1)
        self.assertFalse(state["automatic_write_enabled"])
        self.assertFalse(state["automatic_global_promotion_enabled"])
        self.assertFalse(
            state["skill_eval_queue"][0][
                "automatic_global_promotion_allowed"
            ]
        )
        self.assertEqual(validate_repair_candidate_intake(state), [])

    def test_stale_repair_task_hash_is_blocked(self):
        queue = ready_queue()
        state = build_repair_candidate_intake(
            queue,
            [
                candidate_packet(
                    queue,
                    repair_task_sha256="0" * 64,
                )
            ],
        )
        self.assertEqual(state["candidates"], [])
        self.assertIn(
            "stale_or_mismatched_repair_task_hash",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_reproduction_only_task_cannot_accept_candidate_fix(self):
        queue = reproduction_queue()
        state = build_repair_candidate_intake(
            queue,
            [candidate_packet(queue)],
        )
        self.assertEqual(state["summary"]["ready_for_skill_eval"], 0)
        self.assertIn(
            "repair_task_not_ready",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_failed_regression_is_rejected_not_promoted(self):
        queue = ready_queue()
        state = build_repair_candidate_intake(
            queue,
            [
                candidate_packet(
                    queue,
                    regression_tests_passed=1,
                )
            ],
        )
        self.assertEqual(state["summary"]["blocked"], 0)
        self.assertEqual(state["summary"]["rejected"], 1)
        self.assertEqual(
            state["candidates"][0]["state"],
            "REJECTED",
        )
        self.assertIn(
            "regression_test_failure",
            state["candidates"][0]["assessment_reasons"],
        )
        self.assertEqual(state["skill_eval_queue"], [])

    def test_unrelated_change_is_rejected(self):
        queue = ready_queue()
        state = build_repair_candidate_intake(
            queue,
            [
                candidate_packet(
                    queue,
                    unrelated_files_changed=True,
                )
            ],
        )
        self.assertEqual(
            state["candidates"][0]["state"],
            "REJECTED",
        )
        self.assertIn(
            "unrelated_change_detected",
            state["candidates"][0]["assessment_reasons"],
        )

    def test_scope_widening_is_blocked(self):
        queue = ready_queue()
        state = build_repair_candidate_intake(
            queue,
            [
                candidate_packet(
                    queue,
                    changed_logical_targets=[
                        "STRAT:test",
                        "STRAT:other",
                    ],
                )
            ],
        )
        self.assertEqual(state["candidates"], [])
        self.assertIn(
            "mutation_scope_not_exactly_one_authorized_target",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_wrong_regression_requirement_is_blocked(self):
        queue = ready_queue()
        state = build_repair_candidate_intake(
            queue,
            [
                candidate_packet(
                    queue,
                    regression_test_requirement=(
                        "Run an unrelated passing test instead."
                    ),
                )
            ],
        )
        self.assertEqual(state["candidates"], [])
        self.assertIn(
            "regression_test_requirement_mismatch",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_sensitive_or_benchmark_contamination_is_blocked(self):
        queue = ready_queue()
        state = build_repair_candidate_intake(
            queue,
            [
                candidate_packet(
                    queue,
                    sensitive_material_involved=True,
                ),
                candidate_packet(
                    queue,
                    repair_candidate_id="RCAND:test:2",
                    benchmark_contaminated=True,
                ),
            ],
        )
        reasons = {
            reason
            for row in state["blocked_submissions"]
            for reason in row["reasons"]
        }
        self.assertIn("sensitive_material_blocked", reasons)
        self.assertIn("benchmark_contamination_blocked", reasons)
        self.assertEqual(state["skill_eval_queue"], [])

    def test_duplicate_candidate_id_is_blocked(self):
        queue = ready_queue()
        packet = candidate_packet(queue)
        duplicate = copy.deepcopy(packet)
        state = build_repair_candidate_intake(
            queue,
            [packet, duplicate],
        )
        self.assertEqual(len(state["candidates"]), 1)
        self.assertEqual(len(state["blocked_submissions"]), 1)
        self.assertIn(
            "duplicate_repair_candidate_id",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_bad_diff_hash_is_blocked(self):
        queue = ready_queue()
        state = build_repair_candidate_intake(
            queue,
            [candidate_packet(queue, diff_hash="not-a-sha")],
        )
        self.assertIn(
            "diff_hash_must_be_sha256",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_empty_diff_is_blocked(self):
        queue = ready_queue()
        empty_sha = (
            "e3b0c44298fc1c149afbf4c8996fb924"
            "27ae41e4649b934ca495991b7852b855"
        )
        state = build_repair_candidate_intake(
            queue,
            [candidate_packet(queue, diff_hash=empty_sha)],
        )
        self.assertIn(
            "empty_diff_not_allowed",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_artifact_content_hashes_are_required(self):
        queue = ready_queue()
        state = build_repair_candidate_intake(
            queue,
            [
                candidate_packet(
                    queue,
                    baseline_artifact_sha256="not-a-sha",
                )
            ],
        )
        self.assertIn(
            "baseline_artifact_sha256_required",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_candidate_artifact_hash_must_differ_from_baseline(self):
        queue = ready_queue()
        state = build_repair_candidate_intake(
            queue,
            [
                candidate_packet(
                    queue,
                    candidate_artifact_sha256="1" * 64,
                )
            ],
        )
        self.assertIn(
            "candidate_artifact_hash_must_differ_from_baseline",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_regression_and_decision_history_evidence_must_be_content_addressed(self):
        queue = ready_queue()
        state = build_repair_candidate_intake(
            queue,
            [
                candidate_packet(
                    queue,
                    regression_test_evidence_sha256="",
                    decision_history_sha256="bad",
                )
            ],
        )
        reasons = state["blocked_submissions"][0]["reasons"]
        self.assertIn(
            "regression_test_evidence_sha256_required",
            reasons,
        )
        self.assertIn(
            "decision_history_sha256_required",
            reasons,
        )

    def test_candidate_artifact_must_differ_from_baseline(self):
        queue = ready_queue()
        state = build_repair_candidate_intake(
            queue,
            [
                candidate_packet(
                    queue,
                    candidate_artifact_ref="artifacts/baseline.json",
                )
            ],
        )
        self.assertIn(
            "candidate_artifact_must_differ_from_baseline",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_required_safety_booleans_must_be_explicit(self):
        queue = ready_queue()
        packet = candidate_packet(queue)
        packet.pop("benchmark_contaminated")
        state = build_repair_candidate_intake(
            queue,
            [packet],
        )
        self.assertIn(
            "benchmark_contaminated_boolean_required",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_candidate_record_tamper_fails_validation(self):
        queue = ready_queue()
        state = build_repair_candidate_intake(
            queue,
            [candidate_packet(queue)],
        )
        tampered = copy.deepcopy(state)
        tampered["candidates"][0]["candidate_version"] = "v999"
        errors = validate_repair_candidate_intake(tampered)
        self.assertTrue(
            any(
                error.startswith("candidate_hash_mismatch:")
                for error in errors
            )
        )

    def test_skill_eval_hash_binding_fails_closed(self):
        queue = ready_queue()
        state = build_repair_candidate_intake(
            queue,
            [candidate_packet(queue)],
        )
        tampered = copy.deepcopy(state)
        tampered["skill_eval_queue"][0][
            "candidate_record_sha256"
        ] = "0" * 64
        errors = validate_repair_candidate_intake(tampered)
        self.assertTrue(
            any(
                error.startswith("skill_eval_stale_candidate_hash:")
                for error in errors
            )
        )


if __name__ == "__main__":
    unittest.main()
