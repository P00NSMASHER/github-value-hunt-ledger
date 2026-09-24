"""Governed autonomous software factory for the AI Business OS.

This layer turns one manager-authored engineering goal into restart-safe implementation attempts,
independent verification, and governance-bound PR/merge handoff. It deliberately does not call
GitHub or another coding provider directly; an external executor may act only after the exact
Step-6 authorization has been issued.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
import uuid
from typing import Any, Dict, Optional

from ai_business_os.governance import GovernanceControlPlane, GovernanceError
from ai_business_os.persistent_agents.runtime import AgentRuntime
from ai_business_os.verification import VerificationOrchestrator


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


def _now() -> float:
    return time.time()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-").lower()
    return cleaned[:48] or "work"


class SoftwareFactoryError(ValueError):
    """Raised when a software-factory state or authority invariant is violated."""


class SoftwareFactory:
    """Durable engineering queue coupled to verification and governance."""

    def __init__(
        self,
        runtime: AgentRuntime,
        governance: GovernanceControlPlane,
    ):
        if governance.runtime is not runtime:
            raise SoftwareFactoryError(
                "factory and governance must share the exact AgentRuntime"
            )
        self.runtime = runtime
        self.governance = governance
        self.verification = VerificationOrchestrator(runtime)
        self._migrate()

    def _migrate(self) -> None:
        self.runtime.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS software_factory_items (
                id TEXT PRIMARY KEY,
                repository TEXT NOT NULL,
                issue_ref TEXT NOT NULL,
                title TEXT NOT NULL,
                goal_id TEXT NOT NULL REFERENCES goals(id),
                verification_contract_id TEXT NOT NULL
                    REFERENCES verification_contracts(id),
                manager_agent_id TEXT NOT NULL REFERENCES agents(id),
                executor_agent_id TEXT NOT NULL REFERENCES agents(id),
                auditor_agent_id TEXT NOT NULL REFERENCES agents(id),
                state TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL,
                workspace_id TEXT,
                branch_name TEXT,
                lease_expires_at REAL,
                submission_json TEXT,
                submission_hash TEXT,
                accepted_audit_report_hash TEXT,
                pr_ref TEXT,
                pr_title TEXT,
                merge_ref TEXT,
                last_error TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS software_factory_runs (
                id TEXT PRIMARY KEY,
                work_item_id TEXT NOT NULL REFERENCES software_factory_items(id),
                attempt INTEGER NOT NULL,
                workspace_id TEXT NOT NULL UNIQUE,
                branch_name TEXT NOT NULL UNIQUE,
                executor_agent_id TEXT NOT NULL REFERENCES agents(id),
                started_at REAL NOT NULL,
                ended_at REAL,
                outcome TEXT,
                submission_hash TEXT,
                audit_report_hash TEXT,
                error TEXT,
                UNIQUE(work_item_id, attempt)
            );

            CREATE TABLE IF NOT EXISTS software_factory_events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                work_item_id TEXT NOT NULL REFERENCES software_factory_items(id),
                event_type TEXT NOT NULL,
                from_state TEXT,
                to_state TEXT NOT NULL,
                detail_json TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS software_factory_governance_bindings (
                governance_request_id TEXT PRIMARY KEY
                    REFERENCES governance_action_requests(id),
                work_item_id TEXT NOT NULL REFERENCES software_factory_items(id),
                purpose TEXT NOT NULL,
                receipt_hash TEXT NOT NULL,
                bound_at REAL NOT NULL,
                UNIQUE(work_item_id, purpose)
            );

            CREATE INDEX IF NOT EXISTS idx_factory_queue
                ON software_factory_items(state, created_at);
            CREATE INDEX IF NOT EXISTS idx_factory_runs_item
                ON software_factory_runs(work_item_id, attempt);
            CREATE INDEX IF NOT EXISTS idx_factory_events_item
                ON software_factory_events(work_item_id, seq);
            """
        )
        self.runtime.conn.commit()

    def enqueue(
        self,
        *,
        work_item_id: str,
        repository: str,
        issue_ref: str,
        title: str,
        verification_contract_id: str,
        manager_agent_id: str,
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        work_item_id = work_item_id.strip()
        repository = repository.strip()
        issue_ref = issue_ref.strip()
        title = title.strip()
        if not work_item_id or not repository or not issue_ref or not title:
            raise SoftwareFactoryError(
                "work_item_id, repository, issue_ref, and title are required"
            )
        if max_attempts < 1:
            raise SoftwareFactoryError("max_attempts must be at least 1")
        self.runtime._require_agent(manager_agent_id)

        contract = self.verification.get_contract(verification_contract_id)
        if contract["manager_agent_id"] != manager_agent_id:
            raise SoftwareFactoryError(
                "only the acceptance contract manager may enqueue this work"
            )
        if contract["status"] not in {"DRAFT", "REJECTED", "EXECUTING"}:
            raise SoftwareFactoryError(
                f"verification contract cannot be enqueued from {contract['status']}"
            )
        goal = self.runtime.get_goal(contract["goal_id"])
        if goal["agent_id"] != contract["executor_agent_id"]:
            raise SoftwareFactoryError("contract executor does not own the engineering goal")

        ts = _now()
        try:
            self.runtime.conn.execute(
                """
                INSERT INTO software_factory_items(
                    id, repository, issue_ref, title, goal_id,
                    verification_contract_id, manager_agent_id,
                    executor_agent_id, auditor_agent_id, state,
                    attempts, max_attempts, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'QUEUED', 0, ?, ?, ?)
                """,
                (
                    work_item_id,
                    repository,
                    issue_ref,
                    title,
                    contract["goal_id"],
                    verification_contract_id,
                    manager_agent_id,
                    contract["executor_agent_id"],
                    contract["auditor_agent_id"],
                    max_attempts,
                    ts,
                    ts,
                ),
            )
        except Exception as exc:
            self.runtime.conn.rollback()
            raise SoftwareFactoryError("work item identity already exists") from exc
        self.runtime.conn.commit()
        self._event(
            work_item_id,
            "ENQUEUED",
            None,
            "QUEUED",
            {
                "repository": repository,
                "issue_ref": issue_ref,
                "verification_contract_id": verification_contract_id,
            },
        )
        return self.get(work_item_id)

    def claim(
        self,
        work_item_id: str,
        *,
        executor_agent_id: str,
        lease_seconds: float = 900.0,
    ) -> Dict[str, Any]:
        lease_seconds = float(lease_seconds)
        if not math.isfinite(lease_seconds) or lease_seconds <= 0:
            raise SoftwareFactoryError("lease_seconds must be finite and positive")
        item = self._require_item(work_item_id)
        if item["state"] != "QUEUED":
            raise SoftwareFactoryError(f"work item is not QUEUED: {item['state']}")
        if executor_agent_id != item["executor_agent_id"]:
            raise SoftwareFactoryError(
                "only the contract-bound executor may claim this work item"
            )
        attempt = int(item["attempts"]) + 1
        if attempt > int(item["max_attempts"]):
            raise SoftwareFactoryError("retry limit exhausted")

        contract = self.verification.get_contract(item["verification_contract_id"])
        if contract["status"] in {"DRAFT", "REJECTED"}:
            self.verification.start_execution(item["verification_contract_id"])
        elif contract["status"] != "EXECUTING":
            raise SoftwareFactoryError(
                f"verification contract cannot execute from {contract['status']}"
            )

        workspace_id = f"ws_{_slug(work_item_id)}_{attempt}_{uuid.uuid4().hex[:10]}"
        branch_name = f"ai-factory/{_slug(work_item_id)}/attempt-{attempt}"
        run_id = f"factoryrun_{uuid.uuid4().hex}"
        ts = _now()
        self.runtime.conn.execute(
            """
            UPDATE software_factory_items
            SET state='RUNNING', attempts=?, workspace_id=?, branch_name=?,
                lease_expires_at=?, submission_json=NULL, submission_hash=NULL,
                accepted_audit_report_hash=NULL, pr_ref=NULL, pr_title=NULL,
                merge_ref=NULL, last_error=NULL, updated_at=?
            WHERE id=?
            """,
            (
                attempt,
                workspace_id,
                branch_name,
                ts + lease_seconds,
                ts,
                work_item_id,
            ),
        )
        self.runtime.conn.execute(
            """
            INSERT INTO software_factory_runs(
                id, work_item_id, attempt, workspace_id, branch_name,
                executor_agent_id, started_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                work_item_id,
                attempt,
                workspace_id,
                branch_name,
                executor_agent_id,
                ts,
            ),
        )
        self.runtime.conn.commit()
        self._event(
            work_item_id,
            "CLAIMED",
            "QUEUED",
            "RUNNING",
            {
                "attempt": attempt,
                "workspace_id": workspace_id,
                "branch_name": branch_name,
                "executor_agent_id": executor_agent_id,
            },
        )
        return self.get(work_item_id)

    def heartbeat(
        self,
        work_item_id: str,
        *,
        executor_agent_id: str,
        extend_seconds: float = 900.0,
    ) -> Dict[str, Any]:
        extend_seconds = float(extend_seconds)
        if not math.isfinite(extend_seconds) or extend_seconds <= 0:
            raise SoftwareFactoryError("extend_seconds must be finite and positive")
        item = self._require_active_owner(work_item_id, executor_agent_id)
        ts = _now()
        self.runtime.conn.execute(
            """
            UPDATE software_factory_items
            SET lease_expires_at=?, updated_at=?
            WHERE id=?
            """,
            (ts + extend_seconds, ts, work_item_id),
        )
        self.runtime.conn.commit()
        return self.get(work_item_id)

    def fail_attempt(
        self,
        work_item_id: str,
        *,
        executor_agent_id: str,
        error: str,
    ) -> Dict[str, Any]:
        item = self._require_active_owner(work_item_id, executor_agent_id)
        if item["state"] != "RUNNING":
            raise SoftwareFactoryError("only a RUNNING implementation may fail directly")
        return self._retry_or_block(work_item_id, error=error or "executor failure")

    def submit_for_verification(
        self,
        work_item_id: str,
        *,
        executor_agent_id: str,
        commit_sha: str,
        test_evidence: Dict[str, Any],
        artifact_evidence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        item = self._require_active_owner(work_item_id, executor_agent_id)
        if item["state"] != "RUNNING":
            raise SoftwareFactoryError("work item must be RUNNING before verification")
        commit_sha = commit_sha.strip()
        if not commit_sha:
            raise SoftwareFactoryError("commit_sha is required")
        if not isinstance(test_evidence, dict) or not test_evidence:
            raise SoftwareFactoryError("test_evidence must be non-empty")
        if artifact_evidence is not None and not isinstance(artifact_evidence, dict):
            raise SoftwareFactoryError("artifact_evidence must be an object")

        submission = {
            "work_item_id": work_item_id,
            "repository": item["repository"],
            "issue_ref": item["issue_ref"],
            "workspace_id": item["workspace_id"],
            "branch_name": item["branch_name"],
            "attempt": item["attempts"],
            "commit_sha": commit_sha,
            "test_evidence": test_evidence,
            "artifact_evidence": artifact_evidence or {},
        }
        submission_hash = _sha(submission)
        self.verification.submit_execution(
            item["verification_contract_id"],
            executor_agent_id=executor_agent_id,
            evidence=submission,
        )
        ts = _now()
        self.runtime.conn.execute(
            """
            UPDATE software_factory_items
            SET state='VERIFYING', submission_json=?, submission_hash=?,
                lease_expires_at=NULL, updated_at=?
            WHERE id=?
            """,
            (_json(submission), submission_hash, ts, work_item_id),
        )
        self.runtime.conn.execute(
            """
            UPDATE software_factory_runs
            SET submission_hash=?
            WHERE work_item_id=? AND attempt=? AND ended_at IS NULL
            """,
            (submission_hash, work_item_id, item["attempts"]),
        )
        self.runtime.conn.commit()
        self._event(
            work_item_id,
            "SUBMITTED_FOR_VERIFICATION",
            "RUNNING",
            "VERIFYING",
            {"submission_hash": submission_hash, "commit_sha": commit_sha},
        )
        return self.get(work_item_id)

    def sync_audit(self, work_item_id: str) -> Dict[str, Any]:
        item = self._require_item(work_item_id)
        if item["state"] != "VERIFYING":
            raise SoftwareFactoryError("work item is not VERIFYING")
        contract = self.verification.get_contract(item["verification_contract_id"])
        if contract["status"] == "VERIFYING":
            raise SoftwareFactoryError("independent audit has not finished")
        if contract["status"] == "REJECTED":
            return self._retry_or_block(
                work_item_id,
                error="independent audit rejected the implementation",
                audit_report_hash=contract["report_hash"],
            )
        if contract["status"] != "APPROVED":
            raise SoftwareFactoryError(
                f"unexpected verification contract state: {contract['status']}"
            )

        expected_submission = json.loads(item["submission_json"])
        if contract["submission"] != expected_submission:
            raise SoftwareFactoryError(
                "approved audit is not bound to the current factory submission"
            )
        if not contract["report_hash"]:
            raise SoftwareFactoryError("approved audit is missing its report hash")
        ts = _now()
        self.runtime.conn.execute(
            """
            UPDATE software_factory_items
            SET state='READY_FOR_PR', lease_expires_at=NULL,
                accepted_audit_report_hash=?, updated_at=?
            WHERE id=?
            """,
            (contract["report_hash"], ts, work_item_id),
        )
        self.runtime.conn.execute(
            """
            UPDATE software_factory_runs
            SET ended_at=?, outcome='ACCEPTED', audit_report_hash=?
            WHERE work_item_id=? AND attempt=? AND ended_at IS NULL
            """,
            (
                ts,
                contract["report_hash"],
                work_item_id,
                item["attempts"],
            ),
        )
        self.runtime.conn.commit()
        self._event(
            work_item_id,
            "AUDIT_ACCEPTED",
            "VERIFYING",
            "READY_FOR_PR",
            {"audit_report_hash": contract["report_hash"]},
        )
        return self.get(work_item_id)

    def request_pr_authorization(
        self,
        work_item_id: str,
        *,
        actor_agent_id: str,
        pr_title: str,
        base_branch: str = "main",
    ) -> Dict[str, Any]:
        item = self._require_item(work_item_id)
        if item["state"] != "READY_FOR_PR":
            raise SoftwareFactoryError("PR authorization requires READY_FOR_PR")
        if not item["accepted_audit_report_hash"]:
            raise SoftwareFactoryError("accepted audit is required before PR authorization")
        pr_title = pr_title.strip()
        base_branch = base_branch.strip()
        if not pr_title or not base_branch:
            raise SoftwareFactoryError("pr_title and base_branch are required")
        params = self._pr_params(item, pr_title=pr_title, base_branch=base_branch)
        decision = self.governance.request_action(
            actor_agent_id,
            action_key="github.pr.create",
            action_class="EXTERNAL_WRITE",
            parameters=params,
        )
        self.runtime.conn.execute(
            "UPDATE software_factory_items SET pr_title=?, updated_at=? WHERE id=?",
            (pr_title, _now(), work_item_id),
        )
        self.runtime.conn.commit()
        return decision

    def record_pr(
        self,
        work_item_id: str,
        *,
        pr_ref: str,
        governance_request_id: str,
        base_branch: str = "main",
    ) -> Dict[str, Any]:
        item = self._require_item(work_item_id)
        if item["state"] != "READY_FOR_PR":
            raise SoftwareFactoryError("PR may be recorded only from READY_FOR_PR")
        pr_ref = pr_ref.strip()
        if not pr_ref:
            raise SoftwareFactoryError("pr_ref is required")
        if not item["pr_title"]:
            raise SoftwareFactoryError("PR authorization was never requested")
        expected = self._pr_params(
            item,
            pr_title=item["pr_title"],
            base_branch=base_branch.strip(),
        )
        receipt_hash = self._bind_authorization(
            work_item_id,
            governance_request_id,
            purpose="PR_CREATE",
            expected_agent_id=None,
            expected_action_key="github.pr.create",
            expected_action_class="EXTERNAL_WRITE",
            expected_parameters=expected,
        )
        self.runtime.conn.execute(
            """
            UPDATE software_factory_items
            SET state='PR_OPEN', pr_ref=?, updated_at=?
            WHERE id=?
            """,
            (pr_ref, _now(), work_item_id),
        )
        self.runtime.conn.commit()
        self._event(
            work_item_id,
            "PR_RECORDED",
            "READY_FOR_PR",
            "PR_OPEN",
            {
                "pr_ref": pr_ref,
                "governance_request_id": governance_request_id,
                "governance_receipt_hash": receipt_hash,
            },
        )
        return self.get(work_item_id)

    def request_merge_authorization(
        self,
        work_item_id: str,
        *,
        actor_agent_id: str,
        expected_head_sha: str,
        merge_method: str = "squash",
    ) -> Dict[str, Any]:
        item = self._require_item(work_item_id)
        if item["state"] != "PR_OPEN" or not item["pr_ref"]:
            raise SoftwareFactoryError("merge authorization requires an open PR")
        expected_head_sha = expected_head_sha.strip()
        merge_method = merge_method.strip().lower()
        if not expected_head_sha:
            raise SoftwareFactoryError("expected_head_sha is required")
        if merge_method not in {"merge", "squash", "rebase"}:
            raise SoftwareFactoryError("unsupported merge_method")
        params = self._merge_params(
            item,
            expected_head_sha=expected_head_sha,
            merge_method=merge_method,
        )
        return self.governance.request_action(
            actor_agent_id,
            action_key="github.pr.merge",
            action_class="PRODUCTION_CHANGE",
            parameters=params,
        )

    def record_merge(
        self,
        work_item_id: str,
        *,
        merge_ref: str,
        expected_head_sha: str,
        merge_method: str,
        governance_request_id: str,
    ) -> Dict[str, Any]:
        item = self._require_item(work_item_id)
        if item["state"] != "PR_OPEN":
            raise SoftwareFactoryError("only PR_OPEN work may be merged")
        merge_ref = merge_ref.strip()
        if not merge_ref:
            raise SoftwareFactoryError("merge_ref is required")
        expected = self._merge_params(
            item,
            expected_head_sha=expected_head_sha.strip(),
            merge_method=merge_method.strip().lower(),
        )
        receipt_hash = self._bind_authorization(
            work_item_id,
            governance_request_id,
            purpose="PR_MERGE",
            expected_agent_id=None,
            expected_action_key="github.pr.merge",
            expected_action_class="PRODUCTION_CHANGE",
            expected_parameters=expected,
        )
        # The code audit authorizes PR readiness; the governance-approved merge is the final
        # condition that lets the manager accept the engineering goal as COMPLETE.
        self.verification.complete_goal(
            item["verification_contract_id"],
            manager_agent_id=item["manager_agent_id"],
        )
        self.runtime.conn.execute(
            """
            UPDATE software_factory_items
            SET state='MERGED', merge_ref=?, updated_at=?
            WHERE id=?
            """,
            (merge_ref, _now(), work_item_id),
        )
        self.runtime.conn.commit()
        self._event(
            work_item_id,
            "MERGE_RECORDED",
            "PR_OPEN",
            "MERGED",
            {
                "merge_ref": merge_ref,
                "governance_request_id": governance_request_id,
                "governance_receipt_hash": receipt_hash,
            },
        )
        return self.get(work_item_id)

    def reconcile(self) -> int:
        """Requeue or block stale implementation/verification attempts."""
        ts = _now()
        rows = self.runtime.conn.execute(
            """
            SELECT id FROM software_factory_items
            WHERE state='RUNNING'
              AND lease_expires_at IS NOT NULL
              AND lease_expires_at <= ?
            """,
            (ts,),
        ).fetchall()
        repaired = 0
        for row in rows:
            self._retry_or_block(
                str(row["id"]),
                error="factory attempt lease expired during reconciliation",
            )
            repaired += 1
        return repaired

    def get(self, work_item_id: str) -> Dict[str, Any]:
        row = self._require_item(work_item_id)
        return {
            "id": row["id"],
            "repository": row["repository"],
            "issue_ref": row["issue_ref"],
            "title": row["title"],
            "goal_id": row["goal_id"],
            "verification_contract_id": row["verification_contract_id"],
            "manager_agent_id": row["manager_agent_id"],
            "executor_agent_id": row["executor_agent_id"],
            "auditor_agent_id": row["auditor_agent_id"],
            "state": row["state"],
            "attempts": row["attempts"],
            "max_attempts": row["max_attempts"],
            "workspace_id": row["workspace_id"],
            "branch_name": row["branch_name"],
            "lease_expires_at": row["lease_expires_at"],
            "submission": json.loads(row["submission_json"]) if row["submission_json"] else None,
            "submission_hash": row["submission_hash"],
            "accepted_audit_report_hash": row["accepted_audit_report_hash"],
            "pr_ref": row["pr_ref"],
            "pr_title": row["pr_title"],
            "merge_ref": row["merge_ref"],
            "last_error": row["last_error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def events(self, work_item_id: str) -> list[Dict[str, Any]]:
        self._require_item(work_item_id)
        rows = self.runtime.conn.execute(
            """
            SELECT * FROM software_factory_events
            WHERE work_item_id=?
            ORDER BY seq
            """,
            (work_item_id,),
        ).fetchall()
        return [
            {
                "seq": row["seq"],
                "event_type": row["event_type"],
                "from_state": row["from_state"],
                "to_state": row["to_state"],
                "detail": json.loads(row["detail_json"]),
                "event_hash": row["event_hash"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def _retry_or_block(
        self,
        work_item_id: str,
        *,
        error: str,
        audit_report_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        item = self._require_item(work_item_id)
        if item["state"] not in ACTIVE_STATES:
            raise SoftwareFactoryError(
                f"cannot retry/block work from {item['state']}"
            )
        to_state = (
            "BLOCKED"
            if int(item["attempts"]) >= int(item["max_attempts"])
            else "QUEUED"
        )
        ts = _now()
        self.runtime.conn.execute(
            """
            UPDATE software_factory_items
            SET state=?, workspace_id=NULL, branch_name=NULL,
                lease_expires_at=NULL, submission_json=NULL,
                submission_hash=NULL, accepted_audit_report_hash=NULL,
                last_error=?, updated_at=?
            WHERE id=?
            """,
            (to_state, error, ts, work_item_id),
        )
        self.runtime.conn.execute(
            """
            UPDATE software_factory_runs
            SET ended_at=?, outcome=?, error=?, audit_report_hash=?
            WHERE work_item_id=? AND attempt=? AND ended_at IS NULL
            """,
            (
                ts,
                "BLOCKED" if to_state == "BLOCKED" else "RETRY",
                error,
                audit_report_hash,
                work_item_id,
                item["attempts"],
            ),
        )
        self.runtime.conn.commit()
        self._event(
            work_item_id,
            "ATTEMPT_FAILED",
            item["state"],
            to_state,
            {
                "error": error,
                "attempt": item["attempts"],
                "audit_report_hash": audit_report_hash,
            },
        )
        return self.get(work_item_id)

    def _bind_authorization(
        self,
        work_item_id: str,
        governance_request_id: str,
        *,
        purpose: str,
        expected_agent_id: Optional[str],
        expected_action_key: str,
        expected_action_class: str,
        expected_parameters: Dict[str, Any],
    ) -> str:
        request = self.runtime.conn.execute(
            """
            SELECT * FROM governance_action_requests
            WHERE id=?
            """,
            (governance_request_id,),
        ).fetchone()
        if request is None:
            raise SoftwareFactoryError("unknown governance action request")
        if request["status"] != "AUTHORIZED":
            raise SoftwareFactoryError("governance action request is not AUTHORIZED")
        if expected_agent_id is not None and request["agent_id"] != expected_agent_id:
            raise SoftwareFactoryError("governance request agent mismatch")
        if request["action_key"] != expected_action_key:
            raise SoftwareFactoryError("governance action key mismatch")
        if request["action_class"] != expected_action_class:
            raise SoftwareFactoryError("governance action class mismatch")
        if json.loads(request["parameters_json"]) != expected_parameters:
            raise SoftwareFactoryError(
                "governance authorization is not bound to these exact factory parameters"
            )
        decision = self.runtime.conn.execute(
            """
            SELECT * FROM governance_decisions
            WHERE request_id=? AND decision='ALLOW'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (governance_request_id,),
        ).fetchone()
        if decision is None:
            raise SoftwareFactoryError("authorized request has no ALLOW audit receipt")
        try:
            self.runtime.conn.execute(
                """
                INSERT INTO software_factory_governance_bindings(
                    governance_request_id, work_item_id, purpose,
                    receipt_hash, bound_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    governance_request_id,
                    work_item_id,
                    purpose,
                    decision["receipt_hash"],
                    _now(),
                ),
            )
            self.runtime.conn.commit()
        except Exception as exc:
            self.runtime.conn.rollback()
            raise SoftwareFactoryError(
                "governance authorization has already been consumed by the factory"
            ) from exc
        return str(decision["receipt_hash"])

    def _pr_params(
        self,
        item,
        *,
        pr_title: str,
        base_branch: str,
    ) -> Dict[str, Any]:
        return {
            "work_item_id": item["id"],
            "repository": item["repository"],
            "issue_ref": item["issue_ref"],
            "head_branch": item["branch_name"],
            "base_branch": base_branch,
            "pr_title": pr_title,
            "submission_hash": item["submission_hash"],
            "audit_report_hash": item["accepted_audit_report_hash"],
        }

    def _merge_params(
        self,
        item,
        *,
        expected_head_sha: str,
        merge_method: str,
    ) -> Dict[str, Any]:
        if merge_method not in {"merge", "squash", "rebase"}:
            raise SoftwareFactoryError("unsupported merge_method")
        if not expected_head_sha:
            raise SoftwareFactoryError("expected_head_sha is required")
        return {
            "work_item_id": item["id"],
            "repository": item["repository"],
            "pr_ref": item["pr_ref"],
            "expected_head_sha": expected_head_sha,
            "merge_method": merge_method,
            "audit_report_hash": item["accepted_audit_report_hash"],
        }

    def _event(
        self,
        work_item_id: str,
        event_type: str,
        from_state: Optional[str],
        to_state: str,
        detail: Dict[str, Any],
    ) -> None:
        payload = {
            "work_item_id": work_item_id,
            "event_type": event_type,
            "from_state": from_state,
            "to_state": to_state,
            "detail": detail,
        }
        self.runtime.conn.execute(
            """
            INSERT INTO software_factory_events(
                work_item_id, event_type, from_state, to_state,
                detail_json, event_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                work_item_id,
                event_type,
                from_state,
                to_state,
                _json(detail),
                _sha(payload),
                _now(),
            ),
        )
        self.runtime.conn.commit()

    def _require_active_owner(self, work_item_id: str, executor_agent_id: str):
        item = self._require_item(work_item_id)
        if item["state"] not in ACTIVE_STATES:
            raise SoftwareFactoryError(f"work item is not active: {item['state']}")
        if item["executor_agent_id"] != executor_agent_id:
            raise SoftwareFactoryError("executor does not own this work item")
        if item["lease_expires_at"] is None or float(item["lease_expires_at"]) <= _now():
            raise SoftwareFactoryError("factory attempt lease has expired")
        return item

    def _require_item(self, work_item_id: str):
        row = self.runtime.conn.execute(
            "SELECT * FROM software_factory_items WHERE id=?",
            (work_item_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown software factory work item: {work_item_id}")
        return row
