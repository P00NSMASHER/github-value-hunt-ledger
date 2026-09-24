"""Sparse transaction schema for historical public-record MNPI research.

Step 4 adds transaction-shaped normalized records without inventing missing facts.
Every transaction is anchored to a registered historical case and to an exact
retained artifact already linked to that case.

No field defaults to zero. Unknown price, quantity, profit, side, or instrument
remains explicitly unknown.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
import re

from .case_model import CaseArtifactRole, CaseRegistry
from .raw_artifacts import RawArtifactManifest, SourceArtifactRef
from .source_registry import (
    SourceAdmissibility,
    SourceRegistry,
    canonical_hash,
)


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
_DECIMAL_RE = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


class FactStatus(str, Enum):
    ALLEGED = "ALLEGED"
    ADMITTED = "ADMITTED"
    SETTLED_WITHOUT_ADMISSION = "SETTLED_WITHOUT_ADMISSION"
    FOUND_LIABLE = "FOUND_LIABLE"
    CONVICTED = "CONVICTED"
    COURT_ESTABLISHED = "COURT_ESTABLISHED"
    ACADEMIC_RECONSTRUCTION = "ACADEMIC_RECONSTRUCTION"


class InstrumentType(str, Enum):
    STOCK = "STOCK"
    CALL_OPTION = "CALL_OPTION"
    PUT_OPTION = "PUT_OPTION"
    OPTION_OTHER = "OPTION_OTHER"
    CFD = "CFD"
    BOND = "BOND"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    SELL_SHORT = "SELL_SHORT"
    COVER = "COVER"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class TimePrecision(str, Enum):
    EXACT_TIMESTAMP = "EXACT_TIMESTAMP"
    DATE_ONLY = "DATE_ONLY"
    DATE_RANGE = "DATE_RANGE"


def _parse_date(name: str, value: str) -> str:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc
    return value


def _parse_timestamp(name: str, value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include timezone")
    return value


def _decimal_text(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not _DECIMAL_RE.fullmatch(text):
        raise ValueError(f"{name} must be a non-negative plain decimal string")
    try:
        parsed = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"{name} must be decimal") from exc
    if not parsed.is_finite() or parsed < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return text


@dataclass(frozen=True)
class HistoricalTransaction:
    trade_id: str
    case_id: str
    case_proof_hash: str
    trader_party_id: str
    issuer_id: str
    source_ref: SourceArtifactRef
    fact_status: FactStatus
    status_ref: SourceArtifactRef

    instrument_type: InstrumentType = InstrumentType.UNKNOWN
    side: TradeSide = TradeSide.UNKNOWN

    trade_timestamp: str | None = None
    trade_date: str | None = None
    trade_date_range_start: str | None = None
    trade_date_range_end: str | None = None

    ticker_at_trade: str | None = None
    currency: str | None = None
    quantity: str | None = None
    execution_price: str | None = None
    trade_amount: str | None = None

    option_strike: str | None = None
    option_expiry: str | None = None

    exit_timestamp: str | None = None
    exit_price: str | None = None
    documented_profit: str | None = None

    notes: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "trade_id",
            "case_id",
            "trader_party_id",
            "issuer_id",
        ):
            if not _ID_RE.fullmatch(getattr(self, name)):
                raise ValueError(f"invalid {name}")

        if not re.fullmatch(r"^[0-9a-f]{64}$", self.case_proof_hash):
            raise ValueError("case_proof_hash must be SHA-256")

        temporal_count = sum(
            item is not None
            for item in (
                self.trade_timestamp,
                self.trade_date,
                self.trade_date_range_start,
                self.trade_date_range_end,
            )
        )
        if temporal_count == 0:
            raise ValueError("transaction requires at least one trade-time field")

        if self.trade_timestamp is not None:
            _parse_timestamp("trade_timestamp", self.trade_timestamp)
        if self.trade_date is not None:
            _parse_date("trade_date", self.trade_date)

        range_start = self.trade_date_range_start
        range_end = self.trade_date_range_end
        if (range_start is None) != (range_end is None):
            raise ValueError("trade date range requires both start and end")
        if range_start is not None and range_end is not None:
            start = date.fromisoformat(_parse_date("trade_date_range_start", range_start))
            end = date.fromisoformat(_parse_date("trade_date_range_end", range_end))
            if end < start:
                raise ValueError("trade date range end cannot precede start")

        if self.trade_timestamp is not None and (
            self.trade_date is not None or range_start is not None
        ):
            raise ValueError(
                "use exact timestamp, date-only, or date-range precision, not multiple"
            )
        if self.trade_date is not None and range_start is not None:
            raise ValueError(
                "use date-only or date-range precision, not both"
            )

        if self.ticker_at_trade is not None and not self.ticker_at_trade.strip():
            raise ValueError("ticker_at_trade cannot be blank")
        if self.currency is not None:
            normalized = self.currency.strip().upper()
            if not re.fullmatch(r"^[A-Z]{3}$", normalized):
                raise ValueError("currency must be a 3-letter code")
            object.__setattr__(self, "currency", normalized)

        for field_name in (
            "quantity",
            "execution_price",
            "trade_amount",
            "option_strike",
            "exit_price",
            "documented_profit",
        ):
            object.__setattr__(
                self,
                field_name,
                _decimal_text(field_name, getattr(self, field_name)),
            )

        if self.option_expiry is not None:
            _parse_date("option_expiry", self.option_expiry)

        option_fields_present = (
            self.option_strike is not None or self.option_expiry is not None
        )
        if option_fields_present and self.instrument_type not in {
            InstrumentType.CALL_OPTION,
            InstrumentType.PUT_OPTION,
            InstrumentType.OPTION_OTHER,
        }:
            raise ValueError(
                "option strike/expiry requires an option instrument type"
            )

        if self.exit_timestamp is not None:
            _parse_timestamp("exit_timestamp", self.exit_timestamp)

    @property
    def time_precision(self) -> TimePrecision:
        if self.trade_timestamp is not None:
            return TimePrecision.EXACT_TIMESTAMP
        if self.trade_date is not None:
            return TimePrecision.DATE_ONLY
        return TimePrecision.DATE_RANGE

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "trade_id": self.trade_id,
            "case_id": self.case_id,
            "case_proof_hash": self.case_proof_hash,
            "trader_party_id": self.trader_party_id,
            "issuer_id": self.issuer_id,
            "source_ref_proof_hash": self.source_ref.proof_hash,
            "fact_status": self.fact_status.value,
            "status_ref_proof_hash": self.status_ref.proof_hash,
            "instrument_type": self.instrument_type.value,
            "side": self.side.value,
            "time_precision": self.time_precision.value,
            "trade_timestamp": self.trade_timestamp,
            "trade_date": self.trade_date,
            "trade_date_range_start": self.trade_date_range_start,
            "trade_date_range_end": self.trade_date_range_end,
            "ticker_at_trade": self.ticker_at_trade,
            "currency": self.currency,
            "quantity": self.quantity,
            "execution_price": self.execution_price,
            "trade_amount": self.trade_amount,
            "option_strike": self.option_strike,
            "option_expiry": self.option_expiry,
            "exit_timestamp": self.exit_timestamp,
            "exit_price": self.exit_price,
            "documented_profit": self.documented_profit,
            "notes": self.notes,
        })


class TransactionRegistry:
    def __init__(self) -> None:
        self._by_id: dict[str, HistoricalTransaction] = {}

    def register(
        self,
        transaction: HistoricalTransaction,
        *,
        cases: CaseRegistry,
        source_registry: SourceRegistry,
        artifact_manifest: RawArtifactManifest,
    ) -> HistoricalTransaction:
        verify_transaction_provenance(
            transaction,
            cases=cases,
            source_registry=source_registry,
            artifact_manifest=artifact_manifest,
        )
        existing = self._by_id.get(transaction.trade_id)
        if existing is not None:
            if existing.proof_hash != transaction.proof_hash:
                raise ValueError(
                    "trade_id already registered with different content"
                )
            return existing
        self._by_id[transaction.trade_id] = transaction
        return transaction

    def get(self, trade_id: str) -> HistoricalTransaction:
        try:
            return self._by_id[trade_id]
        except KeyError as exc:
            raise KeyError("unknown trade_id: " + trade_id) from exc

    def all(self) -> tuple[HistoricalTransaction, ...]:
        return tuple(self._by_id[key] for key in sorted(self._by_id))

    @property
    def registry_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "transaction_proof_hashes": [
                item.proof_hash for item in self.all()
            ],
        })


def verify_transaction_provenance(
    transaction: HistoricalTransaction,
    *,
    cases: CaseRegistry,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
) -> None:
    case = cases.get(transaction.case_id)
    if case.proof_hash != transaction.case_proof_hash:
        raise ValueError("transaction case proof mismatch")

    party_ids = {item.party_id for item in case.parties}
    if transaction.trader_party_id not in party_ids:
        raise ValueError("transaction trader is not a party in the case")

    issuer_ids = {item.issuer_id for item in case.issuers}
    if transaction.issuer_id not in issuer_ids:
        raise ValueError("transaction issuer is not part of the case")

    artifact_manifest.resolve_ref(transaction.source_ref)
    source = source_registry.get(transaction.source_ref.source_id)
    if source.proof_hash != transaction.source_ref.source_proof_hash:
        raise ValueError("transaction source proof mismatch")

    artifact_manifest.resolve_ref(transaction.status_ref)
    status_source = source_registry.get(transaction.status_ref.source_id)
    if status_source.proof_hash != transaction.status_ref.source_proof_hash:
        raise ValueError("transaction status source proof mismatch")

    case_artifact_by_ref = {
        link.ref.proof_hash: link for link in case.artifacts
    }
    if transaction.source_ref.proof_hash not in case_artifact_by_ref:
        raise ValueError(
            "transaction source artifact is not linked to the canonical case"
        )
    status_link = case_artifact_by_ref.get(transaction.status_ref.proof_hash)
    if status_link is None:
        raise ValueError(
            "transaction status artifact is not linked to the canonical case"
        )

    if transaction.fact_status is FactStatus.ACADEMIC_RECONSTRUCTION:
        if (
            status_source.admissibility
            is not SourceAdmissibility.PUBLISHED_RESEARCH_RECONSTRUCTION
            or status_link.artifact_role
            is not CaseArtifactRole.ACADEMIC_RECONSTRUCTION
        ):
            raise ValueError(
                "ACADEMIC_RECONSTRUCTION status requires academic reconstruction evidence"
            )
        return

    if status_source.admissibility is not SourceAdmissibility.PRIMARY_PUBLIC_RECORD:
        raise ValueError(
            "non-academic fact status requires a primary public record"
        )

    allowed_roles = {
        FactStatus.ALLEGED: {
            CaseArtifactRole.COMPLAINT,
            CaseArtifactRole.INDICTMENT,
            CaseArtifactRole.LITIGATION_RELEASE,
            CaseArtifactRole.ADMIN_ORDER,
            CaseArtifactRole.EXHIBIT,
            CaseArtifactRole.OTHER,
        },
        FactStatus.ADMITTED: {
            CaseArtifactRole.PLEA_OR_STATEMENT,
            CaseArtifactRole.JUDGMENT,
            CaseArtifactRole.ADMIN_ORDER,
        },
        FactStatus.SETTLED_WITHOUT_ADMISSION: {
            CaseArtifactRole.JUDGMENT,
            CaseArtifactRole.ADMIN_ORDER,
        },
        FactStatus.FOUND_LIABLE: {
            CaseArtifactRole.JUDGMENT,
        },
        FactStatus.CONVICTED: {
            CaseArtifactRole.JUDGMENT,
            CaseArtifactRole.PLEA_OR_STATEMENT,
        },
        FactStatus.COURT_ESTABLISHED: {
            CaseArtifactRole.JUDGMENT,
            CaseArtifactRole.EXHIBIT,
        },
    }
    allowed = allowed_roles[transaction.fact_status]
    if status_link.artifact_role not in allowed:
        raise ValueError(
            f"{transaction.fact_status.value} status is not supported by "
            f"{status_link.artifact_role.value} evidence"
        )


__all__ = [
    "FactStatus",
    "HistoricalTransaction",
    "InstrumentType",
    "TimePrecision",
    "TradeSide",
    "TransactionRegistry",
    "verify_transaction_provenance",
]
