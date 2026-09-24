"""Durable persistent-agent runtime for the AI Business OS.

The runtime deliberately separates persistence from intelligence. LLM/model adapters can sit on
top of this layer later, while goals, state, heartbeats, delegation, event history, and rollback
remain deterministic and inspectable.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


class InvalidTransition(ValueError):
    """Raised when a goal attempts an invalid state transition."""


GOAL_TRANSITIONS = {
    "PENDING": {"ACTIVE", "CANCELLED"},
    "ACTIVE": {"BLOCKED", "VERIFYING", "CANCELLED"},
    "BLOCKED": {"ACTIVE", "CANCELLED"},
    "VERIFYING": {"ACTIVE", "COMPLETE", "BLOCKED", "CANCELLED"},
    "COMPLETE": set(),
    "CANCELLED": set(),
}


def _now() -> float:
    return time.time()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class AgentRuntime:
    """SQLite-backed state manager for long-lived agents."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self._migrate()

    def close(self) -> None:
        self.conn.close()

    def _migrate(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                parent_agent_id TEXT NULL REFERENCES agents(id),
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                generation INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL,
                last_heartbeat REAL NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL REFERENCES agents(id),
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                priority INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                state_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL REFERENCES agents(id),
                goal_id TEXT NULL REFERENCES goals(id),
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                prev_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS snapshots (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL REFERENCES agents(id),
                goal_id TEXT NOT NULL REFERENCES goals(id),
                event_seq INTEGER NOT NULL,
                state_json TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_goals_agent_status ON goals(agent_id, status);
            CREATE INDEX IF NOT EXISTS idx_events_agent_seq ON events(agent_id, seq);
            CREATE INDEX IF NOT EXISTS idx_snapshots_goal_created ON snapshots(goal_id, created_at);
            """
        )
        self.conn.commit()

    def register_agent(
        self,
        role: str,
        *,
        agent_id: Optional[str] = None,
        parent_agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        if parent_agent_id is not None:
            self._require_agent(parent_agent_id)
        agent_id = agent_id or f"agent_{uuid.uuid4().hex}"
        ts = _now()
        self.conn.execute(
            """
            INSERT INTO agents(id, role, parent_agent_id, created_at, last_heartbeat, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (agent_id, role, parent_agent_id, ts, ts, _json(metadata or {})),
        )
        self.conn.commit()
        self.append_event(agent_id, "AGENT_REGISTERED", {"role": role, "parent": parent_agent_id})
        return agent_id

    def spawn_subagent(
        self,
        parent_agent_id: str,
        role: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self.register_agent(role, parent_agent_id=parent_agent_id, metadata=metadata)

    def heartbeat(self, agent_id: str) -> int:
        row = self._require_agent(agent_id)
        generation = int(row["generation"])
        self.conn.execute(
            "UPDATE agents SET last_heartbeat = ?, status = 'ACTIVE' WHERE id = ?",
            (_now(), agent_id),
        )
        self.conn.commit()
        self.append_event(agent_id, "HEARTBEAT", {"generation": generation})
        return generation

    def reclaim_if_stale(self, agent_id: str, stale_after_seconds: float) -> bool:
        row = self._require_agent(agent_id)
        if _now() - float(row["last_heartbeat"]) <= stale_after_seconds:
            return False
        new_generation = int(row["generation"]) + 1
        self.conn.execute(
            """
            UPDATE agents
            SET generation = ?, last_heartbeat = ?, status = 'ACTIVE'
            WHERE id = ?
            """,
            (new_generation, _now(), agent_id),
        )
        self.conn.commit()
        self.append_event(agent_id, "LEASE_RECLAIMED", {"generation": new_generation})
        return True

    def assign_goal(
        self,
        agent_id: str,
        description: str,
        *,
        priority: int = 0,
        state: Optional[Dict[str, Any]] = None,
        goal_id: Optional[str] = None,
    ) -> str:
        self._require_agent(agent_id)
        goal_id = goal_id or f"goal_{uuid.uuid4().hex}"
        ts = _now()
        self.conn.execute(
            """
            INSERT INTO goals(id, agent_id, description, priority, created_at, updated_at, state_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (goal_id, agent_id, description, priority, ts, ts, _json(state or {})),
        )
        self.conn.commit()
        self.append_event(
            agent_id,
            "GOAL_ASSIGNED",
            {"description": description, "priority": priority},
            goal_id=goal_id,
        )
        return goal_id

    def transition_goal(
        self,
        goal_id: str,
        new_status: str,
        *,
        state_patch: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        goal = self._require_goal(goal_id)
        current = str(goal["status"])
        if new_status not in GOAL_TRANSITIONS.get(current, set()):
            raise InvalidTransition(f"{current} -> {new_status} is not allowed")

        state = json.loads(goal["state_json"])
        if state_patch:
            state.update(state_patch)

        self.conn.execute(
            """
            UPDATE goals SET status = ?, state_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_status, _json(state), _now(), goal_id),
        )
        self.conn.commit()
        self.append_event(
            str(goal["agent_id"]),
            "GOAL_TRANSITION",
            {"from": current, "to": new_status, "reason": reason, "state_patch": state_patch or {}},
            goal_id=goal_id,
        )
        return self.get_goal(goal_id)

    def update_goal_state(
        self,
        goal_id: str,
        patch: Dict[str, Any],
        *,
        event_type: str = "GOAL_STATE_UPDATED",
    ) -> Dict[str, Any]:
        goal = self._require_goal(goal_id)
        state = json.loads(goal["state_json"])
        state.update(patch)
        self.conn.execute(
            "UPDATE goals SET state_json = ?, updated_at = ? WHERE id = ?",
            (_json(state), _now(), goal_id),
        )
        self.conn.commit()
        self.append_event(str(goal["agent_id"]), event_type, {"patch": patch}, goal_id=goal_id)
        return self.get_goal(goal_id)

    def snapshot_goal(self, goal_id: str) -> str:
        goal = self._require_goal(goal_id)
        event_seq = self._last_event_seq(str(goal["agent_id"]))
        snapshot_id = f"snap_{uuid.uuid4().hex}"
        state = {
            "status": goal["status"],
            "state": json.loads(goal["state_json"]),
            "updated_at": goal["updated_at"],
        }
        self.conn.execute(
            """
            INSERT INTO snapshots(id, agent_id, goal_id, event_seq, state_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (snapshot_id, goal["agent_id"], goal_id, event_seq, _json(state), _now()),
        )
        self.conn.commit()
        self.append_event(
            str(goal["agent_id"]),
            "SNAPSHOT_CREATED",
            {"snapshot_id": snapshot_id, "event_seq": event_seq},
            goal_id=goal_id,
        )
        return snapshot_id

    def restore_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        row = self.conn.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown snapshot: {snapshot_id}")
        state = json.loads(row["state_json"])
        self.conn.execute(
            """
            UPDATE goals SET status = ?, state_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (state["status"], _json(state["state"]), _now(), row["goal_id"]),
        )
        self.conn.commit()
        self.append_event(
            str(row["agent_id"]),
            "SNAPSHOT_RESTORED",
            {"snapshot_id": snapshot_id, "source_event_seq": row["event_seq"]},
            goal_id=str(row["goal_id"]),
        )
        return self.get_goal(str(row["goal_id"]))

    def append_event(
        self,
        agent_id: str,
        event_type: str,
        payload: Dict[str, Any],
        *,
        goal_id: Optional[str] = None,
    ) -> str:
        self._require_agent(agent_id)
        if goal_id is not None:
            self._require_goal(goal_id)
        prev = self.conn.execute(
            "SELECT event_hash FROM events WHERE agent_id = ? ORDER BY seq DESC LIMIT 1",
            (agent_id,),
        ).fetchone()
        prev_hash = str(prev["event_hash"]) if prev else "GENESIS"
        created_at = _now()
        canonical = _json(
            {
                "agent_id": agent_id,
                "goal_id": goal_id,
                "event_type": event_type,
                "payload": payload,
                "created_at": created_at,
                "prev_hash": prev_hash,
            }
        )
        event_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        self.conn.execute(
            """
            INSERT INTO events(agent_id, goal_id, event_type, payload_json, created_at, prev_hash, event_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (agent_id, goal_id, event_type, _json(payload), created_at, prev_hash, event_hash),
        )
        self.conn.commit()
        return event_hash

    def verify_event_chain(self, agent_id: str) -> bool:
        self._require_agent(agent_id)
        rows = self.conn.execute(
            "SELECT * FROM events WHERE agent_id = ? ORDER BY seq ASC",
            (agent_id,),
        ).fetchall()
        expected_prev = "GENESIS"
        for row in rows:
            if row["prev_hash"] != expected_prev:
                return False
            canonical = _json(
                {
                    "agent_id": row["agent_id"],
                    "goal_id": row["goal_id"],
                    "event_type": row["event_type"],
                    "payload": json.loads(row["payload_json"]),
                    "created_at": row["created_at"],
                    "prev_hash": row["prev_hash"],
                }
            )
            if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != row["event_hash"]:
                return False
            expected_prev = row["event_hash"]
        return True

    def get_goal(self, goal_id: str) -> Dict[str, Any]:
        row = self._require_goal(goal_id)
        return {
            "id": row["id"],
            "agent_id": row["agent_id"],
            "description": row["description"],
            "status": row["status"],
            "priority": row["priority"],
            "state": json.loads(row["state_json"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_goals(self, agent_id: str, statuses: Optional[Iterable[str]] = None) -> list[Dict[str, Any]]:
        self._require_agent(agent_id)
        if statuses:
            statuses = list(statuses)
            marks = ",".join("?" for _ in statuses)
            rows = self.conn.execute(
                f"SELECT id FROM goals WHERE agent_id = ? AND status IN ({marks}) ORDER BY priority DESC, created_at",
                [agent_id, *statuses],
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT id FROM goals WHERE agent_id = ? ORDER BY priority DESC, created_at",
                (agent_id,),
            ).fetchall()
        return [self.get_goal(str(r["id"])) for r in rows]

    def _require_agent(self, agent_id: str) -> sqlite3.Row:
        row = self.conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown agent: {agent_id}")
        return row

    def _require_goal(self, goal_id: str) -> sqlite3.Row:
        row = self.conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown goal: {goal_id}")
        return row

    def _last_event_seq(self, agent_id: str) -> int:
        row = self.conn.execute(
            "SELECT COALESCE(MAX(seq), 0) AS seq FROM events WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        return int(row["seq"])
