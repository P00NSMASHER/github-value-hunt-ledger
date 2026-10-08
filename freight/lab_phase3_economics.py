"""Free-audit/contingency economics for RETALLY's *actual documented offer*.

Inputs are assumptions, NOT observed win rates, collections or ROI.  Amounts
are exact integer cents; zero-upfront auditing and negative margins are retained.
The optional fixed-fee engagement is modeled elsewhere, never conflated here.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_CEILING
from typing import Mapping

from freight.lab_assurance import digest


class EconomicsRejected(ValueError):
    pass


def _cents(x: int, name: str) -> int:
    if type(x) is not int or not 0 <= x <= 2**63 - 1:
        raise EconomicsRejected(f"INVALID_{name.upper()}")
    return x


def _bps(x: int, name: str, low: int = 0, high: int = 10000) -> int:
    if type(x) is not int or not low <= x <= high:
        raise EconomicsRejected(f"INVALID_{name.upper()}")
    return x


def _minutes(x: int, name: str) -> int:
    return _cents(x, name)


def _mul_bps(cents: int, bps: int) -> int:
    return cents * bps // 10000


@dataclass(frozen=True)
class ContingencyAssumptions:
    # The flagship offer always has zero audit fees. No customer revenue until
    # eligible customer recovery, valid contract terms and RETALLY collection.
    opportunity_cents: int
    probability_valid_bps: int
    probability_customer_recovery_bps: int
    probability_fee_collection_bps: int
    expected_reversal_bps: int
    contingency_rate_bps: int
    free_audit_minutes: int
    recovery_work_minutes_if_valid: int
    loaded_analyst_hourly_cents: int
    acquisition_cost_cents: int
    other_delivery_cost_cents: int
    recovery_delay_days: int
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.currency != "USD":
            raise EconomicsRejected("UNSUPPORTED_CURRENCY_IN_USD_MODEL")
        for k in ("opportunity_cents", "loaded_analyst_hourly_cents", "acquisition_cost_cents", "other_delivery_cost_cents"):
            _cents(getattr(self, k), k)
        for k in ("free_audit_minutes", "recovery_work_minutes_if_valid", "recovery_delay_days"):
            _minutes(getattr(self, k), k)
        for k in ("probability_valid_bps", "probability_customer_recovery_bps",
                  "probability_fee_collection_bps", "expected_reversal_bps"):
            _bps(getattr(self, k), k)
        _bps(self.contingency_rate_bps, "contingency_rate_bps", 1, 9999)


@dataclass(frozen=True)
class ContingencyDecision:
    scope: str
    currency: str
    upfront_audit_revenue_cents: int
    potential_overpayment_cents: int
    expected_customer_recovery_cents: int
    expected_gross_fee_cents: int
    expected_collected_fee_cents: int
    expected_audit_cost_cents: int
    expected_recovery_work_cost_cents: int
    expected_acquisition_and_delivery_cost_cents: int
    expected_total_cost_cents: int
    expected_net_margin_cents: int
    break_even_potential_recovery_cents: int | None
    recovery_delay_days_assumption: int
    assessment: str
    evidence_needed: tuple[str, ...]
    receipt_sha256: str


def analyze_contingency(a: ContingencyAssumptions) -> ContingencyDecision:
    if not isinstance(a, ContingencyAssumptions):
        raise EconomicsRejected("INVALID_ASSUMPTIONS")
    # Sequential expected values intentionally disclose that probabilities
    # are conditional assumptions; they are not empirically calibrated.
    valid_cents = _mul_bps(a.opportunity_cents, a.probability_valid_bps)
    applied_cents = _mul_bps(valid_cents, a.probability_customer_recovery_bps)
    net_customer = applied_cents - _mul_bps(applied_cents, a.expected_reversal_bps)
    gross_fee = _mul_bps(net_customer, a.contingency_rate_bps)
    collected_fee = _mul_bps(gross_fee, a.probability_fee_collection_bps)
    audit_cost = (a.free_audit_minutes * a.loaded_analyst_hourly_cents + 59) // 60
    expected_recovery_minutes = _mul_bps(a.recovery_work_minutes_if_valid, a.probability_valid_bps)
    recovery_cost = (expected_recovery_minutes * a.loaded_analyst_hourly_cents + 59) // 60
    other = a.acquisition_cost_cents + a.other_delivery_cost_cents
    total = audit_cost + recovery_cost + other
    net = collected_fee - total
    factor = (Decimal(a.probability_valid_bps) * a.probability_customer_recovery_bps
              * (10000-a.expected_reversal_bps) * a.contingency_rate_bps
              * a.probability_fee_collection_bps) / Decimal(10000**5)
    break_even = None if factor == 0 else int((Decimal(total)/factor).to_integral_value(rounding=ROUND_CEILING))
    assessment = "REVIEW_ONLY_NOT_A_PROFIT_FORECAST" if net > 0 else "MODELED_UNECONOMIC_HOLD"
    evidence = ("Actual buyer-owned invoice and rate authority",
                "Real validation and customer recovery rates",
                "Signed contingency terms and independently reconciled cash",
                "Observed analyst hours, refund frequency and customer acquisition cost")
    body = dict(scope="UNCALIBRATED_SIMULATED_CONTINGENCY_MODEL",currency=a.currency,
                upfront_audit_revenue_cents=0,potential_overpayment_cents=a.opportunity_cents,
                expected_customer_recovery_cents=net_customer,
                expected_gross_fee_cents=gross_fee,expected_collected_fee_cents=collected_fee,
                expected_audit_cost_cents=audit_cost,
                expected_recovery_work_cost_cents=recovery_cost,
                expected_acquisition_and_delivery_cost_cents=other,
                expected_total_cost_cents=total,expected_net_margin_cents=net,
                break_even_potential_recovery_cents=break_even,
                recovery_delay_days_assumption=a.recovery_delay_days,
                assessment=assessment,evidence_needed=evidence)
    return ContingencyDecision(**body,receipt_sha256=digest(body))


def fixed_default_contingency_bps() -> int:
    """Read RETALLY's existing single source of truth, not a second rate."""
    from freight.commercial_terms import DEFAULT_CONTINGENCY_RECOVERY_RATE
    return int(Decimal(DEFAULT_CONTINGENCY_RECOVERY_RATE)*10000)


def compare_scenarios(scenarios: Mapping[str, ContingencyAssumptions]) -> dict:
    if not scenarios or len(scenarios) > 25:
        raise EconomicsRejected("INVALID_SCENARIO_COUNT")
    outcomes = {}
    for k,a in sorted(scenarios.items()):
        if not k or k in outcomes:
            raise EconomicsRejected("INVALID_SCENARIO_NAME")
        outcomes[k] = asdict(analyze_contingency(a))
    return {"scope":"MODELED_PILOT_NO_REAL_CUSTOMERS", "scenarios":outcomes,
            "recommendation":"INVESTIGATE_ASSUMPTIONS_NOT_ISSUE_CLAIMS",
            "receipt_sha256":digest(outcomes)}
