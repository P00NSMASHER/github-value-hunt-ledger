from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence


PROMOTION_STATES = {
    "STAGED",
    "VERIFIED",
    "CANARY",
    "QUARANTINED",
    "GLOBAL_ELIGIBLE",
}

EXPECTED_REQUIREMENTS = {
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


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _sha256(value: Any) -> bool:
    raw = str(value or "").lower()
    return (
        len(raw) == 64
        and all(ch in "0123456789abcdef" for ch in raw)
    )


def _nonempty_sha256(value: Any) -> bool:
    return (
        _sha256(value)
        and str(value).lower() != hashlib.sha256(b"").hexdigest()
    )


def _finalize(row: dict[str, Any], field: str) -> dict[str, Any]:
    out = dict(row)
    out[field] = _stable_hash(out)
    return out


def _task_map(
    skill_eval_intake: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("skill_promotion_id")): row
        for row in skill_eval_intake.get("skill_promotion_queue") or []
        if row.get("skill_promotion_id")
    }


def _result_map(
    skill_eval_intake: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("skill_eval_result_id")): row
        for row in skill_eval_intake.get("results") or []
        if row.get("skill_eval_result_id")
    }


def _packet_errors(packet: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    result_id = str(packet.get("skill_promotion_result_id") or "")
    if not result_id.startswith("SPROMORES:"):
        errors.append("invalid_skill_promotion_result_id")

    for name in (
        "sensitive_material_involved",
        "benchmark_contaminated",
        "adversarial_task_passed",
        "adjacent_domain_task_passed",
        "curator_approved",
    ):
        if not isinstance(packet.get(name), bool):
            errors.append(f"{name}_boolean_required")

    if packet.get("sensitive_material_involved") is True:
        errors.append("sensitive_material_blocked")
    if packet.get("benchmark_contaminated") is True:
        errors.append("benchmark_contamination_blocked")

    successes = packet.get("distinct_success_task_ids")
    if not isinstance(successes, list):
        errors.append("distinct_success_task_ids_array_required")
    else:
        normalized = [str(value) for value in successes]
        if any(not value for value in normalized):
            errors.append("distinct_success_task_ids_nonempty_required")
        if len(set(normalized)) != len(normalized):
            errors.append("distinct_success_task_ids_must_be_unique")

    for name in (
        "heldout_tasks",
        "heldout_passes",
        "heldout_regressions",
        "canary_regressions",
    ):
        value = packet.get(name)
        if not isinstance(value, int) or value < 0:
            errors.append(f"{name}_nonnegative_integer_required")

    heldout_tasks = packet.get("heldout_tasks")
    heldout_passes = packet.get("heldout_passes")
    heldout_regressions = packet.get("heldout_regressions")
    if (
        isinstance(heldout_tasks, int)
        and isinstance(heldout_passes, int)
        and heldout_passes > heldout_tasks
    ):
        errors.append("heldout_passes_exceed_tasks")
    if (
        isinstance(heldout_tasks, int)
        and isinstance(heldout_regressions, int)
        and heldout_regressions > heldout_tasks
    ):
        errors.append("heldout_regressions_exceed_tasks")

    canary_ids = packet.get("canary_hunter_ids")
    if not isinstance(canary_ids, list):
        errors.append("canary_hunter_ids_array_required")
        canary_ids = []
    else:
        normalized = [str(value) for value in canary_ids]
        if any(not value for value in normalized):
            errors.append("canary_hunter_ids_nonempty_required")
        if len(set(normalized)) != len(normalized):
            errors.append("canary_hunter_ids_must_be_unique")

    canary_regressions = packet.get("canary_regressions")
    if (
        isinstance(canary_regressions, int)
        and canary_regressions > len(canary_ids)
    ):
        errors.append("canary_regressions_exceed_hunters")

    if isinstance(heldout_tasks, int) and heldout_tasks > 0:
        for name in ("heldout_set_sha256", "heldout_evidence_sha256"):
            if not _nonempty_sha256(packet.get(name)):
                errors.append(f"{name}_required_for_heldout")

    if packet.get("adversarial_task_passed") is True:
        if not _nonempty_sha256(packet.get("adversarial_evidence_sha256")):
            errors.append("adversarial_evidence_sha256_required")
    if packet.get("adjacent_domain_task_passed") is True:
        if not _nonempty_sha256(packet.get("adjacent_domain_evidence_sha256")):
            errors.append("adjacent_domain_evidence_sha256_required")
    if packet.get("curator_approved") is True:
        if not packet.get("curator_identity"):
            errors.append("curator_identity_required")
        if not _nonempty_sha256(packet.get("curator_evidence_sha256")):
            errors.append("curator_evidence_sha256_required")
    if canary_ids or (
        isinstance(canary_regressions, int)
        and canary_regressions > 0
    ):
        if not _nonempty_sha256(packet.get("canary_evidence_sha256")):
            errors.append("canary_evidence_sha256_required")

    return errors


def _binding_errors(
    packet: Mapping[str, Any],
    task: Mapping[str, Any] | None,
    evaluation: Mapping[str, Any] | None,
) -> list[str]:
    errors: list[str] = []
    if task is None:
        return ["skill_promotion_task_not_found"]
    if evaluation is None:
        return ["skill_eval_result_not_found"]

    if packet.get("skill_promotion_sha256") != task.get(
        "skill_promotion_sha256"
    ):
        errors.append("stale_or_mismatched_skill_promotion_hash")
    if packet.get("skill_eval_result_id") != task.get(
        "skill_eval_result_id"
    ):
        errors.append("skill_eval_result_id_mismatch")
    if packet.get("evaluation_result_sha256") != task.get(
        "evaluation_result_sha256"
    ):
        errors.append("evaluation_result_hash_mismatch")
    if evaluation.get("evaluation_result_sha256") != task.get(
        "evaluation_result_sha256"
    ):
        errors.append("skill_eval_result_hash_drift")

    for field in ("artifact_id", "candidate_version"):
        if packet.get(field) != task.get(field):
            errors.append(f"{field}_mismatch")
        if evaluation.get(field) != task.get(field):
            errors.append(f"evaluation_{field}_drift")

    if evaluation.get("state") != "STAGED_MUTATION":
        errors.append("evaluation_not_staged_mutation")
    if task.get("required_promotion_evidence") != EXPECTED_REQUIREMENTS:
        errors.append("promotion_requirements_drift")
    if task.get("automatic_global_promotion_allowed") is not False:
        errors.append("source_task_allows_auto_global_promotion")
    return errors


def _promotion_state(
    packet: Mapping[str, Any],
) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    successes = packet.get("distinct_success_task_ids") or []
    heldout_tasks = int(packet.get("heldout_tasks") or 0)
    heldout_passes = int(packet.get("heldout_passes") or 0)
    heldout_regressions = int(packet.get("heldout_regressions") or 0)
    canary_ids = packet.get("canary_hunter_ids") or []
    canary_regressions = int(packet.get("canary_regressions") or 0)

    if heldout_regressions > 0:
        return "QUARANTINED", ("heldout_regression",)
    if canary_regressions > 0:
        return "QUARANTINED", ("canary_regression",)

    if len(successes) < EXPECTED_REQUIREMENTS["distinct_success_tasks_min"]:
        reasons.append("two_distinct_success_tasks_required")
    if heldout_tasks < EXPECTED_REQUIREMENTS["heldout_tasks_min"]:
        reasons.append("minimum_five_heldout_tasks")
    if heldout_tasks > 0 and heldout_passes != heldout_tasks:
        reasons.append("heldout_pass_rate_below_one")
    if reasons:
        return "STAGED", tuple(reasons)

    if packet.get("adversarial_task_passed") is not True:
        return "STAGED", ("adversarial_task_required",)
    if packet.get("adjacent_domain_task_passed") is not True:
        return "STAGED", ("adjacent_domain_transfer_required",)
    if packet.get("curator_approved") is not True:
        return "VERIFIED", ("curator_approval_required_for_canary",)
    if len(canary_ids) < EXPECTED_REQUIREMENTS["canary_hunters_min"]:
        return "CANARY", ("three_hunter_canary_required",)
    return "GLOBAL_ELIGIBLE", ("integrator_global_approval_required",)


def build_skill_promotion_result_intake(
    skill_eval_intake: Mapping[str, Any],
    result_packets: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    tasks = _task_map(skill_eval_intake)
    evaluations = _result_map(skill_eval_intake)
    results: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    global_review: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for packet in result_packets:
        result_id = str(packet.get("skill_promotion_result_id") or "")
        if result_id in seen_ids:
            blocked.append(
                {
                    "skill_promotion_result_id": result_id,
                    "reasons": ["duplicate_skill_promotion_result_id"],
                }
            )
            continue
        seen_ids.add(result_id)

        task_id = str(packet.get("skill_promotion_id") or "")
        task = tasks.get(task_id)
        eval_id = str(packet.get("skill_eval_result_id") or "")
        evaluation = evaluations.get(eval_id)

        hard_errors = (
            _packet_errors(packet)
            + _binding_errors(packet, task, evaluation)
        )
        if hard_errors:
            blocked.append(
                {
                    "skill_promotion_result_id": result_id or "INVALID",
                    "skill_promotion_id": task_id or None,
                    "skill_eval_result_id": eval_id or None,
                    "reasons": sorted(set(hard_errors)),
                }
            )
            continue

        state, reasons = _promotion_state(packet)
        row = {
            "schema_version": 1,
            "skill_promotion_result_id": result_id,
            "skill_promotion_id": task_id,
            "skill_promotion_sha256": task.get("skill_promotion_sha256"),
            "skill_eval_result_id": eval_id,
            "evaluation_result_sha256": task.get(
                "evaluation_result_sha256"
            ),
            "artifact_id": task.get("artifact_id"),
            "candidate_version": task.get("candidate_version"),
            "state": state,
            "state_reasons": list(reasons),
            "distinct_success_task_ids": list(
                packet.get("distinct_success_task_ids") or []
            ),
            "heldout_tasks": packet.get("heldout_tasks"),
            "heldout_passes": packet.get("heldout_passes"),
            "heldout_regressions": packet.get("heldout_regressions"),
            "heldout_set_sha256": packet.get("heldout_set_sha256"),
            "heldout_evidence_sha256": packet.get(
                "heldout_evidence_sha256"
            ),
            "adversarial_task_passed": packet.get(
                "adversarial_task_passed"
            ),
            "adversarial_evidence_sha256": packet.get(
                "adversarial_evidence_sha256"
            ),
            "adjacent_domain_task_passed": packet.get(
                "adjacent_domain_task_passed"
            ),
            "adjacent_domain_evidence_sha256": packet.get(
                "adjacent_domain_evidence_sha256"
            ),
            "curator_approved": packet.get("curator_approved"),
            "curator_identity": packet.get("curator_identity"),
            "curator_evidence_sha256": packet.get(
                "curator_evidence_sha256"
            ),
            "canary_hunter_ids": list(
                packet.get("canary_hunter_ids") or []
            ),
            "canary_regressions": packet.get("canary_regressions"),
            "canary_evidence_sha256": packet.get(
                "canary_evidence_sha256"
            ),
            "automatic_live_write_allowed": False,
            "automatic_global_promotion_allowed": False,
            "integrator_global_approval_required": True,
        }
        row = _finalize(row, "promotion_result_sha256")
        results.append(row)

        if state == "GLOBAL_ELIGIBLE":
            review = {
                "schema_version": 1,
                "global_review_id": "GLOBALREVIEW:" + _stable_hash(
                    {
                        "skill_promotion_result_id": result_id,
                        "promotion_result_sha256": row[
                            "promotion_result_sha256"
                        ],
                    }
                )[:16],
                "skill_promotion_result_id": result_id,
                "promotion_result_sha256": row[
                    "promotion_result_sha256"
                ],
                "artifact_id": row["artifact_id"],
                "candidate_version": row["candidate_version"],
                "integrator_approval_required": True,
                "automatic_global_promotion_allowed": False,
            }
            global_review.append(
                _finalize(review, "global_review_sha256")
            )

    results.sort(key=lambda row: row["skill_promotion_result_id"])
    blocked.sort(
        key=lambda row: (
            str(row.get("skill_promotion_result_id") or ""),
            ",".join(row.get("reasons") or []),
        )
    )
    global_review.sort(key=lambda row: row["global_review_id"])

    return {
        "schema_version": 1,
        "mode": "skill_promotion_result_intake",
        "policy_effect": "none",
        "automatic_live_write_enabled": False,
        "automatic_global_promotion_enabled": False,
        "summary": {
            "submitted": len(result_packets),
            "accepted_records": len(results),
            "staged": sum(1 for row in results if row["state"] == "STAGED"),
            "verified": sum(1 for row in results if row["state"] == "VERIFIED"),
            "canary": sum(1 for row in results if row["state"] == "CANARY"),
            "quarantined": sum(
                1 for row in results if row["state"] == "QUARANTINED"
            ),
            "global_eligible": sum(
                1 for row in results if row["state"] == "GLOBAL_ELIGIBLE"
            ),
            "blocked": len(blocked),
        },
        "results": results,
        "global_review_queue": global_review,
        "blocked_submissions": blocked,
    }


def validate_skill_promotion_result_intake(
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

    result_ids: set[str] = set()
    global_hashes: dict[str, str] = {}
    for row in state.get("results") or []:
        result_id = str(row.get("skill_promotion_result_id") or "")
        if result_id in result_ids:
            errors.append(f"duplicate_promotion_result:{result_id}")
        result_ids.add(result_id)
        if row.get("state") not in PROMOTION_STATES:
            errors.append(f"invalid_promotion_state:{result_id}")
        if row.get("automatic_live_write_allowed") is not False:
            errors.append(f"promotion_live_write_enabled:{result_id}")
        if row.get("automatic_global_promotion_allowed") is not False:
            errors.append(f"promotion_auto_global_enabled:{result_id}")
        if row.get("integrator_global_approval_required") is not True:
            errors.append(f"integrator_approval_not_required:{result_id}")

        supplied = row.get("promotion_result_sha256")
        body = dict(row)
        body.pop("promotion_result_sha256", None)
        if supplied != _stable_hash(body):
            errors.append(f"promotion_result_hash_mismatch:{result_id}")

        if row.get("state") == "GLOBAL_ELIGIBLE":
            global_hashes[result_id] = str(supplied)

    review_ids: set[str] = set()
    for row in state.get("global_review_queue") or []:
        result_id = str(row.get("skill_promotion_result_id") or "")
        if result_id in review_ids:
            errors.append(f"duplicate_global_review:{result_id}")
        review_ids.add(result_id)
        if result_id not in global_hashes:
            errors.append(f"global_review_without_eligible_result:{result_id}")
        elif row.get("promotion_result_sha256") != global_hashes[result_id]:
            errors.append(f"global_review_stale_result_hash:{result_id}")
        if row.get("integrator_approval_required") is not True:
            errors.append(f"global_review_missing_integrator_gate:{result_id}")
        if row.get("automatic_global_promotion_allowed") is not False:
            errors.append(f"global_review_auto_promotion_enabled:{result_id}")

        supplied = row.get("global_review_sha256")
        body = dict(row)
        body.pop("global_review_sha256", None)
        if supplied != _stable_hash(body):
            errors.append(f"global_review_hash_mismatch:{result_id}")

    if set(global_hashes) != review_ids:
        errors.append("global_review_queue_not_exactly_global_eligible")

    summary = state.get("summary") or {}
    results = state.get("results") or []
    blocked = state.get("blocked_submissions") or []
    if summary.get("accepted_records") != len(results):
        errors.append("summary_result_count_mismatch")
    if summary.get("blocked") != len(blocked):
        errors.append("summary_blocked_count_mismatch")
    for name, state_name in (
        ("staged", "STAGED"),
        ("verified", "VERIFIED"),
        ("canary", "CANARY"),
        ("quarantined", "QUARANTINED"),
        ("global_eligible", "GLOBAL_ELIGIBLE"),
    ):
        if summary.get(name) != sum(
            1 for row in results if row.get("state") == state_name
        ):
            errors.append(f"summary_{name}_count_mismatch")

    return errors
