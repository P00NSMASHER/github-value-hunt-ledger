"""Fail-closed runtime governance for the AI Business OS.

This module does not execute tools. It decides whether one exact requested action is allowed,
denied, or requires approval. Approvals are bound to an immutable intent hash and are single-use.
High-consequence action classes require human approval by default.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from typing import Any, Dict, Iterable, Optional, Set

from ai_business_os.persistent_agents.runtime import AgentRuntime


ACTION_CLASSES = {
    "READ",
    "INTERNAL_WRITE",
    "EXTERNAL_WRITE",
    "PRODUCTION_CHANGE",
    "MONEY_MOVEMENT",
    "DESTRUCTIVE",
    "POLICY_CHANGE",
}

DEFAULT_HUMAN_APPROVAL_CLASSES = {
    "EXTERNAL_WRITE",
    "PRODUCTION_CHANGE",
    "MONEY_MOVEMENT",
    "DESTRUCTIVE",
    "POLICY_CHANGE",
}


def _now() -> float:
    return time.time()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


class GovernanceError(ValueError):
    """Raised when governance configuration or authorization invariants are violated."""


class GovernanceControlPlane:
    """Permission, budget, approval, audit, and kill-switch control plane."""

    def __init__(self, runtime: AgentRuntime):
        self.runtime = runtime
        self._migrate()

    def _migrate(self) -> None:
        self.runtime.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS governance_state (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                global_kill_switch INTEGER NOT NULL DEFAULT 0,
                reason TEXT,
                updated_by_principal TEXT,
                evidence_hash TEXT,
                updated_at REAL NOT NULL
            );

            INSERT OR IGNORE INTO governance_state(
                id, global_kill_switch, updated_at
            ) VALUES (1, 0, 0);

            CREATE TABLE IF NOT EXISTS governance_agent_state (
                agent_id TEXT PRIMARY KEY REFERENCES agents(id),
                disabled INTEGER NOT NULL DEFAULT 0,
                reason TEXT,
                updated_by_principal TEXT,
                evidence_hash TEXT,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS governance_policies (
                agent_id TEXT PRIMARY KEY REFERENCES agents(id),
                allowed_classes_json TEXT NOT NULL,
                denied_action_keys_json TEXT NOT NULL,
                allowed_action_keys_json TEXT NOT NULL,
                human_approval_classes_json TEXT NOT NULL,
                max_actions_per_window INTEGER,
                window_seconds REAL NOT NULL,
                max_cost_units_per_window REAL,
                max_money_cents_per_window INTEGER,
                version INTEGER NOT NULL,
                policy_hash TEXT NOT NULL,
                updated_by_principal TEXT NOT NULL,
                evidence_hash TEXT NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS governance_action_requests (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL REFERENCES agents(id),
                action_key TEXT NOT NULL,
                action_class TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                intent_hash TEXT NOT NULL UNIQUE,
                cost_units REAL NOT NULL DEFAULT 0,
                amount_cents INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS governance_approvals (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL REFERENCES governance_action_requests(id),
                intent_hash TEXT NOT NULL,
                approver_principal TEXT NOT NULL,
                approver_kind TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                evidence_hash TEXT NOT NULL,
                expires_at REAL NOT NULL,
                consumed_at REAL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS governance_decisions (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL REFERENCES governance_action_requests(id),
                agent_id TEXT NOT NULL REFERENCES agents(id),
                intent_hash TEXT NOT NULL,
                policy_hash TEXT,
                decision TEXT NOT NULL,
                reason TEXT NOT NULL,
                approval_id TEXT REFERENCES governance_approvals(id),
                receipt_hash TEXT NOT NULL UNIQUE,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS governance_consumption (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL REFERENCES governance_action_requests(id),
                agent_id TEXT NOT NULL REFERENCES agents(id),
                action_class TEXT NOT NULL,
                cost_units REAL NOT NULL,
                amount_cents INTEGER NOT NULL,
                receipt_hash TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_governance_requests_agent
                ON governance_action_requests(agent_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_governance_consumption_agent
                ON governance_consumption(agent_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_governance_approvals_request
                ON governance_approvals(request_id, status);
            """
        )
        self.runtime.conn.commit()

    def set_agent_policy(
        self,
        agent_id: str,
        *,
        allowed_classes: Iterable[str],
        updated_by_principal: str,
        principal_kind: str,
        evidence: Dict[str, Any],
        denied_action_keys: Iterable[str] = (),
        allowed_action_keys: Iterable[str] = (),
        human_approval_classes: Iterable[str] = DEFAULT_HUMAN_APPROVAL_CLASSES,
        max_actions_per_window: Optional[int] = None,
        window_seconds: float = 86400.0,
        max_cost_units_per_window: Optional[float] = None,
        max_money_cents_per_window: Optional[int] = None,
    ) -> Dict[str, Any]:
        self.runtime._require_agent(agent_id)
        if principal_kind != "HUMAN":
            raise GovernanceError("governance policy changes require a HUMAN principal")
        if not updated_by_principal.strip() or not evidence:
            raise GovernanceError("policy change requires principal identity and evidence")

        allowed = self._normalize_classes(allowed_classes)
        approval_classes = self._normalize_classes(human_approval_classes)
        if not approval_classes <= allowed:
            raise GovernanceError("approval classes must be a subset of allowed classes")
        denied = sorted({str(x).strip() for x in denied_action_keys if str(x).strip()})
        allowlist = sorted({str(x).strip() for x in allowed_action_keys if str(x).strip()})

        window_seconds = float(window_seconds)
        if not math.isfinite(window_seconds) or window_seconds <= 0:
            raise GovernanceError("window_seconds must be finite and positive")
        if max_actions_per_window is not None and max_actions_per_window < 0:
            raise GovernanceError("max_actions_per_window cannot be negative")
        if max_cost_units_per_window is not None:
            max_cost_units_per_window = float(max_cost_units_per_window)
            if not math.isfinite(max_cost_units_per_window) or max_cost_units_per_window < 0:
                raise GovernanceError("max_cost_units_per_window must be finite and non-negative")
        if max_money_cents_per_window is not None and max_money_cents_per_window < 0:
            raise GovernanceError("max_money_cents_per_window cannot be negative")

        prior = self.runtime.conn.execute(
            "SELECT version FROM governance_policies WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        version = int(prior["version"]) + 1 if prior else 1
        policy_payload = {
            "agent_id": agent_id,
            "allowed_classes": sorted(allowed),
            "denied_action_keys": denied,
            "allowed_action_keys": allowlist,
            "human_approval_classes": sorted(approval_classes),
            "max_actions_per_window": max_actions_per_window,
            "window_seconds": window_seconds,
            "max_cost_units_per_window": max_cost_units_per_window,
            "max_money_cents_per_window": max_money_cents_per_window,
            "version": version,
        }
        policy_hash = _sha(policy_payload)
        evidence_hash = _sha(evidence)
        self.runtime.conn.execute(
            """
            INSERT INTO governance_policies(
                agent_id, allowed_classes_json, denied_action_keys_json,
                allowed_action_keys_json, human_approval_classes_json,
                max_actions_per_window, window_seconds, max_cost_units_per_window,
                max_money_cents_per_window, version, policy_hash,
                updated_by_principal, evidence_hash, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_id) DO UPDATE SET
                allowed_classes_json=excluded.allowed_classes_json,
                denied_action_keys_json=excluded.denied_action_keys_json,
                allowed_action_keys_json=excluded.allowed_action_keys_json,
                human_approval_classes_json=excluded.human_approval_classes_json,
                max_actions_per_window=excluded.max_actions_per_window,
                window_seconds=excluded.window_seconds,
                max_cost_units_per_window=excluded.max_cost_units_per_window,
                max_money_cents_per_window=excluded.max_money_cents_per_window,
                version=excluded.version,
                policy_hash=excluded.policy_hash,
                updated_by_principal=excluded.updated_by_principal,
                evidence_hash=excluded.evidence_hash,
                updated_at=excluded.updated_at
            """,
            (
                agent_id,
                _json(sorted(allowed)),
                _json(denied),
                _json(allowlist),
                _json(sorted(approval_classes)),
                max_actions_per_window,
                window_seconds,
                max_cost_units_per_window,
                max_money_cents_per_window,
                version,
                policy_hash,
                updated_by_principal,
                evidence_hash,
                _now(),
            ),
        )
        self.runtime.conn.commit()
        self.runtime.append_event(
            agent_id,
            "GOVERNANCE_POLICY_SET",
            {
                "version": version,
                "policy_hash": policy_hash,
                "updated_by_principal": updated_by_principal,
                "evidence_hash": evidence_hash,
            },
        )
        return self.get_agent_policy(agent_id)

    def request_action(
        self,
        agent_id: str,
        *,
        action_key: str,
        action_class: str,
        parameters: Dict[str, Any],
        cost_units: float = 0.0,
        amount_cents: int = 0,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.runtime._require_agent(agent_id)
        action_key = action_key.strip()
        action_class = action_class.strip().upper()
        if not action_key:
            raise GovernanceError("action_key must be non-empty")
        if action_class not in ACTION_CLASSES:
            raise GovernanceError(f"unsupported action class: {action_class}")
        if not isinstance(parameters, dict):
            raise GovernanceError("parameters must be an object")
        cost_units = float(cost_units)
        if not math.isfinite(cost_units) or cost_units < 0:
            raise GovernanceError("cost_units must be finite and non-negative")
        if not isinstance(amount_cents, int) or amount_cents < 0:
            raise GovernanceError("amount_cents must be a non-negative integer")
        if action_class != "MONEY_MOVEMENT" and amount_cents != 0:
            raise GovernanceError("amount_cents is only valid for MONEY_MOVEMENT")

        request_id = request_id or f"actreq_{uuid.uuid4().hex}"
        payload = {
            "request_id": request_id,
            "agent_id": agent_id,
            "action_key": action_key,
            "action_class": action_class,
            "parameters": parameters,
            "cost_units": cost_units,
            "amount_cents": amount_cents,
        }
        intent_hash = _sha(payload)
        self.runtime.conn.execute(
            """
            INSERT INTO governance_action_requests(
                id, agent_id, action_key, action_class, parameters_json,
                intent_hash, cost_units, amount_cents, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
            """,
            (
                request_id,
                agent_id,
                action_key,
                action_class,
                _json(parameters),
                intent_hash,
                cost_units,
                amount_cents,
                _now(),
            ),
        )
        self.runtime.conn.commit()
        return self.evaluate_request(request_id)

    def evaluate_request(
        self,
        request_id: str,
        *,
        approval_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        request = self._require_request(request_id)
        policy = self._require_policy(str(request["agent_id"]))

        if self._global_killed():
            return self._decision(request, policy, "DENY", "global kill switch is active")
        if self._agent_disabled(str(request["agent_id"])):
            return self._decision(request, policy, "DENY", "agent kill switch is active")

        allowed_classes = set(json.loads(policy["allowed_classes_json"]))
        if request["action_class"] not in allowed_classes:
            return self._decision(request, policy, "DENY", "action class is not allowed")

        denied_keys = set(json.loads(policy["denied_action_keys_json"]))
        if request["action_key"] in denied_keys:
            return self._decision(request, policy, "DENY", "action key is explicitly denied")

        allowed_keys = set(json.loads(policy["allowed_action_keys_json"]))
        if allowed_keys and request["action_key"] not in allowed_keys:
            return self._decision(request, policy, "DENY", "action key is not on the allowlist")

        budget_reason = self._budget_violation(request, policy)
        if budget_reason:
            return self._decision(request, policy, "DENY", budget_reason)

        approval_classes = set(json.loads(policy["human_approval_classes_json"]))
        if request["action_class"] in approval_classes:
            if approval_id is None:
                return self._decision(
                    request,
                    policy,
                    "REQUIRE_APPROVAL",
                    "human approval required for this action class",
                )
            approval = self._validate_approval(request, approval_id)
            return self._allow_and_consume(request, policy, approval_id=approval["id"])

        return self._allow_and_consume(request, policy, approval_id=None)

    def approve_request(
        self,
        request_id: str,
        *,
        approver_principal: str,
        approver_kind: str,
        evidence: Dict[str, Any],
        ttl_seconds: float = 3600.0,
    ) -> Dict[str, Any]:
        request = self._require_request(request_id)
        if approver_kind != "HUMAN":
            raise GovernanceError("high-consequence approvals require a HUMAN principal")
        if not approver_principal.strip() or not evidence:
            raise GovernanceError("approval requires human identity and evidence")
        ttl_seconds = float(ttl_seconds)
        if not math.isfinite(ttl_seconds) or ttl_seconds <= 0:
            raise GovernanceError("approval ttl must be finite and positive")

        # Approval is valid only if the current policy still says this class is allowed and
        # approval-gated. This prevents approval from resurrecting a now-denied action.
        policy = self._require_policy(str(request["agent_id"]))
        if request["action_class"] not in set(json.loads(policy["allowed_classes_json"])):
            raise GovernanceError("cannot approve an action class denied by current policy")
        if request["action_class"] not in set(json.loads(policy["human_approval_classes_json"])):
            raise GovernanceError("this action class does not require a human approval ticket")

        approval_id = f"approval_{uuid.uuid4().hex}"
        evidence_hash = _sha(
            {
                "request_id": request_id,
                "intent_hash": request["intent_hash"],
                "approver_principal": approver_principal,
                "evidence": evidence,
            }
        )
        self.runtime.conn.execute(
            """
            INSERT INTO governance_approvals(
                id, request_id, intent_hash, approver_principal, approver_kind,
                evidence_json, evidence_hash, expires_at, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
            """,
            (
                approval_id,
                request_id,
                request["intent_hash"],
                approver_principal,
                approver_kind,
                _json(evidence),
                evidence_hash,
                _now() + ttl_seconds,
                _now(),
            ),
        )
        self.runtime.conn.commit()
        return {
            "id": approval_id,
            "request_id": request_id,
            "intent_hash": request["intent_hash"],
            "approver_principal": approver_principal,
            "approver_kind": approver_kind,
            "evidence_hash": evidence_hash,
        }

    def set_global_kill_switch(
        self,
        *,
        enabled: bool,
        principal: str,
        principal_kind: str,
        reason: str,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        if principal_kind != "HUMAN":
            raise GovernanceError("global kill-switch changes require a HUMAN principal")
        if not principal.strip() or not reason.strip() or not evidence:
            raise GovernanceError("kill-switch change requires principal, reason, and evidence")
        evidence_hash = _sha(evidence)
        self.runtime.conn.execute(
            """
            UPDATE governance_state
            SET global_kill_switch = ?, reason = ?, updated_by_principal = ?,
                evidence_hash = ?, updated_at = ?
            WHERE id = 1
            """,
            (int(bool(enabled)), reason, principal, evidence_hash, _now()),
        )
        self.runtime.conn.commit()
        return {
            "enabled": bool(enabled),
            "reason": reason,
            "updated_by_principal": principal,
            "evidence_hash": evidence_hash,
        }

    def set_agent_kill_switch(
        self,
        agent_id: str,
        *,
        enabled: bool,
        principal: str,
        principal_kind: str,
        reason: str,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        self.runtime._require_agent(agent_id)
        if principal_kind != "HUMAN":
            raise GovernanceError("agent kill-switch changes require a HUMAN principal")
        if not principal.strip() or not reason.strip() or not evidence:
            raise GovernanceError("kill-switch change requires principal, reason, and evidence")
        evidence_hash = _sha(evidence)
        self.runtime.conn.execute(
            """
            INSERT INTO governance_agent_state(
                agent_id, disabled, reason, updated_by_principal, evidence_hash, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_id) DO UPDATE SET
                disabled=excluded.disabled,
                reason=excluded.reason,
                updated_by_principal=excluded.updated_by_principal,
                evidence_hash=excluded.evidence_hash,
                updated_at=excluded.updated_at
            """,
            (
                agent_id,
                int(bool(enabled)),
                reason,
                principal,
                evidence_hash,
                _now(),
            ),
        )
        self.runtime.conn.commit()
        return {
            "agent_id": agent_id,
            "enabled": bool(enabled),
            "reason": reason,
            "updated_by_principal": principal,
            "evidence_hash": evidence_hash,
        }

    def get_agent_policy(self, agent_id: str) -> Dict[str, Any]:
        row = self._require_policy(agent_id)
        return {
            "agent_id": row["agent_id"],
            "allowed_classes": json.loads(row["allowed_classes_json"]),
            "denied_action_keys": json.loads(row["denied_action_keys_json"]),
            "allowed_action_keys": json.loads(row["allowed_action_keys_json"]),
            "human_approval_classes": json.loads(row["human_approval_classes_json"]),
            "max_actions_per_window": row["max_actions_per_window"],
            "window_seconds": row["window_seconds"],
            "max_cost_units_per_window": row["max_cost_units_per_window"],
            "max_money_cents_per_window": row["max_money_cents_per_window"],
            "version": row["version"],
            "policy_hash": row["policy_hash"],
            "updated_by_principal": row["updated_by_principal"],
            "evidence_hash": row["evidence_hash"],
            "updated_at": row["updated_at"],
        }

    def _allow_and_consume(
        self,
        request,
        policy,
        *,
        approval_id: Optional[str],
    ) -> Dict[str, Any]:
        # Recheck kill switches and budgets at final authorization to narrow the race window.
        if self._global_killed():
            return self._decision(request, policy, "DENY", "global kill switch is active")
        if self._agent_disabled(str(request["agent_id"])):
            return self._decision(request, policy, "DENY", "agent kill switch is active")
        budget_reason = self._budget_violation(request, policy)
        if budget_reason:
            return self._decision(request, policy, "DENY", budget_reason)

        decision = self._decision(
            request,
            policy,
            "ALLOW",
            "action authorized under current policy",
            approval_id=approval_id,
        )
        self.runtime.conn.execute(
            """
            INSERT INTO governance_consumption(
                id, request_id, agent_id, action_class, cost_units,
                amount_cents, receipt_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"consume_{uuid.uuid4().hex}",
                request["id"],
                request["agent_id"],
                request["action_class"],
                request["cost_units"],
                request["amount_cents"],
                decision["receipt_hash"],
                _now(),
            ),
        )
        if approval_id is not None:
            self.runtime.conn.execute(
                """
                UPDATE governance_approvals
                SET status = 'CONSUMED', consumed_at = ?
                WHERE id = ?
                """,
                (_now(), approval_id),
            )
        self.runtime.conn.execute(
            "UPDATE governance_action_requests SET status = 'AUTHORIZED' WHERE id = ?",
            (request["id"],),
        )
        self.runtime.conn.commit()
        return decision

    def _decision(
        self,
        request,
        policy,
        decision: str,
        reason: str,
        *,
        approval_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {
            "request_id": request["id"],
            "agent_id": request["agent_id"],
            "intent_hash": request["intent_hash"],
            "policy_hash": policy["policy_hash"] if policy is not None else None,
            "decision": decision,
            "reason": reason,
            "approval_id": approval_id,
        }
        receipt_hash = _sha(payload)
        decision_id = f"decision_{uuid.uuid4().hex}"
        self.runtime.conn.execute(
            """
            INSERT INTO governance_decisions(
                id, request_id, agent_id, intent_hash, policy_hash,
                decision, reason, approval_id, receipt_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                request["id"],
                request["agent_id"],
                request["intent_hash"],
                policy["policy_hash"] if policy is not None else None,
                decision,
                reason,
                approval_id,
                receipt_hash,
                _now(),
            ),
        )
        if decision == "DENY":
            self.runtime.conn.execute(
                "UPDATE governance_action_requests SET status = 'DENIED' WHERE id = ?",
                (request["id"],),
            )
        elif decision == "REQUIRE_APPROVAL":
            self.runtime.conn.execute(
                "UPDATE governance_action_requests SET status = 'AWAITING_APPROVAL' WHERE id = ?",
                (request["id"],),
            )
        self.runtime.conn.commit()
        self.runtime.append_event(
            str(request["agent_id"]),
            "GOVERNANCE_DECISION",
            {
                "request_id": request["id"],
                "decision": decision,
                "reason": reason,
                "receipt_hash": receipt_hash,
            },
        )
        return {
            "decision_id": decision_id,
            "request_id": request["id"],
            "intent_hash": request["intent_hash"],
            "decision": decision,
            "reason": reason,
            "approval_id": approval_id,
            "policy_hash": policy["policy_hash"] if policy is not None else None,
            "receipt_hash": receipt_hash,
        }

    def _validate_approval(self, request, approval_id: str):
        row = self.runtime.conn.execute(
            "SELECT * FROM governance_approvals WHERE id = ?",
            (approval_id,),
        ).fetchone()
        if row is None:
            raise GovernanceError("unknown approval")
        if row["request_id"] != request["id"]:
            raise GovernanceError("approval is bound to a different action request")
        if row["intent_hash"] != request["intent_hash"]:
            raise GovernanceError("approval intent hash does not match the request")
        if row["approver_kind"] != "HUMAN":
            raise GovernanceError("approval was not issued by a HUMAN principal")
        if row["status"] != "ACTIVE" or row["consumed_at"] is not None:
            raise GovernanceError("approval is not active")
        if float(row["expires_at"]) <= _now():
            raise GovernanceError("approval has expired")
        return row

    def _budget_violation(self, request, policy) -> Optional[str]:
        since = _now() - float(policy["window_seconds"])
        row = self.runtime.conn.execute(
            """
            SELECT COUNT(*) AS action_count,
                   COALESCE(SUM(cost_units), 0.0) AS cost_total,
                   COALESCE(SUM(amount_cents), 0) AS money_total
            FROM governance_consumption
            WHERE agent_id = ? AND created_at >= ?
            """,
            (request["agent_id"], since),
        ).fetchone()

        projected_actions = int(row["action_count"]) + 1
        projected_cost = float(row["cost_total"]) + float(request["cost_units"])
        projected_money = int(row["money_total"]) + int(request["amount_cents"])

        if (
            policy["max_actions_per_window"] is not None
            and projected_actions > int(policy["max_actions_per_window"])
        ):
            return "action-count budget would be exceeded"
        if (
            policy["max_cost_units_per_window"] is not None
            and projected_cost > float(policy["max_cost_units_per_window"]) + 1e-12
        ):
            return "cost-unit budget would be exceeded"
        if (
            policy["max_money_cents_per_window"] is not None
            and projected_money > int(policy["max_money_cents_per_window"])
        ):
            return "money-movement budget would be exceeded"
        return None

    def _global_killed(self) -> bool:
        row = self.runtime.conn.execute(
            "SELECT global_kill_switch FROM governance_state WHERE id = 1"
        ).fetchone()
        return bool(row["global_kill_switch"])

    def _agent_disabled(self, agent_id: str) -> bool:
        row = self.runtime.conn.execute(
            "SELECT disabled FROM governance_agent_state WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        return bool(row["disabled"]) if row else False

    def _normalize_classes(self, values: Iterable[str]) -> Set[str]:
        normalized = {str(v).strip().upper() for v in values if str(v).strip()}
        unsupported = normalized - ACTION_CLASSES
        if unsupported:
            raise GovernanceError(f"unsupported action classes: {sorted(unsupported)}")
        return normalized

    def _require_policy(self, agent_id: str):
        row = self.runtime.conn.execute(
            "SELECT * FROM governance_policies WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        if row is None:
            raise GovernanceError("agent has no governance policy; fail closed")
        return row

    def _require_request(self, request_id: str):
        row = self.runtime.conn.execute(
            "SELECT * FROM governance_action_requests WHERE id = ?",
            (request_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown governance action request: {request_id}")
        return row
