import pytest

from freight.outcome_adapter import FreightOutcomeInput, build_outcome


def base(**overrides):
    data = dict(
        outcome_id="OUT:20260920:freight-test",
        date="2026-09-20",
        result="PARTIAL",
        evidence_location="freight/rehearsal-output.json",
        origin_search_ids=(),
        contributing_capability_ids=(),
        synthetic=True,
        external_value_evidence=False,
        external_commercial_evidence=False,
        technical_result="synthetic rehearsal passed",
    )
    data.update(overrides)
    return FreightOutcomeInput(**data)


def attribution():
    return dict(
        origin_search_ids=("RUN:20260920T155926Z:hunter03:settlement-persistence-race",),
        contributing_capability_ids=("CAP-006", "CAP-016"),
    )


def test_synthetic_rehearsal_can_be_recorded_only_without_commercial_value():
    out = build_outcome(base())
    assert out["experiment_id"] == "EXP-001"
    assert out["freight_metrics"]["synthetic"] is True
    assert out["revenue_usd"] is None


def test_synthetic_rehearsal_cannot_claim_revenue():
    with pytest.raises(ValueError, match="synthetic rehearsal"):
        build_outcome(base(revenue_usd=1000))


def test_synthetic_rehearsal_cannot_claim_external_evidence():
    with pytest.raises(ValueError, match="synthetic rehearsal"):
        build_outcome(base(external_commercial_evidence=True))


def test_customer_value_requires_direct_external_value_evidence():
    with pytest.raises(ValueError, match="external value evidence"):
        build_outcome(
            base(
                synthetic=False,
                external_commercial_evidence=True,
                engagement_id="pilot-1",
                buyer_cohort_key="buyer-a",
                customer_value_usd=2500,
                realized_recovery_usd=2500,
                **attribution(),
            )
        )


def test_value_only_outcome_requires_engagement_identity_and_can_omit_revenue_evidence():
    out = build_outcome(
        base(
            synthetic=False,
            external_value_evidence=True,
            engagement_id="recovery-1",
            buyer_cohort_key="buyer-a",
            customer_value_usd=2500,
            realized_recovery_usd=2500,
            **attribution(),
        )
    )
    assert out["customer_value_usd"] == 2500
    assert out["revenue_usd"] is None
    assert out["freight_metrics"]["buyer_cohort_key"] == "buyer-a"


def test_revenue_only_requires_external_commercial_not_customer_value_evidence():
    out = build_outcome(
        base(
            synthetic=False,
            external_commercial_evidence=True,
            engagement_id="diag-1",
            buyer_cohort_key="buyer-a",
            diagnostic_paid=True,
            revenue_usd=6250,
            fixed_fee_usd=6250,
            delivery_cost_usd=2500,
            **attribution(),
        )
    )
    assert out["revenue_usd"] == 6250
    assert out["customer_value_usd"] is None
    assert out["freight_metrics"]["gross_margin"] == 0.6


def test_paid_stage_without_engagement_identity_is_rejected():
    with pytest.raises(ValueError, match="engagement_id"):
        build_outcome(
            base(
                synthetic=False,
                external_commercial_evidence=True,
                pilot_paid=True,
                **attribution(),
            )
        )


def test_positive_real_value_requires_search_and_capability_attribution():
    with pytest.raises(ValueError, match="origin_search_ids"):
        build_outcome(
            base(
                synthetic=False,
                external_commercial_evidence=True,
                external_value_evidence=True,
                engagement_id="pilot-1",
                buyer_cohort_key="buyer-a",
                customer_value_usd=2500,
                realized_recovery_usd=2500,
            )
        )


def test_real_outcome_maps_to_global_schema_and_preserves_commercial_metrics():
    out = build_outcome(
        base(
            synthetic=False,
            external_commercial_evidence=True,
            external_value_evidence=True,
            engagement_id="pilot-1",
            buyer_cohort_key="buyer-a",
            **attribution(),
            revenue_usd=20000,
            customer_value_usd=2500,
            realized_recovery_usd=2500,
            pilot_paid=True,
            reviewer_hours=12.5,
            false_positive_usd=0,
            fixed_fee_usd=20000,
            delivery_cost_usd=8000,
            invoices_reviewed=250,
            days_to_final_report=8,
            commercial_result="paid pilot and settlement-proven recovery",
            evidence_location="customer/authorized/pilot-001",
        )
    )
    assert out["opportunity"] == "Freight Recovery"
    assert out["revenue_usd"] == 20000
    assert out["freight_metrics"]["pilot_paid"] is True
    assert out["freight_metrics"]["gross_margin"] == 0.6
    assert out["freight_metrics"]["invoices_reviewed"] == 250


@pytest.mark.parametrize("field", ["revenue_usd", "customer_value_usd", "fixed_fee_usd", "delivery_cost_usd", "reviewer_hours"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), True, "100"])
def test_nonfinite_or_nonnumeric_metrics_cannot_enter_the_learning_ledger(field, value):
    with pytest.raises(ValueError, match=field):
        build_outcome(base(**{field: value}))


@pytest.mark.parametrize("field", ["synthetic", "external_commercial_evidence", "external_value_evidence", "diagnostic_paid", "pilot_paid", "annual_converted"])
@pytest.mark.parametrize("value", ["false", "true", 0, 1])
def test_evidence_and_paid_stage_flags_require_actual_booleans(field, value):
    with pytest.raises(ValueError, match=field):
        build_outcome(base(**{field: value}))


@pytest.mark.parametrize("field", ["invoices_reviewed", "shipments_reviewed"])
def test_boolean_is_not_an_invoice_or_shipment_count(field):
    with pytest.raises(ValueError, match=field):
        build_outcome(base(**{field: True}))
