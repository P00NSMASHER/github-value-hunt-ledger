"""Recovery Ledger: auditable lifecycle for every potential recovered dollar."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone

from .assurance import (
    CaseProofBundle,
    ClientActionAuthorization,
    ExternalActionEnvelope,
    SEVEN_FIGURE_CENTS,
    verify_action_authorization,
    verify_case_bundle,
)
from .models import CaseState, FindingState, RecoveryFinding, canonical_hash
from .policies import assert_claim_authorizable
from .readiness import SevenFigureReadinessPackage, verify_seven_figure_readiness


@dataclass(frozen=True)
class LedgerRecord:
    finding: RecoveryFinding
    case_state: CaseState
    reviewer_approved: bool = False
    reviewer_id: str | None = None
    review_note: str | None = None
    independent_reviewer_id: str | None = None
    independent_review_note: str | None = None
    authorization_id: str | None = None
    customer_actor_id: str | None = None
    case_bundle_hash: str | None = None
    authorization_hash: str | None = None
    readiness_hash: str | None = None
    external_action_envelope_hash: str | None = None
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

    @staticmethod
    def _high_value(record: LedgerRecord) -> bool:
        return record.finding.potential_recovery_cents >= SEVEN_FIGURE_CENTS

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

    def independent_approve(
        self,
        finding_id: str,
        reviewer_id: str,
        note: str,
    ) -> LedgerRecord:
        if not reviewer_id.strip() or not note.strip():
            raise ValueError("independent reviewer_id and note are required")
        record = self.get(finding_id)
        assert_claim_authorizable(record.finding, record.reviewer_approved)
        if not record.reviewer_id:
            raise ValueError("primary review approval is required first")
        if reviewer_id.strip() == record.reviewer_id:
            raise ValueError("independent reviewer must differ from primary reviewer")
        updated = replace(
            record,
            independent_reviewer_id=reviewer_id.strip(),
            independent_review_note=note.strip(),
            updated_at=self._now(),
        )
        self._records[finding_id] = updated
        return updated

    def authorize(self, finding_id: str, authorization_id: str) -> LedgerRecord:
        if not authorization_id.strip():
            raise ValueError("authorization_id is required")
        record = self.get(finding_id)
        if self._high_value(record):
            raise ValueError(
                "seven-figure finding requires frozen case proof and authorize_with_case"
            )
        assert_claim_authorizable(record.finding, record.reviewer_approved)
        updated = replace(
            record,
            case_state=CaseState.AUTHORIZED,
            authorization_id=authorization_id.strip(),
            updated_at=self._now(),
        )
        self._records[finding_id] = updated
        return updated

    def authorize_with_case(
        self,
        finding_id: str,
        bundle: CaseProofBundle,
        authorization: ClientActionAuthorization,
        readiness: SevenFigureReadinessPackage | None = None,
    ) -> LedgerRecord:
        record = self.get(finding_id)
        assert_claim_authorizable(record.finding, record.reviewer_approved)
        verify_case_bundle(bundle)
        verify_action_authorization(bundle, authorization)
        if bundle.finding.finding_id != finding_id:
            raise ValueError("case proof finding_id does not match ledger record")
        if bundle.finding.proof_hash != record.finding.proof_hash:
            raise ValueError("case proof finding does not match ledger proof")
        approving_reviewers = {
            review.reviewer_id
            for review in bundle.reviews
            if review.decision == "APPROVE"
        }
        if record.reviewer_id not in approving_reviewers:
            raise ValueError("primary ledger reviewer is not in frozen case proof")
        if self._high_value(record):
            if not record.independent_reviewer_id:
                raise ValueError("seven-figure finding requires independent ledger approval")
            if record.independent_reviewer_id not in approving_reviewers:
                raise ValueError("independent ledger reviewer is not in frozen case proof")
            if readiness is None:
                raise ValueError(
                    "seven-figure finding requires completed readiness package"
                )
            journal = getattr(self, "journal", None)
            if journal is None:
                raise ValueError(
                    "seven-figure authorization requires DurableRecoveryLedger"
                )
            verify_seven_figure_readiness(
                readiness,
                bundle,
                expected_journal_head_hash=journal.head_hash,
            )
        elif readiness is not None:
            raise ValueError(
                "seven-figure readiness package cannot authorize a sub-seven-figure case"
            )
        if authorization.client_actor_id in {
            record.reviewer_id,
            record.independent_reviewer_id,
        }:
            raise ValueError("client authorizer must differ from RecoveryWorks reviewers")

        updated = replace(
            record,
            case_state=CaseState.AUTHORIZED,
            authorization_id=authorization.authorization_id,
            customer_actor_id=authorization.client_actor_id,
            case_bundle_hash=bundle.bundle_hash,
            authorization_hash=authorization.proof_hash,
            readiness_hash=readiness.package_hash if readiness is not None else None,
            updated_at=self._now(),
        )
        self._records[finding_id] = updated
        return updated

    def mark_claimed(
        self,
        finding_id: str,
        action_envelope: ExternalActionEnvelope | None = None,
    ) -> LedgerRecord:
        record = self.get(finding_id)
        if record.case_state is not CaseState.AUTHORIZED or not record.authorization_id:
            raise ValueError("claim action requires explicit authorization")

        if self._high_value(record):
            if not record.readiness_hash:
                raise ValueError(
                    "seven-figure claim requires completed readiness gate"
                )
            if action_envelope is None:
                raise ValueError(
                    "seven-figure claim requires a hashed external-action envelope"
                )

        envelope_hash = record.external_action_envelope_hash
        if action_envelope is not None:
            action_envelope.verify_integrity()
            if action_envelope.finding_id != finding_id:
                raise ValueError("external action finding_id mismatch")
            if action_envelope.finding_proof_hash != record.finding.proof_hash:
                raise ValueError("external action finding proof mismatch")
            if action_envelope.authorization_id != record.authorization_id:
                raise ValueError("external action authorization id mismatch")
            if record.authorization_hash != action_envelope.authorization_hash:
                raise ValueError("external action authorization hash mismatch")
            if record.case_bundle_hash != action_envelope.case_bundle_hash:
                raise ValueError("external action case bundle hash mismatch")
            envelope_hash = action_envelope.envelope_hash

        updated = replace(
            record,
            case_state=CaseState.CLAIMED,
            external_action_envelope_hash=envelope_hash,
            updated_at=self._now(),
        )
        self._records[finding_id] = updated
        return updated

    def mark_recovered(
        self,
        finding_id: str,
        recovered_cents: int,
        fee_cents: int = 0,
    ) -> LedgerRecord:
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
