"""Persistent scope-bound audit store for Freight Recovery pilots.

SQLite provides durable reference persistence for application audit records.
The store preserves the buyer/business-unit boundary and the hash-chain
semantics from freight.audit_ledger. It is not an external immutable logging
service and does not provide independent trusted timestamping.
"""
from __future__ import annotations

import os
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
        if str(path) == ":memory:":
            raise ValueError("file-backed SQLite is required")
        self.path = str(Path(path).absolute())
        self.buyer_id = self._text("buyer_id", buyer_id)
        self.business_unit = self._text("business_unit", business_unit)
        if type(busy_timeout_ms) is not int or not 1 <= busy_timeout_ms <= 60_000:
            raise ValueError("busy_timeout_ms must be an integer from 1 to 60000")
        self.busy_timeout_ms = busy_timeout_ms
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        from freight.settlement_file_identity_m47 import (
            create_exclusive_empty, identity,
        )
        # M48 closes AuditStore's preexisting create-on-read and
        # auto-repair-on-open vulnerabilities, analogous to SettlementStore.
        # Symlinks and deleted-main/orphan-sidecar files are never adopted.
        is_existing=os.path.lexists(self.path)
        if not is_existing:
            create_exclusive_empty(self.path)
        self._pinned_audit_file_identity=identity(self.path)
        self._initialize(is_new=not is_existing)
        self.verify()

    def _assert_source_identity(self) -> None:
        from freight.settlement_file_identity_m47 import assert_identity
        assert_identity(self.path, self._pinned_audit_file_identity)

    def _initialize(self, *, is_new: bool) -> None:
        from freight.audit_store_integrity_m48 import (
            verify_audit_connection, SCHEMA_PATH,
        )
        delay=0.005
        last=None
        for _ in range(8):
            conn=None
            try:
                conn=self._connect()
                mode=str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
                if is_new:
                    if mode!="wal":
                        conn.execute("PRAGMA journal_mode=WAL")
                    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
                elif mode!="wal":
                    # Do not silently mutate the journal mode of an existing
                    # unfamiliar source; require separately reviewed migration.
                    raise RuntimeError("M48_AUDIT_EXISTING_JOURNAL_MODE_UNREVIEWED")
                conn.execute("BEGIN")
                try:
                    # Reopen verifies approved DDL and ALL tenant chains in
                    # the same consistent read-only SQLite revision.
                    verify_audit_connection(conn,scope=None)
                finally:
                    conn.rollback()
                self._assert_source_identity()
                return
            except sqlite3.OperationalError as exc:
                last=exc
                if "locked" not in str(exc).lower():
                    raise
            except RuntimeError as exc:
                # If a second constructor won the same exclusive file
                # creation race, it may still be executing first-time DDL.
                # Bounded retries may observe the completed schema. Never
                # auto-repair a permanently incomplete existing source.
                if (
                    is_new or not any(label in str(exc) for label in (
                        "M48_AUDIT_SCHEMA_CATALOG_DRIFT",
                        "M48_AUDIT_EXISTING_JOURNAL_MODE_UNREVIEWED",
                    ))
                ):
                    raise
                last=exc
            finally:
                if conn is not None:
                    conn.close()
            time.sleep(delay)
            delay=min(delay*2,0.1)
        if last is not None:
            raise last
        raise RuntimeError("M48_AUDIT_CONSTRUCTOR_FAILED")

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
        self._assert_source_identity()
        try:
            conn=sqlite3.connect(
                Path(self.path).as_uri()+"?mode=rw",
                uri=True,
                timeout=self.busy_timeout_ms/1000,
                isolation_level=None,
            )
        except sqlite3.OperationalError as exc:
            self._assert_source_identity()
            raise RuntimeError("M48_AUDIT_FILE_CONNECT_FAILED") from exc
        try:
            self._assert_source_identity()
            conn.row_factory=sqlite3.Row
            conn.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
            return conn
        except BaseException:
            conn.close()
            raise

    def _write(self, fn: Callable[[sqlite3.Connection], T]) -> T:
        delay = 0.005
        last: Exception | None = None
        for _ in range(8):
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                from freight.audit_store_integrity_m48 import verify_audit_connection
                verify_audit_connection(conn,scope=self._scope)
                out = fn(conn)
                verify_audit_connection(conn,scope=self._scope)
                self._assert_source_identity()
                conn.commit()
                self._assert_source_identity()
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
        conn=self._connect()
        try:
            conn.execute("BEGIN")
            try:
                from freight.audit_store_integrity_m48 import verify_audit_connection
                verify_audit_connection(conn,scope=self._scope)
                result=fn(conn)
                self._assert_source_identity()
                return result
            finally:
                conn.rollback()
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
