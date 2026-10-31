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


class NYCDOBBISAndPublisherReadbackBoundaryTest(unittest.TestCase):
    """One pinned real publisher receipt plus separate metadata-only BIS source."""

    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(
            (FIXTURE.parent / 'nyc_dob_bis_filing_and_now_replay_boundary_v1.json')
            .read_text(encoding='utf-8'))

    @staticmethod
    def guarded_interpretation(case):
        claim, facts = case['claim'], case['facts']
        if claim == 'BIS_NONMATCH_PROVES_NO_NYC_JOB':
            return ('UNKNOWN_SOURCE_EXCLUDES_DOB_NOW' if facts['dob_now_excluded']
                    else 'UNKNOWN_NO_INDEPENDENT_CITYWIDE_NEGATIVE')
        if claim == 'BIS_JOB_APPROVAL_PROVES_ISSUED_PERMIT':
            return ('UNKNOWN_APPLICATION_NOT_PERMIT_ISSUANCE'
                    if facts['event_type'] == 'BIS_JOB_APPLICATION'
                    else 'UNKNOWN_SOURCE_EVENT_TYPE')
        if claim == '20_ROWS_PROVE_20_UNIQUE_PERMITS':
            if facts['published_sample_rows'] != facts['observed_distinct_source_identities']:
                return 'REJECT_ROW_COUNT_AND_PERMIT_COUNT_CONFUSION'
            return 'UNKNOWN_SOURCE_IDENTITIES_NOT_ISSUED_PERMITS'
        if claim == 'THREE_MATCHING_SOURCE_READS_ARE_INDEPENDENT_ISSUANCE_LABELS':
            return ('REJECT_SOURCE_READBACK_AS_INDEPENDENT_ADJUDICATION'
                    if facts['repeat_gets_exact_match'] > 0 and facts['independent_labels'] == 0
                    else 'UNKNOWN_INDEPENDENT_LABEL_VERIFICATION')
        if claim == 'LATEST_ACTION_DATE_PROVES_PAST_ASOF_STATE':
            return ('UNKNOWN_NO_IMMUTABLE_HISTORIC_ASOF'
                    if facts['historic_immutable_snapshot_custodied'] is False
                    else 'UNKNOWN_SNAPSHOT_NEEDS_SOURCE_TRUTH')
        if claim == 'TWO_DOCUMENTS_SAME_JOB_ARE_TWO_ISSUED_PERMITS':
            return ('UNKNOWN_JOB_DOCUMENT_MULTIPLICITY_NOT_PERMIT_COUNT'
                    if len(facts['doc_keys']) > 1 and not facts['permit_registry_match']
                    else 'UNKNOWN_NO_INDEPENDENT_PERMIT_IDENTITY')
        raise ValueError('Unrecognized synthetic control: ' + claim)

    def test_original_source_is_official_not_community_view_and_excludes_now(self):
        p = self.pack
        self.assertEqual(p['schema_version'], 1)
        self.assertEqual(p['newly_reviewed_official_source']['official_dataset_id'], 'ic3t-wcy2')
        s = p['newly_reviewed_official_source']
        self.assertEqual(s['first_published_date'], '2013-04-18')
        self.assertEqual(s['metadata_last_updated_as_reported'], '2026-10-25')
        self.assertEqual(s['source_excludes'], 'ALL_DOB_NOW_JOBS')
        self.assertEqual(s['event_type'], 'BIS_JOB_APPLICATION_NOT_ISSUED_PERMIT')
        self.assertTrue({'job__', 'doc__', 'job_status', 'latest_action_date'}
                        .issubset(set(s['publisher_documented_api_fields'])))
        self.assertEqual(s['original_data_rows_downloaded'], 0)
        self.assertIsNone(s['raw_http_source_bytes_sha256'])
        self.assertIsNone(s['raw_http_response_byte_count'])
        self.assertFalse(p['legal_and_rights']['commercial_scoring_authorized'])
        self.assertFalse(p['legal_and_rights']['supplemental_dataset_or_provider_terms_individually_cleared'])

    def test_original_publisher_receipt_pinned_and_arithmetic_not_accuracy(self):
        r = self.pack['existing_original_publisher_readback']
        self.assertEqual(r['immutable_producer_branch_snapshot_sha'],
                         'c3eec27209b28003f1bedb92589901547784625b')
        self.assertEqual(r['immutable_producer_receipt_git_blob_sha1'],
                         '22ed65ca9c41057637598c19387a5d68b86f0657')
        self.assertEqual(r['producer_receipt_sha256'],
                         'fc60356829cc334280f31e8e0b8864bda561b1707ab3be934f18387e218e931b')
        self.assertEqual(r['producer_canonical_sample_sha256'],
                         '83ddeacca71e2034815021ca608b6ffc69fb2751eb16977d4e668698c529c9eb')
        self.assertEqual(r['sampled_publisher_rows'], r['sample_unique_source_identities'] +
                         r['sample_repeated_source_rows'])
        self.assertEqual((r['sampled_publisher_rows'], r['sample_unique_source_identities'],
                          r['sample_repeated_source_rows']), (20, 19, 1))
        self.assertEqual((r['repeat_gets_checked'], r['repeat_gets_exact_match']), (3, 3))
        self.assertEqual(r['publisher_sample_state'], 'PUBLISHER_REPLAY_DEGRADED')
        self.assertIn('DUPLICATE_SOURCE_IDENTITIES', r['publisher_sample_error_codes'])
        self.assertEqual(r['independent_permit_issuance_outcome_labels'], 0)
        self.assertEqual(r['independent_buyer_opportunity_labels'], 0)
        self.assertIsNone(r['raw_http_source_body_sha256'])
        self.assertEqual(r['original_records_embedded_in_this_pack'], 0)
        self.assertTrue(self.pack['benchmark_readiness']['repeat_source_identity_is_not_automatically_duplicate_legal_permit'])
        self.assertIsNone(self.pack['benchmark_readiness']['permit_scoring_precision'])
        self.assertIsNone(self.pack['benchmark_readiness']['permit_scoring_recall'])

    def test_red_naive_inference_green_guard_on_six_synthetic_cases(self):
        cases = self.pack['synthetic_negative_controls']
        self.assertEqual(len(cases), 6)
        self.assertEqual(len({x['id'] for x in cases}), len(cases))
        self.assertEqual(sum(x['split'] == 'synthetic_holdout' for x in cases), 4)
        for row in cases:
            with self.subTest(control=row['id']):
                # The naive baseline accepts the untrusted claim as proven.
                naive = 'CLAIM_PROVED'
                guarded = self.guarded_interpretation(row)
                self.assertNotEqual(naive, row['expected'])  # red naive baseline
                self.assertEqual(guarded, row['expected'])  # green fixture guard
                self.assertEqual(row['provenance'], 'SYNTHETIC_NOT_REAL_PUBLISHER_ROW')
                self.assertIsNone(row['real_independent_label'])

    def test_publisher_data_quality_not_independent_or_commercial_proof(self):
        b = self.pack['benchmark_readiness']
        self.assertTrue(b['existing_publisher_sample_dedup_arithmetic_reconciles'])
        self.assertFalse(b['underlying_source_receipt_independently_recollected_for_this_pack'])
        self.assertEqual((b['synthetic_calibration_cases'], b['synthetic_heldout_cases']), (2, 4))
        self.assertEqual((b['independent_real_world_heldout_positive_labels'],
                          b['independent_real_world_heldout_negative_labels']), (0, 0))
        self.assertIsNone(b['real_heldout_accuracy'])
        self.assertIsNone(b['field_extraction_accuracy'])
        self.assertEqual(set(self.pack['engine_handoffs']),
                         {'permitplate_48', 'freightrecovery_12', 'recoveryos_12',
                          'capturebrief_52', 'independent_qa_44'})
        safety = self.pack['safety']
        self.assertEqual(safety['official_source_access_requests_added_to_ci'], 0)
        self.assertEqual(safety['customer_medical_student_private_records_saved'], 0)
        self.assertFalse(safety['legacy_15_lab_consolidation_certified'])
        self.assertFalse(safety['product_code_modified'])




class NYCDOBElevatorFilingBoundaryTest(unittest.TestCase):
    """Publisher metadata and SYNTHETIC elevator filing controls, not issuance truth."""

    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads((FIXTURE.parent /
            "nyc_dob_elevator_filing_boundary_v1.json").read_text(encoding="utf-8"))
        cls.cases = {c["id"]: c for c in cls.pack["synthetic_controls"]}

    @staticmethod
    def guard(case):
        k, x = case["kind"], case["facts"]
        if k == "general_build_miss" and x["excluded_elevator"]:
            return "UNKNOWN_ELEVATOR_EXCLUDED_FROM_GENERAL_BUILD"
        if k == "filing_fanout" and x["one_underlying_job"]:
            if len({v["job_number"] for v in x["filings"]}) == 1:
                return "UNKNOWN_TWO_FILINGS_NOT_TWO_BUYER_OPPORTUNITIES"
        if k == "retrospective_suffix" and x["claim_date"] < x["source_observed_date"]:
            if x["job_filing_number"].endswith("-VT") and not x["historic_snapshot_saved"]:
                return "UNKNOWN_CURRENT_SUFFIX_NOT_HISTORIC_ASOF"
        if k == "pending_filing" and not x["certified_independent_issuance"]:
            return "NO_ISSUANCE_PROOF_PENDING_APPLICATION"
        if k == "electrical_reference" and not x["issuer_cross_reference_verified"]:
            return "UNKNOWN_REFERENCE_IS_NOT_SECOND_ELEVATOR_BUYER"
        if k == "community_view" and x["community_created"]:
            return "REJECT_DERIVED_VIEW_NOT_OFFICIAL_ORIGINAL"
        if k == "no_match" and not x["complete_global_elevator_history_proved"]:
            return "UNKNOWN_NONMATCH_NOT_NEGATIVE_ISSUANCE_LABEL"
        return "UNKNOWN_NOT_INDEPENDENTLY_ADJUDICATED"

    def test_official_elevator_source_gap_without_fabricated_original_bytes(self):
        s = self.pack["original_publisher_metadata"]
        self.assertEqual(self.pack["schema_version"], 1)
        self.assertEqual(s["dataset_id"], "kfp4-dz4h")
        self.assertEqual(s["metadata_last_updated_reported"], "2026-10-21")
        self.assertEqual(s["first_public_date"], "2019-10-31")
        self.assertEqual(s["catalog_row_count_approximate"], "71.7K")
        self.assertEqual(s["catalog_columns_reported"], 82)
        self.assertEqual(s["excluded_from"], "DOB_NOW_BUILD_APPROVED_PERMITS_rbx6-tga4")
        self.assertTrue({"job_filing_number", "filing_type", "filing_status",
                         "electrical_permit_number", "elevatordevicetype"}
                        <= set(s["documented_api_fields"]))
        self.assertEqual(s["source_row_bytes_downloaded_this_increment"], 0)
        self.assertIsNone(s["original_response_sha256"])
        self.assertIsNone(s["schema_http_body_sha256"])
        self.assertEqual(s["public_row_ids_retained"], 0)
        self.assertEqual(s["person_or_address_values_retained"], 0)

    def test_synthetic_heldout_labels_not_promoted_into_real_accuracy(self):
        controls = self.pack["synthetic_controls"]
        self.assertEqual(len(controls), 7)
        self.assertEqual(len(self.cases), 7)
        self.assertEqual(sum(x["split"] == "synthetic_calibration" for x in controls), 3)
        self.assertEqual(sum(x["split"] == "synthetic_holdout" for x in controls), 4)
        for c in controls:
            with self.subTest(case=c["id"]):
                self.assertEqual(c["provenance"], "SYNTHETIC_NO_PUBLISHER_ROWS")
                self.assertIsNone(c["independent_real_label"])
                self.assertEqual(self.guard(c), c["expected"])
        b = self.pack["independent_benchmark"]
        self.assertEqual((b["independent_real_positive_labels"],
                          b["independent_real_negative_labels"]), (0, 0))
        self.assertEqual(b["true_real_holdout_cases"], 0)
        self.assertIsNone(b["permit_precision"])
        self.assertIsNone(b["permit_recall"])

    def test_naive_two_filings_and_retroactive_suffix_red_guard_green(self):
        f = self.cases["SYNTH_INITIAL_PLUS_PAA_FANOUT"]
        self.assertEqual(f["facts"]["naive_opportunity_count"], 2)
        self.assertEqual(len({x["job_number"] for x in f["facts"]["filings"]}), 1)
        self.assertNotEqual(self.guard(f), "TWO_BUYERS_CONFIRMED")
        self.assertEqual(self.guard(f), "UNKNOWN_TWO_FILINGS_NOT_TWO_BUYER_OPPORTUNITIES")
        s = self.cases["SYNTH_VT_SUFFIX_RETROACTIVE_ISSUANCE"]
        self.assertTrue(s["facts"]["job_filing_number"].endswith("-VT"))
        self.assertNotEqual(self.guard(s), "ISSUED_AT_HISTORIC_DATE")
        self.assertEqual(self.guard(s), "UNKNOWN_CURRENT_SUFFIX_NOT_HISTORIC_ASOF")
        self.assertEqual(self.guard(self.cases["SYNTH_COMMUNITY_BA3_VIEW_AS_AUTHORITATIVE"]),
                         "REJECT_DERIVED_VIEW_NOT_OFFICIAL_ORIGINAL")

    def test_rights_and_downstream_release_gates_remain_closed(self):
        p = self.pack
        self.assertFalse(p["source_rights"]["additional_provider_or_dataset_terms_review_complete"])
        self.assertFalse(p["source_rights"]["source_specific_commercial_scoring_certified"])
        self.assertFalse(p["independent_benchmark"]["commercial_scoring_allowed"])
        self.assertEqual(set(p["handoffs"]), {"permitplate_48", "retally_recoveryos_12",
                         "freightrecovery_12", "capturebrief_52", "independent_qa_44"})
        self.assertEqual(p["safety"]["new_provider_requests_in_ci"], 0)
        self.assertEqual(p["safety"]["private_customer_medical_student_records"], 0)
        self.assertFalse(p["safety"]["legacy_15_lab_consolidation_certified"])

class NYCDOBLAAApplicationBoundaryTest(unittest.TestCase):
    """First-party NYC LAA source coverage with synthetic-only, non-scoring controls."""

    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads((FIXTURE.parent /
            "nyc_dob_laa_application_boundary_v1.json").read_text(encoding="utf-8"))
        cls.cases = {x["id"]: x for x in cls.pack["synthetic_controls"]}

    @staticmethod
    def guarded_interpretation(case):
        k, x = case["kind"], case["facts"]
        if k == "general_nonmatch" and x["laa_excluded"]:
            return "UNKNOWN_LAA_EXCLUDED_FROM_GENERAL_BUILD"
        if k == "unissued_number" and not x["permit_issued_date"]:
            return "UNKNOWN_ISSUANCE_WITHOUT_DATE_OR_INDEPENDENT_PROOF"
        if k == "issued_expired" and x["permit_expiration_date"] < x["asof"]:
            return "HISTORICAL_SOURCE_ISSUANCE_NOT_ACTIVE_NOW"
        if k == "filing_fanout" and len({a["job_number"] for a in x["filings"]}) == 1:
            return "UNKNOWN_TWO_FILINGS_NOT_TWO_BUYERS"
        if k == "signoff" and x.get("laasign_off_date"):
            return "UNKNOWN_SIGNOFF_NOT_NEW_DEMAND"
        if k == "free_text" and x.get("proposed_work_summary"):
            return "QUARANTINE_FREE_TEXT_FOR_PRIVACY_REVIEW"
        if k == "historical_nonmatch" and not x["complete_history"]:
            return "UNKNOWN_NO_COMPLETE_HISTORICAL_COVERAGE"
        if k == "bin_only_join" and not x["matching_job_number"]:
            return "UNKNOWN_BIN_ONLY_JOIN_NOT_PERMIT_IDENTITY"
        return "UNKNOWN_UNADJUDICATED"

    def test_new_official_laa_source_not_in_general_build(self):
        p, s = self.pack, self.pack["publisher_source"]
        self.assertEqual(p["schema_version"], 1)
        self.assertEqual(s["dataset_id"], "xxbr-ypig")
        self.assertEqual(s["catalog_last_updated_reported"], "2026-10-24")
        self.assertEqual(s["catalog_column_count"], 26)
        self.assertEqual(s["excluded_from_general_build_approved_permits"], "rbx6-tga4")
        self.assertTrue({"job_number", "filing_number", "filing_status_name",
                         "permit_number", "permit_issued_date", "permit_expiration_date",
                         "laasign_off_date", "proposed_work_summary"}
                        <= set(s["documented_public_api_fields"]))
        self.assertEqual(s["original_dataset_rows_downloaded_this_increment"], 0)
        self.assertIsNone(s["original_dataset_http_bytes_sha256"])
        self.assertIsNone(s["original_dataset_metadata_http_body_sha256"])
        self.assertIsNone(s["original_dataset_response_byte_count"])
        self.assertEqual(s["personal_addresses_or_work_descriptions_retained"], 0)

    def test_synthetic_holdouts_falsify_naive_buyer_scoring_without_real_labels(self):
        p, controls = self.pack, self.pack["synthetic_controls"]
        self.assertEqual(len(controls), 8)
        self.assertEqual(len(self.cases), 8)
        self.assertEqual(sum(c["split"] == "synthetic_calibration" for c in controls), 3)
        self.assertEqual(sum(c["split"] == "synthetic_holdout" for c in controls), 5)
        for c in controls:
            with self.subTest(case=c["id"]):
                self.assertEqual(self.guarded_interpretation(c), c["expected"])
                self.assertEqual(c["provenance"], "SYNTHETIC_NOT_OFFICIAL_SOURCE_ROW")
                self.assertIsNone(c["independent_real_label"])
                self.assertNotEqual(c["naive_claim"], c["expected"])
        b = p["benchmark_readiness"]
        self.assertEqual(b["synthetic_holdout_cases"], 5)
        self.assertEqual(b["independent_real_holdout_cases"], 0)
        self.assertEqual(b["independent_real_positive_labels"], 0)
        self.assertEqual(b["independent_real_negative_labels"], 0)
        self.assertIsNone(b["permit_precision"])
        self.assertIsNone(b["permit_recall"])

    def test_metadata_dedup_and_external_publisher_receipt_not_promoted_as_laa(self):
        p = self.pack
        r = p["existing_original_publisher_readback_reference"]
        self.assertEqual(r["source_dataset_id"], "rbx6-tga4")
        self.assertNotEqual(r["source_dataset_id"], p["publisher_source"]["dataset_id"])
        self.assertEqual((r["source_sample_rows"], r["source_distinct_identities"]), (20, 19))
        self.assertEqual(r["source_duplicate_identities"], 1)
        self.assertEqual(r["usable_laa_examples_from_other_cohort"], 0)
        self.assertEqual(r["independent_permit_truth_labels"], 0)
        self.assertEqual(len(r["source_sample_canonical_sha256"]), 64)
        self.assertEqual(len(r["receipt_git_blob_sha1"]), 40)
        self.assertFalse(p["dedup_and_temporal_rules"]["BIN_only_cross_dataset_join_allowed"])
        self.assertFalse(p["dedup_and_temporal_rules"]["complete_history_proven"])

    def test_critical_unknowns_and_source_rights_do_not_open_commercial_gate(self):
        p = self.pack
        self.assertFalse(p["rights"]["dataset_specific_rights_checked"])
        self.assertFalse(p["rights"]["commercial_permit_scoring_cleared"])
        self.assertEqual(p["rights"]["separate_provider_or_embedded_third_party_rights"], "UNKNOWN")
        self.assertFalse(p["benchmark_readiness"]["commercial_scoring_approved"])
        self.assertEqual(set(p["handoffs"]), {"permitplate_48", "freightrecovery_12",
            "recoveryos_12", "capturebrief_52", "independent_qa_44", "executive_director"})
        self.assertFalse(p["safety"]["legacy_15_lab_consolidation_certified"])
        self.assertTrue(p["safety"]["no_production_or_engine_code_changes"])
        self.assertTrue(p["safety"]["no_new_provider_requests_in_test"])
        self.assertEqual(p["safety"]["private_customer_medical_student_records"], 0)


if __name__ == '__main__':
    unittest.main()
