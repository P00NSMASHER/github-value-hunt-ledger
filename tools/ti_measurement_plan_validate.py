#!/usr/bin/env python3
"""Validate observational measurement debt against adaptive learning debt."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEL = ROOT / "intelligence"
PLAN = INTEL / "measurement_plan.json"
CURRICULUM = INTEL / "learning_curriculum.json"


def main() -> int:
    if not PLAN.exists():
        raise SystemExit("missing intelligence/measurement_plan.json")
    if not CURRICULUM.exists():
        raise SystemExit("missing intelligence/learning_curriculum.json")

    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    curriculum = json.loads(CURRICULUM.read_text(encoding="utf-8"))

    if plan.get("count_semantics") != "observational_discovery":
        raise SystemExit("measurement plan count semantics drifted")
    if plan.get("learning_authority") != "intelligence/learning_curriculum.json":
        raise SystemExit("measurement plan learning authority drifted")

    learning_rows = {
        row.get("strategy_id"): row
        for row in curriculum.get("rows") or []
        if isinstance(row, dict) and isinstance(row.get("strategy_id"), str)
    }

    plan_rows = plan.get("rows") or []
    if plan.get("active_strategies") != len(plan_rows):
        raise SystemExit("measurement plan active strategy count mismatch")

    seen: set[str] = set()
    for row in plan_rows:
        sid = row.get("strategy_id")
        if not isinstance(sid, str) or not sid.startswith("STRAT:"):
            raise SystemExit("invalid strategy id in measurement plan")
        if sid in seen:
            raise SystemExit(f"duplicate strategy in measurement plan: {sid}")
        seen.add(sid)

        learning = learning_rows.get(sid)
        if learning is None:
            raise SystemExit(
                f"active measurement strategy missing from learning curriculum: {sid}"
            )

        train = learning.get("train") or {}
        confirm = learning.get("confirm") or {}
        expected = {
            "learning_phase": learning.get("phase"),
            "learning_train_runs": train.get("runs"),
            "learning_train_deep_inspections": train.get("deep_inspections"),
            "learning_confirm_runs": confirm.get("runs"),
            "learning_confirm_deep_inspections": confirm.get("deep_inspections"),
            "learning_policy_eligible": learning.get(
                "eligible_for_policy_consideration"
            ),
        }
        for key, value in expected.items():
            if row.get(key) != value:
                raise SystemExit(
                    f"measurement/learning mismatch for {sid}: "
                    f"{key}={row.get(key)!r}, expected {value!r}"
                )

        if row.get("count_semantics") != "observational_discovery":
            raise SystemExit(
                f"row count semantics drifted for {sid}"
            )

    extra = sorted(set(learning_rows) - seen)
    if extra:
        raise SystemExit(
            "learning curriculum contains active strategies absent from "
            "measurement plan: " + ", ".join(extra)
        )

    print(PLAN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
