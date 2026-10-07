"""Human-review cockpit primitives for RecoveryOS phase 0.

Machine confidence never substitutes for the reviewer.  This module only
prioritizes cases and records immutable human dispositions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable

from freight.contracts import canonical_hash

DECISIONS = {"CONFIRM", "REJECT", "NEED_EVIDENCE", "MODIFY_RULE", "ESCALATE"}
MAX_PPM = 1_000_000


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    value = value.strip()
    if any(ord(ch) < 32 for ch in value):
        raise ValueError(f"{name} contains control characters")
    return value


def _ppm(name: str, value: int) -> int:
    if type(value) is not int or not 0 <= value <= MAX_PPM:
        raise ValueError(f"{name} must be an integer in [0, 1000000]")
    return value


def _cents(name: str, value: int) -> int:
    if type(value) is not int or not 0 <= value <= 2**63 - 1:
        raise ValueError(f"{name} must be non-negative integer cents")
    return value


def _timestamp(name: str, value: str) -> str:
    value = _text(name, value)
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be timezone-aware ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware ISO-8601")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class ReviewCase:
    case_id: str
    record_hash: str
    amount_cents: int
    confidence_ppm: int
    novelty_ppm: int
    downstream_risk_ppm: int
    blocker_codes: tuple[str, ...]
    evidence_hashes: tuple[str, ...]
    case_hash: str

    @property
    def uncertainty_ppm(self) -> int:
        return MAX_PPM - self.confidence_ppm

    @property
    def priority_score(self) -> int:
        # Materiality multiplied by a conservative three-factor review pressure.
        pressure = self.uncertainty_ppm + self.novelty_ppm + self.downstream_risk_ppm
        return self.amount_cents * pressure


@dataclass(frozen=True)
class ReviewQueue:
    items: tuple[ReviewCase, ...]
    queue_hash: str


@dataclass(frozen=True)
class HumanDisposition:
    case_hash: str
    reviewer_id: str
    decision: str
    reason: str
    decided_at: str
    corrected_expected_cents: int | None
    rule_candidate: str | None
    disposition_hash: str


def make_case(
    *,
    case_id: str,
    record_hash: str,
    amount_cents: int,
    confidence_ppm: int,
    novelty_ppm: int,
    downstream_risk_ppm: int,
    blocker_codes: Iterable[str] = (),
    evidence_hashes: Iterable[str] = (),
) -> ReviewCase:
    case_id = _text("case_id", case_id)
    record_hash = _text("record_hash", record_hash)
    amount_cents = _cents("amount_cents", amount_cents)
    confidence_ppm = _ppm("confidence_ppm", confidence_ppm)
    novelty_ppm = _ppm("novelty_ppm", novelty_ppm)
    downstream_risk_ppm = _ppm("downstream_risk_ppm", downstream_risk_ppm)
    blockers = tuple(sorted({_text("blocker_code", x) for x in blocker_codes}))
    evidence = tuple(sorted({_text("evidence_hash", x) for x in evidence_hashes}))
    body = {
        "schema": 1,
        "case_id": case_id,
        "record_hash": record_hash,
        "amount_cents": amount_cents,
        "confidence_ppm": confidence_ppm,
        "novelty_ppm": novelty_ppm,
        "downstream_risk_ppm": downstream_risk_ppm,
        "blocker_codes": blockers,
        "evidence_hashes": evidence,
    }
    return ReviewCase(
        case_id=case_id,
        record_hash=record_hash,
        amount_cents=amount_cents,
        confidence_ppm=confidence_ppm,
        novelty_ppm=novelty_ppm,
        downstream_risk_ppm=downstream_risk_ppm,
        blocker_codes=blockers,
        evidence_hashes=evidence,
        case_hash=canonical_hash(body),
    )


def build_queue(cases: Iterable[ReviewCase]) -> ReviewQueue:
    normalized = tuple(cases)
    if len({x.case_id for x in normalized}) != len(normalized):
        raise ValueError("duplicate case_id")
    if len({x.case_hash for x in normalized}) != len(normalized):
        raise ValueError("duplicate case_hash")
    ordered = tuple(sorted(
        normalized,
        key=lambda x: (-x.priority_score, -x.amount_cents, x.case_id),
    ))
    return ReviewQueue(
        items=ordered,
        queue_hash=canonical_hash({
            "schema": 1,
            "case_hashes": [x.case_hash for x in ordered],
        }),
    )


def record_disposition(
    case: ReviewCase,
    *,
    reviewer_id: str,
    decision: str,
    reason: str,
    decided_at: str,
    corrected_expected_cents: int | None = None,
    rule_candidate: str | None = None,
) -> HumanDisposition:
    reviewer_id = _text("reviewer_id", reviewer_id)
    reason = _text("reason", reason)
    decision = _text("decision", decision).upper()
    if decision not in DECISIONS:
        raise ValueError("unsupported review decision")
    decided_at = _timestamp("decided_at", decided_at)
    if corrected_expected_cents is not None:
        corrected_expected_cents = _cents("corrected_expected_cents", corrected_expected_cents)
    if decision == "MODIFY_RULE":
        rule_candidate = _text("rule_candidate", rule_candidate)
    elif rule_candidate is not None:
        rule_candidate = _text("rule_candidate", rule_candidate)
    body = {
        "schema": 1,
        "case_hash": case.case_hash,
        "reviewer_id": reviewer_id,
        "decision": decision,
        "reason": reason,
        "decided_at": decided_at,
        "corrected_expected_cents": corrected_expected_cents,
        "rule_candidate": rule_candidate,
    }
    return HumanDisposition(
        case_hash=case.case_hash,
        reviewer_id=reviewer_id,
        decision=decision,
        reason=reason,
        decided_at=decided_at,
        corrected_expected_cents=corrected_expected_cents,
        rule_candidate=rule_candidate,
        disposition_hash=canonical_hash(body),
    )


def export_disposition(disposition: HumanDisposition) -> dict:
    return asdict(disposition)
