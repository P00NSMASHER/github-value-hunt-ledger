"""Deterministic charge-to-finding engine for Freight Recovery.

This module is intentionally narrow. It consumes already-normalized invoice
charges and already-normalized authority rules. It does not OCR documents,
interpret natural-language contracts, or choose controlling authority. Those
upstream steps remain evidence-producing review tasks.

Supported pricing models:
- INCLUDED: expected charge is zero.
- FIXED: expected charge is one exact fixed-cent amount.
- PER_UNIT: expected charge is integer units multiplied by an exact cent rate.

A rule can calculate a REVIEW discrepancy before it is confirmed as controlling
authority, but only a verified controlling rule can produce VALIDATED dollars.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Iterable

from freight.contracts import (
    AuthorityRef,
    Finding,
    PopulationManifest,
    REVIEW,
    VALIDATED,
    TruthManifest,
    canonical_hash,
    freeze_truth,
    make_finding,
)

INCLUDED = "INCLUDED"
FIXED = "FIXED"
PER_UNIT = "PER_UNIT"
CLEAR = "CLEAR"
MAX_CENTS = 2**63 - 1


@dataclass(frozen=True)
class InvoiceCharge:
    buyer_id: str
    business_unit: str
    invoice_id: str
    shipment_id: str
    customer_id: str
    carrier_id: str
    currency: str
    charge_id: str
    charge_code: str
    service_date: str
    quantity_units: int
    billed_cents: int
    source_hash: str


@dataclass(frozen=True)
class ChargeRule:
    buyer_id: str
    business_unit: str
    customer_id: str
    carrier_id: str
    currency: str
    authority_document_id: str
    charge_code: str
    pricing_model: str
    effective_from: str
    effective_to: str | None
    document_source_hash: str
    verified_controlling_authority: bool
    fixed_cents: int | None = None
    unit_rate_cents: int | None = None

    @property
    def rule_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})

    @property
    def authority_ref(self) -> AuthorityRef:
        digest = self.rule_hash
        return AuthorityRef(
            authority_id="rule:" + digest,
            buyer_id=self.buyer_id,
            business_unit=self.business_unit,
            customer_id=self.customer_id,
            carrier_id=self.carrier_id,
            currency=self.currency,
            source_hash=digest,
        )


@dataclass(frozen=True)
class ChargeDerivation:
    charge_id: str
    decision: str
    reason: str
    billed_cents: int
    expected_cents: int | None
    variance_cents: int | None
    charge_hash: str
    matched_rule_hashes: tuple[str, ...]
    authority_ref: AuthorityRef | None
    finding: Finding | None
    derivation_hash: str


@dataclass(frozen=True)
class FindingFactoryBatch:
    truth: TruthManifest
    derivations: tuple[ChargeDerivation, ...]
    factory_hash: str

    @property
    def review_count(self) -> int:
        return sum(item.decision == REVIEW for item in self.derivations)

    @property
    def validated_count(self) -> int:
        return sum(item.decision == VALIDATED for item in self.derivations)

    @property
    def clear_count(self) -> int:
        return sum(item.decision == CLEAR for item in self.derivations)


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " is required")
    return value.strip()


def _cents(name: str, value: int, *, positive: bool = False) -> int:
    lower = 1 if positive else 0
    if type(value) is not int or not lower <= value <= MAX_CENTS:
        qualifier = "positive " if positive else "non-negative "
        raise ValueError(name + " must be " + qualifier + "integer cents")
    return value


def _iso_date(name: str, value: str) -> date:
    text = _text(name, value)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(name + " must be YYYY-MM-DD") from exc


def _validate_charge(charge: InvoiceCharge) -> date:
    for name in (
        "buyer_id", "business_unit", "invoice_id", "shipment_id", "customer_id",
        "carrier_id", "currency", "charge_id", "charge_code", "source_hash",
    ):
        _text(name, getattr(charge, name))
    if type(charge.quantity_units) is not int or charge.quantity_units <= 0:
        raise ValueError("quantity_units must be a positive integer")
    _cents("billed_cents", charge.billed_cents)
    return _iso_date("service_date", charge.service_date)


def _validate_rule(rule: ChargeRule) -> tuple[date, date | None]:
    for name in (
        "buyer_id", "business_unit", "customer_id", "carrier_id", "currency",
        "authority_document_id", "charge_code", "document_source_hash",
    ):
        _text(name, getattr(rule, name))
    if type(rule.verified_controlling_authority) is not bool:
        raise ValueError("verified_controlling_authority must be a boolean")
    start = _iso_date("effective_from", rule.effective_from)
    end = _iso_date("effective_to", rule.effective_to) if rule.effective_to is not None else None
    if end is not None and end < start:
        raise ValueError("effective_to cannot precede effective_from")
    if rule.pricing_model == INCLUDED:
        if rule.fixed_cents is not None or rule.unit_rate_cents is not None:
            raise ValueError("INCLUDED rule cannot carry fixed/unit pricing")
    elif rule.pricing_model == FIXED:
        if rule.fixed_cents is None or rule.unit_rate_cents is not None:
            raise ValueError("FIXED rule requires fixed_cents only")
        _cents("fixed_cents", rule.fixed_cents)
    elif rule.pricing_model == PER_UNIT:
        if rule.unit_rate_cents is None or rule.fixed_cents is not None:
            raise ValueError("PER_UNIT rule requires unit_rate_cents only")
        _cents("unit_rate_cents", rule.unit_rate_cents)
    else:
        raise ValueError("unsupported pricing_model")
    return start, end


def _matches(charge: InvoiceCharge, service_day: date, rule: ChargeRule) -> bool:
    start, end = _validate_rule(rule)
    return (
        (rule.buyer_id, rule.business_unit) == (charge.buyer_id, charge.business_unit)
        and (rule.customer_id, rule.carrier_id, rule.currency)
            == (charge.customer_id, charge.carrier_id, charge.currency)
        and rule.charge_code == charge.charge_code
        and start <= service_day
        and (end is None or service_day <= end)
    )


def _expected_cents(charge: InvoiceCharge, rule: ChargeRule) -> int:
    if rule.pricing_model == INCLUDED:
        return 0
    if rule.pricing_model == FIXED:
        assert rule.fixed_cents is not None
        return rule.fixed_cents
    assert rule.pricing_model == PER_UNIT and rule.unit_rate_cents is not None
    value = charge.quantity_units * rule.unit_rate_cents
    if value > MAX_CENTS:
        raise ValueError("calculated expected charge exceeds integer-cent range")
    return value


def _finish(
    *,
    charge: InvoiceCharge,
    decision: str,
    reason: str,
    expected_cents: int | None,
    matched_rules: tuple[ChargeRule, ...],
    finding: Finding | None,
    authority_ref: AuthorityRef | None,
) -> ChargeDerivation:
    charge_hash = canonical_hash({"schema": 1, **asdict(charge)})
    rule_hashes = tuple(sorted(rule.rule_hash for rule in matched_rules))
    variance = None if expected_cents is None else max(charge.billed_cents - expected_cents, 0)
    body = {
        "schema": 1,
        "charge_id": charge.charge_id,
        "decision": decision,
        "reason": reason,
        "billed_cents": charge.billed_cents,
        "expected_cents": expected_cents,
        "variance_cents": variance,
        "charge_hash": charge_hash,
        "matched_rule_hashes": rule_hashes,
        "authority_id": authority_ref.authority_id if authority_ref else None,
        "finding_proof_hash": finding.proof_hash if finding else None,
    }
    return ChargeDerivation(
        charge_id=charge.charge_id,
        decision=decision,
        reason=reason,
        billed_cents=charge.billed_cents,
        expected_cents=expected_cents,
        variance_cents=variance,
        charge_hash=charge_hash,
        matched_rule_hashes=rule_hashes,
        authority_ref=authority_ref,
        finding=finding,
        derivation_hash=canonical_hash(body),
    )


def derive_charge(charge: InvoiceCharge, rules: Iterable[ChargeRule]) -> ChargeDerivation:
    service_day = _validate_charge(charge)
    candidates = tuple(
        sorted(
            (rule for rule in rules if _matches(charge, service_day, rule)),
            key=lambda rule: rule.rule_hash,
        )
    )
    if not candidates:
        return _finish(
            charge=charge, decision=REVIEW, reason="NO_APPLICABLE_RULE",
            expected_cents=None, matched_rules=(), finding=None, authority_ref=None,
        )
    if len(candidates) != 1:
        return _finish(
            charge=charge, decision=REVIEW, reason="AMBIGUOUS_APPLICABLE_RULE",
            expected_cents=None, matched_rules=candidates, finding=None, authority_ref=None,
        )

    rule = candidates[0]
    expected = _expected_cents(charge, rule)
    input_hash = canonical_hash({
        "schema": 1,
        "charge": asdict(charge),
        "rule_hash": rule.rule_hash,
        "expected_cents": expected,
    })
    finding_id = "ff:" + input_hash
    variance = max(charge.billed_cents - expected, 0)

    if not rule.verified_controlling_authority:
        finding = None
        if variance:
            finding = make_finding(
                finding_id=finding_id,
                buyer_id=charge.buyer_id,
                business_unit=charge.business_unit,
                invoice_id=charge.invoice_id,
                shipment_id=charge.shipment_id,
                customer_id=charge.customer_id,
                carrier_id=charge.carrier_id,
                currency=charge.currency,
                authority_id=None,
                expected_cents=expected,
                actual_cents=charge.billed_cents,
                status=REVIEW,
            )
        return _finish(
            charge=charge, decision=REVIEW, reason="AUTHORITY_NOT_VERIFIED",
            expected_cents=expected, matched_rules=(rule,), finding=finding, authority_ref=None,
        )

    authority_ref = rule.authority_ref
    if not variance:
        return _finish(
            charge=charge, decision=CLEAR, reason="BILLED_WITHIN_VERIFIED_RULE",
            expected_cents=expected, matched_rules=(rule,), finding=None,
            authority_ref=authority_ref,
        )

    finding = make_finding(
        finding_id=finding_id,
        buyer_id=charge.buyer_id,
        business_unit=charge.business_unit,
        invoice_id=charge.invoice_id,
        shipment_id=charge.shipment_id,
        customer_id=charge.customer_id,
        carrier_id=charge.carrier_id,
        currency=charge.currency,
        authority_id=authority_ref.authority_id,
        expected_cents=expected,
        actual_cents=charge.billed_cents,
        status=VALIDATED,
    )
    return _finish(
        charge=charge, decision=VALIDATED, reason="VERIFIED_RULE_OVERCHARGE",
        expected_cents=expected, matched_rules=(rule,), finding=finding,
        authority_ref=authority_ref,
    )


def derive_batch(
    population: PopulationManifest,
    charges: Iterable[InvoiceCharge],
    rules: Iterable[ChargeRule],
) -> FindingFactoryBatch:
    normalized_charges = tuple(sorted(charges, key=lambda charge: charge.charge_id))
    if len({charge.charge_id for charge in normalized_charges}) != len(normalized_charges):
        raise ValueError("duplicate charge_id")
    if len({charge.source_hash for charge in normalized_charges}) != len(normalized_charges):
        raise ValueError("duplicate charge source evidence")
    normalized_rules = tuple(rules)
    row_index = {row.row_key: row for row in population.rows}
    covered_rows: set[tuple[str, str]] = set()

    fixed_scope_groups: dict[tuple[str, str, str], list[InvoiceCharge]] = {}
    semantic_groups: dict[tuple[object, ...], list[InvoiceCharge]] = {}
    for charge in normalized_charges:
        fixed_scope_groups.setdefault(
            (charge.invoice_id, charge.shipment_id, charge.charge_code), []
        ).append(charge)
        semantic_groups.setdefault(
            (
                charge.invoice_id,
                charge.shipment_id,
                charge.customer_id,
                charge.carrier_id,
                charge.currency,
                charge.charge_code,
                charge.service_date,
                charge.quantity_units,
                charge.billed_cents,
            ),
            [],
        ).append(charge)

    derivations = []
    for charge in normalized_charges:
        _validate_charge(charge)
        if (charge.buyer_id, charge.business_unit) != (population.buyer_id, population.business_unit):
            raise ValueError("charge scope mismatch")
        row = row_index.get((charge.invoice_id, charge.shipment_id))
        if row is None:
            raise ValueError("charge outside frozen population")
        if (charge.customer_id, charge.carrier_id, charge.currency) != (
            row.customer_id, row.carrier_id, row.currency,
        ):
            raise ValueError("charge identity mismatch with frozen population")
        covered_rows.add((charge.invoice_id, charge.shipment_id))
        semantic_group = semantic_groups[
            (
                charge.invoice_id,
                charge.shipment_id,
                charge.customer_id,
                charge.carrier_id,
                charge.currency,
                charge.charge_code,
                charge.service_date,
                charge.quantity_units,
                charge.billed_cents,
            )
        ]
        if len(semantic_group) > 1:
            service_day = _validate_charge(charge)
            candidates = tuple(
                sorted(
                    (
                        rule for rule in normalized_rules
                        if _matches(charge, service_day, rule)
                    ),
                    key=lambda rule: rule.rule_hash,
                )
            )
            derivations.append(_finish(
                charge=charge,
                decision=REVIEW,
                reason="POSSIBLE_DUPLICATE_CHARGE_EVIDENCE",
                expected_cents=None,
                matched_rules=candidates,
                finding=None,
                authority_ref=None,
            ))
            continue
        multi_line = fixed_scope_groups[
            (charge.invoice_id, charge.shipment_id, charge.charge_code)
        ]
        if len(multi_line) > 1:
            service_day = _validate_charge(charge)
            candidates = tuple(
                sorted(
                    (
                        rule for rule in normalized_rules
                        if _matches(charge, service_day, rule)
                    ),
                    key=lambda rule: rule.rule_hash,
                )
            )
            if len(candidates) == 1 and candidates[0].pricing_model == FIXED:
                derivations.append(_finish(
                    charge=charge,
                    decision=REVIEW,
                    reason="FIXED_SCOPE_AMBIGUOUS_MULTI_LINE",
                    expected_cents=None,
                    matched_rules=candidates,
                    finding=None,
                    authority_ref=None,
                ))
                continue
        derivations.append(derive_charge(charge, normalized_rules))

    missing_rows = set(row_index) - covered_rows
    if missing_rows:
        raise ValueError(
            "audit charge set does not cover every frozen population row: "
            + ",".join(repr(key) for key in sorted(missing_rows))
        )

    derivations = tuple(derivations)
    findings = tuple(item.finding for item in derivations if item.finding is not None)
    authority_map = {
        item.authority_ref.authority_id: item.authority_ref
        for item in derivations
        if item.finding is not None
        and item.finding.status == VALIDATED
        and item.authority_ref is not None
    }
    truth = freeze_truth(population, authority_map.values(), findings)
    body = {
        "schema": 1,
        "population_hash": population.manifest_hash,
        "derivation_hashes": [item.derivation_hash for item in derivations],
        "truth_hash": truth.truth_hash,
    }
    return FindingFactoryBatch(
        truth=truth,
        derivations=derivations,
        factory_hash=canonical_hash(body),
    )
