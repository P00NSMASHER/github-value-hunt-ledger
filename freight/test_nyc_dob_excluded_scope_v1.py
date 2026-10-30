"""NYC DOB excluded-scope companion metadata; no permit-record or customer labels."""
import hashlib
import json
from pathlib import Path
import unittest

PACK = Path(__file__).parent / 'fixtures' / 'nyc_dob_excluded_scope_v1.json'


def sha256_without_self_hash(doc):
    payload = {k: v for k, v in doc.items() if k != 'manifest_sha256'}
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def evaluate_core_nonmatch_as_evidence(doc):
    # Absence from a scope-excluding core catalog cannot establish permit absence.
    return {x['work_type']: 'UNKNOWN_NOT_IN_CORE_SCOPE' for x in doc['synthetic_negative_controls']}


class TestNYCDOBExcludedScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PACK.read_text(encoding='utf-8'))

    def test_canonical_manifest(self):
        d = self.doc
        self.assertEqual(d['schema_version'], 1)
        self.assertEqual(d['pack_id'], 'RETALLY_NYC_DOB_EXCLUDED_SCOPE_V1')
        self.assertEqual(d['manifest_sha256'], sha256_without_self_hash(d))
        self.assertEqual(d['real_permit_records_ingested'], 0)
        self.assertEqual(d['independent_outcome_labels'], 0)

    def test_original_official_companion_metadata_not_issuance_proof(self):
        sources = self.doc['companion_source_candidates']
        self.assertEqual({s['work_type']: s['dataset_id'] for s in sources}, {
            'ELECTRICAL': 'dm9a-ab7w',
            'ELEVATOR': 'kfp4-dz4h',
            'LIMITED_ALTERATION_APPLICATION': 'xxbr-ypig',
        })
        for s in sources:
            with self.subTest(s=s['dataset_id']):
                self.assertEqual(s['publisher'], 'NYC Department of Buildings')
                self.assertEqual(s['event_type'], 'APPLICATION_NOT_ISSUANCE_ADJUDICATION')
                self.assertTrue(s['official_url'].startswith('https://data.cityofnewyork.us/d/'))
                self.assertIsNone(s['original_source_bytes_sha256'])
                self.assertFalse(s['commercial_reuse_authorized'])
                self.assertFalse(s['independent_issuance_adjudicated'])
                self.assertIsNone(s['independent_outcome_label'])

    def test_core_nonmatches_are_unknown_not_negative_labels(self):
        controls = self.doc['synthetic_negative_controls']
        self.assertEqual(len(controls), 3)
        self.assertEqual(set(evaluate_core_nonmatch_as_evidence(self.doc).values()), {'UNKNOWN_NOT_IN_CORE_SCOPE'})
        self.assertEqual({x['work_type'] for x in controls}, {
            'ELECTRICAL', 'ELEVATOR', 'LIMITED_ALTERATION_APPLICATION'
        })
        for x in controls:
            self.assertEqual(x['provenance'], 'SYNTHETIC_NEGATIVE_CONTROL')
            self.assertFalse(x['core_catalog_match'])
            self.assertIsNone(x['independent_issued_permit_truth'])
            self.assertEqual(x['expected_decision'], 'UNKNOWN_NOT_IN_CORE_SCOPE')

    def test_electrical_detail_rows_are_not_distinct_issued_permits(self):
        """Publisher-documented one-to-many detail grain is not permit truth."""
        src = self.doc['source_join_cardinality_candidate']
        ctrl = self.doc['synthetic_join_cardinality_negative_control']
        self.assertEqual(src['dataset_id'], 'xmmq-y7za')
        self.assertEqual(src['official_url'], 'https://data.cityofnewyork.us/d/xmmq-y7za')
        self.assertEqual(src['row_grain'], 'ELECTRICAL_SCOPE_DETAIL_MULTIPLE_PER_JOB_FILING')
        self.assertIsNone(src['original_source_bytes_sha256'])
        self.assertFalse(src['commercial_reuse_authorized'])
        self.assertFalse(src['independent_issuance_adjudicated'])
        self.assertFalse(src['independently_verified_join'])
        self.assertEqual(ctrl['provenance'], 'SYNTHETIC_JOIN_NEGATIVE_CONTROL')
        rows = ctrl['details']
        self.assertEqual(len(rows), ctrl['expected_source_detail_rows'])
        self.assertEqual(len({row['job_filing_number'] for row in rows}),
                         ctrl['expected_distinct_job_filings'])
        self.assertEqual(len(rows), 2)
        self.assertEqual(ctrl['expected_distinct_job_filings'], 1)
        self.assertIsNone(ctrl['expected_issued_permit_count'])
        self.assertIsNone(ctrl['independent_issuance_truth'])
        self.assertEqual(ctrl['expected_decision'], 'UNKNOWN_NO_ISSUANCE_ADJUDICATION')

    def test_base_job_is_not_a_unique_filing_key(self):
        """Synthetic counterexample: collapsing distinct filing suffixes loses work."""
        scope = self.doc['source_filing_grain_candidate']
        self.assertEqual(scope['official_url'],
                         'https://www.nyc.gov/site/buildings/industry/dob-now-build-faqs.page')
        self.assertEqual(scope['independent_issuance_adjudicated'], False)
        self.assertIsNone(scope['original_source_bytes_sha256'])
        ctrl = self.doc['synthetic_base_job_multi_filing_negative_control']
        filings = ctrl['filings']
        base_only_count = len({r['base_job_number'] for r in filings})
        distinct_filing_count = len({r['job_filing_number'] for r in filings})
        self.assertEqual(base_only_count, 1)
        self.assertEqual(distinct_filing_count, 2)
        self.assertNotEqual(base_only_count, distinct_filing_count)
        self.assertEqual({r['work_type'] for r in filings}, {'PL', 'EL'})
        self.assertEqual(distinct_filing_count, ctrl['expected_distinct_filing_count'])
        self.assertIsNone(ctrl['independent_issuance_truth'])
        self.assertEqual(ctrl['expected_decision'],
                         'DISTINCT_FILINGS_WITH_UNKNOWN_PERMIT_ISSUANCE')
        self.assertEqual(ctrl['provenance'], 'SYNTHETIC_JOIN_NEGATIVE_CONTROL')


    def _assert_electrical_application_catalog_contract(self, d):
        x = d["electrical_application_catalog_metadata_2026_10_28"]
        self.assertEqual(x["official_dataset_id"], "dm9a-ab7w")
        self.assertEqual(x["official_metadata_url"],
                         "https://data.cityofnewyork.us/api/views/dm9a-ab7w")
        self.assertEqual(x["publisher_rows_updated_at_utc"],
                         "2026-10-27T21:44:12Z")
        self.assertEqual(x["row_identifier_column_id"], 634408547)
        self.assertEqual(x["row_identifier_field"], "job_filing_number")
        self.assertEqual(x["source_reported_cached_filing_rows"], 596085)
        self.assertEqual(x["source_reported_cached_new_job_filings"], 485091)
        self.assertEqual(x["source_reported_cached_post_approval_amendments"], 96184)
        self.assertEqual(x["source_reported_cached_subsequent_filings"], 14810)
        self.assertEqual(x["source_reported_cached_status_permit_issued"], 151201)
        self.assertEqual(
            x["source_reported_cached_new_job_filings"]
            + x["source_reported_cached_post_approval_amendments"]
            + x["source_reported_cached_subsequent_filings"],
            x["source_reported_cached_filing_rows"])
        self.assertTrue(x["cached_filing_type_count_sum_matches_cached_rows"])
        self.assertTrue(x["source_description_allows_one_base_job_many_filings"])
        self.assertTrue(x["publisher_catalog_cached_stats_not_live_row_query"])
        self.assertFalse(x["raw_original_http_bytes_in_custody"])
        self.assertIsNone(x["original_http_response_sha256"])
        self.assertFalse(x["source_row_join_independently_validated"])
        self.assertTrue(x["citywide_general_open_data_reuse_allowed"])
        self.assertFalse(
            x["source_specific_terms_privacy_and_commercial_scoring_review_complete"])
        self.assertFalse(x["commercial_customer_scoring_approved"])
        self.assertEqual(x["independently_heldout_current_permit_labels"], 0)
        self.assertEqual(x["independently_heldout_issuance_labels"], 0)
        self.assertIsNone(x["confirmed_distinct_real_permit_count"])
        self.assertEqual(x["verified_retally_customer_recovery_cents"], 0)
        controls = x["synthetic_negative_controls"]
        self.assertEqual(len(controls), 4)
        self.assertEqual(len({c["id"] for c in controls}), 4)
        self.assertTrue(all(c["kind"] == "SYNTHETIC" for c in controls))

    def test_electrical_application_cached_metadata_truth(self):
        """First-party cached filing cohorts cannot become independent permits."""
        self._assert_electrical_application_catalog_contract(self.doc)

    def test_forged_electrical_catalog_claims_rejected(self):
        changes = (
            ("source_reported_cached_filing_rows", 596084),
            ("source_reported_cached_post_approval_amendments", 96185),
            ("source_reported_cached_status_permit_issued", 151202),
            ("raw_original_http_bytes_in_custody", True),
            ("original_http_response_sha256", "f" * 64),
            ("source_row_join_independently_validated", True),
            ("commercial_customer_scoring_approved", True),
            ("independently_heldout_issuance_labels", 1),
            ("confirmed_distinct_real_permit_count", 596085),
            ("verified_retally_customer_recovery_cents", 1),
            ("publisher_rows_updated_at_utc", "2026-10-28T21:44:12Z"),
        )
        for field, forged in changes:
            with self.subTest(field=field):
                bad = json.loads(json.dumps(self.doc))
                bad["electrical_application_catalog_metadata_2026_10_28"][field] = forged
                with self.assertRaises(AssertionError):
                    self._assert_electrical_application_catalog_contract(bad)
        bad = json.loads(json.dumps(self.doc))
        bad["electrical_application_catalog_metadata_2026_10_28"]["synthetic_negative_controls"][0]["kind"] = "ORIGINAL"
        with self.assertRaises(AssertionError):
            self._assert_electrical_application_catalog_contract(bad)

    def test_no_cross_dataset_join_or_accuracy_claim(self):
        self.assertEqual(self.doc['cross_dataset_join'], 'UNVERIFIED')
        self.assertEqual(self.doc['freight_error_accuracy'], 'NOT_APPLICABLE')
        self.assertEqual(self.doc['permit_score_accuracy'], 'UNKNOWN_NO_HELD_OUT_LABELS')
        self.assertEqual(self.doc['commercial_use'], 'UNVERIFIED_NOT_APPROVED')


if __name__ == '__main__':
    unittest.main()
