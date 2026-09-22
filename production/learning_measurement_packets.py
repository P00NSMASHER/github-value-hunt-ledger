from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence



def _stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def choose_seed_for_measurement(
    strategy_id: str,
    seeds: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    """Choose the curriculum-backed adaptive measurement seed.

    Adaptive learning packets must never fall back to ordinary discovery or
    frozen benchmark measurement seeds. The seed compiler creates at most one
    current `learning_measurement` seed per recommended strategy; packet
    generation binds to that exact semantic work kind.
    """
    candidates = [
        seed
        for seed in seeds
        if seed.get("strategy_id") == strategy_id
        and seed.get("work_action") == "search"
        and seed.get("seed_type") == "learning_measurement"
        and seed.get("authorization_basis")
        == "adaptive_learning_curriculum"
        and isinstance(seed.get("seed_id"), str)
        and str(seed.get("seed_id")).startswith("SEED:learn:")
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda seed: str(seed.get("seed_id") or "")
    )
    return candidates[0]


def build_measurement_packets(
    curriculum: Mapping[str, Any],
    seeds: Sequence[Mapping[str, Any]],
    *,
    curriculum_sha: str,
    seeds_sha: str,
) -> dict[str, Any]:
    if curriculum.get("mode") != "measurement_only":
        raise ValueError("curriculum must be measurement_only")
    if curriculum.get("policy_effect") != "none":
        raise ValueError("curriculum must have no policy effect")

    packets: list[dict[str, Any]] = []
    unpaired: list[dict[str, Any]] = []

    for rec in curriculum.get("recommended_measurements") or []:
        strategy_id = rec.get("strategy_id")
        if not isinstance(strategy_id, str):
            continue
        seed = choose_seed_for_measurement(strategy_id, seeds)
        if seed is None:
            unpaired.append(
                {
                    "strategy_id": strategy_id,
                    "reason": "no_authorized_search_seed_for_strategy",
                }
            )
            continue

        source = {
            "strategy_id": strategy_id,
            "phase": rec.get("phase"),
            "seed_id": seed["seed_id"],
            "curriculum_sha": curriculum_sha,
            "seeds_sha": seeds_sha,
        }
        packet_id = "LMP:" + _stable_hash(source)[:16]
        packet: dict[str, Any] = {
            "schema_version": 1,
            "packet_id": packet_id,
            "status": "PRECOMMITTED_ADVISORY",
            "policy_effect": "none",
            "execution_authority": False,
            "requires_generated_claim": True,
            "manual_work_can_complete_packet": False,
            "partition_selection_allowed": False,
            "partition_unknown_until_ingestion": True,
            "strategy_id": strategy_id,
            "measurement_phase": rec.get("phase"),
            "selection_reason": rec.get("selection_reason"),
            "measurement_priority_audit_only": rec.get(
                "measurement_priority"
            ),
            "evidence_deficit": {
                "train": rec.get("train") or {},
                "confirm": rec.get("confirm") or {},
            },
            "seed": {
                "seed_id": seed.get("seed_id"),
                "seed_type": seed.get("seed_type"),
                "work_action": seed.get("work_action"),
                "measurement_contract_version": seed.get(
                    "measurement_contract_version"
                ),
                "query_recipe_id": seed.get("query_recipe_id"),
                "query_anchors": list(
                    seed.get("query_anchors") or []
                ),
                "next_action": seed.get("next_action"),
                "action_gate": seed.get("action_gate"),
                "required_signatures": list(
                    seed.get("required_signatures") or []
                ),
                "search_objective_id": seed.get(
                    "search_objective_id"
                ),
                "capability_ids": list(
                    seed.get("capability_ids") or []
                ),
                "experiment_ids": list(
                    seed.get("experiment_ids") or []
                ),
                "authorization_basis": seed.get(
                    "authorization_basis"
                ),
                "acceptance_target": seed.get(
                    "acceptance_target"
                ),
                "why_now": seed.get("why_now"),
                "query_templates": list(
                    seed.get("query_templates") or []
                ),
                "search_surfaces": list(
                    seed.get("search_surfaces") or []
                ),
                "verification_gate": seed.get(
                    "verification_gate"
                ),
                "stop_conditions": list(
                    seed.get("stop_conditions") or []
                ),
                "exclude_domains": list(
                    seed.get("exclude_domains") or []
                ),
            },
            "blind_partition_rule": rec.get(
                "blind_partition_rule"
            ),
            "retry_rule": rec.get("retry_rule"),
            "execution_contract": (
                "When hunters are explicitly resumed, use the normal "
                "generated assignment/claim path exactly once. Execute "
                "the frozen strategy against the frozen seed hypothesis. "
                "Do not inspect, predict, choose, release, or retry based "
                "on train/confirm membership. Canonical ingestion decides "
                "partition and learning credit after execution."
            ),
            "provenance": {
                "learning_curriculum_sha": curriculum_sha,
                "search_seeds_sha": seeds_sha,
            },
        }
        packet["packet_sha256"] = _stable_hash(packet)
        packets.append(packet)

    return {
        "schema_version": 1,
        "mode": "precommit_only",
        "policy_effect": "none",
        "activates_work": False,
        "partition_selection_allowed": False,
        "packets": packets,
        "unpaired_recommendations": unpaired,
    }


def validate_measurement_packets(
    bundle: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if bundle.get("schema_version") != 1:
        errors.append("unexpected_schema_version")
    if bundle.get("mode") != "precommit_only":
        errors.append("mode_must_be_precommit_only")
    if bundle.get("policy_effect") != "none":
        errors.append("policy_effect_must_be_none")
    if bundle.get("activates_work") is not False:
        errors.append("packets_must_not_activate_work")
    if bundle.get("partition_selection_allowed") is not False:
        errors.append("partition_selection_must_be_false")

    seen: set[str] = set()
    for packet in bundle.get("packets") or []:
        pid = packet.get("packet_id")
        if not isinstance(pid, str) or not pid.startswith("LMP:"):
            errors.append("invalid_packet_id")
            continue
        if pid in seen:
            errors.append(f"duplicate_packet:{pid}")
        seen.add(pid)

        if packet.get("status") != "PRECOMMITTED_ADVISORY":
            errors.append(f"invalid_status:{pid}")
        if packet.get("execution_authority") is not False:
            errors.append(f"execution_authority_must_be_false:{pid}")
        if packet.get("requires_generated_claim") is not True:
            errors.append(f"generated_claim_required:{pid}")
        if packet.get("manual_work_can_complete_packet") is not False:
            errors.append(f"manual_completion_must_be_false:{pid}")
        if packet.get("partition_selection_allowed") is not False:
            errors.append(f"packet_partition_selection_must_be_false:{pid}")
        if packet.get("partition_unknown_until_ingestion") is not True:
            errors.append(f"partition_must_remain_unknown:{pid}")
        if not packet.get("blind_partition_rule"):
            errors.append(f"missing_blind_partition_rule:{pid}")
        if not packet.get("retry_rule"):
            errors.append(f"missing_retry_rule:{pid}")

        seed = packet.get("seed") or {}
        if not seed.get("seed_id"):
            errors.append(f"seed_required:{pid}")
        if seed.get("seed_type") != "learning_measurement":
            errors.append(f"learning_measurement_seed_required:{pid}")
        if seed.get("work_action") != "search":
            errors.append(f"learning_measurement_search_required:{pid}")
        if seed.get("measurement_contract_version") != "phase_blind_v1":
            errors.append(f"phase_blind_contract_required:{pid}")
        if not seed.get("query_recipe_id"):
            errors.append(f"query_recipe_required:{pid}")
        if not seed.get("query_anchors"):
            errors.append(f"query_anchors_required:{pid}")
        if not seed.get("next_action"):
            errors.append(f"next_action_required:{pid}")
        if not seed.get("action_gate"):
            errors.append(f"action_gate_required:{pid}")
        if not seed.get("required_signatures"):
            errors.append(f"required_signatures_required:{pid}")
        if seed.get("authorization_basis") != "adaptive_learning_curriculum":
            errors.append(f"learning_curriculum_authorization_required:{pid}")
        if not str(seed.get("seed_id") or "").startswith("SEED:learn:"):
            errors.append(f"learning_seed_id_required:{pid}")
        if not seed.get("acceptance_target"):
            errors.append(f"acceptance_target_required:{pid}")
        if not seed.get("query_templates"):
            errors.append(f"queries_required:{pid}")
        if not seed.get("search_surfaces"):
            errors.append(f"search_surfaces_required:{pid}")

        supplied = packet.get("packet_sha256")
        body = dict(packet)
        body.pop("packet_sha256", None)
        if supplied != _stable_hash(body):
            errors.append(f"packet_hash_mismatch:{pid}")

    return errors
