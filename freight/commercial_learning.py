"""Outcome-grounded commercial calibration for Freight Recovery.

The calibrator is intentionally conservative:
- synthetic/internal outcomes never enter the sample;
- direct external commercial evidence is required;
- unique buyer cohorts, not raw engagement count, govern repricing readiness;
- repeated engagements from one buyer are collapsed to buyer-level medians;
- success-fee/recovery upside is not used to calibrate fixed-fee economics;
- recommendations never mutate pricing automatically.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from statistics import median


class CalibrationStatus(str, Enum):
    NO_EXTERNAL_DATA = "NO_EXTERNAL_DATA"
    OBSERVE_ONLY = "OBSERVE_ONLY"
    REVIEWABLE_EXTERNAL_SAMPLE = "REVIEWABLE_EXTERNAL_SAMPLE"


class CalibrationAction(str, Enum):
    KEEP_PRIOR = "KEEP_PRIOR"
    REVIEW_RAISE_PRICE_OR_NARROW_SCOPE = "REVIEW_RAISE_PRICE_OR_NARROW_SCOPE"
    PROTECT_MARGIN_NO_AUTOMATIC_DISCOUNT = "PROTECT_MARGIN_NO_AUTOMATIC_DISCOUNT"


@dataclass(frozen=True)
class RateEstimate:
    numerator: int
    denominator: int
    rate: float | None
    lower_95: float | None
    upper_95: float | None


@dataclass(frozen=True)
class CommercialCalibration:
    status: CalibrationStatus
    paid_engagements: int
    unique_buyers: int
    buyers_with_margin: int
    median_buyer_gross_margin: float | None
    median_buyer_hours_per_100_invoices: float | None
    diagnostic_to_pilot: RateEstimate
    pilot_to_annual: RateEstimate
    max_buyer_engagement_share: float | None
    target_gross_margin: float
    recommended_action: CalibrationAction
    warnings: tuple[str, ...]


def _wilson(k: int, n: int, z: float = 1.96) -> RateEstimate:
    if n <= 0:
        return RateEstimate(k, n, None, None, None)
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / den
    return RateEstimate(
        k,
        n,
        round(p, 4),
        round(max(0.0, center - half), 4),
        round(min(1.0, center + half), 4),
    )


def _eligible(outcome: dict) -> bool:
    if outcome.get("experiment_id") != "EXP-001":
        return False
    metrics = outcome.get("freight_metrics") or {}
    if metrics.get("synthetic") is not False:
        return False
    if metrics.get("external_commercial_evidence") is not True:
        return False
    if any(not isinstance(metrics.get(name), str) or not metrics[name].strip()
           for name in ("engagement_id", "buyer_cohort_key")):
        return False
    # Outcomes may be loaded directly from JSONL instead of through the adapter.
    # Validate the commercial sample at this boundary as well.
    for name in ("diagnostic_paid", "pilot_paid", "annual_converted"):
        value = metrics.get(name)
        if value is not None and type(value) is not bool:
            raise ValueError(name + " must be a boolean when provided")
    for name, value in (
        ("revenue_usd", outcome.get("revenue_usd")),
        *((name, metrics.get(name)) for name in ("fixed_fee_usd", "delivery_cost_usd", "reviewer_hours")),
    ):
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(name + " must be a finite non-negative number")
    fee = metrics.get("fixed_fee_usd")
    if fee is not None and fee <= 0:
        raise ValueError("fixed_fee_usd must be positive when provided")
    invoices = metrics.get("invoices_reviewed")
    if invoices is not None and (type(invoices) is not int or invoices < 0):
        raise ValueError("invoices_reviewed must be a non-negative integer")
    return bool(
        metrics.get("diagnostic_paid")
        or metrics.get("pilot_paid")
        or metrics.get("annual_converted")
        or (outcome.get("revenue_usd") or 0) > 0
    )


def calibrate_commercial_outcomes(
    outcomes: list[dict] | tuple[dict, ...],
    *,
    target_gross_margin: float = 0.50,
    min_unique_buyers_for_review: int = 5,
    min_paid_engagements_for_review: int = 5,
) -> CommercialCalibration:
    if isinstance(target_gross_margin, bool) or not isinstance(target_gross_margin, (int, float)) or not 0 <= target_gross_margin < 1:
        raise ValueError("target_gross_margin must be in [0,1)")
    if any(type(value) is not int or value < 1 for value in (
        min_unique_buyers_for_review, min_paid_engagements_for_review
    )):
        raise ValueError("minimum sample thresholds must be positive")

    eligible = [o for o in outcomes if _eligible(o)]
    engagement_ids: set[str] = set()
    by_buyer: dict[str, list[dict]] = {}
    for outcome in eligible:
        metrics = outcome["freight_metrics"]
        engagement_id = str(metrics["engagement_id"])
        if engagement_id in engagement_ids:
            raise ValueError("duplicate engagement_id in commercial outcome sample")
        engagement_ids.add(engagement_id)
        buyer = str(metrics["buyer_cohort_key"])
        by_buyer.setdefault(buyer, []).append(outcome)

    if not eligible:
        return CommercialCalibration(
            CalibrationStatus.NO_EXTERNAL_DATA,
            0,
            0,
            0,
            None,
            None,
            _wilson(0, 0),
            _wilson(0, 0),
            None,
            target_gross_margin,
            CalibrationAction.KEEP_PRIOR,
            ("No direct external commercial Freight outcomes are eligible for calibration.",),
        )

    buyer_margin_medians: list[float] = []
    buyer_hours_medians: list[float] = []
    diagnostic_buyers: set[str] = set()
    pilot_buyers: set[str] = set()
    annual_buyers: set[str] = set()

    for buyer, records in by_buyer.items():
        margins: list[float] = []
        hours_per_100: list[float] = []
        for outcome in records:
            metrics = outcome["freight_metrics"]
            if metrics.get("diagnostic_paid"):
                diagnostic_buyers.add(buyer)
            if metrics.get("pilot_paid"):
                pilot_buyers.add(buyer)
            if metrics.get("annual_converted"):
                annual_buyers.add(buyer)

            fee = metrics.get("fixed_fee_usd")
            cost = metrics.get("delivery_cost_usd")
            if fee is not None and cost is not None and fee > 0:
                margins.append((fee - cost) / fee)

            reviewer_hours = metrics.get("reviewer_hours")
            invoices = metrics.get("invoices_reviewed")
            if (
                reviewer_hours is not None
                and invoices is not None
                and reviewer_hours >= 0
                and invoices > 0
            ):
                hours_per_100.append(reviewer_hours / invoices * 100)

        if margins:
            buyer_margin_medians.append(median(margins))
        if hours_per_100:
            buyer_hours_medians.append(median(hours_per_100))

    unique_buyers = len(by_buyer)
    paid_engagements = len(eligible)
    buyers_with_margin = len(buyer_margin_medians)
    max_share = max(len(v) for v in by_buyer.values()) / paid_engagements

    diagnostic_to_pilot = _wilson(
        len(diagnostic_buyers & pilot_buyers),
        len(diagnostic_buyers),
    )
    pilot_to_annual = _wilson(
        len(pilot_buyers & annual_buyers),
        len(pilot_buyers),
    )

    warnings: list[str] = []
    if unique_buyers < min_unique_buyers_for_review:
        warnings.append(
            f"Need at least {min_unique_buyers_for_review} unique buyers before repricing review; have {unique_buyers}."
        )
    if paid_engagements < min_paid_engagements_for_review:
        warnings.append(
            f"Need at least {min_paid_engagements_for_review} paid engagements before repricing review; have {paid_engagements}."
        )
    if buyers_with_margin < min_unique_buyers_for_review:
        warnings.append(
            f"Need usable fixed-fee margin evidence from at least {min_unique_buyers_for_review} unique buyers; have {buyers_with_margin}."
        )
    if max_share > 0.40:
        warnings.append(
            "One buyer represents more than 40% of eligible engagements; buyer-level medians reduce but do not eliminate concentration risk."
        )

    reviewable = (
        unique_buyers >= min_unique_buyers_for_review
        and paid_engagements >= min_paid_engagements_for_review
        and buyers_with_margin >= min_unique_buyers_for_review
    )
    status = (
        CalibrationStatus.REVIEWABLE_EXTERNAL_SAMPLE
        if reviewable
        else CalibrationStatus.OBSERVE_ONLY
    )

    margin = round(median(buyer_margin_medians), 4) if buyer_margin_medians else None
    hours = (
        round(median(buyer_hours_medians), 2)
        if buyer_hours_medians
        else None
    )

    action = CalibrationAction.KEEP_PRIOR
    if reviewable and margin is not None:
        if margin < target_gross_margin - 0.05:
            action = CalibrationAction.REVIEW_RAISE_PRICE_OR_NARROW_SCOPE
        elif margin > target_gross_margin + 0.20:
            action = CalibrationAction.PROTECT_MARGIN_NO_AUTOMATIC_DISCOUNT

    return CommercialCalibration(
        status,
        paid_engagements,
        unique_buyers,
        buyers_with_margin,
        margin,
        hours,
        diagnostic_to_pilot,
        pilot_to_annual,
        round(max_share, 4),
        target_gross_margin,
        action,
        tuple(warnings),
    )
