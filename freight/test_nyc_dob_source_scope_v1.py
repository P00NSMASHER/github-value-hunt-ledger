"""Metadata-only NYC DOB coverage checks; no real person, permit record or customer label."""
import hashlib
import json
from pathlib import Path
import unittest

FIXTURE = Path(__file__).parent / 'fixtures' / 'nyc_dob_source_scope_v1.json'


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def evaluate(doc):
    results = []
    registry = {x['dataset_id']: x for x in doc['official_sources']}
    for row in doc['synthetic_negative_controls']:
        dataset = registry[row['dataset_id']]
        claimed = row['untrusted_claim']
        observation = row['row_fields']
        if dataset['event_type'] == 'JOB_APPLICATION':
            decision = 'UNKNOWN_NO_ISSUANCE_EVIDENCE'
        elif dataset['event_type'] == 'PERMIT_RECORD' and observation.get('work_permit') == 'Permit is not yet issued':
            decision = 'NOT_ISSUED_ACCORDING_TO_SOURCE_FIELD'
        elif claimed == 'DOB_NOW_COMPLETE_BY_BIS_ALONE':
            decision = 'INVALID_COVERAGE_CLAIM'
        else:
            decision = 'UNKNOWN_NOT_INDEPENDENTLY_ADJUDICATED'
        results.append({'id': row['id'], 'decision': decision, 'independent_truth': None})
    return results


class NYCDOBScopeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(FIXTURE.read_text(encoding='utf-8'))

    def test_manifest_census_and_canonical_provenance(self):
        d = self.doc
        self.assertEqual(d['schema_version'], 1)
        self.assertEqual(len(d['official_sources']), 3)
        self.assertEqual({s['dataset_id'] for s in d['official_sources']}, {'w9ak-ipjd', 'rbx6-tga4', 'ipu4-2q9a'})
        self.assertEqual(len(d['synthetic_negative_controls']), 3)
        self.assertEqual(d['manifest_sha256'], canonical_hash({k: v for k, v in d.items() if k != 'manifest_sha256'}))

    def test_source_scopes_and_authority_gates(self):
        d = self.doc
        s = {x['dataset_id']: x for x in d['official_sources']}
        self.assertEqual(s['w9ak-ipjd']['event_type'], 'JOB_APPLICATION')
        self.assertEqual(s['rbx6-tga4']['event_type'], 'PERMIT_RECORD')
        self.assertEqual(s['ipu4-2q9a']['coverage'], 'BIS_ONLY_NOT_DOB_NOW')
        self.assertEqual(s['rbx6-tga4']['excluded_work_types'], ['ELECTRICAL', 'ELEVATOR', 'LIMITED_ALTERATION_APPLICATION'])
        for x in d['official_sources']:
            self.assertIsNone(x['original_source_bytes_sha256'])
            self.assertFalse(x['commercial_reuse_authorized'])
            self.assertFalse(x['independent_outcome_adjudicated'])

    def test_negative_controls_prevent_issuance_and_coverage_false_positives(self):
        expected = {
            'filing_is_not_issuance': 'UNKNOWN_NO_ISSUANCE_EVIDENCE',
            'approved_permits_can_include_pending': 'NOT_ISSUED_ACCORDING_TO_SOURCE_FIELD',
            'bis_coverage_is_not_all_dob': 'INVALID_COVERAGE_CLAIM',
        }
        self.assertEqual({x['id']: x['decision'] for x in evaluate(self.doc)}, expected)
        self.assertTrue(all(x['independent_truth'] is None for x in evaluate(self.doc)))
        for x in self.doc['synthetic_negative_controls']:
            self.assertEqual(x['provenance_class'], 'SYNTHETIC_SCHEMA_NEGATIVE_CONTROL')
            self.assertIsNone(x['real_world_accuracy_label'])

    def test_no_private_record_or_invented_commercial_evidence(self):
        dump = json.dumps(self.doc, sort_keys=True).lower()
        self.assertNotIn('customer_payment', dump)
        self.assertNotIn('verified_recovered', dump)
        self.assertTrue(all(x['rights_class'] == 'NYC_PORTAL_PUBLIC_TERMS_AND_DATASET_SUPPLEMENT_CHECK_REQUIRED' for x in self.doc['official_sources']))
        self.assertEqual(self.doc['accuracy_evaluation'], 'NOT_ESTIMABLE_WITHOUT_INDEPENDENT_LABELS')


if __name__ == '__main__':
    unittest.main()
