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
from .models import (
    CaseState,
    FindingState,
    RecoveryFinding,
    SettlementEvidence,
    canonical_hash,
    normalize_utc_timestamp,
)
from .financial_events import CashEvent
from .models import normalize_sha256
from .policies import assert_claim_authorizable
from .readiness import (
    SevenFigureAuthorizationDossier,
    SevenFigureReadinessPackage,
    verify_seven_figure_authorization_dossier,
)


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
    readiness_dossier_hash: str | None = None
    external_action_envelope_hash: str | None = None
    settlement_id: str | None = None
    settlement_evidence_hash: str | None = None
    settlement_observed_at: str | None = None
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


class EconomicLossConflict(ValueError):
    """A changed proof must be reconciled with its existing economic case."""

    def __init__(self, finding_id: str):
        self.finding_id = finding_id
        super().__init__("economic loss already recorded as " + finding_id
                         + "; reconcile changed evidence before adding another case")


def economic_loss_key(finding: RecoveryFinding) -> tuple:
    # Evidence hashes identify proof versions, not separate financial losses.
    explicit = finding.metadata.get("economic_loss_id")
    if explicit is not None:
        if not isinstance(explicit, str) or not explicit.strip():
            raise ValueError("economic_loss_id must be nonempty text")
        return (finding.client_id, finding.currency, "explicit", explicit.strip())
    return (finding.client_id, finding.currency, finding.branch.value,
            finding.counterparty_id, finding.reference,
            finding.metadata.get("account_id", ""),
            finding.metadata.get("shipment_id", ""),
            finding.metadata.get("business_unit", ""))


class RecoveryLedger:
    def __init__(self) -> None:
        self._records: dict[str, LedgerRecord] = {}
        self._proof_index: dict[str, str] = {}
        self._economic_index: dict[tuple, str] = {}
        self._reconciliation_holds: dict[str, str] = {}
        self._cash_events: dict[tuple[str, str], CashEvent] = {}
        self._superseded: dict[str, str] = {}
        self._settlement_id_index: dict[tuple[str, str], str] = {}
        self._settlement_source_index: dict[tuple[str, str, str], str] = {}

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    @staticmethod
    def _text(name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} is required")
        normalized = value.strip()
        if any(ord(character) < 32 for character in normalized):
            raise ValueError(f"{name} cannot contain control characters")
        return normalized

    @classmethod
    def _transition_time(
        cls,
        record: LedgerRecord | None,
        occurred_at: str | None,
    ) -> str:
        timestamp = (
            cls._now()
            if occurred_at is None
            else normalize_utc_timestamp("occurred_at", occurred_at)
        )
        if record is not None and record.updated_at is not None and timestamp < record.updated_at:
            raise ValueError("lifecycle transition cannot predate the current record state")
        return timestamp

    @staticmethod
    def _require_state(
        record: LedgerRecord,
        allowed: set[CaseState],
        action: str,
    ) -> None:
        if record.case_state not in allowed:
            expected = ", ".join(sorted(state.value for state in allowed))
            raise ValueError(
                f"{action} requires case state {expected}; found {record.case_state.value}"
            )

    @staticmethod
    def _high_value(record: LedgerRecord) -> bool:
        return record.finding.potential_recovery_cents >= SEVEN_FIGURE_CENTS

    def add(
        self,
        finding: RecoveryFinding,
        *,
        occurred_at: str | None = None,
    ) -> LedgerRecord:
        existing_id = self._proof_index.get(finding.proof_hash)
        if existing_id:
            return self._records[existing_id]
        if finding.finding_id in self._records:
            raise ValueError("finding_id already exists with different proof")
        key = economic_loss_key(finding)
        if key in self._economic_index:
            raise EconomicLossConflict(self._economic_index[key])
        state = CaseState.VALIDATED if finding.state is FindingState.VALIDATED else CaseState.REVIEW
        record = LedgerRecord(
            finding=finding,
            case_state=state,
            updated_at=self._transition_time(None, occurred_at),
        )
        self._records[finding.finding_id] = record
        self._proof_index[finding.proof_hash] = finding.finding_id
        self._economic_index[key] = finding.finding_id
        return record

    def hold_for_reconciliation(self, finding_id: str, reason: str, *, occurred_at=None):
        record = self.get(finding_id)
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("reconciliation hold reason required")
        self._transition_time(record, occurred_at)
        self._reconciliation_holds[finding_id] = reason.strip()
        return record

    def resolve_reconciliation(self, finding_id: str, *, reviewer_id: str,
                               independent_reviewer_id: str, evidence_hash: str,
                               expected_record_hash: str, expected_hold_hash: str, note: str, occurred_at=None):
        record = self.get(finding_id)
        if finding_id not in self._reconciliation_holds:
            raise ValueError("case has no reconciliation hold")
        reviewer = self._text("reviewer_id", reviewer_id)
        independent = self._text("independent_reviewer_id", independent_reviewer_id)
        if reviewer == independent:
            raise ValueError("reconciliation requires distinct reviewers")
        normalize_sha256("evidence_hash", evidence_hash)
        self._text("note", note)
        if expected_hold_hash != self.reconciliation_hold_hash(finding_id):
            raise ValueError("stale reconciliation hold review")
        if expected_record_hash != record.record_hash:
            raise ValueError("stale reconciliation review")
        timestamp = self._transition_time(record, occurred_at)
        if record.case_state in {CaseState.REVIEW, CaseState.VALIDATED, CaseState.AUTHORIZED}:
            # Retaining the reviewed proof never retains stale claim permission.
            record = replace(record, case_state=(CaseState.VALIDATED if
                record.finding.state is FindingState.VALIDATED else CaseState.REVIEW),
                reviewer_approved=False, reviewer_id=None, review_note=None,
                independent_reviewer_id=None, independent_review_note=None,
                authorization_id=None, customer_actor_id=None, case_bundle_hash=None,
                authorization_hash=None, readiness_hash=None, readiness_dossier_hash=None,
                external_action_envelope_hash=None, updated_at=timestamp)
        else:
            record = replace(record, updated_at=timestamp)
        self._records[finding_id] = record
        del self._reconciliation_holds[finding_id]
        return record

    def revise_held_case(self, finding_id: str, replacement: RecoveryFinding, *,
                         reviewer_id: str, independent_reviewer_id: str, evidence_hash: str,
                         expected_record_hash: str, expected_hold_hash: str, note: str, occurred_at=None):
        record = self.get(finding_id)
        self._require_state(record, {CaseState.REVIEW, CaseState.VALIDATED, CaseState.AUTHORIZED}, "case revision")
        if record.recovered_cents or record.fee_cents:
            raise ValueError("cash-bearing cases require settlement reconciliation, not revision")
        if not isinstance(replacement, RecoveryFinding):
            raise ValueError("replacement must be a RecoveryFinding")
        if replacement.finding_id in self._records or replacement.proof_hash in self._proof_index:
            raise ValueError("replacement already exists")
        if replacement.branch != record.finding.branch or economic_loss_key(replacement) != economic_loss_key(record.finding):
            raise ValueError("replacement must describe the same economic loss")
        # This validates hold, distinct reviewers, current proof and evidence hash before mutation.
        RecoveryLedger.resolve_reconciliation(self, finding_id, reviewer_id=reviewer_id,
            independent_reviewer_id=independent_reviewer_id, evidence_hash=evidence_hash,
            expected_record_hash=expected_record_hash, expected_hold_hash=expected_hold_hash, note=note, occurred_at=occurred_at)
        timestamp = self.get(finding_id).updated_at
        self._records[finding_id] = replace(self.get(finding_id), case_state=CaseState.REJECTED,
                                            review_note="Superseded: " + note)
        updated = LedgerRecord(finding=replacement, case_state=(CaseState.VALIDATED if
            replacement.state is FindingState.VALIDATED else CaseState.REVIEW), updated_at=timestamp)
        self._records[replacement.finding_id] = updated
        self._proof_index[replacement.proof_hash] = replacement.finding_id
        self._economic_index[economic_loss_key(replacement)] = replacement.finding_id
        self._superseded[finding_id] = replacement.finding_id
        return updated

    def active_records(self):
        return tuple(r for r in self.records() if r.finding.finding_id not in self._superseded)

    def post_cash_event(self, event: CashEvent, *, occurred_at=None):
        if not isinstance(event, CashEvent) or not event.verified:
            raise ValueError("verified CashEvent required")
        record = self.get(event.finding_id)
        client = record.finding.client_id
        key = (client, event.event_id)
        previous = self._cash_events.get(key)
        if previous is not None:
            if previous != event:
                raise ValueError("cash event identity reused with different evidence")
            return record
        self._check_reconciliation_hold(event.finding_id)
        self._require_state(record, {CaseState.CLAIMED, CaseState.RECOVERED}, "cash posting")
        if event.currency != record.finding.currency:
            raise ValueError("cash currency mismatch")
        if key in self._settlement_id_index:
            raise ValueError("cash event identity already allocated")
        source_key = (client, event.source_hash, event.source_locator)
        if source_key in self._settlement_source_index:
            raise ValueError("cash source line already allocated")
        timestamp = self._transition_time(record, occurred_at)
        if event.observed_at < record.updated_at or event.observed_at > timestamp:
            raise ValueError("cash evidence date outside transition interval")
        if event.amount_cents < 0:
            original = self._cash_events.get((client, event.reverses_id))
            if original is None or original.finding_id != event.finding_id or original.amount_cents <= 0:
                raise ValueError("reversal requires original receipt in this case")
            reversals = [e for (c, _), e in self._cash_events.items()
                         if c == client and e.reverses_id == event.reverses_id]
            if -sum(e.amount_cents for e in reversals) - event.amount_cents > original.amount_cents:
                raise ValueError("reversal exceeds original receipt")
            if -sum(e.fee_cents for e in reversals) - event.fee_cents > original.fee_cents:
                raise ValueError("fee reversal exceeds original fee")
        recovered = record.recovered_cents + event.amount_cents
        fees = record.fee_cents + event.fee_cents
        if not 0 <= fees <= recovered <= record.finding.potential_recovery_cents:
            raise ValueError("cash or fee balance exceeds case bounds")
        updated = replace(record, case_state=CaseState.RECOVERED, recovered_cents=recovered,
                          fee_cents=fees, settlement_id=event.event_id,
                          settlement_evidence_hash=event.proof_hash,
                          settlement_observed_at=event.observed_at, updated_at=timestamp)
        self._records[event.finding_id] = updated
        self._cash_events[key] = event
        self._settlement_id_index[key] = event.finding_id
        self._settlement_source_index[source_key] = event.finding_id
        return updated

    def reconciliation_hold_hash(self, finding_id: str) -> str:
        if finding_id not in self._reconciliation_holds:
            raise ValueError("case has no reconciliation hold")
        return canonical_hash({"finding_id": finding_id,
                               "reason": self._reconciliation_holds[finding_id]})

    def reconciliation_holds(self) -> dict[str, str]:
        return dict(self._reconciliation_holds)

    def _check_reconciliation_hold(self, finding_id: str) -> None:
        if finding_id in self._reconciliation_holds:
            raise ValueError("case is held for evidence reconciliation")

    def get(self, finding_id: str) -> LedgerRecord:
        try:
            return self._records[finding_id]
        except KeyError as exc:
            raise KeyError(f"unknown finding_id: {finding_id}") from exc

    def approve(
        self,
        finding_id: str,
        reviewer_id: str,
        note: str,
        *,
        occurred_at: str | None = None,
    ) -> LedgerRecord:
        reviewer_id = self._text("reviewer_id", reviewer_id)
        note = self._text("review note", note)
        self._check_reconciliation_hold(finding_id)
        record = self.get(finding_id)
        self._require_state(record, {CaseState.VALIDATED}, "approval")
        if record.reviewer_approved:
            raise ValueError("primary review is already approved")
        assert_claim_authorizable(record.finding, True)
        updated = replace(
            record,
            reviewer_approved=True,
            reviewer_id=reviewer_id,
            review_note=note,
            updated_at=self._transition_time(record, occurred_at),
        )
        self._records[finding_id] = updated
        return updated

    def independent_approve(
        self,
        finding_id: str,
        reviewer_id: str,
        note: str,
        *,
        occurred_at: str | None = None,
    ) -> LedgerRecord:
        reviewer_id = self._text("independent reviewer_id", reviewer_id)
        note = self._text("independent review note", note)
        self._check_reconciliation_hold(finding_id)
        record = self.get(finding_id)
        self._require_state(record, {CaseState.VALIDATED}, "independent approval")
        assert_claim_authorizable(record.finding, record.reviewer_approved)
        if not record.reviewer_id:
            raise ValueError("primary review approval is required first")
        if reviewer_id == record.reviewer_id:
            raise ValueError("independent reviewer must differ from primary reviewer")
        if record.independent_reviewer_id:
            raise ValueError("independent review is already approved")
        updated = replace(
            record,
            independent_reviewer_id=reviewer_id,
            independent_review_note=note,
            updated_at=self._transition_time(record, occurred_at),
        )
        self._records[finding_id] = updated
        return updated

    def authorize(
        self,
        finding_id: str,
        authorization_id: str,
        *,
        occurred_at: str | None = None,
    ) -> LedgerRecord:
        authorization_id = self._text("authorization_id", authorization_id)
        self._check_reconciliation_hold(finding_id)
        record = self.get(finding_id)
        self._require_state(record, {CaseState.VALIDATED}, "authorization")
        if self._high_value(record):
            raise ValueError(
                "seven-figure finding requires frozen case proof and authorize_with_case"
            )
        assert_claim_authorizable(record.finding, record.reviewer_approved)
        updated = replace(
            record,
            case_state=CaseState.AUTHORIZED,
            authorization_id=authorization_id,
            updated_at=self._transition_time(record, occurred_at),
        )
        self._records[finding_id] = updated
        return updated

    def authorize_with_case(
        self,
        finding_id: str,
        bundle: CaseProofBundle,
        authorization: ClientActionAuthorization,
        readiness: SevenFigureReadinessPackage | None = None,
        dossier: SevenFigureAuthorizationDossier | None = None,
        *,
        occurred_at: str | None = None,
    ) -> LedgerRecord:
        self._check_reconciliation_hold(finding_id)
        record = self.get(finding_id)
        self._require_state(record, {CaseState.VALIDATED}, "case authorization")
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
            if dossier is None:
                raise ValueError(
                    "seven-figure finding requires full authorization dossier"
                )
            if readiness is not None and readiness.package_hash != dossier.readiness.package_hash:
                raise ValueError("readiness package does not match authorization dossier")
            readiness = dossier.readiness
            journal = getattr(self, "journal", None)
            if journal is None:
                raise ValueError(
                    "seven-figure authorization requires DurableRecoveryLedger"
                )
            verify_seven_figure_authorization_dossier(
                dossier,
                bundle,
                expected_journal_head_hash=journal.head_hash,
            )
            authorized_at = datetime.fromisoformat(
                authorization.authorized_at.replace("Z", "+00:00")
            )
            dossier_assembled_at = datetime.fromisoformat(
                dossier.assembled_at.replace("Z", "+00:00")
            )
            if authorized_at < dossier_assembled_at:
                raise ValueError(
                    "client authorization cannot predate completed seven-figure dossier"
                )
        elif readiness is not None or dossier is not None:
            raise ValueError(
                "seven-figure assurance artifacts cannot authorize a sub-seven-figure case"
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
            readiness_dossier_hash=dossier.dossier_hash if dossier is not None else None,
            updated_at=self._transition_time(record, occurred_at),
        )
        self._records[finding_id] = updated
        return updated

    def mark_claimed(
        self,
        finding_id: str,
        action_envelope: ExternalActionEnvelope | None = None,
        *,
        occurred_at: str | None = None,
    ) -> LedgerRecord:
        self._check_reconciliation_hold(finding_id)
        record = self.get(finding_id)
        if record.case_state is not CaseState.AUTHORIZED or not record.authorization_id:
            raise ValueError("claim action requires explicit authorization")

        if self._high_value(record):
            if not record.readiness_hash or not record.readiness_dossier_hash:
                raise ValueError(
                    "seven-figure claim requires completed readiness dossier"
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
            updated_at=self._transition_time(record, occurred_at),
        )
        self._records[finding_id] = updated
        return updated

    def mark_recovered(
        self,
        finding_id: str,
        settlement: SettlementEvidence,
        fee_cents: int = 0,
        *,
        occurred_at: str | None = None,
    ) -> LedgerRecord:
        self._check_reconciliation_hold(finding_id)
        record = self.get(finding_id)
        if record.case_state is not CaseState.CLAIMED:
            raise ValueError("only CLAIMED cases may be marked recovered")
        if not isinstance(settlement, SettlementEvidence):
            raise ValueError("verified SettlementEvidence is required")
        if not settlement.verified:
            raise ValueError("settlement evidence must be externally verified")
        if settlement.finding_id != finding_id:
            raise ValueError("settlement evidence finding_id does not match the claimed case")
        if settlement.currency != record.finding.currency:
            raise ValueError("settlement currency does not match the finding")
        client_id = record.finding.client_id
        settlement_key = (client_id, settlement.settlement_id)
        source_key = (client_id, settlement.source_hash, settlement.source_locator)
        prior_id_owner = self._settlement_id_index.get(settlement_key)
        if prior_id_owner is not None and prior_id_owner != finding_id:
            raise ValueError("settlement_id is already allocated to another finding")
        prior_source_owner = self._settlement_source_index.get(source_key)
        if prior_source_owner is not None and prior_source_owner != finding_id:
            raise ValueError("settlement source line is already allocated to another finding")
        if record.updated_at is not None and settlement.observed_at < record.updated_at:
            raise ValueError("settlement evidence cannot predate the claim")
        transition_time = self._transition_time(record, occurred_at)
        if transition_time < settlement.observed_at:
            raise ValueError("recovery transition cannot predate settlement evidence")
        if type(fee_cents) is not int or fee_cents < 0 or fee_cents > settlement.recovered_cents:
            raise ValueError("fee_cents must be between zero and recovered_cents")
        if settlement.recovered_cents > record.finding.potential_recovery_cents:
            raise ValueError("recovered amount cannot exceed validated potential recovery")
        updated = replace(
            record,
            case_state=CaseState.RECOVERED,
            settlement_id=settlement.settlement_id,
            settlement_evidence_hash=settlement.proof_hash,
            settlement_observed_at=settlement.observed_at,
            recovered_cents=settlement.recovered_cents,
            fee_cents=fee_cents,
            updated_at=transition_time,
        )
        self._records[finding_id] = updated
        self._settlement_id_index[settlement_key] = finding_id
        self._settlement_source_index[source_key] = finding_id
        self._cash_events[settlement_key] = CashEvent(
            settlement.settlement_id, finding_id, settlement.recovered_cents, fee_cents,
            settlement.currency, settlement.source_hash, settlement.source_locator,
            settlement.observed_at, settlement.verified)
        return updated

    def reject(
        self,
        finding_id: str,
        reviewer_id: str,
        note: str,
        *,
        occurred_at: str | None = None,
    ) -> LedgerRecord:
        reviewer_id = self._text("reviewer_id", reviewer_id)
        note = self._text("rejection note", note)
        record = self.get(finding_id)
        self._require_state(
            record,
            {CaseState.REVIEW, CaseState.VALIDATED, CaseState.AUTHORIZED},
            "rejection",
        )
        updated = replace(
            record,
            case_state=CaseState.REJECTED,
            reviewer_id=reviewer_id,
            review_note=note,
            updated_at=self._transition_time(record, occurred_at),
        )
        self._records[finding_id] = updated
        return updated

    def records(self) -> tuple[LedgerRecord, ...]:
        return tuple(sorted(self._records.values(), key=lambda r: r.finding.finding_id))

    def rollup(self) -> dict:
        branches: dict[str, dict[str, int]] = {}
        total_potential = total_validated = total_recovered = total_fees = 0
        for record in self.active_records():
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
                "cases": len(self.active_records()),
                "potential_cents": total_potential,
                "validated_cents": total_validated,
                "recovered_cents": total_recovered,
                "fee_cents": total_fees,
            },
        }
