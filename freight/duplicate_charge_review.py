"""Fail-closed review candidates for repeated freight charges.

The detector deliberately emits REVIEW evidence, not Findings. Matching charge
lines can be legitimate rebills, corrections, split services, or credits. A
candidate therefore has zero validated dollars until invoice lineage, payment
status, credit/rebill status, and service distinction are independently proven.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Iterable

from freight.contracts import PopulationManifest, canonical_hash
from freight.finding_factory import InvoiceCharge


REVIEW = "REVIEW"
POSSIBLE_DUPLICATE_LINE_ITEM = "POSSIBLE_DUPLICATE_LINE_ITEM"
POSSIBLE_ECONOMIC_DUPLICATE = "POSSIBLE_ECONOMIC_DUPLICATE"
MAX_CENTS = 2**63 - 1
UNRESOLVED_EVIDENCE = (
    "CREDIT_REBILL_STATUS",
    "INVOICE_LINEAGE",
    "PAYMENT_STATUS",
    "SERVICE_DISTINCTION",
)


@dataclass(frozen=True)
class DuplicateChargeCandidate:
    candidate_id: str
    buyer_id: str
    business_unit: str
    shipment_id: str
    customer_id: str
    carrier_id: str
    currency: str
    charge_code: str
    service_date: str
    quantity_units: int
    billed_cents: int
    invoice_ids: tuple[str, ...]
    charge_ids: tuple[str, ...]
    source_hashes: tuple[str, ...]
    charge_hashes: tuple[str, ...]
    decision: str
    reason: str
    candidate_excess_cents: int
    requires_human_review: bool
    may_assert_validated_dollars: bool
    unresolved_evidence: tuple[str, ...]
    proof_hash: str

    @property
    def validated_cents(self) -> int:
        return 0


@dataclass(frozen=True)
class DuplicateChargeReviewBatch:
    population_hash: str
    candidates: tuple[DuplicateChargeCandidate, ...]
    batch_hash: str

    @property
    def review_count(self) -> int:
        return len(self.candidates)

    @property
    def candidate_excess_cents(self) -> int:
        return sum(candidate.candidate_excess_cents for candidate in self.candidates)

    @property
    def validated_cents(self) -> int:
        return 0


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " is required")
    return value.strip()


def _validate_charge(charge: InvoiceCharge) -> None:
    for name in (
        "buyer_id", "business_unit", "invoice_id", "shipment_id", "customer_id",
        "carrier_id", "currency", "charge_id", "charge_code", "source_hash",
    ):
        _text(name, getattr(charge, name))
    if type(charge.quantity_units) is not int or charge.quantity_units <= 0:
        raise ValueError("quantity_units must be a positive integer")
    if type(charge.billed_cents) is not int or not 0 <= charge.billed_cents <= MAX_CENTS:
        raise ValueError("billed_cents must be non-negative integer cents")
    try:
        date.fromisoformat(_text("service_date", charge.service_date))
    except ValueError as exc:
        raise ValueError("service_date must be YYYY-MM-DD") from exc


def _economic_key(charge: InvoiceCharge) -> tuple[object, ...]:
    return (
        charge.buyer_id,
        charge.business_unit,
        charge.shipment_id,
        charge.customer_id,
        charge.carrier_id,
        charge.currency,
        charge.charge_code,
        charge.service_date,
        charge.quantity_units,
        charge.billed_cents,
    )


def _candidate(
    population: PopulationManifest,
    group: tuple[InvoiceCharge, ...],
) -> DuplicateChargeCandidate:
    exemplar = group[0]
    invoice_ids = tuple(sorted({charge.invoice_id for charge in group}))
    charge_ids = tuple(charge.charge_id for charge in group)
    source_hashes = tuple(charge.source_hash for charge in group)
    charge_hashes = tuple(
        canonical_hash({"schema": 1, **asdict(charge)}) for charge in group
    )
    excess = exemplar.billed_cents * (len(group) - 1)
    if excess > MAX_CENTS:
        raise ValueError("candidate duplicate exposure exceeds integer-cent range")
    reason = (
        POSSIBLE_DUPLICATE_LINE_ITEM
        if len(invoice_ids) == 1
        else POSSIBLE_ECONOMIC_DUPLICATE
    )
    body = {
        "schema": 1,
        "population_hash": population.manifest_hash,
        "buyer_id": exemplar.buyer_id,
        "business_unit": exemplar.business_unit,
        "shipment_id": exemplar.shipment_id,
        "customer_id": exemplar.customer_id,
        "carrier_id": exemplar.carrier_id,
        "currency": exemplar.currency,
        "charge_code": exemplar.charge_code,
        "service_date": exemplar.service_date,
        "quantity_units": exemplar.quantity_units,
        "billed_cents": exemplar.billed_cents,
        "invoice_ids": invoice_ids,
        "charge_ids": charge_ids,
        "source_hashes": source_hashes,
        "charge_hashes": charge_hashes,
        "decision": REVIEW,
        "reason": reason,
        "candidate_excess_cents": excess,
        "requires_human_review": True,
        "may_assert_validated_dollars": False,
        "unresolved_evidence": UNRESOLVED_EVIDENCE,
    }
    proof_hash = canonical_hash(body)
    return DuplicateChargeCandidate(
        candidate_id="dup:" + proof_hash,
        proof_hash=proof_hash,
        **{key: value for key, value in body.items() if key not in {"schema", "population_hash"}},
    )


def review_duplicate_charges(
    population: PopulationManifest,
    charges: Iterable[InvoiceCharge],
) -> DuplicateChargeReviewBatch:
    """Return strict semantic duplicates as evidence-bound REVIEW candidates."""
    normalized = tuple(sorted(charges, key=lambda charge: charge.charge_id))
    if len({charge.charge_id for charge in normalized}) != len(normalized):
        raise ValueError("duplicate charge_id")

    row_index = {row.row_key: row for row in population.rows}
    groups: dict[tuple[object, ...], list[InvoiceCharge]] = {}
    for charge in normalized:
        _validate_charge(charge)
        if (charge.buyer_id, charge.business_unit) != (
            population.buyer_id,
            population.business_unit,
        ):
            raise ValueError("charge scope mismatch")
        row = row_index.get(f"{charge.invoice_id}|{charge.shipment_id}")
        if row is None:
            raise ValueError("charge outside frozen population")
        if (charge.customer_id, charge.carrier_id, charge.currency) != (
            row.customer_id,
            row.carrier_id,
            row.currency,
        ):
            raise ValueError("charge identity mismatch with frozen population")
        groups.setdefault(_economic_key(charge), []).append(charge)

    candidates = tuple(
        _candidate(population, tuple(group))
        for _, group in sorted(groups.items(), key=lambda item: item[0])
        if len(group) > 1
    )
    body = {
        "schema": 1,
        "population_hash": population.manifest_hash,
        "input_charge_hashes": [
            canonical_hash({"schema": 1, **asdict(charge)}) for charge in normalized
        ],
        "candidate_proof_hashes": [candidate.proof_hash for candidate in candidates],
    }
    return DuplicateChargeReviewBatch(
        population_hash=population.manifest_hash,
        candidates=candidates,
        batch_hash=canonical_hash(body),
    )
