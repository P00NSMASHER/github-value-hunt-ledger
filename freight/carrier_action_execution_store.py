"""Persistent idempotency and evidence ledger for carrier actions.

Evidence rows are immutable. A small transient send-slot table enforces one
active sender per buyer/business-unit/execution key. A successful submission is
also protected by a SQLite partial unique index, so duplicate sends remain
blocked across process restarts and concurrent workers.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TypeVar

from freight.carrier_action_execution import (
    CarrierActionDeliveryReceipt,
    CarrierActionExecutionIntent,
    CarrierActionExecutionReceipt,
    verify_carrier_action_delivery_receipt,
    verify_carrier_action_execution_intent_proof,
    verify_carrier_action_execution_receipt,
)
from freight.contracts import canonical_hash


RESERVED = "RESERVED"
ALREADY_RESERVED = "ALREADY_RESERVED"
IN_FLIGHT = "IN_FLIGHT"
ALREADY_SUBMITTED = "ALREADY_SUBMITTED"
RECORDED = "RECORDED"
ALREADY_RECORDED = "ALREADY_RECORDED"
DELIVERY_RECORDED = "DELIVERY_RECORDED"
ALREADY_DELIVERED = "ALREADY_DELIVERED"

NOT_FOUND = "NOT_FOUND"
PREPARED = "PREPARED"
FAILED_ONLY = "FAILED_ONLY"
SUBMITTED = "SUBMITTED"
DELIVERED = "DELIVERED"

T = TypeVar("T")


@dataclass(frozen=True)
class SendAttemptDecision:
    status: str
    execution_key: str
    attempt_id: str | None
    reservation_hash: str | None
    reason: str


@dataclass(frozen=True)
class ExecutionLedgerState:
    execution_key: str
    state: str
    intent_hash: str | None
    active_attempt_id: str | None
    failed_attempt_count: int
    successful_receipt_hash: str | None
    delivery_receipt_hash: str | None
    snapshot_hash: str


class CarrierActionExecutionStore:
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
        self.busy_timeout_ms = busy_timeout_ms
        if self.path == ":memory:":
            raise ValueError("file-backed SQLite is required for concurrent execution locking")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(
                Path(__file__).with_name("carrier_action_execution_schema.sql").read_text()
            )
            self._assert_schema(conn)

    @staticmethod
    def _assert_schema(conn: sqlite3.Connection) -> None:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(carrier_execution_intents)")}
        if not {"buyer_id", "business_unit", "execution_key", "intent_hash"}.issubset(cols):
            raise RuntimeError("legacy/unscoped carrier execution schema detected")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.path,
            timeout=self.busy_timeout_ms / 1000,
            isolation_level=None,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
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
    def _text(name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(name + " is required")
        return value.strip()

    @staticmethod
    def _timestamp(name: str, value: str) -> str:
        text = CarrierActionExecutionStore._text(name, value)
        normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(name + " must be timezone-aware ISO-8601") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError(name + " must be timezone-aware ISO-8601")
        return (
            parsed.astimezone(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )

    @staticmethod
    def _json(value: object) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @property
    def _scope(self) -> tuple[str, str]:
        return self.buyer_id, self.business_unit

    def _require_intent_scope(self, intent: CarrierActionExecutionIntent) -> None:
        verify_carrier_action_execution_intent_proof(intent)
        if (intent.buyer_id, intent.business_unit) != self._scope:
            raise ValueError("execution intent scope does not match store")

    def _intent_values(self, intent: CarrierActionExecutionIntent) -> dict[str, object]:
        self._require_intent_scope(intent)
        return {
            "buyer_id": self.buyer_id,
            "business_unit": self.business_unit,
            "execution_key": intent.execution_key,
            "intent_hash": intent.intent_hash,
            "prepared_at": intent.prepared_at,
            "intent_json": self._json(asdict(intent)),
        }

    def _ensure_intent(self, conn: sqlite3.Connection, intent: CarrierActionExecutionIntent) -> None:
        v = self._intent_values(intent)
        old = conn.execute(
            """SELECT * FROM carrier_execution_intents
               WHERE buyer_id=? AND business_unit=? AND execution_key=?""",
            (*self._scope, intent.execution_key),
        ).fetchone()
        if old:
            if (
                old["intent_hash"] == v["intent_hash"]
                and old["prepared_at"] == v["prepared_at"]
                and old["intent_json"] == v["intent_json"]
            ):
                return
            raise ValueError("execution_key replay conflicts with immutable execution intent")
        conn.execute(
            """INSERT INTO carrier_execution_intents
               (buyer_id,business_unit,execution_key,intent_hash,prepared_at,intent_json)
               VALUES(:buyer_id,:business_unit,:execution_key,:intent_hash,:prepared_at,:intent_json)""",
            v,
        )

    def reserve_send_attempt(
        self,
        intent: CarrierActionExecutionIntent,
        *,
        attempt_id: str,
        started_at: str,
    ) -> SendAttemptDecision:
        self._require_intent_scope(intent)
        attempt_id = self._text("attempt_id", attempt_id)
        started_at = self._timestamp("started_at", started_at)
        if started_at < intent.prepared_at:
            raise ValueError("send attempt cannot start before intent preparation")
        attempt_body = {
            "schema": 1,
            "buyer_id": self.buyer_id,
            "business_unit": self.business_unit,
            "attempt_id": attempt_id,
            "execution_key": intent.execution_key,
            "intent_hash": intent.intent_hash,
            "started_at": started_at,
        }
        attempt_hash = canonical_hash(attempt_body)

        def op(conn: sqlite3.Connection) -> SendAttemptDecision:
            self._ensure_intent(conn, intent)

            submitted = conn.execute(
                """SELECT receipt_hash FROM carrier_execution_receipts
                   WHERE buyer_id=? AND business_unit=? AND execution_key=?
                     AND action_submitted=1 LIMIT 1""",
                (*self._scope, intent.execution_key),
            ).fetchone()
            if submitted:
                return SendAttemptDecision(
                    ALREADY_SUBMITTED,
                    intent.execution_key,
                    None,
                    None,
                    "execution key already has a submitted action",
                )

            slot = conn.execute(
                """SELECT * FROM carrier_execution_send_slots
                   WHERE buyer_id=? AND business_unit=? AND execution_key=?""",
                (*self._scope, intent.execution_key),
            ).fetchone()
            if slot:
                if slot["attempt_id"] == attempt_id:
                    attempt = conn.execute(
                        """SELECT * FROM carrier_execution_attempts
                           WHERE buyer_id=? AND business_unit=? AND attempt_id=?""",
                        (*self._scope, attempt_id),
                    ).fetchone()
                    if attempt and attempt["attempt_hash"] == attempt_hash:
                        return SendAttemptDecision(
                            ALREADY_RESERVED,
                            intent.execution_key,
                            attempt_id,
                            attempt_hash,
                            "exact send attempt already owns the execution slot",
                        )
                    raise ValueError("active attempt replay conflicts with immutable attempt")
                return SendAttemptDecision(
                    IN_FLIGHT,
                    intent.execution_key,
                    slot["attempt_id"],
                    None,
                    "another send attempt currently owns the execution slot",
                )

            old_attempt = conn.execute(
                """SELECT * FROM carrier_execution_attempts
                   WHERE buyer_id=? AND business_unit=? AND attempt_id=?""",
                (*self._scope, attempt_id),
            ).fetchone()
            if old_attempt:
                if old_attempt["attempt_hash"] == attempt_hash:
                    raise ValueError(
                        "attempt_id already reached a terminal state; use a new attempt_id"
                    )
                raise ValueError("attempt_id replay conflicts with immutable attempt")

            conn.execute(
                """INSERT INTO carrier_execution_attempts
                   (buyer_id,business_unit,attempt_id,execution_key,intent_hash,started_at,attempt_hash)
                   VALUES(?,?,?,?,?,?,?)""",
                (
                    *self._scope,
                    attempt_id,
                    intent.execution_key,
                    intent.intent_hash,
                    started_at,
                    attempt_hash,
                ),
            )
            conn.execute(
                """INSERT INTO carrier_execution_send_slots
                   (buyer_id,business_unit,execution_key,attempt_id,acquired_at)
                   VALUES(?,?,?,?,?)""",
                (*self._scope, intent.execution_key, attempt_id, started_at),
            )
            return SendAttemptDecision(
                RESERVED,
                intent.execution_key,
                attempt_id,
                attempt_hash,
                "exclusive send slot reserved",
            )

        return self._write(op)

    def record_execution_receipt(
        self,
        *,
        attempt_id: str,
        receipt: CarrierActionExecutionReceipt,
    ) -> str:
        attempt_id = self._text("attempt_id", attempt_id)
        verify_carrier_action_execution_receipt(receipt)
        if (receipt.buyer_id, receipt.business_unit) != self._scope:
            raise ValueError("execution receipt scope does not match store")

        receipt_json = self._json(asdict(receipt))

        def op(conn: sqlite3.Connection) -> str:
            existing_attempt_receipt = conn.execute(
                """SELECT * FROM carrier_execution_receipts
                   WHERE buyer_id=? AND business_unit=? AND attempt_id=?""",
                (*self._scope, attempt_id),
            ).fetchone()
            if existing_attempt_receipt:
                if (
                    existing_attempt_receipt["receipt_hash"] == receipt.receipt_hash
                    and existing_attempt_receipt["receipt_json"] == receipt_json
                ):
                    return ALREADY_RECORDED
                raise ValueError("attempt_id already has a different immutable receipt")

            attempt = conn.execute(
                """SELECT * FROM carrier_execution_attempts
                   WHERE buyer_id=? AND business_unit=? AND attempt_id=?""",
                (*self._scope, attempt_id),
            ).fetchone()
            if not attempt:
                raise ValueError("execution receipt references unknown send attempt")
            if attempt["execution_key"] != receipt.execution_key:
                raise ValueError("execution receipt key does not match send attempt")
            if attempt["intent_hash"] != receipt.intent_hash:
                raise ValueError("execution receipt intent does not match send attempt")
            if receipt.executed_at < attempt["started_at"]:
                raise ValueError("execution receipt predates send attempt")

            slot = conn.execute(
                """SELECT attempt_id FROM carrier_execution_send_slots
                   WHERE buyer_id=? AND business_unit=? AND execution_key=?""",
                (*self._scope, receipt.execution_key),
            ).fetchone()
            if not slot or slot["attempt_id"] != attempt_id:
                raise ValueError("send attempt does not own the active execution slot")

            try:
                conn.execute(
                    """INSERT INTO carrier_execution_receipts
                       (buyer_id,business_unit,receipt_hash,execution_key,attempt_id,intent_hash,
                        outcome,action_submitted,delivery_confirmed,executed_at,receipt_json)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        *self._scope,
                        receipt.receipt_hash,
                        receipt.execution_key,
                        attempt_id,
                        receipt.intent_hash,
                        receipt.outcome,
                        int(receipt.action_submitted),
                        int(receipt.delivery_confirmed),
                        receipt.executed_at,
                        receipt_json,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                if receipt.action_submitted:
                    raise ValueError(
                        "execution key already has a successful submitted action"
                    ) from exc
                raise
            conn.execute(
                """DELETE FROM carrier_execution_send_slots
                   WHERE buyer_id=? AND business_unit=? AND execution_key=?
                     AND attempt_id=?""",
                (*self._scope, receipt.execution_key, attempt_id),
            )
            return RECORDED

        return self._write(op)

    def record_delivery_receipt(
        self,
        receipt: CarrierActionDeliveryReceipt,
    ) -> str:
        verify_carrier_action_delivery_receipt(receipt)
        if (receipt.buyer_id, receipt.business_unit) != self._scope:
            raise ValueError("delivery receipt scope does not match store")
        delivery_json = self._json(asdict(receipt))

        def op(conn: sqlite3.Connection) -> str:
            existing = conn.execute(
                """SELECT * FROM carrier_delivery_receipts
                   WHERE buyer_id=? AND business_unit=? AND execution_key=?""",
                (*self._scope, receipt.execution_key),
            ).fetchone()
            if existing:
                if (
                    existing["delivery_receipt_hash"] == receipt.delivery_receipt_hash
                    and existing["delivery_json"] == delivery_json
                ):
                    return ALREADY_DELIVERED
                raise ValueError(
                    "execution key already has a different delivery confirmation"
                )

            submitted = conn.execute(
                """SELECT * FROM carrier_execution_receipts
                   WHERE buyer_id=? AND business_unit=? AND receipt_hash=?""",
                (*self._scope, receipt.submitted_receipt_hash),
            ).fetchone()
            if not submitted:
                raise ValueError("delivery receipt references unknown submitted receipt")
            if not submitted["action_submitted"]:
                raise ValueError("delivery receipt requires submitted execution")
            if submitted["delivery_confirmed"]:
                raise ValueError("execution receipt already confirmed delivery")
            if submitted["execution_key"] != receipt.execution_key:
                raise ValueError("delivery receipt execution key mismatch")
            if receipt.delivered_at < submitted["executed_at"]:
                raise ValueError("delivery receipt predates submitted execution")

            conn.execute(
                """INSERT INTO carrier_delivery_receipts
                   (buyer_id,business_unit,delivery_receipt_hash,execution_key,
                    submitted_receipt_hash,delivered_at,delivery_json)
                   VALUES(?,?,?,?,?,?,?)""",
                (
                    *self._scope,
                    receipt.delivery_receipt_hash,
                    receipt.execution_key,
                    receipt.submitted_receipt_hash,
                    receipt.delivered_at,
                    delivery_json,
                ),
            )
            return DELIVERY_RECORDED

        return self._write(op)

    def _snapshot_conn(self, conn: sqlite3.Connection) -> str:
        tables = (
            "carrier_execution_intents",
            "carrier_execution_attempts",
            "carrier_execution_send_slots",
            "carrier_execution_receipts",
            "carrier_delivery_receipts",
        )
        body: dict[str, list[dict]] = {"schema": 1}
        for table in tables:
            rows = conn.execute(
                f"""SELECT * FROM {table}
                    WHERE buyer_id=? AND business_unit=?
                    ORDER BY 1,2,3""",
                self._scope,
            ).fetchall()
            body[table] = [dict(row) for row in rows]
        return canonical_hash(body)

    def snapshot_hash(self) -> str:
        return self._read(self._snapshot_conn)

    def execution_state(self, execution_key: str) -> ExecutionLedgerState:
        execution_key = self._text("execution_key", execution_key)

        def read(conn: sqlite3.Connection) -> ExecutionLedgerState:
            intent = conn.execute(
                """SELECT * FROM carrier_execution_intents
                   WHERE buyer_id=? AND business_unit=? AND execution_key=?""",
                (*self._scope, execution_key),
            ).fetchone()
            snapshot = self._snapshot_conn(conn)
            if not intent:
                return ExecutionLedgerState(
                    execution_key, NOT_FOUND, None, None, 0, None, None, snapshot
                )

            delivery = conn.execute(
                """SELECT delivery_receipt_hash FROM carrier_delivery_receipts
                   WHERE buyer_id=? AND business_unit=? AND execution_key=?""",
                (*self._scope, execution_key),
            ).fetchone()
            successful = conn.execute(
                """SELECT receipt_hash,delivery_confirmed FROM carrier_execution_receipts
                   WHERE buyer_id=? AND business_unit=? AND execution_key=?
                     AND action_submitted=1 LIMIT 1""",
                (*self._scope, execution_key),
            ).fetchone()
            slot = conn.execute(
                """SELECT attempt_id FROM carrier_execution_send_slots
                   WHERE buyer_id=? AND business_unit=? AND execution_key=?""",
                (*self._scope, execution_key),
            ).fetchone()
            failed_count = int(
                conn.execute(
                    """SELECT COUNT(*) FROM carrier_execution_receipts
                       WHERE buyer_id=? AND business_unit=? AND execution_key=?
                         AND outcome='FAILED'""",
                    (*self._scope, execution_key),
                ).fetchone()[0]
            )

            if delivery or (successful and successful["delivery_confirmed"]):
                state = DELIVERED
            elif successful:
                state = SUBMITTED
            elif slot:
                state = IN_FLIGHT
            elif failed_count:
                state = FAILED_ONLY
            else:
                state = PREPARED

            return ExecutionLedgerState(
                execution_key=execution_key,
                state=state,
                intent_hash=intent["intent_hash"],
                active_attempt_id=slot["attempt_id"] if slot else None,
                failed_attempt_count=failed_count,
                successful_receipt_hash=successful["receipt_hash"] if successful else None,
                delivery_receipt_hash=delivery["delivery_receipt_hash"] if delivery else None,
                snapshot_hash=snapshot,
            )

        return self._read(read)
