"""Verified before/after evidence for realized cloud savings.

Prospective recommendations remain estimates. Realized savings are recognized
only when a savings signal is bound to an approved remediation envelope,
independent implementation evidence, a verified pre-change baseline, a verified
post-change observation, and a reviewed normalization method.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from typing import Any

from recoveryworks.models import (
    canonical_hash,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)
from .cloud_remediation import (
    CloudRemediationAction,
    CloudRemediationApproval,
    CloudRemediationEnvelope,
    CloudRemediationPlan,
)
from .cloud_signals import CloudSignal, CloudSignalType


class SavingsNormalizationMode(str, Enum):
    FIXED_SCOPE = "FIXED_SCOPE"
    ACTIVITY_RATIO = "ACTIVITY_RATIO"


class SavingsEvidenceState(str, Enum):
    REVIEW = "REVIEW"
    VERIFIED = "VERIFIED"


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


def _iso_date(name: str, value: str) -> str:
    raw = _text(name, value)
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _cents(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be non-negative integer cents")
    return value


def _activity(name: str, value: str | None, *, required: bool = False) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValueError(f"{name} is required")
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if amount < 0:
        raise ValueError(f"{name} must be non-negative")
    if required and amount <= 0:
        raise ValueError(f"{name} must be positive")
    return str(amount)


@dataclass(frozen=True)
class CloudSavingsBaseline:
    signal_id: str
    signal_proof_hash: str
    period_start: str
    period_end: str
    cost_cents: int
    activity_units: str | None
    source_hash: str
    source_locator: str
    verified: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "signal_id", _text("signal_id", self.signal_id))
        object.__setattr__(
            self,
            "signal_proof_hash",
            normalize_sha256("signal_proof_hash", self.signal_proof_hash),
        )
        start = _iso_date("period_start", self.period_start)
        end = _iso_date("period_end", self.period_end)
        if end < start:
            raise ValueError("baseline period_end cannot predate period_start")
        object.__setattr__(self, "period_start", start)
        object.__setattr__(self, "period_end", end)
        _cents("cost_cents", self.cost_cents)
        object.__setattr__(
            self, "activity_units", _activity("activity_units", self.activity_units)
        )
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        object.__setattr__(
            self, "source_locator", _text("source_locator", self.source_locator)
        )
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class CloudSavingsImplementationEvidence:
    action_id: str
    envelope_proof_hash: str
    implemented_at: str
    source_hash: str
    source_locator: str
    verified: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "action_id", _text("action_id", self.action_id))
        object.__setattr__(
            self,
            "envelope_proof_hash",
            normalize_sha256("envelope_proof_hash", self.envelope_proof_hash),
        )
        object.__setattr__(
            self,
            "implemented_at",
            normalize_utc_timestamp("implemented_at", self.implemented_at),
        )
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        object.__setattr__(
            self, "source_locator", _text("source_locator", self.source_locator)
        )
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class CloudSavingsPostObservation:
    signal_id: str
    period_start: str
    period_end: str
    cost_cents: int
    activity_units: str | None
    source_hash: str
    source_locator: str
    verified: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "signal_id", _text("signal_id", self.signal_id))
        start = _iso_date("period_start", self.period_start)
        end = _iso_date("period_end", self.period_end)
        if end < start:
            raise ValueError("post period_end cannot predate period_start")
        object.__setattr__(self, "period_start", start)
        object.__setattr__(self, "period_end", end)
        _cents("cost_cents", self.cost_cents)
        object.__setattr__(
            self, "activity_units", _activity("activity_units", self.activity_units)
        )
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        object.__setattr__(
            self, "source_locator", _text("source_locator", self.source_locator)
        )
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class CloudSavingsNormalizationReview:
    mode: SavingsNormalizationMode
    reviewer_id: str
    scope_unchanged: bool
    source_hash: str
    source_locator: str
    verified: bool

    def __post_init__(self) -> None:
        if not isinstance(self.mode, SavingsNormalizationMode):
            raise ValueError("mode must be a SavingsNormalizationMode")
        object.__setattr__(self, "reviewer_id", _text("reviewer_id", self.reviewer_id))
        if type(self.scope_unchanged) is not bool:
            raise ValueError("scope_unchanged must be boolean")
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        object.__setattr__(
            self, "source_locator", _text("source_locator", self.source_locator)
        )
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        if self.mode is SavingsNormalizationMode.FIXED_SCOPE and not self.scope_unchanged:
            raise ValueError("FIXED_SCOPE normalization requires reviewed unchanged scope")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "mode": self.mode.value,
            "reviewer_id": self.reviewer_id,
            "scope_unchanged": self.scope_unchanged,
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": self.verified,
        })


@dataclass(frozen=True)
class CloudSavingsMeasurement:
    measurement_id: str
    signal_id: str
    signal_proof_hash: str
    action_id: str
    baseline_proof_hash: str
    implementation_proof_hash: str
    post_proof_hash: str
    normalization_proof_hash: str
    normalization_mode: SavingsNormalizationMode
    normalized_baseline_cost_cents: int
    post_cost_cents: int
    realized_savings_cents: int
    state: SavingsEvidenceState
    evidence_verified: bool

    def __post_init__(self) -> None:
        for name in (
            "signal_id",
            "action_id",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "signal_proof_hash",
            "baseline_proof_hash",
            "implementation_proof_hash",
            "post_proof_hash",
            "normalization_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        for name in (
            "normalized_baseline_cost_cents",
            "post_cost_cents",
            "realized_savings_cents",
        ):
            _cents(name, getattr(self, name))
        if not isinstance(self.normalization_mode, SavingsNormalizationMode):
            raise ValueError("invalid normalization_mode")
        if not isinstance(self.state, SavingsEvidenceState):
            raise ValueError("invalid savings evidence state")
        if type(self.evidence_verified) is not bool:
            raise ValueError("evidence_verified must be boolean")
        if self.state is SavingsEvidenceState.VERIFIED and not self.evidence_verified:
            raise ValueError("VERIFIED savings requires verified evidence")
        expected = "cloud-realized-savings:" + canonical_hash(self._identity())
        if self.measurement_id != expected:
            raise ValueError("measurement_id does not bind the measurement payload")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "signal_id": self.signal_id,
            "signal_proof_hash": self.signal_proof_hash,
            "action_id": self.action_id,
            "baseline_proof_hash": self.baseline_proof_hash,
            "implementation_proof_hash": self.implementation_proof_hash,
            "post_proof_hash": self.post_proof_hash,
            "normalization_proof_hash": self.normalization_proof_hash,
            "normalization_mode": self.normalization_mode.value,
            "normalized_baseline_cost_cents": self.normalized_baseline_cost_cents,
            "post_cost_cents": self.post_cost_cents,
            "realized_savings_cents": self.realized_savings_cents,
            "state": self.state.value,
            "evidence_verified": self.evidence_verified,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "measurement_id": self.measurement_id,
            "proof_hash": self.proof_hash,
        }


def _period_days(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days + 1


def measure_realized_cloud_savings(
    *,
    signal: CloudSignal,
    action: CloudRemediationAction,
    plan: CloudRemediationPlan,
    approval: CloudRemediationApproval,
    envelope: CloudRemediationEnvelope,
    baseline: CloudSavingsBaseline,
    implementation: CloudSavingsImplementationEvidence,
    post: CloudSavingsPostObservation,
    normalization: CloudSavingsNormalizationReview,
) -> CloudSavingsMeasurement:
    if signal.signal_type is not CloudSignalType.SAVINGS_OPPORTUNITY:
        raise ValueError("realized savings requires a SAVINGS_OPPORTUNITY signal")
    if baseline.signal_id != signal.signal_id or baseline.signal_proof_hash != signal.proof_hash:
        raise ValueError("baseline does not bind the savings signal")
    if post.signal_id != signal.signal_id:
        raise ValueError("post observation does not bind the savings signal")
    if action.signal_id != signal.signal_id or action.source_signal_hash != signal.proof_hash:
        raise ValueError("remediation action does not bind the savings signal")
    if action not in plan.actions:
        raise ValueError("remediation action is not present in the approved plan")
    if approval.plan_id != plan.plan_id or approval.plan_proof_hash != plan.proof_hash:
        raise ValueError("remediation approval does not bind the plan")
    if action.action_id not in approval.approved_action_ids:
        raise ValueError("remediation action was not approved")
    if (
        envelope.action_id != action.action_id
        or envelope.plan_id != plan.plan_id
        or envelope.approval_hash != approval.proof_hash
    ):
        raise ValueError("remediation envelope does not bind the approved action")
    if implementation.action_id != action.action_id:
        raise ValueError("implementation evidence action mismatch")
    if implementation.envelope_proof_hash != envelope.proof_hash:
        raise ValueError("implementation evidence does not bind the remediation envelope")

    implemented_at = datetime.fromisoformat(
        implementation.implemented_at.replace("Z", "+00:00")
    ).date()
    if date.fromisoformat(baseline.period_end) >= implemented_at:
        raise ValueError("baseline must end before implementation")
    if date.fromisoformat(post.period_start) <= implemented_at:
        raise ValueError("post observation must start after implementation")
    if _period_days(baseline.period_start, baseline.period_end) != _period_days(
        post.period_start, post.period_end
    ):
        raise ValueError("baseline and post observation windows must have equal duration")

    if normalization.mode is SavingsNormalizationMode.FIXED_SCOPE:
        normalized_baseline = baseline.cost_cents
    else:
        baseline_activity = Decimal(
            _activity("baseline.activity_units", baseline.activity_units, required=True)
        )
        post_activity = Decimal(
            _activity("post.activity_units", post.activity_units, required=True)
        )
        raw = Decimal(baseline.cost_cents) * post_activity / baseline_activity
        normalized_baseline = int(
            raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )

    realized = max(normalized_baseline - post.cost_cents, 0)
    evidence_verified = all((
        baseline.verified,
        implementation.verified,
        post.verified,
        normalization.verified,
    ))
    state = (
        SavingsEvidenceState.VERIFIED
        if evidence_verified
        else SavingsEvidenceState.REVIEW
    )
    identity = {
        "schema": 1,
        "signal_id": signal.signal_id,
        "signal_proof_hash": signal.proof_hash,
        "action_id": action.action_id,
        "baseline_proof_hash": baseline.proof_hash,
        "implementation_proof_hash": implementation.proof_hash,
        "post_proof_hash": post.proof_hash,
        "normalization_proof_hash": normalization.proof_hash,
        "normalization_mode": normalization.mode.value,
        "normalized_baseline_cost_cents": normalized_baseline,
        "post_cost_cents": post.cost_cents,
        "realized_savings_cents": realized,
        "state": state.value,
        "evidence_verified": evidence_verified,
    }
    return CloudSavingsMeasurement(
        measurement_id="cloud-realized-savings:" + canonical_hash(identity),
        signal_id=signal.signal_id,
        signal_proof_hash=signal.proof_hash,
        action_id=action.action_id,
        baseline_proof_hash=baseline.proof_hash,
        implementation_proof_hash=implementation.proof_hash,
        post_proof_hash=post.proof_hash,
        normalization_proof_hash=normalization.proof_hash,
        normalization_mode=normalization.mode,
        normalized_baseline_cost_cents=normalized_baseline,
        post_cost_cents=post.cost_cents,
        realized_savings_cents=realized,
        state=state,
        evidence_verified=evidence_verified,
    )
