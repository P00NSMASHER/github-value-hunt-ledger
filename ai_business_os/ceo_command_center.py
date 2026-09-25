"""CEO Command Center operator layer for the production AI Business OS.

The command center is an orchestration surface, not a bypass around governance. Natural-language
objectives become deterministic, content-addressed proposals first. A HUMAN may activate an exact
proposal as a PENDING internal goal. External/prod/money/destructive actions still require the
existing governance/approval path and are never executed by this module.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from ai_business_os.portfolio_planning import build_portfolio_plan
from ai_business_os.production_bridge import ProductionBridgeError, ProductionReadBridge


class CommandCenterError(ValueError):
    """Raised when command-center identity or authority invariants are violated."""


ReadExecutor = Callable[[str, tuple[Any, ...]], Sequence[Mapping[str, Any]]]
WriteExecutor = Callable[[str, tuple[Any, ...]], Sequence[Mapping[str, Any]]]

MANDATORY_HUMAN_ACTION_CLASSES = {
    "EXTERNAL_WRITE",
    "PRODUCTION_CHANGE",
    "MONEY_MOVEMENT",
    "DESTRUCTIVE",
    "POLICY_CHANGE",
}

ACTIVATE_GOAL_SQL = """
insert into ai_business_os_prod.agent_goals(
    agent_id,
    goal_type,
    title,
    status,
    priority,
    constraints,
    evidence_requirements,
    created_at,
    updated_at
) values (
    %s, %s, %s, 'PENDING', %s, %s::jsonb, %s::jsonb, now(), now()
)
returning id, agent_id, goal_type, title, status, priority, constraints, evidence_requirements
"""

APPROVAL_LOOKUP_SQL = """
select request_key, agent_id, action_key, action_class, intent_hash, status, expires_at
from ai_business_os_prod.approval_inbox
where request_key = %s
"""

APPROVAL_DECIDE_SQL = """
select *
from ai_business_os_prod.approval_decide(%s, %s, %s, %s)
"""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _clean_text(value: str) -> str:
    return " ".join(str(value).strip().split())


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(re.search(rf"\b{re.escape(word)}\b", low) for word in words)


def _route_role(text: str) -> tuple[str, str]:
    if _contains_any(text, ("build", "fix", "implement", "code", "deploy", "repository", "repo", "bug")):
        return "ENGINEERING", "BUILD"
    if _contains_any(text, ("sell", "sales", "outreach", "customer", "customers", "pipeline", "lead", "leads")):
        return "GROWTH_SALES", "GROWTH"
    if _contains_any(text, ("cash", "cost", "costs", "profit", "finance", "budget", "revenue", "margin")):
        return "FINANCE_ANALYTICS", "ANALYSIS"
    if _contains_any(text, ("product", "roadmap", "ui", "ux", "feature")):
        return "PRODUCT", "PRODUCT"
    if _contains_any(text, ("research", "find", "search", "investigate", "hunter", "evidence")):
        return "RESEARCH", "RESEARCH"
    return "CHIEF_OF_STAFF", "TRIAGE"


def _production_change_intent(text: str) -> bool:
    if _contains_any(text, ("deploy", "migrate", "migration")):
        return True
    low = text.lower()
    production = r"\\b(?:production|prod)\\b"
    change = r"\\b(?:change|update|release|modify|write|push|restart|rollback|promote)\\b"
    return bool(
        re.search(rf"{change}.{{0,48}}{production}", low)
        or re.search(rf"{production}.{{0,48}}{change}", low)
    )


def _possible_action_class(text: str) -> str:
    if _contains_any(text, ("delete", "purge", "destroy", "wipe")):
        return "DESTRUCTIVE"
    if _contains_any(text, ("pay", "purchase", "spend", "transfer", "refund")):
        return "MONEY_MOVEMENT"
    if _production_change_intent(text):
        return "PRODUCTION_CHANGE"
    if _contains_any(text, ("send", "email", "message", "contact", "publish", "post", "outreach")):
        return "EXTERNAL_WRITE"
    return "INTERNAL_WRITE"


def _business_refs(text: str, businesses: Sequence[Mapping[str, Any]]) -> list[str]:
    low = text.lower()
    refs = []
    for business in businesses:
        slug = str(business.get("slug", "")).strip()
        name = str(business.get("name", "")).strip()
        if (slug and slug.lower() in low) or (name and name.lower() in low):
            refs.append(slug or name)
    return sorted(set(refs))


class CommandCenterOperator:
    """Human-facing production orchestration over existing Business OS controls."""

    def __init__(self, bridge: ProductionReadBridge, *, expected_schema_fingerprint: str):
        self.bridge = bridge
        self.expected_schema_fingerprint = expected_schema_fingerprint

    def dashboard(self) -> dict[str, Any]:
        fingerprint = self.bridge.assert_schema_current(self.expected_schema_fingerprint)
        portfolio = self.bridge.portfolio_view(expected_schema_fingerprint=fingerprint)
        inputs = self.bridge.planning_inputs()
        snapshot = portfolio.get("command_center")
        snapshot_hash = str(snapshot["snapshot_hash"]) if snapshot else None
        plan = build_portfolio_plan(
            schema_fingerprint=fingerprint,
            command_center_snapshot_hash=snapshot_hash,
            planning_inputs=inputs,
        )
        return {
            "schema_fingerprint": fingerprint,
            "command_center": snapshot,
            "businesses": portfolio["businesses"],
            "pending_approvals": portfolio["pending_approvals"],
            "planning": plan,
        }

    def propose_objective(self, text: str, *, requested_by: str, priority: int = 80) -> dict[str, Any]:
        objective = _clean_text(text)
        principal = _clean_text(requested_by)
        if not objective:
            raise CommandCenterError("objective text is required")
        if not principal:
            raise CommandCenterError("requesting human principal is required")
        if not isinstance(priority, int) or priority < 0 or priority > 100:
            raise CommandCenterError("priority must be an integer from 0 to 100")

        fingerprint = self.bridge.assert_schema_current(self.expected_schema_fingerprint)
        inputs = self.bridge.planning_inputs()
        role_key, goal_type = _route_role(objective)
        active = [
            row for row in inputs["agents"]
            if row.get("status") == "ACTIVE" and row.get("role_key") == role_key
        ]
        if len(active) != 1:
            raise CommandCenterError(f"expected exactly one active agent for role {role_key}")

        action_class = _possible_action_class(objective)
        proposal_core = {
            "objective": objective,
            "requested_by": principal,
            "priority": priority,
            "target_role": role_key,
            "target_agent_id": active[0]["agent_id"],
            "goal_type": goal_type,
            "possible_action_class": action_class,
            "requires_human_approval_for_possible_action": action_class in MANDATORY_HUMAN_ACTION_CLASSES,
            "business_refs": _business_refs(objective, self.bridge.businesses()),
            "schema_fingerprint": fingerprint,
            "constraints": {
                "command_center_source": "CEO_COMMAND_CENTER",
                "planning_only_until_activated": True,
                "no_external_write_without_governance": True,
                "no_money_movement_without_human_approval": True,
                "no_production_change_without_human_approval": True,
            },
            "evidence_requirements": [
                "Evidence must support completion claims.",
                "Consequential action requests must use the existing governance/approval path.",
                "Independent verification remains required where the bound workflow requires it.",
            ],
        }
        return {
            **proposal_core,
            "objective_hash": _sha(proposal_core),
            "status": "PROPOSED",
        }

    def activate_objective(
        self,
        proposal: Mapping[str, Any],
        *,
        human_principal: str,
        write_execute: WriteExecutor,
    ) -> dict[str, Any]:
        principal = _clean_text(human_principal)
        if not principal:
            raise CommandCenterError("objective activation requires a HUMAN principal")
        if proposal.get("status") != "PROPOSED":
            raise CommandCenterError("only PROPOSED objectives may be activated")
        if proposal.get("requested_by") != principal:
            raise CommandCenterError("activating principal must match the requesting human")

        supplied_hash = str(proposal.get("objective_hash", ""))
        core = {
            key: proposal[key]
            for key in (
                "objective",
                "requested_by",
                "priority",
                "target_role",
                "target_agent_id",
                "goal_type",
                "possible_action_class",
                "requires_human_approval_for_possible_action",
                "business_refs",
                "schema_fingerprint",
                "constraints",
                "evidence_requirements",
            )
        }
        if supplied_hash != _sha(core):
            raise CommandCenterError("objective proposal hash mismatch")

        live_fingerprint = self.bridge.assert_schema_current(self.expected_schema_fingerprint)
        if proposal.get("schema_fingerprint") != live_fingerprint:
            raise CommandCenterError("objective proposal is bound to a stale production schema")

        constraints = dict(proposal["constraints"])
        constraints.update(
            {
                "objective_hash": supplied_hash,
                "activated_by_human": principal,
                "possible_action_class": proposal["possible_action_class"],
                "requires_human_approval_for_possible_action": proposal[
                    "requires_human_approval_for_possible_action"
                ],
                "business_refs": list(proposal["business_refs"]),
            }
        )
        rows = write_execute(
            ACTIVATE_GOAL_SQL,
            (
                proposal["target_agent_id"],
                proposal["goal_type"],
                proposal["objective"],
                proposal["priority"],
                _canonical(constraints),
                _canonical(proposal["evidence_requirements"]),
            ),
        )
        materialized = [dict(row) for row in rows]
        if len(materialized) != 1 or materialized[0].get("status") != "PENDING":
            raise CommandCenterError("production goal activation did not return one PENDING goal")
        return {
            "objective_hash": supplied_hash,
            "activated_by": principal,
            "goal": materialized[0],
        }

    def decide_approval(
        self,
        *,
        request_key: str,
        intent_hash: str,
        decision: str,
        human_principal: str,
        reason: str,
        read_execute: ReadExecutor,
        write_execute: WriteExecutor,
    ) -> dict[str, Any]:
        key = _clean_text(request_key)
        expected_intent = _clean_text(intent_hash)
        principal = _clean_text(human_principal)
        explanation = _clean_text(reason)
        decision = _clean_text(decision).upper()
        if decision not in {"APPROVE", "REJECT"}:
            raise CommandCenterError("approval decision must be APPROVE or REJECT")
        if not key or not expected_intent or not principal or not explanation:
            raise CommandCenterError("approval decision requires request, intent, human, and reason")

        rows = [dict(row) for row in read_execute(APPROVAL_LOOKUP_SQL, (key,))]
        if len(rows) != 1:
            raise CommandCenterError("approval request is missing or non-unique")
        request = rows[0]
        if request.get("status") != "PENDING":
            raise CommandCenterError("approval request is not PENDING")
        if request.get("intent_hash") != expected_intent:
            raise CommandCenterError("approval intent hash mismatch")

        decided = [
            dict(row)
            for row in write_execute(
                APPROVAL_DECIDE_SQL,
                (key, decision, principal, explanation),
            )
        ]
        if len(decided) != 1:
            raise CommandCenterError("approval decision did not return exactly one receipt")
        expected_status = "APPROVED" if decision == "APPROVE" else "REJECTED"
        if decided[0].get("status") != expected_status:
            raise CommandCenterError("approval decision returned an unexpected status")
        return {
            "request_key": key,
            "intent_hash": expected_intent,
            "decision": decision,
            "decided_by": principal,
            "receipt": decided[0],
        }
