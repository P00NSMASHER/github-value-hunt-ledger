"""Independently authored 2026-10-29 Golden Goose safety holdout.

All jobs are fictional; tests make no claims about billable/collectible funds.
"""
import copy
import unittest
from hydrovac_reconcile import inspect, summarize


def job(name, ticket=None):
    x = {
        'job_id': name,
        'service_date': '2026-09-01',
        'approved_at': '2026-09-02',
        'manifest_approved': True,
        'approved_billable_hours': '4',
        'approved_dump_loads': '1',
        'rate_card': {'signed': True, 'effective_on': '2026-01-01', 'hourly_rate': '175', 'dump_fee': '180'},
        'invoices': [],
        'waiver': False, 'credit': False, 'scope_dispute': False,
    }
    if ticket is not None:
        x['ticket_id'] = ticket
    return x


def invoice(line, hours, dumps):
    return {'invoice_line_id': line, 'issued_on': '2026-09-05', 'state': 'ISSUED',
            'hours_qty': str(hours), 'dump_qty': str(dumps)}


class IndependentHoldout(unittest.TestCase):
    def test_duplicate_ticket_cross_job_cannot_double_count_1760(self):
        a, b = job('JOB-001', 'FT-101'), job('JOB-002', 'FT-101')
        result = summarize([a, b])
        self.assertEqual(result['candidate_discrepancies'], 0)
        self.assertEqual(result['review_only'], 2)
        self.assertEqual(result['illustrative_candidate_gross_usd'], '0.00')

    def test_duplicate_ticket_case_whitespace_normalization(self):
        a, b = job('JOB-003', 'ft-102 '), job('JOB-004', 'FT-102')
        self.assertEqual(summarize([a, b])['candidate_discrepancies'], 0)

    def test_duplicate_ticket_one_leg_invoiced_must_not_pass_as_missing(self):
        a, b = job('JOB-005', 'FT-103'), job('JOB-006', 'FT-103')
        a['invoices'] = [invoice('LINE-A', 4, 1)]
        self.assertEqual(summarize([a, b])['candidate_discrepancies'], 0)

    def test_cross_job_duplicate_invoice_line_blocked(self):
        a, b = job('JOB-007', 'FT-104'), job('JOB-008', 'FT-105')
        a['invoices'] = [invoice('SAME-LINE', 3, 1)]
        b['invoices'] = [invoice('SAME-LINE', 3, 1)]
        self.assertEqual(summarize([a, b])['candidate_discrepancies'], 0)

    def test_split_invoice_exact_quantity_clears(self):
        a = job('JOB-009', 'FT-106')
        a['invoices'] = [invoice('L1', 2, 0), invoice('L2', 2, 1)]
        self.assertEqual(inspect(a)['status'], 'CLEAR_RECONCILED')

    def test_split_invoice_real_short_hours_research_flag(self):
        a = job('JOB-010', 'FT-107')
        a['invoices'] = [invoice('L1', '2', 0), invoice('L2', '1.5', 1)]
        result = inspect(a)
        self.assertEqual(result['status'], 'POTENTIAL_HOURS_GAP')
        self.assertEqual(result['gross_variance_usd'], '87.50')
        self.assertIsNone(result['collectible_usd'])

    def test_intervening_rate_change_stops_monetary_guess(self):
        a = job('JOB-011', 'FT-108')
        a['rate_history'] = [{'signed': True, 'effective_on': '2026-08-01',
                              'hourly_rate': '150', 'dump_fee': '0'}]
        self.assertTrue(inspect(a)['status'].startswith('REVIEW_'))

    def test_post_issue_credit_memo_stops_gap_prediction(self):
        a = job('JOB-012', 'FT-109')
        a['invoices'] = [invoice('L1', 3, 1)]
        a['invoices'][0]['credit_memo_id'] = 'CREDIT-777'
        self.assertTrue(inspect(a)['status'].startswith('REVIEW_'))

    def test_invoice_reversal_stops_gap_prediction(self):
        a = job('JOB-013', 'FT-110')
        a['invoices'] = [invoice('L1', 3, 1)]
        a['invoices'][0]['voided_on'] = '2026-09-07'
        self.assertTrue(inspect(a)['status'].startswith('REVIEW_'))

    def test_waiver_stops_gap_prediction(self):
        a = job('JOB-014', 'FT-111')
        a['waiver'] = True
        self.assertEqual(inspect(a)['status'], 'REVIEW_WAIVER')

    def test_missing_ticket_backward_compatible_research_only(self):
        a = job('JOB-015')
        self.assertEqual(inspect(a)['status'], 'POTENTIAL_UNINVOICED_JOB')
        self.assertIsNone(inspect(a)['collectible_usd'])

    def test_malformed_explicit_ticket_fails_closed(self):
        a = job('JOB-016')
        a['ticket_id'] = '  '
        self.assertTrue(inspect(a)['status'].startswith('REVIEW_'))


if __name__ == '__main__':
    unittest.main()
