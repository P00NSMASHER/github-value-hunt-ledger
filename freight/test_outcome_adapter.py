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
        technical_result="synthetic rehearsal passed",
    )
    data.update(overrides)
    return FreightOutcomeInput(**data)


def test_synthetic_rehearsal_can_be_recorded_only_without_commercial_value():
    out = build_outcome(base())
    assert out["experiment_id"] == "EXP-001"
    assert out["freight_metrics"]["synthetic"] is True
    assert out["revenue_usd"] is None


def test_synthetic_rehearsal_cannot_claim_revenue():
    with pytest.raises(ValueError, match="synthetic rehearsal"):
        build_outcome(base(revenue_usd=1000))


def test_positive_real_value_requires_direct_external_evidence():
    with pytest.raises(ValueError, match="direct external evidence"):
        build_outcome(
            base(
                synthetic=False,
                customer_value_usd=2500,
                realized_recovery_usd=2500,
            )
        )


def test_positive_real_value_requires_search_and_capability_attribution():
    with pytest.raises(ValueError, match="origin_search_ids"):
        build_outcome(
            base(
                synthetic=False,
                external_value_evidence=True,
                customer_value_usd=2500,
                realized_recovery_usd=2500,
            )
        )


def test_real_outcome_maps_to_global_schema_and_preserves_freight_metrics():
    out = build_outcome(
        base(
            synthetic=False,
            external_value_evidence=True,
            origin_search_ids=("RUN:20260920T155926Z:hunter03:settlement-persistence-race",),
            contributing_capability_ids=("CAP-006","CAP-016"),
            revenue_usd=20000,
            customer_value_usd=2500,
            realized_recovery_usd=2500,
            pilot_paid=True,
            reviewer_hours=12.5,
            false_positive_usd=0,
            commercial_result="paid pilot and settlement-proven recovery",
            evidence_location="customer/authorized/pilot-001",
        )
    )
    assert out["opportunity"] == "Freight Recovery"
    assert out["revenue_usd"] == 20000
    assert out["freight_metrics"]["pilot_paid"] is True
