"""Deterministic commercial proof contracts for Freight Recovery.

This module intentionally contains no model calls. It encodes the minimum
state transitions needed to prevent discrepancy dollars from becoming
"recovered" dollars without authority, blind-order integrity, and settlement
proof.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Iterable


VALIDATED = "VALIDATED"
REVIEW = "REVIEW"


def canonical_hash(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class PopulationRow:
    invoice_id: str
    shipment_id: str
    customer_id: str
    carrier_id: str
    currency: str
    source_hash: str

    @property
    def row_key(self) -> str:
        return f"{self.invoice_id}|{self.shipment_id}"


@dataclass(frozen=True)
class PopulationManifest:
    buyer_id: str
    business_unit: str
    selection_rule: str
    rows: tuple[PopulationRow, ...]
    manifest_hash: str


@dataclass(frozen=True)
class AuthorityRef:
    authority_id: str
    customer_id: str
    carrier_id: str
    currency: str
    source_hash: str


@dataclass(frozen=True)
class Finding:
    finding_id: str
    invoice_id: str
    customer_id: str
    carrier_id: str
    currency: str
    authority_id: str | None
    expected_cents: int
    actual_cents: int
    status: str
    proof_hash: str

    @property
    def validated_cents(self) -> int:
        if self.status != VALIDATED:
            return 0
        return max(self.actual_cents - self.expected_cents, 0)


@dataclass(frozen=True)
class TruthManifest:
    population_hash: str
    findings: tuple[Finding, ...]
    truth_hash: str


@dataclass(frozen=True)
class IncumbentOutput:
    population_hash: str
    truth_hash: str
    finding_ids: tuple[str, ...]
    output_hash: str


@dataclass(frozen=True)
class SettlementEvent:
    settlement_id: str
    finding_id: str
    amount_cents: int
    currency: str
    source_hash: str
    incumbent_preidentified: bool = False
    automatic_credit: bool = False
    preexisting_credit: bool = False
    ambiguous_allocation: bool = False


@dataclass(frozen=True)
class SettlementAllocation:
    settlement_id: str
    finding_id: str
    allocated_cents: int
    fee_eligible_cents: int
    proof_hash: str


@dataclass(frozen=True)
class RecoveryCertificate:
    finding_id: str
    finding_proof_hash: str
    validated_cents: int
    realized_cents: int
    fee_eligible_cents: int
    settlement_proof_hashes: tuple[str, ...]
    certificate_hash: str


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")


def freeze_population(
    buyer_id: str,
    business_unit: str,
    selection_rule: str,
    rows: Iterable[PopulationRow],
) -> PopulationManifest:
    _require_text("buyer_id", buyer_id)
    _require_text("business_unit", business_unit)
    _require_text("selection_rule", selection_rule)

    normalized = tuple(sorted(rows, key=lambda row: row.row_key))
    if not normalized:
        raise ValueError("population must contain at least one row")

    seen: set[str] = set()
    for row in normalized:
        for name in (
            "invoice_id",
            "shipment_id",
            "customer_id",
            "carrier_id",
            "currency",
            "source_hash",
        ):
            _require_text(name, getattr(row, name))
        if row.row_key in seen:
            raise ValueError(f"duplicate population row: {row.row_key}")
        seen.add(row.row_key)

    body = {
        "schema": 1,
        "buyer_id": buyer_id,
        "business_unit": business_unit,
        "selection_rule": selection_rule,
        "rows": [asdict(row) for row in normalized],
    }
    return PopulationManifest(
        buyer_id=buyer_id,
        business_unit=business_unit,
        selection_rule=selection_rule,
        rows=normalized,
        manifest_hash=canonical_hash(body),
    )


def make_finding(
    *,
    finding_id: str,
    invoice_id: str,
    customer_id: str,
    carrier_id: str,
    currency: str,
    authority_id: str | None,
    expected_cents: int,
    actual_cents: int,
    status: str,
) -> Finding:
    for name, value in (
        ("finding_id", finding_id),
        ("invoice_id", invoice_id),
        ("customer_id", customer_id),
        ("carrier_id", carrier_id),
        ("currency", currency),
    ):
        _require_text(name, value)

    if expected_cents < 0 or actual_cents < 0:
        raise ValueError("money values must be non-negative")
    if status not in {VALIDATED, REVIEW}:
        raise ValueError("status must be VALIDATED or REVIEW")
    if status == VALIDATED and not authority_id:
        raise ValueError("validated finding requires controlling authority")

    body = {
        "schema": 1,
        "finding_id": finding_id,
        "invoice_id": invoice_id,
        "customer_id": customer_id,
        "carrier_id": carrier_id,
        "currency": currency,
        "authority_id": authority_id,
        "expected_cents": expected_cents,
        "actual_cents": actual_cents,
        "status": status,
    }
    return Finding(
        finding_id=finding_id,
        invoice_id=invoice_id,
        customer_id=customer_id,
        carrier_id=carrier_id,
        currency=currency,
        authority_id=authority_id,
        expected_cents=expected_cents,
        actual_cents=actual_cents,
        status=status,
        proof_hash=canonical_hash(body),
    )


def freeze_truth(
    population: PopulationManifest,
    authorities: Iterable[AuthorityRef],
    findings: Iterable[Finding],
) -> TruthManifest:
    authority_index: dict[str, AuthorityRef] = {}
    for authority in authorities:
        if authority.authority_id in authority_index:
            raise ValueError(f"duplicate authority_id: {authority.authority_id}")
        for name in ("authority_id", "customer_id", "carrier_id", "currency", "source_hash"):
            _require_text(name, getattr(authority, name))
        authority_index[authority.authority_id] = authority

    invoice_ids = {row.invoice_id for row in population.rows}
    normalized = tuple(sorted(findings, key=lambda finding: finding.finding_id))
    if not normalized:
        raise ValueError("truth manifest must contain findings")

    seen_ids: set[str] = set()
    for finding in normalized:
        if finding.finding_id in seen_ids:
            raise ValueError(f"duplicate finding_id: {finding.finding_id}")
        seen_ids.add(finding.finding_id)

        if finding.invoice_id not in invoice_ids:
            raise ValueError(f"finding outside frozen population: {finding.invoice_id}")

        if finding.status == REVIEW:
            if finding.validated_cents != 0:
                raise AssertionError("review finding cannot assert validated dollars")
            continue

        authority = authority_index.get(finding.authority_id or "")
        if authority is None:
            raise ValueError("validated finding authority is missing")

        identity = (
            finding.customer_id,
            finding.carrier_id,
            finding.currency,
        )
        authority_identity = (
            authority.customer_id,
            authority.carrier_id,
            authority.currency,
        )
        if identity != authority_identity:
            raise ValueError(
                "authority identity mismatch: customer/carrier/currency must match finding"
            )

    body = {
        "schema": 1,
        "population_hash": population.manifest_hash,
        "findings": [asdict(finding) for finding in normalized],
    }
    return TruthManifest(
        population_hash=population.manifest_hash,
        findings=normalized,
        truth_hash=canonical_hash(body),
    )


def open_incumbent_output(
    *,
    population: PopulationManifest,
    truth: TruthManifest | None,
    incumbent_population_hash: str,
    finding_ids: Iterable[str],
) -> IncumbentOutput:
    if truth is None or not truth.truth_hash:
        raise ValueError("buyer-owned truth must be frozen before incumbent output opens")
    if truth.population_hash != population.manifest_hash:
        raise ValueError("truth manifest is not bound to the frozen population")
    if incumbent_population_hash != population.manifest_hash:
        raise ValueError("incumbent output population hash mismatch")

    normalized_ids = tuple(sorted(str(item) for item in finding_ids))
    body = {
        "schema": 1,
        "population_hash": population.manifest_hash,
        "truth_hash": truth.truth_hash,
        "finding_ids": normalized_ids,
    }
    return IncumbentOutput(
        population_hash=population.manifest_hash,
        truth_hash=truth.truth_hash,
        finding_ids=normalized_ids,
        output_hash=canonical_hash(body),
    )


class RecoveryLedger:
    def __init__(self, truth: TruthManifest):
        self._findings = {finding.finding_id: finding for finding in truth.findings}
        self._allocations: dict[str, list[SettlementAllocation]] = {
            finding_id: [] for finding_id in self._findings
        }
        self._seen_settlement_ids: set[str] = set()
        self._seen_source_hashes: set[str] = set()

    def apply(self, event: SettlementEvent) -> SettlementAllocation:
        finding = self._findings.get(event.finding_id)
        if finding is None:
            raise ValueError("settlement references unknown finding")
        _require_text("settlement_id", event.settlement_id)
        _require_text("source_hash", event.source_hash)

        if event.amount_cents < 0:
            raise ValueError("settlement amount must be non-negative")
        if event.currency != finding.currency:
            raise ValueError("settlement currency mismatch")

        if event.ambiguous_allocation:
            return SettlementAllocation(
                settlement_id=event.settlement_id,
                finding_id=event.finding_id,
                allocated_cents=0,
                fee_eligible_cents=0,
                proof_hash=canonical_hash(
                    {
                        "finding_proof_hash": finding.proof_hash,
                        "settlement_id": event.settlement_id,
                        "source_hash": event.source_hash,
                        "ambiguous_allocation": True,
                    }
                ),
            )

        if event.settlement_id in self._seen_settlement_ids:
            raise ValueError("duplicate settlement_id")
        if event.source_hash in self._seen_source_hashes:
            raise ValueError("settlement source already consumed")

        realized_so_far = sum(
            allocation.allocated_cents for allocation in self._allocations[event.finding_id]
        )
        remaining = max(finding.validated_cents - realized_so_far, 0)
        allocated = min(event.amount_cents, remaining)

        disqualified = (
            event.incumbent_preidentified
            or event.automatic_credit
            or event.preexisting_credit
        )
        fee_eligible = 0 if disqualified else allocated

        body = {
            "schema": 1,
            "finding_id": finding.finding_id,
            "finding_proof_hash": finding.proof_hash,
            "settlement_id": event.settlement_id,
            "amount_cents": event.amount_cents,
            "allocated_cents": allocated,
            "fee_eligible_cents": fee_eligible,
            "currency": event.currency,
            "source_hash": event.source_hash,
            "incumbent_preidentified": event.incumbent_preidentified,
            "automatic_credit": event.automatic_credit,
            "preexisting_credit": event.preexisting_credit,
        }
        allocation = SettlementAllocation(
            settlement_id=event.settlement_id,
            finding_id=finding.finding_id,
            allocated_cents=allocated,
            fee_eligible_cents=fee_eligible,
            proof_hash=canonical_hash(body),
        )
        self._allocations[event.finding_id].append(allocation)
        self._seen_settlement_ids.add(event.settlement_id)
        self._seen_source_hashes.add(event.source_hash)
        return allocation

    def certificate(self, finding_id: str) -> RecoveryCertificate:
        finding = self._findings.get(finding_id)
        if finding is None:
            raise ValueError("unknown finding")

        allocations = self._allocations[finding_id]
        realized = min(
            sum(allocation.allocated_cents for allocation in allocations),
            finding.validated_cents,
        )
        fee_eligible = min(
            sum(allocation.fee_eligible_cents for allocation in allocations),
            realized,
        )
        settlement_proofs = tuple(allocation.proof_hash for allocation in allocations)

        body = {
            "schema": 1,
            "finding_id": finding.finding_id,
            "finding_proof_hash": finding.proof_hash,
            "validated_cents": finding.validated_cents,
            "realized_cents": realized,
            "fee_eligible_cents": fee_eligible,
            "settlement_proof_hashes": settlement_proofs,
        }
        return RecoveryCertificate(
            finding_id=finding.finding_id,
            finding_proof_hash=finding.proof_hash,
            validated_cents=finding.validated_cents,
            realized_cents=realized,
            fee_eligible_cents=fee_eligible,
            settlement_proof_hashes=settlement_proofs,
            certificate_hash=canonical_hash(body),
        )
