"""Research-only, no-network, fail-closed *fictional* freight success-fee model.

NEVER treats identified overcharges, modeled customer recoveries, reported
customer credits, or boolean attestations as owner cash or collectible fees.
The source repo's authoritative recovery accounting remains unchanged.
"""
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_UP

C = Decimal('0.01')
FIELDS = frozenset({
    'case', 'identified_usd', 'modeled_customer_recovery_usd',
    'modeled_attributable_recovery_usd', 'modeled_reversal_usd',
    'hypothetical_fee_rate', 'labor_hours', 'hourly_labor_usd',
    'direct_cost_usd', 'signed_agreement', 'customer_credit_verified',
    'owner_bank_receipt_verified',
})


def decimal(value, field, *, is_money=False):
    if isinstance(value, bool) or value is None or isinstance(value, (list, dict)):
        raise ValueError(f'{field}: invalid numeric type')
    if isinstance(value, str) and not value.strip():
        raise ValueError(f'{field}: empty numeric string')
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f'{field}: invalid decimal') from exc
    if not n.is_finite() or n < 0:
        raise ValueError(f'{field}: nonnegative finite required')
    if is_money:
        try:
            rounded = n.quantize(C)
        except InvalidOperation as exc:
            raise ValueError(f'{field}: unbounded magnitude') from exc
        if rounded != n:
            raise ValueError(f'{field}: no sub-cent money')
    return n


def estimate(row):
    """Conservative contribution model, with actual income strictly unverified."""
    if type(row) is not dict or set(row) != FIELDS:
        raise ValueError('missing or unexpected fields')
    if not isinstance(row['case'], str) or not row['case'].strip():
        raise ValueError('empty case')
    for key in ('signed_agreement', 'customer_credit_verified', 'owner_bank_receipt_verified'):
        if type(row[key]) is not bool:
            raise ValueError(f'{key}: explicit bool required')
    ident = decimal(row['identified_usd'], 'identified_usd', is_money=True)
    received = decimal(row['modeled_customer_recovery_usd'], 'modeled_customer_recovery_usd', is_money=True)
    attributable = decimal(row['modeled_attributable_recovery_usd'], 'modeled_attributable_recovery_usd', is_money=True)
    reversal = decimal(row['modeled_reversal_usd'], 'modeled_reversal_usd', is_money=True)
    rate = decimal(row['hypothetical_fee_rate'], 'hypothetical_fee_rate')
    hours = decimal(row['labor_hours'], 'labor_hours')
    hourly = decimal(row['hourly_labor_usd'], 'hourly_labor_usd', is_money=True)
    direct = decimal(row['direct_cost_usd'], 'direct_cost_usd', is_money=True)
    if rate > 1:
        raise ValueError('hypothetical rate above 1')
    if received > ident or attributable > received - reversal or reversal > received:
        raise ValueError('fictional recoveries cannot exceed supported cash bases')
    fee = (attributable * rate).quantize(C, rounding=ROUND_DOWN)
    cost = (hours * hourly + direct).quantize(C, rounding=ROUND_UP)
    contribution = fee - cost
    return {
        'case': row['case'],
        'fictional_fee_usd': str(fee),
        'fictional_cost_usd': str(cost),
        'fictional_contribution_usd': str(contribution),
        'customer_value_observed_usd': '0.00',
        'owner_collectible_observed_usd': '0.00',
        'owner_cash_verified_usd': '0.00',
        'decision': 'RESEARCH_WATCH_NOT_COMMERCIALLY_VALIDATED',
        'disclaimer': 'Modeled credits, agreement/receipt booleans, competitor list prices and government complaint counts are not owner cash or verified demand.',
    }


def min_recovered_for_fee(target_usd, rate):
    """Required cent-denominated eligible customer recovery for a fictional fee."""
    target = decimal(target_usd, 'target', is_money=True)
    r = decimal(rate, 'rate')
    if r > 1 or r == 0:
        raise ValueError('positive rate at most 1 required')
    return str((target / r).quantize(C, rounding=ROUND_UP))
