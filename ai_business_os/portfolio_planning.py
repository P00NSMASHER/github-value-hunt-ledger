"""Deterministic observe-only planner for production portfolio evidence gaps.

The planner converts verified production state into proposed RESEARCH, BUILD, and VERIFY work.
It does not create goals, claim Hunter leases, call tools, approve requests, or perform external
writes. Hunter eligibility is intentionally narrow: only explicitly public technical source types
may enter the Hunter lane.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from ai_business_os.production_bridge import ProductionBridgeError, ProductionReadBridge


class PortfolioPlanningError(ValueError):
    """Raised when production planning inputs are incomplete or contradictory."""


ROLE_RULES = {
    "cash_collected_30d": ("VERIFY", "FINANCE_ANALYTICS"),
    "cash_costs_30d": ("VERIFY", "FINANCE_ANALYTICS"),
    "ai_cost_30d": ("VERIFY", "FINANCE_ANALYTICS"),
    "contracted_pipeline_value_90d": ("VERIFY", "GROWTH_SALES"),
    "remaining_effort_hours": ("BUILD", "ENGINEERING"),
    "time_to_cash_days": ("RESEARCH", "FINANCE_ANALYTICS"),
    "market_evidence_signal": ("VERIFY", "GROWTH_SALES"),
}

HUNTER_SOURCE_TYPES = {
    "PUBLIC_GITHUB",
    "PUBLIC_CODE",
    "OPEN_SOURCE",
    "REPOSITORY",
    "TECHNICAL_IMPLEMENTATION",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _agent_by_role(agents: list[dict[str, Any]]) -> dict[str, str]:
    role_map: dict[str, str] = {}
    for agent in agents:
        if agent.get("status") != "ACTIVE":
            continue
        role = str(agent.get("role_key", "")).strip()
        agent_id = str(agent.get("agent_id", "")).strip()
        if not role or not agent_id:
            raise PortfolioPlanningError("active agent is missing role_key or agent_id")
        if role in role_map:
            raise PortfolioPlanningError(f"multiple active agents claim role {role}")
        role_map[role] = agent_id
    return role_map


def _acceptance_target(metric_key: str, source_type: str) -> str:
    targets = {
        "cash_collected_30d": "Obtain authoritative collected-cash evidence covering the initiative and measurement window.",
        "cash_costs_30d": "Obtain authoritative cash-cost evidence covering the initiative and measurement window.",
        "ai_cost_30d": "Obtain attributable AI/tool cost evidence from invoice or ledger records.",
        "contracted_pipeline_value_90d": "Verify signed or contract-grade pipeline evidence; do not count unweighted outreach.",
        "remaining_effort_hours": "Produce a repository/project-scoped remaining-work inventory with evidence-backed effort assumptions; do not modify code.",
        "time_to_cash_days": "Produce an evidence-backed time-to-cash estimate with explicit assumptions and source dates.",
        "market_evidence_signal": "Verify completed experiment, customer-response, or equivalent market evidence before treating demand as allocation-grade.",
    }
    return targets.get(
        metric_key,
        f"Resolve the evidence gap using the required source type {source_type} with explicit provenance.",
    )


def _goal_overlap_ids(
    open_goals: list[dict[str, Any]],
    *,
    owner_agent_id: str,
    metric_key: str,
) -> list[str]:
    tokens = {
        "cash_collected_30d": ("cash", "revenue", "outcome"),
        "cash_costs_30d": ("cost", "cash", "economics"),
        "ai_cost_30d": ("ai", "tool", "cost"),
        "contracted_pipeline_value_90d": ("pipeline", "contract", "revenue"),
        "remaining_effort_hours": ("effort", "build", "engineering"),
        "time_to_cash_days": ("time-to-cash", "cash", "revenue"),
        "market_evidence_signal": ("market", "outreach", "reply", "measurement"),
    }.get(metric_key, (metric_key.replace("_", " "),))
    overlaps = []
    for goal in open_goals:
        if goal.get("agent_id") != owner_agent_id:
            continue
        haystack = " ".join(
            [
                str(goal.get("goal_type", "")),
                str(goal.get("title", "")),
                _canonical(goal.get("constraints", {})),
                _canonical(goal.get("evidence_requirements", [])),
            ]
        ).lower()
        if any(token.lower() in haystack for token in tokens):
            overlaps.append(str(goal["id"]))
    return sorted(overlaps)


def build_portfolio_plan(
    *,
    schema_fingerprint: str,
    command_center_snapshot_hash: str | None,
    planning_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    agents = [dict(x) for x in planning_inputs.get("agents", [])]
    initiatives = [dict(x) for x in planning_inputs.get("initiatives", [])]
    gaps = [dict(x) for x in planning_inputs.get("data_gaps", [])]
    open_goals = [dict(x) for x in planning_inputs.get("open_goals", [])]

    role_map = _agent_by_role(agents)
    initiative_map = {str(row["id"]): row for row in initiatives}
    if len(initiative_map) != len(initiatives):
        raise PortfolioPlanningError("duplicate initiative ids in planning input")

    work_items = []
    for gap in gaps:
        initiative_id = str(gap.get("initiative_id", ""))
        initiative = initiative_map.get(initiative_id)
        if not initiative:
            raise PortfolioPlanningError(f"gap references unknown initiative {initiative_id}")

        metric_key = str(gap.get("metric_key", "")).strip()
        source_type = str(gap.get("recommended_source_type", "")).strip()
        gap_type = str(gap.get("gap_type", "")).strip()
        if not metric_key or not source_type or not gap_type:
            raise PortfolioPlanningError("gap is missing metric/source/type identity")

        work_kind, owner_role = ROLE_RULES.get(metric_key, ("RESEARCH", "RESEARCH"))
        owner_agent_id = role_map.get(owner_role)
        if not owner_agent_id:
            raise PortfolioPlanningError(f"no active agent for required role {owner_role}")

        hunter_eligible = source_type.upper() in HUNTER_SOURCE_TYPES
        item_identity = {
            "initiative_key": initiative["initiative_key"],
            "metric_key": metric_key,
            "gap_type": gap_type,
            "source_type": source_type,
            "rationale": gap.get("rationale"),
        }
        work_items.append(
            {
                "work_id": f"portfolio-plan:{_sha(item_identity)[:16]}",
                "initiative_id": initiative_id,
                "initiative_key": initiative["initiative_key"],
                "initiative_name": initiative["name"],
                "metric_key": metric_key,
                "gap_type": gap_type,
                "priority": int(gap.get("priority", 0)),
                "work_kind": work_kind,
                "owner_role": owner_role,
                "owner_agent_id": owner_agent_id,
                "hunter_eligible": hunter_eligible,
                "required_source_type": source_type,
                "acceptance_target": _acceptance_target(metric_key, source_type),
                "overlap_goal_ids": _goal_overlap_ids(
                    open_goals,
                    owner_agent_id=owner_agent_id,
                    metric_key=metric_key,
                ),
                "planning_only": True,
                "external_write_allowed": False,
                "human_approval_required_for_external_write": True,
            }
        )

    work_items.sort(
        key=lambda item: (
            -item["priority"],
            item["initiative_key"],
            item["metric_key"],
            item["work_id"],
        )
    )
    agent_queue = [item for item in work_items if not item["hunter_eligible"]]
    hunter_queue = [item for item in work_items if item["hunter_eligible"]]

    packet_core = {
        "schema_fingerprint": schema_fingerprint,
        "command_center_snapshot_hash": command_center_snapshot_hash,
        "work_items": work_items,
    }
    return {
        **packet_core,
        "plan_hash": _sha(packet_core),
        "summary": {
            "total_work_items": len(work_items),
            "agent_work_items": len(agent_queue),
            "hunter_work_items": len(hunter_queue),
            "research_items": sum(1 for x in work_items if x["work_kind"] == "RESEARCH"),
            "build_items": sum(1 for x in work_items if x["work_kind"] == "BUILD"),
            "verify_items": sum(1 for x in work_items if x["work_kind"] == "VERIFY"),
        },
        "agent_queue": agent_queue,
        "hunter_queue": hunter_queue,
    }


def plan_from_bridge(
    bridge: ProductionReadBridge,
    *,
    expected_schema_fingerprint: str,
) -> dict[str, Any]:
    fingerprint = bridge.assert_schema_current(expected_schema_fingerprint)
    snapshot = bridge.latest_command_center_snapshot()
    snapshot_hash = str(snapshot["snapshot_hash"]) if snapshot else None
    return build_portfolio_plan(
        schema_fingerprint=fingerprint,
        command_center_snapshot_hash=snapshot_hash,
        planning_inputs=bridge.planning_inputs(),
    )
