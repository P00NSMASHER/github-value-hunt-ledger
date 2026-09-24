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


__all__ = [
    "DedupMatchState",
    "EconomicMatchAssessment",
    "EconomicTransactionSignature",
    "build_economic_signature",
    "compare_economic_signatures",
]
