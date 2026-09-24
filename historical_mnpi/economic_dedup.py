"""Conservative economic-transaction deduplication primitives.

Step 11.1 creates source-independent signatures for already-approved historical
rows. It does not merge, delete, or rewrite source-backed transactions.

Exact deduplication is intentionally strict. A row pair is an exact economic
match only when durable trader/issuer identity, information event, exact trade
instant, instrument, side, quantity, and execution price agree. Coarser temporal
precision or missing economics can produce only POSSIBLE_MATCH or
INSUFFICIENT_INFORMATION.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from .review_queue import (
    HistoricalReviewDecision,
    ReviewDecision,
    ReviewQueueItem,
)
from .source_registry import canonical_hash
from .transaction_model import InstrumentType, TimePrecision, TradeSide


class DedupMatchState(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    DISTINCT = "DISTINCT"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


def _decimal_key(value: str | None) -> str | None:
    if value is None:
        return None
    parsed = Decimal(value)
    normalized = format(parsed.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def _timestamp_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class EconomicTransactionSignature:
    normalized_row_hash: str
    review_item_hash: str
    trader_entity_id: str
    issuer_entity_id: str
    event_id: str
    instrument_type: InstrumentType
    side: TradeSide
    time_precision: TimePrecision
    trade_timestamp: str | None = None
    trade_date: str | None = None
    trade_date_range_start: str | None = None
    trade_date_range_end: str | None = None
    currency: str | None = None
    quantity: str | None = None
    execution_price: str | None = None
    option_strike: str | None = None
    option_expiry: str | None = None

    def __post_init__(self) -> None:
        if len(self.normalized_row_hash) != 64:
            raise ValueError("normalized_row_hash must be SHA-256")
        if len(self.review_item_hash) != 64:
            raise ValueError("review_item_hash must be SHA-256")
        if not self.trader_entity_id:
            raise ValueError("trader_entity_id is required")
        if not self.issuer_entity_id:
            raise ValueError("issuer_entity_id is required")
        if not self.event_id:
            raise ValueError("event_id is required")

        present = sum(
            value is not None
            for value in (
                self.trade_timestamp,
                self.trade_date,
                self.trade_date_range_start,
                self.trade_date_range_end,
            )
        )
        if self.time_precision is TimePrecision.EXACT_TIMESTAMP:
            if self.trade_timestamp is None or present != 1:
                raise ValueError("exact signature requires only trade_timestamp")
            _timestamp_utc(self.trade_timestamp)
        elif self.time_precision is TimePrecision.DATE_ONLY:
            if self.trade_date is None or present != 1:
                raise ValueError("date-only signature requires only trade_date")
            date.fromisoformat(self.trade_date)
        elif self.time_precision is TimePrecision.DATE_RANGE:
            if (
                self.trade_date_range_start is None
                or self.trade_date_range_end is None
                or present != 2
            ):
                raise ValueError("date-range signature requires both range bounds")
            start = date.fromisoformat(self.trade_date_range_start)
            end = date.fromisoformat(self.trade_date_range_end)
            if end < start:
                raise ValueError("trade date range end cannot precede start")

        if self.currency is not None:
            object.__setattr__(self, "currency", self.currency.upper())
        for field_name in ("quantity", "execution_price", "option_strike"):
            object.__setattr__(
                self,
                field_name,
                _decimal_key(getattr(self, field_name)),
            )

    @property
    def economic_key_body(self) -> dict:
        return {
            "schema": 1,
            "trader_entity_id": self.trader_entity_id,
            "issuer_entity_id": self.issuer_entity_id,
            "event_id": self.event_id,
            "instrument_type": self.instrument_type.value,
            "side": self.side.value,
            "time_precision": self.time_precision.value,
            "trade_timestamp_utc": (
                _timestamp_utc(self.trade_timestamp).isoformat()
                if self.trade_timestamp is not None
                else None
            ),
            "trade_date": self.trade_date,
            "trade_date_range_start": self.trade_date_range_start,
            "trade_date_range_end": self.trade_date_range_end,
            "currency": self.currency,
            "quantity": self.quantity,
            "execution_price": self.execution_price,
            "option_strike": self.option_strike,
            "option_expiry": self.option_expiry,
        }

    @property
    def economic_key_hash(self) -> str:
        """Source-independent hash. Source row/review hashes are excluded."""
        return canonical_hash(self.economic_key_body)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            **self.economic_key_body,
            "normalized_row_hash": self.normalized_row_hash,
            "review_item_hash": self.review_item_hash,
        })


@dataclass(frozen=True)
class EconomicMatchAssessment:
    left_signature_hash: str
    right_signature_hash: str
    state: DedupMatchState
    agreeing_fields: tuple[str, ...]
    differing_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    reasons: tuple[str, ...]

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "left_signature_hash": self.left_signature_hash,
            "right_signature_hash": self.right_signature_hash,
            "state": self.state.value,
            "agreeing_fields": list(self.agreeing_fields),
            "differing_fields": list(self.differing_fields),
            "missing_fields": list(self.missing_fields),
            "reasons": list(self.reasons),
        })


def build_economic_signature(
    item: ReviewQueueItem,
    decision: HistoricalReviewDecision,
) -> EconomicTransactionSignature:
    item.verify_integrity()
    decision.verify_integrity()
    if decision.decision is not ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH:
        raise ValueError("economic signature requires approved historical row")
    if not decision.research_corpus_eligible:
        raise ValueError("economic signature requires research-corpus eligibility")
    if decision.review_id != item.review_id:
        raise ValueError("review decision/item id mismatch")
    if decision.review_item_hash != item.review_item_hash:
        raise ValueError("review decision/item hash mismatch")
    if decision.normalized_row_hash != item.normalized_row_hash:
        raise ValueError("review decision normalized-row mismatch")
    if item.durable_identity is None:
        raise ValueError("economic signature requires durable identities")
    if decision.durable_identity_hash != item.durable_identity.proof_hash:
        raise ValueError("review decision durable-identity mismatch")
    if item.source_conflict_registry_hash is None:
        raise ValueError("economic signature requires source-conflict snapshot")
    if decision.source_conflict_hash is None:
        raise ValueError("review decision source-conflict proof missing")

    record = item.proposed_record
    return EconomicTransactionSignature(
        normalized_row_hash=item.normalized_row_hash,
        review_item_hash=item.review_item_hash,
        trader_entity_id=item.durable_identity.trader_entity_id,
        issuer_entity_id=item.durable_identity.issuer_entity_id,
        event_id=item.event_id,
        instrument_type=record.instrument_type,
        side=record.side,
        time_precision=record.time_precision,
        trade_timestamp=record.trade_timestamp,
        trade_date=record.trade_date,
        trade_date_range_start=record.trade_date_range_start,
        trade_date_range_end=record.trade_date_range_end,
        currency=record.currency,
        quantity=record.quantity,
        execution_price=record.execution_price,
        option_strike=record.option_strike,
        option_expiry=record.option_expiry,
    )


def _time_relation(
    left: EconomicTransactionSignature,
    right: EconomicTransactionSignature,
) -> tuple[str, bool]:
    if (
        left.time_precision is TimePrecision.EXACT_TIMESTAMP
        and right.time_precision is TimePrecision.EXACT_TIMESTAMP
    ):
        equal = _timestamp_utc(left.trade_timestamp or "") == _timestamp_utc(
            right.trade_timestamp or ""
        )
        return ("EXACT" if equal else "DISJOINT", equal)

    def interval(sig: EconomicTransactionSignature) -> tuple[date, date]:
        if sig.time_precision is TimePrecision.EXACT_TIMESTAMP:
            day = datetime.fromisoformat(
                (sig.trade_timestamp or "").replace("Z", "+00:00")
            ).date()
            return day, day
        if sig.time_precision is TimePrecision.DATE_ONLY:
            day = date.fromisoformat(sig.trade_date or "")
            return day, day
        return (
            date.fromisoformat(sig.trade_date_range_start or ""),
            date.fromisoformat(sig.trade_date_range_end or ""),
        )

    left_start, left_end = interval(left)
    right_start, right_end = interval(right)
    if left_end < right_start or right_end < left_start:
        return "DISJOINT", False
    if (
        left.time_precision is right.time_precision
        and left_start == right_start
        and left_end == right_end
    ):
        return "SAME_COARSE_WINDOW", False
    return "OVERLAP", False


def compare_economic_signatures(
    left: EconomicTransactionSignature,
    right: EconomicTransactionSignature,
) -> EconomicMatchAssessment:
    agreeing = []
    differing = []
    missing = []
    reasons = []

    for field_name in ("trader_entity_id", "issuer_entity_id", "event_id"):
        if getattr(left, field_name) == getattr(right, field_name):
            agreeing.append(field_name)
        else:
            differing.append(field_name)
            reasons.append("IDENTITY_OR_EVENT_MISMATCH:" + field_name)

    if differing:
        return EconomicMatchAssessment(
            left_signature_hash=left.proof_hash,
            right_signature_hash=right.proof_hash,
            state=DedupMatchState.DISTINCT,
            agreeing_fields=tuple(sorted(agreeing)),
            differing_fields=tuple(sorted(differing)),
            missing_fields=(),
            reasons=tuple(sorted(reasons)),
        )

    for field_name in (
        "instrument_type",
        "side",
        "currency",
        "quantity",
        "execution_price",
        "option_strike",
        "option_expiry",
    ):
        lv = getattr(left, field_name)
        rv = getattr(right, field_name)

        if field_name == "instrument_type":
            if lv is InstrumentType.UNKNOWN or rv is InstrumentType.UNKNOWN:
                missing.append(field_name)
                continue
        elif field_name == "side":
            if lv is TradeSide.UNKNOWN or rv is TradeSide.UNKNOWN:
                missing.append(field_name)
                continue
        elif lv is None or rv is None:
            missing.append(field_name)
            continue

        if lv == rv:
            agreeing.append(field_name)
        else:
            differing.append(field_name)
            reasons.append("ECONOMIC_FIELD_MISMATCH:" + field_name)

    relation, exact_time = _time_relation(left, right)
    if relation == "DISJOINT":
        differing.append("trade_time")
        reasons.append("TRADE_TIME_DISJOINT")
    else:
        agreeing.append("trade_time")
        if not exact_time:
            reasons.append("TRADE_TIME_NOT_EXACT")

    if differing:
        state = DedupMatchState.DISTINCT
    else:
        exact_required = {
            "instrument_type",
            "side",
            "quantity",
            "execution_price",
        }
        if exact_time and exact_required.issubset(set(agreeing)):
            state = DedupMatchState.EXACT_MATCH
        else:
            discriminators = {
                "instrument_type",
                "side",
                "quantity",
                "execution_price",
                "option_strike",
                "option_expiry",
            }.intersection(agreeing)
            if discriminators:
                state = DedupMatchState.POSSIBLE_MATCH
            else:
                state = DedupMatchState.INSUFFICIENT_INFORMATION

    return EconomicMatchAssessment(
        left_signature_hash=left.proof_hash,
        right_signature_hash=right.proof_hash,
        state=state,
        agreeing_fields=tuple(sorted(set(agreeing))),
        differing_fields=tuple(sorted(set(differing))),
        missing_fields=tuple(sorted(set(missing))),
        reasons=tuple(sorted(set(reasons))),
    )


class ClusterRegistrationAction(str, Enum):
    NEW_CLUSTER = "NEW_CLUSTER"
    AUTO_JOINED_EXACT = "AUTO_JOINED_EXACT"
    NEW_CLUSTER_REVIEW_REQUIRED = "NEW_CLUSTER_REVIEW_REQUIRED"


@dataclass(frozen=True)
class EconomicTransactionCluster:
    cluster_id: str
    signatures: tuple[EconomicTransactionSignature, ...]

    def __post_init__(self) -> None:
        if not self.cluster_id.startswith("economic:"):
            raise ValueError("cluster_id must use economic: prefix")
        if not self.signatures:
            raise ValueError("economic cluster requires at least one signature")
        proof_hashes = [item.proof_hash for item in self.signatures]
        if len(set(proof_hashes)) != len(proof_hashes):
            raise ValueError("duplicate signature in economic cluster")
        row_hashes = [item.normalized_row_hash for item in self.signatures]
        if len(set(row_hashes)) != len(row_hashes):
            raise ValueError("duplicate normalized row in economic cluster")

    @property
    def member_signature_hashes(self) -> tuple[str, ...]:
        return tuple(sorted(item.proof_hash for item in self.signatures))

    @property
    def normalized_row_hashes(self) -> tuple[str, ...]:
        return tuple(sorted(item.normalized_row_hash for item in self.signatures))

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "cluster_id": self.cluster_id,
            "member_signature_hashes": list(self.member_signature_hashes),
            "normalized_row_hashes": list(self.normalized_row_hashes),
        })


@dataclass(frozen=True)
class DedupReviewCandidate:
    candidate_id: str
    signature_hash: str
    candidate_cluster_id: str
    assessments: tuple[EconomicMatchAssessment, ...]
    reason: str

    def __post_init__(self) -> None:
        if not self.candidate_id.startswith("dedup-review:"):
            raise ValueError("candidate_id must use dedup-review: prefix")
        if not self.candidate_cluster_id.startswith("economic:"):
            raise ValueError("candidate_cluster_id must use economic: prefix")
        if not self.assessments:
            raise ValueError("dedup review candidate requires assessments")
        if not self.reason.strip():
            raise ValueError("dedup review candidate requires reason")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "candidate_id": self.candidate_id,
            "signature_hash": self.signature_hash,
            "candidate_cluster_id": self.candidate_cluster_id,
            "assessment_hashes": sorted(
                item.proof_hash for item in self.assessments
            ),
            "reason": self.reason,
        })


@dataclass(frozen=True)
class EconomicClusterEvent:
    event_id: str
    action: ClusterRegistrationAction
    signature_hash: str
    cluster_id: str
    cluster_proof_hash: str
    review_candidate_hashes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.event_id.startswith("cluster-event:"):
            raise ValueError("event_id must use cluster-event: prefix")
        if not self.cluster_id.startswith("economic:"):
            raise ValueError("cluster_id must use economic: prefix")
        if tuple(sorted(set(self.review_candidate_hashes))) != self.review_candidate_hashes:
            raise ValueError("review_candidate_hashes must be unique and sorted")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "event_id": self.event_id,
            "action": self.action.value,
            "signature_hash": self.signature_hash,
            "cluster_id": self.cluster_id,
            "cluster_proof_hash": self.cluster_proof_hash,
            "review_candidate_hashes": list(self.review_candidate_hashes),
        })


@dataclass(frozen=True)
class EconomicClusterRegistration:
    action: ClusterRegistrationAction
    cluster: EconomicTransactionCluster
    event: EconomicClusterEvent
    review_candidates: tuple[DedupReviewCandidate, ...]


def _new_cluster_id(signature: EconomicTransactionSignature) -> str:
    return "economic:" + canonical_hash({
        "schema": 1,
        "seed_signature_hash": signature.proof_hash,
    })


def _review_candidate(
    signature: EconomicTransactionSignature,
    cluster: EconomicTransactionCluster,
    assessments: tuple[EconomicMatchAssessment, ...],
    *,
    reason: str,
) -> DedupReviewCandidate:
    body = {
        "schema": 1,
        "signature_hash": signature.proof_hash,
        "cluster_id": cluster.cluster_id,
        "assessment_hashes": sorted(
            item.proof_hash for item in assessments
        ),
        "reason": reason,
    }
    return DedupReviewCandidate(
        candidate_id="dedup-review:" + canonical_hash(body),
        signature_hash=signature.proof_hash,
        candidate_cluster_id=cluster.cluster_id,
        assessments=tuple(sorted(
            assessments,
            key=lambda item: item.proof_hash,
        )),
        reason=reason,
    )


class EconomicClusterRegistry:
    """Append-only clustering of approved source rows.

    Signatures remain independent members. Exact matches may be grouped, but no
    source-backed row is removed. Possible/insufficient matches produce manual
    review candidates and remain in a separate new cluster.
    """

    def __init__(self) -> None:
        self._clusters: dict[str, EconomicTransactionCluster] = {}
        self._signature_to_cluster: dict[str, str] = {}
        self._events: list[EconomicClusterEvent] = []
        self._review_candidates: dict[str, DedupReviewCandidate] = {}
        self._registrations: dict[str, EconomicClusterRegistration] = {}

    def get_cluster(self, cluster_id: str) -> EconomicTransactionCluster:
        try:
            return self._clusters[cluster_id]
        except KeyError as exc:
            raise KeyError("unknown economic cluster: " + cluster_id) from exc

    def cluster_for_signature(
        self,
        signature_hash: str,
    ) -> EconomicTransactionCluster:
        try:
            cluster_id = self._signature_to_cluster[signature_hash]
        except KeyError as exc:
            raise KeyError("unknown economic signature") from exc
        return self._clusters[cluster_id]

    def all_clusters(self) -> tuple[EconomicTransactionCluster, ...]:
        return tuple(
            self._clusters[key] for key in sorted(self._clusters)
        )

    def review_candidates(self) -> tuple[DedupReviewCandidate, ...]:
        return tuple(
            self._review_candidates[key]
            for key in sorted(self._review_candidates)
        )

    def events(self) -> tuple[EconomicClusterEvent, ...]:
        return tuple(self._events)

    def register(
        self,
        signature: EconomicTransactionSignature,
    ) -> EconomicClusterRegistration:
        existing = self._registrations.get(signature.proof_hash)
        if existing is not None:
            return existing

        exact_clusters = []
        review_candidates = []

        for cluster in self.all_clusters():
            assessments = tuple(
                compare_economic_signatures(signature, member)
                for member in cluster.signatures
            )
            states = {item.state for item in assessments}
            if states == {DedupMatchState.EXACT_MATCH}:
                exact_clusters.append((cluster, assessments))
                continue

            if DedupMatchState.EXACT_MATCH in states:
                review_candidates.append(_review_candidate(
                    signature,
                    cluster,
                    assessments,
                    reason="PARTIAL_EXACT_CLUSTER_CONFLICT",
                ))
            elif (
                DedupMatchState.POSSIBLE_MATCH in states
                or DedupMatchState.INSUFFICIENT_INFORMATION in states
            ):
                review_candidates.append(_review_candidate(
                    signature,
                    cluster,
                    assessments,
                    reason="NON_EXACT_MATCH_REQUIRES_REVIEW",
                ))

        if len(exact_clusters) == 1:
            cluster, _assessments = exact_clusters[0]
            updated = EconomicTransactionCluster(
                cluster_id=cluster.cluster_id,
                signatures=tuple(sorted(
                    cluster.signatures + (signature,),
                    key=lambda item: item.proof_hash,
                )),
            )
            action = ClusterRegistrationAction.AUTO_JOINED_EXACT
            self._clusters[cluster.cluster_id] = updated
            target_cluster = updated

        else:
            target_cluster = EconomicTransactionCluster(
                cluster_id=_new_cluster_id(signature),
                signatures=(signature,),
            )
            self._clusters[target_cluster.cluster_id] = target_cluster
            if len(exact_clusters) > 1:
                for cluster, assessments in exact_clusters:
                    review_candidates.append(_review_candidate(
                        signature,
                        cluster,
                        assessments,
                        reason="MULTIPLE_EXACT_CLUSTERS_REQUIRE_REVIEW",
                    ))
                action = ClusterRegistrationAction.NEW_CLUSTER_REVIEW_REQUIRED
            elif review_candidates:
                action = ClusterRegistrationAction.NEW_CLUSTER_REVIEW_REQUIRED
            else:
                action = ClusterRegistrationAction.NEW_CLUSTER

        self._signature_to_cluster[signature.proof_hash] = target_cluster.cluster_id
        for candidate in review_candidates:
            self._review_candidates[candidate.candidate_id] = candidate

        event_body = {
            "schema": 1,
            "action": action.value,
            "signature_hash": signature.proof_hash,
            "cluster_id": target_cluster.cluster_id,
            "cluster_proof_hash": target_cluster.proof_hash,
            "review_candidate_hashes": sorted(
                item.proof_hash for item in review_candidates
            ),
        }
        event = EconomicClusterEvent(
            event_id="cluster-event:" + canonical_hash(event_body),
            action=action,
            signature_hash=signature.proof_hash,
            cluster_id=target_cluster.cluster_id,
            cluster_proof_hash=target_cluster.proof_hash,
            review_candidate_hashes=tuple(sorted(
                item.proof_hash for item in review_candidates
            )),
        )
        self._events.append(event)

        registration = EconomicClusterRegistration(
            action=action,
            cluster=target_cluster,
            event=event,
            review_candidates=tuple(sorted(
                review_candidates,
                key=lambda item: item.proof_hash,
            )),
        )
        self._registrations[signature.proof_hash] = registration
        return registration

    @property
    def registry_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "cluster_hashes": [
                item.proof_hash for item in self.all_clusters()
            ],
            "event_hashes": [
                item.proof_hash for item in self._events
            ],
            "review_candidate_hashes": [
                item.proof_hash for item in self.review_candidates()
            ],
        })


__all__ = [
    "ClusterRegistrationAction",
    "DedupMatchState",
    "DedupReviewCandidate",
    "EconomicClusterEvent",
    "EconomicClusterRegistration",
    "EconomicClusterRegistry",
    "EconomicTransactionCluster",
    "EconomicMatchAssessment",
    "EconomicTransactionSignature",
    "build_economic_signature",
    "compare_economic_signatures",
]
