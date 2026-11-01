"""Independent, read-only replay of the *fictional* legacy StagingTwin event semantics.

This deliberately does not import StagingTwin.act or trust funds_json/journal
as authoritative. Does not authenticate third-party source ownership, signed
fee terms, the physical carrier credit, or production RecoveryOS behavior.
"""
from collections import Counter
import json
from .core import sha

FIELDS = (
 'candidate','validated','authorized_limit','offer','settled','received',
 'reconciled','reversed','fee_earned','fee_collected','fee_refund_due','fee_refunded',
)


def replay_event_money(events):
    f={x:0 for x in FIELDS}
    state='INTAKE'
    consent=False;revoked=False
    journal=[]
    for position,x in enumerate(events,1):
        if x['seq'] != position:
            raise ValueError('EVENT_SEQUENCE_GAP')
        kind=x['kind']; p=json.loads(x['payload_json'])
        if not isinstance(p,dict):raise ValueError('BAD_EVENT_PAYLOAD')
        value=p.get('amount_cents',0)
        if type(value) is not int or value<0:raise ValueError('BAD_EVENT_CENTS')
        seq=x['seq']
        def post(dr,cr,amount):
            if amount:
                journal.append((seq,dr,cr,amount))
        if kind=='INTAKE':
            if position != 1 or value != 0:raise ValueError('INVALID_INTAKE')
        elif kind=='CONSENT':
            if p.get('scope_signed') is not True:raise ValueError('UNSIGNED_EVENT')
            consent=True;revoked=False;state='CONSENTED'
        elif kind=='REVOKE':
            revoked=True;state='REVIEW_REQUIRED'
        elif kind=='FREEZE':state='FROZEN'
        elif kind=='CANDIDATE':f['candidate']=value;state='REVIEW_REQUIRED'
        elif kind=='REVIEW':f['validated']=value;state='VALIDATED' if value else 'NO_FINDING'
        elif kind=='AUTHORIZE':f['authorized_limit']=value;state='AUTHORIZED'
        elif kind=='SUBMIT':state='SUBMITTED'
        elif kind=='ACKNOWLEDGE':state='ACKNOWLEDGED'
        elif kind=='OFFER':f['offer']=value;state='CARRIER_OFFER'
        elif kind=='SETTLE':f['settled']=value;state='SETTLED'
        elif kind=='CREDIT':
            f['received']=value;state='RECEIVED'
            post('customer_credit_pending','carrier_credit_receivable',value)
        elif kind=='RECONCILE':
            f['reconciled']=value;state='RECONCILED'
            post('customer_credit_reconciled','customer_credit_pending',value)
        elif kind=='FEE_INVOICE':
            bps=p.get('fee_bps')
            if type(bps) is not int or not 0<=bps<=5000:
                raise ValueError('BAD_EVENT_FEE_RATE')
            earned=f['reconciled']*bps//10000
            f['fee_earned']=earned;state='FEE_INVOICED'
            post('fee_receivable','recovery_fee_revenue_simulated',earned)
        elif kind=='FEE_PAY':
            f['fee_collected']=value;state='FEE_PAID'
            post('simulated_cash','fee_receivable',value)
        elif kind=='REVERSE':
            f['reversed']+=value
            remaining=max(0,f['reconciled']-f['reversed'])
            if f['fee_earned']:
                bps=p.get('original_fee_bps')
                if type(bps) is not int or not 0<=bps<=5000:
                    raise ValueError('BAD_REVERSAL_FEE_RATE')
                f['fee_refund_due']=max(0,f['fee_collected']-remaining*bps//10000-f['fee_refunded'])
            state='REVERSED'
            post('reversal_expense','customer_credit_reconciled',value)
            post('fee_refund_expense','fee_refund_liability',f['fee_refund_due'])
        elif kind=='REFUND':
            f['fee_refund_due']-=value
            f['fee_refunded']+=value
            state='REVERSED'
            post('fee_refund_liability','simulated_cash',value)
        elif kind=='CLOSE':state='CLOSED'
        elif kind in ('COMPLAIN','MESSAGE'):
            pass
        else:raise ValueError('UNEXPECTED_EVENT_KIND')
    return f,state,consent,revoked,Counter(journal)


def verify_case_source_binding(case):
    p=json.loads(case['public_invoice_json'])
    if not isinstance(p,dict):return False
    if case['source_customer_id']!=p.get('customer_id') or case['invoice_id']!=p.get('invoice_id'):
        return False
    body={
      'tenant_id':case['tenant'],
      'source_customer_id':case['source_customer_id'],
      'invoice_id':case['invoice_id'],
      'source_sha256':case['source_sha256'],
      'case_id':case['case_id'],
      'invoice_public_hash':sha(p),
      'simulated_consent':False,
    }
    return sha(body)==case['binding_hash']


def verify_case_replay(con,case):
    cid=case['case_id']
    events=list(con.execute('SELECT * FROM evidence_events WHERE case_id=? ORDER BY seq',(cid,)))
    try:
        expected,state,consent,revoked,expected_journal=replay_event_money(events)
        actual=json.loads(case['funds_json'])
    except (ValueError,TypeError,KeyError,OverflowError) as e:
        return ['UNREPLAYABLE_CASE:'+cid+':'+type(e).__name__]
    failures=[]
    if actual != expected:
        failures.append('FUND_REPLAY_MISMATCH:'+cid)
    if case['state']!=state:
        failures.append('STATE_REPLAY_MISMATCH:'+cid)
    if case['consent']!=int(consent) or case['revoked']!=int(revoked):
        failures.append('CONSENT_REPLAY_MISMATCH:'+cid)
    actual_journal=Counter((x['seq'],x['debit_account'],x['credit_account'],x['amount_cents'])
           for x in con.execute('SELECT * FROM journal WHERE case_id=?',(cid,)))
    if actual_journal!=expected_journal:
        failures.append('JOURNAL_EVENT_MISMATCH:'+cid)
    try:
        if not verify_case_source_binding(case):
            failures.append('SOURCE_BINDING_TAMPER:'+cid)
    except (ValueError,TypeError,KeyError):
        failures.append('SOURCE_BINDING_TAMPER:'+cid)
    return failures
