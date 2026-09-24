"""Persistent agent runtime for AI Business OS.

Stdlib-only control plane providing durable goals, worker registration, leases,
heartbeats, crash recovery, and terminal run records.

This module deliberately does *not* grant tools, credentials, or action rights.
Those are added by later governance layers.
"""
from __future__ import annotations

import contextlib
import dataclasses
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Iterable


TERMINAL_GOAL_STATES = {"COMPLETED", "FAILED", "CANCELLED"}
ACTIVE_GOAL_STATES = {"PENDING", "RUNNING"}


@dataclasses.dataclass(frozen=True)
class Goal:
    id: str
    title: str
    payload: dict[str, Any]
    priority: int
    state: str
    created_at: float
    updated_at: float
    claimed_by: str | None
    lease_generation: int
    lease_expires_at: float | None


@dataclasses.dataclass(frozen=True)
class Agent:
    id: str
    role: str
    status: str
    registered_at: float
    last_heartbeat_at: float
    metadata: dict[str, Any]


class PersistentAgentRuntime:
    """SQLite-backed persistent worker substrate.

    Safety invariants:
    - A goal has at most one live lease owner.
    - Lease generation increases every time a goal is reclaimed.
    - Only the current owner+generation may heartbeat/complete/fail a goal.
    - Expired work is requeued; stale workers cannot later commit success.
    - Payloads and metadata are JSON, keeping the state machine inspectable.
    """

    def __init__(self, db_path: str | Path = "ai_business_os.sqlite3") -> None:
        self.db_path = str(db_path)
        self._initialize()

    @contextlib.contextmanager
    def _connect(self) -> Iterable[sqlite3.Connection]:
        con = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        con.row_factory = sqlite3.Row
        try:
            con.execute("PRAGMA foreign_keys=ON")
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=NORMAL")
            yield con
        finally:
            con.close()

    def _initialize(self) -> None:
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    registered_at REAL NOT NULL,
                    last_heartbeat_at REAL NOT NULL,
                    metadata_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS goals (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 0,
                    state TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    claimed_by TEXT,
                    lease_generation INTEGER NOT NULL DEFAULT 0,
                    lease_expires_at REAL,
                    last_error TEXT,
                    result_json TEXT,
                    CHECK (state IN ('PENDING','RUNNING','COMPLETED','FAILED','CANCELLED'))
                );

                CREATE INDEX IF NOT EXISTS idx_goals_queue
                    ON goals(state, priority DESC, created_at ASC);

                CREATE TABLE IF NOT EXISTS agent_runs (
                    id TEXT PRIMARY KEY,
                    goal_id TEXT NOT NULL REFERENCES goals(id),
                    agent_id TEXT NOT NULL,
                    lease_generation INTEGER NOT NULL,
                    started_at REAL NOT NULL,
                    ended_at REAL,
                    outcome TEXT,
                    result_json TEXT,
                    error TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_runs_goal ON agent_runs(goal_id);
                """
            )

    @staticmethod
    def _now(now: float | None = None) -> float:
        return time.time() if now is None else float(now)

    def register_agent(
        self,
        agent_id: str,
        role: str,
        *,
        metadata: dict[str, Any] | None = None,
        now: float | None = None,
    ) -> Agent:
        ts = self._now(now)
        metadata = metadata or {}
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO agents(id, role, status, registered_at, last_heartbeat_at, metadata_json)
                VALUES(?, ?, 'ACTIVE', ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    role=excluded.role,
                    status='ACTIVE',
                    last_heartbeat_at=excluded.last_heartbeat_at,
                    metadata_json=excluded.metadata_json
                """,
                (agent_id, role, ts, ts, json.dumps(metadata, sort_keys=True)),
            )
        return self.get_agent(agent_id)

    def get_agent(self, agent_id: str) -> Agent:
        with self._connect() as con:
            row = con.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown agent: {agent_id}")
        return Agent(
            id=row["id"],
            role=row["role"],
            status=row["status"],
            registered_at=row["registered_at"],
            last_heartbeat_at=row["last_heartbeat_at"],
            metadata=json.loads(row["metadata_json"]),
        )

    def enqueue_goal(
        self,
        title: str,
        payload: dict[str, Any] | None = None,
        *,
        priority: int = 0,
        goal_id: str | None = None,
        now: float | None = None,
    ) -> Goal:
        ts = self._now(now)
        goal_id = goal_id or f"goal_{uuid.uuid4().hex}"
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO goals(
                    id, title, payload_json, priority, state,
                    created_at, updated_at, lease_generation
                ) VALUES(?, ?, ?, ?, 'PENDING', ?, ?, 0)
                """,
                (
                    goal_id,
                    title,
                    json.dumps(payload or {}, sort_keys=True),
                    int(priority),
                    ts,
                    ts,
                ),
            )
        return self.get_goal(goal_id)

    def get_goal(self, goal_id: str) -> Goal:
        with self._connect() as con:
            row = con.execute("SELECT * FROM goals WHERE id=?", (goal_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown goal: {goal_id}")
        return self._goal_from_row(row)

    def _goal_from_row(self, row: sqlite3.Row) -> Goal:
        return Goal(
            id=row["id"],
            title=row["title"],
            payload=json.loads(row["payload_json"]),
            priority=row["priority"],
            state=row["state"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            claimed_by=row["claimed_by"],
            lease_generation=row["lease_generation"],
            lease_expires_at=row["lease_expires_at"],
        )

    def claim_next_goal(
        self,
        agent_id: str,
        *,
        lease_seconds: float = 300.0,
        now: float | None = None,
    ) -> Goal | None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be > 0")
        ts = self._now(now)
        self.get_agent(agent_id)

        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            self._requeue_expired_in_tx(con, ts)
            row = con.execute(
                """
                SELECT * FROM goals
                WHERE state='PENDING'
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                con.execute("COMMIT")
                return None

            new_generation = int(row["lease_generation"]) + 1
            lease_expires_at = ts + float(lease_seconds)
            cur = con.execute(
                """
                UPDATE goals
                SET state='RUNNING',
                    claimed_by=?,
                    lease_generation=?,
                    lease_expires_at=?,
                    updated_at=?,
                    last_error=NULL
                WHERE id=? AND state='PENDING'
                """,
                (
                    agent_id,
                    new_generation,
                    lease_expires_at,
                    ts,
                    row["id"],
                ),
            )
            if cur.rowcount != 1:
                con.execute("ROLLBACK")
                return None

            run_id = f"run_{uuid.uuid4().hex}"
            con.execute(
                """
                INSERT INTO agent_runs(
                    id, goal_id, agent_id, lease_generation, started_at
                ) VALUES(?, ?, ?, ?, ?)
                """,
                (run_id, row["id"], agent_id, new_generation, ts),
            )
            con.execute(
                "UPDATE agents SET last_heartbeat_at=?, status='ACTIVE' WHERE id=?",
                (ts, agent_id),
            )
            con.execute("COMMIT")

        return self.get_goal(row["id"])

    def heartbeat(
        self,
        agent_id: str,
        goal_id: str,
        lease_generation: int,
        *,
        extend_seconds: float = 300.0,
        now: float | None = None,
    ) -> Goal:
        if extend_seconds <= 0:
            raise ValueError("extend_seconds must be > 0")
        ts = self._now(now)
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM goals WHERE id=?", (goal_id,)).fetchone()
            self._assert_current_lease(row, agent_id, lease_generation, ts)
            con.execute(
                """
                UPDATE goals
                SET lease_expires_at=?, updated_at=?
                WHERE id=?
                """,
                (ts + extend_seconds, ts, goal_id),
            )
            con.execute(
                "UPDATE agents SET last_heartbeat_at=?, status='ACTIVE' WHERE id=?",
                (ts, agent_id),
            )
            con.execute("COMMIT")
        return self.get_goal(goal_id)

    def complete_goal(
        self,
        agent_id: str,
        goal_id: str,
        lease_generation: int,
        result: dict[str, Any] | None = None,
        *,
        now: float | None = None,
    ) -> Goal:
        return self._finish(
            agent_id,
            goal_id,
            lease_generation,
            outcome="COMPLETED",
            result=result or {},
            error=None,
            now=now,
        )

    def fail_goal(
        self,
        agent_id: str,
        goal_id: str,
        lease_generation: int,
        error: str,
        *,
        requeue: bool = False,
        now: float | None = None,
    ) -> Goal:
        return self._finish(
            agent_id,
            goal_id,
            lease_generation,
            outcome="PENDING" if requeue else "FAILED",
            result=None,
            error=error,
            now=now,
        )

    def _finish(
        self,
        agent_id: str,
        goal_id: str,
        lease_generation: int,
        *,
        outcome: str,
        result: dict[str, Any] | None,
        error: str | None,
        now: float | None,
    ) -> Goal:
        ts = self._now(now)
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM goals WHERE id=?", (goal_id,)).fetchone()
            self._assert_current_lease(row, agent_id, lease_generation, ts)

            if outcome == "PENDING":
                claimed_by = None
                lease_expires_at = None
            else:
                claimed_by = agent_id
                lease_expires_at = None

            con.execute(
                """
                UPDATE goals
                SET state=?, updated_at=?, claimed_by=?, lease_expires_at=?,
                    result_json=?, last_error=?
                WHERE id=?
                """,
                (
                    outcome,
                    ts,
                    claimed_by,
                    lease_expires_at,
                    json.dumps(result, sort_keys=True) if result is not None else None,
                    error,
                    goal_id,
                ),
            )
            con.execute(
                """
                UPDATE agent_runs
                SET ended_at=?, outcome=?, result_json=?, error=?
                WHERE goal_id=? AND agent_id=? AND lease_generation=? AND ended_at IS NULL
                """,
                (
                    ts,
                    outcome,
                    json.dumps(result, sort_keys=True) if result is not None else None,
                    error,
                    goal_id,
                    agent_id,
                    lease_generation,
                ),
            )
            con.execute("COMMIT")
        return self.get_goal(goal_id)

    def requeue_expired(self, *, now: float | None = None) -> int:
        ts = self._now(now)
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            count = self._requeue_expired_in_tx(con, ts)
            con.execute("COMMIT")
        return count

    def _requeue_expired_in_tx(self, con: sqlite3.Connection, ts: float) -> int:
        expired = con.execute(
            """
            SELECT id, claimed_by, lease_generation
            FROM goals
            WHERE state='RUNNING'
              AND lease_expires_at IS NOT NULL
              AND lease_expires_at <= ?
            """,
            (ts,),
        ).fetchall()

        for row in expired:
            con.execute(
                """
                UPDATE agent_runs
                SET ended_at=?, outcome='LEASE_EXPIRED',
                    error='lease expired before completion'
                WHERE goal_id=? AND agent_id=? AND lease_generation=?
                  AND ended_at IS NULL
                """,
                (ts, row["id"], row["claimed_by"], row["lease_generation"]),
            )

        cur = con.execute(
            """
            UPDATE goals
            SET state='PENDING',
                claimed_by=NULL,
                lease_expires_at=NULL,
                updated_at=?,
                last_error='lease expired; automatically requeued'
            WHERE state='RUNNING'
              AND lease_expires_at IS NOT NULL
              AND lease_expires_at <= ?
            """,
            (ts, ts),
        )
        return int(cur.rowcount)

    @staticmethod
    def _assert_current_lease(
        row: sqlite3.Row | None,
        agent_id: str,
        lease_generation: int,
        ts: float,
    ) -> None:
        if row is None:
            raise KeyError("unknown goal")
        if row["state"] != "RUNNING":
            raise RuntimeError(f"goal is not RUNNING: {row['state']}")
        if row["claimed_by"] != agent_id:
            raise PermissionError("agent does not own this goal lease")
        if int(row["lease_generation"]) != int(lease_generation):
            raise PermissionError("stale lease generation")
        expires = row["lease_expires_at"]
        if expires is None or float(expires) <= ts:
            raise PermissionError("goal lease has expired")

    def dashboard(self) -> dict[str, Any]:
        with self._connect() as con:
            goal_counts = {
                row["state"]: row["n"]
                for row in con.execute(
                    "SELECT state, COUNT(*) AS n FROM goals GROUP BY state"
                )
            }
            agent_count = con.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
            open_runs = con.execute(
                "SELECT COUNT(*) FROM agent_runs WHERE ended_at IS NULL"
            ).fetchone()[0]
        return {
            "agents": agent_count,
            "goals": {
                state: int(goal_counts.get(state, 0))
                for state in ("PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED")
            },
            "open_runs": int(open_runs),
        }
