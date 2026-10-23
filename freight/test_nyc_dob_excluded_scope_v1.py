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

    def test_no_cross_dataset_join_or_accuracy_claim(self):
        self.assertEqual(self.doc['cross_dataset_join'], 'UNVERIFIED')
        self.assertEqual(self.doc['freight_error_accuracy'], 'NOT_APPLICABLE')
        self.assertEqual(self.doc['permit_score_accuracy'], 'UNKNOWN_NO_HELD_OUT_LABELS')
        self.assertEqual(self.doc['commercial_use'], 'UNVERIFIED_NOT_APPROVED')


if __name__ == '__main__':
    unittest.main()
