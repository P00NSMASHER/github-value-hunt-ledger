"""Durable autonomous software work factory for AI Business OS.

The factory converts an approved engineering work item into an isolated,
restart-safe implementation attempt. No attempt becomes PR-ready until an
independent Upgrade-2 audit receipt accepts the exact executor submission.
"""
from __future__ import annotations

import dataclasses
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from business_os.audit.acceptance import (
    AcceptanceContract,
    AuditReceipt,
    ExecutorSubmission,
)


ACTIVE_STATES = {"RUNNING", "VERIFYING"}
TERMINAL_STATES = {"MERGED", "BLOCKED", "CANCELLED"}
ALL_STATES = {
    "QUEUED",
    "RUNNING",
    "VERIFYING",
    "READY_FOR_PR",
    "PR_OPEN",
    "MERGED",
    "BLOCKED",
    "CANCELLED",
}


@dataclasses.dataclass(frozen=True)
class WorkItem:
    id: str
    repository: str
    issue_ref: str
    title: str
    state: str
    contract_sha256: str
    attempts: int
    max_attempts: int
    workspace_id: str | None
    executor_id: str | None
    lease_expires_at: float | None
    current_submission_sha256: str | None
    accepted_receipt_sha256: str | None
    pr_ref: str | None
    last_error: str | None
    created_at: float
    updated_at: float


class SoftwareFactory:
    """SQLite work queue with isolated attempts and independent completion."""

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
                CREATE TABLE IF NOT EXISTS software_work_items (
                    id TEXT PRIMARY KEY,
                    repository TEXT NOT NULL,
                    issue_ref TEXT NOT NULL,
                    title TEXT NOT NULL,
                    state TEXT NOT NULL,
                    contract_sha256 TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL,
                    workspace_id TEXT,
                    executor_id TEXT,
                    lease_expires_at REAL,
                    current_submission_sha256 TEXT,
                    accepted_receipt_sha256 TEXT,
                    pr_ref TEXT,
                    last_error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS software_runs (
                    run_id TEXT PRIMARY KEY,
                    work_item_id TEXT NOT NULL REFERENCES software_work_items(id),
                    attempt INTEGER NOT NULL,
                    workspace_id TEXT NOT NULL UNIQUE,
                    executor_id TEXT NOT NULL,
                    started_at REAL NOT NULL,
                    ended_at REAL,
                    outcome TEXT,
                    submission_sha256 TEXT,
                    audit_receipt_sha256 TEXT,
                    error TEXT,
                    UNIQUE(work_item_id, attempt)
                );

                CREATE TABLE IF NOT EXISTS software_events (
                    event_id TEXT PRIMARY KEY,
                    work_item_id TEXT NOT NULL,
                    observed_at REAL NOT NULL,
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    detail_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_software_queue
                    ON software_work_items(state, created_at);
                """
            )

    def enqueue(
        self,
        repository: str,
        issue_ref: str,
        title: str,
        contract: AcceptanceContract,
        *,
        max_attempts: int = 3,
        work_item_id: str | None = None,
        now: float | None = None,
    ) -> WorkItem:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if not repository.strip() or not issue_ref.strip() or not title.strip():
            raise ValueError("repository, issue_ref and title are required")
        item_id = work_item_id or contract.task_id
        if contract.task_id != item_id:
            raise ValueError("acceptance contract task_id must equal work item id")
        ts = _now(now)
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO software_work_items(
                    id, repository, issue_ref, title, state, contract_sha256,
                    attempts, max_attempts, created_at, updated_at
                ) VALUES(?, ?, ?, ?, 'QUEUED', ?, 0, ?, ?, ?)
                """,
                (
                    item_id,
                    repository,
                    issue_ref,
                    title,
                    contract.sha256,
                    max_attempts,
                    ts,
                    ts,
                ),
            )
            self._event(
                con, item_id, ts, None, "QUEUED", "ENQUEUED",
                {"contract_sha256": contract.sha256}
            )
        return self.get(item_id)

    def get(self, work_item_id: str) -> WorkItem:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM software_work_items WHERE id=?",
                (work_item_id,),
            ).fetchone()
        if row is None:
            raise KeyError(work_item_id)
        return _item(row)

    def claim(
        self,
        work_item_id: str,
        executor_id: str,
        *,
        lease_seconds: float = 900,
        now: float | None = None,
    ) -> WorkItem:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be > 0")
        if not executor_id.strip():
            raise ValueError("executor_id cannot be empty")
        ts = _now(now)
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT * FROM software_work_items WHERE id=?",
                (work_item_id,),
            ).fetchone()
            if row is None:
                con.rollback()
                raise KeyError(work_item_id)
            if row["state"] != "QUEUED":
                con.rollback()
                raise RuntimeError(f"work item is not QUEUED: {row['state']}")
            attempt = int(row["attempts"]) + 1
            if attempt > int(row["max_attempts"]):
                con.rollback()
                raise RuntimeError("retry limit exhausted")
            workspace_id = (
                f"ws_{work_item_id}_{attempt}_{uuid.uuid4().hex[:12]}"
            )
            run_id = f"run_{uuid.uuid4().hex}"
            con.execute(
                """
                UPDATE software_work_items
                SET state='RUNNING', attempts=?, workspace_id=?,
                    executor_id=?, lease_expires_at=?,
                    current_submission_sha256=NULL,
                    accepted_receipt_sha256=NULL,
                    last_error=NULL, updated_at=?
                WHERE id=?
                """,
                (
                    attempt,
                    workspace_id,
                    executor_id,
                    ts + lease_seconds,
                    ts,
                    work_item_id,
                ),
            )
            con.execute(
                """
                INSERT INTO software_runs(
                    run_id, work_item_id, attempt, workspace_id,
                    executor_id, started_at
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    work_item_id,
                    attempt,
                    workspace_id,
                    executor_id,
                    ts,
                ),
            )
            self._event(
                con, work_item_id, ts, "QUEUED", "RUNNING", "CLAIMED",
                {"attempt": attempt, "workspace_id": workspace_id,
                 "executor_id": executor_id}
            )
            con.commit()
        return self.get(work_item_id)

    def heartbeat(
        self,
        work_item_id: str,
        executor_id: str,
        *,
        extend_seconds: float = 900,
        now: float | None = None,
    ) -> WorkItem:
        ts = _now(now)
        if extend_seconds <= 0:
            raise ValueError("extend_seconds must be > 0")
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM software_work_items WHERE id=?",
                (work_item_id,),
            ).fetchone()
            self._assert_active_owner(row, executor_id, ts)
            con.execute(
                """
                UPDATE software_work_items
                SET lease_expires_at=?, updated_at=?
                WHERE id=?
                """,
                (ts + extend_seconds, ts, work_item_id),
            )
        return self.get(work_item_id)

    def submit_for_verification(
        self,
        work_item_id: str,
        submission: ExecutorSubmission,
        *,
        now: float | None = None,
    ) -> WorkItem:
        ts = _now(now)
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT * FROM software_work_items WHERE id=?",
                (work_item_id,),
            ).fetchone()
            if row is None:
                con.rollback()
                raise KeyError(work_item_id)
            if row["state"] != "RUNNING":
                con.rollback()
                raise RuntimeError("work item must be RUNNING before verification")
            if submission.task_id != work_item_id:
                con.rollback()
                raise ValueError("submission task_id mismatch")
            if submission.executor != row["executor_id"]:
                con.rollback()
                raise PermissionError("submission executor does not own attempt")
            if row["lease_expires_at"] is None or row["lease_expires_at"] <= ts:
                con.rollback()
                raise PermissionError("implementation lease expired")

            con.execute(
                """
                UPDATE software_work_items
                SET state='VERIFYING',
                    current_submission_sha256=?,
                    updated_at=?
                WHERE id=?
                """,
                (submission.sha256, ts, work_item_id),
            )
            con.execute(
                """
                UPDATE software_runs
                SET submission_sha256=?
                WHERE work_item_id=? AND attempt=? AND ended_at IS NULL
                """,
                (submission.sha256, work_item_id, row["attempts"]),
            )
            self._event(
                con, work_item_id, ts, "RUNNING", "VERIFYING",
                "SUBMITTED_FOR_VERIFICATION",
                {"submission_sha256": submission.sha256}
            )
            con.commit()
        return self.get(work_item_id)

    def accept_verification(
        self,
        work_item_id: str,
        receipt: AuditReceipt,
        *,
        now: float | None = None,
    ) -> WorkItem:
        ts = _now(now)
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT * FROM software_work_items WHERE id=?",
                (work_item_id,),
            ).fetchone()
            if row is None:
                con.rollback()
                raise KeyError(work_item_id)
            if row["state"] != "VERIFYING":
                con.rollback()
                raise RuntimeError("work item is not VERIFYING")
            if receipt.task_id != work_item_id:
                con.rollback()
                raise ValueError("audit receipt task mismatch")
            if receipt.contract_sha256 != row["contract_sha256"]:
                con.rollback()
                raise ValueError("audit receipt contract mismatch")
            if receipt.submission_sha256 != row["current_submission_sha256"]:
                con.rollback()
                raise ValueError("audit receipt submission mismatch")
            if receipt.auditor == row["executor_id"]:
                con.rollback()
                raise PermissionError("executor cannot audit its own attempt")

            if receipt.verdict != "ACCEPTED":
                self._retry_or_block(
                    con,
                    row,
                    ts,
                    error="independent audit rejected implementation",
                    receipt_sha256=receipt.sha256,
                )
                con.commit()
                return self.get(work_item_id)

            con.execute(
                """
                UPDATE software_work_items
                SET state='READY_FOR_PR',
                    lease_expires_at=NULL,
                    accepted_receipt_sha256=?,
                    updated_at=?
                WHERE id=?
                """,
                (receipt.sha256, ts, work_item_id),
            )
            con.execute(
                """
                UPDATE software_runs
                SET ended_at=?, outcome='ACCEPTED',
                    audit_receipt_sha256=?
                WHERE work_item_id=? AND attempt=? AND ended_at IS NULL
                """,
                (ts, receipt.sha256, work_item_id, row["attempts"]),
            )
            self._event(
                con, work_item_id, ts, "VERIFYING", "READY_FOR_PR",
                "VERIFICATION_ACCEPTED",
                {"audit_receipt_sha256": receipt.sha256}
            )
            con.commit()
        return self.get(work_item_id)

    def record_pr(
        self,
        work_item_id: str,
        pr_ref: str,
        *,
        now: float | None = None,
    ) -> WorkItem:
        if not pr_ref.strip():
            raise ValueError("pr_ref cannot be empty")
        ts = _now(now)
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM software_work_items WHERE id=?",
                (work_item_id,),
            ).fetchone()
            if row is None:
                raise KeyError(work_item_id)
            if row["state"] != "READY_FOR_PR":
                raise PermissionError("PR may open only after accepted verification")
            if not row["accepted_receipt_sha256"]:
                raise PermissionError("accepted audit receipt is required")
            con.execute(
                """
                UPDATE software_work_items
                SET state='PR_OPEN', pr_ref=?, updated_at=?
                WHERE id=?
                """,
                (pr_ref, ts, work_item_id),
            )
            self._event(
                con, work_item_id, ts, "READY_FOR_PR", "PR_OPEN",
                "PR_RECORDED", {"pr_ref": pr_ref}
            )
        return self.get(work_item_id)

    def record_merge(
        self,
        work_item_id: str,
        *,
        merge_ref: str,
        now: float | None = None,
    ) -> WorkItem:
        if not merge_ref.strip():
            raise ValueError("merge_ref cannot be empty")
        ts = _now(now)
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM software_work_items WHERE id=?",
                (work_item_id,),
            ).fetchone()
            if row is None:
                raise KeyError(work_item_id)
            if row["state"] != "PR_OPEN":
                raise RuntimeError("only an open PR can be recorded as merged")
            con.execute(
                """
                UPDATE software_work_items
                SET state='MERGED', updated_at=?
                WHERE id=?
                """,
                (ts, work_item_id),
            )
            self._event(
                con, work_item_id, ts, "PR_OPEN", "MERGED",
                "MERGE_RECORDED", {"merge_ref": merge_ref}
            )
        return self.get(work_item_id)

    def fail_attempt(
        self,
        work_item_id: str,
        executor_id: str,
        error: str,
        *,
        now: float | None = None,
    ) -> WorkItem:
        ts = _now(now)
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT * FROM software_work_items WHERE id=?",
                (work_item_id,),
            ).fetchone()
            self._assert_active_owner(row, executor_id, ts)
            self._retry_or_block(con, row, ts, error=error)
            con.commit()
        return self.get(work_item_id)

    def reconcile(self, *, now: float | None = None) -> int:
        """Recover stale active attempts after worker/process restart."""
        ts = _now(now)
        repaired = 0
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rows = con.execute(
                """
                SELECT * FROM software_work_items
                WHERE state IN ('RUNNING','VERIFYING')
                  AND lease_expires_at IS NOT NULL
                  AND lease_expires_at <= ?
                """,
                (ts,),
            ).fetchall()
            for row in rows:
                self._retry_or_block(
                    con,
                    row,
                    ts,
                    error="attempt lease expired during reconciliation",
                )
                repaired += 1
            con.commit()
        return repaired

    def events(self, work_item_id: str) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT * FROM software_events
                WHERE work_item_id=?
                ORDER BY observed_at, event_id
                """,
                (work_item_id,),
            ).fetchall()
        return [
            {**dict(row), "detail": json.loads(row["detail_json"])}
            for row in rows
        ]

    def _retry_or_block(
        self,
        con: sqlite3.Connection,
        row: sqlite3.Row,
        ts: float,
        *,
        error: str,
        receipt_sha256: str | None = None,
    ) -> None:
        old_state = row["state"]
        attempts = int(row["attempts"])
        max_attempts = int(row["max_attempts"])
        new_state = "QUEUED" if attempts < max_attempts else "BLOCKED"
        con.execute(
            """
            UPDATE software_work_items
            SET state=?, workspace_id=NULL, executor_id=NULL,
                lease_expires_at=NULL, current_submission_sha256=NULL,
                accepted_receipt_sha256=NULL, last_error=?, updated_at=?
            WHERE id=?
            """,
            (new_state, error, ts, row["id"]),
        )
        con.execute(
            """
            UPDATE software_runs
            SET ended_at=?, outcome=?, audit_receipt_sha256=?, error=?
            WHERE work_item_id=? AND attempt=? AND ended_at IS NULL
            """,
            (
                ts,
                "RETRY" if new_state == "QUEUED" else "BLOCKED",
                receipt_sha256,
                error,
                row["id"],
                attempts,
            ),
        )
        self._event(
            con,
            row["id"],
            ts,
            old_state,
            new_state,
            "ATTEMPT_FAILED",
            {"error": error, "attempt": attempts},
        )

    @staticmethod
    def _assert_active_owner(
        row: sqlite3.Row | None,
        executor_id: str,
        ts: float,
    ) -> None:
        if row is None:
            raise KeyError("unknown work item")
        if row["state"] not in ACTIVE_STATES:
            raise RuntimeError(f"work item is not active: {row['state']}")
        if row["executor_id"] != executor_id:
            raise PermissionError("executor does not own active attempt")
        if row["lease_expires_at"] is None or row["lease_expires_at"] <= ts:
            raise PermissionError("attempt lease expired")

    @staticmethod
    def _event(
        con: sqlite3.Connection,
        work_item_id: str,
        observed_at: float,
        from_state: str | None,
        to_state: str,
        event_type: str,
        detail: dict[str, Any],
    ) -> None:
        con.execute(
            """
            INSERT INTO software_events(
                event_id, work_item_id, observed_at, from_state,
                to_state, event_type, detail_json
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"event_{uuid.uuid4().hex}",
                work_item_id,
                observed_at,
                from_state,
                to_state,
                event_type,
                json.dumps(detail, sort_keys=True),
            ),
        )


def _item(row: sqlite3.Row) -> WorkItem:
    return WorkItem(
        id=row["id"],
        repository=row["repository"],
        issue_ref=row["issue_ref"],
        title=row["title"],
        state=row["state"],
        contract_sha256=row["contract_sha256"],
        attempts=int(row["attempts"]),
        max_attempts=int(row["max_attempts"]),
        workspace_id=row["workspace_id"],
        executor_id=row["executor_id"],
        lease_expires_at=row["lease_expires_at"],
        current_submission_sha256=row["current_submission_sha256"],
        accepted_receipt_sha256=row["accepted_receipt_sha256"],
        pr_ref=row["pr_ref"],
        last_error=row["last_error"],
        created_at=float(row["created_at"]),
        updated_at=float(row["updated_at"]),
    )


def _now(value: float | None) -> float:
    return time.time() if value is None else float(value)
