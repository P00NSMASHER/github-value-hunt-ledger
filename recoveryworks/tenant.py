"""Client-scoped Recovery Ledger facade.

Use this facade for customer-facing/service-layer operations. It prevents callers
from reading or mutating another client's cases even when all clients share one
underlying RecoveryOS ledger/database.
"""
from __future__ import annotations

from typing import Any

from .authorization import (
    AuthorizationRevocation,
    RecoveryActionAuthorization,
    RecoveryActionType,
)
from .ledger import LedgerRecord
from .models import RecoveryFinding


class ClientRecoveryLedger:
    def __init__(self, backend: Any, client_id: str) -> None:
        if not isinstance(client_id, str) or not client_id.strip():
            raise ValueError("client_id is required")
        self._backend = backend
        self.client_id = client_id.strip()

    def _owned(self, finding_id: str) -> LedgerRecord:
        try:
            record = self._backend.get(finding_id)
        except KeyError:
            raise KeyError("unknown recovery case") from None
        if record.finding.client_id != self.client_id:
            # Do not disclose whether a case exists for another client.
            raise KeyError("unknown recovery case")
        return record

    def add(self, finding: RecoveryFinding) -> LedgerRecord:
        if finding.client_id != self.client_id:
            raise ValueError("finding client_id is outside client ledger scope")
        return self._backend.add(finding)

    def get(self, finding_id: str) -> LedgerRecord:
        return self._owned(finding_id)

    def approve(self, finding_id: str, reviewer_id: str, note: str) -> LedgerRecord:
        self._owned(finding_id)
        return self._backend.approve(finding_id, reviewer_id, note)

    def authorize(
        self,
        finding_id: str,
        authorization: RecoveryActionAuthorization,
        *,
        as_of_date: str,
        revocations: tuple[AuthorizationRevocation, ...] = (),
    ) -> LedgerRecord:
        self._owned(finding_id)
        if authorization.client_id != self.client_id:
            raise ValueError("authorization client_id is outside client ledger scope")
        return self._backend.authorize(
            finding_id,
            authorization,
            as_of_date=as_of_date,
            revocations=revocations,
        )

    def mark_claimed(
        self,
        finding_id: str,
        authorization: RecoveryActionAuthorization,
        *,
        as_of_date: str,
        action_type: RecoveryActionType,
        target_counterparty_id: str,
        recipient_reference_hash: str,
        action_payload_hash: str,
        currency: str,
        requested_cents: int,
        revocations: tuple[AuthorizationRevocation, ...] = (),
    ) -> LedgerRecord:
        self._owned(finding_id)
        if authorization.client_id != self.client_id:
            raise ValueError("authorization client_id is outside client ledger scope")
        return self._backend.mark_claimed(
            finding_id,
            authorization,
            as_of_date=as_of_date,
            action_type=action_type,
            target_counterparty_id=target_counterparty_id,
            recipient_reference_hash=recipient_reference_hash,
            action_payload_hash=action_payload_hash,
            currency=currency,
            requested_cents=requested_cents,
            revocations=revocations,
        )

    def mark_recovered(
        self,
        finding_id: str,
        recovered_cents: int,
        fee_cents: int = 0,
    ) -> LedgerRecord:
        self._owned(finding_id)
        return self._backend.mark_recovered(finding_id, recovered_cents, fee_cents)

    def reject(self, finding_id: str, reviewer_id: str, note: str) -> LedgerRecord:
        self._owned(finding_id)
        return self._backend.reject(finding_id, reviewer_id, note)

    def records(self) -> tuple[LedgerRecord, ...]:
        return self._backend.records(client_id=self.client_id)

    def rollup(self) -> dict:
        return self._backend.rollup(client_id=self.client_id)
