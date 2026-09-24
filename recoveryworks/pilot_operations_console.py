"""Read-only pilot operations console snapshot.

The first console iteration is deliberately non-interactive. It summarizes
diagnostic completion, evidence readiness, supersession holds, recovery/savings
totals, and remediation planning state. It has no approval, authorization,
claim, remediation, provider, or external-action mutation method.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from recoveryworks.cloud_diagnostic import AuthorizedCloudDiagnosticResult
from recoveryworks.models import Branch, CaseState, FindingState, canonical_hash
from recoveryworks.private_io import atomic_private_write
from recoveryworks.store import LocalBundleStore


@dataclass(frozen=True)
class PilotOperationsSnapshot:
    diagnostic_id: str
    client_id: str
    diagnostic_status: str
    evidence_readiness: dict[str, int]
    supersession_holds: tuple[dict[str, Any], ...]
    recovery_totals: dict[str, int]
    savings_totals: dict[str, Any]
    remediation_state: dict[str, Any]
    controls: dict[str, bool]

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "diagnostic_id": self.diagnostic_id,
            "client_id": self.client_id,
            "diagnostic_status": self.diagnostic_status,
            "evidence_readiness": self.evidence_readiness,
            "supersession_holds": list(self.supersession_holds),
            "recovery_totals": self.recovery_totals,
            "savings_totals": self.savings_totals,
            "remediation_state": self.remediation_state,
            "controls": self.controls,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "proof_hash": self.proof_hash,
            "console_mode": "READ_ONLY",
        }

    def to_markdown(self) -> str:
        readiness = self.evidence_readiness
        recovery = self.recovery_totals
        savings = self.savings_totals
        remediation = self.remediation_state
        lines = [
            "# Pilot Operations Console — Read Only",
            "",
            f"Diagnostic: {self.diagnostic_id}",
            f"Client: {self.client_id}",
            f"Status: {self.diagnostic_status}",
            f"Snapshot proof: {self.proof_hash}",
            "",
            "## Evidence readiness",
            "",
            f"- Active cloud cases: {readiness['active_cases']}",
            f"- Validated cases: {readiness['validated_cases']}",
            f"- Review cases: {readiness['review_cases']}",
            f"- Verified controlling rules: {readiness['verified_rule_cases']}",
            f"- Fully verified evidence: {readiness['verified_evidence_cases']}",
            f"- Cases requiring evidence review: {readiness['needs_review_cases']}",
            "",
            "## Supersession holds",
            "",
            f"- Holds: {len(self.supersession_holds)}",
        ]
        for hold in self.supersession_holds:
            lines.append(
                f"- {hold['candidate_id']} — "
                + ", ".join(hold["change_reasons"])
            )
        lines.extend([
            "",
            "## Recovery",
            "",
            f"- Potential: {recovery['potential_cents']} cents",
            f"- Validated: {recovery['validated_cents']} cents",
            f"- Authorized: {recovery['authorized_cents']} cents",
            f"- Claimed: {recovery['claimed_cents']} cents",
            f"- Recovered: {recovery['recovered_cents']} cents",
            f"- Superseded history: {recovery.get('superseded_cents', 0)} cents",
            "",
            "## Savings and diagnostics",
            "",
            f"- Estimated savings opportunities: "
            f"{savings['estimated_savings_opportunity_cents']} cents",
            f"- Verified realized savings: {savings['realized_savings_cents']} cents",
            f"- Anomaly exposure: {savings['estimated_anomaly_exposure_cents']} cents",
            f"- Reconciliation drift: {savings['reconciliation_drift_cents']} cents",
            "",
            "## Remediation",
            "",
            f"- State: {remediation['state']}",
            f"- Draft actions: {remediation['draft_action_count']}",
            "- Execution available from console: False",
            "",
            "## Controls",
            "",
            "- This console cannot approve cases.",
            "- This console cannot authorize recovery actions.",
            "- This console cannot execute remediation.",
            "- This console cannot mutate cloud infrastructure.",
            "",
        ])
        return "\n".join(lines)


def _ledger_path(result: AuthorizedCloudDiagnosticResult) -> Path:
    for value in result.pilot.private_paths:
        path = Path(value)
        if path.name == "ledger.json":
            return path
    raise ValueError("diagnostic result does not expose its private ledger path")


def build_pilot_operations_snapshot(
    result: AuthorizedCloudDiagnosticResult,
) -> PilotOperationsSnapshot:
    ledger = LocalBundleStore(_ledger_path(result)).load()
    if ledger is None:
        raise ValueError("diagnostic ledger is unavailable")

    records = [
        record
        for record in ledger.records()
        if record.finding.client_id == result.authorization.client_id
        and record.finding.branch is Branch.CLOUD
        and record.case_state not in {CaseState.REJECTED, CaseState.SUPERSEDED}
    ]
    validated = [
        record for record in records
        if record.finding.state is FindingState.VALIDATED
    ]
    review = [
        record for record in records
        if record.finding.state is FindingState.REVIEW
    ]
    verified_rules = [
        record for record in records
        if record.finding.rule is not None
        and record.finding.rule.verified_controlling
    ]
    verified_evidence = [
        record for record in records
        if all(item.verified for item in record.finding.evidence)
    ]
    needs_review = [
        record for record in records
        if (
            record.finding.rule is None
            or not record.finding.rule.verified_controlling
            or not all(item.verified for item in record.finding.evidence)
        )
    ]
    readiness = {
        "active_cases": len(records),
        "validated_cases": len(validated),
        "review_cases": len(review),
        "verified_rule_cases": len(verified_rules),
        "verified_evidence_cases": len(verified_evidence),
        "needs_review_cases": len(needs_review),
    }

    continuous = result.pilot.continuous_result
    holds = tuple(
        {
            "candidate_id": item.candidate_id,
            "proof_hash": item.proof_hash,
            "change_reasons": list(item.change_reasons),
            "period_start": item.period_start,
            "period_end": item.period_end,
        }
        for item in continuous.supersession_candidates
    )
    remediation_plan = continuous.remediation_plan
    if remediation_plan is None:
        remediation = {
            "state": "DISABLED_OR_NOT_REQUESTED",
            "draft_action_count": 0,
            "plan_id": None,
            "execution_available": False,
        }
    else:
        remediation = {
            "state": "DRAFT_PLAN_ONLY",
            "draft_action_count": len(remediation_plan.actions),
            "plan_id": remediation_plan.plan_id,
            "execution_available": False,
        }

    diagnostic_status = (
        "SUPERSESSION_REVIEW_REQUIRED"
        if holds
        else "COMPLETED_READ_ONLY"
    )
    savings = continuous.savings_report.as_dict()
    controls = {
        "read_only": True,
        "case_approval_available": False,
        "recovery_authorization_available": False,
        "remediation_execution_available": False,
        "cloud_mutation_available": False,
        "external_action_available": False,
    }
    return PilotOperationsSnapshot(
        diagnostic_id=result.intake_receipt.diagnostic_id,
        client_id=result.authorization.client_id,
        diagnostic_status=diagnostic_status,
        evidence_readiness=readiness,
        supersession_holds=holds,
        recovery_totals=dict(continuous.scan.report.totals),
        savings_totals={
            "estimated_savings_opportunity_cents":
                savings["estimated_savings_opportunity_cents"],
            "realized_savings_cents": savings["realized_savings_cents"],
            "estimated_anomaly_exposure_cents":
                savings["estimated_anomaly_exposure_cents"],
            "reconciliation_drift_cents":
                savings["reconciliation_drift_cents"],
        },
        remediation_state=remediation,
        controls=controls,
    )


def write_pilot_operations_snapshot(
    snapshot: PilotOperationsSnapshot,
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
