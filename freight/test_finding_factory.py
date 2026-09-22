from dataclasses import replace

import pytest

from freight.contracts import PopulationRow, REVIEW, VALIDATED, freeze_population
from freight.finding_factory import (
    CLEAR, FIXED, INCLUDED, PER_UNIT,
    ChargeRule, InvoiceCharge, derive_batch, derive_charge,
)


def population():
    return freeze_population(
        "buyer", "unit", "synthetic",
        [PopulationRow("inv-1", "shp-1", "customer", "carrier", "USD", "invoice-source")],
    )


def charge(**overrides):
    values = dict(
        buyer_id="buyer", business_unit="unit", invoice_id="inv-1", shipment_id="shp-1",
        customer_id="customer", carrier_id="carrier", currency="USD",
        charge_id="charge-1", charge_code="DETENTION", service_date="2026-09-10",
        quantity_units=1, billed_cents=12500, source_hash="line-source",
    )
    values.update(overrides)
    return InvoiceCharge(**values)


def rule(**overrides):
    values = dict(
        buyer_id="buyer", business_unit="unit", customer_id="customer", carrier_id="carrier",
        currency="USD", authority_document_id="rate-confirmation-1", charge_code="DETENTION",
        pricing_model=FIXED, effective_from="2026-09-01", effective_to="2026-09-30",
        document_source_hash="rate-source", verified_controlling_authority=True,
        fixed_cents=10000, unit_rate_cents=None,
    )
    values.update(overrides)
    return ChargeRule(**values)


def test_verified_fixed_rule_creates_content_addressed_validated_finding():
    out = derive_charge(charge(), [rule()])
    assert out.decision == VALIDATED
    assert out.variance_cents == 2500
    assert out.finding is not None
    assert out.finding.validated_cents == 2500
    assert out.finding.finding_id.startswith("ff:")
    assert out.finding.authority_id == out.authority_ref.authority_id


def test_included_and_per_unit_rules_calculate_exact_integer_cents():
    included = derive_charge(
        charge(billed_cents=500, charge_code="FUEL"),
        [rule(charge_code="FUEL", pricing_model=INCLUDED, fixed_cents=None)],
    )
    assert included.expected_cents == 0 and included.variance_cents == 500

    per_unit = derive_charge(
        charge(quantity_units=3, billed_cents=1800),
        [rule(pricing_model=PER_UNIT, fixed_cents=None, unit_rate_cents=500)],
    )
    assert per_unit.expected_cents == 1500 and per_unit.variance_cents == 300


def test_unverified_rule_can_create_review_discrepancy_but_not_validated_dollars():
    out = derive_charge(charge(), [rule(verified_controlling_authority=False)])
    assert out.decision == REVIEW
    assert out.reason == "AUTHORITY_NOT_VERIFIED"
    assert out.finding is not None
    assert out.finding.status == REVIEW
    assert out.finding.validated_cents == 0
    assert out.finding.authority_id is None


def test_verified_rule_with_no_positive_variance_is_clear():
    out = derive_charge(charge(billed_cents=9500), [rule()])
    assert out.decision == CLEAR
    assert out.finding is None
    assert out.variance_cents == 0


def test_missing_or_ambiguous_rule_stays_review_without_inventing_expected_dollars():
    missing = derive_charge(charge(), [])
    assert missing.decision == REVIEW
    assert missing.expected_cents is None
    assert missing.finding is None

    ambiguous = derive_charge(charge(), [
        rule(authority_document_id="a"),
        rule(authority_document_id="b", document_source_hash="other"),
    ])
    assert ambiguous.decision == REVIEW
    assert ambiguous.reason == "AMBIGUOUS_APPLICABLE_RULE"
    assert ambiguous.expected_cents is None
    assert ambiguous.finding is None


def test_effective_dates_control_rule_applicability():
    out = derive_charge(charge(service_date="2026-10-01"), [rule()])
    assert out.reason == "NO_APPLICABLE_RULE"


def test_batch_binds_rule_proof_into_truth_and_allows_clean_truth():
    pop = population()
    flagged = derive_batch(pop, [charge()], [rule()])
    assert flagged.truth.findings[0].status == VALIDATED
    assert len(flagged.truth.authorities) == 1
    assert flagged.truth.authorities[0].source_hash == rule().rule_hash

    clean = derive_batch(pop, [charge(billed_cents=9000)], [rule()])
    assert clean.clear_count == 1
    assert clean.truth.findings == ()
    assert clean.truth.authorities == ()
    assert clean.truth.truth_hash


def test_authority_or_invoice_evidence_change_changes_factory_and_truth_proof():
    pop = population()
    a = derive_batch(pop, [charge()], [rule()])
    b = derive_batch(pop, [replace(charge(), source_hash="different-line-source")], [rule()])
    c = derive_batch(pop, [charge()], [replace(rule(), document_source_hash="different-rate-source")])
    assert a.factory_hash != b.factory_hash
    assert a.truth.truth_hash != b.truth.truth_hash
    assert a.factory_hash != c.factory_hash
    assert a.truth.truth_hash != c.truth.truth_hash


def test_batch_rejects_charge_outside_frozen_scope_or_identity():
    pop = population()
    with pytest.raises(ValueError, match="scope mismatch"):
        derive_batch(pop, [charge(buyer_id="other")], [rule()])
    with pytest.raises(ValueError, match="identity mismatch"):
        derive_batch(pop, [charge(carrier_id="other")], [rule(carrier_id="other")])


@pytest.mark.parametrize("bad", [True, 1.5, "100", -1])
def test_money_and_units_require_exact_integer_semantics(bad):
    if bad is True:
        with pytest.raises(ValueError, match="positive integer"):
            derive_charge(charge(quantity_units=bad), [rule()])
    else:
        with pytest.raises(ValueError):
            derive_charge(charge(billed_cents=bad), [rule()])


def test_delimiter_collision_cannot_make_different_charge_look_in_population():
    pop = freeze_population(
        "buyer",
        "unit",
        "synthetic",
        [
            PopulationRow(
                "INV|PART",
                "SHIP",
                "customer",
                "carrier",
                "USD",
                "frozen-source",
            )
        ],
    )
    impostor = charge(
        invoice_id="INV",
        shipment_id="PART|SHIP",
        charge_id="collision",
    )
    with pytest.raises(ValueError, match="outside frozen population"):
        derive_batch(pop, [impostor], [rule()])
