#!/usr/bin/env python3
"""Build an evidence-only measurement curriculum for hunter learning."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.learning_curriculum import (
    build_learning_curriculum,
    validate_learning_curriculum,
)

INTEL = ROOT / "intelligence"


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    if not path.exists():
        return []
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            out.append(json.loads(raw))
    return out


def main() -> int:
    learning = load_json(INTEL / "LEARNING_STATE.json", {})
    strategies = load_jsonl(INTEL / "search_strategies.jsonl")
    policy = load_json(INTEL / "search_policy.json", {})

    curriculum = build_learning_curriculum(
        learning,
        strategies,
        policy,
    )
    errors = validate_learning_curriculum(curriculum)
    if errors:
        raise SystemExit(
            "learning curriculum invalid: " + "; ".join(errors)
        )

    (INTEL / "learning_curriculum.json").write_text(
        json.dumps(curriculum, indent=2) + "\n",
        encoding="utf-8",
    )

    rows = curriculum["rows"]
    recs = curriculum["recommended_measurements"]
    lines = [
        "# HUNTER LEARNING CURRICULUM",
        "",
        "Evidence-collection plan for the adaptive hunter layer. "
        "This is **measurement-only**: learned Q-values do not select "
        "strategies, and this file does not change live policy by itself.",
        "",
        "## Guardrails",
        "",
        "- Generated assignment identity fixes train/confirm membership before execution.",
        "- Never calculate, expose, select, release, or retry work based on its train/confirm partition.",
        "- Manual/unallocated/legacy work remains train-only and cannot manufacture confirm evidence.",
        "- Overfit or confirm-regression signals are repair/falsification targets, not candidates for more allocation.",
        "- Two measurement recommendations target the closest evidence gates; one recommendation preserves zero-run exploration.",
        "",
        "## Recommended measurements",
        "",
        "| Rank | Strategy | Phase | Train evidence | Confirm evidence | Reason |",
        "|---:|---|---|---|---|---|",
    ]
    for rec in recs:
        train = rec["train"]
        confirm = rec["confirm"]
        lines.append(
            f"| {rec['rank']} | {rec['strategy_id']} | {rec['phase']} | "
            f"{train['runs']} runs / {train['deep_inspections']} deep "
            f"(need {train['runs_needed']} / {train['deep_inspections_needed']}) | "
            f"{confirm['runs']} runs / {confirm['deep_inspections']} deep "
            f"(need {confirm['runs_needed']} / {confirm['deep_inspections_needed']}) | "
            f"{rec['selection_reason']} |"
        )
    if not recs:
        lines.append("| — | — | — | — | — | No measurement debt eligible |")

    lines += [
        "",
        "## All active strategies",
        "",
        "| Strategy | Phase | Train runs/deep | Confirm runs/deep | Measurement priority |",
        "|---|---|---:|---:|---:|",
    ]
    for row in sorted(
        rows,
        key=lambda item: (
            -item["measurement_priority"],
            item["strategy_id"],
        ),
    ):
        lines.append(
            f"| {row['strategy_id']} | {row['phase']} | "
            f"{row['train']['runs']}/{row['train']['deep_inspections']} | "
            f"{row['confirm']['runs']}/{row['confirm']['deep_inspections']} | "
            f"{row['measurement_priority']:.1f} |"
        )

    (INTEL / "LEARNING_CURRICULUM.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "recommended": len(recs),
                "strategies": len(rows),
                "q_value_selection": curriculum[
                    "uses_q_value_for_selection"
                ],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
