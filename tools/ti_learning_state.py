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
    observed_search_reward,
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


def support_index(
    search_runs: Iterable[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for run in search_runs:
        if observed_search_reward(run) is None:
            continue

        deep = run.get("deep_inspected")
        deep_value = deep if isinstance(deep, int) and deep >= 0 else 0
        keys: list[str] = []

        strategy = run.get("strategy_id")
        if isinstance(strategy, str) and strategy.startswith("STRAT:"):
            keys.append(strategy)

        query_family = run.get("query_family_id")
        if (
            isinstance(query_family, str)
            and query_family.startswith("QF:")
        ):
            keys.append(query_family)

        for key in keys:
            bucket = out.setdefault(
                key,
                {
                    "measured_runs": 0,
                    "deep_inspections": 0,
                },
            )
            bucket["measured_runs"] += 1
            bucket["deep_inspections"] += deep_value

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
    train_run_ids = {
        episode["run_id"]
        for episode in training_environment["episodes"]
        if episode.get("split") == "train"
    }
    support = support_index(
        run
        for run in search_runs
        if run.get("search_run_id") in train_run_ids
    )

    records: list[dict[str, Any]] = []
    for record in memory.records():
        row = record.to_dict()
        row["support"] = support.get(
            record.key,
            {
                "measured_runs": 0,
                "deep_inspections": 0,
            },
        )
        row["eligible_for_policy_consideration"] = (
            row["support"]["measured_runs"] >= 5
            and row["support"]["deep_inspections"] >= 20
        )
        records.append(row)

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
            "note": (
                "Matches existing repository policy; learning values "
                "never override stage/STOP/verification gates."
            ),
        },
        "memory": {
            "config": asdict(memory.config),
            "records": records,
        },
        "reward_observations": observations,
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
