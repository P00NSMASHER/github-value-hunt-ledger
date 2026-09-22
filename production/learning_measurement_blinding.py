from __future__ import annotations

import json
from typing import Any, Mapping


PHASE_BLIND_CONTRACT_VERSION = "phase_blind_v1"
REQUIRED_AUTHORIZATION_BASIS = "adaptive_learning_curriculum"
REQUIRED_BLINDING_STOP = (
    "Do not inspect LEARNING_CURRICULUM.md, learning_curriculum.json, "
    "LEARNING_STATE.json, TRAINING_SPLIT_STATUS.json, or training split "
    "receipts before freezing this run's evidence and result."
)

FORBIDDEN_WORKER_FIELDS = {
    "learning_phase",
    "learning_curriculum_rank",
    "learning_selection_reason",
    "train_evidence",
    "confirm_evidence",
    "train_runs_needed",
    "confirm_runs_needed",
    "train_deep_inspections_needed",
    "confirm_deep_inspections_needed",
}

FORBIDDEN_WORKER_TEXT = (
    "train_measurement",
    "confirm_measurement",
    "train evidence:",
    "confirm evidence:",
    "train evidence ",
    "confirm evidence ",
    "train gate",
    "confirm gate",
    "learning phase",
    "confirmation debt",
    "training debt",
)


def _serialized_text(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    ).lower()


def worker_measurement_blinding_errors(
    seed: Mapping[str, Any],
) -> list[str]:
    """Return leakage/contract errors for a worker-visible learning seed."""
    if seed.get("seed_type") != "learning_measurement":
        return []

    errors: list[str] = []
    if seed.get("measurement_contract_version") != (
        PHASE_BLIND_CONTRACT_VERSION
    ):
        errors.append("phase_blind_contract_required")
    if seed.get("authorization_basis") != REQUIRED_AUTHORIZATION_BASIS:
        errors.append("adaptive_learning_authorization_required")

    for field in sorted(FORBIDDEN_WORKER_FIELDS):
        if field in seed:
            errors.append(f"planner_only_field_exposed:{field}")

    serialized = _serialized_text(seed)
    for token in FORBIDDEN_WORKER_TEXT:
        if token in serialized:
            errors.append(
                "planner_only_text_exposed:"
                + token.replace(" ", "_").replace(":", "")
            )

    stop_conditions = [
        str(value)
        for value in seed.get("stop_conditions") or []
    ]
    if REQUIRED_BLINDING_STOP not in stop_conditions:
        errors.append("planner_state_blinding_stop_required")

    why_now = str(seed.get("why_now") or "")
    if not why_now:
        errors.append("phase_blind_measurement_reason_required")
    if "scheduler-selected adaptive-learning measurement" not in why_now:
        errors.append("phase_blind_measurement_reason_not_neutral")

    return sorted(set(errors))
