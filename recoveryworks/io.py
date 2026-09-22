"""JSON boundary for deterministic Recovery Scan 360 execution."""
from __future__ import annotations

from typing import Any, Mapping

from .branches.common import observation
from .engine import RecoveryObservation
from .ledger import RecoveryLedger
from .models import Branch, EvidenceRef, RuleRef
from .packets import build_client_portfolio_packet, build_recovery_packet, submission_ready
from .scan import SourceManifestEntry, freeze_scan, run_scan


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _rule(value: Any) -> RuleRef | None:
    if value is None:
        return None
    item = _mapping(value, "rule")
    return RuleRef(
        rule_id=item["rule_id"],
        source_hash=item["source_hash"],
        effective_from=item["effective_from"],
        effective_to=item.get("effective_to"),
        verified_controlling=item.get("verified_controlling", False),
        source_locator=item["source_locator"],
        jurisdiction=item.get("jurisdiction"),
        metadata=item.get("metadata", {}),
    )


def _evidence(values: Any) -> tuple[EvidenceRef, ...]:
    if not isinstance(values, list) or not values:
        raise ValueError("evidence must be a non-empty list")
    return tuple(
        EvidenceRef(
            evidence_id=item["evidence_id"],
            source_hash=item["source_hash"],
            locator=item["locator"],
            kind=item["kind"],
            verified=item.get("verified", False),
            metadata=item.get("metadata", {}),
        )
        for raw in values
        for item in (_mapping(raw, "evidence item"),)
    )


def observation_from_payload(value: Any) -> RecoveryObservation:
    item = _mapping(value, "observation")
    branch = Branch(item["branch"])
    occurred_on = item["occurred_on"]
    return observation(
        branch=branch,
        client_id=item["client_id"],
        counterparty_id=item["counterparty_id"],
        reference=item["reference"],
        currency=item.get("currency", "USD"),
        expected_cents=item["expected_cents"],
        actual_cents=item["actual_cents"],
        occurred_on=occurred_on,
        rule=_rule(item.get("rule")),
        evidence=_evidence(item["evidence"]),
        reason=item["reason"],
        confidence_basis=item["confidence_basis"],
        metadata=item.get("metadata", {}),
    )


def execute_scan_payload(payload: Any) -> tuple[dict[str, Any], RecoveryLedger]:
    """Run a frozen scan and return both the report and its durable ledger object."""
    root = _mapping(payload, "payload")
    if root.get("schema") != 1:
        raise ValueError("unsupported payload schema")

    branches_raw = root.get("branches")
    if not isinstance(branches_raw, list) or not branches_raw:
        raise ValueError("branches must be a non-empty list")
    branches = tuple(Branch(value) for value in branches_raw)

    sources_raw = root.get("sources")
    if not isinstance(sources_raw, list) or not sources_raw:
        raise ValueError("sources must be a non-empty list")
    sources = tuple(
        SourceManifestEntry(
            source_id=item["source_id"],
            branch=Branch(item["branch"]),
            source_hash=item["source_hash"],
            locator=item["locator"],
            kind=item["kind"],
        )
        for raw in sources_raw
        for item in (_mapping(raw, "source"),)
    )

    observations_raw = root.get("observations")
    if not isinstance(observations_raw, list):
        raise ValueError("observations must be a list")
    observations = tuple(observation_from_payload(item) for item in observations_raw)

    manifest = freeze_scan(
        scan_id=root["scan_id"],
        client_id=root["client_id"],
        branches=branches,
        selection_rule=root["selection_rule"],
        sources=sources,
    )
    batch = run_scan(manifest, observations)

    ledger = RecoveryLedger()
    records = tuple(ledger.add(finding) for finding in batch.findings)
    case_packets = tuple(build_recovery_packet(record) for record in records)
    portfolio = build_client_portfolio_packet(ledger, manifest.client_id)

    findings = [{
        "finding_id": packet.finding_id,
        "branch": packet.branch,
        "reference": packet.reference,
        "case_state": packet.case_state,
        "potential_recovery_cents": packet.potential_recovery_cents,
        "packet_hash": packet.packet_hash,
        "submission_ready": submission_ready(packet),
    } for packet in case_packets]

    result = {
        "schema": 1,
        "scan_id": manifest.scan_id,
        "client_id": manifest.client_id,
        "manifest_hash": manifest.manifest_hash,
        "batch_hash": batch.batch_hash,
        "ledger_snapshot_hash": ledger.snapshot_hash,
        "audit_head": ledger.audit_head,
        "portfolio": portfolio,
        "findings": findings,
    }
    return result, ledger


def run_scan_payload(payload: Any) -> dict[str, Any]:
    result, _ = execute_scan_payload(payload)
    return result
