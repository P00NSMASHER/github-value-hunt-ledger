"""Deterministic commercial proof contracts for Freight Recovery.

This module intentionally contains no model calls. It encodes the minimum
state transitions needed to prevent discrepancy dollars from becoming
"recovered" dollars without buyer/business-unit scope, controlling authority,
blind-order integrity, and settlement proof.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
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

    @property
    def identity_key(self) -> tuple[str, str]:
        """Unambiguous internal key; row_key remains display-only."""
        return (self.invoice_id, self.shipment_id)


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
    buyer_id: str
    business_unit: str
    customer_id: str
    carrier_id: str
    currency: str
    source_hash: str


@dataclass(frozen=True)
class Finding:
    finding_id: str
    buyer_id: str
    business_unit: str
    invoice_id: str
    shipment_id: str
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
    buyer_id: str
    business_unit: str
    population_hash: str
    authorities: tuple[AuthorityRef, ...]
    findings: tuple[Finding, ...]
    truth_hash: str


@dataclass(frozen=True)
class SealedIncumbentSubmission:
    buyer_id: str
    business_unit: str
    population_hash: str
    source_hash: str
    sealed_hash: str


@dataclass(frozen=True)
class IncumbentOutput:
    buyer_id: str
    business_unit: str
    population_hash: str
    truth_hash: str
    submission_hash: str
    source_hash: str
    finding_ids: tuple[str, ...]
    output_hash: str


@dataclass(frozen=True)
class SettlementEvent:
    buyer_id: str
    business_unit: str
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
    buyer_id: str
    business_unit: str
    settlement_id: str
    finding_id: str
    allocated_cents: int
    fee_eligible_cents: int
    proof_hash: str


@dataclass(frozen=True)
class RecoveryCertificate:
    buyer_id: str
    business_unit: str
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


def _require_canonical_identity(name: str, value: str) -> None:
    _require_text(name, value)
    if value != value.strip():
        raise ValueError(name + " must not contain surrounding whitespace")
    if unicodedata.normalize("NFC", value) != value:
        raise ValueError(name + " must use canonical Unicode (NFC)")
    if any(unicodedata.category(character).startswith("C") for character in value):
        raise ValueError(name + " contains control characters")


def _require_scope(
    buyer_id: str,
    business_unit: str,
    expected_buyer: str,
    expected_business_unit: str,
    label: str,
) -> None:
    if (buyer_id, business_unit) != (expected_buyer, expected_business_unit):
        raise ValueError(f"{label} scope mismatch: buyer/business_unit must match frozen population")


def freeze_population(
    buyer_id: str,
    business_unit: str,
    selection_rule: str,
    rows: Iterable[PopulationRow],
) -> PopulationManifest:
    _require_text("buyer_id", buyer_id)
    _require_text("business_unit", business_unit)
    _require_text("selection_rule", selection_rule)

    normalized = tuple(sorted(rows, key=lambda row: row.identity_key))
    if not normalized:
        raise ValueError("population must contain at least one row")

    seen: set[tuple[str, str]] = set()
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
        for name in ("invoice_id", "shipment_id"):
            _require_canonical_identity(name, getattr(row, name))
        if row.identity_key in seen:
            raise ValueError(f"duplicate population row: {row.row_key}")
        seen.add(row.identity_key)

    body = {
        "schema": 2,
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


def _verified_population(population: PopulationManifest) -> PopulationManifest:
    """Rebuild a supplied population before it can anchor money-bearing truth."""
    if type(population) is not PopulationManifest:
        raise ValueError("population must be a PopulationManifest")
    verified = freeze_population(
        population.buyer_id,
        population.business_unit,
        population.selection_rule,
        population.rows,
    )
    if verified != population:
        raise ValueError("population proof or canonical ordering mismatch")
    return verified


def make_finding(
    *,
    finding_id: str,
    buyer_id: str,
    business_unit: str,
    invoice_id: str,
    shipment_id: str,
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
        ("buyer_id", buyer_id),
        ("business_unit", business_unit),
        ("invoice_id", invoice_id),
        ("shipment_id", shipment_id),
        ("customer_id", customer_id),
        ("carrier_id", carrier_id),
        ("currency", currency),
    ):
        _require_text(name, value)
    _require_canonical_identity("finding_id", finding_id)
    if authority_id is not None:
        _require_canonical_identity("authority_id", authority_id)

    for name, value in (
        ("expected_cents", expected_cents),
        ("actual_cents", actual_cents),
    ):
        if type(value) is not int or value < 0:
            raise ValueError(name + " must be non-negative integer cents")
    if status not in {VALIDATED, REVIEW}:
        raise ValueError("status must be VALIDATED or REVIEW")
    if status == VALIDATED and not authority_id:
        raise ValueError("validated finding requires controlling authority")

    body = {
        "schema": 2,
        "finding_id": finding_id,
        "buyer_id": buyer_id,
        "business_unit": business_unit,
        "invoice_id": invoice_id,
        "shipment_id": shipment_id,
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
        buyer_id=buyer_id,
        business_unit=business_unit,
        invoice_id=invoice_id,
        shipment_id=shipment_id,
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
    population = _verified_population(population)
    authority_index: dict[str, AuthorityRef] = {}
    for authority in authorities:
        if authority.authority_id in authority_index:
            raise ValueError(f"duplicate authority_id: {authority.authority_id}")
        for name in (
            "authority_id",
            "buyer_id",
            "business_unit",
            "customer_id",
            "carrier_id",
            "currency",
            "source_hash",
        ):
            _require_text(name, getattr(authority, name))
        _require_canonical_identity("authority_id", authority.authority_id)
        _require_scope(
            authority.buyer_id,
            authority.business_unit,
            population.buyer_id,
            population.business_unit,
            "authority",
        )
        authority_index[authority.authority_id] = authority

    normalized_authorities = tuple(
        sorted(authority_index.values(), key=lambda authority: authority.authority_id)
    )
    row_index = {row.identity_key: row for row in population.rows}
    normalized = tuple(sorted(findings, key=lambda finding: finding.finding_id))

    seen_ids: set[str] = set()
    for finding in normalized:
        if finding.finding_id in seen_ids:
            raise ValueError(f"duplicate finding_id: {finding.finding_id}")
        seen_ids.add(finding.finding_id)

        _require_scope(
            finding.buyer_id,
            finding.business_unit,
            population.buyer_id,
            population.business_unit,
            "finding",
        )

        row = row_index.get((finding.invoice_id, finding.shipment_id))
        if row is None:
            raise ValueError(
                f"finding outside frozen population: {finding.invoice_id}|{finding.shipment_id}"
            )

        row_identity = (row.customer_id, row.carrier_id, row.currency)
        finding_identity = (
            finding.customer_id,
            finding.carrier_id,
            finding.currency,
        )
        if finding_identity != row_identity:
            raise ValueError(
                "finding identity mismatch: customer/carrier/currency must match frozen shipment row"
            )

        if finding.status == REVIEW:
            if finding.validated_cents != 0:
                raise AssertionError("review finding cannot assert validated dollars")
            continue

        authority = authority_index.get(finding.authority_id or "")
        if authority is None:
            raise ValueError("validated finding authority is missing")

        authority_identity = (
            authority.customer_id,
            authority.carrier_id,
            authority.currency,
        )
        if finding_identity != authority_identity:
            raise ValueError(
                "authority identity mismatch: customer/carrier/currency must match finding"
            )

    body = {
        "schema": 3,
        "buyer_id": population.buyer_id,
        "business_unit": population.business_unit,
        "population_hash": population.manifest_hash,
        "authorities": [asdict(authority) for authority in normalized_authorities],
        "findings": [asdict(finding) for finding in normalized],
    }
    return TruthManifest(
        buyer_id=population.buyer_id,
        business_unit=population.business_unit,
        population_hash=population.manifest_hash,
        authorities=normalized_authorities,
        findings=normalized,
        truth_hash=canonical_hash(body),
    )


def seal_incumbent_submission(
    population: PopulationManifest,
    source_hash: str,
) -> SealedIncumbentSubmission:
    _require_text("source_hash", source_hash)
    body = {
        "schema": 1,
        "buyer_id": population.buyer_id,
        "business_unit": population.business_unit,
        "population_hash": population.manifest_hash,
        "source_hash": source_hash,
    }
    return SealedIncumbentSubmission(
        buyer_id=population.buyer_id,
        business_unit=population.business_unit,
        population_hash=population.manifest_hash,
        source_hash=source_hash,
        sealed_hash=canonical_hash(body),
    )


def open_incumbent_output(
    *,
    population: PopulationManifest,
    truth: TruthManifest | None,
    submission: SealedIncumbentSubmission,
    finding_ids: Iterable[str],
) -> IncumbentOutput:
    if truth is None or not truth.truth_hash:
        raise ValueError("buyer-owned truth must be frozen before incumbent output opens")
    if truth.population_hash != population.manifest_hash:
        raise ValueError("truth manifest is not bound to the frozen population")
    _require_scope(
        truth.buyer_id,
        truth.business_unit,
        population.buyer_id,
        population.business_unit,
        "truth",
    )
    _require_scope(
        submission.buyer_id,
        submission.business_unit,
        population.buyer_id,
        population.business_unit,
        "incumbent submission",
    )
    if submission.population_hash != population.manifest_hash:
        raise ValueError("incumbent submission population hash mismatch")

    normalized_ids = tuple(sorted(str(item) for item in finding_ids))
    if len(normalized_ids) != len(set(normalized_ids)):
        raise ValueError("duplicate incumbent finding_id")
    truth_finding_ids = {finding.finding_id for finding in truth.findings}
    for finding_id in normalized_ids:
        _require_canonical_identity("finding_id", finding_id)
        if finding_id not in truth_finding_ids:
            raise ValueError("incumbent finding_id is not in frozen truth")

    body = {
        "schema": 2,
        "buyer_id": population.buyer_id,
        "business_unit": population.business_unit,
        "population_hash": population.manifest_hash,
        "truth_hash": truth.truth_hash,
        "submission_hash": submission.sealed_hash,
        "source_hash": submission.source_hash,
        "finding_ids": normalized_ids,
    }
    return IncumbentOutput(
        buyer_id=population.buyer_id,
        business_unit=population.business_unit,
        population_hash=population.manifest_hash,
        truth_hash=truth.truth_hash,
        submission_hash=submission.sealed_hash,
        source_hash=submission.source_hash,
        finding_ids=normalized_ids,
        output_hash=canonical_hash(body),
    )


def _require_ledger_digest(name: str, value: str, expected: str | None = None) -> None:
    if (type(value) is not str or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)):
        raise ValueError(name + " must be lowercase SHA-256")
    if expected is not None and value != expected:
        raise ValueError(name + " hash mismatch")


def _verified_ledger_truth(truth: TruthManifest) -> TruthManifest:
    """Validate supplied truth metadata and copy findings before accounting.

    The ledger has no population rows or original files. This checks internal
    integrity and authority relationships, not population membership, actual
    source bytes, human consent, or independently confirmed recoveries.
    """
    if type(truth) is not TruthManifest:
        raise ValueError("truth must be a TruthManifest")
    _require_text("buyer_id", truth.buyer_id)
    _require_text("business_unit", truth.business_unit)
    _require_ledger_digest("population", truth.population_hash)
    if type(truth.authorities) not in (tuple, list) or type(truth.findings) not in (tuple, list):
        raise ValueError("truth authorities and findings must be record sequences")

    authority_index: dict[str, AuthorityRef] = {}
    for authority in truth.authorities:
        if type(authority) is not AuthorityRef:
            raise ValueError("truth authority must be an AuthorityRef")
        for name in ("authority_id", "buyer_id", "business_unit", "customer_id",
                     "carrier_id", "currency", "source_hash"):
            _require_text(name, getattr(authority, name))
        _require_canonical_identity("authority_id", authority.authority_id)
        _require_scope(authority.buyer_id, authority.business_unit,
                       truth.buyer_id, truth.business_unit, "authority")
        if authority.authority_id in authority_index:
            raise ValueError("duplicate authority_id: " + authority.authority_id)
        authority_index[authority.authority_id] = AuthorityRef(**asdict(authority))

    finding_index: dict[str, Finding] = {}
    for finding in truth.findings:
        if type(finding) is not Finding:
            raise ValueError("truth finding must be a Finding")
        for name in ("expected_cents", "actual_cents"):
            value = getattr(finding, name)
            if type(value) is not int or value < 0:
                raise ValueError(name + " must be non-negative integer cents")
        if type(finding.status) is not str:
            raise ValueError("status must be VALIDATED or REVIEW")
        if finding.authority_id is not None:
            _require_canonical_identity("authority_id", finding.authority_id)
        fields = asdict(finding)
        fields.pop("proof_hash")
        verified = make_finding(**fields)
        _require_ledger_digest("finding proof", finding.proof_hash, verified.proof_hash)
        _require_scope(verified.buyer_id, verified.business_unit,
                       truth.buyer_id, truth.business_unit, "finding")
        if verified.finding_id in finding_index:
            raise ValueError("duplicate finding_id: " + verified.finding_id)
        if verified.status == VALIDATED:
            authority = authority_index.get(verified.authority_id)
            if authority is None:
                raise ValueError("validated finding authority is missing")
            if ((verified.customer_id, verified.carrier_id, verified.currency)
                    != (authority.customer_id, authority.carrier_id, authority.currency)):
                raise ValueError("authority identity mismatch: customer/carrier/currency must match finding")
        finding_index[verified.finding_id] = verified

    authorities = tuple(sorted(authority_index.values(), key=lambda item: item.authority_id))
    findings = tuple(sorted(finding_index.values(), key=lambda item: item.finding_id))
    body = {
        "schema": 3, "buyer_id": truth.buyer_id, "business_unit": truth.business_unit,
        "population_hash": truth.population_hash,
        "authorities": [asdict(item) for item in authorities],
        "findings": [asdict(item) for item in findings],
    }
    _require_ledger_digest("truth manifest", truth.truth_hash, canonical_hash(body))
    return TruthManifest(truth.buyer_id, truth.business_unit, truth.population_hash,
                         authorities, findings, truth.truth_hash)


def _verified_ledger_incumbent(truth: TruthManifest, incumbent: IncumbentOutput) -> IncumbentOutput:
    """Recheck exclusion metadata, including its nested submission digest."""
    if type(incumbent) is not IncumbentOutput:
        raise ValueError("incumbent must be an IncumbentOutput")
    _require_scope(incumbent.buyer_id, incumbent.business_unit,
                   truth.buyer_id, truth.business_unit, "incumbent output")
    if incumbent.truth_hash != truth.truth_hash:
        raise ValueError("incumbent output is not bound to this truth manifest")
    if incumbent.population_hash != truth.population_hash:
        raise ValueError("incumbent output is not bound to this population")
    _require_text("source_hash", incumbent.source_hash)
    if type(incumbent.finding_ids) not in (tuple, list):
        raise ValueError("incumbent finding_ids must be a sequence")
    truth_finding_ids = {finding.finding_id for finding in truth.findings}
    for finding_id in incumbent.finding_ids:
        _require_canonical_identity("finding_id", finding_id)
        if finding_id not in truth_finding_ids:
            raise ValueError("incumbent finding_id is not in frozen truth")
    finding_ids = tuple(sorted(incumbent.finding_ids))
    if len(finding_ids) != len(set(finding_ids)):
        raise ValueError("duplicate incumbent finding_id")
    submission_body = {
        "schema": 1, "buyer_id": incumbent.buyer_id,
        "business_unit": incumbent.business_unit,
        "population_hash": incumbent.population_hash, "source_hash": incumbent.source_hash,
    }
    _require_ledger_digest("incumbent submission", incumbent.submission_hash,
                           canonical_hash(submission_body))
    body = {
        "schema": 2, "buyer_id": incumbent.buyer_id,
        "business_unit": incumbent.business_unit,
        "population_hash": incumbent.population_hash, "truth_hash": incumbent.truth_hash,
        "submission_hash": incumbent.submission_hash, "source_hash": incumbent.source_hash,
        "finding_ids": finding_ids,
    }
    _require_ledger_digest("incumbent output", incumbent.output_hash, canonical_hash(body))
    return IncumbentOutput(incumbent.buyer_id, incumbent.business_unit,
                           incumbent.population_hash, incumbent.truth_hash,
                           incumbent.submission_hash, incumbent.source_hash,
                           finding_ids, incumbent.output_hash)


class RecoveryLedger:
    """In-memory reference accounting; metadata checks do not authorize live cash."""

    def __init__(self, truth: TruthManifest, incumbent: IncumbentOutput | None = None):
        truth = _verified_ledger_truth(truth)
        if incumbent is not None:
            incumbent = _verified_ledger_incumbent(truth, incumbent)
        self.buyer_id = truth.buyer_id
        self.business_unit = truth.business_unit
        self._findings = {finding.finding_id: finding for finding in truth.findings}
        self._incumbent_finding_ids = (
            frozenset(incumbent.finding_ids) if incumbent is not None else frozenset()
        )
        self._allocations: dict[str, list[SettlementAllocation]] = {
            finding_id: [] for finding_id in self._findings
        }
        self._seen_settlement_ids: set[str] = set()
        self._seen_source_hashes: set[str] = set()

    def apply(self, event: SettlementEvent) -> SettlementAllocation:
        if type(event) is not SettlementEvent:
            raise ValueError("event must be a SettlementEvent")
        _require_text("finding_id", event.finding_id)
        _require_text("currency", event.currency)
        _require_scope(
            event.buyer_id,
            event.business_unit,
            self.buyer_id,
            self.business_unit,
            "settlement",
        )
        finding = self._findings.get(event.finding_id)
        if finding is None:
            raise ValueError("settlement references unknown finding")
        _require_canonical_identity("settlement_id", event.settlement_id)
        _require_canonical_identity("source_hash", event.source_hash)

        # Validate all accounting flags before even an ambiguous/zero path.
        # Invalid inputs must not consume settlement IDs, sources or capacity.
        if type(event.amount_cents) is not int or event.amount_cents < 0:
            raise ValueError("settlement amount must be non-negative integer cents")
        for name in ("incumbent_preidentified", "automatic_credit",
                     "preexisting_credit", "ambiguous_allocation"):
            if type(getattr(event, name)) is not bool:
                raise ValueError(name + " must be a boolean")
        if event.currency != finding.currency:
            raise ValueError("settlement currency mismatch")

        if event.settlement_id in self._seen_settlement_ids:
            raise ValueError("duplicate settlement_id")
        if event.source_hash in self._seen_source_hashes:
            raise ValueError("settlement source already consumed")

        if event.ambiguous_allocation:
            allocation = SettlementAllocation(
                buyer_id=self.buyer_id,
                business_unit=self.business_unit,
                settlement_id=event.settlement_id,
                finding_id=event.finding_id,
                allocated_cents=0,
                fee_eligible_cents=0,
                proof_hash=canonical_hash(
                    {
                        "schema": 2,
                        "buyer_id": self.buyer_id,
                        "business_unit": self.business_unit,
                        "finding_proof_hash": finding.proof_hash,
                        "settlement_id": event.settlement_id,
                        "source_hash": event.source_hash,
                        "ambiguous_allocation": True,
                    }
                ),
            )
            self._allocations[event.finding_id].append(allocation)
            self._seen_settlement_ids.add(event.settlement_id)
            self._seen_source_hashes.add(event.source_hash)
            return allocation

        realized_so_far = sum(
            allocation.allocated_cents for allocation in self._allocations[event.finding_id]
        )
        remaining = max(finding.validated_cents - realized_so_far, 0)
        allocated = min(event.amount_cents, remaining)

        disqualified = (
            finding.finding_id in self._incumbent_finding_ids
            or event.incumbent_preidentified
            or event.automatic_credit
            or event.preexisting_credit
        )
        fee_eligible = 0 if disqualified else allocated

        body = {
            "schema": 2,
            "buyer_id": self.buyer_id,
            "business_unit": self.business_unit,
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
            buyer_id=self.buyer_id,
            business_unit=self.business_unit,
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
            "schema": 2,
            "buyer_id": self.buyer_id,
            "business_unit": self.business_unit,
            "finding_id": finding.finding_id,
            "finding_proof_hash": finding.proof_hash,
            "validated_cents": finding.validated_cents,
            "realized_cents": realized,
            "fee_eligible_cents": fee_eligible,
            "settlement_proof_hashes": settlement_proofs,
        }
        return RecoveryCertificate(
            buyer_id=self.buyer_id,
            business_unit=self.business_unit,
            finding_id=finding.finding_id,
            finding_proof_hash=finding.proof_hash,
            validated_cents=finding.validated_cents,
            realized_cents=realized,
            fee_eligible_cents=fee_eligible,
            settlement_proof_hashes=settlement_proofs,
            certificate_hash=canonical_hash(body),
        )
