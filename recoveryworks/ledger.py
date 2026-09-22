"""Recovery Ledger: auditable lifecycle for every potential recovered dollar."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Mapping

from .models import CaseState, FindingState, RecoveryFinding, canonical_hash
from .policies import assert_claim_authorizable


@dataclass(frozen=True)
class LedgerRecord:
    finding: RecoveryFinding
    case_state: CaseState
    reviewer_approved: bool = False
    reviewer_id: str | None = None
    review_note: str | None = None
    authorization_id: str | None = None
    recovered_cents: int = 0
    fee_cents: int = 0
    updated_at: str | None = None

    @property
    def record_hash(self) -> str:
        payload = asdict(self)
        payload["finding"]["branch"] = self.finding.branch.value
        payload["finding"]["mode"] = self.finding.mode.value
        payload["finding"]["state"] = self.finding.state.value
        payload["case_state"] = self.case_state.value
        return canonical_hash(payload)


@dataclass(frozen=True)
class LedgerEvent:
    sequence: int
    finding_id: str
    action: str
    prior_state: str | None
    new_state: str
    actor_id: str | None
    note: str | None
    at: str
    previous_event_hash: str | None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def event_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "sequence": self.sequence,
            "finding_id": self.finding_id,
            "action": self.action,
            "prior_state": self.prior_state,
            "new_state": self.new_state,
            "actor_id": self.actor_id,
            "note": self.note,
            "at": self.at,
            "previous_event_hash": self.previous_event_hash,
            "metadata": dict(self.metadata),
        })


class RecoveryLedger:
    def __init__(self) -> None:
        self._records: dict[str, LedgerRecord] = {}
        self._proof_index: dict[str, str] = {}
        self._events: list[LedgerEvent] = []

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    def _append_event(
        self,
        *,
        record: LedgerRecord,
        action: str,
        prior_state: CaseState | None,
        actor_id: str | None = None,
        note: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> LedgerEvent:
        previous = self._events[-1].event_hash if self._events else None
        event = LedgerEvent(
            sequence=len(self._events) + 1,
            finding_id=record.finding.finding_id,
            action=action,
            prior_state=prior_state.value if prior_state else None,
            new_state=record.case_state.value,
            actor_id=actor_id,
            note=note,
            at=record.updated_at or self._now(),
            previous_event_hash=previous,
            metadata=dict(metadata or {}),
        )
        self._events.append(event)
        return event

    def add(self, finding: RecoveryFinding) -> LedgerRecord:
        existing_id = self._proof_index.get(finding.proof_hash)
        if existing_id:
            return self._records[existing_id]
        if finding.finding_id in self._records:
            raise ValueError("finding_id already exists with different proof")
        state = CaseState.VALIDATED if finding.state is FindingState.VALIDATED else CaseState.REVIEW
        record = LedgerRecord(finding=finding, case_state=state, updated_at=self._now())
        self._records[finding.finding_id] = record
        self._proof_index[finding.proof_hash] = finding.finding_id
        self._append_event(record=record, action="ADDED", prior_state=None, actor_id="system")
        return record

    def get(self, finding_id: str) -> LedgerRecord:
        try:
            return self._records[finding_id]
        except KeyError as exc:
            raise KeyError(f"unknown finding_id: {finding_id}") from exc

    def approve(self, finding_id: str, reviewer_id: str, note: str) -> LedgerRecord:
        if not reviewer_id.strip() or not note.strip():
            raise ValueError("reviewer_id and review note are required")
        record = self.get(finding_id)
        if record.case_state is not CaseState.VALIDATED:
            raise ValueError("only VALIDATED cases may be approved")
        if record.reviewer_approved:
            if record.reviewer_id == reviewer_id.strip() and record.review_note == note.strip():
                return record
            raise ValueError("case is already approved")
        assert_claim_authorizable(record.finding, True)
        updated = replace(
            record,
            reviewer_approved=True,
            reviewer_id=reviewer_id.strip(),
            review_note=note.strip(),
            updated_at=self._now(),
        )
        self._records[finding_id] = updated
        self._append_event(
            record=updated,
            action="APPROVED",
            prior_state=record.case_state,
            actor_id=reviewer_id.strip(),
            note=note.strip(),
        )
        return updated

    def authorize(self, finding_id: str, authorization_id: str) -> LedgerRecord:
        if not authorization_id.strip():
            raise ValueError("authorization_id is required")
        record = self.get(finding_id)
        if record.case_state is CaseState.AUTHORIZED:
            if record.authorization_id == authorization_id.strip():
                return record
            raise ValueError("case already has a different authorization")
        if record.case_state is not CaseState.VALIDATED:
            raise ValueError("only VALIDATED cases may be authorized")
        assert_claim_authorizable(record.finding, record.reviewer_approved)
        updated = replace(
            record,
            case_state=CaseState.AUTHORIZED,
            authorization_id=authorization_id.strip(),
            updated_at=self._now(),
        )
        self._records[finding_id] = updated
        self._append_event(
            record=updated,
            action="AUTHORIZED",
            prior_state=record.case_state,
            metadata={"authorization_id": authorization_id.strip()},
        )
        return updated

    def mark_claimed(self, finding_id: str) -> LedgerRecord:
        record = self.get(finding_id)
        if record.case_state is not CaseState.AUTHORIZED or not record.authorization_id:
            raise ValueError("claim action requires explicit authorization")
        updated = replace(record, case_state=CaseState.CLAIMED, updated_at=self._now())
        self._records[finding_id] = updated
        self._append_event(record=updated, action="CLAIMED", prior_state=record.case_state)
        return updated

    def mark_recovered(self, finding_id: str, recovered_cents: int, fee_cents: int = 0) -> LedgerRecord:
        record = self.get(finding_id)
        if record.case_state is not CaseState.CLAIMED:
            raise ValueError("only CLAIMED cases may be marked recovered")
        if type(recovered_cents) is not int or recovered_cents < 0:
            raise ValueError("recovered_cents must be non-negative integer cents")
        if type(fee_cents) is not int or fee_cents < 0 or fee_cents > recovered_cents:
            raise ValueError("fee_cents must be between zero and recovered_cents")
        if recovered_cents > record.finding.potential_recovery_cents:
            raise ValueError("recovered amount cannot exceed validated potential recovery")
        updated = replace(
            record,
            case_state=CaseState.RECOVERED,
            recovered_cents=recovered_cents,
            fee_cents=fee_cents,
            updated_at=self._now(),
        )
        self._records[finding_id] = updated
        self._append_event(
            record=updated,
            action="RECOVERED",
            prior_state=record.case_state,
            metadata={"recovered_cents": recovered_cents, "fee_cents": fee_cents},
        )
        return updated

    def reject(self, finding_id: str, reviewer_id: str, note: str) -> LedgerRecord:
        if not reviewer_id.strip() or not note.strip():
            raise ValueError("reviewer_id and rejection note are required")
        record = self.get(finding_id)
        if record.case_state in {CaseState.CLAIMED, CaseState.RECOVERED}:
            raise ValueError("claimed/recovered cases cannot be rejected")
        updated = replace(
            record,
            case_state=CaseState.REJECTED,
            reviewer_id=reviewer_id.strip(),
            review_note=note.strip(),
            updated_at=self._now(),
        )
        self._records[finding_id] = updated
        self._append_event(
            record=updated,
            action="REJECTED",
            prior_state=record.case_state,
            actor_id=reviewer_id.strip(),
            note=note.strip(),
        )
        return updated

    def records(self) -> tuple[LedgerRecord, ...]:
        return tuple(sorted(self._records.values(), key=lambda r: r.finding.finding_id))

    def events(self, finding_id: str | None = None) -> tuple[LedgerEvent, ...]:
        events = self._events
        if finding_id is not None:
            events = [event for event in events if event.finding_id == finding_id]
        return tuple(events)

    @property
    def audit_head(self) -> str | None:
        return self._events[-1].event_hash if self._events else None

    def verify_event_chain(self) -> bool:
        previous: str | None = None
        for expected_sequence, event in enumerate(self._events, start=1):
            if event.sequence != expected_sequence:
                return False
            if event.previous_event_hash != previous:
                return False
            previous = event.event_hash
        return True

    @property
    def snapshot_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "record_hashes": sorted(record.record_hash for record in self.records()),
            "audit_head": self.audit_head,
        })

    def rollup(self) -> dict:
        branches: dict[str, dict[str, int]] = {}
        total_potential = total_validated = total_recovered = total_fees = 0
        for record in self.records():
            key = record.finding.branch.value
            bucket = branches.setdefault(key, {
                "cases": 0,
                "potential_cents": 0,
                "validated_cents": 0,
                "recovered_cents": 0,
                "fee_cents": 0,
            })
            potential = record.finding.potential_recovery_cents
            validated = potential if record.finding.state is FindingState.VALIDATED else 0
            bucket["cases"] += 1
            bucket["potential_cents"] += potential
            bucket["validated_cents"] += validated
            bucket["recovered_cents"] += record.recovered_cents
            bucket["fee_cents"] += record.fee_cents
            total_potential += potential
            total_validated += validated
            total_recovered += record.recovered_cents
            total_fees += record.fee_cents
        return {
            "branches": branches,
            "totals": {
                "cases": len(self._records),
                "potential_cents": total_potential,
                "validated_cents": total_validated,
                "recovered_cents": total_recovered,
                "fee_cents": total_fees,
            },
        }
