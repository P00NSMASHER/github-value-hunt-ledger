"""UtilityRecovery adapter for tariff-backed bill recalculation."""
from __future__ import annotations

from typing import Any, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef
from .common import observation


def from_utility_variance(
    *,
    client_id: str,
    utility_id: str,
    bill_id: str,
    bill_date: str,
    expected_cents: int,
    billed_cents: int,
    rule: RuleRef | None,
    evidence: tuple[EvidenceRef, ...],
    currency: str = "USD",
    reason: str = "UTILITY_TARIFF_VARIANCE",
    confidence_basis: str = "deterministic effective-dated tariff calculation",
    metadata: Mapping[str, Any] | None = None,
) -> RecoveryObservation:
    return observation(
        branch=Branch.UTILITY,
        client_id=client_id,
        counterparty_id=utility_id,
        reference=bill_id,
        currency=currency,
        expected_cents=expected_cents,
        actual_cents=billed_cents,
        occurred_on=bill_date,
        rule=rule,
        evidence=evidence,
        reason=reason,
        confidence_basis=confidence_basis,
        metadata=metadata,
    )
