"""Verifier-gated self-improvement for the AI Business OS.

Candidate skills/policies may be proposed and evaluated, but they remain inert until they pass
disjoint held-out evaluation, independent verification, multi-agent canary evidence, and an
explicit curator promotion. The currently active champion never changes merely because an agent
claims an improvement.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional

from ai_business_os.persistent_agents.runtime import AgentRuntime


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


class SkillPromotionError(ValueError):
    """Raised when a candidate attempts to bypass the promotion contract."""


class SelfImprovementGate:
    """Deterministic promotion gate for learned skills and policies."""

    MIN_DEV_TASKS = 2
    MIN_HELDOUT_TASKS = 5
    MIN_CANARY_AGENTS = 3

    def __init__(self, runtime: AgentRuntime):
        self.runtime = runtime
        self._migrate()

    def _migrate(self) -> None:
        self.runtime.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS skill_registry (
                skill_key TEXT PRIMARY KEY,
                champion_version TEXT NOT NULL,
                champion_artifact_hash TEXT NOT NULL,
                curator_agent_id TEXT NOT NULL REFERENCES agents(id),
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS skill_versions (
                skill_key TEXT NOT NULL,
                version TEXT NOT NULL,
                artifact_hash TEXT NOT NULL,
                candidate_id TEXT,
                status TEXT NOT NULL,
                promoted_at REAL,
                PRIMARY KEY(skill_key, version)
            );

            CREATE TABLE IF NOT EXISTS skill_candidates (
                id TEXT PRIMARY KEY,
                skill_key TEXT NOT NULL,
                proposer_agent_id TEXT NOT NULL REFERENCES agents(id),
                verifier_agent_id TEXT NOT NULL REFERENCES agents(id),
                curator_agent_id TEXT NOT NULL REFERENCES agents(id),
                baseline_version TEXT NOT NULL,
                candidate_version TEXT NOT NULL,
                baseline_artifact_hash TEXT NOT NULL,
                candidate_artifact_hash TEXT NOT NULL,
                mutation_hash TEXT NOT NULL,
                min_heldout_delta REAL NOT NULL,
                dev_manifest_hash TEXT,
                heldout_manifest_hash TEXT,
                status TEXT NOT NULL DEFAULT 'DRAFT',
                evaluation_summary_json TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS candidate_tasks (
                candidate_id TEXT NOT NULL REFERENCES skill_candidates(id),
                split TEXT NOT NULL,
                task_id TEXT NOT NULL,
                PRIMARY KEY(candidate_id, split, task_id)
            );

            CREATE TABLE IF NOT EXISTS candidate_evaluations (
                candidate_id TEXT NOT NULL REFERENCES skill_candidates(id),
                split TEXT NOT NULL,
                task_id TEXT NOT NULL,
                verifier_agent_id TEXT NOT NULL REFERENCES agents(id),
                baseline_score REAL NOT NULL,
                candidate_score REAL NOT NULL,
                hard_regression INTEGER NOT NULL,
                evidence_json TEXT NOT NULL,
                evidence_hash TEXT NOT NULL,
                created_at REAL NOT NULL,
                PRIMARY KEY(candidate_id, split, task_id)
            );

            CREATE TABLE IF NOT EXISTS candidate_canaries (
                candidate_id TEXT NOT NULL REFERENCES skill_candidates(id),
                agent_id TEXT NOT NULL REFERENCES agents(id),
                success INTEGER NOT NULL,
                regression INTEGER NOT NULL,
                evidence_json TEXT NOT NULL,
                evidence_hash TEXT NOT NULL,
                created_at REAL NOT NULL,
                PRIMARY KEY(candidate_id, agent_id)
            );

            CREATE TABLE IF NOT EXISTS skill_promotion_history (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_key TEXT NOT NULL,
                candidate_id TEXT,
                from_version TEXT,
                to_version TEXT NOT NULL,
                actor_agent_id TEXT NOT NULL REFERENCES agents(id),
                decision TEXT NOT NULL,
                reason TEXT,
                evidence_hash TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_skill_candidates_status
                ON skill_candidates(skill_key, status);
            CREATE INDEX IF NOT EXISTS idx_candidate_eval
                ON candidate_evaluations(candidate_id, split);
            """
        )
        self.runtime.conn.commit()

    def register_champion(
        self,
        *,
        skill_key: str,
        version: str,
        artifact_hash: str,
        curator_agent_id: str,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        self.runtime._require_agent(curator_agent_id)
        self._validate_skill_identity(skill_key, version, artifact_hash)
        if not evidence:
            raise SkillPromotionError("champion registration requires evidence")
        existing = self.runtime.conn.execute(
            "SELECT * FROM skill_registry WHERE skill_key = ?",
            (skill_key,),
        ).fetchone()
        if existing is not None:
            raise SkillPromotionError("skill already has a registered champion")
        ts = _now()
        self.runtime.conn.execute(
            """
            INSERT INTO skill_registry(
                skill_key, champion_version, champion_artifact_hash, curator_agent_id, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (skill_key, version, artifact_hash, curator_agent_id, ts),
        )
        self.runtime.conn.execute(
            """
            INSERT INTO skill_versions(skill_key, version, artifact_hash, status, promoted_at)
            VALUES (?, ?, ?, 'GLOBAL', ?)
            """,
            (skill_key, version, artifact_hash, ts),
        )
        evidence_hash = _sha(evidence)
        self.runtime.conn.execute(
            """
            INSERT INTO skill_promotion_history(
                skill_key, candidate_id, from_version, to_version, actor_agent_id,
                decision, reason, evidence_hash, created_at
            ) VALUES (?, NULL, NULL, ?, ?, 'INITIAL_CHAMPION', ?, ?, ?)
            """,
            (skill_key, version, curator_agent_id, "initial registration", evidence_hash, ts),
        )
        self.runtime.conn.commit()
        self.runtime.append_event(
            curator_agent_id,
            "SKILL_CHAMPION_REGISTERED",
            {
                "skill_key": skill_key,
                "version": version,
                "artifact_hash": artifact_hash,
                "evidence_hash": evidence_hash,
            },
        )
        return self.get_active_skill(skill_key)

    def propose_candidate(
        self,
        *,
        skill_key: str,
        candidate_version: str,
        candidate_artifact_hash: str,
        mutation: Dict[str, Any],
        proposer_agent_id: str,
        verifier_agent_id: str,
        curator_agent_id: str,
        min_heldout_delta: float = 0.01,
        candidate_id: Optional[str] = None,
    ) -> str:
        champion = self.get_active_skill(skill_key)
        for agent_id in (proposer_agent_id, verifier_agent_id, curator_agent_id):
            self.runtime._require_agent(agent_id)
        if len({proposer_agent_id, verifier_agent_id, curator_agent_id}) != 3:
            raise SkillPromotionError(
                "proposer, verifier, and curator must be three distinct agents"
            )
        if curator_agent_id != champion["curator_agent_id"]:
            raise SkillPromotionError("candidate must use the skill's designated curator")
        self._validate_skill_identity(skill_key, candidate_version, candidate_artifact_hash)
        if candidate_version == champion["version"]:
            raise SkillPromotionError("candidate version must differ from the champion")
        if candidate_artifact_hash == champion["artifact_hash"]:
            raise SkillPromotionError("candidate artifact must differ from the champion")
        if not mutation:
            raise SkillPromotionError("candidate requires a non-empty mutation description")
        if not math.isfinite(min_heldout_delta) or min_heldout_delta < 0:
            raise SkillPromotionError("min_heldout_delta must be finite and non-negative")

        mutation_hash = _sha(
            {
                "skill_key": skill_key,
                "baseline_version": champion["version"],
                "baseline_artifact_hash": champion["artifact_hash"],
                "candidate_version": candidate_version,
                "candidate_artifact_hash": candidate_artifact_hash,
                "mutation": mutation,
            }
        )
        candidate_id = candidate_id or f"skillcand_{uuid.uuid4().hex}"
        ts = _now()
        self.runtime.conn.execute(
            """
            INSERT INTO skill_candidates(
                id, skill_key, proposer_agent_id, verifier_agent_id, curator_agent_id,
                baseline_version, candidate_version, baseline_artifact_hash,
                candidate_artifact_hash, mutation_hash, min_heldout_delta,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT', ?, ?)
            """,
            (
                candidate_id,
                skill_key,
                proposer_agent_id,
                verifier_agent_id,
                curator_agent_id,
                champion["version"],
                candidate_version,
                champion["artifact_hash"],
                candidate_artifact_hash,
                mutation_hash,
                float(min_heldout_delta),
                ts,
                ts,
            ),
        )
        self.runtime.conn.commit()
        self.runtime.append_event(
            proposer_agent_id,
            "SKILL_CANDIDATE_PROPOSED",
            {
                "candidate_id": candidate_id,
                "skill_key": skill_key,
                "baseline_version": champion["version"],
                "candidate_version": candidate_version,
                "mutation_hash": mutation_hash,
            },
        )
        return candidate_id

    def freeze_evaluation_manifest(
        self,
        candidate_id: str,
        *,
        dev_task_ids: Iterable[str],
        heldout_task_ids: Iterable[str],
    ) -> Dict[str, Any]:
        candidate = self._require_candidate(candidate_id)
        if candidate["status"] != "DRAFT":
            raise SkillPromotionError("evaluation manifest can only be frozen from DRAFT")

        dev = self._normalize_task_ids(dev_task_ids, "dev")
        heldout = self._normalize_task_ids(heldout_task_ids, "heldout")
        if len(dev) < self.MIN_DEV_TASKS:
            raise SkillPromotionError(
                f"at least {self.MIN_DEV_TASKS} development tasks are required"
            )
        if len(heldout) < self.MIN_HELDOUT_TASKS:
            raise SkillPromotionError(
                f"at least {self.MIN_HELDOUT_TASKS} held-out tasks are required"
            )
        overlap = set(dev) & set(heldout)
        if overlap:
            raise SkillPromotionError(
                f"development and held-out splits must be disjoint: {sorted(overlap)}"
            )

        dev_hash = _sha({"split": "dev", "tasks": dev})
        heldout_hash = _sha({"split": "heldout", "tasks": heldout})
        for split, task_ids in (("dev", dev), ("heldout", heldout)):
            self.runtime.conn.executemany(
                """
                INSERT INTO candidate_tasks(candidate_id, split, task_id)
                VALUES (?, ?, ?)
                """,
                [(candidate_id, split, task_id) for task_id in task_ids],
            )
        self.runtime.conn.execute(
            """
            UPDATE skill_candidates
            SET dev_manifest_hash = ?, heldout_manifest_hash = ?,
                status = 'EVALUATING', updated_at = ?
            WHERE id = ?
            """,
            (dev_hash, heldout_hash, _now(), candidate_id),
        )
        self.runtime.conn.commit()
        self.runtime.append_event(
            str(candidate["curator_agent_id"]),
            "SKILL_EVALUATION_MANIFEST_FROZEN",
            {
                "candidate_id": candidate_id,
                "dev_manifest_hash": dev_hash,
                "heldout_manifest_hash": heldout_hash,
                "dev_count": len(dev),
                "heldout_count": len(heldout),
            },
        )
        return self.get_candidate(candidate_id)

    def record_evaluation(
        self,
        candidate_id: str,
        *,
        verifier_agent_id: str,
        split: str,
        task_id: str,
        baseline_score: float,
        candidate_score: float,
        hard_regression: bool,
        evidence: Dict[str, Any],
    ) -> None:
        candidate = self._require_candidate(candidate_id)
        if candidate["status"] != "EVALUATING":
            raise SkillPromotionError("candidate is not accepting evaluation results")
        if verifier_agent_id != candidate["verifier_agent_id"]:
            raise SkillPromotionError("only the assigned independent verifier may score tasks")
        if verifier_agent_id == candidate["proposer_agent_id"]:
            raise SkillPromotionError("candidate proposer cannot verify its own candidate")
        if split not in {"dev", "heldout"}:
            raise SkillPromotionError("split must be dev or heldout")
        if not task_id or not isinstance(task_id, str):
            raise SkillPromotionError("task_id must be a non-empty string")
        task = self.runtime.conn.execute(
            """
            SELECT 1 FROM candidate_tasks
            WHERE candidate_id = ? AND split = ? AND task_id = ?
            """,
            (candidate_id, split, task_id),
        ).fetchone()
        if task is None:
            raise SkillPromotionError("evaluation task is not in the frozen manifest")
        if not math.isfinite(float(baseline_score)) or not math.isfinite(float(candidate_score)):
            raise SkillPromotionError("evaluation scores must be finite")
        if not evidence:
            raise SkillPromotionError("evaluation result requires evidence")

        evidence_payload = {
            "candidate_id": candidate_id,
            "split": split,
            "task_id": task_id,
            "baseline_score": float(baseline_score),
            "candidate_score": float(candidate_score),
            "hard_regression": bool(hard_regression),
            "evidence": evidence,
        }
        evidence_hash = _sha(evidence_payload)
        try:
            self.runtime.conn.execute(
                """
                INSERT INTO candidate_evaluations(
                    candidate_id, split, task_id, verifier_agent_id, baseline_score,
                    candidate_score, hard_regression, evidence_json, evidence_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    split,
                    task_id,
                    verifier_agent_id,
                    float(baseline_score),
                    float(candidate_score),
                    int(bool(hard_regression)),
                    _json(evidence),
                    evidence_hash,
                    _now(),
                ),
            )
        except Exception as exc:
            self.runtime.conn.rollback()
            raise SkillPromotionError(
                "evaluation results are immutable; duplicate task results are not allowed"
            ) from exc
        self.runtime.conn.commit()
        self.runtime.append_event(
            verifier_agent_id,
            "SKILL_EVALUATION_RECORDED",
            {
                "candidate_id": candidate_id,
                "split": split,
                "task_id": task_id,
                "evidence_hash": evidence_hash,
            },
        )

    def assess_candidate(
        self,
        candidate_id: str,
        *,
        verifier_agent_id: str,
    ) -> Dict[str, Any]:
        candidate = self._require_candidate(candidate_id)
        if candidate["status"] != "EVALUATING":
            raise SkillPromotionError("candidate must be EVALUATING before assessment")
        if verifier_agent_id != candidate["verifier_agent_id"]:
            raise SkillPromotionError("only the assigned verifier may assess the candidate")

        expected = self.runtime.conn.execute(
            """
            SELECT split, task_id FROM candidate_tasks
            WHERE candidate_id = ?
            ORDER BY split, task_id
            """,
            (candidate_id,),
        ).fetchall()
        results = self.runtime.conn.execute(
            """
            SELECT * FROM candidate_evaluations
            WHERE candidate_id = ?
            ORDER BY split, task_id
            """,
            (candidate_id,),
        ).fetchall()
        expected_keys = {(r["split"], r["task_id"]) for r in expected}
        result_keys = {(r["split"], r["task_id"]) for r in results}
        missing = expected_keys - result_keys
        if missing:
            raise SkillPromotionError(
                f"candidate is missing frozen evaluation results: {sorted(missing)}"
            )

        hard_regressions = [r for r in results if bool(r["hard_regression"])]
        dev = [r for r in results if r["split"] == "dev"]
        heldout = [r for r in results if r["split"] == "heldout"]
        dev_delta = sum(r["candidate_score"] - r["baseline_score"] for r in dev) / len(dev)
        heldout_delta = (
            sum(r["candidate_score"] - r["baseline_score"] for r in heldout) / len(heldout)
        )
        no_dev_improvement = dev_delta <= 0
        insufficient_heldout = heldout_delta < float(candidate["min_heldout_delta"])

        if hard_regressions:
            status = "QUARANTINED"
            reason = "hard regression observed"
        elif no_dev_improvement:
            status = "REJECTED"
            reason = "candidate did not improve development performance"
        elif insufficient_heldout:
            status = "REJECTED"
            reason = "candidate failed minimum held-out improvement"
        else:
            status = "VERIFIED"
            reason = "held-out verifier gate passed"

        summary = {
            "candidate_id": candidate_id,
            "status": status,
            "reason": reason,
            "dev_mean_delta": dev_delta,
            "heldout_mean_delta": heldout_delta,
            "min_heldout_delta": candidate["min_heldout_delta"],
            "hard_regression_count": len(hard_regressions),
            "dev_count": len(dev),
            "heldout_count": len(heldout),
            "dev_manifest_hash": candidate["dev_manifest_hash"],
            "heldout_manifest_hash": candidate["heldout_manifest_hash"],
            "evaluation_evidence_hashes": [r["evidence_hash"] for r in results],
        }
        summary_hash = _sha(summary)
        summary["summary_hash"] = summary_hash
        self.runtime.conn.execute(
            """
            UPDATE skill_candidates
            SET status = ?, evaluation_summary_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, _json(summary), _now(), candidate_id),
        )
        self.runtime.conn.commit()
        self.runtime.append_event(
            verifier_agent_id,
            "SKILL_CANDIDATE_ASSESSED",
            {
                "candidate_id": candidate_id,
                "status": status,
                "summary_hash": summary_hash,
                "reason": reason,
            },
        )
        return self.get_candidate(candidate_id)

    def record_canary(
        self,
        candidate_id: str,
        *,
        agent_id: str,
        success: bool,
        regression: bool,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        candidate = self._require_candidate(candidate_id)
        if candidate["status"] not in {"VERIFIED", "CANARY"}:
            raise SkillPromotionError("only VERIFIED/CANARY candidates may enter canary")
        self.runtime._require_agent(agent_id)
        if agent_id in {
            candidate["proposer_agent_id"],
            candidate["verifier_agent_id"],
            candidate["curator_agent_id"],
        }:
            raise SkillPromotionError(
                "canary evidence must come from agents independent of proposer/verifier/curator"
            )
        if not evidence:
            raise SkillPromotionError("canary result requires evidence")
        payload = {
            "candidate_id": candidate_id,
            "agent_id": agent_id,
            "success": bool(success),
            "regression": bool(regression),
            "evidence": evidence,
        }
        evidence_hash = _sha(payload)
        try:
            self.runtime.conn.execute(
                """
                INSERT INTO candidate_canaries(
                    candidate_id, agent_id, success, regression,
                    evidence_json, evidence_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    agent_id,
                    int(bool(success)),
                    int(bool(regression)),
                    _json(evidence),
                    evidence_hash,
                    _now(),
                ),
            )
        except Exception as exc:
            self.runtime.conn.rollback()
            raise SkillPromotionError("each canary agent may report only once") from exc

        canaries = self.runtime.conn.execute(
            "SELECT * FROM candidate_canaries WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchall()
        if any(bool(row["regression"]) for row in canaries):
            status = "QUARANTINED"
        else:
            successful_agents = {
                row["agent_id"] for row in canaries if bool(row["success"])
            }
            status = (
                "GLOBAL_ELIGIBLE"
                if len(successful_agents) >= self.MIN_CANARY_AGENTS
                else "CANARY"
            )
        self.runtime.conn.execute(
            "UPDATE skill_candidates SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now(), candidate_id),
        )
        self.runtime.conn.commit()
        self.runtime.append_event(
            agent_id,
            "SKILL_CANARY_RECORDED",
            {
                "candidate_id": candidate_id,
                "status": status,
                "evidence_hash": evidence_hash,
            },
        )
        return self.get_candidate(candidate_id)

    def promote_global(
        self,
        candidate_id: str,
        *,
        curator_agent_id: str,
        evidence: Dict[str, Any],
        reason: str,
    ) -> Dict[str, Any]:
        candidate = self._require_candidate(candidate_id)
        if curator_agent_id != candidate["curator_agent_id"]:
            raise SkillPromotionError("only the assigned curator may promote this candidate")
        if candidate["status"] != "GLOBAL_ELIGIBLE":
            raise SkillPromotionError(
                "candidate is not GLOBAL_ELIGIBLE; verified/canary alone is insufficient"
            )
        if not evidence:
            raise SkillPromotionError("global promotion requires explicit evidence")
        current = self.get_active_skill(str(candidate["skill_key"]))
        if (
            current["version"] != candidate["baseline_version"]
            or current["artifact_hash"] != candidate["baseline_artifact_hash"]
        ):
            raise SkillPromotionError(
                "champion changed after evaluation; candidate must be re-evaluated"
            )

        ts = _now()
        self.runtime.conn.execute(
            """
            UPDATE skill_versions SET status = 'SUPERSEDED'
            WHERE skill_key = ? AND version = ?
            """,
            (candidate["skill_key"], current["version"]),
        )
        self.runtime.conn.execute(
            """
            INSERT INTO skill_versions(
                skill_key, version, artifact_hash, candidate_id, status, promoted_at
            ) VALUES (?, ?, ?, ?, 'GLOBAL', ?)
            """,
            (
                candidate["skill_key"],
                candidate["candidate_version"],
                candidate["candidate_artifact_hash"],
                candidate_id,
                ts,
            ),
        )
        self.runtime.conn.execute(
            """
            UPDATE skill_registry
            SET champion_version = ?, champion_artifact_hash = ?, updated_at = ?
            WHERE skill_key = ?
            """,
            (
                candidate["candidate_version"],
                candidate["candidate_artifact_hash"],
                ts,
                candidate["skill_key"],
            ),
        )
        self.runtime.conn.execute(
            "UPDATE skill_candidates SET status = 'GLOBAL', updated_at = ? WHERE id = ?",
            (ts, candidate_id),
        )
        evidence_hash = _sha(
            {
                "candidate_id": candidate_id,
                "evaluation_summary": json.loads(candidate["evaluation_summary_json"]),
                "canaries": self._canary_evidence_hashes(candidate_id),
                "curator_evidence": evidence,
                "reason": reason,
            }
        )
        self.runtime.conn.execute(
            """
            INSERT INTO skill_promotion_history(
                skill_key, candidate_id, from_version, to_version, actor_agent_id,
                decision, reason, evidence_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, 'PROMOTED_GLOBAL', ?, ?, ?)
            """,
            (
                candidate["skill_key"],
                candidate_id,
                current["version"],
                candidate["candidate_version"],
                curator_agent_id,
                reason,
                evidence_hash,
                ts,
            ),
        )
        self.runtime.conn.commit()
        self.runtime.append_event(
            curator_agent_id,
            "SKILL_PROMOTED_GLOBAL",
            {
                "candidate_id": candidate_id,
                "skill_key": candidate["skill_key"],
                "from_version": current["version"],
                "to_version": candidate["candidate_version"],
                "promotion_evidence_hash": evidence_hash,
            },
        )
        return self.get_active_skill(str(candidate["skill_key"]))

    def rollback(
        self,
        *,
        skill_key: str,
        to_version: str,
        curator_agent_id: str,
        reason: str,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        self.runtime._require_agent(curator_agent_id)
        if not reason.strip() or not evidence:
            raise SkillPromotionError("rollback requires a reason and evidence")
        current = self.get_active_skill(skill_key)
        if curator_agent_id != current["curator_agent_id"]:
            raise SkillPromotionError("only the skill's designated curator may roll it back")
        target = self.runtime.conn.execute(
            """
            SELECT * FROM skill_versions
            WHERE skill_key = ? AND version = ?
            """,
            (skill_key, to_version),
        ).fetchone()
        if target is None:
            raise SkillPromotionError("rollback target is not a known skill version")
        if to_version == current["version"]:
            raise SkillPromotionError("rollback target is already active")

        ts = _now()
        self.runtime.conn.execute(
            """
            UPDATE skill_versions SET status = 'SUPERSEDED'
            WHERE skill_key = ? AND version = ?
            """,
            (skill_key, current["version"]),
        )
        self.runtime.conn.execute(
            """
            UPDATE skill_versions SET status = 'GLOBAL', promoted_at = ?
            WHERE skill_key = ? AND version = ?
            """,
            (ts, skill_key, to_version),
        )
        self.runtime.conn.execute(
            """
            UPDATE skill_registry
            SET champion_version = ?, champion_artifact_hash = ?, updated_at = ?
            WHERE skill_key = ?
            """,
            (to_version, target["artifact_hash"], ts, skill_key),
        )
        evidence_hash = _sha(
            {
                "skill_key": skill_key,
                "from_version": current["version"],
                "to_version": to_version,
                "reason": reason,
                "evidence": evidence,
            }
        )
        self.runtime.conn.execute(
            """
            INSERT INTO skill_promotion_history(
                skill_key, candidate_id, from_version, to_version, actor_agent_id,
                decision, reason, evidence_hash, created_at
            ) VALUES (?, NULL, ?, ?, ?, 'ROLLBACK', ?, ?, ?)
            """,
            (
                skill_key,
                current["version"],
                to_version,
                curator_agent_id,
                reason,
                evidence_hash,
                ts,
            ),
        )
        self.runtime.conn.commit()
        self.runtime.append_event(
            curator_agent_id,
            "SKILL_ROLLED_BACK",
            {
                "skill_key": skill_key,
                "from_version": current["version"],
                "to_version": to_version,
                "evidence_hash": evidence_hash,
            },
        )
        return self.get_active_skill(skill_key)

    def get_active_skill(self, skill_key: str) -> Dict[str, Any]:
        row = self.runtime.conn.execute(
            "SELECT * FROM skill_registry WHERE skill_key = ?",
            (skill_key,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown skill: {skill_key}")
        return {
            "skill_key": row["skill_key"],
            "version": row["champion_version"],
            "artifact_hash": row["champion_artifact_hash"],
            "curator_agent_id": row["curator_agent_id"],
            "updated_at": row["updated_at"],
        }

    def get_candidate(self, candidate_id: str) -> Dict[str, Any]:
        row = self._require_candidate(candidate_id)
        return {
            "id": row["id"],
            "skill_key": row["skill_key"],
            "proposer_agent_id": row["proposer_agent_id"],
            "verifier_agent_id": row["verifier_agent_id"],
            "curator_agent_id": row["curator_agent_id"],
            "baseline_version": row["baseline_version"],
            "candidate_version": row["candidate_version"],
            "baseline_artifact_hash": row["baseline_artifact_hash"],
            "candidate_artifact_hash": row["candidate_artifact_hash"],
            "mutation_hash": row["mutation_hash"],
            "min_heldout_delta": row["min_heldout_delta"],
            "dev_manifest_hash": row["dev_manifest_hash"],
            "heldout_manifest_hash": row["heldout_manifest_hash"],
            "status": row["status"],
            "evaluation_summary": (
                json.loads(row["evaluation_summary_json"])
                if row["evaluation_summary_json"]
                else None
            ),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _canary_evidence_hashes(self, candidate_id: str) -> List[str]:
        rows = self.runtime.conn.execute(
            """
            SELECT evidence_hash FROM candidate_canaries
            WHERE candidate_id = ?
            ORDER BY agent_id
            """,
            (candidate_id,),
        ).fetchall()
        return [row["evidence_hash"] for row in rows]

    def _require_candidate(self, candidate_id: str):
        row = self.runtime.conn.execute(
            "SELECT * FROM skill_candidates WHERE id = ?",
            (candidate_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown skill candidate: {candidate_id}")
        return row

    def _normalize_task_ids(self, task_ids: Iterable[str], split: str) -> List[str]:
        normalized = sorted({str(task).strip() for task in task_ids if str(task).strip()})
        if not normalized:
            raise SkillPromotionError(f"{split} split cannot be empty")
        return normalized

    def _validate_skill_identity(self, skill_key: str, version: str, artifact_hash: str) -> None:
        if not skill_key.strip() or not version.strip():
            raise SkillPromotionError("skill_key and version must be non-empty")
        if not _valid_sha256(artifact_hash):
            raise SkillPromotionError("artifact_hash must be a 64-character SHA-256 hex digest")
