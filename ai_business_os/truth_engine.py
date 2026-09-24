"""Persistent evidence / truth engine for the AI Business OS.

Claims are evaluated against explicit proof obligations and typed evidence. Model confidence is
never accepted as proof. Missing, stale, inadmissible, insufficiently independent, contradictory,
and unresolved evidence remain distinct states. Next-evidence planning may use counterfactual
evidence, but hypothetical evidence is never persisted into the real evidence ledger.

The engine can ask the Step-6 governance layer to authorize an evidence-acquisition action; it does
not execute the action itself.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ai_business_os.governance import GovernanceControlPlane
from ai_business_os.persistent_agents.runtime import AgentRuntime


VALID_STANCES = {"SUPPORTS", "CONTRADICTS"}
VALID_VERDICTS = {"PROVEN", "CONTESTED", "NOT_PROVEN", "UNKNOWN"}
VALID_FINDING_STATUSES = {
    "SATISFIED",
    "MISSING",
    "STALE",
    "INADMISSIBLE",
    "INSUFFICIENT_SUPPORT",
    "INSUFFICIENT_INDEPENDENCE",
    "CONFLICTED",
    "CONTRADICTED",
}


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


class TruthEngineError(ValueError):
    """Raised when proof/evidence invariants are violated."""


@dataclass(frozen=True)
class RankedEvidenceAction:
    action_id: str
    obligation_key: str
    description: str
    authority: str
    independence_group: str
    action_key: str
    action_class: str
    action_parameters: Dict[str, Any]
    cost_units: float
    baseline_verdict: str
    counterfactual_verdict: str
    obligations_improved: int
    potential_decision_gain: int
    priority_score: float


class TruthEngine:
    """SQLite-backed proof evaluator and next-evidence planner."""

    VERDICT_RANK = {
        "UNKNOWN": 0,
        "NOT_PROVEN": 1,
        "CONTESTED": 1,
        "PROVEN": 3,
    }

    def __init__(
        self,
        runtime: AgentRuntime,
        governance: Optional[GovernanceControlPlane] = None,
    ):
        if governance is not None and governance.runtime is not runtime:
            raise TruthEngineError("truth engine and governance must share the exact AgentRuntime")
        self.runtime = runtime
        self.governance = governance
        self._migrate()

    def _migrate(self) -> None:
        self.runtime.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS truth_claims (
                id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                statement TEXT NOT NULL,
                context_json TEXT NOT NULL,
                claim_hash TEXT NOT NULL,
                created_by_agent_id TEXT NOT NULL REFERENCES agents(id),
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS truth_obligations (
                claim_id TEXT NOT NULL REFERENCES truth_claims(id),
                obligation_key TEXT NOT NULL,
                description TEXT NOT NULL,
                allowed_authorities_json TEXT NOT NULL,
                min_supporting_sources INTEGER NOT NULL,
                min_independent_groups INTEGER NOT NULL,
                max_age_seconds REAL,
                required INTEGER NOT NULL,
                created_at REAL NOT NULL,
                PRIMARY KEY(claim_id, obligation_key)
            );

            CREATE TABLE IF NOT EXISTS truth_evidence (
                id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL REFERENCES truth_claims(id),
                obligation_key TEXT NOT NULL,
                stance TEXT NOT NULL,
                authority TEXT NOT NULL,
                source_id TEXT NOT NULL,
                independence_group TEXT NOT NULL,
                observed_at REAL NOT NULL,
                source_ref TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                admissible INTEGER NOT NULL,
                valid_until REAL,
                payload_json TEXT NOT NULL,
                evidence_hash TEXT NOT NULL UNIQUE,
                created_by_agent_id TEXT NOT NULL REFERENCES agents(id),
                created_at REAL NOT NULL,
                UNIQUE(claim_id, obligation_key, source_id, source_sha256, stance)
            );

            CREATE TABLE IF NOT EXISTS truth_receipts (
                id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL REFERENCES truth_claims(id),
                claim_hash TEXT NOT NULL,
                verdict TEXT NOT NULL,
                evaluated_at REAL NOT NULL,
                findings_json TEXT NOT NULL,
                evidence_set_hash TEXT NOT NULL,
                receipt_hash TEXT NOT NULL UNIQUE,
                evaluator_agent_id TEXT NOT NULL REFERENCES agents(id),
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS truth_evidence_actions (
                id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL REFERENCES truth_claims(id),
                obligation_key TEXT NOT NULL,
                description TEXT NOT NULL,
                authority TEXT NOT NULL,
                independence_group TEXT NOT NULL,
                action_key TEXT NOT NULL,
                action_class TEXT NOT NULL,
                action_parameters_json TEXT NOT NULL,
                cost_units REAL NOT NULL DEFAULT 0,
                available INTEGER NOT NULL DEFAULT 1,
                deadline_at REAL,
                created_by_agent_id TEXT NOT NULL REFERENCES agents(id),
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS truth_acquisition_requests (
                id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL REFERENCES truth_claims(id),
                receipt_id TEXT NOT NULL REFERENCES truth_receipts(id),
                evidence_action_id TEXT NOT NULL REFERENCES truth_evidence_actions(id),
                governance_request_id TEXT NOT NULL REFERENCES governance_action_requests(id),
                governance_receipt_hash TEXT,
                status TEXT NOT NULL,
                created_at REAL NOT NULL,
                UNIQUE(receipt_id, evidence_action_id)
            );

            CREATE INDEX IF NOT EXISTS idx_truth_evidence_claim
                ON truth_evidence(claim_id, obligation_key);
            CREATE INDEX IF NOT EXISTS idx_truth_receipts_claim
                ON truth_receipts(claim_id, evaluated_at);
            CREATE INDEX IF NOT EXISTS idx_truth_actions_claim
                ON truth_evidence_actions(claim_id, obligation_key, available);
            """
        )
        self.runtime.conn.commit()

    def register_claim(
        self,
        *,
        claim_id: str,
        subject: str,
        statement: str,
        obligations: Iterable[Dict[str, Any]],
        created_by_agent_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.runtime._require_agent(created_by_agent_id)
        claim_id = claim_id.strip()
        subject = subject.strip()
        statement = statement.strip()
        if not claim_id or not subject or not statement:
            raise TruthEngineError("claim_id, subject, and statement are required")
        context = context or {}
        if not isinstance(context, dict):
            raise TruthEngineError("context must be an object")

        normalized = self._normalize_obligations(obligations)
        claim_payload = {
            "claim_id": claim_id,
            "subject": subject,
            "statement": statement,
            "context": context,
            "obligations": normalized,
        }
        claim_hash = _sha(claim_payload)
        ts = _now()
        try:
            self.runtime.conn.execute(
                """
                INSERT INTO truth_claims(
                    id, subject, statement, context_json, claim_hash,
                    created_by_agent_id, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                """,
                (
                    claim_id,
                    subject,
                    statement,
                    _json(context),
                    claim_hash,
                    created_by_agent_id,
                    ts,
                    ts,
                ),
            )
            self.runtime.conn.executemany(
                """
                INSERT INTO truth_obligations(
                    claim_id, obligation_key, description, allowed_authorities_json,
                    min_supporting_sources, min_independent_groups, max_age_seconds,
                    required, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        claim_id,
                        item["key"],
                        item["description"],
                        _json(item["allowed_authorities"]),
                        item["min_supporting_sources"],
                        item["min_independent_groups"],
                        item["max_age_seconds"],
                        int(item["required"]),
                        ts,
                    )
                    for item in normalized
                ],
            )
        except Exception as exc:
            self.runtime.conn.rollback()
            raise TruthEngineError("claim identity already exists or obligations are invalid") from exc
        self.runtime.conn.commit()
        self.runtime.append_event(
            created_by_agent_id,
            "TRUTH_CLAIM_REGISTERED",
            {
                "claim_id": claim_id,
                "claim_hash": claim_hash,
                "obligation_count": len(normalized),
            },
        )
        return self.get_claim(claim_id)

    def add_evidence(
        self,
        claim_id: str,
        *,
        evidence_id: str,
        obligation_key: str,
        stance: str,
        authority: str,
        source_id: str,
        independence_group: str,
        observed_at: float,
        source_ref: str,
        source_sha256: str,
        created_by_agent_id: str,
        admissible: bool = True,
        valid_until: Optional[float] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.runtime._require_agent(created_by_agent_id)
        self._require_claim(claim_id)
        obligation = self._require_obligation(claim_id, obligation_key)
        stance = stance.strip().upper()
        authority = authority.strip()
        source_id = source_id.strip()
        independence_group = independence_group.strip()
        source_ref = source_ref.strip()
        evidence_id = evidence_id.strip()
        if stance not in VALID_STANCES:
            raise TruthEngineError(f"unsupported evidence stance: {stance}")
        if not all([evidence_id, authority, source_id, independence_group, source_ref]):
            raise TruthEngineError("evidence identity/source fields must be non-empty")
        if not _valid_sha256(source_sha256):
            raise TruthEngineError("source_sha256 must be a SHA-256 digest")
        observed_at = float(observed_at)
        if not math.isfinite(observed_at):
            raise TruthEngineError("observed_at must be finite")
        if valid_until is not None:
            valid_until = float(valid_until)
            if not math.isfinite(valid_until) or valid_until < observed_at:
                raise TruthEngineError("valid_until must be finite and >= observed_at")
        payload = payload or {}
        if not isinstance(payload, dict):
            raise TruthEngineError("payload must be an object")

        evidence_payload = {
            "evidence_id": evidence_id,
            "claim_id": claim_id,
            "obligation_key": obligation_key,
            "stance": stance,
            "authority": authority,
            "source_id": source_id,
            "independence_group": independence_group,
            "observed_at": observed_at,
            "source_ref": source_ref,
            "source_sha256": source_sha256,
            "admissible": bool(admissible),
            "valid_until": valid_until,
            "payload": payload,
        }
        evidence_hash = _sha(evidence_payload)
        try:
            self.runtime.conn.execute(
                """
                INSERT INTO truth_evidence(
                    id, claim_id, obligation_key, stance, authority, source_id,
                    independence_group, observed_at, source_ref, source_sha256,
                    admissible, valid_until, payload_json, evidence_hash,
                    created_by_agent_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_id,
                    claim_id,
                    obligation["obligation_key"],
                    stance,
                    authority,
                    source_id,
                    independence_group,
                    observed_at,
                    source_ref,
                    source_sha256,
                    int(bool(admissible)),
                    valid_until,
                    _json(payload),
                    evidence_hash,
                    created_by_agent_id,
                    _now(),
                ),
            )
        except Exception as exc:
            self.runtime.conn.rollback()
            raise TruthEngineError("evidence is duplicate or evidence_id already exists") from exc
        self.runtime.conn.commit()
        self.runtime.append_event(
            created_by_agent_id,
            "TRUTH_EVIDENCE_ADDED",
            {
                "claim_id": claim_id,
                "evidence_id": evidence_id,
                "obligation_key": obligation_key,
                "stance": stance,
                "evidence_hash": evidence_hash,
            },
        )
        return self.get_evidence(evidence_id)

    def evaluate(
        self,
        claim_id: str,
        *,
        evaluator_agent_id: str,
        evaluated_at: Optional[float] = None,
    ) -> Dict[str, Any]:
        self.runtime._require_agent(evaluator_agent_id)
        claim = self._require_claim(claim_id)
        obligations = self._obligations(claim_id)
        evidence = self._evidence_rows(claim_id)
        if not obligations:
            raise TruthEngineError("claim has no proof obligations")
        evaluated_at = _now() if evaluated_at is None else float(evaluated_at)
        if not math.isfinite(evaluated_at):
            raise TruthEngineError("evaluated_at must be finite")

        findings = []
        relevant_total = 0
        for obligation in obligations:
            relevant = [
                row for row in evidence if row["obligation_key"] == obligation["obligation_key"]
            ]
            relevant_total += len(relevant)
            supports = []
            contradicts = []
            stale = []
            inadmissible = []

            for row in relevant:
                status = self._evidence_usability(row, obligation, evaluated_at)
                if status == "STALE":
                    stale.append(row)
                    continue
                if status == "INADMISSIBLE":
                    inadmissible.append(row)
                    continue
                if row["stance"] == "SUPPORTS":
                    supports.append(row)
                else:
                    contradicts.append(row)

            support_groups = sorted({row["independence_group"] for row in supports})

            if supports and contradicts:
                finding_status = "CONFLICTED"
                reason = "admissible evidence both supports and contradicts this obligation"
            elif contradicts:
                finding_status = "CONTRADICTED"
                reason = "admissible evidence contradicts this obligation"
            elif 0 < len(supports) < int(obligation["min_supporting_sources"]):
                finding_status = "INSUFFICIENT_SUPPORT"
                reason = (
                    f"need {obligation['min_supporting_sources']} supporting source(s); "
                    f"have {len(supports)}"
                )
            elif supports and len(support_groups) < int(obligation["min_independent_groups"]):
                finding_status = "INSUFFICIENT_INDEPENDENCE"
                reason = (
                    f"need {obligation['min_independent_groups']} independent group(s); "
                    f"have {len(support_groups)}"
                )
            elif supports:
                finding_status = "SATISFIED"
                reason = "authority, freshness, support, and independence requirements satisfied"
            elif stale:
                finding_status = "STALE"
                reason = "relevant evidence exists but is no longer fresh/valid"
            elif inadmissible:
                finding_status = "INADMISSIBLE"
                reason = "relevant evidence exists but is not admissible for this obligation"
            else:
                finding_status = "MISSING"
                reason = "no evidence supplied for this obligation"

            findings.append(
                {
                    "key": obligation["obligation_key"],
                    "required": bool(obligation["required"]),
                    "status": finding_status,
                    "reason": reason,
                    "supporting_evidence_ids": [row["id"] for row in supports],
                    "contradicting_evidence_ids": [row["id"] for row in contradicts],
                    "stale_evidence_ids": [row["id"] for row in stale],
                    "inadmissible_evidence_ids": [row["id"] for row in inadmissible],
                    "independent_groups": support_groups,
                }
            )

        required_findings = [f for f in findings if f["required"]]
        if any(f["status"] in {"CONFLICTED", "CONTRADICTED"} for f in required_findings):
            verdict = "CONTESTED"
        elif required_findings and all(f["status"] == "SATISFIED" for f in required_findings):
            verdict = "PROVEN"
        elif relevant_total == 0:
            verdict = "UNKNOWN"
        else:
            verdict = "NOT_PROVEN"

        evidence_set_hash = _sha(
            sorted((row["id"], row["evidence_hash"]) for row in evidence)
        )
        receipt_payload = {
            "claim_id": claim_id,
            "claim_hash": claim["claim_hash"],
            "verdict": verdict,
            "evaluated_at": evaluated_at,
            "findings": findings,
            "evidence_set_hash": evidence_set_hash,
        }
        receipt_hash = _sha(receipt_payload)
        receipt_id = f"truthreceipt_{uuid.uuid4().hex}"
        self.runtime.conn.execute(
            """
            INSERT INTO truth_receipts(
                id, claim_id, claim_hash, verdict, evaluated_at, findings_json,
                evidence_set_hash, receipt_hash, evaluator_agent_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                receipt_id,
                claim_id,
                claim["claim_hash"],
                verdict,
                evaluated_at,
                _json(findings),
                evidence_set_hash,
                receipt_hash,
                evaluator_agent_id,
                _now(),
            ),
        )
        self.runtime.conn.commit()
        self.runtime.append_event(
            evaluator_agent_id,
            "TRUTH_RECEIPT_CREATED",
            {
                "receipt_id": receipt_id,
                "claim_id": claim_id,
                "verdict": verdict,
                "receipt_hash": receipt_hash,
                "evidence_set_hash": evidence_set_hash,
            },
        )
        return self.get_receipt(receipt_id)

    def register_evidence_action(
        self,
        claim_id: str,
        *,
        action_id: str,
        obligation_key: str,
        description: str,
        authority: str,
        independence_group: str,
        action_key: str,
        action_class: str,
        action_parameters: Dict[str, Any],
        created_by_agent_id: str,
        cost_units: float = 0.0,
        available: bool = True,
        deadline_at: Optional[float] = None,
    ) -> Dict[str, Any]:
        self.runtime._require_agent(created_by_agent_id)
        self._require_claim(claim_id)
        self._require_obligation(claim_id, obligation_key)
        action_id = action_id.strip()
        description = description.strip()
        authority = authority.strip()
        independence_group = independence_group.strip()
        action_key = action_key.strip()
        action_class = action_class.strip().upper()
        if not all([action_id, description, authority, independence_group, action_key, action_class]):
            raise TruthEngineError("evidence action identity fields must be non-empty")
        if not isinstance(action_parameters, dict):
            raise TruthEngineError("action_parameters must be an object")
        cost_units = float(cost_units)
        if not math.isfinite(cost_units) or cost_units < 0:
            raise TruthEngineError("cost_units must be finite and non-negative")
        if deadline_at is not None:
            deadline_at = float(deadline_at)
            if not math.isfinite(deadline_at):
                raise TruthEngineError("deadline_at must be finite")

        try:
            self.runtime.conn.execute(
                """
                INSERT INTO truth_evidence_actions(
                    id, claim_id, obligation_key, description, authority,
                    independence_group, action_key, action_class,
                    action_parameters_json, cost_units, available, deadline_at,
                    created_by_agent_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action_id,
                    claim_id,
                    obligation_key,
                    description,
                    authority,
                    independence_group,
                    action_key,
                    action_class,
                    _json(action_parameters),
                    cost_units,
                    int(bool(available)),
                    deadline_at,
                    created_by_agent_id,
                    _now(),
                ),
            )
        except Exception as exc:
            self.runtime.conn.rollback()
            raise TruthEngineError("evidence action identity already exists") from exc
        self.runtime.conn.commit()
        return self.get_evidence_action(action_id)

    def rank_next_evidence(
        self,
        claim_id: str,
        *,
        receipt_id: str,
    ) -> List[RankedEvidenceAction]:
        receipt = self.get_receipt(receipt_id)
        if receipt["claim_id"] != claim_id:
            raise TruthEngineError("receipt is bound to a different claim")
        claim = self._require_claim(claim_id)
        if receipt["claim_hash"] != claim["claim_hash"]:
            raise TruthEngineError("receipt claim hash no longer matches current claim")
        evaluated_at = float(receipt["evaluated_at"])
        baseline_findings = {f["key"]: f for f in receipt["findings"]}
        obligation_map = {
            row["obligation_key"]: row for row in self._obligations(claim_id)
        }
        actions = self.runtime.conn.execute(
            """
            SELECT * FROM truth_evidence_actions
            WHERE claim_id=? AND available=1
            ORDER BY id
            """,
            (claim_id,),
        ).fetchall()
        evidence = self._evidence_rows(claim_id)

        ranked: List[RankedEvidenceAction] = []
        for action in actions:
            obligation = obligation_map[action["obligation_key"]]
            if action["deadline_at"] is not None and float(action["deadline_at"]) < evaluated_at:
                continue
            allowed_authorities = set(json.loads(obligation["allowed_authorities_json"]))
            if action["authority"] not in allowed_authorities:
                continue

            existing_groups = {
                row["independence_group"]
                for row in evidence
                if row["obligation_key"] == action["obligation_key"]
                and row["stance"] == "SUPPORTS"
                and self._evidence_usability(row, obligation, evaluated_at) == "USABLE"
            }
            if action["independence_group"] in existing_groups:
                continue

            counter_verdict, counter_findings = self._counterfactual_support(
                claim_id,
                action,
                evaluated_at=evaluated_at,
            )
            before = baseline_findings[action["obligation_key"]]["status"]
            after = {f["key"]: f for f in counter_findings}[action["obligation_key"]]["status"]
            improved = int(before != "SATISFIED" and after == "SATISFIED")
            verdict_gain = max(
                0,
                self.VERDICT_RANK[counter_verdict] - self.VERDICT_RANK[receipt["verdict"]],
            )
            required_weight = 2 if bool(obligation["required"]) else 1
            numerator = verdict_gain * 4 + improved * required_weight
            if numerator <= 0:
                continue
            priority = numerator / (1.0 + float(action["cost_units"]))
            ranked.append(
                RankedEvidenceAction(
                    action_id=action["id"],
                    obligation_key=action["obligation_key"],
                    description=action["description"],
                    authority=action["authority"],
                    independence_group=action["independence_group"],
                    action_key=action["action_key"],
                    action_class=action["action_class"],
                    action_parameters=json.loads(action["action_parameters_json"]),
                    cost_units=float(action["cost_units"]),
                    baseline_verdict=receipt["verdict"],
                    counterfactual_verdict=counter_verdict,
                    obligations_improved=improved,
                    potential_decision_gain=verdict_gain,
                    priority_score=priority,
                )
            )

        ranked.sort(
            key=lambda x: (
                x.priority_score,
                x.potential_decision_gain,
                x.obligations_improved,
                -x.cost_units,
                x.action_id,
            ),
            reverse=True,
        )
        return ranked

    def request_evidence_acquisition(
        self,
        claim_id: str,
        *,
        receipt_id: str,
        evidence_action_id: str,
        actor_agent_id: str,
    ) -> Dict[str, Any]:
        if self.governance is None:
            raise TruthEngineError("governance is required to request evidence acquisition")
        receipt = self.get_receipt(receipt_id)
        if receipt["claim_id"] != claim_id:
            raise TruthEngineError("receipt is bound to a different claim")
        action = self._require_action(evidence_action_id)
        if action["claim_id"] != claim_id:
            raise TruthEngineError("evidence action is bound to a different claim")

        ranked_ids = {item.action_id for item in self.rank_next_evidence(claim_id, receipt_id=receipt_id)}
        if evidence_action_id not in ranked_ids:
            raise TruthEngineError(
                "evidence action is not currently a useful admissible next-evidence action"
            )

        parameters = {
            "claim_id": claim_id,
            "truth_receipt_id": receipt_id,
            "truth_receipt_hash": receipt["receipt_hash"],
            "evidence_action_id": evidence_action_id,
            "authority": action["authority"],
            "independence_group": action["independence_group"],
            "action_parameters": json.loads(action["action_parameters_json"]),
        }
        decision = self.governance.request_action(
            actor_agent_id,
            action_key=action["action_key"],
            action_class=action["action_class"],
            parameters=parameters,
            cost_units=float(action["cost_units"]),
        )
        request_id = f"truthacq_{uuid.uuid4().hex}"
        self.runtime.conn.execute(
            """
            INSERT INTO truth_acquisition_requests(
                id, claim_id, receipt_id, evidence_action_id,
                governance_request_id, governance_receipt_hash, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                claim_id,
                receipt_id,
                evidence_action_id,
                decision["request_id"],
                decision["receipt_hash"],
                decision["decision"],
                _now(),
            ),
        )
        self.runtime.conn.commit()
        return {
            "id": request_id,
            "claim_id": claim_id,
            "receipt_id": receipt_id,
            "evidence_action_id": evidence_action_id,
            "governance": decision,
        }

    def get_claim(self, claim_id: str) -> Dict[str, Any]:
        row = self._require_claim(claim_id)
        return {
            "id": row["id"],
            "subject": row["subject"],
            "statement": row["statement"],
            "context": json.loads(row["context_json"]),
            "claim_hash": row["claim_hash"],
            "created_by_agent_id": row["created_by_agent_id"],
            "status": row["status"],
            "obligations": [
                {
                    "key": item["obligation_key"],
                    "description": item["description"],
                    "allowed_authorities": json.loads(item["allowed_authorities_json"]),
                    "min_supporting_sources": item["min_supporting_sources"],
                    "min_independent_groups": item["min_independent_groups"],
                    "max_age_seconds": item["max_age_seconds"],
                    "required": bool(item["required"]),
                }
                for item in self._obligations(claim_id)
            ],
        }

    def get_evidence(self, evidence_id: str) -> Dict[str, Any]:
        row = self.runtime.conn.execute(
            "SELECT * FROM truth_evidence WHERE id=?",
            (evidence_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown truth evidence: {evidence_id}")
        return {
            "id": row["id"],
            "claim_id": row["claim_id"],
            "obligation_key": row["obligation_key"],
            "stance": row["stance"],
            "authority": row["authority"],
            "source_id": row["source_id"],
            "independence_group": row["independence_group"],
            "observed_at": row["observed_at"],
            "source_ref": row["source_ref"],
            "source_sha256": row["source_sha256"],
            "admissible": bool(row["admissible"]),
            "valid_until": row["valid_until"],
            "payload": json.loads(row["payload_json"]),
            "evidence_hash": row["evidence_hash"],
        }

    def get_receipt(self, receipt_id: str) -> Dict[str, Any]:
        row = self.runtime.conn.execute(
            "SELECT * FROM truth_receipts WHERE id=?",
            (receipt_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown truth receipt: {receipt_id}")
        return {
            "id": row["id"],
            "claim_id": row["claim_id"],
            "claim_hash": row["claim_hash"],
            "verdict": row["verdict"],
            "evaluated_at": row["evaluated_at"],
            "findings": json.loads(row["findings_json"]),
            "evidence_set_hash": row["evidence_set_hash"],
            "receipt_hash": row["receipt_hash"],
            "evaluator_agent_id": row["evaluator_agent_id"],
        }

    def get_evidence_action(self, action_id: str) -> Dict[str, Any]:
        row = self._require_action(action_id)
        return {
            "id": row["id"],
            "claim_id": row["claim_id"],
            "obligation_key": row["obligation_key"],
            "description": row["description"],
            "authority": row["authority"],
            "independence_group": row["independence_group"],
            "action_key": row["action_key"],
            "action_class": row["action_class"],
            "action_parameters": json.loads(row["action_parameters_json"]),
            "cost_units": row["cost_units"],
            "available": bool(row["available"]),
            "deadline_at": row["deadline_at"],
        }

    def _counterfactual_support(
        self,
        claim_id: str,
        action,
        *,
        evaluated_at: float,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        # Counterfactual evidence lives only in memory and is never inserted into truth_evidence.
        fake_source_hash = _sha({"hypothetical_action_id": action["id"]})
        rows = [dict(row) for row in self._evidence_rows(claim_id)]
        rows.append(
            {
                "id": f"hypothetical:{action['id']}",
                "claim_id": claim_id,
                "obligation_key": action["obligation_key"],
                "stance": "SUPPORTS",
                "authority": action["authority"],
                "source_id": f"hypothetical:{action['id']}",
                "independence_group": action["independence_group"],
                "observed_at": evaluated_at,
                "source_ref": f"hypothetical:{action['id']}",
                "source_sha256": fake_source_hash,
                "admissible": 1,
                "valid_until": None,
                "payload_json": _json({"counterfactual": True}),
                "evidence_hash": _sha({"hypothetical": action["id"]}),
            }
        )
        obligations = self._obligations(claim_id)
        findings = []
        relevant_total = 0
        for obligation in obligations:
            relevant = [r for r in rows if r["obligation_key"] == obligation["obligation_key"]]
            relevant_total += len(relevant)
            supports = []
            contradicts = []
            stale = []
            inadmissible = []
            for row in relevant:
                status = self._evidence_usability(row, obligation, evaluated_at)
                if status == "STALE":
                    stale.append(row)
                elif status == "INADMISSIBLE":
                    inadmissible.append(row)
                elif row["stance"] == "SUPPORTS":
                    supports.append(row)
                else:
                    contradicts.append(row)
            groups = sorted({r["independence_group"] for r in supports})
            if supports and contradicts:
                status = "CONFLICTED"
            elif contradicts:
                status = "CONTRADICTED"
            elif 0 < len(supports) < int(obligation["min_supporting_sources"]):
                status = "INSUFFICIENT_SUPPORT"
            elif supports and len(groups) < int(obligation["min_independent_groups"]):
                status = "INSUFFICIENT_INDEPENDENCE"
            elif supports:
                status = "SATISFIED"
            elif stale:
                status = "STALE"
            elif inadmissible:
                status = "INADMISSIBLE"
            else:
                status = "MISSING"
            findings.append(
                {
                    "key": obligation["obligation_key"],
                    "required": bool(obligation["required"]),
                    "status": status,
                }
            )
        required = [f for f in findings if f["required"]]
        if any(f["status"] in {"CONFLICTED", "CONTRADICTED"} for f in required):
            verdict = "CONTESTED"
        elif required and all(f["status"] == "SATISFIED" for f in required):
            verdict = "PROVEN"
        elif relevant_total == 0:
            verdict = "UNKNOWN"
        else:
            verdict = "NOT_PROVEN"
        return verdict, findings

    def _evidence_usability(self, row, obligation, evaluated_at: float) -> str:
        if not bool(row["admissible"]):
            return "INADMISSIBLE"
        allowed = set(json.loads(obligation["allowed_authorities_json"]))
        if row["authority"] not in allowed:
            return "INADMISSIBLE"
        observed_at = float(row["observed_at"])
        if observed_at > evaluated_at:
            return "INADMISSIBLE"
        if row["valid_until"] is not None and float(row["valid_until"]) < evaluated_at:
            return "STALE"
        if obligation["max_age_seconds"] is not None:
            if evaluated_at - observed_at > float(obligation["max_age_seconds"]):
                return "STALE"
        return "USABLE"

    def _normalize_obligations(self, obligations: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        items = list(obligations)
        if not items:
            raise TruthEngineError("at least one proof obligation is required")
        out = []
        seen = set()
        for item in items:
            key = str(item.get("key", "")).strip()
            description = str(item.get("description", "")).strip()
            authorities = sorted(
                {str(x).strip() for x in item.get("allowed_authorities", []) if str(x).strip()}
            )
            min_support = int(item.get("min_supporting_sources", 1))
            min_groups = int(item.get("min_independent_groups", 1))
            max_age = item.get("max_age_seconds")
            if not key or not description or not authorities:
                raise TruthEngineError(
                    "each obligation needs key, description, and allowed_authorities"
                )
            if key in seen:
                raise TruthEngineError(f"duplicate obligation key: {key}")
            if min_support < 1 or min_groups < 1:
                raise TruthEngineError("minimum source/group counts must be >= 1")
            if max_age is not None:
                max_age = float(max_age)
                if not math.isfinite(max_age) or max_age <= 0:
                    raise TruthEngineError("max_age_seconds must be finite and positive")
            seen.add(key)
            out.append(
                {
                    "key": key,
                    "description": description,
                    "allowed_authorities": authorities,
                    "min_supporting_sources": min_support,
                    "min_independent_groups": min_groups,
                    "max_age_seconds": max_age,
                    "required": bool(item.get("required", True)),
                }
            )
        if not any(item["required"] for item in out):
            raise TruthEngineError("at least one proof obligation must be required")
        return out

    def _require_claim(self, claim_id: str):
        row = self.runtime.conn.execute(
            "SELECT * FROM truth_claims WHERE id=?",
            (claim_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown truth claim: {claim_id}")
        return row

    def _require_obligation(self, claim_id: str, obligation_key: str):
        row = self.runtime.conn.execute(
            """
            SELECT * FROM truth_obligations
            WHERE claim_id=? AND obligation_key=?
            """,
            (claim_id, obligation_key),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown proof obligation: {claim_id}:{obligation_key}")
        return row

    def _require_action(self, action_id: str):
        row = self.runtime.conn.execute(
            "SELECT * FROM truth_evidence_actions WHERE id=?",
            (action_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown evidence action: {action_id}")
        return row

    def _obligations(self, claim_id: str):
        return self.runtime.conn.execute(
            """
            SELECT * FROM truth_obligations
            WHERE claim_id=?
            ORDER BY obligation_key
            """,
            (claim_id,),
        ).fetchall()

    def _evidence_rows(self, claim_id: str):
        return self.runtime.conn.execute(
            """
            SELECT * FROM truth_evidence
            WHERE claim_id=?
            ORDER BY obligation_key, id
            """,
            (claim_id,),
        ).fetchall()
