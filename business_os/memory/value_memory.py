"""Value-weighted persistent memory for AI Business OS.

Retrieval is not based on semantic relevance alone. Memories also carry
observed outcome value, confidence, objective scope, and recency. Negative
warnings remain retrievable so the system can learn what *not* to repeat.
"""
from __future__ import annotations

import dataclasses
import json
import math
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


@dataclasses.dataclass(frozen=True)
class Memory:
    id: str
    text: str
    kind: str
    objective_scope: str
    value: float
    confidence: float
    evidence_count: int
    created_at: float
    updated_at: float
    metadata: dict[str, Any]


@dataclasses.dataclass(frozen=True)
class RankedMemory:
    memory: Memory
    relevance: float
    value_factor: float
    confidence_factor: float
    recency_factor: float
    scope_factor: float
    score: float


class ValueMemory:
    ALLOWED_KINDS = {"TACTIC", "OUTCOME", "WARNING", "DECISION"}

    def __init__(self, db_path: str | Path = "ai_business_os.sqlite3") -> None:
        self.db_path = str(db_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path, timeout=30)
        con.row_factory = sqlite3.Row
        return con

    def _initialize(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS value_memory (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    objective_scope TEXT NOT NULL,
                    value REAL NOT NULL,
                    confidence REAL NOT NULL,
                    evidence_count INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    metadata_json TEXT NOT NULL,
                    CHECK(value >= -1.0 AND value <= 1.0),
                    CHECK(confidence >= 0.0 AND confidence <= 1.0),
                    CHECK(evidence_count >= 1)
                )
                """
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS idx_value_memory_scope ON value_memory(objective_scope, updated_at)"
            )

    @staticmethod
    def _now(now: float | None) -> float:
        return time.time() if now is None else float(now)

    def remember(
        self,
        text: str,
        *,
        kind: str = "TACTIC",
        objective_scope: str = "global",
        value: float = 0.0,
        confidence: float = 0.5,
        metadata: dict[str, Any] | None = None,
        memory_id: str | None = None,
        now: float | None = None,
    ) -> Memory:
        if kind not in self.ALLOWED_KINDS:
            raise ValueError(f"unsupported memory kind: {kind}")
        if not text.strip():
            raise ValueError("memory text cannot be empty")
        self._check_unit_interval(confidence, "confidence")
        self._check_value(value)

        ts = self._now(now)
        memory_id = memory_id or f"mem_{uuid.uuid4().hex}"
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO value_memory(
                    id, text, kind, objective_scope, value, confidence,
                    evidence_count, created_at, updated_at, metadata_json
                ) VALUES(?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    memory_id,
                    text.strip(),
                    kind,
                    objective_scope,
                    float(value),
                    float(confidence),
                    ts,
                    ts,
                    json.dumps(metadata or {}, sort_keys=True),
                ),
            )
        return self.get(memory_id)

    def get(self, memory_id: str) -> Memory:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM value_memory WHERE id=?", (memory_id,)
            ).fetchone()
        if row is None:
            raise KeyError(memory_id)
        return self._from_row(row)

    def observe_outcome(
        self,
        memory_id: str,
        reward: float,
        *,
        observation_confidence: float = 1.0,
        now: float | None = None,
    ) -> Memory:
        """Update Q-like value with a confidence-weighted running mean.

        Rewards are bounded to [-1, 1]. Low-confidence observations contribute
        less effective weight than high-confidence realized outcomes.
        """
        self._check_value(reward)
        self._check_unit_interval(observation_confidence, "observation_confidence")
        if observation_confidence == 0:
            return self.get(memory_id)

        ts = self._now(now)
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT * FROM value_memory WHERE id=?", (memory_id,)
            ).fetchone()
            if row is None:
                con.rollback()
                raise KeyError(memory_id)

            old_count = int(row["evidence_count"])
            # Existing record counts as one full-weight prior observation.
            effective_old_weight = float(old_count)
            new_weight = float(observation_confidence)
            new_value = (
                float(row["value"]) * effective_old_weight
                + float(reward) * new_weight
            ) / (effective_old_weight + new_weight)
            new_confidence = 1.0 - (
                (1.0 - float(row["confidence"]))
                * (1.0 - 0.5 * observation_confidence)
            )
            con.execute(
                """
                UPDATE value_memory
                SET value=?, confidence=?, evidence_count=evidence_count+1, updated_at=?
                WHERE id=?
                """,
                (new_value, min(1.0, new_confidence), ts, memory_id),
            )
            con.commit()
        return self.get(memory_id)

    def retrieve(
        self,
        query: str,
        *,
        objective_scope: str = "global",
        top_k: int = 10,
        half_life_days: float = 90.0,
        now: float | None = None,
    ) -> list[RankedMemory]:
        if top_k <= 0:
            return []
        if half_life_days <= 0:
            raise ValueError("half_life_days must be > 0")
        ts = self._now(now)
        q_tokens = _tokens(query)
        if not q_tokens:
            return []

        with self._connect() as con:
            rows = con.execute("SELECT * FROM value_memory").fetchall()

        ranked: list[RankedMemory] = []
        for row in rows:
            memory = self._from_row(row)
            relevance = _jaccard(q_tokens, _tokens(memory.text))
            if relevance == 0:
                continue

            value_factor = self._value_factor(memory)
            confidence_factor = memory.confidence
            age_days = max(0.0, (ts - memory.updated_at) / 86400.0)
            recency_factor = 0.5 ** (age_days / half_life_days)
            scope_factor = self._scope_factor(memory.objective_scope, objective_scope)

            score = (
                relevance
                * value_factor
                * confidence_factor
                * recency_factor
                * scope_factor
            )
            ranked.append(
                RankedMemory(
                    memory=memory,
                    relevance=relevance,
                    value_factor=value_factor,
                    confidence_factor=confidence_factor,
                    recency_factor=recency_factor,
                    scope_factor=scope_factor,
                    score=score,
                )
            )

        ranked.sort(
            key=lambda item: (
                item.score,
                item.memory.updated_at,
                item.memory.evidence_count,
            ),
            reverse=True,
        )
        return ranked[:top_k]

    @staticmethod
    def _value_factor(memory: Memory) -> float:
        if memory.kind == "WARNING":
            # Strong negative evidence is useful because it prevents repetition.
            return 0.5 + 0.5 * abs(memory.value)
        # Productive positive memories rise; weak/negative tactics remain visible
        # but are naturally demoted rather than deleted.
        return 0.25 + 0.75 * ((memory.value + 1.0) / 2.0)

    @staticmethod
    def _scope_factor(memory_scope: str, requested_scope: str) -> float:
        if memory_scope == requested_scope:
            return 1.0
        if memory_scope == "global":
            return 0.85
        if requested_scope == "global":
            return 0.65
        return 0.35

    @staticmethod
    def _check_value(value: float) -> None:
        if not -1.0 <= float(value) <= 1.0:
            raise ValueError("value/reward must be within [-1, 1]")

    @staticmethod
    def _check_unit_interval(value: float, label: str) -> None:
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"{label} must be within [0, 1]")

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Memory:
        return Memory(
            id=row["id"],
            text=row["text"],
            kind=row["kind"],
            objective_scope=row["objective_scope"],
            value=float(row["value"]),
            confidence=float(row["confidence"]),
            evidence_count=int(row["evidence_count"]),
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
            metadata=json.loads(row["metadata_json"]),
        )


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 1
    }


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0
