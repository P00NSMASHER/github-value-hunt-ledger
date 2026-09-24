"""Customer-facing Cloud Recovery & Savings Assurance report.

Recovery, prospective savings, realized savings, anomaly exposure, and
reconciliation drift remain separate financial surfaces. Every active validated
cloud recovery includes a deterministic evidence packet.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

from recoveryworks.branches.cloud_savings import (
    CloudSavingsReport,
    build_cloud_savings_report,
)
from recoveryworks.branches.cloud_savings_evidence import CloudSavingsMeasurement
from recoveryworks.integrations.cletrics_continuous import ContinuousCletricsResult
from recoveryworks.ledger import RecoveryLedger
from recoveryworks.models import (
    Branch,
    CaseState,
    FindingState,
    canonical_hash,
    thaw_json,
)
from recoveryworks.private_io import atomic_private_write


@dataclass(frozen=True)
class CloudAssuranceReport:
    client_id: str
    currency: str
    state_head_hash: str | None
    recovery_summary: dict[str, Any]
    validated_recovery_packets: tuple[dict[str, Any], ...]
    savings_summary: dict[str, Any]
    savings_opportunities: tuple[dict[str, Any], ...]
    diagnostics: dict[str, Any]
    controls: dict[str, Any]

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "client_id": self.client_id,
            "currency": self.currency,
            "state_head_hash": self.state_head_hash,
            "recovery_summary": self.recovery_summary,
            "validated_recovery_packets": list(self.validated_recovery_packets),
            "savings_summary": self.savings_summary,
            "savings_opportunities": list(self.savings_opportunities),
            "diagnostics": self.diagnostics,
            "controls": self.controls,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "proof_hash": self.proof_hash,
        }

    def to_markdown(self) -> str:
        recovery = self.recovery_summary["totals"]
        savings = self.savings_summary
        lines = [
            "# Cloud Recovery & Savings Assurance",
            "",
            f"Client: \`{self.client_id}\`",
            f"Currency: \`{self.currency}\`",
            f"RecoveryOS state head: \`{self.state_head_hash or 'none'}\`",
            f"Report proof hash: \`{self.proof_hash}\`",
            "",
            "## Recoverable cash",
            "",
            f"- Active potential recovery: {recovery['potential_cents']} cents",
            f"- Validated recovery: {recovery['validated_cents']} cents",
            f"- Authorized: {recovery['authorized_cents']} cents",
            f"- Claimed: {recovery['claimed_cents']} cents",
            f"- Recovered cash: {recovery['recovered_cents']} cents",
            f"- Superseded historical amount: {recovery.get('superseded_cents', 0)} cents",
            "",
            "## Prospective and realized savings",
            "",
            f"- Estimated savings opportunities: {savings['estimated_savings_opportunity_cents']} cents",
            f"- Verified realized savings: {savings['realized_savings_cents']} cents",
            f"- Verified realized measurements: {savings['realized_measurement_count']}",
            "",
            "## Diagnostics",
            "",
            f"- Anomaly exposure estimate: {self.diagnostics['estimated_anomaly_exposure_cents']} cents",
            f"- Reconciliation drift: {self.diagnostics['reconciliation_drift_cents']} cents",
            "",
            "## Validated recovery evidence packets",
            "",
        ]
        if not self.validated_recovery_packets:
            lines.append("No active validated recovery packets.")
        for packet in self.validated_recovery_packets:
            lines.extend([
                f"### {packet['reference']}",
                "",
                f"- Finding: \`{packet['finding_id']}\`",
                f"- Case state: \`{packet['case_state']}\`",
                f"- Actual billed: {packet['calculation']['actual_cents']} cents",
                f"- Expected: {packet['calculation']['expected_cents']} cents",
                f"- Potential recovery: {packet['calculation']['potential_recovery_cents']} cents",
                f"- Reason: \`{packet['reason']}\`",
                f"- Finding proof: \`{packet['finding_proof_hash']}\`",
                f"- Rule proof: \`{packet['rule']['proof_hash']}\`",
                f"- Evidence items: {len(packet['evidence'])}",
                "",
            ])
        lines.extend([
            "## Control boundary",
            "",
            "- Recovery dollars require a verified controlling rule and verified load-bearing evidence.",
            "- Prospective savings estimates never increase recovery totals.",
            "- Anomaly exposure and reconciliation drift are diagnostics, not savings or recovery.",
            "- Realized savings only includes VERIFIED before/after measurements.",
            "- This report does not authorize cloud changes or external recovery actions.",
            "",
        ])
        return "\n".join(lines)


def _evidence_packet(record) -> dict[str, Any]:
    finding = record.finding
    if finding.rule is None:
        raise ValueError("validated finding unexpectedly lacks controlling rule")
    return {
        "finding_id": finding.finding_id,
        "reference": finding.reference,
        "case_state": record.case_state.value,
        "counterparty_id": finding.counterparty_id,
        "reason": finding.reason,
        "confidence_basis": finding.confidence_basis,
        "finding_proof_hash": finding.proof_hash,
        "calculation": {
            "mode": finding.mode.value,
            "actual_cents": finding.actual_cents,
            "expected_cents": finding.expected_cents,
            "potential_recovery_cents": finding.potential_recovery_cents,
            "currency": finding.currency,
            "metadata": thaw_json(finding.metadata),
        },
        "rule": {
            "rule_id": finding.rule.rule_id,
            "source_hash": finding.rule.source_hash,
            "source_locator": finding.rule.source_locator,
            "effective_from": finding.rule.effective_from,
            "effective_to": finding.rule.effective_to,
            "verified_controlling": finding.rule.verified_controlling,
            "proof_hash": finding.rule.proof_hash,
            "metadata": thaw_json(finding.rule.metadata),
        },
        "evidence": [
            {
                "evidence_id": item.evidence_id,
                "kind": item.kind,
                "source_hash": item.source_hash,
                "locator": item.locator,
                "verified": item.verified,
                "proof_hash": item.proof_hash,
                "metadata": thaw_json(item.metadata),
            }
            for item in sorted(finding.evidence, key=lambda value: value.evidence_id)
        ],
        "lifecycle": {
            "reviewer_approved": record.reviewer_approved,
            "reviewer_id": record.reviewer_id,
            "authorization_id": record.authorization_id,
            "settlement_id": record.settlement_id,
            "recovered_cents": record.recovered_cents,
            "fee_cents": record.fee_cents,
            "updated_at": record.updated_at,
        },
    }


def build_cloud_assurance_report(
    *,
    result: ContinuousCletricsResult,
    ledger: RecoveryLedger,
    realized_measurements: Iterable[CloudSavingsMeasurement] = (),
) -> CloudAssuranceReport:
    client_id = result.scan.client_id
    records = [
        record
        for record in ledger.records()
        if record.finding.client_id == client_id
        and record.finding.branch is Branch.CLOUD
    ]
    packets = tuple(
        _evidence_packet(record)
        for record in sorted(records, key=lambda item: item.finding.finding_id)
        if record.finding.state is FindingState.VALIDATED
        and record.case_state not in {CaseState.REJECTED, CaseState.SUPERSEDED}
    )
    savings: CloudSavingsReport = build_cloud_savings_report(
        result.cloud_signals,
        realized_measurements=realized_measurements,
    )
    savings_dict = savings.as_dict()
    diagnostics = {
        "anomaly_count": savings.anomaly_count,
        "estimated_anomaly_exposure_cents": savings.estimated_anomaly_exposure_cents,
        "reconciliation_drift_count": savings.reconciliation_drift_count,
        "reconciliation_drift_cents": savings.reconciliation_drift_cents,
        "note": "Diagnostic estimates are not recoverable cash or realized savings.",
    }
    controls = {
        "recovery_requires_verified_rule": True,
        "recovery_requires_verified_evidence": True,
        "estimated_savings_excluded_from_recovery": True,
        "anomaly_exposure_excluded_from_savings": True,
        "realized_savings_requires_verified_measurement": True,
        "cloud_mutation_authorized_by_report": False,
        "external_recovery_action_authorized_by_report": False,
    }
    return CloudAssuranceReport(
        client_id=client_id,
        currency=result.scan.report.currency,
        state_head_hash=result.scan.state_head_hash,
        recovery_summary=result.scan.report.as_dict(),
        validated_recovery_packets=packets,
        savings_summary=savings_dict,
        savings_opportunities=tuple(savings.opportunities),
        diagnostics=diagnostics,
        controls=controls,
    )


def write_cloud_assurance_report(
    report: CloudAssuranceReport,
    *,
    json_path: str | Path,
    markdown_path: str | Path | None = None,
) -> tuple[Path, Path | None]:
    json_target = Path(json_path)
    raw = (
        json.dumps(
            report.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        + b"\n"
    )
    atomic_private_write(json_target, raw)
    markdown_target = None
    if markdown_path is not None:
        markdown_target = Path(markdown_path)
        atomic_private_write(
            markdown_target,
            (report.to_markdown() + "\n").encode("utf-8"),
        )
    return json_target, markdown_target
