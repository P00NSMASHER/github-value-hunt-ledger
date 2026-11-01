import unittest
from recoveryworks.healthcare.demo import synthetic_example
from recoveryworks.healthcare.reporting import export_report


class DemoTests(unittest.TestCase):
    def test_previously_applied_credit_reduces_open_candidate(self):
        r = synthetic_example()
        self.assertEqual(r['environment'], 'SYNTHETIC')
        self.assertEqual(r['report_status'], 'REVIEW_ONLY')
        self.assertEqual(r['review_candidate_cents'], 20000)
        self.assertEqual(r['verified_realized_cents'], 0)
        self.assertEqual(r['findings'][0]['net_issued_credit_cents'], 10000)
        self.assertEqual(r['findings'][0]['applied_credit_cents'], 10000)
        self.assertEqual(r['population']['unassessed_invoice_lines'], 0)
        self.assertFalse(r['holds'])

    def test_demo_json_roundtrip(self):
        import json
        self.assertEqual(json.loads(export_report(synthetic_example(), 'json'))['currency'], 'USD')
