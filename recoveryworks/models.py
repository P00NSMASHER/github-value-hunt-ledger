"""Shared immutable models for RecoveryWorks.

RecoveryOS intentionally separates discovery from validated recoverable dollars.
A finding only becomes VALIDATED when a controlling rule is verified and every
load-bearing evidence reference is verified.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
import hashlib
import json
import math
import re
from typing import Any, Mapping

MAX_CENTS = 2**63 - 1
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_GIT_SHA1_RE = re.compile(r"[0-9a-f]{40}")
_CURRENCY_RE = re.compile(r"[A-Z]{3}")


class _FrozenDict(dict):
    """JSON-compatible dictionary that cannot change after construction."""

    @staticmethod
    def _immutable(*_args: Any, **_kwargs: Any) -> None:
        raise TypeError("proof metadata is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable

    def __deepcopy__(self, _memo: dict[int, Any]) -> "_FrozenDict":
        return self


class _FrozenList(list):
    """JSON-compatible list that cannot change after construction."""

    @staticmethod
    def _immutable(*_args: Any, **_kwargs: Any) -> None:
        raise TypeError("proof metadata is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    append = _immutable
    clear = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    reverse = _immutable
    sort = _immutable
    __iadd__ = _immutable
    __imul__ = _immutable

    def __deepcopy__(self, _memo: dict[int, Any]) -> "_FrozenList":
        return self


def freeze_json(value: Any, *, name: str = "value") -> Any:
    """Detach and recursively freeze a JSON value used in a proof surface."""
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{name} cannot contain NaN or infinity")
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"{name} object keys must be strings")
            frozen[key] = freeze_json(item, name=f"{name}.{key}")
        return _FrozenDict(frozen)
    if isinstance(value, (list, tuple)):
        return _FrozenList(
            freeze_json(item, name=f"{name}[{index}]")
            for index, item in enumerate(value)
        )
    raise ValueError(f"{name} must contain only JSON-compatible values")


def thaw_json(value: Any) -> Any:
    """Return ordinary detached dict/list containers for public serialization."""
    if isinstance(value, Mapping):
        return {key: thaw_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [thaw_json(item) for item in value]
    return value


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
    PARCEL = "parcel"
    PROCUREMENT = "procurement"
    WARRANTY_CREDIT = "warranty_credit"
    PAYROLL_BENEFIT = "payroll_benefit"


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
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _required_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


def normalize_utc_timestamp(name: str, value: str) -> str:
    """Require an offset-aware instant and return canonical UTC seconds."""
    raw = _required_text(name, value)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must include a UTC offset")
    return (
        parsed.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _iso_date(name: str, value: str) -> str:
    raw = _required_text(name, value)
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO-8601 date") from exc


def _currency(value: str) -> str:
    normalized = _required_text("currency", value).upper()
    if _CURRENCY_RE.fullmatch(normalized) is None:
        raise ValueError("currency must be a three-letter code")
    return normalized


def normalize_sha256(name: str, value: str) -> str:
    """Return a canonical lowercase SHA-256 digest."""
    normalized = _required_text(name, value).lower()
    if _SHA256_RE.fullmatch(normalized) is None:
        raise ValueError(f"{name} must be a 64-character SHA-256 hex digest")
    return normalized


def normalize_source_hash(value: str) -> str:
    """Return a canonical SHA-256 digest for a proof-bearing source."""
    return normalize_sha256("source_hash", value)


def normalize_git_commit_sha(name: str, value: str) -> str:
    """Return a canonical full Git SHA-1 commit identifier.

    GitHub Actions and this repository currently identify source revisions with
    40-hex SHA-1 object IDs. Abbreviations and descriptive placeholders are not
    strong enough for a proof-bearing calculation or build attestation.
    """
    normalized = _required_text(name, value).lower()
    if _GIT_SHA1_RE.fullmatch(normalized) is None:
        raise ValueError(f"{name} must be a full 40-character Git commit SHA")
    return normalized


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
        for name in ("evidence_id", "locator", "kind"):
            object.__setattr__(self, name, _required_text(name, getattr(self, name)))
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        object.__setattr__(self, "metadata", freeze_json(self.metadata, name="metadata"))

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
        for name in ("rule_id", "source_locator"):
            object.__setattr__(self, name, _required_text(name, getattr(self, name)))
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        object.__setattr__(
            self,
            "effective_from",
            _iso_date("effective_from", self.effective_from),
        )
        if self.effective_to is not None:
            effective_to = _iso_date("effective_to", self.effective_to)
            if effective_to < self.effective_from:
                raise ValueError("effective_to cannot predate effective_from")
            object.__setattr__(self, "effective_to", effective_to)
        if self.jurisdiction is not None:
            object.__setattr__(
                self,
                "jurisdiction",
                _required_text("jurisdiction", self.jurisdiction),
            )
        if type(self.verified_controlling) is not bool:
            raise ValueError("verified_controlling must be boolean")
        object.__setattr__(self, "metadata", freeze_json(self.metadata, name="metadata"))

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
            "finding_id", "client_id", "counterparty_id", "reference", "reason",
            "confidence_basis",
        ):
            object.__setattr__(self, name, _required_text(name, getattr(self, name)))
        if not isinstance(self.branch, Branch):
            raise ValueError("branch must be a Branch")
        if not isinstance(self.mode, RecoveryMode):
            raise ValueError("mode must be a RecoveryMode")
        if not isinstance(self.state, FindingState):
            raise ValueError("state must be a FindingState")
        object.__setattr__(self, "currency", _currency(self.currency))
        _cents("expected_cents", self.expected_cents)
        _cents("actual_cents", self.actual_cents)
        if not isinstance(self.evidence, tuple) or not all(
            isinstance(reference, EvidenceRef) for reference in self.evidence
        ):
            raise ValueError("evidence must be a tuple of EvidenceRef values")
        if self.rule is not None and not isinstance(self.rule, RuleRef):
            raise ValueError("rule must be a RuleRef or None")
        if not self.evidence:
            raise ValueError("at least one evidence reference is required")
        object.__setattr__(self, "metadata", freeze_json(self.metadata, name="metadata"))
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


@dataclass(frozen=True)
class SettlementEvidence:
    """Externally verified evidence that money was actually recovered."""

    settlement_id: str
    finding_id: str
    source_hash: str
    source_locator: str
    observed_at: str
    recovered_cents: int
    currency: str
    verified: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("settlement_id", "finding_id", "source_locator"):
            object.__setattr__(self, name, _required_text(name, getattr(self, name)))
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        object.__setattr__(
            self,
            "observed_at",
            normalize_utc_timestamp("observed_at", self.observed_at),
        )
        if _cents("recovered_cents", self.recovered_cents) == 0:
            raise ValueError("recovered_cents must be positive")
        object.__setattr__(self, "currency", _currency(self.currency))
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        object.__setattr__(self, "metadata", freeze_json(self.metadata, name="metadata"))

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})
