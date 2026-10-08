"""Independent synthetic collateral tests. NOT a RecoveryOS payment engine."""
from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from pathlib import Path
import json

DATA = json.loads((Path(__file__).parent / 'commercial_truth.json').read_text())
D = lambda value: Decimal(str(value))
CENT = D('0.01')

def cents(value):
    return D(value).quantize(CENT, rounding=ROUND_HALF_UP)

def require(condition, message):
    if not condition:
        raise ValueError(message)

def worked_invoice(w):
    require(w['sample_only'] and w['independent_from_public_aggregate'], 'not a detached sample')
    require(w['currency'] == 'USD', 'unsupported currency')
    lo, hi, at = map(date.fromisoformat, (w['contract_effective_start'],w['contract_effective_end'],w['shipment_date']))
    require(lo <= at <= hi, 'rate source not effective on shipment date')
    for key in ('rate_source_id','invoice_id','shipment_id','authorized_service_source_id'):
        require(str(w.get(key, '')).strip(), 'missing source reference: '+key)
    expected = cents(D(w['base_charge']) + cents(D(w['base_charge'])*D(w['fuel_rate'])) + D(w['authorized_liftgate']))
    billed = cents(expected + D(w['second_unsupported_liftgate']))
    difference = cents(billed-expected)
    require(expected == D(w['expected_charge']), 'expected total mismatch')
    require(billed == D(w['billed_charge']), 'actual billed total mismatch')
    require(difference == D(w['candidate_variance']), 'difference mismatch')
    return dict(expected=str(expected),billed=str(billed),variance=str(difference))

def stage_policy(stage, *, evidence=False, customer_authorization=False, carrier_approval=False, posted=False):
    allowed = {'candidate','supported','authorized','carrier_approved','received'}
    require(stage in allowed, 'invalid stage')
    if stage in ('supported','authorized','carrier_approved','received'):
        require(evidence is True, 'supported stages require source evidence')
    if stage in ('authorized','carrier_approved','received'):
        require(customer_authorization is True, 'carrier action requires written authorization')
    if stage in ('carrier_approved','received'):
        require(carrier_approval is True, 'carrier acceptance required by sample workflow')
    if stage == 'received':
        require(posted is True, 'carrier approval is not received funds')
    return True

def _exact_settlement_amount(value):
    """Accept only finite, positive exact-cent amounts; never silently round."""
    from decimal import InvalidOperation

    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError('settlement amount must be a positive exact-cent value')
    try:
        amount = D(value)
        if not amount.is_finite() or amount <= 0 or amount != amount.quantize(CENT):
            raise ValueError('settlement amount must be a positive exact-cent value')
        return amount.quantize(CENT)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError('settlement amount must be a positive exact-cent value') from exc


def unique_settlement_ledger(events):
    """Reconcile a synthetic ledger with credit-bound, cumulative reversal caps.

    This demonstrates financial controls only; it does not authenticate the
    posted flags, independent buyer cash, carrier identity, or entitlement.
    """
    require(isinstance(events, (list, tuple)), 'settlement events must be a sequence')
    seen = set()
    original_credits = {}
    credited_allocations = set()
    reversals_by_credit = {}
    gross = D('0.00')
    reversals = D('0.00')

    for event in events:
        require(isinstance(event, dict), 'settlement event must be a record')
        require(event.get('currency') == 'USD', 'cannot combine currencies')
        eid = event.get('id')
        allocation = event.get('allocation')
        require(isinstance(eid, str) and 0 < len(eid) <= 200
                and eid.strip() == eid, 'invalid settlement event ID')
        require(eid not in seen, 'duplicate settlement event ID')
        require(isinstance(allocation, str) and 0 < len(allocation) <= 200
                and allocation.strip() == allocation, 'invalid opportunity allocation')
        require(event.get('posted') is True, 'unposted settlement event cannot be booked')
        amount = _exact_settlement_amount(event.get('amount'))

        if event.get('kind') == 'credit':
            require(allocation not in credited_allocations, 'duplicated opportunity allocation')
            require(event.get('references_event') is None,
                    'credit cannot reference an earlier settlement event')
            credited_allocations.add(allocation)
            original_credits[eid] = (allocation, amount)
            gross += amount
        elif event.get('kind') == 'reversal':
            original = event.get('references_event')
            # Check only the original posted credits, not all seen event IDs.
            # This forbids self-reference, reversal-of-reversal and forward links.
            require(isinstance(original, str) and original in original_credits,
                    'reversal without prior original credit')
            expected_allocation, credited = original_credits[original]
            require(allocation == expected_allocation,
                    'reversal allocation differs from original credit')
            prior_reversals = reversals_by_credit.get(original, D('0.00'))
            require(prior_reversals + amount <= credited,
                    'cumulative reversal exceeds original credit')
            reversals_by_credit[original] = prior_reversals + amount
            reversals += amount
        else:
            raise ValueError('unrecognized financial event')
        seen.add(eid)

    require(reversals <= gross, 'reversal exceeds gross')
    return {
        'gross': str(gross.quantize(CENT)),
        'reversals': str(reversals.quantize(CENT)),
        'net': str((gross - reversals).quantize(CENT)),
    }

def aggregate_arithmetic(a):
    m=a['usd']; gross=D(m['gross_posted_recovery']); rev=D(m['reversals'])
    net=gross-rev; eligible=D(m['published_fee_eligible'])
    require(net==D(m['net_posted_recovery']),'gross/reversal arithmetic contradiction')
    require(net-eligible==D(m['eligibility_difference_unallocated']),'eligibility difference contradicts published numbers')
    return {'gross_to_net_reconciles':True,'fee_eligible_source_verified':False,
        'unallocated_difference_usd':str(net-eligible),
        'aggregate_source_level_verified':bool(a['source_level_aggregate_settlements_available'] and a['source_level_aggregate_invoices_available'])}

def eligible_fee(net, exclusions, rate, *, signed=False, itemization_proven=False):
    require(signed is True and itemization_proven is True, 'do not compute a REAL fee without signed terms and validated attribution')
    n=cents(D(net)-sum((D(v) for v in exclusions),D('0')))
    require(D('0')<=n<=D(net), 'invalid eligible base')
    require(D('0')<=D(rate)<=D('1'), 'invalid percentage')
    return cents(n*D(rate))

def training_fee(amount,rate):
    require(DATA['hypothetical_pricing']['sample_only'], 'no real fee approval')
    fee=cents(D(amount)*D(rate)); return {'fee':str(fee),'remainder_before_costs':str(cents(D(amount)-fee))}