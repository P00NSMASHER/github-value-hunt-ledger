from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from production.learning_engine import (
    FailureDecision,
    FailureEvent,
    assess_failure_for_repair,
)


REPAIR_STATES = {
    "NEEDS_REPRODUCTION",
    "READY_FOR_REPAIR",
    "BLOCKED",
}
ALERT_TYPES = {
    "overfit_signal",
    "confirm_regression_signal",
}
PROHIBITED_MUTATION_AREAS = (
    "benchmark_gold",
    "benchmark_scoring",
    "sealed_holdout",
    "verifier",
    "evaluator",
    "controller",
    "credentials",
    "safety_policy",
    "promotion_history",
)


def _stable_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _task_id(source_kind: str, source_id: str, target_id: str) -> str:
    digest = _stable_hash(
        {
            "source_kind": source_kind,
            "source_id": source_id,
            "target_id": target_id,
        }
    )[:16]
    return f"REPAIR:{digest}"


def _base_memory_key(memory_key: str) -> tuple[str | None, str]:
    if memory_key.startswith("CTX:") and "::" in memory_key:
        scope, base = memory_key[4:].split("::", 1)
        return scope, base
    return None, memory_key


def _target_type_from_memory_key(memory_key: str) -> str:
    _scope, base = _base_memory_key(memory_key)
    if base.startswith("QF:"):
        return "query_family"
    if base.startswith("MOVE:"):
        return "search_move"
    if base.startswith("STRAT:"):
        return "search_skill"
    return "memory"


def _mutation_scope(target_type: str, target_id: str) -> dict[str, Any]:
    return {
        "mode": "logical_target_only",
        "target_type": target_type,
        "target_id": target_id,
        "prohibited_areas": list(PROHIBITED_MUTATION_AREAS),
        "automatic_write_allowed": False,
        "global_promotion_allowed": False,
    }


def _episode_matches_memory_key(
    episode: Mapping[str, Any],
    memory_key: str,
) -> bool:
    objective_scope, base = _base_memory_key(memory_key)
    state = episode.get("state") or {}
    action = episode.get("action") or {}
    if objective_scope and state.get("search_objective_id") != objective_scope:
        return False

    if base.startswith("STRAT:"):
        return action.get("strategy_id") == base
    if base.startswith("QF:"):
        return action.get("query_family_id") == base
    if base.startswith("MOVE:"):
        wanted = base[5:]
        for move in action.get("search_moves") or []:
            if not isinstance(move, Mapping):
                continue
            key = str(
                move.get("key")
                or (
                    f"MOVE:{move.get('move_type')}"
                    if move.get("move_type")
                    else ""
                )
            )
            if key == base or key == wanted:
                return True
        return base in set(action.get("search_move_ids") or [])
    return False


def _negative_confirm_refs(
    training_environment: Mapping[str, Any],
    memory_key: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for episode in training_environment.get("episodes") or []:
        if episode.get("split") != "confirm":
            continue
        if not _episode_matches_memory_key(episode, memory_key):
            continue
        reward = (episode.get("reward") or {}).get("training_reward")
        if not isinstance(reward, (int, float)) or reward >= 0:
            continue
        provenance = episode.get("provenance") or {}
        rows.append(
            {
                "run_id": episode.get("run_id"),
                "reward": float(reward),
                "reward_stage": (episode.get("reward") or {}).get("reward_stage"),
                "durable_evidence_path": provenance.get("durable_evidence_path"),
                "episode_sha256": episode.get("episode_sha256"),
            }
        )
    rows.sort(
        key=lambda row: (
            row["reward"],
            str(row.get("run_id") or ""),
        )
    )
    return rows


def _failure_event(packet: Mapping[str, Any]) -> FailureEvent:
    return FailureEvent(
        failure_id=str(packet.get("failure_id") or ""),
        run_id=str(packet.get("run_id") or ""),
        hunter_id=str(packet.get("hunter_id") or ""),
        target_type=str(packet.get("target_type") or ""),
        target_id=str(packet.get("target_id") or ""),
        failure_class=str(packet.get("failure_class") or ""),
        observation=str(packet.get("observation") or ""),
        reproduction_steps=tuple(
            str(item)
            for item in packet.get("reproduction_steps") or []
        ),
        evidence_refs=tuple(
            str(item)
            for item in packet.get("evidence_refs") or []
        ),
        proposed_regression_test=(
            str(packet["proposed_regression_test"])
            if packet.get("proposed_regression_test")
            else None
        ),
        sensitive_material_involved=bool(
            packet.get("sensitive_material_involved", False)
        ),
        benchmark_contaminated=bool(
            packet.get("benchmark_contaminated", False)
        ),
    )


def _finalize_task(task: dict[str, Any]) -> dict[str, Any]:
    body = dict(task)
    body["task_sha256"] = _stable_hash(body)
    return body


def build_repair_queue(
    learning_state: Mapping[str, Any],
    failure_packets: Sequence[Mapping[str, Any]],
    training_environment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    training_environment = training_environment or {}
    tasks: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []

    for packet in failure_packets:
        event = _failure_event(packet)
        assessment = assess_failure_for_repair(event)
        source_id = event.failure_id or f"invalid:{assessment.signature[:12]}"
        if assessment.decision is FailureDecision.BLOCKED:
            blocked.append(
                {
                    "source_kind": "failure_packet",
                    "source_id": source_id,
                    "signature": assessment.signature,
                    "reasons": list(assessment.reasons),
                }
            )
            continue

        task = {
            "schema_version": 1,
            "repair_task_id": _task_id(
                "failure_packet",
                source_id,
                event.target_id,
            ),
            "state": "READY_FOR_REPAIR",
            "priority_score": 100,
            "source": {
                "kind": "failure_packet",
                "id": source_id,
                "run_id": event.run_id,
                "signature": assessment.signature,
            },
            "target": {
                "type": event.target_type,
                "id": event.target_id,
            },
            "failure_class": event.failure_class,
            "failure_observation": event.observation,
            "reproduction_steps": list(event.reproduction_steps),
            "evidence_refs": list(event.evidence_refs),
            "regression_test_requirement": event.proposed_regression_test,
            "confirm_failure_refs": [],
            "mutation_scope": _mutation_scope(
                event.target_type,
                event.target_id,
            ),
            "next_action": (
                "Create one bounded candidate repair inside the logical target, "
                "add/run the stated regression test, freeze the diff hash and "
                "decision history, then submit to assess_repair_candidate. "
                "Do not change the live/global skill."
            ),
        }
        tasks.append(_finalize_task(task))

    existing_targets = {
        (
            task["target"]["type"],
            task["target"]["id"],
        )
        for task in tasks
    }
    for alert in learning_state.get("learning_alerts") or []:
        alert_type = str(alert.get("type") or "")
        if alert_type not in ALERT_TYPES:
            continue
        memory_key = str(alert.get("memory_key") or "")
        if not memory_key:
            continue
        target_type = _target_type_from_memory_key(memory_key)
        target_key = (target_type, memory_key)
        if target_key in existing_targets:
            continue

        confirm_refs = _negative_confirm_refs(
            training_environment,
            memory_key,
        )
        priority = (
            85
            if alert_type == "confirm_regression_signal"
            else 75
        )
        task = {
            "schema_version": 1,
            "repair_task_id": _task_id(
                "learning_alert",
                f"{alert_type}:{memory_key}",
                memory_key,
            ),
            "state": "NEEDS_REPRODUCTION",
            "priority_score": priority,
            "source": {
                "kind": "learning_alert",
                "id": f"{alert_type}:{memory_key}",
                "alert_type": alert_type,
            },
            "target": {
                "type": target_type,
                "id": memory_key,
            },
            "failure_class": (
                "regression"
                if alert_type == "confirm_regression_signal"
                else "overfit"
            ),
            "failure_observation": (
                "Train-ready experience failed independent confirmation; "
                "live prior remains suppressed."
            ),
            "reproduction_steps": [],
            "evidence_refs": [
                ref["durable_evidence_path"]
                for ref in confirm_refs
                if ref.get("durable_evidence_path")
            ],
            "regression_test_requirement": None,
            "confirm_failure_refs": confirm_refs,
            "mutation_scope": _mutation_scope(
                target_type,
                memory_key,
            ),
            "next_action": (
                "Reproduce the confirm failure in a bounded clean context and "
                "submit an immutable learning-failure packet with concrete "
                "evidence and a regression test. Mutation is not authorized "
                "from a statistical alert alone."
            ),
        }
        tasks.append(_finalize_task(task))

    deduped: dict[str, dict[str, Any]] = {}
    for task in sorted(
        tasks,
        key=lambda item: (
            -int(item["priority_score"]),
            item["repair_task_id"],
        ),
    ):
        deduped.setdefault(task["repair_task_id"], task)

    final_tasks = list(deduped.values())
    return {
        "schema_version": 1,
        "mode": "advisory_repair_workbench",
        "policy_effect": "none",
        "automatic_mutation_enabled": False,
        "automatic_promotion_enabled": False,
        "summary": {
            "tasks": len(final_tasks),
            "ready_for_repair": sum(
                1
                for task in final_tasks
                if task["state"] == "READY_FOR_REPAIR"
            ),
            "needs_reproduction": sum(
                1
                for task in final_tasks
                if task["state"] == "NEEDS_REPRODUCTION"
            ),
            "blocked_sources": len(blocked),
        },
        "tasks": final_tasks,
        "blocked_sources": sorted(
            blocked,
            key=lambda item: (
                item["source_id"],
                item["signature"],
            ),
        ),
    }


def validate_repair_queue(queue: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if queue.get("schema_version") != 1:
        errors.append("unexpected_schema_version")
    if queue.get("policy_effect") != "none":
        errors.append("policy_effect_must_be_none")
    if queue.get("automatic_mutation_enabled") is not False:
        errors.append("automatic_mutation_must_be_disabled")
    if queue.get("automatic_promotion_enabled") is not False:
        errors.append("automatic_promotion_must_be_disabled")

    seen_ids: set[str] = set()
    for task in queue.get("tasks") or []:
        task_id = task.get("repair_task_id")
        if not isinstance(task_id, str) or not task_id.startswith("REPAIR:"):
            errors.append("invalid_repair_task_id")
            continue
        if task_id in seen_ids:
            errors.append(f"duplicate_repair_task_id:{task_id}")
        seen_ids.add(task_id)

        state = task.get("state")
        if state not in REPAIR_STATES - {"BLOCKED"}:
            errors.append(f"invalid_active_state:{task_id}:{state}")

        priority = task.get("priority_score")
        if not isinstance(priority, int) or not 0 <= priority <= 100:
            errors.append(f"invalid_priority:{task_id}")

        supplied_hash = task.get("task_sha256")
        body = dict(task)
        body.pop("task_sha256", None)
        if supplied_hash != _stable_hash(body):
            errors.append(f"task_hash_mismatch:{task_id}")

        scope = task.get("mutation_scope") or {}
        if scope.get("automatic_write_allowed") is not False:
            errors.append(f"automatic_write_enabled:{task_id}")
        if scope.get("global_promotion_allowed") is not False:
            errors.append(f"global_promotion_enabled:{task_id}")
        prohibited = set(scope.get("prohibited_areas") or [])
        if not set(PROHIBITED_MUTATION_AREAS).issubset(prohibited):
            errors.append(f"mutation_scope_too_broad:{task_id}")

        source = task.get("source") or {}
        if state == "READY_FOR_REPAIR":
            if source.get("kind") != "failure_packet":
                errors.append(f"ready_without_failure_packet:{task_id}")
            if not task.get("reproduction_steps"):
                errors.append(f"ready_without_reproduction:{task_id}")
            if not task.get("evidence_refs"):
                errors.append(f"ready_without_evidence:{task_id}")
            if not task.get("regression_test_requirement"):
                errors.append(f"ready_without_regression_test:{task_id}")
        elif state == "NEEDS_REPRODUCTION":
            if task.get("regression_test_requirement") is not None:
                errors.append(f"alert_premature_regression_test:{task_id}")
            if source.get("kind") != "learning_alert":
                errors.append(f"reproduction_state_wrong_source:{task_id}")

    summary = queue.get("summary") or {}
    tasks = queue.get("tasks") or []
    if summary.get("tasks") != len(tasks):
        errors.append("summary_task_count_mismatch")
    if summary.get("ready_for_repair") != sum(
        1 for task in tasks if task.get("state") == "READY_FOR_REPAIR"
    ):
        errors.append("summary_ready_count_mismatch")
    if summary.get("needs_reproduction") != sum(
        1 for task in tasks if task.get("state") == "NEEDS_REPRODUCTION"
    ):
        errors.append("summary_reproduction_count_mismatch")

    return errors
