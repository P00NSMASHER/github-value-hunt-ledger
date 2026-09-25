"""Compile Hunter-eligible AI Business OS portfolio work into deterministic Hunter seed packets.

This module is deliberately transport-only. It cannot claim Hunter slots, create leases, emit
execution lifecycle events, or perform external writes. It only converts already Hunter-eligible
portfolio-plan work items into bounded search packets that the existing Hunter allocator may
consider.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

PUBLIC_TECHNICAL_SOURCE_TYPES = {
    "PUBLIC_GITHUB",
    "PUBLIC_CODE",
    "OPEN_SOURCE",
    "REPOSITORY",
    "TECHNICAL_IMPLEMENTATION",
}


class HunterBridgeError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise HunterBridgeError("cannot derive seed slug")
    return slug


def _queries(item: Mapping[str, Any]) -> list[str]:
    initiative = str(item["initiative_name"]).strip()
    metric = str(item["metric_key"]).strip().replace("_", " ")
    source = str(item["required_source_type"]).strip().replace("_", " ")
    return [
        f'"{initiative}" "{metric}" implementation',
        f'"{metric}" "{source}" path:tests',
        f'"{metric}" repository schema migration tests',
    ]


def compile_hunter_seeds(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    plan_hash = str(plan.get("plan_hash", "")).strip()
    if not re.fullmatch(r"[0-9a-f]{64}", plan_hash):
        raise HunterBridgeError("plan_hash must be a SHA-256 hex digest")

    queue = plan.get("hunter_queue", [])
    if not isinstance(queue, list):
        raise HunterBridgeError("hunter_queue must be a list")

    seeds: list[dict[str, Any]] = []
    seen_work_ids: set[str] = set()
    for raw in queue:
        if not isinstance(raw, Mapping):
            raise HunterBridgeError("hunter_queue entries must be objects")
        item = dict(raw)
        work_id = str(item.get("work_id", "")).strip()
        if not work_id or work_id in seen_work_ids:
            raise HunterBridgeError("Hunter work_id is missing or duplicated")
        seen_work_ids.add(work_id)

        source_type = str(item.get("required_source_type", "")).strip().upper()
        if item.get("hunter_eligible") is not True:
            raise HunterBridgeError(f"{work_id}: queue item is not explicitly Hunter-eligible")
        if source_type not in PUBLIC_TECHNICAL_SOURCE_TYPES:
            raise HunterBridgeError(f"{work_id}: source type is outside the public technical allowlist")
        if item.get("planning_only") is not True:
            raise HunterBridgeError(f"{work_id}: planning_only must remain true")
        if item.get("external_write_allowed") is not False:
            raise HunterBridgeError(f"{work_id}: external writes must remain disabled")
        if item.get("human_approval_required_for_external_write") is not True:
            raise HunterBridgeError(f"{work_id}: external writes must remain human-gated")

        initiative_key = str(item.get("initiative_key", "")).strip()
        metric_key = str(item.get("metric_key", "")).strip()
        gap_type = str(item.get("gap_type", "")).strip()
        acceptance_target = str(item.get("acceptance_target", "")).strip()
        priority = int(item.get("priority", 0))
        if not all((initiative_key, metric_key, gap_type, acceptance_target)):
            raise HunterBridgeError(f"{work_id}: missing work identity or acceptance target")
        if not 0 <= priority <= 100:
            raise HunterBridgeError(f"{work_id}: priority outside 0..100")

        seed_core = {
            "bridge_version": 1,
            "business_os_plan_hash": plan_hash,
            "business_os_work_id": work_id,
            "initiative_id": str(item.get("initiative_id", "")),
            "initiative_key": initiative_key,
            "initiative_name": str(item.get("initiative_name", "")).strip(),
            "metric_key": metric_key,
            "gap_type": gap_type,
            "required_source_type": source_type,
            "acceptance_target": acceptance_target,
            "priority": priority,
        }
        seed_hash = _sha(seed_core)
        seeds.append(
            {
                "seed_id": f"BOS:{_slug(initiative_key)}:{_slug(metric_key)}:{seed_hash[:12]}",
                "seed_type": "business_os_gap",
                "work_action": "search",
                "priority": priority,
                "source_id": f"BUSINESS_OS:{work_id}",
                "title": f"Business OS gap — {initiative_key} / {metric_key}",
                "business_os_plan_hash": plan_hash,
                "business_os_work_id": work_id,
                "business_os_seed_hash": seed_hash,
                "initiative_id": seed_core["initiative_id"],
                "initiative_key": initiative_key,
                "metric_key": metric_key,
                "gap_type": gap_type,
                "required_source_type": source_type,
                "query_anchors": [initiative_key, metric_key],
                "queries": _queries(item),
                "acceptance_target": acceptance_target,
                "instructions": {
                    "work_action": "search",
                    "why_now": (
                        f"AI Business OS has an unresolved {gap_type} evidence gap for "
                        f"{initiative_key}/{metric_key} that explicitly requires {source_type}."
                    ),
                    "acceptance_target": acceptance_target,
                    "queries": _queries(item),
                    "search_surfaces": [
                        "public GitHub repository search",
                        "public GitHub code search",
                        "public technical documentation and repository history",
                    ],
                    "verification_gate": (
                        "Return exact public source identity, revision, implementation evidence, tests or "
                        "equivalent technical proof, and provenance. README claims alone are insufficient."
                    ),
                    "stop_conditions": [
                        "Search only legitimate public technical sources.",
                        "Do not inspect, retain, or operationalize credentials, secrets, private data, or accidental confidential material.",
                        "Do not contact external parties, spend money, deploy, modify repositories, or perform other external writes.",
                        "A finding is evidence for the Business OS gap, not automatic closure of that gap.",
                    ],
                },
                "planning_only": True,
                "external_write_allowed": False,
                "human_approval_required_for_external_write": True,
            }
        )

    seeds.sort(key=lambda row: (-row["priority"], row["seed_id"]))
    return seeds
