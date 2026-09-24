"""Durable runtime governance for AI Business OS.

Fail-closed authority boundary combining explicit grants, risk classes,
budgets, exact-request approvals, append-only audit records and a global
emergency kill switch.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


RISK_ORDER = {
    "READ": 0,
    "WRITE_LOW": 1,
    "CONSEQUENTIAL": 2,
    "DESTRUCTIVE": 3,
}


@dataclasses.dataclass(frozen=True)
class ActionRequest:
    agent_id: str
    role: str
    tool: str
    action: str
    risk: str
    estimated_cost_usd: float = 0.0
    budget_key: str = "default"
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)
    request_id: str = dataclasses.field(
        default_factory=lambda: f"req_{uuid.uuid4().hex}"
    )

    def __post_init__(self) -> None:
        if self.risk not in RISK_ORDER:
            raise ValueError(f"unsupported risk: {self.risk}")
        if self.estimated_cost_usd < 0:
            raise ValueError("estimated_cost_usd cannot be negative")
        for field_name in ("agent_id", "role", "tool", "action", "request_id"):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} cannot be empty")

    @property
    def sha256(self) -> str:
        return _sha(dataclasses.asdict(self))


@dataclasses.dataclass(frozen=True)
class GovernanceDecision:
    request_id: str
    request_sha256: str
    decision: str
    reason: str
    approval_id: str | None = None
    audit_id: str | None = None


class GovernanceEngine:
    """SQLite-backed authorization and audit control plane."""

    def __init__(self, db_path: str | Path = "ai_business_os.sqlite3") -> None:
        self.db_path = str(db_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path, timeout=30)
        con.row_factory = sqlite3.Row
        return con

    def _initialize(self) -> None:
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS governance_grants (
                    role TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    action TEXT NOT NULL,
                    max_risk TEXT NOT NULL,
                    PRIMARY KEY(role, tool, action)
                );

                CREATE TABLE IF NOT EXISTS governance_budgets (
                    budget_key TEXT PRIMARY KEY,
                    limit_usd REAL NOT NULL CHECK(limit_usd >= 0),
                    spent_usd REAL NOT NULL DEFAULT 0 CHECK(spent_usd >= 0),
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS governance_approvals (
                    approval_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    request_sha256 TEXT NOT NULL,
                    approver_id TEXT NOT NULL,
                    approved_at REAL NOT NULL,
                    expires_at REAL,
                    consumed_at REAL
                );

                CREATE TABLE IF NOT EXISTS governance_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS governance_audit (
                    audit_id TEXT PRIMARY KEY,
                    observed_at REAL NOT NULL,
                    request_id TEXT NOT NULL,
                    request_sha256 TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    action TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    estimated_cost_usd REAL NOT NULL,
                    budget_key TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    approval_id TEXT,
                    metadata_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS governance_spend (
                    spend_id TEXT PRIMARY KEY,
                    budget_key TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    request_sha256 TEXT NOT NULL,
                    amount_usd REAL NOT NULL CHECK(amount_usd >= 0),
                    recorded_at REAL NOT NULL,
                    receipt_ref TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_gov_audit_request
                    ON governance_audit(request_id, observed_at);
                """
            )
            con.execute(
                """
                INSERT OR IGNORE INTO governance_state(key, value, updated_at)
                VALUES('kill_switch', 'OFF', ?)
                """,
                (time.time(),),
            )

    def grant(
        self,
        role: str,
        tool: str,
        action: str,
        *,
        max_risk: str = "WRITE_LOW",
    ) -> None:
        if max_risk not in RISK_ORDER:
            raise ValueError(f"unsupported max_risk: {max_risk}")
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO governance_grants(role, tool, action, max_risk)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(role, tool, action)
                DO UPDATE SET max_risk=excluded.max_risk
                """,
                (role, tool, action, max_risk),
            )

    def revoke(self, role: str, tool: str, action: str) -> None:
        with self._connect() as con:
            con.execute(
                "DELETE FROM governance_grants WHERE role=? AND tool=? AND action=?",
                (role, tool, action),
            )

    def set_budget(
        self,
        budget_key: str,
        limit_usd: float,
        *,
        now: float | None = None,
    ) -> None:
        if limit_usd < 0:
            raise ValueError("limit_usd cannot be negative")
        ts = _now(now)
        with self._connect() as con:
            row = con.execute(
                "SELECT spent_usd FROM governance_budgets WHERE budget_key=?",
                (budget_key,),
            ).fetchone()
            spent = float(row["spent_usd"]) if row else 0.0
            if spent > float(limit_usd):
                raise ValueError("new limit cannot be below recorded spend")
            con.execute(
                """
                INSERT INTO governance_budgets(budget_key, limit_usd, spent_usd, updated_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(budget_key) DO UPDATE SET
                    limit_usd=excluded.limit_usd,
                    updated_at=excluded.updated_at
                """,
                (budget_key, float(limit_usd), spent, ts),
            )

    def budget_status(self, budget_key: str) -> dict[str, float]:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM governance_budgets WHERE budget_key=?",
                (budget_key,),
            ).fetchone()
        if row is None:
            raise KeyError(budget_key)
        limit = float(row["limit_usd"])
        spent = float(row["spent_usd"])
        return {
            "limit_usd": limit,
            "spent_usd": spent,
            "remaining_usd": max(0.0, limit - spent),
        }

    def set_kill_switch(
        self,
        enabled: bool,
        *,
        actor_id: str,
        now: float | None = None,
    ) -> None:
        if not actor_id.strip():
            raise ValueError("actor_id cannot be empty")
        with self._connect() as con:
            con.execute(
                """
                UPDATE governance_state
                SET value=?, updated_at=?
                WHERE key='kill_switch'
                """,
                ("ON" if enabled else "OFF", _now(now)),
            )

    def kill_switch_enabled(self) -> bool:
        with self._connect() as con:
            row = con.execute(
                "SELECT value FROM governance_state WHERE key='kill_switch'"
            ).fetchone()
        return row is None or row["value"] != "OFF"

    def approve(
        self,
        request: ActionRequest,
        *,
        approver_id: str,
        expires_at: float | None = None,
        now: float | None = None,
    ) -> str:
        if not approver_id.strip():
            raise ValueError("approver_id cannot be empty")
        ts = _now(now)
        if expires_at is not None and float(expires_at) <= ts:
            raise ValueError("approval expiry must be in the future")
        approval_id = f"approval_{uuid.uuid4().hex}"
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO governance_approvals(
                    approval_id, request_id, request_sha256, approver_id,
                    approved_at, expires_at, consumed_at
                ) VALUES(?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    approval_id,
                    request.request_id,
                    request.sha256,
                    approver_id,
                    ts,
                    expires_at,
                ),
            )
        return approval_id

    def authorize(
        self,
        request: ActionRequest,
        *,
        now: float | None = None,
    ) -> GovernanceDecision:
        ts = _now(now)

        if self.kill_switch_enabled():
            return self._audit(request, "DENY", "global kill switch is ON", ts)

        with self._connect() as con:
            grant = con.execute(
                """
                SELECT max_risk FROM governance_grants
                WHERE role=? AND tool=? AND action=?
                """,
                (request.role, request.tool, request.action),
            ).fetchone()

        if grant is None:
            return self._audit(
                request, "DENY", "no explicit grant for role/tool/action", ts
            )

        if RISK_ORDER[request.risk] > RISK_ORDER[grant["max_risk"]]:
            return self._audit(
                request,
                "DENY",
                f"request risk {request.risk} exceeds grant {grant['max_risk']}",
                ts,
            )

        budget_reason = self._budget_reason(request)
        if budget_reason is not None:
            return self._audit(request, "DENY", budget_reason, ts)

        approval_id = None
        if request.risk in {"CONSEQUENTIAL", "DESTRUCTIVE"}:
            approval = self._valid_approval(request, ts)
            if approval is None:
                return self._audit(
                    request,
                    "REQUIRE_APPROVAL",
                    f"{request.risk} actions require exact-request human approval",
                    ts,
                )
            approval_id = approval["approval_id"]
            self._consume_approval(approval_id, ts)

        return self._audit(
            request,
            "ALLOW",
            "explicit grant, risk, budget and approval requirements satisfied",
            ts,
            approval_id=approval_id,
        )

    def record_spend(
        self,
        request: ActionRequest,
        amount_usd: float,
        *,
        receipt_ref: str,
        now: float | None = None,
    ) -> str:
        if amount_usd < 0:
            raise ValueError("amount_usd cannot be negative")
        if not receipt_ref.strip():
            raise ValueError("receipt_ref cannot be empty")
        ts = _now(now)
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT * FROM governance_budgets WHERE budget_key=?",
                (request.budget_key,),
            ).fetchone()
            if row is None:
                con.rollback()
                raise PermissionError("no budget configured")
            new_spent = float(row["spent_usd"]) + float(amount_usd)
            if new_spent > float(row["limit_usd"]) + 1e-9:
                con.rollback()
                raise PermissionError("actual spend would exceed budget")
            spend_id = f"spend_{uuid.uuid4().hex}"
            con.execute(
                """
                INSERT INTO governance_spend(
                    spend_id, budget_key, request_id, request_sha256,
                    amount_usd, recorded_at, receipt_ref
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    spend_id,
                    request.budget_key,
                    request.request_id,
                    request.sha256,
                    float(amount_usd),
                    ts,
                    receipt_ref,
                ),
            )
            con.execute(
                """
                UPDATE governance_budgets
                SET spent_usd=?, updated_at=?
                WHERE budget_key=?
                """,
                (new_spent, ts, request.budget_key),
            )
            con.commit()
        return spend_id

    def audit_rows(self, request_id: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as con:
            if request_id is None:
                rows = con.execute(
                    "SELECT * FROM governance_audit ORDER BY observed_at, audit_id"
                ).fetchall()
            else:
                rows = con.execute(
                    """
                    SELECT * FROM governance_audit
                    WHERE request_id=?
                    ORDER BY observed_at, audit_id
                    """,
                    (request_id,),
                ).fetchall()
        return [
            {**dict(row), "metadata": json.loads(row["metadata_json"])}
            for row in rows
        ]

    def _budget_reason(self, request: ActionRequest) -> str | None:
        if request.estimated_cost_usd == 0:
            return None
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM governance_budgets WHERE budget_key=?",
                (request.budget_key,),
            ).fetchone()
        if row is None:
            return "paid action has no configured budget"
        remaining = float(row["limit_usd"]) - float(row["spent_usd"])
        if request.estimated_cost_usd > remaining + 1e-9:
            return (
                f"estimated cost USD {request.estimated_cost_usd:.2f} exceeds "
                f"remaining budget USD {remaining:.2f}"
            )
        return None

    def _valid_approval(
        self, request: ActionRequest, now: float
    ) -> sqlite3.Row | None:
        with self._connect() as con:
            return con.execute(
                """
                SELECT * FROM governance_approvals
                WHERE request_id=?
                  AND request_sha256=?
                  AND consumed_at IS NULL
                  AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY approved_at DESC
                LIMIT 1
                """,
                (request.request_id, request.sha256, now),
            ).fetchone()

    def _consume_approval(self, approval_id: str, now: float) -> None:
        with self._connect() as con:
            cur = con.execute(
                """
                UPDATE governance_approvals
                SET consumed_at=?
                WHERE approval_id=? AND consumed_at IS NULL
                """,
                (now, approval_id),
            )
            if cur.rowcount != 1:
                raise PermissionError("approval is no longer valid")

    def _audit(
        self,
        request: ActionRequest,
        decision: str,
        reason: str,
        now: float,
        *,
        approval_id: str | None = None,
    ) -> GovernanceDecision:
        audit_id = f"audit_{uuid.uuid4().hex}"
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO governance_audit(
                    audit_id, observed_at, request_id, request_sha256,
                    agent_id, role, tool, action, risk, estimated_cost_usd,
                    budget_key, decision, reason, approval_id, metadata_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    now,
                    request.request_id,
                    request.sha256,
                    request.agent_id,
                    request.role,
                    request.tool,
                    request.action,
                    request.risk,
                    float(request.estimated_cost_usd),
                    request.budget_key,
                    decision,
                    reason,
                    approval_id,
                    _canonical(request.metadata),
                ),
            )
        return GovernanceDecision(
            request_id=request.request_id,
            request_sha256=request.sha256,
            decision=decision,
            reason=reason,
            approval_id=approval_id,
            audit_id=audit_id,
        )


def _now(value: float | None) -> float:
    return time.time() if value is None else float(value)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()
