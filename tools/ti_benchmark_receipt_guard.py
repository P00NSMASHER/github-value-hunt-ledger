#!/usr/bin/env python3
"""Fail closed on benchmark scores without frozen source result records.

Checks structure/provenance only. Never reads benchmark/BENCHMARK_GOLD.md or
compares the substance of CONTROL/EXPERIMENT answers.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

SCORE_ROW = re.compile(r"^\|\s*(\d{2})\s*\|\s*(CONTROL|EXPERIMENT)\s*\|", re.M | re.I)
RESULT_ROW = re.compile(r"^(?:TASK:\s*|#{2,3}\s+TASK\s+)(\d{2})\b", re.M | re.I)
MATCHED = re.compile(r"Matched tasks scored:\s*\*\*(\d+)\*\*", re.I)


class BenchmarkReceiptError(ValueError):
    pass


def pair_tasks(pair: int) -> set[str]:
    if pair < 1 or pair > 7:
        raise BenchmarkReceiptError("Unknown frozen benchmark pair")
    first = 1 if pair == 1 else 9 + (pair - 2) * 7
    last = 8 if pair == 1 else first + 6
    return {f"{task:02d}" for task in range(first, last + 1)}


def validate_benchmark_receipts(root: Path, scoreboard: str, expected_tasks: int = 50) -> dict:
    scored = [(task, arm.upper()) for task, arm in SCORE_ROW.findall(scoreboard)]
    if len(scored) != len(set(scored)):
        raise BenchmarkReceiptError("Duplicate scored benchmark task/condition")
    if any(not 1 <= int(task) <= expected_tasks for task, _ in scored):
        raise BenchmarkReceiptError("Scored task outside frozen benchmark")
    declared_match = MATCHED.search(scoreboard)
    if not declared_match:
        raise BenchmarkReceiptError("Scoreboard matched count is absent")
    declared = int(declared_match.group(1))
    by_task = {}
    for task, arm in scored:
        by_task.setdefault(task, set()).add(arm)
    actual_matched = sum(arms == {"CONTROL", "EXPERIMENT"} for arms in by_task.values())
    if actual_matched != declared:
        raise BenchmarkReceiptError(
            f"Scoreboard matched count {declared} conflicts with {actual_matched} scored task pairs"
        )
    raw = set()
    for pair in range(1, 8):
        expected = pair_tasks(pair)
        for arm in ("CONTROL", "EXPERIMENT"):
            path = root / "benchmark" / "results" / f"pair{pair}-{arm.lower()}.md"
            if not path.is_file():
                raise BenchmarkReceiptError(f"Missing frozen results file {path.name}")
            content = path.read_text(encoding="utf-8")
            task_ids = RESULT_ROW.findall(content)
            if any(task not in expected for task in task_ids):
                raise BenchmarkReceiptError(f"Result contains wrong-pair task in {path.name}")
            raw.update((task, arm) for task in task_ids)
    unsupported = sorted(set(scored) - raw)
    if unsupported:
        raise BenchmarkReceiptError(
            "Scoreboard contains scored conditions without underlying frozen result records: " +
            ", ".join(task + "/" + arm for task, arm in unsupported)
        )
    return {
        "frozen_task_count": expected_tasks,
        "scored_arm_records": len(scored),
        "matched_scored_tasks": actual_matched,
        "raw_result_arm_records": len(raw),
        "unscored_raw_result_arms": len(raw - set(scored)),
        "raw_records_support_all_scored_arms": True,
        "activation_authority": "NONE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    options = parser.parse_args()
    root = Path(options.root)
    text = (root / "benchmark" / "SCOREBOARD.md").read_text(encoding="utf-8")
    result = validate_benchmark_receipts(root, text)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
