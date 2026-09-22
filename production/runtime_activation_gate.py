from __future__ import annotations

from typing import Any, Mapping


PAUSED = "paused"
MEASUREMENT_CANARY = "measurement_canary"
CANARY_SCOPE = "learning_measurement_canary"
ALLOWED_WORK_KIND = "learning_measurement"


def evaluate_runtime_activation_gate(
    policy: Mapping[str, Any],
    readiness: Mapping[str, Any],
    packets: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if policy.get("schema_version") != 1:
        errors.append("unexpected_policy_schema")
    if policy.get("explicit_user_approval_required") is not True:
        errors.append("explicit_user_approval_required")

    mode = policy.get("mode")
    if mode not in {PAUSED, MEASUREMENT_CANARY}:
        errors.append("invalid_runtime_mode")

    rows = [
        row
        for row in packets.get("packets") or []
        if isinstance(row, Mapping)
    ]
    current_seed_ids = sorted(
        {
            str((row.get("seed") or {}).get("seed_id"))
            for row in rows
            if isinstance((row.get("seed") or {}).get("seed_id"), str)
            and (row.get("seed") or {}).get("seed_id")
        }
    )

    if errors:
        return {
            "enabled": False,
            "mode": mode,
            "reason": "invalid_runtime_policy",
            "errors": errors,
            "approval_id": policy.get("approval_id"),
            "maximum_current_activations": 0,
            "allowed_work_kinds": [],
            "allowed_seed_ids": [],
        }

    if mode == PAUSED:
        if int(policy.get("maximum_current_activations") or 0) != 0:
            errors.append("paused_mode_requires_zero_capacity")
        for field in ("approval_scope", "approval_id", "approved_at"):
            if policy.get(field) not in {None, ""}:
                errors.append(f"paused_mode_forbids_{field}")
        return {
            "enabled": False,
            "mode": mode,
            "reason": (
                "invalid_runtime_policy"
                if errors
                else "runtime_policy_paused"
            ),
            "errors": errors,
            "approval_id": None,
            "maximum_current_activations": 0,
            "allowed_work_kinds": [],
            "allowed_seed_ids": [],
        }

    if policy.get("approval_scope") != CANARY_SCOPE:
        errors.append("measurement_canary_scope_required")
    approval_id = policy.get("approval_id")
    if not isinstance(approval_id, str) or not approval_id.startswith(
        "APPROVAL:"
    ):
        errors.append("measurement_canary_approval_id_required")
    approved_at = policy.get("approved_at")
    if not isinstance(approved_at, str) or not approved_at:
        errors.append("measurement_canary_approved_at_required")

    allowed_kinds = policy.get("allowed_work_kinds")
    if allowed_kinds != [ALLOWED_WORK_KIND]:
        errors.append("measurement_canary_work_kind_must_be_exact")

    maximum = policy.get("maximum_current_activations")
    if type(maximum) is not int or not (1 <= maximum <= 3):
        errors.append("measurement_canary_capacity_must_be_1_to_3")
        maximum = 0

    machine_ready = (
        readiness.get("state") == "AWAITING_EXPLICIT_USER_APPROVAL"
        and not (readiness.get("blockers") or [])
        and all(
            value is True
            for value in (readiness.get("gates") or {}).values()
        )
    )
    if not machine_ready:
        errors.append("machine_restart_readiness_blocked")
    if not current_seed_ids:
        errors.append("no_current_precommitted_measurement_seeds")

    return {
        "enabled": not errors,
        "mode": mode,
        "reason": (
            "measurement_canary_approved"
            if not errors
            else "runtime_gate_blocked"
        ),
        "errors": errors,
        "approval_id": approval_id,
        "maximum_current_activations": (
            min(maximum, len(current_seed_ids))
            if not errors
            else 0
        ),
        "allowed_work_kinds": (
            [ALLOWED_WORK_KIND] if not errors else []
        ),
        "allowed_seed_ids": (
            current_seed_ids if not errors else []
        ),
    }
