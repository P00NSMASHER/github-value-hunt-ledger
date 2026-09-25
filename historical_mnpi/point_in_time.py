"""Point-in-time controls for historical MNPI surveillance research.

Step 14 prevents future information from entering graph-aware feature snapshots.
A cutoff can be an exact timestamp or an end-of-day date. Exact intraday cutoffs
exclude date-only/range records ending on that same day because their full-day
content would not yet be safely available.

No legal outcome or later enforcement result is used in these controls.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Iterable

from .economic_dedup import (
    EconomicTransactionCluster,
    EconomicTransactionSignature,
)
from .event_model import EventRegistry
from .source_registry import USAGE_SCOPE, canonical_hash
from .surveillance_features import (
    HistoricalSurveillanceFeatures,
    build_surveillance_features,
)
from .surveillance_graph import build_historical_surveillance_graph
from .transaction_model import TimePrecision


class CutoffPrecision(str, Enum):
    EXACT_TIMESTAMP = "EXACT_TIMESTAMP"
    END_OF_DAY = "END_OF_DAY"


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class PointInTimeCutoff:
    precision: CutoffPrecision
    timestamp: str | None = None
    date_value: str | None = None

    def __post_init__(self) -> None:
        if self.precision is CutoffPrecision.EXACT_TIMESTAMP:
            if self.timestamp is None or self.date_value is not None:
                raise ValueError(
                    "exact cutoff requires timestamp and no date_value"
                )
            _utc(self.timestamp)
        elif self.precision is CutoffPrecision.END_OF_DAY:
            if self.date_value is None or self.timestamp is not None:
                raise ValueError(
                    "end-of-day cutoff requires date_value and no timestamp"
                )
            date.fromisoformat(self.date_value)

    @property
    def cutoff_date(self) -> date:
        if self.precision is CutoffPrecision.EXACT_TIMESTAMP:
            return _utc(self.timestamp or "").date()
        return date.fromisoformat(self.date_value or "")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "precision": self.precision.value,
            "timestamp_utc": (
                _utc(self.timestamp or "").isoformat()
                if self.timestamp is not None
                else None
            ),
            "date_value": self.date_value,
        })


def signature_available_by(
    signature: EconomicTransactionSignature,
    cutoff: PointInTimeCutoff,
) -> bool:
    if cutoff.precision is CutoffPrecision.END_OF_DAY:
        day = cutoff.cutoff_date
        if signature.time_precision is TimePrecision.EXACT_TIMESTAMP:
            return _utc(signature.trade_timestamp or "").date() <= day
        if signature.time_precision is TimePrecision.DATE_ONLY:
            return date.fromisoformat(signature.trade_date or "") <= day
        return date.fromisoformat(
            signature.trade_date_range_end or ""
        ) <= day

    instant = _utc(cutoff.timestamp or "")
    if signature.time_precision is TimePrecision.EXACT_TIMESTAMP:
        return _utc(signature.trade_timestamp or "") <= instant

    # A date-only or date-range row is treated as fully known only after that
    # calendar day has completed. Same-day inclusion at an intraday cutoff would
    # create a future-read risk.
    if signature.time_precision is TimePrecision.DATE_ONLY:
        return date.fromisoformat(signature.trade_date or "") < instant.date()
    return date.fromisoformat(
        signature.trade_date_range_end or ""
    ) < instant.date()


def cluster_available_by(
    cluster: EconomicTransactionCluster,
    cutoff: PointInTimeCutoff,
) -> bool:
    return all(
        signature_available_by(signature, cutoff)
        for signature in cluster.signatures
    )


@dataclass(frozen=True)
class PointInTimeFeatureSnapshot:
    target_cluster_id: str
    cutoff: PointInTimeCutoff
    feature: HistoricalSurveillanceFeatures
    eligible_cluster_hashes: tuple[str, ...]
    excluded_future_cluster_hashes: tuple[str, ...]
    graph_proof_hash: str
    live_use_allowed: bool = False

    def __post_init__(self) -> None:
        if self.feature.cluster_id != self.target_cluster_id:
            raise ValueError("target cluster/feature mismatch")
        if self.feature.graph_proof_hash != self.graph_proof_hash:
            raise ValueError("feature/graph proof mismatch")
        if tuple(sorted(set(self.eligible_cluster_hashes))) != (
            self.eligible_cluster_hashes
        ):
            raise ValueError("eligible_cluster_hashes must be sorted and unique")
        if tuple(sorted(set(self.excluded_future_cluster_hashes))) != (
            self.excluded_future_cluster_hashes
        ):
            raise ValueError(
                "excluded_future_cluster_hashes must be sorted and unique"
            )
        if set(self.eligible_cluster_hashes).intersection(
            self.excluded_future_cluster_hashes
        ):
            raise ValueError("eligible/future cluster sets overlap")
        if self.live_use_allowed is not False:
            raise ValueError("point-in-time historical snapshot cannot enable live use")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "target_cluster_id": self.target_cluster_id,
            "cutoff_hash": self.cutoff.proof_hash,
            "feature_hash": self.feature.proof_hash,
            "eligible_cluster_hashes": list(self.eligible_cluster_hashes),
            "excluded_future_cluster_hashes": list(
                self.excluded_future_cluster_hashes
            ),
            "graph_proof_hash": self.graph_proof_hash,
            "live_use_allowed": False,
        })


def build_point_in_time_snapshot(
    target: EconomicTransactionCluster,
    *,
    clusters: Iterable[EconomicTransactionCluster],
    events: EventRegistry,
    cutoff: PointInTimeCutoff,
) -> PointInTimeFeatureSnapshot:
    cluster_tuple = tuple(sorted(
        clusters,
        key=lambda item: item.cluster_id,
    ))
    by_id = {item.cluster_id: item for item in cluster_tuple}
    if target.cluster_id not in by_id:
        raise ValueError("target cluster is not in supplied corpus")
    if by_id[target.cluster_id].proof_hash != target.proof_hash:
        raise ValueError("target cluster content does not match supplied corpus")

    eligible = tuple(
        item for item in cluster_tuple
        if cluster_available_by(item, cutoff)
    )
    excluded = tuple(
        item for item in cluster_tuple
        if not cluster_available_by(item, cutoff)
    )
    if target.cluster_id not in {item.cluster_id for item in eligible}:
        raise ValueError("target cluster is not available by point-in-time cutoff")

    graph = build_historical_surveillance_graph(eligible)
    feature = build_surveillance_features(
        target,
        graph=graph,
        events=events,
    )
    return PointInTimeFeatureSnapshot(
        target_cluster_id=target.cluster_id,
        cutoff=cutoff,
        feature=feature,
        eligible_cluster_hashes=tuple(sorted(
            item.proof_hash for item in eligible
        )),
        excluded_future_cluster_hashes=tuple(sorted(
            item.proof_hash for item in excluded
        )),
        graph_proof_hash=graph.proof_hash,
        live_use_allowed=False,
    )


@dataclass(frozen=True)
class PointInTimeControlPlan:
    cutoffs: tuple[PointInTimeCutoff, ...]

    def __post_init__(self) -> None:
        if not self.cutoffs:
            raise ValueError("point-in-time control plan requires cutoffs")
        hashes = [item.proof_hash for item in self.cutoffs]
        if len(set(hashes)) != len(hashes):
            raise ValueError("duplicate point-in-time cutoff")
        keys = [cutoff_sort_key(item) for item in self.cutoffs]
        if keys != sorted(keys):
            raise ValueError("point-in-time cutoffs must be chronological")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "cutoff_hashes": [item.proof_hash for item in self.cutoffs],
        })


def cutoff_sort_key(cutoff: PointInTimeCutoff) -> tuple[date, int, str]:
    if cutoff.precision is CutoffPrecision.EXACT_TIMESTAMP:
        instant = _utc(cutoff.timestamp or "")
        return (instant.date(), 0, instant.isoformat())
    day = cutoff.cutoff_date
    return (day, 1, day.isoformat())


@dataclass(frozen=True)
class WalkForwardWindow:
    train_cutoff: PointInTimeCutoff
    evaluation_cutoff: PointInTimeCutoff
    train_cluster_hashes: tuple[str, ...]
    evaluation_cluster_hashes: tuple[str, ...]

    def __post_init__(self) -> None:
        if cutoff_sort_key(self.evaluation_cutoff) <= cutoff_sort_key(
            self.train_cutoff
        ):
            raise ValueError("evaluation cutoff must follow train cutoff")
        if set(self.train_cluster_hashes).intersection(
            self.evaluation_cluster_hashes
        ):
            raise ValueError("walk-forward train/evaluation sets overlap")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "scope": USAGE_SCOPE,
            "train_cutoff_hash": self.train_cutoff.proof_hash,
            "evaluation_cutoff_hash": self.evaluation_cutoff.proof_hash,
            "train_cluster_hashes": list(self.train_cluster_hashes),
            "evaluation_cluster_hashes": list(self.evaluation_cluster_hashes),
        })


def build_walk_forward_window(
    clusters: Iterable[EconomicTransactionCluster],
    *,
    train_cutoff: PointInTimeCutoff,
    evaluation_cutoff: PointInTimeCutoff,
) -> WalkForwardWindow:
    if cutoff_sort_key(evaluation_cutoff) <= cutoff_sort_key(train_cutoff):
        raise ValueError("evaluation cutoff must follow train cutoff")

    cluster_tuple = tuple(clusters)
    train = tuple(
        item for item in cluster_tuple
        if cluster_available_by(item, train_cutoff)
    )
    evaluation = tuple(
        item for item in cluster_tuple
        if (
            not cluster_available_by(item, train_cutoff)
            and cluster_available_by(item, evaluation_cutoff)
        )
    )
    return WalkForwardWindow(
        train_cutoff=train_cutoff,
        evaluation_cutoff=evaluation_cutoff,
        train_cluster_hashes=tuple(sorted(
            item.proof_hash for item in train
        )),
        evaluation_cluster_hashes=tuple(sorted(
            item.proof_hash for item in evaluation
        )),
    )


__all__ = [
    "CutoffPrecision",
    "PointInTimeControlPlan",
    "PointInTimeCutoff",
    "PointInTimeFeatureSnapshot",
    "WalkForwardWindow",
    "build_point_in_time_snapshot",
    "build_walk_forward_window",
    "cluster_available_by",
    "cutoff_sort_key",
    "signature_available_by",
]
