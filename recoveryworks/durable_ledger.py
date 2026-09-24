"""Durable RecoveryLedger wrapper with replayable lifecycle history."""
from __future__ import annotations

from typing import Any, Mapping

from .assurance import (
    CaseProofBundle,
    ClientActionAuthorization,
    ExternalActionEnvelope,
    authorization_from_payload,
    authorization_to_payload,
    case_bundle_from_payload,
    case_bundle_to_payload,
    external_action_from_payload,
    external_action_to_payload,
)
from .journal import (
    RecoveryJournal,
    finding_from_payload,
    finding_to_payload,
    settlement_from_payload,
    settlement_to_payload,
)
from .ledger import RecoveryLedger
from .models import RecoveryFinding, SettlementEvidence
from .readiness import (
    SevenFigureAuthorizationDossier,
    SevenFigureAuthorizationSeal,
    SevenFigureReadinessPackage,
    authorization_dossier_from_payload,
    authorization_dossier_to_payload,
    authorization_seal_from_payload,
    authorization_seal_to_payload,
    readiness_from_payload,
    readiness_to_payload,
    verify_seven_figure_authorization_dossier,
    verify_seven_figure_authorization_seal,
)


class DurableRecoveryLedger(RecoveryLedger):
    """RecoveryLedger plus an append-only tamper-evident lifecycle journal."""

    def __init__(self) -> None:
        super().__init__()
        self.journal = RecoveryJournal()

    def _event_time(self, occurred_at: str | None) -> str:
        timestamp = self._transition_time(None, occurred_at)
        events = self.journal.events()
        if events and timestamp < events[-1].occurred_at:
            raise ValueError("journal occurred_at values must be nondecreasing")
        return timestamp

    def add(self, finding: RecoveryFinding, *, occurred_at: str | None = None):
        existed = finding.proof_hash in self._proof_index
        timestamp = occurred_at if existed else self._event_time(occurred_at)
        record = super().add(finding, occurred_at=timestamp)
        if not existed:
            self.journal.append("ADD", finding.finding_id, {
                "finding": finding_to_payload(finding),
            }, occurred_at=record.updated_at)
        return record

    def approve(
        self,
        finding_id: str,
        reviewer_id: str,
        note: str,
        *,
        occurred_at: str | None = None,
    ):
        occurred_at = self._event_time(occurred_at)
        record = super().approve(
            finding_id,
            reviewer_id,
            note,
            occurred_at=occurred_at,
        )
        self.journal.append("APPROVE", finding_id, {
            "reviewer_id": record.reviewer_id,
            "review_note": record.review_note,
        }, occurred_at=record.updated_at)
        return record

    def independent_approve(
        self,
        finding_id: str,
        reviewer_id: str,
        note: str,
        *,
        occurred_at: str | None = None,
    ):
        occurred_at = self._event_time(occurred_at)
        record = super().independent_approve(
            finding_id,
            reviewer_id,
            note,
            occurred_at=occurred_at,
        )
        self.journal.append("INDEPENDENT_APPROVE", finding_id, {
            "reviewer_id": record.independent_reviewer_id,
            "review_note": record.independent_review_note,
        }, occurred_at=record.updated_at)
        return record

    def authorize(
        self,
        finding_id: str,
        authorization_id: str,
        *,
        occurred_at: str | None = None,
    ):
        occurred_at = self._event_time(occurred_at)
        record = super().authorize(
            finding_id,
            authorization_id,
            occurred_at=occurred_at,
        )
        self.journal.append("AUTHORIZE", finding_id, {
            "authorization_id": record.authorization_id,
        }, occurred_at=record.updated_at)
        return record

    def authorize_with_case(
        self,
        finding_id: str,
        bundle: CaseProofBundle,
        authorization: ClientActionAuthorization,
        readiness: SevenFigureReadinessPackage | None = None,
        dossier: SevenFigureAuthorizationDossier | None = None,
        authorization_seal: SevenFigureAuthorizationSeal | None = None,
        *,
        occurred_at: str | None = None,
    ):
        occurred_at = self._event_time(occurred_at)
        record_before = self.get(finding_id)
        if self._high_value(record_before):
            if dossier is None:
                raise ValueError(
                    "seven-figure finding requires full authorization dossier"
                )
            verify_seven_figure_authorization_dossier(
                dossier,
                bundle,
                expected_journal_head_hash=self.journal.head_hash,
            )
            if readiness is not None and readiness.package_hash != dossier.readiness.package_hash:
                raise ValueError("readiness package does not match authorization dossier")
            readiness = dossier.readiness
            if authorization_seal is None:
                raise ValueError(
                    "seven-figure finding requires final authorization seal"
                )
            verify_seven_figure_authorization_seal(
                authorization_seal,
                authorization,
                bundle,
                dossier,
                expected_journal_head_hash=self.journal.head_hash,
            )
        record = super().authorize_with_case(
            finding_id,
            bundle,
            authorization,
            readiness,
            dossier,
            authorization_seal,
            occurred_at=occurred_at,
        )
        payload = {
            "case_bundle": case_bundle_to_payload(bundle),
            "authorization": authorization_to_payload(authorization),
        }
        if readiness is not None:
            payload["readiness"] = readiness_to_payload(readiness)
        if dossier is not None:
            payload["dossier"] = authorization_dossier_to_payload(dossier)
        if authorization_seal is not None:
            payload["authorization_seal"] = authorization_seal_to_payload(
                authorization_seal
            )
        self.journal.append(
            "AUTHORIZE_CASE",
            finding_id,
            payload,
            occurred_at=record.updated_at,
        )
        return record

    def mark_claimed(
        self,
        finding_id: str,
        action_envelope: ExternalActionEnvelope | None = None,
        *,
        occurred_at: str | None = None,
    ):
        occurred_at = self._event_time(occurred_at)
        record = super().mark_claimed(
            finding_id,
            action_envelope,
            occurred_at=occurred_at,
        )
        payload: dict[str, Any] = {}
        if action_envelope is not None:
            payload["external_action"] = external_action_to_payload(action_envelope)
        self.journal.append("CLAIM", finding_id, payload, occurred_at=record.updated_at)
        return record

    def mark_recovered(
        self,
        finding_id: str,
        settlement: SettlementEvidence,
        fee_cents: int = 0,
        *,
        occurred_at: str | None = None,
    ):
        occurred_at = self._event_time(occurred_at)
        record = super().mark_recovered(
            finding_id,
            settlement,
            fee_cents,
            occurred_at=occurred_at,
        )
        self.journal.append("RECOVER", finding_id, {
            "settlement": settlement_to_payload(settlement),
            "fee_cents": fee_cents,
        }, occurred_at=record.updated_at)
        return record

    def reject(
        self,
        finding_id: str,
        reviewer_id: str,
        note: str,
        *,
        occurred_at: str | None = None,
    ):
        occurred_at = self._event_time(occurred_at)
        record = super().reject(
            finding_id,
            reviewer_id,
            note,
            occurred_at=occurred_at,
        )
        self.journal.append("REJECT", finding_id, {
            "reviewer_id": record.reviewer_id,
            "review_note": record.review_note,
        }, occurred_at=record.updated_at)
        return record

    def export_bundle(self) -> dict[str, Any]:
        self.journal.verify()
        return {
            "schema": 2,
            "journal": self.journal.export(),
            "rollup": self.rollup(),
        }

    @classmethod
    def from_bundle(cls, payload: Mapping[str, Any]) -> "DurableRecoveryLedger":
        if payload.get("schema") == 1:
            raise ValueError(
                "legacy durable ledger schema 1 has no authenticated event timestamps; "
                "recreate it from source evidence or use a reviewed migration"
            )
        if payload.get("schema") != 2:
            raise ValueError("unsupported durable ledger schema")
        journal = RecoveryJournal.from_export(payload["journal"])
        ledger = cls()

        for event in journal.events():
            action = event.action
            data = event.payload
            if action == "ADD":
                ledger.add(
                    finding_from_payload(data["finding"]),
                    occurred_at=event.occurred_at,
                )
            elif action == "APPROVE":
                ledger.approve(
                    event.finding_id,
                    data["reviewer_id"],
                    data["review_note"],
                    occurred_at=event.occurred_at,
                )
            elif action == "INDEPENDENT_APPROVE":
                ledger.independent_approve(
                    event.finding_id,
                    data["reviewer_id"],
                    data["review_note"],
                    occurred_at=event.occurred_at,
                )
            elif action == "AUTHORIZE":
                ledger.authorize(
                    event.finding_id,
                    data["authorization_id"],
                    occurred_at=event.occurred_at,
                )
            elif action == "AUTHORIZE_CASE":
                bundle = case_bundle_from_payload(data["case_bundle"])
                authorization = authorization_from_payload(data["authorization"])
                readiness_raw = data.get("readiness")
                readiness = (
                    readiness_from_payload(readiness_raw)
                    if readiness_raw is not None
                    else None
                )
                dossier_raw = data.get("dossier")
                dossier = (
                    authorization_dossier_from_payload(dossier_raw)
                    if dossier_raw is not None
                    else None
                )
                seal_raw = data.get("authorization_seal")
                authorization_seal = (
                    authorization_seal_from_payload(seal_raw)
                    if seal_raw is not None
                    else None
                )
                ledger.authorize_with_case(
                    event.finding_id,
                    bundle,
                    authorization,
                    readiness,
                    dossier,
                    authorization_seal,
                    occurred_at=event.occurred_at,
                )
            elif action == "CLAIM":
                envelope_raw = data.get("external_action")
                envelope = (
                    external_action_from_payload(envelope_raw)
                    if envelope_raw is not None
                    else None
                )
                ledger.mark_claimed(
                    event.finding_id,
                    envelope,
                    occurred_at=event.occurred_at,
                )
            elif action == "RECOVER":
                ledger.mark_recovered(
                    event.finding_id,
                    settlement_from_payload(data["settlement"]),
                    data.get("fee_cents", 0),
                    occurred_at=event.occurred_at,
                )
            elif action == "REJECT":
                ledger.reject(
                    event.finding_id,
                    data["reviewer_id"],
                    data["review_note"],
                    occurred_at=event.occurred_at,
                )
            else:
                raise ValueError(f"unsupported journal action: {action}")

        if ledger.journal.head_hash != journal.head_hash:
            raise ValueError("replayed journal head does not match source")
        expected_rollup = payload.get("rollup")
        if expected_rollup is not None and ledger.rollup() != expected_rollup:
            raise ValueError("replayed ledger rollup mismatch")
        return ledger
