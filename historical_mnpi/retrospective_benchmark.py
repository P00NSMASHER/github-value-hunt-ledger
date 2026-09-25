"""Deterministic retrospective benchmark harness.

Step 15 evaluates historical surveillance features without using evaluation
labels for fitting and without bypassing Step-14 point-in-time controls.
Scoring is transparent, deterministic, and research-only. It does not authorize
live alerting, live surveillance, trading, or order generation.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Iterable

from .point_in_time import (
    PointInTimeFeatureSnapshot,
    WalkForwardWindow,
    cutoff_sort_key,
)
from .source_registry import USAGE_SCOPE, canonical_hash
from .surveillance_features import TradeReleaseRelation


class HistoricalOutcomeLabel(str, Enum):
    POSITIVE_CASE = "POSITIVE_CASE"
    NEGATIVE_CONTROL = "NEGATIVE_CONTROL"


@dataclass(frozen=True)
class RetrospectiveScoringPolicy:
    policy_id: str
    pre_release_exact_weight: int = 4
    pre_release_coarse_weight: int = 2
    repeated_trader_weight: int = 2
    issuer_breadth_weight: int = 1
    large_notional_weight: int = 1
    large_notional_threshold: str = "100000"
    max_repeat_credit: int = 3
    live_use_allowed: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("policy_id is required")
        for value in (
            self.pre_release_exact_weight,
            self.pre_release_coarse_weight,
            self.repeated_trader_weight,
            self.issuer_breadth_weight,
            self.large_notional_weight,
            self.max_repeat_credit,
        ):
            if value < 0:
                raise ValueError("policy weights/caps must be non-negative")
        threshold = Decimal(self.large_notional_threshold)
        if not threshold.is_finite() or threshold < 0:
            raise ValueError("large_notional_threshold must be non-negative")
        if self.live_use_allowed is not False:
            raise ValueError("retrospective scoring cannot enable live use")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "policy_id": self.policy_id,
            "pre_release_exact_weight": self.pre_release_exact_weight,
            "pre_release_coarse_weight": self.pre_release_coarse_weight,
            "repeated_trader_weight": self.repeated_trader_weight,
            "issuer_breadth_weight": self.issuer_breadth_weight,
            "large_notional_weight": self.large_notional_weight,
            "large_notional_threshold": self.large_notional_threshold,
            "max_repeat_credit": self.max_repeat_credit,
            "live_use_allowed": False,
        })


@dataclass(frozen=True)
class RetrospectiveScore:
    snapshot_hash: str
    policy_hash: str
    score: int
    signal_breakdown: tuple[tuple[str, int], ...]
    live_use_allowed: bool = False

    def __post_init__(self) -> None:
        if self.score < 0:
            raise ValueError("retrospective score cannot be negative")
        if self.score != sum(value for _name, value in self.signal_breakdown):
            raise ValueError("score does not equal signal breakdown")
        if tuple(sorted(self.signal_breakdown)) != self.signal_breakdown:
            raise ValueError("signal_breakdown must be sorted")
        if self.live_use_allowed is not False:
            raise ValueError("retrospective score cannot enable live use")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "snapshot_hash": self.snapshot_hash,
            "policy_hash": self.policy_hash,
            "score": self.score,
            "signal_breakdown": [
                [name, value] for name, value in self.signal_breakdown
            ],
            "live_use_allowed": False,
        })


def score_snapshot(
    snapshot: PointInTimeFeatureSnapshot,
    policy: RetrospectiveScoringPolicy,
) -> RetrospectiveScore:
    feature = snapshot.feature
    signals = {}

    if feature.exact_lead_seconds is not None and feature.exact_lead_seconds > 0:
        signals["PRE_RELEASE_EXACT"] = policy.pre_release_exact_weight
    elif feature.trade_release_relation is TradeReleaseRelation.BEFORE_RELEASE:
        signals["PRE_RELEASE_COARSE"] = policy.pre_release_coarse_weight

    repeat_count = max(0, feature.trader_event_count - 1)
    repeat_credit = min(repeat_count, policy.max_repeat_credit)
    if repeat_credit:
        signals["REPEATED_TRADER_EVENTS"] = (
            repeat_credit * policy.repeated_trader_weight
        )

    if feature.issuer_trader_count > 1:
        signals["ISSUER_NETWORK_BREADTH"] = (
            (feature.issuer_trader_count - 1)
            * policy.issuer_breadth_weight
        )

    if (
        feature.notional is not None
        and Decimal(feature.notional) >= Decimal(policy.large_notional_threshold)
    ):
        signals["LARGE_NOTIONAL"] = policy.large_notional_weight

    breakdown = tuple(sorted(signals.items()))
    return RetrospectiveScore(
        snapshot_hash=snapshot.proof_hash,
        policy_hash=policy.proof_hash,
        score=sum(value for _name, value in breakdown),
        signal_breakdown=breakdown,
        live_use_allowed=False,
    )


@dataclass(frozen=True)
class LabeledHistoricalExample:
    example_id: str
    snapshot: PointInTimeFeatureSnapshot
    label: HistoricalOutcomeLabel

    def __post_init__(self) -> None:
        if not self.example_id.strip():
            raise ValueError("example_id is required")
        if self.snapshot.live_use_allowed is not False:
            raise ValueError("example snapshot must be historical-only")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "example_id": self.example_id,
            "snapshot_hash": self.snapshot.proof_hash,
            "label": self.label.value,
        })


@dataclass(frozen=True)
class ThresholdFitReceipt:
    policy_hash: str
    threshold: int
    train_example_hashes: tuple[str, ...]
    candidate_thresholds: tuple[int, ...]
    balanced_accuracy: str
    live_use_allowed: bool = False

    def __post_init__(self) -> None:
        if self.threshold < 0:
            raise ValueError("threshold cannot be negative")
        if not self.train_example_hashes:
            raise ValueError("threshold fit requires training examples")
        if tuple(sorted(set(self.train_example_hashes))) != (
            self.train_example_hashes
        ):
            raise ValueError("train_example_hashes must be unique and sorted")
        if tuple(sorted(set(self.candidate_thresholds))) != (
            self.candidate_thresholds
        ):
            raise ValueError("candidate_thresholds must be unique and sorted")
        if self.live_use_allowed is not False:
            raise ValueError("threshold receipt cannot enable live use")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "policy_hash": self.policy_hash,
            "threshold": self.threshold,
            "train_example_hashes": list(self.train_example_hashes),
            "candidate_thresholds": list(self.candidate_thresholds),
            "balanced_accuracy": self.balanced_accuracy,
            "live_use_allowed": False,
        })


def _ratio(numerator: int, denominator: int) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return Decimal(numerator) / Decimal(denominator)


def _metric_text(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def _confusion(
    examples: tuple[LabeledHistoricalExample, ...],
    *,
    policy: RetrospectiveScoringPolicy,
    threshold: int,
) -> tuple[int, int, int, int]:
    tp = tn = fp = fn = 0
    for example in examples:
        predicted_positive = score_snapshot(
            example.snapshot,
            policy,
        ).score >= threshold
        actual_positive = example.label is HistoricalOutcomeLabel.POSITIVE_CASE
        if predicted_positive and actual_positive:
            tp += 1
        elif predicted_positive and not actual_positive:
            fp += 1
        elif not predicted_positive and actual_positive:
            fn += 1
        else:
            tn += 1
    return tp, tn, fp, fn


def _balanced_accuracy(tp: int, tn: int, fp: int, fn: int) -> Decimal:
    sensitivity = _ratio(tp, tp + fn)
    specificity = _ratio(tn, tn + fp)
    return (sensitivity + specificity) / Decimal(2)


def fit_threshold_on_train(
    examples: Iterable[LabeledHistoricalExample],
    *,
    policy: RetrospectiveScoringPolicy,
) -> ThresholdFitReceipt:
    train = tuple(sorted(examples, key=lambda item: item.example_id))
    if not train:
        raise ValueError("training set cannot be empty")
    labels = {item.label for item in train}
    if labels != {
        HistoricalOutcomeLabel.POSITIVE_CASE,
        HistoricalOutcomeLabel.NEGATIVE_CONTROL,
    }:
        raise ValueError("training set must contain both outcome classes")

    scores = tuple(
        score_snapshot(item.snapshot, policy).score for item in train
    )
    candidate_thresholds = tuple(sorted(set(
        (0,) + scores + tuple(value + 1 for value in scores)
    )))
    best = None
    for threshold in candidate_thresholds:
        tp, tn, fp, fn = _confusion(
            train,
            policy=policy,
            threshold=threshold,
        )
        balanced = _balanced_accuracy(tp, tn, fp, fn)
        candidate = (balanced, threshold)
        if best is None or candidate > best:
            best = candidate
    assert best is not None
    balanced, threshold = best
    return ThresholdFitReceipt(
        policy_hash=policy.proof_hash,
        threshold=threshold,
        train_example_hashes=tuple(sorted(
            item.proof_hash for item in train
        )),
        candidate_thresholds=candidate_thresholds,
        balanced_accuracy=_metric_text(balanced),
        live_use_allowed=False,
    )


@dataclass(frozen=True)
class HoldoutEvaluationReceipt:
    policy_hash: str
    threshold_fit_hash: str
    holdout_example_hashes: tuple[str, ...]
    true_positive: int
    true_negative: int
    false_positive: int
    false_negative: int
    sensitivity: str
    specificity: str
    precision: str
    balanced_accuracy: str
    live_use_allowed: bool = False

    def __post_init__(self) -> None:
        for value in (
            self.true_positive,
            self.true_negative,
            self.false_positive,
            self.false_negative,
        ):
            if value < 0:
                raise ValueError("confusion counts cannot be negative")
        if self.live_use_allowed is not False:
            raise ValueError("holdout evaluation cannot enable live use")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "policy_hash": self.policy_hash,
            "threshold_fit_hash": self.threshold_fit_hash,
            "holdout_example_hashes": list(self.holdout_example_hashes),
            "true_positive": self.true_positive,
            "true_negative": self.true_negative,
            "false_positive": self.false_positive,
            "false_negative": self.false_negative,
            "sensitivity": self.sensitivity,
            "specificity": self.specificity,
            "precision": self.precision,
            "balanced_accuracy": self.balanced_accuracy,
            "live_use_allowed": False,
        })


def evaluate_holdout(
    examples: Iterable[LabeledHistoricalExample],
    *,
    policy: RetrospectiveScoringPolicy,
    threshold_fit: ThresholdFitReceipt,
) -> HoldoutEvaluationReceipt:
    holdout = tuple(sorted(examples, key=lambda item: item.example_id))
    if not holdout:
        raise ValueError("holdout set cannot be empty")
    if threshold_fit.policy_hash != policy.proof_hash:
        raise ValueError("threshold fit/policy mismatch")
    holdout_hashes = {item.proof_hash for item in holdout}
    if holdout_hashes.intersection(threshold_fit.train_example_hashes):
        raise ValueError("holdout examples overlap threshold-fit training set")

    tp, tn, fp, fn = _confusion(
        holdout,
        policy=policy,
        threshold=threshold_fit.threshold,
    )
    return HoldoutEvaluationReceipt(
        policy_hash=policy.proof_hash,
        threshold_fit_hash=threshold_fit.proof_hash,
        holdout_example_hashes=tuple(sorted(holdout_hashes)),
        true_positive=tp,
        true_negative=tn,
        false_positive=fp,
        false_negative=fn,
        sensitivity=_metric_text(_ratio(tp, tp + fn)),
        specificity=_metric_text(_ratio(tn, tn + fp)),
        precision=_metric_text(_ratio(tp, tp + fp)),
        balanced_accuracy=_metric_text(
            _balanced_accuracy(tp, tn, fp, fn)
        ),
        live_use_allowed=False,
    )


@dataclass(frozen=True)
class WalkForwardBenchmarkReceipt:
    window_hash: str
    policy_hash: str
    threshold_fit_hash: str
    holdout_evaluation_hash: str
    live_use_allowed: bool = False

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "window_hash": self.window_hash,
            "policy_hash": self.policy_hash,
            "threshold_fit_hash": self.threshold_fit_hash,
            "holdout_evaluation_hash": self.holdout_evaluation_hash,
            "live_use_allowed": False,
        })


def run_walk_forward_benchmark(
    *,
    window: WalkForwardWindow,
    train_examples: Iterable[LabeledHistoricalExample],
    evaluation_examples: Iterable[LabeledHistoricalExample],
    policy: RetrospectiveScoringPolicy,
) -> tuple[
    ThresholdFitReceipt,
    HoldoutEvaluationReceipt,
    WalkForwardBenchmarkReceipt,
]:
    train = tuple(train_examples)
    evaluation = tuple(evaluation_examples)
    train_allowed = set(window.train_cluster_hashes)
    evaluation_allowed = set(window.evaluation_cluster_hashes)

    for example in train:
        if example.snapshot.feature.cluster_proof_hash not in train_allowed:
            raise ValueError("training example is outside walk-forward train set")
        if cutoff_sort_key(example.snapshot.cutoff) > cutoff_sort_key(
            window.train_cutoff
        ):
            raise ValueError("training snapshot reads beyond train cutoff")

    for example in evaluation:
        if (
            example.snapshot.feature.cluster_proof_hash
            not in evaluation_allowed
        ):
            raise ValueError(
                "evaluation example is outside walk-forward evaluation set"
            )
        if cutoff_sort_key(example.snapshot.cutoff) > cutoff_sort_key(
            window.evaluation_cutoff
        ):
            raise ValueError("evaluation snapshot reads beyond evaluation cutoff")

    fit = fit_threshold_on_train(train, policy=policy)
    holdout = evaluate_holdout(
        evaluation,
        policy=policy,
        threshold_fit=fit,
    )
    receipt = WalkForwardBenchmarkReceipt(
        window_hash=window.proof_hash,
        policy_hash=policy.proof_hash,
        threshold_fit_hash=fit.proof_hash,
        holdout_evaluation_hash=holdout.proof_hash,
        live_use_allowed=False,
    )
    return fit, holdout, receipt


__all__ = [
    "HistoricalOutcomeLabel",
    "HoldoutEvaluationReceipt",
    "LabeledHistoricalExample",
    "RetrospectiveScore",
    "RetrospectiveScoringPolicy",
    "ThresholdFitReceipt",
    "WalkForwardBenchmarkReceipt",
    "evaluate_holdout",
    "fit_threshold_on_train",
    "run_walk_forward_benchmark",
    "score_snapshot",
]
