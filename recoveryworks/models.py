"""Shared immutable models for RecoveryWorks.

RecoveryOS intentionally separates discovery from validated recoverable dollars.
A finding only becomes VALIDATED when a controlling rule is verified and every
load-bearing evidence reference is verified.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Mapping

MAX_CENTS = 2**63 - 1


class Branch(str, Enum):
    FREIGHT = "freight"
    PAYER = "payer"
    UTILITY = "utility"
    AP = "ap"
    CONSTRUCTION = "construction"
    DUTY = "duty"
    SAAS = "saas"
    TELECOM = "telecom"
    REBATE = "rebate"
    LEASE = "lease"
    TAX = "tax"
    INSURANCE = "insurance"
    CLOUD = "cloud"
    MERCHANT_FEE = "merchant_fee"


class RecoveryMode(str, Enum):
    OVERPAYMENT = "OVERPAYMENT"
    UNDERPAYMENT = "UNDERPAYMENT"


class FindingState(str, Enum):
    REVIEW = "REVIEW"
    VALIDATED = "VALIDATED"


class CaseState(str, Enum):
    DISCOVERED = "DISCOVERED"
    REVIEW = "REVIEW"
    VALIDATED = "VALIDATED"
    AUTHORIZED = "AUTHORIZED"
    CLAIMED = "CLAIMED"
    RECOVERED = "RECOVERED"
    REJECTED = "REJECTED"


def canonical_hash(payload: Mapping[str, Any] | list[Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _required_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _cents(name: str, value: int) -> int:
    if type(value) is not int or not 0 <= value <= MAX_CENTS:
        raise ValueError(f"{name} must be non-negative integer cents")
    return value


@dataclass(frozen=True)
class EvidenceRef:
    evidence_id: str
    source_hash: str
    locator: str
    kind: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("evidence_id", "source_hash", "locator", "kind"):
            _required_text(name, getattr(self, name))
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class RuleRef:
    rule_id: str
    source_hash: str
    effective_from: str
    effective_to: str | None
    verified_controlling: bool
    source_locator: str
    jurisdiction: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("rule_id", "source_hash", "effective_from", "source_locator"):
            _required_text(name, getattr(self, name))
        if type(self.verified_controlling) is not bool:
            raise ValueError("verified_controlling must be boolean")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class RecoveryFinding:
    finding_id: str
    branch: Branch
    client_id: str
    counterparty_id: str
    reference: str
    currency: str
    mode: RecoveryMode
    expected_cents: int
    actual_cents: int
    rule: RuleRef | None
    evidence: tuple[EvidenceRef, ...]
    state: FindingState
    reason: str
    confidence_basis: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "finding_id", "client_id", "counterparty_id", "reference",
            "currency", "reason", "confidence_basis",
        ):
            _required_text(name, getattr(self, name))
        _cents("expected_cents", self.expected_cents)
        _cents("actual_cents", self.actual_cents)
        if not self.evidence:
            raise ValueError("at least one evidence reference is required")
        if self.state is FindingState.VALIDATED:
            if self.rule is None or not self.rule.verified_controlling:
                raise ValueError("validated finding requires verified controlling rule")
            if not all(ref.verified for ref in self.evidence):
                raise ValueError("validated finding requires verified evidence")
            if self.potential_recovery_cents <= 0:
                raise ValueError("validated finding requires positive potential recovery")

    @property
    def potential_recovery_cents(self) -> int:
        if self.mode is RecoveryMode.OVERPAYMENT:
            return max(self.actual_cents - self.expected_cents, 0)
        return max(self.expected_cents - self.actual_cents, 0)

    @property
    def proof_hash(self) -> str:
        payload = {
            "schema": 1,
            "finding_id": self.finding_id,
            "branch": self.branch.value,
            "client_id": self.client_id,
            "counterparty_id": self.counterparty_id,
            "reference": self.reference,
            "currency": self.currency,
            "mode": self.mode.value,
            "expected_cents": self.expected_cents,
            "actual_cents": self.actual_cents,
            "rule_hash": self.rule.proof_hash if self.rule else None,
            "evidence_hashes": sorted(ref.proof_hash for ref in self.evidence),
            "state": self.state.value,
            "reason": self.reason,
            "confidence_basis": self.confidence_basis,
            "metadata": dict(self.metadata),
        }
        return canonical_hash(payload)
