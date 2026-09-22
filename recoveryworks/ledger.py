"""Recovery Ledger: auditable lifecycle for every potential recovered dollar."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone

from .authorization import (
    AuthorizationRevocation,
    RecoveryActionAuthorization,
    RecoveryActionType,
    assert_action_allowed,
    assert_authorization_matches_reviewed_record,
)
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
    authorization_hash: str | None = None
    authorized_cents: int = 0
    claim_action_hash: str | None = None
    claimed_cents: int = 0
    recovered_cents: int = 0
    fee_cents: int = 0
    updated_at: str | None = None

    @property
    def record_hash(self) -> str:
        # State identity must survive deterministic event replay. updated_at is
        # operational metadata, not economic/lifecycle state, so it is excluded.
        payload = asdict(self)
        payload.pop("updated_at", None)
        payload["finding"]["branch"] = self.finding.branch.value
        payload["finding"]["mode"] = self.finding.mode.value
        payload["finding"]["state"] = self.finding.state.value
        payload["case_state"] = self.case_state.value
        return canonical_hash(payload)


class RecoveryLedger:
    def __init__(self) -> None:
        self._records: dict[str, LedgerRecord] = {}
        self._proof_index: dict[str, str] = {}
        self._authorization_index: dict[str, str] = {}
        self._authorization_hash_index: dict[str, str] = {}

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
        reviewer_id = reviewer_id.strip()
        note = note.strip()
        if not reviewer_id or not note:
            raise ValueError("reviewer_id and review note are required")
        record = self.get(finding_id)
        if record.case_state is not CaseState.VALIDATED:
            raise ValueError("review approval requires a VALIDATED case")
        assert_claim_authorizable(record.finding, True)
        if record.reviewer_approved:
            if record.reviewer_id == reviewer_id and record.review_note == note:
                return record
            raise ValueError("case already has reviewer approval; conflicting replay rejected")
        updated = replace(
            record,
            reviewer_approved=True,
            reviewer_id=reviewer_id,
            review_note=note,
            updated_at=self._now(),
        )
        self._records[finding_id] = updated
        return updated

    def authorize(
        self,
        finding_id: str,
        authorization: RecoveryActionAuthorization,
        *,
        as_of_date: str,
        revocations: tuple[AuthorizationRevocation, ...] = (),
    ) -> LedgerRecord:
        if not isinstance(authorization, RecoveryActionAuthorization):
            raise ValueError("scope-bound RecoveryActionAuthorization is required")
        record = self.get(finding_id)
        if record.case_state is CaseState.AUTHORIZED:
            if (
                record.authorization_id == authorization.authorization_id
                and record.authorization_hash == authorization.authorization_hash
            ):
                return record
            raise ValueError("case already authorized under a different authorization")
        if record.case_state is not CaseState.VALIDATED:
            raise ValueError("authorization requires a VALIDATED case")
        assert_claim_authorizable(record.finding, record.reviewer_approved)
        assert_authorization_matches_reviewed_record(
            authorization,
            record,
            as_of_date=as_of_date,
            revocations=revocations,
        )

        existing_id = self._authorization_index.get(authorization.authorization_id)
        if existing_id is not None and existing_id != finding_id:
            raise ValueError("authorization_id is already bound to another finding")
        existing_hash = self._authorization_hash_index.get(authorization.authorization_hash)
        if existing_hash is not None and existing_hash != finding_id:
            raise ValueError("authorization_hash is already bound to another finding")

        updated = replace(
            record,
            case_state=CaseState.AUTHORIZED,
            authorization_id=authorization.authorization_id,
            authorization_hash=authorization.authorization_hash,
            authorized_cents=authorization.authorized_cents,
            updated_at=self._now(),
        )
        self._records[finding_id] = updated
        self._authorization_index[authorization.authorization_id] = finding_id
        self._authorization_hash_index[authorization.authorization_hash] = finding_id
        return updated

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
        record = self.get(finding_id)
        if (
            record.authorization_id != authorization.authorization_id
            or record.authorization_hash != authorization.authorization_hash
        ):
            raise ValueError("claim authorization does not match ledger authorization")

        assert_action_allowed(
            authorization,
            record.finding,
            as_of_date=as_of_date,
            action_type=action_type,
            target_counterparty_id=target_counterparty_id,
            recipient_reference_hash=recipient_reference_hash,
            action_payload_hash=action_payload_hash,
            currency=currency,
            requested_cents=requested_cents,
            revocations=revocations,
        )
        action_hash = canonical_hash({
            "schema": 1,
            "authorization_hash": authorization.authorization_hash,
            "as_of_date": as_of_date,
            "action_type": action_type.value,
            "target_counterparty_id": target_counterparty_id,
            "recipient_reference_hash": recipient_reference_hash,
            "action_payload_hash": action_payload_hash,
            "currency": currency,
            "requested_cents": requested_cents,
            "revocation_hashes": sorted(r.revocation_hash for r in revocations),
        })

        if record.case_state is CaseState.CLAIMED:
            if record.claim_action_hash == action_hash and record.claimed_cents == requested_cents:
                return record
            raise ValueError("case already claimed under a different action")
        if record.case_state is not CaseState.AUTHORIZED:
            raise ValueError("claim action requires AUTHORIZED case state")

        updated = replace(
            record,
            case_state=CaseState.CLAIMED,
            claim_action_hash=action_hash,
            claimed_cents=requested_cents,
            updated_at=self._now(),
        )
        self._records[finding_id] = updated
        return updated

    def mark_recovered(self, finding_id: str, recovered_cents: int, fee_cents: int = 0) -> LedgerRecord:
        record = self.get(finding_id)
        if record.case_state is CaseState.RECOVERED:
            if record.recovered_cents == recovered_cents and record.fee_cents == fee_cents:
                return record
            raise ValueError("recovered case cannot be rewritten with different money")
        if record.case_state is not CaseState.CLAIMED:
            raise ValueError("only CLAIMED cases may be marked recovered")
        if type(recovered_cents) is not int or recovered_cents < 0:
            raise ValueError("recovered_cents must be non-negative integer cents")
        if type(fee_cents) is not int or fee_cents < 0 or fee_cents > recovered_cents:
            raise ValueError("fee_cents must be between zero and recovered_cents")
        if recovered_cents > record.claimed_cents:
            raise ValueError("recovered amount cannot exceed claimed amount")
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
        reviewer_id = reviewer_id.strip()
        note = note.strip()
        if not reviewer_id or not note:
            raise ValueError("reviewer_id and rejection note are required")
        record = self.get(finding_id)
        if record.case_state is CaseState.REJECTED:
            if record.reviewer_id == reviewer_id and record.review_note == note:
                return record
            raise ValueError("case already rejected; conflicting replay rejected")
        if record.case_state not in {CaseState.REVIEW, CaseState.VALIDATED}:
            raise ValueError("authorized/claimed/recovered cases cannot be rejected")
        updated = replace(
            record,
            case_state=CaseState.REJECTED,
            reviewer_approved=False,
            reviewer_id=reviewer_id,
            review_note=note,
            authorization_id=None,
            authorization_hash=None,
            authorized_cents=0,
            claim_action_hash=None,
            claimed_cents=0,
            updated_at=self._now(),
        )
        self._records[finding_id] = updated
        return updated

    def records(self) -> tuple[LedgerRecord, ...]:
        return tuple(sorted(self._records.values(), key=lambda r: r.finding.finding_id))

    def rollup(self) -> dict:
        """Return lifecycle counts plus money partitioned by currency.

        Monetary amounts from different currencies are never summed together.
        Callers must select the applicable currency bucket explicitly.
        """
        branches: dict[str, dict] = {}
        currencies: dict[str, dict[str, int]] = {}
        total_rejected = 0

        validated_states = {
            CaseState.VALIDATED,
            CaseState.AUTHORIZED,
            CaseState.CLAIMED,
            CaseState.RECOVERED,
        }
        authorized_states = {CaseState.AUTHORIZED, CaseState.CLAIMED, CaseState.RECOVERED}
        claimed_states = {CaseState.CLAIMED, CaseState.RECOVERED}

        def empty_money_bucket() -> dict[str, int]:
            return {
                "discovered_cents": 0,
                "potential_cents": 0,
                "validated_cents": 0,
                "authorized_cents": 0,
                "claimed_cents": 0,
                "recovered_cents": 0,
                "fee_cents": 0,
            }

        def apply_money(bucket: dict[str, int], record: LedgerRecord) -> None:
            amount = record.finding.potential_recovery_cents
            rejected = record.case_state is CaseState.REJECTED
            bucket["discovered_cents"] += amount
            bucket["potential_cents"] += 0 if rejected else amount
            bucket["validated_cents"] += amount if record.case_state in validated_states else 0
            bucket["authorized_cents"] += record.authorized_cents if record.case_state in authorized_states else 0
            bucket["claimed_cents"] += record.claimed_cents if record.case_state in claimed_states else 0
            bucket["recovered_cents"] += record.recovered_cents
            bucket["fee_cents"] += record.fee_cents

        for record in self.records():
            branch = record.finding.branch.value
            currency = record.finding.currency
            rejected = record.case_state is CaseState.REJECTED

            branch_bucket = branches.setdefault(
                branch,
                {"cases": 0, "rejected_cases": 0, "currencies": {}},
            )
            branch_bucket["cases"] += 1
            branch_bucket["rejected_cases"] += int(rejected)
            branch_money = branch_bucket["currencies"].setdefault(currency, empty_money_bucket())
            global_money = currencies.setdefault(currency, empty_money_bucket())
            apply_money(branch_money, record)
            apply_money(global_money, record)
            total_rejected += int(rejected)

        return {
            "branches": branches,
            "totals": {
                "cases": len(self._records),
                "rejected_cases": total_rejected,
            },
            "currencies": currencies,
        }
