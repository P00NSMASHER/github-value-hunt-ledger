#!/usr/bin/env python3
"""Validate benchmark measurement semantics against adaptive learning state."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEL = ROOT / "intelligence"
CAMPAIGN = INTEL / "measurement_campaign.json"
CURRICULUM = INTEL / "learning_curriculum.json"


def main() -> int:
    if not CAMPAIGN.exists():
        raise SystemExit("missing intelligence/measurement_campaign.json")
    if not CURRICULUM.exists():
        raise SystemExit("missing intelligence/learning_curriculum.json")

    campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
    curriculum = json.loads(CURRICULUM.read_text(encoding="utf-8"))

    if campaign.get("schema_version") != 2:
        raise SystemExit("unexpected measurement campaign schema")
    if (
        campaign.get("measurement_semantics")
        != "matched_benchmark_observational"
    ):
        raise SystemExit("measurement campaign semantics drifted")
    if (
        campaign.get("adaptive_learning_authority")
        != "intelligence/learning_curriculum.json"
    ):
        raise SystemExit("adaptive learning authority drifted")
    if campaign.get("adaptive_partition_effect") != "none":
        raise SystemExit("benchmark campaign cannot alter adaptive partition")
    if campaign.get("benchmark_records_are") != "evaluation_only":
        raise SystemExit("benchmark records must remain evaluation_only")

    learning_rows = {
        row.get("strategy_id"): row
        for row in curriculum.get("rows") or []
        if isinstance(row, dict) and isinstance(row.get("strategy_id"), str)
    }

    for rec in campaign.get("recommended_strategy_conditions") or []:
        sid = rec.get("strategy_id")
        if sid not in learning_rows:
            raise SystemExit(
                f"campaign strategy absent from learning curriculum: {sid}"
            )
        if rec.get("adaptive_partition_effect") != "none":
            raise SystemExit(
                f"benchmark recommendation changes adaptive partition: {sid}"
            )

        learning = learning_rows[sid]
        train = learning.get("train") or {}
        confirm = learning.get("confirm") or {}
        expected = {
            "adaptive_learning_phase": learning.get("phase"),
            "adaptive_train_runs": train.get("runs"),
            "adaptive_train_deep_inspections": train.get("deep_inspections"),
            "adaptive_train_runs_needed": train.get("runs_needed"),
            "adaptive_train_deep_inspections_needed": train.get(
                "deep_inspections_needed"
            ),
            "adaptive_confirm_runs": confirm.get("runs"),
            "adaptive_confirm_deep_inspections": confirm.get(
                "deep_inspections"
            ),
            "adaptive_confirm_runs_needed": confirm.get("runs_needed"),
            "adaptive_confirm_deep_inspections_needed": confirm.get(
                "deep_inspections_needed"
            ),
            "adaptive_policy_eligible": learning.get(
                "eligible_for_policy_consideration"
            ),
        }
        for key, expected_value in expected.items():
            if rec.get(key) != expected_value:
                raise SystemExit(
                    f"campaign/learning mismatch for {sid}: "
                    f"{key}={rec.get(key)!r}, expected {expected_value!r}"
                )

        # Compatibility aliases must stay observational, never adaptive.
        if rec.get("runs_needed") != rec.get("observational_runs_needed"):
            raise SystemExit(f"runs_needed semantic drift for {sid}")
        if rec.get("inspections_needed") != rec.get(
            "observational_inspections_needed"
        ):
            raise SystemExit(f"inspections_needed semantic drift for {sid}")

    print(CAMPAIGN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
