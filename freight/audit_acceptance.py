"""RecoveryOS blind customer audit acceptance methodology.

This module evaluates methodology integrity and buyer-facing audit quality. It
is deliberately separate from the internal synthetic gold benchmark.

The contract is selective: REVIEW is an abstention, not a correct auto-decision.
Unresolved truth, incomplete evidence, or unresolved authority may never become
an automatic positive/negative money assertion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

TRUTH_LABELS = {"POSITIVE", "NEGATIVE", "UNRESOLVED"}
PREDICTED_LABELS = {"POSITIVE", "NEGATIVE", "REVIEW"}
REVIEW_LABELS = {"POSITIVE", "NEGATIVE", "UNRESOLVED"}
AUTHORITY_STATES = {"VERIFIED", "UNRESOLVED"}
SAMPLE_METHODS = {"CENSUS", "STRATIFIED_RANDOM"}


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sample_hash(case_ids: list[str]) -> str:
    return canonical_hash({"schema": 1, "case_ids": sorted(case_ids)})


def truth_manifest_hash(cases: list[dict]) -> str:
    rows = [
        {
            "case_id": case["case_id"],
            "truth_label": case["truth_label"],
            "truth_variance_cents": case["truth_variance_cents"],
            "authority_state": case["authority_state"],
            "source_complete": case["source_complete"],
            "economic_issue_id": case["economic_issue_id"],
            "truth_incumbent_known": case["truth_incumbent_known"],
        }
        for case in sorted(cases, key=lambda row: row["case_id"])
    ]
    return canonical_hash({"schema": 1, "truth": rows})


def recoveryos_output_hash(cases: list[dict]) -> str:
    rows = [
        {
            "case_id": case["case_id"],
            "predicted_label": case["predicted_label"],
            "predicted_variance_cents": case["predicted_variance_cents"],
            "confidence_ppm": case["confidence_ppm"],
            "predicted_net_new_cents": case["predicted_net_new_cents"],
        }
        for case in sorted(cases, key=lambda row: row["case_id"])
    ]
    return canonical_hash({"schema": 1, "recoveryos_output": rows})


def _parse_time(value: Any, name: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{name} timestamp required")
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{name} must be ISO-8601")
        return None


def _ratio(num: float, den: float) -> float | None:
    return None if den <= 0 else num / den


def _wilson(successes: int, total: int, z: float = 1.959963984540054) -> dict | None:
    if total <= 0:
        return None
    p = successes / total
    z2 = z * z
    denom = 1 + z2 / total
    centre = (p + z2 / (2 * total)) / denom
    margin = z * math.sqrt((p * (1 - p) + z2 / (4 * total)) / total) / denom
    return {
        "point": p,
        "lower": max(0.0, centre - margin),
        "upper": min(1.0, centre + margin),
    }


def _required_sample_size(population_size: int, margin: float, z: float = 1.959963984540054) -> int:
    if population_size <= 0:
        return 0
    n0 = (z * z * 0.25) / (margin * margin)
    adjusted = n0 / (1 + ((n0 - 1) / population_size))
    return min(population_size, math.ceil(adjusted))


def _cohen_kappa(pairs: list[tuple[str, str]]) -> dict | None:
    if not pairs:
        return None
    labels = sorted(REVIEW_LABELS)
    n = len(pairs)
    agree = sum(a == b for a, b in pairs)
    observed = agree / n
    left = Counter(a for a, _ in pairs)
    right = Counter(b for _, b in pairs)
    expected = sum((left[label] / n) * (right[label] / n) for label in labels)
    if expected >= 1:
        kappa = 1.0 if observed == 1.0 else 0.0
    else:
        kappa = (observed - expected) / (1 - expected)
    return {"cases": n, "agreement": observed, "kappa": kappa}


def _calibration(
    rows: list[tuple[float, bool]], bin_count: int = 10
) -> dict | None:
    if not rows:
        return None
    bins: list[list[tuple[float, bool]]] = [[] for _ in range(bin_count)]
    for confidence, correct in rows:
        index = min(bin_count - 1, int(confidence * bin_count))
        bins[index].append((confidence, correct))
    ece = 0.0
    output_bins = []
    for index, bucket in enumerate(bins):
        if not bucket:
            continue
        avg_confidence = sum(item[0] for item in bucket) / len(bucket)
        accuracy = sum(1 for _, correct in bucket if correct) / len(bucket)
        weight = len(bucket) / len(rows)
        ece += weight * abs(avg_confidence - accuracy)
        output_bins.append(
            {
                "index": index,
                "count": len(bucket),
                "avg_confidence": avg_confidence,
                "accuracy": accuracy,
            }
        )
    brier = (
        sum(
            (confidence - (1.0 if correct else 0.0)) ** 2
            for confidence, correct in rows
        )
        / len(rows)
    )
    return {"ece": ece, "brier": brier, "bins": output_bins}


def validate_policy(policy: dict) -> list[str]:
    errors: list[str] = []
    if policy.get("schema_version") != 2:
        errors.append("policy schema_version must be 2")
    if policy.get("policy_id") != "recoveryos-blind-audit-acceptance-v2":
        errors.append("unexpected audit acceptance policy_id")
    thresholds = policy.get("thresholds")
    if not isinstance(thresholds, dict):
        return errors + ["policy thresholds must be an object"]

    integer_minima = {
        "min_adjudicated_cases": 1,
        "min_positive_cases": 1,
        "min_negative_cases": 1,
        "min_dual_review_cases": 1,
        "min_dual_review_positive_cases": 1,
        "min_dual_review_negative_cases": 1,
        "max_unsupported_auto_decisions": 0,
        "max_incumbent_leakage_cents": 0,
        "max_duplicate_leakage_cents": 0,
    }
    for key, minimum in integer_minima.items():
        value = thresholds.get(key)
        if not isinstance(value, int) or value < minimum:
            errors.append(f"{key} must be integer >= {minimum}")

    proportions = (
        "min_dual_review_fraction",
        "min_cohen_kappa",
        "min_auto_coverage",
        "min_precision_lower_95",
        "max_false_positive_rate_upper_95",
        "max_false_negative_rate_upper_95",
        "max_false_positive_dollar_share",
        "max_false_negative_dollar_share",
        "max_review_rate",
        "max_ece",
        "target_case_rate_margin_95",
    )
    for key in proportions:
        value = thresholds.get(key)
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            errors.append(f"{key} must be between 0 and 1")

    if thresholds.get("min_adjudicated_cases", 0) < (
        thresholds.get("min_positive_cases", 0)
        + thresholds.get("min_negative_cases", 0)
    ):
        errors.append(
            "min_adjudicated_cases must allow the positive + negative minima"
        )

    if not isinstance(policy.get("claim_boundary"), list) or len(
        policy["claim_boundary"]
    ) < 3:
        errors.append(
            "policy claim_boundary must contain at least three statements"
        )
    return errors


def validate_pilot(payload: dict, policy: dict) -> list[str]:
    errors = validate_policy(policy)
    if payload.get("schema_version") != 2:
        errors.append("pilot schema_version must be 2")
    if payload.get("protocol_id") != policy.get("policy_id"):
        errors.append("pilot protocol_id does not match policy")

    roles = payload.get("roles") or {}
    role_ids = [
        roles.get(name)
        for name in (
            "truth_owner_id",
            "reviewer_a_id",
            "reviewer_b_id",
            "recoveryos_operator_id",
        )
    ]
    if any(not isinstance(value, str) or not value for value in role_ids):
        errors.append("truth/reviewer/operator role IDs are required")
    elif len(set(role_ids)) != len(role_ids):
        errors.append(
            "truth owner, two reviewers, and RecoveryOS operator must be distinct"
        )

    blindness = payload.get("blindness") or {}
    required_blind = {
        "truth_owner_saw_recoveryos_before_truth_freeze": False,
        "recoveryos_team_saw_truth_before_output_freeze": False,
        "sample_selected_before_recoveryos_output": True,
        "dual_review_selected_before_recoveryos_output": True,
        "truth_owner_independent_of_recoveryos_builder": True,
    }
    for key, expected in required_blind.items():
        if blindness.get(key) is not expected:
            errors.append(f"blindness violation: {key} must be {expected}")

    timeline = payload.get("timeline") or {}
    pop_time = _parse_time(
        timeline.get("population_frozen_at"), "population_frozen_at", errors
    )
    truth_time = _parse_time(
        timeline.get("truth_frozen_at"), "truth_frozen_at", errors
    )
    output_time = _parse_time(
        timeline.get("recoveryos_output_frozen_at"),
        "recoveryos_output_frozen_at",
        errors,
    )
    reveal_time = _parse_time(
        timeline.get("joint_unseal_at"), "joint_unseal_at", errors
    )
    incumbent_time = _parse_time(
        timeline.get("incumbent_output_frozen_at"),
        "incumbent_output_frozen_at",
        errors,
    )
    if all(
        x is not None
        for x in (
            pop_time,
            truth_time,
            output_time,
            reveal_time,
            incumbent_time,
        )
    ):
        if pop_time > min(truth_time, output_time, incumbent_time):
            errors.append(
                "population must be frozen before truth/output/incumbent work"
            )
        if truth_time > reveal_time:
            errors.append("truth must be frozen before joint unseal")
        if output_time > reveal_time:
            errors.append(
                "RecoveryOS output must be frozen before joint unseal"
            )
        if incumbent_time > reveal_time:
            errors.append("incumbent output must be frozen before joint unseal")

    population = payload.get("population") or {}
    population_size = population.get("population_size")
    if not isinstance(population_size, int) or population_size <= 0:
        errors.append("population_size must be a positive integer")
        population_size = 0
    for key in (
        "population_hash",
        "sample_hash",
        "truth_manifest_hash",
        "recoveryos_output_hash",
        "incumbent_output_hash",
    ):
        value = population.get(key)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(ch not in "0123456789abcdef" for ch in value)
        ):
            errors.append(f"{key} must be lowercase SHA-256")

    sampling = payload.get("sampling") or {}
    method = sampling.get("method")
    if method not in SAMPLE_METHODS:
        errors.append(
            "sampling method must be CENSUS or STRATIFIED_RANDOM"
        )
    if method == "STRATIFIED_RANDOM" and not isinstance(
        sampling.get("seed"), str
    ):
        errors.append(
            "stratified random sampling requires a frozen seed"
        )
    strata = sampling.get("strata")
    if not isinstance(strata, list) or not strata:
        errors.append("sampling strata required")
        strata = []

    declared_strata: dict[str, dict] = {}
    for item in strata:
        key = item.get("key")
        if not isinstance(key, str) or not key:
            errors.append("each stratum requires a key")
            continue
        if key in declared_strata:
            errors.append(f"duplicate stratum key: {key}")
            continue
        pop_count = item.get("population_count")
        target = item.get("sample_target")
        if not isinstance(pop_count, int) or pop_count <= 0:
            errors.append(f"{key}: population_count must be positive")
        if not isinstance(target, int) or target <= 0:
            errors.append(f"{key}: sample_target must be positive")
        if (
            isinstance(pop_count, int)
            and isinstance(target, int)
            and target > pop_count
        ):
            errors.append(
                f"{key}: sample_target cannot exceed population_count"
            )
        declared_strata[key] = item
    if population_size and sum(
        int(item.get("population_count") or 0) for item in strata
    ) != population_size:
        errors.append(
            "stratum population counts must sum to population_size"
        )

    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        return errors + ["pilot cases required"]
    if population.get("sample_size") != len(cases):
        errors.append("declared sample_size must equal case count")

    ids: list[str] = []
    actual_strata = Counter()
    for index, case in enumerate(cases):
        prefix = f"case[{index}]"
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{prefix}: case_id required")
            case_id = f"INVALID-{index}"
        ids.append(case_id)
        stratum_key = case.get("stratum_key")
        if stratum_key not in declared_strata:
            errors.append(f"{prefix}: undeclared stratum")
        else:
            actual_strata[stratum_key] += 1

        truth = case.get("truth_label")
        pred = case.get("predicted_label")
        if truth not in TRUTH_LABELS:
            errors.append(f"{prefix}: invalid truth_label")
        if pred not in PREDICTED_LABELS:
            errors.append(f"{prefix}: invalid predicted_label")

        truth_cents = case.get("truth_variance_cents")
        pred_cents = case.get("predicted_variance_cents")
        net_new = case.get("predicted_net_new_cents")
        if not isinstance(truth_cents, int) or truth_cents < 0:
            errors.append(
                f"{prefix}: truth_variance_cents must be nonnegative integer"
            )
        elif truth == "POSITIVE" and truth_cents <= 0:
            errors.append(f"{prefix}: POSITIVE truth requires positive variance")
        elif truth == "NEGATIVE" and truth_cents != 0:
            errors.append(f"{prefix}: NEGATIVE truth requires zero variance")
        if case.get("authority_state") == "UNRESOLVED" or case.get("source_complete") is False:
            if truth != "UNRESOLVED":
                errors.append(
                    f"{prefix}: unresolved authority/incomplete source requires UNRESOLVED truth"
                )
        if pred == "REVIEW":
            if pred_cents is not None:
                errors.append(
                    f"{prefix}: REVIEW predicted_variance_cents must be null"
                )
        elif not isinstance(pred_cents, int) or pred_cents < 0:
            errors.append(
                f"{prefix}: automatic predicted_variance_cents must be nonnegative integer"
            )
        elif pred == "POSITIVE" and pred_cents <= 0:
            errors.append(f"{prefix}: POSITIVE prediction requires positive variance")
        elif pred == "NEGATIVE" and pred_cents != 0:
            errors.append(f"{prefix}: NEGATIVE prediction requires zero variance")
        if not isinstance(net_new, int) or net_new < 0:
            errors.append(
                f"{prefix}: predicted_net_new_cents must be nonnegative integer"
            )
        elif pred != "POSITIVE" and net_new != 0:
            errors.append(f"{prefix}: non-POSITIVE prediction cannot assert net-new cents")
        elif pred == "POSITIVE" and isinstance(pred_cents, int) and net_new > pred_cents:
            errors.append(f"{prefix}: net-new cents cannot exceed predicted variance")

        confidence = case.get("confidence_ppm")
        if (
            not isinstance(confidence, int)
            or not 0 <= confidence <= 1_000_000
        ):
            errors.append(f"{prefix}: confidence_ppm out of range")
        if case.get("authority_state") not in AUTHORITY_STATES:
            errors.append(f"{prefix}: invalid authority_state")
        if not isinstance(case.get("source_complete"), bool):
            errors.append(f"{prefix}: source_complete must be boolean")
        if (
            not isinstance(case.get("economic_issue_id"), str)
            or not case.get("economic_issue_id")
        ):
            errors.append(f"{prefix}: economic_issue_id required")
        if not isinstance(case.get("truth_incumbent_known"), bool):
            errors.append(
                f"{prefix}: truth_incumbent_known must be boolean"
            )

        ra = case.get("reviewer_a_label")
        rb = case.get("reviewer_b_label")
        if (ra is None) != (rb is None):
            errors.append(
                f"{prefix}: dual review labels must be both present or both absent"
            )
        if ra is not None and (
            ra not in REVIEW_LABELS or rb not in REVIEW_LABELS
        ):
            errors.append(f"{prefix}: invalid dual-review label")
        if ra is not None and ra != rb:
            note = case.get("adjudication_note")
            if not isinstance(note, str) or len(note.strip()) < 10:
                errors.append(
                    f"{prefix}: reviewer disagreement requires adjudication_note"
                )

    duplicate_ids = len(ids) - len(set(ids))
    if duplicate_ids:
        errors.append(f"duplicate case IDs: {duplicate_ids}")
    if (
        isinstance(population.get("sample_hash"), str)
        and population["sample_hash"] != sample_hash(ids)
    ):
        errors.append("sample_hash does not match frozen case IDs")
    if (
        isinstance(population.get("truth_manifest_hash"), str)
        and population["truth_manifest_hash"] != truth_manifest_hash(cases)
    ):
        errors.append(
            "truth_manifest_hash does not match case truth"
        )
    if (
        isinstance(population.get("recoveryos_output_hash"), str)
        and population["recoveryos_output_hash"]
        != recoveryos_output_hash(cases)
    ):
        errors.append(
            "recoveryos_output_hash does not match case output"
        )

    for key, item in declared_strata.items():
        target = int(item.get("sample_target") or 0)
        if actual_strata[key] < target:
            errors.append(
                f"{key}: sampled {actual_strata[key]} below target {target}"
            )
        if (
            method == "CENSUS"
            and actual_strata[key]
            != int(item.get("population_count") or 0)
        ):
            errors.append(
                f"{key}: census sample must include whole stratum"
            )
    return errors


def build_report(payload: dict, policy: dict) -> dict:
    errors = validate_pilot(payload, policy)
    if errors:
        raise ValueError("; ".join(errors))

    cases = payload["cases"]
    adjudicated = [
        case
        for case in cases
        if case["truth_label"] in {"POSITIVE", "NEGATIVE"}
    ]
    positives = [
        case for case in adjudicated if case["truth_label"] == "POSITIVE"
    ]
    negatives = [
        case for case in adjudicated if case["truth_label"] == "NEGATIVE"
    ]
    auto = [
        case
        for case in adjudicated
        if case["predicted_label"] != "REVIEW"
    ]
    reviews = [
        case
        for case in adjudicated
        if case["predicted_label"] == "REVIEW"
    ]

    tp = sum(
        case["truth_label"] == "POSITIVE"
        and case["predicted_label"] == "POSITIVE"
        for case in adjudicated
    )
    tn = sum(
        case["truth_label"] == "NEGATIVE"
        and case["predicted_label"] == "NEGATIVE"
        for case in adjudicated
    )
    fp = sum(
        case["truth_label"] == "NEGATIVE"
        and case["predicted_label"] == "POSITIVE"
        for case in adjudicated
    )
    fn = sum(
        case["truth_label"] == "POSITIVE"
        and case["predicted_label"] == "NEGATIVE"
        for case in adjudicated
    )

    unsupported_auto = sum(
        case["predicted_label"] != "REVIEW"
        and (
            case["truth_label"] == "UNRESOLVED"
            or case["authority_state"] != "VERIFIED"
            or not case["source_complete"]
        )
        for case in cases
    )

    predicted_positive_dollars = sum(
        case["predicted_variance_cents"] or 0
        for case in adjudicated
        if case["predicted_label"] == "POSITIVE"
    )
    truth_positive_dollars = sum(
        case["truth_variance_cents"] for case in positives
    )
    fp_dollars = sum(
        case["predicted_variance_cents"] or 0
        for case in negatives
        if case["predicted_label"] == "POSITIVE"
    )
    fn_dollars = sum(
        case["truth_variance_cents"]
        for case in positives
        if case["predicted_label"] == "NEGATIVE"
    )
    review_truth_dollars = sum(
        case["truth_variance_cents"]
        for case in positives
        if case["predicted_label"] == "REVIEW"
    )

    auto_abs_errors = []
    auto_signed_errors = []
    exact_auto = 0
    for case in auto:
        predicted = int(case["predicted_variance_cents"] or 0)
        truth = int(case["truth_variance_cents"])
        delta = predicted - truth
        auto_abs_errors.append(abs(delta))
        auto_signed_errors.append(delta)
        exact_auto += int(delta == 0)

    calibration_rows = []
    for case in auto:
        correct = case["predicted_label"] == case["truth_label"]
        calibration_rows.append(
            (case["confidence_ppm"] / 1_000_000, correct)
        )

    dual_review_cases = [
        case for case in cases if case.get("reviewer_a_label") is not None
    ]
    pairs = [
        (case["reviewer_a_label"], case["reviewer_b_label"])
        for case in dual_review_cases
    ]
    reviewer = _cohen_kappa(pairs)
    dual_review_positive = sum(
        case["truth_label"] == "POSITIVE" for case in dual_review_cases
    )
    dual_review_negative = sum(
        case["truth_label"] == "NEGATIVE" for case in dual_review_cases
    )

    incumbent_leakage = sum(
        case["predicted_net_new_cents"]
        for case in cases
        if case["truth_incumbent_known"]
    )
    duplicate_leakage = 0
    issue_values: dict[str, list[int]] = defaultdict(list)
    for case in cases:
        if case["predicted_net_new_cents"] > 0:
            issue_values[case["economic_issue_id"]].append(
                case["predicted_net_new_cents"]
            )
    for values in issue_values.values():
        if len(values) > 1:
            duplicate_leakage += sum(values) - max(values)

    by_stratum: dict[str, dict] = {}
    for item in payload["sampling"]["strata"]:
        key = item["key"]
        rows = [
            case for case in cases if case["stratum_key"] == key
        ]
        adj = [
            case
            for case in rows
            if case["truth_label"] in {"POSITIVE", "NEGATIVE"}
        ]
        stratum_fp = sum(
            case["truth_label"] == "NEGATIVE"
            and case["predicted_label"] == "POSITIVE"
            for case in adj
        )
        stratum_fn = sum(
            case["truth_label"] == "POSITIVE"
            and case["predicted_label"] == "NEGATIVE"
            for case in adj
        )
        by_stratum[key] = {
            "population_count": item["population_count"],
            "sample_count": len(rows),
            "adjudicated_count": len(adj),
            "false_positive": stratum_fp,
            "false_negative": stratum_fn,
            "review_count": sum(
                case["predicted_label"] == "REVIEW" for case in adj
            ),
        }

    precision = _wilson(tp, tp + fp)
    fpr = _wilson(fp, len(negatives))
    fnr = _wilson(fn, len(positives))
    calibration = _calibration(calibration_rows)

    required_sample_size = _required_sample_size(
        payload["population"]["population_size"],
        policy["thresholds"]["target_case_rate_margin_95"],
    )

    metrics = {
        "sample": {
            "total_cases": len(cases),
            "required_sample_size_95": required_sample_size,
            "adjudicated_cases": len(adjudicated),
            "positive_cases": len(positives),
            "negative_cases": len(negatives),
            "unresolved_truth_cases": len(cases) - len(adjudicated),
            "auto_decisions": len(auto),
            "review_decisions": len(reviews),
            "auto_coverage": _ratio(len(auto), len(adjudicated)),
            "review_rate": _ratio(len(reviews), len(adjudicated)),
            "unsupported_auto_decisions": unsupported_auto,
        },
        "classification": {
            "true_positive": tp,
            "true_negative": tn,
            "false_positive": fp,
            "false_negative": fn,
            "precision_95": precision,
            "false_positive_rate_95": fpr,
            "false_negative_rate_95": fnr,
            "auto_accuracy": _ratio(tp + tn, len(auto)),
        },
        "dollars": {
            "predicted_positive_cents": predicted_positive_dollars,
            "truth_positive_cents": truth_positive_dollars,
            "false_positive_cents": fp_dollars,
            "false_negative_cents": fn_dollars,
            "review_truth_positive_cents": review_truth_dollars,
            "false_positive_dollar_share": (
                _ratio(fp_dollars, predicted_positive_dollars) or 0.0
            ),
            "false_negative_dollar_share": (
                _ratio(fn_dollars, truth_positive_dollars) or 0.0
            ),
            "auto_mean_absolute_error_cents": (
                sum(auto_abs_errors) / len(auto_abs_errors)
                if auto_abs_errors
                else None
            ),
            "auto_net_bias_cents": sum(auto_signed_errors),
            "auto_exact_dollar_rate": _ratio(exact_auto, len(auto)),
            "incumbent_credit_leakage_cents": incumbent_leakage,
            "duplicate_net_new_leakage_cents": duplicate_leakage,
        },
        "calibration": calibration,
        "reviewer_agreement": {
            **(reviewer or {"cases": 0, "agreement": None, "kappa": None}),
            "positive_truth_cases": dual_review_positive,
            "negative_truth_cases": dual_review_negative,
        },
        "strata": by_stratum,
    }

    thresholds = policy["thresholds"]
    gates: dict[str, bool] = {}
    gates["sample_precision_plan"] = len(cases) >= required_sample_size
    gates["sample_adjudicated"] = (
        len(adjudicated) >= min(
            thresholds["min_adjudicated_cases"],
            payload["population"]["population_size"],
        )
    )
    gates["sample_positive"] = (
        len(positives) >= thresholds["min_positive_cases"]
    )
    gates["sample_negative"] = (
        len(negatives) >= thresholds["min_negative_cases"]
    )
    required_dual = max(
        thresholds["min_dual_review_cases"],
        math.ceil(
            len(adjudicated) * thresholds["min_dual_review_fraction"]
        ),
    )
    gates["dual_review_size"] = (
        reviewer is not None and reviewer["cases"] >= required_dual
    )
    gates["dual_review_positive"] = (
        dual_review_positive >= thresholds["min_dual_review_positive_cases"]
    )
    gates["dual_review_negative"] = (
        dual_review_negative >= thresholds["min_dual_review_negative_cases"]
    )
    gates["reviewer_agreement"] = (
        reviewer is not None
        and reviewer["kappa"] >= thresholds["min_cohen_kappa"]
    )
    gates["auto_coverage"] = (
        metrics["sample"]["auto_coverage"] is not None
        and metrics["sample"]["auto_coverage"]
        >= thresholds["min_auto_coverage"]
    )
    gates["review_rate"] = (
        metrics["sample"]["review_rate"] is not None
        and metrics["sample"]["review_rate"]
        <= thresholds["max_review_rate"]
    )
    gates["precision"] = (
        precision is not None
        and precision["lower"] >= thresholds["min_precision_lower_95"]
    )
    gates["false_positive_rate"] = (
        fpr is not None
        and fpr["upper"]
        <= thresholds["max_false_positive_rate_upper_95"]
    )
    gates["false_negative_rate"] = (
        fnr is not None
        and fnr["upper"]
        <= thresholds["max_false_negative_rate_upper_95"]
    )
    gates["false_positive_dollars"] = (
        metrics["dollars"]["false_positive_dollar_share"]
        <= thresholds["max_false_positive_dollar_share"]
    )
    gates["false_negative_dollars"] = (
        metrics["dollars"]["false_negative_dollar_share"]
        <= thresholds["max_false_negative_dollar_share"]
    )
    gates["calibration"] = (
        calibration is not None
        and calibration["ece"] <= thresholds["max_ece"]
    )
    gates["unsupported_auto"] = (
        unsupported_auto
        <= thresholds["max_unsupported_auto_decisions"]
    )
    gates["incumbent_leakage"] = (
        incumbent_leakage
        <= thresholds["max_incumbent_leakage_cents"]
    )
    gates["duplicate_leakage"] = (
        duplicate_leakage
        <= thresholds["max_duplicate_leakage_cents"]
    )
    gates["all_strata_targets_met"] = all(
        row["sample_count"]
        >= next(
            item["sample_target"]
            for item in payload["sampling"]["strata"]
            if item["key"] == key
        )
        for key, row in by_stratum.items()
    )

    evidence_gates = {
        "sample_precision_plan",
        "sample_adjudicated",
        "sample_positive",
        "sample_negative",
        "dual_review_size",
        "dual_review_positive",
        "dual_review_negative",
        "all_strata_targets_met",
    }
    hard_integrity_gates = {
        "unsupported_auto",
        "incumbent_leakage",
        "duplicate_leakage",
    }
    failed = {name for name, passed in gates.items() if not passed}
    if not failed:
        status = "AUDIT_QUALITY_PROVEN"
    elif failed & hard_integrity_gates:
        status = "QUALITY_GATE_FAILED"
    elif failed & evidence_gates:
        status = "INSUFFICIENT_EVIDENCE"
    else:
        status = "QUALITY_GATE_FAILED"

    return {
        "protocol_id": payload["protocol_id"],
        "population_hash": payload["population"]["population_hash"],
        "sample_hash": payload["population"]["sample_hash"],
        "truth_manifest_hash": payload["population"]["truth_manifest_hash"],
        "recoveryos_output_hash": payload["population"][
            "recoveryos_output_hash"
        ],
        "status": status,
        "metrics": metrics,
        "gates": gates,
        "failed_gates": sorted(
            name for name, passed in gates.items() if not passed
        ),
        "claim_boundary": policy["claim_boundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="freight/AUDIT_ACCEPTANCE_POLICY_V2.json",
    )
    parser.add_argument("--pilot", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    policy = _load(args.policy)
    payload = _load(args.pilot)
    errors = validate_pilot(payload, policy)
    if errors:
        result = {"status": "INVALID_METHOD", "errors": errors}
    else:
        result = build_report(payload, policy)
    raw = json.dumps(result, indent=2, sort_keys=True)
    print(raw)
    if args.output:
        Path(args.output).write_text(raw + "\n", encoding="utf-8")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
