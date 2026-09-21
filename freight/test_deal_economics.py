import pytest

from freight.deal_economics import (
    DealProfile,
    DealRoute,
    qualify_deal,
)
from freight.readiness import PilotReadinessInput, assess_readiness


def readiness(**overrides):
    data = dict(
        authorization_documented=True,
        read_only_access=True,
        population_reproducible=True,
        incumbent_output_sealable=True,
        settlement_observable=True,
        material_authority_reconstructable=True,
        customer_identity_stable=True,
        carrier_identity_stable=True,
        retention_defined=True,
        deletion_defined=True,
        invoice_source_coverage=1.0,
        authority_source_coverage=1.0,
        shipment_evidence_coverage=1.0,
    )
    data.update(overrides)
    return assess_readiness(PilotReadinessInput(**data))


def profile(**overrides):
    data = dict(
        annual_transport_spend_usd=8_000_000,
        invoices_per_month=1200,
        carrier_count=8,
        diagnostic_fee_usd=6250,
        pilot_fee_usd=20000,
        diagnostic_analyst_hours=20,
        pilot_analyst_hours=60,
        loaded_hourly_cost_usd=100,
        diagnostic_other_cost_usd=500,
        pilot_other_cost_usd=2000,
        target_gross_margin=0.50,
    )
    data.update(overrides)
    return DealProfile(**data)


def test_ready_buyer_routes_to_profitable_pilot():
    d = qualify_deal(readiness(), profile())
    assert d.route is DealRoute.BLIND_FREIGHT_AUDIT_ACCEPTANCE_TEST
    assert d.economics.delivery_cost_usd == 8000
    assert d.economics.gross_margin == 0.60
    assert d.economics.max_analyst_hours_at_target_margin == 80


def test_conditional_buyer_routes_to_diagnostic():
    d = qualify_deal(
        readiness(authority_source_coverage=0.80),
        profile(),
    )
    assert d.route is DealRoute.DATA_READINESS_DIAGNOSTIC
    assert d.economics.gross_margin == 0.60


def test_pilot_is_held_if_fixed_fee_margin_fails():
    d = qualify_deal(readiness(), profile(pilot_analyst_hours=180))
    assert d.route is DealRoute.HOLD
    assert "fixed_fee_gross_margin_below_target" in d.reasons


def test_small_buyer_is_flagged_but_not_automatically_rejected_if_margin_works():
    d = qualify_deal(
        readiness(),
        profile(annual_transport_spend_usd=1_000_000, invoices_per_month=100),
    )
    assert d.route is DealRoute.BLIND_FREIGHT_AUDIT_ACCEPTANCE_TEST
    assert d.initial_icp_scale is False
    assert "below_initial_icp_scale" in d.reasons


def test_success_fee_is_not_an_input_to_qualification():
    fields = DealProfile.__dataclass_fields__
    assert "success_fee" not in fields
    assert "expected_recovery" not in fields


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), True, "100"])
@pytest.mark.parametrize("field", ["pilot_fee_usd", "pilot_analyst_hours", "loaded_hourly_cost_usd", "pilot_other_cost_usd"])
def test_invalid_financial_values_cannot_qualify_a_deal(field, value):
    with pytest.raises(ValueError, match=field):
        profile(**{field: value})


def test_display_rounding_cannot_promote_below_target_margin():
    decision = qualify_deal(readiness(), profile(pilot_analyst_hours=80.0001))
    assert decision.economics.gross_margin == 0.5
    assert decision.route is DealRoute.HOLD
    assert "fixed_fee_gross_margin_below_target" in decision.reasons


def test_exact_margin_boundary_remains_eligible():
    decision = qualify_deal(readiness(), profile(pilot_analyst_hours=80))
    assert decision.route is DealRoute.BLIND_FREIGHT_AUDIT_ACCEPTANCE_TEST


@pytest.mark.parametrize("field", ["invoices_per_month", "carrier_count"])
def test_customer_counts_must_be_integers(field):
    with pytest.raises(ValueError, match=field):
        profile(**{field: 2.5})


def test_founder_labor_cannot_be_assumed_free_for_qualification():
    with pytest.raises(ValueError, match="including founder labor"):
        profile(loaded_hourly_cost_usd=0)


def test_zero_hour_offer_has_no_infinite_hour_budget():
    decision = qualify_deal(readiness(), profile(
        loaded_hourly_cost_usd=0, diagnostic_analyst_hours=0, pilot_analyst_hours=0,
    ))
    assert decision.economics.max_analyst_hours_at_target_margin is None


def test_finite_inputs_cannot_create_infinite_derived_economics():
    with pytest.raises(ValueError, match="derived offer economics must be finite"):
        qualify_deal(readiness(), profile(pilot_analyst_hours=1e308, loaded_hourly_cost_usd=1e308))
