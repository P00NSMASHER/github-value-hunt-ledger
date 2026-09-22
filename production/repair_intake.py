from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from production.learning_engine import (
    RepairCandidate,
    RepairDecision,
    assess_repair_candidate,
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


def _is_sha256(value: Any) -> bool:
    raw = str(value or "").lower()
    return (
        len(raw) == 64
        and all(ch in "0123456789abcdef" for ch in raw)
    )


def _finalize(row: dict[str, Any], field: str) -> dict[str, Any]:
    out = dict(row)
    out[field] = _stable_hash(out)
    return out


def _repair_tasks(queue: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(task.get("repair_task_id")): task
        for task in queue.get("tasks") or []
        if task.get("repair_task_id")
    }


def _binding_errors(
    packet: Mapping[str, Any],
    task: Mapping[str, Any] | None,
) -> list[str]:
    errors: list[str] = []
    if task is None:
        return ["repair_task_not_found"]
    if task.get("state") != "READY_FOR_REPAIR":
        errors.append("repair_task_not_ready")
    if packet.get("repair_task_sha256") != task.get("task_sha256"):
        errors.append("stale_or_mismatched_repair_task_hash")

    target = task.get("target") or {}
    if packet.get("target_type") != target.get("type"):
        errors.append("target_type_mismatch")
    if packet.get("target_id") != target.get("id"):
        errors.append("target_id_mismatch")
    if (
        packet.get("regression_test_requirement")
        != task.get("regression_test_requirement")
    ):
        errors.append("regression_test_requirement_mismatch")

    scope = task.get("mutation_scope") or {}
    if scope.get("automatic_write_allowed") is not False:
        errors.append("source_task_allows_automatic_write")
    if scope.get("global_promotion_allowed") is not False:
        errors.append("source_task_allows_global_promotion")

    declared = packet.get("changed_logical_targets") or []
    if declared != [target.get("id")]:
        errors.append("mutation_scope_not_exactly_one_authorized_target")

    if packet.get("sensitive_material_involved"):
        errors.append("sensitive_material_blocked")
    if packet.get("benchmark_contaminated"):
        errors.append("benchmark_contamination_blocked")
    return errors


def _packet_errors(packet: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    candidate_id = str(packet.get("repair_candidate_id") or "")
    if not candidate_id.startswith("RCAND:"):
        errors.append("invalid_repair_candidate_id")
    if not packet.get("artifact_id"):
        errors.append("artifact_id_required")
    baseline = str(packet.get("baseline_version") or "")
    candidate = str(packet.get("candidate_version") or "")
    if not baseline:
        errors.append("baseline_version_required")
    if not candidate:
        errors.append("candidate_version_required")
    if baseline and candidate and baseline == candidate:
        errors.append("candidate_version_must_differ_from_baseline")
    if not packet.get("baseline_artifact_ref"):
        errors.append("baseline_artifact_ref_required")
    if not packet.get("candidate_artifact_ref"):
        errors.append("candidate_artifact_ref_required")
    if (
        packet.get("baseline_artifact_ref")
        and packet.get("candidate_artifact_ref")
        and packet.get("baseline_artifact_ref")
        == packet.get("candidate_artifact_ref")
    ):
        errors.append("candidate_artifact_must_differ_from_baseline")

    baseline_hash = packet.get("baseline_artifact_sha256")
    candidate_hash = packet.get("candidate_artifact_sha256")
    if not _is_sha256(baseline_hash):
        errors.append("baseline_artifact_sha256_required")
    if not _is_sha256(candidate_hash):
        errors.append("candidate_artifact_sha256_required")
    if (
        _is_sha256(baseline_hash)
        and _is_sha256(candidate_hash)
        and str(baseline_hash).lower() == str(candidate_hash).lower()
    ):
        errors.append("candidate_artifact_hash_must_differ_from_baseline")

    diff_hash = str(packet.get("diff_hash") or "")
    if len(diff_hash) != 64 or any(ch not in "0123456789abcdef" for ch in diff_hash.lower()):
        errors.append("diff_hash_must_be_sha256")
    elif diff_hash.lower() == hashlib.sha256(b"").hexdigest():
        errors.append("empty_diff_not_allowed")

    for field_name in (
        "unrelated_files_changed",
        "sensitive_material_involved",
        "benchmark_contaminated",
    ):
        if not isinstance(packet.get(field_name), bool):
            errors.append(f"{field_name}_boolean_required")

    total = packet.get("regression_tests_total")
    passed = packet.get("regression_tests_passed")
    if not isinstance(total, int) or total < 1:
        errors.append("positive_regression_test_count_required")
    if not isinstance(passed, int) or passed < 0:
        errors.append("valid_regression_pass_count_required")
    if (
        isinstance(total, int)
        and isinstance(passed, int)
        and passed > total
    ):
        errors.append("regression_passes_exceed_total")
    if not packet.get("regression_test_evidence_refs"):
        errors.append("regression_test_evidence_required")
    if not _is_sha256(packet.get("regression_test_evidence_sha256")):
        errors.append("regression_test_evidence_sha256_required")
    if not packet.get("decision_history_ref"):
        errors.append("decision_history_ref_required")
    if not _is_sha256(packet.get("decision_history_sha256")):
        errors.append("decision_history_sha256_required")
    return errors


def build_repair_candidate_intake(
    repair_queue: Mapping[str, Any],
    candidate_packets: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    tasks = _repair_tasks(repair_queue)
    candidates: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    eval_queue: list[dict[str, Any]] = []

    seen_ids: set[str] = set()
    for packet in candidate_packets:
        candidate_id = str(packet.get("repair_candidate_id") or "")
        if candidate_id in seen_ids:
            blocked.append(
                {
                    "repair_candidate_id": candidate_id,
                    "reasons": ["duplicate_repair_candidate_id"],
                }
            )
            continue
        seen_ids.add(candidate_id)

        task_id = str(packet.get("repair_task_id") or "")
        task = tasks.get(task_id)
        hard_errors = _packet_errors(packet) + _binding_errors(packet, task)
        if hard_errors:
            blocked.append(
                {
                    "repair_candidate_id": candidate_id or "INVALID",
                    "repair_task_id": task_id or None,
                    "reasons": sorted(set(hard_errors)),
                }
            )
            continue

        source = task.get("source") or {}
        assessment = assess_repair_candidate(
            RepairCandidate(
                failure_id=str(
                    source.get("reported_failure_id")
                    or source.get("id")
                    or ""
                ),
                skill_id=str(packet.get("artifact_id")),
                candidate_version=str(packet.get("candidate_version")),
                regression_tests_total=int(packet.get("regression_tests_total")),
                regression_tests_passed=int(packet.get("regression_tests_passed")),
                diff_hash=str(packet.get("diff_hash")),
                decision_history_ref=str(packet.get("decision_history_ref")),
                unrelated_files_changed=bool(
                    packet.get("unrelated_files_changed", False)
                ),
                source_failure_blocked=False,
            )
        )
        state = (
            "READY_FOR_SKILL_EVAL"
            if assessment.decision is RepairDecision.READY_FOR_SKILL_EVAL
            else "REJECTED"
        )
        row = {
            "schema_version": 1,
            "repair_candidate_id": candidate_id,
            "repair_task_id": task_id,
            "repair_task_sha256": task.get("task_sha256"),
            "state": state,
            "assessment_reasons": list(assessment.reasons),
            "target": dict(task.get("target") or {}),
            "artifact_id": packet.get("artifact_id"),
            "baseline_version": packet.get("baseline_version"),
            "candidate_version": packet.get("candidate_version"),
            "baseline_artifact_ref": packet.get("baseline_artifact_ref"),
            "baseline_artifact_sha256": packet.get("baseline_artifact_sha256"),
            "candidate_artifact_ref": packet.get("candidate_artifact_ref"),
            "candidate_artifact_sha256": packet.get("candidate_artifact_sha256"),
            "diff_hash": packet.get("diff_hash"),
            "changed_logical_targets": list(
                packet.get("changed_logical_targets") or []
            ),
            "regression_test_requirement": packet.get(
                "regression_test_requirement"
            ),
            "regression_tests_total": packet.get("regression_tests_total"),
            "regression_tests_passed": packet.get("regression_tests_passed"),
            "regression_test_evidence_refs": list(
                packet.get("regression_test_evidence_refs") or []
            ),
            "regression_test_evidence_sha256": packet.get(
                "regression_test_evidence_sha256"
            ),
            "decision_history_ref": packet.get("decision_history_ref"),
            "decision_history_sha256": packet.get("decision_history_sha256"),
            "automatic_write_allowed": False,
            "global_promotion_allowed": False,
        }
        row = _finalize(row, "candidate_record_sha256")
        candidates.append(row)

        if state == "READY_FOR_SKILL_EVAL":
            eval_packet = {
                "schema_version": 1,
                "skill_eval_id": "SKILLEVAL:" + _stable_hash(
                    {
                        "repair_candidate_id": candidate_id,
                        "candidate_record_sha256": row["candidate_record_sha256"],
                    }
                )[:16],
                "repair_candidate_id": candidate_id,
                "candidate_record_sha256": row["candidate_record_sha256"],
                "artifact_id": packet.get("artifact_id"),
                "baseline_version": packet.get("baseline_version"),
                "candidate_version": packet.get("candidate_version"),
                "required_evaluation": {
                    "mutate_dev_examples_min": 4,
                    "promotion_test_examples_min": 5,
                    "min_score_delta": 0.02,
                    "hard_regressions_max": 0,
                    "split_fingerprints_disjoint_required": True,
                    "provenance_complete_required": True,
                    "adversarial_and_adjacent_domain_gates_still_required": True,
                },
                "automatic_global_promotion_allowed": False,
            }
            eval_queue.append(
                _finalize(eval_packet, "skill_eval_sha256")
            )

    candidates.sort(key=lambda row: row["repair_candidate_id"])
    blocked.sort(
        key=lambda row: (
            str(row.get("repair_candidate_id") or ""),
            ",".join(row.get("reasons") or []),
        )
    )
    eval_queue.sort(key=lambda row: row["skill_eval_id"])
    return {
        "schema_version": 1,
        "mode": "repair_candidate_intake",
        "policy_effect": "none",
        "automatic_write_enabled": False,
        "automatic_global_promotion_enabled": False,
        "summary": {
            "submitted": len(candidate_packets),
            "accepted_records": len(candidates),
            "ready_for_skill_eval": sum(
                1
                for row in candidates
                if row["state"] == "READY_FOR_SKILL_EVAL"
            ),
            "rejected": sum(
                1 for row in candidates if row["state"] == "REJECTED"
            ),
            "blocked": len(blocked),
        },
        "candidates": candidates,
        "skill_eval_queue": eval_queue,
        "blocked_submissions": blocked,
    }


def validate_repair_candidate_intake(
    state: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if state.get("schema_version") != 1:
        errors.append("unexpected_schema_version")
    if state.get("policy_effect") != "none":
        errors.append("policy_effect_must_be_none")
    if state.get("automatic_write_enabled") is not False:
        errors.append("automatic_write_must_be_disabled")
    if state.get("automatic_global_promotion_enabled") is not False:
        errors.append("automatic_global_promotion_must_be_disabled")

    candidate_ids: set[str] = set()
    ready_hashes: dict[str, str] = {}
    for row in state.get("candidates") or []:
        candidate_id = row.get("repair_candidate_id")
        if candidate_id in candidate_ids:
            errors.append(f"duplicate_candidate_record:{candidate_id}")
        candidate_ids.add(candidate_id)
        if row.get("automatic_write_allowed") is not False:
            errors.append(f"candidate_auto_write_enabled:{candidate_id}")
        if row.get("global_promotion_allowed") is not False:
            errors.append(f"candidate_global_promotion_enabled:{candidate_id}")

        supplied = row.get("candidate_record_sha256")
        body = dict(row)
        body.pop("candidate_record_sha256", None)
        if supplied != _stable_hash(body):
            errors.append(f"candidate_hash_mismatch:{candidate_id}")

        if row.get("state") == "READY_FOR_SKILL_EVAL":
            if row.get("assessment_reasons"):
                errors.append(f"ready_candidate_has_rejection_reasons:{candidate_id}")
            ready_hashes[str(candidate_id)] = str(supplied)
        elif row.get("state") != "REJECTED":
            errors.append(f"invalid_candidate_state:{candidate_id}")

    eval_candidate_ids: set[str] = set()
    for row in state.get("skill_eval_queue") or []:
        eval_id = row.get("skill_eval_id")
        candidate_id = str(row.get("repair_candidate_id") or "")
        if candidate_id in eval_candidate_ids:
            errors.append(f"duplicate_skill_eval_candidate:{candidate_id}")
        eval_candidate_ids.add(candidate_id)
        if candidate_id not in ready_hashes:
            errors.append(f"skill_eval_without_ready_candidate:{eval_id}")
        elif row.get("candidate_record_sha256") != ready_hashes[candidate_id]:
            errors.append(f"skill_eval_stale_candidate_hash:{eval_id}")
        if row.get("automatic_global_promotion_allowed") is not False:
            errors.append(f"skill_eval_auto_promotion_enabled:{eval_id}")

        supplied = row.get("skill_eval_sha256")
        body = dict(row)
        body.pop("skill_eval_sha256", None)
        if supplied != _stable_hash(body):
            errors.append(f"skill_eval_hash_mismatch:{eval_id}")

    if set(ready_hashes) != eval_candidate_ids:
        errors.append("skill_eval_queue_not_exactly_ready_candidates")

    summary = state.get("summary") or {}
    candidates = state.get("candidates") or []
    blocked = state.get("blocked_submissions") or []
    if summary.get("accepted_records") != len(candidates):
        errors.append("summary_candidate_count_mismatch")
    if summary.get("blocked") != len(blocked):
        errors.append("summary_blocked_count_mismatch")
    if summary.get("ready_for_skill_eval") != len(ready_hashes):
        errors.append("summary_skill_eval_count_mismatch")
    return errors
