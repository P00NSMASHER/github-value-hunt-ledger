from __future__ import annotations

import copy
from collections import Counter
from typing import Any, Mapping


BOOTSTRAP_MODE = "learning_bootstrap_second_measurement_slot"
BOOTSTRAP_REASON = "blind_learning_bootstrap_no_confirmed_strategy_priors"
DONOR_PREFERENCE = ("adjacency", "coverage", "experiment")


def _role_counts(policy: Mapping[str, Any]) -> dict[str, int]:
    counts = Counter(
        str(slot.get("role") or "")
        for slot in policy.get("slots") or []
        if slot.get("role")
    )
    return dict(counts)


def _confirmed_strategy_priors(
    learning_state: Mapping[str, Any],
) -> int:
    return sum(
        1
        for row in (
            (learning_state.get("memory") or {}).get("records") or []
        )
        if row.get("kind") == "STRATEGY"
        and row.get("eligible_for_policy_consideration") is True
    )


def _measurement_recommendation_count(
    curriculum: Mapping[str, Any],
) -> int:
    return sum(
        1
        for row in curriculum.get("recommended_measurements") or []
        if isinstance(row, Mapping)
        and row.get("phase")
        in {"train_measurement", "confirm_measurement"}
    )


def blind_confirmation_operational(
    curriculum: Mapping[str, Any],
    split_status: Mapping[str, Any],
) -> bool:
    curriculum_blind = curriculum.get("blind_confirmation") or {}
    return (
        curriculum_blind.get("operational") is True
        and split_status.get("key_commitment_active") is True
        and split_status.get("secret_available") is True
    )


def apply_learning_bootstrap(
    base_policy: Mapping[str, Any],
    learning_state: Mapping[str, Any],
    curriculum: Mapping[str, Any],
    split_status: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Temporarily add one adaptive-learning measurement slot.

    The shift is deliberately narrow and reversible. It is allowed only after
    blind confirmation is operational, before any strategy-level prior has
    cleared independent confirmation, and only when at least two current
    curriculum measurements remain.

    The function never changes total fleet capacity and never steals the final
    slot from any donor role. It prefers adjacency because the baseline already
    preserves a second-order exploration slot plus a separate wildcard slot.
    """
    effective = copy.deepcopy(base_policy)
    slots = effective.get("slots") or []
    if not isinstance(slots, list) or not slots:
        return effective, None

    if not blind_confirmation_operational(curriculum, split_status):
        return effective, None
    if _confirmed_strategy_priors(learning_state) > 0:
        return effective, None
    recommendation_count = _measurement_recommendation_count(curriculum)
    if recommendation_count < 2:
        return effective, None

    counts = _role_counts(effective)
    if counts.get("measurement", 0) >= 2:
        return effective, None

    adaptation = effective.get("adaptation") or {}
    min_slots = adaptation.get("min_role_slots") or {
        "experiment": 4,
        "coverage": 2,
        "adjacency": 1,
        "measurement": 1,
        "verification": 1,
        "wildcard": 1,
    }
    max_changes = int(
        adaptation.get("max_slot_changes_per_generation", 1)
        or 0
    )
    if max_changes < 1:
        return effective, None

    measurement_slots = [
        slot
        for slot in slots
        if slot.get("role") == "measurement"
    ]
    if not measurement_slots:
        return effective, None
    template = sorted(
        measurement_slots,
        key=lambda slot: str(slot.get("slot_id") or ""),
    )[0]

    donor_role = None
    donor_slot = None
    for role in DONOR_PREFERENCE:
        if counts.get(role, 0) <= int(min_slots.get(role, 0)):
            continue
        candidates = [
            slot
            for slot in slots
            if slot.get("role") == role
        ]
        if not candidates:
            continue
        donor_role = role
        donor_slot = sorted(
            candidates,
            key=lambda slot: str(slot.get("slot_id") or ""),
            reverse=True,
        )[0]
        break

    if donor_role is None or donor_slot is None:
        return effective, None

    donor_slot["role"] = "measurement"
    donor_slot["accepts"] = list(
        template.get("accepts") or ["learning_measurement"]
    )
    donor_slot["label"] = (
        template.get("label") or "Adaptive learning measurement"
    )

    shift = {
        "reason": BOOTSTRAP_REASON,
        "from_role": donor_role,
        "to_role": "measurement",
        "slot_id": donor_slot.get("slot_id"),
        "measurement_recommendations": recommendation_count,
        "confirmed_strategy_priors": 0,
        "blind_confirmation_operational": True,
        "automatic_revert_condition": (
            "first strategy-level prior becomes "
            "eligible_for_policy_consideration"
        ),
    }
    return effective, shift
