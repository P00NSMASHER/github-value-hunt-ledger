from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence


def _finite_number(value: Any) -> bool:
    return type(value) in {int, float} and math.isfinite(float(value))


def _nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _require_unique_ids(
    rows: Sequence[Mapping[str, Any]],
    field: str,
    label: str,
) -> None:
    seen: set[str] = set()
    for index, row in enumerate(rows, 1):
        value = row.get(field)
        if not isinstance(value, str) or not value:
            continue
        if value in seen:
            raise ValueError(
                f"duplicate {label} {field}={value} at input row {index}"
            )
        seen.add(value)


class ExperienceKind(str, Enum):
    STRATEGY = "STRATEGY"
    QUERY_FAMILY = "QUERY_FAMILY"
    SEARCH_MOVE = "SEARCH_MOVE"
    CONTEXTUAL_STRATEGY = "CONTEXTUAL_STRATEGY"
    CONTEXTUAL_QUERY_FAMILY = "CONTEXTUAL_QUERY_FAMILY"
    CONTEXTUAL_SEARCH_MOVE = "CONTEXTUAL_SEARCH_MOVE"
    SALVAGED_TRAJECTORY = "SALVAGED_TRAJECTORY"
    LOCAL_SKILL = "LOCAL_SKILL"


def contextual_memory_key(
    base_key: str,
    search_objective_id: str | None,
) -> str | None:
    if (
        not isinstance(base_key, str)
        or not base_key
        or not isinstance(search_objective_id, str)
        or not search_objective_id.startswith("OBJ:")
    ):
        return None
    return f"CTX:{search_objective_id}::{base_key}"


class FailureDecision(str, Enum):
    BLOCKED = "BLOCKED"
    QUEUED = "QUEUED"


class RepairDecision(str, Enum):
    REJECTED = "REJECTED"
    READY_FOR_SKILL_EVAL = "READY_FOR_SKILL_EVAL"


class SkillMutationDecision(str, Enum):
    REJECTED = "REJECTED"
    STAGED_MUTATION = "STAGED_MUTATION"


class TransferDecision(str, Enum):
    REJECT = "REJECT"
    ADAPT_LOCAL = "ADAPT_LOCAL"
    ABSORB_LOCAL = "ABSORB_LOCAL"


class HarnessMutationDecision(str, Enum):
    REJECT = "REJECT"
    CANARY_ONLY = "CANARY_ONLY"


@dataclass(frozen=True)
class ValueConfig:
    alpha: float = 0.15
    gamma: float = 0.0
    epsilon: float = 0.10
    similarity_weight: float = 0.45
    value_weight: float = 0.55
    q_floor: float = -1.0
    q_ceiling: float = 1.0

    def validate(self) -> None:
        for name in ("alpha", "epsilon", "similarity_weight", "value_weight"):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.gamma < 0.0 or self.gamma > 1.0:
            raise ValueError("gamma must be in [0, 1]")
        if self.q_floor >= self.q_ceiling:
            raise ValueError("q_floor must be less than q_ceiling")
        if self.similarity_weight + self.value_weight <= 0:
            raise ValueError("at least one ranking weight must be positive")


@dataclass
class MemoryRecord:
    key: str
    kind: ExperienceKind
    q_value: float = 0.0
    visits: int = 0
    reward_ma: float = 0.0
    last_reward: float | None = None
    last_run_id: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        body = asdict(self)
        body["kind"] = self.kind.value
        return body


@dataclass(frozen=True)
class MemoryCandidate:
    key: str
    similarity: float
    payload: Mapping[str, Any] = field(default_factory=dict)


class ValueMemory:
    """Dependency-free Q-value layer for hunter experience.

    Semantic retrieval stays in the existing retrieval/search layer. This class
    only re-ranks relevant memories using observed downstream utility.
    """

    def __init__(self, config: ValueConfig | None = None):
        self.config = config or ValueConfig()
        self.config.validate()
        self._records: dict[str, MemoryRecord] = {}

    def get(self, key: str) -> MemoryRecord | None:
        return self._records.get(key)

    def records(self) -> list[MemoryRecord]:
        return sorted(self._records.values(), key=lambda r: (r.kind.value, r.key))

    def observe(self, key: str, kind: ExperienceKind) -> MemoryRecord:
        if not key:
            raise ValueError("memory key is required")
        existing = self._records.get(key)
        if existing is None:
            existing = MemoryRecord(key=key, kind=kind)
            self._records[key] = existing
        elif existing.kind is not kind:
            raise ValueError(f"memory kind mismatch for {key}")
        return existing

    def update(
        self,
        key: str,
        kind: ExperienceKind,
        reward: float,
        *,
        next_max_q: float = 0.0,
        run_id: str | None = None,
        updated_at: str | None = None,
    ) -> MemoryRecord:
        if not _finite_number(reward):
            raise ValueError("reward must be a finite non-boolean number")
        rec = self.observe(key, kind)
        target = float(reward) + self.config.gamma * float(next_max_q)
        new_q = (1.0 - self.config.alpha) * rec.q_value + self.config.alpha * target
        rec.q_value = max(self.config.q_floor, min(self.config.q_ceiling, new_q))
        rec.visits += 1
        rec.reward_ma = (
            float(reward)
            if rec.visits == 1
            else (1.0 - self.config.alpha) * rec.reward_ma + self.config.alpha * float(reward)
        )
        rec.last_reward = float(reward)
        rec.last_run_id = run_id
        rec.updated_at = updated_at or datetime.now(timezone.utc).isoformat()
        return rec

    def rank(
        self,
        candidates: Sequence[MemoryCandidate],
        *,
        top_k: int = 5,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        if not candidates:
            return []
        rng = random.Random(seed)
        rows: list[dict[str, Any]] = []
        q_span = self.config.q_ceiling - self.config.q_floor
        for candidate in candidates:
            similarity = max(0.0, min(1.0, float(candidate.similarity)))
            rec = self._records.get(candidate.key)
            q_value = rec.q_value if rec else 0.0
            q_norm = (q_value - self.config.q_floor) / q_span
            score = (
                self.config.similarity_weight * similarity
                + self.config.value_weight * q_norm
            )
            rows.append(
                {
                    "key": candidate.key,
                    "similarity": similarity,
                    "q_value": q_value,
                    "score": score,
                    "visits": rec.visits if rec else 0,
                    "payload": dict(candidate.payload),
                }
            )
        rows.sort(key=lambda row: (row["score"], row["similarity"], row["key"]), reverse=True)
        if rng.random() < self.config.epsilon and len(rows) > top_k:
            pool = rows[: max(top_k * 3, top_k + 1)]
            chosen = rng.sample(pool, top_k)
            chosen.sort(key=lambda row: (row["score"], row["similarity"], row["key"]), reverse=True)
            return chosen
        return rows[:top_k]

    def to_state(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "config": asdict(self.config),
            "records": [record.to_dict() for record in self.records()],
        }


@dataclass(frozen=True)
class RewardObservation:
    reward: float
    components: Mapping[str, float]
    reasons: tuple[str, ...]


_SUCCESS_RESULTS = {"SUCCESS", "SUCCEEDED", "PASS", "PASSED", "VALIDATED", "COMPLETE", "COMPLETED"}
_PARTIAL_RESULTS = {"PARTIAL", "MIXED"}
_FAILURE_RESULTS = {"FAIL", "FAILED", "REJECTED", "INVALIDATED", "NO_FIND", "BLOCKED"}


def _safe_ratio(num: Any, den: Any) -> float | None:
    if not _finite_number(num) or not _finite_number(den):
        return None
    if den <= 0:
        return None
    return max(0.0, min(1.0, float(num) / float(den)))


def _outcome_component(outcome: Mapping[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    result = str(outcome.get("result") or "").upper()
    if result in _SUCCESS_RESULTS:
        score += 0.35
        reasons.append("validated_outcome")
    elif result in _PARTIAL_RESULTS:
        score += 0.12
        reasons.append("partial_outcome")
    elif result in _FAILURE_RESULTS:
        score -= 0.35
        reasons.append("failed_outcome")

    revenue = outcome.get("revenue_usd")
    customer_value = outcome.get("customer_value_usd")
    if _finite_number(revenue) and revenue > 0:
        score += 0.35
        reasons.append("realized_revenue")
    if _finite_number(customer_value) and customer_value > 0:
        score += 0.20
        reasons.append("realized_customer_value")

    saved_low = outcome.get("engineering_days_saved_low")
    saved_high = outcome.get("engineering_days_saved_high")
    if (
        _finite_number(saved_low)
        and _finite_number(saved_high)
        and saved_high >= saved_low > 0
    ):
        score += min(0.20, 0.02 * float(saved_low))
        reasons.append("observed_engineering_compression")

    return score, reasons


def observed_search_reward(
    run: Mapping[str, Any],
    linked_outcomes: Sequence[Mapping[str, Any]] = (),
) -> RewardObservation | None:
    """Compute a conservative reward from measured telemetry only.

    Unknown denominators remain unknown; they are never imputed.
    """
    work_action = run.get("work_action")
    if work_action not in (None, "search"):
        return None
    if run.get("measurement_quality") not in {"prospective", "benchmark"}:
        return None

    deep = run.get("deep_inspected")
    if work_action is None:
        candidate_count = run.get("candidate_count")
        legacy_search_evidence = (
            _nonnegative_int(candidate_count)
            and candidate_count > 0
        ) or (
            _nonnegative_int(deep)
            and deep > 0
        )
        if not legacy_search_evidence:
            return None

    deep = run.get("deep_inspected")
    retained = run.get("retained_count")
    promoted = run.get("master_promoted_count")
    if not all(
        _nonnegative_int(value)
        for value in (deep, retained, promoted)
    ):
        return None

    components: dict[str, float] = {}
    reasons: list[str] = []

    retention = _safe_ratio(retained, deep)
    if retention is not None:
        components["retention"] = 0.35 * retention
        reasons.append("measured_retention")
    elif deep == 0:
        components["retention"] = 0.0

    promotion_rate = min(1.0, promoted / max(1, retained))
    components["promotion"] = 0.20 * promotion_rate
    if promoted:
        reasons.append("master_promotion")

    new_caps = len(run.get("new_capability_ids") or [])
    components["new_capabilities"] = 0.15 * min(1.0, new_caps / max(1, deep))
    if new_caps:
        reasons.append("new_capability")

    checks = run.get("candidate_preflight_checks")
    dup_saved = run.get("duplicate_deep_inspections_avoided")
    duplicate_efficiency = _safe_ratio(dup_saved, checks)
    if duplicate_efficiency is not None:
        components["duplicate_efficiency"] = 0.10 * duplicate_efficiency
        reasons.append("measured_duplicate_avoidance")

    if deep >= 2 and retained == 0:
        components["no_retained_penalty"] = -0.30
        reasons.append("deep_inspection_no_retained_candidate")

    outcome_score = 0.0
    for outcome in linked_outcomes:
        delta, outcome_reasons = _outcome_component(outcome)
        outcome_score += delta
        reasons.extend(outcome_reasons)
    if linked_outcomes:
        components["downstream_outcomes"] = max(-0.60, min(0.80, outcome_score))

    reward = max(-1.0, min(1.0, sum(components.values())))
    return RewardObservation(
        reward=reward,
        components=components,
        reasons=tuple(sorted(set(reasons))),
    )


def build_outcome_index(
    outcomes: Iterable[Mapping[str, Any]],
) -> dict[str, list[Mapping[str, Any]]]:
    index: dict[str, list[Mapping[str, Any]]] = {}
    for outcome in outcomes:
        for run_id in outcome.get("origin_search_ids") or []:
            if isinstance(run_id, str) and run_id:
                index.setdefault(run_id, []).append(outcome)
    return index


def learn_value_memory(
    search_runs: Iterable[Mapping[str, Any]],
    outcomes: Iterable[Mapping[str, Any]] = (),
    *,
    config: ValueConfig | None = None,
) -> tuple[ValueMemory, list[dict[str, Any]]]:
    memory = ValueMemory(config)
    run_rows = list(search_runs)
    outcome_rows = list(outcomes)
    _require_unique_ids(run_rows, "search_run_id", "search run")
    _require_unique_ids(outcome_rows, "outcome_id", "outcome")
    outcome_index = build_outcome_index(outcome_rows)
    observations: list[dict[str, Any]] = []

    def sort_key(run: Mapping[str, Any]) -> tuple[str, str]:
        return (
            str(run.get("timestamp") or run.get("date") or ""),
            str(run.get("search_run_id") or ""),
        )

    for run in sorted(run_rows, key=sort_key):
        run_id = str(run.get("search_run_id") or "")
        observation = observed_search_reward(run, outcome_index.get(run_id, []))
        if observation is None:
            continue

        updated: list[str] = []
        strategy_id = run.get("strategy_id")
        if isinstance(strategy_id, str) and strategy_id.startswith("STRAT:"):
            memory.update(
                strategy_id,
                ExperienceKind.STRATEGY,
                observation.reward,
                run_id=run_id or None,
                updated_at=str(run.get("timestamp") or run.get("date") or "") or None,
            )
            updated.append(strategy_id)

        query_family_id = run.get("query_family_id")
        if isinstance(query_family_id, str) and query_family_id.startswith("QF:"):
            memory.update(
                query_family_id,
                ExperienceKind.QUERY_FAMILY,
                observation.reward,
                run_id=run_id or None,
                updated_at=str(run.get("timestamp") or run.get("date") or "") or None,
            )
            updated.append(query_family_id)

        for move in run.get("search_moves") or []:
            if not isinstance(move, Mapping):
                continue
            move_id = move.get("move_id")
            if isinstance(move_id, str) and move_id:
                move_reward = observation.reward
                retained_count = move.get("retained_count")
                deep_count = move.get("deep_inspected")
                if (
                    _nonnegative_int(deep_count)
                    and _nonnegative_int(retained_count)
                    and deep_count > 0
                ):
                    move_reward = max(
                        -1.0,
                        min(
                            1.0,
                            0.7 * observation.reward
                            + 0.3 * (retained_count / deep_count),
                        ),
                    )
                key = f"MOVE:{move_id}"
                memory.update(
                    key,
                    ExperienceKind.SEARCH_MOVE,
                    move_reward,
                    run_id=run_id or None,
                    updated_at=str(run.get("timestamp") or run.get("date") or "") or None,
                )
                updated.append(key)

        observations.append(
            {
                "search_run_id": run_id,
                "reward": observation.reward,
                "components": dict(observation.components),
                "reasons": list(observation.reasons),
                "updated_memory_keys": updated,
            }
        )
    return memory, observations


_MOVE_RESULT_SIGNAL = {
    "qualifying_hit": 1.0,
    "useful_hit": 0.55,
    "weak_hit": 0.10,
    "no_hit": -0.55,
    "retrieval_limited": -0.20,
    "blocked": -0.40,
    "unknown": 0.0,
}


def search_move_training_reward(
    move: Mapping[str, Any],
    run_reward: float,
) -> float:
    """Attribute reward to one retrieval move instead of the whole hunt."""
    result_signal = _MOVE_RESULT_SIGNAL.get(
        str(move.get("result") or "unknown"),
        0.0,
    )
    productivity = 0.0
    deep = move.get("deep_inspected")
    retained = move.get("retained_count")
    if (
        isinstance(deep, int)
        and isinstance(retained, int)
        and deep > 0
        and retained >= 0
    ):
        retention = max(
            0.0,
            min(1.0, retained / deep),
        )
        productivity = max(
            -0.5,
            min(1.0, 2.0 * retention - 0.5),
        )
    value = (
        0.65 * result_signal
        + 0.25 * productivity
        + 0.10 * float(run_reward)
    )
    return max(-1.0, min(1.0, value))


def learn_training_episode_memory(
    episodes: Iterable[Mapping[str, Any]],
    *,
    config: ValueConfig | None = None,
) -> tuple[ValueMemory, list[dict[str, Any]]]:
    """Learn value priors from the train partition only.

    Confirm and evaluation-only episodes are deliberately ignored here. They
    exist to judge candidate policy/skill changes, not to train the live prior.
    """
    memory = ValueMemory(config)
    episode_rows = list(episodes)
    _require_unique_ids(episode_rows, "run_id", "training episode")
    observations: list[dict[str, Any]] = []

    def sort_key(episode: Mapping[str, Any]) -> tuple[str, str]:
        provenance = episode.get("provenance") or {}
        return (
            str(provenance.get("timestamp") or ""),
            str(episode.get("run_id") or ""),
        )

    for episode in sorted(episode_rows, key=sort_key):
        if episode.get("split") != "train":
            continue
        reward_body = episode.get("reward") or {}
        reward = reward_body.get("training_reward")
        if not _finite_number(reward):
            continue

        run_id = str(episode.get("run_id") or "")
        state = episode.get("state") or {}
        action = episode.get("action") or {}
        provenance = episode.get("provenance") or {}
        objective_id = state.get("search_objective_id")
        updated_at = str(provenance.get("timestamp") or "") or None
        updated: list[str] = []

        strategy_id = action.get("strategy_id")
        if isinstance(strategy_id, str) and strategy_id.startswith("STRAT:"):
            memory.update(
                strategy_id,
                ExperienceKind.STRATEGY,
                float(reward),
                run_id=run_id or None,
                updated_at=updated_at,
            )
            updated.append(strategy_id)
            contextual_strategy = contextual_memory_key(
                strategy_id,
                objective_id,
            )
            if contextual_strategy:
                memory.update(
                    contextual_strategy,
                    ExperienceKind.CONTEXTUAL_STRATEGY,
                    float(reward),
                    run_id=run_id or None,
                    updated_at=updated_at,
                )
                updated.append(contextual_strategy)

        query_family_id = action.get("query_family_id")
        if (
            isinstance(query_family_id, str)
            and query_family_id.startswith("QF:")
        ):
            memory.update(
                query_family_id,
                ExperienceKind.QUERY_FAMILY,
                float(reward),
                run_id=run_id or None,
                updated_at=updated_at,
            )
            updated.append(query_family_id)
            contextual_query_family = contextual_memory_key(
                query_family_id,
                objective_id,
            )
            if contextual_query_family:
                memory.update(
                    contextual_query_family,
                    ExperienceKind.CONTEXTUAL_QUERY_FAMILY,
                    float(reward),
                    run_id=run_id or None,
                    updated_at=updated_at,
                )
                updated.append(contextual_query_family)

        structured_moves = [
            move
            for move in action.get("search_moves") or []
            if isinstance(move, Mapping)
        ]
        if structured_moves:
            move_reward_lists: dict[str, list[float]] = {}
            for move in structured_moves:
                key = str(
                    move.get("key")
                    or (
                        f"MOVE:{move.get('move_type')}"
                        if move.get("move_type")
                        else ""
                    )
                )
                if not key:
                    continue
                move_reward_lists.setdefault(key, []).append(
                    search_move_training_reward(
                        move,
                        float(reward),
                    )
                )
            move_rows = [
                (
                    key,
                    sum(values) / len(values),
                )
                for key, values in move_reward_lists.items()
            ]
        else:
            # Backward compatibility for already-generated episode artifacts.
            move_rows = [
                (
                    key,
                    float(reward),
                )
                for key in dict.fromkeys(
                    (
                        move_id
                        if move_id.startswith("MOVE:")
                        else f"MOVE:{move_id}"
                    )
                    for move_id in action.get("search_move_ids") or []
                    if isinstance(move_id, str) and move_id
                )
            ]

        for key, move_reward in move_rows:
            if not key:
                continue
            memory.update(
                key,
                ExperienceKind.SEARCH_MOVE,
                move_reward,
                run_id=run_id or None,
                updated_at=updated_at,
            )
            updated.append(key)
            contextual_move = contextual_memory_key(
                key,
                objective_id,
            )
            if contextual_move:
                memory.update(
                    contextual_move,
                    ExperienceKind.CONTEXTUAL_SEARCH_MOVE,
                    move_reward,
                    run_id=run_id or None,
                    updated_at=updated_at,
                )
                updated.append(contextual_move)

        observations.append(
            {
                "search_run_id": run_id,
                "split": "train",
                "reward": float(reward),
                "reward_stage": reward_body.get("reward_stage"),
                "downstream_outcome_ids": list(
                    (reward_body.get("downstream") or {}).get(
                        "outcome_ids",
                        [],
                    )
                ),
                "updated_memory_keys": updated,
            }
        )

    return memory, observations


@dataclass(frozen=True)
class FailureEvent:
    failure_id: str
    run_id: str
    hunter_id: str
    target_type: str
    target_id: str
    failure_class: str
    observation: str
    reproduction_steps: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    proposed_regression_test: str | None = None
    sensitive_material_involved: bool = False
    benchmark_contaminated: bool = False

    @property
    def signature(self) -> str:
        payload = {
            "target_type": self.target_type.strip().lower(),
            "target_id": self.target_id.strip().lower(),
            "failure_class": self.failure_class.strip().lower(),
            "observation": " ".join(self.observation.split()).lower(),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


_ALLOWED_FAILURE_TARGET_TYPES = {
    "search_skill",
    "query_family",
    "search_move",
    "tool",
    "prompt",
    "workflow",
    "routing",
    "memory",
    "harness",
}
_ALLOWED_FAILURE_CLASSES = {
    "false_positive",
    "false_negative",
    "duplicate_work",
    "retrieval_failure",
    "evidence_failure",
    "tool_failure",
    "prompt_failure",
    "workflow_failure",
    "regression",
    "overfit",
    "transfer_failure",
    "other",
}


@dataclass(frozen=True)
class FailureAssessment:
    decision: FailureDecision
    reasons: tuple[str, ...]
    signature: str


def assess_failure_for_repair(event: FailureEvent) -> FailureAssessment:
    reasons: list[str] = []
    if not event.failure_id:
        reasons.append("failure_id_required")
    if not event.run_id:
        reasons.append("origin_run_required")
    if not event.hunter_id:
        reasons.append("hunter_id_required")
    if event.target_type not in _ALLOWED_FAILURE_TARGET_TYPES:
        reasons.append("invalid_target_type")
    if not event.target_id:
        reasons.append("target_id_required")
    if event.failure_class not in _ALLOWED_FAILURE_CLASSES:
        reasons.append("invalid_failure_class")
    if not event.observation.strip():
        reasons.append("observation_required")
    if not event.reproduction_steps:
        reasons.append("reproduction_required")
    if not event.evidence_refs:
        reasons.append("evidence_required")
    if not event.proposed_regression_test:
        reasons.append("regression_test_required")
    if event.sensitive_material_involved:
        reasons.append("sensitive_material_blocked")
    if event.benchmark_contaminated:
        reasons.append("benchmark_contamination_blocked")
    return FailureAssessment(
        decision=FailureDecision.BLOCKED if reasons else FailureDecision.QUEUED,
        reasons=tuple(reasons),
        signature=event.signature,
    )


@dataclass(frozen=True)
class RepairCandidate:
    failure_id: str
    skill_id: str
    candidate_version: str
    regression_tests_total: int
    regression_tests_passed: int
    diff_hash: str
    decision_history_ref: str
    unrelated_files_changed: bool = False
    source_failure_blocked: bool = False


@dataclass(frozen=True)
class RepairAssessment:
    decision: RepairDecision
    reasons: tuple[str, ...]


def assess_repair_candidate(candidate: RepairCandidate) -> RepairAssessment:
    reasons: list[str] = []
    if candidate.source_failure_blocked:
        reasons.append("source_failure_not_eligible")
    if candidate.regression_tests_total < 1:
        reasons.append("at_least_one_regression_test_required")
    if candidate.regression_tests_passed != candidate.regression_tests_total:
        reasons.append("regression_test_failure")
    if not candidate.diff_hash:
        reasons.append("diff_hash_required")
    if not candidate.decision_history_ref:
        reasons.append("decision_history_required")
    if candidate.unrelated_files_changed:
        reasons.append("unrelated_change_detected")
    return RepairAssessment(
        decision=RepairDecision.REJECTED if reasons else RepairDecision.READY_FOR_SKILL_EVAL,
        reasons=tuple(reasons),
    )


@dataclass(frozen=True)
class TrajectoryOutcome:
    run_id: str
    original_goal_success: bool
    verified_alternate_outcome: str | None = None
    alternate_evidence_refs: tuple[str, ...] = ()
    observed_reward: float | None = None
    safety_blocked: bool = False
    rights_blocked: bool = False
    benchmark_contaminated: bool = False


@dataclass(frozen=True)
class SalvageResult:
    eligible: bool
    memory_scope: str
    reward: float | None
    reasons: tuple[str, ...]


def salvage_trajectory(
    outcome: TrajectoryOutcome,
    *,
    reward_cap: float = 0.40,
) -> SalvageResult:
    reasons: list[str] = []
    if outcome.original_goal_success:
        reasons.append("not_a_failed_trajectory")
    if not outcome.verified_alternate_outcome:
        reasons.append("verified_alternate_outcome_required")
    if not outcome.alternate_evidence_refs:
        reasons.append("alternate_evidence_required")
    if outcome.safety_blocked:
        reasons.append("safety_blocked")
    if outcome.rights_blocked:
        reasons.append("rights_blocked")
    if outcome.benchmark_contaminated:
        reasons.append("benchmark_contaminated")
    if reasons:
        return SalvageResult(False, "NONE", None, tuple(reasons))

    reward = (
        0.20
        if outcome.observed_reward is None
        else max(-reward_cap, min(reward_cap, outcome.observed_reward))
    )
    return SalvageResult(
        True,
        "LOCAL_ONLY_UNTIL_INDEPENDENTLY_VALIDATED",
        reward,
        ("relabelled_from_verified_actual_outcome",),
    )


@dataclass(frozen=True)
class SkillVariantEvidence:
    skill_id: str
    baseline_version: str
    candidate_version: str
    mutate_dev_examples: int
    promotion_test_examples: int
    baseline_dev_score: float
    candidate_dev_score: float
    champion_test_score: float
    candidate_test_score: float
    hard_regressions: int = 0
    split_fingerprints_disjoint: bool = True
    provenance_complete: bool = True
    source_failure_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkillMutationAssessment:
    decision: SkillMutationDecision
    reasons: tuple[str, ...]
    score_delta: float


def assess_skill_variant(
    evidence: SkillVariantEvidence,
    *,
    min_dev_examples: int = 4,
    min_promotion_examples: int = 5,
    min_score_delta: float = 0.02,
) -> SkillMutationAssessment:
    reasons: list[str] = []
    if evidence.mutate_dev_examples < min_dev_examples:
        reasons.append("insufficient_mutate_dev_examples")
    if evidence.promotion_test_examples < min_promotion_examples:
        reasons.append("insufficient_promotion_test_examples")
    if not evidence.split_fingerprints_disjoint:
        reasons.append("dev_test_split_leakage")
    if not evidence.provenance_complete:
        reasons.append("provenance_incomplete")
    if evidence.hard_regressions > 0:
        reasons.append("hard_regression")
    if evidence.candidate_dev_score <= evidence.baseline_dev_score:
        reasons.append("no_dev_improvement")
    delta = evidence.candidate_test_score - evidence.champion_test_score
    if delta < min_score_delta:
        reasons.append("promotion_delta_below_gate")
    return SkillMutationAssessment(
        SkillMutationDecision.REJECTED
        if reasons
        else SkillMutationDecision.STAGED_MUTATION,
        tuple(reasons),
        delta,
    )


@dataclass(frozen=True)
class PeerSkillEvidence:
    skill_id: str
    source_hunter: str
    target_hunter: str
    source_state: str
    source_distinct_successes: int
    source_regressions: int
    compatibility_score: float
    target_failure_overlap: float
    same_runtime: bool
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class PeerTransferAssessment:
    decision: TransferDecision
    reasons: tuple[str, ...]


def assess_peer_skill_transfer(
    evidence: PeerSkillEvidence,
) -> PeerTransferAssessment:
    reasons: list[str] = []
    if evidence.source_state not in {"STAGED", "VERIFIED", "CANARY", "GLOBAL"}:
        reasons.append("source_skill_not_stage_eligible")
    if evidence.source_distinct_successes < 2:
        reasons.append("source_skill_needs_two_successes")
    if evidence.source_regressions > 0:
        reasons.append("source_skill_has_regressions")
    if not evidence.evidence_refs:
        reasons.append("transfer_evidence_required")
    if evidence.compatibility_score < 0.40:
        reasons.append("compatibility_too_low")
    if evidence.target_failure_overlap < 0.20:
        reasons.append("weak_target_need")
    if reasons:
        return PeerTransferAssessment(TransferDecision.REJECT, tuple(reasons))

    if (
        evidence.same_runtime
        and evidence.compatibility_score >= 0.80
        and evidence.source_state in {"VERIFIED", "CANARY", "GLOBAL"}
    ):
        return PeerTransferAssessment(
            TransferDecision.ABSORB_LOCAL,
            ("local_absorption_only_global_gate_unchanged",),
        )
    return PeerTransferAssessment(
        TransferDecision.ADAPT_LOCAL,
        ("personalized_adaptation_required",),
    )


@dataclass(frozen=True)
class FleetAgentCandidate:
    agent_id: str
    performance: float
    success_vector: tuple[float, ...]


@dataclass(frozen=True)
class FleetParentScore:
    agent_id: str
    performance: float
    novelty: float
    combined_score: float


def _cosine_distance(
    a: Sequence[float],
    b: Sequence[float],
    epsilon: float = 1e-8,
) -> float:
    if len(a) != len(b):
        raise ValueError("success vectors must have equal length")
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    norm_a = math.sqrt(sum(float(x) * float(x) for x in a))
    norm_b = math.sqrt(sum(float(y) * float(y) for y in b))
    similarity = dot / (norm_a * norm_b + epsilon)
    similarity = max(-1.0, min(1.0, similarity))
    return 1.0 - similarity


def score_fleet_parents(
    candidates: Sequence[FleetAgentCandidate],
    *,
    nearest_neighbors: int = 4,
) -> list[FleetParentScore]:
    if not candidates:
        return []
    if nearest_neighbors < 1:
        raise ValueError("nearest_neighbors must be positive")
    dimensions = {len(candidate.success_vector) for candidate in candidates}
    if len(dimensions) != 1:
        raise ValueError("all success vectors must have equal length")
    if len(candidates) == 1:
        candidate = candidates[0]
        return [
            FleetParentScore(
                candidate.agent_id,
                candidate.performance,
                1.0,
                max(0.0, candidate.performance),
            )
        ]

    result: list[FleetParentScore] = []
    neighbor_count = min(nearest_neighbors, len(candidates) - 1)
    for index, candidate in enumerate(candidates):
        distances = sorted(
            _cosine_distance(candidate.success_vector, other.success_vector)
            for other_index, other in enumerate(candidates)
            if index != other_index
        )
        novelty = sum(distances[:neighbor_count]) / neighbor_count
        combined = max(0.0, float(candidate.performance)) * math.sqrt(
            max(0.0, novelty)
        )
        result.append(
            FleetParentScore(
                candidate.agent_id,
                candidate.performance,
                novelty,
                combined,
            )
        )
    return sorted(
        result,
        key=lambda row: (row.combined_score, row.performance, row.agent_id),
        reverse=True,
    )


def select_fleet_parents(
    candidates: Sequence[FleetAgentCandidate],
    top_k: int,
    *,
    nearest_neighbors: int = 4,
) -> list[FleetParentScore]:
    if top_k < 1:
        raise ValueError("top_k must be positive")
    return score_fleet_parents(
        candidates,
        nearest_neighbors=nearest_neighbors,
    )[:top_k]


@dataclass(frozen=True)
class HarnessMutationEvidence:
    mutation_id: str
    touched_paths: tuple[str, ...]
    allowed_paths: tuple[str, ...]
    selection_tasks: int
    baseline_score: float
    candidate_score: float
    regressions: int
    diff_hash: str
    evaluator_modified: bool = False
    controller_modified: bool = False
    sealed_final_opened: bool = False
    credentials_touched: bool = False


@dataclass(frozen=True)
class HarnessMutationAssessment:
    decision: HarnessMutationDecision
    reasons: tuple[str, ...]
    score_delta: float


def assess_harness_mutation(
    evidence: HarnessMutationEvidence,
    *,
    min_selection_tasks: int = 5,
    min_score_delta: float = 0.02,
) -> HarnessMutationAssessment:
    reasons: list[str] = []
    allowed = set(evidence.allowed_paths)
    touched = set(evidence.touched_paths)
    if not touched:
        reasons.append("no_mutation")
    if not touched.issubset(allowed):
        reasons.append("mutation_outside_lease")
    if evidence.evaluator_modified:
        reasons.append("evaluator_is_immutable")
    if evidence.controller_modified:
        reasons.append("controller_is_immutable")
    if evidence.sealed_final_opened:
        reasons.append("sealed_final_contaminated")
    if evidence.credentials_touched:
        reasons.append("credentials_outside_candidate_write_set")
    if evidence.selection_tasks < min_selection_tasks:
        reasons.append("insufficient_selection_tasks")
    if evidence.regressions > 0:
        reasons.append("regression_detected")
    if not evidence.diff_hash:
        reasons.append("diff_hash_required")
    delta = evidence.candidate_score - evidence.baseline_score
    if delta < min_score_delta:
        reasons.append("selection_delta_below_gate")
    return HarnessMutationAssessment(
        HarnessMutationDecision.REJECT
        if reasons
        else HarnessMutationDecision.CANARY_ONLY,
        tuple(reasons),
        delta,
    )


@dataclass(frozen=True)
class TrainingTrajectory:
    run_id: str
    reward: float
    verified: bool
    evidence_refs: tuple[str, ...]
    sensitive_material_involved: bool = False
    benchmark_contaminated: bool = False
    payload_ref: str | None = None


@dataclass(frozen=True)
class TrainingExportAssessment:
    eligible: bool
    reasons: tuple[str, ...]


def assess_training_export(
    trajectory: TrainingTrajectory,
) -> TrainingExportAssessment:
    reasons: list[str] = []
    if not trajectory.verified:
        reasons.append("independent_verification_required")
    if not trajectory.evidence_refs:
        reasons.append("evidence_required")
    if not math.isfinite(trajectory.reward):
        reasons.append("finite_reward_required")
    if trajectory.sensitive_material_involved:
        reasons.append("sensitive_material_blocked")
    if trajectory.benchmark_contaminated:
        reasons.append("benchmark_contamination_blocked")
    if not trajectory.payload_ref:
        reasons.append("immutable_payload_ref_required")
    return TrainingExportAssessment(not reasons, tuple(reasons))


def build_training_manifest(
    trajectories: Sequence[TrainingTrajectory],
) -> dict[str, Any]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for trajectory in trajectories:
        assessment = assess_training_export(trajectory)
        row = {
            "run_id": trajectory.run_id,
            "reward": trajectory.reward,
            "payload_ref": trajectory.payload_ref,
            "evidence_refs": list(trajectory.evidence_refs),
        }
        if assessment.eligible:
            accepted.append(row)
        else:
            row["reasons"] = list(assessment.reasons)
            rejected.append(row)

    body = {
        "schema_version": 1,
        "accepted": accepted,
        "rejected": rejected,
    }
    body["manifest_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return body
