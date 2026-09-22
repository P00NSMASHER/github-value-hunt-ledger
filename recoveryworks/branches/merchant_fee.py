"""MerchantFeeRecovery deterministic processor-fee audit.

Scope is intentionally limited to processor-controlled commercial fees:
- fixed/monthly fee
- processor markup in basis points on independent sales volume
- per-transaction fee

Interchange, card-network assessments, taxes, and other pass-through charges are
outside the calculation unless separately reviewed into a different model.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef, canonical_hash


FEE_SCOPE = "processor_controlled_only"


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _iso_date(name: str, value: str) -> date:
    text = _required(name, value)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _cents(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be non-negative integer cents")
    return value


def _count(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be non-negative integer")
    return value


def _bps_fee_cents(gross_sales_cents: int, markup_bps: int) -> int:
    raw = Decimal(gross_sales_cents) * Decimal(markup_bps) / Decimal(10000)
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class MerchantFeeAgreement:
    processor_id: str
    fee_plan_id: str
    effective_from: str
    effective_to: str | None
    fixed_fee_cents: int
    markup_bps: int
    per_transaction_cents: int
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "processor_id", "fee_plan_id", "effective_from",
            "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        start = _iso_date("effective_from", self.effective_from)
        if self.effective_to is not None:
            end = _iso_date("effective_to", self.effective_to)
            if end < start:
                raise ValueError("effective_to cannot precede effective_from")
        _cents("fixed_fee_cents", self.fixed_fee_cents)
        _cents("per_transaction_cents", self.per_transaction_cents)
        if type(self.markup_bps) is not int or not 0 <= self.markup_bps <= 10000:
            raise ValueError("markup_bps must be integer between 0 and 10000")
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        if (
            self.fixed_fee_cents == 0
            and self.markup_bps == 0
            and self.per_transaction_cents == 0
        ):
            raise ValueError("merchant fee agreement must contain at least one fee")

    def covers(self, statement_date: str) -> bool:
        when = _iso_date("statement_date", statement_date)
        start = _iso_date("effective_from", self.effective_from)
        end = _iso_date("effective_to", self.effective_to) if self.effective_to else None
        return when >= start and (end is None or when <= end)

    def rule_ref(self) -> RuleRef:
        identity = {
            "schema": 1,
            "processor_id": self.processor_id,
            "fee_plan_id": self.fee_plan_id,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "fixed_fee_cents": self.fixed_fee_cents,
            "markup_bps": self.markup_bps,
            "per_transaction_cents": self.per_transaction_cents,
            "source_hash": self.source_hash,
            "fee_scope": FEE_SCOPE,
        }
        return RuleRef(
            rule_id="merchant-fee-agreement:" + canonical_hash(identity),
            source_hash=self.source_hash,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            verified_controlling=self.verified,
            source_locator=self.source_locator,
            metadata={
                "kind": "merchant_processor_fee_agreement",
                "processor_id": self.processor_id,
                "fee_plan_id": self.fee_plan_id,
                "fixed_fee_cents": self.fixed_fee_cents,
                "markup_bps": self.markup_bps,
                "per_transaction_cents": self.per_transaction_cents,
                "fee_scope": FEE_SCOPE,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class MerchantFeeStatement:
    statement_id: str
    processor_id: str
    account_id: str
    fee_plan_id: str
    statement_date: str
    actual_processor_fee_cents: int
    source_hash: str
    source_locator: str
    verified: bool
    scope_reviewer_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "statement_id", "processor_id", "account_id", "fee_plan_id",
            "statement_date", "source_hash", "source_locator",
        ):
            _required(name, getattr(self, name))
        _iso_date("statement_date", self.statement_date)
        _cents("actual_processor_fee_cents", self.actual_processor_fee_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        if self.verified and not (
            isinstance(self.scope_reviewer_id, str)
            and self.scope_reviewer_id.strip()
        ):
            raise ValueError(
                "verified merchant statement requires scope_reviewer_id "
                "confirming processor-controlled fee scope"
            )

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"merchant-fee-statement:{self.statement_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="merchant_processor_fee_statement",
            verified=self.verified,
            metadata={
                "processor_id": self.processor_id,
                "account_id": self.account_id,
                "fee_plan_id": self.fee_plan_id,
                "statement_date": self.statement_date,
                "actual_processor_fee_cents": self.actual_processor_fee_cents,
                "fee_scope": FEE_SCOPE,
                "scope_reviewer_id": self.scope_reviewer_id,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class MerchantTransactionSummary:
    statement_id: str
    gross_sales_cents: int
    transaction_count: int
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _required("statement_id", self.statement_id)
        _cents("gross_sales_cents", self.gross_sales_cents)
        _count("transaction_count", self.transaction_count)
        _required("source_hash", self.source_hash)
        _required("source_locator", self.source_locator)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id="merchant-volume:" + canonical_hash({
                "statement_id": self.statement_id,
                "gross_sales_cents": self.gross_sales_cents,
                "transaction_count": self.transaction_count,
                "source_hash": self.source_hash,
                "locator": self.source_locator,
            }),
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="merchant_transaction_summary",
            verified=self.verified,
            metadata={
                "statement_id": self.statement_id,
                "gross_sales_cents": self.gross_sales_cents,
                "transaction_count": self.transaction_count,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class MerchantFeeAuditException:
    reference: str
    code: str
    detail: str


@dataclass(frozen=True)
class MerchantFeeAuditBatch:
    observations: tuple[RecoveryObservation, ...]
    exceptions: tuple[MerchantFeeAuditException, ...]


def audit_merchant_fees(
    *,
    client_id: str,
    statements: Iterable[MerchantFeeStatement],
    agreements: Iterable[MerchantFeeAgreement],
    transaction_summaries: Iterable[MerchantTransactionSummary] = (),
    currency: str = "USD",
) -> MerchantFeeAuditBatch:
    client_id = _required("client_id", client_id)
    currency = _required("currency", currency).upper()

    agreement_index: dict[tuple[str, str], list[MerchantFeeAgreement]] = defaultdict(list)
    for agreement in agreements:
        agreement_index[(agreement.processor_id, agreement.fee_plan_id)].append(agreement)

    summary_groups: dict[str, list[MerchantTransactionSummary]] = defaultdict(list)
    for summary in transaction_summaries:
        summary_groups[summary.statement_id].append(summary)

    summary_by_statement: dict[str, MerchantTransactionSummary] = {}
    exceptions: list[MerchantFeeAuditException] = []
    for statement_id in sorted(summary_groups):
        group = summary_groups[statement_id]
        if len(group) != 1:
            exceptions.append(MerchantFeeAuditException(
                statement_id,
                "CONFLICTING_TRANSACTION_SUMMARIES",
                f"{len(group)} transaction summaries exist for one statement",
            ))
            continue
        summary_by_statement[statement_id] = group[0]

    statement_groups: dict[str, list[MerchantFeeStatement]] = defaultdict(list)
    for statement in statements:
        statement_groups[statement.statement_id].append(statement)

    observations: list[RecoveryObservation] = []
    for statement_id in sorted(statement_groups):
        group = statement_groups[statement_id]
        if len(group) != 1:
            exceptions.append(MerchantFeeAuditException(
                statement_id,
                "DUPLICATE_STATEMENT_ID",
                f"statement_id appears {len(group)} times; all copies excluded",
            ))
            continue
        statement = group[0]
        candidates = [
            agreement
            for agreement in agreement_index.get(
                (statement.processor_id, statement.fee_plan_id), []
            )
            if agreement.covers(statement.statement_date)
        ]
        if not candidates:
            exceptions.append(MerchantFeeAuditException(
                statement_id,
                "NO_FEE_AGREEMENT",
                "no effective merchant fee agreement covers this statement",
            ))
            continue
        if len(candidates) > 1:
            exceptions.append(MerchantFeeAuditException(
                statement_id,
                "OVERLAPPING_FEE_AGREEMENTS",
                f"{len(candidates)} fee agreement versions cover this statement",
            ))
            continue

        agreement = candidates[0]
        variable_pricing = (
            agreement.markup_bps > 0 or agreement.per_transaction_cents > 0
        )
        summary = summary_by_statement.get(statement_id)
        if variable_pricing and summary is None:
            exceptions.append(MerchantFeeAuditException(
                statement_id,
                "MISSING_TRANSACTION_SUMMARY",
                "fee agreement requires independent sales/count evidence",
            ))
            continue

        gross_sales_cents = summary.gross_sales_cents if summary else 0
        transaction_count = summary.transaction_count if summary else 0
        expected_cents = (
            agreement.fixed_fee_cents
            + _bps_fee_cents(gross_sales_cents, agreement.markup_bps)
            + agreement.per_transaction_cents * transaction_count
        )
        if statement.actual_processor_fee_cents <= expected_cents:
            continue

        evidence = [statement.evidence()]
        if summary is not None:
            evidence.append(summary.evidence())

        observations.append(RecoveryObservation(
            branch=Branch.MERCHANT_FEE,
            client_id=client_id,
            counterparty_id=statement.processor_id,
            reference=statement.statement_id,
            currency=currency,
            expected_cents=expected_cents,
            actual_cents=statement.actual_processor_fee_cents,
            rule=agreement.rule_ref(),
            evidence=tuple(evidence),
            reason="MERCHANT_PROCESSOR_FEE_OVERCHARGE",
            confidence_basis=(
                "verified fee agreement + reviewed processor-fee scope + "
                "independent transaction evidence"
                if agreement.verified and all(ref.verified for ref in evidence)
                else "agreement/statement/transaction evidence requires verification"
            ),
            metadata={
                "account_id": statement.account_id,
                "fee_plan_id": statement.fee_plan_id,
                "statement_date": statement.statement_date,
                "fee_scope": FEE_SCOPE,
                "fixed_fee_cents": agreement.fixed_fee_cents,
                "markup_bps": agreement.markup_bps,
                "per_transaction_cents": agreement.per_transaction_cents,
                "gross_sales_cents": gross_sales_cents,
                "transaction_count": transaction_count,
                "scope_reviewer_id": statement.scope_reviewer_id,
            },
        ))

    exceptions.sort(key=lambda x: (x.code, x.reference, x.detail))
    observations.sort(key=lambda x: (x.counterparty_id, x.reference))
    return MerchantFeeAuditBatch(tuple(observations), tuple(exceptions))
