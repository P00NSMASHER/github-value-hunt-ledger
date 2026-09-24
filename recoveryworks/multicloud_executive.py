"""Reviewed executive rollup over isolated provider assurance reports.

This layer never merges rules, evidence packets, findings, or provider state.
It verifies each provider assurance report proof hash and only aggregates a
fixed allowlist of same-currency summary categories with identical semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from recoveryworks.models import canonical_hash
from recoveryworks.multicloud_orchestration import MultiCloudExecutionResult
from recoveryworks.private_io import atomic_private_write


_COMPARABLE_RECOVERY_FIELDS = (
    "potential_cents",
    "review_cents",
    "validated_cents",
    "authorized_cents",
    "claimed_cents",
    "recovered_cents",
    "fee_cents",
    "superseded_cents",
)
_COMPARABLE_SAVINGS_FIELDS = (
    "estimated_savings_opportunity_cents",
    "realized_savings_cents",
)
_COMPARABLE_DIAGNOSTIC_FIELDS = (
    "estimated_anomaly_exposure_cents",
    "reconciliation_drift_cents",
)


def _verified_report(path: str | Path, expected_hash: str) -> Mapping[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("provider assurance report is not readable JSON") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("provider assurance report must be a JSON object")
    actual = payload.get("proof_hash")
    if actual != expected_hash:
        raise ValueError("provider assurance report no longer matches execution result")
    identity = {key: value for key, value in payload.items() if key != "proof_hash"}
    if canonical_hash(identity) != actual:
        raise ValueError("provider assurance report proof hash mismatch")
    controls = payload.get("controls")
    if not isinstance(controls, Mapping):
        raise ValueError("provider assurance report controls are missing")
    required_controls = {
        "recovery_requires_verified_rule": True,
        "recovery_requires_verified_evidence": True,
        "estimated_savings_excluded_from_recovery": True,
        "anomaly_exposure_excluded_from_savings": True,
        "realized_savings_requires_verified_measurement": True,
        "cloud_mutation_authorized_by_report": False,
        "external_recovery_action_authorized_by_report": False,
    }
    for key, expected in required_controls.items():
        if controls.get(key) is not expected:
            raise ValueError(
                f"provider assurance report control mismatch: {key}"
            )
    return payload


@dataclass(frozen=True)
class MultiCloudExecutiveRollup:
    rollup_id: str
    orchestration_execution_proof_hash: str
    client_id: str
    currency: str
    providers: tuple[str, ...]
    provider_reports: tuple[dict[str, Any], ...]
    comparable_totals: dict[str, int]
    comparable_categories: tuple[str, ...]
    excluded_from_rollup: tuple[str, ...]
    provider_authority_merged: bool = False
    provider_evidence_merged: bool = False
    provider_findings_merged: bool = False

    def __post_init__(self) -> None:
        if (
            self.provider_authority_merged
            or self.provider_evidence_merged
            or self.provider_findings_merged
        ):
            raise ValueError("executive rollup cannot merge provider proof planes")
        expected = "multicloud-executive-rollup:" + canonical_hash(
            self._identity()
        )
        if self.rollup_id != expected:
            raise ValueError("rollup_id does not bind executive rollup")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "orchestration_execution_proof_hash":
                self.orchestration_execution_proof_hash,
            "client_id": self.client_id,
            "currency": self.currency,
            "providers": list(self.providers),
            "provider_reports": list(self.provider_reports),
            "comparable_totals": dict(self.comparable_totals),
            "comparable_categories": list(self.comparable_categories),
            "excluded_from_rollup": list(self.excluded_from_rollup),
            "provider_authority_merged": False,
            "provider_evidence_merged": False,
            "provider_findings_merged": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "rollup_id": self.rollup_id,
            "proof_hash": self.proof_hash,
            "state": "EXECUTIVE_SUMMARY_ONLY",
        }

    def to_markdown(self) -> str:
        totals = self.comparable_totals
        lines = [
            "# Multi-Cloud Executive Rollup",
            "",
            f"Client: {self.client_id}",
            f"Currency: {self.currency}",
            f"Providers: {', '.join(p.upper() for p in self.providers)}",
            f"Rollup proof: {self.proof_hash}",
            "",
            "## Comparable financial categories",
            "",
            f"- Active potential recovery: {totals['potential_cents']} cents",
            f"- Review candidate recovery: {totals['review_cents']} cents",
            f"- Validated recovery: {totals['validated_cents']} cents",
            f"- Authorized recovery: {totals['authorized_cents']} cents",
            f"- Claimed recovery: {totals['claimed_cents']} cents",
            f"- Recovered cash: {totals['recovered_cents']} cents",
            f"- Recovery fees: {totals['fee_cents']} cents",
            f"- Superseded historical recovery: {totals['superseded_cents']} cents",
            f"- Prospective savings: {totals['estimated_savings_opportunity_cents']} cents",
            f"- Verified realized savings: {totals['realized_savings_cents']} cents",
            "",
            "## Comparable diagnostics",
            "",
            f"- Anomaly exposure estimate: {totals['estimated_anomaly_exposure_cents']} cents",
            f"- Reconciliation drift: {totals['reconciliation_drift_cents']} cents",
            "",
            "## Provider report proofs",
            "",
        ]
        for row in self.provider_reports:
            lines.extend([
                f"- {row['provider'].upper()}: report proof {row['report_proof_hash']}",
                f"  - report: {row['report_path']}",
                f"  - state head: {row['state_head_hash'] or 'none'}",
            ])
        lines.extend([
            "",
            "## Non-aggregation boundary",
            "",
            "- Provider rules are not merged.",
            "- Provider evidence packets are not merged.",
            "- Individual findings are not merged across clouds.",
            "- Recommendations/confidence scores are not aggregated.",
            "- This rollup cannot authorize recovery or cloud mutation.",
            "",
        ])
        return "\n".join(lines)


def build_multicloud_executive_rollup(
    execution: MultiCloudExecutionResult,
) -> MultiCloudExecutiveRollup:
    providers: list[str] = []
    provider_reports: list[dict[str, Any]] = []
    totals = {
        key: 0
        for key in (
            *_COMPARABLE_RECOVERY_FIELDS,
            *_COMPARABLE_SAVINGS_FIELDS,
            *_COMPARABLE_DIAGNOSTIC_FIELDS,
        )
    }

    for provider_run in execution.provider_runs:
        payload = _verified_report(
            provider_run.assurance_report_path,
            provider_run.assurance_report_proof_hash,
        )
        if payload.get("client_id") != execution.client_id:
            raise ValueError("provider report client_id mismatch")
        if payload.get("currency") != execution.currency:
            raise ValueError("provider report currency mismatch")

        recovery = payload.get("recovery_summary")
        savings = payload.get("savings_summary")
        diagnostics = payload.get("diagnostics")
        if not all(
            isinstance(value, Mapping)
            for value in (recovery, savings, diagnostics)
        ):
            raise ValueError("provider report summary surfaces are missing")
        recovery_totals = recovery.get("totals")
        if not isinstance(recovery_totals, Mapping):
            raise ValueError("provider recovery totals are missing")

        provider_summary: dict[str, int] = {}
        for key in _COMPARABLE_RECOVERY_FIELDS:
            value = recovery_totals.get(key)
            if type(value) is not int or value < 0:
                raise ValueError(f"provider recovery total is invalid: {key}")
            totals[key] += value
            provider_summary[key] = value
        for key in _COMPARABLE_SAVINGS_FIELDS:
            value = savings.get(key)
            if type(value) is not int or value < 0:
                raise ValueError(f"provider savings total is invalid: {key}")
            totals[key] += value
            provider_summary[key] = value
        for key in _COMPARABLE_DIAGNOSTIC_FIELDS:
            value = diagnostics.get(key)
            if type(value) is not int or value < 0:
                raise ValueError(f"provider diagnostic total is invalid: {key}")
            totals[key] += value
            provider_summary[key] = value

        providers.append(provider_run.provider)
        provider_reports.append({
            "provider": provider_run.provider,
            "report_path": provider_run.assurance_report_path,
            "report_proof_hash": provider_run.assurance_report_proof_hash,
            "state_head_hash": provider_run.state_head_hash,
            "summary": provider_summary,
        })

    provider_reports.sort(key=lambda row: row["provider"])
    providers = sorted(providers)
    categories = (
        *_COMPARABLE_RECOVERY_FIELDS,
        *_COMPARABLE_SAVINGS_FIELDS,
        *_COMPARABLE_DIAGNOSTIC_FIELDS,
    )
    excluded = (
        "case counts",
        "review backlog rows",
        "individual findings",
        "controlling rules",
        "evidence packets",
        "provider recommendations",
        "confidence scores",
        "resource identities",
    )
    identity = {
        "schema": 1,
        "orchestration_execution_proof_hash": execution.proof_hash,
        "client_id": execution.client_id,
        "currency": execution.currency,
        "providers": providers,
        "provider_reports": provider_reports,
        "comparable_totals": totals,
        "comparable_categories": list(categories),
        "excluded_from_rollup": list(excluded),
        "provider_authority_merged": False,
        "provider_evidence_merged": False,
        "provider_findings_merged": False,
    }
    return MultiCloudExecutiveRollup(
        rollup_id="multicloud-executive-rollup:" + canonical_hash(identity),
        orchestration_execution_proof_hash=execution.proof_hash,
        client_id=execution.client_id,
        currency=execution.currency,
        providers=tuple(providers),
        provider_reports=tuple(provider_reports),
        comparable_totals=totals,
        comparable_categories=tuple(categories),
        excluded_from_rollup=excluded,
    )


def write_multicloud_executive_rollup(
    rollup: MultiCloudExecutiveRollup,
    *,
    json_path: str | Path,
    markdown_path: str | Path,
) -> None:
    atomic_private_write(
        Path(json_path),
        (
            json.dumps(
                rollup.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8"),
    )
    atomic_private_write(
        Path(markdown_path),
        (rollup.to_markdown() + "\n").encode("utf-8"),
    )
