from decimal import Decimal

import pytest

from freight.commercial_terms import (
    DEFAULT_CONTINGENCY_RECOVERY_RATE,
    calculate_recovery_fee,
    contingency_rate_label,
    normalize_contingency_rate,
)


def test_default_rate_is_configurable_working_assumption():
    assert DEFAULT_CONTINGENCY_RECOVERY_RATE == Decimal("0.30")
    assert contingency_rate_label(DEFAULT_CONTINGENCY_RECOVERY_RATE) == "30%"
    assert contingency_rate_label("0.325") == "32.5%"


def test_fee_is_based_only_on_fee_eligible_actual_recovery():
    result = calculate_recovery_fee(
        actual_recovered_cents=10_000_00,
        fee_eligible_recovered_cents=8_000_00,
    )
    assert result.recovery_fee_cents == 2_400_00
    assert result.customer_net_recovery_cents == 7_600_00


def test_no_recovery_means_no_fee():
    result = calculate_recovery_fee(actual_recovered_cents=0)
    assert result.recovery_fee_cents == 0
    assert result.customer_net_recovery_cents == 0


@pytest.mark.parametrize("rate", [0, 1, -0.1, "nan", True])
def test_rate_fails_closed(rate):
    with pytest.raises(ValueError):
        normalize_contingency_rate(rate)


def test_estimated_or_excess_fee_base_is_rejected():
    with pytest.raises(ValueError, match="between zero and actual"):
        calculate_recovery_fee(
            actual_recovered_cents=5_000,
            fee_eligible_recovered_cents=6_000,
        )
