"""Commercial terms for the flagship Freight Recovery offer.

The public site, operator workflow, and recovery-fee arithmetic all consume the
same default rate from this module.  A rate can be supplied at build or
engagement time, but fees are never calculated from estimated or merely
identified opportunities.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


DEFAULT_CONTINGENCY_RECOVERY_RATE = Decimal("0.30")


def normalize_contingency_rate(value: Decimal | str | int | float) -> Decimal:
    """Return a bounded Decimal rate suitable for money calculations."""
    if isinstance(value, bool):
        raise ValueError("contingency recovery rate must be a number")
    try:
        rate = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError("contingency recovery rate must be a number") from error
    if not rate.is_finite() or rate <= 0 or rate >= 1:
        raise ValueError("contingency recovery rate must be greater than 0 and less than 1")
    return rate.quantize(Decimal("0.0001")).normalize()


def contingency_rate_label(rate: Decimal | str | int | float) -> str:
    normalized = normalize_contingency_rate(rate)
    percent = (normalized * 100).normalize()
    rendered = format(percent, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered + "%"


@dataclass(frozen=True)
class RecoveryFeeBreakdown:
    actual_recovered_cents: int
    fee_eligible_recovered_cents: int
    contingency_rate: Decimal
    recovery_fee_cents: int
    customer_net_recovery_cents: int


def calculate_recovery_fee(
    *,
    actual_recovered_cents: int,
    fee_eligible_recovered_cents: int | None = None,
    contingency_rate: Decimal | str | int | float = DEFAULT_CONTINGENCY_RECOVERY_RATE,
) -> RecoveryFeeBreakdown:
    """Calculate a fee only from recovered funds supported by settlement evidence.

    ``actual_recovered_cents`` is the amount received or posted to the customer.
    ``fee_eligible_recovered_cents`` may be lower when an engagement excludes
    pre-existing, automatic, incumbent-known, unsupported, or reversed amounts.
    """
    if isinstance(actual_recovered_cents, bool) or not isinstance(actual_recovered_cents, int):
        raise ValueError("actual_recovered_cents must be an integer")
    if actual_recovered_cents < 0:
        raise ValueError("actual_recovered_cents must be non-negative")
    eligible = (
        actual_recovered_cents
        if fee_eligible_recovered_cents is None
        else fee_eligible_recovered_cents
    )
    if isinstance(eligible, bool) or not isinstance(eligible, int):
        raise ValueError("fee_eligible_recovered_cents must be an integer")
    if eligible < 0 or eligible > actual_recovered_cents:
        raise ValueError(
            "fee_eligible_recovered_cents must be between zero and actual recovered funds"
        )

    rate = normalize_contingency_rate(contingency_rate)
    fee = int(
        (Decimal(eligible) * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    return RecoveryFeeBreakdown(
        actual_recovered_cents=actual_recovered_cents,
        fee_eligible_recovered_cents=eligible,
        contingency_rate=rate,
        recovery_fee_cents=fee,
        customer_net_recovery_cents=actual_recovered_cents - fee,
    )
