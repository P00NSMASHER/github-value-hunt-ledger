from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


_VALID_RESULTS = {"PASSED", "FAILED", "PARTIAL"}
_RETAINED_STATUSES = {
    "strong",
    "strong-component",
    "strong_component",
    "retained",
    "retained-corrected",
    "retained-source-only",
    "retained_evidence",
    "retained-real-transport-validated",
    "repair-verified-negative-oracle",
    "negative-oracle",
    "strong-component-negative-boundary",
    "watch-strong-transfer-donor",
}


@dataclass(frozen=True)
class TrainingEnvironmentConfig:
    confirm_modulus: int = 5
    confirm_bucket: int = 0
    direct_origin_budget: float = 0.60
    support_origin_budget: float = 0.40
    experiment_path_strength: float = 0.55
    repository_path_strength: float = 0.45
    new_capability_path_strength: float = 0.40
    strengthened_capability_path_strength: float = 0.30
    proxy_reward_ceiling: float = 0.60
    immediate_only_reward_ceiling: float = 0.40

    def validate(self) -> None:
        if self.confirm_modulus < 2:
            raise ValueError("confirm_modulus must be >= 2")
        if not 0 <= self.confirm_bucket < self.confirm_modulus:
            raise ValueError("confirm_bucket must be within modulus")
        if not math.isclose(
            self.direct_origin_budget + self.support_origin_budget,
            1.0,
            rel_tol=0,
            abs_tol=1e-9,
        ):
            raise ValueError("direct/support budgets must sum to 1")
        for name in (
            "direct_origin_budget",
            "support_origin_budget",
            "experiment_path_strength",
            "repository_path_strength",
            "new_capability_path_strength",
            "strengthened_capability_path_strength",
            "proxy_reward_ceiling",
            "immediate_only_reward_ceiling",
        ):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")


def _stable_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _clip(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _safe_ratio(num: Any, den: Any) -> float | None:
    if not isinstance(num, (int, float)) or not isinstance(den, (int, float)):
        return None
    if den <= 0:
        return None
    return max(0.0, min(1.0, float(num) / float(den)))


def _run_time(run: Mapping[str, Any]) -> str:
    return str(run.get("timestamp") or run.get("date") or "")


def _date_key(value: str | None) -> str:
    if not value:
        return ""
    raw = str(value)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _not_after(run: Mapping[str, Any], outcome: Mapping[str, Any]) -> bool:
    run_time = _date_key(_run_time(run))
    out_time = _date_key(str(outcome.get("date") or ""))
    if not run_time or not out_time:
        return True
    return run_time[:10] <= out_time[:10]


def partition_for_id(
    run_id: str,
    *,
    config: TrainingEnvironmentConfig | None = None,
) -> str:
    """Assign an identifier to a deterministic train/confirm partition.

    This helper is intentionally independent of run eligibility. It lets a
    non-search execution/verification origin anchor its downstream outcome to
    one partition without ever becoming a search-training episode itself.
    """
    cfg = config or TrainingEnvironmentConfig()
    cfg.validate()
    if not run_id:
        return "excluded"
    digest = hashlib.sha256(run_id.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:8], "big") % cfg.confirm_modulus
    return "confirm" if bucket == cfg.confirm_bucket else "train"


def split_for_run(
    run: Mapping[str, Any],
    *,
    config: TrainingEnvironmentConfig | None = None,
) -> str:
    cfg = config or TrainingEnvironmentConfig()
    cfg.validate()
    quality = run.get("measurement_quality")
    if quality == "benchmark":
        return "evaluation_only"
    if quality != "prospective":
        return "excluded"
    if run.get("work_action") not in (None, "search"):
        return "excluded"
    run_id = str(run.get("search_run_id") or "")
    if not run_id:
        return "excluded"
    return partition_for_id(run_id, config=cfg)


def discovery_signal(run: Mapping[str, Any]) -> float | None:
    if split_for_run(run) == "excluded":
        return None
    deep = run.get("deep_inspected")
    retained = run.get("retained_count")
    promoted = run.get("master_promoted_count")
    if not all(isinstance(v, int) and v >= 0 for v in (deep, retained, promoted)):
        return None

    score = 0.0
    retention = _safe_ratio(retained, deep)
    if retention is not None:
        score += 0.45 * retention
    promotion = min(1.0, promoted / max(1, retained))
    score += 0.20 * promotion

    new_caps = len(run.get("new_capability_ids") or [])
    strengthened = len(run.get("strengthened_capability_ids") or [])
    score += 0.15 * min(
        1.0,
        (new_caps + 0.5 * strengthened) / max(1, deep),
    )

    duplicate_efficiency = _safe_ratio(
        run.get("duplicate_deep_inspections_avoided"),
        run.get("candidate_preflight_checks"),
    )
    if duplicate_efficiency is not None:
        score += 0.10 * duplicate_efficiency

    if deep >= 2 and retained == 0:
        score -= 0.35

    elapsed = run.get("elapsed_minutes")
    if isinstance(elapsed, (int, float)) and elapsed > 0 and retained > 0:
        retained_per_hour = retained * 60.0 / float(elapsed)
        score += 0.10 * min(1.0, retained_per_hour)

    return _clip(score)


def outcome_signal(outcome: Mapping[str, Any]) -> dict[str, Any] | None:
    result = str(outcome.get("result") or "").upper()
    if result not in _VALID_RESULTS:
        return None
    technical = {
        "PASSED": 1.0,
        "PARTIAL": 0.35,
        "FAILED": -1.0,
    }[result]

    revenue = outcome.get("revenue_usd")
    customer_value = outcome.get("customer_value_usd")
    commercial_observed = (
        isinstance(revenue, (int, float)) and revenue > 0
    ) or (
        isinstance(customer_value, (int, float))
        and customer_value > 0
    )
    commercial = 1.0 if commercial_observed else 0.0

    low = outcome.get("engineering_days_saved_low")
    high = outcome.get("engineering_days_saved_high")
    engineering_observed = (
        isinstance(low, (int, float))
        and isinstance(high, (int, float))
        and high >= low > 0
    )
    engineering = (
        min(1.0, float(low) / 10.0)
        if engineering_observed
        else 0.0
    )

    if commercial_observed:
        scalar = _clip(
            0.15 * technical
            + 0.15 * engineering
            + 0.70 * commercial
        )
        stage = "realized_economic"
    elif engineering_observed:
        scalar = _clip(
            0.45 * technical
            + 0.55 * engineering
        )
        stage = "observed_engineering"
    else:
        scalar = _clip(0.40 * technical)
        stage = "technical_proxy"

    return {
        "technical": technical,
        "commercial": commercial,
        "engineering": engineering,
        "commercial_observed": commercial_observed,
        "engineering_observed": engineering_observed,
        "value_stage": stage,
        "scalar": scalar,
    }


def _repo_key(value: str) -> str:
    raw = value.strip().lower()
    if raw.startswith("https://github.com/"):
        raw = raw[len("https://github.com/"):]
    raw = raw.rstrip("/")
    if raw.endswith(".git"):
        raw = raw[:-4]
    if "@" in raw:
        raw = raw.split("@", 1)[0]
    parts = raw.split("/")
    return "/".join(parts[:2]) if len(parts) >= 2 else raw


def _retained_repositories(run: Mapping[str, Any]) -> set[str]:
    out: set[str] = set()
    for disposition in run.get("candidate_dispositions") or []:
        if not isinstance(disposition, Mapping):
            continue
        repository = disposition.get("repository")
        status = str(disposition.get("status") or "").lower()
        if (
            isinstance(repository, str)
            and repository
            and status in _RETAINED_STATUSES
        ):
            out.add(_repo_key(repository))
    return out


def _path_evidence(
    run: Mapping[str, Any],
    outcome: Mapping[str, Any],
    *,
    config: TrainingEnvironmentConfig,
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    rid = str(run.get("search_run_id") or "")
    if rid and rid in set(outcome.get("origin_search_ids") or []):
        evidence.append(
            {
                "kind": "direct_origin",
                "strength": 1.0,
                "via": rid,
            }
        )

    exp_id = outcome.get("experiment_id")
    if (
        isinstance(exp_id, str)
        and exp_id
        and exp_id in set(run.get("experiment_ids") or [])
    ):
        evidence.append(
            {
                "kind": "shared_experiment",
                "strength": config.experiment_path_strength,
                "via": exp_id,
            }
        )

    outcome_caps = set(outcome.get("contributing_capability_ids") or [])
    for cap in sorted(
        outcome_caps.intersection(
            set(run.get("new_capability_ids") or [])
        )
    ):
        evidence.append(
            {
                "kind": "new_capability",
                "strength": config.new_capability_path_strength,
                "via": cap,
            }
        )
    for cap in sorted(
        outcome_caps.intersection(
            set(run.get("strengthened_capability_ids") or [])
        )
    ):
        evidence.append(
            {
                "kind": "strengthened_capability",
                "strength": config.strengthened_capability_path_strength,
                "via": cap,
            }
        )

    outcome_repos = {
        _repo_key(repo)
        for repo in outcome.get("contributing_repositories") or []
        if isinstance(repo, str)
    }
    for repo in sorted(
        outcome_repos.intersection(_retained_repositories(run))
    ):
        evidence.append(
            {
                "kind": "retained_repository",
                "strength": config.repository_path_strength,
                "via": repo,
            }
        )
    return evidence


def _combine_support_strength(
    evidence: Sequence[Mapping[str, Any]],
) -> float:
    support = [
        float(item["strength"])
        for item in evidence
        if item.get("kind") != "direct_origin"
    ]
    if not support:
        return 0.0
    complement = 1.0
    for strength in support:
        complement *= 1.0 - _clip(strength, 0.0, 1.0)
    return 1.0 - complement


def build_outcome_credit(
    search_runs: Sequence[Mapping[str, Any]],
    outcomes: Sequence[Mapping[str, Any]],
    *,
    config: TrainingEnvironmentConfig | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cfg = config or TrainingEnvironmentConfig()
    cfg.validate()
    runs_by_id = {
        str(run.get("search_run_id")): run
        for run in search_runs
        if run.get("search_run_id")
    }
    splits = {
        rid: split_for_run(run, config=cfg)
        for rid, run in runs_by_id.items()
    }
    edges: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for outcome in outcomes:
        signal = outcome_signal(outcome)
        if signal is None:
            continue
        outcome_id = str(outcome.get("outcome_id") or "")
        direct_ids = [
            rid
            for rid in dict.fromkeys(
                outcome.get("origin_search_ids") or []
            )
            if rid in runs_by_id
        ]
        direct_splits = {
            splits[rid]
            for rid in direct_ids
            if splits[rid] != "excluded"
        }
        if len(direct_splits) > 1:
            excluded.append(
                {
                    "outcome_id": outcome_id,
                    "reason": "mixed_direct_origin_splits",
                    "splits": sorted(direct_splits),
                }
            )
            continue

        if direct_splits:
            outcome_split = next(iter(direct_splits))
            credit_anchor_kind = "eligible_direct_origin"
        else:
            if not direct_ids:
                excluded.append(
                    {
                        "outcome_id": outcome_id,
                        "reason": "no_known_direct_origin",
                    }
                )
                continue
            anchor_splits = {
                partition_for_id(rid, config=cfg)
                for rid in direct_ids
            }
            if len(anchor_splits) != 1:
                excluded.append(
                    {
                        "outcome_id": outcome_id,
                        "reason": (
                            "mixed_excluded_direct_origin_partitions"
                        ),
                        "splits": sorted(anchor_splits),
                    }
                )
                continue
            outcome_split = next(iter(anchor_splits))
            credit_anchor_kind = "excluded_direct_origin_hash"

        allowed_splits = {outcome_split}
        candidates: list[dict[str, Any]] = []
        direct_set = {
            rid
            for rid in direct_ids
            if splits[rid] != "excluded"
        }

        for rid, run in runs_by_id.items():
            if splits[rid] not in allowed_splits:
                continue
            if not _not_after(run, outcome):
                continue
            evidence = _path_evidence(
                run,
                outcome,
                config=cfg,
            )
            if not evidence:
                continue
            candidates.append(
                {
                    "run_id": rid,
                    "split": splits[rid],
                    "direct": rid in direct_set,
                    "support_strength": _combine_support_strength(
                        evidence
                    ),
                    "path_evidence": evidence,
                }
            )

        direct = [
            row for row in candidates
            if row["direct"]
        ]
        support = [
            row for row in candidates
            if (
                not row["direct"]
                and row["support_strength"] > 0
            )
        ]
        if not direct and not support:
            excluded.append(
                {
                    "outcome_id": outcome_id,
                    "reason": (
                        "no_support_path_in_anchor_split"
                        if credit_anchor_kind
                        == "excluded_direct_origin_hash"
                        else "no_provenance_path"
                    ),
                    "anchor_split": outcome_split,
                    "origin_run_ids": direct_ids,
                }
            )
            continue

        if direct and support:
            direct_budget = cfg.direct_origin_budget
            support_budget = cfg.support_origin_budget
        elif direct:
            direct_budget = 1.0
            support_budget = 0.0
        else:
            direct_budget = 0.0
            support_budget = 1.0

        direct_share = (
            direct_budget / len(direct)
            if direct
            else 0.0
        )
        support_total = sum(
            row["support_strength"]
            for row in support
        )

        for row in candidates:
            if row["direct"]:
                credit = direct_share
            elif support_total > 0:
                credit = (
                    support_budget
                    * row["support_strength"]
                    / support_total
                )
            else:
                credit = 0.0
            if credit <= 0:
                continue
            edges.append(
                {
                    "outcome_id": outcome_id,
                    "run_id": row["run_id"],
                    "split": row["split"],
                    "credit": credit,
                    "direct_origin": row["direct"],
                    "path_evidence": row["path_evidence"],
                    "credit_anchor": {
                        "kind": credit_anchor_kind,
                        "split": outcome_split,
                        "origin_run_ids": direct_ids,
                    },
                    "outcome_signal": signal,
                    "credited_scalar_reward": (
                        credit * float(signal["scalar"])
                    ),
                }
            )

    edges.sort(
        key=lambda item: (
            item["outcome_id"],
            -item["credit"],
            item["run_id"],
        )
    )
    excluded.sort(
        key=lambda item: (
            item["outcome_id"],
            item["reason"],
        )
    )
    return edges, excluded


def _aggregate_credit_by_run(
    edges: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for edge in edges:
        rid = str(edge["run_id"])
        bucket = out.setdefault(
            rid,
            {
                "downstream_reward": 0.0,
                "technical_credit": 0.0,
                "commercial_credit": 0.0,
                "engineering_credit": 0.0,
                "commercial_observed": False,
                "engineering_observed": False,
                "outcome_ids": [],
                "credit_edges": 0,
            },
        )
        credit = float(edge["credit"])
        signal = edge["outcome_signal"]
        bucket["downstream_reward"] += float(
            edge["credited_scalar_reward"]
        )
        bucket["technical_credit"] += (
            credit * float(signal["technical"])
        )
        bucket["commercial_credit"] += (
            credit * float(signal["commercial"])
        )
        bucket["engineering_credit"] += (
            credit * float(signal["engineering"])
        )
        bucket["commercial_observed"] = bool(
            bucket["commercial_observed"]
            or signal["commercial_observed"]
        )
        bucket["engineering_observed"] = bool(
            bucket["engineering_observed"]
            or signal["engineering_observed"]
        )
        bucket["outcome_ids"].append(
            edge["outcome_id"]
        )
        bucket["credit_edges"] += 1

    for bucket in out.values():
        bucket["outcome_ids"] = sorted(
            set(bucket["outcome_ids"])
        )
        for key in (
            "downstream_reward",
            "technical_credit",
            "commercial_credit",
            "engineering_credit",
        ):
            bucket[key] = _clip(bucket[key])
    return out


def _training_reward(
    discovery: float,
    downstream: Mapping[str, Any] | None,
    cfg: TrainingEnvironmentConfig,
) -> tuple[float, str]:
    if not downstream:
        return (
            _clip(
                discovery,
                -cfg.immediate_only_reward_ceiling,
                cfg.immediate_only_reward_ceiling,
            ),
            "discovery_only",
        )
    if downstream.get("commercial_observed"):
        value = (
            0.25 * discovery
            + 0.15 * float(
                downstream.get("technical_credit")
                or 0.0
            )
            + 0.60 * float(
                downstream.get("commercial_credit")
                or 0.0
            )
        )
        return _clip(value), "commercial_grounded"
    if downstream.get("engineering_observed"):
        value = (
            0.35 * discovery
            + 0.25 * float(
                downstream.get("technical_credit")
                or 0.0
            )
            + 0.40 * float(
                downstream.get("engineering_credit")
                or 0.0
            )
        )
        return (
            _clip(
                value,
                -cfg.proxy_reward_ceiling,
                cfg.proxy_reward_ceiling,
            ),
            "engineering_grounded",
        )

    value = (
        0.65 * discovery
        + 0.35 * float(
            downstream.get("technical_credit")
            or 0.0
        )
    )
    return (
        _clip(
            value,
            -cfg.proxy_reward_ceiling,
            cfg.proxy_reward_ceiling,
        ),
        "technical_proxy",
    )


def build_training_environment(
    search_runs: Sequence[Mapping[str, Any]],
    outcomes: Sequence[Mapping[str, Any]],
    *,
    config: TrainingEnvironmentConfig | None = None,
) -> dict[str, Any]:
    cfg = config or TrainingEnvironmentConfig()
    cfg.validate()
    credit_edges, excluded_outcomes = build_outcome_credit(
        search_runs,
        outcomes,
        config=cfg,
    )
    credit_by_run = _aggregate_credit_by_run(
        credit_edges
    )

    episodes: list[dict[str, Any]] = []
    excluded_runs: list[dict[str, str]] = []
    for run in sorted(
        search_runs,
        key=lambda item: (
            _run_time(item),
            str(item.get("search_run_id") or ""),
        ),
    ):
        rid = str(run.get("search_run_id") or "")
        split = split_for_run(
            run,
            config=cfg,
        )
        discovery = discovery_signal(run)
        if split == "excluded" or discovery is None:
            excluded_runs.append(
                {
                    "run_id": rid,
                    "reason": (
                        "not_eligible_search_training_record"
                    ),
                }
            )
            continue

        downstream = credit_by_run.get(rid)
        reward, reward_stage = _training_reward(
            discovery,
            downstream,
            cfg,
        )
        episode_payload = {
            "schema_version": 1,
            "run_id": rid,
            "split": split,
            "state": {
                "hunter": (
                    run.get("hunter")
                    or run.get("hunter_role")
                    or run.get("execution_worker_id")
                ),
                "lane_ids": list(
                    run.get("lane_ids") or []
                ),
                "search_objective_id": (
                    run.get("search_objective_id")
                ),
                "seed_mode": run.get("seed_mode"),
                "seed_ids": list(
                    run.get("seed_ids") or []
                ),
                "assignment_work_kind": (
                    run.get("assignment_work_kind")
                ),
                "assignment_slot_role": (
                    run.get("assignment_slot_role")
                ),
            },
            "action": {
                "strategy_id": run.get("strategy_id"),
                "query_family_id": (
                    run.get("query_family_id")
                ),
                "query_family": run.get("query_family"),
                "search_surfaces": list(
                    run.get("search_surfaces") or []
                ),
                "search_move_ids": [
                    str(move.get("move_id"))
                    for move in run.get("search_moves") or []
                    if (
                        isinstance(move, Mapping)
                        and move.get("move_id")
                    )
                ],
                "queries": list(
                    run.get("queries") or []
                ),
                "recall_rescue_used": (
                    run.get("recall_rescue_used")
                ),
                "stop_reason_standard": (
                    run.get("stop_reason_standard")
                ),
            },
            "observation": {
                "candidate_count": (
                    run.get("candidate_count")
                ),
                "deep_inspected": (
                    run.get("deep_inspected")
                ),
                "retained_count": (
                    run.get("retained_count")
                ),
                "master_promoted_count": (
                    run.get("master_promoted_count")
                ),
                "new_capability_ids": list(
                    run.get("new_capability_ids") or []
                ),
                "strengthened_capability_ids": list(
                    run.get(
                        "strengthened_capability_ids"
                    )
                    or []
                ),
                "experiment_ids": list(
                    run.get("experiment_ids") or []
                ),
                "elapsed_minutes": (
                    run.get("elapsed_minutes")
                ),
                "tool_calls": run.get("tool_calls"),
            },
            "reward": {
                "training_reward": reward,
                "reward_stage": reward_stage,
                "discovery": discovery,
                "downstream": downstream
                or {
                    "downstream_reward": 0.0,
                    "technical_credit": 0.0,
                    "commercial_credit": 0.0,
                    "engineering_credit": 0.0,
                    "commercial_observed": False,
                    "engineering_observed": False,
                    "outcome_ids": [],
                    "credit_edges": 0,
                },
            },
            "provenance": {
                "durable_evidence_path": (
                    run.get("durable_evidence_path")
                ),
                "measurement_quality": (
                    run.get("measurement_quality")
                ),
                "timestamp": (
                    run.get("timestamp")
                    or run.get("date")
                ),
            },
        }
        episode_payload["episode_sha256"] = (
            _stable_json_sha256(episode_payload)
        )
        episodes.append(episode_payload)

    source_payload = {
        "search_runs": list(search_runs),
        "outcomes": list(outcomes),
    }
    source_times = [
        _run_time(run)
        for run in search_runs
        if _run_time(run)
    ] + [
        str(outcome.get("date"))
        for outcome in outcomes
        if outcome.get("date")
    ]

    split_counts: dict[str, int] = {}
    reward_stage_counts: dict[str, int] = {}
    for episode in episodes:
        split_counts[episode["split"]] = (
            split_counts.get(
                episode["split"],
                0,
            )
            + 1
        )
        stage = episode["reward"]["reward_stage"]
        reward_stage_counts[stage] = (
            reward_stage_counts.get(stage, 0)
            + 1
        )

    credit_totals: dict[str, float] = {}
    for edge in credit_edges:
        credit_totals[edge["outcome_id"]] = (
            credit_totals.get(
                edge["outcome_id"],
                0.0,
            )
            + float(edge["credit"])
        )

    return {
        "schema_version": 1,
        "mode": "offline_replay_training_environment",
        "causal_claim": False,
        "policy_effect": "none",
        "source_through": (
            max(source_times)
            if source_times
            else None
        ),
        "source_snapshot_sha256": (
            _stable_json_sha256(source_payload)
        ),
        "split_policy": {
            "prospective": (
                "sha256(run_id) mod "
                f"{cfg.confirm_modulus}; bucket "
                f"{cfg.confirm_bucket}=confirm; "
                "others=train"
            ),
            "benchmark": "evaluation_only",
            "retrospective_or_non_search": "excluded",
            "outcome_credit": (
                "never crosses train/confirm/evaluation "
                "split; mixed-origin outcomes excluded"
            ),
        },
        "reward_policy": {
            **asdict(cfg),
            "principle": (
                "technical-only evidence is capped below "
                "commercially grounded evidence"
            ),
        },
        "summary": {
            "episodes": len(episodes),
            "excluded_runs": len(excluded_runs),
            "credit_edges": len(credit_edges),
            "excluded_outcomes": len(
                excluded_outcomes
            ),
            "split_counts": dict(
                sorted(split_counts.items())
            ),
            "reward_stage_counts": dict(
                sorted(reward_stage_counts.items())
            ),
            "commercially_grounded_episodes": sum(
                1
                for episode in episodes
                if (
                    episode["reward"]["reward_stage"]
                    == "commercial_grounded"
                )
            ),
        },
        "credit_conservation": {
            "per_outcome_credit_totals": dict(
                sorted(credit_totals.items())
            ),
            "rule": (
                "credited outcomes conserve total "
                "credit at 1.0"
            ),
        },
        "episodes": episodes,
        "outcome_credit_edges": credit_edges,
        "excluded_runs": excluded_runs,
        "excluded_outcomes": excluded_outcomes,
    }


def validate_training_environment(
    environment: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if environment.get("schema_version") != 1:
        errors.append("unexpected_schema_version")
    if environment.get("causal_claim") is not False:
        errors.append("causal_claim_must_be_false")
    if environment.get("policy_effect") != "none":
        errors.append("policy_effect_must_be_none")

    episodes = environment.get("episodes") or []
    seen_ids: set[str] = set()
    for episode in episodes:
        rid = episode.get("run_id")
        if not isinstance(rid, str) or not rid:
            errors.append("episode_run_id_required")
            continue
        if rid in seen_ids:
            errors.append(f"duplicate_episode:{rid}")
        seen_ids.add(rid)

        if episode.get("split") not in {
            "train",
            "confirm",
            "evaluation_only",
        }:
            errors.append(f"invalid_split:{rid}")

        reward = (
            episode.get("reward") or {}
        ).get("training_reward")
        if (
            not isinstance(reward, (int, float))
            or not math.isfinite(reward)
            or not -1.0 <= reward <= 1.0
        ):
            errors.append(f"invalid_reward:{rid}")

        expected_sha = _stable_json_sha256(
            {
                key: value
                for key, value in episode.items()
                if key != "episode_sha256"
            }
        )
        if (
            episode.get("episode_sha256")
            != expected_sha
        ):
            errors.append(
                f"episode_hash_mismatch:{rid}"
            )

    edges = (
        environment.get("outcome_credit_edges")
        or []
    )
    split_by_run = {
        episode["run_id"]: episode["split"]
        for episode in episodes
    }
    by_outcome: dict[
        str,
        list[Mapping[str, Any]],
    ] = {}
    for edge in edges:
        outcome_id = str(
            edge.get("outcome_id") or ""
        )
        by_outcome.setdefault(
            outcome_id,
            [],
        ).append(edge)

        rid = edge.get("run_id")
        if rid not in split_by_run:
            errors.append(
                f"credit_unknown_run:{rid}"
            )
        elif edge.get("split") != split_by_run[rid]:
            errors.append(
                f"credit_split_mismatch:{rid}"
            )

        credit = edge.get("credit")
        if (
            not isinstance(credit, (int, float))
            or credit <= 0
            or credit > 1
        ):
            errors.append(
                "invalid_credit:"
                f"{outcome_id}:{rid}"
            )

    for outcome_id, rows in by_outcome.items():
        total = sum(
            float(row["credit"])
            for row in rows
        )
        if not math.isclose(
            total,
            1.0,
            rel_tol=0,
            abs_tol=1e-9,
        ):
            errors.append(
                "credit_not_conserved:"
                f"{outcome_id}:{total}"
            )
        splits = {
            row.get("split")
            for row in rows
        }
        if len(splits) != 1:
            errors.append(
                f"outcome_crosses_split:{outcome_id}"
            )

    return errors
