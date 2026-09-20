"""Freight Recovery adapter for the global technology-intelligence outcome schema.

Synthetic rehearsals may be useful technical evidence, but they are never
recorded as customer value or revenue. Positive commercial value requires direct
external evidence and search/capability attribution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


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
    diagnostic_paid: bool | None = None
    pilot_paid: bool | None = None
    annual_converted: bool | None = None
    realized_recovery_usd: float | None = None
    reviewer_hours: float | None = None
    false_positive_usd: float | None = None


def _nonnegative(name: str, value: float | None) -> None:
    if value is not None and value < 0:
        raise ValueError(name + " must be non-negative")


def build_outcome(inp: FreightOutcomeInput) -> dict:
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
    ):
        _nonnegative(name, getattr(inp, name))

    if (
        inp.engineering_days_saved_low is not None
        and inp.engineering_days_saved_high is not None
        and inp.engineering_days_saved_low > inp.engineering_days_saved_high
    ):
        raise ValueError("engineering_days_saved_low cannot exceed high")

    claimed_value = any(
        (value or 0) > 0
        for value in (inp.revenue_usd, inp.customer_value_usd, inp.realized_recovery_usd)
    )
    if inp.synthetic and claimed_value:
        raise ValueError("synthetic rehearsal cannot record revenue/customer value")
    if claimed_value and not inp.external_value_evidence:
        raise ValueError("positive commercial value requires direct external evidence")
    if claimed_value and not inp.origin_search_ids:
        raise ValueError("positive commercial value requires origin_search_ids")
    if claimed_value and not inp.contributing_capability_ids:
        raise ValueError("positive commercial value requires contributing_capability_ids")

    if inp.realized_recovery_usd is not None:
        if inp.customer_value_usd is None:
            raise ValueError("realized recovery requires customer_value_usd")
        if inp.realized_recovery_usd > inp.customer_value_usd:
            raise ValueError("realized recovery cannot exceed recorded customer value")

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
            "diagnostic_paid": inp.diagnostic_paid,
            "pilot_paid": inp.pilot_paid,
            "annual_converted": inp.annual_converted,
            "realized_recovery_usd": inp.realized_recovery_usd,
            "reviewer_hours": inp.reviewer_hours,
            "false_positive_usd": inp.false_positive_usd,
        },
    }
