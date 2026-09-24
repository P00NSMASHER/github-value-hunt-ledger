"""Value-weighted memory for AI Business OS.

Retrieval ranks memories by relevance x observed value x confidence x recency.
The store is intentionally deterministic and stdlib-only. Learned value is an
advisory retrieval prior; it never grants action authority or bypasses audits.
"""
from __future__ import annotations

import contextlib
import dataclasses
import json
import math
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Iterable


_TOKEN_RE = re.compile(r"[a-z0-9]+")


class MemoryError(ValueError):
    pass


@dataclasses.dataclass(frozen=True)
class MemoryItem:
    id: str
    scope: str
    content: str
    tags: tuple[str, ...]
    metadata: dict[str, Any]
    created_at: float
    updated_at: float
    observation_count: int
    value_mean: float
    confidence: float


@dataclasses.dataclass(frozen=True)
class RankedMemory:
    item: MemoryItem
    relevance: float
    observed_value: float
    confidence: float
    recency: float
    score: float


class ValueMemoryStore:
    """SQLite-backed memory whose ranking is tied to observed usefulness.

    Invariants:
    - memories are isolated by explicit scope;
    - observations are append-only and bounded to [0, 1];
    - value/confidence are derived from observation history, not model claims;
    - retrieval factors are exposed so a ranking can be audited;
    - value affects retrieval only and cannot authorize actions.
    """

    def __init__(
        self,
        db_path: str | Path = "ai_business_os.sqlite3",
        *,
        prior_value: float = 0.5,
        prior_confidence: float = 0.20,
        confidence_scale: float = 3.0,
    ) -> None:
        if not 0.0 <= prior_value <= 1.0:
            raise MemoryError("prior_value must be within [0, 1]")
        if not 0.0 < prior_confidence <= 1.0:
            raise MemoryError("prior_confidence must be within (0, 1]")
        if confidence_scale <= 0:
            raise MemoryError("confidence_scale must be > 0")
        self.db_path = str(db_path)
        self.prior_value = float(prior_value)
        self.prior_confidence = float(prior_confidence)
        self.confidence_scale = float(confidence_scale)
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
                CREATE TABLE IF NOT EXISTS value_memory_items (
                    id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_value_memory_scope
                    ON value_memory_items(scope, updated_at DESC);

                CREATE TABLE IF NOT EXISTS value_memory_observations (
                    id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL REFERENCES value_memory_items(id),
                    usefulness REAL NOT NULL,
                    weight REAL NOT NULL,
                    observed_at REAL NOT NULL,
                    outcome_ref TEXT NOT NULL,
                    CHECK (usefulness >= 0.0 AND usefulness <= 1.0),
                    CHECK (weight > 0.0)
                );

                CREATE INDEX IF NOT EXISTS idx_value_memory_observations
                    ON value_memory_observations(memory_id, observed_at ASC);
                """
            )

    @staticmethod
    def _now(now: float | None = None) -> float:
        return time.time() if now is None else float(now)

    def add_memory(
        self,
        scope: str,
        content: str,
        *,
        tags: Iterable[str] = (),
        metadata: dict[str, Any] | None = None,
        memory_id: str | None = None,
        now: float | None = None,
    ) -> MemoryItem:
        scope = scope.strip()
        content = content.strip()
        if not scope:
            raise MemoryError("scope must be non-empty")
        if not content:
            raise MemoryError("content must be non-empty")
        normalized_tags = tuple(
            sorted({str(tag).strip().lower() for tag in tags if str(tag).strip()})
        )
        ts = self._now(now)
        memory_id = memory_id or f"mem_{uuid.uuid4().hex}"
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO value_memory_items(
                    id, scope, content, tags_json, metadata_json, created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    scope,
                    content,
                    json.dumps(normalized_tags),
                    json.dumps(metadata or {}, sort_keys=True),
                    ts,
                    ts,
                ),
            )
        return self.get_memory(memory_id)

    def record_observation(
        self,
        memory_id: str,
        usefulness: float,
        *,
        outcome_ref: str,
        weight: float = 1.0,
        now: float | None = None,
    ) -> MemoryItem:
        usefulness = float(usefulness)
        weight = float(weight)
        if not 0.0 <= usefulness <= 1.0:
            raise MemoryError("usefulness must be within [0, 1]")
        if weight <= 0.0:
            raise MemoryError("weight must be > 0")
        if not outcome_ref.strip():
            raise MemoryError("outcome_ref must bind the observation to evidence")
        ts = self._now(now)
        observation_id = f"obs_{uuid.uuid4().hex}"
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            exists = con.execute(
                "SELECT 1 FROM value_memory_items WHERE id=?", (memory_id,)
            ).fetchone()
            if exists is None:
                con.execute("ROLLBACK")
                raise KeyError(f"unknown memory: {memory_id}")
            con.execute(
                """
                INSERT INTO value_memory_observations(
                    id, memory_id, usefulness, weight, observed_at, outcome_ref
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    observation_id,
                    memory_id,
                    usefulness,
                    weight,
                    ts,
                    outcome_ref.strip(),
                ),
            )
            con.execute(
                "UPDATE value_memory_items SET updated_at=? WHERE id=?",
                (ts, memory_id),
            )
            con.execute("COMMIT")
        return self.get_memory(memory_id)

    def get_memory(self, memory_id: str) -> MemoryItem:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM value_memory_items WHERE id=?", (memory_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown memory: {memory_id}")
            stats = con.execute(
                """
                SELECT COUNT(*) AS n,
                       COALESCE(SUM(usefulness * weight), 0.0) AS weighted_value,
                       COALESCE(SUM(weight), 0.0) AS total_weight
                FROM value_memory_observations
                WHERE memory_id=?
                """,
                (memory_id,),
            ).fetchone()
        n = int(stats["n"])
        total_weight = float(stats["total_weight"])
        if total_weight > 0:
            value_mean = float(stats["weighted_value"]) / total_weight
            evidence_confidence = 1.0 - math.exp(
                -total_weight / self.confidence_scale
            )
            confidence = self.prior_confidence + (
                1.0 - self.prior_confidence
            ) * evidence_confidence
        else:
            value_mean = self.prior_value
            confidence = self.prior_confidence
        return MemoryItem(
            id=row["id"],
            scope=row["scope"],
            content=row["content"],
            tags=tuple(json.loads(row["tags_json"])),
            metadata=json.loads(row["metadata_json"]),
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
            observation_count=n,
            value_mean=value_mean,
            confidence=min(1.0, confidence),
        )

    def retrieve(
        self,
        query: str,
        *,
        scope: str,
        limit: int = 10,
        now: float | None = None,
        half_life_seconds: float = 30.0 * 24.0 * 3600.0,
        minimum_score: float = 0.0,
    ) -> tuple[RankedMemory, ...]:
        query = query.strip()
        scope = scope.strip()
        if not query:
            raise MemoryError("query must be non-empty")
        if not scope:
            raise MemoryError("scope must be non-empty")
        if limit <= 0:
            raise MemoryError("limit must be > 0")
        if half_life_seconds <= 0:
            raise MemoryError("half_life_seconds must be > 0")
        ts = self._now(now)

        with self._connect() as con:
            ids = [
                row["id"]
                for row in con.execute(
                    "SELECT id FROM value_memory_items WHERE scope=?", (scope,)
                )
            ]

        query_tokens = _tokens(query)
        ranked: list[RankedMemory] = []
        for memory_id in ids:
            item = self.get_memory(memory_id)
            candidate_tokens = _tokens(
                item.content + " " + " ".join(item.tags)
            )
            relevance = _jaccard_relevance(query_tokens, candidate_tokens)
            if relevance <= 0.0:
                continue
            age = max(0.0, ts - item.updated_at)
            recency = math.pow(0.5, age / half_life_seconds)
            observed_value = item.value_mean
            score = relevance * observed_value * item.confidence * recency
            if score < minimum_score:
                continue
            ranked.append(
                RankedMemory(
                    item=item,
                    relevance=relevance,
                    observed_value=observed_value,
                    confidence=item.confidence,
                    recency=recency,
                    score=score,
                )
            )

        ranked.sort(key=lambda x: (-x.score, -x.item.updated_at, x.item.id))
        return tuple(ranked[:limit])

    def observation_log(
        self, memory_id: str
    ) -> tuple[dict[str, Any], ...]:
        self.get_memory(memory_id)
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT id, usefulness, weight, observed_at, outcome_ref
                FROM value_memory_observations
                WHERE memory_id=?
                ORDER BY observed_at ASC, id ASC
                """,
                (memory_id,),
            ).fetchall()
        return tuple(dict(row) for row in rows)


def _tokens(text: str) -> frozenset[str]:
    return frozenset(_TOKEN_RE.findall(text.lower()))


def _jaccard_relevance(
    query_tokens: frozenset[str],
    candidate_tokens: frozenset[str],
) -> float:
    if not query_tokens or not candidate_tokens:
        return 0.0
    intersection = len(query_tokens & candidate_tokens)
    if intersection == 0:
        return 0.0
    coverage = intersection / len(query_tokens)
    jaccard = intersection / len(query_tokens | candidate_tokens)
    return 0.8 * coverage + 0.2 * jaccard
