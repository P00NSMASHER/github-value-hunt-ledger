from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence


PAUSED = "paused"
MEASUREMENT_CANARY = "measurement_canary"
CANARY_SCOPE = "learning_measurement_canary"
ALLOWED_WORK_KIND = "learning_measurement"
ACTIVE_CLAIM_STATES = {"CLAIMED", "RUNNING"}


def _blocked(
    *,
    mode: Any,
    reason: str,
    errors: Sequence[str],
    approval_id: Any = None,
) -> dict[str, Any]:
    return {
        "enabled": False,
        "mode": mode,
        "reason": reason,
        "errors": list(errors),
        "approval_id": approval_id,
        "maximum_current_activations": 0,
        "maximum_total_claims": 0,
        "claims_consumed": 0,
        "remaining_claim_budget": 0,
        "active_claims": 0,
        "allowed_work_kinds": [],
        "allowed_seed_ids": [],
        "approved_packet_ids": [],
        "approved_seed_ids": [],
        "claimed_seed_ids": [],
    }


def evaluate_runtime_activation_gate(
    policy: Mapping[str, Any],
    readiness: Mapping[str, Any],
    packets: Mapping[str, Any],
    claims: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    errors: list[str] = []
    if policy.get("schema_version") != 1:
        errors.append("unexpected_policy_schema")
    if policy.get("explicit_user_approval_required") is not True:
        errors.append("explicit_user_approval_required")

    mode = policy.get("mode")
    if mode not in {PAUSED, MEASUREMENT_CANARY}:
        errors.append("invalid_runtime_mode")

    packet_rows = [
        row
        for row in packets.get("packets") or []
        if isinstance(row, Mapping)
    ]
    packet_to_seed = {}
    for row in packet_rows:
        packet_id = row.get("packet_id")
        seed_id = (row.get("seed") or {}).get("seed_id")
        if isinstance(packet_id, str) and isinstance(seed_id, str):
            packet_to_seed[packet_id] = seed_id

    if errors:
        return _blocked(
            mode=mode,
            reason="invalid_runtime_policy",
            errors=errors,
            approval_id=policy.get("approval_id"),
        )

    if mode == PAUSED:
        if int(policy.get("maximum_current_activations") or 0) != 0:
            errors.append("paused_mode_requires_zero_current_capacity")
        if int(policy.get("maximum_total_claims") or 0) != 0:
            errors.append("paused_mode_requires_zero_total_claim_budget")
        if policy.get("approved_packet_ids") not in {None}:
            if list(policy.get("approved_packet_ids") or []):
                errors.append("paused_mode_forbids_approved_packet_ids")
        if policy.get("approved_seed_ids") not in {None}:
            if list(policy.get("approved_seed_ids") or []):
                errors.append("paused_mode_forbids_approved_seed_ids")
        for field in ("approval_scope", "approval_id", "approved_at"):
            if policy.get(field) not in {None, ""}:
                errors.append(f"paused_mode_forbids_{field}")
        return _blocked(
            mode=mode,
            reason=(
                "invalid_runtime_policy"
                if errors
                else "runtime_policy_paused"
            ),
            errors=errors,
        )

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

    maximum_current = policy.get("maximum_current_activations")
    if type(maximum_current) is not int or not (1 <= maximum_current <= 3):
        errors.append("measurement_canary_capacity_must_be_1_to_3")
        maximum_current = 0

    maximum_total = policy.get("maximum_total_claims")
    if type(maximum_total) is not int or not (1 <= maximum_total <= 3):
        errors.append("measurement_canary_total_claims_must_be_1_to_3")
        maximum_total = 0
    if maximum_current and maximum_total and maximum_current > maximum_total:
        errors.append("current_activation_capacity_exceeds_total_claim_budget")

    approved_packet_ids = policy.get("approved_packet_ids")
    approved_seed_ids = policy.get("approved_seed_ids")
    if not isinstance(approved_packet_ids, list) or not approved_packet_ids:
        errors.append("approved_packet_ids_required")
        approved_packet_ids = []
    if not isinstance(approved_seed_ids, list) or not approved_seed_ids:
        errors.append("approved_seed_ids_required")
        approved_seed_ids = []
    if len(approved_packet_ids) != len(set(approved_packet_ids)):
        errors.append("duplicate_approved_packet_id")
    if len(approved_seed_ids) != len(set(approved_seed_ids)):
        errors.append("duplicate_approved_seed_id")
    if len(approved_packet_ids) != len(approved_seed_ids):
        errors.append("approved_packet_seed_count_mismatch")
    if maximum_total and len(approved_packet_ids) != maximum_total:
        errors.append("approved_packet_count_must_equal_total_claim_budget")

    resolved_seed_ids: list[str] = []
    for packet_id in approved_packet_ids:
        seed_id = packet_to_seed.get(packet_id)
        if not seed_id:
            errors.append(f"approved_packet_not_current:{packet_id}")
            continue
        resolved_seed_ids.append(seed_id)
    if sorted(resolved_seed_ids) != sorted(approved_seed_ids):
        errors.append("approved_packet_seed_snapshot_mismatch")

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

    approval_claims = [
        row
        for row in claims
        if row.get("runtime_approval_id") == approval_id
    ]
    for row in approval_claims:
        if row.get("routing_mode") != "generated":
            errors.append("approval_claim_must_be_generated")
        if row.get("assignment_work_kind") != ALLOWED_WORK_KIND:
            errors.append("approval_claim_work_kind_drift")
        if row.get("assignment_source_id") not in set(approved_seed_ids):
            errors.append("approval_claim_seed_drift")

    claimed_seed_ids = [
        str(row.get("assignment_source_id"))
        for row in approval_claims
        if isinstance(row.get("assignment_source_id"), str)
    ]
    counts = Counter(claimed_seed_ids)
    if any(count > 1 for count in counts.values()):
        errors.append("approved_seed_claimed_more_than_once")
    if maximum_total and len(approval_claims) > maximum_total:
        errors.append("approval_total_claim_budget_exceeded")

    if errors:
        return _blocked(
            mode=mode,
            reason="runtime_gate_blocked",
            errors=sorted(set(errors)),
            approval_id=approval_id,
        )

    consumed = len(approval_claims)
    remaining = maximum_total - consumed
    active_claims = sum(
        1
        for row in approval_claims
        if row.get("status") in ACTIVE_CLAIM_STATES
    )
    unclaimed_seed_ids = [
        seed_id
        for seed_id in approved_seed_ids
        if seed_id not in counts
    ]

    if remaining <= 0 or not unclaimed_seed_ids:
        return {
            **_blocked(
                mode=mode,
                reason="canary_claim_budget_exhausted",
                errors=[],
                approval_id=approval_id,
            ),
            "maximum_total_claims": maximum_total,
            "claims_consumed": consumed,
            "remaining_claim_budget": 0,
            "active_claims": active_claims,
            "approved_packet_ids": list(approved_packet_ids),
            "approved_seed_ids": list(approved_seed_ids),
            "claimed_seed_ids": sorted(counts),
        }

    available_concurrency = max(0, maximum_current - active_claims)
    current_capacity = min(
        available_concurrency,
        remaining,
        len(unclaimed_seed_ids),
    )

    return {
        "enabled": True,
        "mode": mode,
        "reason": (
            "measurement_canary_approved"
            if current_capacity > 0
            else "canary_concurrency_capacity_held"
        ),
        "errors": [],
        "approval_id": approval_id,
        "maximum_current_activations": current_capacity,
        "maximum_total_claims": maximum_total,
        "claims_consumed": consumed,
        "remaining_claim_budget": remaining,
        "active_claims": active_claims,
        "allowed_work_kinds": [ALLOWED_WORK_KIND],
        "allowed_seed_ids": unclaimed_seed_ids,
        "approved_packet_ids": list(approved_packet_ids),
        "approved_seed_ids": list(approved_seed_ids),
        "claimed_seed_ids": sorted(counts),
    }
