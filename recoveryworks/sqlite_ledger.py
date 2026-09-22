"""Durable tamper-evident SQLite Recovery Ledger.

The in-memory RecoveryLedger remains the authoritative transition state machine.
This wrapper persists the resulting states and an append-only per-case event hash
chain, then replays those events on process restart.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any, Callable

from .ledger import LedgerRecord, RecoveryLedger
from .models import RecoveryFinding, canonical_hash
from .serde import finding_from_dict, finding_to_dict, record_to_dict


class SQLiteRecoveryLedger:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._init_schema()
        self._ledger = RecoveryLedger()
        self._rehydrate()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        return con

    def _init_schema(self) -> None:
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS recovery_events (
                    finding_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    prev_event_hash TEXT,
                    event_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (finding_id, seq)
                );

                CREATE TABLE IF NOT EXISTS recovery_snapshots (
                    finding_id TEXT PRIMARY KEY,
                    proof_hash TEXT NOT NULL UNIQUE,
                    record_hash TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS ix_recovery_events_finding
                    ON recovery_events(finding_id, seq);
                """
            )

    @staticmethod
    def _event_hash(
        finding_id: str,
        seq: int,
        event_type: str,
        payload: dict[str, Any],
        prev_event_hash: str | None,
    ) -> str:
        return canonical_hash({
            "schema": 1,
            "finding_id": finding_id,
            "seq": seq,
            "event_type": event_type,
            "payload": payload,
            "prev_event_hash": prev_event_hash,
        })

    def _persist(self, event_type: str, record: LedgerRecord, payload: dict[str, Any]) -> None:
        finding_id = record.finding.finding_id
        with self._connect() as con:
            last = con.execute(
                """
                SELECT seq, event_hash
                FROM recovery_events
                WHERE finding_id = ?
                ORDER BY seq DESC
                LIMIT 1
                """,
                (finding_id,),
            ).fetchone()
            seq = 1 if last is None else int(last["seq"]) + 1
            prev_hash = None if last is None else last["event_hash"]
            event_hash = self._event_hash(finding_id, seq, event_type, payload, prev_hash)
            con.execute(
                """
                INSERT INTO recovery_events(
                    finding_id, seq, event_type, payload_json, prev_event_hash, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    finding_id,
                    seq,
                    event_type,
                    json.dumps(payload, sort_keys=True, separators=(",", ":")),
                    prev_hash,
                    event_hash,
                ),
            )
            record_json = json.dumps(record_to_dict(record), sort_keys=True, separators=(",", ":"))
            con.execute(
                """
                INSERT INTO recovery_snapshots(
                    finding_id, proof_hash, record_hash, record_json, updated_at
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(finding_id) DO UPDATE SET
                    proof_hash=excluded.proof_hash,
                    record_hash=excluded.record_hash,
                    record_json=excluded.record_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    finding_id,
                    record.finding.proof_hash,
                    record.record_hash,
                    record_json,
                ),
            )

    def _reload_after_failure(self) -> None:
        self._ledger = RecoveryLedger()
        self._rehydrate()

    def _apply_and_persist(
        self,
        finding_id: str,
        event_type: str,
        payload: dict[str, Any],
        transition: Callable[[], LedgerRecord],
    ) -> LedgerRecord:
        before = self._ledger.get(finding_id)
        after = transition()
        if after.record_hash == before.record_hash:
            return after
        try:
            self._persist(event_type, after, payload)
        except Exception:
            self._reload_after_failure()
            raise
        return after

    def add(self, finding: RecoveryFinding) -> LedgerRecord:
        try:
            existing = self._ledger.add(finding)
        except Exception:
            raise
        # Exact proof replay is idempotent and must not create a second ADD event.
        with self._connect() as con:
            exists = con.execute(
                "SELECT 1 FROM recovery_snapshots WHERE finding_id = ?",
                (existing.finding.finding_id,),
            ).fetchone()
        if exists:
            return existing
        try:
            self._persist("ADD", existing, {"finding": finding_to_dict(finding)})
        except Exception:
            self._reload_after_failure()
            raise
        return existing

    def approve(self, finding_id: str, reviewer_id: str, note: str) -> LedgerRecord:
        return self._apply_and_persist(
            finding_id,
            "APPROVE",
            {"reviewer_id": reviewer_id, "note": note},
            lambda: self._ledger.approve(finding_id, reviewer_id, note),
        )

    def authorize(self, finding_id: str, authorization_id: str) -> LedgerRecord:
        return self._apply_and_persist(
            finding_id,
            "AUTHORIZE",
            {"authorization_id": authorization_id},
            lambda: self._ledger.authorize(finding_id, authorization_id),
        )

    def mark_claimed(self, finding_id: str) -> LedgerRecord:
        return self._apply_and_persist(
            finding_id,
            "CLAIM",
            {},
            lambda: self._ledger.mark_claimed(finding_id),
        )

    def mark_recovered(self, finding_id: str, recovered_cents: int, fee_cents: int = 0) -> LedgerRecord:
        return self._apply_and_persist(
            finding_id,
            "RECOVER",
            {"recovered_cents": recovered_cents, "fee_cents": fee_cents},
            lambda: self._ledger.mark_recovered(finding_id, recovered_cents, fee_cents),
        )

    def reject(self, finding_id: str, reviewer_id: str, note: str) -> LedgerRecord:
        return self._apply_and_persist(
            finding_id,
            "REJECT",
            {"reviewer_id": reviewer_id, "note": note},
            lambda: self._ledger.reject(finding_id, reviewer_id, note),
        )

    def get(self, finding_id: str) -> LedgerRecord:
        return self._ledger.get(finding_id)

    def records(self) -> tuple[LedgerRecord, ...]:
        return self._ledger.records()

    def rollup(self) -> dict:
        return self._ledger.rollup()

    def _rehydrate(self) -> None:
        self.verify_event_chains()
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT finding_id, seq, event_type, payload_json
                FROM recovery_events
                ORDER BY finding_id, seq
                """
            ).fetchall()
        for row in rows:
            payload = json.loads(row["payload_json"])
            finding_id = row["finding_id"]
            event_type = row["event_type"]
            if event_type == "ADD":
                self._ledger.add(finding_from_dict(payload["finding"]))
            elif event_type == "APPROVE":
                self._ledger.approve(finding_id, payload["reviewer_id"], payload["note"])
            elif event_type == "AUTHORIZE":
                self._ledger.authorize(finding_id, payload["authorization_id"])
            elif event_type == "CLAIM":
                self._ledger.mark_claimed(finding_id)
            elif event_type == "RECOVER":
                self._ledger.mark_recovered(
                    finding_id,
                    payload["recovered_cents"],
                    payload.get("fee_cents", 0),
                )
            elif event_type == "REJECT":
                self._ledger.reject(finding_id, payload["reviewer_id"], payload["note"])
            else:
                raise ValueError(f"unknown recovery event type: {event_type}")

        # A valid chain is not enough: the persisted snapshot must equal replayed state.
        with self._connect() as con:
            snapshots = {
                row["finding_id"]: row
                for row in con.execute(
                    "SELECT finding_id, proof_hash, record_hash FROM recovery_snapshots"
                ).fetchall()
            }
        for record in self._ledger.records():
            snapshot = snapshots.get(record.finding.finding_id)
            if snapshot is None:
                raise ValueError("missing recovery snapshot for event-backed case")
            if snapshot["proof_hash"] != record.finding.proof_hash:
                raise ValueError("recovery snapshot proof hash mismatch")
            if snapshot["record_hash"] != record.record_hash:
                raise ValueError("recovery snapshot record hash mismatch")

    def verify_event_chains(self) -> None:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT finding_id, seq, event_type, payload_json, prev_event_hash, event_hash
                FROM recovery_events
                ORDER BY finding_id, seq
                """
            ).fetchall()

        prior_by_finding: dict[str, str | None] = {}
        seq_by_finding: dict[str, int] = {}
        for row in rows:
            finding_id = row["finding_id"]
            expected_seq = seq_by_finding.get(finding_id, 0) + 1
            if row["seq"] != expected_seq:
                raise ValueError("recovery event sequence gap or replay detected")
            expected_prev = prior_by_finding.get(finding_id)
            if row["prev_event_hash"] != expected_prev:
                raise ValueError("recovery event previous-hash mismatch")
            payload = json.loads(row["payload_json"])
            expected_hash = self._event_hash(
                finding_id,
                row["seq"],
                row["event_type"],
                payload,
                row["prev_event_hash"],
            )
            if row["event_hash"] != expected_hash:
                raise ValueError("recovery event hash mismatch")
            prior_by_finding[finding_id] = row["event_hash"]
            seq_by_finding[finding_id] = row["seq"]
