from dataclasses import replace

import pytest

from freight.recovery_engagement import (
    RecoveryEngagementRequest,
    build_recovery_engagement,
    record_actual_recovery,
    render_engagement_summary,
)


def request(**overrides):
    values = {
        "engagement_id": "REC-001",
        "audit_reference": "AUDIT-001",
        "buyer_id": "BUYER-001",
        "business_unit": "US-FREIGHT",
        "scope": "Supported parcel and LTL opportunities in the agreed audit population.",
        "potential_recovery_low_cents": 1_000_000,
        "potential_recovery_high_cents": 2_000_000,
        "recovered_funds_definition": "Eligible cash refunds or posted credits received and verified by the buyer, net of reversals and exclusions.",
        "payment_timing": "Invoice after settlement evidence is reconciled under the governing agreement.",
        "confidentiality_terms_reference": "TERMS:CONFIDENTIALITY:V1",
        "data_use_terms_reference": "TERMS:DATA-USE:V1",
        "termination_terms_reference": "TERMS:TERMINATION:V1",
        "attribution_terms_reference": "TERMS:ATTRIBUTION:V1",
        "governing_agreement_reference": "AGREEMENT:REC-001:V1",
    }
    values.update(overrides)
    return RecoveryEngagementRequest(**values)


def accepted(**overrides):
    return build_recovery_engagement(
        request(
            buyer_accepted=True,
            freight_recovery_accepted=True,
            accepted_at="2026-09-23T15:00:00-04:00",
            **overrides,
        )
    )


def test_default_rate_is_configurable_and_not_applied_to_potential_value():
    engagement = build_recovery_engagement(request())
    assert engagement.state == "READY_FOR_ACCEPTANCE"
    assert engagement.contingency_rate == "0.3"
    assert engagement.contingency_rate_label == "30%"
    assert engagement.approved_claim_value_cents == 0
    assert engagement.actual_recovered_cents == 0
    assert engagement.external_action_authorized is False

    custom = build_recovery_engagement(request(contingency_rate="0.325"))
    assert custom.contingency_rate_label == "32.5%"


def test_acceptance_requires_both_parties_and_timestamp():
    with pytest.raises(ValueError, match="accepted_at"):
        build_recovery_engagement(
            request(buyer_accepted=True, freight_recovery_accepted=True)
        )
    with pytest.raises(ValueError, match="before both parties"):
        build_recovery_engagement(request(accepted_at="2026-09-23T19:00:00Z"))

    engagement = accepted()
    assert engagement.state == "ACCEPTED"
    assert engagement.accepted_at == "2026-09-23T19:00:00Z"
    assert engagement.external_action_authorized is False


def test_fee_is_based_only_on_fee_eligible_actual_recovery():
    record = record_actual_recovery(
        accepted(),
        settlement_evidence_reference="SETTLEMENT:CREDIT-001",
        actual_recovered_cents=1_000_000,
        fee_eligible_recovered_cents=800_000,
        recorded_at="2026-09-24T10:30:00-04:00",
    )
    assert record.engagement_hash == accepted().engagement_hash
    assert record.actual_recovered_cents == 1_000_000
    assert record.fee_eligible_recovered_cents == 800_000
    assert record.recovery_fee_cents == 240_000
    assert record.customer_net_recovery_cents == 760_000
    assert record.recorded_at == "2026-09-24T14:30:00Z"


def test_zero_recovery_means_zero_fee():
    record = record_actual_recovery(
        accepted(),
        settlement_evidence_reference="SETTLEMENT:NONE-001",
        actual_recovered_cents=0,
        recorded_at="2026-09-24T14:30:00Z",
    )
    assert record.recovery_fee_cents == 0
    assert record.customer_net_recovery_cents == 0


def test_fee_cannot_be_recorded_before_acceptance_or_above_actual_cash():
    with pytest.raises(ValueError, match="accepted engagement"):
        record_actual_recovery(
            build_recovery_engagement(request()),
            settlement_evidence_reference="SETTLEMENT:CREDIT-001",
            actual_recovered_cents=100,
            recorded_at="2026-09-24T14:30:00Z",
        )
    with pytest.raises(ValueError, match="between zero and actual"):
        record_actual_recovery(
            accepted(),
            settlement_evidence_reference="SETTLEMENT:CREDIT-001",
            actual_recovered_cents=100,
            fee_eligible_recovered_cents=101,
            recorded_at="2026-09-24T14:30:00Z",
        )


def test_fee_record_rejects_an_engagement_changed_after_acceptance():
    engagement = accepted()
    altered = replace(engagement, contingency_rate="0.5")
    with pytest.raises(ValueError, match="engagement hash"):
        record_actual_recovery(
            altered,
            settlement_evidence_reference="SETTLEMENT:CREDIT-001",
            actual_recovered_cents=100,
            recorded_at="2026-09-24T14:30:00Z",
        )


def test_summary_preserves_amount_distinctions_and_legal_boundary():
    summary = render_engagement_summary(accepted())
    assert "fee-eligible actual recovered funds" in summary
    assert "not approved claim value or actual recovered cash" in summary
    assert "External action authorized by this record:** false" in summary
    assert "not an e-signature system" in summary


@pytest.mark.parametrize("field", [
    "confidentiality_terms_reference",
    "data_use_terms_reference",
    "termination_terms_reference",
    "attribution_terms_reference",
    "governing_agreement_reference",
])
def test_agreement_hooks_are_required(field):
    with pytest.raises(ValueError, match=field):
        build_recovery_engagement(request(**{field: ""}))


def test_potential_range_and_reference_validation_fail_closed():
    with pytest.raises(ValueError, match="high value"):
        build_recovery_engagement(
            request(
                potential_recovery_low_cents=200,
                potential_recovery_high_cents=100,
            )
        )
    with pytest.raises(ValueError, match="stable non-secret"):
        build_recovery_engagement(request(governing_agreement_reference="not allowed!"))
