"""Commercial qualification and fixed-fee unit economics for Freight Recovery.

Success-fee upside is intentionally excluded from qualification. A diagnostic or
pilot must be economically viable on its fixed fee before any recovery outcome
is known. Planned analyst time includes founder labor and requires a positive
loaded hourly cost. Zero-hour profiles may omit that cost, but have no defined
analyst-hour budget.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
import math

from freight.readiness import ReadinessAssessment, ReadinessStatus


class DealRoute(str, Enum):
    DATA_READINESS_DIAGNOSTIC = "DATA_READINESS_DIAGNOSTIC"
    BLIND_FREIGHT_AUDIT_ACCEPTANCE_TEST = "BLIND_FREIGHT_AUDIT_ACCEPTANCE_TEST"
    HOLD = "HOLD"


@dataclass(frozen=True)
class DealProfile:
    annual_transport_spend_usd: float
    invoices_per_month: int
    carrier_count: int
    diagnostic_fee_usd: float
    pilot_fee_usd: float
    diagnostic_analyst_hours: float
    pilot_analyst_hours: float
    loaded_hourly_cost_usd: float
    diagnostic_other_cost_usd: float = 0.0
    pilot_other_cost_usd: float = 0.0
    target_gross_margin: float = 0.50

    def __post_init__(self):
        numeric_nonnegative = (
            "annual_transport_spend_usd",
            "invoices_per_month",
            "carrier_count",
            "diagnostic_fee_usd",
            "pilot_fee_usd",
            "diagnostic_analyst_hours",
            "pilot_analyst_hours",
            "loaded_hourly_cost_usd",
            "diagnostic_other_cost_usd",
            "pilot_other_cost_usd",
        )
        for field in numeric_nonnegative:
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(field + " must be a finite non-negative number")
        for field in ("invoices_per_month", "carrier_count"):
            if not isinstance(getattr(self, field), int):
                raise ValueError(field + " must be a non-negative integer")
        if isinstance(self.target_gross_margin, bool) or not isinstance(self.target_gross_margin, (int, float)) or not 0 <= self.target_gross_margin < 1:
            raise ValueError("target_gross_margin must be in [0,1)")
        if self.loaded_hourly_cost_usd == 0 and (
            self.diagnostic_analyst_hours > 0 or self.pilot_analyst_hours > 0
        ):
            raise ValueError("planned analyst hours require positive loaded_hourly_cost_usd, including founder labor")


@dataclass(frozen=True)
class OfferEconomics:
    fee_usd: float
    delivery_cost_usd: float
    gross_profit_usd: float
    gross_margin: float
    max_analyst_hours_at_target_margin: float | None


@dataclass(frozen=True)
class DealDecision:
    route: DealRoute
    economics: OfferEconomics
    initial_icp_scale: bool
    reasons: tuple[str, ...]


def _offer_economics(
    *,
    fee_usd: float,
    analyst_hours: float,
    loaded_hourly_cost_usd: float,
    other_cost_usd: float,
    target_gross_margin: float,
) -> OfferEconomics:
    if fee_usd <= 0:
        raise ValueError("fee_usd must be positive")
    delivery = analyst_hours * loaded_hourly_cost_usd + other_cost_usd
    gross_profit = fee_usd - delivery
    gross_margin = gross_profit / fee_usd
    if not all(math.isfinite(value) for value in (delivery, gross_profit, gross_margin)):
        raise ValueError("derived offer economics must be finite")

    spendable_delivery = fee_usd * (1 - target_gross_margin) - other_cost_usd
    if loaded_hourly_cost_usd <= 0:
        max_hours = None
    else:
        max_hours = max(spendable_delivery / loaded_hourly_cost_usd, 0.0)
        if not math.isfinite(max_hours):
            raise ValueError("derived analyst-hour budget must be finite")

    return OfferEconomics(
        fee_usd=round(fee_usd, 2),
        delivery_cost_usd=round(delivery, 2),
        gross_profit_usd=round(gross_profit, 2),
        gross_margin=round(gross_margin, 4),
        max_analyst_hours_at_target_margin=round(max_hours, 2) if max_hours is not None else None,
    )


def qualify_deal(readiness: ReadinessAssessment, profile: DealProfile) -> DealDecision:
    initial_scale = (
        profile.annual_transport_spend_usd >= 5_000_000
        or profile.invoices_per_month >= 500
    )

    if readiness.status is ReadinessStatus.READY:
        fee = profile.pilot_fee_usd
        hours = profile.pilot_analyst_hours
        other_cost = profile.pilot_other_cost_usd
        econ = _offer_economics(
            fee_usd=profile.pilot_fee_usd,
            analyst_hours=profile.pilot_analyst_hours,
            loaded_hourly_cost_usd=profile.loaded_hourly_cost_usd,
            other_cost_usd=profile.pilot_other_cost_usd,
            target_gross_margin=profile.target_gross_margin,
        )
        desired = DealRoute.BLIND_FREIGHT_AUDIT_ACCEPTANCE_TEST
    else:
        fee = profile.diagnostic_fee_usd
        hours = profile.diagnostic_analyst_hours
        other_cost = profile.diagnostic_other_cost_usd
        econ = _offer_economics(
            fee_usd=profile.diagnostic_fee_usd,
            analyst_hours=profile.diagnostic_analyst_hours,
            loaded_hourly_cost_usd=profile.loaded_hourly_cost_usd,
            other_cost_usd=profile.diagnostic_other_cost_usd,
            target_gross_margin=profile.target_gross_margin,
        )
        desired = DealRoute.DATA_READINESS_DIAGNOSTIC

    # Qualification uses the supplied precision, not rounded report values.
    # A margin just below the target must not round up into an accepted deal.
    exact_fee = Decimal(str(fee))
    exact_cost = (
        Decimal(str(hours)) * Decimal(str(profile.loaded_hourly_cost_usd))
        + Decimal(str(other_cost))
    )
    exact_profit = exact_fee - exact_cost
    below_margin_target = exact_profit < exact_fee * Decimal(str(profile.target_gross_margin))
    not_profitable = exact_profit <= 0

    reasons: list[str] = []
    if not initial_scale:
        reasons.append("below_initial_icp_scale")
    if profile.carrier_count < 2:
        reasons.append("limited_carrier_complexity")
    if below_margin_target:
        reasons.append("fixed_fee_gross_margin_below_target")
    if not_profitable:
        reasons.append("fixed_fee_not_profitable")

    # Scale is a priority signal, not an automatic rejection. Margin is the hard
    # commercial gate because speculative recovery is intentionally excluded.
    route = desired
    if (
        below_margin_target
        or not_profitable
    ):
        route = DealRoute.HOLD

    return DealDecision(route, econ, initial_scale, tuple(reasons))
