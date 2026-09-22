"""DutyRecovery adapter for tariff/fee overpayment screening."""
from __future__ import annotations

from typing import Any, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef
from .common import observation


def from_duty_variance(
    *,
    client_id: str,
    customs_counterparty_id: str,
    entry_id: str,
    entry_date: str,
    expected_cents: int,
    paid_cents: int,
    rule: RuleRef | None,
    evidence: tuple[EvidenceRef, ...],
    currency: str = "USD",
    reason: str = "DUTY_TARIFF_VARIANCE",
    confidence_basis: str = "deterministic tariff and fee calculation",
    metadata: Mapping[str, Any] | None = None,
) -> RecoveryObservation:
    return observation(
        branch=Branch.DUTY,
        client_id=client_id,
        counterparty_id=customs_counterparty_id,
        reference=entry_id,
        currency=currency,
        expected_cents=expected_cents,
        actual_cents=paid_cents,
        occurred_on=entry_date,
        rule=rule,
        evidence=evidence,
        reason=reason,
        confidence_basis=confidence_basis,
        metadata=metadata,
    )
