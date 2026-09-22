"""RebateRecovery deterministic earned-vs-paid rebate audit."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from typing import Any, Iterable, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef, canonical_hash


class RebateBasis(str, Enum):
    SPEND_BPS = "spend_bps"
    UNIT_CENTS = "unit_cents"


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _date(name: str, value: str) -> date:
    text = _required(name, value)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _nonnegative_int(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be non-negative integer")
    return value


def _decimal(name: str, value: str | int | float | Decimal) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


@dataclass(frozen=True)
class RebateAgreement:
    agreement_id: str
    vendor_id: str
    basis: RebateBasis
    effective_from: str
    effective_to: str | None
    threshold_spend_cents: int
    threshold_units: str
    rate_bps: int
    rate_cents_per_unit: int
    fixed_bonus_cents: int
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("agreement_id", "vendor_id", "effective_from", "source_hash", "source_locator"):
            _required(name, getattr(self, name))
        start = _date("effective_from", self.effective_from)
        if self.effective_to is not None and _date("effective_to", self.effective_to) < start:
            raise ValueError("effective_to cannot precede effective_from")
        _nonnegative_int("threshold_spend_cents", self.threshold_spend_cents)
        _decimal("threshold_units", self.threshold_units)
        _nonnegative_int("rate_bps", self.rate_bps)
        _nonnegative_int("rate_cents_per_unit", self.rate_cents_per_unit)
        _nonnegative_int("fixed_bonus_cents", self.fixed_bonus_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        if self.basis is RebateBasis.SPEND_BPS and self.rate_bps <= 0:
            raise ValueError("spend_bps agreement requires positive rate_bps")
        if self.basis is RebateBasis.UNIT_CENTS and self.rate_cents_per_unit <= 0:
            raise ValueError("unit_cents agreement requires positive rate_cents_per_unit")

    def covers(self, period_end: str) -> bool:
        when = _date("period_end", period_end)
        start = _date("effective_from", self.effective_from)
        end = _date("effective_to", self.effective_to) if self.effective_to else None
        return when >= start and (end is None or when <= end)

    def rule_ref(self) -> RuleRef:
        identity = {
            "schema": 1,
            "agreement_id": self.agreement_id,
            "vendor_id": self.vendor_id,
            "basis": self.basis.value,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "threshold_spend_cents": self.threshold_spend_cents,
            "threshold_units": self.threshold_units,
            "rate_bps": self.rate_bps,
            "rate_cents_per_unit": self.rate_cents_per_unit,
            "fixed_bonus_cents": self.fixed_bonus_cents,
            "source_hash": self.source_hash,
        }
        return RuleRef(
            rule_id="rebate-agreement:" + canonical_hash(identity),
            source_hash=self.source_hash,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            verified_controlling=self.verified,
            source_locator=self.source_locator,
            metadata={"kind": "rebate_agreement", **dict(self.metadata)},
        )


@dataclass(frozen=True)
class RebateActivity:
    agreement_id: str
    period_id: str
    period_end: str
    eligible_spend_cents: int
    eligible_units: str
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("agreement_id", "period_id", "period_end", "source_hash", "source_locator"):
            _required(name, getattr(self, name))
        _date("period_end", self.period_end)
        _nonnegative_int("eligible_spend_cents", self.eligible_spend_cents)
        _decimal("eligible_units", self.eligible_units)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def key(self) -> tuple[str, str]:
        return (self.agreement_id, self.period_id)

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id="rebate-activity:" + canonical_hash({
                "agreement_id": self.agreement_id,
                "period_id": self.period_id,
                "source_hash": self.source_hash,
                "locator": self.source_locator,
            }),
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="rebate_activity",
            verified=self.verified,
            metadata={
                "period_end": self.period_end,
                "eligible_spend_cents": self.eligible_spend_cents,
                "eligible_units": self.eligible_units,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class RebateCredit:
    credit_id: str
    agreement_id: str
    period_id: str
    amount_cents: int
    source_hash: str
    source_locator: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("credit_id", "agreement_id", "period_id", "source_hash", "source_locator"):
            _required(name, getattr(self, name))
        _nonnegative_int("amount_cents", self.amount_cents)
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def key(self) -> tuple[str, str]:
        return (self.agreement_id, self.period_id)

    def evidence(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"rebate-credit:{self.credit_id}",
            source_hash=self.source_hash,
            locator=self.source_locator,
            kind="rebate_credit",
            verified=self.verified,
            metadata={
                "agreement_id": self.agreement_id,
                "period_id": self.period_id,
                "amount_cents": self.amount_cents,
                **dict(self.metadata),
            },
        )


@dataclass(frozen=True)
class RebateAuditException:
    reference: str
    code: str
    detail: str


@dataclass(frozen=True)
class RebateAuditBatch:
    observations: tuple[RecoveryObservation, ...]
    exceptions: tuple[RebateAuditException, ...]


def expected_rebate_cents(agreement: RebateAgreement, activity: RebateActivity) -> int:
    if agreement.basis is RebateBasis.SPEND_BPS:
        if activity.eligible_spend_cents < agreement.threshold_spend_cents:
            return 0
        variable = (
            Decimal(activity.eligible_spend_cents) * Decimal(agreement.rate_bps)
            / Decimal(10000)
        )
        return int(variable.quantize(Decimal("1"), rounding=ROUND_HALF_UP)) + agreement.fixed_bonus_cents

    units = _decimal("eligible_units", activity.eligible_units)
    if units < _decimal("threshold_units", agreement.threshold_units):
        return 0
    variable = units * Decimal(agreement.rate_cents_per_unit)
    return int(variable.quantize(Decimal("1"), rounding=ROUND_HALF_UP)) + agreement.fixed_bonus_cents


def audit_rebates(
    *,
    client_id: str,
    agreements: Iterable[RebateAgreement],
    activities: Iterable[RebateActivity],
    credits: Iterable[RebateCredit],
    currency: str = "USD",
) -> RebateAuditBatch:
    client_id = _required("client_id", client_id)
    currency = _required("currency", currency).upper()
    exceptions: list[RebateAuditException] = []

    agreement_index: dict[str, list[RebateAgreement]] = defaultdict(list)
    for agreement in agreements:
        agreement_index[agreement.agreement_id].append(agreement)

    activity_groups: dict[tuple[str, str], list[RebateActivity]] = defaultdict(list)
    for activity in activities:
        activity_groups[activity.key].append(activity)

    credit_id_groups: dict[str, list[RebateCredit]] = defaultdict(list)
    for credit in credits:
        credit_id_groups[credit.credit_id].append(credit)

    accepted_credits: list[RebateCredit] = []
    for credit_id in sorted(credit_id_groups):
        group = credit_id_groups[credit_id]
        if len(group) != 1:
            exceptions.append(RebateAuditException(
                credit_id,
                "DUPLICATE_CREDIT_ID",
                f"credit_id appears {len(group)} times; all copies excluded",
            ))
            continue
        accepted_credits.append(group[0])

    credits_by_key: dict[tuple[str, str], list[RebateCredit]] = defaultdict(list)
    for credit in accepted_credits:
        credits_by_key[credit.key].append(credit)

    observations: list[RecoveryObservation] = []

    for key in sorted(activity_groups):
        activity_rows = activity_groups[key]
        reference = f"{key[0]}/{key[1]}"
        if len(activity_rows) != 1:
            exceptions.append(RebateAuditException(
                reference,
                "DUPLICATE_ACTIVITY_PERIOD",
                f"{len(activity_rows)} activity summaries exist for agreement/period",
            ))
            continue
        activity = activity_rows[0]

        candidates = [
            agreement
            for agreement in agreement_index.get(activity.agreement_id, [])
            if agreement.covers(activity.period_end)
        ]
        if not candidates:
            exceptions.append(RebateAuditException(
                reference,
                "NO_REBATE_AGREEMENT",
                "no effective rebate agreement covers period_end",
            ))
            continue
        if len(candidates) > 1:
            exceptions.append(RebateAuditException(
                reference,
                "OVERLAPPING_REBATE_AGREEMENTS",
                f"{len(candidates)} agreement versions cover period_end",
            ))
            continue

        period_credits = sorted(credits_by_key.get(key, []), key=lambda c: c.credit_id)
        if not period_credits:
            exceptions.append(RebateAuditException(
                reference,
                "MISSING_CREDIT_LEDGER_ROW",
                "explicit rebate credit ledger row is required, including verified zero",
            ))
            continue

        agreement = candidates[0]
        expected = expected_rebate_cents(agreement, activity)
        actual = sum(item.amount_cents for item in period_credits)
        if expected <= actual:
            continue

        evidence = (activity.evidence(),) + tuple(item.evidence() for item in period_credits)
        verified = agreement.verified and all(ref.verified for ref in evidence)
        observations.append(RecoveryObservation(
            branch=Branch.REBATE,
            client_id=client_id,
            counterparty_id=agreement.vendor_id,
            reference=reference,
            currency=currency,
            expected_cents=expected,
            actual_cents=actual,
            rule=agreement.rule_ref(),
            evidence=evidence,
            reason="REBATE_UNDERPAYMENT",
            confidence_basis=(
                "verified rebate agreement + eligible activity + explicit credit ledger"
                if verified
                else "rebate agreement/activity/credit evidence requires verification"
            ),
            metadata={
                "agreement_id": agreement.agreement_id,
                "period_id": activity.period_id,
                "period_end": activity.period_end,
                "basis": agreement.basis.value,
                "eligible_spend_cents": activity.eligible_spend_cents,
                "eligible_units": activity.eligible_units,
                "credit_ids": [item.credit_id for item in period_credits],
                "detection_basis": "earned_rebate_vs_explicit_credit_ledger",
            },
        ))

    exceptions.sort(key=lambda item: (item.code, item.reference, item.detail))
    return RebateAuditBatch(tuple(observations), tuple(exceptions))
