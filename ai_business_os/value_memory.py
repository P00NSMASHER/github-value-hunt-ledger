"""Evidence-weighted memory for the AI Business OS.

Memory stores what was tried and what happened, but only independently verified outcomes influence
learned value. Outcome credit is conserved across memories so one business result cannot be counted
multiple times at full weight, and objective-specific memories do not silently generalize to
unrelated objectives.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from typing import Any, Dict, Iterable, List, Mapping, Optional

from ai_business_os.persistent_agents.runtime import AgentRuntime


def _now() -> float:
    return time.time()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _valid_sha256(value: str) -> bool:
    if len(value) != 64:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


class ValueMemoryError(ValueError):
    """Raised when evidence-weighted memory invariants are violated."""


class ValueMemory:
    """Persistent, objective-conditioned, evidence-weighted memory."""

    def __init__(self, runtime: AgentRuntime):
        self.runtime = runtime
        self._migrate()

    def _migrate(self) -> None:
        self.runtime.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS value_memory_items (
                id TEXT PRIMARY KEY,
                memory_key TEXT NOT NULL,
                version TEXT NOT NULL,
                scope TEXT NOT NULL,
                objective TEXT NOT NULL,
                content_json TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_by_agent_id TEXT NOT NULL REFERENCES agents(id),
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                UNIQUE(memory_key, version, scope, objective)
            );

            CREATE TABLE IF NOT EXISTS value_memory_observations (
                id TEXT PRIMARY KEY,
                memory_id TEXT NOT NULL REFERENCES value_memory_items(id),
                event_id TEXT NOT NULL,
                observer_agent_id TEXT NOT NULL REFERENCES agents(id),
                reward REAL NOT NULL,
                attribution_fraction REAL NOT NULL,
                evidence_json TEXT NOT NULL,
                evidence_hash TEXT NOT NULL,
                verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
                verifier_agent_id TEXT REFERENCES agents(id),
                verification_report_hash TEXT,
                created_at REAL NOT NULL,
                verified_at REAL,
                UNIQUE(memory_id, event_id)
            );

            CREATE INDEX IF NOT EXISTS idx_value_memory_lookup
                ON value_memory_items(scope, objective, status);
            CREATE INDEX IF NOT EXISTS idx_value_memory_observation_event
                ON value_memory_observations(event_id, verification_status);
            CREATE INDEX IF NOT EXISTS idx_value_memory_observation_memory
                ON value_memory_observations(memory_id, verification_status);
            """
        )
        self.runtime.conn.commit()

    def register_memory(
        self,
        *,
        memory_key: str,
        content: Dict[str, Any],
        created_by_agent_id: str,
        objective: str = "*",
        scope: str = "GLOBAL",
        version: str = "v1",
        memory_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.runtime._require_agent(created_by_agent_id)
        memory_key = memory_key.strip()
        version = version.strip()
        scope = scope.strip()
        objective = objective.strip()
        if not memory_key or not version or not scope or not objective:
            raise ValueMemoryError("memory_key, version, scope, and objective must be non-empty")
        if not isinstance(content, dict) or not content:
            raise ValueMemoryError("memory content must be a non-empty object")

        content_hash = _sha(content)
        memory_id = memory_id or f"memory_{uuid.uuid4().hex}"
        ts = _now()
        try:
            self.runtime.conn.execute(
                """
                INSERT INTO value_memory_items(
                    id, memory_key, version, scope, objective, content_json, content_hash,
                    created_by_agent_id, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                """,
                (
                    memory_id,
                    memory_key,
                    version,
                    scope,
                    objective,
                    _json(content),
                    content_hash,
                    created_by_agent_id,
                    ts,
                    ts,
                ),
            )
        except Exception as exc:
            self.runtime.conn.rollback()
            raise ValueMemoryError(
                "a memory with this key/version/scope/objective already exists"
            ) from exc
        self.runtime.conn.commit()
        self.runtime.append_event(
            created_by_agent_id,
            "VALUE_MEMORY_REGISTERED",
            {
                "memory_id": memory_id,
                "memory_key": memory_key,
                "version": version,
                "scope": scope,
                "objective": objective,
                "content_hash": content_hash,
            },
        )
        return self.get_memory(memory_id)

    def observe_outcome(
        self,
        memory_id: str,
        *,
        event_id: str,
        observer_agent_id: str,
        reward: float,
        attribution_fraction: float,
        evidence: Dict[str, Any],
        observation_id: Optional[str] = None,
    ) -> str:
        memory = self._require_memory(memory_id)
        self.runtime._require_agent(observer_agent_id)
        if memory["status"] != "ACTIVE":
            raise ValueMemoryError("outcomes may only be attached to ACTIVE memories")
        event_id = event_id.strip()
        if not event_id:
            raise ValueMemoryError("event_id must be non-empty")
        reward = float(reward)
        attribution_fraction = float(attribution_fraction)
        if not math.isfinite(reward) or reward < -1.0 or reward > 1.0:
            raise ValueMemoryError("reward must be finite and within [-1, 1]")
        if (
            not math.isfinite(attribution_fraction)
            or attribution_fraction <= 0.0
            or attribution_fraction > 1.0
        ):
            raise ValueMemoryError("attribution_fraction must be within (0, 1]")
        if not isinstance(evidence, dict) or not evidence:
            raise ValueMemoryError("outcome observation requires non-empty evidence")

        evidence_payload = {
            "memory_id": memory_id,
            "event_id": event_id,
            "reward": reward,
            "attribution_fraction": attribution_fraction,
            "evidence": evidence,
        }
        evidence_hash = _sha(evidence_payload)
        observation_id = observation_id or f"memobs_{uuid.uuid4().hex}"
        try:
            self.runtime.conn.execute(
                """
                INSERT INTO value_memory_observations(
                    id, memory_id, event_id, observer_agent_id, reward,
                    attribution_fraction, evidence_json, evidence_hash,
                    verification_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'UNVERIFIED', ?)
                """,
                (
                    observation_id,
                    memory_id,
                    event_id,
                    observer_agent_id,
                    reward,
                    attribution_fraction,
                    _json(evidence),
                    evidence_hash,
                    _now(),
                ),
            )
        except Exception as exc:
            self.runtime.conn.rollback()
            raise ValueMemoryError(
                "the same event cannot be observed twice for the same memory"
            ) from exc
        self.runtime.conn.commit()
        self.runtime.append_event(
            observer_agent_id,
            "VALUE_MEMORY_OUTCOME_OBSERVED",
            {
                "observation_id": observation_id,
                "memory_id": memory_id,
                "event_id": event_id,
                "reward": reward,
                "attribution_fraction": attribution_fraction,
                "evidence_hash": evidence_hash,
            },
        )
        return observation_id

    def verify_observation(
        self,
        observation_id: str,
        *,
        verifier_agent_id: str,
        verification_report_hash: str,
        accepted: bool,
    ) -> Dict[str, Any]:
        row = self._require_observation(observation_id)
        self.runtime._require_agent(verifier_agent_id)
        if row["verification_status"] != "UNVERIFIED":
            raise ValueMemoryError("observation verification is immutable once decided")
        if verifier_agent_id == row["observer_agent_id"]:
            raise ValueMemoryError("observer cannot independently verify its own outcome")
        if not _valid_sha256(verification_report_hash):
            raise ValueMemoryError("verification_report_hash must be a SHA-256 digest")

        status = "VERIFIED" if accepted else "REJECTED"
        if accepted:
            already = self.runtime.conn.execute(
                """
                SELECT COALESCE(SUM(attribution_fraction), 0.0) AS total
                FROM value_memory_observations
                WHERE event_id = ? AND verification_status = 'VERIFIED'
                """,
                (row["event_id"],),
            ).fetchone()
            total = float(already["total"]) + float(row["attribution_fraction"])
            if total > 1.0 + 1e-9:
                raise ValueMemoryError(
                    "verified attribution for one event cannot exceed 1.0 in total"
                )

        self.runtime.conn.execute(
            """
            UPDATE value_memory_observations
            SET verification_status = ?, verifier_agent_id = ?,
                verification_report_hash = ?, verified_at = ?
            WHERE id = ?
            """,
            (
                status,
                verifier_agent_id,
                verification_report_hash,
                _now(),
                observation_id,
            ),
        )
        self.runtime.conn.commit()
        self.runtime.append_event(
            verifier_agent_id,
            "VALUE_MEMORY_OUTCOME_VERIFIED",
            {
                "observation_id": observation_id,
                "memory_id": row["memory_id"],
                "event_id": row["event_id"],
                "status": status,
                "verification_report_hash": verification_report_hash,
            },
        )
        return self.get_observation(observation_id)

    def value_summary(
        self,
        memory_id: str,
        *,
        now: Optional[float] = None,
        half_life_days: float = 90.0,
    ) -> Dict[str, Any]:
        self._require_memory(memory_id)
        if not math.isfinite(float(half_life_days)) or half_life_days <= 0:
            raise ValueMemoryError("half_life_days must be finite and positive")
        now = _now() if now is None else float(now)
        if not math.isfinite(now):
            raise ValueMemoryError("now must be finite")

        rows = self.runtime.conn.execute(
            """
            SELECT * FROM value_memory_observations
            WHERE memory_id = ? AND verification_status = 'VERIFIED'
            ORDER BY verified_at, id
            """,
            (memory_id,),
        ).fetchall()
        weighted_reward = 0.0
        effective_weight = 0.0
        for row in rows:
            verified_at = float(row["verified_at"])
            age_days = max(0.0, (now - verified_at) / 86400.0)
            recency_weight = 0.5 ** (age_days / float(half_life_days))
            weight = float(row["attribution_fraction"]) * recency_weight
            effective_weight += weight
            weighted_reward += float(row["reward"]) * weight

        mean_reward = weighted_reward / effective_weight if effective_weight else 0.0
        confidence = 1.0 - math.exp(-effective_weight / 2.0) if effective_weight else 0.0
        unique_verifiers = len({row["verifier_agent_id"] for row in rows})
        unique_events = len({row["event_id"] for row in rows})
        rejected_count = int(
            self.runtime.conn.execute(
                """
                SELECT COUNT(*) AS n FROM value_memory_observations
                WHERE memory_id = ? AND verification_status = 'REJECTED'
                """,
                (memory_id,),
            ).fetchone()["n"]
        )
        unverified_count = int(
            self.runtime.conn.execute(
                """
                SELECT COUNT(*) AS n FROM value_memory_observations
                WHERE memory_id = ? AND verification_status = 'UNVERIFIED'
                """,
                (memory_id,),
            ).fetchone()["n"]
        )
        return {
            "memory_id": memory_id,
            "verified_count": len(rows),
            "rejected_count": rejected_count,
            "unverified_count": unverified_count,
            "unique_events": unique_events,
            "unique_verifiers": unique_verifiers,
            "effective_weight": effective_weight,
            "mean_reward": mean_reward,
            "confidence": confidence,
            "half_life_days": float(half_life_days),
            "as_of": now,
        }

    def rank_memories(
        self,
        relevance_by_memory_id: Mapping[str, float],
        *,
        objective: str,
        scope: str = "GLOBAL",
        now: Optional[float] = None,
        half_life_days: float = 90.0,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Rank already-retrieved candidates using relevance and verified learned value.

        Semantic relevance remains an upstream retrieval concern. This method re-ranks candidates
        while preserving untested memories at a neutral prior instead of suppressing them.
        """
        objective = objective.strip()
        scope = scope.strip()
        if not objective or not scope:
            raise ValueMemoryError("objective and scope must be non-empty")
        if limit is not None and limit <= 0:
            raise ValueMemoryError("limit must be positive")

        ranked: List[Dict[str, Any]] = []
        for memory_id, relevance_raw in relevance_by_memory_id.items():
            relevance = float(relevance_raw)
            if not math.isfinite(relevance) or relevance < 0.0 or relevance > 1.0:
                raise ValueMemoryError("semantic relevance must be within [0, 1]")
            memory = self._require_memory(memory_id)
            if memory["status"] != "ACTIVE" or memory["scope"] != scope:
                continue
            if memory["objective"] not in {objective, "*"}:
                continue

            summary = self.value_summary(
                memory_id,
                now=now,
                half_life_days=half_life_days,
            )
            # Neutral value prior is 0.5. Verified positive/negative evidence moves it up/down
            # in proportion to confidence, preventing one result from dominating.
            value_factor = 0.5 + 0.5 * summary["mean_reward"] * summary["confidence"]
            objective_factor = 1.0 if memory["objective"] == objective else 0.9
            score = relevance * value_factor * objective_factor
            ranked.append(
                {
                    "memory": memory,
                    "value": summary,
                    "semantic_relevance": relevance,
                    "objective_factor": objective_factor,
                    "value_factor": value_factor,
                    "score": score,
                }
            )

        ranked.sort(
            key=lambda row: (
                row["score"],
                row["value"]["confidence"],
                row["semantic_relevance"],
                row["memory"]["memory_key"],
            ),
            reverse=True,
        )
        return ranked[:limit] if limit is not None else ranked

    def retire_memory(
        self,
        memory_id: str,
        *,
        curator_agent_id: str,
        reason: str,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        memory = self._require_memory(memory_id)
        self.runtime._require_agent(curator_agent_id)
        if not reason.strip() or not evidence:
            raise ValueMemoryError("retirement requires a reason and evidence")
        if memory["status"] != "ACTIVE":
            raise ValueMemoryError("memory is already retired")
        evidence_hash = _sha(
            {
                "memory_id": memory_id,
                "reason": reason,
                "evidence": evidence,
            }
        )
        self.runtime.conn.execute(
            """
            UPDATE value_memory_items
            SET status = 'RETIRED', updated_at = ?
            WHERE id = ?
            """,
            (_now(), memory_id),
        )
        self.runtime.conn.commit()
        self.runtime.append_event(
            curator_agent_id,
            "VALUE_MEMORY_RETIRED",
            {
                "memory_id": memory_id,
                "reason": reason,
                "evidence_hash": evidence_hash,
            },
        )
        return self.get_memory(memory_id)

    def get_memory(self, memory_id: str) -> Dict[str, Any]:
        row = self._require_memory(memory_id)
        return {
            "id": row["id"],
            "memory_key": row["memory_key"],
            "version": row["version"],
            "scope": row["scope"],
            "objective": row["objective"],
            "content": json.loads(row["content_json"]),
            "content_hash": row["content_hash"],
            "created_by_agent_id": row["created_by_agent_id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def get_observation(self, observation_id: str) -> Dict[str, Any]:
        row = self._require_observation(observation_id)
        return {
            "id": row["id"],
            "memory_id": row["memory_id"],
            "event_id": row["event_id"],
            "observer_agent_id": row["observer_agent_id"],
            "reward": row["reward"],
            "attribution_fraction": row["attribution_fraction"],
            "evidence": json.loads(row["evidence_json"]),
            "evidence_hash": row["evidence_hash"],
            "verification_status": row["verification_status"],
            "verifier_agent_id": row["verifier_agent_id"],
            "verification_report_hash": row["verification_report_hash"],
            "created_at": row["created_at"],
            "verified_at": row["verified_at"],
        }

    def _require_memory(self, memory_id: str):
        row = self.runtime.conn.execute(
            "SELECT * FROM value_memory_items WHERE id = ?",
            (memory_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown value memory: {memory_id}")
        return row

    def _require_observation(self, observation_id: str):
        row = self.runtime.conn.execute(
            "SELECT * FROM value_memory_observations WHERE id = ?",
            (observation_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown value-memory observation: {observation_id}")
        return row
