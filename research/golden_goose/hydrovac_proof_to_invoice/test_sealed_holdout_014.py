"""Golden Goose iteration 014: independent synthetic holdout, designed before repairs.

No real customer, data access, debt or earned revenue is implied.
"""
import copy
import unittest

from hydrovac_reconcile import inspect, summarize


def job(name='JOB-200', ticket='TK-200'):
    return {
        'job_id': name,
        'ticket_id': ticket,
        'service_date': '2026-09-01',
        'approved_at': '2026-09-02',
        'manifest_approved': True,
        'approved_billable_hours': '4',
        'approved_dump_loads': '1',
        'rate_card': {'signed': True, 'effective_on': '2026-01-01',
                      'hourly_rate': '175', 'dump_fee': '180'},
        'invoices': [],
    }


def invoice(line, hours, dumps, state='ISSUED', issued_on='2026-09-05'):
    return {'invoice_line_id': line, 'issued_on': issued_on, 'state': state,
            'hours_qty': str(hours), 'dump_qty': str(dumps)}


class SealedHoldout014(unittest.TestCase):
    def test_mixed_issued_and_draft_hours_not_money(self):
        x = job()
        x['invoices'] = [invoice('ISS1', 3, 1), invoice('DRAFT1', 1, 0, 'DRAFT')]
        y = inspect(x)
        self.assertTrue(y['status'].startswith('REVIEW_'), y)
        self.assertEqual(y['gross_variance_usd'], '0.00')

    def test_mixed_issued_and_draft_disposal_not_money(self):
        x = job()
        x['invoices'] = [invoice('ISS2', 4, 0), invoice('DRAFT2', 0, 1, 'DRAFT')]
        y = inspect(x)
        self.assertTrue(y['status'].startswith('REVIEW_'), y)
        self.assertEqual(y['gross_variance_usd'], '0.00')

    def test_invoice_ledger_omitted_not_same_as_zero_invoices(self):
        x = job(); del x['invoices']
        self.assertTrue(inspect(x)['status'].startswith('REVIEW_'))

    def test_collision_same_job_id_different_ticket_id(self):
        a, b = job('SAME-JOB', 'T1'), job('SAME-JOB', 'T2')
        y = summarize([a, b])
        self.assertEqual(y['candidate_discrepancies'], 0, y)
        self.assertEqual(y['review_only'], 2, y)

    def test_collision_normalized_job_id(self):
        a, b = job(' same-job ', 'T3'), job('SAME-JOB', 'T4')
        y = summarize([a, b])
        self.assertEqual(y['candidate_discrepancies'], 0, y)

    def test_duplicate_invoice_line_case_whitespace_same_job(self):
        x = job()
        x['invoices'] = [invoice('Line-Q', 2, 0), invoice(' line-q ', 0, 1)]
        self.assertEqual(inspect(x)['status'], 'REVIEW_DUPLICATE_INVOICE_LINE')

    def test_pre_service_invoice_held_for_review(self):
        x = job()
        x['invoices'] = [invoice('PRE1', 3, 1, issued_on='2026-08-20')]
        self.assertTrue(inspect(x)['status'].startswith('REVIEW_'))

    def test_valid_multi_line_issued_stays_clear(self):
        x = job()
        x['invoices'] = [invoice('A', 2, 0), invoice('B', 2, 1)]
        self.assertEqual(inspect(x)['status'], 'CLEAR_RECONCILED')

    def test_valid_omitted_invoice_stays_potential_not_collectible(self):
        x = job()
        y = inspect(x)
        self.assertEqual(y['status'], 'POTENTIAL_UNINVOICED_JOB')
        self.assertIsNone(y['collectible_usd'])

    def test_draft_only_remains_review(self):
        x = job()
        x['invoices'] = [invoice('DR1', 4, 1, 'DRAFT')]
        self.assertEqual(inspect(x)['status'], 'REVIEW_DRAFT_ONLY')

    def test_synthetic_cash_is_always_zero(self):
        x = job(); y = summarize([x])
        self.assertEqual(y['verified_customer_revenue_usd'], 0)
        self.assertIsNone(y['verified_collectible_usd'])


if __name__ == '__main__':
    unittest.main()
