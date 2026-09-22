from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from production.learning_engine import (
    SkillMutationDecision,
    SkillVariantEvidence,
    assess_skill_variant,
)


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _sha256_string(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(ch in "0123456789abcdef" for ch in value)


def _finite_score(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and math.isfinite(float(value))
        and 0.0 <= float(value) <= 1.0
    )


def _finalize(row: dict[str, Any], field: str) -> dict[str, Any]:
    out = dict(row)
    out[field] = _stable_hash(out)
    return out


def _task_map(
    repair_candidate_intake: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("skill_eval_id")): row
        for row in repair_candidate_intake.get("skill_eval_queue") or []
        if row.get("skill_eval_id")
    }


def _candidate_map(
    repair_candidate_intake: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("repair_candidate_id")): row
        for row in repair_candidate_intake.get("candidates") or []
        if row.get("repair_candidate_id")
    }


def _packet_errors(packet: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    result_id = str(packet.get("skill_eval_result_id") or "")
    if not result_id.startswith("SEVALRES:"):
        errors.append("invalid_skill_eval_result_id")

    for name in (
        "mutate_dev_set_sha256",
        "promotion_test_set_sha256",
        "evaluation_manifest_sha256",
    ):
        if not _sha256_string(packet.get(name)):
            errors.append(f"{name}_must_be_sha256")

    dev_hash = packet.get("mutate_dev_set_sha256")
    promo_hash = packet.get("promotion_test_set_sha256")
    if (
        isinstance(dev_hash, str)
        and isinstance(promo_hash, str)
        and dev_hash == promo_hash
    ):
        errors.append("dev_and_promotion_sets_must_be_distinct")

    for name in (
        "mutator_saw_promotion_test",
        "evaluator_modified",
        "sealed_holdout_opened_by_mutator",
        "provenance_complete",
        "sensitive_material_involved",
        "benchmark_contaminated",
    ):
        if not isinstance(packet.get(name), bool):
            errors.append(f"{name}_boolean_required")

    if packet.get("mutator_saw_promotion_test") is True:
        errors.append("promotion_test_leakage_to_mutator")
    if packet.get("evaluator_modified") is True:
        errors.append("evaluator_mutation_blocked")
    if packet.get("sealed_holdout_opened_by_mutator") is True:
        errors.append("sealed_holdout_contamination")
    if packet.get("sensitive_material_involved") is True:
        errors.append("sensitive_material_blocked")
    if packet.get("benchmark_contaminated") is True:
        errors.append("benchmark_contamination_blocked")

    for name in (
        "mutate_dev_examples",
        "promotion_test_examples",
        "hard_regressions",
    ):
        value = packet.get(name)
        if not isinstance(value, int) or value < 0:
            errors.append(f"{name}_nonnegative_integer_required")

    for name in (
        "baseline_dev_score",
        "candidate_dev_score",
        "champion_test_score",
        "candidate_test_score",
    ):
        if not _finite_score(packet.get(name)):
            errors.append(f"{name}_normalized_score_required")

    if not packet.get("evaluator_identity"):
        errors.append("evaluator_identity_required")
    if not packet.get("evaluation_evidence_refs"):
        errors.append("evaluation_evidence_required")
    return errors


def _binding_errors(
    packet: Mapping[str, Any],
    task: Mapping[str, Any] | None,
    candidate: Mapping[str, Any] | None,
) -> list[str]:
    errors: list[str] = []
    if task is None:
        errors.append("skill_eval_task_not_found")
        return errors
    if candidate is None:
        errors.append("repair_candidate_not_found")
        return errors

    if packet.get("skill_eval_sha256") != task.get("skill_eval_sha256"):
        errors.append("stale_or_mismatched_skill_eval_hash")
    if packet.get("repair_candidate_id") != task.get("repair_candidate_id"):
        errors.append("repair_candidate_id_mismatch")
    if (
        packet.get("candidate_record_sha256")
        != task.get("candidate_record_sha256")
    ):
        errors.append("candidate_record_hash_mismatch")
    if (
        candidate.get("candidate_record_sha256")
        != task.get("candidate_record_sha256")
    ):
        errors.append("intake_candidate_hash_drift")
    for field in (
        "artifact_id",
        "baseline_version",
        "candidate_version",
    ):
        if packet.get(field) != task.get(field):
            errors.append(f"{field}_mismatch")
        if candidate.get(field) != task.get(field):
            errors.append(f"intake_{field}_drift")
    if candidate.get("state") != "READY_FOR_SKILL_EVAL":
        errors.append("repair_candidate_not_ready_for_skill_eval")
    return errors


def build_skill_eval_result_intake(
    repair_candidate_intake: Mapping[str, Any],
    result_packets: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    tasks = _task_map(repair_candidate_intake)
    candidates = _candidate_map(repair_candidate_intake)
    results: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    promotion_queue: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for packet in result_packets:
        result_id = str(packet.get("skill_eval_result_id") or "")
        if result_id in seen_ids:
            blocked.append(
                {
                    "skill_eval_result_id": result_id,
                    "reasons": ["duplicate_skill_eval_result_id"],
                }
            )
            continue
        seen_ids.add(result_id)

        task_id = str(packet.get("skill_eval_id") or "")
        task = tasks.get(task_id)
        candidate_id = str(packet.get("repair_candidate_id") or "")
        candidate = candidates.get(candidate_id)

        hard_errors = (
            _packet_errors(packet)
            + _binding_errors(packet, task, candidate)
        )
        if hard_errors:
            blocked.append(
                {
                    "skill_eval_result_id": result_id or "INVALID",
                    "skill_eval_id": task_id or None,
                    "repair_candidate_id": candidate_id or None,
                    "reasons": sorted(set(hard_errors)),
                }
            )
            continue

        split_disjoint = (
            packet.get("mutate_dev_set_sha256")
            != packet.get("promotion_test_set_sha256")
        )
        assessment = assess_skill_variant(
            SkillVariantEvidence(
                skill_id=str(packet.get("artifact_id")),
                baseline_version=str(packet.get("baseline_version")),
                candidate_version=str(packet.get("candidate_version")),
                mutate_dev_examples=int(packet.get("mutate_dev_examples")),
                promotion_test_examples=int(
                    packet.get("promotion_test_examples")
                ),
                baseline_dev_score=float(
                    packet.get("baseline_dev_score")
                ),
                candidate_dev_score=float(
                    packet.get("candidate_dev_score")
                ),
                champion_test_score=float(
                    packet.get("champion_test_score")
                ),
                candidate_test_score=float(
                    packet.get("candidate_test_score")
                ),
                hard_regressions=int(packet.get("hard_regressions")),
                split_fingerprints_disjoint=split_disjoint,
                provenance_complete=bool(
                    packet.get("provenance_complete")
                ),
                source_failure_ids=tuple(
                    str(value)
                    for value in packet.get("source_failure_ids") or []
                ),
            )
        )
        state = (
            "STAGED_MUTATION"
            if assessment.decision
            is SkillMutationDecision.STAGED_MUTATION
            else "REJECTED"
        )
        row = {
            "schema_version": 1,
            "skill_eval_result_id": result_id,
            "skill_eval_id": task_id,
            "skill_eval_sha256": task.get("skill_eval_sha256"),
            "repair_candidate_id": candidate_id,
            "candidate_record_sha256": task.get(
                "candidate_record_sha256"
            ),
            "state": state,
            "assessment_reasons": list(assessment.reasons),
            "score_delta": assessment.score_delta,
            "artifact_id": packet.get("artifact_id"),
            "baseline_version": packet.get("baseline_version"),
            "candidate_version": packet.get("candidate_version"),
            "mutate_dev_examples": packet.get("mutate_dev_examples"),
            "promotion_test_examples": packet.get(
                "promotion_test_examples"
            ),
            "baseline_dev_score": packet.get("baseline_dev_score"),
            "candidate_dev_score": packet.get("candidate_dev_score"),
            "champion_test_score": packet.get("champion_test_score"),
            "candidate_test_score": packet.get("candidate_test_score"),
            "hard_regressions": packet.get("hard_regressions"),
            "mutate_dev_set_sha256": packet.get(
                "mutate_dev_set_sha256"
            ),
            "promotion_test_set_sha256": packet.get(
                "promotion_test_set_sha256"
            ),
            "evaluation_manifest_sha256": packet.get(
                "evaluation_manifest_sha256"
            ),
            "evaluator_identity": packet.get("evaluator_identity"),
            "evaluation_evidence_refs": list(
                packet.get("evaluation_evidence_refs") or []
            ),
            "provenance_complete": packet.get(
                "provenance_complete"
            ),
            "automatic_live_write_allowed": False,
            "automatic_global_promotion_allowed": False,
        }
        row = _finalize(row, "evaluation_result_sha256")
        results.append(row)

        if state == "STAGED_MUTATION":
            promotion = {
                "schema_version": 1,
                "skill_promotion_id": "SKILLPROMO:" + _stable_hash(
                    {
                        "skill_eval_result_id": result_id,
                        "evaluation_result_sha256": row[
                            "evaluation_result_sha256"
                        ],
                    }
                )[:16],
                "skill_eval_result_id": result_id,
                "evaluation_result_sha256": row[
                    "evaluation_result_sha256"
                ],
                "artifact_id": packet.get("artifact_id"),
                "candidate_version": packet.get("candidate_version"),
                "required_promotion_evidence": {
                    "distinct_success_tasks_min": 2,
                    "heldout_tasks_min": 5,
                    "heldout_pass_rate_required": 1.0,
                    "heldout_regressions_max": 0,
                    "adversarial_task_passed_required": True,
                    "adjacent_domain_task_passed_required": True,
                    "curator_approval_required": True,
                    "canary_hunters_min": 3,
                    "canary_regressions_max": 0,
                },
                "automatic_global_promotion_allowed": False,
            }
            promotion_queue.append(
                _finalize(promotion, "skill_promotion_sha256")
            )

    results.sort(key=lambda row: row["skill_eval_result_id"])
    blocked.sort(
        key=lambda row: (
            str(row.get("skill_eval_result_id") or ""),
            ",".join(row.get("reasons") or []),
        )
    )
    promotion_queue.sort(key=lambda row: row["skill_promotion_id"])

    return {
        "schema_version": 1,
        "mode": "skill_eval_result_intake",
        "policy_effect": "none",
        "automatic_live_write_enabled": False,
        "automatic_global_promotion_enabled": False,
        "summary": {
            "submitted": len(result_packets),
            "accepted_records": len(results),
            "staged_mutations": sum(
                1 for row in results if row["state"] == "STAGED_MUTATION"
            ),
            "rejected": sum(
                1 for row in results if row["state"] == "REJECTED"
            ),
            "blocked": len(blocked),
        },
        "results": results,
        "skill_promotion_queue": promotion_queue,
        "blocked_submissions": blocked,
    }


def validate_skill_eval_result_intake(
    state: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if state.get("schema_version") != 1:
        errors.append("unexpected_schema_version")
    if state.get("policy_effect") != "none":
        errors.append("policy_effect_must_be_none")
    if state.get("automatic_live_write_enabled") is not False:
        errors.append("automatic_live_write_must_be_disabled")
    if state.get("automatic_global_promotion_enabled") is not False:
        errors.append("automatic_global_promotion_must_be_disabled")

    staged_hashes: dict[str, str] = {}
    result_ids: set[str] = set()
    for row in state.get("results") or []:
        result_id = str(row.get("skill_eval_result_id") or "")
        if result_id in result_ids:
            errors.append(f"duplicate_result_record:{result_id}")
        result_ids.add(result_id)
        if row.get("automatic_live_write_allowed") is not False:
            errors.append(f"result_live_write_enabled:{result_id}")
        if row.get("automatic_global_promotion_allowed") is not False:
            errors.append(f"result_global_promotion_enabled:{result_id}")

        supplied = row.get("evaluation_result_sha256")
        body = dict(row)
        body.pop("evaluation_result_sha256", None)
        if supplied != _stable_hash(body):
            errors.append(f"evaluation_result_hash_mismatch:{result_id}")

        state_name = row.get("state")
        if state_name == "STAGED_MUTATION":
            if row.get("assessment_reasons"):
                errors.append(
                    f"staged_mutation_has_rejection_reasons:{result_id}"
                )
            staged_hashes[result_id] = str(supplied)
        elif state_name != "REJECTED":
            errors.append(f"invalid_eval_result_state:{result_id}")

    promotion_ids: set[str] = set()
    for row in state.get("skill_promotion_queue") or []:
        promo_id = str(row.get("skill_promotion_id") or "")
        result_id = str(row.get("skill_eval_result_id") or "")
        if result_id in promotion_ids:
            errors.append(f"duplicate_promotion_result:{result_id}")
        promotion_ids.add(result_id)
        if result_id not in staged_hashes:
            errors.append(f"promotion_without_staged_result:{promo_id}")
        elif (
            row.get("evaluation_result_sha256")
            != staged_hashes[result_id]
        ):
            errors.append(f"promotion_stale_result_hash:{promo_id}")
        if row.get("automatic_global_promotion_allowed") is not False:
            errors.append(f"promotion_auto_global_enabled:{promo_id}")

        req = row.get("required_promotion_evidence") or {}
        expected = {
            "distinct_success_tasks_min": 2,
            "heldout_tasks_min": 5,
            "heldout_pass_rate_required": 1.0,
            "heldout_regressions_max": 0,
            "adversarial_task_passed_required": True,
            "adjacent_domain_task_passed_required": True,
            "curator_approval_required": True,
            "canary_hunters_min": 3,
            "canary_regressions_max": 0,
        }
        if req != expected:
            errors.append(f"promotion_gate_drift:{promo_id}")

        supplied = row.get("skill_promotion_sha256")
        body = dict(row)
        body.pop("skill_promotion_sha256", None)
        if supplied != _stable_hash(body):
            errors.append(f"promotion_hash_mismatch:{promo_id}")

    if set(staged_hashes) != promotion_ids:
        errors.append("promotion_queue_not_exactly_staged_results")

    summary = state.get("summary") or {}
    results = state.get("results") or []
    blocked = state.get("blocked_submissions") or []
    if summary.get("accepted_records") != len(results):
        errors.append("summary_result_count_mismatch")
    if summary.get("staged_mutations") != len(staged_hashes):
        errors.append("summary_staged_count_mismatch")
    if summary.get("blocked") != len(blocked):
        errors.append("summary_blocked_count_mismatch")
    return errors
