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


@pytest.mark.parametrize("values", [
    {"annual_freight_spend_usd": 2_000_000},
    {"annual_freight_spend_usd": 8_000_000, "known_or_suspected_issue": True},
    {"annual_freight_spend_usd": 100_000, "monthly_shipments": 20, "invoice_count": 40},
])
def test_prior_auditor_requires_human_overlap_review_at_any_scale(values):
    decision = qualify_free_audit(profile(previously_audited=True, **values))
    assert decision.state is QualificationState.NEEDS_REVIEW
    assert "prior_audit_overlap_check" in decision.reasons
    assert "prior audit" in decision.recommended_next_step


def test_prior_audit_with_missing_population_remains_insufficient_data():
    decision = qualify_free_audit(profile(previously_audited=True, invoice_count=0))
    assert decision.state is QualificationState.INSUFFICIENT_DATA


def test_prior_audit_flags_missing_authority_and_supporting_sources():
    decision = qualify_free_audit(profile(
        previously_audited=True,
        has_rate_authority=False,
        has_shipment_records=False,
        has_payment_evidence=False,
    ))
    assert decision.state is QualificationState.NEEDS_REVIEW
    assert set(decision.reasons) == {
        "prior_audit_overlap_check",
        "rate_authority_needs_review",
        "supporting_records_need_review",
    }


@pytest.mark.parametrize("field", [
    "has_invoice_export", "has_rate_authority", "has_shipment_records",
    "has_payment_evidence", "previously_audited", "known_or_suspected_issue",
])
@pytest.mark.parametrize("bad", ["false", "true", 0, 1, None])
def test_boolean_evidence_cannot_be_satisfied_by_truthy_strings_or_numbers(field, bad):
    with pytest.raises(ValueError, match="must be a boolean"):
        profile(**{field: bad})


def test_unreviewed_high_priority_candidate_still_routes_as_before():
    decision = qualify_free_audit(profile(
        annual_freight_spend_usd=8_000_000,
        known_or_suspected_issue=True,
        previously_audited=False,
    ))
    assert decision.state is QualificationState.HIGH_PRIORITY_RECOVERY_CANDIDATE
