#!/usr/bin/env python3
"""Compile observed hunter experience into an advisory value-learning state.

This tool is deliberately read-only with respect to search policy. It consumes
canonical search/outcome ledgers, applies the production learning engine, and
emits an inspectable JSON artifact. Existing evidence thresholds still control
any later policy change.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from production.learning_engine import (
    FailureEvent,
    assess_failure_for_repair,
    learn_training_episode_memory,
)
from production.training_environment import build_training_environment


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{path}:{line_no}: invalid JSON: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise ValueError(
                f"{path}:{line_no}: expected JSON object"
            )
        rows.append(value)
    return rows


def load_failure_events(
    path: Path,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    if not path.exists():
        return []
    out: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for file_path in sorted(path.glob("*.json")):
        value = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(
                f"{file_path}: expected JSON object"
            )

        event = FailureEvent(
            failure_id=str(value.get("failure_id") or ""),
            run_id=str(value.get("run_id") or ""),
            hunter_id=str(value.get("hunter_id") or ""),
            target_type=str(value.get("target_type") or ""),
            target_id=str(value.get("target_id") or ""),
            failure_class=str(value.get("failure_class") or ""),
            observation=str(value.get("observation") or ""),
            reproduction_steps=tuple(
                str(item)
                for item in value.get("reproduction_steps") or []
            ),
            evidence_refs=tuple(
                str(item)
                for item in value.get("evidence_refs") or []
            ),
            proposed_regression_test=(
                str(value["proposed_regression_test"])
                if value.get("proposed_regression_test")
                else None
            ),
            sensitive_material_involved=bool(
                value.get("sensitive_material_involved", False)
            ),
            benchmark_contaminated=bool(
                value.get("benchmark_contaminated", False)
            ),
        )
        assessment = assess_failure_for_repair(event)
        out.append(
            (
                value,
                {
                    "file": str(file_path),
                    "failure_id": event.failure_id,
                    "signature": assessment.signature,
                    "decision": assessment.decision.value,
                    "reasons": list(assessment.reasons),
                },
            )
        )
    return out


def episode_support_index(
    episodes: Iterable[dict[str, Any]],
    *,
    split: str,
) -> dict[str, dict[str, Any]]:
    """Measure independent support for a learned memory key."""
    out: dict[str, dict[str, Any]] = {}
    for episode in episodes:
        if episode.get("split") != split:
            continue
        reward = (
            episode.get("reward") or {}
        ).get("training_reward")
        if not isinstance(reward, (int, float)):
            continue
        observation = episode.get("observation") or {}
        deep = observation.get("deep_inspected")
        deep_value = deep if isinstance(deep, int) and deep >= 0 else 0
        action = episode.get("action") or {}
        keys: list[str] = []

        strategy = action.get("strategy_id")
        if isinstance(strategy, str) and strategy.startswith("STRAT:"):
            keys.append(strategy)

        query_family = action.get("query_family_id")
        if (
            isinstance(query_family, str)
            and query_family.startswith("QF:")
        ):
            keys.append(query_family)

        for move_id in action.get("search_move_ids") or []:
            if isinstance(move_id, str) and move_id:
                keys.append(
                    move_id
                    if move_id.startswith("MOVE:")
                    else f"MOVE:{move_id}"
                )

        for key in dict.fromkeys(keys):
            bucket = out.setdefault(
                key,
                {
                    "measured_runs": 0,
                    "deep_inspections": 0,
                    "reward_sum": 0.0,
                    "min_reward": None,
                    "positive_runs": 0,
                },
            )
            bucket["measured_runs"] += 1
            bucket["deep_inspections"] += deep_value
            bucket["reward_sum"] += float(reward)
            bucket["min_reward"] = (
                float(reward)
                if bucket["min_reward"] is None
                else min(
                    float(bucket["min_reward"]),
                    float(reward),
                )
            )
            if float(reward) > 0:
                bucket["positive_runs"] += 1

    for bucket in out.values():
        runs = bucket["measured_runs"]
        bucket["mean_reward"] = (
            bucket["reward_sum"] / runs
            if runs
            else 0.0
        )
        del bucket["reward_sum"]
    return out


def compile_state(
    search_runs: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    failure_dir: Path,
) -> dict[str, Any]:
    training_environment = build_training_environment(
        search_runs,
        outcomes,
    )
    memory, observations = learn_training_episode_memory(
        training_environment["episodes"],
    )
    train_support = episode_support_index(
        training_environment["episodes"],
        split="train",
    )
    confirm_support = episode_support_index(
        training_environment["episodes"],
        split="confirm",
    )

    records: list[dict[str, Any]] = []
    for record in memory.records():
        row = record.to_dict()
        row["support"] = train_support.get(
            record.key,
            {
                "measured_runs": 0,
                "deep_inspections": 0,
                "min_reward": None,
                "positive_runs": 0,
                "mean_reward": 0.0,
            },
        )
        row["confirm_support"] = confirm_support.get(
            record.key,
            {
                "measured_runs": 0,
                "deep_inspections": 0,
                "min_reward": None,
                "positive_runs": 0,
                "mean_reward": 0.0,
            },
        )
        row["train_evidence_ready"] = (
            row["support"]["measured_runs"] >= 5
            and row["support"]["deep_inspections"] >= 20
        )
        row["confirm_evidence_ready"] = (
            row["confirm_support"]["measured_runs"] >= 2
            and row["confirm_support"]["deep_inspections"] >= 6
            and row["confirm_support"]["mean_reward"] >= 0.0
        )
        row["eligible_for_policy_consideration"] = (
            row["train_evidence_ready"]
            and row["confirm_evidence_ready"]
        )
        if row["eligible_for_policy_consideration"]:
            row["generalization_status"] = "confirmed"
        elif (
            row["train_evidence_ready"]
            and row["confirm_support"]["measured_runs"] >= 2
            and row["confirm_support"]["mean_reward"] < 0.0
        ):
            row["generalization_status"] = "overfit_signal"
        elif row["train_evidence_ready"]:
            row["generalization_status"] = "awaiting_confirm"
        else:
            row["generalization_status"] = "gathering_evidence"
        records.append(row)

    learning_alerts = [
        {
            "type": "overfit_signal",
            "memory_key": row["key"],
            "train_mean_reward": row["support"]["mean_reward"],
            "confirm_mean_reward": row["confirm_support"]["mean_reward"],
            "confirm_runs": row["confirm_support"]["measured_runs"],
            "confirm_deep_inspections": row["confirm_support"]["deep_inspections"],
            "recommended_action": (
                "Keep suppressed from live priors; inspect failure shapes "
                "and submit a reproducible learning-failure packet if a "
                "regression test can be defined."
            ),
        }
        for row in records
        if row["generalization_status"] == "overfit_signal"
    ]

    failure_rows = load_failure_events(failure_dir)
    failures = [assessment for _raw, assessment in failure_rows]
    source_payload = {
        "search_runs": search_runs,
        "outcomes": outcomes,
        "failures": [raw for raw, _assessment in failure_rows],
    }
    source_snapshot_sha256 = hashlib.sha256(
        json.dumps(
            source_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    source_times = [
        str(run.get("timestamp") or run.get("date"))
        for run in search_runs
        if run.get("timestamp") or run.get("date")
    ] + [
        str(outcome.get("date"))
        for outcome in outcomes
        if outcome.get("date")
    ]

    return {
        "schema_version": 1,
        "source_through": max(source_times) if source_times else None,
        "source_snapshot_sha256": source_snapshot_sha256,
        "mode": "observe_first_advisory",
        "policy_effect": "none",
        "automatic_expand_retire_enabled": False,
        "policy_gate": {
            "minimum_measured_runs": 5,
            "minimum_deep_inspections": 20,
            "minimum_confirm_runs": 2,
            "minimum_confirm_deep_inspections": 6,
            "minimum_confirm_mean_reward": 0.0,
            "note": (
                "The existing 5-run/20-deep gate must be met on train "
                "episodes, then independently confirmed before a value "
                "prior may steer live search. Learning values never "
                "override stage/STOP/verification gates."
            ),
        },
        "memory": {
            "config": asdict(memory.config),
            "records": records,
        },
        "reward_observations": observations,
        "learning_alerts": learning_alerts,
        "training_environment": {
            "source_snapshot_sha256": (
                training_environment["source_snapshot_sha256"]
            ),
            "split_counts": (
                training_environment["summary"]["split_counts"]
            ),
            "reward_stage_counts": (
                training_environment["summary"][
                    "reward_stage_counts"
                ]
            ),
            "credit_edges": (
                training_environment["summary"]["credit_edges"]
            ),
            "excluded_outcomes": (
                training_environment["summary"][
                    "excluded_outcomes"
                ]
            ),
            "note": (
                "Only train episodes update memory. Confirm and "
                "evaluation-only episodes are held out."
            ),
        },
        "failure_queue": {
            "count": len(failures),
            "queued": sum(
                1
                for item in failures
                if item["decision"] == "QUEUED"
            ),
            "blocked": sum(
                1
                for item in failures
                if item["decision"] == "BLOCKED"
            ),
            "items": failures,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--search-runs",
        default="intelligence/search_runs.jsonl",
    )
    parser.add_argument(
        "--outcomes",
        default="intelligence/outcomes.jsonl",
    )
    parser.add_argument(
        "--failure-dir",
        default="intelligence/learning_failure_spool",
    )
    parser.add_argument(
        "--write",
        help="Write JSON to this path instead of stdout",
    )
    args = parser.parse_args()

    state = compile_state(
        load_jsonl(Path(args.search_runs)),
        load_jsonl(Path(args.outcomes)),
        Path(args.failure_dir),
    )
    rendered = json.dumps(
        state,
        indent=2,
        sort_keys=True,
    ) + "\n"

    if args.write:
        path = Path(args.write)
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_text(
            rendered,
            encoding="utf-8",
        )
    else:
        print(
            rendered,
            end="",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
