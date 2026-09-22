"""Deterministic fulfillment packets for client review and authorized recovery action."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .ledger import LedgerRecord, RecoveryLedger
from .models import CaseState, FindingState, canonical_hash


@dataclass(frozen=True)
class RecoveryPacket:
    finding_id: str
    branch: str
    client_id: str
    counterparty_id: str
    reference: str
    currency: str
    expected_cents: int
    actual_cents: int
    potential_recovery_cents: int
    case_state: str
    rule: Mapping[str, Any] | None
    evidence: tuple[Mapping[str, Any], ...]
    gates: Mapping[str, bool]
    recovered_cents: int
    fee_cents: int
    packet_hash: str


def _packet_body(record: LedgerRecord) -> dict[str, Any]:
    finding = record.finding
    rule = None
    if finding.rule is not None:
        rule = {
            "rule_id": finding.rule.rule_id,
            "source_hash": finding.rule.source_hash,
            "source_locator": finding.rule.source_locator,
            "effective_from": finding.rule.effective_from,
            "effective_to": finding.rule.effective_to,
            "jurisdiction": finding.rule.jurisdiction,
            "verified_controlling": finding.rule.verified_controlling,
            "proof_hash": finding.rule.proof_hash,
        }

    evidence = tuple({
        "evidence_id": ref.evidence_id,
        "source_hash": ref.source_hash,
        "locator": ref.locator,
        "kind": ref.kind,
        "verified": ref.verified,
        "proof_hash": ref.proof_hash,
    } for ref in sorted(finding.evidence, key=lambda item: item.evidence_id))

    gates = {
        "finding_validated": finding.state is FindingState.VALIDATED,
        "controlling_rule_verified": bool(finding.rule and finding.rule.verified_controlling),
        "all_evidence_verified": bool(finding.evidence) and all(ref.verified for ref in finding.evidence),
        "reviewer_approved": record.reviewer_approved,
        "customer_authorized": bool(record.authorization_id),
        "case_state_allows_submission": record.case_state is CaseState.AUTHORIZED,
    }
    return {
        "schema": 1,
        "finding_id": finding.finding_id,
        "branch": finding.branch.value,
        "client_id": finding.client_id,
        "counterparty_id": finding.counterparty_id,
        "reference": finding.reference,
        "currency": finding.currency,
        "expected_cents": finding.expected_cents,
        "actual_cents": finding.actual_cents,
        "potential_recovery_cents": finding.potential_recovery_cents,
        "case_state": record.case_state.value,
        "rule": rule,
        "evidence": evidence,
        "gates": gates,
        "recovered_cents": record.recovered_cents,
        "fee_cents": record.fee_cents,
    }


def build_recovery_packet(record: LedgerRecord) -> RecoveryPacket:
    body = _packet_body(record)
    packet_hash = canonical_hash(body)
    return RecoveryPacket(
        finding_id=body["finding_id"],
        branch=body["branch"],
        client_id=body["client_id"],
        counterparty_id=body["counterparty_id"],
        reference=body["reference"],
        currency=body["currency"],
        expected_cents=body["expected_cents"],
        actual_cents=body["actual_cents"],
        potential_recovery_cents=body["potential_recovery_cents"],
        case_state=body["case_state"],
        rule=body["rule"],
        evidence=body["evidence"],
        gates=body["gates"],
        recovered_cents=body["recovered_cents"],
        fee_cents=body["fee_cents"],
        packet_hash=packet_hash,
    )


def submission_ready(packet: RecoveryPacket) -> bool:
    return all(packet.gates.values())


def build_client_portfolio_packet(ledger: RecoveryLedger, client_id: str) -> dict[str, Any]:
    if not isinstance(client_id, str) or not client_id.strip():
        raise ValueError("client_id is required")
    client_id = client_id.strip()
    packets = tuple(
        build_recovery_packet(record)
        for record in ledger.records()
        if record.finding.client_id == client_id
    )

    branches: dict[str, dict[str, int]] = {}
    total_potential = total_validated = total_recovered = total_fees = 0
    for packet in packets:
        bucket = branches.setdefault(packet.branch, {
            "cases": 0,
            "potential_cents": 0,
            "validated_cents": 0,
            "recovered_cents": 0,
            "fee_cents": 0,
        })
        validated = packet.potential_recovery_cents if packet.gates["finding_validated"] else 0
        bucket["cases"] += 1
        bucket["potential_cents"] += packet.potential_recovery_cents
        bucket["validated_cents"] += validated
        bucket["recovered_cents"] += packet.recovered_cents
        bucket["fee_cents"] += packet.fee_cents
        total_potential += packet.potential_recovery_cents
        total_validated += validated
        total_recovered += packet.recovered_cents
        total_fees += packet.fee_cents

    body = {
        "schema": 1,
        "client_id": client_id,
        "ledger_snapshot_hash": ledger.snapshot_hash,
        "branches": branches,
        "totals": {
            "cases": len(packets),
            "potential_cents": total_potential,
            "validated_cents": total_validated,
            "recovered_cents": total_recovered,
            "fee_cents": total_fees,
        },
        "case_packet_hashes": sorted(packet.packet_hash for packet in packets),
    }
    return {**body, "portfolio_hash": canonical_hash(body)}
