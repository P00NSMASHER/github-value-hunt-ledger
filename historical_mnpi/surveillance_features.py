"""Leakage-conscious retrospective surveillance features.

Step 13 derives deterministic historical surveillance features from the Step-12
relationship graph, Step-11 economic clusters, and Step-6 public-release
boundaries. It intentionally excludes later legal outcomes and enforcement
results from the feature vector.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Iterable

from .economic_dedup import (
    EconomicTransactionCluster,
    EconomicTransactionSignature,
)
from .event_model import BoundaryPrecision, EventRegistry, InformationEvent
from .source_registry import USAGE_SCOPE, canonical_hash
from .surveillance_graph import HistoricalSurveillanceGraph
from .transaction_model import InstrumentType, TimePrecision, TradeSide


class TradeReleaseRelation(str, Enum):
    BEFORE_RELEASE = "BEFORE_RELEASE"
    SAME_DAY_OR_OVERLAP = "SAME_DAY_OR_OVERLAP"
    AFTER_RELEASE = "AFTER_RELEASE"
    UNKNOWN = "UNKNOWN"


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).astimezone(timezone.utc)


def _signature_date_interval(
    signature: EconomicTransactionSignature,
) -> tuple[date, date]:
    if signature.time_precision is TimePrecision.EXACT_TIMESTAMP:
        day = _utc(signature.trade_timestamp or "").date()
        return day, day
    if signature.time_precision is TimePrecision.DATE_ONLY:
        day = date.fromisoformat(signature.trade_date or "")
        return day, day
    return (
        date.fromisoformat(signature.trade_date_range_start or ""),
        date.fromisoformat(signature.trade_date_range_end or ""),
    )


def _event_date_interval(event: InformationEvent) -> tuple[date, date]:
    boundary = event.public_release
    if boundary.precision is BoundaryPrecision.EXACT_TIMESTAMP:
        day = _utc(boundary.timestamp or "").date()
        return day, day
    if boundary.precision is BoundaryPrecision.DATE_ONLY:
        day = date.fromisoformat(boundary.date_value or "")
        return day, day
    return (
        date.fromisoformat(boundary.date_range_start or ""),
        date.fromisoformat(boundary.date_range_end or ""),
    )


def _consensus(
    signatures: tuple[EconomicTransactionSignature, ...],
    field_name: str,
):
    values = {
        getattr(item, field_name)
        for item in signatures
        if getattr(item, field_name) is not None
    }
    if len(values) == 1:
        return next(iter(values))
    return None


def _consensus_enum(
    signatures: tuple[EconomicTransactionSignature, ...],
    field_name: str,
    unknown,
):
    values = {
        getattr(item, field_name)
        for item in signatures
        if getattr(item, field_name) is not unknown
    }
    if len(values) == 1:
        return next(iter(values))
    return unknown


def _exact_trade_timestamp(
    signatures: tuple[EconomicTransactionSignature, ...],
) -> str | None:
    if not signatures:
        return None
    instants = {
        _utc(item.trade_timestamp or "").isoformat()
        for item in signatures
        if item.time_precision is TimePrecision.EXACT_TIMESTAMP
    }
    if len(instants) == 1 and all(
        item.time_precision is TimePrecision.EXACT_TIMESTAMP
        for item in signatures
    ):
        return next(iter(instants))
    return None


@dataclass(frozen=True)
class HistoricalSurveillanceFeatures:
    cluster_id: str
    cluster_proof_hash: str
    trader_entity_id: str
    issuer_entity_id: str
    event_id: str
    graph_proof_hash: str
    source_row_count: int
    trader_event_count: int
    issuer_trader_count: int
    connected_component_size: int
    instrument_type: InstrumentType
    side: TradeSide
    exact_trade_timestamp_utc: str | None
    trade_window_start: str
    trade_window_end: str
    public_release_window_start: str
    public_release_window_end: str
    exact_lead_seconds: int | None
    lead_days_min: int
    lead_days_max: int
    trade_release_relation: TradeReleaseRelation
    currency: str | None
    quantity: str | None
    execution_price: str | None
    notional: str | None
    multi_source_corroboration: bool
    live_use_allowed: bool = False

    def __post_init__(self) -> None:
        if not self.cluster_id.startswith("economic:"):
            raise ValueError("invalid cluster_id")
        if self.source_row_count < 1:
            raise ValueError("source_row_count must be positive")
        for value in (
            self.trader_event_count,
            self.issuer_trader_count,
            self.connected_component_size,
        ):
            if value < 0:
                raise ValueError("graph count cannot be negative")
        if self.live_use_allowed is not False:
            raise ValueError("historical surveillance features cannot enable live use")
        date.fromisoformat(self.trade_window_start)
        date.fromisoformat(self.trade_window_end)
        date.fromisoformat(self.public_release_window_start)
        date.fromisoformat(self.public_release_window_end)

    @property
    def feature_body(self) -> dict:
        return {
            "schema": 1,
            "scope": USAGE_SCOPE,
            "cluster_id": self.cluster_id,
            "cluster_proof_hash": self.cluster_proof_hash,
            "trader_entity_id": self.trader_entity_id,
            "issuer_entity_id": self.issuer_entity_id,
            "event_id": self.event_id,
            "graph_proof_hash": self.graph_proof_hash,
            "source_row_count": self.source_row_count,
            "trader_event_count": self.trader_event_count,
            "issuer_trader_count": self.issuer_trader_count,
            "connected_component_size": self.connected_component_size,
            "instrument_type": self.instrument_type.value,
            "side": self.side.value,
            "exact_trade_timestamp_utc": self.exact_trade_timestamp_utc,
            "trade_window_start": self.trade_window_start,
            "trade_window_end": self.trade_window_end,
            "public_release_window_start": self.public_release_window_start,
            "public_release_window_end": self.public_release_window_end,
            "exact_lead_seconds": self.exact_lead_seconds,
            "lead_days_min": self.lead_days_min,
            "lead_days_max": self.lead_days_max,
            "trade_release_relation": self.trade_release_relation.value,
            "currency": self.currency,
            "quantity": self.quantity,
            "execution_price": self.execution_price,
            "notional": self.notional,
            "multi_source_corroboration": self.multi_source_corroboration,
            "live_use_allowed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self.feature_body)


def build_surveillance_features(
    cluster: EconomicTransactionCluster,
    *,
    graph: HistoricalSurveillanceGraph,
    events: EventRegistry,
) -> HistoricalSurveillanceFeatures:
    if cluster.proof_hash not in graph.cluster_hashes:
        raise ValueError("economic cluster is not represented in surveillance graph")

    signatures = cluster.signatures
    trader_ids = {item.trader_entity_id for item in signatures}
    issuer_ids = {item.issuer_entity_id for item in signatures}
    event_ids = {item.event_id for item in signatures}
    if len(trader_ids) != 1 or len(issuer_ids) != 1 or len(event_ids) != 1:
        raise ValueError("cluster identities/event are not unique")

    trader_id = next(iter(trader_ids))
    issuer_id = next(iter(issuer_ids))
    event_id = next(iter(event_ids))
    event = events.get(event_id)

    trade_intervals = tuple(_signature_date_interval(item) for item in signatures)
    trade_start = min(item[0] for item in trade_intervals)
    trade_end = max(item[1] for item in trade_intervals)
    release_start, release_end = _event_date_interval(event)

    exact_trade = _exact_trade_timestamp(signatures)
    exact_lead_seconds = None
    if (
        exact_trade is not None
        and event.public_release.precision is BoundaryPrecision.EXACT_TIMESTAMP
    ):
        seconds = int(
            (
                _utc(event.public_release.timestamp or "")
                - _utc(exact_trade)
            ).total_seconds()
        )
        exact_lead_seconds = seconds

    lead_days_min = (release_start - trade_end).days
    lead_days_max = (release_end - trade_start).days
    if trade_end < release_start:
        relation = TradeReleaseRelation.BEFORE_RELEASE
    elif trade_start > release_end:
        relation = TradeReleaseRelation.AFTER_RELEASE
    else:
        relation = TradeReleaseRelation.SAME_DAY_OR_OVERLAP

    quantity = _consensus(signatures, "quantity")
    execution_price = _consensus(signatures, "execution_price")
    notional = None
    if quantity is not None and execution_price is not None:
        notional = format(
            (Decimal(quantity) * Decimal(execution_price)).normalize(),
            "f",
        )

    cluster_node = graph.cluster_node_id(cluster.cluster_id)
    return HistoricalSurveillanceFeatures(
        cluster_id=cluster.cluster_id,
        cluster_proof_hash=cluster.proof_hash,
        trader_entity_id=trader_id,
        issuer_entity_id=issuer_id,
        event_id=event_id,
        graph_proof_hash=graph.proof_hash,
        source_row_count=len(signatures),
        trader_event_count=graph.trader_event_count(trader_id),
        issuer_trader_count=graph.issuer_trader_count(issuer_id),
        connected_component_size=len(graph.connected_component(cluster_node)),
        instrument_type=_consensus_enum(
            signatures,
            "instrument_type",
            InstrumentType.UNKNOWN,
        ),
        side=_consensus_enum(
            signatures,
            "side",
            TradeSide.UNKNOWN,
        ),
        exact_trade_timestamp_utc=exact_trade,
        trade_window_start=trade_start.isoformat(),
        trade_window_end=trade_end.isoformat(),
        public_release_window_start=release_start.isoformat(),
        public_release_window_end=release_end.isoformat(),
        exact_lead_seconds=exact_lead_seconds,
        lead_days_min=lead_days_min,
        lead_days_max=lead_days_max,
        trade_release_relation=relation,
        currency=_consensus(signatures, "currency"),
        quantity=quantity,
        execution_price=execution_price,
        notional=notional,
        multi_source_corroboration=len(signatures) > 1,
        live_use_allowed=False,
    )


def build_feature_set(
    clusters: Iterable[EconomicTransactionCluster],
    *,
    graph: HistoricalSurveillanceGraph,
    events: EventRegistry,
) -> tuple[HistoricalSurveillanceFeatures, ...]:
    return tuple(sorted(
        (
            build_surveillance_features(
                cluster,
                graph=graph,
                events=events,
            )
            for cluster in clusters
        ),
        key=lambda item: item.cluster_id,
    ))


__all__ = [
    "HistoricalSurveillanceFeatures",
    "TradeReleaseRelation",
    "build_feature_set",
    "build_surveillance_features",
]
