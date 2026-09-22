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
    canonical_hash,
)
from .policies import policy_for
from .source_coverage import SourceCoverageReceipt, coverage_blockers, coverage_is_conclusive


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
    source_coverage: tuple[SourceCoverageReceipt, ...] = ()


class RecoveryEngine:
    """Convert normalized branch observations into proof-bound findings.

    This class never interprets natural-language source documents and never uses
    an LLM for arithmetic. Upstream branch adapters may extract candidate rules,
    but only a verified controlling rule, verified evidence, and any explicitly
    supplied conclusive source-coverage receipts can produce VALIDATED dollars.
    """

    def evaluate(self, observation: RecoveryObservation) -> RecoveryFinding | None:
        policy = policy_for(observation.branch)
        mode = policy.mode
        if mode is RecoveryMode.OVERPAYMENT:
            recovery = max(observation.actual_cents - observation.expected_cents, 0)
        else:
            recovery = max(observation.expected_cents - observation.actual_cents, 0)
        if recovery <= 0:
            return None

        coverage_ok = coverage_is_conclusive(observation.source_coverage)
        verified = (
            observation.rule is not None
            and observation.rule.verified_controlling
            and bool(observation.evidence)
            and all(ref.verified for ref in observation.evidence)
            and coverage_ok
        )
        state = FindingState.VALIDATED if verified else FindingState.REVIEW
        coverage_hashes = sorted(receipt.proof_hash for receipt in observation.source_coverage)
        identity = {
            "schema": 2 if observation.source_coverage else 1,
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
        if observation.source_coverage:
            identity["source_coverage_hashes"] = coverage_hashes
        finding_id = f"rw:{observation.branch.value}:" + canonical_hash(identity)
        metadata = dict(observation.metadata)
        if observation.source_coverage:
            metadata["source_coverage_hashes"] = coverage_hashes
            blockers = coverage_blockers(observation.source_coverage)
            if blockers:
                metadata["source_coverage_blockers"] = list(blockers)

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
            metadata=metadata,
        )

    def scan(self, observations: Iterable[RecoveryObservation]) -> tuple[RecoveryFinding, ...]:
        findings = [finding for item in observations if (finding := self.evaluate(item)) is not None]
        return tuple(sorted(findings, key=lambda f: (f.branch.value, f.finding_id)))
