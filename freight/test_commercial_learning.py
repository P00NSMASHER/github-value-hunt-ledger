import pytest

from freight.commercial_learning import (
    CalibrationAction,
    CalibrationStatus,
    calibrate_commercial_outcomes,
)


def O(
    buyer,
    engagement,
    *,
    fee=20000,
    cost=8000,
    hours=20,
    invoices=200,
    diagnostic=False,
    pilot=True,
    annual=False,
    synthetic=False,
    external=True,
):
    return {
        "experiment_id": "EXP-001",
        "revenue_usd": fee if (diagnostic or pilot or annual) else None,
        "freight_metrics": {
            "synthetic": synthetic,
            "external_commercial_evidence": external,
            "engagement_id": engagement,
            "buyer_cohort_key": buyer,
            "fixed_fee_usd": fee,
            "delivery_cost_usd": cost,
            "reviewer_hours": hours,
            "invoices_reviewed": invoices,
            "diagnostic_paid": diagnostic,
            "pilot_paid": pilot,
            "annual_converted": annual,
        },
    }


def test_no_external_data_keeps_prior():
    c = calibrate_commercial_outcomes([])
    assert c.status is CalibrationStatus.NO_EXTERNAL_DATA
    assert c.recommended_action is CalibrationAction.KEEP_PRIOR


def test_synthetic_and_unverified_commercial_records_are_excluded():
    c = calibrate_commercial_outcomes([
        O("b1", "e1", synthetic=True),
        O("b2", "e2", external=False),
    ])
    assert c.status is CalibrationStatus.NO_EXTERNAL_DATA


def test_many_engagements_from_one_buyer_cannot_unlock_repricing():
    rows = [O("same-buyer", f"e{i}") for i in range(10)]
    c = calibrate_commercial_outcomes(rows)
    assert c.paid_engagements == 10
    assert c.unique_buyers == 1
    assert c.status is CalibrationStatus.OBSERVE_ONLY
    assert c.max_buyer_engagement_share == 1.0


def test_five_independent_low_margin_buyers_trigger_review_not_auto_change():
    rows = [
        O(f"b{i}", f"e{i}", cost=13000 + i * 200)
        for i in range(5)
    ]
    c = calibrate_commercial_outcomes(rows)
    assert c.status is CalibrationStatus.REVIEWABLE_EXTERNAL_SAMPLE
    assert c.median_buyer_gross_margin < 0.45
    assert c.recommended_action is CalibrationAction.REVIEW_RAISE_PRICE_OR_NARROW_SCOPE


def test_good_margin_preserves_prior_and_reports_buyer_level_effort():
    rows = [
        O(f"b{i}", f"e{i}", cost=7000, hours=10 + i, invoices=200)
        for i in range(5)
    ]
    c = calibrate_commercial_outcomes(rows)
    assert c.status is CalibrationStatus.REVIEWABLE_EXTERNAL_SAMPLE
    assert c.recommended_action is CalibrationAction.KEEP_PRIOR
    assert c.median_buyer_gross_margin == 0.65
    assert c.median_buyer_hours_per_100_invoices == 6.0


def test_conversion_rates_are_buyer_cohort_based():
    rows = [
        O("b1", "d1", fee=6250, cost=2000, diagnostic=True, pilot=False),
        O("b1", "p1", pilot=True),
        O("b2", "d2", fee=6250, cost=2000, diagnostic=True, pilot=False),
        O("b3", "p3", pilot=True, annual=True),
        O("b4", "p4", pilot=True),
        O("b5", "p5", pilot=True),
    ]
    c = calibrate_commercial_outcomes(rows)
    assert c.diagnostic_to_pilot.denominator == 2
    assert c.diagnostic_to_pilot.numerator == 1
    assert c.pilot_to_annual.denominator == 4
    assert c.pilot_to_annual.numerator == 1
    assert 0 <= c.pilot_to_annual.lower_95 <= c.pilot_to_annual.upper_95 <= 1


def test_duplicate_engagement_id_is_rejected():
    with pytest.raises(ValueError, match="duplicate engagement_id"):
        calibrate_commercial_outcomes([O("b1", "same"), O("b2", "same")])
