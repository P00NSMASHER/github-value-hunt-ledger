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
    claim_evidence: Mapping[str, Any] | None
    recovery_evidence: Mapping[str, Any] | None
    recovered_cents: int
    fee_cents: int
    packet_hash: str


def _evidence_body(ref) -> dict[str, Any] | None:
    if ref is None:
        return None
    return {
        "evidence_id": ref.evidence_id,
        "source_hash": ref.source_hash,
        "locator": ref.locator,
        "kind": ref.kind,
        "verified": ref.verified,
        "proof_hash": ref.proof_hash,
    }


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

    evidence = tuple(
        _evidence_body(ref)
        for ref in sorted(finding.evidence, key=lambda item: item.evidence_id)
    )

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
        "claim_evidence": _evidence_body(record.claim_evidence),
        "recovery_evidence": _evidence_body(record.recovery_evidence),
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
        claim_evidence=body["claim_evidence"],
        recovery_evidence=body["recovery_evidence"],
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

    def new_bucket() -> dict[str, int]:
        return {
            "cases": 0,
            "potential_cents": 0,
            "validated_cents": 0,
            "recovered_cents": 0,
            "fee_cents": 0,
        }

    def add(bucket: dict[str, int], packet: RecoveryPacket) -> None:
        validated = packet.potential_recovery_cents if packet.gates["finding_validated"] else 0
        bucket["cases"] += 1
        bucket["potential_cents"] += packet.potential_recovery_cents
        bucket["validated_cents"] += validated
        bucket["recovered_cents"] += packet.recovered_cents
        bucket["fee_cents"] += packet.fee_cents

    branches: dict[str, dict[str, Any]] = {}
    currencies: dict[str, dict[str, int]] = {}
    for packet in packets:
        currency_bucket = currencies.setdefault(packet.currency, new_bucket())
        add(currency_bucket, packet)

        branch = branches.setdefault(packet.branch, {
            "cases": 0,
            "currencies": {},
        })
        branch_currency = branch["currencies"].setdefault(packet.currency, new_bucket())
        add(branch_currency, packet)
        branch["cases"] += 1

    for branch in branches.values():
        branch["currency_count"] = len(branch["currencies"])
        if len(branch["currencies"]) == 1:
            only = next(iter(branch["currencies"].values()))
            for key in ("potential_cents", "validated_cents", "recovered_cents", "fee_cents"):
                branch[key] = only[key]
        else:
            for key in ("potential_cents", "validated_cents", "recovered_cents", "fee_cents"):
                branch[key] = None

    totals: dict[str, Any] = {
        "cases": len(packets),
        "currency_count": len(currencies),
    }
    if len(currencies) == 1:
        only = next(iter(currencies.values()))
        for key in ("potential_cents", "validated_cents", "recovered_cents", "fee_cents"):
            totals[key] = only[key]
    else:
        for key in ("potential_cents", "validated_cents", "recovered_cents", "fee_cents"):
            totals[key] = None

    body = {
        "schema": 2,
        "client_id": client_id,
        "ledger_snapshot_hash": ledger.snapshot_hash,
        "branches": branches,
        "currencies": currencies,
        "totals": totals,
        "case_packet_hashes": sorted(packet.packet_hash for packet in packets),
    }
    return {**body, "portfolio_hash": canonical_hash(body)}
