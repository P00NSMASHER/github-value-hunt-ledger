"""Normalized branch adapter contract."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef


@dataclass(frozen=True)
class BranchInput:
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


class RuleBackedAdapter:
    branch: Branch

    def normalize(self, item: BranchInput) -> RecoveryObservation:
        return RecoveryObservation(
            branch=self.branch,
            client_id=item.client_id,
            counterparty_id=item.counterparty_id,
            reference=item.reference,
            currency=item.currency,
            expected_cents=item.expected_cents,
            actual_cents=item.actual_cents,
            rule=item.rule,
            evidence=item.evidence,
            reason=item.reason,
            confidence_basis=item.confidence_basis,
            metadata=item.metadata,
        )
