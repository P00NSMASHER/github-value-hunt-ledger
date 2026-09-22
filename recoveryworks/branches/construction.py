"""ConstructionRecovery adapter for reviewed change/delay entitlement amounts."""
from __future__ import annotations

from typing import Any, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef
from .common import observation


def from_construction_entitlement(
    *,
    client_id: str,
    counterparty_id: str,
    event_id: str,
    event_date: str,
    entitled_cents: int,
    paid_cents: int,
    rule: RuleRef | None,
    evidence: tuple[EvidenceRef, ...],
    currency: str = "USD",
    reason: str = "UNPAID_CONSTRUCTION_ENTITLEMENT",
    confidence_basis: str = "reviewed contract entitlement + deterministic schedule/cost analysis",
    metadata: Mapping[str, Any] | None = None,
) -> RecoveryObservation:
    return observation(
        branch=Branch.CONSTRUCTION,
        client_id=client_id,
        counterparty_id=counterparty_id,
        reference=event_id,
        currency=currency,
        expected_cents=entitled_cents,
        actual_cents=paid_cents,
        occurred_on=event_date,
        rule=rule,
        evidence=evidence,
        reason=reason,
        confidence_basis=confidence_basis,
        metadata=metadata,
    )
