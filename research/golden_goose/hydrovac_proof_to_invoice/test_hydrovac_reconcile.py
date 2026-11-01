import copy
import json
import unittest
from pathlib import Path
from hydrovac_reconcile import inspect, summarize

DATA=json.loads((Path(__file__).parent/'synthetic_100_jobs.json').read_text())['jobs']

class AuditTests(unittest.TestCase):
    def row(self, category):
        return copy.deepcopy(next(x for x in DATA if x['fixture_category']==category))

    def test_synthetic_100_job_ground_truth(self):
        s=summarize(DATA)
        self.assertEqual((s['total_jobs'],s['candidate_discrepancies'],s['review_only'],s['clear']), (100,12,18,70))
        self.assertEqual(s['illustrative_candidate_gross_usd'],'4940.00')
        self.assertIsNone(s['verified_collectible_usd'])
        self.assertEqual(s['verified_customer_revenue_usd'],0)

    def test_all_planted_detection(self):
        for k in ('missing_invoice','missing_hours','missing_dump'):
            with self.subTest(k=k):
                self.assertTrue(inspect(self.row(k))['status'].startswith('POTENTIAL_'))

    def test_no_clean_false_candidates(self):
        for j in DATA[:70]:
            self.assertEqual(inspect(j)['status'],'CLEAR_RECONCILED')

    def test_no_ambiguous_false_candidates(self):
        for j in DATA[-18:]:
            self.assertTrue(inspect(j)['status'].startswith('REVIEW_'))

    def test_missing_invoice_component_value(self):
        self.assertEqual(inspect(self.row('missing_invoice'))['gross_variance_usd'],'880.00')

    def test_missing_hour_component_value(self):
        self.assertEqual(inspect(self.row('missing_hours'))['gross_variance_usd'],'175.00')

    def test_missing_dump_component_value(self):
        self.assertEqual(inspect(self.row('missing_dump'))['gross_variance_usd'],'180.00')

    def test_unsigned_rate_fails_closed(self):
        x=self.row('missing_invoice'); x['rate_card']['signed']=False
        self.assertEqual(inspect(x)['status'],'REVIEW_RATE_AUTHORITY')

    def test_missing_manifest_fails_closed(self):
        x=self.row('missing_invoice'); x['manifest_approved']=False
        self.assertEqual(inspect(x)['status'],'REVIEW_PROOF')

    def test_waiver_prevents_claimable_guess(self):
        x=self.row('missing_invoice'); x['waiver']=True
        self.assertEqual(inspect(x)['status'],'REVIEW_WAIVER')

    def test_existing_credit_prevents_rebilling(self):
        x=self.row('missing_invoice'); x['credit']=True
        self.assertEqual(inspect(x)['status'],'REVIEW_EXISTING_CREDIT')

    def test_scope_dispute_blocks_positive(self):
        x=self.row('missing_invoice'); x['scope_dispute']=True
        self.assertEqual(inspect(x)['status'],'REVIEW_SCOPE_DISPUTE')

    def test_grace_blocks_new_work(self):
        x=self.row('missing_invoice'); x['service_date']='2026-10-20'; x['approved_at']='2026-10-21'
        self.assertEqual(inspect(x)['status'],'REVIEW_WITHIN_GRACE')

    def test_false_future_invoice_blocked(self):
        x=self.row('clean'); x['invoices'][0]['issued_on']='2026-11-02'
        self.assertEqual(inspect(x)['status'],'REVIEW_FUTURE_EVIDENCE')

    def test_future_rate_card_cannot_authorize_old_job(self):
        x=self.row('missing_invoice'); x['rate_card']['effective_on']='2026-10-01'
        self.assertEqual(inspect(x)['status'],'REVIEW_RATE_AUTHORITY')

    def test_duplicate_invoice_line_blocks(self):
        x=self.row('clean'); x['invoices'].append(copy.deepcopy(x['invoices'][0]))
        self.assertEqual(inspect(x)['status'],'REVIEW_DUPLICATE_INVOICE_LINE')

    def test_draft_does_not_count_as_issued(self):
        x=self.row('missing_hours'); x['invoices'][0]['state']='DRAFT'
        self.assertEqual(inspect(x)['status'],'REVIEW_DRAFT_ONLY')

    def test_qty_overbill_review(self):
        x=self.row('clean'); x['invoices'][0]['dump_qty']='2'
        self.assertEqual(inspect(x)['status'],'REVIEW_OVERBILLING_OR_RECONCILIATION')

    def test_multi_component_gap(self):
        x=self.row('missing_hours'); x['invoices'][0]['dump_qty']='0'
        v=inspect(x)
        self.assertEqual(v['status'],'POTENTIAL_MULTIPLE_COMPONENT_GAP')
        self.assertEqual(v['gross_variance_usd'],'355.00')

    def test_malformed_amounts_block(self):
        for bad in ('NaN','Infinity','-1',True,'bogus'):
            with self.subTest(bad=bad):
                x=self.row('missing_invoice');x['approved_billable_hours']=bad
                self.assertEqual(inspect(x)['status'],'REVIEW_INVALID_INPUT')

    def test_invalid_timestamp_block(self):
        for bad in ('2026-02-30','2026-9-15','nonsense'):
            with self.subTest(bad=bad):
                x=self.row('missing_invoice');x['service_date']=bad
                self.assertEqual(inspect(x)['status'],'REVIEW_INVALID_INPUT')

    def test_no_verified_collectible_on_any_row(self):
        for x in DATA:
            self.assertIsNone(inspect(x)['collectible_usd'])

    def test_issued_invoice_missing_fee_detected(self):
        x=self.row('missing_invoice'); x['invoices']=[{'invoice_line_id':'X','issued_on':'2026-10-01','state':'ISSUED','hours_qty':'0','dump_qty':'0'}]
        v=inspect(x)
        self.assertEqual(v['status'],'POTENTIAL_MULTIPLE_COMPONENT_GAP')
        self.assertEqual(v['gross_variance_usd'],'880.00')

    def test_no_permission_to_treat_gross_as_net(self):
        for x in summarize(DATA)['rows']:
            self.assertNotIn('settled_usd',x)
            self.assertNotIn('payment_usd',x)
            self.assertIsNone(x['collectible_usd'])

if __name__=='__main__':
    unittest.main()
