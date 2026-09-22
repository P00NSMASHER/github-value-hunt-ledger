"""Recovery Ledger: auditable lifecycle for every potential recovered dollar."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone

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


class RecoveryLedger:
    def __init__(self) -> None:
        self._records: dict[str, LedgerRecord] = {}
        self._proof_index: dict[str, str] = {}

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

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
        assert_claim_authorizable(record.finding, True)
        updated = replace(
            record,
            reviewer_approved=True,
            reviewer_id=reviewer_id.strip(),
            review_note=note.strip(),
            updated_at=self._now(),
        )
        self._records[finding_id] = updated
        return updated

    def authorize(self, finding_id: str, authorization_id: str) -> LedgerRecord:
        if not authorization_id.strip():
            raise ValueError("authorization_id is required")
        record = self.get(finding_id)
        assert_claim_authorizable(record.finding, record.reviewer_approved)
        updated = replace(
            record,
            case_state=CaseState.AUTHORIZED,
            authorization_id=authorization_id.strip(),
            updated_at=self._now(),
        )
        self._records[finding_id] = updated
        return updated

    def mark_claimed(self, finding_id: str) -> LedgerRecord:
        record = self.get(finding_id)
        if record.case_state is not CaseState.AUTHORIZED or not record.authorization_id:
            raise ValueError("claim action requires explicit authorization")
        updated = replace(record, case_state=CaseState.CLAIMED, updated_at=self._now())
        self._records[finding_id] = updated
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
        return updated

    def records(self) -> tuple[LedgerRecord, ...]:
        return tuple(sorted(self._records.values(), key=lambda r: r.finding.finding_id))

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
