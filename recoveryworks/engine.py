"""Deterministic expected-vs-actual recovery engine shared by every branch."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .models import (
    Branch,
    EvidenceRef,
    FindingState,
    RecoveryFinding,
    RecoveryMode,
    RuleRef,
    MAX_CENTS,
    canonical_hash,
)
from .policies import policy_for


@dataclass(frozen=True)
class RecoveryObservation:
    branch: Branch
    client_id: str
    counterparty_id: str
    reference: str
    currency: str
    expected_cents: int
    actual_cents: int
    rule: RuleRef | None
    evidence: tuple[EvidenceRef, ...]
    reason: str
    confidence_basis: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


class RecoveryEngine:
    """Convert normalized branch observations into proof-bound findings.

    This class never interprets natural-language source documents and never uses
    an LLM for arithmetic. Upstream branch adapters may extract candidate rules,
    but only a verified controlling rule can produce VALIDATED dollars.
    """

    @staticmethod
    def _validate_observation(observation: RecoveryObservation) -> None:
        if not isinstance(observation.branch, Branch):
            raise ValueError("branch must be a RecoveryWorks Branch")
        for name in ("client_id", "counterparty_id", "reference", "currency", "reason", "confidence_basis"):
            value = getattr(observation, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        if (
            len(observation.currency) != 3
            or not observation.currency.isalpha()
            or observation.currency != observation.currency.upper()
        ):
            raise ValueError("currency must be a canonical 3-letter uppercase code")
        for name in ("expected_cents", "actual_cents"):
            value = getattr(observation, name)
            if type(value) is not int or not 0 <= value <= MAX_CENTS:
                raise ValueError(f"{name} must be non-negative integer cents")
        if observation.rule is not None and not isinstance(observation.rule, RuleRef):
            raise ValueError("rule must be RuleRef or None")
        if not isinstance(observation.evidence, tuple) or not observation.evidence:
            raise ValueError("at least one evidence reference is required")
        if not all(isinstance(ref, EvidenceRef) for ref in observation.evidence):
            raise ValueError("evidence must contain EvidenceRef objects")

    def evaluate(self, observation: RecoveryObservation) -> RecoveryFinding | None:
        self._validate_observation(observation)
        policy = policy_for(observation.branch)
        mode = policy.mode
        if mode is RecoveryMode.OVERPAYMENT:
            recovery = max(observation.actual_cents - observation.expected_cents, 0)
        else:
            recovery = max(observation.expected_cents - observation.actual_cents, 0)
        if recovery <= 0:
            return None

        verified = (
            observation.rule is not None
            and observation.rule.verified_controlling
            and bool(observation.evidence)
            and all(ref.verified for ref in observation.evidence)
        )
        state = FindingState.VALIDATED if verified else FindingState.REVIEW
        identity = {
            "schema": 1,
            "branch": observation.branch.value,
            "client_id": observation.client_id,
            "counterparty_id": observation.counterparty_id,
            "reference": observation.reference,
            "currency": observation.currency,
            "mode": mode.value,
            "expected_cents": observation.expected_cents,
            "actual_cents": observation.actual_cents,
            "rule_hash": observation.rule.proof_hash if observation.rule else None,
            "evidence_hashes": sorted(ref.proof_hash for ref in observation.evidence),
        }
        finding_id = f"rw:{observation.branch.value}:" + canonical_hash(identity)
        return RecoveryFinding(
            finding_id=finding_id,
            branch=observation.branch,
            client_id=observation.client_id,
            counterparty_id=observation.counterparty_id,
            reference=observation.reference,
            currency=observation.currency,
            mode=mode,
            expected_cents=observation.expected_cents,
            actual_cents=observation.actual_cents,
            rule=observation.rule,
            evidence=observation.evidence,
            state=state,
            reason=observation.reason,
            confidence_basis=observation.confidence_basis,
            metadata=observation.metadata,
        )

    def scan(self, observations: Iterable[RecoveryObservation]) -> tuple[RecoveryFinding, ...]:
        findings = [finding for item in observations if (finding := self.evaluate(item)) is not None]
        return tuple(sorted(findings, key=lambda f: (f.branch.value, f.finding_id)))
