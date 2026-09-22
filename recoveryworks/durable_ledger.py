"""Durable RecoveryLedger wrapper with replayable lifecycle history."""
from __future__ import annotations

from typing import Any, Mapping

from .journal import RecoveryJournal, finding_from_payload, finding_to_payload
from .ledger import RecoveryLedger
from .models import RecoveryFinding


class DurableRecoveryLedger(RecoveryLedger):
    """RecoveryLedger plus an append-only tamper-evident lifecycle journal.

    The public lifecycle API stays compatible with RecoveryLedger. Persistence
    can store export_bundle() in any private durable backend and reconstruct the
    exact logical state with from_bundle().
    """

    def __init__(self) -> None:
        super().__init__()
        self.journal = RecoveryJournal()

    def add(self, finding: RecoveryFinding):
        existed = finding.proof_hash in self._proof_index
        record = super().add(finding)
        if not existed:
            self.journal.append("ADD", finding.finding_id, {
                "finding": finding_to_payload(finding),
            })
        return record

    def approve(self, finding_id: str, reviewer_id: str, note: str):
        record = super().approve(finding_id, reviewer_id, note)
        self.journal.append("APPROVE", finding_id, {
            "reviewer_id": record.reviewer_id,
            "review_note": record.review_note,
        })
        return record

    def authorize(self, finding_id: str, authorization_id: str):
        record = super().authorize(finding_id, authorization_id)
        self.journal.append("AUTHORIZE", finding_id, {
            "authorization_id": record.authorization_id,
        })
        return record

    def mark_claimed(self, finding_id: str):
        record = super().mark_claimed(finding_id)
        self.journal.append("CLAIM", finding_id, {})
        return record

    def mark_recovered(self, finding_id: str, recovered_cents: int, fee_cents: int = 0):
        record = super().mark_recovered(finding_id, recovered_cents, fee_cents)
        self.journal.append("RECOVER", finding_id, {
            "recovered_cents": recovered_cents,
            "fee_cents": fee_cents,
        })
        return record

    def reject(self, finding_id: str, reviewer_id: str, note: str):
        record = super().reject(finding_id, reviewer_id, note)
        self.journal.append("REJECT", finding_id, {
            "reviewer_id": record.reviewer_id,
            "review_note": record.review_note,
        })
        return record

    def export_bundle(self) -> dict[str, Any]:
        self.journal.verify()
        return {
            "schema": 1,
            "journal": self.journal.export(),
            "rollup": self.rollup(),
        }

    @classmethod
    def from_bundle(cls, payload: Mapping[str, Any]) -> "DurableRecoveryLedger":
        if payload.get("schema") != 1:
            raise ValueError("unsupported durable ledger schema")
        journal = RecoveryJournal.from_export(payload["journal"])
        ledger = cls()

        for event in journal.events():
            action = event.action
            data = event.payload
            if action == "ADD":
                ledger.add(finding_from_payload(data["finding"]))
            elif action == "APPROVE":
                ledger.approve(event.finding_id, data["reviewer_id"], data["review_note"])
            elif action == "AUTHORIZE":
                ledger.authorize(event.finding_id, data["authorization_id"])
            elif action == "CLAIM":
                ledger.mark_claimed(event.finding_id)
            elif action == "RECOVER":
                ledger.mark_recovered(
                    event.finding_id,
                    data["recovered_cents"],
                    data.get("fee_cents", 0),
                )
            elif action == "REJECT":
                ledger.reject(event.finding_id, data["reviewer_id"], data["review_note"])
            else:
                raise ValueError(f"unsupported journal action: {action}")

        if ledger.journal.head_hash != journal.head_hash:
            raise ValueError("replayed journal head does not match source")
        expected_rollup = payload.get("rollup")
        if expected_rollup is not None and ledger.rollup() != expected_rollup:
            raise ValueError("replayed ledger rollup mismatch")
        return ledger
