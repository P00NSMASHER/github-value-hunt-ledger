"""Persistent scope-bound audit store for Freight Recovery pilots.

SQLite provides durable reference persistence for application audit records.
The store preserves the buyer/business-unit boundary and the hash-chain
semantics from freight.audit_ledger. It is not an external immutable logging
service and does not provide independent trusted timestamping.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Callable, TypeVar

from freight.audit_ledger import (
    AuditEventType,
    AuditRecord,
    append_record,
    chain_head,
    verify_chain,
)

T = TypeVar("T")


class AuditStore:
    def __init__(
        self,
        path: str | Path,
        *,
        buyer_id: str,
        business_unit: str,
        busy_timeout_ms: int = 5000,
    ):
        self.path = str(path)
        self.buyer_id = self._text("buyer_id", buyer_id)
        self.business_unit = self._text("business_unit", business_unit)
        if type(busy_timeout_ms) is not int or not 1 <= busy_timeout_ms <= 60_000:
            raise ValueError("busy_timeout_ms must be an integer from 1 to 60000")
        self.busy_timeout_ms = busy_timeout_ms
        if self.path == ":memory:":
            raise ValueError("file-backed SQLite is required")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        self.verify()

    def _initialize(self) -> None:
        schema = """
            CREATE TABLE IF NOT EXISTS audit_events (
                buyer_id TEXT NOT NULL,
                business_unit TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                object_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                evidence_hash TEXT,
                previous_hash TEXT,
                event_hash TEXT NOT NULL,
                PRIMARY KEY (buyer_id,business_unit,sequence),
                UNIQUE (buyer_id,business_unit,event_hash)
            );

            CREATE TRIGGER IF NOT EXISTS audit_events_immutable_update
            BEFORE UPDATE ON audit_events
            BEGIN
                SELECT RAISE(ABORT,'audit event is immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS audit_events_immutable_delete
            BEFORE DELETE ON audit_events
            BEGIN
                SELECT RAISE(ABORT,'audit event is immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS audit_events_input_guard
            BEFORE INSERT ON audit_events
            BEGIN
                SELECT CASE WHEN
                    length(NEW.occurred_at)<>27 OR
                    NEW.occurred_at NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z' OR
                    julianday(NEW.occurred_at) IS NULL OR
                    strftime('%Y-%m-%dT%H:%M:%S',NEW.occurred_at)<>substr(NEW.occurred_at,1,19)
                THEN RAISE(ABORT,'audit occurred_at must be canonical UTC') END;
                SELECT CASE WHEN
                    NEW.evidence_hash IS NOT NULL AND
                    (length(NEW.evidence_hash)<>64 OR NEW.evidence_hash GLOB '*[^0-9a-f]*')
                THEN RAISE(ABORT,'audit evidence_hash must be lowercase SHA-256') END;
                SELECT CASE WHEN NEW.sequence>1 AND NEW.occurred_at < (
                    SELECT occurred_at FROM audit_events
                    WHERE buyer_id=NEW.buyer_id AND business_unit=NEW.business_unit
                      AND sequence=NEW.sequence-1
                ) THEN RAISE(ABORT,'audit occurred_at values must be nondecreasing') END;
            END;
        """
        delay = 0.005
        last: Exception | None = None
        for _ in range(8):
            conn = self._connect()
            try:
                mode = str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
                if mode != "wal":
                    conn.execute("PRAGMA journal_mode=WAL")
                conn.executescript(schema)
                return
            except sqlite3.OperationalError as exc:
                last = exc
                if "locked" not in str(exc).lower():
                    raise
            finally:
                conn.close()
            time.sleep(delay)
            delay = min(delay * 2, 0.1)
        assert last is not None
        raise last

    @staticmethod
    def _text(name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(name + " is required")
        normalized = value.strip()
        if any(ord(character) < 32 for character in normalized):
            raise ValueError(name + " cannot contain control characters")
        return normalized

    @property
    def _scope(self) -> tuple[str, str]:
        return self.buyer_id, self.business_unit

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.path,
            timeout=self.busy_timeout_ms / 1000,
            isolation_level=None,
        )
        conn.row_factory = sqlite3.Row
        conn.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
        return conn

    def _write(self, fn: Callable[[sqlite3.Connection], T]) -> T:
        delay = 0.005
        last: Exception | None = None
        for _ in range(8):
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                out = fn(conn)
                conn.commit()
                return out
            except sqlite3.OperationalError as exc:
                conn.rollback()
                last = exc
                if "locked" not in str(exc).lower():
                    raise
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
            time.sleep(delay)
            delay = min(delay * 2, 0.1)
        assert last is not None
        raise last

    def _read(self, fn: Callable[[sqlite3.Connection], T]) -> T:
        conn = self._connect()
        try:
            return fn(conn)
        finally:
            conn.close()

    @staticmethod
    def _record(row: sqlite3.Row) -> AuditRecord:
        return AuditRecord(
            sequence=int(row["sequence"]),
            buyer_id=row["buyer_id"],
            business_unit=row["business_unit"],
            event_type=AuditEventType(row["event_type"]),
            object_id=row["object_id"],
            occurred_at=row["occurred_at"],
            evidence_hash=row["evidence_hash"],
            previous_hash=row["previous_hash"],
            event_hash=row["event_hash"],
        )

    def _records(self, conn: sqlite3.Connection) -> tuple[AuditRecord, ...]:
        rows = conn.execute(
            """SELECT * FROM audit_events
               WHERE buyer_id=? AND business_unit=?
               ORDER BY sequence""",
            self._scope,
        ).fetchall()
        return tuple(self._record(row) for row in rows)

    def records(self) -> tuple[AuditRecord, ...]:
        return self._read(self._records)

    def append(
        self,
        *,
        event_type: AuditEventType,
        object_id: str,
        occurred_at: str,
        evidence_hash: str | None = None,
    ) -> AuditRecord:
        def op(conn: sqlite3.Connection) -> AuditRecord:
            records = self._records(conn)
            verify_chain(
                records,
                buyer_id=self.buyer_id,
                business_unit=self.business_unit,
            )
            updated = append_record(
                records,
                buyer_id=self.buyer_id,
                business_unit=self.business_unit,
                event_type=event_type,
                object_id=object_id,
                occurred_at=occurred_at,
                evidence_hash=evidence_hash,
            )
            record = updated[-1]
            conn.execute(
                """INSERT INTO audit_events
                   (buyer_id,business_unit,sequence,event_type,object_id,
                    occurred_at,evidence_hash,previous_hash,event_hash)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    record.buyer_id,
                    record.business_unit,
                    record.sequence,
                    record.event_type.value,
                    record.object_id,
                    record.occurred_at,
                    record.evidence_hash,
                    record.previous_hash,
                    record.event_hash,
                ),
            )
            return record
        return self._write(op)

    def verify(self) -> None:
        verify_chain(
            self.records(),
            buyer_id=self.buyer_id,
            business_unit=self.business_unit,
        )

    def count(self) -> int:
        return self._read(
            lambda conn: int(
                conn.execute(
                    """SELECT COUNT(*) FROM audit_events
                       WHERE buyer_id=? AND business_unit=?""",
                    self._scope,
                ).fetchone()[0]
            )
        )

    def head(self) -> str | None:
        return chain_head(self.records())

    def semantic_summary(self) -> dict:
        self.verify()
        return {
            "buyer_id": self.buyer_id,
            "business_unit": self.business_unit,
            "record_count": self.count(),
            "chain_head": self.head(),
        }
