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
from .journal import RecoveryJournal, finding_from_payload, finding_to_payload
from .ledger import RecoveryLedger
from .models import RecoveryFinding
from .readiness import (
    SevenFigureAuthorizationDossier,
    SevenFigureReadinessPackage,
    authorization_dossier_from_payload,
    authorization_dossier_to_payload,
    readiness_from_payload,
    readiness_to_payload,
    verify_seven_figure_authorization_dossier,
)


class DurableRecoveryLedger(RecoveryLedger):
    """RecoveryLedger plus an append-only tamper-evident lifecycle journal."""

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

    def independent_approve(self, finding_id: str, reviewer_id: str, note: str):
        record = super().independent_approve(finding_id, reviewer_id, note)
        self.journal.append("INDEPENDENT_APPROVE", finding_id, {
            "reviewer_id": record.independent_reviewer_id,
            "review_note": record.independent_review_note,
        })
        return record

    def authorize(self, finding_id: str, authorization_id: str):
        record = super().authorize(finding_id, authorization_id)
        self.journal.append("AUTHORIZE", finding_id, {
            "authorization_id": record.authorization_id,
        })
        return record

    def authorize_with_case(
        self,
        finding_id: str,
        bundle: CaseProofBundle,
        authorization: ClientActionAuthorization,
        readiness: SevenFigureReadinessPackage | None = None,
        dossier: SevenFigureAuthorizationDossier | None = None,
    ):
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
        record = super().authorize_with_case(
            finding_id,
            bundle,
            authorization,
            readiness,
            dossier,
        )
        payload = {
            "case_bundle": case_bundle_to_payload(bundle),
            "authorization": authorization_to_payload(authorization),
        }
        if readiness is not None:
            payload["readiness"] = readiness_to_payload(readiness)
        if dossier is not None:
            payload["dossier"] = authorization_dossier_to_payload(dossier)
        self.journal.append("AUTHORIZE_CASE", finding_id, payload)
        return record

    def mark_claimed(
        self,
        finding_id: str,
        action_envelope: ExternalActionEnvelope | None = None,
    ):
        record = super().mark_claimed(finding_id, action_envelope)
        payload: dict[str, Any] = {}
        if action_envelope is not None:
            payload["external_action"] = external_action_to_payload(action_envelope)
        self.journal.append("CLAIM", finding_id, payload)
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
            elif action == "INDEPENDENT_APPROVE":
                ledger.independent_approve(
                    event.finding_id,
                    data["reviewer_id"],
                    data["review_note"],
                )
            elif action == "AUTHORIZE":
                ledger.authorize(event.finding_id, data["authorization_id"])
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
                ledger.authorize_with_case(
                    event.finding_id,
                    bundle,
                    authorization,
                    readiness,
                    dossier,
                )
            elif action == "CLAIM":
                envelope_raw = data.get("external_action")
                envelope = (
                    external_action_from_payload(envelope_raw)
                    if envelope_raw is not None
                    else None
                )
                ledger.mark_claimed(event.finding_id, envelope)
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
