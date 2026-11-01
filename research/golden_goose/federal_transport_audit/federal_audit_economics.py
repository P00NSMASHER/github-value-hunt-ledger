"""Offline, hypothetical federal freight audit business-case falsifier.

The 50% cap is a 31 USC 3726(e) postpayment-audit contractor ceiling,
not a promise of a commission. The 30% of collected funds below is an
*invented scenario contract*, not an official price or a real engagement.
This module never establishes eligibility, a payable fee or owner revenue.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation, ROUND_DOWN

CENTS = Decimal('0.01')
HALF = Decimal('0.50')


def number(value, field):
    if isinstance(value, bool) or value is None:
        raise ValueError(f'{field}: not an allowed number')
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f'{field}: invalid number') from exc
    if not n.is_finite() or n < 0:
        raise ValueError(f'{field}: must be non-negative and finite')
    return n


def money(value, field):
    n = number(value, field)
    try:
        cents = n.quantize(CENTS)
    except InvalidOperation as exc:
        raise ValueError(f'{field}: unbounded numeric magnitude') from exc
    if n != cents:
        raise ValueError(f'{field}: sub-cent precision not allowed')
    return n


def evaluate(row):
    """Return modeled contribution; never assert actual receipt/eligibility."""
    expected = {'case', 'identified_usd', 'modeled_collected_usd',
                'hypothetical_fee_rate', 'review_hours', 'labor_usd_hour',
                'overhead_usd', 'signed_contract', 'agency_buy_authority',
                'independent_receipt'}
    if set(row) != expected:
        raise ValueError('schema mismatch; missing or unexpected evidence')
    for field in ('signed_contract', 'agency_buy_authority', 'independent_receipt'):
        if type(row[field]) is not bool:
            raise ValueError(f'{field}: must be explicit boolean')
    if not isinstance(row['case'], str) or not row['case'].strip():
        raise ValueError('case: must be named')
    identified = money(row['identified_usd'], 'identified_usd')
    collected = money(row['modeled_collected_usd'], 'modeled_collected_usd')
    rate = number(row['hypothetical_fee_rate'], 'hypothetical_fee_rate')
    hours = number(row['review_hours'], 'review_hours')
    labor = money(row['labor_usd_hour'], 'labor_usd_hour')
    overhead = money(row['overhead_usd'], 'overhead_usd')
    if collected > identified:
        raise ValueError('modeled recovery cannot exceed identified overpayment')
    if rate > 1:
        raise ValueError('fee rate outside 0..1 proportion')
    # Conservative model: 30%-type fee of collected dollars, limited by
    # 31 USC 3726(e)'s 50%-of-identified cap; no statutory entitlement.
    modeled_fee = min(collected * rate, identified * HALF).quantize(CENTS, rounding=ROUND_DOWN)
    modeled_cost = (hours * labor + overhead).quantize(CENTS, rounding=ROUND_DOWN)
    modeled_margin = modeled_fee - modeled_cost
    # Independently documented owner payment is *never* established by an
    # input flag, screenshot, modeled collection or synthetic claim.
    return {
        'case': row['case'],
        'hypothetical_fee_usd': str(modeled_fee),
        'hypothetical_cost_usd': str(modeled_cost),
        'hypothetical_contribution_usd': str(modeled_margin),
        'verified_owner_cash_usd': '0.00',
        'verified_collectible_usd': '0.00',
        'actual_contract_status': 'NOT_VERIFIED',
        'actual_customer_status': 'NONE_VERIFIED',
        'decision': 'NO_GO_FIRST_100_FEDERAL_DIRECT',
        'reason': 'No verified procuring buyer, award, authority, executed scope or owner remittance; model only.',
    }
