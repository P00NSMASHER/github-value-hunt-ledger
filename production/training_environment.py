from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from production.blind_partition import trusted_claim_id


_VALID_RESULTS = {"PASSED", "FAILED", "PARTIAL"}
_VALID_MOVE_TYPES = {
    "direct_domain_search",
    "code_signature_search",
    "official_source_trace",
    "organization_graph",
    "contributor_or_commit_lineage",
    "paper_to_code_lineage",
    "package_or_dependency_graph",
    "adjacent_domain_invariant",
    "independent_comparator",
    "history_archaeology",
    "other",
}
_VALID_MOVE_RESULTS = {
    "qualifying_hit",
    "useful_hit",
    "weak_hit",
    "no_hit",
    "retrieval_limited",
    "blocked",
    "unknown",
}
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


def _training_search_moves(
    run: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Preserve move-level evidence using the schema's stable move_type."""
    rows: list[dict[str, Any]] = []
    for move in run.get("search_moves") or []:
        if not isinstance(move, Mapping):
            continue
        move_type = move.get("move_type")
        result = move.get("result")
        if not isinstance(move_type, str) or not move_type:
            continue
        if not isinstance(result, str) or not result:
            continue
        row = {
            "key": f"MOVE:{move_type}",
            "move_type": move_type,
            "result": result,
            "surface": move.get("surface"),
            "query_or_action": move.get("query_or_action"),
            "candidate_count": move.get("candidate_count"),
            "deep_inspected": move.get("deep_inspected"),
            "retained_count": move.get("retained_count"),
        }
        rows.append(row)
    return rows


def _run_time(run: Mapping[str, Any]) -> str:
    return str(run.get("timestamp") or run.get("date") or "")


def _outcome_time(outcome: Mapping[str, Any]) -> str:
    return str(
        outcome.get("timestamp")
        or outcome.get("observed_at")
        or outcome.get("date")
        or ""
    )


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


def _not_after(
    run: Mapping[str, Any],
    outcome: Mapping[str, Any],
    *,
    direct_origin: bool = False,
) -> bool:
    """Prevent future information from crediting an earlier training episode.

    Direct origins are explicit provenance and may share a date with a
    date-only outcome. Indirect support requires strict temporal precedence
    when the outcome has only day precision, because same-day ordering is
    otherwise unknowable.
    """
    run_raw = _run_time(run)
    outcome_raw = _outcome_time(outcome)
    if not run_raw or not outcome_raw:
        return direct_origin

    run_time = _date_key(run_raw)
    out_time = _date_key(outcome_raw)
    if not run_time or not out_time:
        return direct_origin

    outcome_has_clock = "T" in outcome_raw
    if outcome_has_clock:
        return run_time <= out_time
    if direct_origin:
        return run_time[:10] <= out_time[:10]
    return run_time[:10] < out_time[:10]


def partition_for_id(
    identifier: str,
    *,
    config: TrainingEnvironmentConfig | None = None,
) -> str:
    """Hash a precommitted identifier into train or confirm."""
    cfg = config or TrainingEnvironmentConfig()
    cfg.validate()
    if not identifier:
        return "excluded"
    digest = hashlib.sha256(identifier.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:8], "big") % cfg.confirm_modulus
    return "confirm" if bucket == cfg.confirm_bucket else "train"


def partition_basis_for_run(
    run: Mapping[str, Any],
    *,
    split_receipts: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve a post-run blind partition without exposing it pre-hunt.

    A V14+ generated claim is eligible for independent confirmation only after
    canonical intake has a persisted blind-partition receipt. The worker sees
    the claim ID before searching but not the HMAC key used by CI, so it cannot
    derive train/confirm in advance. Missing receipts remain pending and do not
    train or confirm. Manual/legacy records remain train-only.
    """
    claim_id = trusted_claim_id(run)
    if claim_id:
        partition = (
            (split_receipts or {}).get(claim_id)
            if split_receipts is not None
            else None
        )
        return {
            "trusted": True,
            "source": (
                "blind_partition_receipt"
                if partition in {"train", "confirm"}
                else "pending_blind_partition"
            ),
            "identifier": claim_id,
            "partition": partition,
            "provenance_contract": "validated_v14_generated_claim",
        }
    return {
        "trusted": False,
        "source": "run_id_fallback_train_only",
        "identifier": str(run.get("search_run_id") or ""),
        "partition": "train",
        "provenance_contract": "untrusted_or_legacy",
    }


def telemetry_consistency_errors(
    run: Mapping[str, Any],
) -> tuple[str, ...]:
    """Return cross-field telemetry contradictions that make learning unsafe.

    Schema-valid nonnegative counters can still be mutually impossible. Those
    records remain durable evidence, but they must not train value estimates,
    receive indirect outcome credit, or satisfy policy evidence thresholds.
    """
    errors: list[str] = []

    candidate_count = run.get("candidate_count")
    deep = run.get("deep_inspected")
    retained = run.get("retained_count")
    promoted = run.get("master_promoted_count")

    if (
        isinstance(candidate_count, int)
        and candidate_count >= 0
        and isinstance(deep, int)
        and deep >= 0
        and deep > candidate_count
    ):
        errors.append("deep_inspected_exceeds_candidates")
    if (
        isinstance(deep, int)
        and deep >= 0
        and isinstance(retained, int)
        and retained >= 0
        and retained > deep
    ):
        errors.append("retained_exceeds_deep_inspected")
    if (
        isinstance(retained, int)
        and retained >= 0
        and isinstance(promoted, int)
        and promoted >= 0
        and promoted > retained
    ):
        errors.append("promotions_exceed_retained")

    checks = run.get("candidate_preflight_checks")
    hits = run.get("known_candidate_preflight_hits")
    avoided = run.get("duplicate_deep_inspections_avoided")
    if (
        isinstance(checks, int)
        and checks >= 0
        and isinstance(hits, int)
        and hits >= 0
        and hits > checks
    ):
        errors.append("preflight_hits_exceed_checks")
    if (
        isinstance(checks, int)
        and checks >= 0
        and isinstance(avoided, int)
        and avoided >= 0
        and avoided > checks
    ):
        errors.append("duplicate_avoidance_exceeds_checks")

    elapsed = run.get("elapsed_minutes")
    if isinstance(elapsed, (int, float)) and elapsed < 0:
        errors.append("negative_elapsed_minutes")
    tool_calls = run.get("tool_calls")
    if isinstance(tool_calls, int) and tool_calls < 0:
        errors.append("negative_tool_calls")

    return tuple(errors)


def split_for_run(
    run: Mapping[str, Any],
    *,
    config: TrainingEnvironmentConfig | None = None,
    split_receipts: Mapping[str, str] | None = None,
) -> str:
    cfg = config or TrainingEnvironmentConfig()
    cfg.validate()
    quality = run.get("measurement_quality")
    if quality == "benchmark":
        return "evaluation_only"
    if quality != "prospective":
        return "excluded"
    work_action = run.get("work_action")
    if work_action not in (None, "search"):
        return "excluded"
    if telemetry_consistency_errors(run):
        return "excluded"
    if work_action is None:
        candidate_count = run.get("candidate_count")
        deep_inspected = run.get("deep_inspected")
        legacy_search_evidence = (
            isinstance(candidate_count, int)
            and candidate_count > 0
        ) or (
            isinstance(deep_inspected, int)
            and deep_inspected > 0
        )
        if not legacy_search_evidence:
            return "excluded"
    run_id = str(run.get("search_run_id") or "")
    if not run_id:
        return "excluded"
    basis = partition_basis_for_run(
        run,
        split_receipts=split_receipts,
    )
    if not basis["trusted"]:
        # Manual/unallocated IDs are controllable by the worker. They remain
        # useful train evidence but can never manufacture confirm evidence.
        return "train"
    partition = basis.get("partition")
    if partition not in {"train", "confirm"}:
        return "pending_partition"
    return str(partition)


def discovery_signal(
    run: Mapping[str, Any],
    *,
    split_receipts: Mapping[str, str] | None = None,
) -> float | None:
    if split_for_run(
        run,
        split_receipts=split_receipts,
    ) in {"excluded", "pending_partition"}:
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
    observed_values = [
        float(value)
        for value in (revenue, customer_value)
        if isinstance(value, (int, float)) and value > 0
    ]
    economic_value_usd = max(observed_values) if observed_values else 0.0
    commercial_observed = economic_value_usd > 0
    # Bounded log scale: $1M reaches the ceiling, while small realized
    # amounts still count without being treated as equivalent to $1M.
    commercial = (
        min(
            1.0,
            math.log10(1.0 + economic_value_usd) / 6.0,
        )
        if commercial_observed
        else 0.0
    )

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
        "economic_value_usd": economic_value_usd,
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
    """Score indirect provenance without rewarding experiment membership alone."""
    support_items = [
        item
        for item in evidence
        if item.get("kind") != "direct_origin"
    ]
    if not support_items:
        return 0.0

    concrete_kinds = {
        "new_capability",
        "strengthened_capability",
        "retained_repository",
    }
    if not any(
        item.get("kind") in concrete_kinds
        for item in support_items
    ):
        # Sharing an experiment only establishes context, not contribution.
        return 0.0

    complement = 1.0
    for item in support_items:
        strength = float(item["strength"])
        complement *= 1.0 - _clip(
            strength,
            0.0,
            1.0,
        )
    return 1.0 - complement


def build_outcome_credit(
    search_runs: Sequence[Mapping[str, Any]],
    outcomes: Sequence[Mapping[str, Any]],
    *,
    config: TrainingEnvironmentConfig | None = None,
    split_receipts: Mapping[str, str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cfg = config or TrainingEnvironmentConfig()
    cfg.validate()
    runs_by_id = {
        str(run.get("search_run_id")): run
        for run in search_runs
        if run.get("search_run_id")
    }
    splits = {
        rid: split_for_run(
            run,
            config=cfg,
            split_receipts=split_receipts,
        )
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
            anchor_bases = {
                rid: partition_basis_for_run(
                    runs_by_id[rid]
                )
                for rid in direct_ids
            }
            untrusted_anchor_ids = sorted(
                rid
                for rid, basis in anchor_bases.items()
                if not basis["trusted"]
            )
            if untrusted_anchor_ids:
                excluded.append(
                    {
                        "outcome_id": outcome_id,
                        "reason": (
                            "untrusted_excluded_direct_origin_partition"
                        ),
                        "origin_run_ids": untrusted_anchor_ids,
                    }
                )
                continue
            anchor_splits = {
                partition_for_id(
                    str(basis["identifier"]),
                    config=cfg,
                )
                for basis in anchor_bases.values()
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
            credit_anchor_kind = "excluded_direct_origin_precommit"

        invalid_direct_ids = [
            rid
            for rid in direct_ids
            if not _not_after(
                runs_by_id[rid],
                outcome,
                direct_origin=True,
            )
        ]
        if invalid_direct_ids:
            excluded.append(
                {
                    "outcome_id": outcome_id,
                    "reason": "direct_origin_after_outcome",
                    "origin_run_ids": sorted(invalid_direct_ids),
                }
            )
            continue

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
            is_direct = rid in direct_set
            if not _not_after(
                run,
                outcome,
                direct_origin=is_direct,
            ):
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
    split_receipts: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    cfg = config or TrainingEnvironmentConfig()
    cfg.validate()
    credit_edges, excluded_outcomes = build_outcome_credit(
        search_runs,
        outcomes,
        config=cfg,
        split_receipts=split_receipts,
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
        consistency_errors = telemetry_consistency_errors(run)
        split = split_for_run(
            run,
            config=cfg,
            split_receipts=split_receipts,
        )
        discovery = discovery_signal(
            run,
            split_receipts=split_receipts,
        )
        if split in {"excluded", "pending_partition"} or discovery is None:
            excluded_runs.append(
                {
                    "run_id": rid,
                    "reason": (
                        "inconsistent_search_telemetry:"
                        + ",".join(consistency_errors)
                        if consistency_errors
                        else (
                            "pending_blind_partition"
                            if split == "pending_partition"
                            else "not_eligible_search_training_record"
                        )
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
                "search_moves": _training_search_moves(run),
                "search_move_ids": [
                    move["key"]
                    for move in _training_search_moves(run)
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
                "partition_basis": (
                    partition_basis_for_run(run)
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
                "generated runs hash a precommitted execution claim, "
                "assignment or dispatch id mod "
                f"{cfg.confirm_modulus}; bucket "
                f"{cfg.confirm_bucket}=confirm; others=train. "
                "Manual/untrusted run IDs are train-only."
            ),
            "benchmark": "evaluation_only",
            "retrospective_or_non_search": "excluded",
            "outcome_credit": (
                "never crosses train/confirm/evaluation "
                "split; mixed-origin outcomes excluded"
            ),
            "blind_partition_receipts_required": True,
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
    reward_policy = environment.get("reward_policy") or {}
    try:
        split_validation_config = TrainingEnvironmentConfig(
            confirm_modulus=int(
                reward_policy.get("confirm_modulus", 5)
            ),
            confirm_bucket=int(
                reward_policy.get("confirm_bucket", 0)
            ),
        )
        split_validation_config.validate()
    except (TypeError, ValueError):
        errors.append("invalid_split_policy_config")
        split_validation_config = TrainingEnvironmentConfig()
    seen_ids: set[str] = set()
    for episode in episodes:
        rid = episode.get("run_id")
        if not isinstance(rid, str) or not rid:
            errors.append("episode_run_id_required")
            continue
        if rid in seen_ids:
            errors.append(f"duplicate_episode:{rid}")
        seen_ids.add(rid)

        split = episode.get("split")
        if split not in {
            "train",
            "confirm",
            "evaluation_only",
        }:
            errors.append(f"invalid_split:{rid}")

        basis = (
            episode.get("provenance") or {}
        ).get("partition_basis") or {}
        if split in {"train", "confirm"}:
            trusted = basis.get("trusted") is True
            identifier = basis.get("identifier")
            if split == "confirm" and not trusted:
                errors.append(
                    f"untrusted_confirm_partition:{rid}"
                )
            if trusted:
                if (
                    not isinstance(identifier, str)
                    or not identifier
                ):
                    errors.append(
                        f"missing_partition_identifier:{rid}"
                    )
                else:
                    expected_split = partition_for_id(
                        identifier,
                        config=split_validation_config,
                    )
                    if split != expected_split:
                        errors.append(
                            f"partition_hash_mismatch:{rid}"
                        )
            elif split != "train":
                errors.append(
                    f"untrusted_partition_not_train:{rid}"
                )

        observation = episode.get("observation") or {}
        episode_consistency = telemetry_consistency_errors(observation)
        if episode_consistency:
            errors.append(
                "episode_inconsistent_telemetry:"
                + str(rid)
                + ":"
                + ",".join(episode_consistency)
            )

        reward = (
            episode.get("reward") or {}
        ).get("training_reward")
        if (
            not isinstance(reward, (int, float))
            or not math.isfinite(reward)
            or not -1.0 <= reward <= 1.0
        ):
            errors.append(f"invalid_reward:{rid}")

        action = episode.get("action") or {}
        moves = action.get("search_moves") or []
        move_ids = action.get("search_move_ids") or []
        expected_move_ids: list[str] = []
        for move_index, move in enumerate(moves):
            if not isinstance(move, Mapping):
                errors.append(
                    f"invalid_search_move:{rid}:{move_index}"
                )
                continue
            move_type = move.get("move_type")
            move_result = move.get("result")
            move_key = move.get("key")
            if move_type not in _VALID_MOVE_TYPES:
                errors.append(
                    f"invalid_move_type:{rid}:{move_index}"
                )
            if move_result not in _VALID_MOVE_RESULTS:
                errors.append(
                    f"invalid_move_result:{rid}:{move_index}"
                )
            if (
                not isinstance(move_key, str)
                or move_key != f"MOVE:{move_type}"
            ):
                errors.append(
                    f"invalid_move_key:{rid}:{move_index}"
                )
            else:
                expected_move_ids.append(move_key)

            candidate_count = move.get("candidate_count")
            deep_count = move.get("deep_inspected")
            retained_count = move.get("retained_count")
            for field_name, value in (
                ("candidate_count", candidate_count),
                ("deep_inspected", deep_count),
                ("retained_count", retained_count),
            ):
                if (
                    value is not None
                    and (
                        not isinstance(value, int)
                        or value < 0
                    )
                ):
                    errors.append(
                        f"invalid_move_{field_name}:{rid}:{move_index}"
                    )
            if (
                isinstance(candidate_count, int)
                and isinstance(deep_count, int)
                and deep_count > candidate_count
            ):
                errors.append(
                    f"move_deep_exceeds_candidates:{rid}:{move_index}"
                )
            if (
                isinstance(deep_count, int)
                and isinstance(retained_count, int)
                and retained_count > deep_count
            ):
                errors.append(
                    f"move_retained_exceeds_deep:{rid}:{move_index}"
                )

        if move_ids != expected_move_ids:
            errors.append(f"search_move_ids_mismatch:{rid}")

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
