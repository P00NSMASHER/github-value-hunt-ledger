"""Deterministic RecoveryWorks contingency-fee agreements and assessments."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .models import Branch, RecoveryFinding, canonical_hash

HALF_UP = "HALF_UP"
FLOOR = "FLOOR"


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


@dataclass(frozen=True)
class FeeAgreement:
    agreement_id: str
    client_id: str
    fee_bps: int
    branches: tuple[Branch, ...]
    source_hash: str
    locator: str
    verified: bool
    currency: str | None = None
    rounding: str = HALF_UP
    metadata: Mapping[str, Any] = None

    def __post_init__(self) -> None:
        for name in ("agreement_id", "client_id", "source_hash", "locator"):
            _text(name, getattr(self, name))
        if type(self.fee_bps) is not int or not 0 <= self.fee_bps <= 10000:
            raise ValueError("fee_bps must be an integer from 0 through 10000")
        if not isinstance(self.branches, tuple) or not self.branches:
            raise ValueError("fee agreement must explicitly scope at least one branch")
        if not all(isinstance(branch, Branch) for branch in self.branches):
            raise ValueError("fee agreement branches must be RecoveryWorks Branch values")
        if len(set(self.branches)) != len(self.branches):
            raise ValueError("fee agreement branches must be unique")
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        if self.currency is not None:
            _text("currency", self.currency)
        if self.rounding not in {HALF_UP, FLOOR}:
            raise ValueError("rounding must be HALF_UP or FLOOR")
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})
        elif not isinstance(self.metadata, Mapping):
            raise ValueError("metadata must be a mapping")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "agreement_id": self.agreement_id,
            "client_id": self.client_id,
            "fee_bps": self.fee_bps,
            "branches": sorted(branch.value for branch in self.branches),
            "source_hash": self.source_hash,
            "locator": self.locator,
            "verified": self.verified,
            "currency": self.currency,
            "rounding": self.rounding,
            "metadata": dict(self.metadata),
        })


@dataclass(frozen=True)
class FeeAssessment:
    agreement: FeeAgreement
    recovered_cents: int
    fee_cents: int

    def __post_init__(self) -> None:
        if not isinstance(self.agreement, FeeAgreement):
            raise ValueError("agreement must be FeeAgreement")
        if type(self.recovered_cents) is not int or self.recovered_cents <= 0:
            raise ValueError("recovered_cents must be positive integer cents")
        if type(self.fee_cents) is not int or self.fee_cents < 0:
            raise ValueError("fee_cents must be non-negative integer cents")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "agreement_hash": self.agreement.proof_hash,
            "recovered_cents": self.recovered_cents,
            "fee_cents": self.fee_cents,
        })


def calculate_fee_cents(recovered_cents: int, fee_bps: int, rounding: str = HALF_UP) -> int:
    if type(recovered_cents) is not int or recovered_cents <= 0:
        raise ValueError("recovered_cents must be positive integer cents")
    if type(fee_bps) is not int or not 0 <= fee_bps <= 10000:
        raise ValueError("fee_bps must be an integer from 0 through 10000")
    numerator = recovered_cents * fee_bps
    if rounding == HALF_UP:
        return (numerator + 5000) // 10000
    if rounding == FLOOR:
        return numerator // 10000
    raise ValueError("rounding must be HALF_UP or FLOOR")


def assess_fee(
    finding: RecoveryFinding,
    recovered_cents: int,
    agreement: FeeAgreement,
) -> FeeAssessment:
    if not isinstance(finding, RecoveryFinding):
        raise ValueError("finding must be RecoveryFinding")
    if not agreement.verified:
        raise ValueError("fee agreement must be verified")
    if agreement.client_id != finding.client_id:
        raise ValueError("fee agreement client does not match finding")
    if finding.branch not in agreement.branches:
        raise ValueError("fee agreement does not cover finding branch")
    if agreement.currency is not None and agreement.currency != finding.currency:
        raise ValueError("fee agreement currency does not match finding")
    if recovered_cents > finding.potential_recovery_cents:
        raise ValueError("recovered amount cannot exceed validated potential recovery")

    fee_cents = calculate_fee_cents(
        recovered_cents,
        agreement.fee_bps,
        agreement.rounding,
    )
    return FeeAssessment(
        agreement=agreement,
        recovered_cents=recovered_cents,
        fee_cents=fee_cents,
    )
