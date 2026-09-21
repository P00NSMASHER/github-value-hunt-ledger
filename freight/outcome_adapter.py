"""Freight Recovery adapter for the global technology-intelligence outcome schema.

Synthetic rehearsals may be useful technical evidence, but they are never
recorded as customer value or revenue. Positive commercial claims require
explicit external evidence and search/capability attribution.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


VALID_RESULTS = {"PASSED", "FAILED", "PARTIAL", "INVALID"}


@dataclass(frozen=True)
class FreightOutcomeInput:
    outcome_id: str
    date: str
    result: str
    evidence_location: str
    origin_search_ids: tuple[str, ...]
    contributing_capability_ids: tuple[str, ...]
    contributing_repositories: tuple[str, ...] = ()
    revenue_usd: float | None = None
    customer_value_usd: float | None = None
    engineering_days_saved_low: float | None = None
    engineering_days_saved_high: float | None = None
    technical_result: str | None = None
    commercial_result: str | None = None
    unexpected_failure_modes: tuple[str, ...] = ()
    search_policy_consequence: str | None = None
    notes: str | None = None
    synthetic: bool = False
    external_value_evidence: bool = False
    external_commercial_evidence: bool = False
    engagement_id: str | None = None
    buyer_cohort_key: str | None = None
    diagnostic_paid: bool | None = None
    pilot_paid: bool | None = None
    annual_converted: bool | None = None
    realized_recovery_usd: float | None = None
    reviewer_hours: float | None = None
    false_positive_usd: float | None = None
    fixed_fee_usd: float | None = None
    delivery_cost_usd: float | None = None
    invoices_reviewed: int | None = None
    shipments_reviewed: int | None = None
    days_to_first_finding: float | None = None
    days_to_final_report: float | None = None


def _nonnegative(name: str, value: float | None) -> None:
    if value is not None and (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(name + " must be a finite non-negative number")


def _required_text(name: str, value: str | None) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " is required")


def build_outcome(inp: FreightOutcomeInput) -> dict:
    for name in ("synthetic", "external_value_evidence", "external_commercial_evidence"):
        if type(getattr(inp, name)) is not bool:
            raise ValueError(name + " must be a boolean")
    for name in ("diagnostic_paid", "pilot_paid", "annual_converted"):
        value = getattr(inp, name)
        if value is not None and type(value) is not bool:
            raise ValueError(name + " must be a boolean when provided")
    if not inp.outcome_id.startswith("OUT:"):
        raise ValueError("outcome_id must start with OUT:")
    if not inp.date.strip():
        raise ValueError("date is required")
    if inp.result not in VALID_RESULTS:
        raise ValueError("invalid result")
    if not inp.evidence_location.strip():
        raise ValueError("evidence_location is required")

    for name in (
        "revenue_usd",
        "customer_value_usd",
        "engineering_days_saved_low",
        "engineering_days_saved_high",
        "realized_recovery_usd",
        "reviewer_hours",
        "false_positive_usd",
        "fixed_fee_usd",
        "delivery_cost_usd",
        "days_to_first_finding",
        "days_to_final_report",
    ):
        _nonnegative(name, getattr(inp, name))

    for name in ("invoices_reviewed", "shipments_reviewed"):
        value = getattr(inp, name)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError(name + " must be a non-negative integer")

    if inp.fixed_fee_usd is not None and inp.fixed_fee_usd <= 0:
        raise ValueError("fixed_fee_usd must be positive when provided")

    if (
        inp.engineering_days_saved_low is not None
        and inp.engineering_days_saved_high is not None
        and inp.engineering_days_saved_low > inp.engineering_days_saved_high
    ):
        raise ValueError("engineering_days_saved_low cannot exceed high")

    revenue_claimed = (inp.revenue_usd or 0) > 0
    value_claimed = any(
        (value or 0) > 0
        for value in (inp.customer_value_usd, inp.realized_recovery_usd)
    )
    positive_claim = revenue_claimed or value_claimed

    if inp.synthetic and positive_claim:
        raise ValueError("synthetic rehearsal cannot record revenue/customer value")
    if inp.synthetic and (inp.external_commercial_evidence or inp.external_value_evidence):
        raise ValueError("synthetic rehearsal cannot claim external evidence")
    if revenue_claimed and not inp.external_commercial_evidence:
        raise ValueError("positive revenue requires direct external commercial evidence")
    if value_claimed and not inp.external_value_evidence:
        raise ValueError("positive customer value requires direct external value evidence")
    if positive_claim and not inp.origin_search_ids:
        raise ValueError("positive commercial value requires origin_search_ids")
    if positive_claim and not inp.contributing_capability_ids:
        raise ValueError("positive commercial value requires contributing_capability_ids")

    has_commercial_stage = bool(
        inp.diagnostic_paid
        or inp.pilot_paid
        or inp.annual_converted
        or revenue_claimed
        or inp.fixed_fee_usd is not None
        or inp.delivery_cost_usd is not None
        or inp.invoices_reviewed is not None
        or inp.shipments_reviewed is not None
        or inp.days_to_first_finding is not None
        or inp.days_to_final_report is not None
    )
    if has_commercial_stage:
        if not inp.external_commercial_evidence:
            raise ValueError("commercial engagement metrics require direct external commercial evidence")

    if has_commercial_stage or value_claimed:
        _required_text("engagement_id", inp.engagement_id)
        _required_text("buyer_cohort_key", inp.buyer_cohort_key)

    if inp.realized_recovery_usd is not None:
        if inp.customer_value_usd is None:
            raise ValueError("realized recovery requires customer_value_usd")
        if inp.realized_recovery_usd > inp.customer_value_usd:
            raise ValueError("realized recovery cannot exceed recorded customer value")

    gross_margin = None
    if inp.fixed_fee_usd is not None and inp.delivery_cost_usd is not None:
        gross_margin = round(
            (inp.fixed_fee_usd - inp.delivery_cost_usd) / inp.fixed_fee_usd,
            4,
        )

    return {
        "outcome_id": inp.outcome_id,
        "date": inp.date,
        "experiment_id": "EXP-001",
        "opportunity": "Freight Recovery",
        "result": inp.result,
        "origin_search_ids": list(inp.origin_search_ids),
        "contributing_capability_ids": list(inp.contributing_capability_ids),
        "contributing_repositories": list(inp.contributing_repositories),
        "revenue_usd": inp.revenue_usd,
        "customer_value_usd": inp.customer_value_usd,
        "engineering_days_saved_low": inp.engineering_days_saved_low,
        "engineering_days_saved_high": inp.engineering_days_saved_high,
        "technical_result": inp.technical_result,
        "commercial_result": inp.commercial_result,
        "unexpected_failure_modes": list(inp.unexpected_failure_modes),
        "search_policy_consequence": inp.search_policy_consequence,
        "evidence_location": inp.evidence_location,
        "notes": inp.notes,
        "freight_metrics": {
            "synthetic": inp.synthetic,
            "external_commercial_evidence": inp.external_commercial_evidence,
            "external_value_evidence": inp.external_value_evidence,
            "engagement_id": inp.engagement_id,
            "buyer_cohort_key": inp.buyer_cohort_key,
            "diagnostic_paid": inp.diagnostic_paid,
            "pilot_paid": inp.pilot_paid,
            "annual_converted": inp.annual_converted,
            "realized_recovery_usd": inp.realized_recovery_usd,
            "reviewer_hours": inp.reviewer_hours,
            "false_positive_usd": inp.false_positive_usd,
            "fixed_fee_usd": inp.fixed_fee_usd,
            "delivery_cost_usd": inp.delivery_cost_usd,
            "gross_margin": gross_margin,
            "invoices_reviewed": inp.invoices_reviewed,
            "shipments_reviewed": inp.shipments_reviewed,
            "days_to_first_finding": inp.days_to_first_finding,
            "days_to_final_report": inp.days_to_final_report,
        },
    }
