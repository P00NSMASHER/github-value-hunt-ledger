"""Synthetic commercial-document calculations. NOT RecoveryOS production tests.
Run: python -m unittest discover -s freight/brand/mission2b -p 'test_collateral_m2c.py' -v
"""
from pathlib import Path
from decimal import Decimal
from datetime import date
import json,unittest,copy
T=json.loads((Path(__file__).parent/'COMMERCIAL_TRUTH_M2C_V1.json').read_text())
D=lambda v:Decimal(str(v))
def invoice(w):
    if w['currency']!='USD': raise ValueError('mixed currencies')
    if not date.fromisoformat(w['contract_effective_start'])<=date.fromisoformat(w['shipment_date'])<=date.fromisoformat(w['contract_effective_end']): raise ValueError('rate not effective')
    for k in ('invoice_id','shipment_id','rate_source_id','authorized_service_source_id'):
        if not w[k]: raise ValueError('source reference absent')
    expected=D(w['base_charge'])+(D(w['base_charge'])*D(w['fuel_rate'])).quantize(D('.01'))+D(w['authorized_liftgate'])
    billed=expected+D(w['second_unsupported_liftgate'])
    if expected!=D(w['expected_charge']) or billed!=D(w['billed_charge']) or billed-expected!=D(w['candidate_variance']): raise ValueError('arithmetic mismatch')
    return expected,billed,billed-expected
def require_stage(stage,evidence=False,authorized=False,approved=False,posted=False):
    if stage not in ('candidate','supported','authorized','carrier_approved','received'):raise ValueError('stage')
    if stage in ('supported','authorized','carrier_approved','received') and not evidence:raise ValueError('evidence')
    if stage in ('authorized','carrier_approved','received') and not authorized:raise ValueError('customer authorization')
    if stage in ('carrier_approved','received') and not approved:raise ValueError('carrier approval')
    if stage=='received' and not posted:raise ValueError('posting')
    return True
# Execute the actual collateral financial control rather than duplicating
# a weaker ledger implementation inside the test suite.
from freight.brand.mission2b.source.financial_controls import unique_settlement_ledger

def ledger(events):
    return D(unique_settlement_ledger(events)['net'])

def quote_fee(base,rate,*,signed=False,verified=False):
    if not signed or not verified:raise ValueError('fee base unapproved')
    return (D(base)*D(rate)).quantize(D('.01'))
class CollateralControls(unittest.TestCase):
    def test_worked_invoice(self):self.assertEqual(invoice(T['worked_invoice'])[2],D('125'))
    def test_effective_date(self):
        w=dict(T['worked_invoice'],shipment_date='2027-01-01')
        with self.assertRaisesRegex(ValueError,'effective'):invoice(w)
    def test_missing_reference(self):
        w=dict(T['worked_invoice'],rate_source_id='')
        with self.assertRaisesRegex(ValueError,'reference'):invoice(w)
    def test_currency(self):
        w=dict(T['worked_invoice'],currency='EUR')
        with self.assertRaisesRegex(ValueError,'currencies'):invoice(w)
    def test_status_support_requires_evidence(self):
        with self.assertRaisesRegex(ValueError,'evidence'):require_stage('supported')
    def test_claim_requires_customer_authorization(self):
        with self.assertRaisesRegex(ValueError,'authorization'):require_stage('authorized',evidence=True)
    def test_approved_claim_is_not_cash(self):
        with self.assertRaisesRegex(ValueError,'posting'):require_stage('received',evidence=True,authorized=True,approved=True)
    def test_duplicate_event(self):
        e=dict(id='CR1',kind='credit',allocation='A',currency='USD',amount='125',posted=True)
        with self.assertRaisesRegex(ValueError,'duplicate settlement event'):ledger([e,e])
    def test_duplicate_allocation(self):
        e=dict(id='CR1',kind='credit',allocation='A',currency='USD',amount='125',posted=True)
        with self.assertRaisesRegex(ValueError,'opportunity allocation'):ledger([e,dict(e,id='CR2')])
    def test_unposted_credit(self):
        with self.assertRaisesRegex(ValueError,'unposted'):ledger([dict(id='CR1',kind='credit',allocation='A',currency='USD',amount='125',posted=False)])
    def test_credit_reversal(self):
        self.assertEqual(ledger([dict(id='CR1',kind='credit',allocation='A',currency='USD',amount='125',posted=True),dict(id='RV1',kind='reversal',allocation='A',currency='USD',amount='25',posted=True,references_event='CR1')]),D('100'))
    def test_valid_partial_reversals_preserve_exact_net(self):
        events=[
            dict(id='CR1',kind='credit',allocation='A',currency='USD',amount='100.00',posted=True),
            dict(id='RV1',kind='reversal',allocation='A',currency='USD',amount='40.00',posted=True,references_event='CR1'),
            dict(id='RV2',kind='reversal',allocation='A',currency='USD',amount='60.00',posted=True,references_event='CR1'),
        ]
        self.assertEqual(ledger(events),D('0.00'))
        self.assertEqual(unique_settlement_ledger(events),dict(gross='100.00',reversals='100.00',net='0.00'))

    def test_self_reversals_do_not_launder_credits(self):
        events=[
            dict(id='CR1',kind='credit',allocation='A',currency='USD',amount='100.00',posted=True),
            dict(id='RV1',kind='reversal',allocation='A',currency='USD',amount='10.00',posted=True,references_event='RV1'),
        ]
        with self.assertRaisesRegex(ValueError,'prior original credit'):ledger(events)

    def test_reversal_of_reversal_is_not_a_credit(self):
        events=[
            dict(id='CR1',kind='credit',allocation='A',currency='USD',amount='100.00',posted=True),
            dict(id='RV1',kind='reversal',allocation='A',currency='USD',amount='20.00',posted=True,references_event='CR1'),
            dict(id='RV2',kind='reversal',allocation='A',currency='USD',amount='10.00',posted=True,references_event='RV1'),
        ]
        with self.assertRaisesRegex(ValueError,'prior original credit'):ledger(events)

    def test_cumulative_returns_cannot_exceed_their_source_credit(self):
        events=[
            dict(id='CR1',kind='credit',allocation='A',currency='USD',amount='100.00',posted=True),
            dict(id='CR2',kind='credit',allocation='B',currency='USD',amount='200.00',posted=True),
            dict(id='RV1',kind='reversal',allocation='A',currency='USD',amount='80.00',posted=True,references_event='CR1'),
            dict(id='RV2',kind='reversal',allocation='A',currency='USD',amount='30.00',posted=True,references_event='CR1'),
        ]
        # Gross still exceeds all returns: the original aggregate-only guard failed here.
        with self.assertRaisesRegex(ValueError,'cumulative reversal exceeds original credit'):ledger(events)

    def test_reversal_cannot_use_another_originals_allocation(self):
        events=[
            dict(id='CR1',kind='credit',allocation='A',currency='USD',amount='100.00',posted=True),
            dict(id='CR2',kind='credit',allocation='B',currency='USD',amount='100.00',posted=True),
            dict(id='RV1',kind='reversal',allocation='B',currency='USD',amount='20.00',posted=True,references_event='CR1'),
        ]
        with self.assertRaisesRegex(ValueError,'allocation differs'):ledger(events)

    def test_posting_assertion_must_be_exact_true(self):
        for bad in (False,'false','true',1,None):
            with self.subTest(value=bad):
                c=dict(id='CR1',kind='credit',allocation='A',currency='USD',amount='100.00',posted=bad)
                with self.assertRaisesRegex(ValueError,'unposted'):ledger([c])
                c['posted']=True
                r=dict(id='RV1',kind='reversal',allocation='A',currency='USD',amount='5.00',posted=bad,references_event='CR1')
                with self.assertRaisesRegex(ValueError,'unposted'):ledger([c,r])

    def test_settlement_amount_requires_finite_exact_cents(self):
        for bad in ('NaN','Infinity','-10.00','12.345',0,True,'abc',float('nan')):
            with self.subTest(value=str(bad)):
                c=dict(id='CR1',kind='credit',allocation='A',currency='USD',amount=bad,posted=True)
                with self.assertRaisesRegex(ValueError,'exact-cent'):ledger([c])

    def test_duplicate_reversal_event_never_double_counts(self):
        c=dict(id='CR1',kind='credit',allocation='A',currency='USD',amount='100.00',posted=True)
        r=dict(id='RV1',kind='reversal',allocation='A',currency='USD',amount='20.00',posted=True,references_event='CR1')
        with self.assertRaisesRegex(ValueError,'duplicate settlement event'):ledger([c,r,r])

    def test_aggregate_fee_gap_remains_unverified(self):
        a=T['synthetic_public_aggregate']
        v=a['usd']
        self.assertEqual(D(v['net_posted_recovery'])-D(v['published_fee_eligible']),D('1650.00'))
        self.assertEqual(a['eligible_base_verdict'],'UNVERIFIED_UNALLOCATED_DIFFERENCE')
        self.assertFalse(a['source_level_aggregate_settlements_available'])
        self.assertFalse(a['source_level_aggregate_invoices_available'])

    def test_aggregate_net(self):
        v=T['synthetic_public_aggregate']['usd'];self.assertEqual(D(v['gross_posted_recovery'])-D(v['reversals']),D(v['net_posted_recovery']))
    def test_unallocated_eligibility(self):
        v=T['synthetic_public_aggregate']['usd'];self.assertEqual(D(v['net_posted_recovery'])-D(v['published_fee_eligible']),D('1650'))
        self.assertEqual(T['synthetic_public_aggregate']['eligible_base_verdict'],'UNVERIFIED_UNALLOCATED_DIFFERENCE')
    def test_no_real_client_proof(self):self.assertFalse(T['synthetic_public_aggregate']['real_customer_outcome'])
    def test_no_approved_rate(self):
        with self.assertRaisesRegex(ValueError,'unapproved'):quote_fee('125','.20')
        self.assertFalse(T['hypothetical_pricing']['approved_retally_rate'])
    def test_stages_counts(self):
        c=T['synthetic_public_aggregate']['counts']
        ns=[c[k] for k in ('records_reviewed','candidates','supported','authorized','submitted','carrier_approved','posted_events')]
        self.assertEqual(ns,sorted(ns,reverse=True))
if __name__=='__main__':unittest.main()
