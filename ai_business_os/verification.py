"""Independent Manager -> Executor -> Auditor verification layer.

This module makes completion an evidence-backed state transition. The executor may submit work,
but only the independently assigned auditor can approve the acceptance contract. The persistent
runtime then enforces that approval before allowing VERIFYING -> COMPLETE.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional

from ai_business_os.persistent_agents.runtime import AgentRuntime, InvalidTransition


VERDICTS = {"PASS", "FAIL", "UNKNOWN"}


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _now() -> float:
    return time.time()


class VerificationError(ValueError):
    """Raised when a verification contract or audit is invalid."""


class VerificationOrchestrator:
    """Coordinates independently managed execution and audit."""

    def __init__(self, runtime: AgentRuntime):
        self.runtime = runtime

    def create_contract(
        self,
        goal_id: str,
        *,
        manager_agent_id: str,
        executor_agent_id: str,
        auditor_agent_id: str,
        criteria: Iterable[Dict[str, Any]],
        contract_id: Optional[str] = None,
    ) -> str:
        goal = self.runtime._require_goal(goal_id)
        self.runtime._require_agent(manager_agent_id)
        self.runtime._require_agent(executor_agent_id)
        self.runtime._require_agent(auditor_agent_id)

        identities = {manager_agent_id, executor_agent_id, auditor_agent_id}
        if len(identities) != 3:
            raise VerificationError("manager, executor, and auditor must be three distinct agents")
        if goal["agent_id"] != executor_agent_id:
            raise VerificationError("verification executor must own the bound goal")

        normalized = self._normalize_criteria(criteria)
        contract_id = contract_id or f"verify_{uuid.uuid4().hex}"
        ts = _now()
        self.runtime.conn.execute(
            """
            INSERT INTO verification_contracts(
                id, goal_id, manager_agent_id, executor_agent_id, auditor_agent_id,
                criteria_json, status, attempt, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'DRAFT', 0, ?, ?)
            """,
            (
                contract_id,
                goal_id,
                manager_agent_id,
                executor_agent_id,
                auditor_agent_id,
                _json(normalized),
                ts,
                ts,
            ),
        )
        self.runtime.conn.commit()
        self.runtime.append_event(
            manager_agent_id,
            "VERIFICATION_CONTRACT_CREATED",
            {
                "contract_id": contract_id,
                "executor_agent_id": executor_agent_id,
                "auditor_agent_id": auditor_agent_id,
                "criteria": normalized,
            },
            goal_id=goal_id,
        )
        return contract_id

    def start_execution(self, contract_id: str) -> Dict[str, Any]:
        contract = self._require_contract(contract_id)
        if contract["status"] not in {"DRAFT", "REJECTED"}:
            raise VerificationError(f"cannot start execution from {contract['status']}")

        goal = self.runtime.get_goal(str(contract["goal_id"]))
        if goal["status"] == "PENDING":
            self.runtime.transition_goal(goal["id"], "ACTIVE", reason="verification_contract_started")
        elif goal["status"] == "BLOCKED":
            self.runtime.transition_goal(goal["id"], "ACTIVE", reason="verification_revision_started")
        elif goal["status"] != "ACTIVE":
            raise VerificationError(f"goal cannot execute from {goal['status']}")

        self._update_contract(contract_id, status="EXECUTING")
        self.runtime.append_event(
            str(contract["executor_agent_id"]),
            "VERIFIED_EXECUTION_STARTED",
            {"contract_id": contract_id, "attempt": int(contract["attempt"]) + 1},
            goal_id=str(contract["goal_id"]),
        )
        return self.get_contract(contract_id)

    def submit_execution(
        self,
        contract_id: str,
        *,
        executor_agent_id: str,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        contract = self._require_contract(contract_id)
        if executor_agent_id != contract["executor_agent_id"]:
            raise VerificationError("only the assigned executor can submit execution evidence")
        if contract["status"] != "EXECUTING":
            raise VerificationError(f"cannot submit execution from {contract['status']}")
        if not isinstance(evidence, dict) or not evidence:
            raise VerificationError("execution evidence must be a non-empty object")

        goal = self.runtime.get_goal(str(contract["goal_id"]))
        if goal["status"] != "ACTIVE":
            raise VerificationError(f"goal must be ACTIVE before audit, not {goal['status']}")

        attempt = int(contract["attempt"]) + 1
        self.runtime.conn.execute(
            """
            UPDATE verification_contracts
            SET status = 'VERIFYING', attempt = ?, submission_json = ?,
                report_json = NULL, report_hash = NULL, updated_at = ?
            WHERE id = ?
            """,
            (attempt, _json(evidence), _now(), contract_id),
        )
        self.runtime.conn.commit()
        self.runtime.transition_goal(
            goal["id"],
            "VERIFYING",
            state_patch={
                "verification_contract_id": contract_id,
                "verification_attempt": attempt,
            },
            reason="executor_submitted_for_independent_audit",
        )
        self.runtime.append_event(
            executor_agent_id,
            "EXECUTION_SUBMITTED_FOR_AUDIT",
            {"contract_id": contract_id, "attempt": attempt, "evidence": evidence},
            goal_id=goal["id"],
        )
        return self.get_contract(contract_id)

    def audit(
        self,
        contract_id: str,
        *,
        auditor_agent_id: str,
        results: Iterable[Dict[str, Any]],
        summary: str = "",
    ) -> Dict[str, Any]:
        contract = self._require_contract(contract_id)
        if auditor_agent_id != contract["auditor_agent_id"]:
            raise VerificationError("only the assigned independent auditor may audit this contract")
        if auditor_agent_id == contract["executor_agent_id"]:
            raise VerificationError("executor cannot audit its own work")
        if contract["status"] != "VERIFYING":
            raise VerificationError(f"cannot audit contract from {contract['status']}")

        criteria = json.loads(contract["criteria_json"])
        normalized_results = self._normalize_results(criteria, results)
        required_ids = {c["id"] for c in criteria if c["required"]}
        passed_required = {
            r["criterion_id"]
            for r in normalized_results
            if r["criterion_id"] in required_ids and r["verdict"] == "PASS"
        }
        approved = passed_required == required_ids
        status = "APPROVED" if approved else "REJECTED"
        report = {
            "contract_id": contract_id,
            "goal_id": contract["goal_id"],
            "attempt": int(contract["attempt"]),
            "auditor_agent_id": auditor_agent_id,
            "summary": summary,
            "results": normalized_results,
            "decision": status,
        }
        report_hash = hashlib.sha256(_json(report).encode("utf-8")).hexdigest()

        self.runtime.conn.execute(
            """
            UPDATE verification_contracts
            SET status = ?, report_json = ?, report_hash = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, _json(report), report_hash, _now(), contract_id),
        )
        self.runtime.conn.commit()
        self.runtime.append_event(
            auditor_agent_id,
            "INDEPENDENT_AUDIT_RECORDED",
            {
                "contract_id": contract_id,
                "decision": status,
                "report_hash": report_hash,
                "attempt": int(contract["attempt"]),
            },
            goal_id=str(contract["goal_id"]),
        )

        if not approved:
            self.runtime.transition_goal(
                str(contract["goal_id"]),
                "ACTIVE",
                state_patch={
                    "last_audit_decision": status,
                    "last_audit_report_hash": report_hash,
                },
                reason="independent_audit_requires_revision",
            )
        return self.get_contract(contract_id)

    def complete_goal(self, contract_id: str, *, manager_agent_id: str) -> Dict[str, Any]:
        contract = self._require_contract(contract_id)
        if manager_agent_id != contract["manager_agent_id"]:
            raise VerificationError("only the assigned manager may accept audited work")
        if contract["status"] != "APPROVED" or not contract["report_hash"]:
            raise VerificationError("goal cannot complete without an approved audit report")

        goal = self.runtime.get_goal(str(contract["goal_id"]))
        if goal["status"] != "VERIFYING":
            raise VerificationError(f"approved goal must still be VERIFYING, not {goal['status']}")

        completed = self.runtime.transition_goal(
            goal["id"],
            "COMPLETE",
            state_patch={
                "accepted_verification_contract_id": contract_id,
                "accepted_audit_report_hash": contract["report_hash"],
            },
            reason="manager_accepted_independently_verified_work",
            verification_contract_id=contract_id,
        )
        self._update_contract(contract_id, status="CLOSED")
        self.runtime.append_event(
            manager_agent_id,
            "AUDITED_WORK_ACCEPTED",
            {
                "contract_id": contract_id,
                "report_hash": contract["report_hash"],
                "attempt": int(contract["attempt"]),
            },
            goal_id=goal["id"],
        )
        return completed

    def get_contract(self, contract_id: str) -> Dict[str, Any]:
        row = self._require_contract(contract_id)
        return {
            "id": row["id"],
            "goal_id": row["goal_id"],
            "manager_agent_id": row["manager_agent_id"],
            "executor_agent_id": row["executor_agent_id"],
            "auditor_agent_id": row["auditor_agent_id"],
            "criteria": json.loads(row["criteria_json"]),
            "status": row["status"],
            "attempt": row["attempt"],
            "submission": json.loads(row["submission_json"]) if row["submission_json"] else None,
            "report": json.loads(row["report_json"]) if row["report_json"] else None,
            "report_hash": row["report_hash"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _normalize_criteria(self, criteria: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        items = list(criteria)
        if not items:
            raise VerificationError("verification requires at least one acceptance criterion")
        normalized: List[Dict[str, Any]] = []
        seen = set()
        for item in items:
            criterion_id = str(item.get("id", "")).strip()
            description = str(item.get("description", "")).strip()
            if not criterion_id or not description:
                raise VerificationError("each criterion needs a non-empty id and description")
            if criterion_id in seen:
                raise VerificationError(f"duplicate criterion id: {criterion_id}")
            seen.add(criterion_id)
            normalized.append(
                {
                    "id": criterion_id,
                    "description": description,
                    "required": bool(item.get("required", True)),
                }
            )
        if not any(c["required"] for c in normalized):
            raise VerificationError("at least one criterion must be required")
        return normalized

    def _normalize_results(
        self,
        criteria: List[Dict[str, Any]],
        results: Iterable[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        expected = {c["id"] for c in criteria}
        normalized: List[Dict[str, Any]] = []
        seen = set()
        for result in results:
            criterion_id = str(result.get("criterion_id", "")).strip()
            verdict = str(result.get("verdict", "")).upper().strip()
            if criterion_id not in expected:
                raise VerificationError(f"unknown criterion result: {criterion_id}")
            if criterion_id in seen:
                raise VerificationError(f"duplicate result for criterion: {criterion_id}")
            if verdict not in VERDICTS:
                raise VerificationError(f"invalid verdict for {criterion_id}: {verdict}")
            evidence = result.get("evidence", [])
            if not isinstance(evidence, list):
                raise VerificationError("criterion evidence must be a list")
            normalized.append(
                {
                    "criterion_id": criterion_id,
                    "verdict": verdict,
                    "evidence": evidence,
                    "notes": str(result.get("notes", "")),
                }
            )
            seen.add(criterion_id)
        missing = expected - seen
        if missing:
            raise VerificationError(f"missing criterion results: {sorted(missing)}")
        return normalized

    def _require_contract(self, contract_id: str):
        row = self.runtime.conn.execute(
            "SELECT * FROM verification_contracts WHERE id = ?",
            (contract_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown verification contract: {contract_id}")
        return row

    def _update_contract(self, contract_id: str, *, status: str) -> None:
        self.runtime.conn.execute(
            "UPDATE verification_contracts SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now(), contract_id),
        )
        self.runtime.conn.commit()
