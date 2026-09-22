import copy
import unittest

from production.repair_intake import build_repair_candidate_intake
from production.repair_queue import build_repair_queue
from production.skill_eval_intake import (
    build_skill_eval_result_intake,
    validate_skill_eval_result_intake,
)


def failure_packet():
    return {
        "schema_version": 1,
        "failure_id": "FAIL:skill-eval:1",
        "run_id": "RUN:skill-eval:1",
        "hunter_id": "HUNTER-01",
        "target_type": "search_skill",
        "target_id": "STRAT:test",
        "failure_class": "false_positive",
        "observation": (
            "The search strategy retained a README-only implementation."
        ),
        "reproduction_steps": [
            "Run the frozen search case",
            "Inspect substantive source before retaining",
        ],
        "evidence_refs": ["hunters/19.md#candidate"],
        "proposed_regression_test": (
            "Reject candidates whose central capability is README-only."
        ),
        "sensitive_material_involved": False,
        "benchmark_contaminated": False,
    }


def candidate_intake():
    repair_queue = build_repair_queue(
        {"learning_alerts": []},
        [failure_packet()],
        {},
    )
    task = repair_queue["tasks"][0]
    packet = {
        "schema_version": 1,
        "repair_candidate_id": "RCAND:skill-eval:1",
        "repair_task_id": task["repair_task_id"],
        "repair_task_sha256": task["task_sha256"],
        "target_type": task["target"]["type"],
        "target_id": task["target"]["id"],
        "artifact_id": "SKILL:test",
        "baseline_version": "v1",
        "candidate_version": "v2",
        "baseline_artifact_ref": "sha256:baseline",
        "candidate_artifact_ref": "sha256:candidate",
        "diff_hash": "a" * 64,
        "changed_logical_targets": [task["target"]["id"]],
        "regression_test_requirement": task[
            "regression_test_requirement"
        ],
        "regression_tests_total": 2,
        "regression_tests_passed": 2,
        "regression_test_evidence_refs": [
            "tests/test_skill.py::test_readme_only",
        ],
        "decision_history_ref": (
            "production/history/RCAND-skill-eval-1.json"
        ),
        "unrelated_files_changed": False,
        "sensitive_material_involved": False,
        "benchmark_contaminated": False,
    }
    return build_repair_candidate_intake(
        repair_queue,
        [packet],
    )


def eval_packet(intake=None, **overrides):
    intake = intake or candidate_intake()
    task = intake["skill_eval_queue"][0]
    row = {
        "schema_version": 1,
        "skill_eval_result_id": "SEVALRES:test:1",
        "skill_eval_id": task["skill_eval_id"],
        "skill_eval_sha256": task["skill_eval_sha256"],
        "repair_candidate_id": task["repair_candidate_id"],
        "candidate_record_sha256": task[
            "candidate_record_sha256"
        ],
        "artifact_id": task["artifact_id"],
        "baseline_version": task["baseline_version"],
        "candidate_version": task["candidate_version"],
        "mutate_dev_examples": 6,
        "promotion_test_examples": 6,
        "baseline_dev_score": 0.50,
        "candidate_dev_score": 0.65,
        "champion_test_score": 0.55,
        "candidate_test_score": 0.60,
        "hard_regressions": 0,
        "mutate_dev_set_sha256": "1" * 64,
        "promotion_test_set_sha256": "2" * 64,
        "evaluation_manifest_sha256": "3" * 64,
        "mutator_identity": "MUTATOR:repair-01",
        "evaluator_identity": "VERIFIER:independent-01",
        "evaluation_evidence_refs": [
            "production/evals/SEVALRES-test-1.json",
        ],
        "source_failure_ids": ["FAIL:skill-eval:1"],
        "mutator_saw_promotion_test": False,
        "evaluator_modified": False,
        "controller_modified": False,
        "sealed_holdout_opened_by_mutator": False,
        "provenance_complete": True,
        "sensitive_material_involved": False,
        "benchmark_contaminated": False,
    }
    row.update(overrides)
    return row


class SkillEvalResultIntakeTests(unittest.TestCase):
    def test_clean_evaluation_stages_mutation_only(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [eval_packet(intake)],
        )
        self.assertEqual(state["summary"]["staged_mutations"], 1)
        self.assertEqual(
            state["results"][0]["state"],
            "STAGED_MUTATION",
        )
        self.assertEqual(len(state["skill_promotion_queue"]), 1)
        self.assertFalse(state["automatic_live_write_enabled"])
        self.assertFalse(
            state["automatic_global_promotion_enabled"]
        )
        self.assertFalse(
            state["skill_promotion_queue"][0][
                "automatic_global_promotion_allowed"
            ]
        )
        self.assertEqual(
            validate_skill_eval_result_intake(state),
            [],
        )

    def test_stale_skill_eval_hash_is_blocked(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [
                eval_packet(
                    intake,
                    skill_eval_sha256="0" * 64,
                )
            ],
        )
        self.assertEqual(state["results"], [])
        self.assertIn(
            "stale_or_mismatched_skill_eval_hash",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_candidate_record_hash_drift_is_blocked(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [
                eval_packet(
                    intake,
                    candidate_record_sha256="0" * 64,
                )
            ],
        )
        self.assertIn(
            "candidate_record_hash_mismatch",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_dev_and_promotion_sets_must_be_distinct(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [
                eval_packet(
                    intake,
                    promotion_test_set_sha256="1" * 64,
                )
            ],
        )
        self.assertIn(
            "dev_and_promotion_sets_must_be_distinct",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_mutator_promotion_test_leakage_is_blocked(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [eval_packet(intake, mutator_saw_promotion_test=True)],
        )
        self.assertIn(
            "promotion_test_leakage_to_mutator",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_evaluator_mutation_is_blocked(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [eval_packet(intake, evaluator_modified=True)],
        )
        self.assertIn(
            "evaluator_mutation_blocked",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_controller_mutation_is_blocked(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [eval_packet(intake, controller_modified=True)],
        )
        self.assertIn(
            "controller_mutation_blocked",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_evaluator_must_be_independent_of_mutator(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [
                eval_packet(
                    intake,
                    mutator_identity="SAME:agent",
                    evaluator_identity="SAME:agent",
                )
            ],
        )
        self.assertIn(
            "evaluator_must_be_independent_of_mutator",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_empty_set_or_manifest_hash_is_blocked(self):
        intake = candidate_intake()
        empty_sha = (
            "e3b0c44298fc1c149afbf4c8996fb924"
            "27ae41e4649b934ca495991b7852b855"
        )
        state = build_skill_eval_result_intake(
            intake,
            [
                eval_packet(
                    intake,
                    promotion_test_set_sha256=empty_sha,
                )
            ],
        )
        self.assertIn(
            "promotion_test_set_sha256_cannot_be_empty_hash",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_sealed_holdout_contamination_is_blocked(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [
                eval_packet(
                    intake,
                    sealed_holdout_opened_by_mutator=True,
                )
            ],
        )
        self.assertIn(
            "sealed_holdout_contamination",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_sensitive_or_benchmark_evidence_is_blocked(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [
                eval_packet(
                    intake,
                    sensitive_material_involved=True,
                ),
                eval_packet(
                    intake,
                    skill_eval_result_id="SEVALRES:test:2",
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

    def test_hard_regression_rejects_candidate(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [eval_packet(intake, hard_regressions=1)],
        )
        self.assertEqual(state["results"][0]["state"], "REJECTED")
        self.assertIn(
            "hard_regression",
            state["results"][0]["assessment_reasons"],
        )
        self.assertEqual(state["skill_promotion_queue"], [])

    def test_insufficient_dev_examples_reject(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [eval_packet(intake, mutate_dev_examples=3)],
        )
        self.assertEqual(state["results"][0]["state"], "REJECTED")
        self.assertIn(
            "insufficient_mutate_dev_examples",
            state["results"][0]["assessment_reasons"],
        )

    def test_insufficient_promotion_examples_reject(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [eval_packet(intake, promotion_test_examples=4)],
        )
        self.assertEqual(state["results"][0]["state"], "REJECTED")
        self.assertIn(
            "insufficient_promotion_test_examples",
            state["results"][0]["assessment_reasons"],
        )

    def test_no_dev_improvement_rejects(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [
                eval_packet(
                    intake,
                    candidate_dev_score=0.50,
                )
            ],
        )
        self.assertIn(
            "no_dev_improvement",
            state["results"][0]["assessment_reasons"],
        )

    def test_promotion_delta_below_gate_rejects(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [
                eval_packet(
                    intake,
                    candidate_test_score=0.56,
                )
            ],
        )
        self.assertIn(
            "promotion_delta_below_gate",
            state["results"][0]["assessment_reasons"],
        )

    def test_incomplete_provenance_rejects(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [
                eval_packet(
                    intake,
                    provenance_complete=False,
                )
            ],
        )
        self.assertIn(
            "provenance_incomplete",
            state["results"][0]["assessment_reasons"],
        )

    def test_duplicate_result_id_is_blocked(self):
        intake = candidate_intake()
        packet = eval_packet(intake)
        state = build_skill_eval_result_intake(
            intake,
            [packet, copy.deepcopy(packet)],
        )
        self.assertEqual(len(state["results"]), 1)
        self.assertEqual(len(state["blocked_submissions"]), 1)
        self.assertIn(
            "duplicate_skill_eval_result_id",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_evaluation_result_tamper_fails_validation(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [eval_packet(intake)],
        )
        tampered = copy.deepcopy(state)
        tampered["results"][0]["candidate_test_score"] = 1.0
        errors = validate_skill_eval_result_intake(tampered)
        self.assertTrue(
            any(
                error.startswith("evaluation_result_hash_mismatch:")
                for error in errors
            )
        )

    def test_promotion_gate_tamper_fails_validation(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [eval_packet(intake)],
        )
        tampered = copy.deepcopy(state)
        tampered["skill_promotion_queue"][0][
            "required_promotion_evidence"
        ]["heldout_tasks_min"] = 1
        errors = validate_skill_eval_result_intake(tampered)
        self.assertTrue(
            any(
                error.startswith("promotion_gate_drift:")
                for error in errors
            )
        )

    def test_auto_global_promotion_tamper_fails(self):
        intake = candidate_intake()
        state = build_skill_eval_result_intake(
            intake,
            [eval_packet(intake)],
        )
        tampered = copy.deepcopy(state)
        tampered["skill_promotion_queue"][0][
            "automatic_global_promotion_allowed"
        ] = True
        errors = validate_skill_eval_result_intake(tampered)
        self.assertTrue(
            any(
                error.startswith("promotion_auto_global_enabled:")
                for error in errors
            )
        )


if __name__ == "__main__":
    unittest.main()
