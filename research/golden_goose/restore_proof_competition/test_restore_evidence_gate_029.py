"""Adversarial fully synthetic recovery-evidence acceptance checks."""
import copy
import json
from pathlib import Path
import unittest
from restore_evidence_gate_029 import COMPLETE, PROBLEM, REVIEW, classify, evaluate

DATA = json.loads(Path(__file__).with_name('restore_evidence_fixture_029.json').read_text(encoding='utf-8'))


class StudyInvariants(unittest.TestCase):
    def test_synthetic_cohort_and_honest_naive_baseline(self):
        counts = evaluate(DATA)
        self.assertEqual(counts['synthetic_cases'], 20)
        self.assertEqual(counts['consistent_unauthed'], 4)
        self.assertEqual(counts['needs_review'], 8)
        self.assertEqual(counts['explicit_problems'], 8)
        self.assertEqual(counts['naive_backup_success_count'], 19)
        self.assertEqual(counts['naive_backup_success_not_evidence_complete'], 15)
        self.assertEqual(counts['verified_restores'], 0)
        self.assertEqual(counts['verified_owner_revenue_usd'], '0.00')
        self.assertEqual(counts['verified_collectible_usd'], '0.00')
        self.assertEqual(counts['independent_incumbent_head_to_head'], 'NOT_RUN')
        self.assertEqual(counts['customer_demand'], 'NOT_TESTED')

    def test_mutations_of_good_records_never_green(self):
        for good in DATA['cases'][:4]:
            for key in ['backup_status', 'restore_status', 'app_data_validation',
                        'validation_depth','keys_available','dependencies_recovered',
                        'recovery_minutes','rto_minutes','recovery_point_age_minutes',
                        'rpo_minutes','observer_evidence','attestation_integrity',
                        'evidence_reference','started_at','completed_at']:
                with self.subTest(case=good['id'],key=key):
                    record=copy.deepcopy(good)
                    record[key]=None
                    self.assertNotEqual(classify(record), COMPLETE)

    def test_new_unmodeled_field_cannot_silently_pass(self):
        a=copy.deepcopy(DATA['cases'][0]);a['legal_waiver_override']='EXEMPT'
        self.assertEqual(classify(a),REVIEW)

    def test_boolean_timing_never_coerced_into_number(self):
        a=copy.deepcopy(DATA['cases'][0]);a['recovery_minutes']=True
        self.assertEqual(classify(a),REVIEW)

    def test_numeric_strings_never_coerced(self):
        a=copy.deepcopy(DATA['cases'][0]);a['rto_minutes']='60'
        self.assertEqual(classify(a),REVIEW)

    def test_bad_timestamp_does_not_create_positive(self):
        a=copy.deepcopy(DATA['cases'][0]);a['completed_at']='yesterday'
        self.assertEqual(classify(a),REVIEW)

    def test_not_real_public_evidence_on_self_asserted_observer(self):
        self.assertEqual(classify(DATA['cases'][0]), COMPLETE)
        self.assertEqual(evaluate(DATA)['verified_restores'], 0)

    def test_missing_recovery_measures_never_clear(self):
        a=copy.deepcopy(DATA['cases'][0]);a['recovery_minutes']=-1
        self.assertEqual(classify(a),REVIEW)

    def test_known_time_failure_even_if_scope_missing(self):
        a=copy.deepcopy(DATA['cases'][14]);a['validation_depth']=None
        self.assertEqual(classify(a),PROBLEM)

    def test_rpo_failure_even_if_attestation_unavailable(self):
        a=copy.deepcopy(DATA['cases'][15]);a['attestation_integrity']=None
        self.assertEqual(classify(a),PROBLEM)

    def test_no_external_docs_or_systems_consulted(self):
        self.assertEqual(DATA['real_customer_restore_tests'],0)
        for c in DATA['cases']:
            self.assertTrue(c['evidence_reference'].startswith('SYN-EVID-'))

    def test_owner_revenue_forgery_cannot_enter_cohort(self):
        a=copy.deepcopy(DATA);a['verified_owner_revenue_usd']='199.00'
        with self.assertRaises(ValueError):evaluate(a)

    def test_collectible_forgery_cannot_enter_cohort(self):
        a=copy.deepcopy(DATA);a['verified_collectible_usd']='1000.00'
        with self.assertRaises(ValueError):evaluate(a)

    def test_real_customer_forgery_cannot_enter_cohort(self):
        a=copy.deepcopy(DATA);a['real_customer_restore_tests']=1
        with self.assertRaises(ValueError):evaluate(a)

    def test_unknown_top_level_revenue_claim_cannot_hide(self):
        a=copy.deepcopy(DATA);a['unreviewed_receivable_usd']='500.00'
        with self.assertRaises(ValueError):evaluate(a)

    def test_boolean_customer_count_not_zero(self):
        a=copy.deepcopy(DATA);a['real_customer_restore_tests']=False
        with self.assertRaises(ValueError):evaluate(a)

    def test_snapshot_date_is_fixed(self):
        a=copy.deepcopy(DATA);a['snapshot_date']='2026-10-30'
        with self.assertRaises(ValueError):evaluate(a)

    def test_duplicate_identifiers_block_cohort(self):
        a=copy.deepcopy(DATA);a['cases'][1]['id']=a['cases'][0]['id']
        with self.assertRaises(ValueError):evaluate(a)

    def test_removed_case_blocks_cohort(self):
        a=copy.deepcopy(DATA);a['cases'].pop()
        with self.assertRaises(ValueError):evaluate(a)

    def test_corrupted_goldens_block_acceptance(self):
        a=copy.deepcopy(DATA);a['cases'][0]['expected_class']=PROBLEM
        with self.assertRaises(ValueError):evaluate(a)

    def test_missing_data_never_authentic_by_default(self):
        self.assertEqual(classify({}),REVIEW)
        self.assertEqual(classify(None),REVIEW)


def _make_frozen_case_test(index):
    def test(self):
        case=DATA['cases'][index]
        self.assertEqual(classify(case),case['expected_class'])
    return test

for ix in range(20):
    setattr(StudyInvariants,f'test_frozen_synthetic_{ix+1:02d}',_make_frozen_case_test(ix))

if __name__ == '__main__':
    unittest.main()
