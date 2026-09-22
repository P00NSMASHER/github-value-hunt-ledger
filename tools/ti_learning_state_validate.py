#!/usr/bin/env python3
"""Fail-closed validation for the generated hunter learning state."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "intelligence" / "LEARNING_STATE.json"


def main() -> int:
    if not PATH.exists():
        raise SystemExit("missing intelligence/LEARNING_STATE.json")

    data = json.loads(PATH.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise SystemExit("unexpected learning-state schema")
    if data.get("policy_effect") != "none":
        raise SystemExit("learning state must remain advisory")
    if data.get("automatic_expand_retire_enabled") is not False:
        raise SystemExit("automatic strategy retirement/expansion must remain disabled")

    gate = data.get("policy_gate") or {}
    min_runs = gate.get("minimum_measured_runs")
    min_deep = gate.get("minimum_deep_inspections")
    min_confirm_runs = gate.get("minimum_confirm_runs")
    min_confirm_deep = gate.get("minimum_confirm_deep_inspections")
    min_confirm_mean = gate.get("minimum_confirm_mean_reward")
    if min_runs != 5 or min_deep != 20:
        raise SystemExit("learning policy gates drifted from repository policy")
    if (
        min_confirm_runs != 2
        or min_confirm_deep != 6
        or min_confirm_mean != 0.0
    ):
        raise SystemExit("confirm evidence gates drifted")

    records = ((data.get("memory") or {}).get("records") or [])
    for row in records:
        q_value = row.get("q_value")
        visits = row.get("visits")
        support = row.get("support") or {}
        if not isinstance(q_value, (int, float)) or not -1.0 <= q_value <= 1.0:
            raise SystemExit(f"invalid q_value for {row.get('key')}")
        if not isinstance(visits, int) or visits < 0:
            raise SystemExit(f"invalid visits for {row.get('key')}")
        measured_runs = support.get("measured_runs", 0)
        deep_inspections = support.get("deep_inspections", 0)
        confirm = row.get("confirm_support") or {}
        confirm_runs = confirm.get("measured_runs", 0)
        confirm_deep = confirm.get("deep_inspections", 0)
        confirm_mean = confirm.get("mean_reward", 0.0)
        if (
            not isinstance(measured_runs, int)
            or measured_runs < 0
            or not isinstance(deep_inspections, int)
            or deep_inspections < 0
            or not isinstance(confirm_runs, int)
            or confirm_runs < 0
            or not isinstance(confirm_deep, int)
            or confirm_deep < 0
            or not isinstance(confirm_mean, (int, float))
        ):
            raise SystemExit(f"invalid support counts for {row.get('key')}")
        expected_train = measured_runs >= min_runs and deep_inspections >= min_deep
        expected_confirm = (
            confirm_runs >= min_confirm_runs
            and confirm_deep >= min_confirm_deep
            and confirm_mean >= min_confirm_mean
        )
        if row.get("train_evidence_ready") is not expected_train:
            raise SystemExit(f"train evidence mismatch for {row.get('key')}")
        if row.get("confirm_evidence_ready") is not expected_confirm:
            raise SystemExit(f"confirm evidence mismatch for {row.get('key')}")
        if (
            row.get("eligible_for_policy_consideration")
            is not (expected_train and expected_confirm)
        ):
            raise SystemExit(f"policy eligibility mismatch for {row.get('key')}")

    failure_queue = data.get("failure_queue") or {}
    items = failure_queue.get("items") or []
    if failure_queue.get("count") != len(items):
        raise SystemExit("failure queue count mismatch")
    for item in items:
        if item.get("decision") not in {"QUEUED", "BLOCKED"}:
            raise SystemExit("invalid failure decision")
        signature = item.get("signature")
        if not isinstance(signature, str) or len(signature) != 64:
            raise SystemExit("invalid failure signature")

    print(PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
