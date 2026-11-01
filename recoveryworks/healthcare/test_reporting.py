import csv
import io
import json
import unittest
from dataclasses import replace

from recoveryworks.healthcare.test_engine import SOURCE, fixture, run, make_batch
from recoveryworks.healthcare.ingestion import canonical_bytes
from recoveryworks.healthcare.reporting import build_report, export_report
from recoveryworks.healthcare.models import InvoiceLine, SourceRef


class ReportingTests(unittest.TestCase):
    def test_rendered_report_never_claims_real_recovery(self):
        batch = fixture()
        report = build_report(run(batch), batch)
        self.assertEqual(report['environment'], 'SYNTHETIC')
        self.assertEqual(report['report_status'], 'REVIEW_ONLY')
        self.assertEqual(report['review_candidate_cents'], 3000)
        self.assertEqual(report['verified_realized_cents'], 0)
        self.assertTrue(report['not_a_claim'])
        self.assertEqual(len(report['findings'][0]['evidence']), 1)
        self.assertTrue(report['findings'][0]['trace'])

    def test_csv_has_numbers_and_no_formula_evaluation(self):
        batch = fixture()
        report = build_report(run(batch), batch)
        report['findings'][0]['evidence'][0]['locator'] = '=HYPERLINK("http://bad.example")'
        raw = export_report(report, 'csv').decode('utf-8')
        rows = list(csv.reader(io.StringIO(raw)))
        self.assertEqual(rows[1][11], '3000')
        self.assertTrue(rows[1][-1].startswith("'="))
        self.assertNotIn('NaN', raw)

    def test_json_roundtrip_has_int_cents_and_scope_hash(self):
        batch = fixture()
        report = build_report(run(batch), batch)
        result = json.loads(export_report(report, 'json'))
        self.assertEqual(result['findings'][0]['expected_cents'], 28000)
        self.assertEqual(result['source_hash'], batch.import_batch.original_hash)
        self.assertTrue(result['findings'][0]['economic_loss_id'])

    def test_report_marks_holds_incomplete(self):
        batch = fixture(receipt_qty='8')
        report = build_report(run(batch), batch)
        self.assertEqual(report['report_status'], 'INCOMPLETE')
        self.assertEqual(report['review_candidate_cents'], 0)
        self.assertGreater(len(report['holds']), 0)

    def test_report_rejects_wrong_source_population(self):
        batch = fixture()
        other = fixture(receipt_qty='8')
        with self.assertRaisesRegex(ValueError, 'REPORT_EVIDENCE_SCOPE_MISMATCH'):
            build_report(run(other), batch)

    def test_export_rejects_bad_format(self):
        batch = fixture()
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_REPORT_FORMAT'):
            export_report(build_report(run(batch), batch), 'pdf')
