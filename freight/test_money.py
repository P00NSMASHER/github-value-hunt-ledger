import pytest

from freight.money import format_cents, format_dollars


def test_exact_integer_cent_formatting_at_supported_stress_values():
    assert format_cents("USD", 9_007_199_254_740_993) == "USD 90,071,992,547,409.93"
    assert format_cents("USD", 2**63 - 1) == "USD 92,233,720,368,547,758.07"
    assert format_dollars(-123) == "$-1.23"


@pytest.mark.parametrize("bad", [True, 1.5, "100", None])
def test_formatters_reject_non_integer_cents(bad):
    with pytest.raises(ValueError):
        format_cents("USD", bad)
