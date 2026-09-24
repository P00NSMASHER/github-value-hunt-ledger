"""Runtime governance for AI Business OS.

Deterministic permission boundary for tool allowlists, budgets, independent
approvals, append-only audit records and global/per-agent kill switches.
It decides whether an action may be attempted; it never performs the external
action itself.
"""
from __future__ import annotations

import contextlib
import dataclasses
import fnmatch
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


RISK_LEVELS = {
    "READ",
    "LOW_RISK_WRITE",
    "EXTERNAL_COMMUNICATION",
    "PRODUCTION",
    "FINANCIAL",
    "LEGAL",
    "DESTRUCTIVE",
}
MODES = {"ALLOW", "APPROVAL", "DENY"}
APPROVER_ROLES = {"HUMAN", "INTEGRATOR", "ADMIN"}
KILL_ACTOR_ROLES = {"SYSTEM", "HUMAN", "INTEGRATOR", "ADMIN"}
KILL_RELEASE_ROLES = {"INTEGRATOR", "ADMIN"}


class GovernanceError(ValueError):
    pass


@dataclasses.dataclass(frozen=True)
class AgentPolicy:
    agent_id: str
    allowed_tools: tuple[str, ...]
    risk_modes: dict[str, str]
    daily_budget_usd: float
    max_action_cost_usd: float
    updated_at: float


@dataclasses.dataclass(frozen=True)
class AuthorizationDecision:
    request_id: str
    state: str
    reasons: tuple[str, ...]
    budget_remaining_usd: float | None
    receipt_id: str | None = None


@dataclasses.dataclass(frozen=True)
class ApprovalReceipt:
    request_id: str
    approver_id: str
    approver_role: str
    state: str
    reason: str
    authorization_receipt_id: str | None
    created_at: float


class GovernanceControlPlane:
    """SQLite-backed runtime governance gate.

    Invariants:
    - missing policy fails closed;
    - tools are allowlist-only;
    - requesting agents cannot approve their own requests;
    - approval rechecks current policy, kill switch and budget;
    - authorization receipts are the only point where budget is charged;
    - kill switches dominate normal policy;
    - audit events are append-only.
    """

    def __init__(self, db_path: str | Path = "ai_business_os.sqlite3") -> None:
        self.db_path = str(db_path)
        self._initialize()

    @contextlib.contextmanager
    def _connect(self):
        con = sqlite3.connect(self.db_path, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _initialize(self) -> None:
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS governance_policies (
                    agent_id TEXT PRIMARY KEY,
                    allowed_tools_json TEXT NOT NULL,
                    risk_modes_json TEXT NOT NULL,
                    daily_budget_usd REAL NOT NULL,
                    max_action_cost_usd REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    CHECK(daily_budget_usd >= 0.0),
                    CHECK(max_action_cost_usd >= 0.0)
                );

                CREATE TABLE IF NOT EXISTS governance_requests (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    action TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    estimated_cost_usd REAL NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    initial_state TEXT NOT NULL,
                    CHECK(estimated_cost_usd >= 0.0)
                );

                CREATE TABLE IF NOT EXISTS governance_authorizations (
                    receipt_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL UNIQUE REFERENCES governance_requests(id),
                    agent_id TEXT NOT NULL,
                    charged_usd REAL NOT NULL,
                    authorized_by TEXT NOT NULL,
                    authorized_at REAL NOT NULL,
                    CHECK(charged_usd >= 0.0)
                );

                CREATE TABLE IF NOT EXISTS governance_approvals (
                    request_id TEXT PRIMARY KEY REFERENCES governance_requests(id),
                    approver_id TEXT NOT NULL,
                    approver_role TEXT NOT NULL,
                    state TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    authorization_receipt_id TEXT,
                    created_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS governance_kill_switches (
                    scope TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    engaged INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    actor_role TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY(scope, scope_id)
                );

                CREATE TABLE IF NOT EXISTS governance_audit_log (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    request_id TEXT,
                    agent_id TEXT,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_governance_auth_agent_time
                    ON governance_authorizations(agent_id, authorized_at);
                CREATE INDEX IF NOT EXISTS idx_governance_audit_time
                    ON governance_audit_log(created_at, sequence);
                """
            )

    @staticmethod
    def safe_default_modes() -> dict[str, str]:
        return {
            "READ": "ALLOW",
            "LOW_RISK_WRITE": "ALLOW",
            "EXTERNAL_COMMUNICATION": "APPROVAL",
            "PRODUCTION": "APPROVAL",
            "FINANCIAL": "APPROVAL",
            "LEGAL": "APPROVAL",
            "DESTRUCTIVE": "DENY",
        }

    @staticmethod
    def _now(now: float | None = None) -> float:
        return time.time() if now is None else float(now)

    def set_policy(
        self,
        agent_id: str,
        *,
        allowed_tools: tuple[str, ...],
        risk_modes: dict[str, str] | None = None,
        daily_budget_usd: float = 25.0,
        max_action_cost_usd: float = 5.0,
        now: float | None = None,
    ) -> AgentPolicy:
        if not agent_id.strip():
            raise GovernanceError("agent_id cannot be empty")
        if not allowed_tools or any(not x.strip() for x in allowed_tools):
            raise GovernanceError("allowed_tools must contain non-empty patterns")
        daily_budget_usd = float(daily_budget_usd)
        max_action_cost_usd = float(max_action_cost_usd)
        if daily_budget_usd < 0 or max_action_cost_usd < 0:
            raise GovernanceError("budgets cannot be negative")

        modes = dict(self.safe_default_modes() if risk_modes is None else risk_modes)
        if set(modes) != RISK_LEVELS:
            missing = sorted(RISK_LEVELS - set(modes))
            extra = sorted(set(modes) - RISK_LEVELS)
            raise GovernanceError(
                f"risk_modes must cover exact risk set; missing={missing}, extra={extra}"
            )
        invalid = {k: v for k, v in modes.items() if v not in MODES}
        if invalid:
            raise GovernanceError(f"invalid policy mode(s): {invalid}")

        ts = self._now(now)
        tools = tuple(sorted(set(allowed_tools)))
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO governance_policies(
                    agent_id, allowed_tools_json, risk_modes_json,
                    daily_budget_usd, max_action_cost_usd, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    allowed_tools_json=excluded.allowed_tools_json,
                    risk_modes_json=excluded.risk_modes_json,
                    daily_budget_usd=excluded.daily_budget_usd,
                    max_action_cost_usd=excluded.max_action_cost_usd,
                    updated_at=excluded.updated_at
                """,
                (
                    agent_id,
                    json.dumps(tools),
                    json.dumps(modes, sort_keys=True),
                    daily_budget_usd,
                    max_action_cost_usd,
                    ts,
                ),
            )
            self._audit(
                con,
                "POLICY_SET",
                None,
                agent_id,
                {
                    "allowed_tools": tools,
                    "risk_modes": modes,
                    "daily_budget_usd": daily_budget_usd,
                    "max_action_cost_usd": max_action_cost_usd,
                },
                ts,
            )
        return self.get_policy(agent_id)

    def get_policy(self, agent_id: str) -> AgentPolicy:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM governance_policies WHERE agent_id=?", (agent_id,)
            ).fetchone()
        if row is None:
            raise KeyError(agent_id)
        return AgentPolicy(
            agent_id=row["agent_id"],
            allowed_tools=tuple(json.loads(row["allowed_tools_json"])),
            risk_modes=dict(json.loads(row["risk_modes_json"])),
            daily_budget_usd=float(row["daily_budget_usd"]),
            max_action_cost_usd=float(row["max_action_cost_usd"]),
            updated_at=float(row["updated_at"]),
        )

    def request_action(
        self,
        agent_id: str,
        tool: str,
        action: str,
        *,
        risk_level: str,
        estimated_cost_usd: float = 0.0,
        metadata: dict[str, Any] | None = None,
        request_id: str | None = None,
        now: float | None = None,
    ) -> AuthorizationDecision:
        risk_level = risk_level.upper().strip()
        if risk_level not in RISK_LEVELS:
            raise GovernanceError(f"unsupported risk_level: {risk_level}")
        if not tool.strip() or not action.strip():
            raise GovernanceError("tool and action must be non-empty")
        estimated_cost_usd = float(estimated_cost_usd)
        if estimated_cost_usd < 0:
            raise GovernanceError("estimated_cost_usd cannot be negative")

        ts = self._now(now)
        request_id = request_id or f"greq_{uuid.uuid4().hex}"
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            if con.execute(
                "SELECT 1 FROM governance_requests WHERE id=?", (request_id,)
            ).fetchone():
                raise GovernanceError("request_id already exists")

            state, reasons, remaining = self._evaluate(
                con,
                agent_id=agent_id,
                tool=tool,
                risk_level=risk_level,
                estimated_cost_usd=estimated_cost_usd,
                now=ts,
            )
            con.execute(
                """
                INSERT INTO governance_requests(
                    id, agent_id, tool, action, risk_level, estimated_cost_usd,
                    metadata_json, created_at, initial_state
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    agent_id,
                    tool,
                    action,
                    risk_level,
                    estimated_cost_usd,
                    json.dumps(metadata or {}, sort_keys=True),
                    ts,
                    state,
                ),
            )
            self._audit(
                con,
                "ACTION_REQUESTED",
                request_id,
                agent_id,
                {
                    "tool": tool,
                    "action": action,
                    "risk_level": risk_level,
                    "estimated_cost_usd": estimated_cost_usd,
                },
                ts,
            )

            receipt_id = None
            if state == "ALLOW":
                receipt_id = self._authorize(
                    con,
                    request_id,
                    agent_id,
                    estimated_cost_usd,
                    "POLICY",
                    ts,
                )
                self._audit(
                    con,
                    "ACTION_ALLOWED",
                    request_id,
                    agent_id,
                    {"receipt_id": receipt_id, "reasons": reasons},
                    ts,
                )
            elif state == "REQUIRE_APPROVAL":
                self._audit(
                    con,
                    "APPROVAL_REQUIRED",
                    request_id,
                    agent_id,
                    {"reasons": reasons},
                    ts,
                )
            else:
                self._audit(
                    con,
                    "ACTION_DENIED",
                    request_id,
                    agent_id,
                    {"reasons": reasons},
                    ts,
                )

        return AuthorizationDecision(
            request_id=request_id,
            state=state,
            reasons=tuple(reasons),
            budget_remaining_usd=remaining,
            receipt_id=receipt_id,
        )

    def approve(
        self,
        request_id: str,
        *,
        approver_id: str,
        approver_role: str,
        reason: str,
        now: float | None = None,
    ) -> ApprovalReceipt:
        approver_role = approver_role.upper().strip()
        if approver_role not in APPROVER_ROLES:
            raise PermissionError("approver_role must be HUMAN, INTEGRATOR or ADMIN")
        if not reason.strip():
            raise GovernanceError("approval reason cannot be empty")
        ts = self._now(now)

        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            request = con.execute(
                "SELECT * FROM governance_requests WHERE id=?", (request_id,)
            ).fetchone()
            if request is None:
                raise KeyError(request_id)
            if request["agent_id"] == approver_id:
                raise PermissionError("requesting agent cannot approve its own action")
            if request["initial_state"] != "REQUIRE_APPROVAL":
                raise GovernanceError("request is not awaiting approval")
            if con.execute(
                "SELECT 1 FROM governance_approvals WHERE request_id=?", (request_id,)
            ).fetchone():
                raise GovernanceError("request already has an approval decision")

            state, reasons, remaining = self._evaluate(
                con,
                agent_id=request["agent_id"],
                tool=request["tool"],
                risk_level=request["risk_level"],
                estimated_cost_usd=float(request["estimated_cost_usd"]),
                now=ts,
                approval_present=True,
            )
            if state != "ALLOW":
                con.execute(
                    """
                    INSERT INTO governance_approvals(
                        request_id, approver_id, approver_role, state, reason,
                        authorization_receipt_id, created_at
                    ) VALUES(?, ?, ?, 'DENIED', ?, NULL, ?)
                    """,
                    (request_id, approver_id, approver_role, reason.strip(), ts),
                )
                self._audit(
                    con,
                    "APPROVAL_BLOCKED",
                    request_id,
                    request["agent_id"],
                    {"approver_id": approver_id, "reasons": reasons},
                    ts,
                )
                return ApprovalReceipt(
                    request_id=request_id,
                    approver_id=approver_id,
                    approver_role=approver_role,
                    state="DENIED",
                    reason=reason.strip(),
                    authorization_receipt_id=None,
                    created_at=ts,
                )

            receipt_id = self._authorize(
                con,
                request_id,
                request["agent_id"],
                float(request["estimated_cost_usd"]),
                f"{approver_role}:{approver_id}",
                ts,
            )
            con.execute(
                """
                INSERT INTO governance_approvals(
                    request_id, approver_id, approver_role, state, reason,
                    authorization_receipt_id, created_at
                ) VALUES(?, ?, ?, 'APPROVED', ?, ?, ?)
                """,
                (
                    request_id,
                    approver_id,
                    approver_role,
                    reason.strip(),
                    receipt_id,
                    ts,
                ),
            )
            self._audit(
                con,
                "ACTION_APPROVED",
                request_id,
                request["agent_id"],
                {
                    "approver_id": approver_id,
                    "approver_role": approver_role,
                    "receipt_id": receipt_id,
                    "budget_remaining_usd": remaining,
                },
                ts,
            )

        return ApprovalReceipt(
            request_id=request_id,
            approver_id=approver_id,
            approver_role=approver_role,
            state="APPROVED",
            reason=reason.strip(),
            authorization_receipt_id=receipt_id,
            created_at=ts,
        )

    def deny(
        self,
        request_id: str,
        *,
        approver_id: str,
        approver_role: str,
        reason: str,
        now: float | None = None,
    ) -> ApprovalReceipt:
        approver_role = approver_role.upper().strip()
        if approver_role not in APPROVER_ROLES:
            raise PermissionError("invalid approver role")
        if not reason.strip():
            raise GovernanceError("denial reason cannot be empty")
        ts = self._now(now)
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            request = con.execute(
                "SELECT * FROM governance_requests WHERE id=?", (request_id,)
            ).fetchone()
            if request is None:
                raise KeyError(request_id)
            if request["agent_id"] == approver_id:
                raise PermissionError("requesting agent cannot decide its own request")
            if request["initial_state"] != "REQUIRE_APPROVAL":
                raise GovernanceError("request is not awaiting approval")
            if con.execute(
                "SELECT 1 FROM governance_approvals WHERE request_id=?", (request_id,)
            ).fetchone():
                raise GovernanceError("request already has an approval decision")
            con.execute(
                """
                INSERT INTO governance_approvals(
                    request_id, approver_id, approver_role, state, reason,
                    authorization_receipt_id, created_at
                ) VALUES(?, ?, ?, 'DENIED', ?, NULL, ?)
                """,
                (request_id, approver_id, approver_role, reason.strip(), ts),
            )
            self._audit(
                con,
                "ACTION_DENIED_BY_APPROVER",
                request_id,
                request["agent_id"],
                {"approver_id": approver_id, "reason": reason.strip()},
                ts,
            )
        return ApprovalReceipt(
            request_id=request_id,
            approver_id=approver_id,
            approver_role=approver_role,
            state="DENIED",
            reason=reason.strip(),
            authorization_receipt_id=None,
            created_at=ts,
        )

    def engage_kill_switch(
        self,
        *,
        scope: str = "GLOBAL",
        scope_id: str = "*",
        reason: str,
        actor_id: str,
        actor_role: str,
        now: float | None = None,
    ) -> None:
        self._set_kill_switch(
            scope=scope,
            scope_id=scope_id,
            engaged=True,
            reason=reason,
            actor_id=actor_id,
            actor_role=actor_role,
            now=now,
        )

    def release_kill_switch(
        self,
        *,
        scope: str = "GLOBAL",
        scope_id: str = "*",
        reason: str,
        actor_id: str,
        actor_role: str,
        now: float | None = None,
    ) -> None:
        if actor_role.upper().strip() not in KILL_RELEASE_ROLES:
            raise PermissionError("kill switch release requires INTEGRATOR or ADMIN")
        self._set_kill_switch(
            scope=scope,
            scope_id=scope_id,
            engaged=False,
            reason=reason,
            actor_id=actor_id,
            actor_role=actor_role,
            now=now,
        )

    def _set_kill_switch(
        self,
        *,
        scope: str,
        scope_id: str,
        engaged: bool,
        reason: str,
        actor_id: str,
        actor_role: str,
        now: float | None,
    ) -> None:
        scope = scope.upper().strip()
        actor_role = actor_role.upper().strip()
        if scope not in {"GLOBAL", "AGENT"}:
            raise GovernanceError("kill switch scope must be GLOBAL or AGENT")
        if scope == "GLOBAL":
            scope_id = "*"
        if not scope_id.strip() or not reason.strip() or not actor_id.strip():
            raise GovernanceError("scope_id, reason and actor_id must be non-empty")
        if actor_role not in KILL_ACTOR_ROLES:
            raise PermissionError("actor is not allowed to change kill switch state")
        ts = self._now(now)
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO governance_kill_switches(
                    scope, scope_id, engaged, reason, actor_id, actor_role, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scope, scope_id) DO UPDATE SET
                    engaged=excluded.engaged,
                    reason=excluded.reason,
                    actor_id=excluded.actor_id,
                    actor_role=excluded.actor_role,
                    updated_at=excluded.updated_at
                """,
                (
                    scope,
                    scope_id,
                    1 if engaged else 0,
                    reason.strip(),
                    actor_id,
                    actor_role,
                    ts,
                ),
            )
            self._audit(
                con,
                "KILL_SWITCH_ENGAGED" if engaged else "KILL_SWITCH_RELEASED",
                None,
                scope_id if scope == "AGENT" else None,
                {
                    "scope": scope,
                    "scope_id": scope_id,
                    "reason": reason.strip(),
                    "actor_id": actor_id,
                    "actor_role": actor_role,
                },
                ts,
            )

    def budget_used(self, agent_id: str, *, now: float | None = None) -> float:
        ts = self._now(now)
        start, end = _utc_day_bounds(ts)
        with self._connect() as con:
            value = con.execute(
                """
                SELECT COALESCE(SUM(charged_usd), 0.0)
                FROM governance_authorizations
                WHERE agent_id=? AND authorized_at>=? AND authorized_at<?
                """,
                (agent_id, start, end),
            ).fetchone()[0]
        return float(value)

    def audit_log(self) -> tuple[dict[str, Any], ...]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM governance_audit_log ORDER BY sequence"
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            result.append(item)
        return tuple(result)

    def _evaluate(
        self,
        con: sqlite3.Connection,
        *,
        agent_id: str,
        tool: str,
        risk_level: str,
        estimated_cost_usd: float,
        now: float,
        approval_present: bool = False,
    ) -> tuple[str, list[str], float | None]:
        if self._kill_engaged(con, agent_id):
            return "DENY", ["kill switch engaged"], None

        row = con.execute(
            "SELECT * FROM governance_policies WHERE agent_id=?", (agent_id,)
        ).fetchone()
        if row is None:
            return "DENY", ["no policy registered for agent"], None

        allowed_tools = tuple(json.loads(row["allowed_tools_json"]))
        remaining = self._remaining_budget(con, row, now)
        if not any(fnmatch.fnmatchcase(tool, p) for p in allowed_tools):
            return "DENY", ["tool is not allowlisted"], remaining
        if estimated_cost_usd > float(row["max_action_cost_usd"]):
            return "DENY", ["estimated action cost exceeds per-action cap"], remaining
        if estimated_cost_usd > remaining + 1e-12:
            return "DENY", ["daily budget would be exceeded"], remaining

        mode = dict(json.loads(row["risk_modes_json"]))[risk_level]
        if mode == "DENY":
            return "DENY", [f"policy denies {risk_level}"], remaining
        if mode == "APPROVAL" and not approval_present:
            return "REQUIRE_APPROVAL", [f"policy requires approval for {risk_level}"], remaining
        return "ALLOW", ["policy conditions satisfied"], remaining - estimated_cost_usd

    def _remaining_budget(
        self, con: sqlite3.Connection, policy_row: sqlite3.Row, now: float
    ) -> float:
        start, end = _utc_day_bounds(now)
        used = float(
            con.execute(
                """
                SELECT COALESCE(SUM(charged_usd), 0.0)
                FROM governance_authorizations
                WHERE agent_id=? AND authorized_at>=? AND authorized_at<?
                """,
                (policy_row["agent_id"], start, end),
            ).fetchone()[0]
        )
        return max(0.0, float(policy_row["daily_budget_usd"]) - used)

    @staticmethod
    def _kill_engaged(con: sqlite3.Connection, agent_id: str) -> bool:
        return bool(
            con.execute(
                """
                SELECT 1 FROM governance_kill_switches
                WHERE engaged=1 AND (
                    (scope='GLOBAL' AND scope_id='*') OR
                    (scope='AGENT' AND scope_id=?)
                )
                LIMIT 1
                """,
                (agent_id,),
            ).fetchone()
        )

    @staticmethod
    def _authorize(
        con: sqlite3.Connection,
        request_id: str,
        agent_id: str,
        charged_usd: float,
        authorized_by: str,
        now: float,
    ) -> str:
        receipt_id = f"gauth_{uuid.uuid4().hex}"
        con.execute(
            """
            INSERT INTO governance_authorizations(
                receipt_id, request_id, agent_id, charged_usd,
                authorized_by, authorized_at
            ) VALUES(?, ?, ?, ?, ?, ?)
            """,
            (receipt_id, request_id, agent_id, charged_usd, authorized_by, now),
        )
        return receipt_id

    @staticmethod
    def _audit(
        con: sqlite3.Connection,
        event_type: str,
        request_id: str | None,
        agent_id: str | None,
        payload: dict[str, Any],
        now: float,
    ) -> None:
        con.execute(
            """
            INSERT INTO governance_audit_log(
                event_type, request_id, agent_id, payload_json, created_at
            ) VALUES(?, ?, ?, ?, ?)
            """,
            (
                event_type,
                request_id,
                agent_id,
                json.dumps(payload, sort_keys=True),
                now,
            ),
        )


def _utc_day_bounds(timestamp: float) -> tuple[float, float]:
    day = int(timestamp // 86400)
    start = float(day * 86400)
    return start, start + 86400.0
