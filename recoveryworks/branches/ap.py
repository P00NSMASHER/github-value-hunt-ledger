"""APRecovery adapter for supplier overpayments and reconciliation leakage."""
from __future__ import annotations

from typing import Any, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef
from .common import observation


def from_ap_variance(
    *,
    client_id: str,
    vendor_id: str,
    transaction_id: str,
    transaction_date: str,
    expected_cents: int,
    paid_cents: int,
    rule: RuleRef | None,
    evidence: tuple[EvidenceRef, ...],
    currency: str = "USD",
    reason: str = "AP_OVERPAYMENT",
    confidence_basis: str = "deterministic AP/payment reconciliation",
    metadata: Mapping[str, Any] | None = None,
) -> RecoveryObservation:
    return observation(
        branch=Branch.AP,
        client_id=client_id,
        counterparty_id=vendor_id,
        reference=transaction_id,
        currency=currency,
        expected_cents=expected_cents,
        actual_cents=paid_cents,
        occurred_on=transaction_date,
        rule=rule,
        evidence=evidence,
        reason=reason,
        confidence_basis=confidence_basis,
        metadata=metadata,
    )
