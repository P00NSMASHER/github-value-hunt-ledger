"""Validate RecoveryOS Phase 3 Step 5 synthetic customer proof and enterprise readiness.

The Step 5 program intentionally distinguishes:
- synthetic AI buyer pressure-testing;
- internally completed diligence/readiness artifacts;
- real customer evidence that remains external.

A simulated buyer may approve a synthetic pilot scenario, but that result must
never be promoted into customer adoption, revenue, willingness-to-pay, or a case
study.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


VALID_DECISIONS = {"APPROVE_PILOT", "CONDITIONAL", "BLOCKED"}
VALID_STATES = {
    "COMPLETE_INTERNAL",
    "COMPLETE_SYNTHETIC",
    "COMPLETE_CURRENT",
    "PENDING_EXTERNAL",
    "PENDING_PRODUCT",
}
FORBIDDEN_PROMOTIONS = (
    "real customer",
    "customer testimonial",
    "customer case study",
    "paid customer",
    "customer revenue",
    "proven willingness to pay",
)
REQUIRED_INTERNAL_WORKSTREAMS = {
    "buyer_security_questionnaire",
    "architecture_and_data_flow",
    "implementation_runbook",
    "slo_sla_framework",
    "roi_methodology",
    "customer_proof_package",
    "synthetic_ai_customer_simulation",
    "competitor_matrix",
}
REQUIRED_EXTERNAL_WORKSTREAMS = {
    "blind_real_customer_accuracy",
    "genuine_reference_customer",
    "realized_recovery_customer_proof",
    "independent_security_assurance",
}
REQUIRED_PRODUCT_GAPS = {
    "enterprise_identity",
    "named_enterprise_connectors",
}


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_simulation(payload: dict) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != 1:
        errors.append("simulation schema_version must be 1")
    if payload.get("simulation_type") != "SYNTHETIC_AI_BUYER_PERSONA_SIMULATION":
        errors.append("simulation_type must be SYNTHETIC_AI_BUYER_PERSONA_SIMULATION")

    generator = payload.get("generator") or {}
    if generator.get("independent_of_builder") is not False:
        errors.append("AI buyer simulation must disclose that it is not independent")

    boundaries = payload.get("claim_boundary")
    if not isinstance(boundaries, list) or not boundaries:
        errors.append("simulation claim_boundary required")
    else:
        joined = " ".join(str(item).lower() for item in boundaries)
        required = ("fictional", "not customer evidence", "not independent")
        for phrase in required:
            if phrase not in joined:
                errors.append(f"simulation boundary must disclose: {phrase}")

    buyers = payload.get("buyer_archetypes")
    if not isinstance(buyers, list) or len(buyers) < 3:
        errors.append("simulation requires at least three buyer archetypes")
        return errors

    bot_ids: set[str] = set()
    decisions = Counter()
    blocker_counts = Counter()
    buyers_with_approver = 0
    enterprise_ready = 0

    for buyer in buyers:
        if buyer.get("fictional") is not True:
            errors.append(f"{buyer.get('buyer_id')}: buyer must be marked fictional")
        bots = buyer.get("bots")
        if not isinstance(bots, list) or len(bots) < 3:
            errors.append(f"{buyer.get('buyer_id')}: requires >=3 buyer bots")
            continue
        has_approve = False
        all_approve = True
        for bot in bots:
            bot_id = bot.get("bot_id")
            if not isinstance(bot_id, str) or not bot_id:
                errors.append("bot_id required")
                continue
            if bot_id in bot_ids:
                errors.append(f"duplicate bot_id: {bot_id}")
            bot_ids.add(bot_id)

            decision = bot.get("decision")
            if decision not in VALID_DECISIONS:
                errors.append(f"{bot_id}: invalid decision")
                continue
            decisions[decision] += 1
            has_approve = has_approve or decision == "APPROVE_PILOT"
            all_approve = all_approve and decision == "APPROVE_PILOT"

            primary = bot.get("primary_blocker")
            if not isinstance(primary, str) or not primary:
                errors.append(f"{bot_id}: primary_blocker required")
            blockers = bot.get("blockers")
            if not isinstance(blockers, list):
                errors.append(f"{bot_id}: blockers must be a list")
                blockers = []
            blocker_counts.update(str(item) for item in blockers)

            if not isinstance(bot.get("rationale"), str) or not bot["rationale"].strip():
                errors.append(f"{bot_id}: rationale required")
            if not isinstance(bot.get("questions"), list) or len(bot["questions"]) < 2:
                errors.append(f"{bot_id}: at least two buyer questions required")
            if not isinstance(bot.get("conditions_to_approve"), list) or not bot["conditions_to_approve"]:
                errors.append(f"{bot_id}: conditions_to_approve required")

        buyers_with_approver += int(has_approve)
        enterprise_ready += int(all_approve)

    expected = payload.get("aggregate_expected") or {}
    if int(expected.get("total_bots") or -1) != len(bot_ids):
        errors.append("aggregate total_bots mismatch")
    if int(expected.get("approve_pilot") or -1) != decisions["APPROVE_PILOT"]:
        errors.append("aggregate approve_pilot mismatch")
    if int(expected.get("conditional") or -1) != decisions["CONDITIONAL"]:
        errors.append("aggregate conditional mismatch")
    if int(expected.get("blocked") or -1) != decisions["BLOCKED"]:
        errors.append("aggregate blocked mismatch")
    if int(expected.get("buyers_with_at_least_one_pilot_approver") or -1) != buyers_with_approver:
        errors.append("aggregate buyers_with_at_least_one_pilot_approver mismatch")
    enterprise_expected = expected.get("enterprise_wide_ready_buyers")
    if enterprise_expected is None or int(enterprise_expected) != enterprise_ready:
        errors.append("aggregate enterprise_wide_ready_buyers mismatch")

    ordered_blockers = [
        name
        for name, _ in sorted(
            blocker_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    expected_top = expected.get("most_common_blockers") or []
    for blocker in expected_top:
        if blocker not in ordered_blockers[:5]:
            errors.append(f"expected common blocker not present near top: {blocker}")

    if expected.get("overall_simulated_verdict") != (
        "SCOPED_PILOT_SELLABLE_ENTERPRISE_ROLLOUT_NOT_YET_READY"
    ):
        errors.append("synthetic overall verdict must remain conservative")

    raw = json.dumps(payload, sort_keys=True).lower()
    for phrase in FORBIDDEN_PROMOTIONS:
        if phrase in raw and phrase not in " ".join(str(x).lower() for x in boundaries):
            errors.append(f"simulation contains unsafe promotion phrase: {phrase}")
    return errors


def summarize_simulation(payload: dict) -> dict:
    errors = validate_simulation(payload)
    if errors:
        raise ValueError("; ".join(errors))

    decisions = Counter()
    blocker_counts = Counter()
    role_decisions: dict[str, Counter] = {}
    for buyer in payload["buyer_archetypes"]:
        for bot in buyer["bots"]:
            decisions[bot["decision"]] += 1
            blocker_counts.update(bot["blockers"])
            role_decisions.setdefault(bot["role"], Counter())[bot["decision"]] += 1

    return {
        "buyers": len(payload["buyer_archetypes"]),
        "bots": sum(decisions.values()),
        "decisions": dict(decisions),
        "blockers": dict(
            sorted(blocker_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
        "role_decisions": {
            role: dict(counter) for role, counter in sorted(role_decisions.items())
        },
        "verdict": payload["aggregate_expected"]["overall_simulated_verdict"],
        "customer_evidence": False,
    }


def validate_readiness(payload: dict) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != 1:
        errors.append("readiness schema_version must be 1")
    expected_state = (
        "INTERNAL_ENTERPRISE_READINESS_PACKAGE_COMPLETE_EXTERNAL_CUSTOMER_PROOF_PENDING"
    )
    if payload.get("state") != expected_state:
        errors.append("readiness state must preserve external-customer-proof boundary")

    workstreams = payload.get("workstreams")
    if not isinstance(workstreams, dict):
        return errors + ["workstreams must be an object"]

    required = (
        REQUIRED_INTERNAL_WORKSTREAMS
        | REQUIRED_EXTERNAL_WORKSTREAMS
        | REQUIRED_PRODUCT_GAPS
    )
    missing = required - set(workstreams)
    if missing:
        errors.append("missing workstreams: " + ", ".join(sorted(missing)))

    for name, stream in workstreams.items():
        state = (stream or {}).get("state")
        if state not in VALID_STATES:
            errors.append(f"{name}: invalid workstream state")

    for name in REQUIRED_INTERNAL_WORKSTREAMS:
        if name in workstreams and not str(workstreams[name]["state"]).startswith("COMPLETE"):
            errors.append(f"{name}: internal workstream must be complete")

    for name in REQUIRED_EXTERNAL_WORKSTREAMS:
        if name in workstreams and workstreams[name]["state"] != "PENDING_EXTERNAL":
            errors.append(f"{name}: must remain PENDING_EXTERNAL")

    for name in REQUIRED_PRODUCT_GAPS:
        if name in workstreams and workstreams[name]["state"] != "PENDING_PRODUCT":
            errors.append(f"{name}: must remain PENDING_PRODUCT")

    commercial = payload.get("commercial_readiness") or {}
    if commercial.get("scoped_second_look_pilot") != (
        "READY_WITH_BUYER_AUTHORIZATION_AND_DATA_READINESS"
    ):
        errors.append("scoped pilot readiness must require buyer authorization/data readiness")
    if commercial.get("broad_enterprise_rollout") != "NOT_READY":
        errors.append("broad enterprise rollout must remain NOT_READY")

    completion = payload.get("completion_rule")
    if not isinstance(completion, list) or len(completion) < 3:
        errors.append("completion_rule must preserve synthetic/external boundary")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--simulation",
        default="freight/PHASE3_SYNTHETIC_CUSTOMER_SIMULATION_2026-10-07.json",
    )
    parser.add_argument(
        "--readiness",
        default="freight/PHASE3_ENTERPRISE_READINESS_2026-10-07.json",
    )
    args = parser.parse_args()

    simulation = _load(args.simulation)
    readiness = _load(args.readiness)
    errors = validate_simulation(simulation) + validate_readiness(readiness)
    result = {
        "state": "PASS" if not errors else "FAIL",
        "errors": errors,
        "simulation": summarize_simulation(simulation) if not errors else None,
        "readiness_state": readiness.get("state"),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
