import copy
import unittest

from production.repair_intake import build_repair_candidate_intake
from production.repair_queue import build_repair_queue
from production.skill_eval_intake import build_skill_eval_result_intake
from production.skill_promotion_intake import (
    build_skill_promotion_result_intake,
    validate_skill_promotion_result_intake,
)


def failure_packet():
    return {
        "schema_version": 1,
        "failure_id": "FAIL:promotion:1",
        "run_id": "RUN:promotion:1",
        "hunter_id": "HUNTER-01",
        "target_type": "search_skill",
        "target_id": "STRAT:test",
        "failure_class": "false_positive",
        "observation": "The strategy retained an implementation without source proof.",
        "reproduction_steps": [
            "Run the frozen search case",
            "Inspect substantive source before retaining",
        ],
        "evidence_refs": ["hunters/19.md#candidate"],
        "proposed_regression_test": (
            "Reject candidates whose core implementation is unsupported."
        ),
        "sensitive_material_involved": False,
        "benchmark_contaminated": False,
    }


def skill_eval_intake():
    repair_queue = build_repair_queue(
        {"learning_alerts": []},
        [failure_packet()],
        {},
    )
    task = repair_queue["tasks"][0]
    candidate = {
        "schema_version": 1,
        "repair_candidate_id": "RCAND:promotion:1",
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
        "regression_test_requirement": task[
            "regression_test_requirement"
        ],
        "regression_tests_total": 2,
        "regression_tests_passed": 2,
        "regression_test_evidence_refs": [
            "tests/test_skill.py::test_core_source",
        ],
        "regression_test_evidence_sha256": "3" * 64,
        "decision_history_ref": "production/history/promotion.json",
        "decision_history_sha256": "4" * 64,
        "unrelated_files_changed": False,
        "sensitive_material_involved": False,
        "benchmark_contaminated": False,
    }
    repair_intake = build_repair_candidate_intake(
        repair_queue,
        [candidate],
    )
    eval_task = repair_intake["skill_eval_queue"][0]
    eval_packet = {
        "schema_version": 1,
        "skill_eval_result_id": "SEVALRES:promotion:1",
        "skill_eval_id": eval_task["skill_eval_id"],
        "skill_eval_sha256": eval_task["skill_eval_sha256"],
        "repair_candidate_id": eval_task["repair_candidate_id"],
        "candidate_record_sha256": eval_task[
            "candidate_record_sha256"
        ],
        "artifact_id": eval_task["artifact_id"],
        "baseline_version": eval_task["baseline_version"],
        "candidate_version": eval_task["candidate_version"],
        "mutate_dev_examples": 6,
        "promotion_test_examples": 6,
        "baseline_dev_score": 0.50,
        "candidate_dev_score": 0.65,
        "champion_test_score": 0.55,
        "candidate_test_score": 0.60,
        "hard_regressions": 0,
        "mutate_dev_set_sha256": "5" * 64,
        "promotion_test_set_sha256": "6" * 64,
        "evaluation_manifest_sha256": "7" * 64,
        "mutator_identity": "MUTATOR:01",
        "evaluator_identity": "VERIFIER:01",
        "evaluation_evidence_refs": ["production/evals/promotion.json"],
        "evaluation_evidence_sha256": "8" * 64,
        "source_failure_ids": ["FAIL:promotion:1"],
        "mutator_saw_promotion_test": False,
        "evaluator_modified": False,
        "controller_modified": False,
        "sealed_holdout_opened_by_mutator": False,
        "provenance_complete": True,
        "sensitive_material_involved": False,
        "benchmark_contaminated": False,
    }
    return build_skill_eval_result_intake(
        repair_intake,
        [eval_packet],
    )


def promotion_packet(intake=None, **overrides):
    intake = intake or skill_eval_intake()
    task = intake["skill_promotion_queue"][0]
    row = {
        "schema_version": 1,
        "skill_promotion_result_id": "SPROMORES:test:1",
        "skill_promotion_id": task["skill_promotion_id"],
        "skill_promotion_sha256": task["skill_promotion_sha256"],
        "skill_eval_result_id": task["skill_eval_result_id"],
        "evaluation_result_sha256": task[
            "evaluation_result_sha256"
        ],
        "artifact_id": task["artifact_id"],
        "candidate_version": task["candidate_version"],
        "distinct_success_task_ids": ["TASK:1", "TASK:2"],
        "heldout_tasks": 5,
        "heldout_passes": 5,
        "heldout_regressions": 0,
        "heldout_set_sha256": "9" * 64,
        "heldout_evidence_sha256": "a" * 64,
        "adversarial_task_passed": True,
        "adversarial_evidence_sha256": "b" * 64,
        "adjacent_domain_task_passed": True,
        "adjacent_domain_evidence_sha256": "c" * 64,
        "curator_approved": True,
        "curator_identity": "INTEGRATOR:curator",
        "curator_evidence_sha256": "d" * 64,
        "canary_hunter_ids": [
            "HUNTER-01",
            "HUNTER-02",
            "HUNTER-03",
        ],
        "canary_regressions": 0,
        "canary_evidence_sha256": "e" * 64,
        "sensitive_material_involved": False,
        "benchmark_contaminated": False,
    }
    row.update(overrides)
    return row


class SkillPromotionIntakeTests(unittest.TestCase):
    def test_complete_evidence_is_global_eligible_not_global(self):
        intake = skill_eval_intake()
        state = build_skill_promotion_result_intake(
            intake,
            [promotion_packet(intake)],
        )
        self.assertEqual(state["summary"]["global_eligible"], 1)
        self.assertEqual(
            state["results"][0]["state"],
            "GLOBAL_ELIGIBLE",
        )
        self.assertEqual(len(state["global_review_queue"]), 1)
        review = state["global_review_queue"][0]
        self.assertTrue(review["integrator_approval_required"])
        self.assertFalse(review["automatic_global_promotion_allowed"])
        self.assertFalse(state["automatic_global_promotion_enabled"])
        self.assertEqual(
            validate_skill_promotion_result_intake(state),
            [],
        )

    def test_heldout_regression_quarantines(self):
        intake = skill_eval_intake()
        state = build_skill_promotion_result_intake(
            intake,
            [
                promotion_packet(
                    intake,
                    heldout_passes=4,
                    heldout_regressions=1,
                )
            ],
        )
        self.assertEqual(state["results"][0]["state"], "QUARANTINED")
        self.assertEqual(state["global_review_queue"], [])

    def test_missing_curator_approval_stops_at_verified(self):
        intake = skill_eval_intake()
        state = build_skill_promotion_result_intake(
            intake,
            [
                promotion_packet(
                    intake,
                    curator_approved=False,
                    curator_identity=None,
                    curator_evidence_sha256=None,
                    canary_hunter_ids=[],
                    canary_evidence_sha256=None,
                )
            ],
        )
        self.assertEqual(state["results"][0]["state"], "VERIFIED")

    def test_insufficient_canary_stops_at_canary(self):
        intake = skill_eval_intake()
        state = build_skill_promotion_result_intake(
            intake,
            [
                promotion_packet(
                    intake,
                    canary_hunter_ids=["HUNTER-01"],
                )
            ],
        )
        self.assertEqual(state["results"][0]["state"], "CANARY")

    def test_incomplete_heldout_stays_staged(self):
        intake = skill_eval_intake()
        state = build_skill_promotion_result_intake(
            intake,
            [
                promotion_packet(
                    intake,
                    heldout_tasks=4,
                    heldout_passes=4,
                )
            ],
        )
        self.assertEqual(state["results"][0]["state"], "STAGED")

    def test_stale_promotion_task_hash_is_blocked(self):
        intake = skill_eval_intake()
        state = build_skill_promotion_result_intake(
            intake,
            [
                promotion_packet(
                    intake,
                    skill_promotion_sha256="0" * 64,
                )
            ],
        )
        self.assertEqual(state["results"], [])
        self.assertIn(
            "stale_or_mismatched_skill_promotion_hash",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_sensitive_or_benchmark_evidence_is_blocked(self):
        intake = skill_eval_intake()
        state = build_skill_promotion_result_intake(
            intake,
            [
                promotion_packet(
                    intake,
                    sensitive_material_involved=True,
                ),
                promotion_packet(
                    intake,
                    skill_promotion_result_id="SPROMORES:test:2",
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

    def test_claimed_pass_requires_frozen_evidence(self):
        intake = skill_eval_intake()
        state = build_skill_promotion_result_intake(
            intake,
            [
                promotion_packet(
                    intake,
                    adversarial_evidence_sha256=None,
                )
            ],
        )
        self.assertIn(
            "adversarial_evidence_sha256_required",
            state["blocked_submissions"][0]["reasons"],
        )

    def test_global_review_tamper_fails_closed(self):
        intake = skill_eval_intake()
        state = build_skill_promotion_result_intake(
            intake,
            [promotion_packet(intake)],
        )
        tampered = copy.deepcopy(state)
        tampered["global_review_queue"][0][
            "automatic_global_promotion_allowed"
        ] = True
        errors = validate_skill_promotion_result_intake(tampered)
        self.assertTrue(
            any(
                error.startswith("global_review_auto_promotion_enabled:")
                for error in errors
            )
        )


if __name__ == "__main__":
    unittest.main()
