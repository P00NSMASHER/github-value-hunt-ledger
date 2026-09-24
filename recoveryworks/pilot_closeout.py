"""Pilot closeout/economics review snapshot.

This is arithmetic and evidence packaging only. It does not create invoices,
assert payment obligations, authorize continuation, or perform external action.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from recoveryworks.cloud_assurance_report import CloudAssuranceReport
from recoveryworks.models import canonical_hash, normalize_sha256, normalize_utc_timestamp
from recoveryworks.pilot_charter import RecoveryWorksPilotCharter
from recoveryworks.pilot_kickoff import PilotKickoffGate
from recoveryworks.private_io import atomic_private_write


@dataclass(frozen=True)
class PilotCloseoutSnapshot:
    closeout_id: str
    charter_id: str
    charter_proof_hash: str
    kickoff_gate_proof_hash: str
    buyer_review_evidence_hash: str
    assurance_report_proof_hash: str
    reviewed_at: str
    currency: str
    potential_recovery_cents: int
    review_recovery_cents: int
    validated_recovery_cents: int
    authorized_recovery_cents: int
    claimed_recovery_cents: int
    recovered_cash_cents: int
    recorded_recovery_fee_cents: int
    prospective_savings_cents: int
    realized_savings_cents: int
    anomaly_exposure_cents: int
    reconciliation_drift_cents: int
    diagnostic_fee_cents_hypothesis: int
    recovered_cash_success_fee_bps_hypothesis: int
    recovered_cash_success_fee_cents_arithmetic: int
    monthly_assurance_fee_cents_hypothesis: int
    ready_for_human_closeout_review: bool = True
    monthly_assurance_option_review_ready: bool = True
    continuation_authorized: bool = False
    invoice_created: bool = False
    payment_due_asserted: bool = False
    payment_received: bool = False
    external_action_authorized: bool = False

    def __post_init__(self) -> None:
        for name in (
            "charter_proof_hash", "kickoff_gate_proof_hash",
            "buyer_review_evidence_hash", "assurance_report_proof_hash",
        ):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        object.__setattr__(
            self, "reviewed_at", normalize_utc_timestamp("reviewed_at", self.reviewed_at)
        )
        cents_fields = (
            "potential_recovery_cents", "review_recovery_cents",
            "validated_recovery_cents", "authorized_recovery_cents",
            "claimed_recovery_cents", "recovered_cash_cents",
            "recorded_recovery_fee_cents", "prospective_savings_cents",
            "realized_savings_cents", "anomaly_exposure_cents",
            "reconciliation_drift_cents", "diagnostic_fee_cents_hypothesis",
            "recovered_cash_success_fee_cents_arithmetic",
            "monthly_assurance_fee_cents_hypothesis",
        )
        for name in cents_fields:
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if (
            type(self.recovered_cash_success_fee_bps_hypothesis) is not int
            or not 0 <= self.recovered_cash_success_fee_bps_hypothesis <= 10000
        ):
            raise ValueError("success fee bps must be in 0..10000")
        expected_fee = (
            self.recovered_cash_cents
            * self.recovered_cash_success_fee_bps_hypothesis
        ) // 10000
        if self.recovered_cash_success_fee_cents_arithmetic != expected_fee:
            raise ValueError("success fee arithmetic must use recovered cash only")
        if not self.ready_for_human_closeout_review:
            raise ValueError("closeout snapshot must be ready for human review")
        if not self.monthly_assurance_option_review_ready:
            raise ValueError("closeout snapshot must expose the continuation option for review")
        if (
            self.continuation_authorized
            or self.invoice_created
            or self.payment_due_asserted
            or self.payment_received
            or self.external_action_authorized
        ):
            raise ValueError("closeout snapshot cannot create commercial/external commitments")
        expected = "recoveryworks-pilot-closeout:" + canonical_hash(self._identity())
        if self.closeout_id != expected:
            raise ValueError("closeout_id does not bind closeout snapshot")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "charter_id": self.charter_id,
            "charter_proof_hash": self.charter_proof_hash,
            "kickoff_gate_proof_hash": self.kickoff_gate_proof_hash,
            "buyer_review_evidence_hash": self.buyer_review_evidence_hash,
            "assurance_report_proof_hash": self.assurance_report_proof_hash,
            "reviewed_at": self.reviewed_at,
            "currency": self.currency,
            "potential_recovery_cents": self.potential_recovery_cents,
            "review_recovery_cents": self.review_recovery_cents,
            "validated_recovery_cents": self.validated_recovery_cents,
            "authorized_recovery_cents": self.authorized_recovery_cents,
            "claimed_recovery_cents": self.claimed_recovery_cents,
            "recovered_cash_cents": self.recovered_cash_cents,
            "recorded_recovery_fee_cents": self.recorded_recovery_fee_cents,
            "prospective_savings_cents": self.prospective_savings_cents,
            "realized_savings_cents": self.realized_savings_cents,
            "anomaly_exposure_cents": self.anomaly_exposure_cents,
            "reconciliation_drift_cents": self.reconciliation_drift_cents,
            "diagnostic_fee_cents_hypothesis": self.diagnostic_fee_cents_hypothesis,
            "recovered_cash_success_fee_bps_hypothesis":
                self.recovered_cash_success_fee_bps_hypothesis,
            "recovered_cash_success_fee_cents_arithmetic":
                self.recovered_cash_success_fee_cents_arithmetic,
            "monthly_assurance_fee_cents_hypothesis":
                self.monthly_assurance_fee_cents_hypothesis,
            "ready_for_human_closeout_review": True,
            "monthly_assurance_option_review_ready": True,
            "continuation_authorized": False,
            "invoice_created": False,
            "payment_due_asserted": False,
            "payment_received": False,
            "external_action_authorized": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "closeout_id": self.closeout_id,
            "proof_hash": self.proof_hash,
            "state": "PILOT_CLOSEOUT_REVIEW_READY",
        }

    def to_markdown(self) -> str:
        return "\n".join([
            "# RecoveryWorks Pilot Closeout Review",
            "",
            f"Currency: {self.currency}",
            f"Recovered cash: {self.recovered_cash_cents} cents",
            f"Validated recovery: {self.validated_recovery_cents} cents",
            f"Prospective savings: {self.prospective_savings_cents} cents",
            f"Verified realized savings: {self.realized_savings_cents} cents",
            f"Anomaly exposure: {self.anomaly_exposure_cents} cents",
            f"Reconciliation drift: {self.reconciliation_drift_cents} cents",
            "",
            "## Commercial arithmetic (hypothesis only)",
            "",
            f"Diagnostic fee hypothesis: {self.diagnostic_fee_cents_hypothesis} cents",
            f"Recovered-cash success fee: {self.recovered_cash_success_fee_cents_arithmetic} cents",
            f"Monthly assurance fee hypothesis: {self.monthly_assurance_fee_cents_hypothesis} cents",
            "",
            "No invoice, payment obligation, payment receipt, continuation authorization, or external action is created by this artifact.",
            "",
        ])


def build_pilot_closeout_snapshot(
    charter: RecoveryWorksPilotCharter,
    kickoff: PilotKickoffGate,
    assurance: CloudAssuranceReport,
    *,
    buyer_review_evidence_hash: str,
    reviewed_at: str,
) -> PilotCloseoutSnapshot:
    if kickoff.charter_id != charter.charter_id:
        raise ValueError("kickoff gate charter id mismatch")
    if kickoff.charter_proof_hash != charter.proof_hash:
        raise ValueError("kickoff gate charter proof mismatch")
    recovery = assurance.recovery_summary.get("totals")
    if not isinstance(recovery, dict):
        raise ValueError("assurance recovery totals missing")
    savings = assurance.savings_summary
    diagnostics = assurance.diagnostics

    def cents(mapping: dict[str, Any], key: str) -> int:
        value = mapping.get(key, 0)
        if type(value) is not int or value < 0:
            raise ValueError(f"assurance {key} must be non-negative integer")
        return value

    recovered = cents(recovery, "recovered_cents")
    success_fee = (
        recovered * charter.recovered_cash_success_fee_bps
    ) // 10000
    buyer_review_hash = normalize_sha256(
        "buyer_review_evidence_hash", buyer_review_evidence_hash
    )
    reviewed = normalize_utc_timestamp("reviewed_at", reviewed_at)
    identity = {
        "schema": 1,
        "charter_id": charter.charter_id,
        "charter_proof_hash": charter.proof_hash,
        "kickoff_gate_proof_hash": kickoff.proof_hash,
        "buyer_review_evidence_hash": buyer_review_hash,
        "assurance_report_proof_hash": assurance.proof_hash,
        "reviewed_at": reviewed,
        "currency": assurance.currency,
        "potential_recovery_cents": cents(recovery, "potential_cents"),
        "review_recovery_cents": cents(recovery, "review_cents"),
        "validated_recovery_cents": cents(recovery, "validated_cents"),
        "authorized_recovery_cents": cents(recovery, "authorized_cents"),
        "claimed_recovery_cents": cents(recovery, "claimed_cents"),
        "recovered_cash_cents": recovered,
        "recorded_recovery_fee_cents": cents(recovery, "fee_cents"),
        "prospective_savings_cents": cents(
            savings, "estimated_savings_opportunity_cents"
        ),
        "realized_savings_cents": cents(savings, "realized_savings_cents"),
        "anomaly_exposure_cents": cents(
            diagnostics, "estimated_anomaly_exposure_cents"
        ),
        "reconciliation_drift_cents": cents(
            diagnostics, "reconciliation_drift_cents"
        ),
        "diagnostic_fee_cents_hypothesis": charter.diagnostic_fee_cents,
        "recovered_cash_success_fee_bps_hypothesis":
            charter.recovered_cash_success_fee_bps,
        "recovered_cash_success_fee_cents_arithmetic": success_fee,
        "monthly_assurance_fee_cents_hypothesis":
            charter.monthly_assurance_fee_cents,
        "ready_for_human_closeout_review": True,
        "monthly_assurance_option_review_ready": True,
        "continuation_authorized": False,
        "invoice_created": False,
        "payment_due_asserted": False,
        "payment_received": False,
        "external_action_authorized": False,
    }
    return PilotCloseoutSnapshot(
        closeout_id="recoveryworks-pilot-closeout:" + canonical_hash(identity),
        charter_id=charter.charter_id,
        charter_proof_hash=charter.proof_hash,
        kickoff_gate_proof_hash=kickoff.proof_hash,
        buyer_review_evidence_hash=buyer_review_hash,
        assurance_report_proof_hash=assurance.proof_hash,
        reviewed_at=reviewed,
        currency=assurance.currency,
        potential_recovery_cents=identity["potential_recovery_cents"],
        review_recovery_cents=identity["review_recovery_cents"],
        validated_recovery_cents=identity["validated_recovery_cents"],
        authorized_recovery_cents=identity["authorized_recovery_cents"],
        claimed_recovery_cents=identity["claimed_recovery_cents"],
        recovered_cash_cents=recovered,
        recorded_recovery_fee_cents=identity["recorded_recovery_fee_cents"],
        prospective_savings_cents=identity["prospective_savings_cents"],
        realized_savings_cents=identity["realized_savings_cents"],
        anomaly_exposure_cents=identity["anomaly_exposure_cents"],
        reconciliation_drift_cents=identity["reconciliation_drift_cents"],
        diagnostic_fee_cents_hypothesis=charter.diagnostic_fee_cents,
        recovered_cash_success_fee_bps_hypothesis=
            charter.recovered_cash_success_fee_bps,
        recovered_cash_success_fee_cents_arithmetic=success_fee,
        monthly_assurance_fee_cents_hypothesis=charter.monthly_assurance_fee_cents,
    )


def write_pilot_closeout_snapshot(
    snapshot: PilotCloseoutSnapshot,
    *,
    json_path: str | Path,
    markdown_path: str | Path,
) -> None:
    atomic_private_write(
        Path(json_path),
        (
            json.dumps(
                snapshot.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8"),
    )
    atomic_private_write(
        Path(markdown_path),
        (snapshot.to_markdown() + "\n").encode("utf-8"),
    )
