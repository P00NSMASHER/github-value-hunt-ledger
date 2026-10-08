"""RETALLY no-upfront founding-pilot risk analysis.

Scenario modeling ONLY. This module does not approve prices, claims, contracts,
a scope or confidential-data intake. Recoveries are uncertain; zero recovery
means zero contingency fee and RETALLY still bears real delivery costs.
The existing freight.deal_economics fixed-fee route is intentionally untouched.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import argparse
import json
from pathlib import Path

P = Decimal
ZERO = P("0")
ONE = P("1")
CENTS = P("0.01")
REQUIRED_MONEY = (
    "supported_opportunity_usd",
    "loaded_hourly_cost_usd",
    "other_delivery_cost_usd",
    "recovery_administration_cost_usd",
    "max_authorized_loss_usd",
)
REQUIRED_HOURS = ("analyst_hours", "independent_reviewer_hours", "administrative_hours", "max_authorized_hours")
REQUIRED_FRACTIONS = (
    "hypothetical_contingency_rate",
    "realization_fraction",
    "unique_attribution_fraction",
    "fee_eligibility_fraction",
    "target_expected_gross_margin",
)
REQUIRED_FLAGS = (
    "actual_rate_approved_in_signed_terms",
    "buyer_specific_scope_authorized",
    "buyer_data_controls_verified",
    "independent_reviewer_reserved",
)
REQUIRED = {"scenario_label", "is_synthetic", *REQUIRED_MONEY, *REQUIRED_HOURS,
            *REQUIRED_FRACTIONS, *REQUIRED_FLAGS}


def decimal_field(data: dict, name: str) -> Decimal:
    value = data[name]
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError(name + " must be a finite numeric value")
    try:
        number = P(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(name + " must be a finite numeric value") from exc
    if not number.is_finite():
        raise ValueError(name + " must be finite")
    if number < ZERO:
        raise ValueError(name + " cannot be negative")
    return number


def dollar(value: Decimal) -> str:
    return str(value.quantize(CENTS, rounding=ROUND_HALF_UP))


def model_scenario(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("scenario must be a JSON object")
    missing = REQUIRED - set(data)
    unknown = set(data) - REQUIRED
    if missing or unknown:
        raise ValueError("schema mismatch; missing=" + ",".join(sorted(missing)) + "; unknown=" + ",".join(sorted(unknown)))
    if data["is_synthetic"] is not True:
        raise ValueError("real customer inputs prohibited in this public scenario model")
    if not isinstance(data["scenario_label"], str) or not data["scenario_label"].strip():
        raise ValueError("scenario_label required")
    for flag in REQUIRED_FLAGS:
        if type(data[flag]) is not bool:
            raise ValueError(flag + " must be a boolean")
    v = {k: decimal_field(data, k) for k in (REQUIRED_MONEY + REQUIRED_HOURS + REQUIRED_FRACTIONS)}
    for key in REQUIRED_FRACTIONS:
        if v[key] > ONE:
            raise ValueError(key + " must be within [0,1]")
    if not ZERO < v["hypothetical_contingency_rate"] < ONE:
        raise ValueError("hypothetical_contingency_rate must be within (0,1)")
    if not ZERO <= v["target_expected_gross_margin"] < ONE:
        raise ValueError("target_expected_gross_margin must be within [0,1)")
    if not v["loaded_hourly_cost_usd"] > ZERO:
        raise ValueError("loaded_hourly_cost_usd must include positive real founder/reviewer labor cost")
    hours = sum((v[name] for name in REQUIRED_HOURS[:3]), ZERO)
    # Exclude the cap itself from the consumed-hours sum.
    costs = hours * v["loaded_hourly_cost_usd"] + v["other_delivery_cost_usd"] + v["recovery_administration_cost_usd"]
    # These fractions are hypotheses, not estimated customer recoveries.
    expected_eligible = (v["supported_opportunity_usd"] * v["realization_fraction"]
                         * v["unique_attribution_fraction"] * v["fee_eligibility_fraction"])
    expected_fee = expected_eligible * v["hypothetical_contingency_rate"]
    expected_contribution = expected_fee - costs
    margin = expected_contribution / expected_fee if expected_fee > ZERO else None
    realized_eligible_break_even = costs / v["hypothetical_contingency_rate"]
    portion = (v["realization_fraction"] * v["unique_attribution_fraction"] * v["fee_eligibility_fraction"])
    supported_opportunity_break_even = realized_eligible_break_even / portion if portion > ZERO else None
    evidence_missing = [key for key in REQUIRED_FLAGS if data[key] is False]
    reasons = []
    if hours > v["max_authorized_hours"]:
        reasons.append("planned_hours_exceed_cap")
    if costs > v["max_authorized_loss_usd"]:
        reasons.append("zero_recovery_cash_loss_exceeds_cap")
    if expected_fee <= ZERO:
        reasons.append("no_probability_adjusted_fee")
    elif margin < v["target_expected_gross_margin"]:
        reasons.append("hypothetical_margin_below_target")
    reasons.extend(evidence_missing)
    return {
        "scenario_label": data["scenario_label"],
        "classification": "SYNTHETIC_INTERNAL_WHAT_IF_ONLY",
        "customer_price_or_approved_rate": False,
        "customer_kickoff_authorized": False,
        "cost": {
            "review_hours": str(hours),
            "delivery_cost_usd": dollar(costs),
            "zero_recovery_fee_usd": "0.00",
            "zero_recovery_loss_usd": dollar(costs),
            "authorized_hour_cap": str(v["max_authorized_hours"]),
            "authorized_loss_cap_usd": dollar(v["max_authorized_loss_usd"]),
        },
        "illustrative_only": {
            "modeled_supported_opportunity_usd": dollar(v["supported_opportunity_usd"]),
            "assumed_realization_fraction": str(v["realization_fraction"]),
            "assumed_unique_attribution_fraction": str(v["unique_attribution_fraction"]),
            "assumed_fee_eligibility_fraction": str(v["fee_eligibility_fraction"]),
            "unapproved_example_fee_rate": str(v["hypothetical_contingency_rate"]),
            "modeled_expected_fee_usd": dollar(expected_fee),
            "modeled_expected_contribution_usd": dollar(expected_contribution),
            "modeled_expected_margin": None if margin is None else str(margin.quantize(P(".0001"), rounding=ROUND_HALF_UP)),
            "break_even_actual_fee_eligible_receipts_usd": dollar(realized_eligible_break_even),
            "break_even_supported_opportunity_usd": None if supported_opportunity_break_even is None else dollar(supported_opportunity_break_even),
        },
        "risk_decision": "HOLD" if reasons else "HUMAN_REVIEW_REQUIRED_NOT_KICKOFF_AUTHORIZED",
        "blocking_reasons": sorted(reasons),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--require-human-review-eligible", action="store_true")
    args = parser.parse_args()
    result = model_scenario(json.loads(args.scenario.read_text(encoding="utf-8")))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if args.require_human_review_eligible and result["risk_decision"] == "HOLD" else 0


if __name__ == "__main__":
    raise SystemExit(main())
