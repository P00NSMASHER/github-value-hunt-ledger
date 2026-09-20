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
