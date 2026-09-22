from __future__ import annotations

from typing import Any, Mapping, Sequence


_SUPPRESSED = {
    "overfit_signal",
    "confirm_regression_signal",
}


def _support(row: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = row.get(key)
    return dict(value) if isinstance(value, Mapping) else {}


def _allocation(policy: Mapping[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in policy.get("strategy_allocation") or []:
        sid = row.get("strategy_id")
        value = row.get("allocation")
        if isinstance(sid, str) and isinstance(value, (int, float)):
            out[sid] = float(value)
    return out


def build_learning_curriculum(
    learning_state: Mapping[str, Any],
    strategies: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
    *,
    gate_closing_slots: int = 2,
    zero_run_exploration_slots: int = 1,
) -> dict[str, Any]:
    """Rank evidence collection without using learned performance as allocation.

    The curriculum is measurement-only. Q-values and reward means are reported
    for auditability but never enter the priority formula.
    """
    if gate_closing_slots < 0 or zero_run_exploration_slots < 0:
        raise ValueError("slot counts must be nonnegative")

    gate = learning_state.get("policy_gate") or {}
    min_runs = int(gate.get("minimum_measured_runs") or 5)
    min_deep = int(gate.get("minimum_deep_inspections") or 20)
    min_confirm_runs = int(gate.get("minimum_confirm_runs") or 2)
    min_confirm_deep = int(
        gate.get("minimum_confirm_deep_inspections") or 6
    )

    active = {
        row["strategy_id"]: row
        for row in strategies
        if row.get("status") == "active"
        and isinstance(row.get("strategy_id"), str)
    }
    records = {
        row.get("key"): row
        for row in ((learning_state.get("memory") or {}).get("records") or [])
        if row.get("kind") == "STRATEGY"
        and isinstance(row.get("key"), str)
        and row.get("key", "").startswith("STRAT:")
    }
    allocation = _allocation(policy)

    rows: list[dict[str, Any]] = []
    for sid, strategy in sorted(active.items()):
        learned = records.get(sid) or {}
        train = _support(learned, "support")
        confirm = _support(learned, "confirm_support")

        train_runs = int(train.get("measured_runs") or 0)
        train_deep = int(train.get("deep_inspections") or 0)
        confirm_runs = int(confirm.get("measured_runs") or 0)
        confirm_deep = int(confirm.get("deep_inspections") or 0)

        train_runs_needed = max(0, min_runs - train_runs)
        train_deep_needed = max(0, min_deep - train_deep)
        confirm_runs_needed = max(0, min_confirm_runs - confirm_runs)
        confirm_deep_needed = max(0, min_confirm_deep - confirm_deep)

        train_ready = bool(learned.get("train_evidence_ready"))
        confirm_ready = bool(learned.get("confirm_evidence_ready"))
        eligible = bool(learned.get("eligible_for_policy_consideration"))
        generalization = str(
            learned.get("generalization_status") or "gathering_evidence"
        )

        run_progress = min(1.0, train_runs / max(1, min_runs))
        deep_progress = min(1.0, train_deep / max(1, min_deep))
        train_progress = 0.5 * run_progress + 0.5 * deep_progress

        if eligible:
            phase = "ready"
            measurement_priority = 0.0
            selection_reason = "learning_prior_already_confirmed"
        elif generalization in _SUPPRESSED:
            phase = "repair_or_falsify"
            measurement_priority = 0.0
            selection_reason = generalization
        elif train_ready:
            phase = "confirm_measurement"
            confirm_progress = 0.5 * min(
                1.0, confirm_runs / max(1, min_confirm_runs)
            ) + 0.5 * min(
                1.0, confirm_deep / max(1, min_confirm_deep)
            )
            measurement_priority = 90.0 + 10.0 * confirm_progress
            selection_reason = "train_gate_clear_confirm_evidence_missing"
        else:
            phase = "train_measurement"
            measurement_priority = 60.0 + 30.0 * train_progress
            selection_reason = "reduce_train_evidence_deficit"

        rows.append(
            {
                "strategy_id": sid,
                "strategy_name": strategy.get("name"),
                "phase": phase,
                "measurement_priority": round(measurement_priority, 4),
                "selection_reason": selection_reason,
                "policy_allocation": allocation.get(sid, 0.0),
                "train": {
                    "runs": train_runs,
                    "deep_inspections": train_deep,
                    "runs_needed": train_runs_needed,
                    "deep_inspections_needed": train_deep_needed,
                    "ready": train_ready,
                },
                "confirm": {
                    "runs": confirm_runs,
                    "deep_inspections": confirm_deep,
                    "runs_needed": confirm_runs_needed,
                    "deep_inspections_needed": confirm_deep_needed,
                    "ready": confirm_ready,
                },
                "generalization_status": generalization,
                "eligible_for_policy_consideration": eligible,
                "audit_only_q_value": learned.get("q_value"),
                "zero_train_runs": train_runs == 0,
            }
        )

    measurable = [
        row
        for row in rows
        if row["phase"] in {"train_measurement", "confirm_measurement"}
    ]
    nonzero = sorted(
        (row for row in measurable if not row["zero_train_runs"]),
        key=lambda row: (
            -row["measurement_priority"],
            row["train"]["runs_needed"],
            row["train"]["deep_inspections_needed"],
            row["strategy_id"],
        ),
    )
    zero = sorted(
        (row for row in measurable if row["zero_train_runs"]),
        key=lambda row: row["strategy_id"],
    )

    selected: list[dict[str, Any]] = []
    for row in nonzero[:gate_closing_slots]:
        selected.append(row)
    for row in zero[:zero_run_exploration_slots]:
        if row not in selected:
            selected.append(row)

    capacity = gate_closing_slots + zero_run_exploration_slots
    if len(selected) < capacity:
        for row in sorted(
            measurable,
            key=lambda item: (
                -item["measurement_priority"],
                item["strategy_id"],
            ),
        ):
            if row in selected:
                continue
            selected.append(row)
            if len(selected) >= capacity:
                break

    recommendations = []
    for rank, row in enumerate(selected, 1):
        recommendations.append(
            {
                "rank": rank,
                "strategy_id": row["strategy_id"],
                "phase": row["phase"],
                "measurement_priority": row["measurement_priority"],
                "selection_reason": row["selection_reason"],
                "train": row["train"],
                "confirm": row["confirm"],
                "blind_partition_rule": (
                    "Do not calculate, expose, select, release, retry, or "
                    "otherwise alter execution based on train/confirm "
                    "membership. Generated assignment identity fixes the "
                    "partition before execution and retries keep that identity."
                ),
            }
        )

    return {
        "schema_version": 1,
        "mode": "measurement_only",
        "policy_effect": "none",
        "uses_q_value_for_selection": False,
        "partition_selection_allowed": False,
        "thresholds": {
            "minimum_train_runs": min_runs,
            "minimum_train_deep_inspections": min_deep,
            "minimum_confirm_runs": min_confirm_runs,
            "minimum_confirm_deep_inspections": min_confirm_deep,
        },
        "reservation": {
            "gate_closing_slots": gate_closing_slots,
            "zero_run_exploration_slots": zero_run_exploration_slots,
        },
        "recommended_measurements": recommendations,
        "rows": rows,
    }


def validate_learning_curriculum(
    curriculum: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if curriculum.get("schema_version") != 1:
        errors.append("unexpected_schema_version")
    if curriculum.get("mode") != "measurement_only":
        errors.append("mode_must_be_measurement_only")
    if curriculum.get("policy_effect") != "none":
        errors.append("policy_effect_must_be_none")
    if curriculum.get("uses_q_value_for_selection") is not False:
        errors.append("q_value_selection_must_be_false")
    if curriculum.get("partition_selection_allowed") is not False:
        errors.append("partition_selection_must_be_false")

    rows = curriculum.get("rows") or []
    by_id: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        sid = row.get("strategy_id")
        if not isinstance(sid, str) or not sid.startswith("STRAT:"):
            errors.append("invalid_strategy_id")
            continue
        if sid in by_id:
            errors.append(f"duplicate_strategy:{sid}")
        by_id[sid] = row
        if row.get("phase") not in {
            "train_measurement",
            "confirm_measurement",
            "repair_or_falsify",
            "ready",
        }:
            errors.append(f"invalid_phase:{sid}")
        priority = row.get("measurement_priority")
        if (
            not isinstance(priority, (int, float))
            or not 0.0 <= float(priority) <= 100.0
        ):
            errors.append(f"invalid_priority:{sid}")

    seen: set[str] = set()
    for rec in curriculum.get("recommended_measurements") or []:
        sid = rec.get("strategy_id")
        if sid not in by_id:
            errors.append(f"unknown_recommendation:{sid}")
            continue
        if sid in seen:
            errors.append(f"duplicate_recommendation:{sid}")
        seen.add(sid)
        row = by_id[sid]
        if row.get("phase") not in {
            "train_measurement",
            "confirm_measurement",
        }:
            errors.append(f"nonmeasurement_recommendation:{sid}")
        if not rec.get("blind_partition_rule"):
            errors.append(f"missing_blind_partition_rule:{sid}")

    return errors
