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
        if (observation.get('catalog_match') is False
                and observation.get('work_type') in dataset.get('excluded_work_types', [])):
            decision = 'UNKNOWN_OUT_OF_SCOPE_NOT_NO_PERMIT'
        elif dataset['event_type'] == 'JOB_APPLICATION':
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
        self.assertEqual(len(d['synthetic_negative_controls']), 4)
        self.assertEqual(d['acceptance_boundaries']['truth_unknown_count'], 4)
        self.assertEqual(d['manifest_sha256'], canonical_hash({k: v for k, v in d.items() if k != 'manifest_sha256'}))

    def test_research_authored_descriptor_digests_match_exact_contents(self):
        self.assertEqual(
            self.doc['schema_descriptor_hash_contract'],
            'RESEARCH_AUTHORED_DESCRIPTOR_SHA256_OF_CANONICAL_JSON_EXCLUDING_SELF_NOT_ORIGINAL_SOURCE_BYTES')
        for source in self.doc['official_sources']:
            self.assertEqual(
                source['schema_descriptor_sha256'],
                canonical_hash({k: v for k, v in source.items() if k != 'schema_descriptor_sha256'}),
                msg=source['dataset_id'])
            self.assertIsNone(source['original_source_bytes_sha256'])

    def test_source_scopes_and_authority_gates(self):
        d = self.doc
        s = {x['dataset_id']: x for x in d['official_sources']}
        self.assertEqual(s['w9ak-ipjd']['event_type'], 'JOB_APPLICATION')
        self.assertEqual(s['w9ak-ipjd']['excluded_work_types'],
                         ['ELECTRICAL', 'ELEVATOR', 'LIMITED_ALTERATION_APPLICATION'])
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
            'job_applications_electrical_nonmatch_is_unknown': 'UNKNOWN_OUT_OF_SCOPE_NOT_NO_PERMIT',
        }
        self.assertEqual({x['id']: x['decision'] for x in evaluate(self.doc)}, expected)
        self.assertTrue(all(x['independent_truth'] is None for x in evaluate(self.doc)))
        for x in self.doc['synthetic_negative_controls']:
            self.assertEqual(x['provenance_class'], 'SYNTHETIC_SCHEMA_NEGATIVE_CONTROL')
            self.assertIsNone(x['real_world_accuracy_label'])

    def test_community_view_is_not_an_official_original_dataset(self):
        """An NYC Open Data host/title does not establish DOB publisher endorsement."""
        from freight.unified_research_lab import permitplate_catalog_in_scope, permitplate_url_in_scope
        sample_path = FIXTURE.parent / 'nyc_dob_community_view_v1.json'
        pack = json.loads(sample_path.read_text(encoding='utf-8'))
        self.assertEqual(pack['evaluation_family'], 'GOVERNMENT_PERMIT_SOURCE_PROVENANCE_ONLY')
        self.assertEqual(pack['real_record_count'], 0)
        self.assertEqual(pack['independent_issuance_labels'], 0)
        self.assertEqual(len(pack['synthetic_metadata_replays']), 2)
        observed = {r['dataset_id']: r for r in pack['synthetic_metadata_replays']}
        official = observed['rbx6-tga4']
        community = observed['qnmk-7xra']
        # Reproduce the precise limitation in the existing title-only scout.
        for candidate in (official, community):
            self.assertTrue(permitplate_catalog_in_scope(candidate['catalog_resource']))
            self.assertTrue(permitplate_url_in_scope(candidate['source_url']))
            self.assertFalse(candidate['commercial_reuse_authorized'])
            self.assertIsNone(candidate['original_source_bytes_sha256'])
            self.assertIsNone(candidate['independent_issuance_truth'])
            self.assertEqual(candidate['provenance_class'], 'SYNTHETIC_CATALOG_METADATA_REPLAY')
        self.assertFalse(community['portal_endorsed_view'])
        self.assertEqual(community['catalog_kind'], 'COMMUNITY_CREATED_DERIVATIVE_VIEW')
        self.assertEqual(community['parent_dataset_id'], 'rbx6-tga4')
        self.assertEqual(community['expected_source_role'], 'DERIVED_VIEW_REVIEW_ONLY')
        self.assertEqual(official['expected_source_role'], 'ORIGINAL_PUBLISHER_METADATA_RIGHTS_HELD')
        self.assertEqual(official['catalog_kind'], 'ORIGINAL_DATASET')
        # This is a fixture-level provenance gate, not a claim the scout was fixed.
        self.assertEqual(
            {r['dataset_id'] for r in observed.values() if r['catalog_kind'] == 'ORIGINAL_DATASET'
             and r['portal_endorsed_view']}, {'rbx6-tga4'})

    def test_no_private_record_or_invented_commercial_evidence(self):
        dump = json.dumps(self.doc, sort_keys=True).lower()
        self.assertNotIn('customer_payment', dump)
        self.assertNotIn('verified_recovered', dump)
        self.assertTrue(all(x['rights_class'] == 'NYC_PORTAL_PUBLIC_TERMS_AND_DATASET_SUPPLEMENT_CHECK_REQUIRED' for x in self.doc['official_sources']))
        self.assertEqual(self.doc['accuracy_evaluation'], 'NOT_ESTIMABLE_WITHOUT_INDEPENDENT_LABELS')



class NYCDOBOccupancyBoundaryTest(unittest.TestCase):
    """Official NYC source metadata, with four SYNTHETIC non-scoring probes."""

    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(
            (FIXTURE.parent / 'nyc_dob_occupancy_boundary_v1.json')
            .read_text(encoding='utf-8'))

    @staticmethod
    def classify(case):
        facts = case['facts']
        if case['claim'] == 'CO_ISSUED':
            if facts.get('c_of_o_status') != 'Issued' or not facts.get('c_of_o_issuance_date'):
                return 'UNKNOWN_CO_ISSUANCE_NOT_ESTABLISHED'
            return 'CO_ISSUANCE_SOURCE_METADATA_NOT_INDEPENDENT_TRUTH'
        if case['claim'] == 'CURRENT_BUILD_PERMIT_FROM_CO':
            return 'UNKNOWN_NOT_PERMIT_ISSUANCE_EVIDENCE'
        if case['claim'] == 'NO_CO_EVER_FROM_NO_NOW_MATCH':
            if (facts.get('checked_dataset') == 'pkdm-hqz6'
                    and facts.get('event_date', '') < '2021-03-01'):
                return 'UNKNOWN_PRE_DOB_NOW_COHORT'
            return 'UNKNOWN_NO_COMPLETE_NEGATIVE'
        if case['claim'] == 'TWO_PERMITS_FROM_SAME_BIN':
            return 'UNKNOWN_JOIN_CARDINALITY_NOT_PERMITS'
        return 'UNKNOWN_UNSUPPORTED_CLAIM'

    def test_primary_and_historic_source_are_disjoint_coverage_semantics(self):
        p = self.pack
        self.assertEqual(p['schema_version'], 1)
        self.assertEqual(p['primary_source']['dataset_id'], 'pkdm-hqz6')
        self.assertEqual(p['historic_comparison_source']['dataset_id'], 'bs8b-p36w')
        self.assertEqual(p['primary_source']['event_type'],
                         'CERTIFICATE_OF_OCCUPANCY_NOT_WORK_PERMIT')
        self.assertIn('MARCH_2021', p['primary_source']['event_coverage'])
        self.assertIn('MARCH_2021', p['historic_comparison_source']['temporal_coverage'])
        self.assertEqual(p['primary_source']['original_rows_retrieved'], 0)
        self.assertEqual(p['historic_comparison_source']['original_rows_retrieved'], 0)
        self.assertIsNone(p['primary_source']['original_source_bytes_sha256'])
        self.assertIsNone(p['historic_comparison_source']['original_source_bytes_sha256'])

    def test_all_four_synthetic_negatives_and_heldout_trust_boundary(self):
        p = self.pack
        self.assertEqual(p['evaluation']['negative_controls_synthetic'], 4)
        self.assertEqual(len(p['synthetic_controls']), 4)
        self.assertEqual(len(set(x['id'] for x in p['synthetic_controls'])), 4)
        for row in p['synthetic_controls']:
            with self.subTest(case=row['id']):
                self.assertEqual(self.classify(row), row['expected'])
                self.assertEqual(row['provenance'], 'SYNTHETIC_NOT_REAL_RECORD')
                self.assertIsNone(row['independent_real_label'])
        self.assertEqual(p['evaluation']['held_out_real_world_cases'], 0)
        self.assertEqual(p['evaluation']['independently_labeled_issued_build_permits'], 0)
        self.assertEqual(p['evaluation']['measured_accuracy'],
                         'UNKNOWN_ZERO_REAL_INDEPENDENT_LABELS')

    def test_rights_provenance_dedupe_and_separate_engine_handoffs(self):
        p = self.pack
        self.assertEqual(p['primary_source']['source_last_updated_as_reported'], '2026-10-28')
        self.assertEqual(p['rights']['primary_dataset_license_field'], 'UNSPECIFIED')
        self.assertFalse(p['rights']['permitplate_product_commercial_reuse_certified'])
        self.assertFalse(p['rights']['supplemental_dataset_or_third_party_terms_checked'])
        self.assertFalse(p['evaluation']['allowed_scoring'])
        self.assertTrue(p['provenance']['original_publisher_metadata_review_only'])
        self.assertEqual(p['provenance']['current_catalog_content_hash'], 'UNKNOWN_NOT_ACQUIRED')
        self.assertTrue(p['provenance']['entity_join_requires_multiple_independent_keys'])
        self.assertEqual(len(p['consumers']), 5)
        self.assertTrue(p['no_product_code_changes'])
        self.assertTrue(p['no_new_data_services'])


if __name__ == '__main__':
    unittest.main()
