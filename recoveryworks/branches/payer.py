"""PayerRecovery adapter for deterministic reimbursement variances."""
from __future__ import annotations

from typing import Any, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef
from .common import observation


def from_payer_variance(
    *,
    client_id: str,
    payer_id: str,
    claim_id: str,
    service_date: str,
    expected_cents: int,
    paid_cents: int,
    rule: RuleRef | None,
    evidence: tuple[EvidenceRef, ...],
    currency: str = "USD",
    reason: str = "PAYER_UNDERPAYMENT",
    confidence_basis: str = "deterministic reimbursement calculation",
    metadata: Mapping[str, Any] | None = None,
) -> RecoveryObservation:
    return observation(
        branch=Branch.PAYER,
        client_id=client_id,
        counterparty_id=payer_id,
        reference=claim_id,
        currency=currency,
        expected_cents=expected_cents,
        actual_cents=paid_cents,
        occurred_on=service_date,
        rule=rule,
        evidence=evidence,
        reason=reason,
        confidence_basis=confidence_basis,
        metadata=metadata,
    )
