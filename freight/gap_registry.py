"""Canonical Freight Recovery gap registry.

Research is denied by default. A registered gap authorizes GitHub search only
when it is explicitly ACTIVE_SEARCH and its requested trigger is allowlisted.
"""
from __future__ import annotations
import argparse
import json
from dataclasses import dataclass
from pathlib import Path

VALID_STATUSES = {
    "BLOCKED_EXTERNAL",
    "ACTIVE_DILIGENCE",
    "ACTIVE_INTERNAL",
    "DORMANT_TRIGGERED",
    "ACTIVE_SEARCH",
    "CLOSED",
}

@dataclass(frozen=True)
class GapDecision:
    allowed: bool
    reasons: tuple[str, ...]
    gap: dict | None = None

def load_register(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())

def validate_register(register: dict) -> list[str]:
    errors: list[str] = []
    if register.get("stage_gate") != "EXP-001":
        errors.append("register must be bound to EXP-001")
    gaps = register.get("gaps")
    if not isinstance(gaps, list) or not gaps:
        return errors + ["gaps must be a non-empty list"]

    seen: set[str] = set()
    for index, gap in enumerate(gaps):
        prefix = f"gaps[{index}]"
        gap_id = gap.get("gap_id")
        if not isinstance(gap_id, str) or not gap_id.strip():
            errors.append(f"{prefix}.gap_id is required")
            continue
        if gap_id in seen:
            errors.append(f"duplicate gap_id: {gap_id}")
        seen.add(gap_id)

        if gap.get("status") not in VALID_STATUSES:
            errors.append(f"{gap_id}: invalid status")
        if not isinstance(gap.get("search_allowed"), bool):
            errors.append(f"{gap_id}: search_allowed must be boolean")
        if not isinstance(gap.get("allowed_triggers"), list):
            errors.append(f"{gap_id}: allowed_triggers must be a list")
        for field in ("title","commercial_effect","stop_condition"):
            value = gap.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{gap_id}: {field} is required")
        evidence = gap.get("evidence_to_close")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{gap_id}: evidence_to_close must be non-empty")

        if gap.get("search_allowed") and gap.get("status") != "ACTIVE_SEARCH":
            errors.append(f"{gap_id}: search_allowed requires ACTIVE_SEARCH status")
        if gap.get("status") == "ACTIVE_SEARCH" and not gap.get("search_allowed"):
            errors.append(f"{gap_id}: ACTIVE_SEARCH must set search_allowed=true")
    return errors

def gap_index(register: dict) -> dict[str, dict]:
    errors = validate_register(register)
    if errors:
        raise ValueError("; ".join(errors))
    return {gap["gap_id"]: gap for gap in register["gaps"]}

def authorize_search(register: dict, gap_id: str, trigger: str) -> GapDecision:
    gaps = gap_index(register)
    gap = gaps.get(gap_id)
    if gap is None:
        return GapDecision(False, ("gap_id_not_registered",), None)

    reasons: list[str] = []
    if gap["status"] != "ACTIVE_SEARCH":
        reasons.append(f"gap_status_{gap['status'].lower()}_does_not_authorize_search")
    if not gap["search_allowed"]:
        reasons.append("gap_search_not_allowed")
    if trigger not in gap["allowed_triggers"]:
        reasons.append("trigger_not_allowed_for_gap")
    return GapDecision(not reasons, tuple(reasons), gap)

def active_search_gaps(register: dict) -> list[str]:
    return sorted(
        gap["gap_id"]
        for gap in gap_index(register).values()
        if gap["status"] == "ACTIVE_SEARCH" and gap["search_allowed"]
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default="freight/GAP_REGISTER.json")
    parser.add_argument("--list-active-search", action="store_true")
    args = parser.parse_args()
    register = load_register(args.registry)
    errors = validate_register(register)
    result = {
        "valid": not errors,
        "errors": errors,
        "active_search_gaps": active_search_gaps(register) if not errors else [],
    }
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if errors else 0)
