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
        require(evidence, 'supported stages require source evidence')
    if stage in ('authorized','carrier_approved','received'):
        require(customer_authorization, 'carrier action requires written authorization')
    if stage in ('carrier_approved','received'):
        require(carrier_approval, 'carrier acceptance required by sample workflow')
    if stage == 'received':
        require(posted, 'carrier approval is not received funds')
    return True

def unique_settlement_ledger(events):
    unique = set(); gross=D('0.00'); reversals=D('0.00'); allocations=set()
    for e in events:
        require(e['currency'] == 'USD', 'cannot combine currencies')
        require(e['id'] not in unique, 'duplicate settlement event ID')
        unique.add(e['id'])
        require(e['allocation'] not in allocations or e['kind']=='reversal','duplicated opportunity allocation')
        allocations.add(e['allocation'])
        amount=cents(e['amount']); require(amount>0,'nonpositive event')
        if e['kind']=='credit':
            require(bool(e.get('posted')), 'unposted credit cannot be recovered funds')
            gross += amount
        elif e['kind']=='reversal':
            require(bool(e.get('posted')), 'unposted reversal cannot be booked')
            require(e.get('references_event') in unique, 'reversal without prior original settlement')
            reversals += amount
        else: raise ValueError('unrecognized financial event')
    require(gross>=reversals,'reversal exceeds gross')
    return {'gross':str(gross),'reversals':str(reversals),'net':str(cents(gross-reversals))}

def aggregate_arithmetic(a):
    m=a['usd']; gross=D(m['gross_posted_recovery']); rev=D(m['reversals'])
    net=gross-rev; eligible=D(m['published_fee_eligible'])
    require(net==D(m['net_posted_recovery']),'gross/reversal arithmetic contradiction')
    require(net-eligible==D(m['eligibility_difference_unallocated']),'eligibility difference contradicts published numbers')
    return {'gross_to_net_reconciles':True,'fee_eligible_source_verified':False,
        'unallocated_difference_usd':str(net-eligible),
        'aggregate_source_level_verified':bool(a['source_level_aggregate_settlements_available'] and a['source_level_aggregate_invoices_available'])}

def eligible_fee(net, exclusions, rate, *, signed=False, itemization_proven=False):
    require(signed and itemization_proven, 'do not compute a REAL fee without signed terms and validated attribution')
    n=cents(D(net)-sum((D(v) for v in exclusions),D('0')))
    require(D('0')<=n<=D(net), 'invalid eligible base')
    require(D('0')<=D(rate)<=D('1'), 'invalid percentage')
    return cents(n*D(rate))

def training_fee(amount,rate):
    require(DATA['hypothetical_pricing']['sample_only'], 'no real fee approval')
    fee=cents(D(amount)*D(rate)); return {'fee':str(fee),'remainder_before_costs':str(cents(D(amount)-fee))}