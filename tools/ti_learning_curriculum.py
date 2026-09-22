#!/usr/bin/env python3
"""Build the measurement-only curriculum for adaptive hunter learning."""

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
    rows = []
    for line_no, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(
                f"{path}:{line_no}: expected JSON object"
            )
        rows.append(value)
    return rows


def main() -> int:
    learning = load_json(
        INTEL / "LEARNING_STATE.json", {}
    )
    strategies = load_jsonl(
        INTEL / "search_strategies.jsonl"
    )
    policy = load_json(
        INTEL / "search_policy.json", {}
    )
    split_status = load_json(
        INTEL / "TRAINING_SPLIT_STATUS.json", {}
    )

    curriculum = build_learning_curriculum(
        learning,
        strategies,
        policy,
        split_status=split_status,
    )
    errors = validate_learning_curriculum(
        curriculum
    )
    if errors:
        raise SystemExit(
            "learning curriculum invalid: "
            + "; ".join(errors)
        )

    json_path = INTEL / "learning_curriculum.json"
    json_path.write_text(
        json.dumps(
            curriculum,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    recs = curriculum[
        "recommended_measurements"
    ]
    rows = curriculum["rows"]

    lines = [
        "# HUNTER LEARNING CURRICULUM",
        "",
        (
            "Evidence-collection plan for the adaptive hunter layer. "
            "This is **measurement-only**: learned Q-values, reward "
            "means and current policy allocations do not select "
            "strategies, and this file does not change live policy."
        ),
        "",
        "## Blind confirmation readiness",
        "",
        (
            "- Operational: **"
            + (
                "yes"
                if curriculum["blind_confirmation"]["operational"]
                else "no"
            )
            + "**"
        ),
        (
            "- Key commitment active: **"
            + str(
                curriculum["blind_confirmation"][
                    "key_commitment_active"
                ]
            ).lower()
            + "**"
        ),
        (
            "- Split secret available to CI: **"
            + str(
                curriculum["blind_confirmation"][
                    "secret_available"
                ]
            ).lower()
            + "**"
        ),
        (
            "- Pending trusted generated claims: **"
            + str(
                curriculum["blind_confirmation"][
                    "pending_claim_count"
                ]
            )
            + "**"
        ),
        (
            "- Confirmation blocker: **"
            + str(
                curriculum["blind_confirmation"]["blocker"]
                or "none"
            )
            + "**"
        ),
        "",
        "## Guardrails",
        "",
        (
            "- Measurement work must use the normal generated "
            "assignment/claim path."
        ),
        (
            "- Never calculate, expose, choose, release, or retry "
            "work based on train/confirm membership."
        ),
        (
            "- Manual, legacy, or unallocated work cannot manufacture "
            "confirmation evidence."
        ),
        (
            "- Suppressed overfit/regression strategies go to repair "
            "or falsification, not additional exploitation."
        ),
        (
            "- Two slots target the closest evidence gates and one "
            "slot preserves zero-run exploration."
        ),
        "",
        "## Recommended measurements",
        "",
        (
            "| Rank | Strategy | Phase | Train evidence | "
            "Confirm evidence | Reason |"
        ),
        "|---:|---|---|---|---|---|",
    ]

    for rec in recs:
        train = rec["train"]
        confirm = rec["confirm"]
        lines.append(
            f"| {rec['rank']} | {rec['strategy_id']} | "
            f"{rec['phase']} | "
            f"{train['runs']} runs / "
            f"{train['deep_inspections']} deep "
            f"(need {train['runs_needed']} / "
            f"{train['deep_inspections_needed']}) | "
            f"{confirm['runs']} runs / "
            f"{confirm['deep_inspections']} deep "
            f"(need {confirm['runs_needed']} / "
            f"{confirm['deep_inspections_needed']}) | "
            f"{rec['selection_reason']} |"
        )

    if not recs:
        lines.append(
            "| — | — | — | — | — | "
            "No measurement debt eligible |"
        )

    lines += [
        "",
        "## All active strategies",
        "",
        (
            "| Strategy | Phase | Train runs/deep | "
            "Confirm runs/deep | Priority |"
        ),
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
            f"| {row['strategy_id']} | "
            f"{row['phase']} | "
            f"{row['train']['runs']}/"
            f"{row['train']['deep_inspections']} | "
            f"{row['confirm']['runs']}/"
            f"{row['confirm']['deep_inspections']} | "
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
                "reward_selection": curriculum[
                    "uses_reward_for_selection"
                ],
                "policy_effect": curriculum[
                    "policy_effect"
                ],
                "blind_confirmation_operational": (
                    curriculum["blind_confirmation"][
                        "operational"
                    ]
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
