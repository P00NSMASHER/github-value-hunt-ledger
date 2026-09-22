"""Canonical serialization for RecoveryWorks findings and ledger records."""
from __future__ import annotations

from typing import Any

from .ledger import LedgerRecord
from .models import (
    Branch,
    CaseState,
    EvidenceRef,
    FindingState,
    RecoveryFinding,
    RecoveryMode,
    RuleRef,
)


def evidence_to_dict(ref: EvidenceRef) -> dict[str, Any]:
    return {
        "evidence_id": ref.evidence_id,
        "source_hash": ref.source_hash,
        "locator": ref.locator,
        "kind": ref.kind,
        "verified": ref.verified,
        "metadata": dict(ref.metadata),
    }


def evidence_from_dict(data: dict[str, Any]) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=data["evidence_id"],
        source_hash=data["source_hash"],
        locator=data["locator"],
        kind=data["kind"],
        verified=data["verified"],
        metadata=dict(data.get("metadata") or {}),
    )


def rule_to_dict(rule: RuleRef | None) -> dict[str, Any] | None:
    if rule is None:
        return None
    return {
        "rule_id": rule.rule_id,
        "source_hash": rule.source_hash,
        "effective_from": rule.effective_from,
        "effective_to": rule.effective_to,
        "verified_controlling": rule.verified_controlling,
        "source_locator": rule.source_locator,
        "jurisdiction": rule.jurisdiction,
        "metadata": dict(rule.metadata),
    }


def rule_from_dict(data: dict[str, Any] | None) -> RuleRef | None:
    if data is None:
        return None
    return RuleRef(
        rule_id=data["rule_id"],
        source_hash=data["source_hash"],
        effective_from=data["effective_from"],
        effective_to=data.get("effective_to"),
        verified_controlling=data["verified_controlling"],
        source_locator=data["source_locator"],
        jurisdiction=data.get("jurisdiction"),
        metadata=dict(data.get("metadata") or {}),
    )


def finding_to_dict(finding: RecoveryFinding) -> dict[str, Any]:
    return {
        "finding_id": finding.finding_id,
        "branch": finding.branch.value,
        "client_id": finding.client_id,
        "counterparty_id": finding.counterparty_id,
        "reference": finding.reference,
        "currency": finding.currency,
        "mode": finding.mode.value,
        "expected_cents": finding.expected_cents,
        "actual_cents": finding.actual_cents,
        "rule": rule_to_dict(finding.rule),
        "evidence": [evidence_to_dict(ref) for ref in finding.evidence],
        "state": finding.state.value,
        "reason": finding.reason,
        "confidence_basis": finding.confidence_basis,
        "metadata": dict(finding.metadata),
    }


def finding_from_dict(data: dict[str, Any]) -> RecoveryFinding:
    return RecoveryFinding(
        finding_id=data["finding_id"],
        branch=Branch(data["branch"]),
        client_id=data["client_id"],
        counterparty_id=data["counterparty_id"],
        reference=data["reference"],
        currency=data["currency"],
        mode=RecoveryMode(data["mode"]),
        expected_cents=data["expected_cents"],
        actual_cents=data["actual_cents"],
        rule=rule_from_dict(data.get("rule")),
        evidence=tuple(evidence_from_dict(item) for item in data["evidence"]),
        state=FindingState(data["state"]),
        reason=data["reason"],
        confidence_basis=data["confidence_basis"],
        metadata=dict(data.get("metadata") or {}),
    )


def record_to_dict(record: LedgerRecord) -> dict[str, Any]:
    return {
        "finding": finding_to_dict(record.finding),
        "case_state": record.case_state.value,
        "reviewer_approved": record.reviewer_approved,
        "reviewer_id": record.reviewer_id,
        "review_note": record.review_note,
        "authorization_id": record.authorization_id,
        "recovered_cents": record.recovered_cents,
        "fee_cents": record.fee_cents,
        "updated_at": record.updated_at,
    }


def record_from_dict(data: dict[str, Any]) -> LedgerRecord:
    return LedgerRecord(
        finding=finding_from_dict(data["finding"]),
        case_state=CaseState(data["case_state"]),
        reviewer_approved=data.get("reviewer_approved", False),
        reviewer_id=data.get("reviewer_id"),
        review_note=data.get("review_note"),
        authorization_id=data.get("authorization_id"),
        recovered_cents=data.get("recovered_cents", 0),
        fee_cents=data.get("fee_cents", 0),
        updated_at=data.get("updated_at"),
    )
