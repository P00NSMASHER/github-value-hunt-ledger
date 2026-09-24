import pytest

from freight.lead_qualification import (
    AuditLeadProfile,
    QualificationState,
    qualify_free_audit,
)


def profile(**overrides):
    values = dict(
        annual_freight_spend_usd=2_000_000,
        monthly_shipments=400,
        invoice_count=1_000,
        history_months=12,
        carrier_count=3,
        mode_count=2,
        has_invoice_export=True,
        has_rate_authority=True,
        has_shipment_records=True,
        has_payment_evidence=True,
    )
    values.update(overrides)
    return AuditLeadProfile(**values)


def test_routes_ready_scaled_lead_without_exposing_a_score():
    decision = qualify_free_audit(profile())
    assert decision.state is QualificationState.QUALIFIED
    assert "records_ready" in decision.reasons


def test_prioritizes_large_ready_candidate_with_suspected_issue():
    decision = qualify_free_audit(profile(
        annual_freight_spend_usd=8_000_000,
        known_or_suspected_issue=True,
    ))
    assert decision.state is QualificationState.HIGH_PRIORITY_RECOVERY_CANDIDATE


def test_fails_closed_when_minimum_population_is_missing():
    decision = qualify_free_audit(profile(invoice_count=0))
    assert decision.state is QualificationState.INSUFFICIENT_DATA


def test_small_population_without_issue_uses_low_effort_queue():
    decision = qualify_free_audit(profile(
        annual_freight_spend_usd=100_000,
        monthly_shipments=20,
        invoice_count=40,
        known_or_suspected_issue=False,
    ))
    assert decision.state is QualificationState.LOW_EXPECTED_RECOVERY


def test_uncertain_authority_requires_review():
    decision = qualify_free_audit(profile(has_rate_authority=False))
    assert decision.state is QualificationState.NEEDS_REVIEW
    assert "rate_authority_needs_review" in decision.reasons


def test_profile_rejects_invalid_numbers():
    with pytest.raises(ValueError):
        profile(invoice_count=-1)
