"""Persistent production workers for AI Business OS.

Workers only claim goal types with an explicitly registered executor. A worker can submit evidence
for independent verification, but it cannot mark a goal COMPLETE or perform arbitrary external
actions.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol


class WorkerGateway(Protocol):
    def call(self, action: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]: ...


@dataclass(frozen=True)
class WorkerResult:
    summary: str
    evidence_refs: list[dict[str, Any]]

    def canonical_payload(self) -> dict[str, Any]:
        return {"summary": self.summary, "evidence_refs": self.evidence_refs}

    def output_hash(self) -> str:
        raw = json.dumps(
            self.canonical_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


Executor = Callable[[Mapping[str, Any]], WorkerResult]


class PersistentGoalWorker:
    def __init__(
        self,
        gateway: WorkerGateway,
        *,
        worker_instance_id: str,
        executors: Mapping[str, Executor],
        lease_seconds: int = 180,
        heartbeat_seconds: int = 45,
        poll_seconds: float = 15.0,
    ):
        if not worker_instance_id.strip():
            raise ValueError("worker_instance_id is required")
        if not executors:
            raise ValueError("at least one executor must be registered")
        if not 30 <= lease_seconds <= 900:
            raise ValueError("lease_seconds must be between 30 and 900")
        if not 5 <= heartbeat_seconds < lease_seconds:
            raise ValueError("heartbeat_seconds must be >=5 and less than lease_seconds")
        if poll_seconds <= 0:
            raise ValueError("poll_seconds must be > 0")
        self.gateway = gateway
        self.worker_instance_id = worker_instance_id
        self.executors = dict(executors)
        self.lease_seconds = int(lease_seconds)
        self.heartbeat_seconds = int(heartbeat_seconds)
        self.poll_seconds = float(poll_seconds)
        self._stop = threading.Event()
        self._stats_lock = threading.Lock()
        self._stats = {
            "ticks": 0,
            "claims": 0,
            "submitted": 0,
            "failed": 0,
            "last_error": None,
            "last_tick_at": None,
        }

    @property
    def supported_goal_types(self) -> list[str]:
        return sorted(self.executors)

    def stop(self) -> None:
        self._stop.set()

    def snapshot(self) -> dict[str, Any]:
        with self._stats_lock:
            return {
                **self._stats,
                "worker_instance_id": self.worker_instance_id,
                "supported_goal_types": self.supported_goal_types,
                "running": not self._stop.is_set(),
            }

    def run_once(self) -> int:
        planning = self.gateway.call("planning_inputs")
        agents = planning.get("agents", [])
        if not isinstance(agents, list):
            raise RuntimeError("planning_inputs agents must be a list")
        claims = 0
        for row in agents:
            if not isinstance(row, Mapping) or row.get("status") != "ACTIVE":
                continue
            agent_id = str(row.get("agent_id", "")).strip()
            if not agent_id:
                continue
            claimed = self._claim_and_execute(agent_id)
            claims += int(claimed)
        with self._stats_lock:
            self._stats["ticks"] += 1
            self._stats["last_tick_at"] = time.time()
        return claims

    def run_forever(self) -> None:
        while not self._stop.is_set():
            try:
                self.run_once()
                with self._stats_lock:
                    self._stats["last_error"] = None
            except Exception as exc:
                with self._stats_lock:
                    self._stats["last_error"] = str(exc)
                print(
                    json.dumps(
                        {"event": "worker_tick_failed", "error": str(exc)},
                        separators=(",", ":"),
                    ),
                    flush=True,
                )
            self._stop.wait(self.poll_seconds)

    def _claim_and_execute(self, agent_id: str) -> bool:
        data = self.gateway.call(
            "worker_claim",
            {
                "agent_id": agent_id,
                "worker_instance_id": self.worker_instance_id,
                "goal_types": self.supported_goal_types,
                "lease_seconds": self.lease_seconds,
            },
        )
        claim = data.get("claim")
        if not isinstance(claim, Mapping) or claim.get("goal") is None:
            return False
        goal = claim["goal"]
        if not isinstance(goal, Mapping):
            raise RuntimeError("worker claim returned malformed goal")
        goal_type = str(goal.get("goal_type", ""))
        executor = self.executors.get(goal_type)
        if executor is None:
            raise RuntimeError("gateway returned a goal type without a registered executor")

        run_id = str(claim["run_id"])
        generation = int(claim["lease_generation"])
        goal_id = str(goal["id"])
        with self._stats_lock:
            self._stats["claims"] += 1

        heartbeat_stop = threading.Event()
        heartbeat = threading.Thread(
            target=self._heartbeat_loop,
            args=(heartbeat_stop, agent_id, goal_id, run_id, generation),
            daemon=True,
        )
        heartbeat.start()
        try:
            result = executor(goal)
            if not isinstance(result, WorkerResult):
                raise TypeError("worker executor must return WorkerResult")
            self.gateway.call(
                "worker_submit",
                {
                    "agent_id": agent_id,
                    "worker_instance_id": self.worker_instance_id,
                    "goal_id": goal_id,
                    "run_id": run_id,
                    "lease_generation": generation,
                    "output_hash": result.output_hash(),
                    "evidence_refs": result.evidence_refs,
                    "summary": result.summary,
                },
            )
            with self._stats_lock:
                self._stats["submitted"] += 1
            print(
                json.dumps(
                    {
                        "event": "worker_submitted",
                        "agent_id": agent_id,
                        "goal_id": goal_id,
                        "run_id": run_id,
                        "lease_generation": generation,
                        "output_hash": result.output_hash(),
                    },
                    separators=(",", ":"),
                ),
                flush=True,
            )
        except Exception as exc:
            try:
                self.gateway.call(
                    "worker_fail",
                    {
                        "agent_id": agent_id,
                        "worker_instance_id": self.worker_instance_id,
                        "goal_id": goal_id,
                        "run_id": run_id,
                        "lease_generation": generation,
                        "error": str(exc)[:1000],
                        "requeue": False,
                    },
                )
            finally:
                with self._stats_lock:
                    self._stats["failed"] += 1
            print(
                json.dumps(
                    {
                        "event": "worker_goal_failed",
                        "agent_id": agent_id,
                        "goal_id": goal_id,
                        "run_id": run_id,
                        "error": str(exc),
                    },
                    separators=(",", ":"),
                ),
                flush=True,
            )
        finally:
            heartbeat_stop.set()
            heartbeat.join(timeout=max(1.0, self.heartbeat_seconds))
        return True

    def _heartbeat_loop(
        self,
        stop: threading.Event,
        agent_id: str,
        goal_id: str,
        run_id: str,
        generation: int,
    ) -> None:
        while not stop.wait(self.heartbeat_seconds):
            self.gateway.call(
                "worker_heartbeat",
                {
                    "agent_id": agent_id,
                    "worker_instance_id": self.worker_instance_id,
                    "goal_id": goal_id,
                    "run_id": run_id,
                    "lease_generation": generation,
                    "extend_seconds": self.lease_seconds,
                },
            )


def system_health_executor(gateway: WorkerGateway) -> Executor:
    def execute(goal: Mapping[str, Any]) -> WorkerResult:
        health = gateway.call("health")
        planning = gateway.call("planning_inputs")
        agents = planning.get("agents", [])
        gaps = planning.get("data_gaps", [])
        goals = planning.get("open_goals", [])
        fingerprint = str(health.get("schema_fingerprint", ""))
        if len(fingerprint) != 64:
            raise RuntimeError("health check returned invalid schema fingerprint")
        return WorkerResult(
            summary="Production runtime health and planning surfaces were read successfully.",
            evidence_refs=[
                {"kind": "schema_fingerprint", "sha256": fingerprint},
                {"kind": "active_agent_count", "value": len(agents) if isinstance(agents, list) else None},
                {"kind": "open_data_gap_count", "value": len(gaps) if isinstance(gaps, list) else None},
                {"kind": "open_goal_count", "value": len(goals) if isinstance(goals, list) else None},
                {"kind": "goal_id", "value": str(goal.get("id", ""))},
            ],
        )
    return execute


def default_worker_instance_id() -> str:
    railway_service = os.environ.get("RAILWAY_SERVICE_ID", "").strip()
    railway_environment = os.environ.get("RAILWAY_ENVIRONMENT_ID", "").strip()
    suffix = f"{railway_service}:{railway_environment}" if railway_service else f"pid:{os.getpid()}"
    return "aibos-runtime:" + suffix
